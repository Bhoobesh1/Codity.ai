import logging

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories import user_repository

logger = logging.getLogger(__name__)


def register_user(db: Session, *, email: str, password: str, full_name: str) -> User:
    if user_repository.get_by_email(db, email) is not None:
        raise ConflictError("An account with this email already exists.")

    user = user_repository.create(
        db, email=email, hashed_password=hash_password(password), full_name=full_name
    )
    db.commit()
    db.refresh(user)
    logger.info("User registered: %s", user.id)
    return user


def authenticate(db: Session, *, email: str, password: str) -> str:
    """Returns a signed access token, or raises UnauthorizedError."""
    user = user_repository.get_by_email(db, email)
    # Deliberately give the same error for "no such user" and "wrong
    # password" -- distinguishing them lets an attacker enumerate which
    # emails have accounts.
    if user is None or not verify_password(password, user.hashed_password):
        logger.info("Failed login attempt for email: %s", email)
        raise UnauthorizedError("Incorrect email or password.")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.")

    logger.info("User logged in: %s", user.id)
    return create_access_token(subject=user.id)
