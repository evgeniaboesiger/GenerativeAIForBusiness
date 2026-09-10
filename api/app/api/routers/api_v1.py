from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional, List
from app.db import session as db_session
from app.db import models
from app.matching.engine import score_candidate_job
from app.db.models import MatchingLog
from app.orchestrator import service as orchestrator_service
from app.orchestrator import schemas as orchestrator_schemas
from app.db.models import Workflow, AgentLog
from app.profile.agent import ProfileAgent
from app.profile.schemas import ProfileExtractionRequest, ProfileReviewUpdate
from app.assessment import questions as assessment_questions
from app.assessment.schemas import (
    PersonalitySubmission,
    ValuesSubmission,
    CandidateValuesUpdate,
    CompanyValuesUpdate,
)

router = APIRouter()
PROFILE_AGENT = ProfileAgent(model_name="demo-profile-agent")


class CandidatePreferencesUpdate(BaseModel):
    """Validated payload for PUT /api/candidates/{id}/preferences."""

    preference_tiers: Optional[Dict[str, Any]] = None
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    remote_preference: Optional[str] = None
    employment_percentage: Optional[int] = Field(default=None, ge=0, le=100)


def get_db():
    db = db_session.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/api/profile/extract")
def extract_profile(payload: ProfileExtractionRequest, db: Session = Depends(get_db)):
    result = PROFILE_AGENT.extract_profile(payload.cv_text)
    if payload.candidate_id is not None:
        exists = db.query(models.Candidate).filter(models.Candidate.id == payload.candidate_id).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Candidate not found")
        extraction = models.ProfileExtraction(
            candidate_id=payload.candidate_id,
            source=payload.source,
            raw_text=payload.cv_text,
            profile_json=result.model_dump(),
            model_name=result.audit.model_used,
            execution_time_ms=result.audit.execution_time_ms,
            token_estimate=result.audit.token_estimate,
            estimated_cost=result.audit.estimated_cost,
        )
        db.add(extraction)
        db.commit()
    return result.model_dump()


@router.get("/api/profile/candidate/{candidate_id}")
def get_candidate_profile(candidate_id: int, db: Session = Depends(get_db)):
    extraction = db.query(models.ProfileExtraction).filter(models.ProfileExtraction.candidate_id == candidate_id).order_by(models.ProfileExtraction.created_at.desc()).first()
    if not extraction:
        raise HTTPException(status_code=404, detail="Profile extraction not found")
    return extraction.profile_json


@router.post("/api/profile/candidate/{candidate_id}/review")
def review_candidate_profile(candidate_id: int, payload: ProfileReviewUpdate, db: Session = Depends(get_db)):
    if payload.candidate_id != candidate_id:
        raise HTTPException(status_code=400, detail="Candidate id mismatch")

    if not db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first():
        raise HTTPException(status_code=404, detail="Candidate not found")

    review = models.ProfileReview(
        candidate_id=candidate_id,
        profile_json=payload.profile.model_dump(),
        review_status=payload.review_status,
        notes=payload.notes,
    )
    db.add(review)
    db.commit()
    return {
        "candidate_id": candidate_id,
        "review_status": payload.review_status,
        "profile": payload.profile.model_dump(),
    }


@router.get("/api/candidates")
def list_candidates(db: Session = Depends(get_db)):
    candidates = db.query(models.Candidate).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "location": c.location,
        }
        for c in candidates
    ]


@router.get("/api/candidates/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # serialize basic profile
    return {
        "id": c.id,
        "name": c.name,
        "location": c.location,
        "years_experience": c.years_experience,
    }


@router.get("/api/candidates/{candidate_id}/preferences")
def get_candidate_preferences(candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {
        "candidate_id": c.id,
        "preference_tiers": getattr(c, "preference_tiers", None) or {},
        "salary_min": c.salary_min,
        "salary_max": c.salary_max,
        "remote_preference": c.remote_preference,
        "employment_percentage": c.employment_percentage,
    }


@router.put("/api/candidates/{candidate_id}/preferences")
def update_candidate_preferences(
    candidate_id: int, payload: CandidatePreferencesUpdate, db: Session = Depends(get_db)
):
    c = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if payload.preference_tiers is not None:
        c.preference_tiers = payload.preference_tiers
    if payload.salary_min is not None:
        c.salary_min = payload.salary_min
    if payload.salary_max is not None:
        c.salary_max = payload.salary_max
    if payload.remote_preference is not None:
        c.remote_preference = payload.remote_preference
    if payload.employment_percentage is not None:
        c.employment_percentage = payload.employment_percentage
    db.commit()
    db.refresh(c)
    return {
        "candidate_id": c.id,
        "preference_tiers": getattr(c, "preference_tiers", None) or {},
        "salary_min": c.salary_min,
        "salary_max": c.salary_max,
        "remote_preference": c.remote_preference,
        "employment_percentage": c.employment_percentage,
    }


def _job_dict(j: models.Job) -> Dict[str, Any]:
    """Build the engine-facing job dict from the ORM model.

    ``employment_percentage_min/max`` mirror the job's declared (single)
    employment percentage, or stay ``None`` so the engine treats an
    unspecified workload as unknown/neutral instead of assuming full-time.
    """
    return {
        "id": j.id,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "required_skills": j.required_skills,
        "preferred_skills": j.preferred_skills,
        "minimum_years_experience": j.minimum_years_experience,
        "education_requirements": j.education_requirements,
        "language_requirements": j.language_requirements,
        "employment_percentage_min": j.employment_percentage,
        "employment_percentage_max": j.employment_percentage,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "remote_percentage": getattr(j, 'remote_percentage', 0),
        "department": getattr(j, 'department', None),
        "company_values": getattr(j, 'company_values', None),
        "personality_preferences": getattr(j, 'personality_preferences', None),
    }


@router.get("/api/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(models.Job).all()
    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "employment_percentage": j.employment_percentage,
            "employment_percentage_min": j.employment_percentage,
            "employment_percentage_max": j.employment_percentage,
        }
        for j in jobs
    ]


@router.get("/api/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": j.id,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "employment_percentage": j.employment_percentage,
        "employment_percentage_min": j.employment_percentage,
        "employment_percentage_max": j.employment_percentage,
        "remote_percentage": getattr(j, 'remote_percentage', 0),
        "required_skills": j.required_skills,
        "preferred_skills": j.preferred_skills,
    }


def _candidate_dict(c: models.Candidate) -> Dict[str, Any]:
    """Build the engine-facing candidate dict from the ORM model."""
    pct = c.employment_percentage
    return {
        "id": c.id,
        "name": c.name,
        "location": c.location,
        "years_experience": c.years_experience,
        "skills": [{"skill": s.skill, "level": s.level} for s in c.skills],
        "education": [{"degree": e.degree, "field": e.field} for e in c.education],
        "languages": [],
        "salary_expectation_min": getattr(c, 'salary_min', 0),
        "salary_expectation_max": getattr(c, 'salary_max', 9999999),
        "employment_percentage_min": pct if pct is not None else 50,
        "employment_percentage_max": pct if pct is not None else 100,
        "remote_preference": getattr(c, 'remote_preference', 'office'),
        "career_goal": getattr(c, 'career_goal', ''),
        "desired_roles": getattr(c, 'desired_roles', []),
        "personality": getattr(c, 'personality', None),
        "values": [v["value"] if isinstance(v, dict) else v for v in (getattr(c, 'values', None) or [])],
        "preference_tiers": getattr(c, 'preference_tiers', None),
    }


@router.get("/api/matching/candidate/{candidate_id}/job/{job_id}")
@router.post("/api/matching/candidate/{candidate_id}/job/{job_id}")
def match_candidate_job(request: Request, candidate_id: int, job_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not c or not j:
        raise HTTPException(status_code=404, detail="Candidate or job not found")

    # build dicts for engine
    candidate = _candidate_dict(c)
    job = _job_dict(j)

    result = score_candidate_job(candidate, job)

    # persist matching log on write operations only: a GET must not mutate
    # the database (REST). The POST path is the explicit "run + record" call.
    if request.method == "POST":
        log = MatchingLog(candidate_id=candidate_id, job_id=job_id, execution_time_ms=result.get('execution_time_ms'), algorithm_version=result.get('algorithm_version'))
        db.add(log)
        db.commit()

    return result


@router.get("/api/matching/candidate/{candidate_id}")
def match_candidate_all(candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    jobs = db.query(models.Job).all()
    candidate = _candidate_dict(c)

    results = []
    for j in jobs:
        job = _job_dict(j)
        r = score_candidate_job(candidate, job)
        results.append(r)
    results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
    return results


@router.get("/api/matching/job/{job_id}")
def match_job_all(job_id: int, db: Session = Depends(get_db)):
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    candidates = db.query(models.Candidate).all()
    job = _job_dict(j)
    results = []
    for c in candidates:
        candidate = _candidate_dict(c)
        r = score_candidate_job(candidate, job)
        results.append(r)
    results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
    return results


@router.get("/api/assessment/questions")
def get_assessment_questions():
    """Return the personality + values assessment framework to the frontend."""
    return {
        "personality_dimensions": assessment_questions.PERSONALITY_DIMENSIONS,
        "personality_questions": assessment_questions.PERSONALITY_QUESTIONS,
        "value_questions": assessment_questions.VALUE_QUESTIONS,
        "company_values": assessment_questions.COMPANY_VALUES,
    }


@router.post("/api/assessment/personality")
def submit_personality(payload: PersonalitySubmission, db: Session = Depends(get_db)):
    """Save a candidate's personality assessment and compute their profile."""
    profile = assessment_questions.compute_personality_profile(payload.responses)
    if payload.candidate_id is not None:
        c = db.query(models.Candidate).filter(models.Candidate.id == payload.candidate_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Candidate not found")
        c.personality = profile
        db.commit()
    return profile


@router.post("/api/assessment/values")
def submit_values(payload: ValuesSubmission, db: Session = Depends(get_db)):
    """Save a candidate's values assessment and compute their ranked values."""
    ranked = assessment_questions.compute_values_from_responses(payload.responses)
    if payload.candidate_id is not None:
        c = db.query(models.Candidate).filter(models.Candidate.id == payload.candidate_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Candidate not found")
        c.values = ranked
        db.commit()
    return {"values": ranked}


@router.get("/api/assessment/candidate/{candidate_id}")
def get_candidate_assessment(candidate_id: int, db: Session = Depends(get_db)):
    """Return a candidate's stored personality profile and value ranking."""
    c = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {
        "personality": c.personality,
        "values": c.values,
    }


@router.post("/api/assessment/job/{job_id}/values")
def update_job_values(job_id: int, payload: CompanyValuesUpdate, db: Session = Depends(get_db)):
    """Store a company's declared values (and optional personality preferences) for a job."""
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    j.company_values = payload.company_values
    if payload.personality_preferences is not None:
        j.personality_preferences = payload.personality_preferences
    db.commit()
    return {
        "job_id": job_id,
        "company_values": j.company_values,
        "personality_preferences": j.personality_preferences,
    }


@router.post("/api/workflows/start/{candidate_id}/{job_id}")
def start_workflow(candidate_id: int, job_id: int):
    wf_id = orchestrator_service.orchestrator.start_workflow(candidate_id, job_id)
    return {"workflow_id": wf_id}


@router.get("/api/workflows/{workflow_id}")
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    logs = db.query(AgentLog).filter(AgentLog.workflow_id == workflow_id).order_by(AgentLog.start_time.asc()).all()
    agent_history = []
    for l in logs:
        agent_history.append({
            "agent": l.agent,
            "agent_version": l.agent_version,
            "status": l.status,
            "start_time": l.start_time,
            "end_time": l.end_time,
            "latency_ms": l.latency_ms,
            "model": l.model,
            "estimated_cost": float(l.estimated_cost or 0),
            "input_reference": l.input_reference,
            "output_reference": l.output_reference,
            "error": l.error,
        })
    return {
        "workflow_id": wf.workflow_id,
        "candidate_id": wf.candidate_id,
        "job_id": wf.job_id,
        "state": wf.state,
        "created_at": wf.created_at,
        "updated_at": wf.updated_at,
        "agent_history": agent_history,
    }
