# FlyRank Capstone: AI Image Understanding & Content Matching Engine

## What it does

This system classifies images with a vision model (Gemini Flash), embeds images and blog posts into a shared vector space, ranks candidate images per post, and runs every ranked candidate through a "mismatch guard" — a safety layer that rejects wrong pairings (e.g. a wolf photo for a fox post) with a human-readable explanation. If nothing clears the bar, it returns "no confident match" with reasons instead of guessing.

## Architecture

*Diagram TBD*

Components:
- **Vision Pipeline**: Gemini Flash free tier for image classification and captioning
- **Embedding Engine**: Shared vector space for images and blog posts
- **Matching Service**: Cosine similarity ranking with pgvector-ready design
- **Mismatch Guard**: Tag validation + similarity threshold + confidence floor
- **API Layer**: FastAPI endpoints for suggestions, approvals, rejections

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
# Edit .env with your GEMINI_API_KEY and DATABASE_URL

# Start PostgreSQL (Docker)
docker compose up -d

# Run migrations
alembic upgrade head

# Seed database
python scripts/seed.py

# Run API server
uvicorn app.main:app --reload
```

## Seed steps

1. Run `scripts/fetch_dataset.py` to download ~40-50 free-license images
2. Run `scripts/seed.py` to populate database with images, tags, posts, and eval set
3. Verify with `GET /health` and `GET /images`

## Limitations

- Uses Gemini Flash free tier (rate limits apply)
- No pgvector extension initially (~50 images, in-Postgres array storage)
- API-only review interface (no frontend UI)
- Single-user design (no auth/tenancy)
- English-only content for MVP