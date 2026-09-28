"""
T014 — Login definitivo de administrador (RF-001/002/020).

GIVEN un sistema con ADMIN_USERNAME/ADMIN_PASSWORD_HASH configurados,
WHEN se hace POST /api/admin/auth/login,
THEN con credenciales validas responde 200 + token; con password incorrecto responde 401
sin distinguir si el usuario existe (edge case de spec.md).
"""
from tests.conftest import ADMIN_USERNAME, ADMIN_PASSWORD


def test_login_valido_devuelve_token_200(client, admin_credentials):
    # WHEN
    resp = client.post("/api/admin/auth/login", json=admin_credentials)

    # THEN
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body.get("token_type", "bearer") == "bearer"


def test_login_password_incorrecto_devuelve_401(client):
    resp = client.post(
        "/api/admin/auth/login",
        json={"username": ADMIN_USERNAME, "password": "incorrecta", "timezone": "UTC"},
    )
    assert resp.status_code == 401
    assert "password" not in resp.text.lower() or "detail" in resp.json()


def test_login_usuario_inexistente_devuelve_401_sin_revelar_existencia(client):
    resp_password_mala = client.post(
        "/api/admin/auth/login",
        json={"username": ADMIN_USERNAME, "password": "otra-mala", "timezone": "UTC"},
    )
    resp_usuario_inexistente = client.post(
        "/api/admin/auth/login",
        json={"username": "no-existe", "password": ADMIN_PASSWORD, "timezone": "UTC"},
    )

    # THEN: mismo codigo y mismo mensaje generico en ambos casos (no se revela cual dato es incorrecto)
    assert resp_password_mala.status_code == 401
    assert resp_usuario_inexistente.status_code == 401
    assert resp_password_mala.json() == resp_usuario_inexistente.json()


def test_login_requiere_username_password_timezone(client):
    resp = client.post("/api/admin/auth/login", json={"username": ADMIN_USERNAME})
    assert resp.status_code == 422
