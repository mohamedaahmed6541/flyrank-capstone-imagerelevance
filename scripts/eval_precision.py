#!/usr/bin/env python3
"""
Evaluation script: computes TOP-1 precision against eval_set.json.

For each post in eval_set:
  - Get suggestions via matching service
  - Filter to guard-passed only
  - Check if rank-1 guard-passed matches labeled correct image
  - If no guard-passed suggestions, count as incorrect

TOP-1 Precision = posts with correct #1 guard-passed / total posts (10)
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.matching import get_suggestions_for_post


def main():
    # Load eval set
    eval_path = Path(__file__).parent.parent / "data" / "eval_set.json"
    with open(eval_path) as f:
        eval_set = json.load(f)

    print("=" * 70)
    print("TOP-1 PRECISION EVALUATION")
    print("=" * 70)
    print(f"Eval set size: {len(eval_set)} posts")
    print()

    correct = 0
    total = len(eval_set)
    results = []

    for post_id, correct_filename in eval_set.items():
        result = get_suggestions_for_post(post_id, top_k=5)
        
        if "error" in result:
            print(f"  [ERROR] {post_id}: {result['error']}")
            results.append((post_id, correct_filename, None, False, "Post not found"))
            continue

        suggestions = result.get("suggestions", [])
        guard_passed = [s for s in suggestions if s.get("guard_passed")]
        
        if not guard_passed:
            # No guard-passed candidates = incorrect
            print(f"  [MISS]  {result['post_title'][:40]}")
            print(f"           No guard-passed suggestions")
            print(f"           Expected: {correct_filename}")
            results.append((post_id, correct_filename, None, False, "No guard-passed"))
            continue

        top1 = guard_passed[0]
        top1_filename = top1["filename"]
        is_correct = top1_filename == correct_filename
        
        if is_correct:
            correct += 1
            status = "OK"
        else:
            status = "FAIL"

        print(f"  [{status}] {result['post_title'][:40]}")
        print(f"           Rank-1 guard-passed: {top1_filename} (sim={top1['similarity_score']:.4f})")
        print(f"           Expected:            {correct_filename}")
        results.append((post_id, correct_filename, top1_filename, is_correct, ""))

    print()
    print("=" * 70)
    print(f"TOP-1 PRECISION: {correct}/{total} = {correct/total:.2%}")
    print("=" * 70)
    print()
    print("Note: Fox category eval only includes 2 correctly-tagged images")
    print("(vulpine_00.jpg, vulpine_05.jpg). The 4 misclassified fox images")
    print("are not in the eval set's ground truth. Precision reflects")
    print("matching+guard accuracy on correctly-tagged images only.")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())