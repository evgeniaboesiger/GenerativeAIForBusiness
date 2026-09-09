"""
MATCHA - Career Goals & Work Preferences onboarding wizard.

Collects EXPLICIT, job-relevant employment preferences from the candidate
(never a personality test). The candidate sees a summary before saving and
can edit preferences at any time.

Ethical contract (displayed to the candidate):
  Preferences describe the type of work environment the candidate is looking
  for. They are used only to improve job recommendations and are never used
  to assess personality or personal worth.
"""

import streamlit as st

from db import load_preferences, save_preferences
from i18n import tr
from preferences import (
    AVAILABILITY_OPTIONS,
    CAREER_GOAL_OPTIONS,
    COMPANY_SIZE_OPTIONS,
    COMMUTE_MODES,
    COMMUTE_OPTIONS,
    EMPLOYMENT_LEVELS,
    PREFERENCE_SCALE,
    REMOTE_PREFERENCES,
    SALARY_CURRENCIES,
    SALARY_PERIODS,
    SWISS_LOCATIONS,
    WORK_STYLE_ITEMS,
    WORK_VALUE_ITEMS,
    default_preferences,
    normalise_preferences,
    preferences_summary,
)

WORKING_LANGUAGE_OPTIONS = ["German", "English", "French", "Italian", "Other"]

STEP_NAMES = {
    "goals": "Step 2 · Career Goals",
    "work_style": "Step 3 · Work Preferences",
    "location": "Step 4 · Location & Remote Work",
    "salary": "Step 5 · Salary & Employment",
    "tiers": "Step 6 · Set Your Deal-Breakers",
    "review": "Step 7 · Review & Confirm",
}

STEP_NAMES_DE = {
    "goals": "Schritt 2 · Karriereziele",
    "work_style": "Schritt 3 · Arbeitspräferenzen",
    "location": "Schritt 4 · Standort & Remote-Arbeit",
    "salary": "Schritt 5 · Gehalt & Anstellung",
    "tiers": "Schritt 6 · Ihre Ausschlusskriterien festlegen",
    "review": "Schritt 7 · Prüfen & Bestätigen",
}


def _working() -> dict:
    """Session-scoped working copy of the preferences being edited."""
    if "pref_working" not in st.session_state:
        st.session_state.pref_working = default_preferences()
    return st.session_state.pref_working


def _level_label(value) -> str:
    if value is None:
        return "Not specified"
    return f"{value}%"


def _pct_from_label(label: str):
    if not label or label in ("Not specified", "Flexible"):
        return None
    return int(label.replace("%", ""))


def _commute_from_label(label: str):
    if not label or label in ("No limit", "Flexible"):
        return None
    return int(label.replace("Up to ", "").replace(" minutes", ""))


def _set_value(key, value):
    st.session_state.pref_working[key] = value


def _persist_widgets():
    """Store current widget values into the working copy (called on Next/Review)."""
    w = _working()
    w = normalise_preferences(w)
    st.session_state.pref_working = w


def get_active_preferences():
    """
    Return the candidate's preferences for matching: session value first,
    otherwise the stored (encrypted) value. Returns None when none exist.
    """
    if st.session_state.get("current_preferences"):
        prefs = dict(st.session_state.current_preferences)
        prefs.pop("_updated_at", None)
        return prefs

    user = st.session_state.user
    if user:
        saved = load_preferences(user["id"])
        if saved:
            st.session_state.current_preferences = dict(saved)
            prefs = dict(saved)
            prefs.pop("_updated_at", None)
            return prefs
    return None


def show_preferences_page():
    """Main entry point for the Career Goals & Preferences page."""
    st.title(tr("🎯 Career Goals & Preferences", "🎯 Karriereziele & Präferenzen"))
    st.markdown("---")

    st.info(
        tr("*Your preferences describe the type of work environment you are looking for. "
           "They are used to improve job recommendations and are not used to assess your "
           "personality or personal worth.*",
           "*Ihre Präferenzen beschreiben die Art von Arbeitsumfeld, das Sie suchen. "
           "Sie dienen dazu, Job-Empfehlungen zu verbessern, und bewerten nicht Ihre "
           "Persönlichkeit oder Ihren persönlichen Wert.*")
    )

    user = st.session_state.user
    has_saved = False
    if user:
        has_saved = load_preferences(user["id"]) is not None

    if has_saved and not st.session_state.get("pref_editing", False):
        _show_saved_section(user)
        return

    _show_onboarding_flow(user)


def _show_saved_section(user):
    """Show currently saved preferences with review/edit/start-over options."""
    st.subheader(tr("Your saved preferences", "Ihre gespeicherten Präferenzen"))
    saved = load_preferences(user["id"])
    summary = preferences_summary(saved)

    for label, value in summary:
        st.markdown(f"**{label}:** {value}")

    st.caption(tr("Last updated: {}", "Zuletzt aktualisiert: {}").format(saved.get('_updated_at', '')))

    col1, col2 = st.columns(2)
    with col1:
        if st.button(tr("✏️ Edit my preferences", "✏️ Präferenzen bearbeiten"), type="primary", use_container_width=True):
            st.session_state.pref_working = normalise_preferences(saved)
            st.session_state.pref_wizard_step = "goals"
            st.session_state.pref_editing = True
            st.rerun()
    with col2:
        if st.button(tr("Start over (reset to not stated)", "Neu beginnen (auf nicht angegeben zurücksetzen)"), use_container_width=True):
            st.session_state.pref_working = default_preferences()
            st.session_state.pref_wizard_step = "goals"
            st.session_state.pref_editing = True
            st.rerun()


def _show_onboarding_flow(user):
    """The multi-step wizard: Steps 2-6 (Step 1 is the Candidate Profile page)."""
    st.markdown(tr(
        "**Onboarding flow:** ① *Professional Profile (Candidate Profile page)* → "
        "② Career Goals → ③ Work Preferences → ④ Location & Remote → "
        "⑤ Salary & Employment → ⑥ Set Your Deal-Breakers → ⑦ Review & Confirm",
        "**Onboarding-Ablauf:** ① *Berufliches Profil (Seite Kandidatenprofil)* → "
        "② Karriereziele → ③ Arbeitspräferenzen → ④ Standort & Remote → "
        "⑤ Gehalt & Anstellung → ⑥ Ausschlusskriterien festlegen → ⑦ Prüfen & Bestätigen"
    ))
    st.markdown("---")

    if "pref_wizard_step" not in st.session_state:
        st.session_state.pref_wizard_step = "goals"

    step = st.session_state.pref_wizard_step
    st.subheader(tr(STEP_NAMES[step], STEP_NAMES_DE[step]))

    if step == "goals":
        _step_goals()
    elif step == "work_style":
        _step_work_style()
    elif step == "location":
        _step_location()
    elif step == "salary":
        _step_salary()
    elif step == "tiers":
        _step_tiers()
    elif step == "review":
        _step_review(user)


# ---------------------------------------------------------------------- #
#  Individual wizard steps
# ---------------------------------------------------------------------- #
def _nav_buttons(next_step: str, back_step: str = None):
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if back_step:
            if st.button(tr("← Back", "← Zurück"), use_container_width=True):
                _persist_widgets()
                st.session_state.pref_wizard_step = back_step
                st.rerun()
    with col2:
        if st.button(tr("Next →", "Weiter →"), type="primary", use_container_width=True):
            _persist_widgets()
            st.session_state.pref_wizard_step = next_step
            st.rerun()


def _step_goals():
    st.markdown(tr("**What are your main career goals?** *(select all that apply)*",
                   "**Was sind Ihre wichtigsten Karriereziele?** *(alle zutreffenden auswählen)*"))
    selected = st.multiselect(
        tr("Career goals", "Karriereziele"),
        CAREER_GOAL_OPTIONS,
        default=_working().get("career_goals", []),
        key="pref_goals",
        label_visibility="collapsed",
        help=tr("These help tailor recommendations - a career change is never penalized.",
                "Diese helfen, Empfehlungen anzupassen - ein Karrierewechsel wird nie bestraft.")
    )
    _set_value("career_goals", selected)

    st.markdown(tr("**Tell us about your career goal.** (optional)", "**Erzählen Sie uns etwas zu Ihrem Karriereziel.** (optional)"))
    goal_text = st.text_area(
        tr("Career goal (optional)", "Karriereziel (optional)"),
        value=_working().get("career_goal_text", ""),
        height=90,
        key="pref_goal_text",
        help=tr("Optional free text. It is only used as context and is never ranked directly.",
                "Optionaler Freitext. Er wird nur als Kontext verwendet und nie direkt bewertet."),
    )
    _set_value("career_goal_text", goal_text)
    st.caption(tr("ℹ️ This question is optional.", "ℹ️ Diese Frage ist optional."))

    _nav_buttons(next_step="work_style")


def _step_work_style():
    w = _working()
    st.markdown(
        tr("**How important are the following to you?** *Your work-environment "
           "preferences - not a personality test.*",
           "**Wie wichtig sind Ihnen die folgenden Punkte?** *Ihre Arbeitsumfeld-"
           "Präferenzen - kein Persönlichkeitstest.*")
    )

    for key, question in WORK_STYLE_ITEMS:
        score = st.slider(
            question, *PREFERENCE_SCALE,
            value=int(w["preference_scores"].get(key, 3)),
            key=f"pref_style_{key}",
        )
        w["preference_scores"][key] = score

    st.markdown(tr("**Do you have a preference for company size?**", "**Haben Sie eine Präferenz für die Unternehmensgröße?**"))
    size = st.selectbox(
        tr("Company size preference", "Präferenz Unternehmensgröße"),
        COMPANY_SIZE_OPTIONS,
        index=COMPANY_SIZE_OPTIONS.index(w.get("company_size_preference", "No preference")),
        key="pref_company_size",
    )
    _set_value("company_size_preference", size)

    st.markdown(
        tr("**How important are the following work values to you?** "
           "*(leave at 3 if not important to you)* covering the type of role you seek.",
           "**Wie wichtig sind Ihnen die folgenden Arbeitswerte?** "
           "*(bei 3 lassen, wenn sie Ihnen nicht wichtig sind)* bezogen auf die Art von Rolle, die Sie suchen.")
    )
    cols = st.columns(2)
    for i, (key, label) in enumerate(WORK_VALUE_ITEMS):
        with cols[i % 2]:
            score = st.slider(
                label, *PREFERENCE_SCALE,
                value=int(w["work_values"].get(key, 3)),
                key=f"pref_value_{key}",
            )
            w["work_values"][key] = score

    _nav_buttons(next_step="location", back_step="goals")


def _step_location():
    w = _working()
    st.markdown(tr("**Where would you prefer to work?** *(select all that apply)*",
                   "**Wo möchten Sie bevorzugt arbeiten?** *(alle zutreffenden auswählen)*"))
    locations = st.multiselect(
        tr("Preferred locations", "Bevorzugte Standorte"),
        SWISS_LOCATIONS,
        default=w.get("preferred_locations", []),
        key="pref_locations",
        help=tr("Location preference is used only for matching; you can choose several cities.",
                "Die Standortpräferenz wird nur für das Matching verwendet; Sie können mehrere Städte wählen."),
    )
    _set_value("preferred_locations", locations)

    current_commute = w.get("max_commute_minutes")
    commute_default = "No limit"
    for opt in COMMUTE_OPTIONS:
        if _commute_from_label(opt) == current_commute:
            commute_default = opt
    commute = st.selectbox(
        tr("Maximum acceptable commute", "Maximale akzeptable Pendelzeit"),
        COMMUTE_OPTIONS,
        index=COMMUTE_OPTIONS.index(commute_default),
        key="pref_commute",
    )
    _set_value("max_commute_minutes", _commute_from_label(commute))

    mode = st.selectbox(
        tr("Preferred commute mode (optional)", "Bevorzugtes Verkehrsmittel (optional)"),
        COMMUTE_MODES,
        index=COMMUTE_MODES.index(w.get("commute_mode", "Flexible")),
        key="pref_commute_mode",
    )
    _set_value("commute_mode", mode)

    relocate = st.radio(
        tr("Are you willing to relocate for the right position?", "Wären Sie bereit, für die richtige Stelle umzuziehen?"),
        [tr("No", "Nein"), tr("Yes", "Ja")],
        index=1 if w.get("relocation_willing") else 0,
        horizontal=True,
        key="pref_relocate",
    )
    _set_value("relocation_willing", relocate == tr("Yes", "Ja"))

    st.markdown("---")
    st.markdown(tr("**What type of work arrangement do you prefer?**", "**Welche Arbeitsform bevorzugen Sie?**"))
    remote = st.selectbox(
        tr("Work arrangement", "Arbeitsform"),
        REMOTE_PREFERENCES,
        index=REMOTE_PREFERENCES.index(w.get("remote_preference", "No preference")),
        key="pref_remote",
    )
    _set_value("remote_preference", remote)

    importance = st.slider(
        tr("How important is remote work to you? (1 = not important, 5 = very important)",
           "Wie wichtig ist Ihnen Remote-Arbeit? (1 = nicht wichtig, 5 = sehr wichtig)"),
        *PREFERENCE_SCALE,
        value=int(w.get("remote_importance", 3)),
        key="pref_remote_importance",
    )
    _set_value("remote_importance", importance)

    _nav_buttons(next_step="salary", back_step="work_style")


def _step_salary():
    w = _working()
    st.markdown(tr("**What employment level are you looking for?**", "**Welches Anstellungsniveau suchen Sie?**"))
    target_default = w.get("preferred_employment_target")
    target_default_label = "Flexible" if target_default is None else f"{target_default}%"
    target = st.selectbox(
        tr("Preferred employment level", "Bevorzugtes Anstellungsniveau"),
        EMPLOYMENT_LEVELS,
        index=EMPLOYMENT_LEVELS.index(target_default_label),
        key="pref_employment_target",
        help=tr("If you are flexible about the level, pick 'Flexible'.",
                "Wenn Ihnen das Niveau nicht wichtig ist, wählen Sie 'Flexible'."),
    )
    _set_value("preferred_employment_target", _pct_from_label(target))

    col_min, col_max = st.columns(2)
    with col_min:
        min_label = _level_label(w.get("preferred_employment_min"))
        pmin = st.selectbox(
            tr("Acceptable minimum", "Akzeptables Minimum"),
            ["Not specified"] + EMPLOYMENT_LEVELS,
            index=(["Not specified"] + EMPLOYMENT_LEVELS).index(min_label),
            key="pref_employment_min",
        )
        _set_value("preferred_employment_min", _pct_from_label(pmin))
    with col_max:
        max_label = _level_label(w.get("preferred_employment_max"))
        pmax = st.selectbox(
            tr("Acceptable maximum", "Akzeptables Maximum"),
            ["Not specified"] + EMPLOYMENT_LEVELS,
            index=(["Not specified"] + EMPLOYMENT_LEVELS).index(max_label),
            key="pref_employment_max",
        )
        _set_value("preferred_employment_max", _pct_from_label(pmax))

    st.markdown("---")
    st.markdown(tr("**What salary range are you looking for?**", "**Welche Gehaltsspanne suchen Sie?**"))

    flexible = st.checkbox(
        tr("Flexible / open to discussion", "Flexibel / verhandelbar"),
        value=bool(w.get("salary_flexible", False)),
        key="pref_salary_flexible",
        help=tr("If checked, salary is a soft signal only and never blocks a recommendation.",
                "Wenn aktiviert, ist das Gehalt nur ein weiches Signal und blockiert nie eine Empfehlung."),
    )
    _set_value("salary_flexible", flexible)

    col_curr, col_period = st.columns(2)
    with col_curr:
        currency = st.selectbox(
            tr("Currency", "Währung"),
            SALARY_CURRENCIES,
            index=SALARY_CURRENCIES.index(w.get("salary_currency", "CHF")),
            key="pref_salary_currency",
        )
        _set_value("salary_currency", currency)
    with col_period:
        period = st.selectbox(
            tr("Salary period", "Gehaltsperiode"),
            SALARY_PERIODS,
            index=SALARY_PERIODS.index(w.get("salary_period", "yearly")),
            key="pref_salary_period",
        )
        _set_value("salary_period", period)

    col1, col2 = st.columns(2)
    with col1:
        min_salary = st.number_input(
            tr("Minimum annual salary ({})", "Mindestjahresgehalt ({})").format(currency),
            min_value=0, max_value=600000, step=5000,
            value=int(w.get("salary_min") or 0),
            key="pref_salary_min",
            help=tr("Optional. Leave at 0 if you do not want to state a minimum.",
                    "Optional. Bei 0 lassen, wenn Sie kein Minimum angeben möchten."),
        )
        _set_value("salary_min", int(min_salary) if min_salary > 0 else None)
    with col2:
        pref_salary = st.number_input(
            tr("Preferred annual salary ({})", "Bevorzugtes Jahresgehalt ({})").format(currency),
            min_value=0, max_value=600000, step=5000,
            value=int(w.get("salary_preferred") or 0),
            key="pref_salary_pref",
            help=tr("Optional.", "Optional."),
        )
        _set_value("salary_preferred", int(pref_salary) if pref_salary > 0 else None)

    st.markdown("---")
    st.markdown(tr("**Working language** *(the language you prefer to work in - "
                   "this is separate from your language proficiency)*",
                   "**Arbeitssprache** *(die Sprache, in der Sie bevorzugt arbeiten - "
                   "getrennt von Ihren Sprachkenntnissen)*"))
    langs = st.multiselect(
        tr("Preferred working language(s)", "Bevorzugte Arbeitssprache(n)"),
        WORKING_LANGUAGE_OPTIONS,
        default=w.get("preferred_working_languages", []),
        key="pref_langs",
    )
    _set_value("preferred_working_languages", langs)

    st.markdown(tr("**When could you start a new position?**", "**Ab wann könnten Sie eine neue Stelle antreten?**"))
    availability_default = w.get("availability")
    availability = st.selectbox(
        tr("Availability", "Verfügbarkeit"),
        AVAILABILITY_OPTIONS,
        index=AVAILABILITY_OPTIONS.index(availability_default) if availability_default in AVAILABILITY_OPTIONS else 0,
        key="pref_availability",
    )
    _set_value("availability", availability)

    _nav_buttons(next_step="tiers", back_step="location")


# ---------------------------------------------------------------------- #
#  Tiered preferences step (Ideal / Acceptable / Deal-breaker)
# ---------------------------------------------------------------------- #
def _tier_dim(dim: str):
    """Current tier value for a dimension, or None when not set."""
    t = (_working().get("preference_tiers") or {}).get(dim)
    return t if isinstance(t, dict) else None


def _set_tier_dim(dim: str, value):
    """Store (or clear) one tier dimension in the working copy."""
    w = _working()
    tiers = dict(w.get("preference_tiers") or {})
    if value:
        tiers[dim] = value
    else:
        tiers.pop(dim, None)
    w["preference_tiers"] = tiers or None


def _emp_label(v) -> str:
    return "Flexible" if v is None else f"{v}%"


def _step_tiers():
    st.markdown(tr(
        "**Optionally set your deal-breakers for each dimension.** For every "
        "factor below you can define an *ideal* range, an *acceptable* range, "
        "and what is a hard *deal-breaker*. Jobs that violate a deal-breaker "
        "are not recommended to you.",
        "**Optional: Legen Sie Ihre Ausschlusskriterien für jede Dimension fest.** "
        "Für jeden Faktor unten können Sie einen *idealen* Bereich, einen "
        "*akzeptablen* Bereich und ein hartes *Ausschlusskriterium* definieren. "
        "Jobs, die ein Ausschlusskriterium verletzen, werden Ihnen nicht empfohlen.")
    )
    st.caption(tr("All options are optional - leave a dimension off and it will not restrict your matches.",
                  "Alle Angaben sind optional - lassen Sie eine Dimension weg, schränkt sie Ihre Matches nicht ein."))
    st.markdown("---")

    # 1) Workload (employment percentage)
    key_prefix = "tiers_emp"
    on = st.checkbox(
        tr("⚖️ Set workload (employment percentage) tiers", "⚖️ Arbeitszeit (Anstellungsgrad) festlegen"),
        value=bool(_tier_dim("employment_percentage")),
        key=key_prefix + "_on",
    )
    if on:
        existing = _tier_dim("employment_percentage") or {
            "ideal": [80, 100], "acceptable": [60, 100], "deal_breaker": [50, 100]}
        col_ideal, col_acc, col_db = st.columns(3)
        tiers_out = {}
        for label, col, tier_name, default in [
            (tr("Ideal", "Ideal"), col_ideal, "ideal", existing.get("ideal", [80, 100])),
            (tr("Acceptable", "Akzeptabel"), col_acc, "acceptable", existing.get("acceptable", [60, 100])),
            (tr("Deal-breaker (outside this range)", "Ausschlusskriterium (außerhalb dieses Bereichs)"), col_db, "deal_breaker", existing.get("deal_breaker", [50, 100])),
        ]:
            with col:
                st.markdown(f"**{label}**")
                lo_lbl = _emp_label(default[0])
                hi_lbl = _emp_label(default[1])
                lo_idx = EMPLOYMENT_LEVELS.index(lo_lbl) if lo_lbl in EMPLOYMENT_LEVELS else 0
                hi_idx = EMPLOYMENT_LEVELS.index(hi_lbl) if hi_lbl in EMPLOYMENT_LEVELS else len(EMPLOYMENT_LEVELS) - 1
                lo = st.selectbox(tr("min", "min"), EMPLOYMENT_LEVELS, index=lo_idx, key=f"{key_prefix}_{tier_name}_lo")
                hi = st.selectbox(tr("max", "max"), EMPLOYMENT_LEVELS, index=hi_idx, key=f"{key_prefix}_{tier_name}_hi")
                lo_v, hi_v = _pct_from_label(lo), _pct_from_label(hi)
                if lo_v is not None and hi_v is not None and lo_v <= hi_v:
                    tiers_out[tier_name] = [lo_v, hi_v]
        _set_tier_dim("employment_percentage", tiers_out if len(tiers_out) == 3 else None)
    else:
        _set_tier_dim("employment_percentage", None)

    st.markdown("---")

    # 2) Salary (annual, CHF)
    key_prefix = "tiers_sal"
    on = st.checkbox(
        tr("💰 Set salary tiers (CHF, annual)", "💰 Gehalt festlegen (CHF, jährlich)"),
        value=bool(_tier_dim("salary")),
        key=key_prefix + "_on",
    )
    if on:
        existing = _tier_dim("salary") or {
            "ideal": [90000, 120000], "acceptable": [80000, 130000], "deal_breaker": [70000, 150000]}
        col_ideal, col_acc, col_db = st.columns(3)
        tiers_out = {}
        for label, col, tier_name, default in [
            (tr("Ideal", "Ideal"), col_ideal, "ideal", existing.get("ideal", [90000, 120000])),
            (tr("Acceptable", "Akzeptabel"), col_acc, "acceptable", existing.get("acceptable", [80000, 130000])),
            (tr("Minimum you need", "Ihr Mindestgehalt"), col_db, "deal_breaker", existing.get("deal_breaker", [70000, 150000])),
        ]:
            with col:
                st.markdown(f"**{label}**")
                lo = st.number_input(tr("min", "min"), min_value=0, max_value=1000000, step=5000,
                                     value=int(default[0]), key=f"{key_prefix}_{tier_name}_lo")
                hi = st.number_input(tr("max", "max"), min_value=0, max_value=1000000, step=5000,
                                     value=int(default[1]), key=f"{key_prefix}_{tier_name}_hi")
                if lo <= hi:
                    tiers_out[tier_name] = [lo, hi]
        _set_tier_dim("salary", tiers_out if len(tiers_out) == 3 else None)
    else:
        _set_tier_dim("salary", None)

    st.markdown("---")

    # 3) Commute
    key_prefix = "tiers_comm"
    on = st.checkbox(
        tr("🚆 Set commute tiers", "🚆 Pendelzeit festlegen"),
        value=bool(_tier_dim("commute")),
        key=key_prefix + "_on",
    )
    if on:
        existing = _tier_dim("commute") or {
            "ideal_max_minutes": 30, "acceptable_max_minutes": 45, "deal_breaker_max_minutes": 60}
        col_ideal, col_acc, col_db = st.columns(3)
        tiers_out = {}
        for label, col, tier_name, default in [
            (tr("Ideal", "Ideal"), col_ideal, "ideal_max_minutes", existing.get("ideal_max_minutes", 30)),
            (tr("Acceptable", "Akzeptabel"), col_acc, "acceptable_max_minutes", existing.get("acceptable_max_minutes", 45)),
            (tr("Deal-breaker (max)", "Ausschlusskriterium (max)"), col_db, "deal_breaker_max_minutes", existing.get("deal_breaker_max_minutes", 60)),
        ]:
            with col:
                st.markdown(f"**{label}**")
                pct = st.number_input(tr("minutes", "Minuten"), min_value=5, max_value=180, step=5,
                                      value=int(default), key=f"{key_prefix}_{tier_name}")
                tiers_out[tier_name] = int(pct)
        _set_tier_dim("commute", tiers_out if len(tiers_out) == 3 else None)
    else:
        _set_tier_dim("commute", None)

    st.markdown("---")

    # 4) Remote work
    key_prefix = "tiers_rem"
    on = st.checkbox(
        tr("🏠 Set remote-work tiers", "🏠 Remote-Arbeit festlegen"),
        value=bool(_tier_dim("remote")),
        key=key_prefix + "_on",
    )
    REMOTE_TIER_OPTS = [tr("Remote", "Remote"), tr("Hybrid", "Hybrid"), tr("Office", "Präsenz")]
    REMOTE_OPT_TO_LEVEL = {o: lvl for o, lvl in zip(REMOTE_TIER_OPTS, ("remote", "hybrid", "office"))}
    REMOTE_LEVEL_TO_OPT = {lvl: o for o, lvl in REMOTE_OPT_TO_LEVEL.items()}
    if on:
        existing = _tier_dim("remote") or {
            "ideal": ["remote"], "acceptable": ["remote", "hybrid"], "deal_breaker": ["office"]}
        col_ideal, col_acc, col_db = st.columns(3)
        tiers_out = {}
        for label, col, tier_name, default in [
            (tr("Ideal", "Ideal"), col_ideal, "ideal", existing.get("ideal", ["remote"])),
            (tr("Acceptable", "Akzeptabel"), col_acc, "acceptable", existing.get("acceptable", ["remote", "hybrid"])),
            (tr("Deal-breaker", "Ausschlusskriterium"), col_db, "deal_breaker", existing.get("deal_breaker", ["office"])),
        ]:
            with col:
                st.markdown(f"**{label}**")
                default_opts = [REMOTE_LEVEL_TO_OPT[lvl] for lvl in default if lvl in REMOTE_LEVEL_TO_OPT]
                sel = st.multiselect(tr("arrangement", "Arbeitsform"), REMOTE_TIER_OPTS,
                                     default=default_opts, key=f"{key_prefix}_{tier_name}")
                levels = [REMOTE_OPT_TO_LEVEL[o] for o in sel if o in REMOTE_OPT_TO_LEVEL]
                if levels:
                    tiers_out[tier_name] = levels
        _set_tier_dim("remote", tiers_out if len(tiers_out) == 3 else None)
    else:
        _set_tier_dim("remote", None)

    st.markdown("---")

    # 5) Weekend / on-call
    key_prefix = "tiers_wk"
    on = st.checkbox(
        tr("🗓️ Set weekend / on-call work deal-breaker", "🗓️ Wochenend-/Bereitschaftsarbeit festlegen"),
        value=bool(_tier_dim("weekend")),
        key=key_prefix + "_on",
    )
    if on:
        existing = _tier_dim("weekend") or {"ideal": False, "acceptable": True, "deal_breaker": True}
        avoid = st.radio(
            tr("Do you prefer to avoid weekend or on-call work?",
               "Möchten Sie Wochenend- oder Bereitschaftsarbeit vermeiden?"),
            [tr("No preference", "Keine Präferenz"), tr("I prefer to avoid it", "Ich möchte es vermeiden")],
            index=1 if existing.get("ideal") else 0,
            key=key_prefix + "_avoid",
        )
        db_breaker = st.checkbox(
            tr("Weekend or on-call work is a deal-breaker for me (I would reject such roles)",
               "Wochenend- oder Bereitschaftsarbeit ist für mich ein Ausschlusskriterium (solche Rollen lehne ich ab)"),
            value=bool(existing.get("deal_breaker", True)),
            key=key_prefix + "_db",
        )
        _set_tier_dim("weekend", {
            "ideal": avoid == tr("I prefer to avoid it", "Ich möchte es vermeiden"),
            "acceptable": True,
            "deal_breaker": db_breaker,
        })
    else:
        _set_tier_dim("weekend", None)

    st.markdown("---")
    _nav_buttons(next_step="review", back_step="salary")


def _step_review(user):
    """Step 6: show the summary and require explicit confirmation before saving."""
    w = _working()
    st.markdown(tr("**Review your preferences before saving**", "**Prüfen Sie Ihre Präferenzen vor dem Speichern**"))
    summary = preferences_summary(w)
    for label, value in summary:
        st.markdown(f"- **{label}:** {value}")

    st.markdown("---")
    consent = st.checkbox(
        tr("I confirm these are my explicit employment preferences. "
           "I understand they are used only to improve job recommendations "
           "and not to assess my personality or personal worth.",
           "Ich bestätige, dass dies meine ausdrücklichen Beschäftigungspräferenzen sind. "
           "Ich verstehe, dass sie nur zur Verbesserung von Job-Empfehlungen verwendet werden "
           "und nicht zur Bewertung meiner Persönlichkeit oder meines persönlichen Werts.")
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button(tr("← Back", "← Zurück"), use_container_width=True):
            _persist_widgets()
            st.session_state.pref_wizard_step = "tiers"
            st.rerun()
    with col2:
        if st.button(tr("💾 Confirm & Save", "💾 Bestätigen & Speichern"), type="primary", use_container_width=True, disabled=not consent):
            st.session_state.pref_working = normalise_preferences(w)
            saved = st.session_state.pref_working
            save_preferences(user["id"], saved)
            st.session_state.current_preferences = dict(saved)
            st.session_state.pref_editing = False
            st.session_state.pref_wizard_step = "goals"
            st.success(tr("✅ Your preferences were saved securely (encrypted).", "✅ Ihre Präferenzen wurden sicher (verschlüsselt) gespeichert."))
            st.info(tr("Go to **Job Matching** to see recommendations that consider these preferences.",
                       "Gehen Sie zu **Job-Matching**, um Empfehlungen zu sehen, die diese Präferenzen berücksichtigen."))
            st.button(tr("Continue", "Weiter"), use_container_width=True, on_click=lambda: st.rerun())

    st.markdown("---")
    st.caption(
        tr("🔒 Privacy: preference data is encrypted before storage, kept separate from your "
           "professional profile, and only used for employment matching. Questions marked "
           "optional collect nothing beyond what improves recommendations.",
           "🔒 Datenschutz: Präferenzdaten werden vor der Speicherung verschlüsselt, getrennt von "
           "Ihrem beruflichen Profil gehalten und nur für das Arbeits-Matching verwendet. Fragen, "
           "die als optional markiert sind, erfassen nur, was Empfehlungen verbessert.")
    )