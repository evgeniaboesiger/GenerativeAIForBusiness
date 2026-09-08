"""
MATCHA - Matching-efficiency telemetry.

Records anonymized, aggregate metadata about each matching run so the team can
compare two setups:

    Version A:  matching from the CV / professional profile only
    Version B:  CV / professional profile + explicit candidate preferences

Metrics collected per run:
    jobs_reviewed            - how many positions the engine scanned
    matches_returned         - how many recommendations were produced
    relevant_recommendations - how many returned matches reached score >= 60
    first_relevant_rank      - position of the first relevant match (1-based)
    avg_match_score          - mean score of returned matches
    score_distribution       - buckets [<25, 25-50, 50-75, 75-100]
    time_to_identify_s       - wall-clock time for the run

IMPORTANT: no personal data is ever recorded. Only aggregate counters and
derived scores are logged. The results shown in the UI come only from this
file - nothing is fabricated.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
DEFAULT_PATH = os.environ.get("MATCHA_TELEMETRY_PATH",
                              os.path.join(DATA_DIR, "match_telemetry.jsonl"))

_RELEVANCE_THRESHOLD = 60.0


def set_log_path(path: str) -> None:
    """Override the telemetry log location (used by tests)."""
    global DEFAULT_PATH
    DEFAULT_PATH = path


def detect_version(profile: Dict[str, Any]) -> str:
    """
    Return "B" when the candidate has explicit structured preferences,
    otherwise "A" (CV / professional info only).
    """
    prefs = profile.get("preferences") or {}
    structured = ["preferred_employment_target", "salary_preferred",
                  "preferred_locations", "career_goals", "remote_preference"]
    for key in structured:
        value = prefs.get(key)
        if isinstance(value, list):
            if value:
                return "B"
        elif value:
            return "B"
    return "A"


def log_matching_run(version: str, jobs_reviewed: int, matches_returned: int,
                     scores: List[float], elapsed_s: float,
                     first_relevant_rank: Optional[int]) -> None:
    """Append one run record to the telemetry log."""
    scores = [float(s) for s in scores if s is not None]
    relevant = sum(1 for s in scores if s >= _RELEVANCE_THRESHOLD)
    buckets = {"<25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    for s in scores:
        if s < 25:
            buckets["<25"] += 1
        elif s < 50:
            buckets["25-50"] += 1
        elif s < 75:
            buckets["50-75"] += 1
        else:
            buckets["75-100"] += 1

    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": version,
        "jobs_reviewed": jobs_reviewed,
        "matches_returned": matches_returned,
        "relevant_recommendations": relevant,
        "first_relevant_rank": first_relevant_rank,
        "avg_match_score": round(sum(scores) / len(scores), 1) if scores else None,
        "score_distribution": buckets,
        "elapsed_s": round(elapsed_s, 3),
    }

    os.makedirs(os.path.dirname(DEFAULT_PATH), exist_ok=True)
    with open(DEFAULT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_all() -> List[Dict[str, Any]]:
    if not os.path.exists(DEFAULT_PATH):
        return []
    records = []
    try:
        with open(DEFAULT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []
    return records


def summary() -> Dict[str, Any]:
    """Aggregate per-version statistics from the telemetry log."""
    records = _read_all()
    result = {"total_runs": len(records), "versions": {}, "distribution": {}}

    for version in ("A", "B"):
        runs = [r for r in records if r.get("version") == version]
        if not runs:
            result["versions"][version] = None
            continue

        avg_score_values = [r["avg_match_score"] for r in runs if r.get("avg_match_score") is not None]
        agg = {
            "runs": len(runs),
            "total_relevant_recommendations": sum(r.get("relevant_recommendations", 0) for r in runs),
            "avg_jobs_reviewed": round(sum(r.get("jobs_reviewed", 0) for r in runs) / len(runs), 1),
            "avg_matches_returned": round(sum(r.get("matches_returned", 0) for r in runs) / len(runs), 1),
            "avg_match_score": round(sum(avg_score_values) / len(avg_score_values), 1) if avg_score_values else None,
            "avg_time_s": round(sum(r.get("elapsed_s", 0) for r in runs) / len(runs), 3) if runs else None,
            "first_relevant_ranks": [r.get("first_relevant_rank") for r in runs if r.get("first_relevant_rank") is not None],
        }
        if agg["first_relevant_ranks"]:
            agg["avg_first_relevant_rank"] = round(sum(agg["first_relevant_ranks"]) / len(agg["first_relevant_ranks"]), 2)
        result["versions"][version] = agg

        dist = {"<25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
        for r in runs:
            for bucket, count in (r.get("score_distribution") or {}).items():
                if bucket in dist:
                    dist[bucket] += count
        counted = sum(dist.values())
        result["distribution"][version] = (
            {k: (round(v / counted, 3) if counted else 0.0) for k, v in dist.items()}
        )

    return result


def reset_log() -> None:
    """Delete the telemetry log (used by tests)."""
    if os.path.exists(DEFAULT_PATH):
        os.remove(DEFAULT_PATH)


if __name__ == "__main__":
    # Quick self-test with disposable data.
    reset_log()
    log_matching_run("A", jobs_reviewed=8, matches_returned=5,
                     scores=[72, 55, 48, 40, 22], elapsed_s=0.2, first_relevant_rank=1)
    log_matching_run("B", jobs_reviewed=8, matches_returned=5,
                     scores=[88, 81, 66, 54, 41], elapsed_s=0.2, first_relevant_rank=1)
    print(json.dumps(summary(), indent=2))
    reset_log()
    print("TELEMETRY SELF-TEST PASSED")