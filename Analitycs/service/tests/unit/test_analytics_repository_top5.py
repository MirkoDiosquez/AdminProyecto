"""
T038 — top_five_apps_by_screen_time() con apps empatadas en avg_minutes debe
devolver siempre el mismo orden (desempate alfabetico por app_label), ejecutado
varias veces para probar la propiedad "Repeatable" de F.I.R.S.T. Requiere
PostgreSQL de test con el fixture aplicado (2 apps empatadas en 50.0: Epsilon/Zeta).
"""
import pytest


@pytest.mark.postgres
def test_top5_desempate_alfabetico_es_estable_entre_llamadas():
    from app.repositories.analytics_repository import analytics_repository as repo

    first_run = repo.top_five_apps_by_screen_time()
    second_run = repo.top_five_apps_by_screen_time()

    assert first_run == second_run

    empatadas = [r for r in first_run if r["avg_minutes"] == 50.0]
    labels = [r["app_label"] for r in empatadas]
    assert labels == sorted(labels)
