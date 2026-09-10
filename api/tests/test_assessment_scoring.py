from app.assessment.questions import compute_mbti_type, compute_personality_profile, PERSONALITY_QUESTIONS


def test_reverse_keyed_items_are_tagged():
    reversed_ids = [q["id"] for q in PERSONALITY_QUESTIONS if q.get("reverse")]
    assert len(reversed_ids) == 20
    for expected in ("mind_2", "mind_3", "mind_6", "mind_8", "mind_10",
                     "energy_1", "energy_3", "energy_5", "energy_7", "energy_9",
                     "nature_1", "nature_3", "nature_5", "nature_7", "nature_9",
                     "tactics_1", "tactics_3", "tactics_5", "tactics_7", "tactics_9"):
        assert expected in reversed_ids, f"{expected} should be reverse-keyed"


def test_agreement_with_reverse_keyed_item_maps_to_left_pole():
    # mind_2: "prefer a small group of close friends" expresses Introversion
    # (the LEFT pole). Agreeing strongly must score left, i.e. "I".
    profile = compute_personality_profile({"mind_2": 7})
    assert profile["dimensions"]["mind"]["score"] <= 20
    assert profile["dimensions"]["mind"]["pole"] == "left"
    assert profile["type_code"][0] == "I"


def test_agreement_with_forward_keyed_item_maps_to_right_pole():
    # mind_1: "easy to introduce yourself" expresses Extraversion (right).
    profile = compute_personality_profile({"mind_1": 7})
    assert profile["dimensions"]["mind"]["score"] >= 80
    assert profile["dimensions"]["mind"]["pole"] == "right"
    assert profile["type_code"][0] == "E"


def test_neutral_answers_score_center():
    profile = compute_personality_profile({"mind_1": 4, "mind_2": 4})
    assert profile["dimensions"]["mind"]["score"] == 50.0


def test_full_battery_consistent():
    # All reverse-keyed items at 7 (agree to left), all forward at 1 (disagree
    # to right content) => every dimension should land on the left pole.
    responses = {}
    for q in PERSONALITY_QUESTIONS:
        responses[q["id"]] = 7 if q.get("reverse") else 1
    profile = compute_personality_profile(responses)
    for dim in ("mind", "energy", "nature", "tactics"):
        assert profile["dimensions"][dim]["pole"] == "left", f"{dim} should be left"
    assert compute_mbti_type(profile["dimensions"]) == "ISTJ"