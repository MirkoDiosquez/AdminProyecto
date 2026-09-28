"""
T046 — Simulacion de "Try it out" de Swagger UI: requests HTTP reales contra la
app (via TestClient) para un endpoint protegido, verificando que 401/422 se
muestran con el body nativo de FastAPI (sin envelope custom, US5).
"""


def test_try_it_out_sin_authorization_header_401(client, mock_repo):
    resp = client.get("/api/admin/analytics/screen-time/age-range", params={"min_age": 18, "max_age": 25})
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_try_it_out_parametros_invalidos_422(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/screen-time/age-range",
        params={"min_age": 30, "max_age": 10},
        headers=admin_token,
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_try_it_out_con_token_valido_200_datos_reales(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/screen-time/age-range",
        params={"min_age": 18, "max_age": 25},
        headers=admin_token,
    )
    assert resp.status_code == 200
    assert resp.json()["avg_minutes"] == 25.5
