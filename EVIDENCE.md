# Evidence Log

This file tracks proof of completion for each requirement. Fill in as each item is done.

## Phase 1 Requirements

### 1. Repository Initialization & Project Layout
- [ ] Git repo initialized at `flyrank-capstone-imagerelevance`
- [ ] Standard Python/FastAPI layout (app/, tests/, scripts/, data/)
- [ ] `pyproject.toml` with dependencies
- [ ] `.gitignore` ignoring .env, __pycache__, venv, node_modules, large datasets
- [ ] MIT `LICENSE`

### 2. Required Documentation Files
- [ ] `README.md` with placeholder sections
- [ ] `capstone.yaml` manifest with run/seed/test/base_url/endpoints
- [ ] `EVIDENCE.md` (this file) with one heading per requirement
- [ ] `BUILDLOG.md` logging tech choices and AI assistance
- [ ] `.env.example` with GEMINI_API_KEY, DATABASE_URL placeholders

### 3. DESIGN.md
- [ ] Problem statement (2-3 sentences)
- [ ] Image metadata schema (JSON Schema / Pydantic model)
- [ ] Matching strategy sketch (cosine similarity, pgvector-ready)
- [ ] Mismatch guard sketch (tag match + similarity threshold + confidence floor)
- [ ] Database design (tables, PKs, FKs, indexes) as ERD or table list
- [ ] One explicit non-goal

### 4. Database Migrations
- [ ] Migration files created (Alembic or raw SQL)
- [ ] Tables: images, tags, embeddings, posts, suggestions, approvals
- [ ] Primary/foreign keys defined
- [ ] Indexes per DESIGN.md
- [ ] Migrations run cleanly against local Postgres

### 5. Image Dataset
- [ ] `scripts/fetch_dataset.py` downloads/references ~40-50 free-license images
- [ ] At least 4 categories (e.g., red fox, wolf, dog, bear, deer)
- [ ] Categories support fox vs wolf mismatch demo
- [ ] No large binaries committed (manifest/download script or lightweight images)
- [ ] `data/README.md` with image URLs + license attribution

### 6. Sample Blog Posts & Eval Set
- [ ] ~10 sample blog posts (.md or .json)
- [ ] At least one post about red foxes
- [ ] `eval_set.json` mapping post -> correct image filename