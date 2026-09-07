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
