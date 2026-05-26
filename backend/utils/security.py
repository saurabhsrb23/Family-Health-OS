import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from cache.redis_client import CacheKeys, cache
from config import settings
from database import get_db

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    Payload includes: sub (user_id), type=access, exp, iat, jti (unique token id).
    """
    import uuid as _uuid

    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": str(_uuid.uuid4()),  # unique token id — used for blacklisting on logout
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a signed JWT refresh token with 7-day expiry.
    Payload includes: sub (user_id), type=refresh, exp, iat, jti.
    """
    import uuid as _uuid

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": str(_uuid.uuid4()),
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.
    Raises HTTP 401 if token is expired, malformed, or signature is invalid.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AUTH_INVALID_TOKEN", "detail": "Token is invalid or expired", "status_code": 401},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency — resolves the authenticated user from Bearer token.

    Steps:
      1. Extract token from Authorization header
      2. Decode + verify JWT signature
      3. Check token type == "access"
      4. Check jti not in Redis blacklist (logged-out tokens)
      5. Load user from DB by user_id in token sub claim
      6. Check user.is_active == True
      7. Return User ORM object
    """
    from models.user import User

    token = credentials.credentials
    payload = decode_token(token)

    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AUTH_WRONG_TOKEN_TYPE", "detail": "Access token required", "status_code": 401},
        )

    # Check blacklist (logout invalidation)
    jti = payload.get("jti")
    if jti:
        blacklist_key = CacheKeys.format(CacheKeys.TOKEN_BLACKLIST, jti=jti)
        if cache.exists(blacklist_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "AUTH_TOKEN_REVOKED", "detail": "Token has been revoked", "status_code": 401},
            )

    # Load user
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AUTH_INVALID_TOKEN", "detail": "Token missing subject", "status_code": 401},
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AUTH_USER_NOT_FOUND", "detail": "User not found", "status_code": 401},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "AUTH_ACCOUNT_INACTIVE", "detail": "Account is inactive", "status_code": 403},
        )

    return user
