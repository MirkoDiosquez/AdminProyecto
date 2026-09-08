"""
AnalyticsController — expone endpoints REST para el Panel Admin.
No contiene lógica de negocio ni SQL: delega todo a AnalyticsService.
"""
from typing import Optional
from fastapi import APIRouter, Query
from app.services.analytics_service import analytics_service as service

router = APIRouter(prefix="/api/admin/analytics", tags=["analytics"])


@router.get("/users/total")
def total_users():
    return service.total_users()


@router.get("/users/active")
def active_users(
    period: str = Query(..., pattern="^(day|week|month|total)$"),
    period_key: Optional[str] = Query(None, description="'YYYY-MM-DD'|'YYYY-WW'|'YYYY-MM'"),
):
    if period == "total":
        return service.active_users_total()
    if not period_key:
        return {"error": "period_key es requerido para period=day|week|month"}
    return service.active_users(period, period_key)


@router.get("/screen-time/age-range")
def screen_time_age_range(min_age: int = Query(...), max_age: int = Query(...)):
    return service.average_screen_time_by_age_range(min_age, max_age)


@router.get("/apps/top5")
def top_five_apps():
    return service.top_five_apps()


@router.get("/challenges/summary")
def challenges_summary():
    return service.challenges_summary()


@router.get("/tasks/summary")
def tasks_summary():
    return service.tasks_summary()


@router.get("/tasks/by-status")
def tasks_by_status(status: Optional[str] = Query("all", pattern="^(completed|not-completed|all)$")):
    mapped = {"completed": "completed", "not-completed": "pending", "all": "all"}
    return service.tasks_by_status(mapped.get(status, "all"))


@router.get("/devices")
def users_by_device():
    return service.users_by_device()


@router.get("/registration-period")
def users_by_registration_period(
    period: str = Query("all", pattern="^(last_week|last_month|last_3_months|last_year|all)$")
):
    return service.users_by_registration_period(period)


@router.get("/age/average")
def average_user_age():
    return service.average_user_age()


@router.get("/gender")
def users_by_gender():
    return service.users_by_gender()


@router.get("/country")
def users_by_country(country: Optional[str] = Query(None)):
    return service.users_by_country(country)
