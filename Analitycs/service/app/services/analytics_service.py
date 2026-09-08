"""
Service de Analytics: AnalyticsController -> AnalyticsService -> Redis (cache)
-> si MISS -> AnalyticsRepository (PostgreSQL).

Ninguna lógica de negocio vive en el router/controller.
"""
import datetime as dt
from typing import Optional
from app.cache.analytics_cache import cached
from app.config import settings
from app.repositories.analytics_repository import analytics_repository as repo

KEY_PREFIX = "admin:analytics"


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
        return {"top_apps": value}

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

    def tasks_summary(self) -> dict:
        avg_key = f"{KEY_PREFIX}:tasks:average"
        completed_key = f"{KEY_PREFIX}:tasks:completed-average"
        return {
            "avg_tasks_per_user": cached(avg_key, settings.cache_ttl_default,
                                          repo.average_tasks_per_user),
            "avg_completed_tasks_per_user": cached(completed_key, settings.cache_ttl_default,
                                                    repo.average_completed_tasks_per_user),
        }

    def tasks_by_status(self, status_filter: Optional[str] = "all") -> dict:
        key = f"{KEY_PREFIX}:tasks:{status_filter or 'all'}"
        value = cached(key, settings.cache_ttl_default,
                        lambda: repo.tasks_by_status(status_filter))
        return {"status_filter": status_filter or "all", "items": value}

    def users_by_device(self) -> dict:
        key = f"{KEY_PREFIX}:devices"
        value = cached(key, settings.cache_ttl_slow, repo.users_by_device)
        return {"devices": value}

    def users_by_registration_period(self, period: str) -> dict:
        """
        period: 'last_week' | 'last_month' | 'last_3_months' | 'last_year' | 'all'
        """
        now = dt.datetime.now(dt.timezone.utc)
        deltas = {
            "last_week": dt.timedelta(days=7),
            "last_month": dt.timedelta(days=30),
            "last_3_months": dt.timedelta(days=90),
            "last_year": dt.timedelta(days=365),
        }
        since_ms = None
        if period in deltas:
            since_ms = int((now - deltas[period]).timestamp() * 1000)

        key = f"{KEY_PREFIX}:registration-age:{period}"
        value = cached(key, settings.cache_ttl_slow,
                        lambda: repo.users_by_registration_period(since_ms, None))
        return {"period": period, "buckets": value}

    def average_user_age(self) -> dict:
        key = f"{KEY_PREFIX}:age:average"
        value = cached(key, settings.cache_ttl_slow, repo.average_user_age)
        return {"avg_age": value}

    def users_by_gender(self) -> dict:
        key = f"{KEY_PREFIX}:gender"
        value = cached(key, settings.cache_ttl_slow, repo.users_by_gender)
        return {"genders": value}

    def users_by_country(self, country: Optional[str] = None) -> dict:
        key = f"{KEY_PREFIX}:country:{country.lower() if country else 'global'}"
        value = cached(key, settings.cache_ttl_slow,
                        lambda: repo.users_by_country(country))
        return {"country_filter": country, "items": value}


analytics_service = AnalyticsService()
