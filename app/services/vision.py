"""Vision service using Ollama (local, no quota) for image classification."""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image as PILImage

from app.core.config import settings
from app.schemas.vision import ImageMetadata, VisionResult, CONFIDENCE_FLOOR

logger = logging.getLogger(__name__)

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
    """Raised for transient errors (network issues, timeouts)."""
    pass


class ModelNotFoundError(VisionError):
    """Raised when the model is not found (404)."""
    pass


def _extract_json_from_response(response_text: str) -> dict:
    """
    Extract JSON from response, handling markdown code blocks and prose.
    Local models often embed JSON in explanatory text.
    """
    text = response_text.strip()
    
    # Try direct JSON first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Find first {...} block in prose (common with local models)
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # If all else fails, raise the original error
    raise json.JSONDecodeError(f"Could not extract valid JSON from: {text[:200]}...", text, 0)


def _encode_image_to_base64(image_path: Path) -> str:
    """Encode image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_ollama_vision(image_path: Path, prompt: str) -> tuple[str, dict]:
    """
    Call Ollama's /api/generate endpoint with an image and prompt.
    Returns (raw_response_text, usage_metadata_dict).
    """
    # Encode image to base64
    image_b64 = _encode_image_to_base64(image_path)
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
        }
    }
    
    # Use generous timeout for local inference
    timeout = httpx.Timeout(120.0, connect=10.0)
    
    with httpx.Client(timeout=timeout) as client:
        try:
            response = client.post(
                f"{settings.OLLAMA_HOST}/api/generate",
                json=payload,
            )
            
            if response.status_code == 404:
                raise ModelNotFoundError(
                    f"Model '{settings.OLLAMA_MODEL}' not found. "
                    f"Run: ollama pull {settings.OLLAMA_MODEL}"
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Ollama returns: {"response": "...", "done": true, ...}
            response_text = data.get("response", "")
            
            # Extract usage metadata if available
            usage = {}
            if "eval_count" in data:
                usage = {
                    "input_tokens": data.get("prompt_eval_count"),
                    "output_tokens": data.get("eval_count"),
                }
            
            return response_text, usage
            
        except httpx.ConnectError as e:
            raise TransientError(f"Cannot connect to Ollama at {settings.OLLAMA_HOST}: {e}") from e
        except httpx.TimeoutException as e:
            raise TransientError(f"Ollama request timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ModelNotFoundError(
                    f"Model '{settings.OLLAMA_MODEL}' not found. "
                    f"Run: ollama pull {settings.OLLAMA_MODEL}"
                ) from e
            elif e.response.status_code >= 500:
                raise TransientError(f"Ollama server error: {e}") from e
            else:
                raise VisionError(f"Ollama API error: {e}") from e
        except httpx.RequestError as e:
            raise TransientError(f"Ollama request failed: {e}") from e


def _classify_with_prompt(image_path: Path, prompt: str) -> VisionResult:
    """Single classification attempt with given prompt."""
    filename = image_path.name
    
    try:
        raw_response, usage = _call_ollama_vision(image_path, prompt)
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
    except ModelNotFoundError:
        # Re-raise model not found - not retryable
        raise
    except TransientError:
        # Re-raise transient errors
        raise
    except Exception as e:
        # Unknown error - treat as validation failure
        logger.warning(f"Unknown error for {filename}, treating as validation failure: {e}")
        raise ValidationError(str(e)) from e


def classify_image(image_path: Path) -> VisionResult:
    """
    Classify a single image using Ollama (local llava).
    Retries once with stricter prompt on validation failure.
    Does NOT retry on transient errors (handled by batch layer).
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
    except ModelNotFoundError:
        # Re-raise model not found - not retryable
        raise
    except TransientError:
        # Re-raise transient errors
        raise
    except Exception as e:
        # Unknown error - treat as validation failure
        logger.error(f"Unknown error for {filename}: {e}")
        raise ValidationError(str(e)) from e