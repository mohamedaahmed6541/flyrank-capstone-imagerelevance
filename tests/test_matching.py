"""Tests for matching engine and mismatch guard."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from app.services.matching import (
    cosine_similarity,
    evaluate_guard,
    get_candidate_images_for_post,
    run_matching_pipeline,
)
from app.schemas.vision import ImageMetadata, VisionResult, CONFIDENCE_FLOOR
from app.models.image import Image
from app.models.post import Post
from app.services.embedding import cosine_similarity as emb_cosine_similarity


class TestCosineSimilarity:
    """Tests for cosine similarity function."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity 1.0."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        assert cosine_similarity(a, b) == 1.0

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity 0.0."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        assert cosine_similarity(a, b) == 0.0

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity -1.0."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([-1.0, 0.0, 0.0])
        assert cosine_similarity(a, b) == -1.0

    def test_zero_vector(self):
        """Zero vector should return 0.0 similarity."""
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        assert cosine_similarity(a, b) == 0.0


class TestGuardLogic:
    """Tests for the mismatch guard logic."""

    def test_guard_all_pass(self):
        """Guard should pass when all three conditions met."""
        from app.schemas.vision import ImageMetadata, VisionResult, CONFIDENCE_FLOOR
        
        post = Mock(spec=Post)
        post.target_category = "vulpine"
        post.id = "test-post-id"
        
        image = Mock(spec=Image)
        image.category = "vulpine"
        image.confidence = 0.9
        image.id = "test-image-id"
        image.filename = "fox.jpg"
        
        similarity = 0.85  # Above 0.75 threshold
        
        result = evaluate_guard(post, image, similarity)
        
        assert result.accepted is True
        assert result.category_match is True
        assert result.similarity_pass is True
        assert result.confidence_pass is True
        assert "All guard checks passed" in result.reason

    def test_guard_category_mismatch_rejects(self):
        """Guard should reject on category mismatch."""
        from app.services.matching import evaluate_guard
        from unittest.mock import Mock
        
        post = Mock(spec=Post)
        post.target_category = "vulpine"
        post.id = "test-post-id"
        
        image = Mock(spec=Image)
        image.category = "canid_dog"  # Different category
        image.confidence = 0.9
        image.id = "test-image-id"
        image.filename = "dog.jpg"
        
        similarity = 0.85  # Above threshold
        
        result = evaluate_guard(post, image, similarity)
        
        assert result.accepted is False
        assert result.category_match is False
        assert result.category_match_pass is False
        assert "Category mismatch" in result.reason
        assert "vulpine" in result.reason
        assert "canid_dog" in result.reason

    def test_guard_similarity_below_threshold_rejects(self):
        """Guard should reject when similarity below threshold."""
        from app.services.matching import evaluate_guard
        from unittest.mock import Mock
        
        post = Mock(spec=Post)
        post.target_category = "vulpine"
        post.id = "test-post-id"
        
        image = Mock(spec=Image)
        image.category = "vulpine"
        image.confidence = 0.9
        image.id = "test-image-id"
        image.filename = "fox.jpg"
        
        similarity = 0.50  # Below 0.75 threshold
        
        result = evaluate_guard(post, image, similarity)
        
        assert result.accepted is False
        assert result.category_match is True
        assert result.similarity_pass is False
        assert "Similarity below threshold" in result.reason
        assert "0.50" in result.reason or "0.5" in result.reason

    def test_guard_confidence_below_floor_rejects(self):
        """Guard should reject when confidence below floor."""
        from app.services.matching import evaluate_guard
        from unittest.mock import Mock
        
        post = Mock(spec=Post)
        post.target_category = "vulpine"
        post.id = "test-post-id"
        
        image = Mock(spec=Image)
        image.category = "vulpine"
        image.confidence = 0.50  # Below 0.60 floor
        image.id = "test-image-id"
        image.filename = "fox.jpg"
        
        similarity = 0.85  # Above threshold
        
        result = evaluate_guard(post, image, similarity)
        
        assert result.accepted is False
        assert result.category_match is True
        assert result.similarity_pass is True
        assert result.confidence_pass is False
        assert "Confidence below floor" in result.reason
        assert "0.50" in result.reason or "0.5" in result.reason

    def test_guard_multiple_failures(self):
        """Guard should report all failures when multiple conditions fail."""
        from app.services.matching import evaluate_guard
        from unittest.mock import Mock
        
        post = Mock(spec=Post)
        post.target_category = "vulpine"
        post.id = "test-post-id"
        
        image = Mock(spec=Image)
        image.category = "canid_dog"  # Wrong category
        image.confidence = 0.50  # Below floor
        image.id = "test-image-id"
        image.filename = "dog.jpg"
        
        similarity = 0.50  # Below threshold
        
        result = evaluate_guard(post, image, similarity)
        
        assert result.accepted is False
        assert result.category_match is False
        assert result.similarity_pass is False
        assert result.confidence_pass is False
        # Should mention all three failures
        assert "Category mismatch" in result.reason
        assert "Similarity below threshold" in result.reason
        assert "Confidence below floor" in result.reason


class TestSimilarityComputation:
    """Tests for similarity computation."""

    def test_cosine_similarity_identical(self):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])
        assert abs(cosine_similarity(a, b) - 1.0) < 1e-6

    def test_cosine_similarity_known_values(self):
        a = np.array([3.0, 4.0])
        b = np.array([3.0, 4.0])
        assert abs(cosine_similarity(a, b) - 1.0) < 1e-6
        
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert abs(cosine_similarity(a, b) - 0.0) < 1e-6

    def test_cosine_similarity_zero_vector(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        assert cosine_similarity(a, b) == 0.0


class TestGuardResultDataclass:
    """Tests for GuardResult dataclass."""

    def test_guard_result_creation(self):
        from app.services.matching import GuardResult
        
        result = GuardResult(
            accepted=True,
            image_id="test-id",
            image_filename="test.jpg",
            similarity_score=0.85,
            confidence_score=0.90,
            category_match=True,
            similarity_pass=True,
            confidence_pass=True,
            category_match_pass=True,
            reason="All guard checks passed",
            details={"category_match": True, "similarity_score": 0.85}
        )
        
        assert result.accepted is True
        assert result.similarity_score == 0.85
        assert result.confidence_score == 0.90
        assert result.category_match is True


class TestGuardThresholds:
    """Tests for guard threshold constants."""

    def test_similarity_threshold_default(self):
        from app.core.config import settings
        assert settings.SIMILARITY_THRESHOLD == 0.65

    def test_confidence_floor_default(self):
        from app.core.config import settings
        assert settings.CONFIDENCE_FLOOR == 0.60

    def test_embedding_dim_default(self):
        from app.core.config import settings
        assert settings.EMBEDDING_DIM == 768


if __name__ == "__main__":
    pytest.main([__file__, "-v"])