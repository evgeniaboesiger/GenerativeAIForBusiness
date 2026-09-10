import time
import uuid
from datetime import date

from sqlalchemy.orm import selectinload

from app.db.models import AgentLog, Candidate, Experience, Job, Workflow
from app.db.session import SessionLocal
from app.orchestrator import schemas
from app.orchestrator import service as orchestrator_service
from app.orchestrator.service import orchestrator


def _make_candidate(job_like=False, with_experience=True):
    db = SessionLocal()
    try:
        c = Candidate(name="Flow Candidate", email=f"flow-{uuid.uuid4()}@example.com", location="Zurich")
        if with_experience:
            c.experiences.append(
                Experience(company="A", job_title="Dev", start_date=date(2019, 1, 1), end_date=date(2023, 6, 30))
            )
        db.add(c)
        j = Job(title="Flow Job", company="B", location="Zurich", salary_min=90000, salary_max=110000)
        db.add(j)
        db.commit()
        db.refresh(c)
        db.refresh(j)
        return c.id, j.id
    finally:
        db.close()


def _seed_workflow(wf_id, candidate_id, job_id):
    db = SessionLocal()
    try:
        wf = Workflow(
            workflow_id=wf_id,
            candidate_id=candidate_id,
            job_id=job_id,
            state=schemas.WorkflowState.PROFILE_CREATED,
        )
        db.add(wf)
        db.commit()
        db.refresh(wf)
        return wf
    finally:
        db.close()


def _workflow_state(wf_id):
    db = SessionLocal()
    try:
        wf = db.query(Workflow).filter(Workflow.workflow_id == wf_id).first()
        return wf.state if wf else None
    finally:
        db.close()


def _agent_logs(wf_id):
    db = SessionLocal()
    try:
        logs = (
            db.query(AgentLog)
            .filter(AgentLog.workflow_id == wf_id)
            .order_by(AgentLog.start_time.asc())
            .all()
        )
        return [{"agent": l.agent, "status": l.status, "error": l.error} for l in logs]
    finally:
        db.close()


def _cleanup(cid, jid, wf_id):
    db = SessionLocal()
    try:
        db.query(AgentLog).filter(AgentLog.workflow_id == wf_id).delete(synchronize_session=False)
        db.query(Workflow).filter(Workflow.workflow_id == wf_id).delete(synchronize_session=False)
        db.query(Job).filter(Job.id == jid).delete(synchronize_session=False)
        c = db.query(Candidate).filter(Candidate.id == cid).first()
        if c:
            db.delete(c)
        db.commit()
    finally:
        db.close()


def test_workflow_runs_full_chain_to_recruiter_review():
    cid, jid = _make_candidate()
    wf_id = f"aaaa0000-0000-0000-0000-00000000000{1}"  # last hex != 0x0 -> no human review
    _seed_workflow(wf_id, cid, jid)
    try:
        orchestrator._run_profile_and_match(wf_id, cid, jid)
        time.sleep(1.5)  # let the async assessment/follow-up thread finish
        assert _workflow_state(wf_id) == schemas.WorkflowState.RECRUITER_REVIEW
        logs = _agent_logs(wf_id)
        agents = [l["agent"] for l in logs]
        assert agents == [
            "ProfileAgent",
            "JobMatchingAgent",
            "AssessmentAgent",
            "QualificationAgent",
            "ApplicationAgent",
            "RecruiterScreeningAgent",
        ]
        assert all(l["status"] == "completed" for l in logs), logs
        assert all(l["error"] is None for l in logs), logs
    finally:
        _cleanup(cid, jid, wf_id)


def test_workflow_stops_at_human_review():
    cid, jid = _make_candidate()
    wf_id = f"bbbb0000-0000-0000-0000-00000000000{0}"  # last hex == 0x0 -> human review required
    _seed_workflow(wf_id, cid, jid)
    try:
        orchestrator._run_profile_and_match(wf_id, cid, jid)
        time.sleep(1.5)
        assert _workflow_state(wf_id) == schemas.WorkflowState.QUALIFICATION_REVIEW
        logs = _agent_logs(wf_id)
        assert [l["agent"] for l in logs] == [
            "ProfileAgent",
            "JobMatchingAgent",
            "AssessmentAgent",
            "QualificationAgent",
        ]
        assert logs[-1]["status"] == "requires_review"
    finally:
        _cleanup(cid, jid, wf_id)


def test_workflow_logs_error_when_candidate_missing():
    cid, jid = _make_candidate()
    missing = 99999999
    wf_id = f"cccc0000-0000-0000-0000-00000000000{5}"
    _seed_workflow(wf_id, missing, jid)
    try:
        orchestrator._run_profile_and_match(wf_id, missing, jid)
        time.sleep(0.3)
        assert _workflow_state(wf_id) == schemas.WorkflowState.PROFILE_VERIFIED
        logs = _agent_logs(wf_id)
        assert logs[-1]["agent"] == "JobMatchingAgent"
        assert logs[-1]["status"] == "failed"
        assert logs[-1]["error"]
    finally:
        _cleanup(cid, jid, wf_id)


# --- agent failure branches (each agent logs 'failed' and stops) ----------- #

def _boom_on(n):
    state = {"i": 0}

    def _inner(*_args, **_kwargs):
        state["i"] += 1
        if state["i"] == n:
            raise RuntimeError("boom")

    return _inner


def _wipe(wf_id):
    db = SessionLocal()
    try:
        db.query(AgentLog).filter(AgentLog.workflow_id == wf_id).delete(synchronize_session=False)
        db.query(Workflow).filter(Workflow.workflow_id == wf_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_profile_agent_logs_failure(monkeypatch):
    wf_id = f"dddd0000-0000-0000-0000-00000000000{2}"
    try:
        monkeypatch.setattr(orchestrator_service.time, "sleep", _boom_on(1))
        orchestrator._run_profile_and_match(wf_id, 1, 1)
        logs = _agent_logs(wf_id)
        assert [l["agent"] for l in logs] == ["ProfileAgent"]
        assert logs[0]["status"] == "failed"
        assert logs[0]["error"]
    finally:
        _wipe(wf_id)


def test_assessment_agent_logs_failure(monkeypatch):
    wf_id = f"eeee0000-0000-0000-0000-00000000000{3}"
    try:
        monkeypatch.setattr(orchestrator_service.time, "sleep", _boom_on(1))
        orchestrator._run_assessment_and_followups(wf_id, 1, 1)
        logs = _agent_logs(wf_id)
        assert [l["agent"] for l in logs] == ["AssessmentAgent"]
        assert logs[0]["status"] == "failed"
    finally:
        _wipe(wf_id)


def test_qualification_agent_logs_failure(monkeypatch):
    wf_id = f"ffff0000-0000-0000-0000-00000000000{4}"
    try:
        monkeypatch.setattr(orchestrator_service.time, "sleep", _boom_on(2))
        orchestrator._run_assessment_and_followups(wf_id, 1, 1)
        logs = _agent_logs(wf_id)
        assert [l["agent"] for l in logs] == ["AssessmentAgent", "QualificationAgent"]
        assert logs[-1]["status"] == "failed"
    finally:
        _wipe(wf_id)


def test_application_agent_logs_failure(monkeypatch):
    wf_id = f"aba20000-0000-0000-0000-00000000000{6}"
    try:
        monkeypatch.setattr(orchestrator_service.time, "sleep", _boom_on(3))
        orchestrator._run_assessment_and_followups(wf_id, 1, 1)
        logs = _agent_logs(wf_id)
        assert [l["agent"] for l in logs] == [
            "AssessmentAgent",
            "QualificationAgent",
            "ApplicationAgent",
        ]
        assert logs[-1]["status"] == "failed"
    finally:
        _wipe(wf_id)


def test_recruiter_agent_logs_failure(monkeypatch):
    wf_id = f"aca30000-0000-0000-0000-00000000000{7}"
    try:
        monkeypatch.setattr(orchestrator_service.time, "sleep", _boom_on(4))
        orchestrator._run_assessment_and_followups(wf_id, 1, 1)
        logs = _agent_logs(wf_id)
        assert [l["agent"] for l in logs] == [
            "AssessmentAgent",
            "QualificationAgent",
            "ApplicationAgent",
            "RecruiterScreeningAgent",
        ]
        assert logs[-1]["status"] == "failed"
    finally:
        _wipe(wf_id)