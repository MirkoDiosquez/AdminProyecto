"""
DTOs de respuesta de Analytics (Pydantic). El Controller/Service nunca
devuelve filas crudas de PostgreSQL directamente.
"""
from typing import Optional
from pydantic import BaseModel


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
