"""Bot request review endpoints (admin only)."""

from fastapi import APIRouter

from app.api.deps import AdminPerson, DbDep
from app.models import ClassRegistrationRequest, PlanRequest, RequestStatus
from app.schemas.entities import ClassRequestOut, PlanRequestOut
from app.services import requests as requests_service

router = APIRouter(prefix="/requests", tags=["requests"])


def _class_out(request: ClassRegistrationRequest) -> ClassRequestOut:
    out = ClassRequestOut.model_validate(request)
    out.person_name = request.person.name
    out.class_title = request.class_type.title
    return out


def _plan_out(request: PlanRequest) -> PlanRequestOut:
    out = PlanRequestOut.model_validate(request)
    out.person_name = request.person.name
    return out


@router.get("/classes", response_model=list[ClassRequestOut])
def list_class_requests(
    db: DbDep, _: AdminPerson, status: RequestStatus | None = None
) -> list[ClassRequestOut]:
    return [_class_out(r) for r in requests_service.list_class_requests(db, status)]


@router.post("/classes/{request_id}/decision", response_model=ClassRequestOut)
def decide_class_request(
    request_id: int, approve: bool, db: DbDep, _: AdminPerson
) -> ClassRequestOut:
    return _class_out(requests_service.decide_class_request(db, request_id, approve))


@router.get("/plans", response_model=list[PlanRequestOut])
def list_plan_requests(
    db: DbDep, _: AdminPerson, status: RequestStatus | None = None
) -> list[PlanRequestOut]:
    return [_plan_out(r) for r in requests_service.list_plan_requests(db, status)]


@router.post("/plans/{request_id}/decision", response_model=PlanRequestOut)
def decide_plan_request(
    request_id: int, approve: bool, db: DbDep, _: AdminPerson
) -> PlanRequestOut:
    return _plan_out(requests_service.decide_plan_request(db, request_id, approve))
