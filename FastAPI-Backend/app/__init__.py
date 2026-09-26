"""Application package bootstrap and shared runtime configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_runtime_env() -> None:
    """Load one shared environment file before any service module reads it."""
    configured_path = os.environ.get("RESUME_ENV_FILE")
    if configured_path:
        candidates = [Path(configured_path)]
    else:
        here = Path(__file__).resolve()
        candidates = [
            here.parents[2] / ".env",
            *[parent / "FastAPI-Backend" / ".env" for parent in here.parents[2:]],
        ]
    for env_path in candidates:
        if env_path.is_file():
            load_dotenv(env_path, override=False)
            os.environ.setdefault("RESUME_ENV_FILE", str(env_path))
            break


_load_runtime_env()

__version__ = "0.1.0"
