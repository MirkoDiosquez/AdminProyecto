"""
T029 — GET /tasks/summary?status=not-completed (FR-009). Usa status != 'completed',
no asume un valor literal como 'pending' (discrepancia conocida corregida).
"""


def test_tasks_summary_not_completed_usa_filtro_real_no_pending_hardcodeado(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/tasks/summary",
        params={"status": "not-completed"},
        headers=admin_token,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status_filter"] == "not-completed"
    assert body["avg_completed_tasks_per_user"] != body["avg_tasks_per_user"]


def test_tasks_summary_status_invalido_devuelve_422(client, mock_repo, admin_token):
    resp = client.get(
        "/api/admin/analytics/tasks/summary",
        params={"status": "no-existe"},
        headers=admin_token,
    )
    assert resp.status_code == 422
