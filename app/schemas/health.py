"""Health check response."""

from pydantic import BaseModel


class HealthRead(BaseModel):
    status: str
    version: str
