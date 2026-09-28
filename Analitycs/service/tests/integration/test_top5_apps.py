"""
T039 — GET /apps/top5 (FR-008, FR-016). Shape labels/values, exactamente 5 items.
"""


def test_top5_apps_devuelve_labels_values_con_5_items(client, mock_repo, admin_token):
    resp = client.get("/api/admin/analytics/apps/top5", headers=admin_token)
    assert resp.status_code == 200
    body = resp.json()

    labels = body.get("labels") or [a["app_label"] for a in body.get("top_apps", [])]
    values = body.get("values") or [a["avg_minutes"] for a in body.get("top_apps", [])]

    assert len(labels) == 5
    assert len(values) == 5
    assert values == sorted(values, reverse=True)
