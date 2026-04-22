"""Authentication helpers for the CS Controle 360 stack."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

import bcrypt
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..config import AUTH_ENABLED, AUTH_SECRET, AUTH_TOKEN_MAX_AGE_SECONDS, GOOGLE_CLIENT_ID
from ..models.auth_audit import insert_auth_audit
from ..models.user import (
    find_by_email,
    find_by_google_sub,
    find_by_username,
    get_user,
    insert_user,
    touch_last_login,
    update_user,
)

bearer_scheme = HTTPBearer(auto_error=False)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(AUTH_SECRET, salt="cs-control-360-auth")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(user: Dict[str, Any]) -> str:
    payload = {
        "user_id": user["id"],
        "username": user.get("username"),
        "role": user.get("role", "user"),
        "provider": user.get("provider", "local"),
        "approval_status": user.get("approval_status", "approved"),
        "issued_at": datetime.utcnow().isoformat(),
    }
    return _serializer().dumps(payload)


def _token_expires_at() -> str:
    return (datetime.utcnow() + timedelta(seconds=AUTH_TOKEN_MAX_AGE_SECONDS)).isoformat()


def _auth_response(user: Dict[str, Any], status: str = "authenticated", message: str | None = None) -> Dict[str, Any]:
    refreshed = user_payload(user)
    payload: Dict[str, Any] = {
        "status": status,
        "token": create_token(user) if status == "authenticated" else None,
        "user": refreshed,
        "expires_at": _token_expires_at() if status == "authenticated" else None,
    }
    if message:
        payload["message"] = message
    return payload


def record_auth_event(
    *,
    event_type: str,
    status: str,
    message: str,
    actor_user: Dict[str, Any] | None = None,
    target_user: Dict[str, Any] | None = None,
    provider: str | None = None,
    details: Dict[str, Any] | None = None,
) -> None:
    insert_auth_audit(
        {
            "actor_user_id": actor_user.get("id") if actor_user else None,
            "actor_username": actor_user.get("username") if actor_user else None,
            "target_user_id": target_user.get("id") if target_user else None,
            "target_username": target_user.get("username") if target_user else None,
            "event_type": event_type,
            "status": status,
            "provider": provider,
            "message": message,
            "details_json": details or {},
        }
    )


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = _serializer().loads(token, max_age=AUTH_TOKEN_MAX_AGE_SECONDS)
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return payload
    except SignatureExpired as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc


def user_payload(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role", "user"),
        "provider": user.get("provider", "local"),
        "approval_status": user.get("approval_status", "approved"),
        "is_active": bool(user.get("is_active", 1)),
        "last_login_at": user.get("last_login_at"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }


def bootstrap_default_admin() -> Dict[str, Any]:
    admin = find_by_username("admin")
    if admin:
        if not admin.get("password_hash"):
            password_hash = hash_password("admin")
            update_user(admin["id"], {"password_hash": password_hash, "approval_status": "approved", "is_active": 1, "role": "admin"})
            admin = get_user(admin["id"]) or admin
        return admin
    password_hash = hash_password("admin")
    user_id = insert_user(
        {
            "username": "admin",
            "email": "admin@local",
            "password_hash": password_hash,
            "role": "admin",
            "provider": "local",
            "approval_status": "approved",
            "is_active": 1,
            "full_name": "Administrator",
        }
    )
    return get_user(user_id) or {"id": user_id, "username": "admin"}


def _ensure_active_approved(user: Dict[str, Any]) -> None:
    if not user.get("is_active", 1):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário desativado")
    if str(user.get("approval_status") or "").lower() != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso aguardando aprovação interna")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Dict[str, Any]:
    if not AUTH_ENABLED:
        return {"id": 0, "username": "system", "role": "admin", "approval_status": "approved", "is_active": 1}
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária")
    payload = decode_token(credentials.credentials)
    user = get_user(int(payload["user_id"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    _ensure_active_approved(user)
    return user


async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if not AUTH_ENABLED:
        return user
    if str(user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao administrador")
    return user


async def login_local(username: str, password: str) -> Dict[str, Any]:
    user = find_by_username(username)
    if not user or not verify_password(password, user.get("password_hash")):
        record_auth_event(
            event_type="login_local",
            status="failed",
            message="Usuário ou senha inválidos",
            provider="local",
            details={"username": username},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos")
    _ensure_active_approved(user)
    touch_last_login(user["id"])
    refreshed = get_user(user["id"]) or user
    record_auth_event(
        event_type="login_local",
        status="success",
        message="Login local autenticado com sucesso",
        actor_user=refreshed,
        target_user=refreshed,
        provider="local",
    )
    return _auth_response(refreshed)


async def verify_google_credential(credential: str) -> Dict[str, Any]:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google login não configurado")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": credential})
    if response.status_code != 200:
        detail = None
        try:
            detail = response.json().get("error_description") or response.json().get("error")
        except Exception:
            detail = response.text
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail or "Credential Google inválida")
    payload = response.json()
    if payload.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google client_id inválido")
    if str(payload.get("email_verified", "")).lower() != "true":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail Google não verificado")
    return payload


async def login_google(credential: str) -> Dict[str, Any]:
    claims = await verify_google_credential(credential)
    google_sub = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    full_name = str(claims.get("name") or claims.get("email") or "Google User").strip()
    user = find_by_google_sub(google_sub) if google_sub else None
    if user is None and email:
        user = find_by_email(email)
        if user and not user.get("google_sub"):
            update_user(
                user["id"],
                {
                    "google_sub": google_sub,
                    "provider": "google",
                    "full_name": full_name,
                },
            )
            user = get_user(user["id"]) or user

    if user is None:
        user_id = insert_user(
            {
                "username": email or f"google_{google_sub[:12]}",
                "email": email,
                "password_hash": None,
                "role": "user",
                "provider": "google",
                "google_sub": google_sub,
                "full_name": full_name,
                "approval_status": "pending",
                "is_active": 0,
            }
        )
        user = get_user(user_id)
    elif user and not user.get("google_sub") and google_sub:
        update_user(user["id"], {"google_sub": google_sub, "provider": "google", "full_name": full_name})
        user = get_user(user["id"]) or user

    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao preparar usuário Google")

    if str(user.get("approval_status") or "").lower() != "approved" or not user.get("is_active", 1):
        record_auth_event(
            event_type="login_google",
            status="pending_approval",
            message="Acesso Google aguardando liberação interna do administrador.",
            target_user=user,
            provider="google",
            details={"email": email, "google_sub": google_sub},
        )
        return {
            "status": "pending_approval",
            "user": user_payload(user),
            "message": "Acesso Google aguardando liberação interna do administrador.",
            "expires_at": None,
            "token": None,
        }

    touch_last_login(user["id"])
    refreshed = get_user(user["id"]) or user
    record_auth_event(
        event_type="login_google",
        status="success",
        message="Login Google autenticado com sucesso",
        actor_user=refreshed,
        target_user=refreshed,
        provider="google",
        details={"email": email, "google_sub": google_sub},
    )
    return _auth_response(refreshed)
