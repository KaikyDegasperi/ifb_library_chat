"""API HTTP da aplicação."""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings, get_settings
from app.dependencies import provide_settings
from app.logging_config import configure_logging
from app.observability import bind_request_id, new_request_id, reset_request_id
from app.routes.chat import router as chat_router
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router
from app.routes.search import router as search_router


class RequestTooLargeError(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await self._respond(scope, receive, send, 400, "Content-Length inválido")
                return
            if declared_size < 0:
                await self._respond(scope, receive, send, 400, "Content-Length inválido")
                return
            if declared_size > self.max_bytes:
                await self._respond(
                    scope,
                    receive,
                    send,
                    413,
                    "Requisição excede o limite configurado",
                )
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    scope.setdefault("state", {})["request_too_large"] = True
                    raise RequestTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLargeError:
            await self._respond(
                scope,
                receive,
                send,
                413,
                "Requisição excede o limite configurado",
            )

    @staticmethod
    async def _respond(
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        detail: str,
    ) -> None:
        response = JSONResponse(status_code=status_code, content={"detail": detail})
        await response(scope, receive, send)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings: Settings = application.state.settings
    settings.ensure_directories()
    configure_logging(settings.log_level, settings.logs_dir)
    logging.getLogger(__name__).info("Aplicação iniciada")
    yield
    logging.getLogger(__name__).info("Aplicação encerrada")


async def observe_request(request: Request, call_next):
    request_id = new_request_id()
    context_token = bind_request_id(request_id)
    started = time.perf_counter()
    status_code = 500
    error_type = "none"
    try:
        response = await call_next(request)
        status_code = response.status_code
        if status_code >= 400:
            error_type = f"http_{status_code}"
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        error_type = type(exc).__name__
        raise
    finally:
        route = request.scope.get("route")
        endpoint = getattr(route, "path", "<unmatched>")
        logging.getLogger(__name__).info(
            "request_completed",
            extra={
                "request_id": request_id,
                "endpoint": endpoint,
                "status": status_code,
                "duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
                "error_type": error_type,
            },
        )
        reset_request_id(context_token)


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    docs_enabled = active_settings.docs_enabled
    application = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        description=(
            "API para ingestão, indexação, busca e consulta RAG dos TCCs da "
            "Licenciatura em Matemática do IFB Campus Estrutural."
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    if active_settings.cors_allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=active_settings.cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            expose_headers=["X-Request-ID"],
        )
    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=active_settings.max_request_size_bytes,
    )
    application.middleware("http")(observe_request)

    @application.exception_handler(RequestValidationError)
    async def safe_validation_error(
        _: Request,
        __: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": "Requisição inválida"},
        )

    @application.exception_handler(StarletteHTTPException)
    async def safe_http_error(
        request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        if getattr(request.state, "request_too_large", False):
            return JSONResponse(
                status_code=413,
                content={"detail": "Requisição excede o limite configurado"},
            )
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
            headers=error.headers,
        )

    application.include_router(health_router)
    application.include_router(documents_router)
    application.include_router(search_router)
    application.include_router(chat_router)
    return application


app = create_app()

__all__ = ["app", "create_app", "provide_settings"]
