# Data Model: API de Reportes (modelo de lectura/proyección)

**Feature**: `001-reportes-fastapi` | **Fecha**: 2026-09-15

Este feature **no modifica el esquema PostgreSQL**. Este documento describe el esquema existente
(`postgre.sql`/`indexes.sql`) desde la perspectiva de **proyección de solo lectura** que consume la
API de reportes, y documenta por separado las estructuras **temporales** que vive en Redis (que
nunca deben confundirse con el modelo de datos de PostgreSQL).

## 1. Entidades PostgreSQL consumidas (solo lectura)

### `dim_users`

| Columna | Tipo | Uso en reportes |
|---|---|---|
| `user_id` | `VARCHAR(128)` PK | Join implícito con todas las tablas `fact_*`. |
| `gender` | `VARCHAR(30)` (libre, puede ser `NULL`) | FR-014: se reagrupa a 3 categorías fijas + "sin dato" **en la capa de servicio/repositorio**, no se asume que el dato crudo ya viene en esas categorías. |
| `age` | `SMALLINT` (puede ser `NULL`) | FR-005 (rango libre), FR-012 (promedio, excluyendo `NULL`). |
| `country` | `VARCHAR(100)` (puede ser `NULL`) | FR-015: filtro puntual o global. |
| `device` | `VARCHAR(150)` (puede ser `NULL`) | FR-010: agrupación simple por valor existente. |
| `registered_at` | `BIGINT` epoch ms (puede ser `NULL`) | FR-011: antigüedad agrupada por bucket temporal, usando la tz del cliente para calcular "última semana/mes/año" (ver `research.md` §2). |

### `fact_user_activity`

| Columna | Uso |
|---|---|
| `user_id`, `activity_date` (`TEXT 'YYYY-MM-DD'`) | FR-004: usuario activo = al menos 1 fila en el rango de período solicitado. La agrupación por semana/mes usa el `activity_date` como fecha pura (no epoch), consistente con el Principio IV de la constitución. |

### `fact_app_usage`

| Columna | Uso |
|---|---|
| `user_id`, `package_name`, `app_label`, `minutes_used` | FR-005 (promedio por rango de edad, join con `dim_users.age`), FR-008/13ero reporte (top 5 apps por promedio, con desempate por `app_label ASC`). |

### `fact_challenges`

| Columna | Uso |
|---|---|
| `user_id`, `status` (`active`/`completed`/`expired`) | FR-006 (promedio general, sin filtro), FR-007 (conteo total), FR-013 (promedio solo `status='completed'`, claramente distinto de FR-006). |

### `fact_tasks`

| Columna | Uso |
|---|---|
| `user_id`, `status` | FR-009: promedio general + promedio filtrado. "No completada" se define como `status != 'completed'` (no un valor literal como `'pending'`), según Clarifications de `spec.md`. |

### `fact_user_groups`

No es consumida por ninguno de los 13 reportes definidos en el alcance actual de `spec.md`; se
documenta su existencia por completitud del esquema, pero **no requiere cambios ni nuevas
consultas** en este feature.

## 2. Reglas de proyección (no son cambios de esquema)

Estas reglas se implementan en `repositories/analytics_repository.py` (SQL) o
`services/analytics_service.py` (post-procesamiento), **nunca** alterando las tablas:

1. **Género fijo (FR-014)**: la consulta SQL debe forzar el agrupamiento vía `CASE WHEN gender IN
   ('Hombre','Mujer','No binario') THEN gender ELSE 'sin dato' END`, en vez de `GROUP BY gender`
   crudo (corrige la discrepancia conocida de `users_by_gender()`).
2. **Tareas no completadas (FR-009)**: el filtro `not-completed` debe traducirse a
   `WHERE status != 'completed'` en SQL, no a un valor fijo `'pending'`.
3. **Desempate top-5 (FR-008 / edge case)**: `ORDER BY avg_minutes DESC, app_label ASC LIMIT 5`.
4. **Exclusión de `NULL` en promedios (FR-012 y en general)**: cualquier `AVG(...)` sobre una
   columna nullable ya excluye `NULL` por semántica estándar de SQL; se documenta explícitamente
   para que no se "corrija" agregando un `COALESCE(age, 0)` que sesgaría el promedio.
5. **Categoría "sin dato" en distribuciones (género, país)**: el denominador del porcentaje sigue
   siendo el total global de `dim_users`, pero el numerador de cada categoría (incluida "sin
   dato") se calcula por separado, de forma que las categorías + "sin dato" sumen 100%.

## 3. Modelos de Request (Pydantic — `dto/analytics_dto.py`)

| Modelo | Campos | Validaciones declarativas |
|---|---|---|
| `LoginRequest` | `username: str`, `password: str`, `timezone: str` (IANA, ej. `America/Argentina/Buenos_Aires`) | `timezone` validado contra `zoneinfo.available_timezones()`. |
| `ActiveUsersQuery` | `period: Literal["day","week","month","total"]`, `period_key: str | None` | Si `period != "total"` y `period_key` es `None` → error de validación (422), reemplazando el actual `return {"error": ...}` con 200. |
| `AgeRangeQuery` | `min_age: int`, `max_age: int` | `ge=0` en ambos; `@model_validator` que exige `min_age <= max_age`. |
| `TasksStatusQuery` | `status: Literal["completed","not-completed","all"] = "all"` | Enum estricto (ya lo era parcialmente). |
| `RegistrationPeriodQuery` | `period: Literal["last_week","last_month","last_3_months","last_year","all"] = "all"` | Enum estricto (ya existente). |
| `CountryQuery` | `country: str | None` | Trim/normalización de mayúsculas/minúsculas antes de consultar. |

## 4. Modelos de Response (Pydantic — contrato de salida)

| Modelo | Shape | Reportes que lo usan |
|---|---|---|
| `TokenResponse` | `{"access_token": str, "token_type": "bearer", "expires_at": <epoch ms>}` | Login definitivo y de prueba. |
| `CountResponse` | `{"<campo>": int}` | Total usuarios, total competencias. |
| `AverageResponse` | `{"<campo>": float | null}` | Promedio edad, promedio competencias/usuario, promedio tiempo pantalla por rango de edad (`null` explícito si no hay datos, nunca `0` engañoso — edge case de `spec.md`). |
| `LabelsValuesResponse` | `{"labels": [...], "values": [...], "percentages"?: [...]}` | Top 5 apps, dispositivos, género, país, antigüedad de registro (FR-016). |
| `TasksSummaryResponse` | `{"avg_tasks_per_user": float|null, "avg_completed_tasks_per_user": float|null, "status_filter": str}` | Reporte de tareas (FR-009). |
| `ErrorResponse` | `{"detail": str}` | Todos los códigos de error (401/422/500). |

## 5. Estructuras temporales en Redis (NO es modelo de datos PostgreSQL)

Redis se usa **exclusivamente** como caché read-through de los resultados ya agregados; no
almacena entidades de negocio ni es fuente de verdad (FR-017, FR-022).

| Clave (patrón) | Valor (JSON serializado) | TTL | Invalidada por |
|---|---|---|---|
| `admin:analytics:users:total` | `int` | `cache_ttl_default` (10 min) | ETL (patrón global) |
| `admin:analytics:users:active:<period>:<period_key>` | `int` | `cache_ttl_realtime` (5 min) | ETL |
| `admin:analytics:screen-time:age:<min>-<max>` | `float \| null` | `cache_ttl_default` | ETL |
| `admin:analytics:apps:top5` | `list[{package_name, app_label, avg_minutes}]` | `cache_ttl_default` | ETL |
| `admin:analytics:challenges:*` | `int \| float` | `cache_ttl_default` | ETL |
| `admin:analytics:tasks:<status_filter>` | `dict` (ver `TasksSummaryResponse`) | `cache_ttl_default` | ETL |
| `admin:analytics:devices` | `LabelsValuesResponse` | `cache_ttl_slow` (15 min) | ETL |
| `admin:analytics:registration-age:<period>` | `LabelsValuesResponse` | `cache_ttl_slow` | ETL |
| `admin:analytics:age:average` | `float \| null` | `cache_ttl_slow` | ETL |
| `admin:analytics:gender` | `LabelsValuesResponse` (con `percentages`) | `cache_ttl_slow` | ETL |
| `admin:analytics:country:<country\|global>` | `LabelsValuesResponse` (con `percentages`) | `cache_ttl_slow` | ETL |

**Invalidación**: todas las claves comparten el prefijo `admin:analytics:`; el proceso de
invalidación post-ETL ejecuta `invalidate_pattern("admin:analytics:*")` (ya implementado en
`cache/analytics_cache.py`), sin necesidad de enumerar cada clave individualmente.

**Nota explícita**: las sesiones de administrador (tokens) **no** se guardan en esta misma
estructura de Redis (ver `research.md` §1, Opción C elegida — JWT-like stateless), precisamente
para que la invalidación masiva de caché de reportes nunca afecte accidentalmente sesiones activas.

## 6. Trazabilidad de reportes (13) → entidad → FR

| # | Reporte | Entidad(es) fuente | FR |
|---|---|---|---|
| 1 | Total de usuarios | `dim_users` | FR-003 |
| 2 | Usuarios activos (día/semana/mes/total) | `fact_user_activity` | FR-004 |
| 3 | Promedio tiempo en pantalla por rango de edad | `fact_app_usage` + `dim_users.age` | FR-005 |
| 4 | Promedio de competencias por usuario | `fact_challenges` | FR-006 |
| 5 | Total de competencias | `fact_challenges` | FR-007 |
| 6 | Top 5 apps por tiempo en pantalla | `fact_app_usage` | FR-008 |
| 7 | Promedio de tareas / tareas completadas por usuario | `fact_tasks` | FR-009 |
| 8 | Usuarios por dispositivo | `dim_users.device` | FR-010 |
| 9 | Usuarios por antigüedad de registro | `dim_users.registered_at` | FR-011 |
| 10 | Promedio de edad | `dim_users.age` | FR-012 |
| 11 | Promedio de desafíos completados por usuario | `fact_challenges` (`status='completed'`) | FR-013 |
| 12 | Distribución por género | `dim_users.gender` | FR-014 |
| 13 | Distribución por país | `dim_users.country` | FR-015 |
