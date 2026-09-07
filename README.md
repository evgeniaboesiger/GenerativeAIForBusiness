# FRAUMATCH — GenerativeAIForBusiness Workspace

This workspace contains the FRAUMATCH proof-of-concept application: a Swiss government-supported employment matching platform focused on helping women job seekers and recruiters. It includes a Next.js + TypeScript frontend and a FastAPI backend with PostgreSQL schema and seed data.

Work is organized into:
- `web/` — Next.js frontend (TypeScript, Tailwind, shadcn/ui placeholders)
- `api/` — FastAPI backend (Python)
- `db/` — Database schema and seed SQL

See `web/README.md` and `api/README.md` for run instructions.

Architecture overview:
- The deterministic matching engine and demo dataset live in `api/` and `db/`.
- Matching runs and performance logs are stored in PostgreSQL (`db/schema.sql`).
- High-level architecture and flow are documented in [ARCHITECTURE.md](ARCHITECTURE.md).

# GenerativeAIForBusiness