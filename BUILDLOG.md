# Build Log

## 2024-01-XX - Project Initialization

**Tech Stack Decisions:**
- **Vision/Embeddings**: Gemini Flash free tier (Google AI Studio API key, no credit card required)
- **Backend**: Python 3.11+ with FastAPI
- **Database**: PostgreSQL via Docker (pgvector-ready design, no extension initially)
- **ORM**: SQLAlchemy 2.0 with asyncpg
- **Migrations**: Alembic
- **Config**: pydantic-settings with .env support

**AI Assistance**: This log, DESIGN.md, and initial project scaffolding were created with AI assistance (OpenCode/Nemotron). All architectural decisions reviewed and approved by human developer.

---

## 2024-01-XX - Phase 1 Design Complete

- Repository initialized with standard layout
- All required documentation files created
- DESIGN.md written covering all required sections
- Database migrations created (Alembic)
- Dataset fetch script and sample posts prepared
- Migrations verified against local Postgres

*Phase 2 (Vision Pipeline) and Phase 3 (Matching Engine + Guard) to follow.*