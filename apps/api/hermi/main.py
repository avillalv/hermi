from fastapi import FastAPI

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

    return app


def __getattr__(name: str) -> FastAPI:
    # Lazy `hermi.main:app` so importing the module does not load settings.
    if name == "app":
        return create_app()
    raise AttributeError(name)
