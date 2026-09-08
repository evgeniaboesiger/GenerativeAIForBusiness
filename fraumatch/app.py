"""
FRAUMATCH - Swiss Employment Matching Platform
A university proof-of-concept demonstrating AI-powered job matching

This is the main Streamlit application that ties together all three agents.
"""

import streamlit as st
import json
import os
import sys

# Add the agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))

from profile_agent import ProfileAgent
from matching_agent import MatchingAgent
from application_agent import ApplicationAgent

# Page configuration
st.set_page_config(
    page_title="FRAUMATCH - Smart Job Matching",
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
    
    # Sidebar - navigation
    st.sidebar.title("🤝 FRAUMATCH")
    st.sidebar.markdown("*Smart Job Matching for Women in Switzerland*")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navigate",
        ["🏠 Dashboard", "👤 Candidate Profile", "🎯 Job Matching", "📝 Application Agent"]
    )
    
    # Check Ollama status
    ollama_ok = check_ollama_connection()
    if not ollama_ok:
        st.sidebar.warning("⚠️ Ollama (local AI) not detected. Starting app in demo mode with sample data.")
    
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
        show_profile_page(sample_cvs, ollama_ok)
    elif page == "🎯 Job Matching":
        show_matching_page(sample_jobs, ollama_ok)
    elif page == "📝 Application Agent":
        show_application_page(sample_jobs, ollama_ok)


def show_dashboard():
    """Main dashboard with overview and impact metrics."""
    
    st.title("👩‍💼 FRAUMATCH Dashboard")
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
    st.subheader("🎯 What is FRAUMATCH?")
    st.markdown("""
    FRAUMATCH is a **Swiss employment-matching platform** designed to:
    
    - **Help women job seekers** identify suitable job opportunities faster
    - **Help recruiters** identify relevant candidates with less manual screening
    - **Reduce screening effort** while improving transparency and consistency
    
    FRAUMATCH does **NOT** replace recruiters or make automated hiring decisions. 
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
    
    # About section
    st.subheader("🏛️ About This Project")
    st.markdown("""
    **FRAUMATCH** is a university proof-of-concept demonstrating:
    
    1. **AI can be implemented responsibly** - with human oversight
    2. **AI creates measurable business value** - faster matching, reduced screening
    3. **Transparency by design** - every match is explainable and reviewable
    
    *This is a demonstration project. No real hiring decisions are made by AI.*
    """)


def show_profile_page(sample_cvs, ollama_ok):
    """Candidate Profile page - uses Profile Agent."""
    
    st.title("📋 Candidate Profile Extraction")
    st.markdown("---")
    
    st.subheader("Step 1: Select or Paste a CV")
    
    # Option to use sample data
    use_sample = st.selectbox(
        "Choose a sample CV or paste your own",
        ["Select a sample CV..."] + [cv["name"] for cv in sample_cvs]
    )
    
    cv_text = ""
    if use_sample != "Select a sample CV...":
        # Find the selected CV
        selected = next((cv for cv in sample_cvs if cv["name"] == use_sample), None)
        if selected:
            cv_text = selected["cv_text"]
            st.info(f"Selected: {selected['name']}")
    
    # OR paste custom CV
    st.markdown("**— OR —**")
    custom_cv = st.text_area(
        "Paste your own CV text here:",
        value=cv_text,
        height=200,
        placeholder="Paste your CV text here..."
    )
    
    if custom_cv:
        cv_text = custom_cv
    
    col1, col2 = st.columns([1, 3])
    with col1:
        extract_button = st.button("🔍 Extract Profile", type="primary", use_container_width=True)
    
    if extract_button and cv_text:
        with st.spinner("Profile Agent is analyzing your CV..."):
            # Use the Profile Agent
            profile_agent = ProfileAgent()
            
            if ollama_ok:
                profile = profile_agent.extract_profile(cv_text)
            else:
                profile = profile_agent.extract_profile_simple(cv_text)
            
            # Store in session
            st.session_state.current_profile = profile
            
            st.success("✅ Profile extracted successfully!")
            show_profile_results(profile)
    
    elif extract_button and not cv_text:
        st.warning("Please select a sample CV or paste CV text.")
    
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


def show_matching_page(sample_jobs, ollama_ok):
    """Job Matching page - uses Matching Agent."""
    
    st.title("🎯 Job Matching")
    st.markdown("---")
    
    if not st.session_state.current_profile:
        st.warning("⚠️ No candidate profile yet. Please go to **Candidate Profile** page first and extract a profile.")
        return
    
    profile = st.session_state.current_profile
    st.success(f"Matching for: **{profile.get('personal_info', {}).get('name', 'Candidate')}**")
    
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
            
            # Find matches
            matches = matching_agent.find_matches(profile, sample_jobs, top_n=top_n)
            st.session_state.current_matches = matches
            
            st.success(f"Found {len(matches)} potential matches!")
    
    # Display matches
    if st.session_state.current_matches:
        matches = st.session_state.current_matches
        show_matches(matches)
    
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


def show_matches(matches):
    """Display job matches with scores and explanations."""
    
    st.subheader("Matching Results")
    
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


def show_application_page(sample_jobs, ollama_ok):
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
                
                if ollama_ok:
                    result = application_agent.generate_application(profile, selected_job)
                else:
                    result = application_agent.generate_application(profile, selected_job)
                    # Even in demo mode, use the generation (it has fallbacks)
                
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
                
                FRAUMATCH does **NOT** automatically submit applications.
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
            **FRAUMATCH Application Agent Disclaimer:**
            
            - All application materials are generated using **verified candidate information only**
            - The AI **never invents** experience, qualifications, skills, or achievements
            - The candidate **must approve** the application before it is sent
            - Applications are **never automatically submitted** to employers
            - FRAUMATCH assists but does **not** replace human recruiters
            """)


if __name__ == "__main__":
    main()
