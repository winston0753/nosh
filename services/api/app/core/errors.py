from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class NoshError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
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


async def nosh_error_handler(request: Request, exc: NoshError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )
