"""Batch processor for vision pipeline using ThreadPoolExecutor."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.core.config import settings
from app.db.session import get_session
from app.models.image import Image
from app.models.api_call import ApiCall
from app.schemas.vision import VisionResult, CONFIDENCE_FLOOR
from app.services.vision import classify_image, TransientError, VisionError
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
    needs_review: int = 0
    total_cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)

    def log_progress(self) -> None:
        logger.info(
            f"Progress: {self.processed}/{self.total} "
            f"(succeeded: {self.succeeded}, "
            f"validation_failed: {self.failed_validation}, "
            f"transient_failed: {self.failed_transient}, "
            f"needs_review: {self.needs_review}, "
            f"cost: ${self.total_cost_usd:.6f})"
        )


def estimate_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float:
    """
    Estimate cost for Gemini Flash free tier.
    Free tier: $0.00 per request (but track anyway).
    """
    # Gemini Flash free tier is $0, but we track for future paid tiers
    # If paid: ~$0.075 per 1M input tokens, $0.30 per 1M output tokens
    if input_tokens is None or output_tokens is None:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * 0.075
    output_cost = (output_tokens / 1_000_000) * 0.30
    return input_cost + output_cost


def process_image_with_retry(
    image_path: Path,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> VisionResult:
    """
    Process a single image with retry logic for transient errors.
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
                time.sleep(delay)
            else:
                logger.error(f"All retries exhausted for {image_path.name}")
                # Return a failed result instead of raising
                return VisionResult(
                    filename=image_path.name,
                    metadata=None,
                    validation_status="failed",
                    error_message=f"Transient error after {max_retries} retries: {last_error}",
                )
        except VisionError as e:
            # Non-transient validation error - don't retry
            logger.error(f"Validation error for {image_path.name}: {e}")
            return VisionResult(
                filename=image_path.name,
                metadata=None,
                validation_status="failed",
                error_message=str(e),
            )
    
    # Should not reach here
    return VisionResult(
        filename=image_path.name,
        metadata=None,
        validation_status="failed",
        error_message="Unknown error",
    )


def save_vision_result(
    session,
    image_id: uuid.UUID,
    result: VisionResult,
    model: str = "gemini-1.5-flash",
) -> None:
    """
    Save vision result to database (image + api_calls).
    """
    # Update image record
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

    # Calculate cost
    cost = 0.0  # We'll extract from usage if available
    
    # Record API call
    api_call = ApiCall(
        image_id=image_id,
        model=model,
        input_tokens=None,  # Would extract from usage metadata
        output_tokens=None,
        estimated_cost_usd=cost,
        status="success" if result.validation_status != "failed" else "failed",
        error_message=result.error_message,
    )
    session.add(api_call)
    session.commit()
    
    # Update cost tracking if we have usage data
    # (In a real implementation, we'd pass usage from classify_image)


def run_vision_batch(
    images_dir: Path,
    max_workers: int = 3,
    progress_callback: Callable[[ProcessingStats], None] | None = None,
) -> ProcessingStats:
    """
    Run vision classification on all images in a directory.
    Uses ThreadPoolExecutor for controlled concurrency.
    """
    # Get all image files
    image_files = sorted(images_dir.glob("*.jpg")) + sorted(images_dir.glob("*.jpeg")) + sorted(images_dir.glob("*.png"))
    
    stats = ProcessingStats(total=len(image_files))
    
    logger.info(f"Starting vision batch processing for {stats.total} images with {max_workers} workers")
    
    # Get existing images from DB to match by filename
    with get_session() as session:
        existing_images = {img.filename: img.id for img in session.query(Image).all()}
    
    # Process images in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {
            executor.submit(process_image_with_retry, img_path): img_path
            for img_path in image_files
        }
        
        # Process completed tasks
        for future in as_completed(future_to_path):
            img_path = future_to_path[future]
            stats.processed += 1
            
            try:
                result = future.result()
                
                # Save to database
                image_id = existing_images.get(img_path.name)
                if image_id:
                    with get_session() as session:
                        save_vision_result(session, image_id, result)
                else:
                    logger.warning(f"No database record found for {img_path.name}")
                
                # Update stats
                if result.validation_status == "success":
                    stats.succeeded += 1
                    if result.metadata and result.metadata.needs_review:
                        stats.needs_review += 1
                elif result.validation_status == "partial":
                    stats.succeeded += 1
                    if result.metadata and result.metadata.needs_review:
                        stats.needs_review += 1
                else:
                    stats.failed_validation += 1
                    stats.errors.append(f"{img_path.name}: {result.error_message}")
                    
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