"""Project structure paths and import names."""

from dataclasses import dataclass

_LAYERED_ROUTES = {
    "health": "api.routes.health",
    "items": "api.routes.items",
    "auth": "api.routes.auth",
    "auth_email": "api.routes.auth_email",
    "oauth": "api.routes.oauth",
    "documents": "api.routes.documents",
    "pages": "api.routes.pages",
    "ws": "api.routes.ws",
    "limited": "api.routes.limited",
    "uploads": "api.routes.uploads",
}
_FEATURE_ROUTES = {
    "health": "features.health.router",
    "items": "features.items.router",
    "auth": "features.auth.router",
    "auth_email": "features.auth.email_router",
    "oauth": "features.auth.oauth_router",
    "documents": "features.documents.router",
    "pages": "features.pages.router",
    "ws": "features.websockets.router",
    "limited": "features.rate_limit.router",
    "uploads": "features.uploads.router",
}
_LAYERED_MODELS = {
    "item": "models.item",
    "user": "models.user",
    "document": "models.document",
}
_FEATURE_MODELS = {
    "item": "features.items.models",
    "user": "features.auth.models",
    "document": "features.documents.models",
}
_LAYERED_SCHEMAS = {
    "item": "schemas.item",
    "user": "schemas.user",
    "document": "schemas.document",
}
_FEATURE_SCHEMAS = {
    "item": "features.items.schemas",
    "user": "features.auth.schemas",
    "document": "features.documents.schemas",
}
_LAYERED_SERVICES = {
    "items": "services.items",
    "auth": "services.auth",
    "auth_email": "services.auth_email",
    "oauth": "services.oauth",
    "documents": "services.documents",
}
_FEATURE_SERVICES = {
    "items": "features.items.service",
    "auth": "features.auth.service",
    "auth_email": "features.auth.email_service",
    "oauth": "features.auth.oauth_service",
    "documents": "features.documents.service",
}
_FEATURE_OUTPUTS = {
    "models/item.py": "features/items/models.py",
    "schemas/item.py": "features/items/schemas.py",
    "services/items.py": "features/items/service.py",
    "api/routes/items.py": "features/items/router.py",
    "models/user.py": "features/auth/models.py",
    "schemas/user.py": "features/auth/schemas.py",
    "services/auth.py": "features/auth/service.py",
    "api/routes/auth.py": "features/auth/router.py",
    "services/auth_email.py": "features/auth/email_service.py",
    "api/routes/auth_email.py": "features/auth/email_router.py",
    "services/oauth.py": "features/auth/oauth_service.py",
    "api/routes/oauth.py": "features/auth/oauth_router.py",
    "models/document.py": "features/documents/models.py",
    "schemas/document.py": "features/documents/schemas.py",
    "services/documents.py": "features/documents/service.py",
    "api/routes/documents.py": "features/documents/router.py",
    "api/routes/health.py": "features/health/router.py",
    "api/routes/pages.py": "features/pages/router.py",
    "api/routes/ws.py": "features/websockets/router.py",
    "api/routes/limited.py": "features/rate_limit/router.py",
    "api/routes/uploads.py": "features/uploads/router.py",
    "api/routes/__init__.py": "api/router.py",
    "models/__init__.py": "models_registry.py",
    "graphql/__init__.py": "features/graphql/__init__.py",
    "graphql/schema.py": "features/graphql/schema.py",
}


@dataclass(frozen=True, slots=True)
class Layout:
    """Resolve structure-specific import names and output paths."""

    structure: str
    package: str

    @property
    def is_feature(self) -> bool:
        return self.structure == "feature"

    @property
    def is_minimal(self) -> bool:
        return self.structure == "minimal"

    @property
    def config_import(self) -> str:
        """Return the dotted import for application settings."""
        return "config" if self.is_minimal else "core.config"

    @property
    def observability_import(self) -> str:
        """Return the dotted import for Sentry initialization."""
        return "observability" if self.is_minimal else "core.observability"

    @property
    def tracing_import(self) -> str:
        """Return the dotted import for OpenTelemetry setup."""
        return "tracing" if self.is_minimal else "core.tracing"

    def route(self, name: str) -> str:
        """Return the dotted import for a route module."""
        if self.is_feature:
            return _FEATURE_ROUTES[name]
        return _LAYERED_ROUTES[name]

    def model(self, name: str) -> str:
        """Return the dotted import for a model module."""
        if self.is_feature:
            return _FEATURE_MODELS[name]
        return _LAYERED_MODELS[name]

    def schema(self, name: str) -> str:
        """Return the dotted import for a schema module."""
        if self.is_feature:
            return _FEATURE_SCHEMAS[name]
        return _LAYERED_SCHEMAS[name]

    def service(self, name: str) -> str:
        """Return the dotted import for a service module."""
        if self.is_feature:
            return _FEATURE_SERVICES[name]
        return _LAYERED_SERVICES[name]

    @property
    def router_import(self) -> str:
        """Return the dotted import for the aggregated API router."""
        return "api.router" if self.is_feature else "api.routes"

    @property
    def models_import(self) -> str:
        """Return the dotted import for the models registry."""
        return "models_registry" if self.is_feature else "models"

    @property
    def graphql_import(self) -> str:
        """Return the dotted import for the GraphQL schema."""
        return "features.graphql.schema" if self.is_feature else "graphql.schema"

    def output_path(self, path: str) -> str:
        """Map a layered logical path to the selected structure."""
        if self.is_minimal:
            prefix = f"src/{self.package}/"
            if not path.startswith(prefix):
                return path
            relative = path.removeprefix(prefix)
            minimal = {
                "core/config.py": "config.py",
                "core/errors.py": "errors.py",
                "core/logging.py": "logging.py",
                "core/middleware.py": "middleware.py",
                "core/observability.py": "observability.py",
                "core/tracing.py": "tracing.py",
            }
            mapped = minimal.get(relative)
            return f"{prefix}{mapped}" if mapped else path
        if not self.is_feature:
            return path
        prefix = f"src/{self.package}/"
        if not path.startswith(prefix):
            return path
        relative = path.removeprefix(prefix)
        mapped = _FEATURE_OUTPUTS.get(relative)
        return f"{prefix}{mapped}" if mapped else path
