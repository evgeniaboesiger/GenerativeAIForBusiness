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
    "review": "Step 6 · Review & Confirm",
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
    st.title("🎯 Career Goals & Preferences")
    st.markdown("---")

    st.info(
        "*Your preferences describe the type of work environment you are looking for. "
        "They are used to improve job recommendations and are not used to assess your "
        "personality or personal worth.*"
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
    st.subheader("Your saved preferences")
    saved = load_preferences(user["id"])
    summary = preferences_summary(saved)

    for label, value in summary:
        st.markdown(f"**{label}:** {value}")

    st.caption(f"Last updated: {saved.get('_updated_at', '')}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ Edit my preferences", type="primary", use_container_width=True):
            st.session_state.pref_working = normalise_preferences(saved)
            st.session_state.pref_wizard_step = "goals"
            st.session_state.pref_editing = True
            st.rerun()
    with col2:
        if st.button("Start over (reset to not stated)", use_container_width=True):
            st.session_state.pref_working = default_preferences()
            st.session_state.pref_wizard_step = "goals"
            st.session_state.pref_editing = True
            st.rerun()


def _show_onboarding_flow(user):
    """The multi-step wizard: Steps 2-6 (Step 1 is the Candidate Profile page)."""
    st.markdown(
        "**Onboarding flow:** ① *Professional Profile (Candidate Profile page)* → "
        "② Career Goals → ③ Work Preferences → ④ Location & Remote → "
        "⑤ Salary & Employment → ⑥ Review & Confirm"
    )
    st.markdown("---")

    if "pref_wizard_step" not in st.session_state:
        st.session_state.pref_wizard_step = "goals"

    step = st.session_state.pref_wizard_step
    st.subheader(STEP_NAMES[step])

    if step == "goals":
        _step_goals()
    elif step == "work_style":
        _step_work_style()
    elif step == "location":
        _step_location()
    elif step == "salary":
        _step_salary()
    elif step == "review":
        _step_review(user)


# ---------------------------------------------------------------------- #
#  Individual wizard steps
# ---------------------------------------------------------------------- #
def _nav_buttons(next_step: str, back_step: str = None):
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if back_step:
            if st.button("← Back", use_container_width=True):
                _persist_widgets()
                st.session_state.pref_wizard_step = back_step
                st.rerun()
    with col2:
        if st.button("Next →", type="primary", use_container_width=True):
            _persist_widgets()
            st.session_state.pref_wizard_step = next_step
            st.rerun()


def _step_goals():
    st.markdown("**What are your main career goals?** *(select all that apply)*")
    selected = st.multiselect(
        "Career goals",
        CAREER_GOAL_OPTIONS,
        default=_working().get("career_goals", []),
        key="pref_goals",
        label_visibility="collapsed",
        help="These help tailor recommendations - a career change is never penalized."
    )
    _set_value("career_goals", selected)

    st.markdown("**Tell us about your career goal.** (optional)")
    goal_text = st.text_area(
        "Career goal (optional)",
        value=_working().get("career_goal_text", ""),
        height=90,
        key="pref_goal_text",
        help="Optional free text. It is only used as context and is never ranked directly.",
    )
    _set_value("career_goal_text", goal_text)
    st.caption("ℹ️ This question is optional.")

    _nav_buttons(next_step="work_style")


def _step_work_style():
    w = _working()
    st.markdown(
        "**How important are the following to you?** *Your work-environment "
        "preferences - not a personality test.*"
    )

    for key, question in WORK_STYLE_ITEMS:
        score = st.slider(
            question, *PREFERENCE_SCALE,
            value=int(w["preference_scores"].get(key, 3)),
            key=f"pref_style_{key}",
        )
        w["preference_scores"][key] = score

    st.markdown("**Do you have a preference for company size?**")
    size = st.selectbox(
        "Company size preference",
        COMPANY_SIZE_OPTIONS,
        index=COMPANY_SIZE_OPTIONS.index(w.get("company_size_preference", "No preference")),
        key="pref_company_size",
    )
    _set_value("company_size_preference", size)

    st.markdown(
        "**How important are the following work values to you?** "
        "*(leave at 3 if not important to you)* covering the type of role you seek."
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
    st.markdown("**Where would you prefer to work?** *(select all that apply)*")
    locations = st.multiselect(
        "Preferred locations",
        SWISS_LOCATIONS,
        default=w.get("preferred_locations", []),
        key="pref_locations",
        help="Location preference is used only for matching; you can choose several cities.",
    )
    _set_value("preferred_locations", locations)

    current_commute = w.get("max_commute_minutes")
    commute_default = "No limit"
    for opt in COMMUTE_OPTIONS:
        if _commute_from_label(opt) == current_commute:
            commute_default = opt
    commute = st.selectbox(
        "Maximum acceptable commute",
        COMMUTE_OPTIONS,
        index=COMMUTE_OPTIONS.index(commute_default),
        key="pref_commute",
    )
    _set_value("max_commute_minutes", _commute_from_label(commute))

    mode = st.selectbox(
        "Preferred commute mode (optional)",
        COMMUTE_MODES,
        index=COMMUTE_MODES.index(w.get("commute_mode", "Flexible")),
        key="pref_commute_mode",
    )
    _set_value("commute_mode", mode)

    relocate = st.radio(
        "Are you willing to relocate for the right position?",
        ["No", "Yes"],
        index=1 if w.get("relocation_willing") else 0,
        horizontal=True,
        key="pref_relocate",
    )
    _set_value("relocation_willing", relocate == "Yes")

    st.markdown("---")
    st.markdown("**What type of work arrangement do you prefer?**")
    remote = st.selectbox(
        "Work arrangement",
        REMOTE_PREFERENCES,
        index=REMOTE_PREFERENCES.index(w.get("remote_preference", "No preference")),
        key="pref_remote",
    )
    _set_value("remote_preference", remote)

    importance = st.slider(
        "How important is remote work to you? (1 = not important, 5 = very important)",
        *PREFERENCE_SCALE,
        value=int(w.get("remote_importance", 3)),
        key="pref_remote_importance",
    )
    _set_value("remote_importance", importance)

    _nav_buttons(next_step="salary", back_step="work_style")


def _step_salary():
    w = _working()
    st.markdown("**What employment level are you looking for?**")
    target_default = w.get("preferred_employment_target")
    target_default_label = "Flexible" if target_default is None else f"{target_default}%"
    target = st.selectbox(
        "Preferred employment level",
        EMPLOYMENT_LEVELS,
        index=EMPLOYMENT_LEVELS.index(target_default_label),
        key="pref_employment_target",
        help="If you are flexible about the level, pick 'Flexible'.",
    )
    _set_value("preferred_employment_target", _pct_from_label(target))

    col_min, col_max = st.columns(2)
    with col_min:
        min_label = _level_label(w.get("preferred_employment_min"))
        pmin = st.selectbox(
            "Acceptable minimum",
            ["Not specified"] + EMPLOYMENT_LEVELS,
            index=(["Not specified"] + EMPLOYMENT_LEVELS).index(min_label),
            key="pref_employment_min",
        )
        _set_value("preferred_employment_min", _pct_from_label(pmin))
    with col_max:
        max_label = _level_label(w.get("preferred_employment_max"))
        pmax = st.selectbox(
            "Acceptable maximum",
            ["Not specified"] + EMPLOYMENT_LEVELS,
            index=(["Not specified"] + EMPLOYMENT_LEVELS).index(max_label),
            key="pref_employment_max",
        )
        _set_value("preferred_employment_max", _pct_from_label(pmax))

    st.markdown("---")
    st.markdown("**What salary range are you looking for?**")

    flexible = st.checkbox(
        "Flexible / open to discussion",
        value=bool(w.get("salary_flexible", False)),
        key="pref_salary_flexible",
        help="If checked, salary is a soft signal only and never blocks a recommendation.",
    )
    _set_value("salary_flexible", flexible)

    col_curr, col_period = st.columns(2)
    with col_curr:
        currency = st.selectbox(
            "Currency",
            SALARY_CURRENCIES,
            index=SALARY_CURRENCIES.index(w.get("salary_currency", "CHF")),
            key="pref_salary_currency",
        )
        _set_value("salary_currency", currency)
    with col_period:
        period = st.selectbox(
            "Salary period",
            SALARY_PERIODS,
            index=SALARY_PERIODS.index(w.get("salary_period", "yearly")),
            key="pref_salary_period",
        )
        _set_value("salary_period", period)

    col1, col2 = st.columns(2)
    with col1:
        min_salary = st.number_input(
            f"Minimum annual salary ({currency})",
            min_value=0, max_value=600000, step=5000,
            value=int(w.get("salary_min") or 0),
            key="pref_salary_min",
            help="Optional. Leave at 0 if you do not want to state a minimum.",
        )
        _set_value("salary_min", int(min_salary) if min_salary > 0 else None)
    with col2:
        pref_salary = st.number_input(
            f"Preferred annual salary ({currency})",
            min_value=0, max_value=600000, step=5000,
            value=int(w.get("salary_preferred") or 0),
            key="pref_salary_pref",
            help="Optional.",
        )
        _set_value("salary_preferred", int(pref_salary) if pref_salary > 0 else None)

    st.markdown("---")
    st.markdown("**Working language** *(the language you prefer to work in - "
                "this is separate from your language proficiency)*")
    langs = st.multiselect(
        "Preferred working language(s)",
        WORKING_LANGUAGE_OPTIONS,
        default=w.get("preferred_working_languages", []),
        key="pref_langs",
    )
    _set_value("preferred_working_languages", langs)

    st.markdown("**When could you start a new position?**")
    availability_default = w.get("availability")
    availability = st.selectbox(
        "Availability",
        AVAILABILITY_OPTIONS,
        index=AVAILABILITY_OPTIONS.index(availability_default) if availability_default in AVAILABILITY_OPTIONS else 0,
        key="pref_availability",
    )
    _set_value("availability", availability)

    _nav_buttons(next_step="review", back_step="location")


def _step_review(user):
    """Step 6: show the summary and require explicit confirmation before saving."""
    w = _working()
    st.markdown("**Review your preferences before saving**")
    summary = preferences_summary(w)
    for label, value in summary:
        st.markdown(f"- **{label}:** {value}")

    st.markdown("---")
    consent = st.checkbox(
        "I confirm these are my explicit employment preferences. "
        "I understand they are used only to improve job recommendations "
        "and not to assess my personality or personal worth."
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("← Back", use_container_width=True):
            _persist_widgets()
            st.session_state.pref_wizard_step = "salary"
            st.rerun()
    with col2:
        if st.button("💾 Confirm & Save", type="primary", use_container_width=True, disabled=not consent):
            st.session_state.pref_working = normalise_preferences(w)
            saved = st.session_state.pref_working
            save_preferences(user["id"], saved)
            st.session_state.current_preferences = dict(saved)
            st.session_state.pref_editing = False
            st.session_state.pref_wizard_step = "goals"
            st.success("✅ Your preferences were saved securely (encrypted).")
            st.info("Go to **Job Matching** to see recommendations that consider these preferences.")
            st.button("Continue", use_container_width=True, on_click=lambda: st.rerun())

    st.markdown("---")
    st.caption(
        "🔒 Privacy: preference data is encrypted before storage, kept separate from your "
        "professional profile, and only used for employment matching. Questions marked "
        "optional collect nothing beyond what improves recommendations."
    )