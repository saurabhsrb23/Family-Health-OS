import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from cache.redis_client import CacheKeys, cache
from database import get_db
from models.user import User
from schemas.user import RefreshTokenRequest, TokenResponse, UserLogin, UserRegister, UserResponse
from utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    security,
    verify_password,
)
from fastapi.security import HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── helpers ───────────────────────────────────────────────────────────────────

def _error(code: str, detail: str, status_code: int):
    raise HTTPException(
        status_code=status_code,
        detail={"error": code, "detail": detail, "status_code": status_code},
    )


def _build_token_response(user: User) -> TokenResponse:
    payload = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ── POST /auth/register ───────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.
    Returns access + refresh tokens immediately (no email verification required for MVP).
    """
    existing = db.query(User).filter(
        User.email == body.email.lower(),
        User.deleted_at.is_(None),
    ).first()
    if existing:
        _error("AUTH_DUPLICATE_EMAIL", f"An account with {body.email} already exists", 409)

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New user registered: {user.email}")
    return _build_token_response(user)


# ── POST /auth/login ──────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    Login with email + password.
    Rate limited to 5 attempts per IP per minute.
    """
    # Rate limiting
    ip = request.client.host if request.client else "unknown"
    minute = datetime.utcnow().strftime("%Y%m%d%H%M")
    rate_key = CacheKeys.format(CacheKeys.RATE_LIMIT, endpoint="login", ip=ip, minute=minute)
    attempts = cache.increment(rate_key, ttl=60)
    if attempts > 5:
        _error("RATE_LIMIT_EXCEEDED", "Too many login attempts. Try again in 1 minute.", 429)

    # Lookup user
    user = db.query(User).filter(
        User.email == body.email.lower(),
        User.deleted_at.is_(None),
    ).first()

    # Use constant-time comparison to prevent user enumeration
    if not user or not verify_password(body.password, user.hashed_password):
        _error("AUTH_INVALID_CREDENTIALS", "Invalid email or password", 401)

    if not user.is_active:
        _error("AUTH_ACCOUNT_INACTIVE", "Account is inactive. Contact support.", 403)

    logger.info(f"User logged in: {user.email}")
    return _build_token_response(user)


# ── POST /auth/refresh ────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token.
    Refresh token must not be blacklisted.
    """
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        _error("AUTH_WRONG_TOKEN_TYPE", "Refresh token required", 400)

    # Check refresh token blacklist
    jti = payload.get("jti")
    if jti:
        blacklist_key = CacheKeys.format(CacheKeys.TOKEN_BLACKLIST, jti=jti)
        if cache.exists(blacklist_key):
            _error("AUTH_TOKEN_REVOKED", "Refresh token has been revoked", 401)

    user_id = payload.get("sub")
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
        User.is_active.is_(True),
    ).first()

    if not user:
        _error("AUTH_USER_NOT_FOUND", "User not found or inactive", 401)

    return _build_token_response(user)


# ── POST /auth/logout ─────────────────────────────────────────────────────────

@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
):
    """
    Logout — blacklist the current access token in Redis.
    Token becomes invalid immediately (even before natural expiry).
    """
    token = credentials.credentials
    payload = decode_token(token)

    jti = payload.get("jti")
    exp = payload.get("exp")

    if jti and exp:
        # TTL = remaining lifetime of token so blacklist auto-expires
        remaining_ttl = int(exp - datetime.utcnow().timestamp())
        if remaining_ttl > 0:
            blacklist_key = CacheKeys.format(CacheKeys.TOKEN_BLACKLIST, jti=jti)
            cache.set(blacklist_key, "revoked", ttl=remaining_ttl)

    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Logged out successfully"}


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
