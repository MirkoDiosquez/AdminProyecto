# Research: API de Reportes y Documentación Interactiva

**Feature**: `001-reportes-fastapi` | **Fecha**: 2026-09-15

Este documento resuelve las decisiones técnicas no triviales necesarias para pasar de `spec.md` a
un diseño concreto (`data-model.md`, `contracts/openapi.yaml`). Solo se investigan puntos que
`spec.md` deja abiertos o que el plan requiere decidir; no se repite información ya cerrada en la
spec o en la constitución.

## 1. Estrategia de autenticación / token de sesión

**Pregunta**: ¿Cómo se implementa la "credencial de sesión" de FR-001, de forma que expire a
medianoche en la tz del cliente, sin tabla de administradores en PostgreSQL (FR-020)?

**Opciones evaluadas**:

| Opción | Descripción | Pros | Contras |
|---|---|---|---|
| A. JWT firmado stateless | Token JWT firmado (HMAC con secreto de servidor) con claim `exp` = próxima medianoche en la tz recibida. Validación sin estado (solo verifica firma + `exp`). | No requiere Redis/PostgreSQL para sesiones; simple de invalidar por expiración; encaja con "sin tabla de admins". | Requiere una librería JWT (`python-jose` o similar) — dependencia nueva a justificar. |
| B. Token opaco + Redis | Token aleatorio opaco, se guarda en Redis con TTL = segundos hasta medianoche. | Reutiliza Redis ya presente. | Acopla la sesión de auth con la misma infraestructura de cache de reportes (mezcla dos responsabilidades); si Redis cae, también caen las sesiones. |
| C. JWT firmado con librería estándar de `cryptography`/HMAC manual (`hmac` + `hashlib`, stdlib) | Igual que A pero sin dependencia externa, implementando firma/verificación manualmente sobre un payload JSON + `hmac.compare_digest`. | Cero dependencias nuevas (cumple restricción "no introducir frameworks sin necesidad real"). | Requiere implementar cuidadosamente encode/decode y comparación segura (riesgo si se hace mal). |

**Decisión**: **Opción C** (JWT-like firmado con HMAC de la stdlib), evitando una dependencia
nueva salvo que el equipo prefiera adoptar `python-jose`/`pyjwt` por simplicidad de
implementación. Se documenta como decisión abierta a validar en `/speckit-tasks`: si el equipo
prioriza velocidad de implementación sobre "cero dependencias", **Opción A** con `pyjwt` (librería
pequeña, ampliamente usada, sin conflicto con FastAPI) es una alternativa aceptable y debe
justificarse en el PR correspondiente. En ambos casos, el **contrato observable** (header
`Authorization: Bearer <token>`, expiración a medianoche tz-cliente, 401 si inválido/expirado) es
idéntico, por lo que no bloquea el resto del diseño.

**Por qué no la Opción B**: acoplar sesiones de auth a Redis mezclaría la responsabilidad de
"cache de reportes" (que se invalida masivamente post-ETL) con "sesiones de admin" (que no deben
invalidarse por ese evento); un `invalidate_pattern("admin:analytics:*")` accidentalmente amplio
podría desloguear al admin. Mantenerlas separadas es más seguro y más simple de razonar.

## 2. Mecanismo de transporte de la zona horaria del cliente

**Pregunta**: FR-002/021 exigen usar la tz vigente del cliente, pero no fijan el mecanismo.

**Opciones evaluadas**:

| Opción | Descripción | Pros | Contras |
|---|---|---|---|
| A. Header HTTP `X-Client-Timezone` en cada request + campo `timezone` en login | Nombre IANA (ej. `America/Argentina/Buenos_Aires`), validado con `zoneinfo`. | Explícito, cacheable por clave (se puede incluir en la clave de cache si en el futuro se requiere), fácil de documentar en OpenAPI (`parameter` reutilizable). | El frontend debe agregarlo en cada llamada (pequeño costo de integración). |
| B. Solo en el login, y el server "recuerda" la tz asociada al token | La tz queda embebida en el token/sesión; los reportes usan la tz del token, no de cada request. | Menos repetición en el frontend. | Si el admin cambia de tz a mitad de sesión (ej. viaja), los reportes de período usarían una tz desactualizada; más ambiguo respecto a "la tz vigente al momento de la solicitud" (FR-021 habla de "al momento de la solicitud", no "al momento del login"). |
| C. Query param opcional `?tz=...` en cada endpoint de reporte | Similar a A pero como query param en vez de header. | Visible en Swagger "Try it out" sin configurar headers custom. | Contamina la firma de cada endpoint con un parámetro repetido; menos "transversal" que un header. |

**Decisión**: **Opción A** (header `X-Client-Timezone` para los reportes + campo `timezone` en el
body de login para calcular la expiración de sesión). Es la que más fielmente cumple "la zona
horaria vigente del cliente/admin **al momento de la solicitud**" (FR-002/FR-021), ya que cada
request de reporte puede llevar su propia tz vigente, independiente de cuándo se hizo login.

**Default si el header no se envía**: `NEEDS CLARIFICATION` — se propone `UTC` como valor por
defecto seguro (determinístico, sin sorpresas), pero debe confirmarse con el equipo antes de
`/speckit-tasks`, ya que no está definido en `spec.md`.

## 3. Estrategia de invalidación de caché post-ETL

**Pregunta**: FR-022 exige invalidación explícita tras cada corrida del ETL; `cache/
analytics_cache.py` ya expone `invalidate_pattern()`, pero no existe un "disparador".

**Opciones evaluadas**:

| Opción | Descripción | Pros | Contras |
|---|---|---|---|
| A. Endpoint interno protegido (ej. `POST /internal/cache/invalidate-reports`) que el ETL llama vía HTTP al terminar. | Simple, desacoplado, el ETL solo necesita hacer un `POST`. | Requiere exponer un endpoint adicional protegido (con su propio mecanismo de auth, distinto del de admin humano). |
| B. El ETL escribe directamente en Redis (import de `invalidate_pattern` como librería compartida). | Cero endpoint nuevo. | Acopla el proceso ETL (otro equipo/repo) al código interno de este servicio; viola el principio de capas independientes si el ETL vive en otro repo/lenguaje. |
| C. Mensaje/evento (ej. una cola) que este servicio consume para disparar la invalidación. | Más robusto ante fallos de red puntuales. | Introduce infraestructura de mensajería nueva no justificada por el alcance de este feature (la Constitución ya fija RabbitMQ para Notificaciones, no para esto). |

**Decisión**: **Opción A** (endpoint interno HTTP), por ser la que respeta mejor la independencia
de capas (Principio I) sin introducir infraestructura nueva. **Queda como contrato pendiente de
confirmar por escrito con el equipo del ETL** (ver `plan.md` §14): el nombre exacto del endpoint,
su mecanismo de autenticación (ej. un secreto compartido distinto del login de admin, ya que el
ETL no es un humano) y la red desde la que se invoca, se definen en `/speckit-tasks` una vez
confirmado. No se implementa el lado ETL en este feature.

## 4. Comportamiento ante Redis no disponible

**Pregunta**: no cubierto explícitamente por `spec.md`. ¿Qué hace `cached()` si Redis no responde?

**Decisión**: **fail-open hacia PostgreSQL** — si `get_redis()`/`r.get(key)` lanza una excepción de
conexión, se captura, se seguirá como si fuera cache-miss (ejecutar `loader()` y devolver el
resultado), y se registra un log de advertencia, **sin** intentar `r.set(...)` (para no fallar dos
veces) y **sin** propagar un 500 al cliente. Esto prioriza disponibilidad de lectura de reportes
por sobre la optimización de performance, coherente con que PostgreSQL sigue siendo la fuente de
verdad (FR-017) y Redis es solo una optimización, nunca la única vía de acceso a los datos.

## 5. Formato `labels`/`values` — estructura exacta

**Pregunta**: FR-016 exige un formato "labels + values", pero no fija el JSON exacto.

**Decisión**: estructura mínima común para los 5 reportes de gráfico:

```json
{
  "labels": ["Argentina", "Uruguay", "..."],
  "values": [120, 8, "..."],
  "percentages": [93.7, 6.3]
}
```

- `labels`/`values` son obligatorios y **siempre del mismo largo**.
- `percentages` (u otro array paralelo) se agrega **solo** cuando el reporte lo requiere (género,
  país); se documenta explícitamente en cada schema de `contracts/openapi.yaml` cuál aplica.
- Se elige **arrays paralelos** (no una lista de objetos) porque es el formato que la mayoría de
  las librerías de gráficos de un Panel Admin (ej. Chart.js) consumen directamente sin
  transformación adicional (alineado a SC-006).

## 6. Validación declarativa de parámetros (422)

**Decisión**: usar las capacidades nativas de FastAPI/Pydantic (`Query(..., ge=0)`,
`pattern="^...$"`, validadores `@field_validator`) en vez de `if`s manuales dispersos en el router,
de forma que FastAPI genere automáticamente el `422` con el detalle del campo inválido **antes**
de que el router llame al service (cumpliendo FR-019 "antes de ejecutar la consulta agregada").
Para la regla cruzada `min_age <= max_age` (que Pydantic simple no valida entre dos campos sin un
modelo), se usa un modelo Pydantic dedicado (`AgeRangeQuery`) con un `@model_validator` que lanza
`ValueError`, que FastAPI traduce automáticamente a `422`.

## 7. Uso de índices existentes (`indexes.sql`)

Se confirma que `indexes.sql` ya cubre las columnas de filtro/agrupación necesarias para los 13
reportes (detalle en `plan.md` §12); **no se requieren índices nuevos**. No se investiga más allá
de esta confirmación porque no hay indicios de un problema de performance real a resolver.

## 8. Estrategia de testing

**Decisión**: `pytest` + `TestClient` de FastAPI (ya viene con `fastapi[testclient]`/`httpx` como
dependencia transitiva) para tests de integración; no se introduce un framework de testing E2E
(ej. Playwright) porque el alcance de este feature es una API, no una UI. Para tests de repository
contra PostgreSQL real, se usa una base de test separada (ver `quickstart.md`) poblada con
fixtures SQL mínimas — no se introduce un ORM ni una librería de fixtures adicional (ej.
`factory_boy`) sin necesidad real, dado el tamaño acotado de los fixtures requeridos.

## Resumen de puntos `NEEDS CLARIFICATION` abiertos

1. Valor por defecto de zona horaria si el cliente no envía `X-Client-Timezone` (propuesto: `UTC`).
2. Mecanismo exacto de autenticación del endpoint interno de invalidación de caché para el ETL
   (propuesto: secreto compartido vía variable de entorno, distinto del login de admin humano).
3. Confirmación del frontend (Panel Admin) para adoptar el header `X-Client-Timezone` y el campo
   `timezone` en login.

Estos 3 puntos no bloquean el resto del diseño (Fase 1) porque tienen un default razonable
documentado, pero deben resolverse antes de `/speckit-implement`.
