import asyncio
import os
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from sqlalchemy.engine import make_url
from app.models.session_models import Base
from app.models import resume_storage_models
from app.models.resume_storage_schema import TABLE_NAMES
from app.models import experience_import_models
from app.models.experience_import_schema import TABLE_NAMES as IMPORT_TABLE_NAMES

url = os.environ.get("RESUME_DATABASE_URL") or os.environ.get("DATABASE_URL")
if os.environ.get("RESUME_DATABASE_URL") and os.environ.get("DATABASE_URL") and make_url(os.environ["RESUME_DATABASE_URL"]) != make_url(os.environ["DATABASE_URL"]):
    raise RuntimeError("DATABASE_URL and RESUME_DATABASE_URL must refer to the same explicit database")
if not url or make_url(url).drivername != "mysql+aiomysql":
    raise RuntimeError("explicit RESUME_DATABASE_URL=mysql+aiomysql://... required")


def include_object(obj, name, type_, reflected, compare_to):
    table = obj if type_ == "table" else getattr(obj, "table", None)
    return table is None or table.name in TABLE_NAMES + IMPORT_TABLE_NAMES


def configure(connection=None):
    context.configure(connection=connection, url=url if connection is None else None,
        target_metadata=Base.metadata, version_table="resume_phase1_alembic_version",
        include_object=include_object, literal_binds=connection is None,
        dialect_opts={"paramstyle": "named"}, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = create_async_engine(url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(configure)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    configure()
else:
    asyncio.run(online())
