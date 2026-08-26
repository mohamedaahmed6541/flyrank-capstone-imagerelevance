#!/usr/bin/env python3
"""
Populate database with images, tags, posts from manifest and seed data.
Run after migrations and seed.py download.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime

from app.db.session import get_session
from app.models.image import Image
from app.models.tag import Tag
from app.models.post import Post
from app.models.image import ImageTag


DATA_DIR = Path(__file__).parent.parent / "data"
MANIFEST_PATH = DATA_DIR / "manifest.json"
POSTS_PATH = DATA_DIR / "posts.json"


def main():
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    
    with open(POSTS_PATH) as f:
        posts_data = json.load(f)
    
    with get_session() as session:
        # Check if already populated
        existing_count = session.query(Image).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} images, skipping population")
            return
        
        # Create tags first
        categories = set()
        for img in manifest["images"]:
            categories.add(img["category"])
        
        tag_map = {}
        for cat in categories:
            tag = Tag(name=cat, category=cat)
            session.add(tag)
            session.flush()
            tag_map[cat] = tag.id
        
        # Insert images
        for img_data in manifest["images"]:
            # Use placeholder values for vision fields (will be updated by vision pipeline)
            image = Image(
                id=uuid.uuid4(),
                filename=img_data["filename"],
                url=img_data["source_url"],
                license=img_data["license"],
                attribution=img_data["attribution"],
                subject="",  # Will be filled by vision
                category=img_data["category"],
                attributes=[],
                caption="",
                confidence=0.0,
                embedding=[0.0] * 768,  # Placeholder, will be filled by embedding pipeline
                validation_status="pending",
                needs_review=False,
            )
            session.add(image)
            session.flush()
            
            # Link to tag
            tag_id = tag_map[img_data["category"]]
            session.add(ImageTag(image_id=image.id, tag_id=tag_id))
        
        # Insert posts
        for post_data in posts_data:
            post = Post(
                id=uuid.uuid4(),
                title=post_data["title"],
                slug=post_data["slug"],
                body=post_data["body"],
                target_category=post_data["target_category"],
                target_subject=post_data["target_subject"],
                embedding=None,
            )
            session.add(post)
        
        session.commit()
        print(f"Populated database with {len(manifest['images'])} images, {len(categories)} tags, {len(posts_data)} posts")


if __name__ == "__main__":
    main()