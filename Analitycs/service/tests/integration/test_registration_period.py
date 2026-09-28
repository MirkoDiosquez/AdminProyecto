"""
T028 — GET /registration-period (FR-011, FR-021). Usa la tz del cliente via header
X-Client-Timezone en vez de UTC fijo (discrepancia conocida corregida).
"""
import datetime as dt


def test_registration_period_last_month_devuelve_buckets(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/registration-period",
        params={"period": "last_month"},
        headers={**admin_token, "X-Client-Timezone": "America/Argentina/Buenos_Aires"},
    )
    assert resp.status_code == 200
    body = resp.json()
    labels = body.get("labels") or [b["bucket"] for b in body.get("buckets", [])]
    assert labels == ["2026-09"]


def test_registration_period_usa_tz_del_header_no_utc_fijo(client, mock_repo, admin_token, monkeypatch):
    from app.core import timezone as tzmod

    captured = {}
    original = tzmod.period_bounds_epoch_ms

    def spy(period, tz):
        captured["tz"] = tz
        return original(period, tz)

    monkeypatch.setattr(tzmod, "period_bounds_epoch_ms", spy)

    client.get(
        "/api/admin/analytics/registration-period",
        params={"period": "last_week"},
        headers={**admin_token, "X-Client-Timezone": "America/Argentina/Buenos_Aires"},
    )
    assert str(captured["tz"]) == "America/Argentina/Buenos_Aires"
