#!/usr/bin/env python3
"""Test the API endpoints directly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.matching import get_suggestions_for_post
from pathlib import Path

# Test the fox post (should accept vulpine images)
result = get_suggestions_for_post('f947c85d-0be2-431f-a7f0-57ac4cd50480', top_k=5)

print(f"Post: {result['post_title']}")
print(f"Target category: {result['post_target_category']}")
print("Suggestions:")
for s in result['suggestions']:
    print(f"  Rank {s['rank']}: {s['filename']} | cat={s['category']} | sim={s['similarity_score']:.4f} | guard={s['guard_passed']} | {s['guard_reason']}")
print(f"Accepted: {result['accepted_count']}, Rejected: {result['rejected_count']}, No match: {result['no_confident_match']}")

print("\n--- Testing wolf post (should accept canid_wolf) ---")
result2 = get_suggestions_for_post('bd6ed7a9-f844-437b-93a4-63770f350fd0', top_k=5)
print(f"Post: {result2['post_title']}")
print(f"Target category: {result2['post_target_category']}")
print("Suggestions:")
for s in result2['suggestions']:
    print(f"  Rank {s['rank']}: {s['filename']} | cat={s['category']} | sim={s['similarity_score']:.4f} | guard={s['guard_passed']} | {s['guard_reason']}")
print(f"Accepted: {result2['accepted_count']}, Rejected: {result2['rejected_count']}, No match: {result2['no_confident_match']}")

print("\n--- Testing fox post with wolf image (should REJECT - category mismatch) ---")
result3 = get_suggestions_for_post('f947c85d-0be2-431f-a7f0-57ac4cd50480', top_k=5)
print(f"Post: {result3['post_title']}")
print(f"Target category: {result3['post_target_category']}")
print("Suggestions:")
for s in result3['suggestions']:
    print(f"  Rank {s['rank']}: {s['filename']} | cat={s['category']} | sim={s['similarity_score']:.4f} | guard={s['guard_passed']} | {s['guard_reason']}")
print(f"Accepted: {result3['accepted_count']}, Rejected: {result3['rejected_count']}, No match: {result3['no_confident_match']}")