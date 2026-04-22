"""Authentication schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="admin")


class GoogleLoginRequest(BaseModel):
    credential: str = Field(..., description="Google ID token credential")


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    provider: str
    approval_status: str
    is_active: bool
    last_login_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AuthResponse(BaseModel):
    status: str
    token: Optional[str] = None
    user: UserResponse
    message: Optional[str] = None

