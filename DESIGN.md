# Design Document: AI Image Understanding & Content Matching Engine

## Problem Statement

Blog platforms and content management systems struggle to automatically pair articles with relevant, accurate images. Generic stock photos often mismatch the specific subject (e.g., a wolf photo for a "red fox behavior" article), misleading readers and damaging credibility. This system classifies images with a vision model, embeds both images and posts into a shared vector space, ranks candidates by semantic similarity, and applies a "mismatch guard" that rejects semantically-close but factually-wrong pairings with human-readable explanations.

---

## Image Metadata Schema

### Pydantic Model (Vision Output)

```python
from pydantic import BaseModel, Field, field_validator
from typing import List

class ImageMetadata(BaseModel):
    """Structured output from vision model classification."""
    subject: str = Field(..., min_length=1, max_length=100, description="Primary subject (e.g., 'red fox', 'gray wolf')")
    category: str = Field(..., min_length=1, max_length=50, description="Broad category (e.g., 'canid', 'cervid', 'ursid')")
    attributes: List[str] = Field(default_factory=list, description="Visual attributes (e.g., ['red fur', 'bushy tail', 'pointed ears'])")
    caption: str = Field(..., min_length=10, max_length=500, description="Natural language description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in classification")

    @field_validator('subject', 'category')
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Field cannot be empty or whitespace')
        return v.strip().lower()

    @field_validator('attributes')
    @classmethod
    def normalize_attributes(cls, v: List[str]) -> List[str]:
        return [a.strip().lower() for a in v if a.strip()]
```

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ImageMetadata",
  "type": "object",
  "required": ["subject", "category", "attributes", "caption", "confidence"],
  "properties": {
    "subject": { "type": "string", "minLength": 1, "maxLength": 100 },
    "category": { "type": "string", "minLength": 1, "maxLength": 50 },
    "attributes": { "type": "array", "items": { "type": "string" } },
    "caption": { "type": "string", "minLength": 10, "maxLength": 500 },
    "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
  },
  "additionalProperties": false
}
```

### Validation Rules
- All fields required
- `confidence` must be in [0.0, 1.0]
- `subject` and `category` normalized to lowercase, trimmed
- `attributes` array items normalized to lowercase, trimmed; empty strings removed
- `caption` minimum 10 chars to ensure descriptive quality

---

## Matching Strategy Sketch

### Embedding Generation
1. **Images**: Vision model caption + subject + attributes concatenated → Gemini embedding model (text-embedding-004, 768-dim)
2. **Posts**: Post title + body (truncated to 8k tokens) → same embedding model
3. Both use identical embedding model for shared vector space

### Similarity & Ranking
- **Metric**: Cosine similarity (normalized dot product)
- **Formula**: `sim(a, b) = (a · b) / (||a|| ||b||)`
- **Ranking**: Descending cosine similarity
- **Top-K**: Return top 5 candidates per post for guard evaluation

### Vector Storage (pgvector-ready)
- **Phase 1**: Store embeddings as `vector(768)` column using PostgreSQL native `array` type (no pgvector extension)
- **Migration Path**: Column type `vector(768)` compatible with pgvector; enable extension later with `CREATE EXTENSION vector; ALTER COLUMN ... TYPE vector(768) USING embedding::vector`
- **Index**: Not needed at ~50 images; brute-force cosine similarity in Python is fast enough. Add `ivfflat` index when >10k vectors.

---

## Mismatch Guard Sketch

### Rule Combination (ALL must pass)
```
PASS = (tag_category_match) AND (similarity >= threshold) AND (confidence >= floor)
```

| Rule | Parameter | Default | Description |
|------|-----------|---------|-------------|
| Tag Category Match | Exact string match on `category` | Required | Image category must equal post's target category |
| Similarity Threshold | `SIMILARITY_THRESHOLD` | 0.75 | Cosine similarity between post and image embeddings |
| Confidence Floor | `CONFIDENCE_FLOOR` | 0.60 | Vision model's confidence in its own classification |

### Reject Output
```json
{
  "accepted": false,
  "reason": "Category mismatch: image category 'canid' != post target 'vulpine'",
  "details": {
    "tag_category_match": false,
    "similarity_score": 0.82,
    "similarity_pass": true,
    "confidence_score": 0.88,
    "confidence_pass": true
  }
}
```

### No Confident Match
If all candidates fail guard:
```json
{
  "accepted": false,
  "reason": "No confident match found",
  "candidates_evaluated": 3,
  "rejection_reasons": [
    "wolf_01.jpg: Category mismatch (canid vs vulpine)",
    "dog_03.jpg: Similarity below threshold (0.68 < 0.75)",
    "fox_02.jpg: Confidence below floor (0.52 < 0.60)"
  ]
}
```

---

## Database Design

### Tables

#### `images`
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default gen_random_uuid() |
| filename | VARCHAR(255) | NOT NULL, UNIQUE |
| url | TEXT | NOT NULL |
| license | VARCHAR(100) | NOT NULL |
| attribution | TEXT | NOT NULL |
| subject | VARCHAR(100) | NOT NULL |
| category | VARCHAR(50) | NOT NULL, INDEX |
| attributes | JSONB | NOT NULL DEFAULT '[]' |
| caption | TEXT | NOT NULL |
| confidence | NUMERIC(3,2) | NOT NULL CHECK (confidence >= 0 AND confidence <= 1) |
| embedding | FLOAT[] | NOT NULL, -- 768-dim, pgvector-ready |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: `idx_images_category (category)`, `idx_images_subject (subject)`

#### `tags`
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default gen_random_uuid() |
| name | VARCHAR(50) | NOT NULL, UNIQUE |
| category | VARCHAR(50) | NOT NULL, INDEX |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

#### `image_tags` (many-to-many)
| Column | Type | Constraints |
|--------|------|-------------|
| image_id | UUID | PK, FK → images.id ON DELETE CASCADE |
| tag_id | UUID | PK, FK → tags.id ON DELETE CASCADE |

#### `posts`
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default gen_random_uuid() |
| title | VARCHAR(255) | NOT NULL |
| slug | VARCHAR(255) | NOT NULL, UNIQUE |
| body | TEXT | NOT NULL |
| target_category | VARCHAR(50) | NOT NULL, INDEX |
| target_subject | VARCHAR(100) | NOT NULL |
| embedding | FLOAT[] | -- 768-dim, pgvector-ready |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: `idx_posts_target_category (target_category)`

#### `suggestions`
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default gen_random_uuid() |
| post_id | UUID | NOT NULL, FK → posts.id ON DELETE CASCADE, INDEX |
| image_id | UUID | NOT NULL, FK → images.id ON DELETE CASCADE, INDEX |
| similarity_score | NUMERIC(4,3) | NOT NULL CHECK (similarity_score >= -1 AND similarity_score <= 1) |
| guard_passed | BOOLEAN | NOT NULL DEFAULT false |
| guard_reason | TEXT | |
| rank | INTEGER | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: `idx_suggestions_post_rank (post_id, rank)`, `idx_suggestions_guard_passed (guard_passed)`

#### `approvals`
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default gen_random_uuid() |
| suggestion_id | UUID | NOT NULL, FK → suggestions.id ON DELETE CASCADE, UNIQUE |
| decision | VARCHAR(20) | NOT NULL CHECK (decision IN ('approved', 'rejected')) |
| reason | TEXT | |
| decided_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

### ASCII ERD

```
images ||--o{ image_tags }o--|| tags
posts ||--o{ suggestions }o--|| images
suggestions ||--|| approvals
```

### Key Design Notes
- `images.embedding` and `posts.embedding` use `FLOAT[]` (768 elements) for pgvector compatibility
- `image_tags` allows multiple tags per image beyond the primary category
- `suggestions.rank` enables ordered retrieval per post
- `approvals.suggestion_id` is UNIQUE to enforce one decision per suggestion

---

## Non-Goals

- **No frontend UI** — review/approval is API-only (JSON endpoints)
- No authentication/authorization (single-user MVP)
- No multi-tenancy or organizations
- No real-time WebSocket updates
- No image upload/management UI (images seeded via script only)
- No A/B testing or experiment framework