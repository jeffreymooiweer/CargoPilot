import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes.assistant import admin_router as assistant_admin_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.auth import router as auth_router
from app.api.routes.branding import admin_router as branding_admin_router
from app.api.routes.branding import public_router as branding_public_router
from app.api.routes.cards import router as cards_router
from app.api.routes.catalog import reference_router
from app.api.routes.catalog_search import router as catalog_search_router
from app.api.routes.units import router as units_router
from app.api.routes.equipment import equipment_router
from app.api.routes.import_files import router as import_files_router
from app.api.routes.dangerous_goods import router as dangerous_goods_router
from app.api.routes.documents import mail_router as documents_mail_router
from app.api.routes.documents import router as documents_router
from app.api.routes.geo import router as geo_router
from app.api.routes.history import router as history_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.meta import router as meta_router
from app.api.routes.settings import public_router as settings_public_router
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

#: The work: what both applications serve. Parsing, judging, rendering, the
#: reference data, and the public facts the interface draws itself from.
WORK_ROUTERS = (
    assistant_router,
    jobs_router,
    dangerous_goods_router,
    documents_router,
    geo_router,
    reference_router,
    import_files_router,
    catalog_search_router,
    units_router,
    settings_public_router,
    # What is on the door: the name and the pictures, read by the sign-in
    # page before anybody has signed in and by the open application.
    branding_public_router,
)

#: The accounts: what only the organisation application serves. Signing in
#: and everything that presumes somebody did — their settings, the users
#: page, the equipment library, mail, the administrator's maintenance. In
#: the open application these are not hidden behind a refusal; they are not
#: mounted, so they answer 404 like any address that does not exist. The
#: test suite asserts their absence route by route.
ACCOUNT_ROUTERS = (
    auth_router,
    users_router,
    settings_router,
    equipment_router,
    documents_mail_router,
    un_cards_admin_router,
    assistant_admin_router,
    branding_admin_router,
    meta_router,
)

#: The history: what only an organisation application that keeps its
#: shipments serves. Not mounted without CARGOPILOT_HISTORY=true, so on every
#: other installation "nothing is kept" is a matter of which addresses exist.
HISTORY_ROUTERS = (history_router,)


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
            # Which application this is. A visitor cannot see an environment
            # variable; this line, the footer that repeats it and the public
            # source are what make "nothing is kept about you" checkable
            # rather than merely true.
            "mode": settings.mode,
            # And whether it keeps its shipments — the other half of what a
            # visitor may want to know before typing a customer's name.
            "history": settings.history_enabled,
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
        return {"has_admin": getattr(app.state, "has_admin", False),
                "mode": settings.mode}

    for router in WORK_ROUTERS:
        app.include_router(router, prefix="/api")
    if not settings.is_open:
        for router in ACCOUNT_ROUTERS:
            app.include_router(router, prefix="/api")
    if settings.history_enabled:
        for router in HISTORY_ROUTERS:
            app.include_router(router, prefix="/api")
    # Public by design in both applications — see app/api/routes/cards.py.
    # It is off unless an administrator, or the environment, turns it on.
    app.include_router(cards_router, prefix="/api")

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
