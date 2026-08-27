#!/usr/bin/env python3
"""
Per-post breakdown of eval precision.
Shows expected vs actual #1 guard-passed for each post.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.matching import get_suggestions_for_post


def main():
    eval_path = Path(__file__).parent.parent / "data" / "eval_set.json"
    with open(eval_path) as f:
        eval_set = json.load(f)

    print("=" * 100)
    print("PER-POST EVAL BREAKDOWN")
    print("=" * 100)

    for post_id, expected_filename in eval_set.items():
        result = get_suggestions_for_post(post_id, top_k=5)
        
        if "error" in result:
            print(f"ERROR: {post_id} - {result['error']}")
            continue

        suggestions = result.get("suggestions", [])
        guard_passed = [s for s in suggestions if s.get("guard_passed")]
        
        print(f"\nPost: {result['post_title']}")
        print(f"  Target category: {result['post_target_category']}")
        print(f"  Expected (ground truth): {expected_filename}")
        print(f"  Guard-passed suggestions: {len(guard_passed)}")
        
        if not guard_passed:
            print(f"  -> NO GUARD-PASSED CANDIDATES")
            continue

        # Show all guard-passed with ranks and scores
        for i, s in enumerate(guard_passed):
            marker = " <- #1 ACTUAL" if i == 0 else ""
            match_marker = " MATCH" if s['filename'] == expected_filename else " MISMATCH"
            print(f"    Rank {i+1}: {s['filename']} (cat={s['category']}, sim={s['similarity_score']:.4f}){marker}{match_marker}")

        # Check if expected is even in guard-passed
        expected_in_guard = any(s['filename'] == expected_filename for s in guard_passed)
        if not expected_in_guard:
            print(f"  -> EXPECTED IMAGE NOT IN GUARD-PASSED AT ALL!")
            # Check if it was evaluated but rejected
            for s in suggestions:
                if s['filename'] == expected_filename:
                    print(f"     (was evaluated: guard_passed={s['guard_passed']}, reason={s['guard_reason']})")

    print("\n" + "=" * 100)
    print("SUMMARY BY CATEGORY")
    print("=" * 100)
    
    # Group by category
    by_category = {}
    for post_id, expected_filename in eval_set.items():
        result = get_suggestions_for_post(post_id, top_k=5)
        cat = result.get('post_target_category', 'unknown')
        if cat not in by_category:
            by_category[cat] = {'total': 0, 'correct': 0, 'posts': []}
        by_category[cat]['total'] += 1
        
        suggestions = result.get("suggestions", [])
        guard_passed = [s for s in suggestions if s.get("guard_passed")]
        
        is_correct = guard_passed and guard_passed[0]['filename'] == expected_filename
        if is_correct:
            by_category[cat]['correct'] += 1
        
        by_category[cat]['posts'].append({
            'title': result['post_title'][:50],
            'expected': expected_filename,
            'actual': guard_passed[0]['filename'] if guard_passed else 'NONE',
            'correct': is_correct
        })

    for cat, data in by_category.items():
        print(f"\n{cat.upper()}: {data['correct']}/{data['total']} correct")
        for p in data['posts']:
            status = "OK" if p['correct'] else "FAIL"
            print(f"  [{status}] {p['title']}")
            print(f"     Expected: {p['expected']} | Actual #1: {p['actual']}")


if __name__ == "__main__":
    main()