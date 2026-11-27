import pytest

from app.core.db import database_url_for_runtime


def test_database_url_for_runtime_normalizes_postgres_driver():
    parsed = database_url_for_runtime(
        "postgresql://demo_user@db.example.neon.tech/vinculo_demo?sslmode=require"
    )

    assert parsed.drivername == "postgresql+psycopg"
    assert parsed.database == "vinculo_demo"
    assert parsed.query["sslmode"] == "require"


def test_database_url_for_runtime_does_not_echo_malformed_secret():
    malformed_value = "not-a-database-url-secret-marker"

    with pytest.raises(ValueError) as error:
        database_url_for_runtime(malformed_value)

    assert str(error.value) == "DATABASE_URL must be a valid SQLAlchemy connection URL"
    assert malformed_value not in str(error.value)
    assert error.value.__suppress_context__ is True
