"""
Capa de cache genérica para Analytics.

Flujo (obligatorio para todo endpoint de Analytics):
    1. Buscar clave en Redis.
    2. HIT  -> devolver valor cacheado (no tocar PostgreSQL).
    3. MISS -> ejecutar `loader()` contra PostgreSQL, guardar en Redis con TTL,
       devolver el resultado.
"""
import json
from typing import Any, Callable
from app.db.redis_client import get_redis


def cached(key: str, ttl_seconds: int, loader: Callable[[], Any]) -> Any:
    r = get_redis()
    hit = r.get(key)
    if hit is not None:
        return json.loads(hit)

    value = loader()
    r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    return value


def invalidate(*keys: str) -> None:
    """Invalidar claves puntuales (usado por el ETL luego de cada corrida)."""
    r = get_redis()
    if keys:
        r.delete(*keys)


def invalidate_pattern(pattern: str) -> None:
    """Invalidar todas las claves que matcheen un patrón, ej: 'admin:analytics:*'."""
    r = get_redis()
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match=pattern, count=200)
        if keys:
            r.delete(*keys)
        if cursor == 0:
            break
