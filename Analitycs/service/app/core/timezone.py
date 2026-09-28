"""
Utilidades de zona horaria (T007). Resuelve la tz vigente del cliente/admin al
momento de la solicitud (FR-002, FR-021, research.md §2), sin depender de una
zona horaria fija de servidor. Usa exclusivamente `zoneinfo` (stdlib), sin
dependencias nuevas.
"""
import datetime as dt
from zoneinfo import ZoneInfo, available_timezones

from app.config import settings

_AVAILABLE_TZ_CACHE: set[str] | None = None


def _available_tz() -> set[str]:
    global _AVAILABLE_TZ_CACHE
    if _AVAILABLE_TZ_CACHE is None:
        _AVAILABLE_TZ_CACHE = available_timezones()
    return _AVAILABLE_TZ_CACHE


def resolve_client_timezone(header_value: str | None) -> ZoneInfo:
    """Devuelve la ZoneInfo a partir de un nombre IANA recibido por header/campo
    `timezone`. Si `header_value` es None o no es un nombre IANA valido, cae al
    default configurado (`settings.default_client_timezone`, UTC por defecto)."""
    candidate = header_value or settings.default_client_timezone
    if candidate not in _available_tz():
        candidate = settings.default_client_timezone
    if candidate not in _available_tz():
        candidate = "UTC"
    return ZoneInfo(candidate)


def next_midnight_epoch_ms(tz: ZoneInfo, now: dt.datetime | None = None) -> int:
    """Epoch ms (UTC) de la proxima medianoche 00:00 en la tz dada, tomando como
    referencia `now` (UTC-aware) — usado para el `exp` de la sesion (FR-002)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    local_now = now.astimezone(tz)
    next_midnight_local = (local_now + dt.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int(next_midnight_local.astimezone(dt.timezone.utc).timestamp() * 1000)


def period_bounds_epoch_ms(period: str, tz: ZoneInfo, now: dt.datetime | None = None) -> tuple[int | None, int | None]:
    """Calcula (since_ms, until_ms) para 'last_week'/'last_month'/'last_3_months'/
    'last_year'/'all', usando medianoche local de `tz` como corte (FR-011/FR-021).
    Devuelve (None, None) para 'all' (sin acotar)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    local_now = now.astimezone(tz)
    today_midnight_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    deltas = {
        "last_week": dt.timedelta(days=7),
        "last_month": dt.timedelta(days=30),
        "last_3_months": dt.timedelta(days=90),
        "last_year": dt.timedelta(days=365),
    }
    if period not in deltas:
        return None, None

    since_local = today_midnight_local - deltas[period]
    since_ms = int(since_local.astimezone(dt.timezone.utc).timestamp() * 1000)
    until_ms = int(today_midnight_local.astimezone(dt.timezone.utc).timestamp() * 1000)
    return since_ms, until_ms
