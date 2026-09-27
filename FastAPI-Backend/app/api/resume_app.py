"""Lightweight resume-only application; no interview/AI client initialization."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.experience_app import register_experience_routes
from app.api.resume_generation_routes import router as generation
from app.api.resume_document_routes import router as documents
from app.api.resume_template_routes import router as templates
from app.api.resume_routes import router as legacy_resumes
from app.api.resume_library_routes import router as resume_library
from app.api.local_interview_routes import router as local_interview
from app.api.local_resume_optimize_routes import router as local_resume_optimize


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
    # Keep the legacy resume upload/list/delete contract available to the
    # existing frontend while the new resume document workflow is enabled.
    app.include_router(legacy_resumes)
    app.include_router(resume_library)
    # The local app intentionally uses deterministic in-memory compatibility
    # handlers for interview/optimization screens instead of initializing the
    # heavyweight AI service or Docker-only runtime.
    app.include_router(local_interview)
    app.include_router(local_resume_optimize)

    return app


app = create_resume_app()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "resume-local"}
