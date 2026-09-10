from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any

_PERSONALITY_MIN, _PERSONALITY_MAX = 1, 7
_VALUES_MIN, _VALUES_MAX = 1, 5


class PersonalitySubmission(BaseModel):
    candidate_id: Optional[int] = None
    # {question_id: 1..7}
    responses: Dict[str, int]

    @field_validator("responses")
    @classmethod
    def _responses_in_range(cls, v: Dict[str, int]) -> Dict[str, int]:
        for qid, value in v.items():
            if not isinstance(value, int) or not (_PERSONALITY_MIN <= value <= _PERSONALITY_MAX):
                raise ValueError(
                    f"Personality response for '{qid}' must be between "
                    f"{_PERSONALITY_MIN} and {_PERSONALITY_MAX}, got {value!r}"
                )
        return v


class ValuesSubmission(BaseModel):
    candidate_id: Optional[int] = None
    # {question_id: 1..5}
    responses: Dict[str, int]

    @field_validator("responses")
    @classmethod
    def _responses_in_range(cls, v: Dict[str, int]) -> Dict[str, int]:
        for qid, value in v.items():
            if not isinstance(value, int) or not (_VALUES_MIN <= value <= _VALUES_MAX):
                raise ValueError(
                    f"Values response for '{qid}' must be between "
                    f"{_VALUES_MIN} and {_VALUES_MAX}, got {value!r}"
                )
        return v


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
