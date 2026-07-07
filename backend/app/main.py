import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes.auth import router as auth_router
from app.api.routes.catalog import reference_router
from app.api.routes.equipment import equipment_router
from app.api.routes.dangerous_goods import router as dangerous_goods_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.core.startup import init_app

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app = FastAPI(title=settings.app_name)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.on_event("startup")
    def on_startup():
        has_admin = init_app()
        app.state.has_admin = has_admin

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    @app.get("/api/setup-status")
    def setup_status():
        return {"has_admin": getattr(app.state, "has_admin", False)}

    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(dangerous_goods_router, prefix="/api")
    app.include_router(reference_router, prefix="/api")
    app.include_router(equipment_router, prefix="/api")

    static_dir = settings.static_dir
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def spa(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            index = static_dir / "index.html"
            if index.exists():
                return FileResponse(index)
            return JSONResponse({"detail": "Frontend not built"}, status_code=404)

    return app


app = create_app()
