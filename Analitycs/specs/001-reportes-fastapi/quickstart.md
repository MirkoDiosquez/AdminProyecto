# Quickstart: API de Reportes (`001-reportes-fastapi`)

Guía mínima para levantar y probar localmente el servicio `Analitycs/service` una vez implementado
este feature. No incluye credenciales reales — reemplazar los placeholders antes de usar.

## 1. Requisitos previos

- Python 3.11+ (según `requirements.txt` del servicio).
- PostgreSQL con el esquema de `Analitycs/postgre.sql` + `Analitycs/indexes.sql` ya aplicado
  (poblado por el ETL externo, o con datos de prueba mínimos para desarrollo — ver §4).
- Redis corriendo localmente (ej. vía `docker-compose.yml` ya presente en `Analitycs/`).

## 2. Variables de entorno (`.env`)

Crear `Analitycs/service/.env` (nunca commitear valores reales) con, como mínimo:

```dotenv
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=anti_procrastinacion
POSTGRES_USER=analytics_user
POSTGRES_PASSWORD=<reemplazar>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Entorno / Swagger (FR-032)
ENVIRONMENT=development   # development|qa habilitan Swagger UI; cualquier otro valor lo oculta

# Autenticación de administrador (FR-020) — NUNCA hardcodear en código
ADMIN_USERNAME=<reemplazar>
ADMIN_PASSWORD_HASH=<hash-bcrypt-o-similar>

# Login de prueba EXCLUSIVO para Swagger (FR-031) — separado del anterior
TEST_ADMIN_USER=<reemplazar>
TEST_ADMIN_PASSWORD=<reemplazar>

# Zona horaria por defecto si el cliente no envía X-Client-Timezone (resuelto en clarify: UTC)
DEFAULT_CLIENT_TIMEZONE=UTC

# Secreto compartido para el endpoint interno de invalidación de caché (llamado por el ETL)
ETL_CACHE_INVALIDATION_SECRET=<reemplazar>
```

## 3. Levantar el servicio

```bash
cd Analitycs/service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health check: `GET http://localhost:8000/health` → `{"status": "ok"}`.
- Swagger UI (solo si `ENVIRONMENT=development` o `qa`): `http://localhost:8000/docs`.
- OpenAPI JSON: `http://localhost:8000/openapi.json`.

## 4. Datos de prueba mínimos (opcional, para desarrollo local)

Si no se dispone del ETL corriendo, se puede insertar un dataset mínimo manualmente contra una
base de desarrollo (nunca contra producción) siguiendo el esquema de `postgre.sql`, por ejemplo
unos pocos `dim_users` con distintas combinaciones de `gender`/`country`/`age`/`device`, y algunas
filas en `fact_user_activity`/`fact_app_usage`/`fact_challenges`/`fact_tasks` asociadas.

## 5. Probar el flujo completo desde Swagger UI (HU 4, 5, 6)

1. Abrir `http://localhost:8000/docs`.
2. Ejecutar `POST /api/admin/auth/test-login` con "Try it out", usando `TEST_ADMIN_USER` /
   `TEST_ADMIN_PASSWORD` del `.env` y una `timezone` válida (ej.
   `America/Argentina/Buenos_Aires`).
3. Copiar el `access_token` de la respuesta.
4. Click en el botón **Authorize** (candado) en la parte superior de Swagger UI, pegar
   `Bearer <access_token>`.
5. Ejecutar cualquier endpoint bajo el tag `analytics` con "Try it out": debe responder `200` con
   datos reales, sin necesidad de volver a pegar el token.
6. Para verificar `401`: quitar la autorización (botón Authorize → Logout) y volver a ejecutar un
   endpoint protegido; debe responder `401`.
7. Para verificar `422`: ejecutar `GET /api/admin/analytics/screen-time/age-range` con
   `min_age=30&max_age=10`; debe responder `422` con detalle descriptivo.

## 6. Probar la invalidación de caché (simulada, sin ETL real)

Mientras el contrato con el ETL no esté implementado (ver `plan.md` §14), se puede simular
localmente:

```bash
# Verificar cache-hit: ejecutar el mismo reporte dos veces y observar el mismo resultado
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/admin/analytics/users/total

# Forzar invalidación manual (equivalente a lo que haría el ETL) desde una shell de Redis
redis-cli KEYS "admin:analytics:*"
redis-cli --scan --pattern "admin:analytics:*" | xargs -r redis-cli DEL
```

## 7. Ejecutar los tests

```bash
cd Analitycs/service
pytest tests/unit -v
pytest tests/integration -v   # requiere PostgreSQL y Redis de prueba corriendo
```

Nunca apuntar `POSTGRES_DB`/`POSTGRES_HOST` de los tests de integración a una base de producción.

## 8. Notas de seguridad

- No commitear `.env` ni ningún valor real de `ADMIN_PASSWORD_HASH`, `TEST_ADMIN_PASSWORD`, etc.
- `ENVIRONMENT` distinto de `development`/`qa` debe ocultar Swagger UI automáticamente
  (comportamiento seguro por defecto, FR-032) — verificar antes de desplegar a un entorno público.
- El login de prueba (`/auth/test-login`) debe deshabilitarse o eliminarse cuando exista el flujo
  definitivo de autenticación de usuarios finales (ver Supuestos de `spec.md`).
