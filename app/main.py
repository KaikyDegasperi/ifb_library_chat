"""Alias de execução da API para ``uvicorn app.main:app``."""

from app.api import app

__all__ = ["app"]
