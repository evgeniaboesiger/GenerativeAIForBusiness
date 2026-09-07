from pydantic import BaseModel, Field, Json, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class AgentOutput(BaseModel):
    agent: str
    agent_version: str
    status: str
    start_time: datetime
    end_time: datetime
    latency_ms: int
    model: Optional[str] = None
    estimated_cost: Optional[float] = None
    input_reference: Optional[Dict[str, Any]] = None
    output_reference: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WorkflowState(str):
    PROFILE_CREATED = "PROFILE_CREATED"
    PROFILE_REQUIRES_CONFIRMATION = "PROFILE_REQUIRES_CONFIRMATION"
    PROFILE_VERIFIED = "PROFILE_VERIFIED"
    MATCHING_COMPLETE = "MATCHING_COMPLETE"
    JOB_SELECTED = "JOB_SELECTED"
    ASSESSMENT_PENDING = "ASSESSMENT_PENDING"
    ASSESSMENT_COMPLETE = "ASSESSMENT_COMPLETE"
    QUALIFICATION_REVIEW = "QUALIFICATION_REVIEW"
    APPLICATION_DRAFTED = "APPLICATION_DRAFTED"
    APPLICATION_REQUIRES_APPROVAL = "APPLICATION_REQUIRES_APPROVAL"
    APPLICATION_APPROVED = "APPLICATION_APPROVED"
    RECRUITER_REVIEW = "RECRUITER_REVIEW"
    HUMAN_DECISION = "HUMAN_DECISION"


class WorkflowCreate(BaseModel):
    workflow_id: str
    candidate_id: int
    job_id: int
    initial_state: str = Field(default=WorkflowState.PROFILE_CREATED)


class WorkflowStatus(BaseModel):
    workflow_id: str
    candidate_id: int
    job_id: int
    state: str
    created_at: datetime
    updated_at: datetime
    agent_history: List[AgentOutput] = []
