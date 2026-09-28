"""
T030 — Test de repositorio: users_by_gender() agrupa valores fuera de catalogo
("otro", NULL) como "sin dato" (FR-014, data-model.md §2.1). Requiere PostgreSQL
de test con el fixture aplicado (tests/fixtures/postgres_fixture.sql); se marca
como test de integracion liviano contra DB real, no usa mocks para no enmascarar
un bug real en el SQL.
"""
import pytest


@pytest.mark.postgres
def test_users_by_gender_agrupa_fuera_de_catalogo_como_sin_dato():
    from app.repositories.analytics_repository import analytics_repository as repo

    rows = repo.users_by_gender()
    genders = {r["gender"] for r in rows}

    # Solo deben existir las 3 categorias fijas + "sin dato"; "otro" (fuera de
    # catalogo, ver fixture u4) y NULL (fixture u5) deben caer en "sin dato".
    assert genders <= {"Hombre", "Mujer", "No binario", "sin dato"}
    assert "otro" not in genders

    sin_dato = next(r for r in rows if r["gender"] == "sin dato")
    assert sin_dato["count"] >= 2  # u4 ('otro') + u5 (NULL)
