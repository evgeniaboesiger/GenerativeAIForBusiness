from app.assessment.questions import (
    COMPANY_VALUES,
    PERSONALITY_DIMENSIONS,
    PERSONALITY_QUESTIONS,
    VALUE_QUESTIONS,
    compute_mbti_type,
    compute_personality_overlap,
    compute_personality_profile,
    compute_values_from_responses,
    compute_values_overlap,
)


def test_personality_question_ids_unique():
    ids = [q["id"] for q in PERSONALITY_QUESTIONS]
    assert len(ids) == len(set(ids))
    assert len(PERSONALITY_QUESTIONS) == 40


def test_value_question_ids_unique():
    ids = [q["id"] for q in VALUE_QUESTIONS]
    assert len(ids) == len(set(ids))
    assert len(VALUE_QUESTIONS) == 13


def test_personality_all_dimensions_covered_ten_to_twenty():
    from collections import Counter

    counts = Counter(q["dimension"] for q in PERSONALITY_QUESTIONS)
    for dim in PERSONALITY_DIMENSIONS:
        assert dim["id"] in counts
        assert 10 <= counts[dim["id"]] <= 20


def test_compute_personality_profile_empty_responses():
    profile = compute_personality_profile({})
    assert len(profile["dimensions"]) == 4
    for dim in PERSONALITY_DIMENSIONS:
        d = profile["dimensions"][dim["id"]]
        assert d == {"score": 50.0, "pole": "left", "confidence": 0.0}
    assert profile["type_code"] == "ENFP"  # a balanced score of 50 maps to the right letter


def test_compute_personality_profile_ignores_unknown_ids():
    profile = compute_personality_profile({"bogus_x": 7, "other": 2})
    assert profile == compute_personality_profile({})


def test_compute_personality_profile_reverse_scoring():
    # mind_2 is reverse-keyed: agreement (7) maps to the LEFT pole -> score 0
    profile = compute_personality_profile({"mind_2": 7})
    mind = profile["dimensions"]["mind"]
    assert mind["score"] == 0.0
    assert mind["pole"] == "left"
    assert mind["confidence"] == 100.0


def test_compute_mbti_type():
    assert compute_mbti_type({}) == "ENFP"
    null = {d["id"]: {"score": 0} for d in PERSONALITY_DIMENSIONS}
    assert compute_mbti_type(null) == "ISTJ"
    half = {d["id"]: {"score": 50} for d in PERSONALITY_DIMENSIONS}
    assert compute_mbti_type(half) == "ENFP"


def test_compute_values_from_responses_empty():
    ranked = compute_values_from_responses({})
    assert len(ranked) == len(COMPANY_VALUES)
    assert all(r["score"] == 0.0 for r in ranked)
    assert all(r["value"] in COMPANY_VALUES for r in ranked)


def test_compute_values_from_responses_scoring_and_ranking():
    ranked = compute_values_from_responses({"value_1": 5})
    assert ranked[0]["value"] == "innovation"
    assert ranked[0]["score"] == 100.0

    ranked2 = compute_values_from_responses({"value_1": 5, "value_2": 5})
    assert ranked2[0]["value"] == "innovation"
    assert ranked2[1]["value"] == "integrity"
    assert ranked2[0]["score"] == 100.0
    assert ranked2[1]["score"] == 100.0


def test_compute_values_from_responses_partial_agreement():
    value_3 = next(q for q in VALUE_QUESTIONS if q["id"] == "value_3")
    assert value_3["values"] == ["collaboration", "diversity"]
    # 3/5 agreement -> 60.0
    ranked = compute_values_from_responses({"value_3": 3})
    assert ranked[0]["value"] in ("collaboration", "diversity")
    assert ranked[0]["score"] == 60.0
    assert ranked[1]["value"] in ("collaboration", "diversity")
    assert ranked[1]["score"] == 60.0


def test_compute_values_from_responses_ignores_unknown_ids():
    assert compute_values_from_responses({"nope": 5}) == compute_values_from_responses({})


def test_compute_values_overlap_no_company_values():
    assert compute_values_overlap(["a", "b"], []) == (100.0, [])
    assert compute_values_overlap(["a", "b"], None) == (100.0, [])


def test_compute_values_overlap_no_candidate_values():
    assert compute_values_overlap([], ["a"]) == (0.0, [])


def test_compute_values_overlap_perfect_and_partial():
    assert compute_values_overlap(["a"], ["a"]) == (100.0, ["a"])
    score, matched = compute_values_overlap(["a", "b"], ["a"])
    assert score == 54.05
    assert matched == ["a"]


def test_compute_values_overlap_no_match():
    assert compute_values_overlap(["a", "b"], ["z"]) == (0.0, [])


def test_compute_values_overlap_weight_decay():
    # 7 candidates, last one (weight 0.1) matches
    score, matched = compute_values_overlap(["a1", "b2", "c3", "d4", "e5", "f6", "g"], ["g"])
    assert matched == ["g"]
    assert score == 2.6

    # item beyond the weight cut (index 7, weight <= 0) can never match
    too_many = ["a1", "b2", "c3", "d4", "e5", "f6", "g", "h"]
    assert compute_values_overlap(too_many, ["h"]) == (0.0, [])


def test_compute_personality_overlap_no_preferences():
    cand = {"dimensions": {"mind": {"score": 100.0, "pole": "right", "confidence": 100.0}}}
    assert compute_personality_overlap(cand, {}) == (100.0, [])
    assert compute_personality_overlap(cand, None) == (100.0, [])


def test_compute_personality_overlap_pole_alignment():
    cand = {"dimensions": {"mind": {"score": 100.0, "pole": "right"}}}
    assert compute_personality_overlap(cand, {"mind": {"pole": "right", "importance": 1}}) == (100.0, ["mind"])
    assert compute_personality_overlap(cand, {"mind": {"pole": "left", "importance": 1}}) == (0.0, [])
    # no preferred pole -> no distance, perfect fit
    assert compute_personality_overlap(cand, {"mind": {"pole": None, "importance": 1}}) == (100.0, ["mind"])


def test_compute_personality_overlap_zero_importance():
    cand = {"dimensions": {"mind": {"score": 100.0, "pole": "right"}}}
    assert compute_personality_overlap(cand, {"mind": {"pole": "left", "importance": 0}}) == (100.0, [])


def test_compute_personality_overlap_mixed_dimensions():
    cand = {
        "dimensions": {
            "mind": {"score": 100.0, "pole": "right"},
            "energy": {"score": 0.0, "pole": "left"},
        }
    }
    prefs = {
        "mind": {"pole": "right", "importance": 1},
        "energy": {"pole": "right", "importance": 1},
    }
    assert compute_personality_overlap(cand, prefs) == (50.0, ["mind"])


def test_compute_personality_overlap_fractional_importance():
    cand = {"dimensions": {"mind": {"score": 100.0, "pole": "right"}}}
    prefs = {"mind": {"pole": "right", "importance": 0.5}}
    assert compute_personality_overlap(cand, prefs) == (100.0, ["mind"])


def test_compute_personality_overlap_missing_dimension_defaults():
    # candidate dimension missing -> score defaults to 50, pole defaults to left
    # distance from preferred right pole = (100-50)/100 = 0.5 -> fit 0.5 (< 0.6, not matched)
    cand = {"dimensions": {}}
    prefs = {"mind": {"pole": "right", "importance": 1}}
    assert compute_personality_overlap(cand, prefs) == (50.0, [])