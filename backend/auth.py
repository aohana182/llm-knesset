"""Authentication and session management for LLM Knesset."""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

import httpx
import jwt
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from fastapi import Cookie, HTTPException

SESSION_COOKIE = "llmc_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

FIREBASE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

_cert_cache: dict = {"certs": None, "expires": 0}


def _get_secret() -> str:
    secret = os.getenv("SESSION_SECRET", "")
    if not secret:
        raise RuntimeError("SESSION_SECRET environment variable not set")
    return secret


def create_session_token(user: dict) -> str:
    payload = json.dumps({**user, "exp": int(time.time()) + SESSION_MAX_AGE}).encode()
    b64 = base64.urlsafe_b64encode(payload).decode()
    sig = hmac.new(_get_secret().encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def verify_session_token(token: str) -> Optional[dict]:
    try:
        b64, sig = token.rsplit(".", 1)
        expected = hmac.new(_get_secret().encode(), b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(b64))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


async def _fetch_firebase_certs() -> dict:
    now = time.time()
    if _cert_cache["certs"] and _cert_cache["expires"] > now:
        return _cert_cache["certs"]
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(FIREBASE_CERTS_URL)
        resp.raise_for_status()
        max_age = 3600
        cc = resp.headers.get("cache-control", "")
        for part in cc.split(","):
            part = part.strip()
            if part.startswith("max-age="):
                try:
                    max_age = int(part[8:])
                except ValueError:
                    pass
        _cert_cache["certs"] = resp.json()
        _cert_cache["expires"] = now + max_age
    return _cert_cache["certs"]


async def verify_firebase_token(id_token: str) -> dict:
    project_id = os.getenv("VITE_FIREBASE_PROJECT_ID", "")
    if not project_id:
        raise HTTPException(status_code=503, detail="Firebase not configured. Set VITE_FIREBASE_PROJECT_ID.")

    certs = await _fetch_firebase_certs()

    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    if kid not in certs:
        raise HTTPException(status_code=401, detail="Invalid Firebase token: unknown key id")

    cert = x509.load_pem_x509_certificate(certs[kid].encode(), default_backend())
    public_key = cert.public_key()

    try:
        payload = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Firebase token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {e}")

    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Firebase token missing subject")
    if not payload.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Google account email not verified")

    return payload


def _get_user_from_cookie(llmc_session: Optional[str]) -> Optional[dict]:
    if not llmc_session:
        return None
    return verify_session_token(llmc_session)


def require_user(llmc_session: Optional[str] = Cookie(default=None)) -> dict:
    user = _get_user_from_cookie(llmc_session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(llmc_session: Optional[str] = Cookie(default=None)) -> dict:
    from . import settings_store
    user = _get_user_from_cookie(llmc_session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user.get("email") not in settings_store.get_admin_emails():
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
