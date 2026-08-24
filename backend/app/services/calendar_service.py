import logging
from datetime import datetime, timezone

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.calendar import CalendarConnection

logger = logging.getLogger("calendar_service")

SCOPES = [settings.GOOGLE_SCOPES]


def _flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI)


def build_authorization_url(state: str) -> str:
    flow = _flow()
    url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
    return url


def exchange_code(code: str) -> Credentials:
    flow = _flow()
    flow.fetch_token(code=code)
    return flow.credentials


def save_connection(db: Session, user_id: int, credentials: Credentials) -> CalendarConnection:
    conn = db.query(CalendarConnection).filter(
        CalendarConnection.user_id == user_id, CalendarConnection.provider == "google"
    ).first()
    if not conn:
        conn = CalendarConnection(user_id=user_id, provider="google")
        db.add(conn)
    conn.access_token = credentials.token
    conn.refresh_token = credentials.refresh_token or conn.refresh_token
    conn.token_expiry = credentials.expiry.replace(tzinfo=timezone.utc) if credentials.expiry else None
    conn.is_valid = True
    db.commit()
    db.refresh(conn)
    return conn


def _credentials_from_connection(conn: CalendarConnection) -> Credentials:
    return Credentials(
        token=conn.access_token,
        refresh_token=conn.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )


def _get_calendar_client(db: Session, conn: CalendarConnection):
    creds = _credentials_from_connection(conn)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            conn.access_token = creds.token
            conn.is_valid = True
            db.commit()
        except RefreshError as exc:
            # Refresh token revoked/expired: mark the connection invalid so
            # the caller can skip calendar sync instead of failing booking.
            logger.warning("Google token refresh failed for user %s: %s", conn.user_id, exc)
            conn.is_valid = False
            db.commit()
            raise
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


class CalendarResult:
    def __init__(self, success: bool, event_id: str | None = None, error: str | None = None):
        self.success = success
        self.event_id = event_id
        self.error = error


def create_event(
    db: Session,
    conn: CalendarConnection,
    summary: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
) -> CalendarResult:
    """Never raises. Calendar sync is best-effort and must not invalidate
    an already-confirmed appointment."""
    try:
        service = _get_calendar_client(db, conn)
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time.isoformat()},
            "end": {"dateTime": end_time.isoformat()},
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        return CalendarResult(True, event_id=created["id"])
    except RefreshError as exc:
        return CalendarResult(False, error=f"Google token invalid/expired: {exc}")
    except HttpError as exc:
        logger.warning("Google Calendar create_event failed: %s", exc)
        return CalendarResult(False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected calendar failure (create_event)")
        return CalendarResult(False, error=str(exc))


def update_event(
    db: Session, conn: CalendarConnection, google_event_id: str, start_time: datetime, end_time: datetime
) -> CalendarResult:
    try:
        service = _get_calendar_client(db, conn)
        patch = {"start": {"dateTime": start_time.isoformat()}, "end": {"dateTime": end_time.isoformat()}}
        service.events().patch(calendarId="primary", eventId=google_event_id, body=patch).execute()
        return CalendarResult(True, event_id=google_event_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Google Calendar update_event failed: %s", exc)
        return CalendarResult(False, error=str(exc))


def delete_event(db: Session, conn: CalendarConnection, google_event_id: str) -> CalendarResult:
    try:
        service = _get_calendar_client(db, conn)
        service.events().delete(calendarId="primary", eventId=google_event_id).execute()
        return CalendarResult(True)
    except HttpError as exc:
        if exc.resp.status == 410:  # already deleted
            return CalendarResult(True)
        logger.warning("Google Calendar delete_event failed: %s", exc)
        return CalendarResult(False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected calendar failure (delete_event)")
        return CalendarResult(False, error=str(exc))
