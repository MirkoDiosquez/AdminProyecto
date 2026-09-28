"""
AuthService — login de administrador (T019). No hay tabla de admins en
PostgreSQL (FR-020): las credenciales validas son las de `settings` (env vars).
"""
from fastapi import HTTPException

from app.config import settings
from app.core.security import issue_session_token, verify_password
from app.core.timezone import resolve_client_timezone
from app.dto.analytics_dto import LoginRequest


class AuthService:

    def login(self, request: LoginRequest) -> dict:
        """Login definitivo (FR-001/002/020). Responde 401 generico tanto si el
        usuario no coincide como si el password no coincide, sin distinguir cual
        de los dos fallo (edge case de spec.md)."""
        if not self._credenciales_validas(request.username, request.password):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

        tz = resolve_client_timezone(request.timezone)
        token, exp_ms = issue_session_token(request.username, tz)
        return {"access_token": token, "token_type": "bearer", "expires_at": exp_ms}

    def _credenciales_validas(self, username: str, password: str) -> bool:
        return username == settings.admin_username and verify_password(
            password, settings.admin_password_hash
        )

    def test_login(self, request: LoginRequest) -> dict:
        """Login de prueba EXCLUSIVO para Swagger (T050, FR-031). Comparacion
        directa sin hash — relajacion explicita permitida solo aqui, nunca usar
        en produccion."""
        if not (
            request.username == settings.test_admin_user
            and request.password == settings.test_admin_password
        ):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

        tz = resolve_client_timezone(request.timezone)
        token, exp_ms = issue_session_token(request.username, tz)
        return {"access_token": token, "token_type": "bearer", "expires_at": exp_ms}


auth_service = AuthService()
