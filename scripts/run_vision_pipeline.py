#!/usr/bin/env python3
"""
Vision pipeline runner script.
Processes all images in data/images/ through Gemini Flash vision model.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.env_check import ensure_env_file
from app.core.config import settings
from app.db.session import get_session
from app.models.image import Image
from app.services.batch import run_vision_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Main entry point."""
    # Ensure .env exists and has valid API key
    ensure_env_file()
    
    # Get images directory
    images_dir = Path(__file__).parent.parent / "data" / "images"
    if not images_dir.exists():
        logger.error(f"Images directory not found: {images_dir}")
        return 1
    
    # Check database has image records
    with get_session() as session:
        count = session.query(Image).count()
        if count == 0:
            logger.error("No images in database. Run 'python scripts/seed.py' first.")
            return 1
        logger.info(f"Found {count} images in database")
    
    # Run batch processing
    logger.info("Starting vision pipeline...")
    stats = run_vision_batch(images_dir, max_workers=3)
    
    # Print summary
    print("\n" + "=" * 60)
    print("VISION PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Total images:          {stats.total}")
    print(f"Processed:             {stats.processed}")
    print(f"Succeeded:             {stats.succeeded}")
    print(f"  - Needs review:      {stats.needs_review}")
    print(f"Failed (validation):   {stats.failed_validation}")
    print(f"Failed (transient):    {stats.failed_transient}")
    print(f"Total estimated cost:  ${stats.total_cost_usd:.6f}")
    print("=" * 60)
    
    if stats.errors:
        print("\nErrors:")
        for err in stats.errors:
            print(f"  - {err}")
    
    # Exit with error code if any validation failures
    if stats.failed_validation > 0 or stats.failed_transient > 0:
        logger.warning("Some images failed processing")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())