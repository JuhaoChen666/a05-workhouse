"""One explicit runtime database for API, workers and maintenance."""
import os
from functools import lru_cache
from pathlib import Path
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


@lru_cache(maxsize=4)
def _factory(raw):
    url = make_url(raw)
    if url.drivername != "mysql+aiomysql" or not url.database:
        raise ValueError("explicit MySQL DATABASE_URL required")
    engine = create_async_engine(url, echo=False, pool_size=5, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


def session_factory():
    raw = os.environ.get("DATABASE_URL", "")
    if not raw:
        raise ValueError("explicit MySQL DATABASE_URL required")
    return _factory(raw)


def asset_store():
    from app.infrastructure.private_resume_assets import PrivateAssets
    raw = os.environ.get("RESUME_PRIVATE_ASSET_ROOT", "")
    if not raw or not Path(raw).is_absolute():
        raise ValueError("explicit absolute RESUME_PRIVATE_ASSET_ROOT required")
    return PrivateAssets(raw)
