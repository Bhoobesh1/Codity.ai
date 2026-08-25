from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories import user_repository

# auto_error=False so we can raise our own structured UnauthorizedError
# instead of FastAPI's default plain-text 403 when the header is missing.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing authentication token.")

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise UnauthorizedError("Invalid or expired authentication token.")

    user = user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired authentication token.")

    return user
