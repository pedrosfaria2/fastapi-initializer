"""Application entry point."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi_initializr import __version__
from fastapi_initializr.api.routes import api_router

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(title="FastAPI Initializr", version=__version__)
    app.mount(
        "/static",
        StaticFiles(directory=str(BASE_DIR / "static")),
        name="static",
    )
    app.include_router(api_router)

    @app.get("/", response_class=Response, include_in_schema=False)
    def index(request: Request) -> Response:
        return templates.TemplateResponse(request=request, name="index.html")

    return app


app = create_app()


def main() -> None:
    """Run the development server."""
    import uvicorn

    uvicorn.run("fastapi_initializr.main:app", host="127.0.0.1", port=8000, reload=True)
