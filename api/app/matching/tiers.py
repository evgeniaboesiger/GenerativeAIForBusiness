"""
Tiered preferences: Ideal / Acceptable / Deal-breaker.

Candidates can mark each practical preference dimension with three tiers:
- ideal:        the aspirational value / range; score full fit (100)
- acceptable:   workable range / values; score partial fit (70)
- deal_breaker: the outer boundary; if the job violates it, the job is NOT
                recommended regardless of how well it otherwise matches.

This implements the "Ideal / Acceptable / Deal-breaker" principle from the
matching research (see commit history) on top of the P1 hard-constraint layer.

All functions are pure and deterministic. Unknown / malformed tiers are
silently dropped so a dimension falls back to the scalar preferences.
"""

from typing import Any, Dict, List, Optional, Tuple

# Accepted preference dimensions that can carry tiers.
TIER_DIMENSIONS = ("employment_percentage", "salary", "commute", "remote", "weekend")

# Normalised remote-work levels used by the remote tier.
REMOTE_LEVELS = ("remote", "hybrid", "office")

# --------------------------------------------------------------------------- #
# Shared helpers (kept here so both the tier module and the engine can use them)
# --------------------------------------------------------------------------- #
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
        return 65
    return 120


def job_employment_range(job: Dict[str, Any]) -> Tuple[int, int]:
    """Resolve the job's employment percentage as a (min, max) range."""
    jmin = job.get("employment_percentage_min")
    jmax = job.get("employment_percentage_max")
    single = job.get("employment_percentage")
    if jmin is None:
        jmin = single if single is not None else 100
    if jmax is None:
        jmax = single if single is not None else 100
    return jmin, jmax


def job_has_weekend_work(job: Dict[str, Any]) -> bool:
    """Detect weekend / on-call requirements from the job description.

    Negation-aware: phrases like "no weekend work", "no on-call" or "rarely
    works weekends" do not count as weekend requirements. Detection is
    sentence-scoped so a negation applies only to its own sentence.
    """
    haystack = " ".join([
        str(job.get("description") or ""),
        str(job.get("requirements") or ""),
    ]).lower()
    positives = ["weekend", "saturday", "sunday", "24/7", "on-call", "shift work"]
    softeners = ["rare", "occasional", "seldom", "rarely", "sporad"]
    sentences = [s for s in haystack.replace(";", ".").replace("!", ".").split(".") if s.strip()]

    def _negated(sentence: str) -> bool:
        if any(w in sentence for w in ["no ", "without", "not ", "never "]):
            return True
        if any(w in sentence for w in softeners):
            return True
        return False

    for tag in positives:
        for sent in sentences:
            if tag in sent and not _negated(sent):
                return True
    return False


def job_remote_level(job: Dict[str, Any]) -> str:
    """Map a job's remote_percentage (0-100) to a normalised level."""
    pct = job.get("remote_percentage") or 0
    if pct >= 70:
        return "remote"
    if pct >= 30:
        return "hybrid"
    return "office"


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #
def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _range_pair(value: Any) -> Optional[Tuple[int, int]]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    lo, hi = _int(value[0]), _int(value[1])
    if lo is None or hi is None or lo > hi:
        return None
    return lo, hi


def _level_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    normalized = []
    for v in value:
        s = str(v).strip().lower()
        if s in ("remote", "mostly remote", "fully remote"):
            normalized.append("remote")
        elif s in ("hybrid",):
            normalized.append("hybrid")
        elif s in ("office", "fully office", "mostly office", "onsite", "on-site"):
            normalized.append("office")
    # de-dup
    return list(dict.fromkeys(normalized))


def normalize_preference_tiers(raw: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Validate and normalise a raw preference_tiers dict.

    Returns a dict with only the fully-specified dimensions present. A
    dimension that is missing or malformed is left out, so the engine falls
    back to the candidate's scalar preferences for it.
    """
    if not isinstance(raw, dict):
        return {}
    tiers: Dict[str, Dict[str, Any]] = {}

    emp = raw.get("employment_percentage")
    if isinstance(emp, dict):
        cleaned = {k: _range_pair(emp.get(k)) for k in ("ideal", "acceptable", "deal_breaker")}
        if all(isinstance(cleaned[k], tuple) for k in cleaned):
            bounds_ok = all(0 <= v <= 100 for k, pair in cleaned.items() for v in pair)
            if bounds_ok:
                tiers["employment_percentage"] = {k: list(v) for k, v in cleaned.items()}

    sal = raw.get("salary")
    if isinstance(sal, dict):
        cleaned = {k: _range_pair(sal.get(k)) for k in ("ideal", "acceptable", "deal_breaker")}
        if all(isinstance(cleaned[k], tuple) for k in cleaned):
            tiers["salary"] = {k: list(v) for k, v in cleaned.items()}

    cm = raw.get("commute")
    if isinstance(cm, dict):
        cleaned = {}
        for tier in ("ideal_max_minutes", "acceptable_max_minutes", "deal_breaker_max_minutes"):
            v = _int(cm.get(tier))
            if v is not None and 0 <= v <= 600:
                cleaned[tier] = v
        if len(cleaned) == 3:
            tiers["commute"] = cleaned

    rm = raw.get("remote")
    if isinstance(rm, dict):
        cleaned = {k: _level_list(rm.get(k)) for k in ("ideal", "acceptable", "deal_breaker")}
        if all(len(cleaned[k]) > 0 for k in cleaned):
            # deal_breaker must be disjoint from ideal/acceptable for sanity
            tiers["remote"] = cleaned

    wk = raw.get("weekend")
    if isinstance(wk, dict):
        ideal = bool(wk.get("ideal", False))
        acceptable = bool(wk.get("acceptable", False))
        deal_breaker = bool(wk.get("deal_breaker", True))
        tiers["weekend"] = {
            "ideal": ideal,
            "acceptable": acceptable,
            "deal_breaker": deal_breaker,
        }

    return tiers


def has_tiers(candidate: Dict[str, Any]) -> bool:
    return bool(candidate.get("preference_tiers"))


# --------------------------------------------------------------------------- #
# Per-dimension evaluation
# --------------------------------------------------------------------------- #
def evaluate_employment(tiers: Dict[str, Any], candidate: Dict[str, Any],
                        job: Dict[str, Any]) -> Tuple[bool, float, str]:
    tr = tiers["employment_percentage"]
    jmin, jmax = job_employment_range(job)
    if jmin >= tr["ideal"][0] and jmax <= tr["ideal"][1]:
        return True, 100.0, f"Workload {jmin}–{jmax}% matches your ideal range"
    if jmin >= tr["acceptable"][0] and jmax <= tr["acceptable"][1]:
        return True, 70.0, f"Workload {jmin}–{jmax}% is acceptable for you"
    if jmin >= tr["deal_breaker"][0] and jmax <= tr["deal_breaker"][1]:
        return True, 40.0, f"Workload {jmin}–{jmax}% is below preference but tolerable"
    return False, 0.0, f"Workload {jmin}–{jmax}% is a deal-breaker for you"


def evaluate_salary(tiers: Dict[str, Any], candidate: Dict[str, Any],
                    job: Dict[str, Any]) -> Tuple[bool, float, str]:
    jmin = job.get("salary_min")
    jmax = job.get("salary_max")
    if jmin is None or jmax is None:
        return True, 50.0, "No salary information to compare against"
    ideal = tiers["salary"]["ideal"]
    acceptable = tiers["salary"]["acceptable"]
    floor = tiers["salary"]["deal_breaker"][0]
    if jmin <= ideal[0] and jmax >= ideal[1]:
        return True, 100.0, f"Salary CHF {jmin:,}–{jmax:,} fully meets your ideal range"
    if jmax >= acceptable[0] and jmin <= acceptable[1]:
        return True, 70.0, f"Salary CHF {jmin:,}–{jmax:,} sits in your acceptable range"
    if jmax >= floor:
        return True, 40.0, f"Salary CHF {jmin:,}–{jmax:,} is below ideal but above your minimum"
    return False, 0.0, f"Salary tops out at CHF {jmax:,}, below your minimum (deal-breaker)"


def evaluate_commute(tiers: Dict[str, Any], candidate: Dict[str, Any],
                     job: Dict[str, Any]) -> Tuple[bool, float, str]:
    minutes = commute_minutes(candidate.get("location"), job.get("location"))
    ideal = tiers["commute"]["ideal_max_minutes"]
    acceptable = tiers["commute"]["acceptable_max_minutes"]
    limit = tiers["commute"]["deal_breaker_max_minutes"]
    if minutes <= ideal:
        return True, 100.0, f"{minutes} min commute is within your ideal ({ideal} min)"
    if minutes <= acceptable:
        return True, 70.0, f"{minutes} min commute is acceptable (up to {acceptable} min)"
    if minutes <= limit:
        return True, 40.0, f"{minutes} min commute is long but tolerable (up to {limit} min)"
    return False, 0.0, f"{minutes} min commute exceeds your limit ({limit} min) — deal-breaker"


def evaluate_remote(tiers: Dict[str, Any], candidate: Dict[str, Any],
                    job: Dict[str, Any]) -> Tuple[bool, float, str]:
    tr = tiers["remote"]
    level = job_remote_level(job)
    if level in tr["ideal"]:
        return True, 100.0, f"{level.title()} work matches your ideal setup"
    if level in tr["acceptable"]:
        return True, 70.0, f"{level.title()} work is acceptable for you"
    if level in tr["deal_breaker"]:
        return False, 0.0, f"{level.title()} work is a deal-breaker for you"
    return True, 40.0, f"{level.title()} work is a compromise for you"


def evaluate_weekend(tiers: Dict[str, Any], candidate: Dict[str, Any],
                     job: Dict[str, Any]) -> Tuple[bool, float, str]:
    tr = tiers["weekend"]
    weekend = job_has_weekend_work(job)
    if weekend and tr.get("deal_breaker"):
        return False, 0.0, "Weekend / on-call work is a deal-breaker for you"
    if weekend:
        return True, 60.0, "Role involves weekend work, which you rated as acceptable"
    return True, 100.0, "No weekend work scheduled"


_EVALUATORS = {
    "employment_percentage": evaluate_employment,
    "salary": evaluate_salary,
    "commute": evaluate_commute,
    "remote": evaluate_remote,
    "weekend": evaluate_weekend,
}


def evaluate_preference_tiers(candidate: Dict[str, Any],
                              job: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate all candidate preference tiers against a job.

    Returns a dict of per-dimension results plus aggregated outcomes:
        {
          "dimensions": {name: {"score": float, "deal_breaker": bool, "rationale": str}},
          "hard_constraints_met": bool,
          "hard_constraint_violations": [str],
          "score_overrides": {component_key: score},   # practical-fit override
        }
    If no tiers exist the result is empty / neutral so callers can fall back.
    """
    tiers = normalize_preference_tiers(candidate.get("preference_tiers"))
    dimensions: Dict[str, Any] = {}
    violations: List[str] = []
    overrides: Dict[str, float] = {}

    if "employment_percentage" in tiers:
        ok, score, why = evaluate_employment(tiers, candidate, job)
        dimensions["employment_percentage"] = {"score": score, "deal_breaker": not ok, "rationale": why}
        if not ok:
            violations.append(why)
        overrides["employment"] = score

    if "salary" in tiers:
        ok, score, why = evaluate_salary(tiers, candidate, job)
        dimensions["salary"] = {"score": score, "deal_breaker": not ok, "rationale": why}
        if not ok:
            violations.append(why)
        overrides["salary"] = score

    if "commute" in tiers:
        ok, score, why = evaluate_commute(tiers, candidate, job)
        dimensions["commute"] = {"score": score, "deal_breaker": not ok, "rationale": why}
        if not ok:
            violations.append(why)
        overrides["location"] = score

    if "remote" in tiers:
        ok, score, why = evaluate_remote(tiers, candidate, job)
        dimensions["remote"] = {"score": score, "deal_breaker": not ok, "rationale": why}
        if not ok:
            violations.append(why)
        overrides["remote"] = score

    if "weekend" in tiers:
        ok, score, why = evaluate_weekend(tiers, candidate, job)
        dimensions["weekend"] = {"score": score, "deal_breaker": not ok, "rationale": why}
        if not ok:
            violations.append(why)

    return {
        "dimensions": dimensions,
        "hard_constraints_met": len(violations) == 0,
        "hard_constraint_violations": violations,
        "score_overrides": overrides,
    }