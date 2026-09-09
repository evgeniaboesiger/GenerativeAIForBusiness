"""
Matching Agent - Calculates match scores and generates explanations
Uses deterministic scoring with LLM for explanations only

The numerical score always comes from deterministic calculation, NEVER from
the LLM. Candidate employment preferences feed the deterministic scoring
through dedicated weight buckets (see WEIGHTS) and are explained to the
candidate as preference checks.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from preferences import (
    career_goal_compatibility,
    commute_compatibility,
    company_size_compatibility,
    employment_compatibility,
    job_career_signals,
    location_compatibility,
    normalise_preferences,
    remote_compatibility,
    salary_compatibility,
)
import telemetry


class MatchingAgent:
    """
    Agent that matches candidates to jobs using deterministic scoring.

    Matching weights stay exactly as specified in the brief:
    skills 30%, experience 20%, education 10%, languages 10%,
    location/remote 10%, employment preference 10%, salary 5%, career goals 5%.
    """

    # Matching weights as specified in the project brief
    WEIGHTS = {
        "skills": 0.30,           # 30%
        "experience": 0.20,       # 20%
        "education": 0.10,        # 10%
        "languages": 0.10,        # 10%
        "location_remote": 0.10,  # 10%  (location + commute + remote)
        "employment_preference": 0.10,  # 10% (employment percentage)
        "salary": 0.05,           # 5%
        "career_goals": 0.05      # 5%  (career goals + work values)
    }

    # Sub-weights inside the location/remote bucket (sums to 1.0)
    LOCATION_SUBWEIGHTS = {"location": 0.40, "commute": 0.30, "remote": 0.30}

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2"

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def find_matches(self, profile: Dict[str, Any], jobs: List[Dict[str, Any]],
                     top_n: int = 5, use_ai: bool = True,
                     record_telemetry: bool = False) -> List[Dict[str, Any]]:
        """
        Find and rank job matches for a candidate.

        Args:
            profile: Structured candidate profile (may carry a "preferences" key)
            jobs: List of job listings
            top_n: Number of top matches to return
            use_ai: If True, use LLM for explanations. If False, use
                    fast deterministic explanations (no AI needed).
            record_telemetry: If True, log an anonymized aggregate run record.

        Returns:
            List of matches with scores, explanations and preference checks
        """
        start = time.time()
        matches = []
        first_relevant_rank: Optional[int] = None

        for job in jobs:
            mandatory_met = self._check_mandatory_requirements(profile, job)
            score, score_breakdown, pref_checks = self._calculate_score(profile, job)

            explanation = ""
            if score > 0:
                if use_ai:
                    explanation = self._generate_ai_explanation(profile, job, score, pref_checks)
                else:
                    explanation = self._fast_explanation(profile, score, pref_checks)

            match_result = {
                "job_id": job["id"],
                "job_title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "mandatory_met": mandatory_met,
                "score": round(score * 100, 1),
                "score_breakdown": {k: round(v * 100, 1) for k, v in score_breakdown.items()},
                "explanation": explanation,
                "preference_checks": pref_checks,
                "job_details": job.get("details", {}),
                "start_date": job.get("details", {}).get("start_date", ""),
            }
            matches.append(match_result)

        matches.sort(key=lambda x: (x["mandatory_met"], x["score"]), reverse=True)
        top = matches[:top_n]

        if record_telemetry:
            for idx, m in enumerate(top):
                if m["score"] >= telemetry._RELEVANCE_THRESHOLD:
                    first_relevant_rank = idx + 1
                    break
            telemetry.log_matching_run(
                version=telemetry.detect_version(profile),
                jobs_reviewed=len(jobs),
                matches_returned=len(top),
                scores=[m["score"] for m in top],
                elapsed_s=time.time() - start,
                first_relevant_rank=first_relevant_rank,
            )

        return top

    def _fast_explanation(self, profile: Dict[str, Any], score: float,
                          pref_checks: List[Dict[str, str]]) -> str:
        """Deterministic explanation assembled from the preference checks."""
        if not pref_checks:
            return f"This job matches your profile with a {round(score * 100)}% score."

        ok_lines = [f"✓ {c['text']}" for c in pref_checks if c["status"] == "ok"]
        warn_lines = [f"⚠ {c['text']}" for c in pref_checks if c["status"] == "warn"]

        parts = ["Why this job matches your preferences:"]
        if ok_lines:
            parts.extend(ok_lines[:5])
        if warn_lines:
            parts.append("Things to consider:")
            parts.extend(warn_lines[:3])
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    #  Mandatory requirements (hard filter, same behaviour as before)
    # ------------------------------------------------------------------ #
    def _check_mandatory_requirements(self, profile: Dict[str, Any], job: Dict[str, Any]) -> bool:
        mandatory = job.get("requirements", {}).get("mandatory", [])
        profile_text = json.dumps(profile).lower()

        for requirement in mandatory:
            req_lower = requirement.lower()

            if "years" in req_lower or "experience" in req_lower:
                numbers = re.findall(r'\d+', req_lower)
                if numbers:
                    if "years" in profile_text or "experience" in profile_text:
                        continue
                    else:
                        return False

            elif "german" in req_lower or "french" in req_lower or "english" in req_lower:
                language_found = False
                for lang in profile.get("languages", []):
                    if isinstance(lang, dict):
                        lang_name = lang.get("language", "").lower()
                        if req_lower.split()[0] in lang_name:
                            language_found = True
                            break
                if not language_found:
                    return False

            else:
                req_words = [w for w in req_lower.split() if len(w) > 3]
                if req_lower not in profile_text and not any(w in profile_text for w in req_words):
                    return False

        return True

    # ------------------------------------------------------------------ #
    #  Deterministic scoring
    # ------------------------------------------------------------------ #
    def _calculate_score(self, profile: Dict[str, Any], job: Dict[str, Any]
                         ) -> Tuple[float, Dict[str, float], List[Dict[str, str]]]:
        """
        Calculate deterministic match score based on weighted criteria.

        Returns:
            (total_score, score_breakdown, preference_checks)
        """
        raw_prefs = profile.get("preferences") or {}
        prefs = normalise_preferences(raw_prefs)
        checks: List[Dict[str, str]] = []

        scores = {}
        scores["skills"] = self._score_skills(profile, job)
        scores["experience"] = self._score_experience(profile, job)
        scores["education"] = self._score_education(profile, job)
        scores["languages"] = self._score_languages(profile, job)
        scores["location_remote"], location_checks = self._score_location_remote(prefs, job)
        scores["employment_preference"], empl_checks = self._score_employment_preference(prefs, job)
        scores["salary"], salary_checks = self._score_salary(prefs, job)
        scores["career_goals"], goals_checks = self._score_career_goals(prefs, job)

        # Additional, explanation-only preference signals (no weight bucket).
        checks.extend(self._explain_language_preference(prefs, job))
        checks.extend(self._explain_availability(prefs, job))
        checks.extend(self._explain_company_size(prefs, job))
        checks = location_checks + empl_checks + salary_checks + goals_checks + checks

        total_score = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        return total_score, scores, checks

    def _score_skills(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        profile_skills = set(s.lower() for s in profile.get("skills", []))
        job_skills = set(s.lower() for s in job.get("skills_required", []))
        if not job_skills:
            return 0.5
        matched = profile_skills.intersection(job_skills)
        match_ratio = len(matched) / len(job_skills)
        return min(match_ratio * 1.2, 1.0)

    def _score_experience(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        work_exp = profile.get("work_experience", [])
        if not work_exp:
            # Some credit for education. A career break (no work history) is
            # never treated as a disqualification here.
            return 0.3
        total_years = 0
        for exp in work_exp:
            duration = exp.get("duration", "")
            if "-" in duration:
                try:
                    start, end = duration.split("-")
                    start_year = int(start.strip())
                    end_year = int(end.strip()) if end.strip().isdigit() else 2024
                    total_years += end_year - start_year
                except Exception:
                    pass
        if total_years >= 5:
            return 1.0
        elif total_years >= 3:
            return 0.8
        elif total_years >= 1:
            return 0.6
        else:
            return 0.4

    def _score_education(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        education = profile.get("education", [])
        if not education:
            return 0.3
        has_masters = any("master" in edu.get("degree", "").lower() for edu in education)
        has_bachelors = any("bachelor" in edu.get("degree", "").lower() for edu in education)
        if has_masters:
            return 1.0
        elif has_bachelors:
            return 0.8
        else:
            return 0.5

    def _score_languages(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """
        Language PROFICIENCY score. This is factual qualification data and is
        deliberately kept separate from the preferred working languages
        preference (see _explain_language_preference).
        """
        languages = profile.get("languages", [])
        job_requirements = job.get("requirements", {}).get("mandatory", [])
        required_languages = []
        for req in job_requirements:
            for lang_name in ("german", "french", "english"):
                if lang_name in req.lower():
                    required_languages.append(lang_name)

        if not required_languages:
            return 0.8

        profile_langs = {}
        for lang in languages:
            if isinstance(lang, dict):
                lang_name = lang.get("language", "").lower()
                level = lang.get("level", "").lower()
                profile_langs[lang_name] = level

        scores = []
        for req_lang in required_languages:
            if req_lang in profile_langs:
                level = profile_langs[req_lang]
                if any(token in level for token in ("native", "fluent", "c1", "c2")):
                    scores.append(1.0)
                elif any(token in level for token in ("intermediate", "b1", "b2")):
                    scores.append(0.7)
                else:
                    scores.append(0.5)
            else:
                scores.append(0.0)

        return sum(scores) / len(scores) if scores else 0.5

    # ------------------------------------------------------------------ #
    #  Preference-driven scoring buckets
    # ------------------------------------------------------------------ #
    def _score_location_remote(self, prefs: Dict[str, Any], job: Dict[str, Any]
                               ) -> Tuple[float, List[Dict[str, str]]]:
        """
        Location/Remote bucket (10% weight):
        location (40%) + commute (30%) + remote preference (30%).
        """
        details = job.get("details", {}) or {}
        job_location = job.get("location", "")
        job_commute = job.get("commute_minutes")
        job_remote_pct = job.get("remote_pct")
        job_details = job.get("details", {}) or {}
        job_geo = f"{job_location} {details.get('region', '')}".strip()

        loc = location_compatibility(prefs.get("preferred_locations", []),
                                     job_geo, prefs.get("relocation_willing", False))
        commute = commute_compatibility(prefs.get("max_commute_minutes"),
                                        job_commute, job_remote_pct)
        remote = remote_compatibility(prefs.get("remote_preference", "No preference"),
                                      prefs.get("remote_importance"), job_remote_pct)

        score = (loc * self.LOCATION_SUBWEIGHTS["location"]
                 + commute * self.LOCATION_SUBWEIGHTS["commute"]
                 + remote * self.LOCATION_SUBWEIGHTS["remote"])

        checks: List[Dict[str, str]] = []
        preferred_locs = prefs.get("preferred_locations", [])
        if preferred_locs:
            if loc >= 0.9:
                checks.append({"status": "ok", "text": f"Location {job_location} is among your preferred places to work."})
            elif loc <= 0.3:
                checks.append({"status": "warn", "text": f"The position is located in {job_location}, which is not on your preferred location list."})
            else:
                checks.append({"status": "info", "text": f"The position is in {job_location} (you are open to relocation)."})

        max_commute = prefs.get("max_commute_minutes")
        if job_commute is not None:
            if commute >= 0.9:
                checks.append({"status": "ok", "text": f"Estimated commute of about {job_commute} minutes is within your limit."})
            elif max_commute is None:
                checks.append({"status": "info", "text": f"The estimated commute of about {job_commute} minutes is not a limiting factor (no maximum stated)."})
            elif commute >= 0.6:
                checks.append({"status": "info", "text": f"Estimated commute of about {job_commute} minutes is close to, or partially compensated by, remote work."})
            else:
                checks.append({"status": "warn", "text": f"The estimated commute of about {job_commute} minutes exceeds your stated limit" + (f" of {max_commute} minutes." if max_commute else ".")})

        remote_pref = prefs.get("remote_preference", "No preference")
        work_arr = job.get("work_arrangement") or (job_details.get("remote_policy") or "")
        if remote_pref and remote_pref != "No preference":
            if remote >= 0.9:
                checks.append({"status": "ok", "text": f"({remote_pref}) matches the position's work arrangement ({work_arr})."})
            elif remote >= 0.6:
                checks.append({"status": "info", "text": f"The position's work arrangement ({work_arr}) is a reasonable fit for your {remote_pref} preference."})
            else:
                checks.append({"status": "warn", "text": f"The position offers {work_arr}, which does not match your {remote_pref} preference."})

        return score, checks

    def _score_employment_preference(self, prefs: Dict[str, Any], job: Dict[str, Any]
                                     ) -> Tuple[float, List[Dict[str, str]]]:
        """
        Employment preference bucket (10% weight): percentage compatibility.
        """
        job_min = job.get("employment_pct_min")
        job_max = job.get("employment_pct_max")
        job_details = job.get("details", {}) or {}
        job_type = job_details.get("employment_type", "")

        score = employment_compatibility(
            prefs.get("preferred_employment_target"),
            prefs.get("preferred_employment_min"),
            prefs.get("preferred_employment_max"),
            prefs.get("employment_flexible", False),
            job_min, job_max,
        )

        checks: List[Dict[str, str]] = []
        if job_min is not None:
            if score >= 0.9:
                checks.append({"status": "ok", "text": f"Employment level ({prefs.get('preferred_employment_target') or 'flexible'}%) is compatible with this position ({job_type})."})
            elif score >= 0.5:
                checks.append({"status": "info", "text": f"Employment level ({job_type}) is close to your preferred range."})
            else:
                checks.append({"status": "warn", "text": f"Employment level ({job_type}) is outside your preferred range."})
        return score, checks

    def _score_salary(self, prefs: Dict[str, Any], job: Dict[str, Any]
                      ) -> Tuple[float, List[Dict[str, str]]]:
        """
        Salary bucket (5% weight). A mismatch lowers the score but never
        blocks a recommendation, and "flexible" softens the penalty.
        """
        job_min = job.get("salary_min")
        job_max = job.get("salary_max")
        job_range = job.get("details", {}).get("salary_range", "")

        score = salary_compatibility(
            prefs.get("salary_min"), prefs.get("salary_preferred"),
            prefs.get("salary_flexible", False), job_min, job_max,
        )

        checks: List[Dict[str, str]] = []
        if job_min is not None and (prefs.get("salary_min") or prefs.get("salary_preferred")):
            if score >= 0.9:
                checks.append({"status": "ok", "text": f"Salary range ({job_range}) overlaps with your expectations."})
            elif score >= 0.6:
                checks.append({"status": "info", "text": f"Salary range ({job_range}) is close to your expectations (you are open to discussion)."})
            else:
                checks.append({"status": "warn", "text": f"Salary range ({job_range}) is below your stated expectations. This is shown for transparency - you can still consider this role."})
        return score, checks

    def _score_career_goals(self, prefs: Dict[str, Any], job: Dict[str, Any]
                            ) -> Tuple[float, List[Dict[str, str]]]:
        """
        Career goals bucket (5% weight): goal alignment + small work-value
        bonus when the job exposes a matching structured attribute.
        """
        goals = prefs.get("career_goals", [])
        work_values = prefs.get("work_values", {})
        score = career_goal_compatibility(goals, job, work_values)

        checks: List[Dict[str, str]] = []
        if goals:
            signals = job_career_signals(job)
            aligned = [g for g in goals
                       if GOAL_SIGNAL_LOOKUP.get(g) and signals.get(GOAL_SIGNAL_LOOKUP[g])]
            neutral = [g for g in goals if g in ("Career change", "Enter a new industry")]
            if aligned:
                checks.append({"status": "ok", "text": "Career goal alignment: " + ", ".join(aligned[:3]) + "."})
            elif neutral and not aligned:
                checks.append({"status": "info", "text": "This position is a new direction for you - switching paths is not penalized here."})
            else:
                checks.append({"status": "info", "text": "This role is not directly aligned with your stated career goals, but your skills still matter."})

            matched_values = [
                label for key, label in WORK_VALUE_LABELS
                if work_values.get(key, 0) >= 4 and int((job.get("work_values") or {}).get(key, 0)) >= 4
            ]
            if matched_values:
                checks.append({"status": "ok", "text": "Work values: the position supports " + ", ".join(matched_values[:3]) + "."})

        return score, checks

    # ------------------------------------------------------------------ #
    #  Explanation-only preference signals (no weight bucket)
    # ------------------------------------------------------------------ #
    def _explain_language_preference(self, prefs: Dict[str, Any], job: Dict[str, Any]) -> List[Dict[str, str]]:
        preferred = prefs.get("preferred_working_languages", [])
        if not preferred:
            return []
        job_langs = job.get("working_languages", [])
        if not job_langs:
            return []
        norm = [l.lower() for l in job_langs]
        matched = any(p.lower() in norm for p in preferred)
        if matched:
            return [{"status": "ok", "text": "Your preferred working languages match the languages used in this position."}]
        return [{"status": "warn", "text": f"The position mainly operates in {', '.join(job_langs)} while you prefer {', '.join(preferred)}. Language proficiency remains the deciding factor."}]

    def _explain_availability(self, prefs: Dict[str, Any], job: Dict[str, Any]) -> List[Dict[str, str]]:
        availability = prefs.get("availability")
        start_date = job.get("details", {}).get("start_date", "")
        if not availability:
            return []
        if not start_date or start_date.lower() == "flexible":
            return [{"status": "info", "text": f"Availability: you can start {availability}. The position has a flexible start."}]
        return [{"status": "info", "text": f"Availability: you can start {availability}; the position starts {start_date}."}]

    def _explain_company_size(self, prefs: Dict[str, Any], job: Dict[str, Any]) -> List[Dict[str, str]]:
        compat = company_size_compatibility(prefs.get("company_size_preference", "No preference"),
                                            job.get("company_size"))
        if compat is None:
            return []
        if compat >= 0.9:
            return [{"status": "ok", "text": f"Company size ({job.get('company_size')}) matches your organizational preference."}]
        return [{"status": "warn", "text": f"The company is a {job.get('company_size')}-sized organization, which differs from your preferred size."}]

    # ------------------------------------------------------------------ #
    #  AI explanation (explanations only - never scores)
    # ------------------------------------------------------------------ #
    def _generate_ai_explanation(self, profile: Dict[str, Any], job: Dict[str, Any],
                                 score: float, pref_checks: List[Dict[str, str]]) -> str:
        prompt = f"""You are a helpful HR assistant. Explain this job match to the candidate.

CANDIDATE PROFILE:
- Name: {profile.get('personal_info', {}).get('name', 'N/A')}
- Skills: {', '.join(profile.get('skills', [])[:5])}
- Experience: {len(profile.get('work_experience', []))} positions
- Location: {profile.get('personal_info', {}).get('location', 'N/A')}

JOB:
- Title: {job.get('title', 'N/A')}
- Company: {job.get('company', 'N/A')}
- Location: {job.get('location', 'N/A')}
- Required Skills: {', '.join(job.get('skills_required', [])[:5])}

MATCH SCORE: {round(score * 100)}%

PREFERENCE CHECKS (machine-generated, do not contradict these):
{json.dumps(pref_checks, ensure_ascii=False)}

Write a brief, friendly explanation (3-4 sentences) of:
1. Why this is a good match (top 2-3 strengths)
2. Any areas that could be improved
3. A encouraging closing statement

Be specific and reference actual details from the profile and job.
Do NOT make up any information. Do NOT mention personality, culture fit,
loyalty or any psychological assessment."""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 300}
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            return self._fast_explanation(profile, score, pref_checks)


GOAL_SIGNAL_LOOKUP = {
    "Career advancement": "career_advancement",
    "Leadership": "leadership",
    "Return to work": "return_friendly",
    "Re-entering after a career break": "return_friendly",
    "Gain professional experience": "jr_entry",
    "Develop new skills": "learning",
    "Specialize in an existing field": "specialization",
    "Increase responsibility": "career_advancement",
    "Improve work-life balance": "flexible_hours",
    "Find greater job stability": "stability",
}

WORK_VALUE_LABELS = [
    ("work_life_balance", "Work-life balance"),
    ("career_development", "Career development"),
    ("job_stability", "Job stability"),
    ("autonomy", "Autonomy"),
    ("teamwork", "Teamwork"),
    ("innovation", "Innovation"),
    ("social_impact", "Social impact"),
    ("sustainability", "Sustainability"),
    ("learning", "Learning"),
    ("international_environment", "International environment"),
]


# ---------------------------------------------------------------------- #
#  CLI self-test
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    agent = MatchingAgent()

    test_profile = {
        "personal_info": {"name": "Sophie Müller", "location": "Basel"},
        "skills": ["Digital Marketing", "Brand Management", "SEO/SEM", "Google Analytics"],
        "work_experience": [{"duration": "2018-2022"}],
        "education": [{"degree": "Master of Science in Marketing"}],
        "languages": [{"language": "German", "level": "Native"}, {"language": "English", "level": "Fluent"}],
        "preferences": {
            "preferred_employment_target": 80,
            "salary_preferred": 90000,
            "preferred_locations": ["Basel"],
            "remote_preference": "Hybrid",
            "career_goals": ["Career advancement"],
        }
    }

    import os
    jobs_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "data", "sample_jobs.json")
    with open(jobs_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    print("Testing Matching Agent with structured preferences...")
    matches = agent.find_matches(test_profile, jobs, top_n=5, use_ai=False)
    for m in matches:
        print(f"- {m['job_title']} ({m['company']}): {m['score']}% mandatory_met={m['mandatory_met']}")
        for c in m["preference_checks"]:
            symbol = {"ok": "[OK]", "warn": "[!]", "info": "[i]"}[c["status"]]
            print(f"    {symbol} {c['text']}")
    print("\nMATCHING AGENT SELF-TEST COMPLETE")