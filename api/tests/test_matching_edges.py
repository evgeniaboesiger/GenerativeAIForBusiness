"""Edge-path coverage for the matching engine + tiers module.

Complements test_matching.py: focuses on the branch lines that the existing
suite does not reach (partial language fit, remote-preference branches,
employment partial overlap, availability/career-goal paths, preference-tier
deal-breakers across each dimension, category bands, etc.). All pure.
"""
from app.matching.engine import (
    compute_availability_score,
    compute_career_goal_score,
    compute_education_score,
    compute_employment_score,
    compute_language_score,
    compute_location_score,
    compute_remote_score,
    compute_values_score,
    compute_personality_score,
    score_candidate_job,
)
from app.matching.tiers import (
    _int,
    _range_pair,
    _level_list,
    commute_minutes,
    evaluate_commute,
    evaluate_employment,
    evaluate_preference_tiers,
    evaluate_remote,
    evaluate_salary,
    evaluate_weekend,
    normalize_preference_tiers,
)


def _cand(**kw):
    d = {"skills": [], "education": [], "languages": [], "location": "Zurich",
         "salary_expectation_min": 80000, "salary_expectation_max": 100000}
    d.update(kw)
    return d


def _job(**kw):
    d = {"required_skills": [], "preferred_skills": [], "language_requirements": [],
         "location": "Zurich", "salary_min": 80000, "salary_max": 100000}
    d.update(kw)
    return d


# --- compute_* unit gaps -------------------------------------------------- #

def test_education_score_full_when_degree_or_field_matches():
    cand = _cand(education=[{"degree": "Bachelor", "field": "Economics"}])
    assert compute_education_score(cand, _job(education_requirements="economics")) == 100.0
    assert compute_education_score(cand, _job(education_requirements="Bachelor")) == 100.0
    assert compute_education_score(cand, _job(education_requirements="Nonexistent")) == 50.0


def test_language_partial_fit_when_below_required():
    cand = _cand(languages=[{"language": "German", "level": "A2"}])
    job = _job(language_requirements=[{"language": "German", "level": "B2", "mandatory": False}])
    score, missing = compute_language_score(cand, job)
    assert missing == []
    assert 30 < score < 40  # 25/75 -> 33.33


def test_location_score_gives_100_for_remote_conscious_prefs():
    # hybrid/remote preference + job offers >=50% remote -> full location score
    assert compute_location_score(
        _cand(remote_preference="hybrid"), _job(remote_percentage=50)
    ) == 100.0
    assert compute_location_score(
        _cand(remote_preference="remote"), _job(remote_percentage=70)
    ) == 100.0
    # office preference is not boosted by remote work alone
    assert compute_location_score(
        _cand(remote_preference="office", location="Winterthur"), _job(remote_percentage=70)
    ) == 70.0


def test_employment_partial_overlap_and_no_overlap():
    # partial overlap -> proportional score (60-70 vs 50-100 = 10/50 => 70)
    assert compute_employment_score(
        _cand(employment_percentage_min=60, employment_percentage_max=70),
        _job(employment_percentage_min=50, employment_percentage_max=100),
    ) == 70.0
    # no overlap -> 20.0
    assert compute_employment_score(
        _cand(employment_percentage_min=50, employment_percentage_max=60),
        _job(employment_percentage_min=90, employment_percentage_max=100),
    ) == 20.0


def test_remote_score_branches():
    assert compute_remote_score(_cand(remote_preference="remote"), _job(remote_percentage=80)) == 100.0
    assert compute_remote_score(_cand(remote_preference="remote"), _job(remote_percentage=40)) == 70.0
    assert compute_remote_score(_cand(remote_preference="remote"), _job(remote_percentage=0)) == 30.0
    assert compute_remote_score(_cand(remote_preference="hybrid"), _job(remote_percentage=50)) == 100.0
    assert compute_remote_score(_cand(remote_preference="hybrid"), _job(remote_percentage=5)) == 70.0
    assert compute_remote_score(_cand(remote_preference="hybrid"), _job(remote_percentage=0)) == 40.0
    assert compute_remote_score(_cand(remote_preference="office"), _job(remote_percentage=50)) == 50.0
    assert compute_remote_score(_cand(remote_preference="office"), _job(remote_percentage=0)) == 100.0


def test_availability_score_paths():
    cand = _cand(availability="2026-06-01")
    assert compute_availability_score(cand, _job(start_date="2026-03-01")) == 70.0
    assert compute_availability_score(cand, _job(start_date="immediately")) == 100.0
    assert compute_availability_score(cand, _job(start_date=None)) == 100.0
    assert compute_availability_score(_cand(), _job()) == 100.0


def test_career_goal_transferable_via_department():
    cand = _cand(career_goal="Finance Analyst roles")
    # department inside the goal -> transferable 70
    assert compute_career_goal_score(cand, _job(title="Engineer", department="Finance")) == 70.0
    # job title appears verbatim inside the candidate's career goal
    assert compute_career_goal_score(cand, _job(title="Analyst", department="X")) == 100.0
    assert compute_career_goal_score(_cand(), _job(title="Gardener")) == 40.0
    # desired_roles match
    assert compute_career_goal_score(
        _cand(desired_roles=["Analyst"]), _job(title="Analyst II")
    ) == 100.0


def test_values_score_weight_cutoff():
    values = [f"v{i}" for i in range(8)]
    cand = _cand(values=values)
    job = _job(company_values=values)
    score, matched = compute_values_score(cand, job)
    # positive weights: 1.0, 0.85, ..., 0.1 (7) then weight drops to <= 0 on the 8th
    assert len(matched) == 7
    assert score == 100.0


def test_personality_score_neutral_when_no_dimensions():
    job = _job(personality_preferences={"mind": {"pole": "right", "importance": 1.0}})
    assert compute_personality_score(_cand(), job) == (100.0, [])


def test_personality_score_pole_none_and_zero_importance():
    cand = _cand(personality={"dimensions": {"mind": {"score": 10, "pole": "left"}}})
    assert compute_personality_score(
        cand, _job(personality_preferences={"mind": {"pole": None, "importance": 1.0}})
    ) == (100.0, ["mind"])
    assert compute_personality_score(
        cand, _job(personality_preferences={"mind": {"pole": "right", "importance": 0.0}})
    ) == (100.0, [])


# --- tiers unit gaps ------------------------------------------------------ #

def test_commute_minutes_unknown_locations():
    assert commute_minutes("Mars", "Zurich") == 120
    assert commute_minutes("", "") == 120
    assert commute_minutes("Zurich", "Zurich") == 20
    assert commute_minutes("Winterthur", "Zurich") == 35


def test_tier_int_and_range_helpers():
    assert _int("abc") is None
    assert _int("12") == 12
    assert _range_pair("nope") is None
    assert _range_pair([1, 2, 3]) is None
    assert _range_pair([90, 80]) is None  # lo > hi
    assert _range_pair([80, 90]) == (80, 90)


def test_level_list_and_normalize_empty():
    assert _level_list("remote") == []
    assert _level_list(["Onsite", "ONSITE"]) == ["office"]
    assert _level_list(["remote", "REMOTE", "hybrid"]) == ["remote", "hybrid"]
    assert normalize_preference_tiers(None) == {}
    assert normalize_preference_tiers("junk") == {}


def test_evaluate_employment_all_branches():
    tiers = {"employment_percentage": {
        "ideal": [80, 100], "acceptable": [70, 100], "deal_breaker": [50, 100]}}
    cand = _cand()
    assert evaluate_employment(tiers, cand, _job()) == (True, 100.0, "No workload information to compare against")
    assert evaluate_employment(tiers, cand, _job(employment_percentage=85))[0:2] == (True, 100.0)
    assert evaluate_employment(tiers, cand, _job(employment_percentage=75))[0:2] == (True, 70.0)
    assert evaluate_employment(tiers, cand, _job(employment_percentage=60))[0:2] == (True, 40.0)
    assert evaluate_employment(tiers, cand, _job(employment_percentage=30))[0:2] == (False, 0.0)


def test_evaluate_salary_no_data():
    tiers = {"salary": {"ideal": [90000, 120000], "acceptable": [80000, 130000], "deal_breaker": [75000, 150000]}}
    job = _job()
    job.pop("salary_min")
    job.pop("salary_max")
    assert evaluate_salary(tiers, _cand(), job)[0:2] == (True, 50.0)
    # sits in the deal_breaker floor band -> tolerable 40
    assert evaluate_salary(tiers, _cand(), _job(salary_min=76000, salary_max=78000))[0:2] == (True, 40.0)
    # fully in the ideal range -> 100
    assert evaluate_salary(tiers, _cand(), _job(salary_min=88000, salary_max=125000))[0:2] == (True, 100.0)
    # acceptable band -> 70
    assert evaluate_salary(tiers, _cand(), _job(salary_min=80000, salary_max=85000))[0:2] == (True, 70.0)
    # below floor -> deal-breaker
    assert evaluate_salary(tiers, _cand(), _job(salary_min=60000, salary_max=65000))[0] is False


def test_evaluate_commute_all_branches():
    tiers = {"commute": {"ideal_max_minutes": 30, "acceptable_max_minutes": 40, "deal_breaker_max_minutes": 70}}
    cand = _cand(location="Zurich")
    assert evaluate_commute(tiers, cand, _job(location="Zurich"))[0:2] == (True, 100.0)  # 20 min
    c2 = _cand(location="Winterthur")  # 35 min from Zurich
    assert evaluate_commute(tiers, c2, _job(location="Zurich"))[0:2] == (True, 70.0)
    c3 = _cand(location="Basel")  # 65 min from Zurich
    assert evaluate_commute(tiers, c3, _job(location="Zurich"))[0:2] == (True, 40.0)
    c4 = _cand(location="Locarno")  # not in any cluster -> 120 min from Zurich
    assert evaluate_commute(tiers, c4, _job(location="Zurich"))[0:2] == (False, 0.0)
    # fully remote commute waived
    assert evaluate_commute(tiers, c4, _job(location="Zurich", remote_percentage=100))[0:2] == (True, 100.0)


def test_evaluate_remote_compromise_branch():
    tiers = {"remote": {"ideal": ["remote"], "acceptable": ["hybrid"], "deal_breaker": ["office"]}}
    # office job with a remote-tiers candidate -> deal-breaker
    assert evaluate_remote(tiers, _cand(), _job(remote_percentage=0))[0:2] == (False, 0.0)
    # hybrid levels fall outside ideal but inside acceptable
    assert evaluate_remote(tiers, _cand(), _job(remote_percentage=40))[0:2] == (True, 70.0)
    # a level in none of the lists -> compromise 40
    tiers2 = {"remote": {"ideal": ["remote"], "acceptable": ["office"], "deal_breaker": []}}
    assert evaluate_remote(tiers2, _cand(), _job(remote_percentage=40))[0:2] == (True, 40.0)


def test_evaluate_weekend_acceptable_branch():
    tiers = {"weekend": {"ideal": False, "acceptable": True, "deal_breaker": True}}
    job = _job(description="Weekend on-call cover is required.")
    assert evaluate_weekend(tiers, _cand(), job)[0:2] == (False, 0.0)
    tiers_no_deal = {"weekend": {"ideal": False, "acceptable": True, "deal_breaker": False}}
    assert evaluate_weekend(tiers_no_deal, _cand(), job)[0:2] == (True, 60.0)


def test_evaluate_preference_tiers_persists_dealbreakers_per_dimension():
    cand = _cand(
        preference_tiers={
            "employment_percentage": {"ideal": [80, 100], "acceptable": [70, 100], "deal_breaker": [50, 100]},
            "salary": {"ideal": [90000, 120000], "acceptable": [80000, 130000], "deal_breaker": [75000, 150000]},
            "commute": {"ideal_max_minutes": 30, "acceptable_max_minutes": 45, "deal_breaker_max_minutes": 60},
            "remote": {"ideal": ["remote"], "acceptable": ["hybrid"], "deal_breaker": ["office"]},
            "weekend": {"ideal": False, "acceptable": True, "deal_breaker": True},
        }
    )
    # an office / far-away / low-salary / weekend job violates several tiers
    job = _job(location="Basel", remote_percentage=0, salary_min=60000, salary_max=70000,
               employment_percentage=30, description="Weekend on-call required.")
    result = evaluate_preference_tiers(cand, job)
    assert result["hard_constraints_met"] is False
    names = set(result["dimensions"])
    assert names == {"employment_percentage", "salary", "commute", "remote", "weekend"}
    for name in names:
        assert result["dimensions"][name]["deal_breaker"] is True
    assert len(result["hard_constraint_violations"]) == 5
    # salary is the only scalar component superseded by tiers in this case
    assert set(result["score_overrides"]) == {"employment", "salary", "location", "remote"}


# --- composite score-band categories --------------------------------------- #

def test_weak_match_category_band():
    cand = _cand(skills=[{"skill": "Python", "level": "advanced"}, {"skill": "SQL", "level": "advanced"}],
                 years_experience=2, education=[{"degree": "Bachelor", "field": "Business"}],
                 location="Bern", salary_expectation_min=96000, salary_expectation_max=104000)
    job = _job(required_skills=[{"skill": "Python", "mandatory": True}, {"skill": "SQL", "mandatory": True}],
               minimum_years_experience=6, location="Zurich",
               language_requirements=[{"language": "German", "level": "B2", "mandatory": False}],
               salary_min=90000, salary_max=100000)
    r = score_candidate_job(cand, job)
    assert r["category"] == "Weak match"  # score band 60-70
    assert r["mandatory_requirements_met"] is True
    assert r["hard_constraints_met"] is True
    assert "Insufficient relevant experience" in r["gaps"]


def test_score_driven_not_recommended_below_60():
    cand = _cand(skills=[{"skill": "Python", "level": "advanced"}, {"skill": "SQL", "level": "advanced"}],
                 years_experience=0, education=[{"degree": "Bachelor", "field": "Business"}],
                 location="Basel", salary_expectation_min=96000, salary_expectation_max=104000)
    job = _job(required_skills=[{"skill": "Python", "mandatory": True}, {"skill": "SQL", "mandatory": True}],
               minimum_years_experience=6, location="Zurich",
               language_requirements=[{"language": "German", "level": "B2", "mandatory": False}],
               salary_min=90000, salary_max=100000)
    r = score_candidate_job(cand, job)
    assert r["category"] == "Not recommended"  # score below 60, no deal-breakers
    assert r["hard_constraints_met"] is True
    assert r["recommendation"] == "Not recommended"
    assert "Overall fit below recommended threshold" in r["gaps"]
    assert "Insufficient relevant experience" in r["gaps"]


def test_education_gap_absent_when_degree_field_matches():
    cand = _cand(skills=[{"skill": "Python", "level": "advanced"}], years_experience=5,
                 education=[{"degree": "Master", "field": "Computer Science"}],
                 languages=[{"language": "German", "level": "C1"}])
    job = _job(required_skills=[{"skill": "Python", "mandatory": True}],
               minimum_years_experience=2, education_requirements="Computer Science",
               language_requirements=[{"language": "German", "level": "B2", "mandatory": True}])
    r = score_candidate_job(cand, job)
    assert r["mandatory_requirements_met"] is True
    assert not any("Education" in g for g in r["gaps"])
    assert r["recommendation"] == "Recommended"