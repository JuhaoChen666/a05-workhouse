"""Exercise fixture connection setup without accessing any MySQL server."""
import pytest
from conftest import mysql_schema as mysql_schema_fixture


@pytest.mark.parametrize("database", ["unused", "existing_business_database"])
def test_admin_connection_does_not_select_supplied_database(monkeypatch, database):
    monkeypatch.setenv(
        "RESUME_TEST_MYSQL_URL",
        f"mysql+aiomysql://fixture:fixture@127.0.0.1:3306/{database}?charset=utf8mb4",
    )
    connections = []

    class StopBeforeNetwork(Exception):
        pass

    def connect(*args, **kwargs):
        connections.append(kwargs)
        assert kwargs.get("database", kwargs.get("db")) is None
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["charset"] == "utf8mb4"
        raise StopBeforeNetwork

    monkeypatch.setattr("pymysql.connect", connect)
    fixture = mysql_schema_fixture.__wrapped__()
    try:
        with pytest.raises(StopBeforeNetwork):
            next(fixture)
    finally:
        fixture.close()
    assert len(connections) == 1
