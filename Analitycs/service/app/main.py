"""
Punto de entrada de la API de Reportes/Analytics del Panel Admin.
Panel Admin (React) -> este servicio -> Redis -> PostgreSQL.
Nunca accede a Firestore directamente (arquitectura definida en constitution.md).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers.analytics_router import router as analytics_router
from app.routers.auth_router import router as auth_router
from app.routers.internal_router import router as internal_router

logger = logging.getLogger(__name__)

# FR-032: Swagger UI (/docs, /redoc, /openapi.json) solo se expone en entornos de
# desarrollo/QA (seguro-por-defecto); cualquier otro valor de ENVIRONMENT lo oculta.
_docs_enabled = settings.environment in ("development", "qa")

app = FastAPI(
    title="Admin Analytics Service",
    version="1.0.0",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(internal_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """FR-018: ningun error no controlado debe exponer stack trace, nombres de
    tabla, ni mensajes crudos de psycopg/redis-py al cliente."""
    logger.exception("Error no controlado procesando %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal_error"})


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "opaque-hmac",
    }
    schema["security"] = [{"bearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health")
def health():
    return {"status": "ok"}

