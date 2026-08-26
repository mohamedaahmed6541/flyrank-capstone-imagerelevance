#!/usr/bin/env python3
"""
Seed database with images from manifest_v2.json and posts/eval set.
Creates fresh database entries for the new curated dataset.
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
from app.models.api_call import ApiCall


DATA_DIR = Path(__file__).parent.parent / "data"
MANIFEST_PATH = DATA_DIR / "manifest_v2.json"
POSTS_PATH = DATA_DIR / "posts.json"
EVAL_SET_PATH = DATA_DIR / "eval_set.json"


def main():
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    
    with open(POSTS_PATH) as f:
        posts_data = json.load(f)
    
    with open(EVAL_SET_PATH) as f:
        eval_set = json.load(f)
    
    with get_session() as session:
        # Clear existing data
        print("Clearing existing data...")
        session.query(ImageTag).delete()
        session.query(ApiCall).delete()
        session.query(Image).delete()
        session.query(Tag).delete()
        session.query(Post).delete()
        session.commit()
        
        # Create tags for each category
        categories = ["vulpine", "canid_wolf", "canid_dog", "ursid", "cervid"]
        tag_map = {}
        for cat in categories:
            tag = Tag(name=cat, category=cat)
            session.add(tag)
            session.flush()
            tag_map[cat] = tag.id
        
        # Insert images from manifest
        for img_data in manifest["images"]:
            image = Image(
                id=uuid.uuid4(),
                filename=img_data["filename"],
                url=img_data["source_url"],
                license=img_data["license"],
                attribution=img_data["attribution"],
                subject="",  # Will be filled by vision pipeline
                category=img_data["category"],
                attributes=[],
                caption="",
                confidence=0.0,
                embedding=[0.0] * 768,
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
        
        # Count
        img_count = session.query(Image).count()
        tag_count = session.query(Tag).count()
        post_count = session.query(Post).count()
        
        print(f"Seeded database with {img_count} images, {tag_count} tags, {post_count} posts")


if __name__ == "__main__":
    main()