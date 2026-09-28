"""
Seguridad de administrador (T008/T009/T010).

Password: bcrypt (hash_password/verify_password) — FR-020.
Sesion: token "JWT-like" firmado a mano con HMAC-SHA256 sobre hashlib/hmac de la
stdlib (research.md §1, Opcion C), sin dependencias nuevas. Formato del token:
    "<payload_base64url>.<firma_hex>"
payload = {"username": str, "exp": <epoch_ms medianoche local del cliente>}.

La clave de firma se deriva de `settings.admin_password_hash` (ya es un secreto
por-instalacion leido de variables de entorno), evitando agregar otro campo de
configuracion solo para esto.
"""
import base64
import hashlib
import hmac
import json
import time
import datetime as dt
from zoneinfo import ZoneInfo

import bcrypt
from fastapi import Header, HTTPException

from app.config import settings
from app.core.timezone import next_midnight_epoch_ms


def _now() -> dt.datetime:
    """Punto unico de acceso al reloj (UTC-aware). Se referencia `time.time()`
    para que los tests puedan mockear tanto `time.time` como `_now` directamente
    (ver tests/integration/test_auth_guard.py y test_session_timezone.py)."""
    return dt.datetime.fromtimestamp(time.time(), tz=dt.timezone.utc)


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _signing_key() -> bytes:
    return hashlib.sha256(settings.admin_password_hash.encode("utf-8")).digest()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_session_token(username: str, tz: ZoneInfo) -> tuple[str, int]:
    """Emite un token cuyo `exp` es la proxima medianoche 00:00 en `tz` (FR-002)."""
    exp_ms = next_midnight_epoch_ms(tz, now=_now())
    payload = {"username": username, "exp": exp_ms}
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_signing_key(), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}", exp_ms


def _decode_token(token: str) -> dict | None:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = hmac.new(_signing_key(), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        return json.loads(_b64decode(payload_b64))
    except Exception:
        return None


def verify_session_token(token: str) -> bool:
    payload = _decode_token(token)
    if payload is None or "exp" not in payload:
        return False
    now_ms = int(_now().timestamp() * 1000)
    return now_ms < payload["exp"]


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def require_admin_session(authorization: str | None = Header(default=None)) -> str:
    """Dependency FastAPI (T009): exige `Authorization: Bearer <token>` valido y
    no expirado. Devuelve el username para que el endpoint lo use si necesita."""
    token = _extract_bearer_token(authorization)
    if not token or not verify_session_token(token):
        raise HTTPException(status_code=401, detail="No autenticado o sesión expirada")
    payload = _decode_token(token)
    return payload["username"]


def require_internal_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    """Dependency FastAPI (T010): exige `X-Internal-Secret` igual al configurado
    para el endpoint interno de invalidacion de cache llamado por el ETL."""
    if not x_internal_secret or not hmac.compare_digest(
        x_internal_secret, settings.etl_cache_invalidation_secret
    ):
        raise HTTPException(status_code=401, detail="Secreto interno inválido")
