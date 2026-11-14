"""RFC 7807 Problem Details error handler for FastAPI."""

import json
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from episwarm.service.models import ProblemDetail

PROBLEM_JSON_MIME = "application/problem+json"


def create_problem_response(
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    error_type: str = "about:blank",
    invalid_params: Any = None,
) -> JSONResponse:
    """Build an RFC 7807 Problem Details JSONResponse."""
    payload: Dict[str, Any] = {
        "type": error_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    if invalid_params is not None:
        payload["invalid_params"] = invalid_params

    return JSONResponse(
        content=payload,
        status_code=status_code,
        media_type=PROBLEM_JSON_MIME,
    )


def register_problem_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI application."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        title_map = {
            status.HTTP_400_BAD_REQUEST: "Bad Request",
            status.HTTP_401_UNAUTHORIZED: "Unauthorized",
            status.HTTP_403_FORBIDDEN: "Forbidden",
            status.HTTP_404_NOT_FOUND: "Not Found",
            status.HTTP_409_CONFLICT: "Conflict",
            status.HTTP_422_UNPROCESSABLE_ENTITY: "Unprocessable Entity",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal Server Error",
        }
        title = title_map.get(exc.status_code, "HTTP Error")
        err_type = f"https://episwarm.org/errors/{title.lower().replace(' ', '-')}"
        detail_msg = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)

        return create_problem_response(
            status_code=exc.status_code,
            title=title,
            detail=detail_msg,
            instance=request.url.path,
            error_type=err_type,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        invalid_params = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            invalid_params.append({
                "name": loc,
                "reason": err.get("msg", "Validation error"),
                "type": err.get("type", "value_error"),
            })

        return create_problem_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Unprocessable Entity",
            detail="The request entity contained invalid parameters or failed schema validation.",
            instance=request.url.path,
            error_type="https://episwarm.org/errors/validation-error",
            invalid_params=invalid_params,
        )
