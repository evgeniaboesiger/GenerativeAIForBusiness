from app.profile.agent import ProfileAgent


agent = ProfileAgent(model_name="demo-test-model")


def test_complete_cv_extracts_structured_profile():
    cv = """
    Anna Keller
    Senior Python Developer | Zurich, Switzerland
    Summary: Python, Django, SQL, AWS, mentoring. Experienced in fintech and data teams.
    Experience
    2020-2023 Senior Python Developer, Alpine Data AG, Zurich
    - Built APIs with Python, Django and PostgreSQL
    - Led migration to AWS and CI/CD
    2016-2020 Data Engineer, Nova Analytics, Basel
    Education
    2016 BSc Computer Science, ETH Zurich
    Languages: English C1, German C2, French B1
    Preferred employment: 80%
    Preferred locations: Zurich, Basel
    Remote: yes
    Salary expectation: CHF 110000-130000
    Career goals: Senior platform engineer
    Availability: from 2025-02-01
    """

    result = agent.extract_profile(cv)

    assert result.profile.name == "Anna Keller"
    assert any(item.name == "Python" for item in result.profile.skills)
    assert any(item.name == "AWS" for item in result.profile.skills)
    assert len(result.profile.work_experience) >= 2
    assert result.profile.education[0].degree == "BSc"
    assert any(lang.language == "German" and lang.level == "C2" for lang in result.profile.languages)
    assert result.profile.preferred_employment_percentage == 80
    assert result.profile.remote_preference == "yes"
    assert result.profile.salary_expectation == {"min": 110000, "max": 130000, "currency": "CHF"}
    assert result.profile.availability == "2025-02-01"
    assert result.audit.fields_extracted >= 10
    assert result.audit.fields_needing_review == 0


def test_incomplete_cv_returns_unknown_for_missing_fields():
    cv = """
    Sofia Rossi
    Python developer with 4 years of experience.
    Experience: 2021-2023 Python Developer, BluePeak AG, Geneva
    Skills: Python, SQL
    """

    result = agent.extract_profile(cv)

    assert result.profile.name == "Sofia Rossi"
    assert result.profile.education is None
    assert result.profile.salary_expectation is None
    assert result.profile.preferred_locations is None
    assert result.profile.availability is None
    assert result.profile.work_experience[0].end_date == "2023"


def test_ambiguous_skill_is_marked_for_review():
    cv = """
    I am strong in digital transformation and business enablement.
    """

    result = agent.extract_profile(cv)

    ambiguous = [skill for skill in result.profile.skills if getattr(skill, "status", None) == "needs_review"]
    assert len(ambiguous) >= 1
    assert any(item.name == "digital transformation" for item in result.profile.skills)


def test_missing_dates_are_marked_unknown():
    cv = """
    Maria Meier
    Senior analyst at Nordic Finance.
    Experience: Senior Analyst, Nordic Finance
    Skills: Excel, Power BI
    """

    result = agent.extract_profile(cv)

    assert result.profile.work_experience[0].start_date is None
    assert result.profile.work_experience[0].end_date is None
    assert result.profile.work_experience[0].provenance.status in {"unverified", "needs_review"}


def test_multilingual_cv_extracts_language_levels():
    cv = """
    Je parle français B2, deutsch C1, english C1.
    """

    result = agent.extract_profile(cv)
    languages = {lng.language.lower(): lng.level for lng in result.profile.languages}

    assert languages.get("french") == "B2"
    assert languages.get("german") == "C1"
    assert languages.get("english") == "C1"


def test_duplicate_skills_are_deduplicated_and_validated():
    cv = """
    Python, SQL, Python, SQL, data analysis, Data Analysis
    """

    result = agent.extract_profile(cv)
    names = [skill.name.lower() for skill in result.profile.skills]

    assert names.count("python") == 1
    assert names.count("sql") == 1
    assert names.count("data analysis") == 1
    assert result.audit.duplicate_skills == ["python", "sql", "data analysis"]


def test_unsupported_information_is_not_extracted():
    cv = """
    Born in 1992, married, has two children, not disabled.
    Skills: Excel, Power BI
    """

    result = agent.extract_profile(cv)

    assert result.profile.skills and any(skill.name == "Excel" for skill in result.profile.skills)
    assert result.audit.unsupported_fields == ["date_of_birth", "marital_status", "children", "disability_status"]


def test_hallucination_prevention_for_missing_salary_and_remote_preferences():
    cv = """
    Product Manager with strong stakeholder communication and roadmap planning.
    """

    result = agent.extract_profile(cv)

    assert result.profile.salary_expectation is None
    assert result.profile.remote_preference is None
    assert result.profile.preferred_locations is None
    assert result.audit.fields_needing_review >= 0
