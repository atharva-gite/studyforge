"""Per-account request windows.

The web app proxies every call, so the peer address is the proxy. Login and
register are limited by email. Study calls that use the model are limited by
user id.
"""

import threading
import time
from collections.abc import Callable
from typing import TypeVar

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_current_user
from app.models import User
from app.services.language import TransientLanguageError

T = TypeVar("T")

_WINDOW_SECONDS = 60.0
_lock = threading.Lock()
_auth: dict[str, list[float]] = {}
_model: dict[str, list[float]] = {}

AUTH_DETAIL = "Too many attempts. Try again shortly."
MODEL_DETAIL = "Too many study requests. Try again shortly."


def _hit(bucket: dict[str, list[float]], key: str, limit: int, detail: str) -> None:
    now = time.monotonic()
    with _lock:
        recent = [stamp for stamp in bucket.get(key, []) if now - stamp < _WINDOW_SECONDS]
        if len(recent) >= limit:
            bucket[key] = recent
            retry_after = max(1, int(_WINDOW_SECONDS - (now - recent[0])) + 1)
            raise HTTPException(
                status_code=429,
                detail=detail,
                headers={"Retry-After": str(retry_after)},
            )
        recent.append(now)
        bucket[key] = recent
        if len(bucket) > 10000:
            stale = [item for item, stamps in bucket.items() if now - stamps[-1] >= _WINDOW_SECONDS]
            for item in stale:
                bucket.pop(item, None)


def clear_limits() -> None:
    with _lock:
        _auth.clear()
        _model.clear()


def limit_auth(email: str) -> None:
    _hit(_auth, email, get_settings().auth_attempts_per_minute, AUTH_DETAIL)


def require_model_budget(user: User = Depends(get_current_user)) -> User:
    _hit(_model, str(user.id), get_settings().model_requests_per_minute, MODEL_DETAIL)
    return user


def retry_transient(db: Session, operation: Callable[[], T]) -> T:
    """Run one extra time when the model blip is temporary. A second failure propagates."""
    try:
        return operation()
    except TransientLanguageError:
        db.rollback()
        return operation()
