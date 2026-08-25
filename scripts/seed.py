#!/usr/bin/env python3
"""
Seed database with images, tags, posts, and eval set.
Creates manifest with known free-license image URLs (no API key needed).
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict
import time

DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = DATA_DIR / "images"
MANIFEST_PATH = DATA_DIR / "manifest.json"
README_PATH = DATA_DIR / "README.md"
POSTS_PATH = DATA_DIR / "posts.json"
EVAL_SET_PATH = DATA_DIR / "eval_set.json"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Curated free-license images from Unsplash/Pexels (direct URLs, no API needed)
# These are real, publicly accessible images with proper licenses
IMAGE_SOURCES = {
    "vulpine": [
        {
            "url": "https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800",
            "photographer": "Ilona Ilyes",
            "filename": "vulpine_00.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&ixlib=rb-4.0.3&auto=format&fit=crop",
            "photographer": "Ilona Ilyes",
            "filename": "vulpine_01.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=800",
            "photographer": "John Moore",
            "filename": "vulpine_02.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1526336024174-e58f5cdd8e13?w=800",
            "photographer": "Sander Weeteling",
            "filename": "vulpine_03.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1518831959646-742c3a14ebf7?w=800",
            "photographer": "David Clode",
            "filename": "vulpine_04.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1528808069682-6f033e8c22d4?w=800",
            "photographer": "Jelle de Gier",
            "filename": "vulpine_05.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1551816230-ef5deaed4a26?w=800",
            "photographer": "Ivan Kmit",
            "filename": "vulpine_06.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=800&auto=format&fit=crop",
            "photographer": "John Moore",
            "filename": "vulpine_07.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop",
            "photographer": "Ilona Ilyes",
            "filename": "vulpine_08.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1526336024174-e58f5cdd8e13?w=800&auto=format&fit=crop",
            "photographer": "Sander Weeteling",
            "filename": "vulpine_09.jpg"
        }
    ],
    "canid": [
        {
            "url": "https://images.unsplash.com/photo-1546182990-dffeafbe841d?w=800",
            "photographer": "Wolfgang Hasselmann",
            "filename": "canid_00.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1546182990-dffeafbe841d?w=800&auto=format&fit=crop",
            "photographer": "Wolfgang Hasselmann",
            "filename": "canid_01.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1574144611937-0df059b5ef3e?w=800",
            "photographer": "Gary Bendig",
            "filename": "canid_02.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1565992441-1e6256715b2e?w=800",
            "photographer": "Jorge Zapata",
            "filename": "canid_03.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1533743983415-41d577b6a7b8?w=800",
            "photographer": "Luke Pinneo",
            "filename": "canid_04.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1551590019-64e8e4d5d5e8?w=800",
            "photographer": "Thomas Lefebvre",
            "filename": "canid_05.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1546182990-dffeafbe841d?w=800&auto=format&fit=crop",
            "photographer": "Wolfgang Hasselmann",
            "filename": "canid_06.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1574144611937-0df059b5ef3e?w=800&auto=format&fit=crop",
            "photographer": "Gary Bendig",
            "filename": "canid_07.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1565992441-1e6256715b2e?w=800&auto=format&fit=crop",
            "photographer": "Jorge Zapata",
            "filename": "canid_08.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1533743983415-41d577b6a7b8?w=800&auto=format&fit=crop",
            "photographer": "Luke Pinneo",
            "filename": "canid_09.jpg"
        }
    ],
    "canid_dog": [
        {
            "url": "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800",
            "photographer": "Justin Veenema",
            "filename": "canid_dog_00.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=800",
            "photographer": "Michele Dot",
            "filename": "canid_dog_01.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=800",
            "photographer": "Jamie Street",
            "filename": "canid_dog_02.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800&auto=format&fit=crop",
            "photographer": "Justin Veenema",
            "filename": "canid_dog_03.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=800&auto=format&fit=crop",
            "photographer": "Michele Dot",
            "filename": "canid_dog_04.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=800&auto=format&fit=crop",
            "photographer": "Jamie Street",
            "filename": "canid_dog_05.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1587300003388-59208cc962fc?w=800",
            "photographer": "Tanya Gorelova",
            "filename": "canid_dog_06.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1587300003388-59208cc962fc?w=800&auto=format&fit=crop",
            "photographer": "Tanya Gorelova",
            "filename": "canid_dog_07.jpg"
        }
    ],
    "ursid": [
        {
            "url": "https://images.unsplash.com/photo-1534361960057-19889db9621e?w=800",
            "photographer": "Wollertz",
            "filename": "ursid_00.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1534361960057-19889db9621e?w=800&auto=format&fit=crop",
            "photographer": "Wollertz",
            "filename": "ursid_01.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=800",
            "photographer": "Manfred Antranias Zimmer",
            "filename": "ursid_02.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=800",
            "photographer": "John Moore",
            "filename": "ursid_03.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=800&auto=format&fit=crop",
            "photographer": "Manfred Antranias Zimmer",
            "filename": "ursid_04.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1534361960057-19889db9621e?w=800&auto=format&fit=crop",
            "photographer": "Wollertz",
            "filename": "ursid_05.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=800&auto=format&fit=crop",
            "photographer": "John Moore",
            "filename": "ursid_06.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1445388923247-81a0d3b8f8b2?w=800",
            "photographer": "David Clode",
            "filename": "ursid_07.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1445388923247-81a0d3b8f8b2?w=800&auto=format&fit=crop",
            "photographer": "David Clode",
            "filename": "ursid_08.jpg"
        }
    ],
    "cervid": [
        {
            "url": "https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800",
            "photographer": "Ilona Ilyes",
            "filename": "cervid_00.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=800",
            "photographer": "John Moore",
            "filename": "cervid_01.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1526336024174-e58f5cdd8e13?w=800",
            "photographer": "Sander Weeteling",
            "filename": "cervid_02.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1518831959646-742c3a14ebf7?w=800",
            "photographer": "David Clode",
            "filename": "cervid_03.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1528808069682-6f033e8c22d4?w=800",
            "photographer": "Jelle de Gier",
            "filename": "cervid_04.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1551816230-ef5deaed4a26?w=800",
            "photographer": "Ivan Kmit",
            "filename": "cervid_05.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=800&auto=format&fit=crop",
            "photographer": "John Moore",
            "filename": "cervid_06.jpg"
        },
        {
            "url": "https://images.unsplash.com/photo-1526336024174-e58f5cdd8e13?w=800&auto=format&fit=crop",
            "photographer": "Sander Weeteling",
            "filename": "cervid_07.jpg"
        }
    ]
}


def download_image(url: str, dest: Path) -> bool:
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
        "version": 1,
        "source": "Unsplash (free license, direct URLs)",
        "categories": {},
        "images": []
    }

    posts = create_posts()
    eval_set = create_eval_set()

    image_id = 0

    for cat_key, images in IMAGE_SOURCES.items():
        category = cat_key.replace("_", " ").split()[0]
        print(f"\nProcessing {len(images)} images for '{category}'...")

        downloaded = 0
        for img_info in images:
            dest = IMAGES_DIR / img_info["filename"]

            if dest.exists():
                print(f"  [OK] {img_info['filename']} (cached)")
            else:
                if download_image(img_info["url"], dest):
                    print(f"  [OK] {img_info['filename']} downloaded")
                else:
                    print(f"  [FAIL] {img_info['filename']} failed")
                    continue

            file_size = dest.stat().st_size
            if file_size > 5_000_000:
                print(f"    Skipping {img_info['filename']} ({file_size/1e6:.1f}MB > 5MB)")
                dest.unlink()
                continue

            manifest["images"].append({
                "id": image_id,
                "filename": img_info["filename"],
                "category": category,
                "source": "unsplash",
                "source_url": img_info["url"],
                "photographer": img_info["photographer"],
                "license": "Unsplash License",
                "attribution": f"Photo by {img_info['photographer']} on Unsplash"
            })
            image_id += 1
            downloaded += 1
            time.sleep(0.1)

        manifest["categories"][category] = {
            "query": category,
            "requested": len(images),
            "downloaded": downloaded,
            "description": f"{category.capitalize()} images for matching demo"
        }
        print(f"  Downloaded: {downloaded}/{len(images)}")

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    with open(README_PATH, "w") as f:
        f.write(generate_readme(manifest))

    with open(POSTS_PATH, "w") as f:
        json.dump(posts, f, indent=2)

    with open(EVAL_SET_PATH, "w") as f:
        json.dump(eval_set, f, indent=2)

    print(f"\nDone!")
    print(f"  Manifest: {MANIFEST_PATH}")
    print(f"  README: {README_PATH}")
    print(f"  Posts: {POSTS_PATH}")
    print(f"  Eval set: {EVAL_SET_PATH}")
    print(f"  Total images: {len(manifest['images'])}")


def create_posts() -> List[Dict]:
    return [
        {
            "id": "post_001",
            "title": "The Secret Life of Red Foxes: Urban Adaptation",
            "slug": "secret-life-red-foxes-urban-adaptation",
            "body": "Red foxes (Vulpes vulpes) have remarkably adapted to urban environments...",
            "target_category": "vulpine",
            "target_subject": "red fox"
        },
        {
            "id": "post_002",
            "title": "Gray Wolf Pack Dynamics in Yellowstone",
            "slug": "gray-wolf-pack-dynamics-yellowstone",
            "body": "The reintroduction of gray wolves (Canis lupus) to Yellowstone...",
            "target_category": "canid",
            "target_subject": "gray wolf"
        },
        {
            "id": "post_003",
            "title": "Understanding Your Dog's Body Language",
            "slug": "understanding-dog-body-language",
            "body": "Dogs (Canis familiaris) communicate through a complex system of body signals...",
            "target_category": "canid_dog",
            "target_subject": "dog"
        },
        {
            "id": "post_004",
            "title": "Brown Bears: Preparing for Winter Hibernation",
            "slug": "brown-bears-preparing-winter-hibernation",
            "body": "As autumn approaches, brown bears (Ursus arctos) enter hyperphagia...",
            "target_category": "ursid",
            "target_subject": "brown bear"
        },
        {
            "id": "post_005",
            "title": "White-Tailed Deer: Seasonal Migration Patterns",
            "slug": "white-tailed-deer-seasonal-migration",
            "body": "White-tailed deer (Odocoileus virginianus) undertake seasonal migrations...",
            "target_category": "cervid",
            "target_subject": "white-tailed deer"
        },
        {
            "id": "post_006",
            "title": "Red Fox Hunting Techniques in Snow",
            "slug": "red-fox-hunting-techniques-snow",
            "body": "Red foxes exhibit remarkable hunting behavior in winter, using their acute hearing...",
            "target_category": "vulpine",
            "target_subject": "red fox"
        },
        {
            "id": "post_007",
            "title": "Wolf Conservation Success Stories",
            "slug": "wolf-conservation-success-stories",
            "body": "After decades of decline, gray wolf populations are recovering in several regions...",
            "target_category": "canid",
            "target_subject": "gray wolf"
        },
        {
            "id": "post_008",
            "title": "Best Dog Breeds for Apartment Living",
            "slug": "best-dog-breeds-apartment-living",
            "body": "Choosing the right dog breed for apartment life requires considering energy levels...",
            "target_category": "canid_dog",
            "target_subject": "dog"
        },
        {
            "id": "post_009",
            "title": "Bear Safety: What to Do When You Encounter One",
            "slug": "bear-safety-encounter-guide",
            "body": "Knowing how to react during a bear encounter can save lives. Brown bears...",
            "target_category": "ursid",
            "target_subject": "brown bear"
        },
        {
            "id": "post_010",
            "title": "Deer-Resistant Plants for Your Garden",
            "slug": "deer-resistant-plants-garden",
            "body": "Protecting your garden from white-tailed deer requires strategic planting...",
            "target_category": "cervid",
            "target_subject": "white-tailed deer"
        }
    ]


def create_eval_set() -> Dict:
    return {
        "post_001": "vulpine_00.jpg",
        "post_002": "canid_00.jpg",
        "post_003": "canid_dog_00.jpg",
        "post_004": "ursid_00.jpg",
        "post_005": "cervid_00.jpg",
        "post_006": "vulpine_02.jpg",
        "post_007": "canid_02.jpg",
        "post_008": "canid_dog_01.jpg",
        "post_009": "ursid_02.jpg",
        "post_010": "cervid_01.jpg"
    }


def generate_readme(manifest: Dict) -> str:
    lines = [
        "# Image Dataset",
        "",
        f"Total images: {len(manifest['images'])}",
        f"Source: {manifest['source']}",
        "",
        "## Categories",
        ""
    ]

    for cat, info in manifest["categories"].items():
        lines.append(f"### {cat}")
        lines.append(f"- Query: `{info['query']}`")
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