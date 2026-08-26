"""Pydantic schemas for vision model output."""

from typing import List
from pydantic import BaseModel, Field, field_validator, ConfigDict


CONFIDENCE_FLOOR = 0.6

# Closed enum matching our 5 dataset categories
ALLOWED_CATEGORIES = frozenset(["vulpine", "canid_wolf", "canid_dog", "ursid", "cervid"])


class ImageMetadata(BaseModel):
    """
    Structured output from vision model classification.
    Matches the schema defined in DESIGN.md.
    """
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(..., min_length=1, max_length=100, description="Primary subject (e.g., 'red fox', 'gray wolf')")
    category: str = Field(..., description="Broad category from closed enum")
    attributes: List[str] = Field(default_factory=list, description="Visual attributes (e.g., ['red fur', 'bushy tail', 'pointed ears'])")
    caption: str = Field(..., min_length=10, max_length=500, description="Natural language description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in classification")

    @field_validator('subject', 'category')
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Field cannot be empty or whitespace')
        return v.strip().lower()

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        v_normalized = v.strip().lower()
        if v_normalized not in ALLOWED_CATEGORIES:
            raise ValueError(f'Category must be one of: {", ".join(sorted(ALLOWED_CATEGORIES))}')
        return v_normalized

    @field_validator('attributes')
    @classmethod
    def normalize_attributes(cls, v: List[str]) -> List[str]:
        return [a.strip().lower() for a in v if a.strip()]

    @property
    def needs_review(self) -> bool:
        """True if confidence is below the threshold for automatic acceptance."""
        return self.confidence < CONFIDENCE_FLOOR


class VisionResult(BaseModel):
    """Result of vision processing for a single image."""
    model_config = ConfigDict(extra="forbid")

    filename: str
    metadata: ImageMetadata | None = None
    validation_status: str = "success"  # "success", "failed", "partial"
    error_message: str | None = None
    raw_response: str | None = None