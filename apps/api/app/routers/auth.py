from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, user_by_email
from app.models import User
from app.schemas import LoginIn, RegisterIn, UserOut
from app.security import clear_session_cookie, hash_password, set_session_cookie, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@lru_cache
def _dummy_password_hash() -> str:
    return hash_password("not-a-real-password")


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)) -> User:
    if user_by_email(db, body.email) is not None:
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with that email already exists") from None
    db.refresh(user)
    set_session_cookie(response, user.id)
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> User:
    user = user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        if user is None:
            verify_password(body.password, _dummy_password_hash())
        raise HTTPException(status_code=401, detail="Invalid email or password")
    set_session_cookie(response, user.id)
    return user


@router.post("/logout", status_code=204)
def logout() -> Response:
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
