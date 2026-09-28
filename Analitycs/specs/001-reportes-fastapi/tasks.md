# Tasks: API de Reportes y Documentación Interactiva para el Panel de Administración

**Input**: Documentos de diseño de `/specs/001-reportes-fastapi/` (`plan.md`, `spec.md`,
`research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`)

**Prerequisitos**: `plan.md` ✅, `spec.md` ✅ (6 historias de usuario), `research.md` ✅,
`data-model.md` ✅, `contracts/openapi.yaml` ✅, `quickstart.md` ✅

**Tests**: Se incluyen tareas de testing explícitamente, porque el Principio VI de la Constitución
raíz exige tests de integración obligatorios en todo punto de contacto entre módulos (ej. endpoint
con credencial inválida → 401) y `plan.md` §11 define una estrategia de testing detallada.

**Organización**: Las tareas se agrupan por historia de usuario (según prioridad de `spec.md`) para
permitir implementación y prueba independientes de cada una.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias entre sí)
- **[Story]**: A qué historia de usuario pertenece (US1...US6)
- Todas las rutas de archivo son relativas a `Analitycs/service/`

## Convenciones de ruta

Proyecto único ya existente (FastAPI): `Analitycs/service/app/` y `Analitycs/service/tests/`
(nuevo), según `plan.md` §"Project Structure".

---

## Phase 1: Setup (Infraestructura compartida)

**Propósito**: Preparar el proyecto para agregar autenticación, timezone y testing sin romper lo
ya implementado.

- [ ] T001 Agregar `pytest`, `pytest-asyncio`, `httpx` y `bcrypt` (o `passlib[bcrypt]`) a
  `Analitycs/service/requirements.txt`, justificando en un comentario que `bcrypt` es necesario
  para FR-020 (hash de password) y que no se introduce ningún framework de testing/auth adicional
  no justificado (Principio VI).
- [ ] T002 [P] Crear estructura de tests en `Analitycs/service/tests/__init__.py`,
  `Analitycs/service/tests/unit/__init__.py`, `Analitycs/service/tests/integration/__init__.py`,
  `Analitycs/service/tests/fixtures/__init__.py`.
- [ ] T003 [P] Crear `Analitycs/service/.env.example` con todas las variables nuevas documentadas
  en `quickstart.md` (`ENVIRONMENT`, `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, `TEST_ADMIN_USER`,
  `TEST_ADMIN_PASSWORD`, `DEFAULT_CLIENT_TIMEZONE`, `ETL_CACHE_INVALIDATION_SECRET`), sin valores
  reales.
- [ ] T004 [P] Configurar fixture de base de datos de test en
  `Analitycs/service/tests/fixtures/postgres_fixture.sql` con datos mínimos conocidos que cubran
  los 13 reportes (usuarios con `gender`/`age`/`country`/`device`/`registered_at` variados,
  actividad, uso de apps de al menos 6 apps distintas con empate en promedio para probar
  desempate, desafíos con distintos `status`, tareas con distintos `status`).

**Checkpoint**: Proyecto listo para agregar dependencias de negocio (Foundational).

---

## Phase 2: Foundational (Bloqueante para todas las historias)

**Propósito**: Infraestructura núcleo (config, timezone, seguridad, manejo de errores) que
**todas** las historias de usuario necesitan. Ninguna historia puede completarse sin esto.

**⚠️ CRÍTICO**: Ninguna tarea de una historia de usuario puede darse por completa hasta que esta
fase esté terminada.

- [ ] T005 Ampliar `Analitycs/service/app/config.py`: agregar `environment: str = "development"`,
  `admin_username: str`, `admin_password_hash: str`, `test_admin_user: str`,
  `test_admin_password: str`, `default_client_timezone: str = "UTC"`,
  `etl_cache_invalidation_secret: str`, todos leídos vía `pydantic-settings` desde variables de
  entorno (FR-020, FR-031, FR-032, research.md §1/§3).
- [ ] T006 [P] Crear `Analitycs/service/app/core/__init__.py` (paquete nuevo).
- [ ] T007 [P] Crear `Analitycs/service/app/core/timezone.py`: función
  `resolve_client_timezone(header_value: str | None) -> ZoneInfo` (usa `zoneinfo` de la stdlib,
  valida contra `zoneinfo.available_timezones()`, default `settings.default_client_timezone` si es
  `None` o inválida — research.md §2); función `next_midnight_epoch_ms(tz: ZoneInfo) -> int`;
  función `period_bounds_epoch_ms(period: str, tz: ZoneInfo) -> tuple[int, int]` para
  `last_week/last_month/last_3_months/last_year`.
- [ ] T008 [P] Crear `Analitycs/service/app/core/security.py`: funciones `hash_password(raw: str)
  -> str` y `verify_password(raw: str, hashed: str) -> bool` (bcrypt); funciones
  `issue_session_token(username: str, tz: ZoneInfo) -> tuple[str, int]` (payload firmado con HMAC
  sobre `hashlib`/`hmac` de stdlib, incluye `exp` = próxima medianoche en `tz`, sin dependencias
  nuevas — research.md §1 Opción C) y `verify_session_token(token: str) -> bool` (valida firma con
  `hmac.compare_digest` y `exp` no vencido).
- [ ] T009 [P] En `Analitycs/service/app/core/security.py`, agregar dependency FastAPI
  `require_admin_session(authorization: str = Header(...))` que extrae `Bearer <token>`, llama a
  `verify_session_token`, y lanza `HTTPException(401, detail="No autenticado o sesión expirada")`
  si falta/inválido/expirado (FR-002, plan.md §5).
- [ ] T010 [P] En `Analitycs/service/app/core/security.py`, agregar dependency
  `require_internal_secret(x_internal_secret: str = Header(...))` que compara contra
  `settings.etl_cache_invalidation_secret` con `hmac.compare_digest`, lanza `401` si no coincide
  (research.md §3, para el endpoint interno de invalidación).
- [ ] T011 Ampliar `Analitycs/service/app/cache/analytics_cache.py`: envolver `cached()` en
  try/except sobre errores de conexión de Redis, cayendo a ejecutar `loader()` directamente sin
  cachear (fail-open, research.md §4), logueando una advertencia; no modificar la firma pública de
  `cached()`/`invalidate_pattern()`.
- [ ] T012 Crear `Analitycs/service/app/dto/__init__.py` si no existe, y ampliar
  `Analitycs/service/app/dto/analytics_dto.py` con los modelos Pydantic base compartidos:
  `ErrorResponse`, `LabelsValuesResponse` (con `percentages: list[float] | None`),
  `TokenResponse`.
- [ ] T013 Actualizar `Analitycs/service/app/main.py`: agregar manejador global de excepciones
  (`@app.exception_handler(Exception)`) que devuelve `{"detail": "internal_error"}` con `500` sin
  exponer stack trace (FR-018); configurar `docs_url`/`openapi_url`/`redoc_url` como `None` si
  `settings.environment` no es `"development"`/`"qa"` (FR-032, seguro-por-defecto); declarar el
  `securitySchemes` `bearerAuth` (`HTTPBearer`) en la app para que Swagger UI muestre "Authorize".

**Checkpoint**: Config, timezone, seguridad, manejo de errores y toggle de Swagger listos — las
historias de usuario pueden comenzar.

---

## Phase 3: Historia de Usuario 1 - Visión general de usuarios y actividad (Prioridad: P1) 🎯 MVP

**Objetivo**: Total de usuarios y usuarios activos (día/semana/mes/total), protegidos por sesión
de administrador.

**Prueba independiente**: Con login válido, `GET /api/admin/analytics/users/total` y
`GET /api/admin/analytics/users/active` con cada `period` devuelven valores correctos contra el
fixture de datos; sin credencial válida, ambos responden 401.

### Tests para US1

- [ ] T014 [P] [US1] Test de integración: login definitivo válido/inválido en
  `Analitycs/service/tests/integration/test_auth.py` (`POST /api/admin/auth/login` con
  `ADMIN_USERNAME`/hash correcto → 200 + token; con password incorrecto → 401).
- [ ] T015 [P] [US1] Test de integración: acceso sin token / token corrupto / token expirado a
  `GET /api/admin/analytics/users/total` en
  `Analitycs/service/tests/integration/test_auth_guard.py` → 401 en los 3 casos.
- [ ] T016 [P] [US1] Test de integración: expiración de sesión a medianoche en 2 timezones
  distintas (ej. `UTC` y `America/Argentina/Buenos_Aires`) en
  `Analitycs/service/tests/integration/test_session_timezone.py`, mockeando el reloj.
- [ ] T017 [P] [US1] Test de integración: `GET /api/admin/analytics/users/total` con token válido
  devuelve el conteo esperado contra el fixture, en
  `Analitycs/service/tests/integration/test_users_total.py`.
- [ ] T018 [P] [US1] Test de integración: `GET /api/admin/analytics/users/active` para
  `period=day|week|month|total` devuelve los conteos esperados contra el fixture, y `422` si falta
  `period_key` cuando `period != total`, en
  `Analitycs/service/tests/integration/test_users_active.py`.

### Implementación de US1

- [ ] T019 [US1] Crear `Analitycs/service/app/services/auth_service.py`: clase `AuthService` con
  método `login(username, password, timezone) -> TokenResponse` que valida contra
  `settings.admin_username`/`settings.admin_password_hash` usando `verify_password` (T008) y emite
  token con `issue_session_token` (T008); lanza `HTTPException(401)` si las credenciales no
  coinciden, sin distinguir si el usuario existe (edge case de `spec.md`).
- [ ] T020 [US1] Crear `Analitycs/service/app/routers/auth_router.py`: `POST
  /api/admin/auth/login` (tag `auth`) usando `LoginRequest`/`TokenResponse` de
  `dto/analytics_dto.py` y `AuthService.login` (T019); registrar el router en
  `Analitycs/service/app/main.py`.
- [ ] T021 [US1] En `Analitycs/service/app/dto/analytics_dto.py`, agregar `LoginRequest` (con
  validación de `timezone` contra `zoneinfo.available_timezones()`), `ActiveUsersQuery` (modelo
  Pydantic con `period: Literal[...]`, `period_key: str | None`, validador que exige
  `period_key` si `period != "total"`, reemplazando el `{"error": ...}` actual por un 422 real —
  discrepancia conocida de `spec.md`).
- [ ] T022 [US1] En `Analitycs/service/app/routers/analytics_router.py`, agregar
  `Depends(require_admin_session)` (T009) a **todos** los endpoints existentes y nuevos del router
  (aplica a US1, US2 y US3 por igual, se hace una sola vez aquí porque es transversal).
- [ ] T023 [US1] En `Analitycs/service/app/routers/analytics_router.py`, reemplazar la firma de
  `GET /users/active` para usar `ActiveUsersQuery` (T021) como dependency de query, delegando la
  validación 422 a Pydantic en vez del `if` manual actual.
- [ ] T024 [US1] En `Analitycs/service/app/services/analytics_service.py`, actualizar
  `active_users`/`active_users_total` para recibir la `tz` resuelta (T007) y usarla si en el
  futuro se requiere acotar "day/week/month" a la tz del cliente (documentar explícitamente si
  `period_key` ya viene pre-calculado por el cliente o si el service debe derivarlo — ver
  `research.md` §2, sin cambiar el contrato de `period_key` definido en `spec.md`).

**Checkpoint**: US1 funcional de forma independiente — login, guard de sesión, y los 2 reportes de
US1 protegidos y correctos.

---

## Phase 4: Historia de Usuario 2 - Reportes demográficos y de engagement (Prioridad: P2)

**Objetivo**: Tiempo en pantalla por rango de edad, género (3 categorías fijas + sin dato), país
(global/puntual), antigüedad de registro, promedio de tareas con filtro de estado.

**Prueba independiente**: Con el fixture de datos, cada endpoint demográfico devuelve promedios/
conteos/porcentajes correctos, incluyendo el caso de valores `NULL` y el shape `labels/values`.

### Tests para US2

- [ ] T025 [P] [US2] Test de integración: `GET /screen-time/age-range` con `min_age=18&max_age=25`
  devuelve el promedio correcto; con `min_age=30&max_age=10` → 422; con `min_age=-1` → 422; con
  rango sin datos → `avg_minutes: null` (no error), en
  `Analitycs/service/tests/integration/test_screen_time.py`.
- [ ] T026 [P] [US2] Test de integración: `GET /gender` devuelve exactamente las 3 categorías fijas
  + "sin dato" con porcentajes sumando 100%, en
  `Analitycs/service/tests/integration/test_gender.py`.
- [ ] T027 [P] [US2] Test de integración: `GET /country` sin filtro devuelve todos los países;
  con `country=Argentina` devuelve conteo + porcentaje sobre el total global; con país inexistente
  devuelve 0/0%, en `Analitycs/service/tests/integration/test_country.py`.
- [ ] T028 [P] [US2] Test de integración: `GET /registration-period?period=last_month` devuelve
  buckets acotados al rango, usando la tz del cliente (header `X-Client-Timezone`), en
  `Analitycs/service/tests/integration/test_registration_period.py`.
- [ ] T029 [P] [US2] Test de integración: `GET /tasks/summary?status=not-completed` usa
  `status != 'completed'` (no asume `pending`), en
  `Analitycs/service/tests/integration/test_tasks_summary.py`.
- [ ] T030 [P] [US2] Test de repositorio: `users_by_gender()` agrupa correctamente valores fuera
  de catálogo (ej. `"otro"`, `NULL`) como "sin dato", en
  `Analitycs/service/tests/unit/test_analytics_repository_gender.py`.

### Implementación de US2

- [ ] T031 [US2] En `Analitycs/service/app/repositories/analytics_repository.py`, corregir
  `users_by_gender()` para usar `CASE WHEN gender IN ('Hombre','Mujer','No binario') THEN gender
  ELSE 'sin dato' END` en el `GROUP BY` (FR-014, data-model.md §2.1), en vez de agrupar por el
  valor crudo.
- [ ] T032 [US2] En `Analitycs/service/app/repositories/analytics_repository.py`, agregar método
  `average_not_completed_tasks_per_user()` con `WHERE status != 'completed'` (FR-009, data-model.md
  §2.2), y actualizar `tasks_by_status()` para aceptar el filtro real sin mapear a `'pending'`.
- [ ] T033 [US2] En `Analitycs/service/app/services/analytics_service.py`, actualizar
  `tasks_summary()` para aceptar un parámetro `status_filter: Literal["all","completed",
  "not-completed"]` y delegar al método correcto de T032 (corrige discrepancia conocida FR-009).
- [ ] T034 [US2] En `Analitycs/service/app/routers/analytics_router.py`, actualizar
  `tasks_by_status`/`tasks_summary` para eliminar el mapeo hardcodeado `not-completed -> pending`
  y pasar el filtro real al service (T033).
- [ ] T035 [US2] En `Analitycs/service/app/routers/analytics_router.py`, agregar validación
  declarativa Pydantic para `min_age`/`max_age` en `/screen-time/age-range` (modelo
  `AgeRangeQuery` con `ge=0` y `@model_validator` que exige `min_age <= max_age` — FR-019,
  data-model.md §3), reemplazando la ejecución directa sin validar.
- [ ] T036 [US2] En `Analitycs/service/app/services/analytics_service.py`, actualizar
  `users_by_registration_period()` para recibir la `tz` resuelta (T007, vía header
  `X-Client-Timezone`) y calcular `since_ms`/`until_ms` con `period_bounds_epoch_ms()` en vez de
  `dt.datetime.now(dt.timezone.utc)` fijo (corrige discrepancia conocida FR-021).
- [ ] T037 [US2] En `Analitycs/service/app/services/analytics_service.py`, transformar las
  respuestas de `users_by_device`, `users_by_registration_period`, `users_by_gender`,
  `users_by_country`, y `top_five_apps` (esta última en US3, pero el helper se define aquí) al
  shape `{"labels": [...], "values": [...], "percentages"?: [...]}` (FR-016) mediante una función
  compartida `to_labels_values(rows, label_key, value_key, percentage_key=None)` en
  `Analitycs/service/app/services/analytics_service.py`.

**Checkpoint**: US1 + US2 funcionan de forma independiente y combinada.

---

## Phase 5: Historia de Usuario 3 - Rankings y comparativas (Prioridad: P3)

**Objetivo**: Top 5 apps (con desempate determinístico), promedio/total de competencias,
promedio de desafíos completados, claramente diferenciado del promedio general.

**Prueba independiente**: Con apps empatadas en promedio, el top 5 devuelve siempre el mismo
orden (desempate alfabético); los 2 reportes de competencias devuelven valores distintos y
etiquetados sin ambigüedad.

### Tests para US3

- [ ] T038 [P] [US3] Test de repositorio: `top_five_apps_by_screen_time()` con 2+ apps empatadas
  en `avg_minutes` devuelve siempre el mismo orden (alfabético por `app_label`) en ejecuciones
  repetidas, en `Analitycs/service/tests/unit/test_analytics_repository_top5.py`.
- [ ] T039 [P] [US3] Test de integración: `GET /apps/top5` devuelve shape `labels/values` con
  exactamente 5 ítems cuando hay ≥5 apps, en
  `Analitycs/service/tests/integration/test_top5_apps.py`.
- [ ] T040 [P] [US3] Test de integración: `GET /challenges/summary` devuelve
  `avg_challenges_per_user` (sin filtro) y `avg_completed_challenges_per_user` (`status=
  'completed'`) con valores distintos y verificables contra el fixture, en
  `Analitycs/service/tests/integration/test_challenges_summary.py`.

### Implementación de US3

- [ ] T041 [US3] En `Analitycs/service/app/repositories/analytics_repository.py`, corregir
  `top_five_apps_by_screen_time()` agregando `ORDER BY avg_minutes DESC, app_label ASC` (FR-008,
  edge case de `spec.md`, data-model.md §2.3).
- [ ] T042 [US3] En `Analitycs/service/app/services/analytics_service.py`, aplicar
  `to_labels_values()` (T037) a `top_five_apps()` para devolver el shape `labels/values` (FR-016).

**Checkpoint**: Los 13 reportes (US1+US2+US3) completos, corregidos y protegidos por sesión.

---

## Phase 6: Historia de Usuario 4 - Explorar y entender los endpoints disponibles (Prioridad: P1)

**Objetivo**: Swagger UI lista automáticamente todos los endpoints (13 reportes + logins),
agrupados por tag, con parámetros/respuestas/códigos documentados.

**Prueba independiente**: Abrir `/docs` y verificar visualmente que aparecen todos los endpoints
agrupados por tag, con parámetros y ejemplo de respuesta.

### Tests para US4

- [ ] T043 [P] [US4] Test de integración: `GET /openapi.json` incluye los 13 operationIds de
  reportes + `login`/`test-login`, cada uno con al menos un código de respuesta distinto de `200`
  documentado, en `Analitycs/service/tests/integration/test_openapi_schema.py`.

### Implementación de US4

- [ ] T044 [US4] Ampliar `Analitycs/service/app/dto/analytics_dto.py`: agregar `examples`/
  `json_schema_extra` a cada modelo de respuesta (`CountResponse`, `AverageResponse`,
  `LabelsValuesResponse`, `TasksSummaryResponse`, `ChallengesSummaryResponse`) para que Swagger
  muestre ejemplos realistas (FR-003/025), consistentes con `contracts/openapi.yaml`.
- [ ] T045 [US4] Revisar cada decorador de ruta en `Analitycs/service/app/routers/
  analytics_router.py` y `auth_router.py`: agregar `summary`, `description`, `tags` y
  `response_model` explícitos para que coincidan con `contracts/openapi.yaml` (FR-002/024).

**Checkpoint**: La documentación interactiva lista y describe todos los endpoints correctamente.

---

## Phase 7: Historia de Usuario 5 - Ejecutar endpoints desde Swagger (Prioridad: P1)

**Objetivo**: "Try it out" funcional contra el servicio real, mostrando 401/422 reales cuando
corresponda.

**Prueba independiente**: Ejecutar un endpoint protegido sin token desde Swagger → 401 visible;
con parámetros inválidos → 422 visible; con token válido → 200 con datos reales.

### Tests para US5

- [ ] T046 [P] [US5] Test de integración end-to-end vía `TestClient`: simular una llamada estilo
  Swagger "Try it out" (request HTTP real contra la app) para un endpoint protegido sin header
  `Authorization` → 401 con body `{"detail": ...}`; con `min_age=30&max_age=10` → 422 con body
  `{"detail": ...}`, en `Analitycs/service/tests/integration/test_try_it_out.py`.

### Implementación de US5

- [ ] T047 [US5] Verificar en `Analitycs/service/app/main.py` que no hay configuración de CORS que
  bloquee las llamadas desde el propio Swagger UI servido por FastAPI (mismo origen; documentar si
  se requiere `CORSMiddleware` para un Panel Admin en otro origen, sin implementarlo si no es
  necesario para Swagger mismo).
- [ ] T048 [US5] Confirmar que el manejador global de excepciones (T013) y las validaciones
  Pydantic (T021/T035) devuelven siempre `HTTPException`/`RequestValidationError` nativos de
  FastAPI (no un envelope custom), para que Swagger UI renderice el 401/422 real sin
  transformación adicional.

**Checkpoint**: Todo endpoint es ejecutable y verificable desde Swagger UI con respuestas reales.

---

## Phase 8: Historia de Usuario 6 - Autenticarse desde Swagger (Prioridad: P2)

**Objetivo**: Login de prueba temporal + botón "Authorize" cargando el token automáticamente
para el resto de los "Try it out".

**Prueba independiente**: Ejecutar `/auth/test-login` desde Swagger, cargar el token en
"Authorize", y ejecutar un reporte protegido sin pegar el token manualmente → 200.

### Tests para US6

- [ ] T049 [P] [US6] Test de integración: `POST /api/admin/auth/test-login` con
  `TEST_ADMIN_USER`/`TEST_ADMIN_PASSWORD` válidos → 200 + token; con credenciales incorrectas →
  401; verificar que el tag del endpoint en `/openapi.json` es `auth-test-only` y su descripción
  contiene "prueba", en `Analitycs/service/tests/integration/test_auth_test_login.py`.

### Implementación de US6

- [ ] T050 [US6] En `Analitycs/service/app/services/auth_service.py`, agregar método
  `test_login(username, password, timezone) -> TokenResponse` que valida contra
  `settings.test_admin_user`/`settings.test_admin_password` (comparación directa, sin hash —
  FR-031 permite esta relajación explícita solo para el login de prueba) y reutiliza
  `issue_session_token` (mismo formato de token que el login definitivo, research.md §1).
- [ ] T051 [US6] En `Analitycs/service/app/routers/auth_router.py`, agregar `POST
  /api/admin/auth/test-login` con `tags=["auth-test-only"]` y `description="Solo para pruebas —
  no usar en producción"` (FR-031), devolviendo `TokenResponse`.

**Checkpoint**: Flujo completo login-de-prueba → Authorize → ejecutar reporte protegido, 100%
operable desde Swagger UI sin herramientas externas.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Propósito**: Cierre transversal: endpoint interno de invalidación de caché, checklist de
requisitos, validación de quickstart.

- [ ] T052 [P] Crear `Analitycs/service/app/routers/internal_router.py`: `POST
  /internal/cache/invalidate-reports` con `Depends(require_internal_secret)` (T010), que llama a
  `invalidate_pattern("admin:analytics:*")` (ya existente en `cache/analytics_cache.py`) y
  responde `204` (research.md §3, FR-022); registrar el router en `main.py` con `tags=
  ["internal"]`, **excluido** de la doc pública si se decide ocultarlo (opcional, documentar
  decisión).
- [ ] T053 [P] Test de integración: `POST /internal/cache/invalidate-reports` sin
  `X-Internal-Secret` → 401; con secreto correcto → 204 y las claves `admin:analytics:*` quedan
  eliminadas de Redis, en `Analitycs/service/tests/integration/test_internal_invalidate.py`.
- [ ] T054 [P] Test de cache: `cached()` en cache-hit no invoca al `loader` (mock/spy); en
  cache-miss sí lo invoca y persiste con el TTL correcto según `settings.cache_ttl_*`; comportamiento
  fail-open si Redis lanza una excepción de conexión, en
  `Analitycs/service/tests/unit/test_analytics_cache.py`.
- [ ] T055 [P] Actualizar `Analitycs/specs/001-reportes-fastapi/checklists/requirements.md` si
  quedara algún ítem pendiente tras cerrar las discrepancias conocidas (revisión final, no debería
  requerir cambios de contenido ya que la spec no se modifica).
- [ ] T056 Ejecutar manualmente la guía de `Analitycs/specs/001-reportes-fastapi/quickstart.md`
  completa (login test → Authorize → ejecutar reportes → 401/422 → invalidación simulada) como
  validación final de aceptación end-to-end.
- [ ] T057 [P] Revisar que ningún log o respuesta de error exponga SQL, nombres de tabla, o
  excepciones crudas de `psycopg`/`redis-py` (FR-018) — auditoría rápida de
  `Analitycs/service/app/main.py` y `core/security.py`.

---

## Dependencies & Execution Order

### Dependencias entre fases

- **Setup (Phase 1)**: sin dependencias — puede iniciar de inmediato.
- **Foundational (Phase 2)**: depende de Setup — **bloquea** todas las historias de usuario.
- **US1 (Phase 3, P1)**: depende de Foundational. Es el MVP (login + guard + 2 reportes base).
- **US2 (Phase 4, P2)**: depende de Foundational; reutiliza el guard de sesión ya aplicado en T022
  (US1) sobre el router completo — por eso T022 vive en US1 pero cubre también los endpoints de
  US2/US3.
- **US3 (Phase 5, P3)**: depende de Foundational; independiente de US2 salvo por `to_labels_values`
  (T037, definida en US2 pero reutilizada aquí — documentado explícitamente en T042).
- **US4 (Phase 6, P1 doc)**: depende de que existan los endpoints de US1-US3 (para documentarlos
  con ejemplos reales) y de Foundational (Swagger toggle, T013).
- **US5 (Phase 7, P1 doc)**: depende de US4 (la doc debe existir para poder "Try it out") y de
  Foundational (manejo de errores, T013).
- **US6 (Phase 8, P2 doc)**: depende de Foundational (T008/T009, mismo mecanismo de token) y de
  US5 (para poder verificar el flujo completo Authorize → ejecutar reporte).
- **Polish (Phase 9)**: depende de todas las historias anteriores.

### Oportunidades de paralelismo

- Todas las tareas `[P]` de Setup (T002-T004) en paralelo.
- Todas las tareas `[P]` de Foundational (T006-T010, T012) en paralelo entre sí (T005, T011, T013
  tienen dependencias de archivo compartido y van secuenciales respecto a las anteriores).
- Dentro de cada historia, todos los tests marcados `[P]` pueden ejecutarse/escribirse en paralelo
  antes de la implementación.
- US2 y US3 pueden trabajarse en paralelo por distintas personas una vez completado US1 (comparten
  poca superficie: solo `to_labels_values()` en `analytics_service.py`, ver nota de T042).
- US4 puede empezar en paralelo con la cola de US2/US3 si ya existen suficientes endpoints de US1
  para documentar como referencia, aunque lo ideal es completarlas antes para documentar el shape
  final.

---

## Implementation Strategy

### MVP primero (US1 solamente)

1. Completar Phase 1 (Setup) + Phase 2 (Foundational).
2. Completar Phase 3 (US1): login, guard de sesión, total de usuarios, usuarios activos.
3. **Detener y validar**: correr `quickstart.md` parcialmente (login + 2 endpoints) de forma
   manual o vía `pytest tests/integration/test_users_total.py test_users_active.py`.
4. Demo: Panel Admin (o Swagger) puede loguearse y ver los 2 reportes base protegidos.

### Entrega incremental

1. Setup + Foundational → base lista.
2. US1 → MVP demostrable (auth + 2 reportes).
3. US2 → +6 reportes demográficos/engagement, corrige 4 discrepancias conocidas.
4. US3 → +3 reportes de ranking, corrige desempate top-5.
5. US4 → documentación Swagger completa y descriptiva.
6. US5 → verificación de que todo es ejecutable con respuestas reales (401/422) desde Swagger.
7. US6 → login de prueba + Authorize, cerrando el flujo de prueba end-to-end sin herramientas
   externas.
8. Polish → endpoint interno de invalidación (contrato con ETL) + auditoría de seguridad/errores.

### Trazabilidad rápida con FR/SC

Ver `plan.md` §15 para la tabla completa FR↔SC↔sección del plan; cada tarea de este documento
referencia explícitamente el FR que corrige o implementa entre paréntesis en su descripción.
