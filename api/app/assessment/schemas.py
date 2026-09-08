from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PersonalitySubmission(BaseModel):
    candidate_id: Optional[int] = None
    # {question_id: 1..7}
    responses: Dict[str, int]


class ValuesSubmission(BaseModel):
    candidate_id: Optional[int] = None
    # {question_id: 1..5}
    responses: Dict[str, int]


class CandidateValuesUpdate(BaseModel):
    value_ids: List[str]


class CompanyValuesUpdate(BaseModel):
    company_values: List[str]
    personality_preferences: Optional[Dict[str, Dict[str, Any]]] = None


class AssessmentResult(BaseModel):
    candidate_id: Optional[int] = None
    personality: Optional[Dict[str, Any]] = None
    values: Optional[List[Dict[str, Any]]] = None
    type_code: Optional[str] = None
