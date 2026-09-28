# 📊 Panel de Estado — API de Reportes (`001-reportes-fastapi`)

> Última corrida: **28 de septiembre de 2026** · `pytest tests -q -m "not postgres"`
> **Resultado: ✅ 50 passed, 2 deselected (requieren PostgreSQL real)**

Este documento resume el estado de implementación de `tasks.md` y sirve como panel único para
ver rápidamente qué está probado y en qué archivo vive cada test. Se regenera corriendo:

```bash
cd Analitycs/service
source .venv/bin/activate
python -m pytest tests -v -m "not postgres"
```

---

## ✅ Progreso por fase

| Fase | Historia | Estado | Tests |
|---|---|---|---|
| 1 | Setup (deps, conftest, fixtures) | ✅ Completa | — (infraestructura) |
| 2 | Foundational (config, timezone, security, cache, DTOs, main) | ✅ Completa | 3/3 |
| 3 | US1 — Usuarios y actividad (MVP) | ✅ Completa | 18/18 |
| 4 | US2 — Demográficos y engagement | ✅ Completa | 13/13 |
| 5 | US3 — Rankings y comparativas | ✅ Completa | 3/3 |
| 6 | US4 — Documentación Swagger | ✅ Completa | 3/3 |
| 7 | US5 — Ejecutar desde Swagger | ✅ Completa | 3/3 |
| 8 | US6 — Autenticarse desde Swagger | ✅ Completa | incluido en Fase 3 |
| 9 | Polish (invalidación de caché, auditoría) | ✅ Completa | 3/3 |

**Total: 50/50 tests en verde** (+ 2 tests marcados `@pytest.mark.postgres`, pendientes de correr
contra una base de datos real con `tests/fixtures/postgres_fixture.sql` aplicado).

---

## 🧪 Mapa de tests (dónde está cada uno)

### `tests/integration/` — contra la app completa (TestClient + mocks de repo/Redis)

| Archivo | Qué prueba | Tests |
|---|---|---|
| `test_auth.py` | Login admin: válido, password incorrecto, usuario inexistente (401 genérico), validación de campos | 4 |
| `test_auth_guard.py` | Guard de sesión: sin token, token corrupto, token expirado, no expone datos en 401 | 4 |
| `test_auth_test_login.py` | Login de prueba Swagger: válido/inválido, tag `auth-test-only` en OpenAPI, token sirve para endpoints protegidos | 4 |
| `test_session_timezone.py` | Expiración de sesión a medianoche en 2 timezones (UTC, Buenos Aires) | 2 |
| `test_users_total.py` | `GET /users/total` con/sin token | 2 |
| `test_users_active.py` | `GET /users/active` por período (day/week/month/total), 422 si falta `period_key` | 6 |
| `test_screen_time.py` | `GET /screen-time/age-range`: rango válido, `min>max` → 422, negativo → 422, sin datos → `null` | 4 |
| `test_gender.py` | `GET /gender`: 4 categorías, porcentajes suman 100%, 401 sin token | 2 |
| `test_country.py` | `GET /country`: sin filtro, con filtro válido, país inexistente → 0 | 3 |
| `test_registration_period.py` | `GET /registration-period`: buckets correctos, usa tz del header (no UTC fijo) | 2 |
| `test_tasks_summary.py` | `GET /tasks/summary`: filtro `not-completed` real, status inválido → 422 | 2 |
| `test_top5_apps.py` | `GET /apps/top5`: shape labels/values, exactamente 5 ítems | 1 |
| `test_challenges_summary.py` | `GET /challenges/summary`: promedio general ≠ completadas, sin token → 401 | 2 |
| `test_openapi_schema.py` | `/openapi.json`: incluye los 13 endpoints + auth, códigos de error documentados, tags presentes | 3 |
| `test_try_it_out.py` | Simulación "Try it out": 401 sin auth, 422 con params inválidos, 200 con token válido | 3 |
| `test_internal_invalidate.py` | `POST /internal/cache/invalidate-reports`: sin secreto, secreto incorrecto, correcto → 204 + borra claves | 3 |

### `tests/unit/` — funciones aisladas

| Archivo | Qué prueba | Tests | Requiere |
|---|---|---|---|
| `test_analytics_cache.py` | `cached()`: cache-hit no invoca loader, cache-miss persiste con TTL, fail-open si Redis falla | 3 | Nada (FakeRedis) |
| `test_analytics_repository_gender.py` | `users_by_gender()` agrupa "otro"/`NULL` como "sin dato" | 1 | 🐘 PostgreSQL real |
| `test_analytics_repository_top5.py` | Desempate alfabético estable entre llamadas repetidas | 1 | 🐘 PostgreSQL real |

### `tests/fixtures/`

| Archivo | Contenido |
|---|---|
| `postgres_fixture.sql` | Dataset mínimo: géneros fuera de catálogo, apps empatadas, tareas no-`completed` con valor distinto de `pending`, países/edades variados |

### `tests/conftest.py` — fixtures compartidas

- `fake_redis` — doble de prueba en memoria (get/set/delete/scan + simulación de fallas).
- `mock_repo` — parchea `AnalyticsRepository` con valores conocidos (sin depender de PostgreSQL).
- `client` — `TestClient` de FastAPI listo para usar.
- `admin_token` / `test_admin_credentials` — helpers de autenticación para tests protegidos.

---

## ▶️ Cómo correr los tests vos mismo

```bash
cd Analitycs/service
source .venv/bin/activate

# Rápido, sin infraestructura (usa mocks/FakeRedis) — recomendado en el día a día
python -m pytest tests -v -m "not postgres"

# Completo, incluyendo los 2 tests que requieren PostgreSQL real con el fixture aplicado
psql -h localhost -U analytics_user -d test_db -f tests/fixtures/postgres_fixture.sql
python -m pytest tests -v
```

---

## 🌐 Swagger UI / OpenAPI

Con el servidor corriendo (`uvicorn app.main:app --reload --port 8000`):

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
- Health check: http://localhost:8000/health

**Credenciales de desarrollo local** (`.env`, solo para este entorno, nunca producción):

| Login | Usuario | Password |
|---|---|---|
| `POST /api/admin/auth/login` (definitivo) | `admin` | `Admin12345` |
| `POST /api/admin/auth/test-login` (solo pruebas) | `tester` | `Tester12345` |

Flujo sugerido en Swagger UI:
1. Ejecutar `POST /api/admin/auth/test-login` con "Try it out".
2. Copiar el `access_token` de la respuesta.
3. Click en **Authorize** (candado, arriba a la derecha), pegar `Bearer <token>`.
4. Ejecutar cualquier endpoint del tag `analytics` — debería responder `200`.
5. Sin token, cualquiera de esos endpoints responde `401`.

> Nota: como no hay PostgreSQL/Redis reales corriendo en este entorno, los reportes que consultan
> la base de datos devolverán error de conexión al ejecutarlos (fail-open de caché, pero
> PostgreSQL sigue siendo la fuente de verdad). El login, el guard de sesión y la documentación
> se pueden probar igual sin infraestructura externa.
