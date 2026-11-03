"""FastAPI entry point for the local demonstration backend."""

from fastapi import FastAPI

from app.catalog.router import router as catalog_router
from app.errors import register_error_handlers
from app.planning.router import router as planning_router


def create_app() -> FastAPI:
    application = FastAPI(title="智能旅游行程规划与管理系统")
    register_error_handlers(application)

    @application.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(catalog_router)
    application.include_router(planning_router)
    # Member A supplies this router; until then the rest of B's backend stays runnable.
    try:
        from app.itineraries.router import router as itineraries_router
    except ModuleNotFoundError as exc:
        if exc.name not in {"app.itineraries", "app.itineraries.router"}:
            raise
    else:
        application.include_router(itineraries_router)
    return application


app = create_app()
