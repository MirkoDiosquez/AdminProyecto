"""
InternalController — endpoint interno llamado por el ETL tras cada corrida
(T052, FR-022, research.md §3). Protegido por secreto compartido
(X-Internal-Secret), no por sesion de administrador humano.
"""
from fastapi import APIRouter, Depends, status

from app.cache.analytics_cache import invalidate_pattern
from app.core.security import require_internal_secret

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post(
    "/cache/invalidate-reports",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidar caché de reportes (uso interno del ETL)",
    description="Borra todas las claves 'admin:analytics:*' de Redis. Debe ser "
    "llamado por el proceso ETL tras cada corrida nocturna (FR-022). Protegido "
    "por X-Internal-Secret, no por sesión de administrador humano.",
    dependencies=[Depends(require_internal_secret)],
)
def invalidate_reports_cache():
    invalidate_pattern("admin:analytics:*")
