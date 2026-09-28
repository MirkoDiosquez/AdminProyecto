"""
T049 — Login de prueba temporal para Swagger (FR-031, US6).

GIVEN TEST_ADMIN_USER/TEST_ADMIN_PASSWORD configurados,
WHEN se hace POST /api/admin/auth/test-login,
THEN con credenciales correctas responde 200 + token; con incorrectas 401;
y el endpoint esta etiquetado como 'auth-test-only' con descripcion que menciona "prueba".
"""
from tests.conftest import TEST_ADMIN_USER, TEST_ADMIN_PASSWORD


def test_test_login_valido_devuelve_token(client, test_admin_credentials):
    resp = client.post("/api/admin/auth/test-login", json=test_admin_credentials)
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_test_login_invalido_devuelve_401(client):
    resp = client.post(
        "/api/admin/auth/test-login",
        json={"username": TEST_ADMIN_USER, "password": "mala", "timezone": "UTC"},
    )
    assert resp.status_code == 401


def test_test_login_tag_y_descripcion_en_openapi(client):
    schema = client.get("/openapi.json").json()
    path_item = schema["paths"]["/api/admin/auth/test-login"]["post"]
    assert path_item["tags"] == ["auth-test-only"]
    assert "prueba" in path_item.get("description", "").lower()


def test_test_login_token_sirve_para_endpoint_protegido(client, mock_repo, test_admin_credentials):
    login_resp = client.post("/api/admin/auth/test-login", json=test_admin_credentials)
    token = login_resp.json()["access_token"]

    resp = client.get(
        "/api/admin/analytics/users/total",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
