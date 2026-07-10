import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import backtest, health, market
from app.core.config import get_settings
from app.core.db import init_db


def _configure_logging() -> None:
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    _configure_logging()
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.include_router(health.router)
    application.include_router(market.router, prefix="/api/v1/market", tags=["market"])
    application.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
    return application


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
