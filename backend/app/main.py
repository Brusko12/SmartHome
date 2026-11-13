import asyncio
import secrets
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.adapters.registry import AdapterRegistry
from app.api.errors import install_error_handlers
from app.api.frontend import install_frontend
from app.api.router import router
from app.api.security import install_security
from app.core.config import Settings
from app.database.base import utc_now
from app.database.initialize import expected_revision, initialize_database
from app.database.lock import DatabaseLock
from app.database.session import Database
from app.services.runtime import RuntimeWorker


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(configuration.database_path)
        adapters = AdapterRegistry()
        lock = DatabaseLock(configuration.database_path)
        stop = asyncio.Event()
        task = None
        try:
            if configuration.background_tasks:
                lock.acquire()
            initialize_database(configuration, database)
            app.state.database = database
            app.state.gate = threading.Lock()
            app.state.auth_epoch = 0
            app.state.expected_revision = expected_revision()
            adapters.connect()
            app.state.adapters = adapters
            app.state.configuration = configuration
            app.state.started_at = utc_now()
            app.state.runtime = RuntimeWorker(database, adapters, gate=app.state.gate)
            app.state.runtime_task = None
            if configuration.background_tasks:
                app.state.runtime.recover(utc_now())
                task = asyncio.create_task(app.state.runtime.run(stop))
                app.state.runtime_task = task
            yield
        finally:
            stop.set()
            if task is not None:
                await task
            adapters.disconnect()
            database.close()
            lock.release()

    app = FastAPI(title="SmartHome", version=__version__, lifespan=lifespan)
    app.state.instance_id = secrets.token_urlsafe(16)
    app.state.shutdown_callback = None
    install_security(app)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    install_error_handlers(app)
    app.include_router(router)
    install_frontend(app, configuration.frontend_dir)
    return app
