"""
T040 — GET /challenges/summary (FR-006, FR-007, FR-013). avg_challenges_per_user
(sin filtro) y avg_completed_challenges_per_user (status='completed') deben ser
valores distintos y estar claramente etiquetados.
"""


def test_challenges_summary_avg_general_distinto_de_avg_completadas(client, mock_repo, admin_token):
    resp = client.get("/api/admin/analytics/challenges/summary", headers=admin_token)
    assert resp.status_code == 200
    body = resp.json()

    assert body["avg_challenges_per_user"] == 2.0
    assert body["avg_completed_challenges_per_user"] == 1.0
    assert body["avg_challenges_per_user"] != body["avg_completed_challenges_per_user"]
    assert body["total_challenges"] == 4


def test_challenges_summary_sin_token_401(client, mock_repo):
    resp = client.get("/api/admin/analytics/challenges/summary")
    assert resp.status_code == 401
