from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import session as db_session
from app.db import models
from app.matching.engine import score_candidate_job
from app.db.models import MatchingLog
from app.orchestrator import service as orchestrator_service
from app.orchestrator import schemas as orchestrator_schemas
from app.db.models import Workflow, AgentLog
from app.profile.agent import ProfileAgent
from app.profile.schemas import ProfileExtractionRequest, ProfileReviewUpdate

router = APIRouter()
PROFILE_AGENT = ProfileAgent(model_name="demo-profile-agent")
PROFILE_AGENT = ProfileAgent(model_name="demo-profile-agent")


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
        "years_experience": c.experiences and len(c.experiences) and sum([( (e.end_date.year if e.end_date else 2026) - (e.start_date.year if e.start_date else 0)) for e in c.experiences ]) or 0,
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
            "employment_percentage_min": j.minimum_years_experience if False else None,
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
        "required_skills": j.required_skills,
        "preferred_skills": j.preferred_skills,
    }


@router.get("/api/matching/candidate/{candidate_id}/job/{job_id}")
@router.post("/api/matching/candidate/{candidate_id}/job/{job_id}")
def match_candidate_job(candidate_id: int, job_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not c or not j:
        raise HTTPException(status_code=404, detail="Candidate or job not found")

    # build dicts for engine
    candidate = {
        "id": c.id,
        "name": c.name,
        "location": c.location,
        "years_experience": sum([((e.end_date.year if e.end_date else 2026) - (e.start_date.year if e.start_date else 0)) for e in c.experiences]) if c.experiences else 0,
        "skills": [{"skill": s.skill, "level": s.level} for s in c.skills],
        "education": [{"degree": e.degree, "field": e.field} for e in c.education],
        "languages": [],
        "salary_expectation_min": getattr(c, 'salary_min', 0),
        "salary_expectation_max": getattr(c, 'salary_max', 9999999),
        "employment_percentage_min": getattr(c, 'employment_percentage_min', 50),
        "employment_percentage_max": getattr(c, 'employment_percentage_max', 100),
        "remote_preference": getattr(c, 'remote_preference', 'office'),
        "maximum_commute_minutes": getattr(c, 'maximum_commute_minutes', 60),
        "career_goal": getattr(c, 'career_goal', ''),
        "desired_roles": getattr(c, 'desired_roles', [])
    }

    job = {
        "id": j.id,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "required_skills": j.required_skills,
        "preferred_skills": j.preferred_skills,
        "minimum_years_experience": j.minimum_years_experience,
        "education_requirements": j.education_requirements,
        "language_requirements": j.language_requirements,
        "employment_percentage_min": None,
        "employment_percentage_max": None,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "remote_percentage": getattr(j, 'remote_percentage', 0),
        "department": getattr(j, 'department', None),
    }

    result = score_candidate_job(candidate, job)

    # persist matching log
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
    candidate = {
        "id": c.id,
        "name": c.name,
        "location": c.location,
        "years_experience": sum([((e.end_date.year if e.end_date else 2026) - (e.start_date.year if e.start_date else 0)) for e in c.experiences]) if c.experiences else 0,
        "skills": [{"skill": s.skill, "level": s.level} for s in c.skills],
        "education": [{"degree": e.degree, "field": e.field} for e in c.education],
        "languages": [],
        "salary_expectation_min": getattr(c, 'salary_min', 0),
        "salary_expectation_max": getattr(c, 'salary_max', 9999999),
        "employment_percentage_min": getattr(c, 'employment_percentage_min', 50),
        "employment_percentage_max": getattr(c, 'employment_percentage_max', 100),
        "remote_preference": getattr(c, 'remote_preference', 'office'),
        "maximum_commute_minutes": getattr(c, 'maximum_commute_minutes', 60),
        "career_goal": getattr(c, 'career_goal', ''),
        "desired_roles": getattr(c, 'desired_roles', [])
    }

    results = []
    for j in jobs:
        job = {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "required_skills": j.required_skills,
            "preferred_skills": j.preferred_skills,
            "minimum_years_experience": j.minimum_years_experience,
            "education_requirements": j.education_requirements,
            "language_requirements": j.language_requirements,
            "employment_percentage_min": None,
            "employment_percentage_max": None,
            "salary_min": j.salary_min,
            "salary_max": j.salary_max,
            "remote_percentage": getattr(j, 'remote_percentage', 0),
            "department": getattr(j, 'department', None),
        }
        r = score_candidate_job(candidate, job)
        results.append(r)
        # store log for each
        log = MatchingLog(candidate_id=c.id, job_id=j.id, execution_time_ms=r.get('execution_time_ms'), algorithm_version=r.get('algorithm_version'))
        db.add(log)
    db.commit()
    # sort by overall_score desc
    results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
    return results


@router.get("/api/matching/job/{job_id}")
def match_job_all(job_id: int, db: Session = Depends(get_db)):
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    candidates = db.query(models.Candidate).all()
    job = {
        "id": j.id,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "required_skills": j.required_skills,
        "preferred_skills": j.preferred_skills,
        "minimum_years_experience": j.minimum_years_experience,
        "education_requirements": j.education_requirements,
        "language_requirements": j.language_requirements,
        "employment_percentage_min": None,
        "employment_percentage_max": None,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "remote_percentage": getattr(j, 'remote_percentage', 0),
        "department": getattr(j, 'department', None),
    }
    results = []
    for c in candidates:
        candidate = {
            "id": c.id,
            "name": c.name,
            "location": c.location,
            "years_experience": sum([((e.end_date.year if e.end_date else 2026) - (e.start_date.year if e.start_date else 0)) for e in c.experiences]) if c.experiences else 0,
            "skills": [{"skill": s.skill, "level": s.level} for s in c.skills],
            "education": [{"degree": e.degree, "field": e.field} for e in c.education],
            "languages": [],
            "salary_expectation_min": getattr(c, 'salary_min', 0),
            "salary_expectation_max": getattr(c, 'salary_max', 9999999),
            "employment_percentage_min": getattr(c, 'employment_percentage_min', 50),
            "employment_percentage_max": getattr(c, 'employment_percentage_max', 100),
            "remote_preference": getattr(c, 'remote_preference', 'office'),
            "maximum_commute_minutes": getattr(c, 'maximum_commute_minutes', 60),
            "career_goal": getattr(c, 'career_goal', ''),
            "desired_roles": getattr(c, 'desired_roles', [])
        }
        r = score_candidate_job(candidate, job)
        results.append(r)
        log = MatchingLog(candidate_id=c.id, job_id=j.id, execution_time_ms=r.get('execution_time_ms'), algorithm_version=r.get('algorithm_version'))
        db.add(log)
    db.commit()
    results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
    return results


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
