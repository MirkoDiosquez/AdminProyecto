"""
T018 — GET /api/admin/analytics/users/active (FR-004).

Cubre period=day|week|month|total, y el edge case 422 (antes 200 con {"error": ...})
cuando falta period_key y period != total (data-model.md ActiveUsersQuery).
"""
import pytest


@pytest.mark.parametrize("period,period_key", [
    ("day", "2026-09-28"),
    ("week", "2026-39"),
    ("month", "2026-09"),
])
def test_active_users_con_period_key_devuelve_conteo(client, mock_repo, admin_token, period, period_key):
    resp = client.get(
        "/api/admin/analytics/users/active",
        params={"period": period, "period_key": period_key},
        headers=admin_token,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_users"] == 30
    assert body["period"] == period


def test_active_users_period_total_no_requiere_period_key(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/users/active", params={"period": "total"}, headers=admin_token
    )
    assert resp.status_code == 200
    assert resp.json()["active_users"] == 42


def test_active_users_sin_period_key_devuelve_422_no_200_con_error_en_body(client, mock_repo, admin_token):
    # Discrepancia conocida corregida: antes devolvia 200 + {"error": ...}
    resp = client.get(
        "/api/admin/analytics/users/active", params={"period": "day"}, headers=admin_token
    )
    assert resp.status_code == 422
    assert "error" not in resp.json() or "detail" in resp.json()


def test_active_users_sin_token_401(client, mock_repo):
    resp = client.get("/api/admin/analytics/users/active", params={"period": "total"})
    assert resp.status_code == 401
