"""
MATCHA - Candidate preference model and deterministic preference compatibility.

This module defines the structured "Career Goals & Job Preferences" that a
candidate provides explicitly during onboarding (NOT inferred from a CV and
NOT a personality assessment).

Ethical contract:
- Only explicit, job-relevant preferences are collected.
- Preference data is used ONLY to improve job recommendations.
- No personality traits, psychological suitability, "culture fit", loyalty,
  retention, motivation or mental state is ever computed or stored.
- Missing preference data never penalizes a candidate (neutral scoring).

The compatibility functions in this module are pure, deterministic logic.
They are unit-tested separately from the matching agent.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------- #
#  Controlled vocabularies (used by the onboarding wizard)
# ---------------------------------------------------------------------- #
EMPLOYMENT_LEVELS = ["Flexible", "20%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]

SALARY_CURRENCIES = ["CHF", "EUR", "USD"]
SALARY_PERIODS = ["yearly", "monthly"]

SWISS_LOCATIONS = [
    "Basel", "Zurich", "Bern", "Geneva", "Lausanne", "Lucerne",
    "St. Gallen", "Zug", "Winterthur", "Other"
]

COMMUTE_OPTIONS = ["No limit", "Up to 15 minutes", "Up to 30 minutes", "Up to 60 minutes",
                   "Up to 90 minutes", "Flexible"]
COMMUTE_MODES = ["Flexible", "Public transport", "Bicycle", "Walking", "Car", "Motor scooter"]

RELOCATION_OPTIONS = ["No", "Yes"]

REMOTE_PREFERENCES = [
    "No preference", "Fully remote", "Mostly remote", "Hybrid",
    "Mostly office", "Fully office"
]

CAREER_GOAL_OPTIONS = [
    "Career advancement",
    "Leadership",
    "Career change",
    "Return to work",
    "Re-entering after a career break",
    "Gain professional experience",
    "Develop new skills",
    "Specialize in an existing field",
    "Increase responsibility",
    "Improve work-life balance",
    "Find greater job stability",
    "Enter a new industry",
]

COMPANY_SIZE_OPTIONS = ["No preference", "Small company/start-up", "Medium-sized company", "Large organization"]
COMPANY_SIZE_KEYS = {"Small company/start-up": "startup",
                     "Medium-sized company": "medium",
                     "Large organization": "large",
                     "No preference": "no_preference"}

AVAILABILITY_OPTIONS = ["Immediately", "Within 1 month", "Within 3 months", "More than 3 months", "Specific date"]

# Work style items: (stored key, question label). 1-5 importance scale.
WORK_STYLE_ITEMS = [
    ("independent_work", "How important is independent work to you?"),
    ("teamwork", "How important is teamwork to you?"),
    ("predictable_structure", "How important is a predictable and structured working environment?"),
    ("flexible_hours", "How important is flexibility in working hours?"),
    ("learning_development", "How important are learning and professional development opportunities?"),
    ("autonomy", "How important is having autonomy in your work?"),
    ("international_environment", "How important is working in an international environment?"),
]

# Work values: (stored key, label). 1-5 importance. Used ONLY as an additional
# signal when the job contains a matching structured attribute.
WORK_VALUE_ITEMS = [
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

PREFERENCE_SCALE = (1, 5)


def default_preferences() -> Dict[str, Any]:
    """
    Neutral defaults. Every field is optional from the candidate's point of
    view; an absent value keeps the matching effect neutral instead of
    penalizing the candidate.
    """
    return {
        "preferred_employment_target": None,       # int 20..100 or None
        "preferred_employment_min": None,          # int 20..100 or None
        "preferred_employment_max": None,          # int 20..100 or None
        "employment_flexible": False,

        "salary_min": None,                        # annual figure in salary_currency
        "salary_preferred": None,
        "salary_currency": "CHF",
        "salary_period": "yearly",
        "salary_flexible": False,

        "preferred_locations": [],                 # list of city names
        "max_commute_minutes": None,               # int or None
        "commute_mode": "Flexible",
        "relocation_willing": False,

        "remote_preference": "No preference",
        "remote_importance": 3,

        "career_goals": [],                        # list from CAREER_GOAL_OPTIONS
        "career_goal_text": "",                    # optional free text (never ranked directly)

        "company_size_preference": "No preference",

        "preference_scores": {key: 3 for key, _ in WORK_STYLE_ITEMS},   # 1-5
        "work_values": {key: 3 for key, _ in WORK_VALUE_ITEMS},         # 1-5

        "preferred_working_languages": [],         # list e.g. ["German", "English"]
        "availability": None,
    }


# Keys that exist in the preference model. Anything else is refused, which
# prevents storing protected or personality-type characteristics.
ALLOWED_PREFERENCE_KEYS = set(default_preferences().keys())


def normalise_preferences(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate and normalise a raw preferences dict into the canonical model.
    Unknown keys are dropped (defence against personality/protected fields).
    """
    prefs = default_preferences()
    if not raw:
        return prefs

    for key in ALLOWED_PREFERENCE_KEYS:
        if key not in raw or raw[key] is None:
            continue
        value = raw[key]

        if key == "preferred_employment_target":
            prefs[key] = _to_pct(value)
        elif key in ("preferred_employment_min", "preferred_employment_max"):
            parsed = _to_pct(value)
            prefs[key] = parsed
        elif key in ("employment_flexible", "salary_flexible", "relocation_willing"):
            prefs[key] = bool(value)
        elif key in ("salary_min", "salary_preferred"):
            prefs[key] = int(value) if isinstance(value, (int, float)) else (int(value) if str(value).strip().isdigit() else None)
        elif key in ("salary_currency", "salary_period", "remote_preference",
                     "commute_mode", "availability", "company_size_preference"):
            prefs[key] = str(value) if str(value).strip() else prefs[key]
        elif key in ("preferred_locations", "career_goals", "preferred_working_languages"):
            if isinstance(value, list):
                prefs[key] = [str(v).strip() for v in value if str(v).strip()]
        elif key == "career_goal_text":
            prefs[key] = str(value).strip()
        elif key in ("preference_scores", "work_values"):
            clean = {}
            allowed_subkeys = dict(WORK_STYLE_ITEMS) if key == "preference_scores" else dict(WORK_VALUE_ITEMS)
            if isinstance(value, dict):
                for subkey, val in value.items():
                    if subkey in allowed_subkeys and isinstance(val, (int, float)):
                        clean[subkey] = int(max(1, min(5, val)))
            prefs[key] = clean or prefs[key]
        elif key == "max_commute_minutes":
            prefs[key] = int(value) if isinstance(value, (int, float)) and value > 0 else (int(value) if str(value).strip().isdigit() else None)
        elif key == "remote_importance":
            prefs[key] = int(max(1, min(5, value if isinstance(value, (int, float)) else 3)))

    # Keep employment bounds consistent (swap if reversed).
    lo, hi = prefs["preferred_employment_min"], prefs["preferred_employment_max"]
    if lo is not None and hi is not None and lo > hi:
        prefs["preferred_employment_min"], prefs["preferred_employment_max"] = hi, lo

    return prefs


def _to_pct(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if 20 <= int(value) <= 100 else None
    s = str(value).strip()
    if s.lower() in ("flexible", "none", ""):
        return None
    s = s.replace("%", "")
    return int(s) if s.isdigit() and 20 <= int(s) <= 100 else None


# ---------------------------------------------------------------------- #
#  Human-readable summary for the review step ("Review & Confirm")
# ---------------------------------------------------------------------- #
def preferences_summary(prefs: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return (label, human readable value) pairs used by the Review step."""
    p = normalise_preferences(prefs)
    lines: List[Tuple[str, str]] = []

    if p["employment_flexible"] or (p["preferred_employment_min"] is None and p["preferred_employment_max"] is None):
        work_level = "Flexible (open to any employment level)"
    else:
        target = f"{p['preferred_employment_target']}% preferred" if p["preferred_employment_target"] else "Flexible preferred"
        bounds = []
        if p["preferred_employment_min"]:
            bounds.append(f"{p['preferred_employment_min']}% minimum")
        if p["preferred_employment_max"]:
            bounds.append(f"{p['preferred_employment_max']}% maximum")
        work_level = f"{target}" + (f" ({', '.join(bounds)})" if bounds else "")
    lines.append(("Employment level", work_level))

    if p["salary_flexible"]:
        salary = "Flexible / open to discussion"
    else:
        parts = []
        if p["salary_min"]:
            parts.append(f"{p['salary_min']:,} minimum")
        if p["salary_preferred"]:
            parts.append(f"{p['salary_preferred']:,} preferred")
        salary = f"{p['salary_currency']} " + " | ".join(parts) if parts else "Not stated"
    line_salary = f"{salary} ({p['salary_period']})"
    lines.append(("Salary", line_salary))

    locations = ", ".join(p["preferred_locations"]) if p["preferred_locations"] else "No preference"
    commute = f"up to {p['max_commute_minutes']} minutes" if p["max_commute_minutes"] else "no limit"
    location = f"{locations}; commute {commute}; relocate: {'yes' if p['relocation_willing'] else 'no'}"
    lines.append(("Location & commute", location))

    remote = f"{p['remote_preference']} (importance {p['remote_importance']}/5)"
    lines.append(("Work arrangement", remote))

    goals = ", ".join(p["career_goals"]) if p["career_goals"] else "No specific goals"
    lines.append(("Career goals", goals))

    languages = ", ".join(p["preferred_working_languages"]) if p["preferred_working_languages"] else "No preference"
    lines.append(("Working languages", languages))

    availability = p["availability"] or "Not stated"
    lines.append(("Availability", availability))

    company = p["company_size_preference"] if p["company_size_preference"] != "No preference" else "No preference"
    lines.append(("Company size", company))

    important_values = [label for key, label in WORK_VALUE_ITEMS
                        if p.get("work_values", {}).get(key, 0) >= 4]
    lines.append(("Important work values", ", ".join(important_values) if important_values else "None stated"))

    return lines


# ---------------------------------------------------------------------- #
#  Deterministic compatibility helpers (pure logic, unit-tested)
# ---------------------------------------------------------------------- #
def employment_compatibility(target: Optional[int], pref_min: Optional[int], pref_max: Optional[int],
                             flexible: bool, job_min: Optional[int], job_max: Optional[int]) -> float:
    """
    Employment-percentage compatibility.

    - A flexible candidate effectively accepts a wide range.
    - A clear mismatch (further than 20 percentage points away) scores low,
      but nearby levels still receive partial compatibility.
    """
    if job_min is None and job_max is None:
        return 0.5  # job does not state a percentage -> neutral

    jmin = job_min if job_min is not None else 0
    jmax = job_max if job_max is not None else 100

    if flexible:
        cmin = pref_min if pref_min is not None else 1
        cmax = pref_max if pref_max is not None else 100
    elif pref_min is not None or pref_max is not None:
        cmin = pref_min if pref_min is not None else target if target else 1
        cmax = pref_max if pref_max is not None else target if target else 100
    elif target is not None:
        cmin = cmax = target
    else:
        return 0.5  # no employment preference stated -> neutral

    if cmin is None:
        cmin = 1
    if cmax is None:
        cmax = 100

    # Exact same fixed level.
    if jmin == jmax and cmin == cmax and cmin == jmin:
        return 1.0

    if cmin <= jmax and cmax >= jmin:
        return 1.0  # ranges overlap

    # Measure the gap between the two ranges.
    if cmin > jmax:
        gap = cmin - jmax
    else:
        gap = jmin - cmax

    if gap <= 20:
        return 0.6  # close -> partial
    if gap <= 40:
        return 0.4
    return 0.2  # clear mismatch


def salary_compatibility(salary_min: Optional[int], salary_preferred: Optional[int],
                         salary_flexible: bool, job_min: Optional[int], job_max: Optional[int]) -> float:
    """
    Salary compatibility. Never an automatic rejection: a mismatch lowers the
    recommendation score but never blocks the job, and "flexible" softens it.
    """
    if job_min is None and job_max is None:
        return 0.5  # unknown -> neutral

    floor = salary_min or salary_preferred
    if floor is None:
        return 0.5  # no expectation stated -> neutral, never penalized

    jmax = job_max if job_max is not None else job_min
    jmin = job_min if job_min is not None else job_max

    if floor <= jmax:
        if salary_preferred is not None and salary_preferred <= jmax:
            return 1.0  # preferred salary is achievable -> full compatibility
        if floor <= jmin:
            return 1.0  # job minimum already covers the candidate's floor
        return 0.8      # candidate's floor sits inside the job range

    # The job pays less than the candidate's minimum.
    if salary_flexible:
        return 0.6      # open to discussion -> partial compatibility
    excess = floor - jmax
    ratio = excess / jmax if jmax else 1.0
    if ratio <= 0.1:
        return 0.5      # close -> partial
    return 0.2          # clear salary mismatch


def location_compatibility(preferred_locations: List[str], job_location: str,
                           relocation_willing: bool) -> float:
    """City-level preference. No preference -> neutral (no penalty)."""
    if not preferred_locations:
        return 0.5
    jloc = (job_location or "").strip().lower()
    if not jloc:
        return 0.5
    for loc in preferred_locations:
        l = (loc or "").strip().lower()
        if l and (l in jloc or jloc in l):
            return 1.0
    if relocation_willing:
        return 0.5  # open to relocating -> partial credit
    return 0.2


def commute_compatibility(max_commute_minutes: Optional[int], job_commute_minutes: Optional[int],
                          remote_pct: Optional[int]) -> float:
    """Commute tolerance. High remote share lowers the impact of a long commute."""
    if job_commute_minutes is None:
        return 0.6  # unknown commute -> neutral-ish
    remote = remote_pct or 0
    if max_commute_minutes is None:
        return 0.8 if remote >= 60 else 0.6  # no stated limit -> lenient

    if job_commute_minutes <= max_commute_minutes:
        return 1.0

    if remote >= 60:
        return 0.7  # exceeds the limit but remote work makes the position accessible
    if job_commute_minutes <= max_commute_minutes * 1.5:
        return 0.7
    if job_commute_minutes <= max_commute_minutes * 2.0:
        return 0.4
    return 0.2


def remote_compatibility(remote_preference: str, remote_importance: Optional[int],
                         job_remote_pct: Optional[int]) -> float:
    """
    Remote-work preference vs. the position's remote share (0-100).
    Importance scales the impact of a mismatch.
    """
    if job_remote_pct is None:
        return 0.6
    pref = (remote_preference or "No preference").strip().lower()
    importance = remote_importance if remote_importance is not None else 3
    importance = int(max(1, min(5, importance)))

    if pref in ("", "no preference", "flexible"):
        return 0.8 if job_remote_pct >= 50 else 0.6

    targets = {
        "fully remote": (80, 100),
        "mostly remote": (60, 100),
        "hybrid": (30, 70),
        "mostly office": (0, 40),
        "fully office": (0, 10),
    }
    lo, hi = targets.get(pref, (0, 100))

    if lo <= job_remote_pct <= hi:
        return 1.0

    miss = min(abs(job_remote_pct - lo), abs(job_remote_pct - hi))
    if miss <= 20:
        base = 0.7
    else:
        base = 0.4
    if importance <= 2:
        base = min(base + 0.15, 1.0)
    elif importance >= 4:
        base = max(base - 0.2, 0.0)
    return base


def job_career_signals(job: Dict[str, Any]) -> Dict[str, bool]:
    """Detect structured job attributes that career goals / values can align to."""
    title = job.get("title", "") or ""
    description = job.get("description", "") or ""
    details = job.get("details", {}) or {}
    work_values = job.get("work_values") or {}
    text = f"{title} {description}".lower()

    def has(*words: str) -> bool:
        return any(w in text for w in words)

    signals = {
        "career_advancement": work_values.get("career_development", 0) >= 4 or has("career", "promotion", "growth", "advance"),
        "leadership": has("lead", "head of", "manage a team", "manage team", "senior"),
        "return_friendly": (has("return", "returning") and has("workforce", "career break", "re-enter", "re-enter"))
                        or bool(details.get("return_friendly")),
        "learning": work_values.get("learning", 0) >= 4 or has("training", "mentorship", "professional development", "learning"),
        "flexible_hours": work_values.get("work_life_balance", 0) >= 4 or has("flexible hours", "flexible working", "work-life balance", "part-time"),
        "jr_entry": has("junior", "entry-level", "entry level", "graduate", "assistant"),
        "stability": work_values.get("job_stability", 0) >= 4 or has("stable", "established", "long-standing", "bank", "large organization"),
        "specialization": work_values.get("career_development", 0) >= 4 or has("specializ", "expert", "expertise", "deep focus"),
        "international": work_values.get("international_environment", 0) >= 4 or has("international", "multiling", "global"),
        "innovation": work_values.get("innovation", 0) >= 4 or has("innovative", "cutting-edge", "startup"),
        "social_impact": work_values.get("social_impact", 0) >= 4 or has("impact", "society", "public", "health awareness"),
    }
    return signals


# Career goal -> (structured signal, alignment score when signal is present).
# Goals marked None are intentionally NEUTRAL: a different career path is
# never treated as a mismatch (career changes / re-entry are not penalized).
GOAL_SIGNALS = {
    "Career advancement": ("career_advancement", 1.0),
    "Leadership": ("leadership", 1.0),
    "Career change": None,
    "Return to work": ("return_friendly", 1.0),
    "Re-entering after a career break": ("return_friendly", 1.0),
    "Gain professional experience": ("jr_entry", 1.0),
    "Develop new skills": ("learning", 1.0),
    "Specialize in an existing field": ("specialization", 0.7),
    "Increase responsibility": ("career_advancement", 1.0),
    "Improve work-life balance": ("flexible_hours", 1.0),
    "Find greater job stability": ("stability", 1.0),
    "Enter a new industry": None,
}

MISSED_GOAL_SCORE = 0.35  # gentle downward nudge for a genuinely misaligned goal


def career_goal_compatibility(goals: List[str], job: Dict[str, Any],
                              work_values: Optional[Dict[str, int]] = None) -> float:
    """
    Career-goal alignment (weight bucket: 5%).

    - Goals that cannot be assessed against a job (career change, new industry)
      are neutral, never a penalty.
    - Work values only add a small bonus when the JOB contains a matching
      structured attribute and the candidate rated it >= 4/5.
    """
    if not goals:
        return 0.5  # no stated goals -> neutral

    signals = job_career_signals(job)
    aligned = []
    for goal in goals:
        entry = GOAL_SIGNALS.get(goal)
        if entry is None:
            aligned.append(0.5)  # neutral: career change is not penalized
        else:
            signal, direct_score = entry
            aligned.append(direct_score if signals.get(signal) else MISSED_GOAL_SCORE)

    base = sum(aligned) / len(aligned)

    bonus = 0.0
    for key, importance in (work_values or {}).items():
        if importance >= 4:
            job_level = (job.get("work_values") or {}).get(key)
            if job_level is not None:
                try:
                    if int(job_level) >= 4:
                        bonus += 0.05
                except (TypeError, ValueError):
                    pass
    return min(base + min(bonus, 0.2), 1.0)


def company_size_compatibility(preference: str, job_company_size: Optional[str]) -> Optional[float]:
    """
    Company-size preference -> None when it cannot be assessed (callers treat
    None as neutral / explanation only). Values: start/med/large.
    """
    key = COMPANY_SIZE_KEYS.get(preference)
    if not key or key == "no_preference":
        return None
    if not job_company_size:
        return None
    return 1.0 if key == job_company_size else 0.3