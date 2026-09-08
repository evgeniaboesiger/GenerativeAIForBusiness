"""
MATCHA - Swiss Employment Matching Platform
A university proof-of-concept demonstrating AI-powered job matching

This is the main Streamlit application that ties together all three agents.
"""

import streamlit as st
import json
import os
import sys
import io

# Add the agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))

from profile_agent import ProfileAgent
from matching_agent import MatchingAgent
from application_agent import ApplicationAgent
from db import (
    register_user, login_user, save_profile, load_profile, init_session,
    get_connection, load_preferences, save_preferences
)
from telemetry import summary as telemetry_summary

# Career Goals & Work Preferences onboarding wizard
from preferences_ui import show_preferences_page, get_active_preferences

# Candidate assessment: areas to improve (professional + administrative)
from assessment import RecommendationEngine

# PDF and Word document text extraction
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

def read_uploaded_file(uploaded_file) -> str:
    """Extract text from an uploaded CV file (PDF, Word, or TXT)."""
    import traceback

    name = (uploaded_file.name or "").lower()
    data = uploaded_file.getvalue()
    try:
        if name.endswith(".pdf"):
            if PdfReader is None:
                return "PDF support not installed. Add 'pypdf' to requirements.txt."
            reader = PdfReader(io.BytesIO(data))
            text_parts = []
            for page in reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception:
                    text_parts.append("")
            text = "\n".join(text_parts).strip()
            if not text:
                return "Could not extract text from this PDF. It may be a scanned document (image-based)."
            return text
        elif name.endswith(".docx"):
            if Document is None:
                return "Word (.docx) support not installed. Add 'python-docx' to requirements.txt."
            document = Document(io.BytesIO(data))
            text_parts = []
            for para in document.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text.strip())
            # Also pick up text from tables if present
            for table in document.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        text_parts.append(" | ".join(cells))
            text = "\n".join(text_parts).strip()
            return text if text else "No text found in this Word document."
        elif name.endswith(".txt"):
            return data.decode("utf-8", errors="replace").strip() or "Empty text file."
        else:
            return f"Unsupported file type: {uploaded_file.name}. Please upload a .pdf, .docx, or .txt file."
    except Exception as e:
        traceback.print_exc()
        return f"Error reading file {uploaded_file.name}: {str(e)}"

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


def main():
    """Main application entry point."""
    init_session()

    # Sidebar - navigation
    st.sidebar.title("🤝 MATCHA")
    st.sidebar.markdown("*Smart Job Matching for Women in Switzerland*")
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
        "Navigate",
        ["🏠 Dashboard", "👤 Candidate Profile", "🎯 Career Goals",
         "🎯 Job Matching", "📈 Areas to Improve", "📝 Application Agent", "🔐 My Account"]
    )
    
    # Logout button
    if st.sidebar.button("🚪 Log out", use_container_width=True):
        st.session_state.user = None
        st.session_state.current_profile = None
        st.session_state.current_matches = []
        st.session_state.current_preferences = None
        st.session_state.pref_working = None
        st.rerun()
    st.sidebar.markdown("---")

    # Check Ollama status
    ollama_ok = check_ollama_connection()
    
    # AI mode toggle - default OFF for reliable fast demo, ON for AI explanations
    use_ai = st.sidebar.toggle(
        "🤖 AI mode (Ollama)",
        value=False,
        help="Enable AI-generated explanations and cover letters. Requires Ollama running. Fast demo mode is instant and reliable."
    )
    
    if not ollama_ok:
        st.sidebar.warning("⚠️ Ollama (local AI) not detected. Fast demo mode will be used.")
        use_ai = False
    elif use_ai:
        st.sidebar.success("🤖 AI mode active")
    else:
        st.sidebar.info("⚡ Fast demo mode (instant results)")
    
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
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "👤 Candidate Profile":
        show_profile_page(sample_cvs, use_ai)
    elif page == "🎯 Career Goals":
        show_preferences_page()
    elif page == "🎯 Job Matching":
        show_matching_page(sample_jobs, use_ai)
    elif page == "📈 Areas to Improve":
        show_assessment_page(sample_jobs)
    elif page == "📝 Application Agent":
        show_application_page(sample_jobs, use_ai)
    elif page == "🔐 My Account":
        show_account_page()


def show_auth_page():
    """Login / registration page shown when the user is not signed in."""
    st.title("🤝 Welcome to MATCHA")
    st.markdown(
        "The Swiss employment-matching platform helping women find suitable jobs faster."
    )
    st.markdown("---")

    # Buttons for choosing login vs register mode
    tab_login, tab_register = st.tabs(["🔐 Log in", "📝 Create account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
            if submitted:
                user = login_user(email, password)
                if user:
                    st.session_state.user = user
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid email or password. Please try again.")

    with tab_register:
        with st.form("register_form"):
            full_name = st.text_input("Full name", key="reg_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input(
                "Password (min. 6 characters)", type="password", key="reg_password"
            )
            role = st.selectbox("I am a...", ["Candidate (job seeker)", "Recruiter"])

            submitted_reg = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if submitted_reg:
                role_value = "candidate" if role.startswith("Candidate") else "recruiter"
                try:
                    user = register_user(reg_email, reg_password, full_name, role=role_value)
                    st.session_state.user = user
                    st.success(f"Welcome, {user['full_name']}! Please now log in with your new password.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.markdown("---")
    with st.expander("🔒 How is my data protected?"):
        st.markdown(
            """
            **MATCHA protects personal data:**

            - **Passwords** are stored as salted hashes (PBKDF2) — never in plain text.
            - **CV content** is encrypted before it is written to the database.
            - The database and encryption key are kept out of the source repository.
            - Accounts are per-user; each user can only see their own data.

            *This is a university proof-of-concept. Always follow applicable data
            protection regulations (e.g., GDPR) in a production deployment.*
            """
        )

    # Quick demo access (optional convenience - not real auth)
    st.markdown("---")
    st.caption("**Demo tip:** Create a test account to try registration, or use any email + password you make up for a quick login.")


def show_account_page():
    """Show the user's saved data, allow loading a saved profile."""
    user = st.session_state.user
    st.title("🔐 My Account")
    st.markdown("---")

    st.subheader("Account details")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Name", value=user["full_name"], disabled=True)
    with col2:
        st.text_input("Email", value=user["email"], disabled=True)
    st.info(f"Role: {'Candidate' if user['role'] == 'candidate' else 'Recruiter'}")

    st.markdown("---")
    st.subheader("Saved profile & CV")

    saved = load_profile(user["id"])
    if saved:
        st.success(f"Saved profile found (last updated: {saved.get('updated_at', '')}).")
        if saved.get("profile"):
            profile = saved["profile"]
            name = profile.get("personal_info", {}).get("name", "N/A")
            skills = profile.get("skills", [])
            st.markdown(f"**Profile for:** {name}")
            st.markdown(f"**Skills ({len(skills)}):** {', '.join(skills[:6]) if skills else 'N/A'}")
        else:
            st.info("No structured profile saved yet.")

        # Load saved data into session so matching can continue
        if st.button("🔄 Load my saved profile", use_container_width=True):
            st.session_state.current_profile = saved.get("profile") or {}
            st.success("Profile loaded! Go to **Job Matching** to find matches.")
    else:
        st.info("No saved profile yet. Extract a profile on the **Candidate Profile** page, then click **Save to my account**.")

    st.markdown("---")
    st.subheader("🎯 Saved career preferences")
    saved_prefs = load_preferences(user["id"])
    if saved_prefs:
        st.success(f"Career goals & work preferences saved (last updated: {saved_prefs.get('_updated_at', '')}).")
        summary = get_active_preferences()
        if summary:
            from preferences import preferences_summary
            for label, value in preferences_summary(summary):
                st.markdown(f"- **{label}:** {value}")
        st.info("Edit them anytime on the **Career Goals** page - they are used for matching recommendations.")
    else:
        st.info("No career preferences saved yet. Set them on the **Career Goals** page to get preferences-aware recommendations.")


def show_dashboard():
    """Main dashboard with overview and impact metrics."""
    
    st.title("👩‍💼 MATCHA Dashboard")
    st.markdown("---")
    
    # Hero section
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Candidates", "4", "Demo Data")
    with col2:
        st.metric("Open Positions", "8", "Demo Data")
    with col3:
        st.metric("Match Success Rate", "72%", "↑ 5%")
    
    st.markdown("---")
    
    # Project overview
    st.subheader("🎯 What is MATCHA?")
    st.markdown("""
    MATCHA is a **Swiss employment-matching platform** designed to:
    
    - **Help women job seekers** identify suitable job opportunities faster
    - **Help recruiters** identify relevant candidates with less manual screening
    - **Reduce screening effort** while improving transparency and consistency
    
    MATCHA does **NOT** replace recruiters or make automated hiring decisions. 
    It assists human decision-making with AI-powered tools.
    """)
    
    st.markdown("---")
    
    # Three agents overview
    st.subheader("🤖 Our Three AI Agents")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📋 Profile Agent")
        st.markdown("""
        **Goal:** Convert unstructured CVs into structured profiles.
        
        - Extracts skills, experience, education
        - Normalizes job titles
        - Identifies preferences & goals
        - NEVER invents information
        """)
    
    with col2:
        st.markdown("### 🎯 Matching Agent")
        st.markdown("""
        **Goal:** Identify relevant jobs faster.
        
        - **Deterministic scoring** (not AI-based)
        - Transparent weightings
        - Mandatory requirement checks
        - AI only for explanations
        """)
    
    with col3:
        st.markdown("### 📝 Application Agent")
        st.markdown("""
        **Goal:** Reduce application prep time.
        
        - Tailored cover letters
        - CV summaries
        - Uses ONLY verified info
        - Requires candidate approval
        """)
    
    st.markdown("---")
    
    # Matching weights visualization
    st.subheader("⚖️ Matching Weights")
    
    weights = {
        "Skills": 30,
        "Experience": 20,
        "Education": 10,
        "Languages": 10,
        "Location/Remote": 10,
        "Employment Preference": 10,
        "Salary": 5,
        "Career Goals": 5
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
    with st.expander("📊 Matching Efficiency Experiment (A/B test)"):
        st.markdown(
            "Each time a **Job Matching** run completes, anonymized aggregate metrics are "
            "recorded. Compare two groups to see whether collecting explicit preferences "
            "(**Version B**) improves matching efficiency over CV-only matching (**Version A**). "
            "*No personal data is logged; results come only from real runs.*"
        )
        stats = telemetry_summary()
        if stats["total_runs"] == 0:
            st.info("No matching runs recorded yet. Run a few matches with and without career preferences to populate the chart.")
        else:
            colA, colB = st.columns(2)
            for col, version in ((colA, "A"), (colB, "B")):
                agg = stats["versions"][version]
                label = {"A": "Version A · CV only", "B": "Version B · CV + preferences"}[version]
                with col:
                    st.markdown(f"#### {label}")
                    if agg is None:
                        st.write("No runs recorded for this version yet.")
                    else:
                        st.metric("Runs", agg["runs"])
                        st.metric("Avg. match score", f"{agg.get('avg_match_score')}%" if agg.get("avg_match_score") is not None else "—")
                        st.metric("Avg. time per run", f"{agg.get('avg_time_s', 0)}s")
                        st.metric("Jobs reviewed / run", agg.get("avg_jobs_reviewed"))
                        st.metric("Relevant recommendations", agg.get("total_relevant_recommendations"))
                        fr = agg.get("avg_first_relevant_rank")
                        st.metric("First relevant match at rank", f"{fr}" if fr is not None else "—")
                        dist = stats["distribution"].get(version) or {}
                        if dist:
                            st.write("**Score distribution:**")
                            for bucket, frac in dist.items():
                                st.markdown(f"`{bucket}%` — {round(frac * 100)}%")
        st.caption(
            "Metrics: number of relevant recommendations (score ≥ 60), time to identify "
            "jobs, jobs reviewed before finding a relevant opportunity, match-score "
            "distribution. This demonstrates whether richer candidate preferences create "
            "measurable business value."
        )

    # About section
    st.subheader("🏛️ About This Project")
    st.markdown("""
    **MATCHA** is a university proof-of-concept demonstrating:
    
    1. **AI can be implemented responsibly** - with human oversight
    2. **AI creates measurable business value** - faster matching, reduced screening
    3. **Transparency by design** - every match is explainable and reviewable
    
    *This is a demonstration project. No real hiring decisions are made by AI.*
    """)


def show_profile_page(sample_cvs, use_ai):
    """Candidate Profile page - uses Profile Agent."""
    
    st.title("📋 Candidate Profile Extraction")
    st.markdown("---")
    
    st.subheader("Step 1: Choose How to Provide the CV")
    
    # Input source selector
    input_mode = st.radio(
        "Select an input method:",
        ["📁 Upload a CV file", "📄 Use a sample CV", "✍️ Paste CV text"],
        horizontal=True
    )
    
    cv_text = ""
    source_label = ""
    
    if input_mode == "📁 Upload a CV file":
        uploaded_file = st.file_uploader(
            "Upload your CV (PDF, Word, or TXT)",
            type=["pdf", "docx", "txt"],
            help="Uploading a file makes it possible to extract your CV for analysis."
        )
        if uploaded_file is not None:
            with st.spinner("Reading file..."):
                cv_text = read_uploaded_file(uploaded_file)
                source_label = f"📁 {uploaded_file.name}"
            if cv_text:
                st.info(f"Loaded text from **{uploaded_file.name}** ({len(cv_text)} characters)")
            else:
                st.warning("No text could be read from this file.")
    
    elif input_mode == "📄 Use a sample CV":
        use_sample = st.selectbox(
            "Choose a sample CV for the demo:",
            ["Select a sample CV..."] + [cv["name"] for cv in sample_cvs]
        )
        if use_sample != "Select a sample CV...":
            selected = next((cv for cv in sample_cvs if cv["name"] == use_sample), None)
            if selected:
                cv_text = selected["cv_text"]
                source_label = f"📄 {selected['name']}"
                st.info(f"Selected: {selected['name']}")
    
    else:  # Paste CV text
        custom_cv = st.text_area(
            "Paste your CV text here:",
            height=200,
            placeholder="Copy and paste your CV text here..."
        )
        if custom_cv:
            cv_text = custom_cv
            source_label = "✍️ Pasted CV"
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        extract_button = st.button("🔍 Extract Profile", type="primary", use_container_width=True)
    
    if extract_button and cv_text:
        with st.spinner("Profile Agent is analyzing your CV..."):
            # Use the Profile Agent (fast deterministic extraction - always works)
            profile_agent = ProfileAgent()
            profile = profile_agent.extract_profile_main(cv_text)
            
            # Store in session
            st.session_state.current_profile = profile
            st.session_state.current_profile_source = source_label
            st.session_state.last_cv_text = cv_text
            
            st.success("✅ Profile extracted successfully!")
            show_profile_results(profile)
    
    elif extract_button and not cv_text:
        st.warning("No CV provided. Please upload a file, select a sample, or paste CV text.")
    
    # Show existing profile if available
    elif st.session_state.current_profile:
        show_profile_results(st.session_state.current_profile)


def show_profile_results(profile):
    """Display the extracted profile in a nice format."""
    
    st.subheader("Extracted Candidate Profile")
    
    # Check if there's an error
    if "error" in profile:
        st.error(profile.get("error", "Error extracting profile"))
        if "raw_response" in profile:
            with st.expander("View raw response"):
                st.code(profile["raw_response"])
        return
    
    # Personal info
    personal = profile.get("personal_info", {})
    st.markdown("### 👤 Personal Information")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.text_input("Name", value=personal.get("name", ""), disabled=True)
    with col2:
        st.text_input("Location", value=personal.get("location", ""), disabled=True)
    with col3:
        st.text_input("Email", value=personal.get("email", ""), disabled=True)
    with col4:
        st.text_input("Phone", value=personal.get("phone", ""), disabled=True)
    
    if profile.get("summary"):
        st.markdown("**Professional Summary:**")
        st.write(profile["summary"])
    
    st.markdown("---")
    
    # Work experience
    st.markdown("### 💼 Work Experience")
    work_exp = profile.get("work_experience", [])
    if work_exp:
        for exp in work_exp:
            with st.container():
                st.markdown(f"**{exp.get('title', 'Role')}** at *{exp.get('company', 'Company')}*")
                st.caption(f"Duration: {exp.get('duration', 'N/A')}")
                achievements = exp.get("key_achievements", [])
                if achievements:
                    for achievement in achievements[:3]:
                        st.markdown(f"- {achievement}")
                st.markdown("---")
    else:
        st.info("No work experience found.")
    
    # Education
    st.markdown("### 🎓 Education")
    education = profile.get("education", [])
    if education:
        for edu in education:
            st.markdown(f"**{edu.get('degree', 'Degree')}** - {edu.get('institution', 'Institution')} ({edu.get('year', '')})")
    else:
        st.info("No education found.")
    
    st.markdown("---")
    
    # Skills
    st.markdown("### 🔧 Skills")
    skills = profile.get("skills", [])
    if skills:
        # Display as tags
        skills_html = " ".join([f'<span style="background-color:#e0e0e0;padding:4px 8px;border-radius:4px;margin:2px;">{s}</span>' for s in skills])
        st.markdown(f"<div style='margin-bottom:10px;'>{skills_html}</div>", unsafe_allow_html=True)
    else:
        st.info("No skills found.")
    
    # Languages
    st.markdown("### 🌍 Languages")
    languages = profile.get("languages", [])
    if languages:
        for lang in languages:
            if isinstance(lang, dict):
                st.markdown(f"- {lang.get('language', '')}: {lang.get('level', '')}")
            else:
                st.markdown(f"- {lang}")
    else:
        st.info("No languages found.")
    
    # Certifications
    certs = profile.get("certifications", [])
    if certs:
        st.markdown("### 📜 Certifications")
        for cert in certs:
            st.markdown(f"- {cert}")
    
    # Preferences
    prefs = profile.get("preferences", {})
    if prefs:
        st.markdown("### ⚙️ Preferences")
        for key, value in prefs.items():
            if value:
                st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")
    
    # Career goals
    if profile.get("career_goals"):
        st.markdown("### 🎯 Career Goals")
        st.write(profile["career_goals"])
    
    st.markdown("---")
    st.info("💡 **Verification:** Please review all extracted information. You can correct any errors before proceeding to job matching.")

    # Save profile to the user's account (stored encrypted in the database)
    if st.session_state.user:
        existing_saved = load_profile(st.session_state.user["id"])
        col_save, _ = st.columns([1, 2])
        with col_save:
            if st.button("💾 Save to my account", type="primary", use_container_width=True):
                try:
                    save_profile(
                        st.session_state.user["id"],
                        getattr(st.session_state, "last_cv_text", ""),
                        profile
                    )
                    st.success("✅ Profile and CV saved securely to your account!")
                except Exception as e:
                    st.error(f"Could not save profile: {e}")
        if existing_saved and existing_saved.get("profile"):
            st.caption("📁 You already have a saved profile. Saving again will update it.")


def show_matching_page(sample_jobs, use_ai):
    """Job Matching page - uses Matching Agent."""
    
    st.title("🎯 Job Matching")
    st.markdown("---")
    
    if not st.session_state.current_profile:
        st.warning("⚠️ No candidate profile yet. Please go to **Candidate Profile** page first and extract a profile.")
        return
    
    profile = st.session_state.current_profile
    st.success(f"Matching for: **{profile.get('personal_info', {}).get('name', 'Candidate')}**")

    # Merge the candidate's explicit preferences (if any) into the profile so
    # the matching engine can use them. Missing preferences stay neutral.
    active_prefs = get_active_preferences()
    prefs_status = "not set"
    if active_prefs:
        profile = {**profile, "preferences": active_prefs}
        prefs_status = "active"

    if active_prefs:
        st.info("🎯 Your saved **Career Goals & Work Preferences** are being used to tailor these recommendations.")
    else:
        st.info("ℹ️ You have **no career preferences set yet**. Recommendations use your CV only. "
                "Add preferences on the **Career Goals** page for more tailored results.")

    col1, col2 = st.columns([1, 2])
    with col1:
        top_n = st.slider("Number of matches to show", 3, 8, 5)

    match_button = st.button("🔍 Find Matching Jobs", type="primary")

    if match_button:
        with st.spinner("Matching Agent is analyzing job compatibility..."):
            matching_agent = MatchingAgent()

            # Check if profile has error
            if "error" in profile:
                st.error("Profile extraction had errors. Please re-extract profile.")
                return

            import time
            start = time.time()
            matches = matching_agent.find_matches(profile, sample_jobs, top_n=top_n,
                                                  use_ai=use_ai, record_telemetry=True)
            st.session_state.current_matches = matches

            st.success(f"Found {len(matches)} potential matches (took {time.time() - start:.2f}s, preferences: {prefs_status}).")
    
    # Display matches
    if st.session_state.current_matches:
        matches = st.session_state.current_matches
        show_matches(matches, sample_jobs, profile)
    
    # Show matching weights explanation
    with st.expander("📊 How Matching Works"):
        st.markdown("""
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
        """)


def show_assessment_page(sample_jobs):
    """Full 'Areas to Improve' report: professional + administrative improvements."""

    st.title("📈 Areas to Improve")
    st.markdown("---")

    if not st.session_state.current_profile:
        st.warning("⚠️ No candidate profile yet. Please go to **Candidate Profile** page first and extract a profile.")
        return

    profile = st.session_state.current_profile
    active_prefs = get_active_preferences()

    st.markdown(
        "*This assessment compares your profile against your best-fit positions and points "
        "you to **job-relevant** areas to improve - professional skills and administrative "
        "details. It does **not** assess your personality or personal worth.*"
    )

    if active_prefs:
        profile = {**profile, "preferences": active_prefs}

    st.success(f"Assessment for: **{profile.get('personal_info', {}).get('name', 'Candidate')}**")

    if st.button("🔄 Refresh assessment", type="primary"):
        pass  # re-run below (Streamlit reruns on button click)

    engine = RecommendationEngine()
    result = engine.assess(profile, sample_jobs, active_prefs)

    st.markdown("### 🎯 Based on your best-fit roles")
    top_jobs = result["top_jobs"]
    if top_jobs:
        cols = st.columns(min(len(top_jobs), 4))
        for col, job in zip(cols, top_jobs[:4]):
            with col:
                st.metric(job["title"], f"{job['score']}%", help=job["company"])
    else:
        st.info("No comparable positions found to assess against.")

    st.markdown("---")

    # Professional improvement areas
    st.markdown("### 💼 Professional areas to improve")
    professional = result["professional"]
    if professional:
        for item in professional:
            badge = {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟡 Low"}[item["priority"]]
            with st.container(border=True):
                st.markdown(f"**{item['area']}** — `{badge}`")
                st.caption(item["detail"])
                st.markdown(f"→ **Suggestion:** {item['action']}")
                if item.get("source_jobs"):
                    st.caption(f"Relevant for: {', '.join(item['source_jobs'])}")
    else:
        st.info("No professional gaps found - you already cover your best-fit roles well.")

    st.markdown("---")

    # Administrative / profile-setup areas
    st.markdown("### 🗂️ Administrative & profile areas to improve")
    admin = result["admin"]
    if admin:
        for item in admin:
            badge = {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟡 Low"}[item["priority"]]
            with st.container(border=True):
                st.markdown(f"**{item['area']}** — `{badge}`")
                st.caption(item["detail"])
                st.markdown(f"→ **Suggestion:** {item['action']}")
    else:
        st.info("Your profile and preferences are complete - nothing to do here.")


def show_matches(matches, jobs=None, profile=None):
    """Display job matches with scores, explanations, and per-job improvement areas."""

    st.subheader("Matching Results")

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

        with st.container(border=True):
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
                    st.success("✅ Meets mandatory requirements")
                else:
                    st.error("❌ Does NOT meet mandatory requirements")

            with col2:
                st.markdown(f"### {score}%")
                st.caption("Match Score")

            # Score breakdown
            with st.expander("📊 Score Breakdown"):
                breakdown = match.get("score_breakdown", {})

                for criterion, value in breakdown.items():
                    label = criterion.replace("_", " ").title()
                    st.markdown(f"**{label}:** {value}%")
                    st.progress(min(value / 100, 1.0))

            # Explainable preference compatibility
            preference_checks = match.get("preference_checks", [])
            if preference_checks:
                with st.expander("🎯 Why this job matches your preferences"):
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
                    with st.expander("📈 Areas to improve for this role"):
                        st.caption("Based only on job-relevant gaps between your profile and this position.")
                        for line in short:
                            st.markdown(f"- {line}")

            # Explanation (AI-generated)
            if match.get("explanation"):
                with st.expander("💬 Why this match?"):
                    st.write(match["explanation"])
            
            # Select job button
            if mandatory_met:
                if st.button(f"📝 Select this Job", key=f"select_{match['job_id']}", type="primary"):
                    st.session_state.selected_job = match
                    st.success(f"Selected: {match['job_title']} at {match['company']}")
                    st.info("Go to **Application Agent** to generate your application materials.")
            
            st.markdown("---")


def show_application_page(sample_jobs, use_ai):
    """Application Agent page."""
    
    st.title("📝 Application Agent")
    st.markdown("---")
    
    if not st.session_state.current_profile:
        st.warning("⚠️ No candidate profile yet. Please extract a profile first on the **Candidate Profile** page.")
        return
    
    profile = st.session_state.current_profile
    
    # Let user pick which job to apply for
    st.subheader("Select Job for Application")
    
    # Build dropdown of jobs
    job_options = {}
    for job in sample_jobs:
        label = f"{job['title']} - {job['company']}"
        job_options[label] = job
    
    selected_label = st.selectbox("Choose a job:", list(job_options.keys()))
    
    if selected_label:
        selected_job = job_options[selected_label]
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"### {selected_job['title']}")
            st.markdown(f"**{selected_job['company']}** | {selected_job['location']}")
            st.write(selected_job["description"])
        with col2:
            details = selected_job.get("details", {})
            st.markdown("**Position Details:**")
            for key, value in details.items():
                st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")
        
        st.markdown("---")
        
        generate_button = st.button("✨ Generate Application", type="primary")
        
        if generate_button:
            with st.spinner("Application Agent is preparing your application materials..."):
                application_agent = ApplicationAgent()
                
                result = application_agent.generate_application(profile, selected_job, use_ai=use_ai)
                
                st.session_state.current_application = result
                st.session_state.current_application_job = selected_job
                st.success("✅ Application materials generated!")
        
        # Display generated application
        if "current_application" in st.session_state and st.session_state.current_application_job:
            if st.session_state.current_application_job["title"] == selected_job["title"]:
                result = st.session_state.current_application
                
                # Cover letter
                tab1, tab2, tab3 = st.tabs(["💌 Cover Letter", "📄 CV Summary", "📋 Guidelines"])
                
                with tab1:
                    st.subheader("Cover Letter")
                    st.write(result["cover_letter"])
                    
                    # Edit capability
                    if st.button("📝 Edit Cover Letter"):
                        st.session_state.editing_letter = True
                    
                    if st.session_state.get("editing_letter", False):
                        edited = st.text_area(
                            "Edit your cover letter:",
                            value=result["cover_letter"],
                            height=300
                        )
                        if st.button("💾 Save Edits"):
                            result["cover_letter"] = edited
                            st.session_state.editing_letter = False
                            st.success("✓ Cover letter saved!")
                
                with tab2:
                    st.subheader("CV Summary")
                    st.info(result["cv_summary"])
                
                with tab3:
                    st.subheader("Application Guidelines")
                    st.write(result["application_notes"])
                
                st.markdown("---")
                
                # Approval workflow
                st.subheader("✅ Candidate Approval Required")
                st.markdown("""
                Before you can submit this application, please review all materials carefully.
                
                MATCHA does **NOT** automatically submit applications.
                """)
                
                approve = st.checkbox("I have reviewed all information and approve this application")
                
                if approve:
                    st.success("✅ Application approved! Review complete.")
                    st.info("📤 In a real deployment, this application would now be sent to the recruiter for review. No automated email submission occurs in this demo.")
                    
                    if st.button("🔒 Send to Recruiter Review (Demo)"):
                        st.success("🎉 Application sent to Recruiter Review Queue!")
                        st.markdown("""
                        ### Next Steps in the Recruitment Process:
                        1. ✅ Application received
                        2. 📋 Human reviewer will assess application
                        3. 💬 Interview scheduling (human decision)
                        4. 🤝 Final hiring decision (HUMAN only)
                        """)
                else:
                    st.warning("⚠️ You must review and approve the application before it can be sent.")
        
        # Show disclaimer always
        with st.expander("⚠️ Important Disclaimer"):
            st.markdown("""
            **MATCHA Application Agent Disclaimer:**
            
            - All application materials are generated using **verified candidate information only**
            - The AI **never invents** experience, qualifications, skills, or achievements
            - The candidate **must approve** the application before it is sent
            - Applications are **never automatically submitted** to employers
            - MATCHA assists but does **not** replace human recruiters
            """)


if __name__ == "__main__":
    main()
