"""
Security primitives: password hashing and JWT encode/decode.

Kept separate from app/api/deps.py (which wires these into FastAPI
dependencies) so this module has zero FastAPI imports -- it's pure,
testable logic you could reuse in the worker service later if it ever
needed to verify a token.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    # bcrypt has a hard 72-byte input limit; truncate defensively so a very
    # long password doesn't raise instead of just being (safely) shortened.
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(subject: str) -> str:
    """
    Create a signed JWT whose `sub` claim is the user's id.

    We intentionally keep the payload minimal (just sub + exp + iat).
    Anything else about the user (email, roles) should be looked up from
    the DB on each request rather than trusted from the token, so that
    revoking access or changing a user's data takes effect immediately
    instead of only after their token expires.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": subject, "iat": now, "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Returns the user id (sub claim) if the token is valid, else None."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None
