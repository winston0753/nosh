from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class NoshError(Exception):
    def __init__(
        self, code: str, message: str, status_code: int = 400, field: str | None = None
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
        super().__init__(message)


class NotFoundError(NoshError):
    def __init__(self, resource: str, id: str) -> None:
        super().__init__(
            code="not_found",
            message=f"{resource} {id!r} not found",
            status_code=404,
        )


class ForbiddenError(NoshError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(code="forbidden", message=message, status_code=403)


class ConflictError(NoshError):
    def __init__(self, message: str) -> None:
        super().__init__(code="conflict", message=message, status_code=409)


class InvalidStateError(NoshError):
    def __init__(self, message: str) -> None:
        super().__init__(code="invalid_state_transition", message=message, status_code=422)


class ValidationFailedError(NoshError):
    """A request that is well-formed but violates a cross-field or stored-state rule.

    Uses the same ``validation_error`` code as schema validation so clients
    handle both identically.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(code="validation_error", message=message, status_code=422, field=field)


async def nosh_error_handler(request: Request, exc: NoshError) -> JSONResponse:
    content: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.field is not None:
        content["field"] = exc.field
    return JSONResponse(status_code=exc.status_code, content=content)


def _field_from_loc(loc: tuple[Any, ...] | list[Any]) -> str | None:
    """Turn a Pydantic error location such as ("body", "active_days", 2) into a field name."""
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts) or None


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Schema-validation failures share the Nosh error shape.

    ``detail`` keeps FastAPI's original per-field list so existing consumers
    still work; ``code``, ``message``, and ``field`` add the stable contract.
    """
    errors = exc.errors()
    first = errors[0] if errors else {}
    message = str(first.get("msg", "Request validation failed"))
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": message,
            "field": _field_from_loc(first.get("loc", ())),
            "detail": jsonable_encoder(errors),
        },
    )
