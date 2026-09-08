"""
MATCHA - Automated tests for the candidate assessment engine
(Categorized "Areas to Improve" recommendations: professional + admin).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

from assessment import RecommendationEngine  # noqa: E402

engine = RecommendationEngine()


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


def make_profile(prefs=None, skills=("Python",), languages=(("German", "Native"),),
                 work_exp=None, education=None):
    profile = {
        "personal_info": {"name": "Ana", "location": "Basel", "email": "ana@example.ch"},
        "summary": "Experienced specialist.",
        "skills": list(skills),
        "work_experience": work_exp if work_exp is not None else [{"duration": "2018-2022"}],
        "education": education if education is not None else [{"degree": "Bachelor of Science"}],
        "languages": [{"language": lang, "level": level} for lang, level in languages],
        "certifications": ["Some Certificate"],
        "preferences": prefs or {},
    }
    return profile


def flat(items):
    text = " ".join(f"{i['area']} {i['detail']} {i['action']}" for i in items).lower()
    return text


# ---------------------------------------------------------------------- #
#  Professional areas
# ---------------------------------------------------------------------- #
def test_missing_required_skill_is_flagged_high_for_top_role():
    profile = make_profile(skills=("Marketing",))
    job = make_job(description="Software role", skills_required=["Python", "Docker"])
    result = engine.assess(profile, [job])
    skill_items = [i for i in result["professional"] if i["area"].startswith("Add skill")]
    assert any("Python" in i["area"] for i in skill_items)
    assert any("Docker" in i["area"] for i in skill_items)
    assert all(i["priority"] == "high" for i in skill_items)


def test_skills_already_present_are_not_suggested():
    profile = make_profile(skills=("Python", "Docker"))
    job = make_job(skills_required=["Python", "Docker"])
    result = engine.assess(profile, [job])
    assert not result["professional"] or not any("Add skill" in i["area"] for i in result["professional"])


def test_language_gap_detected():
    profile = make_profile(languages=(("German", "B1"),))
    job = make_job(requirements={"mandatory": ["German C1 or native"], "nice_to_have": []})
    result = engine.assess(profile, [job])
    assert any("Improve German" in i["area"] for i in result["professional"])


def test_language_on_profile_not_nagged():
    profile = make_profile(languages=(("German", "Native"),))
    job = make_job(requirements={"mandatory": ["German C1 or native"], "nice_to_have": []})
    result = engine.assess(profile, [job])
    assert not any("Learn German" in i["area"] or "Improve German" in i["area"]
                   for i in result["professional"])


def test_experience_years_gap():
    profile = make_profile(work_exp=[{"duration": "2021-2022"}])
    job = make_job(requirements={"mandatory": ["5+ years experience"], "nice_to_have": []})
    result = engine.assess(profile, [job])
    assert any("Gain more experience" in i["area"] for i in result["professional"])


def test_experience_sufficient_not_nagged():
    profile = make_profile(work_exp=[{"duration": "2016-2022"}])
    job = make_job(requirements={"mandatory": ["5+ years experience"], "nice_to_have": []})
    result = engine.assess(profile, [job])
    assert not any("Gain more experience" in i["area"] for i in result["professional"])


def test_deduplicates_shared_skills_across_jobs():
    profile = make_profile(skills=("Marketing",))
    job_a = make_job(id="a", title="Developer A", skills_required=["Python"])
    job_b = make_job(id="b", title="Developer B", skills_required=["Python"])
    result = engine.assess(profile, [job_a, job_b])
    python_items = [i for i in result["professional"] if "Python" in i["area"]]
    assert len(python_items) == 1
    assert len(python_items[0]["source_jobs"]) == 2


def test_priority_ordering_high_first():
    profile = make_profile(skills=("Marketing",))
    job = make_job(description="Software role", skills_required=["Python"])
    result = engine.assess(profile, [job])
    ranks = {"high": 0, "medium": 1, "low": 2}
    prios = [ranks[i["priority"]] for i in result["professional"]]
    assert prios == sorted(prios)


# ---------------------------------------------------------------------- #
#  Admin & profile-setup areas
# ---------------------------------------------------------------------- #
def test_missing_preferences_is_high_admin_item():
    result = engine.assess(make_profile(prefs=None), [make_job()])
    assert any(i["area"] == "Complete your Career Goals & Preferences" and i["priority"] == "high"
               for i in result["admin"])


def test_set_preferences_not_nagged():
    prefs = {"preferred_locations": ["Basel"], "salary_flexible": True,
             "availability": "Within 1 month"}
    result = engine.assess(make_profile(prefs=prefs), [make_job()])
    assert not any("Career Goals & Preferences" in i["area"] for i in result["admin"])


def test_completeness_items_for_sparse_profile():
    sparse = make_profile(work_exp=[], education=[], languages=[], skills=())
    result = engine.assess(sparse, [make_job()])
    areas = [i["area"] for i in result["admin"]]
    assert any("Add your skills" in a for a in areas)
    assert any("Add your education" in a for a in areas)
    assert any("Add your languages" in a for a in areas)
    assert any("Add your work history" in a for a in areas)


def test_career_break_not_penalized_in_admin_tip():
    sparse = make_profile(work_exp=[], skills=("Python",),
                          education=[{"degree": "BSc"}], languages=(("English", "Fluent"),))
    result = engine.assess(sparse, [make_job()])
    work_history = [i for i in result["admin"] if i["area"] == "Add your work history"]
    assert work_history
    assert "not penalized" in work_history[0]["action"].lower()


# ---------------------------------------------------------------------- #
#  Short per-job version (used in Job Matching)
# ---------------------------------------------------------------------- #
def test_short_for_job_bounded_and_actionable():
    profile = make_profile(skills=("Marketing",), prefs=None)
    job = make_job(description="Software role", skills_required=["Python", "Docker", "AWS"])
    short = engine.short_for_job(profile, job, preferences=None)
    assert 0 < len(short) <= 3
    assert all(isinstance(line, str) and "—" in line for line in short)


# ---------------------------------------------------------------------- #
#  Ethics: job-relevant only, no personality/psychology language
# ---------------------------------------------------------------------- #
FORBIDDEN_TERMS = ["personality", "culture fit", "culture-fit", "loyalty", "retention",
                   "emotional", "psychological", "mental", "motivation", "trait"]


def test_no_forbidden_language_in_recommendations():
    profile = make_profile(skills=("Marketing",), prefs=None)
    job = make_job(description="Software role", skills_required=["Python"])
    result = engine.assess(profile, [job])
    text = flat(result["professional"]) + flat(result["admin"])
    for term in FORBIDDEN_TERMS:
        assert term not in text, f"Forbidden term {term!r} found in assessment"


def test_recommendations_only_job_relevant():
    # Assessment output must only ever reference job requirements / profile
    # completeness - never a person's character.
    profile = make_profile(skills=("Marketing",), prefs=None)
    job = make_job(description="Software role", skills_required=["Python"])
    result = engine.assess(profile, [job])
    all_data = (flat(result["professional"]) + flat(result["admin"]) +
                " ".join(j["title"] for j in result["top_jobs"]).lower())
    for token in ("you are", "reliable", "hardworking", "dependable", "motivated"):
        assert token not in all_data