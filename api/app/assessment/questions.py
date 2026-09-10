"""
Personality & values assessment framework for FRAUMATCH.

Personality model is a 16personalities-inspired four-dimension framework
(Mind, Energy, Nature, Tactics). Each dimension is scored on a continuum;
the candidate's responses place them along each axis. No protected
attributes are used.

Values are work-related company values that candidates rank and companies
declare. Matching is based on overlap of the candidate's top values with the
company's stated values.
"""

# Four personality dimensions used by the assessment
PERSONALITY_DIMENSIONS = [
    {"id": "mind", "label": "Mind", "left": "Introverted (I)", "right": "Extraverted (E)"},
    {"id": "energy", "label": "Energy", "left": "Observant (S)", "right": "Intuitive (N)"},
    {"id": "nature", "label": "Nature", "left": "Thinking (T)", "right": "Feeling (F)"},
    {"id": "tactics", "label": "Tactics", "left": "Judging (J)", "right": "Prospecting (P)"},
]

# 40 personality questions: 10 per dimension.
# Each question maps to a dimension; the response scale is 1..7 where the
# left-anchor of the scale corresponds to the "left" pole and the right
# anchor corresponds to the "right" pole. Questions whose statement expresses
# the LEFT pole are marked reverse=True so agreement is mapped to the left
# side of the scale (8 - answer) before averaging.
PERSONALITY_QUESTIONS = [
    # --- Mind (10) ---
    {"id": "mind_1", "dimension": "mind", "text": "You find it easy to introduce yourself to other people."},
    {"id": "mind_2", "dimension": "mind", "text": "You often prefer to spend time with a small group of close friends rather than a large group.", "reverse": True},
    {"id": "mind_3", "dimension": "mind", "text": "You tend to be quiet and reserved in unfamiliar situations.", "reverse": True},
    {"id": "mind_4", "dimension": "mind", "text": "After a busy day, you recharge best by being around other people."},
    {"id": "mind_5", "dimension": "mind", "text": "You usually think out loud and talk through ideas with others."},
    {"id": "mind_6", "dimension": "mind", "text": "You prefer to work independently rather than in a lively group setting.", "reverse": True},
    {"id": "mind_7", "dimension": "mind", "text": "You feel energized by social events and networking."},
    {"id": "mind_8", "dimension": "mind", "text": "You often need quiet time alone to think clearly.", "reverse": True},
    {"id": "mind_9", "dimension": "mind", "text": "You are comfortable being the center of attention."},
    {"id": "mind_10", "dimension": "mind", "text": "You would rather observe a conversation than lead it.", "reverse": True},
    # --- Energy (10) ---
    {"id": "energy_1", "dimension": "energy", "text": "You rely more on your experience than on your imagination when making decisions.", "reverse": True},
    {"id": "energy_2", "dimension": "energy", "text": "You enjoy thinking about possibilities and what could be, not just what is."},
    {"id": "energy_3", "dimension": "energy", "text": "You focus on concrete facts and details rather than abstract theories.", "reverse": True},
    {"id": "energy_4", "dimension": "energy", "text": "You find it easy to think of new ways to do things."},
    {"id": "energy_5", "dimension": "energy", "text": "You prefer sticking to proven methods over experimenting.", "reverse": True},
    {"id": "energy_6", "dimension": "energy", "text": "You often notice patterns and connections that others miss."},
    {"id": "energy_7", "dimension": "energy", "text": "You are more practical than visionary.", "reverse": True},
    {"id": "energy_8", "dimension": "energy", "text": "You are drawn to big-picture thinking and future trends."},
    {"id": "energy_9", "dimension": "energy", "text": "You trust established routines and procedures.", "reverse": True},
    {"id": "energy_10", "dimension": "energy", "text": "You enjoy brainstorming speculative ideas, even if they are not realistic."},
    # --- Nature (10) ---
    {"id": "nature_1", "dimension": "nature", "text": "You base your decisions more on logic than on how they affect people.", "reverse": True},
    {"id": "nature_2", "dimension": "nature", "text": "You find it important to acknowledge other people's feelings."},
    {"id": "nature_3", "dimension": "nature", "text": "You would rather point out the truth than spare someone's feelings.", "reverse": True},
    {"id": "nature_4", "dimension": "nature", "text": "You value harmony in a team over being objectively right."},
    {"id": "nature_5", "dimension": "nature", "text": "You tend to make decisions with your head rather than your heart.", "reverse": True},
    {"id": "nature_6", "dimension": "nature", "text": "You are quick to praise the efforts of others."},
    {"id": "nature_7", "dimension": "nature", "text": "You find it easy to separate personal feelings from professional decisions.", "reverse": True},
    {"id": "nature_8", "dimension": "nature", "text": "You are moved by other people's stories and struggles."},
    {"id": "nature_9", "dimension": "nature", "text": "You prefer direct, honest feedback even when it is harsh.", "reverse": True},
    {"id": "nature_10", "dimension": "nature", "text": "You consider team morale as important as results."},
    # --- Tactics (10) ---
    {"id": "tactics_1", "dimension": "tactics", "text": "You like to have a clear plan before starting a project.", "reverse": True},
    {"id": "tactics_2", "dimension": "tactics", "text": "You are comfortable with last-minute changes to your schedule."},
    {"id": "tactics_3", "dimension": "tactics", "text": "You tend to finish tasks well ahead of their deadlines.", "reverse": True},
    {"id": "tactics_4", "dimension": "tactics", "text": "You enjoy improvising rather than following a strict schedule."},
    {"id": "tactics_5", "dimension": "tactics", "text": "You prefer your day to be structured and organized.", "reverse": True},
    {"id": "tactics_6", "dimension": "tactics", "text": "You are open to changing your plans at the last minute."},
    {"id": "tactics_7", "dimension": "tactics", "text": "You create to-do lists and like to tick items off.", "reverse": True},
    {"id": "tactics_8", "dimension": "tactics", "text": "You like to keep your options open rather than commit early."},
    {"id": "tactics_9", "dimension": "tactics", "text": "You find it stressful when plans keep changing.", "reverse": True},
    {"id": "tactics_10", "dimension": "tactics", "text": "You work best with freedom and flexibility rather than rigid rules."},
]

# Work-related company/candidate values used for matching.
# Candidate selects/ranks their top personal values; a company declares its
# top values. Matching is based on the overlap of the candidate's ranked
# values with the company's stated values.
COMPANY_VALUES = {
    "innovation": {"label": "Innovation", "description": "Creativity, new ideas, and continuous improvement"},
    "integrity": {"label": "Integrity", "description": "Honesty, transparency, and ethical conduct"},
    "collaboration": {"label": "Collaboration", "description": "Teamwork, inclusion, and mutual support"},
    "customer_centricity": {"label": "Customer centricity", "description": "Putting customers and their needs first"},
    "sustainability": {"label": "Sustainability", "description": "Environmental and social responsibility"},
    "excellence": {"label": "Excellence", "description": "High quality standards and mastery"},
    "autonomy": {"label": "Autonomy", "description": "Independence, freedom, and self-direction"},
    "agility": {"label": "Agility", "description": "Flexibility, speed, and adaptiveness"},
    "growth": {"label": "Growth", "description": "Learning, development, and progress"},
    "security": {"label": "Security", "description": "Stability, safety, and predictability"},
    "diversity": {"label": "Diversity", "description": "Valuing different backgrounds and perspectives"},
    "work_life_balance": {"label": "Work-life balance", "description": "Well-being and balance between work and life"},
    "impact": {"label": "Impact", "description": "Making a meaningful difference"},
    "profitability": {"label": "Profitability", "description": "Financial performance and efficiency"},
}

# Candidate value statements that reveal which values matter to the person.
# Each statement maps to one (or more) underlying values. Used to build the
# candidate's ranked value profile from their questionnaire responses.
VALUE_QUESTIONS = [
    {
        "id": "value_1",
        "statement": "I get the most satisfaction at work when I can put my creative ideas into practice.",
        "values": ["innovation"],
    },
    {
        "id": "value_2",
        "statement": "I would rather work for a company that is honest and transparent than one that bends the rules.",
        "values": ["integrity"],
    },
    {
        "id": "value_3",
        "statement": "I perform at my best when I am part of a supportive, inclusive team.",
        "values": ["collaboration", "diversity"],
    },
    {
        "id": "value_4",
        "statement": "Understanding the customer deeply and serving their needs is what motivates me.",
        "values": ["customer_centricity"],
    },
    {
        "id": "value_5",
        "statement": "Working for an organization that cares about the environment is important to me.",
        "values": ["sustainability"],
    },
    {
        "id": "value_6",
        "statement": "I take pride in delivering work of the highest possible quality.",
        "values": ["excellence"],
    },
    {
        "id": "value_7",
        "statement": "I thrive when I am given responsibility and the freedom to make my own decisions.",
        "values": ["autonomy"],
    },
    {
        "id": "value_8",
        "statement": "I enjoy adapting quickly when priorities change and moving fast.",
        "values": ["agility"],
    },
    {
        "id": "value_9",
        "statement": "Continuous learning and personal development are at the core of my career.",
        "values": ["growth"],
    },
    {
        "id": "value_10",
        "statement": "I value a predictable, stable work environment where I feel secure.",
        "values": ["security"],
    },
    {
        "id": "value_11",
        "statement": "I want my work to fit around my life and protect my well-being.",
        "values": ["work_life_balance"],
    },
    {
        "id": "value_12",
        "statement": "I am driven by the desire to make a real difference in the world.",
        "values": ["impact"],
    },
    {
        "id": "value_13",
        "statement": "I care about results and efficiency more than almost anything else.",
        "values": ["profitability"],
    },
]


def compute_personality_profile(responses):
    """Aggregate 1..7 responses into a per-dimension continuous score.

    Each dimension cluster is scored as the mean of its responses mapped to a
    0..100 scale, where 0 = left pole and 100 = right pole. A score of 50
    indicates a balanced preference.
    """
    dims = {}
    for q in PERSONALITY_QUESTIONS:
        answer = responses.get(q["id"])
        if answer is None:
            continue
        # Reverse-keyed items express the LEFT pole: agreement maps to the
        # left side of the scale (1..7 => 7..1).
        if q.get("reverse"):
            answer = 8 - answer
        dims.setdefault(q["dimension"], []).append(float(answer))

    profile = {}
    for dim in PERSONALITY_DIMENSIONS:
        values = dims.get(dim["id"], [])
        if not values:
            profile[dim["id"]] = {"score": 50.0, "pole": "left", "confidence": 0.0}
            continue
        mean = sum(values) / len(values)
        # map 1..7 to 0..100
        score = round(((mean - 1) / 6) * 100, 1)
        pole = "right" if score >= 50 else "left"
        # confidence by closeness to extremes
        confidence = round(abs(score - 50) / 50 * 100, 1)
        profile[dim["id"]] = {"score": score, "pole": pole, "confidence": confidence}

    return {"dimensions": profile, "type_code": compute_mbti_type(profile)}


def compute_mbti_type(profile):
    """Derive a 4-letter type code from a personality profile."""
    letter_map = {
        "mind": ("I", "E"),
        "energy": ("S", "N"),
        "nature": ("T", "F"),
        "tactics": ("J", "P"),
    }
    code = ""
    for dim_id, (left, right) in letter_map.items():
        score = profile.get(dim_id, {}).get("score", 50)
        code += right if score >= 50 else left
    return code


def compute_values_from_responses(value_responses):
    """Aggregate agreement responses (1..5) into a ranked list of values.

    Each question's underlying values gain weight by agreement. Returns the
    ranked list of value ids, most important first.
    """
    scores = {vid: 0.0 for vid in COMPANY_VALUES}
    counts = {vid: 0 for vid in COMPANY_VALUES}
    for q in VALUE_QUESTIONS:
        answer = value_responses.get(q["id"])
        if answer is None:
            continue
        weight = float(answer) / 5.0  # 0..1
        for vid in q["values"]:
            scores[vid] += weight
            counts[vid] += 1

    # normalize by number of times a value is referenced
    ranked = {}
    for vid, s in scores.items():
        n = counts[vid] or 1
        ranked[vid] = round(s / n * 100, 1)

    ordered = sorted(ranked.items(), key=lambda x: x[1], reverse=True)
    return [{"value": vid, "label": COMPANY_VALUES[vid]["label"], "score": s} for vid, s in ordered]


def compute_values_overlap(candidate_values, company_values):
    """Score how well a candidate's top values overlap with a company's values.

    candidate_values: list of value ids ordered by candidate priority.
    company_values: list of company value ids (only declared ones).

    Returns 0..100 overlap score and the list of matched values.
    """
    if not company_values:
        return 100.0, []
    company_set = set(company_values)
    # weight earlier (higher-priority) candidate values more
    weight = 1.0
    total = 0.0
    matched = []
    for cand in candidate_values:
        if cand in company_set:
            matched.append(cand)
            total += weight
        weight -= 0.15
        if weight <= 0:
            break
    if not candidate_values:
        return 0.0, []
    max_possible = sum(max(1.0 - i * 0.15, 0) for i in range(len(candidate_values)))
    if max_possible == 0:
        return 0.0, matched
    return round((total / max_possible) * 100, 2), matched


def compute_personality_overlap(candidate_personality, job_personality_preferences):
    """Score how well a candidate's personality fits a company's preference.

    job_personality_preferences: dict of {dimension: {pole, importance}}.
    Returns 0..100 overlap score.
    """
    if not job_personality_preferences:
        return 100.0, []
    dims = candidate_personality.get("dimensions", {}) if candidate_personality else {}
    total = 0.0
    weights = 0.0
    matched = []
    for dim_id, pref in job_personality_preferences.items():
        pref_pole = pref.get("pole")
        importance = float(pref.get("importance", 1.0))
        cand = dims.get(dim_id, {})
        cand_pole = cand.get("pole", "left")
        score = cand.get("score", 50)
        if pref_pole is None:
            distance = 0.0
        else:
            # distance from the preferred pole's extreme (0 or 100)
            if pref_pole == "right":
                distance = (100 - score) / 100
            else:
                distance = score / 100
            distance = max(distance, 0.0)
        fit = max(0.0, 1.0 - distance)
        total += fit * importance
        weights += importance
        if fit >= 0.6:
            matched.append(dim_id)
    if weights == 0:
        return 100.0, []
    return round((total / weights) * 100, 2), matched
