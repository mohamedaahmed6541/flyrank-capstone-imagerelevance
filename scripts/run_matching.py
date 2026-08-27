#!/usr/bin/env python3
"""Run the matching pipeline to generate image suggestions for posts."""

import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.matching import run_matching_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    print("Running matching pipeline...")
    stats = run_matching_pipeline()
    print(f"\nMatching Pipeline Results:")
    print(f"  Posts processed: {stats['posts_processed']}")
    print(f"  Total suggestions: {stats['total_suggestions']}")
    print(f"  Accepted: {stats['accepted']}")
    print(f"  Rejected: {stats['rejected']}")
    print(f"  No confident match: {stats['no_confident_match']}")