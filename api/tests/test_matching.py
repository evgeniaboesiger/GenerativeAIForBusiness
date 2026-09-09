import pytest
from app.db.models import Candidate, Job
from app.db.session import SessionLocal
from app.matching.engine import score_candidate_job
from scripts.seed_demo_data import seed


def make_candidate(skills, years=3, education=None, languages=None, salary_min=70000, salary_max=90000, employment_min=80, employment_max=100, location='Zurich'):
    return {
        "id": 1,
        "skills": [{"skill": s, "level": "advanced"} for s in skills],
        "years_experience": years,
        "education": education or [],
        "languages": languages or [],
        "salary_expectation_min": salary_min,
        "salary_expectation_max": salary_max,
        "employment_percentage_min": employment_min,
        "employment_percentage_max": employment_max,
        "location": location,
        "maximum_commute_minutes": 60,
    }


def make_job(required_skills, preferred_skills=None, min_years=2, salary_min=70000, salary_max=90000, location='Zurich'):
    return {
        "id": 1,
        "required_skills": [{"skill": s, "mandatory": True} for s in required_skills],
        "preferred_skills": preferred_skills or [],
        "minimum_years_experience": min_years,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "location": location,
        "language_requirements": [{"language": "German", "level": "B2", "mandatory": True}],
    }


def test_exact_skill_match():
    candidate = make_candidate(["Python","SQL","React"], years=5, languages=[{"language":"German","level":"C1"}])
    job = make_job(["Python","SQL"], preferred_skills=["React"], min_years=3)
    res = score_candidate_job(candidate, job)
    assert res["component_scores"]["skills"] >= 90


def test_missing_mandatory_language():
    candidate = make_candidate(["Python","SQL"], years=5, languages=[{"language":"English","level":"C1"}])
    job = make_job(["Python"], min_years=2)
    res = score_candidate_job(candidate, job)
    assert res["mandatory_requirements_met"] is False


def test_salary_inside_range():
    candidate = make_candidate(["Marketing"], salary_min=80000, salary_max=90000, languages=[{"language":"German","level":"B2"}])
    job = make_job(["Marketing"], salary_min=75000, salary_max=95000)
    res = score_candidate_job(candidate, job)
    assert res["component_scores"]["salary"] >= 90


def test_reproducible_scoring():
    candidate = make_candidate(["Python", "SQL", "React"], years=5, languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python", "SQL"], preferred_skills=["React"], min_years=3)

    first = score_candidate_job(candidate, job)
    second = score_candidate_job(candidate, job)

    assert first == second


def test_missing_mandatory_skill_and_education_block_recommendation():
    candidate = {
        "id": 2,
        "skills": [{"skill": "SQL", "level": "advanced"}],
        "years_experience": 4,
        "education": [{"degree": "Bachelor", "field": "Business"}],
        "languages": [{"language": "German", "level": "B2"}],
        "salary_expectation_min": 70000,
        "salary_expectation_max": 90000,
        "employment_percentage_min": 80,
        "employment_percentage_max": 100,
        "location": "Zurich",
        "maximum_commute_minutes": 60,
        "career_goal": "Business Analyst",
    }
    job = {
        "id": 2,
        "required_skills": [{"skill": "Python", "mandatory": True}],
        "preferred_skills": ["SQL"],
        "minimum_years_experience": 2,
        "education_requirements": "Master",
        "language_requirements": [{"language": "German", "level": "B2", "mandatory": True}],
        "salary_min": 70000,
        "salary_max": 95000,
        "location": "Zurich",
        "department": "Data",
    }

    result = score_candidate_job(candidate, job)

    assert result["mandatory_requirements_met"] is False
    assert any("Missing mandatory skill" in gap for gap in result["gaps"])
    assert any("Education requirement not met" in gap for gap in result["gaps"])


def test_seed_population_is_structurally_valid():
    stats = seed()
    assert stats == {"candidates": 100, "jobs": 50}

    db = SessionLocal()
    try:
        assert db.query(Candidate).count() == 100
        assert db.query(Job).count() == 50
        assert db.query(Candidate).filter(Candidate.email == "demo0@example.local").count() == 1
    finally:
        db.close()


def test_step3_demo_scenarios():
    scenarios = [
        (
            make_candidate(["Python", "SQL", "React"], years=5, languages=[{"language": "German", "level": "C1"}]),
            make_job(["Python", "SQL"], preferred_skills=["React"], min_years=3),
            True,
            "Recommended",
        ),
        (
            make_candidate(["Python", "SQL"], years=5, languages=[{"language": "English", "level": "C1"}]),
            make_job(["Python"], min_years=2),
            False,
            "Not recommended",
        ),
        (
            make_candidate(["Marketing"], salary_min=80000, salary_max=90000, languages=[{"language": "German", "level": "B2"}]),
            make_job(["Marketing"], salary_min=75000, salary_max=95000),
            True,
            "Recommended",
        ),
        (
            make_candidate(["Data Analysis"], years=3, languages=[{"language": "German", "level": "B2"}], education=[{"degree": "Bachelor", "field": "Economics"}]),
            make_job(["Data Analysis"], min_years=2, salary_min=70000, salary_max=90000),
            True,
            "Recommended",
        ),
        (
            make_candidate(["Finance", "Excel"], years=4, languages=[{"language": "German", "level": "C1"}], education=[{"degree": "Bachelor", "field": "Finance"}], location='Zurich'),
            make_job(["Finance", "Excel"], min_years=2, salary_min=70000, salary_max=90000, location='Zurich'),
            True,
            "Recommended",
        ),
        (
            make_candidate(["SQL"], years=2, languages=[{"language": "German", "level": "B2"}], education=[{"degree": "Bachelor", "field": "Business"}]),
            make_job(["Python", "SQL"], min_years=2, salary_min=70000, salary_max=90000),
            False,
            "Not recommended",
        ),
        (
            make_candidate(["Python", "Docker"], years=5, languages=[{"language": "German", "level": "C1"}], education=[{"degree": "Master", "field": "Computer Science"}], salary_min=85000, salary_max=95000, employment_min=50, employment_max=100),
            make_job(["Python", "Docker"], preferred_skills=["Kubernetes"], min_years=3, salary_min=80000, salary_max=100000),
            True,
            "Recommended",
        ),
        (
            make_candidate(["Java", "SQL"], years=1, languages=[{"language": "English", "level": "C1"}], education=[{"degree": "Bachelor", "field": "Engineering"}], location='Zurich'),
            make_job(["Java", "SQL"], min_years=3, salary_min=80000, salary_max=100000, location='Bern'),
            False,
            "Not recommended",
        ),
    ]

    for candidate, job, expected_mandatory, expected_recommendation in scenarios:
        result = score_candidate_job(candidate, job)
        assert result["mandatory_requirements_met"] is expected_mandatory
        if expected_recommendation == "Recommended":
            assert result["recommendation"] == "Recommended"
        else:
            assert result["recommendation"] in {"Not recommended", "Recommended"}


def test_values_overlap_scoring():
    candidate = make_candidate(["Python"], years=3, languages=[{"language": "German", "level": "C1"}])
    candidate["values"] = ["innovation", "integrity", "collaboration"]
    job = make_job(["Python"], min_years=2)
    job["company_values"] = ["innovation", "integrity", "customer_centricity"]

    res = score_candidate_job(candidate, job)
    values_score = res["component_scores"]["values"]
    # two of the candidate's top three values overlap
    assert 50 < values_score < 100
    # informational only - never used for a strength/gap or the score
    assert "values" in res["informational_only"]
    assert not any("alig" in s.lower() for s in res["strengths"] + res["gaps"])


def test_personality_fit_scoring():
    candidate = make_candidate(["Python"], years=3, languages=[{"language": "German", "level": "C1"}])
    candidate["personality"] = {
        "dimensions": {
            "mind": {"score": 20, "pole": "left", "confidence": 60},
            "energy": {"score": 80, "pole": "right", "confidence": 60},
            "nature": {"score": 50, "pole": "left", "confidence": 0},
            "tactics": {"score": 50, "pole": "left", "confidence": 0},
        }
    }
    job = make_job(["Python"], min_years=2)
    job["personality_preferences"] = {
        "mind": {"pole": "left", "importance": 1.0},
        "energy": {"pole": "right", "importance": 1.0},
    }

    res = score_candidate_job(candidate, job)
    personality_score = res["component_scores"]["personality"]
    # candidate aligns well with both preferences (left-mind, right-energy)
    assert personality_score >= 70
    assert "personality" in res["informational_only"]
    assert not any("culture" in s.lower() or "personality" in s.lower() for s in res["strengths"] + res["gaps"])


def test_missing_personality_does_not_hurt_score():
    # candidate has no personality/values -> those components are neutral (100)
    candidate = make_candidate(["Python", "SQL"], years=4, languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python"], min_years=2)
    job["company_values"] = ["innovation"]
    res = score_candidate_job(candidate, job)
    assert res["component_scores"]["values"] == 100.0
    assert res["component_scores"]["personality"] == 100.0


def test_personality_and_values_do_not_affect_overall_score():
    # Personality/values are informational only: their presence must never
    # change the weighted overall score or the recommendation.
    base_candidate = make_candidate(["Python"], years=3, languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python"], min_years=2)

    base = score_candidate_job(dict(base_candidate), job)

    aligned = dict(base_candidate)
    aligned["values"] = ["innovation", "integrity", "collaboration"]
    aligned["personality"] = {
        "dimensions": {
            "mind": {"score": 95, "pole": "right", "confidence": 90},
            "energy": {"score": 90, "pole": "right", "confidence": 80},
            "nature": {"score": 50, "pole": "left", "confidence": 0},
            "tactics": {"score": 50, "pole": "left", "confidence": 0},
        }
    }

    misaligned = dict(base_candidate)
    misaligned["values"] = ["profitability"]
    misaligned["personality"] = {
        "dimensions": {
            "mind": {"score": 1, "pole": "left", "confidence": 90},
            "energy": {"score": 1, "pole": "left", "confidence": 90},
            "nature": {"score": 50, "pole": "left", "confidence": 0},
            "tactics": {"score": 50, "pole": "left", "confidence": 0},
        }
    }

    for job_prefs in ({"company_values": ["innovation"]},
                      {"company_values": ["profitability"]},
                      {"personality_preferences": {"mind": {"pole": "right", "importance": 1.0}}},):
        job_with_extras = dict(job)
        job_with_extras.update(job_prefs)
        a = score_candidate_job(aligned, job_with_extras)
        m = score_candidate_job(misaligned, job_with_extras)
        assert a["overall_score"] == base["overall_score"]
        assert m["overall_score"] == base["overall_score"]
        assert a["recommendation"] == base["recommendation"]
        assert m["recommendation"] == base["recommendation"]


# --- P1: hard constraints + fit buckets ----------------------------------- #

def test_salary_floor_below_job_range_blocks_recommendation():
    # Candidate needs at least 90k but the job tops out at 85k -> deal-breaker.
    candidate = make_candidate(["Python", "SQL"], salary_min=90000, salary_max=105000,
                               languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python"], salary_min=70000, salary_max=85000)
    res = score_candidate_job(candidate, job)
    assert res["hard_constraints_met"] is False
    assert res["recommendation"] == "Not recommended"
    assert any("salary" in v.lower() or "tops out" in v.lower() for v in res["hard_constraint_violations"])


def test_salary_floor_not_blocking_when_job_can_pay():
    candidate = make_candidate(["Python"], salary_min=80000, salary_max=90000,
                               languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python"], salary_min=75000, salary_max=95000)
    res = score_candidate_job(candidate, job)
    assert res["hard_constraints_met"] is True


def test_workload_percentage_blocks_recommendation():
    # Candidate is available only 50-80% but the role requires 100%.
    candidate = make_candidate(["Python"], employment_min=50, employment_max=80,
                               languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python"])
    job["employment_percentage"] = 100
    res = score_candidate_job(candidate, job)
    assert res["hard_constraints_met"] is False
    assert any("workload" in v.lower() for v in res["hard_constraint_violations"])


def test_overlapping_workload_passes():
    candidate = make_candidate(["Python"], employment_min=80, employment_max=100,
                               languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python"])
    job["employment_percentage"] = 80
    res = score_candidate_job(candidate, job)
    assert res["hard_constraints_met"] is True


def test_commute_dealbreaker():
    # Candidate max commute is 30 min, job is far away.
    candidate = make_candidate(["Python"], location="Zurich",
                               languages=[{"language": "German", "level": "C1"}])
    candidate["maximum_commute_minutes"] = 30
    job = make_job(["Python"], location="Bern")
    res = score_candidate_job(candidate, job)
    # Zurich->Bern is ~65+ min so it must be a deal-breaker
    assert res["hard_constraints_met"] is False
    assert any("commute" in v.lower() for v in res["hard_constraint_violations"])


def test_weekend_work_flags_dealbreaker():
    candidate = make_candidate(["Python"], languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python"])
    job["description"] = "This role requires weekend and public holiday cover, including on-call duty."
    res = score_candidate_job(candidate, job)
    assert res["hard_constraints_met"] is False
    assert any("weekend" in v.lower() or "on-call" in v.lower() for v in res["hard_constraint_violations"])


def test_fit_buckets_are_present_and_breakdown_visible():
    candidate = make_candidate(["Python", "SQL", "React"], years=5,
                               languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python", "SQL"], preferred_skills=["React"], min_years=3)
    res = score_candidate_job(candidate, job)
    fb = res["fit_buckets"]
    for key in ("professional", "practical", "values", "overall_weighted"):
        assert key in fb
    # professional and practical should be high for a strong match
    assert fb["professional"] >= 80
    # overall weighted is a number between 0 and 100
    assert 0 <= fb["overall_weighted"] <= 100
    # aliases exposed on the top-level result
    assert res["professional_fit"] == fb["professional"]
    assert res["practical_fit"] == fb["practical"]
    assert res["values_fit"] == fb["values"]


def test_values_still_not_merged_into_overall_under_fit_model():
    # If values are absent they are neutral (100); with a present but
    # misaligned value they must NOT change the overall score or recommendation.
    candidate = make_candidate(["Python"], years=5, languages=[{"language": "German", "level": "C1"}])
    job = make_job(["Python"], min_years=3)

    base = score_candidate_job(dict(candidate), job)

    misaligned = dict(candidate)
    misaligned["values"] = ["profitability"]
    job_mis = dict(job)
    job_mis["company_values"] = ["innovation", "integrity"]
    res = score_candidate_job(misaligned, job_mis)

    assert res["overall_score"] == base["overall_score"]
    assert res["recommendation"] == base["recommendation"]
    # values_fit is reported for transparency but informational only
    assert "values" in res["informational_only"]
    assert res["values_fit"] < 100


# --------------------------------------------------------------------------- #
# P2: Ideal / Acceptable / Deal-breaker preference tiers
# --------------------------------------------------------------------------- #
def make_tiered_candidate():
    c = make_candidate(["Python"], years=5, languages=[{"language": "German", "level": "C1"}])
    c["preference_tiers"] = {
        "salary": {"ideal": [90000, 120000], "acceptable": [80000, 130000], "deal_breaker": [75000, 150000]},
        "commute": {"ideal_max_minutes": 30, "acceptable_max_minutes": 45, "deal_breaker_max_minutes": 60},
        "remote": {"ideal": ["remote"], "acceptable": ["hybrid"], "deal_breaker": ["office"]},
        "weekend": {"ideal": False, "acceptable": False, "deal_breaker": True},
    }
    return c


def test_ideal_tier_scores_full_and_overrides_scalar():
    candidate = make_tiered_candidate()
    job = make_job(["Python"])
    job.update({"salary_min": 90000, "salary_max": 120000, "remote_percentage": 100,
                "description": "Fully remote. No weekend work."})
    res = score_candidate_job(candidate, job)
    assert res["hard_constraints_met"] is True
    tr = res["preference_tiers"]
    assert tr["hard_constraints_met"] is True
    comps = res["component_scores"]
    # tier score overrides the scalar employment/salary/location/remote scores
    assert comps["salary"] == 100.0
    assert comps["remote"] == 100.0
    assert comps["location"] >= 90
    for name in ("salary", "commute", "remote", "weekend"):
        assert tr["dimensions"][name]["deal_breaker"] is False


def test_acceptable_tier_scores_partial():
    candidate = make_tiered_candidate()
    job = make_job(["Python"])
    # salary sits only in the acceptable band (80k-90k top edge)
    job.update({"salary_min": 80000, "salary_max": 85000, "remote_percentage": 50,
                "description": "Hybrid work. No weekend cover."})
    res = score_candidate_job(candidate, job)
    tr = res["preference_tiers"]["dimensions"]
    assert tr["salary"]["score"] == 70.0
    assert tr["salary"]["deal_breaker"] is False
    assert tr["remote"]["score"] == 70.0
    assert res["hard_constraints_met"] is True


def test_deal_breaker_tier_disqualifies():
    candidate = make_tiered_candidate()
    job = make_job(["Python"])
    job.update({"salary_min": 60000, "salary_max": 70000, "remote_percentage": 0,
                "description": "Office based. Weekend on-call shifts are required."})
    res = score_candidate_job(candidate, job)
    assert res["hard_constraints_met"] is False
    assert res["category"] == "Not recommended"
    tr = res["preference_tiers"]
    assert tr["hard_constraints_met"] is False
    assert any("deal-breaker" in v.lower() for v in tr["hard_constraint_violations"])
    # overrides still applied - salary & remote scored 0 on this job
    assert res["component_scores"]["salary"] == 0.0
    assert res["component_scores"]["remote"] == 0.0


def test_no_tiers_falls_back_to_scalar_preferences():
    candidate = make_candidate(["Python"], years=5, languages=[{"language": "German", "level": "C1"}])
    assert "preference_tiers" not in candidate
    job = make_job(["Python"])
    job.update({"description": "No weekend work."})
    res = score_candidate_job(candidate, job)
    assert res["preference_tiers"] is None
    # existing scalar commute limit still enforced
    assert res["component_scores"]["salary"] > 0
    # remote now contributes to practical fit (dilution bug fixed)
    comps = res["component_scores"]
    assert "remote" in comps and "availability" in comps


def test_negated_weekend_phrasing_is_not_a_dealbreaker():
    from app.matching.tiers import job_has_weekend_work
    job = make_job(["Python"])
    job["description"] = "No weekend work. On-call rare and optional."
    job["remote_percentage"] = 100
    assert job_has_weekend_work(job) is False
    res = score_candidate_job(make_tiered_candidate(), job)
    assert res["hard_constraints_met"] is True
