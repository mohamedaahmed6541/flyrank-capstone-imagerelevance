"""Embedding service using Ollama local embeddings (nomic-embed-text)."""

import logging
from typing import List
import httpx
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Ollama embedding endpoint
OLLAMA_EMBED_URL = f"{settings.OLLAMA_HOST}/api/embeddings"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def get_embedding(text: str) -> List[float]:
    """Get embedding for a single text using Ollama nomic-embed-text."""
    payload = {
        "model": settings.OLLAMA_EMBEDDING_MODEL,
        "prompt": text,
    }
    
    timeout = httpx.Timeout(120.0, connect=10.0)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            OLLAMA_EMBED_URL,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Get embeddings for multiple texts (sequential for simplicity)."""
    embeddings = []
    for text in texts:
        try:
            emb = get_embedding(text)
            embeddings.append(emb)
        except Exception as e:
            logger.error(f"Failed to get embedding for text: {e}")
            embeddings.append([0.0] * 768)
    return embeddings


def embed_image_caption(caption: str, subject: str, attributes: List[str]) -> List[float]:
    """Generate embedding for an image using its caption, subject, and attributes."""
    # Combine caption + subject + attributes for richer embedding
    parts = [caption.strip()]
    if subject:
        parts.append(f"Subject: {subject}")
    if attributes:
        parts.append(f"Attributes: {', '.join(attributes)}")
    text = " | ".join(parts)
    return get_embedding(text)


def embed_post_content(title: str, body: str) -> List[float]:
    """Generate embedding for a blog post using title + body."""
    # Combine title + body, truncate to reasonable length
    text = f"Title: {title.strip()}\n\nBody: {body.strip()}"
    # Truncate to ~8000 chars to stay within context limits
    if len(text) > 8000:
        text = text[:8000]
    return get_embedding(text)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))