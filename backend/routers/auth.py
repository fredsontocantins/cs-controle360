"""Authentication endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.user import get_user, list_users, update_user
from ..schemas.auth import AuthResponse, GoogleLoginRequest, LoginRequest, UserResponse
from ..services.auth import get_current_user, login_google, login_local, require_admin, user_payload

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    return await login_local(data.username, data.password)


@router.post("/google", response_model=AuthResponse)
async def google_login(data: GoogleLoginRequest):
    return await login_google(data.credential)


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return user_payload(user)


@router.get("/users")
async def get_users(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    _admin=Depends(require_admin),
):
    users = list_users(approval_status=status_filter)
    return {"users": [user_payload(user) for user in users]}


@router.post("/users/{user_id}/approve")
async def approve_user(user_id: int, _admin=Depends(require_admin)):
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    update_user(user_id, {"approval_status": "approved", "is_active": 1})
    refreshed = get_user(user_id) or user
    return {"status": "approved", "user": user_payload(refreshed)}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(user_id: int, _admin=Depends(require_admin)):
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    update_user(user_id, {"approval_status": "blocked", "is_active": 0})
    refreshed = get_user(user_id) or user
    return {"status": "deactivated", "user": user_payload(refreshed)}
