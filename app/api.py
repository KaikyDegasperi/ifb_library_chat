"""API HTTP da aplicação."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import get_settings
from app.dependencies import provide_settings
from app.logging_config import configure_logging
from app.routes.chat import router as chat_router
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router
from app.routes.search import router as search_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.ensure_directories()
    configure_logging(settings.log_level, settings.logs_dir)
    logging.getLogger(__name__).info("Aplicação iniciada")
    yield
    logging.getLogger(__name__).info("Aplicação encerrada")


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "API para ingestão, indexação, busca e consulta RAG dos TCCs da "
        "Licenciatura em Matemática do IFB Campus Estrutural."
    ),
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(chat_router)

__all__ = ["app", "provide_settings"]
