# Analytics / Admin — Persistencia (PostgreSQL + Redis) y API de Reportes

> Módulo: Panel Admin — Área C (Notificaciones + Admin), según `constitution.md` Sección 2.
> Stack real del proyecto para este módulo (ver `Documentos/arquitectura.md` y
> `plan-de-trabajo.txt`): **Python + FastAPI + pandas**, no Spring Boot/Java
> (ese stack es del backend social). Se respetó la decisión existente.

## Arquitectura implementada

```
Firebase / Firestore
        |
        | ETL (idempotente, upsert)
        v
PostgreSQL (anti_procrastinacion)   <- fuente persistente y de respaldo
        |
        v
Redis (cache, TTL 5-15 min)         <- acelera consultas frecuentes
        |
        v
AnalyticsService (Python)
        |
        v
AnalyticsController / FastAPI router
        |
        v
Panel Admin (React) — nunca accede a Firestore ni a Postgres directamente
```

Capas de código (Controller → Service → Repository), en `Analitycs/service/app/`:
- `routers/analytics_router.py` → Controller
- `services/analytics_service.py` → Service + cache read-through
- `cache/analytics_cache.py` → utilidades de cache (get/set/invalidate)
- `repositories/analytics_repository.py` → Repository (SQL puro sobre PostgreSQL)
- `dto/analytics_dto.py` → DTOs de respuesta
- `etl/etl_firestore_to_postgres.py` → ETL idempotente

## 1. Archivos creados

```
Analitycs/
  postgre.sql                 (estaba vacío, esquema completo)
  indexes.sql
  docker-compose.yml
  .env.example
  README.md                   (este archivo)
  service/
    requirements.txt
    app/
      main.py
      config.py
      db/{postgres.py, redis_client.py, __init__.py}
      cache/{analytics_cache.py, __init__.py}
      dto/{analytics_dto.py, __init__.py}
      repositories/{analytics_repository.py, __init__.py}
      services/{analytics_service.py, __init__.py}
      routers/{analytics_router.py, __init__.py}
      etl/{etl_firestore_to_postgres.py, __init__.py}
```

## 2. Archivos modificados

- `ModeloDeDatos/modelo_admin.md` — se agregó nota de amendment (no se borró contenido).
- `ModeloDeDatos/der_admin.md` — se agregó nota de amendment (no se borró contenido).
- `Analitycs/postgre.sql` — estaba vacío, se completó.

Ningún otro archivo del repo (launcher-demo, constitution*, etc.) fue tocado.

## 3. Esquema final de PostgreSQL (`anti_procrastinacion`)

Tablas: `dim_users`, `fact_user_activity`, `fact_app_usage`, `fact_challenges`,
`fact_tasks`, `fact_user_groups`. Ver `Analitycs/postgre.sql` (DDL completo) e
`Analitycs/indexes.sql` (índices).

## 4. Relaciones

```
dim_users (1) ──< fact_user_activity   (N)   [UNIQUE user_id+activity_date]
dim_users (1) ──< fact_app_usage       (N)   [UNIQUE user_id+usage_date+package_name]
dim_users (1) ──< fact_challenges      (N)   [UNIQUE user_id+challenge_id]
dim_users (1) ──< fact_tasks           (N)   [UNIQUE user_id+task_id]
dim_users (1) ──< fact_user_groups     (N)   [UNIQUE user_id+group_id+joined_at]
```

Todas las tablas `fact_*` tienen FK hacia `dim_users(user_id)`.

## 5. Claves usadas en Redis

```
admin:analytics:users:total
admin:analytics:users:active:total
admin:analytics:users:active:day:{YYYY-MM-DD}
admin:analytics:users:active:week:{YYYY-WW}
admin:analytics:users:active:month:{YYYY-MM}
admin:analytics:screen-time:age:{min}-{max}
admin:analytics:apps:top5
admin:analytics:challenges:total
admin:analytics:challenges:average
admin:analytics:challenges:completed-average
admin:analytics:tasks:average
admin:analytics:tasks:completed-average
admin:analytics:tasks:{completed|pending|all}
admin:analytics:devices
admin:analytics:registration-age:{last_week|last_month|last_3_months|last_year|all}
admin:analytics:age:average
admin:analytics:gender
admin:analytics:country:global
admin:analytics:country:{country}
```

TTLs (`app/config.py`): `cache_ttl_realtime`=5 min (usuarios activos),
`cache_ttl_default`=10 min (mayoría de métricas), `cache_ttl_slow`=15 min
(distribuciones demográficas). El ETL invalida `admin:analytics:*` al finalizar.

## 6. Flujo Firebase → ETL → PostgreSQL → Redis → Analytics → Admin

1. `etl_firestore_to_postgres.run_etl()` lee colecciones de Firestore.
2. Hace UPSERT (`ON CONFLICT`) en las 6 tablas → idempotente.
3. Al terminar, invalida `admin:analytics:*` en Redis.
4. El Panel Admin llama a un endpoint (ej. `/api/admin/analytics/users/total`).
5. El Service busca la clave en Redis: HIT → responde directo; MISS → consulta
   `AnalyticsRepository` (PostgreSQL), guarda en Redis con TTL, responde.

## 7. Cómo levantar PostgreSQL y Redis

```bash
cd Analitycs
cp .env.example .env   # ajustar credenciales
docker compose up -d
```

## 8. Ejecutar el esquema manualmente (sin Docker)

```bash
psql -U <user> -h <host> -f Analitycs/postgre.sql
psql -U <user> -h <host> -d anti_procrastinacion -f Analitycs/indexes.sql
```

Con Docker Compose, `postgre.sql` e `indexes.sql` se montan en
`/docker-entrypoint-initdb.d/` y se ejecutan automáticamente en el primer arranque.

Correr la API:
```bash
cd Analitycs/service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Correr el ETL manualmente:
```bash
cd Analitycs/service
python -m app.etl.etl_firestore_to_postgres
```

## 9. Ejemplos de consultas de Analytics (SQL puro, ejecutadas por el Repository)

```sql
-- Top 5 apps por promedio de minutos
SELECT package_name, MAX(app_label), AVG(minutes_used) AS avg_minutes
FROM fact_app_usage GROUP BY package_name ORDER BY avg_minutes DESC LIMIT 5;

-- Porcentaje de usuarios por género
SELECT gender, COUNT(*), ROUND(COUNT(*)*100.0/NULLIF((SELECT COUNT(*) FROM dim_users),0),2)
FROM dim_users GROUP BY gender;
```

## 10. Ejemplos de respuesta JSON

`GET /api/admin/analytics/users/total`
```json
{ "total_users": 1284 }
```

`GET /api/admin/analytics/users/active?period=week&period_key=2026-W36`
```json
{ "period": "week", "period_key": "2026-W36", "active_users": 512 }
```

`GET /api/admin/analytics/apps/top5`
```json
{
  "top_apps": [
    {"package_name": "com.instagram.android", "app_label": "Instagram", "avg_minutes": 63.4},
    {"package_name": "com.zhiliaoapp.musically", "app_label": "TikTok", "avg_minutes": 58.1}
  ]
}
```

`GET /api/admin/analytics/gender`
```json
{ "genders": [
  {"gender": "Hombre", "count": 600, "percentage": 46.7},
  {"gender": "Mujer", "count": 580, "percentage": 45.2},
  {"gender": "Rarito", "count": 60, "percentage": 4.7},
  {"gender": null, "count": 44, "percentage": 3.4}
]}
```

`GET /api/admin/analytics/country?country=Argentina`
```json
{ "country_filter": "Argentina", "items": [
  {"country": "Argentina", "count": 800, "percentage": 62.3}
]}
```

## 11. Decisiones tomadas

- **Stack Python/FastAPI** en lugar de Spring Boot: el proyecto ya decidió esto
  en `plan-de-trabajo.txt` ("Módulo de Reportes: Python · FastAPI"). Se
  respetó la decisión cerrada en lugar de introducir Java donde no corresponde.
- **Esquema alineado a `constitution.md`** (epoch ms / TEXT dates) en vez del
  esquema previo de `modelo_admin.md` (TIMESTAMPTZ/DATE) — ver sección de
  conflictos.
- Clave natural de `fact_user_groups`: `(user_id, group_id, joined_at)` para
  soportar reingresos (un usuario puede abandonar y volver a unirse).
- `gender`/`country`/`device` se mantienen como `VARCHAR` libres (no ENUM) para
  no hardcodear valores, según pedido explícito.
- Redis solo cachea resultados agregados de Analytics; no se usa para sesión,
  colas ni nada que compita con RabbitMQ.

## 12. Conflictos detectados (no resueltos silenciosamente)

1. `ModeloDeDatos/modelo_admin.md` / `der_admin.md` usaban `TIMESTAMPTZ`/`DATE`
   contradiciendo `constitution.md` Sección 3, y no tenían `fact_user_activity`
   ni `fact_tasks`. **Propuesta aplicada**: se agregó nota de amendment en
   ambos archivos señalando que `Analitycs/postgre.sql` es ahora el esquema
   autoritativo; se conserva el contenido original para no romper referencias
   existentes. Se recomienda al equipo ratificar esto formalmente (2
   integrantes, según Sección 10 de `constitution.md`) y luego reescribir esos
   `.md` en limpio.
2. `Analitycs/postgre.sql` estaba vacío y sin dueño claro — se asumió que es el
   lugar correcto para el schema (coincide con el nombre del archivo y la
   carpeta `Analitycs/`).
