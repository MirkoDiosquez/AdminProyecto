"""
T025 — GET /screen-time/age-range (FR-005, FR-019, data-model.md AgeRangeQuery).
"""


def test_rango_valido_devuelve_promedio(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/screen-time/age-range",
        params={"min_age": 18, "max_age": 25},
        headers=admin_token,
    )
    assert resp.status_code == 200
    assert resp.json()["avg_minutes"] == 25.5


def test_min_mayor_que_max_devuelve_422(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/screen-time/age-range",
        params={"min_age": 30, "max_age": 10},
        headers=admin_token,
    )
    assert resp.status_code == 422


def test_min_age_negativo_devuelve_422(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/screen-time/age-range",
        params={"min_age": -1, "max_age": 10},
        headers=admin_token,
    )
    assert resp.status_code == 422


def test_rango_sin_datos_devuelve_null_no_error(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/screen-time/age-range",
        params={"min_age": 90, "max_age": 99},
        headers=admin_token,
    )
    assert resp.status_code == 200
    assert resp.json()["avg_minutes"] is None
