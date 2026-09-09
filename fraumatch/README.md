# MATCHA - Swiss Employment Matching Platform

A university proof-of-concept demonstrating AI-powered job matching for women job seekers in Switzerland.

> **No technical background needed.** This guide walks you through everything in plain language.

---

## Quick Start (Recommended: Demo Mode)

The app runs in **Demo Mode** by default — it works instantly with built-in sample data and **does not need any AI setup**. This is the most reliable option for your class presentation.

### Option A: Run on YOUR computer (VS Code)

**Step 1 — Check Python is installed**
1. Open the **Command Prompt** (press the `Windows` key, type `cmd`, press Enter)
2. Type `python --version` and press Enter
   - If you see something like `Python 3.x.x`, Python is installed → go to Step 2
   - If you see `'python' is not recognized`, you need to install it first:
     - Go to https://python.org/downloads
     - Click **Download Python**
     - Run the installer and **check the box "Add Python to PATH"** before clicking Install

**Step 2 — Open the project in VS Code**
1. Open **VS Code**
2. Click **File → Open Folder**
3. Navigate to the `matcha` folder
4. Click **Select Folder**

**Step 3 — Start the app**
1. Open the terminal: press **Ctrl + `** (the backtick key, next to the 1 key)
2. Type this and press Enter:
   ```
   pip install -r requirements.txt
   python -m streamlit run app.py
   ```
3. Your browser opens automatically at `http://localhost:8501`

> **Tip:** Use `python -m streamlit run app.py` (not just `streamlit run app.py`) — this avoids "streamlit not recognized" errors.

---

### Option B: Run in GitHub Codespaces (cloud, no install needed)

Codespaces runs everything in your browser — you don't need to install Python or anything on your own computer.

**Step 1 — Push the project to GitHub**

If you haven't yet, create a GitHub repository:
1. Go to https://github.com and sign in
2. Click the **+** in the top-right → **New repository**
3. Name it `matcha`
4. Click **Create repository**
5. Follow the on-screen instructions to push your existing code, OR upload the files by clicking **Add file → Upload files**

**Step 2 — Open a Codespace**
1. On your `matcha` repository page, click the green **Code** button
2. Switch to the **Codespaces** tab
3. Click **Create codespace on main** (free, loads in ~1 minute)

**Step 3 — Start the app**
1. In the Codespace terminal (bottom of the window), type:
   ```
   pip install -r requirements.txt
   python -m streamlit run app.py
   ```
2. Streamlit shows a URL like `http://localhost:8501`
3. Click the **Ports** tab in the Codespace, find port 8501, and click the 🌐 (Open in Browser) icon

> Codespaces gives you free compute hours monthly. If it asks, choose the smallest machine — it's plenty.

---

## How to Use the App

You must **create an account** or **log in** first (email + password). Your CV and profile are then saved securely to your account for future sessions.

After logging in, the app has **7 pages** in the left sidebar:

| Page | What it does |
|------|--------------|
| **Dashboard** | Live overview of the demo data (real vacancy count, sample profiles, your profile status), matching weights, shortcuts to every page, and the matching-efficiency experiment |
| **Candidate Profile** | Upload a CV (PDF/Word/TXT), use a sample CV, or paste text → watch the structured profile extraction |
| **Career Goals** | Onboarding wizard for explicit work preferences (employment %, salary, location, remote, career goals…) — see below |
| **Job Matching** | Find matching jobs → ranked results with scores, explanations & preference checks |
| **Areas to Improve** | A recommendation section based on your assessment: categorized **professional** and **administrative** areas to improve — see below |
| **Application Agent** | Generate a tailored cover letter & application |
| **My Account** | View your saved profile & preferences, reload them, see account details |

> **AI mode toggle:** In the left sidebar you can turn on **🤖 AI mode**. It's **off by default** so the demo is instant and reliable. Turn it on (requires Ollama) to get AI-written explanations and cover letters.

---

## 🎯 Career Goals & Work Preferences

The app collects **explicit, job-relevant preferences** directly from the candidate through an onboarding wizard (Step 1 is the professional profile, then Steps 2–6):

1. **Career Goals** — multi-select goals + optional free text (never ranked directly)
2. **Work Preferences** — 1–5 importance scales for working style, company size and work values
3. **Location & Remote Work** — preferred cities, max commute, relocation, work arrangement & remote importance
4. **Salary & Employment** — employment percentage (target / min / max / flexible), salary range + currency, "flexible / open to discussion"
5. **Review & Confirm** — the candidate sees a full summary and confirms before saving

**How preferences are stored & used**

- Stored **separately from the professional profile**, encrypted in the database (`candidate_preferences` table)
- Preferences feed the **deterministic matching engine** (not a separate AI score) using the same weights:
  **Employment = 10% · Location = 10% · Salary = 5% · Career Goals = 5%**
- Every recommendation shows a **"Why this job matches your preferences"** checklist (✓ / ⚠ / ℹ) generated only from the stored preferences and structured job data
- **No preference is ever a rejection**: a salary or employment mismatch only lowers the recommendation score, and 100% flexible options are treated as fully compatible
- A candidate can **edit preferences at any time** (re-run the wizard on the Career Goals page)

**Onboarding flow in the app:** ① *Candidate Profile* → ② Career Goals → ③ Work Preferences → ④ Location & Remote → ⑤ Salary & Employment → ⑥ Review & Confirm.

### ⚖️ Ethics: preferences, not personality

This feature intentionally **does not** implement a psychological personality test. It collects only explicit work-environment preferences.

- No personality scores, types, "culture fit", loyalty, retention, motivation or mental-state assessments are computed or stored
- Protected characteristics are never collected or used
- Missing preference data never penalizes a candidate (neutral scores)
- Career changes / career breaks are **not** penalized (they are treated as neutral or aligned)
- Work values are only used when the **job** contains the corresponding structured attribute

The UI tells the candidate: *"Your preferences describe the type of work environment you are looking for. They are used to improve job recommendations and are not used to assess your personality or personal worth."*

### 🔒 How your data is protected

- **Passwords** are stored as salted hashes (PBKDF2, 200,000 iterations) — never in plain text
- **CV content** is encrypted with AES (Fernet) before it is written to the database
- The **database** and **encryption key** are excluded from Git (see `.gitignore`)
- Each user can only access their **own** saved data
- The app **never automatically shares or submits** your CV anywhere

> This is a university proof-of-concept. A production deployment should add GDPR compliance documentation, password reset flows, and managed cloud hosting.

### Demo Flow for Class (Suggested Script)

0. **Register** a test account (e.g., `demo@matcha.ch`) → show the profile dashboard
1. **Dashboard** — Show the project overview, the **live demo-data overview** (vacancy count + sample profiles, all real data), the matching weights (30% skills, 20% experience, etc.), and the **"What you can do in MATCHA"** shortcut cards → click **Open** to jump straight into a page
2. **Candidate Profile** — Pick "Sophie Müller" → show the extracted profile → click **💾 Save to my account**
3. **Career Goals** — Fill in the wizard → show the Review & Confirm summary → save → show the ethics note ("preferences, not personality")
4. **Job Matching** — Click **Find Matching Jobs** → expand **"🎯 Why this job matches your preferences"** to show ✓/⚠ preference checks, and **"📈 Areas to improve for this role"** for the per-job gaps
5. **Areas to Improve** — Show the categorized professional + administrative recommendations (3.5% → "you have strong preferences, but need skills X and Y for your top role")
5. **My Account** — Show the saved profile *and preferences* were stored, then **Load my saved profile**
6. **Application Agent** — Select a job → generate a cover letter → check the approval step
7. **Dashboard → Matching Efficiency Experiment** — show Version A vs Version B telemetry

---

## 📈 Areas to Improve (Assessment & Recommendations)

The **Areas to Improve** page turns the candidate's assessment into **actionable, job-relevant recommendations** — split into two categories so the user can work on skills and on practical/admin setup separately:

| Category | What it contains |
|----------|------------------|
| **💼 Professional areas** | Gaps between the candidate's profile and their **best-fit positions**: missing required skills, language proficiency below the role's requirement (e.g. German B1 → C1), fewer experience years than required, education-level gaps, and optional "nice-to-have" credentials |
| **🗂️ Administrative & profile areas** | Profile completeness (contact info, summary, skills, work history, education, languages), setup of Career Goals & Preferences, and an optional hint about administrative skills **when the candidate's top roles are administrative** (e.g. coordinator/office roles) |

Every recommendation has a **priority** (🔴 High / 🟠 Medium / 🟡 Low) and a concrete **suggestion**. In **Job Matching**, each result also shows a compact **"📈 Areas to improve for this role"** expander (max 3 items) so the candidate knows right next to a match what would make them stronger for *that* job.

**How it works**

- The engine first ranks the candidate against the job pool (fast deterministic mode — no AI needed for the recommendations themselves), then derives gaps **only from the structured job data** (requirements, `skills_required`, generated language expectations) and the candidate's own profile
- Missing/unknown values are **neutral, never penalized**
- Career breaks are **not** penalized (the report explicitly says so in the work-history tip)
- Duplicate gaps are merged across jobs and list which roles they matter for

**Ethics (same contract as the rest of the app):** recommendations are job-relevant only. There is **no** personality, culture-fit, loyalty, retention, motivation or psychological assessment language, and no protected characteristics are used.

---

## 📊 Matching Efficiency Experiment (A vs B)

The app anonymously logs aggregate matching metadata (no personal data) so you can demonstrate whether **richer candidate preferences create business value**:

| Metric | Description |
|--------|-------------|
| Relevant recommendations | Matches with score ≥ 60 |
| Time to identify jobs | Wall-clock time per matching run |
| Jobs reviewed | Positions scanned before/among recommendations |
| First relevant match rank | How early a relevant job appears in the results |
| Score distribution | Share of matches in <25 / 25-50 / 50-75 / 75-100% |

- **Version A** = matching from the CV / professional information only
- **Version B** = CV + explicit candidate preferences

The Dashboard expander **"Matching Efficiency Experiment"** shows both versions side by side. Results come **only from real runs** — nothing is fabricated. Data file: `data/match_telemetry.jsonl` (git-ignored).

---

## 🧪 Running the Automated Tests

The preference model, matching rules and ethical safeguards are covered by a test suite:

```
python -m pytest tests/ -q
```

Run from the `matcha` folder. Tests cover the preference model & matching rules, the ethical safeguards, **and the assessment/recommendation engine** (professional gap detection, language/experience gaps, admin & profile-completeness items, deduplication across jobs, priority ordering, and the ethical rules — no personality traits, no protected characteristics, no career-break penalty).

---

## Project Structure

```
matcha/
├── app.py                    # Main Streamlit application
├── preferences_ui.py         # Career Goals & Preferences onboarding wizard
├── agents/
│   ├── profile_agent.py      # Agent 1: CV → Structured Profile
│   ├── matching_agent.py     # Agent 2: Deterministic Job Matching
│   ├── application_agent.py  # Agent 3: Tailored Applications
│   ├── preferences.py        # Structured preference model + compatibility rules
│   ├── assessment.py         # Areas-to-improve engine (professional + admin categories)
│   ├── telemetry.py          # Anonymized A/B matching-efficiency logging
│   └── db.py                 # Secure accounts + encrypted profile & preference storage
├── data/
│   ├── sample_cvs.json       # Demo candidate profiles
│   ├── sample_jobs.json      # Demo job listings (with structured attributes)
│   └── match_telemetry.jsonl # Generated at runtime (git-ignored)
├── tests/
│   ├── test_preferences.py   # Automated tests (49 cases)
│   └── test_assessment.py    # Assessment engine tests (15 cases)
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## Key Design Principles

1. **Transparency** — Every match shows its score breakdown **and** its preference checklist
2. **Human Control** — AI never makes hiring decisions
3. **No Fabrication** — AI only uses verified candidate information
4. **Deterministic Scoring** — Match scores come from rules, not AI
5. **AI for Explanation** — The LLM explains matches in plain language
6. **Preferences, not Personality** — Only explicit, job-relevant preferences are collected; no psychological assessments, and no automatic rejections based on salary or employment expectations
7. **Data Minimization** — Optional questions are optional, preference data is encrypted, and is used only for employment matching

---

## (Optional) Adding Real AI with Ollama

Demo mode works without AI, but if you want real AI-generated cover letters and explanations, you can run a free local AI with **Ollama**:

1. Download from https://ollama.com and install it
2. Open Command Prompt and run:
   ```
   ollama pull llama3.2
   ```
3. Restart the app (`python -m streamlit run app.py`)

> **Note:** On computers without a strong GPU, local AI can be slow. For a smooth class demo, stick with Demo Mode.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `'python' is not recognized` | Install Python and check "Add to PATH" |
| `'streamlit' is not recognized` | Use `python -m streamlit run app.py` |
| `App won't open` | Make sure you're in the `matcha` folder when you run the command |
| `Port already in use` | Run `python -m streamlit run app.py --server.port 8502` |

---

## About

This is a proof-of-concept for educational purposes. MATCHA does not replace recruiters, make hiring decisions, or automatically submit applications.
