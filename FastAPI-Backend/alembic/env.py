import asyncio
import os
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from sqlalchemy.engine import make_url
from app.models.session_models import Base
from app.models import resume_storage_models
from app.models.resume_storage_schema import TABLE_NAMES

url = os.environ.get("RESUME_DATABASE_URL")
if not url or make_url(url).drivername != "mysql+aiomysql":
    raise RuntimeError("explicit RESUME_DATABASE_URL=mysql+aiomysql://... required")


def include_object(obj, name, type_, reflected, compare_to):
    table = obj if type_ == "table" else getattr(obj, "table", None)
    return table is None or table.name in TABLE_NAMES


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
