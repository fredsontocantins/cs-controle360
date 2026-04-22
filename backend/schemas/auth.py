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
    expires_at: Optional[str] = None


class AuthAuditLog(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    target_user_id: Optional[int] = None
    target_username: Optional[str] = None
    event_type: str
    status: str
    provider: Optional[str] = None
    message: Optional[str] = None
    details: Optional[dict] = None
    created_at: str


class AuthAuditLogList(BaseModel):
    logs: list[AuthAuditLog]
