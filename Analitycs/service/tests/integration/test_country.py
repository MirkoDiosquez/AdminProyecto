"""
T027 — GET /country (FR-015). Sin filtro devuelve todos los paises; con filtro
puntual devuelve conteo + porcentaje sobre el total global; pais inexistente -> 0/0%.
"""


def test_country_sin_filtro_devuelve_todos(client, mock_repo, admin_token):
    resp = client.get("/api/admin/analytics/country", headers=admin_token)
    assert resp.status_code == 200
    body = resp.json()
    labels = body.get("labels") or [c["country"] for c in body.get("items", [])]
    assert "Argentina" in labels and "Brasil" in labels and "Chile" in labels


def test_country_con_filtro_argentina_devuelve_conteo_y_porcentaje(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/country", params={"country": "Argentina"}, headers=admin_token
    )
    assert resp.status_code == 200
    body = resp.json()
    values = body.get("values") or [c["count"] for c in body.get("items", [])]
    percentages = body.get("percentages") or [c["percentage"] for c in body.get("items", [])]
    assert values[0] == 2
    assert percentages[0] == 40.0


def test_country_inexistente_devuelve_cero_sin_error(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/country", params={"country": "PaisInexistente"}, headers=admin_token
    )
    assert resp.status_code == 200
    body = resp.json()
    values = body.get("values") or [c["count"] for c in body.get("items", [])]
    assert values[0] == 0
