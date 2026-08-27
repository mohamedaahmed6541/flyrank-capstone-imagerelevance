#!/usr/bin/env python3
"""
Download curated images using Pexels API.
Fetches images via Pexels search API for canid_wolf, ursid, cervid.
Keeps existing vulpine/canid_dog images (already correct).
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = DATA_DIR / "images"
MANIFEST_PATH = DATA_DIR / "manifest_v3.json"
README_PATH = DATA_DIR / "README_v3.md"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Pexels API configuration
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_API_URL = "https://api.pexels.com/v1/search"

# Search queries for each missing category
PEXELS_SEARCH_QUERIES = {
    "canid_wolf": "gray wolf",
    "ursid": "brown bear",
    "cervid": "white tailed deer",
}

# Existing working images we keep (don't re-download)
EXISTING_WORKING_IMAGES = {
    "vulpine": 6,   # 6 vulpine images already correct
    "canid_dog": 8, # 8 domestic dog images already correct
}

# Target counts per category (aim for ~4-5 each for missing categories)
TARGET_COUNTS = {
    "canid_wolf": 5,
    "ursid": 4,
    "cervid": 3,
}

DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = DATA_DIR / "images"
MANIFEST_PATH = DATA_DIR / "manifest_v3.json"
README_PATH = DATA_DIR / "README_v3.md"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def search_pexels(query: str, per_page: int = 15) -> List[Dict]:
    """Search Pexels API for images matching query."""
    if not PEXELS_API_KEY:
        raise ValueError("PEXELS_API_KEY not set in environment")
    
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}
    
    resp = requests.get(PEXELS_API_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("photos", [])


def download_image(url: str, dest: Path) -> bool:
    """Download image to destination, following redirects."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        resp = requests.get(url, timeout=60, stream=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }, allow_redirects=True)
        resp.raise_for_status()
        
        content_type = resp.headers.get('Content-Type', '')
        if 'image' not in content_type and 'octet-stream' not in content_type:
            print(f"  Warning: Content-Type is {content_type}, not image")
        
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return False


def download_pexels_photos(photo_list: List[Dict], cat_key: str, max_count: int) -> List[Dict]:
    """Download images from Pexels photo list."""
    downloaded = []
    
    for photo in photo_list:
        if len(downloaded) >= max_count:
            break
            
        # Get the large2x or original URL
        src = photo.get("src", {})
        url = src.get("large2x") or src.get("original") or src.get("large") or src.get("medium")
        if not url:
            continue
            
        filename = f"{cat_key}_{len(downloaded):02d}.jpg"
        dest = IMAGES_DIR / filename
        
        if dest.exists():
            print(f"  [OK] {filename} (cached)")
            continue
            
        print(f"  Downloading from: {url}")
        if download_image(url, dest):
            file_size = dest.stat().st_size
            if file_size > 5_000_000:
                print(f"  Skipping {filename} ({file_size/1e6:.1f}MB > 5MB)")
                dest.unlink()
                continue
            downloaded.append({
                "filename": filename,
                "url": photo.get("url", ""),
                "image_url": url,
                "photographer": photo.get("photographer", "Pexels Contributor"),
            })
            print(f"  [OK] {filename} ({file_size/1024:.1f}KB)")
            time.sleep(0.3)
        else:
            print(f"  [FAIL] Failed to download")
    
    return downloaded


def main():
    if not os.getenv("PEXELS_API_KEY"):
        print("[ERROR] PEXELS_API_KEY not set in environment")
        print("Get a free API key at https://www.pexels.com/api/")
        print("Then set PEXELS_API_KEY in your .env file")
        return 1
    
    manifest = {
        "version": 7,
        "source": "Pexels API (verified search results) + existing Unsplash (vulpine, canid_dog)",
        "categories": {},
        "images": []
    }
    
    image_id = 0
    
    # First, add existing working images to manifest (copy from existing manifest if available)
    old_manifest_path = Path(__file__).parent.parent / "data" / "manifest_v2.json"
    if old_manifest_path.exists():
        with open(old_manifest_path) as f:
            old_manifest = json.load(f)
            for img in old_manifest.get("images", []):
                if img["category"] in ["vulpine", "canid_dog"]:
                    manifest["images"].append({
                        "id": image_id,
                        "filename": img["filename"],
                        "category": img["category"],
                        "source": img["source"],
                        "source_url": img["source_url"],
                        "photographer": img["photographer"],
                        "license": img["license"],
                        "attribution": img["attribution"],
                    })
                    image_id += 1
    
    # Count existing vulpine/canid_dog
    vulpine_count = sum(1 for img in manifest["images"] if img["category"] == "vulpine")
    canid_dog_count = sum(1 for img in manifest["images"] if img["category"] == "canid_dog")
    print(f"Existing vulpine: {vulpine_count}, canid_dog: {canid_dog_count}")
    
    # Fetch and download for missing categories
    for cat_key, query in PEXELS_SEARCH_QUERIES.items():
        target_count = TARGET_COUNTS.get(cat_key, 5)
        print(f"\nSearching Pexels for '{query}' (target: {target_count})...")
        
        photos = search_pexels(query, per_page=15)
        print(f"Found {len(photos)} photos")
        
        downloaded = download_pexels_photos(photos, cat_key, target_count)
        
        for d in downloaded:
            manifest["images"].append({
                "id": image_id,
                "filename": d["filename"],
                "category": cat_key,
                "source": "pexels",
                "source_url": d["url"],
                "image_url": d["image_url"],
                "photographer": d["photographer"],
                "license": "Pexels License",
                "attribution": f"Photo by {d['photographer']} on Pexels",
            })
            image_id += 1
    
    # Save manifest
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Generate README
    readme = generate_readme(manifest)
    with open(README_PATH, "w") as f:
        f.write(readme)
    
    print(f"\nDone! Manifest: {MANIFEST_PATH}")
    print(f"README: {README_PATH}")
    print(f"Total images: {len(manifest['images'])}")
    return 0


def generate_readme(manifest: Dict) -> str:
    lines = [
        "# Image Dataset v7",
        "",
        f"Total images: {len(manifest['images'])}",
        f"Source: {manifest['source']}",
        "",
        "## Categories",
        ""
    ]

    for cat in ["vulpine", "canid_wolf", "canid_dog", "ursid", "cervid"]:
        count = sum(1 for img in manifest["images"] if img["category"] == cat)
        lines.append(f"### {cat}")
        lines.append(f"- Count: {count}")
        lines.append("")

    lines.append("## Image Details")
    lines.append("")

    for img in manifest["images"]:
        lines.append(f"### {img['filename']}")
        lines.append(f"- Category: {img['category']}")
        lines.append(f"- Source: {img['source']} ({img['source_url']})")
        if 'image_url' in img:
            lines.append(f"- Image URL: {img['image_url']}")
        lines.append(f"- Photographer: {img['photographer']}")
        lines.append(f"- License: {img['license']}")
        lines.append(f"- Attribution: {img['attribution']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    sys.exit(main())