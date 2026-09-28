"""
Service de Analytics: AnalyticsController -> AnalyticsService -> Redis (cache)
-> si MISS -> AnalyticsRepository (PostgreSQL).

Ninguna lógica de negocio vive en el router/controller.
"""
from typing import Optional
from zoneinfo import ZoneInfo

from app.cache.analytics_cache import cached
from app.config import settings
from app.core import timezone as timezone_module
from app.repositories.analytics_repository import analytics_repository as repo

KEY_PREFIX = "admin:analytics"


def to_labels_values(rows: list[dict], label_key: str, value_key: str,
                      percentage_key: Optional[str] = None) -> dict:
    """Transforma una lista de filas (formato tabla cruda) al shape
    labels/values (+percentages opcional) exigido por FR-016 (T037,
    research.md §5), para los reportes pensados para graficar."""
    result = {
        "labels": [row[label_key] if row[label_key] is not None else "sin dato" for row in rows],
        "values": [row[value_key] for row in rows],
    }
    if percentage_key is not None:
        result["percentages"] = [row[percentage_key] for row in rows]
    return result


class AnalyticsService:

    def total_users(self) -> dict:
        key = f"{KEY_PREFIX}:users:total"
        value = cached(key, settings.cache_ttl_default, repo.total_users)
        return {"total_users": value}

    def active_users(self, period: str, period_key: str) -> dict:
        key = f"{KEY_PREFIX}:users:active:{period}:{period_key}"
        value = cached(key, settings.cache_ttl_realtime,
                        lambda: repo.active_users(period, period_key))
        return {"period": period, "period_key": period_key, "active_users": value}

    def active_users_total(self) -> dict:
        key = f"{KEY_PREFIX}:users:active:total"
        value = cached(key, settings.cache_ttl_realtime, repo.active_users_total)
        return {"active_users": value}

    def average_screen_time_by_age_range(self, min_age: int, max_age: int) -> dict:
        key = f"{KEY_PREFIX}:screen-time:age:{min_age}-{max_age}"
        value = cached(key, settings.cache_ttl_default,
                        lambda: repo.average_screen_time_by_age_range(min_age, max_age))
        return {"age_range": f"{min_age}-{max_age}", "avg_minutes": value}

    def top_five_apps(self) -> dict:
        key = f"{KEY_PREFIX}:apps:top5"
        value = cached(key, settings.cache_ttl_default, repo.top_five_apps_by_screen_time)
        return to_labels_values(value, "app_label", "avg_minutes")

    def challenges_summary(self) -> dict:
        total_key = f"{KEY_PREFIX}:challenges:total"
        avg_key = f"{KEY_PREFIX}:challenges:average"
        completed_key = f"{KEY_PREFIX}:challenges:completed-average"
        return {
            "total_challenges": cached(total_key, settings.cache_ttl_default, repo.total_challenges),
            "avg_challenges_per_user": cached(avg_key, settings.cache_ttl_default,
                                               repo.average_challenges_per_user),
            "avg_completed_challenges_per_user": cached(
                completed_key, settings.cache_ttl_default,
                repo.average_completed_challenges_per_user),
        }

    def tasks_summary(self, status_filter: str = "all") -> dict:
        """FR-009: soporta filtro completadas/no completadas/todas, calculando
        el promedio correcto segun `status_filter` (T033, corrige la
        discrepancia conocida de siempre calcular ambos promedios sin filtro)."""
        avg_key = f"{KEY_PREFIX}:tasks:average"
        completed_key = f"{KEY_PREFIX}:tasks:completed-average"
        not_completed_key = f"{KEY_PREFIX}:tasks:not-completed-average"

        avg_tasks = cached(avg_key, settings.cache_ttl_default, repo.average_tasks_per_user)
        if status_filter == "not-completed":
            avg_completed = cached(not_completed_key, settings.cache_ttl_default,
                                    repo.average_not_completed_tasks_per_user)
        else:
            avg_completed = cached(completed_key, settings.cache_ttl_default,
                                    repo.average_completed_tasks_per_user)

        return {
            "avg_tasks_per_user": avg_tasks,
            "avg_completed_tasks_per_user": avg_completed,
            "status_filter": status_filter,
        }

    def tasks_by_status(self, status_filter: Optional[str] = "all") -> dict:
        key = f"{KEY_PREFIX}:tasks:{status_filter or 'all'}"
        value = cached(key, settings.cache_ttl_default,
                        lambda: repo.tasks_by_status(status_filter))
        return {"status_filter": status_filter or "all", "items": value}

    def users_by_device(self) -> dict:
        key = f"{KEY_PREFIX}:devices"
        value = cached(key, settings.cache_ttl_slow, repo.users_by_device)
        return to_labels_values(value, "device", "count")

    def users_by_registration_period(self, period: str, tz: ZoneInfo) -> dict:
        """
        period: 'last_week' | 'last_month' | 'last_3_months' | 'last_year' | 'all'
        tz: zona horaria vigente del cliente (FR-021, resuelta via X-Client-Timezone
        en el router), en vez de UTC fijo (discrepancia conocida corregida, T036).
        """
        since_ms, until_ms = timezone_module.period_bounds_epoch_ms(period, tz)

        key = f"{KEY_PREFIX}:registration-age:{period}"
        value = cached(key, settings.cache_ttl_slow,
                        lambda: repo.users_by_registration_period(since_ms, until_ms))
        return {"period": period, **to_labels_values(value, "bucket", "count")}

    def average_user_age(self) -> dict:
        key = f"{KEY_PREFIX}:age:average"
        value = cached(key, settings.cache_ttl_slow, repo.average_user_age)
        return {"avg_age": value}

    def users_by_gender(self) -> dict:
        key = f"{KEY_PREFIX}:gender"
        value = cached(key, settings.cache_ttl_slow, repo.users_by_gender)
        return to_labels_values(value, "gender", "count", "percentage")

    def users_by_country(self, country: Optional[str] = None) -> dict:
        key = f"{KEY_PREFIX}:country:{country.lower() if country else 'global'}"
        value = cached(key, settings.cache_ttl_slow,
                        lambda: repo.users_by_country(country))
        return to_labels_values(value, "country", "count", "percentage")


analytics_service = AnalyticsService()
