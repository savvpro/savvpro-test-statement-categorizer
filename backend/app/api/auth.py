"""Authentication API – user registration and login."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from app.db import get_session
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

_SECRET_SALT = b"taxsort_secure_salt_2026"


def _hash_password(password: str) -> str:
    """Hash password using PBKDF2 HMAC SHA-256."""
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _SECRET_SALT, 100_000)
    return h.hex()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored hash."""
    expected = _hash_password(password)
    return hmac.compare_digest(expected, hashed)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = "Tax Filer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# Simple in-memory token store: token -> user_id
_ACTIVE_TOKENS: dict[str, int] = {}


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, session: Session = Depends(get_session)):
    """Register a new user account."""
    existing = session.exec(select(User).where(User.email == body.email.lower())).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = User(
        email=body.email.lower(),
        full_name=body.full_name or "Tax Filer",
        password_hash=_hash_password(body.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = secrets.token_hex(24)
    _ACTIVE_TOKENS[token] = user.id

    return AuthResponse(
        token=token,
        user=UserOut(id=user.id, email=user.email, full_name=user.full_name),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    """Authenticate existing user with email and password."""
    user = session.exec(select(User).where(User.email == body.email.lower())).first()
    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_hex(24)
    _ACTIVE_TOKENS[token] = user.id

    return AuthResponse(
        token=token,
        user=UserOut(id=user.id, email=user.email, full_name=user.full_name),
    )


@router.get("/me", response_model=UserOut)
def get_current_user(
    authorization: Optional[str] = Header(None),
    session: Session = Depends(get_session),
):
    """Retrieve currently logged in user info."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization.replace("Bearer ", "").strip()
    user_id = _ACTIVE_TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserOut(id=user.id, email=user.email, full_name=user.full_name)
