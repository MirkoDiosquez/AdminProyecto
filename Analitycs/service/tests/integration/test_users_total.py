"""
T017 — GET /api/admin/analytics/users/total (FR-003).

GIVEN 100 filas en dim_users (mock del repositorio),
WHEN el admin autenticado solicita el total,
THEN la API responde 200 con {"total_users": 100} y 401 sin token.
"""


def test_total_users_con_token_valido(client, mock_repo, admin_token):
    resp = client.get("/api/admin/analytics/users/total", headers=admin_token)
    assert resp.status_code == 200
    assert resp.json() == {"total_users": 100}


def test_total_users_sin_token_401(client, mock_repo):
    resp = client.get("/api/admin/analytics/users/total")
    assert resp.status_code == 401
