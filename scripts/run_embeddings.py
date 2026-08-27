#!/usr/bin/env python3
"""
Generate embeddings for all images and posts in the database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_session
from app.models.image import Image
from app.models.post import Post
from app.services.embedding import embed_image_caption, embed_post_content

from sqlalchemy.orm import Session
from pathlib import Path


def generate_image_embeddings(session: Session) -> int:
    """Generate embeddings for all images missing them."""
    images = session.query(Image).filter(Image.embedding.is_(None)).all()
    updated = 0
    
    for img in images:
        if not img.caption or not img.subject:
            print(f"  Skipping {img.filename}: missing caption or subject")
            continue
        
        try:
            embedding = embed_image_caption(img.caption, img.subject, img.attributes or [])
            img.embedding = embedding
            session.commit()
            print(f"  [OK] {img.filename}")
        except Exception as e:
            print(f"  [FAIL] {img.filename}: {e}")
            session.rollback()
    
    return updated


def generate_post_embeddings(session: Session) -> int:
    """Generate embeddings for all posts missing them."""
    posts = session.query(Post).filter(Post.embedding.is_(None)).all()
    updated = 0
    
    for post in posts:
        try:
            embedding = embed_post_content(post.title, post.body)
            post.embedding = embedding
            session.commit()
            print(f"  [OK] {post.title}")
        except Exception as e:
            print(f"  [FAIL] {post.title}: {e}")
            session.rollback()
    
    return updated


def main():
    from app.db.session import get_session
    from app.models.image import Image
    from app.models.post import Post
    
    with get_session() as session:
        print("Generating image embeddings...")
        img_count = 0
        images = session.query(Image).filter(Image.embedding.is_(None)).all()
        for img in images:
            if not img.caption or not img.subject:
                print(f"  Skipping {img.filename}: missing caption or subject")
                continue
            try:
                embedding = embed_image_caption(img.caption, img.subject, img.attributes or [])
                img.embedding = embedding
                session.commit()
                print(f"  [OK] {img.filename}")
            except Exception as e:
                print(f"  [FAIL] {img.filename}: {e}")
                session.rollback()
        
        print("\nGenerating post embeddings...")
        posts = session.query(Post).filter(Post.embedding.is_(None)).all()
        for post in posts:
            try:
                embedding = embed_post_content(post.title, post.body)
                post.embedding = embedding
                session.commit()
                print(f"  [OK] {post.title}")
            except Exception as e:
                print(f"  [FAIL] {post.title}: {e}")
                session.rollback()
        
        print("\nDone!")


if __name__ == "__main__":
    main()