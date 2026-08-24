import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes.assistant import router as assistant_router
from app.api.routes.auth import router as auth_router
from app.api.routes.catalog import reference_router
from app.api.routes.catalog_search import router as catalog_search_router
from app.api.routes.units import router as units_router
from app.api.routes.equipment import equipment_router
from app.api.routes.import_files import router as import_files_router
from app.api.routes.dangerous_goods import router as dangerous_goods_router
from app.api.routes.documents import router as documents_router
from app.api.routes.geo import router as geo_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.meta import router as meta_router
from app.api.routes.settings import router as settings_router
from app.api.routes.un_cards_admin import router as un_cards_admin_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.core.security_checks import apply_security_configuration
from app.core.startup import init_app
from app.services.regulatory_manifest import build_manifest, summary
from app.version import get_version

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    # Before anything else: a published signing key is an app that can be used
    # without logging in. One is made and stored for it here — refusing to start
    # left the user with nothing but a dead container.
    apply_security_configuration(settings)
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
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": get_version(),
            # Which editions this installation uses, compactly. Whoever reports a
            # bug passes on straight away what their app computes with.
            "regulatory": summary(),
        }

    @app.get("/api/regulatory")
    def regulatory():
        """Per rule set: edition, source, validity, errata and checksum."""
        return build_manifest()

    @app.get("/api/setup-status")
    def setup_status():
        return {"has_admin": getattr(app.state, "has_admin", False)}

    app.include_router(assistant_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(dangerous_goods_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(geo_router, prefix="/api")
    app.include_router(reference_router, prefix="/api")
    app.include_router(equipment_router, prefix="/api")
    app.include_router(import_files_router, prefix="/api")
    app.include_router(catalog_search_router, prefix="/api")
    app.include_router(units_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(un_cards_admin_router, prefix="/api")
    app.include_router(meta_router, prefix="/api")

    static_dir = settings.static_dir
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        static_root = static_dir.resolve()

        @app.get("/{full_path:path}")
        async def spa(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            if full_path:
                candidate = (static_dir / full_path).resolve()
                if candidate.is_file() and candidate.is_relative_to(static_root):
                    return FileResponse(candidate)
            index = static_dir / "index.html"
            if index.exists():
                return FileResponse(index)
            return JSONResponse({"detail": "Frontend not built"}, status_code=404)

    return app


app = create_app()
