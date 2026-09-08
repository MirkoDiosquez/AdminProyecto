"""
Repository de Analytics — todas las consultas contra PostgreSQL.
Todos los cálculos (COUNT/AVG/SUM/GROUP BY/FILTER) se hacen en SQL,
nunca trayendo filas a memoria para calcular en Python.
"""
from typing import Optional
from app.db.postgres import get_pool


class AnalyticsRepository:

    # ---------- Usuarios ----------
    def total_users(self) -> int:
        with get_pool().connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM dim_users").fetchone()
            return row[0]

    def active_users(self, period: str, period_key: str) -> int:
        """
        period: 'day' | 'week' | 'month'
        period_key: 'YYYY-MM-DD' | 'YYYY-WW' | 'YYYY-MM'
        """
        if period == "day":
            sql = """
                SELECT COUNT(DISTINCT user_id) FROM fact_user_activity
                WHERE activity_date = %s
            """
        elif period == "week":
            sql = """
                SELECT COUNT(DISTINCT user_id) FROM fact_user_activity
                WHERE to_char(to_date(activity_date, 'YYYY-MM-DD'), 'IYYY-IW') = %s
            """
        elif period == "month":
            sql = """
                SELECT COUNT(DISTINCT user_id) FROM fact_user_activity
                WHERE substring(activity_date from 1 for 7) = %s
            """
        else:
            raise ValueError("period debe ser day|week|month")

        with get_pool().connection() as conn:
            row = conn.execute(sql, (period_key,)).fetchone()
            return row[0]

    def active_users_total(self) -> int:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT COUNT(DISTINCT user_id) FROM fact_user_activity"
            ).fetchone()
            return row[0]

    # ---------- Screen time ----------
    def average_screen_time_by_age_range(self, min_age: int, max_age: int) -> Optional[float]:
        sql = """
            SELECT AVG(fap.minutes_used)
            FROM fact_app_usage fap
            JOIN dim_users u ON u.user_id = fap.user_id
            WHERE u.age BETWEEN %s AND %s
        """
        with get_pool().connection() as conn:
            row = conn.execute(sql, (min_age, max_age)).fetchone()
            return row[0]

    def top_five_apps_by_screen_time(self):
        sql = """
            SELECT package_name, MAX(app_label) AS app_label, AVG(minutes_used) AS avg_minutes
            FROM fact_app_usage
            GROUP BY package_name
            ORDER BY avg_minutes DESC
            LIMIT 5
        """
        with get_pool().connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [
                {"package_name": r[0], "app_label": r[1], "avg_minutes": float(r[2])}
                for r in rows
            ]

    # ---------- Challenges ----------
    def total_challenges(self) -> int:
        with get_pool().connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM fact_challenges").fetchone()
            return row[0]

    def average_challenges_per_user(self) -> Optional[float]:
        sql = """
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) AS cnt FROM fact_challenges GROUP BY user_id
            ) t
        """
        with get_pool().connection() as conn:
            row = conn.execute(sql).fetchone()
            return row[0]

    def average_completed_challenges_per_user(self) -> Optional[float]:
        sql = """
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) FILTER (WHERE status = 'completed') AS cnt
                FROM fact_challenges GROUP BY user_id
            ) t
        """
        with get_pool().connection() as conn:
            row = conn.execute(sql).fetchone()
            return row[0]

    # ---------- Tasks ----------
    def average_tasks_per_user(self) -> Optional[float]:
        sql = """
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) AS cnt FROM fact_tasks GROUP BY user_id
            ) t
        """
        with get_pool().connection() as conn:
            row = conn.execute(sql).fetchone()
            return row[0]

    def average_completed_tasks_per_user(self) -> Optional[float]:
        sql = """
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) FILTER (WHERE status = 'completed') AS cnt
                FROM fact_tasks GROUP BY user_id
            ) t
        """
        with get_pool().connection() as conn:
            row = conn.execute(sql).fetchone()
            return row[0]

    def tasks_by_status(self, status_filter: Optional[str] = None):
        if status_filter and status_filter != "all":
            sql = "SELECT status, COUNT(*) FROM fact_tasks WHERE status = %s GROUP BY status"
            params = (status_filter,)
        else:
            sql = "SELECT status, COUNT(*) FROM fact_tasks GROUP BY status"
            params = ()
        with get_pool().connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [{"status": r[0], "count": r[1]} for r in rows]

    # ---------- Devices ----------
    def users_by_device(self):
        sql = """
            SELECT device, COUNT(*) FROM dim_users
            GROUP BY device ORDER BY COUNT(*) DESC
        """
        with get_pool().connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [{"device": r[0], "count": r[1]} for r in rows]

    # ---------- Registro ----------
    def users_by_registration_period(self, since_epoch_ms: Optional[int] = None,
                                       until_epoch_ms: Optional[int] = None):
        """
        Agrupa usuarios por mes de registro (epoch ms -> 'YYYY-MM'),
        con filtro opcional de rango (última semana/mes/3 meses/año/custom
        se resuelve en el Service calculando since/until).
        """
        sql = """
            SELECT to_char(to_timestamp(registered_at / 1000.0), 'YYYY-MM') AS bucket,
                   COUNT(*) AS cnt
            FROM dim_users
            WHERE registered_at IS NOT NULL
              AND (%(since)s IS NULL OR registered_at >= %(since)s)
              AND (%(until)s IS NULL OR registered_at <= %(until)s)
            GROUP BY bucket
            ORDER BY bucket
        """
        with get_pool().connection() as conn:
            rows = conn.execute(sql, {"since": since_epoch_ms, "until": until_epoch_ms}).fetchall()
            return [{"bucket": r[0], "count": r[1]} for r in rows]

    # ---------- Demográficos ----------
    def average_user_age(self) -> Optional[float]:
        with get_pool().connection() as conn:
            row = conn.execute("SELECT AVG(age) FROM dim_users WHERE age IS NOT NULL").fetchone()
            return row[0]

    def users_by_gender(self):
        sql = """
            SELECT gender, COUNT(*) AS cnt,
                   ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM dim_users), 0), 2) AS pct
            FROM dim_users
            GROUP BY gender
            ORDER BY cnt DESC
        """
        with get_pool().connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [{"gender": r[0], "count": r[1], "percentage": float(r[2] or 0)} for r in rows]

    def users_by_country(self, country_filter: Optional[str] = None):
        sql = """
            SELECT country, COUNT(*) AS cnt,
                   ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM dim_users), 0), 2) AS pct
            FROM dim_users
            WHERE (%(country)s IS NULL OR country = %(country)s)
            GROUP BY country
            ORDER BY cnt DESC
        """
        with get_pool().connection() as conn:
            rows = conn.execute(sql, {"country": country_filter}).fetchall()
            return [{"country": r[0], "count": r[1], "percentage": float(r[2] or 0)} for r in rows]


analytics_repository = AnalyticsRepository()
