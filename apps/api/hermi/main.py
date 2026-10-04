from fastapi import FastAPI
from fastapi.responses import JSONResponse

from hermi import health
from hermi.config import Settings, load_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    # Loading here makes every start path (cli, plain uvicorn) fail fast on bad config.
    # An ASGI start does not know its bind host; assume non-loopback so claude_cli is refused.
    settings = settings or load_settings(bind_host="0.0.0.0")
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

    return app


def __getattr__(name: str) -> FastAPI:
    # Lazy `hermi.main:app` so importing the module does not load settings.
    if name == "app":
        return create_app()
    raise AttributeError(name)
