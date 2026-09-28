"""
AuthController — login de administrador (T020) y login de prueba para Swagger
(T051). No contiene logica de negocio: delega a AuthService.
"""
from fastapi import APIRouter

from app.dto.analytics_dto import ErrorResponse, LoginRequest, TokenResponse
from app.services.auth_service import auth_service as service

router = APIRouter(prefix="/api/admin/auth")


@router.post(
    "/login",
    response_model=TokenResponse,
    tags=["auth"],
    summary="Login de administrador",
    description="Autentica al administrador con credenciales fijas (env vars, FR-020) "
    "y emite una sesion que expira a medianoche en la timezone indicada.",
    responses={401: {"model": ErrorResponse, "description": "Credenciales inválidas"}},
)
def login(body: LoginRequest):
    return service.login(body)


@router.post(
    "/test-login",
    response_model=TokenResponse,
    tags=["auth-test-only"],
    summary="Login de prueba (solo para Swagger)",
    description="Endpoint temporal exclusivo para pruebas — no usar en producción. "
    "Permite ejercitar 'Try it out' en Swagger UI mientras no exista el login definitivo "
    "de usuarios finales.",
    responses={401: {"model": ErrorResponse, "description": "Credenciales inválidas"}},
)
def test_login(body: LoginRequest):
    return service.test_login(body)
