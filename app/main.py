"""Stockscope API entrypoint."""

import logging
import math
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import router as v1_router
from app.config import settings
from app.middleware import RequestLoggingMiddleware

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("stockscope").info("starting app_env=%s", settings.app_env)

app = FastAPI(
    title="Stockscope API",
    version=__version__,
    description="Stock screening and analysis for publicly listed companies.",
)
app.include_router(v1_router)
app.add_middleware(RequestLoggingMiddleware)


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


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("stockscope").exception(
        "unhandled error method=%s path=%s", request.method, request.url.path
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
