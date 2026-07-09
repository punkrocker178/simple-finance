from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import backtest, health, market
from app.core.config import get_settings
from app.core.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
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
