"""Application settings + dashboard stats endpoints (admin only)."""

from fastapi import APIRouter

from app.api.deps import AdminPerson, DbDep
from app.schemas.entities import SettingsIn, SettingsOut
from app.services import app_settings as settings_service
from app.services import stats as stats_service

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
def get_app_settings(db: DbDep, _: AdminPerson) -> SettingsOut:
    return SettingsOut(values=settings_service.get_all(db))


@router.put("/settings", response_model=SettingsOut)
def update_app_settings(body: SettingsIn, db: DbDep, _: AdminPerson) -> SettingsOut:
    for key, value in body.values.items():
        settings_service.set_value(db, key, value)
    return SettingsOut(values=settings_service.get_all(db))


@router.get("/stats/dashboard")
def dashboard_stats(db: DbDep, _: AdminPerson) -> dict:
    return stats_service.dashboard(db)
