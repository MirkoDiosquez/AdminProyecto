"""
T016 — Expiracion de sesion a medianoche segun la timezone del cliente (FR-002).

La sesion emitida en el login DEBE expirar a las 00:00 de la timezone indicada por
el cliente (no una zona fija del servidor), sin importar la hora de login.
Se prueba con 2 timezones distintas: UTC y America/Argentina/Buenos_Aires.
"""
import datetime as dt
from zoneinfo import ZoneInfo

import pytest


@pytest.mark.parametrize("timezone_name", ["UTC", "America/Argentina/Buenos_Aires"])
def test_token_expira_a_medianoche_de_la_tz_del_cliente(client, mock_repo, admin_credentials, timezone_name, monkeypatch):
    from app.core import security

    admin_credentials = {**admin_credentials, "timezone": timezone_name}

    # GIVEN: login realizado a una hora arbitraria (23:50 hora local de esa tz)
    tz = ZoneInfo(timezone_name)
    fake_now = dt.datetime.now(tz).replace(hour=23, minute=50, second=0, microsecond=0)
    monkeypatch.setattr(security, "_now", lambda: fake_now.astimezone(dt.timezone.utc))

    resp = client.post("/api/admin/auth/login", json=admin_credentials)
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # WHEN: todavia no paso la medianoche local -> sigue autenticado
    still_before_midnight = fake_now + dt.timedelta(minutes=5)
    monkeypatch.setattr(security, "_now", lambda: still_before_midnight.astimezone(dt.timezone.utc))
    resp_ok = client.get("/api/admin/analytics/users/total", headers=headers)
    assert resp_ok.status_code == 200

    # THEN: pasada la medianoche local -> 401
    after_midnight = fake_now + dt.timedelta(hours=1)
    monkeypatch.setattr(security, "_now", lambda: after_midnight.astimezone(dt.timezone.utc))
    resp_expired = client.get("/api/admin/analytics/users/total", headers=headers)
    assert resp_expired.status_code == 401
