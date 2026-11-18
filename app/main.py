"""Stockscope API entrypoint."""

from fastapi import FastAPI

from app import __version__
from app.api.v1.router import router as v1_router

app = FastAPI(
    title="Stockscope API",
    version=__version__,
    description="Stock screening and analysis for publicly listed companies.",
)
app.include_router(v1_router)
