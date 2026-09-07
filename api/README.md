# FRAUMATCH API (FastAPI)

This folder contains a minimal FastAPI backend scaffold for the FRAUMATCH proof-of-concept.

Run locally (example):

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Configure database via environment variables (see `.env.example`).
