"""
MATCHA - Interface language support.

Lightweight, dependency-free translation helper for the Streamlit UI.
The user picks an interface language in the sidebar; that choice is kept
in `st.session_state["lang"]` (default "en"). `tr()` returns the English
text by default and the matching translation for the selected language.

To add another language: register it in `SUPPORTED_LANGUAGES` and extend
the `tr(...)` calls (each takes the English text followed by the German
translation, add further languages in the same order).
"""

import streamlit as st

# Map of supported interface languages (code -> display name in its own language).
SUPPORTED_LANGUAGES = {
    "en": "English",
    "de": "Deutsch",
}

# Fallback language used whenever nothing is stored in the session.
_DEFAULT_LANG = "en"


def get_current_lang() -> str:
    """Return the currently selected interface language code."""
    lang = st.session_state.get("lang")
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return _DEFAULT_LANG


def tr(en_text: str, de_text: str) -> str:
    """Return `de_text` when German is selected, otherwise `en_text`.

    Add further languages by accepting more arguments after `de_text`.
    """
    if get_current_lang() == "de":
        return de_text
    return en_text