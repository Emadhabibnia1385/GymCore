"""Reports for the coach: the year at a glance, built by services/reports.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.db.session import get_db
from app.services import reports as reports_service

router = APIRouter(prefix="/api/admin", tags=["reports"], dependencies=[Depends(require_admin)])


@router.get("/reports", operation_id="reports_year")
def year_report(
    year: int | None = Query(default=None, ge=1300, le=1500), db: Session = Depends(get_db)
) -> dict:
    return reports_service.build(db, year)
