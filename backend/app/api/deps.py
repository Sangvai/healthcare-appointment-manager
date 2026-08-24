from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise UnauthorizedError("Missing authentication token")
    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedError("Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def require_roles(*roles: UserRole):
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError(f"Requires one of roles: {[r.value for r in roles]}")
        return user

    return _checker


require_patient = require_roles(UserRole.PATIENT)
require_doctor = require_roles(UserRole.DOCTOR)
require_admin = require_roles(UserRole.ADMIN)
