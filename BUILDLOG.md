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

---

## 2024-01-XX - Phase 2 Vision Pipeline Complete

**Code Changes:**
- Added `app/schemas/vision.py` with `ImageMetadata` and `VisionResult` Pydantic models
- Added `CONFIDENCE_FLOOR = 0.6` constant shared with Phase 3 guard
- Created Alembic migrations for `needs_review`, `validation_status` on images table, and new `api_calls` table
- Added `app/models/api_call.py` for cost tracking
- Implemented `app/services/vision.py` with Gemini Flash integration:
  - Structured output via `response_mime_type="application/json"`
  - Validation against Pydantic schema
  - Single retry with stricter prompt on validation failure
  - Marks failures with `validation_status="failed"` (never silently accepts)
- Implemented `app/services/batch.py` with ThreadPoolExecutor (3 workers):
  - Retry logic: 3 retries with exponential backoff (1s, 2s, 4s)
  - Progress tracking via logging
  - Per-image cost tracking in `api_calls` table
- Created `scripts/run_vision_pipeline.py` runner script with summary output
- Added `app/core/env_check.py` to ensure `.env` exists with valid `GEMINI_API_KEY`
- Updated `capstone.yaml` with `vision:` section

**Tests:**
- 16 tests in `tests/test_vision.py` covering schema validation and confidence floor logic
- All tests pass with mocked Gemini API (no real API calls in tests)

**AI Assistance**: Vision service, batch processor, schemas, migrations, runner script, and tests created with AI assistance. Human review of all architectural decisions.