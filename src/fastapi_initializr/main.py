"""Application entry point."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi_initializr import __version__
from fastapi_initializr.api.routes import api_router
from fastapi_initializr.core.config import get_settings
from fastapi_initializr.generation.catalog import metadata
from fastapi_initializr.generation.limits import ProjectLimitError
from fastapi_initializr.generation.plugins import install_plugins

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    settings = get_settings()
    if settings.plugin_dir:
        install_plugins(Path(settings.plugin_dir))
    app = FastAPI(title="FastAPI Initializr", version=__version__)
    app.mount(
        "/static",
        StaticFiles(directory=str(BASE_DIR / "static")),
        name="static",
    )
    app.include_router(api_router)

    @app.exception_handler(ProjectLimitError)
    async def project_limit_handler(
        _request: Request,
        exc: ProjectLimitError,
    ) -> JSONResponse:
        return JSONResponse(status_code=413, content={"detail": str(exc)})

    @app.get("/", response_class=Response, include_in_schema=False)
    def index(request: Request) -> Response:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"metadata": metadata()},
        )

    return app


app = create_app()


def main() -> None:
    """Run the development server."""
    import uvicorn

    uvicorn.run("fastapi_initializr.main:app", host="127.0.0.1", port=8000, reload=True)
