"""Create the three fictional accounts on one explicitly authorized Neon database.

This is a one-shot operator tool. It never migrates, prints credentials, or accepts
local databases. Keep seed_local.py as the only local-development seed command.
"""

from __future__ import annotations

import getpass
import os
import re
import sys
from dataclasses import dataclass
from typing import Callable, Mapping

import httpx
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.core.auth import hash_password
from app.models import (
    AuthSession,
    LoginAttemptEvent,
    LoyaltyMember,
    LoyaltyProgram,
    LoyaltyPurchase,
    LoyaltyRedemption,
    LoyaltyReward,
    LoyaltyStampEntry,
    LoyaltyVisit,
    User,
)

BASELINE_REVISION = "0001_vinculo_baseline"
EXPECTED_DATABASE = "vinculo_demo"
EXPECTED_PROJECT_SLUG = "vinculo-public-demo"
TABLES = {
    "alembic_version", "auth_sessions", "login_attempt_events", "loyalty_members",
    "loyalty_programs", "loyalty_purchases", "loyalty_redemptions", "loyalty_rewards",
    "loyalty_stamp_entries", "loyalty_visits", "users",
}
EMPTY_TABLES = (
    AuthSession, LoginAttemptEvent, LoyaltyMember, LoyaltyPurchase,
    LoyaltyRedemption, LoyaltyStampEntry, LoyaltyVisit, User,
)
ACCOUNTS = (
    ("vinculo-owner", "owner"),
    ("vinculo-cashier", "cashier"),
    ("vinculo-customer", "customer"),
)


class SeedSafetyError(ValueError):
    """A target or database state failed a safety check."""


@dataclass(frozen=True)
class SeedTarget:
    url: URL
    host: str
    database: str
    project_id: str
    branch_id: str

    @property
    def confirmation(self) -> str:
        return f"SEED {self.project_id} {self.branch_id} {self.database}"


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise SeedSafetyError(f"Missing required setting: {key}")
    return value


def validate_target(env: Mapping[str, str]) -> SeedTarget:
    if env.get("VINCULO_REMOTE_SEED_ENABLED") != "true":
        raise SeedSafetyError("Remote seed is disabled; explicitly enable it for this one-shot operation")
    if _required(env, "VINCULO_SEED_PROJECT_SLUG") != EXPECTED_PROJECT_SLUG:
        raise SeedSafetyError("Project slug does not match the dedicated Vínculo demo project")

    project_id = _required(env, "VINCULO_SEED_PROJECT_ID")
    branch_id = _required(env, "VINCULO_SEED_BRANCH_ID")
    if not re.fullmatch(r"[a-z0-9-]{6,80}", project_id) or not re.fullmatch(r"br-[a-z0-9-]{6,80}", branch_id):
        raise SeedSafetyError("Neon project or branch identifier has an invalid format")

    expected_host = _required(env, "VINCULO_SEED_ALLOWED_HOST").lower().rstrip(".")
    expected_database = _required(env, "VINCULO_SEED_ALLOWED_DATABASE")
    if expected_database != EXPECTED_DATABASE:
        raise SeedSafetyError("Allowed database name must be vinculo_demo")

    try:
        url = make_url(_required(env, "VINCULO_SEED_DATABASE_URL"))
    except Exception as exc:
        raise SeedSafetyError("Seed connection URL is invalid") from exc
    host = (url.host or "").lower().rstrip(".")
    if url.get_backend_name() != "postgresql" or url.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise SeedSafetyError("Only PostgreSQL with the Psycopg driver is accepted")
    if not url.password or not url.username:
        raise SeedSafetyError("Seed connection URL must include a database user and password")
    if not host.endswith(".neon.tech") or "-pooler." in host:
        raise SeedSafetyError("Use the direct endpoint of the dedicated Neon project")
    if host != expected_host:
        raise SeedSafetyError("Connection host differs from the explicitly authorized Neon endpoint")
    if url.database != EXPECTED_DATABASE:
        raise SeedSafetyError("Connection database is not the dedicated Vínculo demo database")
    if url.query.get("sslmode", "").lower() not in {"require", "verify-ca", "verify-full"}:
        raise SeedSafetyError("Neon TLS must be required by the seed connection")

    return SeedTarget(url=url, host=host, database=url.database, project_id=project_id, branch_id=branch_id)


def verify_neon_control_plane(
    target: SeedTarget,
    env: Mapping[str, str],
    client_factory: Callable[..., httpx.Client] = httpx.Client,
) -> None:
    """Verify project, branch, and endpoint against Neon before touching PostgreSQL."""
    api_key = _required(env, "NEON_API_KEY")
    expected_branch_name = _required(env, "VINCULO_SEED_BRANCH_NAME")
    try:
        with client_factory(
            base_url="https://console.neon.tech/api/v2",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=10.0,
        ) as client:
            project_response = client.get(f"/projects/{target.project_id}")
            branch_response = client.get(f"/projects/{target.project_id}/branches/{target.branch_id}")
            endpoints_response = client.get(
                f"/projects/{target.project_id}/branches/{target.branch_id}/endpoints"
            )
        if any(response.status_code != 200 for response in
               (project_response, branch_response, endpoints_response)):
            raise SeedSafetyError("Neon did not confirm the requested project, branch, and endpoint")
        project = project_response.json().get("project", {})
        branch = branch_response.json().get("branch", {})
        endpoints = endpoints_response.json().get("endpoints", [])
        endpoint_matches = [item for item in endpoints
                            if item.get("branch_id") == target.branch_id
                            and str(item.get("host", "")).lower().rstrip(".") == target.host
                            and item.get("type") == "read_write"]
        if (project.get("id") != target.project_id
                or project.get("name") != EXPECTED_PROJECT_SLUG
                or branch.get("id") != target.branch_id
                or branch.get("project_id") != target.project_id
                or branch.get("name") != expected_branch_name
                or len(endpoint_matches) != 1):
            raise SeedSafetyError("Neon metadata does not match the dedicated Vínculo target")
    except SeedSafetyError:
        raise
    except Exception:
        # Never include HTTP client exceptions: they may contain request headers or response bodies.
        raise SeedSafetyError("Could not verify the Neon target; nothing was changed") from None


def verify_empty_baseline(connection) -> None:
    table_names = set(inspect(connection).get_table_names(schema="public"))
    if table_names != TABLES:
        raise SeedSafetyError("Database schema is not the exact fresh Vínculo baseline")
    revision = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one_or_none()
    if revision != BASELINE_REVISION:
        raise SeedSafetyError("Database must be at migration 0001_vinculo_baseline")
    if connection.execute(text("SELECT current_database()")).scalar_one() != EXPECTED_DATABASE:
        raise SeedSafetyError("Connected database name does not match the authorized Vínculo database")
    for model in EMPTY_TABLES:
        if connection.execute(select(func.count()).select_from(model.__table__)).scalar_one() != 0:
            raise SeedSafetyError("Database already contains accounts or demo activity; refusing to seed")
    if connection.execute(select(func.count()).select_from(LoyaltyProgram)).scalar_one() != 1:
        raise SeedSafetyError("Fresh baseline must contain exactly one demo loyalty program")
    if connection.execute(select(func.count()).select_from(LoyaltyReward)).scalar_one() != 1:
        raise SeedSafetyError("Fresh baseline must contain exactly one demo reward")
    program = connection.execute(text(
        "SELECT id, code, active, minimum_purchase, stamps_per_purchase, reward_stamps "
        "FROM public.loyalty_programs"
    )).one_or_none()
    reward = connection.execute(text(
        "SELECT name, stamps_cost, active, program_id "
        "FROM public.loyalty_rewards"
    )).one_or_none()
    if (program is None or tuple(program)[1:] != ("DEMO_FIVE_STAMPS", True, 10000, 1, 5)
            or reward is None
            or tuple(reward) != ("Premio de fidelidad", 5, True, program[0])):
        raise SeedSafetyError("Fresh baseline program or reward differs from the fictional Vínculo template")


def collect_passwords(
    prompt: Callable[[str], str] = getpass.getpass,
    *,
    is_tty: bool | None = None,
) -> dict[str, str]:
    if is_tty is None:
        is_tty = sys.stdin.isatty()
    if not is_tty:
        raise SeedSafetyError("Remote seed requires an interactive terminal for hidden password input")
    passwords: dict[str, str] = {}
    for username, _role in ACCOUNTS:
        first = prompt(f"Nueva contraseña para {username} (mínimo 24 caracteres): ")
        second = prompt(f"Confirma contraseña para {username}: ")
        if len(first) < 24:
            raise SeedSafetyError("Each fictional account password must contain at least 24 characters")
        if first != second:
            raise SeedSafetyError("Password confirmation did not match")
        passwords[username] = first
    if len(set(passwords.values())) != len(passwords):
        raise SeedSafetyError("Each fictional account must have a unique password")
    return passwords


def insert_demo_accounts(db: Session, passwords: Mapping[str, str]) -> None:
    created: dict[str, User] = {}
    for username, role in ACCOUNTS:
        user = User(
            username=username,
            name=f"Vínculo demo {role}",
            password_hash=hash_password(passwords[username]),
            role=role,
            active=True,
        )
        db.add(user)
        created[role] = user
    db.flush()
    db.add(LoyaltyMember(user_id=created["customer"].id, display_name="Cliente ficticio Vínculo"))


def run(env: Mapping[str, str] = os.environ, prompt: Callable[[str], str] = getpass.getpass) -> None:
    target = validate_target(env)
    verify_neon_control_plane(target, env)
    typed = input(f"Verifica Neon project {target.project_id}, branch {target.branch_id}, database {target.database}.\n"
                  f"Escribe exactamente '{target.confirmation}' para continuar: ").strip()
    if typed != target.confirmation:
        raise SeedSafetyError("Target confirmation did not match; nothing was changed")
    passwords = collect_passwords(prompt)

    # No migration, retries, or automatic re-seeding. State checks happen both before and
    # inside the transaction to avoid a race with another operator.
    engine = create_engine(target.url, poolclass=NullPool, pool_pre_ping=True, echo=False)
    try:
        with engine.connect() as connection:
            verify_empty_baseline(connection)
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            verify_empty_baseline(db.connection())
            insert_demo_accounts(db, passwords)
            db.commit()
    except Exception:
        engine.dispose()
        # Do not print exception text: drivers can include SQL parameters in error messages.
        raise SeedSafetyError("Remote seed failed; no credentials or SQL parameters were emitted") from None
    engine.dispose()
    print("Created three fictional Vínculo accounts and the customer member. Passwords were not logged.")


def main() -> None:
    try:
        run()
    except SeedSafetyError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    except Exception:
        print("STOP: remote seed aborted; sensitive values were not logged", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
