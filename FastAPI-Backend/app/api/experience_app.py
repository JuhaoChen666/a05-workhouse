"""Reusable P2 registration and a lightweight executable app for isolated API serving/QA."""
from fastapi import FastAPI
from app.api.experience_routes import router as experiences
from app.api.experience_import_routes import router as imports
from app.api.experience_body_limit import ExperienceBodyLimitMiddleware


def register_experience_routes(app):
    app.add_middleware(ExperienceBodyLimitMiddleware)
    app.include_router(experiences)
    app.include_router(imports)


def create_experience_app():
    app = FastAPI(title="Personal experience library", version="2.0.0")
    register_experience_routes(app)
    return app


app = create_experience_app()
