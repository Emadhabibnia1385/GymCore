"""REST API v1 — aggregated router."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    classes,
    courses,
    payments,
    persons,
    plans,
    settings,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(persons.router)
api_router.include_router(classes.router)
api_router.include_router(courses.router)
api_router.include_router(payments.router)
api_router.include_router(plans.router)
api_router.include_router(settings.router)
