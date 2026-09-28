"""
T026 — GET /gender (FR-014, FR-016). Exactamente 3 categorias fijas + "sin dato",
en formato labels/values con percentages que suman 100%.
"""


def test_gender_devuelve_4_categorias_labels_values_percentages_100(client, mock_repo, admin_token):
    resp = client.get("/api/admin/analytics/gender", headers=admin_token)
    assert resp.status_code == 200
    body = resp.json()

    labels = body.get("labels") or [g["gender"] for g in body.get("genders", [])]
    assert set(labels) == {"Hombre", "Mujer", "No binario", "sin dato"}

    percentages = body.get("percentages") or [g["percentage"] for g in body.get("genders", [])]
    assert round(sum(percentages), 2) == 100.0


def test_gender_sin_token_401(client, mock_repo):
    resp = client.get("/api/admin/analytics/gender")
    assert resp.status_code == 401
