from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.security import read_user_id


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = read_user_id(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))
