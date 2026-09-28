"""
T015 — Guard de sesion sobre endpoints de reportes (FR-002).

GIVEN un endpoint protegido (GET /api/admin/analytics/users/total),
WHEN se llama sin token / con token corrupto / con token expirado,
THEN responde 401 en los 3 casos, sin exponer datos.
"""
import time


PROTECTED_URL = "/api/admin/analytics/users/total"


def test_sin_token_devuelve_401(client, mock_repo):
    resp = client.get(PROTECTED_URL)
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_token_corrupto_devuelve_401(client, mock_repo):
    resp = client.get(PROTECTED_URL, headers={"Authorization": "Bearer esto-no-es-un-token-valido"})
    assert resp.status_code == 401


def test_token_expirado_devuelve_401(client, mock_repo, admin_token, monkeypatch):
    # GIVEN un token valido ya emitido
    # WHEN simulamos que el tiempo avanzo mas alla del `exp` embebido en el token
    from app.core import security

    original_time = time.time
    monkeypatch.setattr(security.time, "time", lambda: original_time() + 60 * 60 * 24 * 2)

    # THEN
    resp = client.get(PROTECTED_URL, headers=admin_token)
    assert resp.status_code == 401


def test_401_no_expone_datos_del_reporte(client, mock_repo):
    resp = client.get(PROTECTED_URL)
    assert resp.status_code == 401
    assert "total_users" not in resp.text
