# FlyRank Capstone: AI Image Understanding & Content Matching Engine

## What it does

This system classifies images with a vision model (Ollama llava), embeds images and blog posts into a shared vector space using Ollama nomic-embed-text, ranks candidate images per post by cosine similarity, and runs every ranked candidate through a "mismatch guard" — a three-signal AND gate (category match + similarity threshold + confidence floor) that rejects wrong pairings (e.g. a wolf photo for a fox post) with a human-readable explanation. If nothing clears the bar, it returns "no confident match" with reasons instead of guessing.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Images    │     │    Posts    │     │  nomic-embed-text │
│  (26 files) │     │   (10 blog) │────▶│   (768-dim, local)│
└──────┬──────┘     └──────┬──────┘     └────────┬─────────┘
       │                   │                      │
       ▼                   ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    EMBEDDING GENERATION                      │
│  Images: caption + subject + attributes  →  FLOAT[768]     │
│  Posts:  title + body (truncated)         →  FLOAT[768]     │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    MATCHING ENGINE                           │
│  1. Compute cosine similarity (post_emb vs image_emb)       │
│  2. Rank candidates by similarity (top-5 per post)          │
│  3. Run MISMATCH GUARD (3-signal AND gate):                 │
│     ✓ Category match: image.category == post.target_category│
│     ✓ Similarity ≥ 0.65 (SIMILARITY_THRESHOLD)              │
│     ✓ Confidence ≥ 0.60 (CONFIDENCE_FLOOR)                  │
│  4. ACCEPT if ALL pass, else REJECT with specific reason    │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                               │
│  GET  /posts/{id}/suggestions  → top-5 with guard results   │
│  POST /suggestions/{id}/approve → record approval           │
│  POST /suggestions/{id}/reject  → record rejection          │
│  GET  /posts/{id}/approved-image → final approved image     │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. **Vision Pipeline** (Phase 2): `ollama llava` → classifies 26 images into 5 categories (vulpine, canid_dog, canid_wolf, ursid, cervid)
2. **Embedding Generation** (Phase 3): `ollama nomic-embed-text` → 768-dim vectors stored as `FLOAT[]` in PostgreSQL
3. **Matching Engine** (Phase 3): Cosine similarity + mismatch guard → ranked suggestions with ACCEPT/REJECT
4. **API Layer** (Phase 3-4): FastAPI endpoints for suggestions, approvals, rejections

## Setup & run

```bash
# Clone and enter
git clone <repo-url>
cd flyrank-capstone-imagerelevance

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your OLLAMA_HOST and OLLAMA_MODEL (defaults work for local Ollama)

# Ensure Ollama is running with required models
ollama pull llava
ollama pull nomic-embed-text
ollama serve

# Start PostgreSQL (Docker)
docker compose up -d

# Run migrations
alembic upgrade head

# Seed database with 26 verified images + 10 posts + eval set
python scripts/seed_v2.py

# Run vision pipeline (local Ollama, no quota, resumable)
python scripts/run_vision_pipeline.py

# Generate embeddings for images + posts
python scripts/run_embeddings.py

# Run matching pipeline (generates suggestions with guard evaluation)
python scripts/run_matching.py

# Evaluate TOP-1 precision against eval set
python scripts/eval_precision.py

# Run API server
uvicorn app.main:app --reload
```

## Seed steps

1. **Dataset**: 26 verified images sourced from Pexels/Unsplash (see `data/manifest_v3.json`)
2. **Seed database**: `python scripts/seed_v2.py` → populates images, tags, posts, eval_set.json
3. **Vision classification**: `python scripts/run_vision_pipeline.py` → runs Ollama llava on all images
4. **Embeddings**: `python scripts/run_embeddings.py` → generates nomic-embed-text vectors
5. **Matching**: `python scripts/run_matching.py` → generates suggestions with guard evaluation
6. **Evaluation**: `python scripts/eval_precision.py` → computes TOP-1 precision

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/posts/{id}/suggestions` | Top-5 ranked images with guard evaluation (ACCEPT/REJECT + reason) |
| POST | `/suggestions/{id}/approve` | Record approval decision for a suggestion |
| POST | `/suggestions/{id}/reject` | Record rejection decision for a suggestion |
| GET | `/posts/{id}/approved-image` | Get the approved image for a post (if any) |

**Example response** (`GET /posts/{id}/suggestions`):
```json
{
  "post_id": "uuid",
  "post_title": "The Secret Life of Red Foxes",
  "post_target_category": "vulpine",
  "suggestions": [
    {
      "rank": 1,
      "image_id": "uuid",
      "filename": "vulpine_00.jpg",
      "subject": "red fox",
      "category": "vulpine",
      "confidence": 1.00,
      "similarity_score": 0.7285,
      "guard_passed": true,
      "guard_reason": "All guard checks passed",
      "details": {"category_match": true, "similarity_score": 0.7285, ...}
    }
  ],
  "accepted_count": 2,
  "rejected_count": 3,
  "no_confident_match": false
}
```

## Run tests

```bash
# All tests (fast, no external dependencies)
pytest tests/ -v

# Specific test groups
pytest tests/test_vision.py -v        # 16 vision schema/confidence tests
pytest tests/test_matching.py -v      # 16 matching/guard logic tests  
pytest tests/test_eval_precision.py -v -s  # 6 eval/API tests (prints precision)
```

## Eval Methodology Note

**TOP-1 Precision: 20% (2/10)** — The eval set designates ONE correct image per post, but our dataset has **2+ valid same-category images per category** that all legitimately pass the mismatch guard. **7 of the 8 "misses" are cases where the system ranked a different, equally valid same-category image higher** — not cases where it picked something wrong.

**Concrete examples:**
- **Wolf posts**: Both `canid_wolf_00.jpg` (sim=0.757) and `canid_wolf_02.jpg` (sim=0.762) pass the guard. The eval set picked `canid_wolf_00.jpg` as "correct," but `canid_wolf_02.jpg` ranked #1 by 0.005 similarity margin — essentially tied.
- **Bear posts**: `ursid_00.jpg` (sim=0.718) and `ursid_01.jpg` (sim=0.742) both pass; eval chose one, system ranked the other first.
- **Dog post 1**: `canid_dog_00.jpg` (sim=0.666) ranked #6, cut by `top_k=5`; 5 other valid dogs ranked higher.

**TOP-5 Recall: 90% (9/10)** — The correct image appears in the top-5 guard-passed suggestions for 9 of 10 posts, confirming the system finds relevant matches. TOP-1 precision is misleading here because the eval set forces a single "correct" answer where multiple valid same-category candidates exist.

**One genuine issue (flagged separately):** "Understanding Your Dog's Body Language" ranks `vulpine_01.jpg` (a fox misclassified as `canid_dog` in Phase 2) at #1. This is a **vision-tagging error cascading into the guard** — the guard correctly trusts the category it was given and cannot self-correct a wrong upstream tag. This is a known Phase 2 vision limitation (vulpine→canid_dog confusion), not a matching bug.

---

## Limitations (honest documentation)

1. **Vulpine classification accuracy: 33% (2/6)** — Local `llava:7B` model cannot reliably distinguish red foxes from domestic dogs on visually similar images. 4/6 fox images are misclassified as `canid_dog`. All other categories (wolf, bear, deer, dog) achieve 100% on our 26-image verified dataset. This is a known limitation of small local vision models on visually similar canid species.

2. **Dataset size: 26 images** — Originally planned 40-50, but sourcing verified free-license images with reliable category labels proved harder than expected. Pexels API + manual curation yielded 26 high-quality images across 5 categories. The eval set uses only correctly-tagged images as ground truth (vulpine_00.jpg, vulpine_05.jpg for fox posts), so reported precision reflects matching+guard accuracy on correctly-tagged images only.

3. **TOP-1 Precision: 20% (2/10)** — The eval set arbitrarily picks one "correct" image per post, but semantic similarity ranks by overall content match, not a specific pre-chosen image. The system is designed to return multiple good candidates (top-5) rather than guarantee a specific arbitrary choice at rank 1.

4. **Local models throughout** — Both vision (`llava`) and embeddings (`nomic-embed-text`) run locally via Ollama. No API keys, no quotas, no external dependencies. Trade-off: smaller models have lower accuracy than cloud alternatives.

5. **Scenario 9 (no confident match) — dataset limitation** — Every category in our dataset has matching images, so the "no confident match" code path isn't exercised by real data. The guard logic is tested via unit tests; the API returns the structure but real data always has candidates.

6. **No pgvector extension** — Embeddings stored as `FLOAT[768]` (`ARRAY(Float)`) in PostgreSQL. pgvector-ready design: column type compatible, migration path documented in `DESIGN.md`.

7. **API-only review interface** — No frontend UI. Single-user design (no auth/tenancy). English-only content for MVP.

## Project structure

```
flyrank-capstone-imagerelevance/
├── app/
│   ├── api/suggestions.py      # FastAPI endpoints
│   ├── core/config.py          # Settings (thresholds, Ollama config)
│   ├── db/                     # SQLAlchemy models, session, migrations
│   ├── models/                 # Image, Post, Suggestion, Approval, Tag
│   ├── schemas/vision.py       # Pydantic models for vision output
│   ├── services/
│   │   ├── embedding.py        # nomic-embed-text via Ollama
│   │   ├── matching.py         # Cosine similarity + mismatch guard
│   │   ├── vision.py           # llava vision classification
│   │   └── batch.py            # Resumable batch processor
│   └── main.py                 # FastAPI app
├── scripts/
│   ├── seed_v2.py              # Seed DB with images/posts/eval_set
│   ├── run_vision_pipeline.py  # Vision classification (Ollama)
│   ├── run_embeddings.py       # Embedding generation
│   ├── run_matching.py         # Matching pipeline + guard
│   ├── eval_precision.py       # TOP-1 precision evaluation
│   └── fetch_dataset_pexels.py # Pexels API fetcher
├── data/
│   ├── manifest_v3.json        # 26 verified image metadata
│   └── eval_set.json           # 10 post UUID → correct image mapping
├── tests/
│   ├── test_vision.py          # 16 tests: schema, confidence floor
│   ├── test_matching.py        # 16 tests: guard logic, cosine similarity
│   └── test_eval_precision.py  # 6 tests: precision, API endpoints
└── alembic/                    # Database migrations
```