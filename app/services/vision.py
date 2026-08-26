"""Vision service using Gemini Flash for image classification."""

import json
import logging
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
    """Raised for transient errors (rate limits, network issues)."""
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


def _call_gemini_vision(image_path: Path, prompt: str) -> tuple[str, dict]:
    """
    Call Gemini Flash with an image and prompt.
    Returns (raw_response_text, usage_metadata_dict).
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    
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


def classify_image(image_path: Path) -> VisionResult:
    """
    Classify a single image using Gemini Flash.
    Retries once with stricter prompt on validation failure.
    """
    filename = image_path.name
    
    # First attempt with standard prompt
    try:
        raw_response, usage = _call_gemini_vision(image_path, VISION_PROMPT)
        parsed = _extract_json_from_response(raw_response)
        metadata = ImageMetadata(**parsed)
        return VisionResult(
            filename=filename,
            metadata=metadata,
            validation_status="success",
            raw_response=raw_response,
        )
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        logger.warning(f"First attempt failed for {filename}: {e}. Retrying with stricter prompt...")
        
        # Second attempt with stricter prompt
        try:
            raw_response, usage = _call_gemini_vision(image_path, STRICTER_PROMPT)
            parsed = _extract_json_from_response(raw_response)
            metadata = ImageMetadata(**parsed)
            return VisionResult(
                filename=filename,
                metadata=metadata,
                validation_status="partial",  # succeeded on retry
                raw_response=raw_response,
            )
        except (json.JSONDecodeError, ValidationError, ValueError) as e2:
            logger.error(f"Both attempts failed for {filename}: {e2}")
            return VisionResult(
                filename=filename,
                metadata=None,
                validation_status="failed",
                error_message=str(e2),
                raw_response=raw_response if 'raw_response' in locals() else None,
            )
    except Exception as e:
        # Transient error (network, rate limit, etc.)
        logger.error(f"Transient error for {filename}: {e}")
        raise TransientError(str(e)) from e