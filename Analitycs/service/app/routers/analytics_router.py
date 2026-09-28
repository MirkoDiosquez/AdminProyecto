"""
AnalyticsController — expone endpoints REST para el Panel Admin.
No contiene lógica de negocio ni SQL: delega todo a AnalyticsService.

Todos los endpoints requieren sesion de administrador valida (Depends(require_admin_session),
T022, FR-002); se aplica una sola vez aca porque es transversal a US1/US2/US3.
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Header, Query
from app.core.security import require_admin_session
from app.core.timezone import resolve_client_timezone
from app.dto.analytics_dto import (
    ActiveUsersQuery,
    AgeRangeQuery,
    ChallengesSummaryDTO,
    ErrorResponse,
    LabelsValuesResponse,
    RegistrationPeriodQuery,
    RegistrationPeriodResponse,
    ScreenTimeByAgeRangeDTO,
    TasksStatusQuery,
    TasksSummaryDTO,
    TotalUsersDTO,
)
from app.services.analytics_service import analytics_service as service

# Responses comunes a todo endpoint protegido (FR-002/018, T044/T045).
_UNAUTHORIZED = {401: {"model": ErrorResponse, "description": "No autenticado o sesión expirada"}}
_UNAUTHORIZED_AND_INVALID = {**_UNAUTHORIZED, 422: {"model": ErrorResponse, "description": "Parámetros de filtro inválidos"}}

router = APIRouter(
    prefix="/api/admin/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_admin_session)],
)


@router.get(
    "/users/total",
    response_model=TotalUsersDTO,
    summary="Total de usuarios registrados",
    description="Devuelve la cantidad total de filas en dim_users (FR-003).",
    responses=_UNAUTHORIZED,
)
def total_users():
    return service.total_users()


@router.get(
    "/users/active",
    summary="Usuarios activos por período",
    description="Cantidad de usuarios con actividad en el período solicitado "
    "(día/semana/mes/total). FR-004. Requiere period_key si period != total.",
    responses=_UNAUTHORIZED_AND_INVALID,
)
def active_users(query: Annotated[ActiveUsersQuery, Query()]):
    if query.period == "total":
        return service.active_users_total()
    return service.active_users(query.period, query.period_key)


@router.get(
    "/screen-time/age-range",
    response_model=ScreenTimeByAgeRangeDTO,
    summary="Promedio de tiempo en pantalla por rango de edad",
    description="Promedio de minutes_used filtrando por rango de edad libre (FR-005/019).",
    responses=_UNAUTHORIZED_AND_INVALID,
)
def screen_time_age_range(query: Annotated[AgeRangeQuery, Query()]):
    return service.average_screen_time_by_age_range(query.min_age, query.max_age)


@router.get(
    "/apps/top5",
    response_model=LabelsValuesResponse,
    summary="Top 5 apps por tiempo en pantalla",
    description="Top 5 apps con mayor promedio de minutes_used, con desempate "
    "alfabético determinístico (FR-008).",
    responses=_UNAUTHORIZED,
)
def top_five_apps():
    return service.top_five_apps()


@router.get(
    "/challenges/summary",
    response_model=ChallengesSummaryDTO,
    summary="Resumen de competencias",
    description="Total de competencias, promedio general por usuario y promedio "
    "de completadas por usuario, claramente diferenciados (FR-006/007/013).",
    responses=_UNAUTHORIZED,
)
def challenges_summary():
    return service.challenges_summary()


@router.get(
    "/tasks/summary",
    response_model=TasksSummaryDTO,
    summary="Resumen de tareas por usuario",
    description="Promedio de tareas por usuario y de tareas completadas, "
    "soportando filtro de estado completadas/no completadas/todas (FR-009).",
    responses=_UNAUTHORIZED_AND_INVALID,
)
def tasks_summary(query: Annotated[TasksStatusQuery, Query()]):
    return service.tasks_summary(query.status)


@router.get(
    "/tasks/by-status",
    summary="Cantidad de tareas por estado",
    description="Conteo de tareas agrupadas por status, con filtro opcional.",
    responses=_UNAUTHORIZED_AND_INVALID,
)
def tasks_by_status(status: Optional[str] = Query("all", pattern="^(completed|not-completed|all)$")):
    return service.tasks_by_status(status)


@router.get(
    "/devices",
    response_model=LabelsValuesResponse,
    summary="Usuarios por dispositivo",
    description="Cantidad de usuarios agrupados por dim_users.device (FR-010), "
    "en formato labels/values.",
    responses=_UNAUTHORIZED,
)
def users_by_device():
    return service.users_by_device()


@router.get(
    "/registration-period",
    response_model=RegistrationPeriodResponse,
    summary="Usuarios por antigüedad de registro",
    description="Usuarios agrupados por bucket temporal de registered_at, "
    "acotado al período solicitado usando la timezone del cliente "
    "(header X-Client-Timezone, FR-011/021).",
    responses=_UNAUTHORIZED,
)
def users_by_registration_period(
    query: Annotated[RegistrationPeriodQuery, Query()],
    x_client_timezone: Optional[str] = Header(default=None, alias="X-Client-Timezone"),
):
    tz = resolve_client_timezone(x_client_timezone)
    return service.users_by_registration_period(query.period, tz)


@router.get(
    "/age/average",
    summary="Promedio de edad",
    description="Promedio de dim_users.age excluyendo valores NULL (FR-012).",
    responses=_UNAUTHORIZED,
)
def average_user_age():
    return service.average_user_age()


@router.get(
    "/gender",
    response_model=LabelsValuesResponse,
    summary="Distribución de usuarios por género",
    description="Porcentaje de usuarios agrupados en 3 categorías fijas "
    "(Hombre/Mujer/No binario) más 'sin dato' (FR-014).",
    responses=_UNAUTHORIZED,
)
def users_by_gender():
    return service.users_by_gender()


@router.get(
    "/country",
    response_model=LabelsValuesResponse,
    summary="Distribución de usuarios por país",
    description="Cantidad y porcentaje de usuarios por país, con filtro "
    "opcional por país puntual (FR-015).",
    responses=_UNAUTHORIZED,
)
def users_by_country(country: Optional[str] = Query(None)):
    return service.users_by_country(country)
