from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_ok():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_missing_candidate_returns_404():
    res = client.get("/api/candidates/9999999")
    assert res.status_code == 404
    res = client.get("/api/candidates/9999999/preferences")
    assert res.status_code == 404


def test_update_preferences_validates_and_404s_for_unknown_candidate():
    # Unknown candidate -> 404, no DB write happens.
    res = client.put("/api/candidates/9999999/preferences", json={"salary_min": 80000})
    assert res.status_code == 404

    # Out-of-range employment -> 422 before any DB access.
    res = client.put("/api/candidates/9999999/preferences", json={"employment_percentage": 150})
    assert res.status_code == 422

    # Negative salary -> 422.
    res = client.put("/api/candidates/9999999/preferences", json={"salary_min": -1000})
    assert res.status_code == 422


def test_assessment_responses_are_range_validated():
    # Personality scores must be 1..7.
    res = client.post("/api/assessment/personality", json={"responses": {"mind_1": 9}})
    assert res.status_code == 422

    # Values scores must be 1..5.
    res = client.post("/api/assessment/values", json={"responses": {"v1": 6}})
    assert res.status_code == 422

    # Valid answers pass validation (no crash on the demo data path).
    res = client.post("/api/assessment/personality", json={"responses": {"mind_1": 5}})
    assert res.status_code == 200