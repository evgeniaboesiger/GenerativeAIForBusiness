# FRAUMATCH - Swiss Employment Matching Platform

A university proof-of-concept demonstrating AI-powered job matching for women job seekers in Switzerland.

## Quick Start (2 minutes)

### Option A: With AI (Ollama - Free, runs locally)

1. **Install Ollama** (free, ~5 minutes):
   - Go to [ollama.com](https://ollama.com) and download for Windows
   - Install and run it
   - Open Command Prompt and run:
     ```
     ollama pull llama3.2
     ```

2. **Open VS Code** and open the `fraumatch` folder

3. **Run the setup**:
   - Open the integrated terminal (View → Terminal)
   - Run: `python setup.bat`

4. **The app** will open in your browser automatically

### Option B: Without AI (Demo mode with sample data)

1. Open VS Code and open the `fraumatch` folder
2. In the integrated terminal, run:
   ```
   pip install streamlit requests
   python -m streamlit run app.py
   ```

## How to Use the App

The app has 4 pages in the left sidebar:

| Page | What it does |
|------|--------------|
| **Dashboard** | Overview of the project and impact metrics |
| **Candidate Profile** | Paste a CV → AI extracts a structured profile |
| **Job Matching** | See ranked job matches with explanations |
| **Application Agent** | Generate a tailored cover letter & application |

### Demo Flow for Class:

1. **Dashboard** - Show the project overview and matching weights
2. **Candidate Profile** - Pick a sample CV → watch the AI extract structured info
3. **Job Matching** - Click "Find Matching Jobs" → show ranked results with scores
4. **Application Agent** - Select a job → generate cover letter → approve it

## Project Structure

```
fraumatch/
├── app.py                    # Main Streamlit application
├── agents/
│   ├── profile_agent.py      # Agent 1: CV → Structured Profile
│   ├── matching_agent.py     # Agent 2: Deterministic Job Matching
│   └── application_agent.py  # Agent 3: Tailored Applications
├── data/
│   ├── sample_cvs.json       # Demo candidate profiles
│   └── sample_jobs.json      # Demo job listings
├── requirements.txt          # Python dependencies
├── setup.bat                # One-click setup
└── run.bat                  # Quick launch
```

## Key Design Principles

1. **Transparency** - Every match shows its score breakdown
2. **Human Control** - AI never makes hiring decisions
3. **No Fabrication** - AI only uses verified candidate information
4. **Deterministic Scoring** - Match scores come from rules, not AI
5. **AI for Explanation** - The LLM explains matches in plain language

## Troubleshooting

**Problem:** "streamlit is not recognized"
**Fix:** `pip install streamlit` then try again

**Problem:** App won't connect to AI
**Fix:** Make sure Ollama is running (look for Ollama icon in taskbar)

**Problem:** Port already in use
**Fix:** Run with a different port: `streamlit run app.py --server.port 8502`

## About

This is a proof-of-concept for educational purposes. FRAUMATCH does not replace recruiters, make hiring decisions, or automatically submit applications.
