# Implementation Plan: API de Reportes y Documentación Interactiva para el Panel de Administración

**Branch**: `001-reportes-fastapi` | **Fecha**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-reportes-fastapi/spec.md`

**Constitución**: [constitution.md](../../.specify/memory/constitution.md) v1.0.0

## 1. Resumen del enfoque

Este plan cubre exclusivamente el módulo `reportes-fastapi` (Área C): una API FastAPI de **solo
lectura** que expone 13 reportes agregados sobre PostgreSQL (poblado por un ETL externo), protegida
por una autenticación de administrador propia (cuenta única, credenciales en variables de entorno),
servida a través de una **capa de caché Redis read-through** con invalidación post-ETL, y totalmente
documentada/ejecutable desde **Swagger UI/OpenAPI** (incluyendo un login de prueba temporal para
Swagger, separado del login definitivo).

El enfoque técnico es **evolutivo, no de reescritura**: la estructura de capas (`routers` →
`services` → `repositories` → `db`/`cache`) ya existe en `service/app/` y ya sigue el patrón
correcto (router sin SQL, service coordina cache+repo, repository encapsula SQL). El plan por lo
tanto se centra en:

1. Cerrar las **discrepancias conocidas** documentadas en `spec.md` entre el código actual y los
   requisitos (timezone fija, género dinámico, filtro de tareas, desempate top-5, validaciones
   422, formato `labels/values`).
2. Agregar lo que **no existe todavía**: autenticación de administrador (FR-001/002/020),
   dependency centralizada de auth, endpoint de login (definitivo + de prueba para Swagger),
   configuración de entorno para exponer/ocultar Swagger (FR-032), y el contrato OpenAPI completo.
3. Formalizar la **estrategia de zona horaria del cliente** (FR-002/021), hoy ausente por completo
   en el código (no hay ningún mecanismo para que el cliente comunique su zona horaria).

No se modifica PostgreSQL, Redis (como producto), Firestore, ni el proceso ETL. No se crea
frontend. No se implementa código en esta fase — este plan es la entrada de `/speckit-tasks` y
`/speckit-implement`.

## 2. Constitution Check

*GATE: Debe aprobarse antes de investigar detalles (Fase 0) y se re-verifica tras el diseño
(Fase 1).*

| Principio | Chequeo | Estado |
|---|---|---|
| I. Arquitectura en Capas Independientes | El Panel Admin (vía esta API) solo lee PostgreSQL, nunca Firestore en tiempo real (FR-017). No hay comunicación con RabbitMQ/FCM desde este módulo. | ✅ Cumple |
| II. Offline-First para lo Personal | No aplica: este módulo es 100% interno/admin, siempre online (declarado explícitamente en `spec.md`). | ✅ N/A explícito |
| III. Backend como Única Fuente de Verdad (Anti-Trampa) | No aplica directamente (no hay pase de emergencia ni contadores de usuario final en este módulo); los agregados siempre se recalculan desde PostgreSQL en cache-miss, nunca se confía en un valor de cliente. | ✅ Cumple |
| IV. Modelado de Datos Consistente y Documentado | No se modifica el esquema; timestamps epoch ms y fechas `TEXT 'YYYY-MM-DD'` ya son la convención de `postgre.sql` y se preservan en todos los cálculos. Los ajustes de configuración de este módulo (TTLs, flags) se documentan en `research.md`/`quickstart.md`, no como nuevas tablas. | ✅ Cumple |
| V. Seguridad, Privacidad y Manejo de Errores | El backend nunca maneja contraseñas de usuarios finales (solo la cuenta única de admin, hasheada). Autenticación centralizada en una única dependency FastAPI (no repetida por endpoint, ver §5). Respuestas JSON consistentes, sin stack traces (FR-018). | ✅ Cumple (a implementar) |
| VI. Testing Riguroso en Puntos de Integración | Se planifica testing de integración en el punto de contacto crítico: endpoint con JWT/token inválido → 401 (ver §11). No se introduce ningún framework de testing nuevo sin justificar (se usa `pytest`, ya implícito en el stack Python/FastAPI). | ✅ Cumple |
| VII. Flujo Spec-Kit Obligatorio y Decisiones Cerradas | Este plan sigue a `/speckit-specify` + `/speckit-clarify` ya ejecutados sobre `spec.md`. No contradice ninguna decisión cerrada (Firebase Auth/Firestore es de usuarios finales, no de este módulo; el Panel Admin lee siempre PostgreSQL). | ✅ Cumple |

**⚠️ Contradicción señalada (no resuelta unilateralmente)**: la Constitución (Principio V) exige que
"el JWT emitido por Firebase Auth se valida en un único punto centralizado del backend". Ese
principio está redactado pensando en el **Backend propio** (Área B) que sí usa JWT de Firebase para
usuarios finales. La cuenta de administrador de este módulo (Área C) **no es un usuario final** y,
según `spec.md` (FR-020, decisión cerrada de la Constitución: "Firebase como proveedor de
Auth/Firestore/FCM, no se programa un reemplazo propio"), usa credenciales propias en variables de
entorno, no Firebase Auth. Esto **no contradice** la decisión cerrada porque esa decisión aplica al
sistema de autenticación de usuarios finales de la app, no a la cuenta interna y única del Panel
Admin — pero se señala explícitamente aquí, tal como exige el Principio VII, para que quede
registrado y no se interprete como que este módulo "reemplaza Firebase Auth". Si el equipo
considera que esto necesita una aclaración formal en la Constitución, se recomienda una enmienda
PATCH que aclare que Firebase Auth aplica a usuarios finales, no a la cuenta interna de admin.

**Resultado**: ✅ Sin violaciones que requieran `Complexity Tracking`.

## 3. Arquitectura propuesta

Se mantiene la arquitectura ya existente en `Analitycs/service/app/`, reforzando la separación de
responsabilidades exigida:

```text
Panel Admin (React, fuera de alcance)
        │  HTTPS + Bearer token
        ▼
┌───────────────────────────────────────────────────────────────┐
│ FastAPI app (main.py)                                         │
│  - CORS, OpenAPI/Swagger config (FR-023, FR-032)               │
│  - Manejador global de excepciones (FR-018)                    │
│                                                                 │
│  routers/                                                       │
│   ├── auth_router.py        (NUEVO: login definitivo + prueba)  │
│   └── analytics_router.py   (13 endpoints, sin SQL/lógica)      │
│         depends(require_admin_session)  ← auth centralizada     │
│                                                                 │
│  services/                                                      │
│   ├── auth_service.py       (NUEVO: emitir/validar sesión)      │
│   └── analytics_service.py  (coordina cache + repo, sin SQL)    │
│                                                                 │
│  cache/analytics_cache.py   (ya existe: cached/invalidate*)     │
│  db/redis_client.py, db/postgres.py  (ya existen)               │
│  repositories/analytics_repository.py (SQL puro, ya existe)     │
│  core/timezone.py           (NUEVO: resolver tz del cliente)     │
│  core/security.py           (NUEVO: hash/verify password, token) │
│  config.py                  (ampliar: admin creds, tz, entorno) │
└───────────────────────────────────────────────────────────────┘
        │
        ▼ solo lectura
   PostgreSQL (dim_*/fact_*, ya poblado por ETL externo)
```

**Decisión de estructura**: se **reutiliza** la estructura de carpetas ya presente (`routers`,
`services`, `repositories`, `db`, `cache`, `dto`) — es la Opción "single project" del
`plan-template`, adaptada a un servicio FastAPI ya existente. Se agregan solo los módulos nuevos
estrictamente necesarios (`auth_router.py`, `auth_service.py`, `core/timezone.py`,
`core/security.py`) sin introducir un patrón arquitectónico distinto.

## 4. Estructura de componentes

| Capa | Responsabilidad | Regla dura |
|---|---|---|
| `routers/*_router.py` | Definir rutas, parsear query params vía Pydantic/`Query`, declarar `Depends(require_admin_session)` en endpoints protegidos, delegar 100% al service. | Cero SQL, cero lógica de negocio, cero acceso directo a Redis. |
| `services/analytics_service.py` | Orquestar cache-aside (`cached()`), construir claves de cache, aplicar reglas de negocio no expresables en SQL (ej. mapeo de período → rango de fechas usando tz del cliente). | No abre conexiones a PostgreSQL directamente; usa `repositories`. |
| `services/auth_service.py` (nuevo) | Verificar credenciales contra hash, emitir token de sesión, calcular expiración a medianoche según tz del cliente, validar token. | No persiste sesiones en PostgreSQL (no hay tabla de admins). |
| `repositories/analytics_repository.py` | Toda consulta SQL agregada (`COUNT`/`AVG`/`GROUP BY`/`FILTER`) contra `dim_*`/`fact_*`. | Solo lectura; ninguna sentencia `INSERT`/`UPDATE`/`DELETE`. |
| `cache/analytics_cache.py` | `cached()`, `invalidate()`, `invalidate_pattern()` ya existentes; se reutilizan tal cual. | Única puerta de entrada a Redis para reportes. |
| `core/security.py` (nuevo) | Dependency `require_admin_session` (FastAPI `Depends`), hash/verify de password, generación/validación de token firmado. | Único punto de validación de sesión; no se repite lógica de auth por endpoint. |
| `core/timezone.py` (nuevo) | Resolver la zona horaria vigente del cliente/admin a partir de la solicitud (header propuesto, ver §8), calcular "medianoche" y límites de período en esa tz. | Ninguna capa usa `datetime.now(UTC)` fijo para lógica de negocio de reportes/sesión. |
| `dto/analytics_dto.py` | Modelos Pydantic de request/response, incluyendo el shape `labels`/`values`. | Es el contrato que valida FastAPI y alimenta OpenAPI. |
| `config.py` | Variables de entorno: credenciales admin, credenciales de prueba Swagger, TTLs, flag de entorno/docs. | Nunca hardcodear secretos (ya es la convención existente). |

## 5. Flujo de autenticación

1. **Login definitivo** (`POST /api/admin/auth/login`, FR-001/002/020): recibe `username`,
   `password` y la zona horaria del cliente (ver §8). `auth_service` compara contra
   `ADMIN_USERNAME`/`ADMIN_PASSWORD_HASH` (variables de entorno). Si coincide, emite un token
   (ver "Estrategia de token" en `research.md`) cuya expiración es **la próxima medianoche en la
   tz recibida**, codificada dentro del propio token (no hay estado server-side ni tabla).
2. **Login de prueba Swagger** (`POST /api/admin/auth/test-login`, FR-031): mismo mecanismo, pero
   valida contra `TEST_ADMIN_USER`/`TEST_ADMIN_PASSWORD` (variables de entorno separadas),
   claramente tageado `"test-only"` en OpenAPI. Emite el **mismo tipo de token** (mismo formato,
   misma validación), de forma que `require_admin_session` no necesita distinguir el origen.
3. **Autorización por request**: todo endpoint de `analytics_router` declara
   `Depends(require_admin_session)`. Esta dependency:
   - Extrae el token del header `Authorization: Bearer <token>`.
   - Si falta o es inválido/corrupto → `401`.
   - Si es válido pero su expiración (medianoche en la tz con la que se emitió) ya pasó → `401`.
   - Si es válido → deja pasar la request (no expone datos de sesión adicionales; no hay roles).
4. **Swagger UI**: el esquema de seguridad OpenAPI (`HTTPBearer`) permite cargar el token vía el
   botón **Authorize** una sola vez; Swagger UI adjunta el header automáticamente en cada "Try it
   out" posterior (FR-005/027).

Diagrama simplificado:

```text
Admin/QA → POST /auth/login (o /auth/test-login) → auth_service.issue_token()
                                                        │
                                            token (expira a medianoche, tz cliente)
                                                        │
Admin/QA → GET /api/admin/analytics/... (Authorization: Bearer <token>)
                                                        │
                                    Depends(require_admin_session) valida
                                                        │
                                     401 si inválido/expirado │ 200 si OK → analytics_service
```

## 6. Flujo de consulta de reportes

Sin cambios conceptuales respecto al patrón ya implementado en `analytics_service.py` /
`analytics_repository.py`; se generaliza así para los 13 reportes:

1. `router` recibe la request, valida/parsea parámetros con Pydantic/`Query` (422 si inválidos,
   antes de tocar cache o PostgreSQL — FR-019).
2. `router` llama a `service.<reporte>(params)`.
3. `service` construye la clave de cache determinística (ver §7) y llama a
   `cached(key, ttl, loader)`.
4. **Cache-hit**: `cached()` deserializa y devuelve sin tocar PostgreSQL.
5. **Cache-miss**: `loader()` invoca a `repository.<consulta>()` (SQL agregado puro), `cached()`
   serializa y guarda en Redis con el TTL correspondiente, y devuelve el valor.
6. `service` da forma final a la respuesta (incluyendo transformar a `{"labels": [...], "values":
   [...]}` para los 5 reportes de gráfico — FR-016).
7. `router` devuelve la respuesta tal cual (sin post-procesar).

## 7. Estrategia Redis

Ver detalle de alternativas evaluadas en `research.md` (§ Redis). Resumen de la estrategia elegida:

- **Claves**: `admin:analytics:<reporte>:<params-normalizados>`, ej.
  `admin:analytics:screen-time:age:18-25`, `admin:analytics:users:active:week:2026-W37`. Los
  parámetros se incluyen **siempre** en la clave, ordenados y normalizados (ej. minúsculas para
  país), para que dos combinaciones de filtro distintas nunca colisionen ni se pisen entre sí
  (evita inconsistencias entre filtros).
- **Cache-hit**: devuelve el JSON deserializado tal cual, **sin** ejecutar ninguna consulta a
  PostgreSQL (ya es el comportamiento de `cached()`).
- **Cache-miss**: ejecuta el `loader` (repository → PostgreSQL), serializa con `json.dumps(...,
  default=str)` (ya maneja `Decimal`/fechas), guarda con `SETEX key ttl value`.
- **TTL por tipo de reporte** (ya parametrizado en `config.py`, se reutiliza y se documenta su
  criterio):
  - `cache_ttl_realtime` (5 min): reportes de alta variabilidad — usuarios activos por día/semana.
  - `cache_ttl_default` (10 min): promedios/conteos de uso, tareas, competencias.
  - `cache_ttl_slow` (15 min): distribuciones que cambian poco — género, país, dispositivo,
    antigüedad, edad promedio.
- **Invalidación post-ETL**: se documenta como **contrato pendiente de confirmar con el equipo del
  ETL** (no se implementa el lado ETL en este feature). El contrato propuesto: el ETL, al finalizar
  su corrida, debe invocar (o publicar un evento que dispare) `invalidate_pattern("admin:analytics:*")`
  ya existente en `cache/analytics_cache.py`. Mecanismo exacto (llamada HTTP interna, script
  compartido, o mensaje) queda como **decisión pendiente**, documentada en §14.
- **Redis no disponible**: se define como comportamiento explícito (no estaba cubierto por
  `spec.md` con este nivel de detalle) — ante error de conexión a Redis, `cached()` debe
  degradar a **fail-open hacia PostgreSQL** (ejecutar el `loader()` directamente y devolver el
  resultado sin cachear), en vez de devolver `500`, priorizando disponibilidad de lectura sobre
  performance. Este comportamiento se documenta como decisión técnica en `research.md` (no está en
  `spec.md`, se marca como tal).
- **Serialización**: JSON plano (`dict`/`list` ya serializables), consistente con lo ya
  implementado; no se introduce un formato binario nuevo.

## 8. Estrategia de zona horaria

**Problema**: hoy no existe ningún mecanismo para que el cliente comunique su zona horaria; el
código usa `datetime.now(dt.timezone.utc)` fijo (discrepancia conocida, FR-021).

**Decisión propuesta** (detalle de alternativas en `research.md`): el cliente (Panel Admin o
Swagger) envía su zona horaria IANA (ej. `America/Argentina/Buenos_Aires`) en:
- Un **header HTTP dedicado**, ej. `X-Client-Timezone`, en cada request a `analytics_router`
  (para filtros de período), y
- Un **campo en el body del login** (`timezone`), para que quede embebido en el token y la
  expiración a medianoche se calcule con la tz vigente **al momento del login** (consistente con
  FR-002, que fija la tz "al momento de la solicitud" de login).

Si el header/campo no se envía, se aplica un **valor por defecto documentado** (ej. `UTC`) — esto
es una decisión de implementación no cerrada por `spec.md`, se marca `NEEDS CLARIFICATION` en
`research.md` para confirmar con el equipo antes de `/speckit-tasks`.

`core/timezone.py` centraliza: parseo/validación del nombre de tz (usando `zoneinfo` de la stdlib
de Python, sin nueva dependencia), cálculo de "medianoche siguiente" en esa tz, y cálculo de
límites de período (día/semana/mes/último N) en esa tz. Tanto `auth_service` (expiración de
sesión) como `analytics_service` (filtros de período) usan este único módulo, evitando duplicar
lógica de tz.

## 9. Estrategia de errores

Formato de error consistente para todos los endpoints:

```json
{
  "detail": "<mensaje descriptivo, sin datos internos>"
}
```

(Se reutiliza el formato nativo de `HTTPException` de FastAPI, ya compatible con Swagger UI y sin
introducir un envelope custom no solicitado por la spec.)

| Código | Cuándo | Responsable |
|---|---|---|
| `401` | Falta header `Authorization`, token inválido/corrupto, o token expirado (medianoche tz cliente). | `core/security.py` (dependency) |
| `403` | Reservado para un futuro caso de autorización insuficiente (hoy no hay roles distintos; no se usa en v1 salvo que surja un caso real). | N/A en v1 |
| `422` | Parámetros de filtro inválidos (`min_age > max_age`, edad negativa, `period_key` faltante/mal formado, `status` no soportado, país vacío inválido, etc.) — validado **antes** de tocar cache/PostgreSQL, preferentemente vía tipos Pydantic (`Query(..., ge=0)`, validadores) en vez de checks manuales dispersos. | `routers/*` + `dto/*` (validación declarativa) |
| `500` | Error no controlado (ej. PostgreSQL caído). Manejador global de excepciones en `main.py` captura cualquier excepción no prevista y devuelve `{"detail": "internal_error"}` sin stack trace. | Manejador global en `main.py` |

Ningún handler expone SQL, nombres de tabla, ni excepción cruda del driver (`psycopg`) o de
`redis-py`.

## 10. Estrategia Swagger/OpenAPI

- Se usa el soporte **nativo de FastAPI** (`app.docs_url`, `app.openapi_url`) — no se genera
  documentación manual ni se agrega una librería adicional.
- **Toggle por entorno** (FR-032): `config.py` agrega `environment: str = "development"` (o
  `enable_docs: bool`). En `main.py`, si el entorno no es de desarrollo/QA, `docs_url` y
  `openapi_url` se instancian como `None` (comportamiento seguro-por-defecto: oculto salvo que se
  indique explícitamente `development`/`qa`).
- **Seguridad en OpenAPI**: se declara un esquema `HTTPBearer` (o `APIKeyHeader` si se prefiere
  cabecera custom) a nivel de `FastAPI(...)`/`APIRouter(...)`, de forma que Swagger UI muestre el
  botón **Authorize** y lo aplique automáticamente a todos los endpoints protegidos (FR-005/027).
- **Login de prueba** (FR-031/010 heredado): se expone en un tag separado, ej. `auth-test-only`,
  con `description` explícita "Solo para pruebas — no usar en producción", para que no se confunda
  con el login definitivo.
- **Ejemplos de respuesta**: cada modelo Pydantic de respuesta (`dto/analytics_dto.py`) declara
  `json_schema_extra`/`Field(..., examples=[...])` para que Swagger muestre un ejemplo realista
  (FR-003/025).
- **Errores 401/422 reales**: como los handlers usan `HTTPException` nativo de FastAPI, Swagger
  UI ya muestra la respuesta real (no hace falta lógica adicional) — se verifica en testing (§11).

## 11. Estrategia de testing

Se usa `pytest` (+ `pytest-asyncio` si se requiere para clientes async) y `httpx`/`TestClient` de
FastAPI para integración — sin introducir frameworks nuevos no justificados.

| Área | Casos mínimos |
|---|---|
| **Autenticación** | login válido → 200 + token; login inválido → 401; endpoint protegido sin header → 401; con token corrupto → 401; con token expirado (mockeando reloj/tz) → 401; expiración exactamente a medianoche en tz del cliente (no UTC) → verificar con al menos 2 tz distintas. |
| **Reportes (13)** | Un test de integración por endpoint verificando: shape de respuesta, código 200 con datos de prueba conocidos, y su/sus edge case(s) específico(s) de `spec.md` (ver tabla en `data-model.md` §"Trazabilidad de reportes"). |
| **Repositorio (PostgreSQL)** | Tests contra una base de test (fixture con datos conocidos, nunca contra datos reales) para cada método de `analytics_repository.py`: `NULL`s excluidos correctamente, `GROUP BY` correcto, desempate determinístico del top-5 (`ORDER BY avg_minutes DESC, app_label ASC`), filtro `status != 'completed'` para "no completadas". |
| **Redis (cache)** | cache-hit no llama al repository (mock/spy); cache-miss sí llama y luego persiste; TTL correcto por tipo de reporte; `invalidate_pattern` borra únicamente las claves con el prefijo esperado; comportamiento fail-open si Redis no responde (§7). |
| **API (integración)** | Para cada uno de los 5 endpoints "para graficar", validar explícitamente el shape `{"labels": [...], "values": [...]}` (FR-016/SC-006); validar 422 en `/screen-time/age-range` con `min_age > max_age` y valores negativos; validar 422 en `/users/active` sin `period_key`. |
| **Swagger/OpenAPI** | Test que carga `/openapi.json` y verifica: los 13 reportes + login(s) están presentes; cada uno tiene al menos un código de respuesta documentado distinto de solo `200`; el esquema de seguridad `HTTPBearer` está declarado. (La ejecución manual de "Try it out" se valida en `quickstart.md`, no es automatizable de forma trivial en CI). |

Regla dura: **ningún test escribe sobre las tablas `dim_*`/`fact_*` de una base real**; los tests
de repositorio usan una base de test aislada (ver `quickstart.md`) poblada con fixtures SQL
mínimas, nunca el dataset de producción.

## 12. Consideraciones de rendimiento

- Todas las consultas de `analytics_repository.py` ya delegan la agregación a SQL (`COUNT`,
  `AVG`, `GROUP BY`, `FILTER`), evitando traer filas a memoria — se mantiene este patrón para
  cualquier reporte nuevo o corregido.
- Índices ya cubiertos por `indexes.sql` para las columnas de filtro/agrupación más usadas:
  `dim_users(country, gender, age, device, registered_at)`, `fact_user_activity(user_id,
  activity_date)`, `fact_app_usage(user_id, usage_date, package_name)`, `fact_challenges(user_id,
  status, ...)`, `fact_tasks(user_id, status, created_at)`. **No se crean índices nuevos**: se
  verificó que cubren los filtros usados por los 13 reportes (edad vía `idx_dim_users_age`, país
  vía `idx_dim_users_country`, género vía `idx_dim_users_gender`, dispositivo vía
  `idx_dim_users_device`, antigüedad vía `idx_dim_users_registered_at`, estado de tareas vía
  `idx_ft_status`).
- Consulta potencialmente costosa a vigilar: `top_five_apps_by_screen_time` (agrupa
  `fact_app_usage` completa por `package_name`); ya tiene índice en `package_name`, aceptable para
  el volumen esperado (decenas/cientos de apps, no millones).
- No hay riesgo de N+1: todas las consultas son de una sola sentencia SQL por reporte (o dos como
  máximo, ej. `tasks_summary` con dos promedios); no se itera en Python para calcular agregados.
- La caché Redis es la principal palanca de performance: en cache-hit el costo es O(1) sobre Redis
  y cero sobre PostgreSQL, crítico para que el Panel Admin pueda refrescar dashboards
  frecuentemente sin sobrecargar la base analítica.
- Tamaño de respuesta esperado: acotado en todos los casos (máximo `~decenas` de buckets/países/
  dispositivos según Supuestos de `spec.md`); no se requiere paginación en esta iteración.

## 13. Riesgos y decisiones

| Riesgo/Decisión | Detalle | Mitigación / Estado |
|---|---|---|
| Mecanismo exacto de comunicar la tz del cliente no está cerrado por `spec.md` | FR-002/021 exigen usar "la tz vigente del cliente" pero delegan el mecanismo a `/plan`. | Propuesto: header `X-Client-Timezone` + campo `timezone` en login (§8). **Confirmar con Panel Admin (frontend) antes de `/implement`.** |
| Formato/estrategia de token de sesión no especificado en detalle por `spec.md` | Solo se exige "credencial de sesión" con expiración a medianoche. | Se define en `research.md` (opciones evaluadas: JWT firmado stateless vs. token opaco + Redis). |
| Invalidación de caché post-ETL depende de un proceso externo a este repo | El "otro equipo" (ver conversación previa) implementa el ETL; este feature solo expone `invalidate_pattern()`. | Documentado como **contrato pendiente** en §7/§14; no se implementa el lado ETL aquí. |
| Comportamiento de Redis caído no estaba en `spec.md` | Se definió fail-open hacia PostgreSQL. | Documentado explícitamente como decisión técnica nueva (no de negocio) en `research.md`. |
| Valor por defecto de tz si el cliente no la envía | No cerrado por `spec.md`. | Marcado `NEEDS CLARIFICATION` en `research.md`; default propuesto `UTC` hasta confirmación. |
| Login de prueba Swagger conviviendo con login definitivo | Ambos emiten el mismo tipo de token; riesgo de confusión de uso en producción. | Mitigado con tag `auth-test-only` + descripción explícita + variables de entorno separadas (FR-031). |

## 14. Dependencias y contratos externos

| Contrato | Con quién | Estado |
|---|---|---|
| Esquema PostgreSQL (`postgre.sql`, `indexes.sql`) | Proceso ETL (otro equipo) | ✅ Confirmado — este feature es estrictamente de solo lectura sobre ese esquema, sin cambios. |
| Invalidación de caché Redis tras cada corrida ETL | Proceso ETL (otro equipo) | ⚠️ **Pendiente de confirmar por escrito**: este feature expone `invalidate_pattern("admin:analytics:*")`, pero *quién* la invoca y *cómo* (llamada HTTP interna protegida, script, mensaje) no está definido. No se implementa el lado ETL en este feature. |
| Envío de la zona horaria del cliente | Panel Admin (React), fuera de este repo | ⚠️ **Pendiente de confirmar**: se propone header `X-Client-Timezone` + campo `timezone` en login; el frontend debe adoptar este contrato. |
| Consumo de los 13 endpoints + login | Panel Admin (React) | Contrato REST completo documentado en `contracts/openapi.yaml` (fuente de verdad para el frontend). |

No se asume ningún contrato adicional no mencionado en `spec.md`.

## 15. Trazabilidad con la spec

| Sección del plan | FR cubiertos | SC cubiertos |
|---|---|---|
| §5 Flujo de autenticación | FR-001, FR-002, FR-020, FR-031 | SC-001, SC-003, SC-007 |
| §6 Flujo de consulta de reportes | FR-003 a FR-016, FR-021 | SC-002, SC-006 |
| §7 Estrategia Redis | FR-022 | SC-008 |
| §8 Estrategia de zona horaria | FR-002, FR-021 | SC-007 |
| §9 Estrategia de errores | FR-018, FR-019 | SC-004 |
| §10 Estrategia Swagger/OpenAPI | FR-023 a FR-030, FR-032 | SC-009, SC-010, SC-011, SC-012 |
| §11 Estrategia de testing | Todos (verificación) | Todos (verificación) |
| §12 Rendimiento | FR-017 (implícito, no degradar por volumen) | — |
| Constitution Check (§2) | FR-017 (no Firestore), FR-020 (no tabla admins) | SC-005 |

Todas las **discrepancias conocidas** listadas en `spec.md` quedan cubiertas por este plan y se
convierten en tareas concretas de corrección en `/speckit-tasks`:

- Timezone fija (UTC) en `users_by_registration_period` → corregida vía `core/timezone.py` (§8).
- Agrupación dinámica de género → corregida vía categorías fijas en el repository (documentado en
  `data-model.md`).
- Falta de filtro de estado en `tasks_summary` → corregida vía parámetro de filtro (§6, FR-009).
- Mapeo `not-completed → pending` → corregido a `status != 'completed'` (§6).
- Falta de desempate en top-5 → corregido con `ORDER BY avg_minutes DESC, app_label ASC` (§12).
- Validación de edad y `period_key` faltantes → corregidas vía validación declarativa Pydantic
  antes de tocar cache/DB (§9).
- Formato tabla cruda en los 5 endpoints de gráfico → corregido al shape `labels`/`values` (§6,
  FR-016).

## Project Structure

### Documentation (this feature)

```text
specs/001-reportes-fastapi/
├── plan.md              # Este archivo
├── research.md          # Fase 0 — decisiones técnicas
├── data-model.md         # Fase 1 — modelo de lectura + estructuras Redis
├── quickstart.md         # Fase 1 — cómo levantar/probar localmente
├── contracts/
│   └── openapi.yaml      # Fase 1 — contrato OpenAPI completo
└── checklists/
    └── requirements.md    # Ya existente
```

### Source Code (repository root, dentro de `Analitycs/`)

```text
service/
├── app/
│   ├── main.py                       # Ajustar: toggle docs por entorno, exception handler global
│   ├── config.py                     # Ampliar: admin creds, test creds, environment, tz default
│   ├── core/                         # NUEVO paquete
│   │   ├── security.py               # require_admin_session, hash/verify password, token
│   │   └── timezone.py               # Resolver tz cliente, medianoche, límites de período
│   ├── routers/
│   │   ├── auth_router.py            # NUEVO: /auth/login, /auth/test-login
│   │   └── analytics_router.py       # Ajustar: Depends(require_admin_session), validación 422
│   ├── services/
│   │   ├── auth_service.py           # NUEVO
│   │   └── analytics_service.py      # Ajustar: tz cliente, filtros, shape labels/values
│   ├── repositories/
│   │   └── analytics_repository.py   # Ajustar: género fijo, tasks status, desempate top-5
│   ├── dto/
│   │   └── analytics_dto.py          # Ampliar: modelos de request/response con ejemplos
│   ├── cache/analytics_cache.py       # Sin cambios de contrato (ya cumple §7)
│   └── db/{postgres,redis_client}.py  # Sin cambios de contrato
└── tests/                             # NUEVO
    ├── unit/
    ├── integration/
    └── fixtures/
```

**Structure Decision**: proyecto único (FastAPI service ya existente en `Analitycs/service/`); se
extiende con un paquete `core/` para autenticación y zona horaria, y con `tests/` (hoy inexistente).
No se introduce una segunda app ni un monorepo adicional; no aplica la opción "Web application"
(el frontend Panel Admin vive en otro repo, fuera de este alcance) ni "Mobile + API".

## Complexity Tracking

*Sin violaciones del Constitution Check que requieran justificación.*
