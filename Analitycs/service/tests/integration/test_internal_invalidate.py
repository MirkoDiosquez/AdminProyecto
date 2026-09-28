"""
T053 — POST /internal/cache/invalidate-reports (T052, FR-022). Requiere
X-Internal-Secret; con secreto correcto invalida (204) y borra las claves
'admin:analytics:*' de Redis.
"""
from tests.conftest import INTERNAL_SECRET


def test_invalidate_sin_secreto_401(client):
    resp = client.post("/internal/cache/invalidate-reports")
    assert resp.status_code == 401


def test_invalidate_con_secreto_incorrecto_401(client):
    resp = client.post(
        "/internal/cache/invalidate-reports", headers={"X-Internal-Secret": "incorrecto"}
    )
    assert resp.status_code == 401


def test_invalidate_con_secreto_correcto_204_y_borra_claves(client, fake_redis):
    fake_redis.set("admin:analytics:users:total", "100", ex=600)
    fake_redis.set("otra:clave:no-relacionada", "x", ex=600)

    resp = client.post(
        "/internal/cache/invalidate-reports", headers={"X-Internal-Secret": INTERNAL_SECRET}
    )

    assert resp.status_code == 204
    assert fake_redis.get("admin:analytics:users:total") is None
    assert fake_redis.get("otra:clave:no-relacionada") is not None
