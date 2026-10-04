from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hermi import health
from hermi.config import Settings, load_settings
from hermi.logging_setup import setup_logging
from hermi.modules.notifications import waitlist


def create_app(settings: Settings | None = None) -> FastAPI:
    # Loading here makes every start path (cli, plain uvicorn) fail fast on bad config.
    # An ASGI start does not know its bind host; assume non-loopback so claude_cli is refused.
    settings = settings or load_settings(bind_host="0.0.0.0")
    setup_logging(settings.log_level)
    app = FastAPI(title="Hermi API")
    app.state.settings = settings

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
    waitlist.register(app)
    return app


def __getattr__(name: str) -> FastAPI:
    # Lazy `hermi.main:app` so importing the module does not load settings.
    if name == "app":
        return create_app()
    raise AttributeError(name)
