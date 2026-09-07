import uuid
import time
import threading
from datetime import datetime
from typing import Dict, Any, List
from app.db import session as db_session
from app.db import models
from app.orchestrator import schemas
from app.matching.engine import score_candidate_job

MAX_RETRIES = 2


def _now():
    return datetime.utcnow()


class Orchestrator:
    def __init__(self):
        self.lock = threading.Lock()

    def start_workflow(self, candidate_id: int, job_id: int) -> str:
        workflow_id = str(uuid.uuid4())
        db = db_session.SessionLocal()
        wf = models.Workflow(workflow_id=workflow_id, candidate_id=candidate_id, job_id=job_id, state=schemas.WorkflowState.PROFILE_CREATED)
        db.add(wf)
        db.commit()
        db.close()

        # run profile agent synchronously (small demo)
        threading.Thread(target=self._run_profile_and_match, args=(workflow_id, candidate_id, job_id)).start()
        return workflow_id

    def _log_agent(self, workflow_id: str, agent_name: str, start_time: datetime, end_time: datetime, status: str, input_ref: Dict[str, Any], output_ref: Dict[str, Any], error: str = None):
        db = db_session.SessionLocal()
        latency = int((end_time - start_time).total_seconds() * 1000)
        log = models.AgentLog(
            workflow_id=workflow_id,
            agent=agent_name,
            agent_version="1.0",
            status=status,
            start_time=start_time,
            end_time=end_time,
            latency_ms=latency,
            model=None,
            estimated_cost=0,
            input_reference=input_ref,
            output_reference=output_ref,
            error=error,
        )
        db.add(log)
        db.commit()
        db.close()

    def _update_workflow_state(self, workflow_id: str, new_state: str):
        db = db_session.SessionLocal()
        wf = db.query(models.Workflow).filter(models.Workflow.workflow_id == workflow_id).first()
        if wf:
            wf.state = new_state
            wf.updated_at = datetime.utcnow()
            db.add(wf)
            db.commit()
        db.close()

    def _run_profile_and_match(self, workflow_id: str, candidate_id: int, job_id: int):
        # Profile Agent: read candidate docs (read-only), write profile extraction (stored in DB by candidate profile flow)
        agent = "ProfileAgent"
        start = _now()
        try:
            # For POC: assume profile exists; in real system, call Profile Agent service
            time.sleep(0.1)
            output = {"profile_extracted": True}
            status = "completed"
            self._log_agent(workflow_id, agent, start, _now(), status, {"candidate_id": candidate_id}, output)
            self._update_workflow_state(workflow_id, schemas.WorkflowState.PROFILE_VERIFIED)
        except Exception as e:
            self._log_agent(workflow_id, agent, start, _now(), "failed", {"candidate_id": candidate_id}, {}, str(e))
            return

        # Matching Agent: deterministic scoring
        agent = "JobMatchingAgent"
        start = _now()
        try:
            # load candidate and job
            db = db_session.SessionLocal()
            c = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
            j = db.query(models.Job).filter(models.Job.id == job_id).first()
            db.close()
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
            status = "completed"
            self._log_agent(workflow_id, agent, start, _now(), status, {"candidate_id": candidate_id, "job_id": job_id}, result)
            self._update_workflow_state(workflow_id, schemas.WorkflowState.MATCHING_COMPLETE)
        except Exception as e:
            self._log_agent(workflow_id, agent, start, _now(), "failed", {"candidate_id": candidate_id, "job_id": job_id}, {}, str(e))
            return

        # Next steps: Assessment, Qualification, Application, Recruiter Screening
        # For demo, create queued states and logs; do not auto-approve applications
        self._update_workflow_state(workflow_id, schemas.WorkflowState.JOB_SELECTED)

        # Mark assessment pending and schedule assessment agent asynchronously
        self._update_workflow_state(workflow_id, schemas.WorkflowState.ASSESSMENT_PENDING)
        threading.Thread(target=self._run_assessment_and_followups, args=(workflow_id, candidate_id, job_id)).start()

    def _run_assessment_and_followups(self, workflow_id: str, candidate_id: int, job_id: int):
        # Assessment Agent
        agent = "AssessmentAgent"
        start = _now()
        try:
            time.sleep(0.2)
            output = {"assessment_created": True, "score": 80}
            self._log_agent(workflow_id, agent, start, _now(), "completed", {"candidate_id": candidate_id}, output)
            self._update_workflow_state(workflow_id, schemas.WorkflowState.ASSESSMENT_COMPLETE)
        except Exception as e:
            self._log_agent(workflow_id, agent, start, _now(), "failed", {"candidate_id": candidate_id}, {}, str(e))
            return

        # Qualification Verification Agent
        agent = "QualificationAgent"
        start = _now()
        try:
            time.sleep(0.1)
            # Simulate possible human review required in 1/10 cases
            needs_review = (int(workflow_id[-1], 16) % 10) == 0
            output = {"verified": not needs_review, "needs_human_review": needs_review}
            status = "completed" if not needs_review else "requires_review"
            self._log_agent(workflow_id, agent, start, _now(), status, {"candidate_id": candidate_id}, output)
            self._update_workflow_state(workflow_id, schemas.WorkflowState.QUALIFICATION_REVIEW)
            if needs_review:
                # stop orchestration until human resolves
                return
        except Exception as e:
            self._log_agent(workflow_id, agent, start, _now(), "failed", {"candidate_id": candidate_id}, {}, str(e))
            return

        # Application Agent (draft only)
        agent = "ApplicationAgent"
        start = _now()
        try:
            time.sleep(0.05)
            output = {"application_drafted": True}
            self._log_agent(workflow_id, agent, start, _now(), "completed", {"candidate_id": candidate_id, "job_id": job_id}, output)
            self._update_workflow_state(workflow_id, schemas.WorkflowState.APPLICATION_DRAFTED)
        except Exception as e:
            self._log_agent(workflow_id, agent, start, _now(), "failed", {"candidate_id": candidate_id, "job_id": job_id}, {}, str(e))
            return

        # Recruiter Screening Agent
        agent = "RecruiterScreeningAgent"
        start = _now()
        try:
            time.sleep(0.05)
            output = {"recommendation": "proceed"}
            self._log_agent(workflow_id, agent, start, _now(), "completed", {"candidate_id": candidate_id, "job_id": job_id}, output)
            self._update_workflow_state(workflow_id, schemas.WorkflowState.RECRUITER_REVIEW)
        except Exception as e:
            self._log_agent(workflow_id, agent, start, _now(), "failed", {"candidate_id": candidate_id, "job_id": job_id}, {}, str(e))
            return


orchestrator = Orchestrator()
