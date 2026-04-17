"""Authentication and authorization for the CS Controle 360 web app.

Provides:

* ``hash_password`` / ``verify_password`` using bcrypt via ``passlib``.
* ``authenticate(username, password)`` → looks up a user and checks the hash.
* Session cookie helpers backed by ``itsdangerous`` (signed, opaque token
  storing the user id and a timestamp).
* ``ensure_default_admin()`` — seeds a default admin account on first boot
  when the database has no users; the password comes from
  ``CS_ADMIN_PASSWORD`` (defaults to ``admin`` with a console warning).
* ``get_current_user`` / ``require_role`` FastAPI dependencies that enforce
  authentication on protected routes. Legacy ``X-API-Key`` / ``api_key``
  credentials continue to work and are mapped to a synthetic admin user for
  backward compatibility.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Any, Dict, Iterable, Optional

import bcrypt
from fastapi import Header, HTTPException, Query, Request, status as http_status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from cs_web.repository import user_repo

logger = logging.getLogger(__name__)

SESSION_COOKIE = "cs_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours
API_KEY_USER: Dict[str, Any] = {
    "id": 0,
    "username": "api-key",
    "role": "admin",
    "is_api_key": True,
}

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def _secret_key() -> str:
    """Return the signing key, generating an ephemeral one if none is set.

    In production always configure ``CS_SESSION_SECRET`` — the generated
    key is reset on each process restart, which invalidates every active
    session. A warning is logged the first time a fallback is used.
    """
    key = os.environ.get("CS_SESSION_SECRET")
    if key:
        return key
    global _EPHEMERAL_KEY
    if _EPHEMERAL_KEY is None:
        _EPHEMERAL_KEY = secrets.token_urlsafe(32)
        logger.warning(
            "CS_SESSION_SECRET is not set; using an ephemeral signing key. "
            "Sessions will be invalidated on restart."
        )
    return _EPHEMERAL_KEY


_EPHEMERAL_KEY: Optional[str] = None


def _admin_token() -> str:
    return os.environ.get("CS_API_KEY", "cs-secret")


def _allow_unsecured_admin() -> bool:
    """Backwards-compat escape hatch: disable auth entirely.

    Defaults to ``0`` now that the app ships with real auth. Existing
    installs that relied on unsecured access can set
    ``CS_ALLOW_UNSECURED_ADMIN=1`` while they roll out accounts.
    """
    return os.environ.get("CS_ALLOW_UNSECURED_ADMIN", "0").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


# bcrypt limits the input to 72 bytes; we defensively truncate to match that
# behaviour so the application cannot be crashed by overly long passwords.
_BCRYPT_MAX_BYTES = 72


def _encode_password(plain: str) -> bytes:
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_encode_password(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_encode_password(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    user = user_repo.get_by_username(username.strip())
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


# ---------------------------------------------------------------------------
# Session cookie helpers
# ---------------------------------------------------------------------------


def _signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_secret_key(), salt="cs-session-v1")


def issue_session_token(user_id: int) -> str:
    return _signer().dumps({"uid": int(user_id)})


def read_session_token(token: str) -> Optional[int]:
    try:
        payload = _signer().loads(token, max_age=SESSION_MAX_AGE)
    except SignatureExpired:
        return None
    except BadSignature:
        return None
    try:
        return int(payload["uid"])
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# User seeding
# ---------------------------------------------------------------------------


def ensure_default_admin() -> None:
    """Create a default admin user if the users table is empty.

    Reads the password from ``CS_ADMIN_PASSWORD`` (default ``admin``).
    Intended to be called on application startup so the first deployment
    is usable without manual bootstrapping.
    """
    existing = user_repo.list()
    if existing:
        return
    username = os.environ.get("CS_ADMIN_USERNAME", "admin").strip() or "admin"
    password = os.environ.get("CS_ADMIN_PASSWORD", "admin")
    if password == "admin":
        logger.warning(
            "Creating default admin user with password 'admin'. "
            "Change it immediately or set CS_ADMIN_PASSWORD."
        )
    user_repo.insert(
        {
            "username": username,
            "password_hash": hash_password(password),
            "role": "admin",
        }
    )


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def _resolve_api_key_user(
    api_key_header: Optional[str], api_key_query: Optional[str]
) -> Optional[Dict[str, Any]]:
    key = api_key_header or api_key_query
    if key and key == _admin_token():
        return dict(API_KEY_USER)
    return None


def get_current_user(
    request: Request,
    api_key_header: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_query: Optional[str] = Query(None, alias="api_key"),
) -> Optional[Dict[str, Any]]:
    """Return the authenticated user (cookie or API key) or ``None``."""
    api_user = _resolve_api_key_user(api_key_header, api_key_query)
    if api_user is not None:
        return api_user
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    user_id = read_session_token(token)
    if user_id is None:
        return None
    user = user_repo.get(user_id)
    if not user:
        return None
    return user


def require_role(*roles: str):
    """FastAPI dependency that enforces authentication and role membership.

    When ``CS_ALLOW_UNSECURED_ADMIN=1`` the guard is skipped (backwards
    compatibility). Otherwise, missing authentication raises 401 and
    insufficient role raises 403.
    """
    allowed: Iterable[str] = tuple(roles) or ("admin",)

    def _dependency(
        request: Request,
        api_key_header: Optional[str] = Header(None, alias="X-API-Key"),
        api_key_query: Optional[str] = Query(None, alias="api_key"),
    ) -> Dict[str, Any]:
        if _allow_unsecured_admin():
            return dict(API_KEY_USER)
        user = get_current_user(request, api_key_header, api_key_query)
        if user is None:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Autenticação requerida",
                headers={"WWW-Authenticate": "Session"},
            )
        if user.get("role") not in allowed:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para esta operação",
            )
        return user

    return _dependency


__all__ = [
    "SESSION_COOKIE",
    "SESSION_MAX_AGE",
    "authenticate",
    "ensure_default_admin",
    "get_current_user",
    "hash_password",
    "issue_session_token",
    "read_session_token",
    "require_role",
    "verify_password",
]
