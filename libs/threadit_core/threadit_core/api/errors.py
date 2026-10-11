from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from threadit_core.domain.errors import DomainError
from threadit_core.logging import get_logger, set_correlation_id

_PROBLEM = "application/problem+json"
_log = get_logger("api")


def _problem(status: int, type_: str, title: str, detail: str, retryable: bool) -> JSONResponse:
    from threadit_core.logging import get_correlation_id

    return JSONResponse(
        status_code=status,
        media_type=_PROBLEM,
        content={
            "type": type_,
            "title": title,
            "status": status,
            "detail": detail,
            "correlationId": get_correlation_id(),
            "retryable": retryable,
        },
    )


def install_error_handling(app: FastAPI) -> None:
    @app.middleware("http")
    async def correlation(request: Request, call_next):
        set_correlation_id(request.headers.get("x-correlation-id"))
        response = await call_next(request)
        from threadit_core.logging import get_correlation_id

        response.headers["x-correlation-id"] = get_correlation_id()
        return response

    @app.exception_handler(DomainError)
    async def _domain(_r: Request, exc: DomainError) -> JSONResponse:
        if exc.status >= 500:
            _log.error("domain_error", error_type=exc.error_type, status=exc.status)
        return _problem(exc.status, exc.error_type, exc.title, exc.detail, exc.retryable)

    @app.exception_handler(RequestValidationError)
    async def _validation(_r: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            400,
            "https://threadit/errors/validation",
            "Invalid request",
            "request failed validation",
            False,
        )
