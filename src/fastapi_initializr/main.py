"""Application entry point."""

from fastapi import FastAPI

from fastapi_initializr import __version__


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(title="FastAPI Initializr", version=__version__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def main() -> None:
    """Run the development server."""
    import uvicorn

    uvicorn.run("fastapi_initializr.main:app", host="127.0.0.1", port=8000, reload=True)
