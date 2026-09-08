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
   pip install streamlit requests pypdf python-docx
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
   pip install streamlit requests pypdf python-docx
   python -m streamlit run app.py
   ```
2. Streamlit shows a URL like `http://localhost:8501`
3. Click the **Ports** tab in the Codespace, find port 8501, and click the 🌐 (Open in Browser) icon

> Codespaces gives you free compute hours monthly. If it asks, choose the smallest machine — it's plenty.

---

## How to Use the App

The app has **4 pages** in the left sidebar:

| Page | What it does |
|------|--------------|
| **Dashboard** | Overview of the project + impact metrics |
| **Candidate Profile** | Upload a CV (PDF/Word/TXT), use a sample CV, or paste text → watch the structured profile extraction |
| **Job Matching** | Find matching jobs → ranked results with scores & explanations |
| **Application Agent** | Generate a tailored cover letter & application |

> **AI mode toggle:** In the left sidebar you can turn on **🤖 AI mode**. It's **off by default** so the demo is instant and reliable. Turn it on (requires Ollama) to get AI-written explanations and cover letters.

### Demo Flow for Class (Suggested Script)

1. **Dashboard** — Show the project overview and the matching weights (30% skills, 20% experience, etc.)
2. **Candidate Profile** — Pick "Sophie Müller" → show the extracted profile (skills, experience, languages, preferences)
3. **Job Matching** — Click **Find Matching Jobs** → show ranked results with scores and "why this match" explanations
4. **Application Agent** — Select a job → generate a cover letter → check the approval step

---

## Project Structure

```
matcha/
├── app.py                    # Main Streamlit application
├── agents/
│   ├── profile_agent.py      # Agent 1: CV → Structured Profile
│   ├── matching_agent.py     # Agent 2: Deterministic Job Matching
│   └── application_agent.py  # Agent 3: Tailored Applications
├── data/
│   ├── sample_cvs.json       # Demo candidate profiles
│   └── sample_jobs.json      # Demo job listings
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## Key Design Principles

1. **Transparency** — Every match shows its score breakdown
2. **Human Control** — AI never makes hiring decisions
3. **No Fabrication** — AI only uses verified candidate information
4. **Deterministic Scoring** — Match scores come from rules, not AI
5. **AI for Explanation** — The LLM explains matches in plain language

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
