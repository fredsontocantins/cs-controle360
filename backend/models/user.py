"""User repository for authentication and approval control."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import TABLE_USER
from .base import BaseRepository


class UserRepository(BaseRepository):
    table = TABLE_USER
    columns = (
        "username",
        "email",
        "password_hash",
        "role",
        "provider",
        "google_sub",
        "full_name",
        "approval_status",
        "is_active",
        "created_at",
        "updated_at",
        "last_login_at",
    )
    json_fields = ()
    order_by = "created_at DESC"


def list_users(approval_status: Optional[str] = None) -> List[Dict[str, Any]]:
    if approval_status is None:
        return UserRepository.list()
    with UserRepository._connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM {UserRepository.table} WHERE approval_status = ? ORDER BY created_at DESC",
            (approval_status,),
        ).fetchall()
    return [UserRepository._to_dict(row) for row in rows]


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    return UserRepository.get(user_id)


def find_by_username(username: str) -> Optional[Dict[str, Any]]:
    with UserRepository._connect() as conn:
        row = conn.execute(
            f"SELECT * FROM {UserRepository.table} WHERE username = ?",
            (username,),
        ).fetchone()
    return UserRepository._to_dict(row) if row else None


def find_by_email(email: str) -> Optional[Dict[str, Any]]:
    with UserRepository._connect() as conn:
        row = conn.execute(
            f"SELECT * FROM {UserRepository.table} WHERE email = ?",
            (email,),
        ).fetchone()
    return UserRepository._to_dict(row) if row else None


def find_by_google_sub(google_sub: str) -> Optional[Dict[str, Any]]:
    with UserRepository._connect() as conn:
        row = conn.execute(
            f"SELECT * FROM {UserRepository.table} WHERE google_sub = ?",
            (google_sub,),
        ).fetchone()
    return UserRepository._to_dict(row) if row else None


def insert_user(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    payload.setdefault("updated_at", datetime.utcnow().isoformat())
    payload.setdefault("is_active", 1)
    payload.setdefault("approval_status", "approved")
    payload.setdefault("provider", "local")
    payload.setdefault("role", "user")
    return UserRepository.insert(payload)


def update_user(user_id: int, data: Dict[str, Any]) -> bool:
    payload = {**data, "updated_at": datetime.utcnow().isoformat()}
    return UserRepository.update(user_id, payload)


def touch_last_login(user_id: int) -> bool:
    return update_user(user_id, {"last_login_at": datetime.utcnow().isoformat()})
