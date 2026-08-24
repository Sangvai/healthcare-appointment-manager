import secrets

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ValidationAppError
from app.models.user import User
from app.services import calendar_service

router = APIRouter(prefix="/google", tags=["google-calendar"])

# In production back this with Redis; in-memory is fine for a single dev instance.
_STATE_TO_USER: dict[str, int] = {}


@router.post("/connect")
def connect(user: User = Depends(get_current_user)):
    """Returns the Google consent URL for the frontend to redirect to.
    `state` binds the OAuth callback back to this user without requiring
    the user to be re-authenticated via a cookie/session at callback time.
    """
    state = secrets.token_urlsafe(24)
    _STATE_TO_USER[state] = user.id
    url = calendar_service.build_authorization_url(state)
    return {"authorization_url": url}


@router.get("/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    user_id = _STATE_TO_USER.pop(state, None)
    if not user_id:
        raise ValidationAppError("Invalid or expired OAuth state")
    credentials = calendar_service.exchange_code(code)
    calendar_service.save_connection(db, user_id, credentials)
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/calendar-connected")
