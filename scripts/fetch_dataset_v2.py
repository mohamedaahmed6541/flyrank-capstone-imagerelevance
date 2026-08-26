#!/usr/bin/env python3
"""
Fetch unique free-license images from Unsplash for each category.
Uses specific search terms to get the right animals.
Does NOT commit large binaries - downloads to data/images/ and writes manifest.
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict
import time

DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = DATA_DIR / "images"
MANIFEST_PATH = DATA_DIR / "manifest_v2.json"
README_PATH = DATA_DIR / "README_v2.md"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Specific search terms that return the RIGHT animals
CATEGORIES = {
    "vulpine": {
        "queries": ["red fox wild", "vulpes vulpes", "red fox forest"],
        "count": 10,
        "description": "Red fox (Vulpes vulpes) - for fox vs wolf mismatch demo"
    },
    "canid_wolf": {
        "queries": ["gray wolf wild", "canis lupus", "wolf pack", "timber wolf"],
        "count": 10,
        "description": "Gray wolf (Canis lupus) - primary mismatch target for fox posts"
    },
    "canid_dog": {
        "queries": ["dog breed", "domestic dog", "dog portrait", "golden retriever", "german shepherd"],
        "count": 8,
        "description": "Domestic dog (Canis familiaris) - similar canid, different species"
    },
    "ursid": {
        "queries": ["brown bear wild", "grizzly bear", "ursus arctos", "bear forest"],
        "count": 9,
        "description": "Brown bear (Ursus arctos) - distinct category"
    },
    "cervid": {
        "queries": ["white-tailed deer wild", "deer forest", "odocoileus virginianus", "buck deer"],
        "count": 8,
        "description": "White-tailed deer (Odocoileus virginianus) - distinct category"
    }
}

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")


def fetch_unsplash_images(query: str, count: int) -> List[Dict]:
    """Fetch images from Unsplash API."""
    if not UNSPLASH_ACCESS_KEY:
        return []

    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    params = {"query": query, "per_page": min(count, 30), "orientation": "landscape"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        print(f"Unsplash fetch failed for '{query}': {e}")
        return []


def fetch_pexels_images(query: str, count: int) -> List[Dict]:
    """Fetch images from Pexels API."""
    pexels_key = os.getenv("PEXELS_API_KEY")
    if not pexels_key:
        return []

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": pexels_key}
    params = {"query": query, "per_page": min(count, 80), "orientation": "landscape"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("photos", [])
    except Exception as e:
        print(f"Pexels fetch failed for '{query}': {e}")
        return []


def download_image(url: str, dest: Path) -> bool:
    """Download image to destination."""
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return False


def main():
    manifest = {
        "version": 2,
        "source": "Unsplash + Pexels (free license, unique URLs per category)",
        "categories": {},
        "images": []
    }

    total_needed = sum(c["count"] for c in CATEGORIES.values())
    print(f"Target: {total_needed} images across {len(CATEGORIES)} categories")

    image_id = 0

    for cat_key, cat_info in CATEGORIES.items():
        count = cat_info["count"]
        queries = cat_info["queries"]
        print(f"\nFetching {count} images for '{cat_key}'...")

        downloaded = 0
        used_urls = set()

        for query in queries:
            if downloaded >= count:
                break

            print(f"  Query: '{query}'")
            unsplash_results = fetch_unsplash_images(query, count - downloaded)
            pexels_results = fetch_pexels_images(query, count - downloaded)

            all_results = []
            for r in unsplash_results:
                img_url = r["urls"]["regular"]
                if img_url not in used_urls:
                    all_results.append({
                        "url": img_url,
                        "photographer": r.get("user", {}).get("name", "Unknown"),
                        "source": "unsplash",
                        "license": "Unsplash License"
                    })
                    used_urls.add(img_url)

            for r in pexels_results:
                img_url = r["src"]["large"]
                if img_url not in used_urls:
                    all_results.append({
                        "url": img_url,
                        "photographer": r.get("photographer", "Unknown"),
                        "source": "pexels",
                        "license": "Pexels License"
                    })
                    used_urls.add(img_url)

            for result in all_results:
                if downloaded >= count:
                    break

                ext = ".jpg"
                filename = f"{cat_key}_{downloaded:02d}{ext}"
                dest = IMAGES_DIR / filename

                if download_image(result["url"], dest):
                    file_size = dest.stat().st_size
                    if file_size > 5_000_000:
                        print(f"  Skipping {filename} ({file_size/1e6:.1f}MB > 5MB)")
                        dest.unlink()
                        continue

                    manifest["images"].append({
                        "id": image_id,
                        "filename": filename,
                        "category": cat_key,
                        "source": result["source"],
                        "source_url": result["url"],
                        "photographer": result["photographer"],
                        "license": result["license"],
                        "attribution": f"Photo by {result['photographer']} on {result['source'].capitalize()}"
                    })
                    image_id += 1
                    downloaded += 1
                    print(f"  ✓ {filename} ({file_size/1024:.1f}KB)")
                    time.sleep(0.1)

        manifest["categories"][cat_key] = {
            "queries": queries,
            "requested": count,
            "downloaded": downloaded,
            "description": cat_info["description"]
        }
        print(f"  Downloaded: {downloaded}/{count}")

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    readme = generate_readme(manifest)
    with open(README_PATH, "w") as f:
        f.write(readme)

    print(f"\nDone! Manifest: {MANIFEST_PATH}")
    print(f"README: {README_PATH}")
    print(f"Total images: {len(manifest['images'])}")


def generate_readme(manifest: Dict) -> str:
    lines = [
        "# Image Dataset v2",
        "",
        f"Total images: {len(manifest['images'])}",
        f"Source: {manifest['source']}",
        "",
        "## Categories",
        ""
    ]

    for cat, info in manifest["categories"].items():
        lines.append(f"### {cat}")
        lines.append(f"- Queries: {', '.join(f'`{q}`' for q in info['queries'])}")
        lines.append(f"- Requested: {info['requested']}, Downloaded: {info['downloaded']}")
        lines.append(f"- Description: {info['description']}")
        lines.append("")

    lines.append("## Image Details")
    lines.append("")

    for img in manifest["images"]:
        lines.append(f"### {img['filename']}")
        lines.append(f"- Category: {img['category']}")
        lines.append(f"- Source: {img['source']} ({img['source_url']})")
        lines.append(f"- Photographer: {img['photographer']}")
        lines.append(f"- License: {img['license']}")
        lines.append(f"- Attribution: {img['attribution']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()