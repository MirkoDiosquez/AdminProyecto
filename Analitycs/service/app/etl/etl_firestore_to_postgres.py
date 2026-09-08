"""
ETL: Firebase/Firestore -> PostgreSQL (dim_users + tablas fact_*).

Diseño IDEMPOTENTE: usa UPSERT (ON CONFLICT) con las claves naturales
definidas en el requerimiento. Ejecutarlo N veces no duplica datos.

Al finalizar cada corrida, invalida las claves de Redis afectadas para que
el próximo request recalcule contra los datos frescos de PostgreSQL.

Este script se corre por cron (ej: 1 vez por noche), igual que el
Data Transformer descripto en arquitectura.md / plan-de-trabajo.txt.
"""
import time
from typing import Any, Iterable

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import settings
from app.db.postgres import get_pool
from app.cache.analytics_cache import invalidate_pattern


def _init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def upsert_users(conn, users: Iterable[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO dim_users
            (user_id, display_name, email, gender, age, country, device,
             registered_at, first_login_at, last_login_at)
        VALUES
            (%(user_id)s, %(display_name)s, %(email)s, %(gender)s, %(age)s,
             %(country)s, %(device)s, %(registered_at)s, %(first_login_at)s,
             %(last_login_at)s)
        ON CONFLICT (user_id) DO UPDATE SET
            display_name   = EXCLUDED.display_name,
            email          = EXCLUDED.email,
            gender         = EXCLUDED.gender,
            age            = EXCLUDED.age,
            country        = EXCLUDED.country,
            device         = EXCLUDED.device,
            last_login_at  = EXCLUDED.last_login_at
    """
    count = 0
    for u in users:
        conn.execute(sql, u)
        count += 1
    return count


def upsert_activity(conn, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO fact_user_activity (user_id, activity_date)
        VALUES (%(user_id)s, %(activity_date)s)
        ON CONFLICT (user_id, activity_date) DO NOTHING
    """
    count = 0
    for r in rows:
        conn.execute(sql, r)
        count += 1
    return count


def upsert_app_usage(conn, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO fact_app_usage
            (user_id, usage_date, package_name, app_label, minutes_used,
             over_limit, limit_min, recorded_at)
        VALUES
            (%(user_id)s, %(usage_date)s, %(package_name)s, %(app_label)s,
             %(minutes_used)s, %(over_limit)s, %(limit_min)s, %(recorded_at)s)
        ON CONFLICT (user_id, usage_date, package_name) DO UPDATE SET
            minutes_used = EXCLUDED.minutes_used,
            over_limit   = EXCLUDED.over_limit,
            limit_min    = EXCLUDED.limit_min,
            recorded_at  = EXCLUDED.recorded_at
    """
    count = 0
    for r in rows:
        conn.execute(sql, r)
        count += 1
    return count


def upsert_challenges(conn, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO fact_challenges
            (user_id, group_id, challenge_id, title, start_date, end_date,
             status, points_reward, points_earned, completed_at, recorded_at)
        VALUES
            (%(user_id)s, %(group_id)s, %(challenge_id)s, %(title)s,
             %(start_date)s, %(end_date)s, %(status)s, %(points_reward)s,
             %(points_earned)s, %(completed_at)s, %(recorded_at)s)
        ON CONFLICT (user_id, challenge_id) DO UPDATE SET
            status         = EXCLUDED.status,
            points_earned  = EXCLUDED.points_earned,
            completed_at   = EXCLUDED.completed_at,
            recorded_at    = EXCLUDED.recorded_at
    """
    count = 0
    for r in rows:
        conn.execute(sql, r)
        count += 1
    return count


def upsert_tasks(conn, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO fact_tasks
            (user_id, task_id, title, status, created_at, completed_at, recorded_at)
        VALUES
            (%(user_id)s, %(task_id)s, %(title)s, %(status)s, %(created_at)s,
             %(completed_at)s, %(recorded_at)s)
        ON CONFLICT (user_id, task_id) DO UPDATE SET
            status       = EXCLUDED.status,
            completed_at = EXCLUDED.completed_at,
            recorded_at  = EXCLUDED.recorded_at
    """
    count = 0
    for r in rows:
        conn.execute(sql, r)
        count += 1
    return count


def upsert_user_groups(conn, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO fact_user_groups
            (user_id, group_id, group_name, joined_at, left_at, is_active)
        VALUES
            (%(user_id)s, %(group_id)s, %(group_name)s, %(joined_at)s,
             %(left_at)s, %(is_active)s)
        ON CONFLICT (user_id, group_id, joined_at) DO UPDATE SET
            left_at   = EXCLUDED.left_at,
            is_active = EXCLUDED.is_active
    """
    count = 0
    for r in rows:
        conn.execute(sql, r)
        count += 1
    return count


def run_etl():
    """
    NOTA: la lectura concreta de colecciones de Firestore (`/users`, `/usage`,
    `/challenges`, `/tasks`, `/groups`) depende del contrato final acordado
    entre el Área B (API) y el Área C (Admin) — ver constitution.md Sección 2.
    Este esqueleto deja los "extract_*" como puntos de extensión.
    """
    db = _init_firebase()
    pool = get_pool()

    with pool.connection() as conn:
        users = extract_users(db)
        n_users = upsert_users(conn, users)

        activity = extract_activity(db)
        n_activity = upsert_activity(conn, activity)

        usage = extract_app_usage(db)
        n_usage = upsert_app_usage(conn, usage)

        challenges = extract_challenges(db)
        n_challenges = upsert_challenges(conn, challenges)

        tasks = extract_tasks(db)
        n_tasks = upsert_tasks(conn, tasks)

        groups = extract_user_groups(db)
        n_groups = upsert_user_groups(conn, groups)

    invalidate_pattern("admin:analytics:*")

    return {
        "users": n_users, "activity": n_activity, "app_usage": n_usage,
        "challenges": n_challenges, "tasks": n_tasks, "user_groups": n_groups,
    }


# ---- Puntos de extensión: extraer datos desde Firestore ----
def extract_users(db) -> Iterable[dict]:
    for doc in db.collection("users").stream():
        d = doc.to_dict()
        yield {
            "user_id": doc.id,
            "display_name": d.get("displayName"),
            "email": d.get("email"),
            "gender": d.get("gender"),
            "age": d.get("age"),
            "country": d.get("country"),
            "device": d.get("device"),
            "registered_at": d.get("registeredAt"),
            "first_login_at": d.get("firstLoginAt"),
            "last_login_at": d.get("lastLoginAt"),
        }


def extract_activity(db) -> Iterable[dict]:
    for doc in db.collection("user_activity").stream():
        d = doc.to_dict()
        yield {"user_id": d.get("userId"), "activity_date": d.get("activityDate")}


def extract_app_usage(db) -> Iterable[dict]:
    for doc in db.collection("app_usage").stream():
        d = doc.to_dict()
        yield {
            "user_id": d.get("userId"), "usage_date": d.get("usageDate"),
            "package_name": d.get("packageName"), "app_label": d.get("appLabel"),
            "minutes_used": d.get("minutesUsed"), "over_limit": d.get("overLimit", False),
            "limit_min": d.get("limitMin"), "recorded_at": d.get("recordedAt", int(time.time() * 1000)),
        }


def extract_challenges(db) -> Iterable[dict]:
    for doc in db.collection("challenges_progress").stream():
        d = doc.to_dict()
        yield {
            "user_id": d.get("userId"), "group_id": d.get("groupId"),
            "challenge_id": d.get("challengeId"), "title": d.get("title"),
            "start_date": d.get("startDate"), "end_date": d.get("endDate"),
            "status": d.get("status"), "points_reward": d.get("pointsReward"),
            "points_earned": d.get("pointsEarned"), "completed_at": d.get("completedAt"),
            "recorded_at": d.get("recordedAt", int(time.time() * 1000)),
        }


def extract_tasks(db) -> Iterable[dict]:
    for doc in db.collection("tasks_sync").stream():
        d = doc.to_dict()
        yield {
            "user_id": d.get("userId"), "task_id": d.get("taskId"),
            "title": d.get("title"), "status": d.get("status"),
            "created_at": d.get("createdAt"), "completed_at": d.get("completedAt"),
            "recorded_at": d.get("recordedAt", int(time.time() * 1000)),
        }


def extract_user_groups(db) -> Iterable[dict]:
    for doc in db.collection("group_memberships").stream():
        d = doc.to_dict()
        yield {
            "user_id": d.get("userId"), "group_id": d.get("groupId"),
            "group_name": d.get("groupName"), "joined_at": d.get("joinedAt"),
            "left_at": d.get("leftAt"), "is_active": d.get("isActive", True),
        }


if __name__ == "__main__":
    result = run_etl()
    print(f"ETL finalizado: {result}")
