from __future__ import annotations

import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from .schemas import (
    CandidateProfessionalProfile,
    EducationItem,
    ExtractionAudit,
    LanguageItem,
    ProfileExtractionResult,
    Provenance,
    SkillItem,
    WorkExperience,
)


class ProfileAgent:
    """Deterministic profile extraction agent for CV text.

    This service does not decide candidate quality or make ranking decisions. It extracts,
    normalizes, and validates job-relevant profile data using deterministic parsing rules
    and explicit traceability metadata.
    """

    SKILL_ALIASES = {
        "python": "Python",
        "sql": "SQL",
        "data analysis": "Data Analysis",
        "power bi": "Power BI",
        "project management": "Project Management",
        "ux research": "UX Research",
        "ui design": "UI Design",
        "aws": "AWS",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "react": "React",
        "typescript": "TypeScript",
        "javascript": "JavaScript",
        "excel": "Excel",
        "customer success": "Customer Success",
        "business development": "Business Development",
        "salesforce": "Salesforce",
        "agile": "Agile",
        "scrum": "Scrum",
        "jira": "Jira",
        "tableau": "Tableau",
        "machine learning": "Machine Learning",
        "communication": "Communication",
        "presentation": "Presentation",
        "finance": "Finance",
        "marketing": "Marketing",
        "hr": "HR",
        "recruitment": "Recruitment",
        "accounting": "Accounting",
    }

    AMBIGUOUS_SKILLS = {
        "digital transformation": "digital transformation",
        "business enablement": "business enablement",
        "stakeholder communication": "stakeholder communication",
        "roadmap planning": "roadmap planning",
    }

    LANGUAGE_ALIASES = {
        "english": "English",
        "en": "English",
        "german": "German",
        "deutsch": "German",
        "de": "German",
        "french": "French",
        "français": "French",
        "fr": "French",
        "italian": "Italian",
        "spanish": "Spanish",
        "es": "Spanish",
    }

    UNSUPPORTED_FIELD_PATTERNS = {
        "date_of_birth": [r"born in\s+\d{4}", r"date of birth"],
        "marital_status": [r"married", r"single", r"divorced", r"widowed"],
        "children": [r"\bchildren\b", r"(?:one|two|three|four|many|\d+)\s+children\b", r"has\s+(?:one|two|three|four|many|\d+)\s+children", r"childcare"],
        "disability_status": [r"disabled", r"disability"],
    }

    def __init__(self, model_name: str = "demo-profile-agent"):
        self.model_name = model_name

    def extract_profile(self, cv_text: str) -> ProfileExtractionResult:
        start = time.perf_counter()
        text = (cv_text or "").strip()

        profile = CandidateProfessionalProfile(
            name=self._extract_name(text),
            skills=self._extract_skills(text),
            work_experience=self._extract_work_experience(text),
            job_titles=[],
            education=self._extract_education(text),
            languages=self._extract_languages(text),
            certificates=self._extract_certificates(text),
            preferred_employment_percentage=self._extract_preferred_employment_percentage(text),
            preferred_locations=self._extract_preferred_locations(text),
            remote_preference=self._extract_remote_preference(text),
            salary_expectation=self._extract_salary_expectation(text),
            career_goals=self._extract_career_goals(text),
            availability=self._extract_availability(text),
        )

        profile.job_titles = [item.title for item in profile.work_experience if item.title]
        profile.years_experience = self._calculate_years_experience(profile.work_experience)
        profile.relevant_experience_years = profile.years_experience

        duplicate_skills = self._detect_duplicate_skills(text)
        profile.skills = self._deduplicate_skills(profile.skills, duplicate_skills)

        unsupported_fields = self._detect_unsupported_fields(text)

        fields_extracted = self._count_extracted_fields(profile)
        fields_needing_review = self._count_fields_needing_review(profile)

        execution_time_ms = int((time.perf_counter() - start) * 1000)
        audit = ExtractionAudit(
            fields_extracted=fields_extracted,
            fields_needing_review=fields_needing_review,
            duplicate_skills=duplicate_skills,
            unsupported_fields=unsupported_fields,
            model_used=self.model_name,
            execution_time_ms=execution_time_ms,
            token_estimate=max(1, len(text.split()) * 2),
            estimated_cost=round((len(text.split()) * 0.00002), 6),
        )
        return ProfileExtractionResult(profile=profile, audit=audit)

    def _extract_name(self, text: str) -> Optional[str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if not any(keyword in line.lower() for keyword in ["experience", "education", "skills", "languages", "summary"]):
                if len(line.split()) <= 8:
                    return line
        return None

    def _extract_skills(self, text: str) -> List[SkillItem]:
        skill_items: List[SkillItem] = []
        for term, canonical in self.SKILL_ALIASES.items():
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            if pattern.search(text):
                item = SkillItem(
                    name=canonical,
                    level=self._suggest_skill_level(term, text),
                    status="extracted",
                    provenance=Provenance(source="cv", confidence=0.9, status="unverified"),
                )
                skill_items.append(item)

        for term, canonical in self.AMBIGUOUS_SKILLS.items():
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            if pattern.search(text):
                item = SkillItem(
                    name=canonical,
                    level=None,
                    status="needs_review",
                    provenance=Provenance(source="cv", confidence=0.4, status="needs_review", comment="Ambiguous skill phrase extracted from text"),
                )
                skill_items.append(item)

        if not skill_items:
            return []
        return skill_items

    def _suggest_skill_level(self, skill: str, text: str) -> Optional[str]:
        patterns = {
            "python": [r"python\s*(?:expert|advanced|strong|proficient)", r"python\s*\d+\+?"],
            "sql": [r"sql\s*(?:expert|advanced|strong|proficient)", r"sql\s*queries"],
            "aws": [r"aws\s*(?:expert|advanced|strong|cloud)"],
        }
        lowered = text.lower()
        for pattern in patterns.get(skill, []):
            if re.search(pattern, lowered):
                return "advanced"
        return None

    def _extract_work_experience(self, text: str) -> List[WorkExperience]:
        entries: List[WorkExperience] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = re.search(
                r"(?P<start>\d{4})(?:\s*(?:-|–|to)\s*(?P<end>\d{4}|present|current))?\s+(?P<title>[^,]+?)(?:,\s*(?P<company>[^,]+?))(?:,\s*(?P<location>.*))?$",
                stripped,
                flags=re.IGNORECASE,
            )
            if match:
                title = match.group("title").strip()
                company = match.group("company").strip() if match.group("company") else None
                location = match.group("location").strip() if match.group("location") else None
                start_date = match.group("start")
                entries.append(
                    WorkExperience(
                        company=company,
                        title=title,
                        start_date=start_date,
                        end_date=None,
                        description=location,
                        status="extracted",
                        provenance=Provenance(source="cv", confidence=0.8, status="unverified"),
                    )
                )
            elif re.search(r"(?:^experience\s*:|^experience$|^role\s*:|^role$|worked at)", stripped, flags=re.IGNORECASE):
                if "," in stripped:
                    parts = [part.strip() for part in stripped.split(",")]
                    if len(parts) >= 2:
                        entries.append(
                            WorkExperience(
                                company=parts[-1],
                                title=parts[0],
                                start_date=None,
                                end_date=None,
                                description=None,
                                status="needs_review",
                                provenance=Provenance(source="cv", confidence=0.4, status="needs_review"),
                            )
                        )
        if not entries:
            return []
        return entries

    def _extract_education(self, text: str) -> Optional[List[EducationItem]]:
        items: List[EducationItem] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = re.search(
                r"(?P<year>\d{4})\s+(?P<degree>BSc|Bachelor|MSc|Master|MBA|Diploma|PhD|Certificate)\s+(?P<field>[^,]+?)(?:,\s*(?P<institution>.*))?$",
                stripped,
                flags=re.IGNORECASE,
            )
            if match:
                items.append(
                    EducationItem(
                        institution=match.group("institution").strip() if match.group("institution") else None,
                        degree=match.group("degree").strip(),
                        field=match.group("field").strip(),
                        graduation_year=int(match.group("year")),
                        status="extracted",
                        provenance=Provenance(source="cv", confidence=0.8, status="unverified"),
                    )
                )
        return items or None

    def _extract_languages(self, text: str) -> List[LanguageItem]:
        items: List[LanguageItem] = []
        lowered = text.lower()
        for alias, canonical in self.LANGUAGE_ALIASES.items():
            pattern = re.compile(rf"\b{re.escape(alias)}\b\s*(?:\b(?P<level>A1|A2|B1|B2|C1|C2|native|fluent|basic)\b|\b(?:level)\s*(?P<level2>A1|A2|B1|B2|C1|C2)\b)", re.IGNORECASE)
            match = pattern.search(lowered)
            if match:
                level = (match.group("level") or match.group("level2") or "").upper()
                items.append(
                    LanguageItem(
                        language=canonical,
                        level=level or None,
                        status="extracted",
                        provenance=Provenance(source="cv", confidence=0.9, status="unverified"),
                    )
                )
        if not items:
            return []
        return items

    def _extract_certificates(self, text: str) -> List[str]:
        certs: List[str] = []
        match = re.findall(r"(?:certificate|certification|certified)\s*[:\-]?\s*([A-Za-z0-9\-\s]+)", text, flags=re.IGNORECASE)
        if match:
            certs.extend([item.strip() for item in match if item.strip()])
        return certs

    def _extract_preferred_employment_percentage(self, text: str) -> Optional[int]:
        match = re.search(r"(?:preferred\s+employment|employment\s+preference|employment\s*[:\-]?\s*)(\d{1,3})%?", text, flags=re.IGNORECASE)
        if not match:
            match = re.search(r"\b(\d{1,3})%\b", text)
        if not match:
            return None
        value = int(match.group(1))
        if 0 <= value <= 100:
            return value
        return None

    def _extract_preferred_locations(self, text: str) -> Optional[List[str]]:
        match = re.search(r"preferred\s+locations?\s*[:\-]?\s*(.*)", text, flags=re.IGNORECASE)
        if not match:
            return None
        locations = [item.strip() for item in match.group(1).split(",")]
        cleaned = [loc for loc in locations if loc and not re.match(r"^(remote|yes|no|hybrid)$", loc, flags=re.IGNORECASE)]
        return cleaned or None

    def _extract_remote_preference(self, text: str) -> Optional[str]:
        if re.search(r"\bremote\s*[:\-]?\s*yes\b|\bremote\s*:\s*" , text, flags=re.IGNORECASE):
            return "yes"
        if re.search(r"\bremote\s*[:\-]?\s*no\b", text, flags=re.IGNORECASE):
            return "no"
        if re.search(r"\bremote\s*[:\-]?\s*hybrid\b", text, flags=re.IGNORECASE):
            return "hybrid"
        return None

    def _extract_salary_expectation(self, text: str) -> Optional[Dict[str, Any]]:
        patterns = [
            r"(?:salary\s*(?:expectation)?\s*[:\-]?\s*)(?:CHF\s*)?(\d[\d,]*)\s*(?:-|–|to)\s*(\d[\d,]*)",
            r"(?:salary\s*(?:expectation)?\s*[:\-]?\s*)(?:CHF\s*)?(\d[\d,]*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    low = int(match.group(1).replace(",", ""))
                    high = int(match.group(2).replace(",", ""))
                    return {"min": low, "max": high, "currency": "CHF"}
                low = int(match.group(1).replace(",", ""))
                return {"min": low, "max": low, "currency": "CHF"}
        return None

    def _extract_career_goals(self, text: str) -> Optional[List[str]]:
        match = re.search(r"(?:career goals?|career objective)\s*[:\-]?\s*(.*)", text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return [value]
        return None

    def _extract_availability(self, text: str) -> Optional[str]:
        match = re.search(r"(?:availability|available\s+from)\s*[:\-]?\s*(?:from\s+)?(\d{4}-\d{2}-\d{2})", text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _calculate_years_experience(self, work_experience: List[WorkExperience]) -> Optional[int]:
        if not work_experience:
            return None
        total = 0
        for item in work_experience:
            if item.start_date and item.end_date:
                try:
                    start = int(item.start_date[:4])
                    end = int(item.end_date[:4])
                    total += max(end - start, 0)
                except ValueError:
                    continue
        return total or None

    def _detect_duplicate_skills(self, text: str) -> List[str]:
        duplicates: List[str] = []
        for term, canonical in self.SKILL_ALIASES.items():
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            if len(pattern.findall(text)) > 1:
                duplicates.append(canonical.lower())
        return duplicates

    def _deduplicate_skills(self, skills: List[SkillItem], duplicate_skills: List[str]) -> List[SkillItem]:
        seen: Dict[str, SkillItem] = {}
        ordered: List[SkillItem] = []
        for skill in skills:
            key = skill.name.strip().lower()
            if key not in seen:
                seen[key] = skill
                ordered.append(skill)
        return ordered

    def _detect_unsupported_fields(self, text: str) -> List[str]:
        unsupported: List[str] = []
        for key, patterns in self.UNSUPPORTED_FIELD_PATTERNS.items():
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                unsupported.append(key)
        return unsupported

    def _count_extracted_fields(self, profile: CandidateProfessionalProfile) -> int:
        count = 0
        count += len(profile.skills)
        count += len(profile.work_experience)
        if profile.education:
            count += len(profile.education)
        count += len(profile.languages)
        if profile.salary_expectation is not None:
            count += 1
        if profile.preferred_locations is not None:
            count += 1
        if profile.remote_preference is not None:
            count += 1
        if profile.availability is not None:
            count += 1
        if profile.career_goals:
            count += len(profile.career_goals)
        if profile.preferred_employment_percentage is not None:
            count += 1
        if profile.name:
            count += 1
        return count

    def _count_fields_needing_review(self, profile: CandidateProfessionalProfile) -> int:
        review_count = 0
        review_count += sum(1 for skill in profile.skills if skill.status == "needs_review")
        review_count += sum(1 for experience in profile.work_experience if experience.status == "needs_review")
        if profile.education:
            review_count += sum(1 for item in profile.education if item.status == "needs_review")
        review_count += sum(1 for language in profile.languages if language.status == "needs_review")
        return review_count
