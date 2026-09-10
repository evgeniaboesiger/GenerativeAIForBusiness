import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.db.models import (
    AgentLog,
    Candidate,
    Experience,
    Job,
    ProfileExtraction,
    ProfileReview,
    Workflow,
)
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _new_candidate(db, **kw):
    c = Candidate(name="Test Candidate", email=f"test-{uuid.uuid4()}@example.com", **kw)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _new_job(db, **kw):
    j = Job(title="Test Job", **kw)
    db.add(j)
    db.commit()
    db.refresh(j)
    return j


def _cleanup(ids=(), job_ids=(), workflow_ids=()):
    db = SessionLocal()
    try:
        db.query(ProfileReview).filter(ProfileReview.candidate_id.in_(ids)).delete(
            synchronize_session=False
        )
        db.query(ProfileExtraction).filter(ProfileExtraction.candidate_id.in_(ids)).delete(
            synchronize_session=False
        )
        for wid in workflow_ids:
            db.query(AgentLog).filter(AgentLog.workflow_id == wid).delete(
                synchronize_session=False
            )
            db.query(Workflow).filter(Workflow.workflow_id == wid).delete(
                synchronize_session=False
            )
        for jid in job_ids:
            db.query(Job).filter(Job.id == jid).delete(synchronize_session=False)
        for cid in ids:
            c = db.query(Candidate).filter(Candidate.id == cid).first()
            if c:
                db.delete(c)
        db.commit()
    finally:
        db.close()


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


def test_candidate_preferences_round_trip():
    db = SessionLocal()
    try:
        c = _new_candidate(db)
    finally:
        db.close()

    try:
        res = client.get(f"/api/candidates/{c.id}/preferences")
        assert res.status_code == 200
        assert res.json()["salary_min"] is None

        payload = {"salary_min": 90000, "remote_preference": "remote", "employment_percentage": 80}
        res = client.put(f"/api/candidates/{c.id}/preferences", json=payload)
        assert res.status_code == 200
        assert res.json()["salary_min"] == 90000
        assert res.json()["remote_preference"] == "remote"
        assert res.json()["employment_percentage"] == 80

        res = client.get(f"/api/candidates/{c.id}/preferences")
        assert res.json()["salary_min"] == 90000

        # Empty payload is a no-op, not an error.
        res = client.put(f"/api/candidates/{c.id}/preferences", json={})
        assert res.status_code == 200
    finally:
        _cleanup(ids=[c.id])


def test_years_experience_derives_from_experiences():
    db = SessionLocal()
    try:
        c1 = _new_candidate(db)
        c1.experiences.append(
            Experience(company="A", job_title="Dev", start_date=date(2019, 1, 1), end_date=date(2023, 6, 30))
        )
        c2 = _new_candidate(db)
        c2.experiences.append(Experience(company="B", job_title="Dev", start_date=date(2020, 1, 1)))
        db.commit()
        ids = [c1.id, c2.id]
    finally:
        db.close()

    try:
        res = client.get(f"/api/candidates/{c1.id}")
        assert res.status_code == 200
        assert res.json()["years_experience"] == 4

        # Ongoing entry (no end date) counts up to the current year (2026).
        res = client.get(f"/api/candidates/{c2.id}")
        assert res.json()["years_experience"] == 6
    finally:
        _cleanup(ids=ids)


def test_profile_extract_review_round_trip():
    db = SessionLocal()
    try:
        c = _new_candidate(db)
    finally:
        db.close()

    try:
        res = client.post(
            "/api/profile/extract",
            json={"candidate_id": c.id, "cv_text": "Anna Test\nPython, SQL.\nExperience: 2019-2023 Developer, Atlassian"},
        )
        assert res.status_code == 200

        res = client.get(f"/api/profile/candidate/{c.id}")
        assert res.status_code == 200
        assert "profile" in res.json()

        res = client.post(
            f"/api/profile/candidate/{c.id}/review",
            json={"candidate_id": c.id, "profile": {"name": "Anna Test"}, "notes": "confirmed"},
        )
        assert res.status_code == 200
        assert res.json()["review_status"] == "candidate_confirmed"

        # Candidate-id mismatch is rejected with 400.
        res = client.post(
            f"/api/profile/candidate/{c.id}/review",
            json={"candidate_id": 9999999, "profile": {"name": "Anna Test"}},
        )
        assert res.status_code == 400

        res = client.get("/api/profile/candidate/9999999")
        assert res.status_code == 404
    finally:
        _cleanup(ids=[c.id])


def test_job_values_update_and_missing_job():
    db = SessionLocal()
    try:
        j = _new_job(db)
    finally:
        db.close()

    try:
        res = client.post(f"/api/assessment/job/{j.id}/values", json={"company_values": ["innovation", "agility"]})
        assert res.status_code == 200
        assert res.json()["company_values"] == ["innovation", "agility"]

        res = client.post("/api/assessment/job/9999999/values", json={"company_values": ["innovation"]})
        assert res.status_code == 404

        res = client.post(f"/api/assessment/job/{j.id}/values", json={})
        assert res.status_code == 422
    finally:
        _cleanup(job_ids=[j.id])


def test_workflow_start_get_round_trip():
    db = SessionLocal()
    try:
        c = _new_candidate(db)
        j = _new_job(db)
        cid, jid = c.id, j.id
    finally:
        db.close()

    wid = None
    try:
        res = client.post(f"/api/workflows/start/{cid}/{jid}")
        assert res.status_code == 200
        wid = res.json()["workflow_id"]

        res = client.get(f"/api/workflows/{wid}")
        assert res.status_code == 200
        body = res.json()
        assert body["workflow_id"] == wid
        assert body["state"]

        res = client.get("/api/workflows/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404
    finally:
        _cleanup(ids=[cid], job_ids=[jid], workflow_ids=[wid] if wid else [])


def test_personality_and_values_persist_for_candidate():
    db = SessionLocal()
    try:
        c = _new_candidate(db)
    finally:
        db.close()

    try:
        res = client.post(
            "/api/assessment/personality",
            json={"candidate_id": c.id, "responses": {"mind_2": 7}},
        )
        assert res.status_code == 200

        res = client.post(
            "/api/assessment/values",
            json={"candidate_id": c.id, "responses": {"value_1": 4}},
        )
        assert res.status_code == 200

        res = client.get(f"/api/assessment/candidate/{c.id}")
        assert res.status_code == 200
        body = res.json()
        assert body["personality"] is not None
        assert body["values"] is not None

        res = client.get("/api/assessment/candidate/9999999")
        assert res.status_code == 404
    finally:
        _cleanup(ids=[c.id])


def test_admin_impact_ok():
    res = client.get("/admin/impact")
    assert res.status_code == 200