"""Only freshly created random MySQL schemas may be mutated or dropped."""
import os
from pathlib import Path
from uuid import uuid4
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def private_store(tmp_path):
    from app.infrastructure.private_resume_assets import PrivateAssets
    return PrivateAssets(tmp_path / "private")


def migrate(url, direction="upgrade", revision=None):
    config = Config(str(BACKEND / "alembic.ini"))
    previous = os.environ.get("RESUME_DATABASE_URL")
    os.environ["RESUME_DATABASE_URL"] = url.render_as_string(hide_password=False)
    try:
        if direction == "upgrade":
            command.upgrade(config, revision or "head")
        else:
            command.downgrade(config, revision or "base")
    finally:
        if previous is None:
            os.environ.pop("RESUME_DATABASE_URL", None)
        else:
            os.environ["RESUME_DATABASE_URL"] = previous


@pytest.fixture
def mysql_schema():
    raw = os.environ.get("RESUME_TEST_MYSQL_URL")
    if not raw:
        pytest.skip("explicit RESUME_TEST_MYSQL_URL required; no SQLite substitution")
    url = make_url(raw)
    if url.drivername != "mysql+aiomysql":
        raise ValueError("expected mysql+aiomysql")
    name = "resume_p1_restart_test_" + uuid4().hex[:16]
    admin = create_engine(url.set(drivername="mysql+pymysql", database=None), echo=False)
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            created = True
        test_url = url.set(database=name)
        legacy = create_engine(test_url.set(drivername="mysql+pymysql"), echo=False)
        try:
            with legacy.begin() as connection:
                connection.execute(text("CREATE TABLE resumes (id BIGINT UNSIGNED PRIMARY KEY, user_id INT NOT NULL, filename VARCHAR(255) NOT NULL, local_path VARCHAR(511) NOT NULL, content_text TEXT, uploaded_at DATETIME) ENGINE=InnoDB"))
                connection.execute(text("CREATE TABLE resume_optimizations (session_id VARCHAR(36) COLLATE utf8mb4_unicode_ci PRIMARY KEY, user_id INT NOT NULL, original_text TEXT, optimized_text TEXT, progress INT, status VARCHAR(20), created_at DATETIME, updated_at DATETIME) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"))
                connection.execute(text("INSERT INTO resumes VALUES (1,71,'sentinel.pdf','unchanged','original',NOW())"))
                connection.execute(text("INSERT INTO resume_optimizations VALUES ('old',71,'original','# Legacy',100,'completed',NOW(),NOW())"))
            migrate(test_url)
            yield test_url
        finally:
            legacy.dispose()
    finally:
        if created:
            # This exact name is locally generated, never comes from a supplied URL.
            with admin.connect() as connection:
                connection.execute(text(f"DROP DATABASE `{name}`"))
        admin.dispose()


@pytest_asyncio.fixture
async def sessions(mysql_schema):
    engine = create_async_engine(mysql_schema, echo=False, pool_size=5)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
