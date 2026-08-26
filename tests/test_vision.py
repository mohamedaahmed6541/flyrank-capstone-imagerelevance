"""Tests for vision schema and validation logic."""

import pytest
from app.schemas.vision import ImageMetadata, VisionResult, CONFIDENCE_FLOOR


class TestImageMetadataSchema:
    """Tests for ImageMetadata Pydantic model."""

    def test_valid_input_passes(self):
        """Valid input should pass validation."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur", "bushy tail", "pointed ears"],
            "caption": "A red fox standing in snow with its distinctive bushy tail.",
            "confidence": 0.92,
        }
        metadata = ImageMetadata(**data)
        assert metadata.subject == "red fox"
        assert metadata.category == "vulpine"
        assert metadata.attributes == ["red fur", "bushy tail", "pointed ears"]
        assert metadata.confidence == 0.92

    def test_missing_subject_fails(self):
        """Missing subject should fail validation."""
        data = {
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 0.9,
        }
        with pytest.raises(Exception) as exc_info:
            ImageMetadata(**data)
        assert "subject" in str(exc_info.value).lower()

    def test_missing_category_fails(self):
        """Missing category should fail validation."""
        data = {
            "subject": "red fox",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 0.9,
        }
        with pytest.raises(Exception) as exc_info:
            ImageMetadata(**data)
        assert "category" in str(exc_info.value).lower()

    def test_confidence_out_of_range_fails(self):
        """Confidence outside 0-1 range should fail."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 1.5,
        }
        with pytest.raises(Exception) as exc_info:
            ImageMetadata(**data)
        assert "confidence" in str(exc_info.value).lower()

    def test_confidence_negative_fails(self):
        """Negative confidence should fail."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": -0.1,
        }
        with pytest.raises(Exception) as exc_info:
            ImageMetadata(**data)
        assert "confidence" in str(exc_info.value).lower()

    def test_caption_too_short_fails(self):
        """Caption shorter than 10 chars should fail."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "Fox.",
            "confidence": 0.9,
        }
        with pytest.raises(Exception) as exc_info:
            ImageMetadata(**data)
        assert "caption" in str(exc_info.value).lower()

    def test_subject_whitespace_normalized(self):
        """Subject should be stripped and lowercased."""
        data = {
            "subject": "  RED FOX  ",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 0.9,
        }
        metadata = ImageMetadata(**data)
        assert metadata.subject == "red fox"

    def test_category_whitespace_normalized(self):
        """Category should be stripped and lowercased (before enum validation)."""
        data = {
            "subject": "red fox",
            "category": "  vulpine  ",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 0.9,
        }
        metadata = ImageMetadata(**data)
        assert metadata.category == "vulpine"

    def test_attributes_normalized(self):
        """Attributes should be stripped and lowercased, empty removed."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["  RED FUR  ", "Bushy Tail", "", "  "],
            "caption": "A red fox in snow.",
            "confidence": 0.9,
        }
        metadata = ImageMetadata(**data)
        assert metadata.attributes == ["red fur", "bushy tail"]

    def test_extra_fields_rejected(self):
        """Extra fields should be rejected (extra='forbid')."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 0.9,
            "extra_field": "not allowed",
        }
        with pytest.raises(Exception) as exc_info:
            ImageMetadata(**data)
        assert "extra" in str(exc_info.value).lower()


class TestConfidenceFloor:
    """Tests for confidence floor and needs_review flag."""

    def test_confidence_above_floor_no_review(self):
        """Confidence >= 0.6 should not need review."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 0.7,
        }
        metadata = ImageMetadata(**data)
        assert metadata.needs_review is False

    def test_confidence_at_floor_no_review(self):
        """Confidence exactly at 0.6 should not need review."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": CONFIDENCE_FLOOR,
        }
        metadata = ImageMetadata(**data)
        assert metadata.needs_review is False

    def test_confidence_below_floor_needs_review(self):
        """Confidence < 0.6 should need review."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 0.55,
        }
        metadata = ImageMetadata(**data)
        assert metadata.needs_review is True

    def test_confidence_zero_needs_review(self):
        """Confidence 0 should need review."""
        data = {
            "subject": "red fox",
            "category": "vulpine",
            "attributes": ["red fur"],
            "caption": "A red fox in snow.",
            "confidence": 0.0,
        }
        metadata = ImageMetadata(**data)
        assert metadata.needs_review is True


class TestVisionResult:
    """Tests for VisionResult model."""

    def test_success_result(self):
        """Successful vision result."""
        metadata = ImageMetadata(
            subject="red fox",
            category="vulpine",
            attributes=["red fur"],
            caption="A red fox in snow.",
            confidence=0.9,
        )
        result = VisionResult(
            filename="test.jpg",
            metadata=metadata,
            validation_status="success",
        )
        assert result.validation_status == "success"
        assert result.metadata is not None
        assert result.error_message is None

    def test_failed_result(self):
        """Failed vision result."""
        result = VisionResult(
            filename="test.jpg",
            metadata=None,
            validation_status="failed",
            error_message="Validation failed",
        )
        assert result.validation_status == "failed"
        assert result.metadata is None
        assert result.error_message == "Validation failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])