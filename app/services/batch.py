"""Batch processor for vision pipeline with Ollama (local, no quota)."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.core.config import settings
from app.db.session import get_session
from app.models.image import Image
from app.models.api_call import ApiCall
from app.schemas.vision import VisionResult, CONFIDENCE_FLOOR
from app.services.vision import (
    classify_image, 
    TransientError, 
    VisionError, 
    ValidationError,
    ModelNotFoundError
)
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics for batch processing."""
    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed_validation: int = 0
    failed_transient: int = 0
    failed_model_not_found: int = 0
    needs_review: int = 0
    total_cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)

    def log_progress(self) -> None:
        logger.info(
            f"Progress: {self.processed}/{self.total} "
            f"(succeeded: {self.succeeded}, "
            f"validation_failed: {self.failed_validation}, "
            f"transient_failed: {self.failed_transient}, "
            f"model_not_found: {self.failed_model_not_found}, "
            f"needs_review: {self.needs_review}, "
            f"cost: ${self.total_cost_usd:.6f})"
        )


def is_image_already_processed(session, image_id: uuid.UUID) -> bool:
    """Check if image already has a successful vision result."""
    image = session.get(Image, image_id)
    if not image:
        return False
    return image.validation_status in ("success", "partial")


def save_vision_result(
    session,
    image_id: uuid.UUID,
    result: VisionResult,
    model: str = "llava",
) -> None:
    """
    Save vision result to database (image + api_calls).
    """
    image = session.get(Image, image_id)
    if not image:
        logger.error(f"Image {image_id} not found in database")
        return

    if result.metadata:
        image.subject = result.metadata.subject
        image.category = result.metadata.category
        image.attributes = result.metadata.attributes
        image.caption = result.metadata.caption
        image.confidence = result.metadata.confidence
        image.needs_review = result.metadata.needs_review
        image.validation_status = result.validation_status
    else:
        image.validation_status = result.validation_status
        image.needs_review = True  # Default to review on failure

    cost = 0.0
    
    api_call = ApiCall(
        image_id=image_id,
        model=model,
        input_tokens=None,
        output_tokens=None,
        estimated_cost_usd=cost,
        status="success" if result.validation_status in ("success", "partial") else "failed",
        error_message=result.error_message,
    )
    session.add(api_call)
    session.commit()


def process_image_with_retry(
    image_path: Path,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> VisionResult:
    """
    Process a single image with retry logic for transient errors only.
    Does NOT retry on validation errors (handled by classify_image internally).
    Does NOT retry on ModelNotFoundError.
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = classify_image(image_path)
            return result
        except TransientError as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # exponential backoff: 1s, 2s, 4s
                logger.warning(f"Transient error for {image_path.name} (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                import time
                time.sleep(delay)
            else:
                logger.error(f"All retries exhausted for {image_path.name}")
                return VisionResult(
                    filename=image_path.name,
                    metadata=None,
                    validation_status="failed",
                    error_message=f"Transient error after {max_retries} retries: {last_error}",
                )
        except ModelNotFoundError:
            # Re-raise model not found - not retryable
            raise
        except ValidationError as e:
            # Validation error - classify_image already handled retry internally
            logger.error(f"Validation error for {image_path.name}: {e}")
            return VisionResult(
                filename=image_path.name,
                metadata=None,
                validation_status="failed",
                error_message=str(e),
            )
    
    return VisionResult(
        filename=image_path.name,
        metadata=None,
        validation_status="failed",
        error_message="Unknown error",
    )


def run_vision_batch(
    images_dir: Path,
    max_workers: int = 1,  # Sequential for local inference
    progress_callback: Callable[[ProcessingStats], None] | None = None,
    clean_slate: bool = True,  # Process all images regardless of previous state
) -> ProcessingStats:
    """
    Run vision classification on all images in a directory.
    Sequential processing with local Ollama (no quota limits).
    If clean_slate=True, processes ALL images regardless of previous state.
    """
    # Get all image files
    image_files = sorted(images_dir.glob("*.jpg")) + sorted(images_dir.glob("*.jpeg")) + sorted(images_dir.glob("*.png"))
    
    stats = ProcessingStats(total=len(image_files))
    
    logger.info(f"Starting vision batch processing for {stats.total} images (sequential, local Ollama, clean_slate={clean_slate})")
    
    # Get existing images from DB to match by filename
    with get_session() as session:
        existing_images = {img.filename: img.id for img in session.query(Image).all()}
    
    # Process images sequentially (local inference)
    for img_path in image_files:
        image_id = existing_images.get(img_path.name)
        
        # Skip if already processed successfully (unless clean_slate)
        if image_id and not clean_slate:
            with get_session() as session:
                if is_image_already_processed(session, image_id):
                    logger.info(f"Skipping {img_path.name} - already processed successfully")
                    continue
        
        stats.processed += 1
        
        try:
            result = process_image_with_retry(img_path)
            
            # Save to database
            if image_id:
                with get_session() as session:
                    save_vision_result(session, image_id, result)
            else:
                logger.warning(f"No database record found for {img_path.name}")
            
            # Update stats
            if result.validation_status in ("success", "partial"):
                stats.succeeded += 1
                if result.metadata and result.metadata.needs_review:
                    stats.needs_review += 1
            else:
                stats.failed_validation += 1
                stats.errors.append(f"{img_path.name}: {result.error_message}")
                
        except ModelNotFoundError as e:
            # Model not found - stop processing
            logger.error(f"Model not found: {e}. Stopping batch.")
            stats.failed_model_not_found = stats.total - stats.processed
            stats.errors.append(f"{img_path.name}: MODEL_NOT_FOUND - {e}")
            break
            
        except Exception as e:
            stats.failed_transient += 1
            stats.errors.append(f"{img_path.name}: {e}")
            logger.error(f"Unexpected error processing {img_path.name}: {e}")
        
        # Progress callback
        if progress_callback:
            progress_callback(stats)
        else:
            stats.log_progress()
    
    return stats