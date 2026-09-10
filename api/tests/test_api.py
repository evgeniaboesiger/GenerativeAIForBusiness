import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.db import session as db_session
from app.db.models import (
    AgentLog,
    Candidate,
    Experience,
    Job,
    Match,
    MatchingLog,
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
            db.query(Match).filter(Match.job_id == jid).delete(synchronize_session=False)
            db.query(MatchingLog).filter(MatchingLog.job_id == jid).delete(
                synchronize_session=False
            )
            db.query(Job).filter(Job.id == jid).delete(synchronize_session=False)
        for cid in ids:
            db.query(Match).filter(Match.candidate_id == cid).delete(synchronize_session=False)
            db.query(MatchingLog).filter(MatchingLog.candidate_id == cid).delete(
                synchronize_session=False
            )
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


def test_health_endpoints():
    for prefix, expected in [("/auth/health", "auth ok"), ("/candidate/health", "candidate ok"), ("/recruiter/health", "recruiter ok")]:
        res = client.get(prefix)
        assert res.status_code == 200
        assert res.json()["status"] == expected


def test_get_db_generator_closes_session():
    import pytest

    gen = db_session.get_db()
    db = next(gen)
    assert db is not None
    with pytest.raises(StopIteration):
        next(gen)


def test_list_candidates_and_jobs():
    db = SessionLocal()
    try:
        c = _new_candidate(db)
        j = _new_job(db, company="ACME", location="Bern")
        cid, jid = c.id, j.id
    finally:
        db.close()

    try:
        res = client.get("/api/candidates")
        assert res.status_code == 200
        found = [c for c in res.json() if c["id"] == cid]
        assert len(found) == 1
        assert found[0]["name"] == "Test Candidate"

        res = client.get("/api/jobs")
        assert res.status_code == 200
        found = [j for j in res.json() if j["id"] == jid]
        assert len(found) == 1
        assert found[0]["company"] == "ACME"
        assert found[0]["employment_percentage_min"] == found[0]["employment_percentage_max"]
    finally:
        _cleanup(ids=[cid], job_ids=[jid])


def test_get_job_fields_and_404():
    db = SessionLocal()
    try:
        j = _new_job(db, company="ACME", salary_min=90000, salary_max=120000)
        j.title = "Backend"
        db.commit()
        jid = j.id
    finally:
        db.close()

    try:
        res = client.get(f"/api/jobs/{jid}")
        assert res.status_code == 200
        body = res.json()
        assert body["title"] == "Backend"
        assert body["salary_min"] == 90000
        assert body["salary_max"] == 120000
        assert body["employment_percentage_min"] == body["employment_percentage_max"]
        assert body["remote_percentage"] == 0
        assert body["required_skills"] is None

        res = client.get("/api/jobs/9999999")
        assert res.status_code == 404
    finally:
        _cleanup(job_ids=[jid])


def test_match_get_is_read_only_post_writes_log():
    db = SessionLocal()
    try:
        c = _new_candidate(db, location="Zurich")
        c.experiences.append(Experience(company="A", job_title="Dev", start_date=date(2019, 1, 1), end_date=date(2023, 6, 30)))
        c.salary_min = 90000
        c.salary_max = 120000
        j = _new_job(db, company="ACME", location="Zurich", salary_min=90000, salary_max=120000)
        j.title = "Dev"
        db.commit()
        cid, jid = c.id, j.id
    finally:
        db.close()

    try:
        res = client.get(f"/api/matching/candidate/{cid}/job/{jid}")
        assert res.status_code == 200
        assert "overall_score" in res.json()

        db = SessionLocal()
        try:
            assert db.query(MatchingLog).filter(MatchingLog.candidate_id == cid, MatchingLog.job_id == jid).count() == 0
        finally:
            db.close()

        res = client.post(f"/api/matching/candidate/{cid}/job/{jid}")
        assert res.status_code == 200

        db = SessionLocal()
        try:
            assert db.query(MatchingLog).filter(MatchingLog.candidate_id == cid, MatchingLog.job_id == jid).count() == 1
        finally:
            db.close()
    finally:
        _cleanup(ids=[cid], job_ids=[jid])


def test_match_404_for_missing_candidate_or_job():
    db = SessionLocal()
    try:
        j = _new_job(db)
        jid = j.id
    finally:
        db.close()
    try:
        res = client.get(f"/api/matching/candidate/9999999/job/{jid}")
        assert res.status_code == 404
        res = client.post(f"/api/matching/candidate/9999999/job/{jid}")
        assert res.status_code == 404
        res = client.get(f"/api/matching/candidate/9999999")
        assert res.status_code == 404
        res = client.get("/api/matching/job/9999999")
        assert res.status_code == 404
    finally:
        _cleanup(job_ids=[jid])


def test_match_candidate_all_ranked():
    db = SessionLocal()
    try:
        c = _new_candidate(db, location="Zurich")
        c.experiences.append(Experience(company="A", job_title="Dev", start_date=date(2019, 1, 1), end_date=date(2023, 6, 30)))
        j1 = _new_job(db, company="ACME", location="Zurich")
        j1.title = "Dev"
        j2 = _new_job(db, company="Other", location="Geneva")
        j2.title = "Sales PM"
        db.commit()
        cid, j1id, j2id = c.id, j1.id, j2.id
    finally:
        db.close()
    try:
        res = client.get(f"/api/matching/candidate/{cid}")
        assert res.status_code == 200
        body = res.json()
        assert len(body) >= 1
        scores = [r["overall_score"] for r in body]
        assert scores == sorted(scores, reverse=True)
    finally:
        _cleanup(ids=[cid], job_ids=[j1id, j2id])


def test_match_job_all_ranked():
    db = SessionLocal()
    try:
        j = _new_job(db, company="ACME", location="Zurich")
        j.title = "Dev"
        c1 = _new_candidate(db, location="Zurich")
        c2 = _new_candidate(db, location="Geneva")
        jid, c1id, c2id = j.id, c1.id, c2.id
        db.commit()
    finally:
        db.close()
    try:
        res = client.get(f"/api/matching/job/{jid}")
        assert res.status_code == 200
        body = res.json()
        assert len(body) >= 1
        scores = [r["overall_score"] for r in body]
        assert scores == sorted(scores, reverse=True)
    finally:
        _cleanup(ids=[c1id, c2id], job_ids=[jid])


def test_assessment_questions_endpoint():
    res = client.get("/api/assessment/questions")
    assert res.status_code == 200
    body = res.json()
    assert len(body["personality_questions"]) == 40
    assert len(body["value_questions"]) == 13
    assert len(body["personality_dimensions"]) == 4
    assert len(body["company_values"]) == 14


def test_assessment_404s_for_unknown_candidate():
    res = client.post("/api/assessment/personality", json={"candidate_id": 9999999, "responses": {"mind_1": 5}})
    assert res.status_code == 404

    res = client.post("/api/assessment/values", json={"candidate_id": 9999999, "responses": {"value_1": 5}})
    assert res.status_code == 404


def test_profile_endpoints_404_for_unknown_candidate():
    res = client.post("/api/profile/extract", json={"candidate_id": 9999999, "cv_text": "Test CV"})
    assert res.status_code == 404

    res = client.post(
        "/api/profile/candidate/9999999/review",
        json={"candidate_id": 9999999, "profile": {"name": "Nope"}},
    )
    assert res.status_code == 404


def test_update_preferences_full_field_set():
    db = SessionLocal()
    try:
        c = _new_candidate(db)
        cid = c.id
    finally:
        db.close()
    try:
        payload = {
            "preference_tiers": {"employment_percentage": {"ideal": [100, 100]}},
            "salary_min": 70000,
            "salary_max": 95000,
            "remote_preference": "hybrid",
            "employment_percentage": 100,
        }
        res = client.put(f"/api/candidates/{cid}/preferences", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["preference_tiers"]["employment_percentage"]["ideal"] == [100, 100]
        assert body["salary_max"] == 95000
        assert body["remote_preference"] == "hybrid"
    finally:
        _cleanup(ids=[cid])


def test_job_values_update_with_personality_preferences():
    db = SessionLocal()
    try:
        j = _new_job(db)
        jid = j.id
    finally:
        db.close()
    try:
        res = client.post(
            f"/api/assessment/job/{jid}/values",
            json={"company_values": ["excellence"], "personality_preferences": {"nature": {"pole": "right", "importance": 1}}},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["company_values"] == ["excellence"]
        assert body["personality_preferences"]["nature"]["pole"] == "right"
    finally:
        _cleanup(job_ids=[jid])


def test_workflow_get_returns_agent_history():
    db = SessionLocal()
    try:
        wf = Workflow(
            workflow_id="aaaa0000-0000-0000-0000-00000000001",
            candidate_id=1,
            job_id=1,
            state="RUNNING",
        )
        db.add(wf)
        db.flush()
        db.add(AgentLog(workflow_id=wf.workflow_id, agent="ProfileAgent", status="completed"))
        db.commit()
        wid = wf.workflow_id
    finally:
        db.close()
    try:
        res = client.get(f"/api/workflows/{wid}")
        assert res.status_code == 200
        history = res.json()["agent_history"]
        assert len(history) == 1
        assert history[0]["agent"] == "ProfileAgent"
        assert history[0]["status"] == "completed"
        assert history[0]["estimated_cost"] == 0.0
    finally:
        _cleanup(workflow_ids=[wid])
def test_years_experience_skips_experience_without_start_date():
    db = SessionLocal()
    try:
        c = Candidate(name="yearless", email="yearless@example.com")
        db.add(c); db.flush()
        db.add(Experience(candidate_id=c.id, job_title="Dev", company="X",
                           start_date=None, end_date=None))
        db.commit()
        c = db.get(Candidate, c.id)
        assert c.years_experience == 0
    finally:
        db.rollback()
        db.query(Experience).filter_by(company="X").delete(synchronize_session=False)
        db.query(Candidate).filter_by(email="yearless@example.com").delete(synchronize_session=False)
        db.commit()
        db.close()
