from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models import LoyaltyMember, User
from app.scripts.seed_remote_demo import (
    EXPECTED_DATABASE,
    EXPECTED_PROJECT_SLUG,
    SeedSafetyError,
    collect_passwords,
    insert_demo_accounts,
    validate_target,
    verify_empty_baseline,
    verify_neon_control_plane,
)


def seed_env(**overrides):
    env = {
        "VINCULO_REMOTE_SEED_ENABLED": "true",
        "VINCULO_SEED_PROJECT_SLUG": EXPECTED_PROJECT_SLUG,
        "VINCULO_SEED_PROJECT_ID": "small-poetry-abcdef12",
        "VINCULO_SEED_BRANCH_ID": "br-demo-branch-abcdef",
        "VINCULO_SEED_BRANCH_NAME": "demo-live",
        "VINCULO_SEED_ALLOWED_HOST": "ep-demo-neon.us-east-2.aws.neon.tech",
        "VINCULO_SEED_ALLOWED_DATABASE": EXPECTED_DATABASE,
        "VINCULO_SEED_DATABASE_URL": (
            "postgresql+psycopg://vinculo_seed:fictional-not-a-secret@"
            "ep-demo-neon.us-east-2.aws.neon.tech/vinculo_demo?sslmode=require"
        ),
        "NEON_API_KEY": "fictional-test-key-not-valid",
    }
    env.update(overrides)
    return env


def test_remote_seed_requires_explicit_enablement():
    with pytest.raises(SeedSafetyError, match="disabled"):
        validate_target(seed_env(VINCULO_REMOTE_SEED_ENABLED="false"))


@pytest.mark.parametrize("overrides", [
    {"VINCULO_SEED_PROJECT_SLUG": "another-project"},
    {"VINCULO_SEED_ALLOWED_HOST": "other-project.neon.tech"},
    {"VINCULO_SEED_ALLOWED_DATABASE": "pos_mvp"},
    {"VINCULO_SEED_DATABASE_URL": "postgresql+psycopg://u:p@localhost/vinculo_demo?sslmode=require"},
    {"VINCULO_SEED_DATABASE_URL": (
        "postgresql+psycopg://u:p@ep-demo-neon.us-east-2.aws.neon.tech/other"
        "?sslmode=require"
    )},
    {"VINCULO_SEED_DATABASE_URL": (
        "postgresql+psycopg://u:p@ep-demo-neon.us-east-2.aws.neon.tech/vinculo_demo"
    )},
    {"VINCULO_SEED_DATABASE_URL": (
        "postgresql+psycopg://u:p@ep-demo-neon-pooler.us-east-2.aws.neon.tech/"
        "vinculo_demo?sslmode=require"
    )},
])
def test_remote_seed_rejects_wrong_or_unsafe_database_target(overrides):
    with pytest.raises(SeedSafetyError):
        validate_target(seed_env(**overrides))


@dataclass
class FakeResponse:
    payload: dict
    status_code: int = 200

    def json(self):
        return self.payload


class FakeNeonClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.responses = {
            "/projects/small-poetry-abcdef12": FakeResponse({"project": {
                "id": "small-poetry-abcdef12", "name": EXPECTED_PROJECT_SLUG,
            }}),
            "/projects/small-poetry-abcdef12/branches/br-demo-branch-abcdef": FakeResponse({"branch": {
                "id": "br-demo-branch-abcdef", "project_id": "small-poetry-abcdef12", "name": "demo-live",
            }}),
            "/projects/small-poetry-abcdef12/branches/br-demo-branch-abcdef/endpoints": FakeResponse({"endpoints": [{
                "branch_id": "br-demo-branch-abcdef",
                "host": "ep-demo-neon.us-east-2.aws.neon.tech",
                "type": "read_write",
            }]}),
        }

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, path):
        return self.responses[path]


def test_neon_preflight_confirms_project_branch_and_exact_endpoint():
    env = seed_env()
    target = validate_target(env)
    verify_neon_control_plane(target, env, FakeNeonClient)

    client = FakeNeonClient()
    client.responses[
        "/projects/small-poetry-abcdef12/branches/br-demo-branch-abcdef"
    ] = FakeResponse({"branch": {
        "id": "br-demo-branch-abcdef", "project_id": "another-project", "name": "demo-live",
    }})
    with pytest.raises(SeedSafetyError, match="metadata"):
        verify_neon_control_plane(target, env, lambda **_kwargs: client)


def test_remote_seed_requires_hidden_interactive_unique_passwords():
    values = iter(["owner-password-fictional-unique-001", "owner-password-fictional-unique-001",
                   "cashier-password-fictional-unique-02", "cashier-password-fictional-unique-02",
                   "customer-password-fictional-unique-03", "customer-password-fictional-unique-03"])
    passwords = collect_passwords(lambda _prompt: next(values), is_tty=True)
    assert len(passwords) == 3
    assert len(set(passwords.values())) == 3

    with pytest.raises(SeedSafetyError, match="interactive terminal"):
        collect_passwords(lambda _prompt: "x" * 24, is_tty=False)

    short = iter(["short", "short"])
    with pytest.raises(SeedSafetyError, match="24 characters"):
        collect_passwords(lambda _prompt: next(short), is_tty=True)

    mismatch = iter(["a" * 24, "b" * 24])
    with pytest.raises(SeedSafetyError, match="did not match"):
        collect_passwords(lambda _prompt: next(mismatch), is_tty=True)


def test_remote_seed_creates_only_fictional_roles_and_customer_member():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    passwords = {
        "vinculo-owner": "owner-fictional-password-unique-0001",
        "vinculo-cashier": "cashier-fictional-password-unique-0002",
        "vinculo-customer": "customer-fictional-password-unique-0003",
    }
    try:
        with Session(engine) as db:
            insert_demo_accounts(db, passwords)
            db.commit()
            users = db.execute(select(User.username, User.role, User.active, User.password_hash)).all()
            members = db.scalars(select(LoyaltyMember)).all()
            assert {(row.username, row.role, row.active) for row in users} == {
                ("vinculo-owner", "owner", True),
                ("vinculo-cashier", "cashier", True),
                ("vinculo-customer", "customer", True),
            }
            assert all(row.password_hash not in passwords.values() for row in users)
            assert len(members) == 1 and members[0].display_name == "Cliente ficticio Vínculo"
            assert db.scalar(select(func.count()).select_from(User)) == 3
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_seed_refuses_nonempty_or_nonbaseline_database(monkeypatch):
    class FakeResult:
        def __init__(self, value):
            self.value = value

        def scalar_one(self):
            return self.value

        def scalar_one_or_none(self):
            return self.value

        def one_or_none(self):
            return self.value

        def __iter__(self):
            return iter(self.value)

    class FakeInspector:
        def get_table_names(self, schema):
            assert schema == "public"
            return ["alembic_version", "auth_sessions", "login_attempt_events", "loyalty_members",
                    "loyalty_programs", "loyalty_purchases", "loyalty_redemptions", "loyalty_rewards",
                    "loyalty_stamp_entries", "loyalty_visits", "users"]

    class FakeConnection:
        def __init__(self):
            self.nonempty = False
            self.bad_revision = False
            self.program = ("demo-program-id", "DEMO_FIVE_STAMPS", True, 10000, 1, 5)
            self.reward = ("Premio de fidelidad", 5, True, "demo-program-id")

        def execute(self, statement):
            sql = str(statement)
            if "version_num" in sql:
                return FakeResult("0034" if self.bad_revision else "0001_vinculo_baseline")
            if "current_database" in sql:
                return FakeResult(EXPECTED_DATABASE)
            if "FROM public.loyalty_programs" in sql:
                return FakeResult(self.program)
            if "FROM public.loyalty_rewards" in sql:
                return FakeResult(self.reward)
            table_name = statement.get_final_froms()[0].name
            count = 1 if table_name in {"loyalty_programs", "loyalty_rewards"} else int(self.nonempty)
            return FakeResult(count)

    monkeypatch.setattr("app.scripts.seed_remote_demo.inspect", lambda _connection: FakeInspector())
    connection = FakeConnection()
    verify_empty_baseline(connection)
    connection.nonempty = True
    with pytest.raises(SeedSafetyError, match="already contains"):
        verify_empty_baseline(connection)
    connection.nonempty = False
    connection.bad_revision = True
    with pytest.raises(SeedSafetyError, match="migration"):
        verify_empty_baseline(connection)
    connection.bad_revision = False
    connection.program = ("demo-program-id", "UNEXPECTED", True, 10000, 1, 5)
    with pytest.raises(SeedSafetyError, match="program or reward"):
        verify_empty_baseline(connection)
