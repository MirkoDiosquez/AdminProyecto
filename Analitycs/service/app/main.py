"""
Punto de entrada de la API de Reportes/Analytics del Panel Admin.
Panel Admin (React) -> este servicio -> Redis -> PostgreSQL.
Nunca accede a Firestore directamente (arquitectura definida en constitution.md).
"""
from fastapi import FastAPI
from app.routers.analytics_router import router as analytics_router

app = FastAPI(title="Admin Analytics Service", version="1.0.0")
app.include_router(analytics_router)


@app.get("/health")
def health():
    return {"status": "ok"}
