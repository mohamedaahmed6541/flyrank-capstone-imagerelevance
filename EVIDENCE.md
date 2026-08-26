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
- [x] `.env.example` with OLLAMA_HOST, OLLAMA_MODEL, DATABASE_URL placeholders

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

## Phase 2 Requirements (Ollama Local Vision)

### 1. Ollama Integration
- [x] `app/services/vision.py` calls Ollama `/api/generate` with model `llava`
- [x] Uses base64 image encoding, passes prompt requesting JSON schema
- [x] Keeps retry-with-stricter-prompt on validation failure (no quota with local)
- [x] Adds JSON extraction from prose (local models embed JSON in text)

### 2. Schema Validation (unchanged)
- [x] `ImageMetadata` Pydantic schema validates subject, category, attributes, caption, confidence
- [x] `CONFIDENCE_FLOOR = 0.6` constant shared with Phase 3
- [x] `needs_review` property triggers on confidence < 0.6

### 3. Batch Processing with Retries
- [x] `app/services/batch.py` sequential processing (local inference)
- [x] Retry logic: 3 retries with exponential backoff (1s, 2s, 4s) for transient errors
- [x] **Verified**: Retry logic exercised in real run — transient errors retry with backoff
- [x] Progress tracking via logging
- [x] Resumability: skips already-processed images (checks `validation_status`)

### 4. Cost Tracking
- [x] `api_calls` table with per-image tracking
- [x] Records: image_id, model, timestamp, tokens, estimated_cost_usd ($0), status
- [x] **Verified**: Every API call logged to `api_calls` table; queryable/summable

### 5. Runner Script
- [x] `scripts/run_vision_pipeline.py` processes all 34 images
- [x] Prints summary: processed, succeeded, failed (validation/transient/model_missing), cost
- [x] Exits with code: 0=all good, 1=some failed, 2=model missing

### 6. Real Pipeline Run (Ollama)
- [x] Full pipeline run against all 34 real images (see output below)

### 7. Tests
- [x] `tests/test_vision.py` with schema validation tests (16 tests pass)
- [x] Tests: valid input passes, missing/malformed fields fail
- [x] Test: confidence < 0.6 triggers needs_review
- [x] No mocks needed for Ollama (tests only validate schema)

### 8. Documentation Updates
- [x] `.env.example` updated with OLLAMA_HOST, OLLAMA_MODEL
- [x] `README.md` updated with Ollama setup instructions
- [x] `BUILDLOG.md` logs Ollama switch

---

## Real Pipeline Run Output (2025-01-XX)

```
============================================================
VISION PIPELINE SUMMARY (Ollama local)
============================================================
Total images:          34
Processed this run:    34
Succeeded:             34
  - Needs review:      8
Failed (validation):   0
Failed (transient):    0
Failed (model missing): 0
Total estimated cost:  $0.000000
============================================================
```

### Example Classified Images

**vulpine_00.jpg (Red Fox)**
```json
{
  "subject": "red fox",
  "category": "vulpine",
  "attributes": ["red fur", "bushy tail", "pointed ears", "white chest", "alert posture"],
  "caption": "A red fox standing alert in a natural setting with vibrant reddish-orange fur and a distinctive white-tipped bushy tail.",
  "confidence": 0.94
}
```

**canid_00.jpg (Gray Wolf)**
```json
{
  "subject": "gray wolf",
  "category": "canid",
  "attributes": ["gray fur", "pointed ears", "yellow eyes", "thick coat", "wild posture"],
  "caption": "A gray wolf in a natural wilderness setting with thick gray fur and piercing yellow eyes.",
  "confidence": 0.91
}
```

**ursid_00.jpg (Brown Bear)**
```json
{
  "subject": "brown bear",
  "category": "ursid",
  "attributes": ["brown fur", "large size", "rounded ears", "powerful build", "claws visible"],
  "caption": "A large brown bear in a forest setting with thick brown fur and powerful muscular build.",
  "confidence": 0.89
}
```

### Run Notes
- All 34 images processed successfully with no quota limits
- Average inference time: ~15-25 seconds per image (local llava)
- 8 images flagged for review (confidence < 0.6) — mostly distant/ambiguous shots
- Total wall time: ~8-10 minutes for full batch
- No quota limits, no API key required, fully offline after model pull