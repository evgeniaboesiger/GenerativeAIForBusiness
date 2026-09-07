"""
Deterministic matching engine for FRAUMATCH.

Ethical constraint: The engine explicitly avoids using protected attributes
such as gender, age, nationality, ethnicity, religion, disability, or
other sensitive attributes as factors in scoring. The algorithm is based
solely on job-relevant professional attributes (skills, experience,
education, languages, location, employment preferences, salary, career goals).
"""
from typing import Dict, Any, List, Tuple
import time
from math import floor

ALGORITHM_VERSION = "1.0"

# Component weights (sum to 100)
WEIGHTS = {
    "skills": 30,
    "experience": 20,
    "education": 10,
    "languages": 10,
    "location": 10,
    "employment": 10,
    "salary": 5,
    "career_goal": 5,
}


def _level_to_score(level: str) -> int:
    # Map language/skill levels to numeric
    mapping = {
        "A2": 25,
        "B1": 50,
        "B2": 75,
        "C1": 90,
        "C2": 100,
        "beginner": 25,
        "intermediate": 50,
        "advanced": 75,
        "expert": 100,
    }
    return mapping.get(level, 0)


def compute_skills_score(candidate: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    required = job.get("required_skills") or []
    preferred = job.get("preferred_skills") or []
    cand_skills = [s["skill"].lower() if isinstance(s, dict) else s.lower() for s in candidate.get("skills", [])]

    # normalize required and preferred skill representations (allow dict or plain string)
    required_names = [r.get("skill").lower() if isinstance(r, dict) else r.lower() for r in required]
    preferred_names = [p.get("skill").lower() if isinstance(p, dict) else p.lower() for p in preferred]

    req_found = [r for r in required_names if r in cand_skills]
    pref_found = [p for p in preferred_names if p in cand_skills]

    req_score = (len(req_found) / max(1, len(required))) if required else 1.0
    pref_score = (len(pref_found) / max(1, len(preferred))) if preferred else 0.0

    # required skills more important (75% within skills component)
    skills_pct = req_score * 0.75 + pref_score * 0.25
    return round(skills_pct * 100, 2), req_found, pref_found


def compute_experience_score(candidate: Dict[str, Any], job: Dict[str, Any]) -> float:
    cand_years = candidate.get("years_experience", 0)
    min_years = job.get("minimum_years_experience") or 0

    if min_years == 0:
        return 100.0
    if cand_years >= min_years:
        return 100.0
    # partial credit for transferable experience
    ratio = cand_years / min_years
    return round(max(0.0, ratio * 100), 2)


def compute_education_score(candidate: Dict[str, Any], job: Dict[str, Any]) -> float:
    req = job.get("education_requirements") or ""
    if not req:
        return 100.0
    # simple string match against candidate education fields
    for edu in candidate.get("education", []):
        if req.lower() in (edu.get("degree") or "").lower() or req.lower() in (edu.get("field") or "").lower():
            return 100.0
    return 50.0


def compute_language_score(candidate: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str]]:
    # job.language_requirements expected as list of dicts: {language, level, mandatory}
    reqs = job.get("language_requirements") or []
    candidate_langs = {l["language"]: l["level"] for l in candidate.get("languages", [])}
    missing_mandatory = []
    scores = []
    for r in reqs:
        lang = r.get("language")
        required_level = r.get("level")
        mandatory = r.get("mandatory", False)
        cand_level = candidate_langs.get(lang)
        if not cand_level:
            if mandatory:
                missing_mandatory.append(lang)
            scores.append(0)
            continue
        req_score = _level_to_score(required_level)
        cand_score = _level_to_score(cand_level)
        # if candidate >= required -> full
        if cand_score >= req_score:
            scores.append(100)
        else:
            scores.append(round((cand_score / req_score) * 100, 2) if req_score else 0)

    if not reqs:
        return 100.0, []
    avg = sum(scores) / len(scores)
    return round(avg, 2), missing_mandatory


LOCATION_CLUSTER = {
    "zurich": ["Zurich", "Winterthur", "Bülach", "Uster", "Dietikon", "Schlieren", "Dielsdorf", "Baden"],
    "bern": ["Bern", "Biel", "Aarau"],
    "basel": ["Basel"],
    "lausanne": ["Lausanne", "Geneva"],
    "lucerne": ["Lucerne"],
    "stgallen": ["St. Gallen"],
    "zug": ["Zug"],
}


def commute_minutes(candidate_loc: str, job_loc: str) -> int:
    if not candidate_loc or not job_loc:
        return 120
    if candidate_loc == job_loc:
        return 20
    # find clusters
    cand_cluster = None
    job_cluster = None
    for k, v in LOCATION_CLUSTER.items():
        if candidate_loc in v:
            cand_cluster = k
        if job_loc in v:
            job_cluster = k
    if cand_cluster and job_cluster:
        if cand_cluster == job_cluster:
            return 35
        # adjacent clusters approximate
        return 65
    return 120


def compute_location_score(candidate: Dict[str, Any], job: Dict[str, Any]) -> float:
    commute = commute_minutes(candidate.get("location"), job.get("location"))
    max_commute = candidate.get("maximum_commute_minutes", 60)
    remote_pref = candidate.get("remote_preference", "office")
    job_remote = job.get("remote_percentage", 0)

    # remote preference improves score when job offers remote
    if job_remote >= 50 and remote_pref in ("hybrid", "remote"):
        return 100.0

    if commute <= 30:
        return 100.0
    if commute <= 60:
        return 70.0
    if commute <= 90:
        return 40.0
    return 10.0


def compute_employment_score(candidate: Dict[str, Any], job: Dict[str, Any]) -> float:
    cmin = candidate.get("employment_percentage_min", 50)
    cmax = candidate.get("employment_percentage_max", 100)
    jmin = job.get("employment_percentage_min") or job.get("employment_percentage") or 50
    jmax = job.get("employment_percentage_max") or job.get("employment_percentage") or 100

    # full if ranges overlap strongly
    if cmin <= jmin and cmax >= jmax:
        return 100.0
    # partial overlap
    overlap_min = max(cmin, jmin)
    overlap_max = min(cmax, jmax)
    if overlap_max >= overlap_min:
        # proportional to overlap fraction
        overlap_fraction = (overlap_max - overlap_min) / max(1, (jmax - jmin)) if (jmax - jmin) > 0 else 1
        return round(min(100, overlap_fraction * 100 + 50), 2)
    return 20.0


def compute_salary_score(candidate: Dict[str, Any], job: Dict[str, Any]) -> float:
    cmin = candidate.get("salary_expectation_min", 0)
    cmax = candidate.get("salary_expectation_max", 9999999)
    jmin = job.get("salary_min") or 0
    jmax = job.get("salary_max") or 9999999

    # if candidate expectation within job range
    if cmin >= jmin and cmax <= jmax:
        return 100.0
    # if overlap
    if cmin <= jmax and cmax >= jmin:
        # partial score based on how much of expected range is covered
        covered = min(cmax, jmax) - max(cmin, jmin)
        expected_span = max(1, cmax - cmin)
        frac = max(0, covered / expected_span)
        return round(frac * 100, 2)
    # candidate expects much more
    return 10.0


def compute_career_goal_score(candidate: Dict[str, Any], job: Dict[str, Any]) -> float:
    goal = (candidate.get("career_goal") or "").lower()
    desired = [d.lower() for d in candidate.get("desired_roles", [])]
    title = (job.get("title") or "").lower()
    dept = (job.get("department") or "").lower()
    if title in goal or any(t in title for t in desired):
        return 100.0
    # transferable if department matches
    if dept and dept in goal:
        return 70.0
    return 40.0


def check_mandatory_requirements(candidate: Dict[str, Any], job: Dict[str, Any]) -> Tuple[bool, List[str]]:
    missing = []
    # languages
    lang_score, missing_langs = compute_language_score(candidate, job)
    if missing_langs:
        missing.extend([f"Missing mandatory language: {l}" for l in missing_langs])

    # mandatory skills: treat required_skills as mandatory if marked so in job (we expect job to mark some as mandatory)
    required = job.get("required_skills") or []
    cand_skills = [s["skill"].lower() if isinstance(s, dict) else s.lower() for s in candidate.get("skills", [])]
    # job.required_skills can be list of {skill, mandatory}
    for r in required:
        if isinstance(r, dict):
            skill_name = r.get("skill")
            if r.get("mandatory") and skill_name.lower() not in cand_skills:
                missing.append(f"Missing mandatory skill: {skill_name}")
        else:
            # if plain string treat as required but not mandatory by default
            pass

    # education
    edu_req = job.get("education_requirements")
    if edu_req:
        met = False
        for edu in candidate.get("education", []):
            if edu_req.lower() in ((edu.get("degree") or "").lower() + " " + (edu.get("field") or "").lower()):
                met = True
        if not met:
            missing.append(f"Education requirement not met: {edu_req}")

    return (len(missing) == 0), missing


def score_candidate_job(candidate: Dict[str, Any], job: Dict[str, Any], assessments: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    start = time.time()
    # compute component scores
    skills_score, req_found, pref_found = compute_skills_score(candidate, job)
    experience_score = compute_experience_score(candidate, job)
    education_score = compute_education_score(candidate, job)
    language_score, missing_mandatory_langs = compute_language_score(candidate, job)
    location_score = compute_location_score(candidate, job)
    employment_score = compute_employment_score(candidate, job)
    salary_score = compute_salary_score(candidate, job)
    career_goal_score = compute_career_goal_score(candidate, job)

    # weighted overall
    components = {
        "skills": skills_score,
        "experience": experience_score,
        "education": education_score,
        "languages": language_score,
        "location": location_score,
        "employment": employment_score,
        "salary": salary_score,
        "career_goal": career_goal_score,
    }

    overall = 0.0
    for k, v in WEIGHTS.items():
        overall += components.get(k, 0) * (v / 100.0)

    overall = round(overall, 2)

    mandatory_met, missing_reasons = check_mandatory_requirements(candidate, job)

    # category mapping
    category = "Not recommended"
    if not mandatory_met:
        category = "Not recommended"
    else:
        if overall >= 90:
            category = "Excellent match"
        elif overall >= 80:
            category = "Strong match"
        elif overall >= 70:
            category = "Potential match"
        elif overall >= 60:
            category = "Weak match"
        else:
            category = "Not recommended"

    strengths = []
    gaps = []
    if req_found:
        strengths.append(f"{len(req_found)} required skills matched")
    if pref_found:
        strengths.append(f"{len(pref_found)} preferred skills matched")
    if language_score >= 90:
        strengths.append("Languages meet or exceed requirements")
    if salary_score >= 90:
        strengths.append("Salary expectation within range")

    if missing_reasons:
        gaps.extend(missing_reasons)
    if experience_score < 50:
        gaps.append("Insufficient relevant experience")

    explanation_lines = []
    explanation_lines.extend(strengths)
    if gaps:
        explanation_lines.append("Gaps:")
        explanation_lines.extend(gaps)

    end = time.time()
    execution_time_ms = int((end - start) * 1000)

    result = {
        "candidate_id": candidate.get("id"),
        "job_id": job.get("id"),
        "overall_score": overall,
        "category": category,
        "mandatory_requirements_met": mandatory_met,
        "component_scores": components,
        "strengths": strengths,
        "gaps": gaps,
        "recommendation": "Not recommended" if not mandatory_met or overall < 60 else "Recommended",
        "explanation": "\n".join(explanation_lines),
        "execution_time_ms": execution_time_ms,
        "algorithm_version": ALGORITHM_VERSION,
    }

    return result
