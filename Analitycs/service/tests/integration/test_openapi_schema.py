"""
T043 — GET /openapi.json incluye los 13 operationIds de reportes + login/test-login,
cada uno con al menos un codigo de respuesta distinto de 200 documentado (US4).
"""

EXPECTED_PATHS = [
    "/api/admin/analytics/users/total",
    "/api/admin/analytics/users/active",
    "/api/admin/analytics/screen-time/age-range",
    "/api/admin/analytics/apps/top5",
    "/api/admin/analytics/challenges/summary",
    "/api/admin/analytics/tasks/summary",
    "/api/admin/analytics/devices",
    "/api/admin/analytics/registration-period",
    "/api/admin/analytics/age/average",
    "/api/admin/analytics/gender",
    "/api/admin/analytics/country",
    "/api/admin/auth/login",
    "/api/admin/auth/test-login",
]


def test_openapi_incluye_todos_los_endpoints_esperados(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    faltantes = [p for p in EXPECTED_PATHS if p not in paths]
    assert not faltantes, f"Endpoints faltantes en OpenAPI: {faltantes}"


def test_cada_endpoint_documenta_al_menos_un_codigo_distinto_de_200(client):
    schema = client.get("/openapi.json").json()
    for path in EXPECTED_PATHS:
        for method, operation in schema["paths"][path].items():
            responses = set(operation.get("responses", {}).keys())
            assert responses - {"200"}, f"{method.upper()} {path} no documenta codigos de error"


def test_endpoints_estan_agrupados_por_tag(client):
    schema = client.get("/openapi.json").json()
    for path, methods in schema["paths"].items():
        if path in ("/health",):
            continue
        for operation in methods.values():
            assert operation.get("tags"), f"{path} no tiene tag asignado"
