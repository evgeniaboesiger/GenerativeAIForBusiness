"""
MATCHA - Candidate Assessment: "Areas to Improve" recommendations.

A deterministic, job-relevant gap analysis. It compares the candidate's
profile plus their explicit preferences against the structured job data and
produces improvement recommendations in two categories:

    professional   - hard qualifications: skills, languages, experience,
                     education and certifications needed for the roles the
                     candidate is closest to.
    admin          - administrative & profile-setup improvements: missing
                     profile/CV information, certifications, and preference /
                     availability data that would make matching work better.

Ethical contract (same as the rest of the platform):
- Recommendations are based ONLY on job-relevant, factual gaps.
- No personality, motivation, loyalty, "culture fit", or psychological
  assessment is made or recommended.
- Career breaks are never framed as something to "fix".
- If the candidate is already strong somewhere, no improvement is suggested.

Everything is deterministic and unit-tested.
"""

import re
from typing import Any, Dict, List

# Required only for ranking the candidate's best-fit roles.
from matching_agent import MatchingAgent

COMPLETENESS_FIELDS = ("name", "location", "email")

ADMIN_ROLE_WORDS = ("assistant", "coordinator", "secretary", "office", "admin", "hr ")
ADMIN_SKILL_WORDS = ("administrative support", "organization", "scheduling", "time management",
                     "office", "coordination", "administration", "calendar")


class RecommendationEngine:
    """Generate categorized, deterministic improvement recommendations."""

    def __init__(self, top_n: int = 4):
        self.top_n = top_n
        self._agent = MatchingAgent()

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def assess(self, profile: Dict[str, Any], jobs: List[Dict[str, Any]],
               preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Full assessment.

        Returns:
            {
              "professional": [ {priority, area, detail, action, source_jobs}, ...],
              "admin":        [ ... ],
              "top_jobs":     [ {title, company, score}, ... ],
            }
        """
        if preferences is None:
            preferences = profile.get("preferences") or {}
        merged = {**profile}

        ranked = self._agent.find_matches(merged, jobs, top_n=self.top_n, use_ai=False)
        top_jobs = [{"title": m["job_title"], "company": m["company"],
                     "score": m["score"], "job_id": m["job_id"]} for m in ranked]
        job_by_id = {j["id"]: j for j in jobs}
        # Remember the top roles so admin-style ones can be recognised.
        self._admin_jobs_cache = [job_by_id[m["job_id"]] for m in ranked if m["job_id"] in job_by_id]

        professional: List[Dict[str, Any]] = []
        for match in ranked:
            job = job_by_id.get(match["job_id"])
            if job is None:
                continue
            is_top = match["job_id"] == (ranked[0]["job_id"] if ranked else None)
            for item in self._job_requirements_gaps(merged, job, top=is_top):
                self._merge(professional, "professional", item, match["job_title"])

        admin = self._completeness_gaps(merged, preferences)
        for item in admin:
            self._merge(admin, "admin", item, None)

        professional.sort(key=self._priority_rank)
        admin.sort(key=self._priority_rank)
        return {"professional": professional, "admin": admin, "top_jobs": top_jobs}

    def short_for_job(self, profile: Dict[str, Any], job: Dict[str, Any],
                      preferences: Dict[str, Any] = None) -> List[str]:
        """
        Compact, job-specific improvement list shown next to each match
        (used by the Job Matching page).
        """
        if preferences is None:
            preferences = profile.get("preferences") or {}
        merged = {**profile}
        if preferences:
            merged["preferences"] = preferences

        items = self._job_requirements_gaps(merged, job, top=False)
        items.sort(key=self._priority_rank)

        short = []
        for item in items[:3]:
            short.append(f"{item['area']} — {item['action']} ({item['priority']})")
        # A small, relevant admin hint if one exists.
        admin = self._completeness_gaps(merged, preferences)
        if admin and len(short) < 3:
            short.append(f"{admin[0]['area']} — {admin[0]['action']} ({admin[0]['priority']})")
        return short

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _priority_rank(item: Dict[str, Any]) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(item.get("priority"), 2)

    @staticmethod
    def _merge(items: List[Dict[str, Any]], category: str, item: Dict[str, Any],
               source_job: str) -> None:
        """Deduplicate items by area+detail and accumulate their source roles."""
        for existing in items:
            if (existing["area"], existing["detail"]) == (item["area"], item["detail"]):
                if source_job and source_job not in existing["source_jobs"]:
                    existing["source_jobs"].append(source_job)
                return
        item["source_jobs"] = [source_job] if source_job else []
        items.append(item)

    # ------------------------------------------------------------------ #
    #  Professional gaps (derived from the candidate's best-fit jobs)
    # ------------------------------------------------------------------ #
    def _job_requirements_gaps(self, profile: Dict[str, Any], job: Dict[str, Any],
                               top: bool) -> List[Dict[str, Any]]:
        """Improvements needed to meet a specific job's requirements."""
        items: List[Dict[str, Any]] = []
        profile_skills = set(s.lower() for s in profile.get("skills", []))

        # Skills required by the role but missing from the profile.
        for skill in job.get("skills_required", []):
            if skill.lower() not in profile_skills:
                base = "high" if top else "medium"
                items.append({
                    "priority": base,
                    "area": f"Add skill: {skill}",
                    "detail": f"'{skill}' is required/valuable for this role and is not in your profile.",
                    "action": f"Add or strengthen {skill} (courses, projects, or experience).",
                })

        # Language proficiency gaps vs. mandatory requirements.
        lang_levels = self._profile_language_levels(profile)
        for lang, required in self._required_languages(job):
            level = lang_levels.get(lang.lower())
            if level is None:
                items.append({
                    "priority": "high" if top else "medium",
                    "area": f"Learn {lang}",
                    "detail": f"{lang} is required for this role but is not on your profile.",
                    "action": f"Start learning or document your {lang} level.",
                })
            elif self._level_strength(level) < self._level_strength(required):
                items.append({
                    "priority": "medium",
                    "area": f"Improve {lang} ({level} → {required})",
                    "detail": f"The role expects {lang} at {required}; your level is {level}.",
                    "action": f"Work towards {lang} {required} (e.g., a language course or official test).",
                })

        # Experience-years gap vs. mandatory requirements.
        years_gap, required_years = self._experience_gap(profile, job)
        if years_gap > 0:
            items.append({
                "priority": "medium",
                "area": f"Gain more experience ({required_years}+ years)",
                "detail": "This role expects more years of experience than you currently show.",
                "action": "Continue gaining relevant experience; highlight transferable and project experience in your CV.",
            })

        # Education-level gap.
        edu_gap = self._education_gap(profile, job)
        if edu_gap:
            items.append({
                "priority": "medium",
                "area": f"Education: {edu_gap}",
                "detail": "A higher qualification appears in this role's requirements.",
                "action": "Consider a certification or degree that matches the requirement, and add it to your profile.",
            })

        # Nice-to-have / soft-credential gaps (always low priority).
        for requirement in job.get("requirements", {}).get("nice_to_have", []):
            req_lower = requirement.lower()
            if req_lower in " ".join(s.lower() for s in profile_skills):
                continue
            items.append({
                "priority": "low",
                "area": f"Nice-to-have: {requirement}",
                "detail": "Optional for the role, but it would strengthen your application.",
                "action": f"If you have this, add it to your profile/CV; if not, it is only optional.",
            })

        return items

    # ------------------------------------------------------------------ #
    #  Admin / profile-setup gaps
    # ------------------------------------------------------------------ #
    def _completeness_gaps(self, profile: Dict[str, Any],
                           preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Administrative & profile-completeness improvements."""
        items: List[Dict[str, Any]] = []
        personal = profile.get("personal_info", {}) or {}

        for field in COMPLETENESS_FIELDS:
            if not (personal.get(field) or "").strip() or (personal.get(field) or "").strip() == "N/A":
                items.append({
                    "priority": "low",
                    "area": f"Complete your {field}",
                    "detail": "Basic contact/profile information is missing.",
                    "action": f"Add your {field} to your profile.",
                })

        if not (profile.get("summary") or "").strip():
            items.append({
                "priority": "medium",
                "area": "Add a professional summary",
                "detail": "A summary helps put your strengths into context.",
                "action": "Write 2-3 sentences about your background and what you are looking for.",
            })

        if not profile.get("skills"):
            items.append({
                "priority": "high",
                "area": "Add your skills",
                "detail": "Skills are the foundation of the matching engine.",
                "action": "List at least a few skills - matching quality depends on them.",
            })

        if not profile.get("education"):
            items.append({
                "priority": "medium",
                "area": "Add your education",
                "detail": "Education is one of the matching criteria.",
                "action": "Add your degrees and institutions.",
            })

        if not profile.get("languages"):
            items.append({
                "priority": "medium",
                "area": "Add your languages",
                "detail": "Language requirements are checked per role.",
                "action": "Add your languages and your level for each.",
            })

        if not profile.get("work_experience"):
            items.append({
                "priority": "medium",
                "area": "Add your work history",
                "detail": "Experience contributes to matching. A career break is not a problem.",
                "action": "Add your roles, including volunteer or project experience. Career breaks are not penalized.",
            })

        if not profile.get("certifications"):
            items.append({
                "priority": "low",
                "area": "Add certifications",
                "detail": "Certifications are optional but strengthen applications.",
                "action": "Add any certificates you hold; many roles list them as nice-to-have.",
            })

        # Administrative skills for admin-style target roles.
        if admin_role_targeted(self._target_admin_jobs()) and not any(
                w in " ".join(s.lower() for s in profile.get("skills", [])) for w in ADMIN_SKILL_WORDS):
            items.append({
                "priority": "medium",
                "area": "Administrative skills",
                "detail": "Your best-fit roles lean administrative/coordinator-style.",
                "action": "Highlight skills like organization, coordination, administrative support, or scheduling.",
            })

        self._admin_preference_items(preferences, items)

        return items

    def _admin_preference_items(self, preferences: Dict[str, Any],
                                items: List[Dict[str, Any]]) -> None:
        prefs = preferences or {}
        if not prefs:
            items.append({
                "priority": "high",
                "area": "Complete your Career Goals & Preferences",
                "detail": "Preferences make recommendations noticeably more relevant.",
                "action": "Fill in the Career Goals wizard (employment %, salary, location, remote, etc.).",
            })
            return

        if not prefs.get("preferred_locations"):
            items.append({
                "priority": "medium",
                "area": "State preferred locations",
                "detail": "Location is used in every recommendation.",
                "action": "Choose 1-3 preferred cities on the Career Goals page.",
            })
        if not prefs.get("salary_min") and not prefs.get("salary_preferred") and not prefs.get("salary_flexible"):
            items.append({
                "priority": "low",
                "area": "Add salary expectations (or mark flexible)",
                "detail": "Salary is a small matching component and never blocks a job.",
                "action": "Add a range or tick 'Flexible / open to discussion'.",
            })
        if not prefs.get("availability"):
            items.append({
                "priority": "low",
                "area": "Add your availability",
                "detail": "Start-date informs recommendations transparently.",
                "action": "Set when you could start a new position.",
            })

    # ------------------------------------------------------------------ #
    #  Sub-analysis helpers (pure + deterministic)
    # ------------------------------------------------------------------ #
    def _target_admin_jobs(self) -> List[Dict[str, Any]]:
        """Jobs picked up by matching that look administrative. Filled from the
        last assess() ranking; cheap default returns [] (no nagging)."""
        return getattr(self, "_admin_jobs_cache", [])

    def _profile_language_levels(self, profile: Dict[str, Any]) -> Dict[str, str]:
        levels = {}
        for lang in profile.get("languages", []):
            if isinstance(lang, dict):
                levels[lang.get("language", "").lower()] = lang.get("level", "").lower()
            elif isinstance(lang, str):
                levels[lang.lower()] = "native"
        return levels

    @staticmethod
    def _required_languages(job: Dict[str, Any]) -> List[tuple]:
        langs = []
        for req in job.get("requirements", {}).get("mandatory", []):
            lower = req.lower()
            matched = [n for n in ("german", "french", "english") if n in lower]
            for m in matched:
                level = "B1"
                if "native" in lower or "c1" in lower or "c2" in lower or "fluent" in lower:
                    level = "C1"
                elif "b2" in lower or "intermediate" in lower:
                    level = "B2"
                langs.append((m.capitalize(), level))
        return list(set(langs))

    @staticmethod
    def _level_strength(level: str) -> int:
        l = level.lower()
        if any(t in l for t in ("native", "fluent", "c1", "c2")):
            return 3
        if any(t in l for t in ("b1", "b2", "intermediate")):
            return 2
        return 1

    @staticmethod
    def _years_from_duration(duration: str) -> int:
        if "-" not in duration:
            return 0
        try:
            start, end = duration.split("-")
            return int(end.strip()) - int(start.strip())
        except Exception:
            return 0

    def _experience_gap(self, profile: Dict[str, Any], job: Dict[str, Any]) -> tuple:
        required = 0
        for req in job.get("requirements", {}).get("mandatory", []):
            lower = req.lower()
            if "years" in lower:
                numbers = re.findall(r"\d+", lower)
                if numbers:
                    required = max(required, int(numbers[0]))
        total = sum(self._years_from_duration(e.get("duration", ""))
                    for e in profile.get("work_experience", []))
        return max(required - total, 0), required

    @staticmethod
    def _education_gap(profile: Dict[str, Any], job: Dict[str, Any]) -> str:
        edu = " ".join((e.get("degree", "") or "").lower() for e in profile.get("education", []))
        for max_level in ("master", "bachelor", "degree"):
            for req in job.get("requirements", {}).get("mandatory", []):
                if max_level in req.lower() and max_level not in edu:
                    return f"{max_level.title()} qualification not shown"
        return ""


def admin_role_targeted(jobs: List[Dict[str, Any]]) -> bool:
    return any(any(w in (j.get("title", "") or "").lower() for w in ADMIN_ROLE_WORDS) for j in jobs)


if __name__ == "__main__":
    import os
    import json
    engine = RecommendationEngine()
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "sample_cvs.json"), encoding="utf-8") as f:
        cvs = json.load(f)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "sample_jobs.json"), encoding="utf-8") as f:
        jobs = json.load(f)

    from profile_agent import ProfileAgent
    profile = ProfileAgent().extract_profile_main(cvs[0]["cv_text"])
    result = engine.assess(profile, jobs)
    print("Top jobs:", ", ".join(f"{j['title']} ({j['score']}%)" for j in result["top_jobs"]))
    print("\n--- PROFESSIONAL improvement areas ---")
    for item in result["professional"]:
        print(f"[{item['priority']}] {item['area']} -> {item['action']}  (for: {', '.join(item['source_jobs'])[:60]})")
    print("\n--- ADMIN / profile-setup areas ---")
    for item in result["admin"]:
        print(f"[{item['priority']}] {item['area']} -> {item['action']}")