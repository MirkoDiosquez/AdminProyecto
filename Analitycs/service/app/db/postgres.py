"""
Pool de conexiones a PostgreSQL. Fuente persistente y de respaldo de Analytics.
"""
from psycopg_pool import ConnectionPool
from app.config import settings

pool = ConnectionPool(conninfo=settings.postgres_dsn, min_size=1, max_size=10, open=False)


def get_pool() -> ConnectionPool:
    if pool.closed:
        pool.open()
    return pool
