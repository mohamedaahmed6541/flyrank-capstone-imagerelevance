"""Vision service using Gemini Flash for image classification."""

import json
import logging
import re
from typing import Optional
from pathlib import Path

import google.generativeai as genai
from PIL import Image as PILImage

from app.core.config import settings
from app.schemas.vision import ImageMetadata, VisionResult, CONFIDENCE_FLOOR

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# Prompt for structured output
VISION_PROMPT = """
Analyze this image and return a JSON object with the following fields:
- subject: Primary subject (e.g., "red fox", "gray wolf", "domestic dog", "brown bear", "white-tailed deer")
- category: Broad taxonomic category (e.g., "vulpine", "canid", "ursid", "cervid")
- attributes: List of visual attributes (e.g., ["red fur", "bushy tail", "pointed ears", "snow background"])
- caption: Natural language description (1-2 sentences, minimum 10 characters)
- confidence: Your confidence in this classification (0.0 to 1.0)

Return ONLY valid JSON. No extra text.
""".strip()

STRICTER_PROMPT = VISION_PROMPT + """

IMPORTANT: The response MUST be valid JSON with EXACTLY these 5 fields.
- subject: string (1-100 chars)
- category: string (1-50 chars)
- attributes: array of strings
- caption: string (10-500 chars)
- confidence: number (0.0-1.0)

Example:
{
  "subject": "red fox",
  "category": "vulpine",
  "attributes": ["red fur", "bushy tail", "pointed ears", "snow"],
  "caption": "A red fox standing in snow with its distinctive bushy tail and pointed ears.",
  "confidence": 0.92
}
""".strip()


class VisionError(Exception):
    """Base exception for vision service errors."""
    pass


class ValidationError(VisionError):
    """Raised when vision output fails validation."""
    pass


class TransientError(VisionError):
    """Raised for transient errors (network issues, 5xx, timeouts)."""
    pass


class QuotaExceededError(VisionError):
    """Raised when API quota is exceeded (429). Do not retry."""
    pass


def _extract_json_from_response(response_text: str) -> dict:
    """Extract JSON from response, handling markdown code blocks."""
    text = response_text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def _is_quota_error(error: Exception) -> bool:
    """Check if an exception is a quota exceeded (429) error."""
    error_str = str(error)
    # Check for 429 status code or quota exceeded message
    return (
        "429" in error_str 
        or "quota" in error_str.lower() 
        or "rate limit" in error_str.lower()
        or "generate_content_free_tier_requests" in error_str
    )


def _is_permission_error(error: Exception) -> bool:
    """Check if an exception is a permission denied (403) error."""
    error_str = str(error)
    return (
        "403" in error_str
        or "permission" in error_str.lower()
        or "denied access" in error_str.lower()
    )


def _is_transient_error(error: Exception) -> bool:
    """Check if an exception is a genuinely transient error worth retrying."""
    # Network errors, timeouts, 5xx server errors
    error_str = str(error).lower()
    transient_patterns = [
        "timeout",
        "connection",
        "network",
        "dns",
        "socket",
        "500",
        "502",
        "503",
        "504",
        "unavailable",
        "internal error",
    ]
    return any(pattern in error_str for pattern in transient_patterns)


def _call_gemini_vision(image_path: Path, prompt: str) -> tuple[str, dict]:
    """
    Call Gemini Flash with an image and prompt.
    Returns (raw_response_text, usage_metadata_dict).
    """
    model = genai.GenerativeModel("gemini-flash-latest")
    
    # Load image
    pil_image = PILImage.open(image_path)
    
    # Generate content
    response = model.generate_content(
        [prompt, pil_image],
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    
    # Extract usage metadata if available
    usage = {}
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        usage = {
            "input_tokens": getattr(response.usage_metadata, 'prompt_token_count', None),
            "output_tokens": getattr(response.usage_metadata, 'candidates_token_count', None),
        }
    
    return response.text, usage


def _classify_with_prompt(image_path: Path, prompt: str) -> VisionResult:
    """Single classification attempt with given prompt."""
    filename = image_path.name
    
    try:
        raw_response, usage = _call_gemini_vision(image_path, prompt)
        parsed = _extract_json_from_response(raw_response)
        metadata = ImageMetadata(**parsed)
        return VisionResult(
            filename=filename,
            metadata=metadata,
            validation_status="success",
            raw_response=raw_response,
        )
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        # Classify the error type
        if _is_quota_error(e):
            raise QuotaExceededError(str(e)) from e
        elif _is_permission_error(e):
            # 403 is not retryable - it's a config issue
            raise ValidationError(f"Permission denied: {e}") from e
        elif _is_transient_error(e):
            raise TransientError(str(e)) from e
        else:
            # Unknown error - treat as validation failure
            logger.warning(f"Unknown error for {filename}, treating as validation failure: {e}")
            raise ValidationError(str(e)) from e


def classify_image(image_path: Path) -> VisionResult:
    """
    Classify a single image using Gemini Flash.
    Retries once with stricter prompt on validation failure.
    Does NOT retry on quota exceeded (429) - raises QuotaExceededError.
    """
    filename = image_path.name
    
    # First attempt with standard prompt
    try:
        return _classify_with_prompt(image_path, VISION_PROMPT)
    except ValidationError as e:
        logger.warning(f"First attempt failed for {filename}: {e}. Retrying with stricter prompt...")
        
        # Second attempt with stricter prompt
        try:
            result = _classify_with_prompt(image_path, STRICTER_PROMPT)
            result.validation_status = "partial"  # succeeded on retry
            return result
        except ValidationError as e2:
            logger.error(f"Both attempts failed for {filename}: {e2}")
            return VisionResult(
                filename=filename,
                metadata=None,
                validation_status="failed",
                error_message=str(e2),
            )
    except QuotaExceededError:
        # Re-raise quota errors immediately - don't retry
        raise
    except TransientError:
        # Re-raise transient errors
        raise
    except Exception as e:
        # Unknown error - treat as validation failure
        logger.error(f"Unknown error for {filename}: {e}")
        raise ValidationError(str(e)) from e