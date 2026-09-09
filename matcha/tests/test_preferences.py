"""
MATCHA - Automated tests for structured career preferences & matching.

Covers: employment percentage, salary, remote, commute, location,
career goals, work values, working-language preference, flexible options,
missing preferences, preference changes, and ethical safeguards
(no personality traits, no protected characteristics, no career-break penalty).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

from preferences import ALLOWED_PREFERENCE_KEYS, career_goal_compatibility  # noqa: E402
from matching_agent import MatchingAgent  # noqa: E402
from telemetry import detect_version  # noqa: E402

import preferences as p

agent = MatchingAgent()


# ---------------------------------------------------------------------- #
#  Fixtures
# ---------------------------------------------------------------------- #
def make_job(**kw):
    job = {
        "id": "j1",
        "title": "Role",
        "company": "Company AG",
        "location": "Basel",
        "description": "A standard role.",
        "requirements": {"mandatory": [], "nice_to_have": []},
        "details": {"employment_type": "Full-time (100%)",
                    "salary_range": "CHF 100,000 - 120,000",
                    "remote_policy": "Hybrid",
                    "start_date": "Immediately"},
        "skills_required": ["Python"],
        "employment_pct_min": 100,
        "employment_pct_max": 100,
        "salary_min": 100000,
        "salary_max": 120000,
        "remote_pct": 40,
        "work_arrangement": "hybrid",
        "commute_minutes": 20,
        "working_languages": ["German"],
        "company_size": "medium",
        "work_values": {"learning": 3},
    }
    job.update(kw)
    return job


def make_profile(prefs=None, skills=("Python",), languages=("English", "Fluent"),
                 work_exp=None):
    profile = {
        "personal_info": {"name": "Ana", "location": "Basel"},
        "skills": list(skills),
        "work_experience": work_exp if work_exp is not None else [{"duration": "2018-2022"}],
        "education": [{"degree": "Bachelor of Science"}],
        "languages": [{"language": languages[0], "level": languages[1]}]
        if isinstance(languages, tuple) else languages,
        "preferences": prefs or {},
    }
    return profile


# ---------------------------------------------------------------------- #
#  1. Employment percentage compatibility
# ---------------------------------------------------------------------- #
def test_employment_exact_match():
    assert p.employment_compatibility(80, 60, 100, False, 80, 80) == 1.0


def test_employment_within_acceptable_range():
    # Accepts 60-100%, job is 100% -> compatible
    assert p.employment_compatibility(None, 60, 100, False, 100, 100) == 1.0


def test_employment_max_limit_mismatch_partial():
    # Accepts maximum 80%, job is 100% -> 20 point gap -> partial
    assert p.employment_compatibility(None, None, 80, False, 100, 100) == 0.6


def test_employment_mismatch_clear():
    assert p.employment_compatibility(None, None, 50, False, 100, 100) == 0.2


def test_employment_flexible_accepts_anything():
    # "Flexible" without bounds -> compatible with every level
    assert p.employment_compatibility(None, None, None, True, 100, 100) == 1.0
    assert p.employment_compatibility(None, None, None, True, 50, 60) == 1.0


def test_employment_missing_is_neutral():
    assert p.employment_compatibility(None, None, None, False, 100, 100) == 0.5


def test_employment_job_unknown_is_neutral():
    assert p.employment_compatibility(80, 60, 100, False, None, None) == 0.5


# ---------------------------------------------------------------------- #
#  2 + 9. Salary compatibility (incl. flexible salary)
# ---------------------------------------------------------------------- #
def test_salary_floor_within_job_range():
    # minimum 80k, job 85-100k -> compatible
    assert p.salary_compatibility(80000, 85000, False, 85000, 100000) == 1.0


def test_salary_mismatch_does_not_reject():
    # floor 100k, job 70-80k -> low score but never an automatic rejection
    assert p.salary_compatibility(100000, 100000, False, 70000, 80000) == 0.2


def test_salary_preferred_above_job_range():
    # candidate's floor sits just inside the job range; preferred salary is above
    assert p.salary_compatibility(90000, 130000, False, 85000, 100000) == 0.8


def test_salary_floor_below_job_min_is_full_match():
    assert p.salary_compatibility(75000, 130000, False, 85000, 100000) == 1.0


def test_salary_flexible_softens_mismatch():
    assert p.salary_compatibility(100000, 100000, True, 70000, 80000) == 0.6


def test_salary_missing_is_neutral():
    assert p.salary_compatibility(None, None, False, 85000, 100000) == 0.5


# ---------------------------------------------------------------------- #
#  3. Remote preference
# ---------------------------------------------------------------------- #
def test_remote_strong_match():
    assert p.remote_compatibility("Fully remote", 5, 100) == 1.0


def test_remote_requires_fully_remote_but_office():
    # fully remote required, job is fully office, importance high -> strong mismatch
    assert p.remote_compatibility("Fully remote", 5, 0) <= 0.4


def test_remote_importance_reduces_mismatch():
    # low importance -> softer mismatch
    assert p.remote_compatibility("Fully remote", 1, 0) > p.remote_compatibility("Fully remote", 5, 0)


def test_remote_hybrid_vs_full_remote_partial():
    assert p.remote_compatibility("Hybrid", 5, 100) < 1.0
    assert p.remote_compatibility("Hybrid", 5, 50) == 1.0


def test_remote_no_preference_neutral():
    assert p.remote_compatibility("No preference", 3, 0) == 0.6


# ---------------------------------------------------------------------- #
#  4. Commute
# ---------------------------------------------------------------------- #
def test_commute_within_limit():
    assert p.commute_compatibility(60, 30, 40) == 1.0


def test_commute_exceeds_limit_poor():
    assert p.commute_compatibility(30, 90, 0) == 0.2


def test_commute_exceeds_but_remote_makes_accessible():
    assert p.commute_compatibility(30, 90, 100) == 0.7


def test_commute_unknown_neutral():
    assert p.commute_compatibility(60, None, 0) == 0.6


# ---------------------------------------------------------------------- #
#  5. Location preference
# ---------------------------------------------------------------------- #
def test_location_match():
    assert p.location_compatibility(["Basel"], "Basel", False) == 1.0


def test_location_mismatch_with_relocation_partial():
    assert p.location_compatibility(["Basel"], "Bern", True) == 0.5


def test_location_mismatch_no_relocation_low():
    assert p.location_compatibility(["Basel"], "Bern", False) == 0.2


def test_location_no_preference_neutral():
    assert p.location_compatibility([], "Bern", False) == 0.5


# ---------------------------------------------------------------------- #
#  6. Career goal alignment
# ---------------------------------------------------------------------- #
def test_career_direct_alignment():
    job = make_job(description="An opportunity for career development and growth.",
                   work_values={"career_development": 4})
    assert career_goal_compatibility(["Career advancement"], job, {}) >= 0.9


def test_career_related_goal_partial():
    job = make_job(description="Standard role, no growth language.", work_values={})
    assert career_goal_compatibility(["Specialize in an existing field"], job, {}) < 0.7


def test_career_change_never_penalized():
    job = make_job(description="Anything.")
    assert career_goal_compatibility(["Career change"], job, {}) == 0.5
    assert career_goal_compatibility(["Enter a new industry"], job, {}) == 0.5


def test_career_break_not_penalized():
    job = make_job(description="Returning to the workforce is welcome here.",
                   details={"return_friendly": True})
    assert career_goal_compatibility(["Re-entering after a career break"], job, {}) >= 0.9
    assert career_goal_compatibility(["Return to work"], job, {}) >= 0.9


# ---------------------------------------------------------------------- #
#  7. Work-value alignment (only via structured job attributes)
# ---------------------------------------------------------------------- #
def test_work_value_bonus_when_job_has_structured_attribute():
    job_aligned = make_job(work_values={"learning": 5})
    job_without = make_job(work_values={})
    values = {"learning": 5}
    aligned = career_goal_compatibility(["Develop new skills"], job_aligned, values)
    no_attr = career_goal_compatibility(["Develop new skills"], job_without, values)
    assert aligned > no_attr
    # no structured job attribute -> no bonus invented
    assert career_goal_compatibility(["Career advancement"], make_job(work_values={}), values) <= no_attr


def test_work_life_balance_value():
    job = make_job(work_values={"work_life_balance": 5})
    assert career_goal_compatibility(["Improve work-life balance"], job, {"work_life_balance": 5}) >= 0.9


# ---------------------------------------------------------------------- #
#  8. Working language preference (separate from proficiency)
# ---------------------------------------------------------------------- #
def test_language_preference_explanation_match():
    chk = agent._explain_language_preference({"preferred_working_languages": ["German"]},
                                             make_job(working_languages=["German"]))
    assert any(c["status"] == "ok" for c in chk)


def test_language_preference_explanation_mismatch():
    chk = agent._explain_language_preference({"preferred_working_languages": ["French"]},
                                             make_job(working_languages=["German"]))
    assert any(c["status"] == "warn" for c in chk)


def test_language_proficiency_stays_factual():
    # Proficiency bucket is not affected by the language preference alone.
    profile = make_profile()
    job = make_job(requirements={"mandatory": ["German fluent"], "nice_to_have": []})
    profile_wo = make_profile()
    prof = agent._score_languages(profile_wo, job)
    assert prof < 0.5  # candidate has no German -> low proficiency score (factual)


# ---------------------------------------------------------------------- #
#  12. Company size preference (explanation-only when unstructured)
# ---------------------------------------------------------------------- #
def test_company_size_compatibility():
    assert p.company_size_compatibility("Large organization", "large") == 1.0
    assert p.company_size_compatibility("Large organization", "startup") == 0.3
    assert p.company_size_compatibility("No preference", "large") is None


# ---------------------------------------------------------------------- #
#  11. Missing preference data does not unfairly penalize
# ---------------------------------------------------------------------- #
def test_missing_preferences_neutral_in_engine():
    profile = make_profile(prefs={})
    job = make_job()
    score, breakdown, checks = agent._calculate_score(profile, job)
    # Preference buckets stay neutral (no penalty) when nothing is stated.
    assert breakdown["employment_preference"] == 0.5
    assert breakdown["salary"] == 0.5
    assert breakdown["career_goals"] == 0.5
    assert 0.45 <= breakdown["location_remote"] <= 0.60  # mildly lenient, never penalizing


def test_missing_preferences_never_zero():
    profile = make_profile(prefs=None)
    job = make_job()
    score, breakdown, _ = agent._calculate_score(profile, job)
    assert all(v >= 0.4 for v in breakdown.values())


# ---------------------------------------------------------------------- #
#  12+13. Preference changes affect recommendations
# ---------------------------------------------------------------------- #
def test_changing_preferences_changes_recommendations():
    base = dict(
        title="Developer", company="Co", skills_required=["Python"],
        requirements={"mandatory": [], "nice_to_have": []},
        details={"employment_type": "Full-time (100%)", "salary_range": "CHF 100k - 120k",
                 "remote_policy": "Hybrid", "start_date": "Now"},
    )
    job_basel = make_job(**base, id="b", location="Basel", commute_minutes=15)
    job_zurich = make_job(**base, id="z", location="Zurich", commute_minutes=30)

    profile = make_profile()
    prefs_basel = {
        "preferred_locations": ["Basel"], "employment_flexible": True,
        "salary_flexible": True, "remote_preference": "No preference",
    }
    prefs_zurich = {
        "preferred_locations": ["Zurich"], "employment_flexible": True,
        "salary_flexible": True, "remote_preference": "No preference",
    }
    m1 = agent.find_matches(make_profile(prefs=prefs_basel), [job_basel, job_zurich],
                            top_n=2, use_ai=False)
    m2 = agent.find_matches(make_profile(prefs=prefs_zurich), [job_basel, job_zurich],
                            top_n=2, use_ai=False)
    assert m1[0]["job_id"] == "b"
    assert m2[0]["job_id"] == "z"
    assert m1[0]["job_id"] != m2[0]["job_id"]


def test_pref_change_updates_check_text():
    profile = make_profile(prefs={"preferred_locations": ["Basel"]})
    job = make_job(location="Bern")
    _, _, checks = agent._calculate_score(profile, job)
    assert any(c["status"] == "warn" for c in checks)


# ---------------------------------------------------------------------- #
#  16. Ethical safeguards
# ---------------------------------------------------------------------- #
FORBIDDEN_TERMS = [
    "personality", "culture fit", "culture-fit", "loyalty", "retention",
    "emotional stability", "psychological", "mental state", "motivation",
]


def test_no_personality_or_protected_fields_in_model():
    for key in ALLOWED_PREFERENCE_KEYS:
        tokens = key.lower().replace("-", "_").split("_")
        for term in FORBIDDEN_TERMS + ["gender", "age", "ethnic", "religion", "health"]:
            assert term not in tokens, f"Forbidden field name {term!r} found in preference model: {key}"


def test_normalise_refuses_unknown_fields():
    clean = p.normalise_preferences({"gender": "female", "age": 34,
                                     "personality_type": "E",
                                     "work_values": {"teamwork": 5}})
    assert "gender" not in clean
    assert "age" not in clean
    assert "personality_type" not in clean
    assert clean["work_values"]["teamwork"] == 5  # known nested field still accepted


def test_no_personality_language_in_matches():
    profile = make_profile(prefs={
        "preferred_locations": ["Basel"], "career_goals": ["Career advancement"],
        "salary_flexible": True, "employment_flexible": True,
    })
    job = make_job()
    _, _, checks = agent._calculate_score(profile, job)
    text = " ".join(c["text"] for c in checks).lower()
    for term in FORBIDDEN_TERMS:
        assert term not in text, f"Forbidden term {term!r} found in preference explanation"


def test_missing_preferences_checks_are_low_signal():
    # Without preferences the checks list should not contain hard mismatches.
    profile = make_profile(prefs={})
    job = make_job()
    _, _, checks = agent._calculate_score(profile, job)
    assert not any(c["status"] == "warn" for c in checks)


def test_career_break_in_engine_not_penalized():
    # A candidate with a gap (no recent work entries) is not scored at zero.
    profile = make_profile(work_exp=[])
    job = make_job()
    score, breakdown, _ = agent._calculate_score(profile, job)
    assert breakdown["experience"] >= 0.2


def test_explanation_uses_genuine_checks():
    profile = make_profile(prefs={"preferred_locations": ["Basel"],
                                  "preferred_employment_min": 80, "salary_min": 100000})
    job = make_job(location="Basel")
    matches = agent.find_matches(profile, [job], top_n=1, use_ai=False)
    assert matches[0]["explanation"].startswith("Why this job matches your preferences:")
    assert "delay" not in matches[0]["explanation"]  # no invented content marker


# ---------------------------------------------------------------------- #
#  Telemetry A/B version detection
# ---------------------------------------------------------------------- #
def test_telemetry_detect_version():
    assert detect_version(make_profile()) == "A"
    assert detect_version(make_profile(prefs={"preferred_locations": ["Basel"]})) == "B"
    assert detect_version(make_profile(prefs={"salary_preferred": 90000})) == "B"


def test_telemetry_round_trip(tmp_path):
    import telemetry
    path = os.path.join(str(tmp_path), "telem.jsonl")
    telemetry.set_log_path(path)
    telemetry.reset_log()
    telemetry.log_matching_run("A", jobs_reviewed=8, matches_returned=5,
                               scores=[72, 55, 48, 40, 22], elapsed_s=0.2,
                               first_relevant_rank=1)
    telemetry.log_matching_run("B", jobs_reviewed=8, matches_returned=5,
                               scores=[88, 81, 66, 54, 41], elapsed_s=0.2,
                               first_relevant_rank=1)
    stats = telemetry.summary()
    assert stats["total_runs"] == 2
    assert stats["versions"]["A"]["runs"] == 1
    assert stats["versions"]["B"]["total_relevant_recommendations"] == 3
    assert stats["versions"]["A"]["avg_match_score"] < stats["versions"]["B"]["avg_match_score"]
    telemetry.reset_log()


def test_preferences_summary_render():
    summary = p.preferences_summary({
        "preferred_employment_target": 80, "preferred_employment_min": 60,
        "salary_preferred": 85000, "salary_min": 75000,
        "remote_preference": "Hybrid", "remote_importance": 4,
        "preferred_locations": ["Basel"], "max_commute_minutes": 60,
        "career_goals": ["Career advancement", "Specialize in an existing field"],
        "availability": "Within 1 month",
    })
    text = " ".join(f"{label}: {value}" for label, value in summary)
    assert "80% preferred" in text


# ---------------------------------------------------------------------- #
#  Tiered preferences (Ideal / Acceptable / Deal-breaker)
# ---------------------------------------------------------------------- #
VALID_TIERS = {
    "employment_percentage": {"ideal": [80, 100], "acceptable": [60, 100], "deal_breaker": [50, 100]},
    "salary": {"ideal": [90000, 120000], "acceptable": [80000, 130000], "deal_breaker": [70000, 150000]},
    "commute": {"ideal_max_minutes": 30, "acceptable_max_minutes": 45, "deal_breaker_max_minutes": 60},
    "remote": {"ideal": ["remote"], "acceptable": ["remote", "hybrid"], "deal_breaker": ["office"]},
    "weekend": {"ideal": True, "acceptable": False, "deal_breaker": True},
}


def test_tiers_are_whitelisted_and_default_none():
    assert "preference_tiers" in p.ALLOWED_PREFERENCE_KEYS
    assert p.default_preferences()["preference_tiers"] is None


def test_normalise_preferences_keeps_valid_tiers():
    prefs = p.normalise_preferences({"preference_tiers": VALID_TIERS})
    tiers = prefs["preference_tiers"]
    assert tiers["employment_percentage"]["ideal"] == [80, 100]
    assert tiers["salary"]["deal_breaker"][0] == 70000
    assert tiers["commute"]["ideal_max_minutes"] == 30
    assert tiers["remote"]["ideal"] == ["remote"]
    assert tiers["weekend"]["deal_breaker"] is True


def test_normalise_tiers_is_idempotent():
    once = p.normalise_preferences({"preference_tiers": VALID_TIERS})
    twice = p.normalise_preferences({"preference_tiers": once["preference_tiers"]})
    assert once == twice


def test_normalise_tiers_drops_malformed_dimensions():
    raw = {
        "employment_percentage": {"ideal": [100, 50], "acceptable": [60, 100], "deal_breaker": [50, 100]},
        "salary": {"ideal": [90000, 120000], "acceptable": [90000, 80000], "deal_breaker": [70000, 150000]},
        "commute": {"ideal_max_minutes": 30, "acceptable_max_minutes": 45},
        "remote": {"ideal": ["remote"], "acceptable": [], "deal_breaker": ["office"]},
        "weekend": {"ideal": True, "acceptable": False, "deal_breaker": True},
    }
    tiers = p.normalise_preferences({"preference_tiers": raw})["preference_tiers"]
    assert tiers is not None
    # reversed / incomplete ranges and empty levels are dropped entirely
    assert "employment_percentage" not in tiers
    assert "salary" not in tiers
    assert "commute" not in tiers
    assert "remote" not in tiers
    # the fully-specified weekend dimension survives
    assert tiers["weekend"]["deal_breaker"] is True


def test_empty_tiers_normalises_to_none():
    assert p.normalise_preferences({"preference_tiers": None})["preference_tiers"] is None
    assert p.normalise_preferences({"preference_tiers": {"remote": {"ideal": []}}})["preference_tiers"] is None


def test_tiers_appear_in_summary():
    summary = p.preferences_summary({"preference_tiers": VALID_TIERS})
    text = " ".join(f"{label}: {value}" for label, value in summary)
    assert "Deal-breakers" in text
    assert "100–120" in text or "120" in text
    assert "weekend" in text.lower()
    assert "CHF" in text


# ---------------------------------------------------------------------- #
#  Tiered deal-breakers are HARD CONSTRAINTS in the matching engine
# ---------------------------------------------------------------------- #
def _profile_with_tiers(tiers):
    prefs = {"preference_tiers": p.normalise_preference_tiers(tiers)}
    return make_profile(prefs=prefs)


def test_employment_deal_breaker_rejects_job_and_lists_reason():
    profile = _profile_with_tiers({
        "employment_percentage": {"ideal": [80, 100], "acceptable": [60, 100], "deal_breaker": [100, 100]},
    })
    job60 = make_job(employment_pct_min=60, employment_pct_max=60)
    job100 = make_job(employment_pct_min=100, employment_pct_max=100)
    assert p.tier_violation_reasons(profile["preferences"], job60)
    assert not p.tier_violation_reasons(profile["preferences"], job100)

    match = agent.find_matches(profile, [job60], use_ai=False)[0]
    assert match["mandatory_met"] is False
    assert any("Deal-breaker" in c["text"] for c in match["preference_checks"])

    match = agent.find_matches(profile, [job100], use_ai=False)[0]
    assert match["mandatory_met"] is True


def test_salary_deal_breaker_floor_rejects_job():
    profile = _profile_with_tiers({
        "salary": {"ideal": [120000, 180000], "acceptable": [100000, 200000], "deal_breaker": [100000, 250000]},
    })
    low = make_job(salary_min=55000, salary_max=65000)
    ok = make_job(salary_min=100000, salary_max=120000)
    assert p.tier_violation_reasons(profile["preferences"], low)
    assert not p.tier_violation_reasons(profile["preferences"], ok)
    assert agent.find_matches(profile, [low], use_ai=False)[0]["mandatory_met"] is False
    assert agent.find_matches(profile, [ok], use_ai=False)[0]["mandatory_met"] is True


def test_salary_deal_breaker_ceiling_rejects_overpaying_job():
    profile = _profile_with_tiers({
        "salary": {"ideal": [90000, 110000], "acceptable": [85000, 120000], "deal_breaker": [80000, 130000]},
    })
    over = make_job(salary_min=150000, salary_max=170000)
    assert p.tier_violation_reasons(profile["preferences"], over)
    assert agent.find_matches(profile, [over], use_ai=False)[0]["mandatory_met"] is False


def test_commute_deal_breaker_rejects_long_commute():
    profile = _profile_with_tiers({
        "commute": {"ideal_max_minutes": 20, "acceptable_max_minutes": 30, "deal_breaker_max_minutes": 45},
    })
    long = make_job(commute_minutes=90)
    short = make_job(commute_minutes=25)
    assert p.tier_violation_reasons(profile["preferences"], long)
    assert not p.tier_violation_reasons(profile["preferences"], short)
    assert agent.find_matches(profile, [long], use_ai=False)[0]["mandatory_met"] is False
    assert agent.find_matches(profile, [short], use_ai=False)[0]["mandatory_met"] is True


def test_remote_deal_breaker_filters_office_jobs_only():
    profile = _profile_with_tiers({
        "remote": {"ideal": ["remote"], "acceptable": ["remote", "hybrid"], "deal_breaker": ["office"]},
    })
    office_job = make_job(work_arrangement="office")
    hybrid_job = make_job(work_arrangement="hybrid")
    assert p.tier_violation_reasons(profile["preferences"], office_job)
    assert not p.tier_violation_reasons(profile["preferences"], hybrid_job)
    assert agent.find_matches(profile, [office_job], use_ai=False)[0]["mandatory_met"] is False
    assert agent.find_matches(profile, [hybrid_job], use_ai=False)[0]["mandatory_met"] is True


def test_weekend_deal_breaker_is_negation_aware():
    profile = _profile_with_tiers({
        "weekend": {"ideal": False, "acceptable": True, "deal_breaker": True},
    })
    weekend_job = make_job(description="You will cover a weekend on-call rotation once a month.")
    no_weekend_job = make_job(description="No weekend work: you are off on Saturdays and Sundays.")
    assert p.tier_violation_reasons(profile["preferences"], weekend_job)
    assert not p.tier_violation_reasons(profile["preferences"], no_weekend_job)
    assert agent.find_matches(profile, [weekend_job], use_ai=False)[0]["mandatory_met"] is False
    assert agent.find_matches(profile, [no_weekend_job], use_ai=False)[0]["mandatory_met"] is True


def test_no_tiers_never_changes_recommendations():
    profile = make_profile(prefs={"career_goals": ["Career advancement"]})
    job = make_job(employment_pct_min=60, employment_pct_max=60)
    assert not p.tier_violation_reasons(profile["preferences"], job)
    assert agent.find_matches(profile, [job], use_ai=False)[0]["mandatory_met"] is True


def test_missing_job_info_never_counts_as_violation():
    profile = _profile_with_tiers({
        "employment_percentage": {"ideal": [80, 100], "acceptable": [60, 100], "deal_breaker": [100, 100]},
    })
    sparse = make_job(employment_pct_min=None, employment_pct_max=None,
                      salary_min=None, salary_max=None, commute_minutes=None, work_arrangement="")
    assert not p.tier_violation_reasons(profile["preferences"], sparse)


# ---------------------------------------------------------------------- #
#  AI explanations really use the LLM when Ollama is available
#  (regression: requests was used without being imported, so the AI path
#   always fell back to the fast deterministic explanation)
# ---------------------------------------------------------------------- #
def test_ai_explanation_uses_ollama_when_available(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "AI explanation generated by the model"}

    class FakeRequests:
        def __init__(self):
            self.called = False

        def post(self, *args, **kwargs):
            self.called = True
            return FakeResponse()

    fake = FakeRequests()
    monkeypatch.setattr("matching_agent.requests", fake)

    profile = make_profile(prefs=None)
    job = make_job()
    explanation = agent._generate_ai_explanation(profile, job, score=0.85, pref_checks=[])
    assert fake.called, "requests.post should be reached when Ollama is available"
    assert "AI explanation generated" in explanation