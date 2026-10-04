from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Hermi API")

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
