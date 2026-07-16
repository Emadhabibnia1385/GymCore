"""Auth endpoints: login (token + cookie), current user, logout."""

from fastapi import APIRouter, Response

from app.api.deps import COOKIE_NAME, CurrentPerson, DbDep
from app.core.config import get_settings
from app.schemas.entities import LoginIn, PersonOut, TokenOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, response: Response, db: DbDep) -> TokenOut:
    settings = get_settings()
    _, token = auth_service.login(db, body.phone, body.password)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return TokenOut(access_token=token)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {"detail": "logged out"}


@router.get("/me", response_model=PersonOut)
def me(person: CurrentPerson) -> PersonOut:
    return PersonOut.model_validate(person)
