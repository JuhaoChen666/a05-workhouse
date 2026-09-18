"""Lightweight resume-only application; no interview/AI client initialization."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.experience_app import register_experience_routes
from app.api.resume_generation_routes import router as generation
from app.api.resume_document_routes import router as documents
from app.api.resume_template_routes import router as templates


def create_resume_app():
    app = FastAPI(title="Personal resume workflow")
    origins = [origin.strip() for origin in os.environ.get("RESUME_FRONTEND_ORIGINS", "").split(",") if origin.strip()]
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
    register_experience_routes(app)
    app.include_router(generation)
    app.include_router(documents)
    app.include_router(templates)
    return app


app = create_resume_app()
