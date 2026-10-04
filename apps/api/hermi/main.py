from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hermi import api_v1, db, errors, health
from hermi.config import LOCAL_ENVIRONMENTS, Settings, load_settings
from hermi.logging_setup import setup_logging
from hermi.modules.auth.router import dev_router
from hermi.modules.notifications import waitlist
from hermi.security.jwt import TokenVerifier


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # The app engine refuses an unsafe login here, so a misconfigured API never serves a request.
    s: Settings = app.state.settings
    app.state.engine = db.open_app_engine(s) if s.database_url else None
    try:
        yield
    finally:
        if app.state.engine is not None:
            app.state.engine.dispose()
        db.dispose_system_engines()


def create_app(settings: Settings | None = None) -> FastAPI:
    # Loading here makes every start path (cli, plain uvicorn) fail fast on bad config.
    # An ASGI start does not know its bind host; assume non-loopback so claude_cli is refused.
    settings = settings or load_settings(bind_host="0.0.0.0")
    setup_logging(settings.log_level)
    app = FastAPI(title="Hermi API", lifespan=_lifespan)
    app.state.settings = settings
    app.state.verifier = TokenVerifier(settings)
    errors.register(app)

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready() -> JSONResponse:
        url = settings.database_url.get_secret_value() if settings.database_url else None
        ok, body = health.check_ready(url, settings.ai_provider)
        return JSONResponse(body, status_code=200 if ok else 503)

    # The landing page on Cloudflare Pages posts here cross-origin.
    # List its origin in CORS_ALLOWED_ORIGINS.
    origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(errors.RequestIdMiddleware)  # last added = outermost, wraps CORS
    waitlist.register(app)
    app.include_router(api_v1.router)
    if settings.auth_mode == "dev" and settings.environment in LOCAL_ENVIRONMENTS:
        app.include_router(dev_router, prefix="/v1")  # absent from every other OpenAPI
    return app


def __getattr__(name: str) -> FastAPI:
    # Lazy `hermi.main:app` so importing the module does not load settings.
    if name == "app":
        return create_app()
    raise AttributeError(name)
