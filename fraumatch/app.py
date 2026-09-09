"""
MATCHA - Swiss Employment Matching Platform
A university proof-of-concept demonstrating AI-powered job matching

This is the main Streamlit application that ties together all three agents.
"""

import streamlit as st
import json
import os
import sys
import copy

# Add the agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))

from profile_agent import ProfileAgent
from matching_agent import MatchingAgent
from application_agent import ApplicationAgent
from db import (
    register_user, login_user, update_user_name, save_profile, load_profile,
    save_submitted_application, load_submitted_applications,
    init_session, get_connection, load_preferences, save_preferences
)
from telemetry import summary as telemetry_summary

# Interface language support (English default, German available)
from i18n import SUPPORTED_LANGUAGES, tr

# Career Goals & Work Preferences onboarding wizard
from preferences_ui import show_preferences_page, get_active_preferences

# Candidate assessment: areas to improve (professional + administrative)
from assessment import RecommendationEngine

# CV text extraction (PDF / Word / TXT) lives in document_tools - a fast tool
# used by the Profile Agent, with an OCR fallback for scanned / image PDFs.

# Page configuration
st.set_page_config(
    page_title="MATCHA - Smart Job Matching",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load sample data
@st.cache_data
def load_sample_cvs():
    """Load sample CVs from JSON file."""
    try:
        filepath = os.path.join(os.path.dirname(__file__), "data", "sample_cvs.json")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@st.cache_data
def load_sample_jobs():
    """Load sample jobs from JSON file."""
    try:
        filepath = os.path.join(os.path.dirname(__file__), "data", "sample_jobs.json")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def check_ollama_connection():
    """Check if Ollama is running."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        return response.status_code == 200
    except:
        return False


# --- Page titles (used for both navigation and routing) ------------------- #
# Keys stay language-independent; labels are translated per active language. #
PAGE_KEYS = ["dashboard", "profile", "career_goals", "matching", "assessment", "application", "account"]


def page_label(key: str) -> str:
    """Return the (translated) sidebar label for a page key."""
    labels = {
        "dashboard": tr("🏠 Dashboard", "🏠 Übersicht"),
        "profile": tr("👤 Candidate Profile", "👤 Kandidatenprofil"),
        "career_goals": tr("🎯 Career Goals", "🎯 Karriereziele"),
        "matching": tr("🎯 Job Matching", "🎯 Job-Matching"),
        "assessment": tr("📈 Areas to Improve", "📈 Verbesserungsbereiche"),
        "application": tr("📝 Application Agent", "📝 Bewerbungsassistent"),
        "account": tr("🔐 My Account", "🔐 Mein Konto"),
    }
    return labels[key]


def main():
    """Main application entry point."""
    init_session()

    # Honour a pending navigation request from the Dashboard shortcuts.
    # Must happen before the sidebar radio widget is instantiated.
    pending_page = st.session_state.pop("_open_page", None)
    if pending_page is not None:
        st.session_state.nav_page = pending_page

    # Sidebar - navigation
    st.sidebar.title("🤝 MATCHA")
    st.sidebar.markdown(tr("*Smart Job Matching for Women in Switzerland*",
                           "*Smartes Job-Matching für Frauen in der Schweiz*"))
    lang = st.sidebar.radio(
        tr("Language", "Sprache"),
        list(SUPPORTED_LANGUAGES),
        format_func=lambda code: SUPPORTED_LANGUAGES[code],
        horizontal=True,
        key="lang",
    )
    st.sidebar.markdown("---")

    # Authentication flow: if not logged in, show login/register first.
    if st.session_state.user is None:
        show_auth_page()
        return

    # Show logged-in user in sidebar
    user = st.session_state.user
    st.sidebar.markdown(f"👤 **{user['full_name']}**")
    st.sidebar.caption(user["email"])

    page = st.sidebar.radio(
        tr("Navigate", "Navigation"),
        [page_label(key) for key in PAGE_KEYS],
        key="nav_page"
    )
    
    # Logout button
    if st.sidebar.button(tr("🚪 Log out", "🚪 Abmelden"), use_container_width=True):
        st.session_state.user = None
        st.session_state.current_profile = None
        st.session_state.current_matches = []
        st.session_state.current_preferences = None
        st.session_state.pref_working = None
        st.session_state.pop("account_name", None)
        st.session_state.pop("editing_name", None)
        st.session_state.pop("submitted_job_ids", None)
        st.rerun()
    st.sidebar.markdown("---")

    # Check Ollama status
    ollama_ok = check_ollama_connection()
    
    # AI mode toggle - default OFF for reliable fast demo, ON for AI explanations
    use_ai = st.sidebar.toggle(
        tr("🤖 AI mode (Ollama)", "🤖 KI-Modus (Ollama)"),
        value=False,
        help=tr("Enable AI-generated explanations and cover letters. Requires Ollama running. Fast demo mode is instant and reliable.",
                "Aktiviert KI-generierte Erklärungen und Bewerbungsschreiben. Erfordert ein laufendes Ollama. Der schnelle Demo-Modus ist sofort und zuverlässig.")
    )

    if not ollama_ok:
        st.sidebar.warning(tr("⚠️ Ollama (local AI) not detected. Fast demo mode will be used.",
                              "⚠️ Ollama (lokale KI) wurde nicht erkannt. Es wird der schnelle Demo-Modus verwendet."))
        use_ai = False
    elif use_ai:
        st.sidebar.success(tr("🤖 AI mode active", "🤖 KI-Modus aktiv"))
    else:
        st.sidebar.info(tr("⚡ Fast demo mode (instant results)", "⚡ Schneller Demo-Modus (sofortige Ergebnisse)"))
    
    # Load data
    sample_cvs = load_sample_cvs()
    sample_jobs = load_sample_jobs()
    
    # Initialize session state for profile and matches
    if "current_profile" not in st.session_state:
        st.session_state.current_profile = None
    if "current_matches" not in st.session_state:
        st.session_state.current_matches = []
    if "selected_job" not in st.session_state:
        st.session_state.selected_job = None
    
    # Route to selected page
    if page == page_label("dashboard"):
        show_dashboard()
    elif page == page_label("profile"):
        show_profile_page(sample_cvs, use_ai)
    elif page == page_label("career_goals"):
        show_preferences_page()
    elif page == page_label("matching"):
        show_matching_page(sample_jobs, use_ai)
    elif page == page_label("assessment"):
        show_assessment_page(sample_jobs)
    elif page == page_label("application"):
        show_application_page(sample_jobs, use_ai)
    elif page == page_label("account"):
        show_account_page()


def show_auth_page():
    """Login / registration page shown when the user is not signed in."""
    st.title(tr("🤝 Welcome to MATCHA", "🤝 Willkommen bei MATCHA"))
    st.markdown(
        tr("The Swiss employment-matching platform helping women find suitable jobs faster.",
           "Die Schweizer Job-Matching-Plattform, die Frauen hilft, schneller passende Stellen zu finden.")
    )
    st.markdown("---")

    # Buttons for choosing login vs register mode
    tab_login, tab_register = st.tabs([tr("🔐 Log in", "🔐 Anmelden"), tr("📝 Create account", "📝 Konto erstellen")])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input(tr("Email", "E-Mail"), key="login_email")
            password = st.text_input(tr("Password", "Passwort"), type="password", key="login_password")
            submitted = st.form_submit_button(tr("Log in", "Anmelden"), type="primary", use_container_width=True)
            if submitted:
                user = login_user(email, password)
                if user:
                    st.session_state.user = user
                    st.success(tr("Logged in successfully!", "Erfolgreich angemeldet!"))
                    st.rerun()
                else:
                    st.error(tr("Invalid email or password. Please try again.",
                                "Ungültige E-Mail oder ungültiges Passwort. Bitte versuchen Sie es erneut."))

    with tab_register:
        with st.form("register_form"):
            full_name = st.text_input(tr("Full name", "Vollständiger Name"), key="reg_name")
            reg_email = st.text_input(tr("Email", "E-Mail"), key="reg_email")
            reg_password = st.text_input(
                tr("Password (min. 6 characters)", "Passwort (mind. 6 Zeichen)"), type="password", key="reg_password"
            )
            role = st.selectbox(tr("I am a...", "Ich bin..."), [tr("Candidate (job seeker)", "Kandidatin (Jobsuchende)"), tr("Recruiter", "Recruiter:in")])

            submitted_reg = st.form_submit_button(tr("Create account", "Konto erstellen"), type="primary", use_container_width=True)
            if submitted_reg:
                role_value = "candidate" if role.startswith(("Candidate", "Kandidatin")) else "recruiter"
                try:
                    user = register_user(reg_email, reg_password, full_name, role=role_value)
                    st.session_state.user = user
                    st.success(tr("Welcome, {}! Please now log in with your new password.",
                                  "Willkommen, {}! Bitte melden Sie sich nun mit Ihrem neuen Passwort an.").format(user['full_name']))
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.markdown("---")
    with st.expander(tr("🔒 How is my data protected?", "🔒 Wie werden meine Daten geschützt?")):
        st.markdown(tr(
            """
            **MATCHA protects personal data:**

            - **Passwords** are stored as salted hashes (PBKDF2) — never in plain text.
            - **CV content** is encrypted before it is written to the database.
            - The database and encryption key are kept out of the source repository.
            - Accounts are per-user; each user can only see their own data.

            *This is a university proof-of-concept. Always follow applicable data
            protection regulations (e.g., GDPR) in a production deployment.*
            """,
            """
            **MATCHA schützt persönliche Daten:**

            - **Passwörter** werden als gesalzene Hashwerte (PBKDF2) gespeichert — niemals im Klartext.
            - **CV-Inhalte** werden verschlüsselt, bevor sie in die Datenbank geschrieben werden.
            - Datenbank und Verschlüsselungsschlüssel liegen außerhalb des Quell-Repositorys.
            - Konten sind pro Person angelegt; jede Person kann nur ihre eigenen Daten sehen.

            *Dies ist ein universitäres Proof-of-Concept. In einem Produktiveinsatz gelten die
            jeweils anwendbaren Datenschutzregeln (z. B. DSGVO).*
            """
        ))

    # Quick demo access (optional convenience - not real auth)
    st.markdown("---")
    st.caption(tr("**Demo tip:** Create a test account to try registration, or use any email + password you make up for a quick login.",
                  "**Demo-Tipp:** Legen Sie ein Testkonto an, um die Registrierung auszuprobieren, oder verwenden Sie eine beliebige E-Mail und ein beliebiges Passwort für einen schnellen Login."))


def show_account_page():
    """Show the user's saved data, allow editing the name, and track job applications."""
    user = st.session_state.user
    st.title(tr("🔐 My Account", "🔐 Mein Konto"))
    st.markdown("---")

    st.subheader(tr("Account details", "Kontodetails"))

    # Editable display name - saved back to the account (email stays immutable).
    # In view mode the name is plain text so the Edit button aligns with it;
    # in edit mode an editable field appears next to Save / Cancel.
    editing_name = st.session_state.get("editing_name", False)
    if editing_name:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.text_input(tr("Name", "Name"),
                          value=user["full_name"],
                          key="account_name")
        with col2:
            if st.button(tr("💾 Save", "💾 Speichern"), use_container_width=True, key="save_name_btn", type="primary"):
                new_name = (st.session_state.get("account_name") or "").strip()
                if new_name:
                    update_user_name(user["id"], new_name)
                    st.session_state.user["full_name"] = new_name
                    st.session_state.editing_name = False
                    st.rerun()
                else:
                    st.error(tr("Name cannot be empty.", "Der Name darf nicht leer sein."))
        with col3:
            if st.button(tr("Cancel", "Abbrechen"), use_container_width=True, key="cancel_name_btn"):
                st.session_state.pop("account_name", None)
                st.session_state.editing_name = False
                st.rerun()
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{tr('Name', 'Name')}**\n\n{user['full_name']}")
        with col2:
            if st.button(tr("✏️ Edit", "✏️ Bearbeiten"), use_container_width=True, key="edit_name_btn"):
                st.session_state.editing_name = True
                st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.text_input(tr("Email", "E-Mail"), value=user["email"], disabled=True)
    with col2:
        role_label = tr("Candidate", "Kandidatin") if user['role'] == 'candidate' else tr("Recruiter", "Recruiter:in")
        st.text_input(tr("Role", "Rolle"), value=role_label, disabled=True)

    st.markdown("---")

    # Track submitted applications and their status (e.g., under review).
    st.subheader(tr("📨 Submitted applications", "📨 Eingereichte Bewerbungen"))
    applications = load_submitted_applications(user["id"])
    if applications:
        for app in applications:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{app['job_title']}**")
                st.caption(app.get("company", ""))
            with col2:
                if app.get("status") == "under_review":
                    st.markdown(tr("🟡 Under review", "🟡 In Prüfung"))
                else:
                    st.markdown(app.get("status", "").replace("_", " ").title())
            with col3:
                st.caption(app.get("submitted_at", ""))
    else:
        st.info(tr("No submitted applications yet. Approve an application on the **Application Agent** page to track its status here.",
                   "Noch keine eingereichten Bewerbungen. Genehmigen Sie eine Bewerbung auf der Seite **Bewerbungsagent**, um ihren Status hier zu verfolgen."))

    st.markdown("---")
    st.subheader(tr("Saved profile & CV", "Gespeichertes Profil & CV"))

    saved = load_profile(user["id"])
    if saved:
        st.success(tr("Saved profile found (last updated: {}).",
                      "Gespeichertes Profil gefunden (zuletzt aktualisiert: {}).").format(saved.get('updated_at', '')))
        if saved.get("profile"):
            profile = saved["profile"]
            name = profile.get("personal_info", {}).get("name", "N/A")
            skills = profile.get("skills", [])
            st.markdown(tr("**Profile for:** {}", "**Profil für:** {}").format(name))
            st.markdown(tr("**Skills ({}):** {}", "**Fähigkeiten ({}):** {}").format(len(skills), ', '.join(skills[:6]) if skills else 'N/A'))
        else:
            st.info(tr("No structured profile saved yet.", "Noch kein strukturiertes Profil gespeichert."))

        # Load saved data into session so matching can continue
        if st.button(tr("🔄 Load my saved profile", "🔄 Gespeichertes Profil laden"), use_container_width=True):
            st.session_state.current_profile = saved.get("profile") or {}
            st.success(tr("Profile loaded! Go to **Job Matching** to find matches.",
                          "Profil geladen! Gehen Sie zu **Job Matching**, um passende Stellen zu finden."))
    else:
        st.info(tr("No saved profile yet. Extract a profile on the **Candidate Profile** page, then click **Save to my account**.",
                   "Noch kein gespeichertes Profil. Extrahieren Sie ein Profil auf der Seite **Candidate Profile** und klicken Sie dann auf **Save to my account**."))

    st.markdown("---")
    st.subheader(tr("🎯 Saved career preferences", "🎯 Gespeicherte Karriere-Präferenzen"))
    saved_prefs = load_preferences(user["id"])
    if saved_prefs:
        st.success(tr("Career goals & work preferences saved (last updated: {}).",
                      "Karriereziele & Arbeitspräferenzen gespeichert (zuletzt aktualisiert: {}).").format(saved_prefs.get('_updated_at', '')))
        summary = get_active_preferences()
        if summary:
            from preferences import preferences_summary
            for label, value in preferences_summary(summary):
                st.markdown(f"- **{label}:** {value}")
        st.info(tr("Edit them anytime on the **Career Goals** page - they are used for matching recommendations.",
                   "Sie können sie jederzeit auf der Seite **Career Goals** bearbeiten - sie werden für Match-Empfehlungen verwendet."))
    else:
        st.info(tr("No career preferences saved yet. Set them on the **Career Goals** page to get preferences-aware recommendations.",
                   "Noch keine Karriere-Präferenzen gespeichert. Legen Sie sie auf der Seite **Career Goals** fest, um passgenauere Empfehlungen zu erhalten."))


def show_dashboard():
    """Main dashboard: shortcuts to every real page of the app."""
    st.title(tr("👩‍💼 MATCHA Dashboard", "👩‍💼 MATCHA Dashboard"))
    st.markdown("---")

    # What MATCHA actually does - every card maps to a real page in the app
    st.subheader(tr("🚀 What you can do in MATCHA", "🚀 Was Sie in MATCHA tun können"))

    st.markdown(
        """
        <style>
        [data-testid="stColumn"] [data-testid="stVerticalBlockBorderWrapper"] {
            height: 100%;
        }
        [data-testid="stColumn"] [data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] {
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        [data-testid="stColumn"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stButton"] {
            margin-top: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    app_pages = [
        (page_label("profile"),
         tr("Upload a CV or pick one of the sample profiles, then watch the structured profile extraction.",
            "Laden Sie einen Lebenslauf hoch oder wählen Sie ein Beispielprofil aus und beobachten Sie die strukturierte Profilextraktion.")),
        (page_label("career_goals"),
         tr("Tell MATCHA your work preferences (location, remote, employment %, salary, goals) in the onboarding wizard.",
            "Teilen Sie MATCHA im Onboarding-Assistenten Ihre Arbeitspräferenzen mit (Standort, Remote, Beschäftigungsgrad, Gehalt, Ziele).")),
        (page_label("matching"),
         tr("Rank your best-fit demo vacancies with explainable scores, preference checks and per-job tips.",
            "Ranken Sie Ihre am besten passenden Demo-Stellen mit nachvollziehbaren Scores, Präferenz-Checks und Tipps pro Stelle.")),
        (page_label("assessment"),
         tr("Get prioritized, job-relevant recommendations - professional and administrative - before you apply.",
            "Erhalten Sie priorisierte, jobspezifische Empfehlungen - fachlich und administrativ - bevor Sie sich bewerben.")),
        (page_label("application"),
         tr("Generate a tailored cover letter and CV summary from verified facts, review and approve it.",
            "Erstellen Sie ein passgenaues Bewerbungsschreiben und eine CV-Zusammenfassung aus verifizierten Fakten - prüfen und bestätigen Sie.")),
        (page_label("account"),
         tr("Inspect the profile and preferences saved under your account and reload them anytime.",
            "Sehen Sie sich die unter Ihrem Konto gespeicherten Profile und Präferenzen an und laden Sie sie jederzeit neu.")),
    ]

    cards = st.columns(3)
    for i, (page_name, page_desc) in enumerate(app_pages):
        with cards[i % 3]:
            with st.container():
                st.markdown(f"#### {page_name}")
                st.markdown(page_desc)
                if st.button(tr("Open", "Öffnen"), key=f"open_page_{i}"):
                    st.session_state._open_page = page_name
                    st.rerun()

    st.markdown("---")
    
    # Project overview
    st.subheader(tr("🎯 What is MATCHA?", "🎯 Was ist MATCHA?"))
    st.markdown(tr("""
    MATCHA is a **Swiss employment-matching platform** designed to:

    - **Help women job seekers** identify suitable job opportunities faster
    - **Help recruiters** identify relevant candidates with less manual screening
    - **Reduce screening effort** while improving transparency and consistency

    MATCHA does **NOT** replace recruiters or make automated hiring decisions. 
    It assists human decision-making with AI-powered tools.
    """,
    """
    MATCHA ist eine **Schweizer Job-Matching-Plattform** mit dem Ziel:

    - **Arbeitssuchenden Frauen** schneller geeignete Stellenangebote zu finden
    - **Recruiter:innen** relevante Kandidatinnen mit weniger manuellem Screening zu identifizieren
    - **Screening-Aufwand zu reduzieren** bei mehr Transparenz und Konsistenz

    MATCHA **ersetzt keine** Recruiter:innen und trifft keine automatisierten
    Einstellungsentscheidungen. Es unterstützt menschliche Entscheidungen mit KI-gestützten Tools.
    """))

    st.markdown("---")

    # Three agents overview
    st.subheader(tr("🤖 Our Three AI Agents", "🤖 Unsere drei KI-Agenten"))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📋 Profile Agent")
        st.markdown(tr("""
        **Goal:** Convert unstructured CVs into structured profiles.

        - Extracts skills, experience, education
        - Normalizes job titles
        - Identifies preferences & goals
        - NEVER invents information
        """,
        """
        **Ziel:** Unstrukturierte Lebensläufe in strukturierte Profile umwandeln.

        - Extrahiert Fähigkeiten, Erfahrung, Ausbildung
        - Normalisiert Berufsbezeichnungen
        - Erkennt Präferenzen & Ziele
        - ERFINDET NIE Informationen
        """))

    with col2:
        st.markdown("### 🎯 Matching Agent")
        st.markdown(tr("""
        **Goal:** Identify relevant jobs faster.

        - **Deterministic scoring** (not AI-based)
        - Transparent weightings
        - Mandatory requirement checks
        - AI only for explanations
        """,
        """
        **Ziel:** Relevante Jobs schneller erkennen.

        - **Deterministische Bewertung** (nicht KI-basiert)
        - Transparente Gewichtung
        - Prüfung von Pflichtanforderungen
        - KI nur für Erklärungen
        """))

    with col3:
        st.markdown("### 📝 Application Agent")
        st.markdown(tr("""
        **Goal:** Reduce application prep time.

        - Tailored cover letters
        - CV summaries
        - Uses ONLY verified info
        - Requires candidate approval
        """,
        """
        **Ziel:** Die Vorbereitungszeit für Bewerbungen verkürzen.

        - Maßgeschneiderte Bewerbungsschreiben
        - CV-Zusammenfassungen
        - Verwendet NUR verifizierte Informationen
        - Erfordert die Zustimmung der Kandidatin
        """))

    st.markdown("---")

    # Matching weights visualization
    st.subheader(tr("⚖️ Matching Weights", "⚖️ Gewichtung des Matchings"))

    weights = {
        tr("Skills", "Fähigkeiten"): 30,
        tr("Experience", "Erfahrung"): 20,
        tr("Education", "Ausbildung"): 10,
        tr("Languages", "Sprachen"): 10,
        tr("Location/Remote", "Standort/Remote"): 10,
        tr("Employment Preference", "Beschäftigungspräferenz"): 10,
        tr("Salary", "Gehalt"): 5,
        tr("Career Goals", "Karriereziele"): 5
    }
    
    # Create a simple bar chart
    chart_data = [(name, pct) for name, pct in weights.items()]
    
    # Use st.metric for a simple display
    cols = st.columns(4)
    weight_items = list(weights.items())
    for i in range(0, 8, 2):
        with cols[i // 2]:
            for name, pct in weight_items[i:i+2]:
                st.metric(name, f"{pct}%")
    
    st.markdown("---")

    # Matching efficiency experiment (telemetry - real data only, never invented)
    with st.expander(tr("📊 Matching Efficiency Experiment (A/B test)",
                        "📊 Matching-Effizienz-Experiment (A/B-Test)")):
        st.markdown(tr(
            "Each time a **Job Matching** run completes, anonymized aggregate metrics are "
            "recorded. Compare two groups to see whether collecting explicit preferences "
            "(**Version B**) improves matching efficiency over CV-only matching (**Version A**). "
            "*No personal data is logged; results come only from real runs.*",
            "Jedes Mal, wenn ein **Job-Matching**-Durchlauf abgeschlossen ist, werden anonymisierte, "
            "aggregierte Kennzahlen erfasst. Vergleichen Sie zwei Gruppen: ob das Erfassen expliziter "
            "Präferenzen (**Version B**) die Match-Effizienz gegenüber dem reinen CV-Matching "
            "(**Version A**) verbessert. *Es werden keine persönlichen Daten protokolliert; die "
            "Ergebnisse stammen nur aus echten Durchläufen.*"
        ))
        stats = telemetry_summary()
        if stats["total_runs"] == 0:
            st.info(tr("No matching runs recorded yet. Run a few matches with and without career preferences to populate the chart.",
                       "Noch keine Matching-Durchläufe erfasst. Führen Sie ein paar Matches mit und ohne Karriere-Präferenzen aus, um die Grafik zu füllen."))
        else:
            colA, colB = st.columns(2)
            for col, version in ((colA, "A"), (colB, "B")):
                agg = stats["versions"][version]
                label = {"A": tr("Version A · CV only", "Version A · nur CV"), "B": tr("Version B · CV + preferences", "Version B · CV + Präferenzen")}[version]
                with col:
                    st.markdown(f"#### {label}")
                    if agg is None:
                        st.write(tr("No runs recorded for this version yet.", "Für diese Version wurden noch keine Durchläufe erfasst."))
                    else:
                        st.metric(tr("Runs", "Durchläufe"), agg["runs"])
                        st.metric(tr("Avg. match score", "Ø Match-Score"), f"{agg.get('avg_match_score')}%" if agg.get("avg_match_score") is not None else "—")
                        st.metric(tr("Avg. time per run", "Ø Zeit pro Durchlauf"), f"{agg.get('avg_time_s', 0)}s")
                        st.metric(tr("Jobs reviewed / run", "Geprüfte Jobs / D."), agg.get("avg_jobs_reviewed"))
                        st.metric(tr("Relevant recommendations", "Relevante Empfehlungen"), agg.get("total_relevant_recommendations"))
                        fr = agg.get("avg_first_relevant_rank")
                        st.metric(tr("First relevant match at rank", "Erster relevanter Treffer auf Rang"), f"{fr}" if fr is not None else "—")
                        dist = stats["distribution"].get(version) or {}
                        if dist:
                            st.write(tr("**Score distribution:**", "**Score-Verteilung:**"))
                            for bucket, frac in dist.items():
                                st.markdown(f"`{bucket}%` — {round(frac * 100)}%")
        st.caption(tr(
            "Metrics: number of relevant recommendations (score ≥ 60), time to identify "
            "jobs, jobs reviewed before finding a relevant opportunity, match-score "
            "distribution. This demonstrates whether richer candidate preferences create "
            "measurable business value.",
            "Kennzahlen: Anzahl relevanter Empfehlungen (Score ≥ 60), Zeit bis zum Finden "
            "von Jobs, geprüfte Jobs vor einem relevanten Treffer, Score-Verteilung. "
            "Das zeigt, ob umfangreichere Präferenzen der Kandidatin messbaren geschäftlichen Nutzen schaffen."
        ))

    # About section
    st.subheader(tr("🏛️ About This Project", "🏛️ Über dieses Projekt"))
    st.markdown(tr("""
    **MATCHA** is a university proof-of-concept demonstrating:

    1. **AI can be implemented responsibly** - with human oversight
    2. **AI creates measurable business value** - faster matching, reduced screening
    3. **Transparency by design** - every match is explainable and reviewable

    *This is a demonstration project. No real hiring decisions are made by AI.*
    """,
    """
    **MATCHA** ist ein universitäres Proof-of-Concept, das zeigt:

    1. **KI kann verantwortungsvoll eingesetzt werden** - mit menschlicher Kontrolle
    2. **KI schafft messbaren Nutzen** - schnelleres Matching, weniger Screening
    3. **Transparenz durch Design** - jeder Match ist erklärbar und nachvollziehbar

    *Dies ist ein Demonstrationsprojekt. Es werden keine echten Einstellungsentscheidungen von KI getroffen.*
    """))


def show_profile_page(sample_cvs, use_ai):
    """Candidate Profile page - uses Profile Agent."""
    
    st.title(tr("📋 Candidate Profile Extraction", "📋 Profilextraktion für Kandidatin"))
    st.markdown("---")

    st.subheader(tr("Step 1: Choose How to Provide the CV", "Schritt 1: So stellen Sie Ihren Lebenslauf bereit"))

    # Input source selector
    input_mode = st.radio(
        tr("Select an input method:", "Wählen Sie eine Eingabemethode:"),
        [tr("📁 Upload a CV file", "📁 CV-Datei hochladen"), tr("📄 Use a sample CV", "📄 Beispiel-CV verwenden"), tr("✍️ Paste CV text", "✍️ CV-Text einfügen")],
        horizontal=True
    )
    
    cv_text = ""
    source_label = ""
    uploaded_doc = None

    input_upload = tr("📁 Upload a CV file", "📁 CV-Datei hochladen")
    input_sample = tr("📄 Use a sample CV", "📄 Beispiel-CV verwenden")
    input_paste = tr("✍️ Paste CV text", "✍️ CV-Text einfügen")

    if input_mode == input_upload:
        uploaded_file = st.file_uploader(
            tr("Upload your CV (PDF, Word, or TXT)", "Lebenslauf hochladen (PDF, Word oder TXT)"),
            type=["pdf", "docx", "txt"],
            help=tr("Uploading a file makes it possible to extract your CV for analysis.",
                    "Durch das Hochladen einer Datei kann Ihr CV für die Analyse extrahiert werden.")
        )
        if uploaded_file is not None:
            uploaded_doc = {"name": uploaded_file.name, "data": uploaded_file.getvalue()}
            st.caption(tr("Ready: **{}**", "Bereit: **{}**").format(uploaded_file.name))

    elif input_mode == input_sample:
        use_sample = st.selectbox(
            tr("Choose a sample CV for the demo:", "Wählen Sie einen Beispiel-CV für die Demo:"),
            [tr("Select a sample CV...", "Beispiel-CV auswählen...")] + [cv["name"] for cv in sample_cvs]
        )
        if use_sample != tr("Select a sample CV...", "Beispiel-CV auswählen..."):
            selected = next((cv for cv in sample_cvs if cv["name"] == use_sample), None)
            if selected:
                cv_text = selected["cv_text"]
                source_label = f"📄 {selected['name']}"
                st.info(tr("Selected: {}", "Ausgewählt: {}").format(selected['name']))

    else:  # Paste CV text
        custom_cv = st.text_area(
            tr("Paste your CV text here:", "CV-Text hier einfügen:"),
            height=200,
            placeholder=tr("Copy and paste your CV text here...", "Kopieren Sie Ihren CV-Text hierher und fügen Sie ihn ein...")
        )
        if custom_cv:
            cv_text = custom_cv
            source_label = tr("✍️ Pasted CV", "✍️ Eingefügter CV")

    st.markdown("---")

    col1, col2 = st.columns([1, 3])
    with col1:
        extract_button = st.button(tr("🔍 Extract Profile", "🔍 Profil extrahieren"), type="primary", use_container_width=True)

    if extract_button:
        profile = None
        warned = False

        if uploaded_doc is not None:
            with st.spinner(tr("Profile Agent is extracting text and analyzing your CV...",
                               "Der Profil-Agent extrahiert den Text und analysiert Ihren Lebenslauf...")):
                profile_agent = ProfileAgent()
                profile, meta = profile_agent.extract_profile_from_document(uploaded_doc["data"], uploaded_doc["name"])
                cv_text = meta["transcript"]
                source_label = f"📁 {uploaded_doc['name']}"
            if cv_text:
                ocr_note = tr(" · OCR applied (image-based PDF)", " · OCR angewendet (bildbasiertes PDF)") if meta["ocr_used"] else ""
                st.info(tr("Loaded text from **{}** ({} characters).", "Text aus **{}** geladen ({} Zeichen).").format(uploaded_doc['name'], meta["characters"]) + ocr_note)
            elif meta["text_source"] == "pdf_ocr_missing":
                warned = True
                st.info(tr("This PDF appears to be scanned (image-based), but the OCR tool is not available. Install Tesseract plus 'pytesseract' and 'pymupdf' (see README) to extract scanned CVs.",
                           "Dieses PDF scheint gescannt zu sein (bildbasiert), aber das OCR-Tool ist nicht verfügbar. Installieren Sie Tesseract sowie 'pytesseract' und 'pymupdf' (siehe README), um gescannte Lebensläufe zu extrahieren."))
            elif meta["text_source"] == "pdf_empty":
                warned = True
                st.warning(tr("Could not extract text from this PDF. It may be corrupt or image-based.",
                              "Der Text konnte nicht aus dem PDF extrahiert werden. Es könnte beschädigt oder bildbasiert sein."))
            elif meta["text_source"] == "unsupported":
                warned = True
                st.warning(tr("Unsupported file type. Please upload a .pdf, .docx, or .txt file.",
                              "Nicht unterstützter Dateityp. Bitte laden Sie eine .pdf-, .docx- oder .txt-Datei hoch."))
            elif meta["text_source"] in ("pdf_pkg_missing", "docx_pkg_missing"):
                warned = True
                st.warning(tr("Document support is not installed. Check requirements.txt (pypdf, python-docx).",
                              "Die Dokumentunterstützung ist nicht installiert. Überprüfen Sie requirements.txt (pypdf, python-docx)."))
            else:
                warned = True
                st.warning(tr("No text could be read from this file.",
                              "Aus dieser Datei konnte kein Text gelesen werden."))
        elif cv_text:
            with st.spinner(tr("Profile Agent is analyzing your CV...", "Der Profil-Agent analysiert Ihren Lebenslauf...")):
                profile_agent = ProfileAgent()
                profile = profile_agent.extract_profile_main(cv_text)

        if profile is not None:
            # Store in session
            st.session_state.current_profile = profile
            st.session_state.current_profile_source = source_label
            st.session_state.last_cv_text = cv_text
            st.session_state.edit_profile_mode = False
            st.session_state.edit_profile = None

            st.success(tr("✅ Profile extracted successfully!", "✅ Profil erfolgreich extrahiert!"))
            show_profile_results(profile)
        elif not warned:
            st.warning(tr("No CV provided. Please upload a file, select a sample, or paste CV text.",
                          "Kein Lebenslauf angegeben. Bitte laden Sie eine Datei hoch, wählen Sie ein Beispiel oder fügen Sie CV-Text ein."))

    # Show existing profile if available
    elif st.session_state.current_profile:
        show_profile_results(st.session_state.current_profile)


def show_profile_results(profile):
    """Display the extracted profile, with an edit mode so candidates can
    correct or complete any information the CV extraction missed."""

    st.subheader(tr("Extracted Candidate Profile", "Extrahiertes Kandidatenprofil"))

    # Check if there's an error
    if "error" in profile:
        st.error(profile.get("error", tr("Error extracting profile", "Fehler bei der Profilextraktion")))
        if "raw_response" in profile:
            with st.expander(tr("View raw response", "Rohantwort anzeigen")):
                st.code(profile["raw_response"])
        return

    editing = st.session_state.get("edit_profile_mode", False)

    # Toggle edit mode
    col_top, _ = st.columns([1, 3])
    with col_top:
        if not editing:
            if st.button(tr("✏️ Edit Profile", "✏️ Profil bearbeiten"), use_container_width=True):
                st.session_state.edit_profile_mode = True
                st.session_state.edit_profile = copy.deepcopy(profile)
                st.rerun()
        else:
            if st.button(tr("◀ Back to View", "◀ Zurück zur Ansicht"), use_container_width=True):
                st.session_state.edit_profile_mode = False
                st.session_state.edit_profile = None
                st.rerun()

    if editing:
        st.info(tr("✏️ **Editing mode:** correct or complete any information that was "
                   "not extracted from your CV, then click **💾 Save Profile Changes** below.",
                   "✏️ **Bearbeitungsmodus:** korrigieren oder ergänzen Sie alle Informationen, "
                   "die nicht aus Ihrem CV extrahiert wurden, und klicken Sie unten auf **💾 Profiländerungen speichern**."))
        work = st.session_state.get("edit_profile") or copy.deepcopy(profile)
    else:
        work = profile

    # Personal info
    personal = work.get("personal_info", {})
    st.markdown(tr("### 👤 Personal Information", "### 👤 Persönliche Angaben"))
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.text_input(tr("Name", "Name"), value=personal.get("name", ""), disabled=not editing, key="pi_name")
    with col2:
        st.text_input(tr("Location", "Ort"), value=personal.get("location", ""), disabled=not editing, key="pi_location")
    with col3:
        st.text_input(tr("Email", "E-Mail"), value=personal.get("email", ""), disabled=not editing, key="pi_email")
    with col4:
        st.text_input(tr("Phone", "Telefon"), value=personal.get("phone", ""), disabled=not editing, key="pi_phone")

    # Summary
    if work.get("summary") or editing:
        st.markdown(tr("**Professional Summary:**", "**Berufliche Zusammenfassung:**"))
        if editing:
            st.text_area(tr("Summary", "Zusammenfassung"), value=work.get("summary", ""), key="summary_edit", label_visibility="collapsed")
        else:
            st.write(work["summary"])

    st.markdown("---")

    # Work experience
    st.markdown(tr("### 💼 Work Experience", "### 💼 Berufserfahrung"))
    work_exp = work.get("work_experience", [])
    if editing:
        st.caption(tr("Edit each role below, or use the buttons to add / remove entries.",
                      "Bearbeiten Sie jede Rolle unten oder nutzen Sie die Schaltflächen zum Hinzufügen / Entfernen."))
    if work_exp:
        for i, exp in enumerate(work_exp):
            if editing:
                col_t, col_c, col_d, col_del = st.columns([2, 2, 2, 1])
                with col_t:
                    st.text_input(tr("Title", "Titel"), value=exp.get("title", ""), key=f"exp_title_{i}")
                with col_c:
                    st.text_input(tr("Company", "Unternehmen"), value=exp.get("company", ""), key=f"exp_company_{i}")
                with col_d:
                    st.text_input(tr("Duration", "Dauer"), value=exp.get("duration", ""), key=f"exp_duration_{i}")
                with col_del:
                    if st.button("🗑️", key=f"exp_del_{i}", help=tr("Remove this entry", "Diesen Eintrag entfernen")):
                        work["work_experience"].pop(i)
                        st.rerun()
                achievements = "\n".join(exp.get("key_achievements", []))
                st.text_area(tr("Key achievements (one per line)", "Wichtigste Erfolge (eine Zeile pro Eintrag)"), value=achievements,
                             key=f"exp_achiev_{i}")
            else:
                with st.container():
                    st.markdown(f"**{exp.get('title', 'Role')}** at *{exp.get('company', 'Company')}*")
                    st.caption(tr("Duration: {}", "Dauer: {}").format(exp.get('duration', 'N/A')))
                    achievements = exp.get("key_achievements", [])
                    if achievements:
                        for achievement in achievements[:3]:
                            st.markdown(f"- {achievement}")
                    st.markdown("---")
    else:
        st.info(tr("No work experience found.", "Keine Berufserfahrung gefunden."))
    if editing:
        if st.button(tr("➕ Add work experience", "➕ Berufserfahrung hinzufügen"), key="exp_add"):
            work["work_experience"].append({"title": "", "company": "", "duration": "", "key_achievements": []})
            st.rerun()

    st.markdown("---")

    # Education
    st.markdown(tr("### 🎓 Education", "### 🎓 Ausbildung"))
    education = work.get("education", [])
    if editing:
        st.caption(tr("Edit each education entry below, or use the buttons to add / remove entries.",
                      "Bearbeiten Sie jeden Ausbildungseintrag unten oder nutzen Sie die Schaltflächen zum Hinzufügen / Entfernen."))
    if education:
        for i, edu in enumerate(education):
            if editing:
                col_deg, col_inst, col_year, col_del = st.columns([2, 2, 1, 1])
                with col_deg:
                    st.text_input(tr("Degree", "Abschluss"), value=edu.get("degree", ""), key=f"edu_degree_{i}")
                with col_inst:
                    st.text_input(tr("Institution", "Institution"), value=edu.get("institution", ""), key=f"edu_inst_{i}")
                with col_year:
                    st.text_input(tr("Year", "Jahr"), value=edu.get("year", ""), key=f"edu_year_{i}")
                with col_del:
                    if st.button("🗑️", key=f"edu_del_{i}", help=tr("Remove this entry", "Diesen Eintrag entfernen")):
                        work["education"].pop(i)
                        st.rerun()
            else:
                st.markdown(f"**{edu.get('degree', 'Degree')}** - {edu.get('institution', 'Institution')} ({edu.get('year', '')})")
    else:
        st.info(tr("No education found.", "Keine Ausbildung gefunden."))
    if editing:
        if st.button(tr("➕ Add education", "➕ Ausbildung hinzufügen"), key="edu_add"):
            work["education"].append({"degree": "", "institution": "", "year": ""})
            st.rerun()

    st.markdown("---")

    # Skills
    st.markdown(tr("### 🔧 Skills", "### 🔧 Fähigkeiten"))
    skills = work.get("skills", [])
    if editing:
        skills_text = ", ".join(skills)
        st.text_input(tr("Skills (comma-separated)", "Fähigkeiten (durch Kommas getrennt)"), value=skills_text, key="skills_edit")
        st.caption(tr("Separate multiple skills with commas, e.g. Python, SQL, Project Management",
                      "Trennen Sie mehrere Fähigkeiten durch Kommas, z. B. Python, SQL, Projektmanagement"))
    elif skills:
        # Display as tags
        skills_html = " ".join([f'<span style="background-color:#e0e0e0;padding:4px 8px;border-radius:4px;margin:2px;">{s}</span>' for s in skills])
        st.markdown(f"<div style='margin-bottom:10px;'>{skills_html}</div>", unsafe_allow_html=True)
    else:
        st.info(tr("No skills found.", "Keine Fähigkeiten gefunden."))

    # Languages
    st.markdown(tr("### 🌍 Languages", "### 🌍 Sprachen"))
    languages = work.get("languages", [])
    if editing:
        st.caption(tr("Edit your languages and levels below, or use the buttons to add / remove entries.",
                      "Bearbeiten Sie unten Ihre Sprachen und Niveaus oder nutzen Sie die Schaltflächen zum Hinzufügen / Entfernen."))
    if languages:
        for i, lang in enumerate(languages):
            if editing:
                col_lang, col_lvl, col_del = st.columns([2, 2, 1])
                with col_lang:
                    st.text_input(tr("Language", "Sprache"), value=lang.get("language", "") if isinstance(lang, dict) else "", key=f"lang_name_{i}")
                with col_lvl:
                    st.text_input(tr("Level", "Niveau"), value=lang.get("level", "") if isinstance(lang, dict) else "", key=f"lang_level_{i}")
                with col_del:
                    if st.button("🗑️", key=f"lang_del_{i}", help=tr("Remove this entry", "Diesen Eintrag entfernen")):
                        work["languages"].pop(i)
                        st.rerun()
            else:
                if isinstance(lang, dict):
                    st.markdown(f"- {lang.get('language', '')}: {lang.get('level', '')}")
                else:
                    st.markdown(f"- {lang}")
    else:
        st.info(tr("No languages found.", "Keine Sprachen gefunden."))
    if editing:
        if st.button(tr("➕ Add language", "➕ Sprache hinzufügen"), key="lang_add"):
            work["languages"].append({"language": "", "level": ""})
            st.rerun()

    # Certifications
    certs = work.get("certifications", [])
    if certs or editing:
        st.markdown(tr("### 📜 Certifications", "### 📜 Zertifikate"))
        if editing:
            certs_text = ", ".join(certs)
            st.text_input(tr("Certifications (comma-separated)", "Zertifikate (durch Kommas getrennt)"), value=certs_text, key="certs_edit")
            st.caption(tr("Separate multiple certifications with commas, e.g. PMP, AWS Certified, CPA",
                          "Trennen Sie mehrere Zertifikate durch Kommas, z. B. PMP, AWS Certified, CPA"))
        else:
            for cert in certs:
                st.markdown(f"- {cert}")

    # Preferences
    prefs = work.get("preferences", {})
    if prefs or editing:
        st.markdown(tr("### ⚙️ Preferences", "### ⚙️ Präferenzen"))
        if editing:
            pref_keys = ["employment_type", "remote_preference", "location_constraint", "salary_expectation"]
            pref_cols = st.columns(2)
            for j, pk in enumerate(pref_keys):
                with pref_cols[j % 2]:
                    st.text_input(pk.replace("_", " ").title(),
                                  value=prefs.get(pk, ""), key=f"pref_{pk}")
        else:
            for key, value in prefs.items():
                if value:
                    st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")

    # Career goals
    if editing or work.get("career_goals"):
        st.markdown(tr("### 🎯 Career Goals", "### 🎯 Karriereziele"))
        if editing:
            st.text_area(tr("Career goals", "Karriereziele"), value=work.get("career_goals", ""),
                         key="career_goals_edit", label_visibility="collapsed")
        else:
            st.write(work["career_goals"])

    st.markdown("---")

    if editing:
        # Save edits back into the working profile
        if st.button(tr("💾 Save Profile Changes", "💾 Profiländerungen speichern"), type="primary", use_container_width=True):
            edit = st.session_state.get("edit_profile") or copy.deepcopy(profile)

            edit["personal_info"] = {
                "name": st.session_state.get("pi_name", ""),
                "location": st.session_state.get("pi_location", ""),
                "email": st.session_state.get("pi_email", ""),
                "phone": st.session_state.get("pi_phone", ""),
            }
            edit["summary"] = st.session_state.get("summary_edit", "")

            skills_text = st.session_state.get("skills_edit", "") or ""
            edit["skills"] = [s.strip() for s in skills_text.split(",") if s.strip()]
            certs_text = st.session_state.get("certs_edit", "") or ""
            edit["certifications"] = [c.strip() for c in certs_text.split(",") if c.strip()]

            new_exp = []
            for exp in edit.get("work_experience", []):
                i = len(new_exp)
                ach_text = st.session_state.get(f"exp_achiev_{i}", "") or ""
                new_exp.append({
                    "title": st.session_state.get(f"exp_title_{i}", ""),
                    "company": st.session_state.get(f"exp_company_{i}", ""),
                    "duration": st.session_state.get(f"exp_duration_{i}", ""),
                    "key_achievements": [a.strip() for a in ach_text.split("\n") if a.strip()],
                })
            edit["work_experience"] = new_exp

            new_edu = []
            for edu in edit.get("education", []):
                i = len(new_edu)
                new_edu.append({
                    "degree": st.session_state.get(f"edu_degree_{i}", ""),
                    "institution": st.session_state.get(f"edu_inst_{i}", ""),
                    "year": st.session_state.get(f"edu_year_{i}", ""),
                })
            edit["education"] = new_edu

            new_langs = []
            for lang in edit.get("languages", []):
                i = len(new_langs)
                new_langs.append({
                    "language": st.session_state.get(f"lang_name_{i}", ""),
                    "level": st.session_state.get(f"lang_level_{i}", ""),
                })
            edit["languages"] = new_langs

            edit_prefs = edit.get("preferences", {})
            for pk in ["employment_type", "remote_preference", "location_constraint", "salary_expectation"]:
                edit_prefs[pk] = st.session_state.get(f"pref_{pk}", "")
            edit["preferences"] = edit_prefs

            edit["career_goals"] = st.session_state.get("career_goals_edit", "")

            st.session_state.current_profile = edit
            st.session_state.edit_profile_mode = False
            st.session_state.edit_profile = None
            st.success(tr("✅ Profile updated successfully!", "✅ Profil erfolgreich aktualisiert!"))
            st.rerun()
    else:
        st.info(tr("💡 **Verification:** Please review all extracted information. "
                   "You can correct any errors by clicking **✏️ Edit Profile** before proceeding to job matching.",
                   "💡 **Prüfung:** Bitte überprüfen Sie alle extrahierten Informationen. "
                   "Sie können Fehler korrigieren, indem Sie **✏️ Profil bearbeiten** klicken, bevor Sie mit dem Job-Matching fortfahren."))

        # Save profile to the user's account (stored encrypted in the database)
        if st.session_state.user:
            existing_saved = load_profile(st.session_state.user["id"])
            col_save, _ = st.columns([1, 2])
            with col_save:
                if st.button(tr("💾 Save to my account", "💾 Auf meinem Konto speichern"), type="primary", use_container_width=True):
                    try:
                        save_profile(
                            st.session_state.user["id"],
                            getattr(st.session_state, "last_cv_text", ""),
                            profile
                        )
                        st.success(tr("✅ Profile and CV saved securely to your account!", "✅ Profil und CV wurden sicher auf Ihrem Konto gespeichert!"))
                    except Exception as e:
                        st.error(tr("Could not save profile: {}", "Profil konnte nicht gespeichert werden: {}").format(e))
            if existing_saved and existing_saved.get("profile"):
                st.caption(tr("📁 You already have a saved profile. Saving again will update it.",
                              "📁 Sie haben bereits ein gespeichertes Profil. Beim erneuten Speichern wird es aktualisiert."))


def show_matching_page(sample_jobs, use_ai):
    """Job Matching page - uses Matching Agent."""
    
    st.title(tr("🎯 Job Matching", "🎯 Job-Matching"))
    st.markdown("---")
    
    if not st.session_state.current_profile:
        st.warning(tr("⚠️ No candidate profile yet. Please go to **Candidate Profile** page first and extract a profile.",
                      "⚠️ Noch kein Kandidatenprofil. Bitte gehen Sie zuerst auf die Seite **Kandidatenprofil** und extrahieren Sie ein Profil."))
        return
    
    profile = st.session_state.current_profile
    st.success(tr("Matching for: **{}**", "Matching für: **{}**").format(profile.get('personal_info', {}).get('name', tr('Candidate', 'Kandidatin'))))

    # Merge the candidate's explicit preferences (if any) into the profile so
    # the matching engine can use them. Missing preferences stay neutral.
    active_prefs = get_active_preferences()
    prefs_status = tr("not set", "nicht gesetzt")
    if active_prefs:
        profile = {**profile, "preferences": active_prefs}
        prefs_status = tr("active", "aktiv")

    if active_prefs:
        st.info(tr("🎯 Your saved **Career Goals & Work Preferences** are being used to tailor these recommendations.",
                   "🎯 Ihre gespeicherten **Karriereziele & Arbeitspräferenzen** werden verwendet, um diese Empfehlungen anzupassen."))
    else:
        st.info(tr("ℹ️ You have **no career preferences set yet**. Recommendations use your CV only. "
                   "Add preferences on the **Career Goals** page for more tailored results.",
                   "ℹ️ Sie haben **noch keine Karriere-Präferenzen gesetzt**. Die Empfehlungen basieren nur auf Ihrem CV. "
                   "Legen Sie Präferenzen auf der Seite **Karriereziele** fest, um passgenauere Ergebnisse zu erhalten."))

    col1, col2 = st.columns([1, 2])
    with col1:
        top_n = st.slider(tr("Number of matches to show", "Anzahl der anzuzeigenden Treffer"), 3, 8, 5)

    match_button = st.button(tr("🔍 Find Matching Jobs", "🔍 Passende Jobs finden"), type="primary")

    if match_button:
        with st.spinner(tr("Matching Agent is analyzing job compatibility...", "Der Matching-Agent analysiert die Job-Kompatibilität...")):
            matching_agent = MatchingAgent()

            # Check if profile has error
            if "error" in profile:
                st.error(tr("Profile extraction had errors. Please re-extract profile.",
                            "Die Profilextraktion enthielt Fehler. Bitte extrahieren Sie das Profil erneut."))
                return

            import time
            start = time.time()
            matches = matching_agent.find_matches(profile, sample_jobs, top_n=top_n,
                                                  use_ai=use_ai, record_telemetry=True)
            st.session_state.current_matches = matches

            st.success(tr("Found {} potential matches (took {:.2f}s, preferences: {}).",
                          "{} potenzielle Treffer gefunden (dauerte {:.2f}s, Präferenzen: {}).").format(len(matches), time.time() - start, prefs_status))

    # Display matches
    if st.session_state.current_matches:
        matches = st.session_state.current_matches
        show_matches(matches, sample_jobs, profile)

    # Show matching weights explanation
    with st.expander(tr("📊 How Matching Works", "📊 So funktioniert das Matching")):
        st.markdown(tr("""
        ### Deterministic Scoring Weights:
        
        | Criterion | Weight |
        |-----------|--------|
        | Skills | 30% |
        | Experience | 20% |
        | Education | 10% |
        | Languages | 10% |
        | Location/Remote | 10% |
        | Employment Preference | 10% |
        | Salary | 5% |
        | Career Goals | 5% |
        
        **Mandatory requirements are checked separately.** If a candidate does not meet a 
        mandatory requirement (e.g., required language), they are not recommended for that 
        position regardless of the numerical score.
        
        The **AI (LLM) is only used for explanations** - never for the actual scoring.
        """,
        """
        ### Deterministische Gewichtung:

        | Kriterium | Gewicht |
        |-----------|---------|
        | Fähigkeiten | 30 % |
        | Erfahrung | 20 % |
        | Ausbildung | 10 % |
        | Sprachen | 10 % |
        | Standort/Remote | 10 % |
        | Beschäftigungspräferenz | 10 % |
        | Gehalt | 5 % |
        | Karriereziele | 5 % |

        **Pflichtanforderungen werden separat geprüft.** Erfüllt eine Kandidatin eine
        Pflichtanforderung (z. B. eine geforderte Sprache) nicht, wird sie für diese
        Position unabhängig von der Punktzahl nicht empfohlen.

        Die **KI (LLM) wird nur für Erklärungen verwendet** - nie für die eigentliche Bewertung.
        """)
    )


def show_assessment_page(sample_jobs):
    """Full 'Areas to Improve' report: professional + administrative improvements."""

    st.title(tr("📈 Areas to Improve", "📈 Verbesserungsbereiche"))
    st.markdown("---")

    if not st.session_state.current_profile:
        st.warning(tr("⚠️ No candidate profile yet. Please go to **Candidate Profile** page first and extract a profile.",
                      "⚠️ Noch kein Kandidatenprofil. Bitte gehen Sie zuerst auf die Seite **Kandidatenprofil** und extrahieren Sie ein Profil."))
        return

    profile = st.session_state.current_profile
    active_prefs = get_active_preferences()

    st.markdown(tr(
        "*This assessment compares your profile against your best-fit positions and points "
        "you to **job-relevant** areas to improve - professional skills and administrative "
        "details. It does **not** assess your personality or personal worth.*",
        "*Diese Einschätzung vergleicht Ihr Profil mit Ihren am besten passenden Positionen "
        "und zeigt Ihnen **jobspezifische** Verbesserungsbereiche - fachliche Fähigkeiten und "
        "administrative Details. Sie bewertet **nicht** Ihre Persönlichkeit oder Ihren persönlichen Wert.*"
    ))

    if active_prefs:
        profile = {**profile, "preferences": active_prefs}

    st.success(tr("Assessment for: **{}**", "Einschätzung für: **{}**").format(profile.get('personal_info', {}).get('name', tr('Candidate', 'Kandidatin'))))

    if st.button(tr("🔄 Refresh assessment", "🔄 Einschätzung aktualisieren"), type="primary"):
        pass  # re-run below (Streamlit reruns on button click)

    engine = RecommendationEngine()
    result = engine.assess(profile, sample_jobs, active_prefs)

    st.markdown(tr("### 🎯 Based on your best-fit roles", "### 🎯 Basierend auf Ihren Best-Match-Rollen"))
    top_jobs = result["top_jobs"]
    if top_jobs:
        cols = st.columns(min(len(top_jobs), 4))
        for col, job in zip(cols, top_jobs[:4]):
            with col:
                st.metric(job["title"], f"{job['score']}%", help=job["company"])
    else:
        st.info(tr("No comparable positions found to assess against.",
                   "Keine vergleichbaren Positionen für die Einschätzung gefunden."))

    st.markdown("---")

    # Professional improvement areas
    st.markdown(tr("### 💼 Professional areas to improve", "### 💼 Fachliche Verbesserungsbereiche"))
    professional = result["professional"]
    if professional:
        for item in professional:
            badge = {"high": tr("🔴 High", "🔴 Hoch"), "medium": tr("🟠 Medium", "🟠 Mittel"), "low": tr("🟡 Low", "🟡 Niedrig")}[item["priority"]]
            with st.container():
                st.markdown(f"**{item['area']}** — `{badge}`")
                st.caption(item["detail"])
                st.markdown(tr("→ **Suggestion:** {}", "→ **Vorschlag:** {}").format(item["action"]))
                if item.get("source_jobs"):
                    st.caption(tr("Relevant for: {}", "Relevant für: {}").format(", ".join(item["source_jobs"])))
    else:
        st.info(tr("No professional gaps found - you already cover your best-fit roles well.",
                   "Keine fachlichen Lücken gefunden - Sie decken Ihre Best-Match-Rollen bereits gut ab."))

    st.markdown("---")

    # Administrative / profile-setup areas
    st.markdown(tr("### 🗂️ Administrative & profile areas to improve", "### 🗂️ Administrative & Profil-Bereiche"))
    admin = result["admin"]
    if admin:
        for item in admin:
            badge = {"high": tr("🔴 High", "🔴 Hoch"), "medium": tr("🟠 Medium", "🟠 Mittel"), "low": tr("🟡 Low", "🟡 Niedrig")}[item["priority"]]
            with st.container():
                st.markdown(f"**{item['area']}** — `{badge}`")
                st.caption(item["detail"])
                st.markdown(tr("→ **Suggestion:** {}", "→ **Vorschlag:** {}").format(item["action"]))
    else:
        st.info(tr("Your profile and preferences are complete - nothing to do here.",
                   "Ihr Profil und Ihre Präferenzen sind vollständig - hier gibt es nichts zu tun."))


def show_matches(matches, jobs=None, profile=None):
    """Display job matches with scores, explanations, and per-job improvement areas."""

    st.subheader(tr("Matching Results", "Matching-Ergebnisse"))

    # Cache one engine per page interaction for per-job improvement hints.
    if "assessment_engine" not in st.session_state:
        st.session_state.assessment_engine = RecommendationEngine()
    engine = st.session_state.assessment_engine
    active_prefs = get_active_preferences()
    job_by_id = {j["id"]: j for j in jobs} if jobs else {}

    for i, match in enumerate(matches):
        score = match["score"]
        mandatory_met = match["mandatory_met"]

        # Determine color based on score
        if score >= 75:
            color = "🟢"
        elif score >= 50:
            color = "🟡"
        else:
            color = "🟠"

        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### {color} {match['job_title']}")
                st.markdown(f"**{match['company']}** | {match['location']}")

                # Employment details
                details = match.get("job_details", {})
                if details:
                    st.caption(f"⏰ {details.get('employment_type', 'N/A')} | 🌐 {details.get('remote_policy', 'N/A')} | 💰 {details.get('salary_range', 'N/A')}")

                # Mandatory requirement status
                if mandatory_met:
                    st.success(tr("✅ Meets mandatory requirements", "✅ Erfüllt Pflichtanforderungen"))
                else:
                    st.error(tr("❌ Does NOT meet mandatory requirements", "❌ Erfüllt Pflichtanforderungen NICHT"))

            with col2:
                st.markdown(f"### {score}%")
                st.caption(tr("Match Score", "Match-Punktzahl"))

            # Score breakdown
            with st.expander(tr("📊 Score Breakdown", "📊 Punkte-Aufschlüsselung")):
                breakdown = match.get("score_breakdown", {})

                for criterion, value in breakdown.items():
                    label = criterion.replace("_", " ").title()
                    st.markdown(f"**{label}:** {value}%")
                    st.progress(min(value / 100, 1.0))

            # Explainable preference compatibility
            preference_checks = match.get("preference_checks", [])
            if preference_checks:
                with st.expander(tr("🎯 Why this job matches your preferences", "🎯 Warum dieser Job zu Ihren Präferenzen passt")):
                    for check in preference_checks:
                        status = check.get("status", "info")
                        text = check.get("text", "")
                        if status == "ok":
                            st.markdown(f"✅ {text}")
                        elif status == "warn":
                            st.markdown(f"⚠️ {text}")
                        else:
                            st.markdown(f"ℹ️ {text}")

            # Areas to improve for this specific role (compact version)
            if profile and match["job_id"] in job_by_id:
                job = job_by_id[match["job_id"]]
                short = engine.short_for_job(profile, job, active_prefs)
                if short:
                    with st.expander(tr("📈 Areas to improve for this role", "📈 Verbesserungsbereiche für diese Rolle")):
                        st.caption(tr("Based only on job-relevant gaps between your profile and this position.",
                                      "Basiert nur auf jobspezifischen Lücken zwischen Ihrem Profil und dieser Position."))
                        for line in short:
                            st.markdown(f"- {line}")

            # Explanation (AI-generated)
            if match.get("explanation"):
                with st.expander(tr("💬 Why this match?", "💬 Warum dieser Treffer?")):
                    st.write(match["explanation"])

            # Select job button
            if mandatory_met:
                if st.button(tr("📝 Select this Job", "📝 Diesen Job auswählen"), key=f"select_{match['job_id']}", type="primary"):
                    # Carry the FULL job object (not just the match summary) so the
                    # Application Agent can show description/details and generate materials.
                    st.session_state.selected_job = job_by_id.get(match["job_id"]) or match
                    st.success(tr("Selected: {} at {}", "Ausgewählt: {} bei {}").format(match['job_title'], match['company']))
                    st.info(tr("Go to **Application Agent** to generate your application materials.",
                               "Gehen Sie zum **Bewerbungsagenten**, um Ihre Bewerbungsunterlagen zu erstellen."))
            
            st.markdown("---")


def show_application_page(sample_jobs, use_ai):
    """Application Agent page."""
    
    st.title(tr("📝 Application Agent", "📝 Bewerbungsagent"))
    st.markdown("---")
    
    if not st.session_state.current_profile:
        st.warning(tr("⚠️ No candidate profile yet. Please extract a profile first on the **Candidate Profile** page.",
                      "⚠️ Noch kein Kandidatenprofil. Bitte extrahieren Sie zuerst auf der Seite **Kandidatenprofil** ein Profil."))
        return
    
    profile = st.session_state.current_profile
    
    # Let user pick which job to apply for
    st.subheader(tr("Select Job for Application", "Job für die Bewerbung auswählen"))
    
    # Build dropdown of jobs
    job_options = {}
    for job in sample_jobs:
        label = f"{job['title']} - {job['company']}"
        job_options[label] = job

    labels = list(job_options.keys())

    # Preselect the job chosen on the Job Matching page (if any), so the
    # candidate's selected role carries over instead of defaulting to the
    # first job in the list.
    preselected_label = None
    carried_job = st.session_state.get("selected_job")
    if isinstance(carried_job, dict) and carried_job.get("id"):
        for label in labels:
            if job_options[label]["id"] == carried_job["id"]:
                preselected_label = label
                break

    index = labels.index(preselected_label) if preselected_label else 0
    selected_label = st.selectbox(tr("Choose a job:", "Wählen Sie einen Job:"), labels, index=index)

    if preselected_label:
        st.caption(tr("👆 This job was selected on the **Job Matching** page.",
                      "👆 Dieser Job wurde auf der Seite **Job-Matching** ausgewählt."))
    
    if selected_label:
        selected_job = job_options[selected_label]
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"### {selected_job['title']}")
            st.markdown(f"**{selected_job['company']}** | {selected_job['location']}")
            st.write(selected_job["description"])
        with col2:
            details = selected_job.get("details", {})
            st.markdown(tr("**Position Details:**", "**Positionsdetails:**"))
            for key, value in details.items():
                st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")
        
        st.markdown("---")
        
        generate_button = st.button(tr("✨ Generate Application", "✨ Bewerbung erstellen"), type="primary")
        
        if generate_button:
            with st.spinner(tr("Application Agent is preparing your application materials...", "Der Bewerbungsagent bereitet Ihre Bewerbungsunterlagen vor...")):
                application_agent = ApplicationAgent()
                
                result = application_agent.generate_application(profile, selected_job, use_ai=use_ai)
                
                st.session_state.current_application = result
                st.session_state.current_application_job = selected_job
                st.success(tr("✅ Application materials generated!", "✅ Bewerbungsunterlagen erstellt!"))
        
        # Display generated application
        if "current_application" in st.session_state and st.session_state.current_application_job:
            if st.session_state.current_application_job["title"] == selected_job["title"]:
                result = st.session_state.current_application
                
                # Cover letter
                tab1, tab2, tab3 = st.tabs([tr("💌 Cover Letter", "💌 Anschreiben"), tr("📄 CV Summary", "📄 CV-Zusammenfassung"), tr("📋 Guidelines", "📋 Richtlinien")])
                
                with tab1:
                    st.subheader(tr("Cover Letter", "Anschreiben"))
                    st.write(result["cover_letter"])
                    
                    # Edit capability
                    if st.button(tr("📝 Edit Cover Letter", "📝 Anschreiben bearbeiten")):
                        st.session_state.editing_letter = True
                    
                    if st.session_state.get("editing_letter", False):
                        edited = st.text_area(
                            tr("Edit your cover letter:", "Bearbeiten Sie Ihr Anschreiben:"),
                            value=result["cover_letter"],
                            height=300
                        )
                        if st.button(tr("💾 Save Edits", "💾 Änderungen speichern")):
                            result["cover_letter"] = edited
                            st.session_state.editing_letter = False
                            st.success(tr("✓ Cover letter saved!", "✓ Anschreiben gespeichert!"))
                
                with tab2:
                    st.subheader(tr("CV Summary", "CV-Zusammenfassung"))
                    st.info(result["cv_summary"])
                
                with tab3:
                    st.subheader(tr("Application Guidelines", "Bewerbungsrichtlinien"))
                    st.write(result["application_notes"])
                
                st.markdown("---")
                
                # Approval workflow
                st.subheader(tr("✅ Candidate Approval Required", "✅ Freigabe der Kandidatin erforderlich"))
                st.markdown(tr("""
                Before you can submit this application, please review all materials carefully.
                
                MATCHA does **NOT** automatically submit applications.
                """,
                """
                Bevor Sie diese Bewerbung absenden können, prüfen Sie bitte alle Unterlagen sorgfältig.
                
                MATCHA sendet Bewerbungen **NICHT** automatisch ab.
                """))

                approve = st.checkbox(tr("I have reviewed all information and approve this application",
                                         "Ich habe alle Informationen geprüft und genehmige diese Bewerbung"))
                
                if approve:
                    st.success(tr("✅ Application approved! Review complete.", "✅ Bewerbung genehmigt! Prüfung abgeschlossen."))
                    st.info(tr("📤 In a real deployment, this application would now be sent to the recruiter for review. No automated email submission occurs in this demo.",
                               "📤 In einer echten Bereitstellung würde diese Bewerbung nun zur Prüfung an die Recruiterin gesendet. In dieser Demo erfolgt keine automatisierte E-Mail-Übermittlung."))
                    
                    if st.button(tr("🔒 Send to Recruiter Review (Demo)", "🔒 An Recruiter-Prüfung senden (Demo)")):
                        # Record the submission so it can be tracked on the My Account page.
                        if "submitted_job_ids" not in st.session_state:
                            st.session_state.submitted_job_ids = set()
                        job_key = selected_job.get("id") or f"{selected_job['title']} - {selected_job['company']}"
                        if job_key not in st.session_state.submitted_job_ids:
                            save_submitted_application(st.session_state.user["id"], selected_job)
                            st.session_state.submitted_job_ids.add(job_key)
                        st.success(tr("🎉 Application sent to Recruiter Review Queue! You can track its status on the **My Account** page.",
                                      "🎉 Bewerbung in die Recruiter-Prüfungswarteschlange gesendet! Sie können den Status auf der Seite **Mein Konto** verfolgen."))
                        st.markdown(tr("""
                        ### Next Steps in the Recruitment Process:
                        1. ✅ Application received
                        2. 📋 Human reviewer will assess application
                        3. 💬 Interview scheduling (human decision)
                        4. 🤝 Final hiring decision (HUMAN only)
                        """,
                        """
                        ### Nächste Schritte im Einstellungsprozess:
                        1. ✅ Bewerbung eingegangen
                        2. 📋 Eine menschliche Prüferin bewertet die Bewerbung
                        3. 💬 Interview-Terminplanung (menschliche Entscheidung)
                        4. 🤝 Endgültige Einstellungsentscheidung (NUR menschlich)
                        """))
                else:
                    st.warning(tr("⚠️ You must review and approve the application before it can be sent.",
                                  "⚠️ Sie müssen die Bewerbung prüfen und genehmigen, bevor sie gesendet werden kann."))
        
        # Show disclaimer always
        with st.expander(tr("⚠️ Important Disclaimer", "⚠️ Wichtiger Hinweis")):
            st.markdown(tr("""
            **MATCHA Application Agent Disclaimer:**
            
            - All application materials are generated using **verified candidate information only**
            - The AI **never invents** experience, qualifications, skills, or achievements
            - The candidate **must approve** the application before it is sent
            - Applications are **never automatically submitted** to employers
            - MATCHA assists but does **not** replace human recruiters
            """,
            """
            **MATCHA-Bewerbungsagent-Hinweis:**

            - Alle Bewerbungsunterlagen werden nur mit **verifizierten Kandidateninformationen** erstellt
            - Die KI **erfindet nie** Erfahrungen, Qualifikationen, Fähigkeiten oder Erfolge
            - Die Kandidatin **muss** die Bewerbung genehmigen, bevor sie gesendet wird
            - Bewerbungen werden **nie automatisch** an Arbeitgeber übermittelt
            - MATCHA unterstützt, ersetzt aber **nicht** menschliche Recruiterinnen
            """))


if __name__ == "__main__":
    main()
