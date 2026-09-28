"""
Fixtures compartidas para toda la suite de tests (T002).

Notas de diseño:
- No requiere PostgreSQL/Redis reales corriendo: se usa un Redis "fake" en memoria
  (misma interfaz que `redis.Redis`: get/set/delete/scan) y se monkeypatchean los
  metodos de `AnalyticsRepository` con valores conocidos derivados del fixture
  descripto en `tests/fixtures/postgres_fixture.sql`, para que los tests sean
  F.I.R.S.T. (rapidos, independientes, repetibles) sin infraestructura externa.
- Las variables de entorno requeridas por `app.config.Settings` (T005) se fijan
  ANTES de importar cualquier modulo de `app`, porque `settings = Settings()` se
  ejecuta al importar el modulo.
- Password de test: "SuperSecreta123" hasheada con bcrypt a demanda si `bcrypt`
  ya esta instalado (T001); si no, se usa un valor dummy y los tests de login
  quedaran en RED hasta que exista `core.security.hash_password` (esperado en TDD).
"""
import os
import sys
import time
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "SuperSecreta123"
TEST_ADMIN_USER = "tester"
TEST_ADMIN_PASSWORD = "TestSuperSecreta123"
INTERNAL_SECRET = "internal-secret-for-tests"


def _bcrypt_hash(raw: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        return "dummy-hash-bcrypt-not-installed"


os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("ADMIN_USERNAME", ADMIN_USERNAME)
os.environ.setdefault("ADMIN_PASSWORD_HASH", _bcrypt_hash(ADMIN_PASSWORD))
os.environ.setdefault("TEST_ADMIN_USER", TEST_ADMIN_USER)
os.environ.setdefault("TEST_ADMIN_PASSWORD", TEST_ADMIN_PASSWORD)
os.environ.setdefault("DEFAULT_CLIENT_TIMEZONE", "UTC")
os.environ.setdefault("ETL_CACHE_INVALIDATION_SECRET", INTERNAL_SECRET)

import pytest
import fnmatch


class FakeRedis:
    """Doble de prueba (Stub) en memoria con la interfaz minima usada por
    `app.cache.analytics_cache` (get/set/delete/scan). Permite simular
    cache-hit/miss y fallas de conexion sin depender de un Redis real."""

    def __init__(self):
        self._store = {}
        self.raise_on_call = False

    def get(self, key):
        if self.raise_on_call:
            raise ConnectionError("redis down (simulado)")
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and expires_at < time.time():
            del self._store[key]
            return None
        return value

    def set(self, key, value, ex=None):
        if self.raise_on_call:
            raise ConnectionError("redis down (simulado)")
        expires_at = time.time() + ex if ex else None
        self._store[key] = (value, expires_at)

    def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)

    def scan(self, cursor=0, match="*", count=200):
        matched = [k for k in self._store.keys() if fnmatch.fnmatch(k, match)]
        return 0, matched


@pytest.fixture
def fake_redis(monkeypatch):
    """Reemplaza `app.db.redis_client.get_redis` por un FakeRedis limpio por test
    (Independent — I de F.I.R.S.T.)."""
    from app.db import redis_client
    instance = FakeRedis()
    monkeypatch.setattr(redis_client, "get_redis", lambda: instance)
    # Tambien parcheamos la referencia ya importada dentro de analytics_cache.
    from app.cache import analytics_cache
    monkeypatch.setattr(analytics_cache, "get_redis", lambda: instance)
    return instance


@pytest.fixture
def mock_repo(monkeypatch):
    """Monkeypatchea `analytics_repository` (singleton) con valores conocidos
    equivalentes al fixture SQL, para tests de integracion que no dependen de
    PostgreSQL real. Devuelve el propio repo ya parcheado por si un test
    necesita sobreescribir un metodo puntual."""
    from app.repositories.analytics_repository import analytics_repository as repo

    monkeypatch.setattr(repo, "total_users", lambda: 100)
    monkeypatch.setattr(repo, "active_users", lambda period, period_key: 30)
    monkeypatch.setattr(repo, "active_users_total", lambda: 42)
    monkeypatch.setattr(
        repo, "average_screen_time_by_age_range",
        lambda min_age, max_age: (25.5 if (min_age, max_age) == (18, 25) else None),
    )
    monkeypatch.setattr(
        repo, "top_five_apps_by_screen_time",
        lambda: [
            {"package_name": "com.e", "app_label": "Epsilon", "avg_minutes": 50.0},
            {"package_name": "com.f", "app_label": "Zeta", "avg_minutes": 50.0},
            {"package_name": "com.d", "app_label": "Delta", "avg_minutes": 40.0},
            {"package_name": "com.c", "app_label": "Gamma", "avg_minutes": 30.0},
            {"package_name": "com.b", "app_label": "Beta", "avg_minutes": 20.0},
            {"package_name": "com.a", "app_label": "Alpha", "avg_minutes": 10.0},
        ][:5],
    )
    monkeypatch.setattr(repo, "total_challenges", lambda: 4)
    monkeypatch.setattr(repo, "average_challenges_per_user", lambda: 2.0)
    monkeypatch.setattr(repo, "average_completed_challenges_per_user", lambda: 1.0)
    monkeypatch.setattr(repo, "average_tasks_per_user", lambda: 1.5)
    monkeypatch.setattr(repo, "average_completed_tasks_per_user", lambda: 0.5)
    monkeypatch.setattr(
        repo, "average_not_completed_tasks_per_user", lambda: 1.0, raising=False
    )
    monkeypatch.setattr(
        repo, "users_by_device",
        lambda: [{"device": "android", "count": 3}, {"device": "ios", "count": 2}],
    )
    monkeypatch.setattr(
        repo, "users_by_registration_period",
        lambda since_ms, until_ms: [{"bucket": "2026-09", "count": 5}],
    )
    monkeypatch.setattr(repo, "average_user_age", lambda: 28.0)
    monkeypatch.setattr(
        repo, "users_by_gender",
        lambda: [
            {"gender": "Hombre", "count": 1, "percentage": 20.0},
            {"gender": "Mujer", "count": 1, "percentage": 20.0},
            {"gender": "No binario", "count": 1, "percentage": 20.0},
            {"gender": "sin dato", "count": 2, "percentage": 40.0},
        ],
    )
    monkeypatch.setattr(
        repo, "users_by_country",
        lambda country_filter=None: (
            [{"country": "Argentina", "count": 2, "percentage": 40.0}]
            if country_filter == "Argentina"
            else (
                [{"country": None, "count": 0, "percentage": 0.0}]
                if country_filter == "PaisInexistente"
                else [
                    {"country": "Argentina", "count": 2, "percentage": 40.0},
                    {"country": "Brasil", "count": 1, "percentage": 20.0},
                    {"country": "Chile", "count": 1, "percentage": 20.0},
                    {"country": None, "count": 1, "percentage": 20.0},
                ]
            )
        ),
    )
    return repo


@pytest.fixture
def app_instance(fake_redis):
    from app.main import app
    return app


@pytest.fixture
def client(app_instance):
    from fastapi.testclient import TestClient
    with TestClient(app_instance) as c:
        yield c


@pytest.fixture
def admin_credentials():
    return {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD, "timezone": "UTC"}


@pytest.fixture
def test_admin_credentials():
    return {"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASSWORD, "timezone": "UTC"}


@pytest.fixture
def admin_token(client, admin_credentials):
    """Hace login real contra el endpoint (una vez implementado, T019/T020) y
    devuelve el header Authorization listo para usar."""
    resp = client.post("/api/admin/auth/login", json=admin_credentials)
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
