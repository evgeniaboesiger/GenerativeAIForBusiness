from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

ProvenanceStatus = Literal["verified", "unverified", "needs_review"]
ItemStatus = Literal["extracted", "needs_review", "candidate_confirmed"]


class Provenance(BaseModel):
    source: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: ProvenanceStatus = "unverified"
    comment: Optional[str] = None


class SkillItem(BaseModel):
    name: str
    level: Optional[str] = None
    status: ItemStatus = "extracted"
    provenance: Provenance = Field(default_factory=lambda: Provenance(source="cv", confidence=0.7, status="unverified"))

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Skill name is required")
        return cleaned


class WorkExperience(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    status: ItemStatus = "extracted"
    provenance: Provenance = Field(default_factory=lambda: Provenance(source="cv", confidence=0.7, status="unverified"))


class EducationItem(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    graduation_year: Optional[int] = None
    status: ItemStatus = "extracted"
    provenance: Provenance = Field(default_factory=lambda: Provenance(source="cv", confidence=0.7, status="unverified"))


class LanguageItem(BaseModel):
    language: str
    level: Optional[str] = None
    status: ItemStatus = "extracted"
    provenance: Provenance = Field(default_factory=lambda: Provenance(source="cv", confidence=0.7, status="unverified"))


class CandidateProfessionalProfile(BaseModel):
    name: Optional[str] = None
    skills: List[SkillItem] = Field(default_factory=list)
    work_experience: List[WorkExperience] = Field(default_factory=list)
    job_titles: List[str] = Field(default_factory=list)
    years_experience: Optional[int] = None
    relevant_experience_years: Optional[int] = None
    education: Optional[List[EducationItem]] = None
    languages: List[LanguageItem] = Field(default_factory=list)
    certificates: List[str] = Field(default_factory=list)
    preferred_employment_percentage: Optional[int] = None
    preferred_locations: Optional[List[str]] = None
    remote_preference: Optional[str] = None
    salary_expectation: Optional[Dict[str, Any]] = None
    career_goals: Optional[List[str]] = None
    availability: Optional[str] = None


class ExtractionAudit(BaseModel):
    fields_extracted: int = 0
    fields_needing_review: int = 0
    duplicate_skills: List[str] = Field(default_factory=list)
    unsupported_fields: List[str] = Field(default_factory=list)
    model_used: str = "demo-profile-agent"
    execution_time_ms: int = 0
    estimated_cost: Optional[float] = None
    token_estimate: Optional[int] = None


class ProfileExtractionResult(BaseModel):
    profile: CandidateProfessionalProfile
    audit: ExtractionAudit


class ProfileExtractionRequest(BaseModel):
    candidate_id: Optional[int] = None
    cv_text: str
    source: str = "cv"


class ProfileReviewUpdate(BaseModel):
    candidate_id: int
    profile: CandidateProfessionalProfile
    review_status: Literal["candidate_confirmed", "needs_review"] = "candidate_confirmed"
    notes: Optional[str] = None


class ProfileReviewRecord(BaseModel):
    candidate_id: int
    profile: CandidateProfessionalProfile
    review_status: Literal["candidate_confirmed", "needs_review"] = "candidate_confirmed"
    notes: Optional[str] = None
