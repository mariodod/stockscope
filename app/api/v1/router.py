"""Aggregate version 1 endpoints."""

from fastapi import APIRouter

from app.api.v1 import companies, health, metrics, screen

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(metrics.router)
router.include_router(companies.router)
router.include_router(screen.router)
