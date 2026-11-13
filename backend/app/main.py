from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.adapters.registry import AdapterRegistry
from app.api.errors import install_error_handlers
from app.api.router import router
from app.core.config import Settings
from app.database.initialize import expected_revision, initialize_database
from app.database.session import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(configuration.database_path)
        adapters = AdapterRegistry()
        try:
            initialize_database(configuration, database)
            app.state.database = database
            app.state.expected_revision = expected_revision()
            adapters.connect()
            app.state.adapters = adapters
            yield
        finally:
            adapters.disconnect()
            database.close()

    app = FastAPI(title="SmartHome", version=__version__, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    install_error_handlers(app)
    app.include_router(router)
    return app
