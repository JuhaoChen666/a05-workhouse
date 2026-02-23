"""Emo2Vec-Agent - FastAPI + LangChain AI Agent."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import agent, chat, system
from app.core.config import settings
from app.core.events import lifespan


def create_application() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(
        chat.router,
        prefix=settings.API_V1_PREFIX,
    )
    app.include_router(
        agent.router,
        prefix=settings.API_V1_PREFIX,
    )
    app.include_router(
        system.router,
        prefix=settings.API_V1_PREFIX,
    )

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "api": settings.API_V1_PREFIX,
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_application()
