"""API HTTP da aplicação."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI

from app.config import Settings, get_settings
from app.health import build_health
from app.logging_config import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.ensure_directories()
    configure_logging(settings.log_level, settings.logs_dir)
    logging.getLogger(__name__).info("Aplicação iniciada")
    yield
    logging.getLogger(__name__).info("Aplicação encerrada")


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)


async def provide_settings() -> Settings:
    return get_settings()


@app.get("/health", tags=["operação"])
async def health(
    current_settings: Settings = Depends(provide_settings),
) -> dict[str, object]:
    return build_health(current_settings)
