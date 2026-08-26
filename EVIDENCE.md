# Evidence Log

This file tracks proof of completion for each requirement. Fill in as each item is done.

## Phase 1 Requirements

### 1. Repository Initialization & Project Layout
- [x] Git repo initialized at `flyrank-capstone-imagerelevance`
- [x] Standard Python/FastAPI layout (app/, tests/, scripts/, data/)
- [x] `pyproject.toml` with dependencies
- [x] `.gitignore` ignoring .env, __pycache__, venv, node_modules, large datasets
- [x] MIT `LICENSE`

### 2. Required Documentation Files
- [x] `README.md` with placeholder sections
- [x] `capstone.yaml` manifest with run/seed/test/base_url/endpoints
- [x] `EVIDENCE.md` (this file) with one heading per requirement
- [x] `BUILDLOG.md` logging tech choices and AI assistance
- [x] `.env.example` with GEMINI_API_KEY, DATABASE_URL placeholders

### 3. DESIGN.md
- [x] Problem statement (2-3 sentences)
- [x] Image metadata schema (JSON Schema / Pydantic model)
- [x] Matching strategy sketch (cosine similarity, pgvector-ready)
- [x] Mismatch guard sketch (tag match + similarity threshold + confidence floor)
- [x] Database design (tables, PKs, FKs, indexes) as ERD or table list
- [x] One explicit non-goal

### 4. Database Migrations
- [x] Migration files created (Alembic or raw SQL)
- [x] Tables: images, tags, embeddings, posts, suggestions, approvals
- [x] Primary/foreign keys defined
- [x] Indexes per DESIGN.md
- [x] Migrations run cleanly against local Postgres

### 5. Image Dataset
- [x] `scripts/fetch_dataset.py` downloads/references ~40-50 free-license images
- [x] At least 4 categories (e.g., red fox, wolf, dog, bear, deer)
- [x] Categories support fox vs wolf mismatch demo
- [x] No large binaries committed (manifest/download script or lightweight images)
- [x] `data/README.md` with image URLs + license attribution

### 6. Sample Blog Posts & Eval Set
- [x] ~10 sample blog posts (.md or .json)
- [x] At least one post about red foxes
- [x] `eval_set.json` mapping post -> correct image filename

## Phase 2 Requirements

### 1. Gemini Flash Integration
- [ ] `app/services/vision.py` with structured output (JSON mode)
- [ ] Validates against Pydantic schema from `app/schemas/vision.py`
- [ ] Retries once with stricter prompt on validation failure
- [ ] Marks validation failures with `validation_status="failed"`

### 2. Low-Confidence Flagging
- [ ] `needs_review` column added to images table via migration
- [ ] `CONFIDENCE_FLOOR = 0.6` constant shared with Phase 3
- [ ] Flag triggers on at least one real image in dataset

### 3. Batch Processing with Retries
- [ ] `app/services/batch.py` with ThreadPoolExecutor (3 workers)
- [ ] Retry logic: 3 retries with exponential backoff (1s, 2s, 4s)
- [ ] Progress tracking via logging

### 4. Cost Tracking
- [ ] `api_calls` table with per-image tracking
- [ ] Records: image_id, model, timestamp, tokens, estimated_cost_usd, status
- [ ] Queryable/summable for total cost reporting

### 5. Runner Script
- [ ] `scripts/run_vision_pipeline.py` processes all 34 images
- [ ] Prints summary: processed, flagged, failed, cost
- [ ] Exits with error code on failures

### 6. Tests
- [ ] `tests/test_vision.py` with schema validation tests
- [ ] Tests: valid input passes, missing/malformed fields fail
- [ ] Test: confidence < 0.6 triggers needs_review
- [ ] Mocks Gemini API (no real calls in tests)

### 7. capstone.yaml Updated
- [ ] Added `vision:` section with run command