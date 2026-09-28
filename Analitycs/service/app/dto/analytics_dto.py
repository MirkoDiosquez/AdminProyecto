"""
DTOs de respuesta de Analytics (Pydantic). El Controller/Service nunca
devuelve filas crudas de PostgreSQL directamente.
"""
from typing import Literal, Optional
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    """Body de POST /api/admin/auth/login y /api/admin/auth/test-login (T021,
    data-model.md §3). `timezone` se usa para calcular el `exp` de la sesion
    (medianoche local, FR-002)."""
    username: str
    password: str
    timezone: str

    @field_validator("timezone")
    @classmethod
    def _timezone_debe_ser_iana_valida(cls, value: str) -> str:
        if value not in available_timezones():
            raise ValueError(f"timezone '{value}' no es un nombre IANA válido")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "admin",
                "password": "********",
                "timezone": "America/Argentina/Buenos_Aires",
            }
        }
    }


class ActiveUsersQuery(BaseModel):
    """Query params de GET /users/active (T021, data-model.md §3). Reemplaza el
    `{"error": ...}` con 200 anterior por un 422 real cuando falta `period_key`
    y `period != 'total'`."""
    period: Literal["day", "week", "month", "total"]
    period_key: Optional[str] = None

    @model_validator(mode="after")
    def _period_key_requerido_si_no_es_total(self) -> "ActiveUsersQuery":
        if self.period != "total" and not self.period_key:
            raise ValueError("period_key es requerido cuando period != 'total'")
        return self


class AgeRangeQuery(BaseModel):
    """Query params de GET /screen-time/age-range (T035, FR-019, data-model.md §3).
    Reemplaza la ejecucion sin validar por 422 con mensaje descriptivo."""
    min_age: int = Field(ge=0)
    max_age: int = Field(ge=0)

    @model_validator(mode="after")
    def _min_no_puede_superar_max(self) -> "AgeRangeQuery":
        if self.min_age > self.max_age:
            raise ValueError("min_age no puede ser mayor que max_age")
        return self


class TasksStatusQuery(BaseModel):
    """Query param de GET /tasks/summary (T033, data-model.md §3)."""
    status: Literal["completed", "not-completed", "all"] = "all"


class RegistrationPeriodQuery(BaseModel):
    """Query param de GET /registration-period (data-model.md §3)."""
    period: Literal["last_week", "last_month", "last_3_months", "last_year", "all"] = "all"



class ErrorResponse(BaseModel):
    """Shape estandar de error (401/422/500) — FR-018, T012."""
    detail: str

    model_config = {"json_schema_extra": {"example": {"detail": "No autenticado o sesión expirada"}}}



class LabelsValuesResponse(BaseModel):
    """Shape comun para los reportes pensados para graficar (FR-016, research.md §5):
    top5 apps, dispositivos, genero, pais, antiguedad de registro."""
    labels: list[str]
    values: list[float]
    percentages: Optional[list[float]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "labels": ["Argentina", "Brasil", "Chile"],
                "values": [120, 45, 10],
                "percentages": [67.8, 25.4, 5.6],
            }
        }
    }


class RegistrationPeriodResponse(LabelsValuesResponse):
    """Shape de GET /registration-period: LabelsValuesResponse + el `period`
    solicitado (bug corregido: usar solo LabelsValuesResponse como response_model
    descartaba silenciosamente este campo de la respuesta real)."""
    period: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "period": "last_month",
                "labels": ["2026-08", "2026-09"],
                "values": [12, 30],
            }
        }
    }


class TokenResponse(BaseModel):
    """Respuesta de login definitivo y de prueba (data-model.md §4)."""
    access_token: str
    token_type: str = "bearer"
    expires_at: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOi...",
                "token_type": "bearer",
                "expires_at": 1735689600000,
            }
        }
    }


class TotalUsersDTO(BaseModel):
    total_users: int


class ActiveUsersDTO(BaseModel):
    period: str
    period_key: str
    active_users: int


class ScreenTimeByAgeRangeDTO(BaseModel):
    age_range: str
    avg_minutes: Optional[float]


class ChallengesSummaryDTO(BaseModel):
    total_challenges: int
    avg_challenges_per_user: Optional[float]
    avg_completed_challenges_per_user: Optional[float]


class TopAppDTO(BaseModel):
    package_name: str
    app_label: Optional[str]
    avg_minutes: float


class TasksSummaryDTO(BaseModel):
    avg_tasks_per_user: Optional[float]
    avg_completed_tasks_per_user: Optional[float]
    status_filter: str = "all"


class TaskStatusCountDTO(BaseModel):
    status: str
    count: int


class DeviceCountDTO(BaseModel):
    device: Optional[str]
    count: int


class RegistrationBucketDTO(BaseModel):
    bucket: str
    count: int


class AverageAgeDTO(BaseModel):
    avg_age: Optional[float]


class GenderPercentageDTO(BaseModel):
    gender: Optional[str]
    count: int
    percentage: float


class CountryDTO(BaseModel):
    country: Optional[str]
    count: int
    percentage: float
