"""Lazy infrastructure and verified Spring-compatible authentication for P2."""
import os
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.models.resume_storage_contracts import owner_id

bearer = HTTPBearer(auto_error=False)


def trusted_owner(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, {"code": "AUTH_REQUIRED", "message": "Bearer token required"},
                            headers={"WWW-Authenticate": "Bearer"})
    secret = os.environ.get("RESUME_JWT_SECRET", "")
    algorithm = os.environ.get("RESUME_JWT_ALGORITHM", "HS256")
    minimum = {"HS256": 32, "HS384": 48, "HS512": 64}
    if algorithm not in minimum or len(secret.encode("utf8")) < minimum.get(algorithm, 32):
        raise HTTPException(503, {"code": "AUTH_NOT_CONFIGURED", "message": "JWT verification not configured"})
    try:
        claims = jwt.decode(credentials.credentials, secret.encode("utf8"), algorithms=[algorithm],
                            options={"require": ["exp", "iat", "id", "username", "roleId"]})
        owner = owner_id(claims["id"])
        if not isinstance(claims["username"], str) or not claims["username"].strip():
            raise ValueError("invalid username")
        if type(claims["roleId"]) is not int or claims["roleId"] <= 0:
            raise ValueError("invalid role")
        if type(claims["exp"]) not in (int, float) or type(claims["iat"]) not in (int, float):
            raise ValueError("invalid dates")
        if claims["exp"] <= claims["iat"]:
            raise ValueError("invalid lifetime")
        return owner
    except (jwt.PyJWTError, ValueError, KeyError, TypeError, OverflowError):
        raise HTTPException(401, {"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
                            headers={"WWW-Authenticate": "Bearer"}) from None


async def experience_session():
    # Import only when called; routing/OpenAPI does not instantiate a DB engine.
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import ArgumentError
    try:
        url = make_url(os.environ.get("DATABASE_URL", ""))
        if url.drivername != "mysql+aiomysql" or not url.database:
            raise ValueError("explicit MySQL database required")
    except (ValueError, ArgumentError):
        # Do not fall back to the legacy default business database.
        raise HTTPException(503, {"code":"STORAGE_NOT_CONFIGURED", "message":"Explicit MySQL DATABASE_URL required"}) from None
    from app.infrastructure.resume_runtime import session_factory
    async with session_factory()() as session:
        yield session


def private_store():
    from app.infrastructure.resume_runtime import asset_store
    try:
        return asset_store()
    except ValueError:
        raise HTTPException(503, detail="私有文件根目录未配置") from None


def draft_extractor():
    from app.services.pdf_experience_extractor import PDFExperienceAI
    return PDFExperienceAI()


def legacy_pdf_root():
    from app.infrastructure.private_resume_assets import LEGACY_ROOTS
    return LEGACY_ROOTS[0]
