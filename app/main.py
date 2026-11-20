"""Stockscope API entrypoint."""

import math
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import router as v1_router

app = FastAPI(
    title="Stockscope API",
    version=__version__,
    description="Stock screening and analysis for publicly listed companies.",
)
app.include_router(v1_router)


def _json_safe(value: Any) -> Any:
    """Replace non-finite floats so validation errors remain JSON serializable."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    detail = []
    for error in exc.errors():
        detail.append(
            {
                key: _json_safe(value)
                for key, value in error.items()
                if key in {"loc", "msg", "type", "input"}
            }
        )
    return JSONResponse(status_code=422, content={"detail": detail})
