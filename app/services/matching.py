"""Matching service with cosine similarity and mismatch guard."""

import logging
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from app.db.session import get_session
from app.models.image import Image
from app.models.post import Post
from app.models.suggestion import Suggestion
from app.models.approval import Approval
from app.services.embedding import (
    get_embedding,
    cosine_similarity,
    embed_image_caption,
    embed_post_content,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Guard thresholds from config
SIMILARITY_THRESHOLD = settings.SIMILARITY_THRESHOLD  # 0.75
CONFIDENCE_FLOOR = settings.CONFIDENCE_FLOOR  # 0.60


@dataclass
class GuardResult:
    """Result of guard evaluation for a single candidate."""
    accepted: bool
    image_id: str
    image_filename: str
    similarity_score: float
    confidence_score: float
    category_match: bool
    similarity_pass: bool
    confidence_pass: bool
    category_match_pass: bool
    reason: str
    details: dict


def evaluate_guard(
    post: Post,
    image: Image,
    similarity: float,
) -> GuardResult:
    """
    Evaluate the mismatch guard for a post-image pair.
    All three conditions must pass: category match, similarity threshold, confidence floor.
    """
    # 1. Category match (exact string match)
    category_match = (image.category == post.target_category)
    
    # 2. Similarity threshold
    similarity_pass = similarity >= settings.SIMILARITY_THRESHOLD
    
    # 3. Confidence floor
    confidence_pass = image.confidence >= settings.CONFIDENCE_FLOOR
    
    # All must pass
    accepted = category_match and similarity_pass and confidence_pass
    
    # Build reason
    reasons = []
    if not category_match:
        reasons.append(f"Category mismatch: image category '{image.category}' != post target '{post.target_category}'")
    if not similarity_pass:
        reasons.append(f"Similarity below threshold ({similarity:.2f} < {settings.SIMILARITY_THRESHOLD})")
    if not confidence_pass:
        reasons.append(f"Confidence below floor ({image.confidence:.2f} < {settings.CONFIDENCE_FLOOR})")
    
    if accepted:
        reason = "All guard checks passed"
    else:
        reason = "; ".join(reasons)
    
    return GuardResult(
        accepted=accepted,
        image_id=str(image.id),
        image_filename=image.filename,
        similarity_score=round(similarity, 4),
        confidence_score=round(image.confidence, 4),
        category_match=category_match,
        similarity_pass=similarity_pass,
        confidence_pass=confidence_pass,
        category_match_pass=category_match,
        reason=reason,
        details={
            "category_match": category_match,
            "similarity_score": round(similarity, 4),
            "similarity_pass": similarity_pass,
            "confidence_score": round(image.confidence, 4),
            "confidence_pass": confidence_pass,
        }
    )


def compute_embeddings_for_images() -> int:
    """Generate embeddings for all images that don't have them yet."""
    updated = 0
    with get_session() as session:
        images = session.query(Image).filter(Image.embedding.is_(None)).all()
        
        for img in images:
            if not img.caption or not img.subject:
                logger.warning(f"Skipping {img.filename}: missing caption or subject")
                continue
            
            try:
                embedding = embed_image_caption(img.caption, img.subject, img.attributes or [])
                img.embedding = embedding
                session.commit()
                updated += 1
                logger.info(f"Generated embedding for {img.filename}")
            except Exception as e:
                logger.error(f"Failed to generate embedding for {img.filename}: {e}")
                session.rollback()
    
    logger.info(f"Generated embeddings for {updated} images")
    return updated


def compute_embeddings_for_posts() -> int:
    """Generate embeddings for all posts that don't have them yet."""
    updated = 0
    with get_session() as session:
        posts = session.query(Post).filter(Post.embedding.is_(None)).all()
        
        for post in posts:
            try:
                embedding = embed_post_content(post.title, post.body)
                post.embedding = embedding
                session.commit()
                updated += 1
                logger.info(f"Generated embedding for post: {post.title}")
            except Exception as e:
                logger.error(f"Failed to generate embedding for post {post.id}: {e}")
                session.rollback()
    
    logger.info(f"Generated embeddings for {updated} posts")
    return updated


def get_candidate_images_for_post(post: Post, limit: int = 50) -> List[Image]:
    """Get candidate images for a post, filtered by category match first."""
    with get_session() as session:
        # First, get images with matching category
        matching = session.query(Image).filter(
            Image.category == post.target_category,
            Image.embedding.is_not(None),
            Image.validation_status.in_(["success", "partial"])
        ).all()
        
        if len(matching) >= 5:
            return matching[:50]
        
        # If not enough matching, add non-matching images with embeddings
        other = session.query(Image).filter(
            Image.category != post.target_category,
            Image.embedding.is_not(None),
            Image.validation_status.in_(["success", "partial"])
        ).limit(50 - len(matching)).all()
        
        return matching + other


def generate_suggestions_for_post(post: Post, top_k: int = 5) -> List[Suggestion]:
    """
    Generate ranked image suggestions for a post with guard evaluation.
    Returns top-K suggestions with guard evaluation results.
    """
    # Ensure post has embedding
    with get_session() as session:
        post_obj = session.get(Post, post.id)
        if not post_obj.embedding:
            post_obj.embedding = embed_post_content(post.title, post.body)
            session.commit()
        post_embedding = np.array(post_obj.embedding, dtype=np.float32)
    
    # Get candidate images
    candidates = get_candidate_images_for_post(post)
    
    suggestions = []
    
    for img in candidates:
        if not img.embedding:
            continue
        
        # Compute similarity
        img_embedding = np.array(img.embedding, dtype=np.float32)
        similarity = cosine_similarity(post_embedding, img_embedding)
        
        # Evaluate guard
        guard_result = evaluate_guard(post, img, similarity)
        
        # Create suggestion
        suggestion = Suggestion(
            post_id=post.id,
            image_id=img.id,
            similarity_score=guard_result.similarity_score,
            guard_passed=guard_result.accepted,
            guard_reason=guard_result.reason if not guard_result.accepted else None,
            rank=0,  # Will be set after sorting
        )
        suggestions.append((suggestion, guard_result))
    
    # Sort by similarity descending
    suggestions.sort(key=lambda x: x[1].similarity_score, reverse=True)
    
    # Assign ranks and take top-K
    final_suggestions = []
    for rank, (suggestion, guard_result) in enumerate(suggestions[:5], 1):
        suggestion.rank = rank
        final_suggestions.append(suggestion)
    
    return final_suggestions


def run_matching_pipeline() -> dict:
    """
    Run the full matching pipeline for all posts.
    Returns summary statistics.
    """
    logger.info("Starting matching pipeline...")
    
    # Ensure embeddings are computed
    compute_embeddings_for_images()
    compute_embeddings_for_posts()
    
    stats = {
        "posts_processed": 0,
        "total_suggestions": 0,
        "accepted": 0,
        "rejected": 0,
        "no_confident_match": 0,
    }
    
    with get_session() as session:
        posts = session.query(Post).all()
        
        for post in posts:
            stats["posts_processed"] += 1
            suggestions = generate_suggestions_for_post(post)
            
            # Save suggestions to database
            for suggestion in suggestions:
                session.add(suggestion)
            
            accepted = sum(1 for s in suggestions if s.guard_passed)
            rejected = sum(1 for s in suggestions if not s.guard_passed)
            stats["total_suggestions"] += len(suggestions)
            stats["accepted"] += accepted
            stats["rejected"] += rejected
            
            # Check for "no confident match" - no suggestions passed guard
            if accepted == 0:
                stats["no_confident_match"] += 1
            
            session.commit()
            logger.info(f"Post '{post.title}': {accepted} accepted, {len(suggestions) - accepted} rejected")
    
    logger.info(f"Matching pipeline complete: {stats}")
    return stats


@dataclass
class SuggestionResult:
    """Result of suggestion generation for a single post."""
    post_id: str
    post_title: str
    suggestions: List[dict]
    accepted_count: int
    rejected_count: int
    no_confident_match: bool


def get_suggestions_for_post(post_id: str, top_k: int = 5) -> dict:
    """
    Get ranked suggestions for a post with guard evaluation.
    Returns structured response for API.
    """
    with get_session() as session:
        post = session.get(Post, post_id)
        if not post:
            return {"error": "Post not found"}
        
        # Ensure embeddings exist
        if not post.embedding:
            post.embedding = embed_post_content(post.title, post.body)
            session.commit()
        post_embedding = np.array(post.embedding, dtype=np.float32)
        
        # Get candidate images
        candidates = []
        # Matching category first
        matching = session.query(Image).filter(
            Image.category == post.target_category,
            Image.embedding.is_not(None),
            Image.validation_status.in_(["success", "partial"])
        ).all()
        
        other = session.query(Image).filter(
            Image.category != post.target_category,
            Image.embedding.is_not(None),
            Image.validation_status.in_(["success", "partial"])
        ).limit(50).all()
        
        candidates = matching + other
        
        suggestions = []
        for img in candidates:
            if not img.embedding:
                continue
            
            img_embedding = np.array(img.embedding, dtype=np.float32)
            similarity = cosine_similarity(post_embedding, img_embedding)
            guard_result = evaluate_guard(post, img, similarity)
            
            suggestions.append({
                "image_id": str(img.id),
                "filename": img.filename,
                "subject": img.subject,
                "category": img.category,
                "confidence": round(img.confidence, 2),
                "similarity_score": round(similarity, 4),
                "guard_passed": True if guard_result.accepted else False,
                "guard_reason": guard_result.reason if not guard_result.accepted else "All guard checks passed",
                "details": guard_result.details,
            })
        
        # Sort by similarity descending
        suggestions.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Take top K
        suggestions = suggestions[:5]
        
        # Add rank
        for rank, s in enumerate(suggestions, 1):
            s["rank"] = rank
        
        accepted = sum(1 for s in suggestions if s["guard_passed"])
        rejected = sum(1 for s in suggestions if not s["guard_passed"])
        no_confident_match = accepted == 0
        
        return {
            "post_id": str(post.id),
            "post_title": post.title,
            "post_target_category": post.target_category,
            "post_target_subject": post.target_subject,
            "suggestions": suggestions,
            "accepted_count": accepted,
            "rejected_count": rejected,
            "no_confident_match": no_confident_match,
        }