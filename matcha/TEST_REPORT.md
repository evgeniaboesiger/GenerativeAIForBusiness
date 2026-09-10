# MATCHA — Whole-Program Test Report

Date: 2026-09-10 (initial round 2026-09-09)
Scope: the complete MATCHA Streamlit application in `matcha/` (12 pages/flows, EN + DE, fresh database).
Method: the whole program was tested **twice** — once before fixing (baseline) and once more after the fixes — using three layers:

1. **Unit/integration suite** — `python -m pytest tests/ -q`: **92 passed** at baseline, **101 passed** after fixes, **104 passed** as of the second test round (2026-09-10).
2. **Three AppTest smoke scripts** (`smoke_i18n`, `smoke_account`, `smoke_job_carryover`): all pass.
3. **Comprehensive end-to-end AppTest walkthrough** (`e2e_full.py`): **34 checks** covering every page in both languages on a fresh DB, plus cross-session persistence. All pass (run on baseline and again after fixes).

The e2e walkthrough exercises: auth (EN + DE), wrong-password rejection, duplicate registration, registration auto-login, all 7 side-bar pages, no-profile guard states, sample-CV extraction, .txt upload through the document pipeline, paste-CV extraction, the 6-step Career Goals wizard (including Step 6 deal-breakers), matching, job selection carry-over to the Application Agent, application generation/approval/send, submitted-application tracking on My Account, name edit save + cancel, and persistence of login/name/applications across fresh sessions.

---

## Bugs found and how they were addressed

### BUG 1 — HIGH: AI explanations silently never used Ollama
- **Where:** `matcha/agents/matching_agent.py`
- **What:** `_generate_ai_explanation()` calls `requests.post(...)` (line ~514) but `requests` was **never imported** in that module. Every call raised `NameError`, which was swallowed by the surrounding `except Exception`, so the match explanation *always* fell back to the fast deterministic text — even when Ollama was running and AI mode was on. The app showed no error, which is why it went unnoticed (and only the application agent and `app.py` imported `requests`, masking the pattern).
- **How detected:** static review (the two generated code paths visually looked identical), confirmed that only `application_agent.py` and `app.py` import `requests`.
- **Fix:** added `import requests` to `matching_agent.py`.
- **Verification:** new regression test `test_ai_explanation_uses_ollama_when_available` monkeypatches `matching_agent.requests` and asserts the AI branch is actually reached and returned when Ollama responds.

### BUG 2 — MEDIUM: Deal-breakers set in the wizard were never enforced
- **Where:** `matcha/preferences_ui.py` (Step 6) vs. `matcha/agents/matching_agent.py`
- **What:** the Career Goals wizard collects Ideal/Acceptable/**Deal-breaker** tiers and its intro states *"Jobs that violate a deal-breaker are not recommended to you."* However the app's matching engine never read `preference_tiers` — a part-time (60%) job could be recommended as if fully compatible even when the candidate set a 100%-only deal-breaker. (The separate FastAPI service under `api/` implements tiered matching; the Streamlit app did not.)
- **How detected:** grep showed `preference_tiers` only used in `preferences_ui.py`/`preferences.py`/tests — never in `matching_agent.py`; the UI promise (line ~497) had no backing implementation.
- **Fix:** added `tier_violation_reasons(raw_prefs, job)` to `agents/preferences.py` (pure, deterministic) and wired it into `MatchingAgent.find_matches()`:
  - a job that violates any deal-breaker is marked `mandatory_met = False` (i.e. not recommended / not selectable),
  - a `"Deal-breaker: …"` warning check is added to the match explanation for transparency,
  - dimensions with no stored tier or a job with missing data are never treated as violations (no unfair filtering).
- **Verification:** 8 new tests in `tests/test_preferences.py` (employment, salary floor, salary ceiling, commute, remote, weekend negation-aware, preference tiers can't alter recommendations when absent, missing job info never counts). The e2e walkthrough also sets a real 100%-only deal-breaker through the wizard and asserts the engine filters the 60% job but keeps the 100% job against the real `sample_jobs.json`.

### BUG 3 — LOW: misleading copy on the auth page
- **Where:** `matcha/app.py`
- **What:** after registration the app auto-logs the new user in, but the success message said *"Please now log in with your new password."* The demo caption also claimed you could *"use any email + password you make up for a quick login"* — not true, accounts must exist.
- **How detected:** end-to-end walkthrough of the register flow (message contradicts observed auto-login); code review of `login_user`.
- **Fix:** registration now says the account was created and the user is logged in; demo tip now only mentions creating a test account.

### Checked and confirmed NOT bugs
- The `smoke_i18n` "DE auth title missing" line: a test-harness artifact (`str(proto)` ignores `.value`), the actual assertion on the rendered German title passes — German titles render correctly.
- Name-edit cancel/save, submitted-application persistence, OCR Tesseract resolution, both-language labels, dashboard shortcuts, and matching weights: all verified in the e2e walkthrough.

---

## Final status
- `python -m pytest tests/ -q` → **104 passed**
- 3 smoke scripts → **passed**
- e2e walkthrough (34 checks, EN + DE, fresh DB) → **passed**, run twice
- Repository: fixes + regression tests + this report committed on `main` and pushed.

## Second round (2026-09-10) — additional fixes

### BUG 4 — MEDIUM: mandatory language check only required one of several languages
- **Where:** `matcha/agents/matching_agent.py`
- **What:** when a job requirement named several languages (e.g. "German and English"), the check only required **one** of them to be present in the CV, so candidates speaking just one were wrongly accepted.
- **Fix:** `_check_mandatory_requirements` now extracts every language keyword from the requirement and requires each one (word-boundary matching via `MANDATORY_LANGUAGE_KEYWORDS`).
- **Verification:** 3 new tests — multi-language mandatory requirement, single-language requirement, and flexible employment marking (`test_preferences.py`). Suite grew **101 → 104**.

### BUG 5 — LOW: "Flexible" salary target left `employment_flexible` unset
- **Where:** `matcha/preferences_ui.py` (`_step_salary`)
- **What:** choosing a flexible salary target in the wizard did not set the `employment_flexible` preference, so downstream matching treated employment flexibility as unknown.
- **Fix:** `_set_value("employment_flexible", _pct_from_label(target) is None)` when the chosen target is "Flexible".
- **Verification:** covered by the new flexible-employment test (summary text + stored value).

### Checked and confirmed still NOT bugs (second round)
- Preference save/load round-trip only stores explicitly-set keys; defaults are applied on read (`load_preferences` returns a sparse dict). Not a defect.
- Requirement checks and scores are deterministic across repeated `find_matches` runs (no hidden randomness).

## How to reproduce
```
cd matcha
python -m pytest tests/ -q
python C:\Users\pocha\AppData\Local\Temp\opencode\smoke_i18n.py
python C:\Users\pocha\AppData\Local\Temp\opencode\smoke_account.py
python C:\Users\pocha\AppData\Local\Temp\opencode\smoke_job_carryover.py
python C:\Users\pocha\AppData\Local\Temp\opencode\e2e_full.py   # uses a fresh temp DB per run
```