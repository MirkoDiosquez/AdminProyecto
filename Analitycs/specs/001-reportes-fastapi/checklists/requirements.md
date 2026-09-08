# Specification Quality Checklist: API de Reportes para el Panel de Administración

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- El marcador `[NEEDS CLARIFICATION]` de `FR-020` (mecanismo de autenticación de administrador)
  se resolvió en la sesión de clarificación del 2026-09-07: cuenta única con credenciales fijas
  en variables de entorno, contraseña hasheada. Ver sección **Clarifications** del spec.
- En la misma sesión también se resolvieron: la duración/expiración de la sesión de
  administrador (medianoche del día en curso, ver FR-002); el filtro del reporte de país
  (solo país puntual, sin soporte de región, ver FR-015); la zona horaria de referencia para
  la expiración de sesión y los filtros de período — decidida finalmente como la zona horaria
  **vigente del cliente/admin al momento de la solicitud** (no una zona fija de servidor), ver
  FR-002 y FR-021; y la existencia de una capa de caché de solo lectura (Redis, read-through)
  delante de PostgreSQL para servir los 13 reportes, invalidada tras cada corrida del ETL (ver
  FR-022).
- **Discrepancia código-spec detectada y resuelta**: `analytics_service.py` (implementación ya
  existente) usa UTC fijo en `users_by_registration_period`, contradiciendo la decisión de zona
  horaria dinámica. Se confirmó que prevalece la especificación; el código queda marcado como
  pendiente de corrección en `/plan`/`/implement` (ver FR-021).
- **Discrepancia código-spec detectada y resuelta**: `analytics_repository.py` (implementación
  ya existente) agrupa dinámicamente por el valor crudo de `gender` en `users_by_gender()`, sin
  categorías fijas ni bucket "sin dato", contradiciendo FR-014. Se confirmó que prevalece la
  especificación (3 categorías fijas + "sin dato"); el código queda marcado como pendiente de
  corrección en `/plan`/`/implement` (ver FR-014).
- **Discrepancia código-spec detectada y resuelta**: `analytics_service.py::tasks_summary()`
  (implementación ya existente) no soporta ningún filtro de estado y siempre calcula ambos
  promedios (todas + completadas), y `analytics_repository.py` no tiene un método para "no
  completadas" por usuario, contradiciendo FR-009. Se confirmó que prevalece la especificación
  (filtro real completadas/no completadas/todas); el código queda marcado como pendiente de
  corrección en `/plan`/`/implement` (ver FR-009).
- **Discrepancia código-spec detectada y resuelta**: `top_five_apps_by_screen_time()` en
  `analytics_repository.py` (implementación ya existente) no tiene desempate secundario en su
  `ORDER BY`, contradiciendo el edge case de desempate determinístico para el top 5 de apps. Se
  confirmó que prevalece la especificación; el código queda marcado como pendiente de corrección
  en `/plan`/`/implement` (agregar `ORDER BY avg_minutes DESC, app_label ASC`).
- **Discrepancia código-spec detectada y resuelta**: `analytics_router.py` (implementación ya
  existente) no valida `min_age`/`max_age` en `/screen-time/age-range` y responde 200 con
  `{"error": ...}` (en vez de 422) cuando falta `period_key` en `/users/active`, contradiciendo
  FR-019 y el edge case de rango de edad inválido. Se confirmó que prevalece la especificación
  (422 con mensaje descriptivo); el código queda marcado como pendiente de corrección en
  `/plan`/`/implement` (ver FR-019).
- **Ambigüedad documentada y resuelta**: la spec no especificaba los valores exactos de
  `fact_tasks.status`; se documentó en **Supuestos** que "no completadas" (FR-009) se define
  como `status != 'completed'` (no un valor literal fijo como `'pending'`), más robusto ante
  posibles estados intermedios. El mapeo hardcodeado `not-completed -> 'pending'` en
  `analytics_router.py::tasks_by_status` queda marcado como pendiente de corrección en
  `/plan`/`/implement` para usar esta definición (ver FR-009).
- **Discrepancia código-spec detectada y resuelta**: los 5 endpoints de gráfico ya implementados
  (`top_five_apps`, `users_by_device`, `users_by_gender`, `users_by_country`,
  `users_by_registration_period` en `analytics_service.py`) devuelven listas de objetos por ítem
  (tabla cruda) en vez del formato `labels`/`values` exigido por FR-016. Se confirmó que
  prevalece la especificación; el código queda marcado como pendiente de corrección en
  `/plan`/`/implement` (ver FR-016).
- El resto de las preguntas originales del usuario (shape exacto de JSON por endpoint,
  paginación, manejo de NULL) se resolvieron con supuestos razonables documentados en la sección
  **Supuestos** del spec.
- Spec lista para avanzar a `/speckit-plan`.
