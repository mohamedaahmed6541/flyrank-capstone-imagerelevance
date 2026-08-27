#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_session
from app.models.image import Image
from app.models.post import Post
from app.services.matching import evaluate_guard, get_suggestions_for_post
from app.services.embedding import cosine_similarity
from app.core.config import settings
import numpy as np

THRESHOLD = settings.SIMILARITY_THRESHOLD

def get_post_by_category(target_category):
    with get_session() as session:
        return session.query(Post).filter(Post.target_category == target_category).first()

def get_image_by_filename(filename):
    with get_session() as session:
        return session.query(Image).filter(Image.filename == filename).first()

def get_image_embedding(image):
    if image.embedding:
        return np.array(image.embedding, dtype=np.float32)
    return None

def get_post_embedding(post):
    if post.embedding:
        return np.array(post.embedding, dtype=np.float32)
    return None

def run_scenario(name, post, image, expected):
    if not post.embedding or not image.embedding:
        return False, "Missing embedding", 0.0
    post_emb = get_post_embedding(post)
    img_emb = get_image_embedding(image)
    similarity = cosine_similarity(post_emb, img_emb)
    result = evaluate_guard(post, image, similarity)
    actual = "ACCEPT" if result.accepted else "REJECT"
    passed = actual == expected
    return passed, result.reason, similarity

def test_no_confident_match():
    with get_session() as session:
        post = session.query(Post).filter(Post.target_category == "cervid").first()
        if not post:
            return False, "No cervid post found", []
        result = get_suggestions_for_post(str(post.id), top_k=5)
        accepted = result.get("accepted_count", 0)
        suggestions = result.get("suggestions", [])
        all_rejected = all(not s["guard_passed"] for s in suggestions)
        reasons_listed = all(s.get("guard_reason") for s in suggestions if not s["guard_passed"])
        details = [(s["filename"], s["similarity_score"], s["guard_reason"]) for s in suggestions]
        if accepted == 0 and all_rejected and reasons_listed:
            return True, "No confident match - {} candidates rejected with reasons".format(len(suggestions)), details
        return False, "Expected no confident match, got accepted={}, suggestions={}".format(accepted, len(suggestions)), details

def analyze_all_suggestions():
    """Analyze all 50 suggestions from the matching pipeline run."""
    with get_session() as session:
        from app.models.suggestion import Suggestion
        suggestions = session.query(Suggestion).all()
        
        similarity_rejects = 0
        category_rejects = 0
        confidence_rejects = 0
        multi_rejects = 0
        
        for s in suggestions:
            if not s.guard_passed:
                reason = s.guard_reason or ""
                has_sim = "Similarity below threshold" in reason
                has_cat = "Category mismatch" in reason
                has_conf = "Confidence below floor" in reason
                
                count = sum([has_sim, has_cat, has_conf])
                if count > 1:
                    multi_rejects += 1
                elif has_sim:
                    similarity_rejects += 1
                elif has_cat:
                    category_rejects += 1
                elif has_conf:
                    confidence_rejects += 1
        
        return {
            "total": len(suggestions),
            "accepted": sum(1 for s in suggestions if s.guard_passed),
            "rejected": sum(1 for s in suggestions if not s.guard_passed),
            "similarity_only": similarity_rejects,
            "category_only": category_rejects,
            "confidence_only": confidence_rejects,
            "multiple": multi_rejects
        }

def main():
    print("=" * 90)
    print("MISMATCH GUARD VERIFICATION - 9 SCENARIOS")
    print("=" * 90)

    fox_post = get_post_by_category("vulpine")
    wolf_post = get_post_by_category("canid_wolf")
    bear_post = get_post_by_category("ursid")
    deer_post = get_post_by_category("cervid")
    dog_post = get_post_by_category("canid_dog")

    if not all([fox_post, wolf_post, bear_post, deer_post, dog_post]):
        print("ERROR: Missing posts for one or more categories")
        return 1

    vulpine_00 = get_image_by_filename("vulpine_00.jpg")
    vulpine_01 = get_image_by_filename("vulpine_01.jpg")
    vulpine_02 = get_image_by_filename("vulpine_02.jpg")
    vulpine_05 = get_image_by_filename("vulpine_05.jpg")

    with get_session() as session:
        canid_wolf_img = session.query(Image).filter(Image.category == "canid_wolf").first()
        ursid_img = session.query(Image).filter(Image.category == "ursid").first()
        cervid_img = session.query(Image).filter(Image.category == "cervid").first()
        canid_dog_img = session.query(Image).filter(Image.category == "canid_dog").first()

    if not all([vulpine_00, vulpine_01, vulpine_02, vulpine_05, canid_wolf_img, ursid_img, cervid_img, canid_dog_img]):
        print("ERROR: Missing test images")
        return 1

    scenarios = [
        ("1. Fox post -> vulpine_00.jpg (correct fox)", fox_post, vulpine_00, "ACCEPT"),
        ("2. Fox post -> vulpine_01.jpg (mistagged as canid_dog)", fox_post, vulpine_01, "REJECT"),
        ("3. Wolf post -> canid_wolf image", wolf_post, canid_wolf_img, "ACCEPT"),
        ("4. Wolf post -> vulpine_00.jpg (fox)", wolf_post, vulpine_00, "REJECT"),
        ("5. Wolf post -> vulpine_01.jpg (mistagged fox->dog)", wolf_post, vulpine_01, "REJECT"),
        ("6. Bear post -> ursid image", bear_post, ursid_img, "ACCEPT"),
        ("7. Deer post -> cervid image", deer_post, cervid_img, "ACCEPT"),
        ("8. Dog post -> canid_dog image", dog_post, canid_dog_img, "ACCEPT"),
    ]

    results = []
    for name, post, image, expected in scenarios:
        passed, reason, sim = run_scenario(name, post, image, expected)
        if expected == "ACCEPT":
            actual = "ACCEPT" if passed else "REJECT"
        else:
            actual = "REJECT" if passed else "ACCEPT"
        status = "PASS" if passed else "FAIL"
        results.append((name, status, expected, actual, reason, sim))
        sim_str = "{:.4f}".format(sim)
        print("[{}] {}".format(status, name))
        print("       Expected: {}, Got: {}, Similarity: {} (threshold: {})".format(expected, actual, sim_str, THRESHOLD))
        print("       Reason: {}".format(reason))
        print()

    print("9. Post with only wrong-category candidates -> No confident match")
    passed, reason, details = test_no_confident_match()
    status = "PASS" if passed else "FAIL"
    results.append(("9. No confident match", status, "No confident match", "No confident match" if passed else "Has matches", reason, 0.0))
    print("[{}] 9. No confident match".format(status))
    print("       {}".format(reason))
    for fname, sim, reason_str in details:
        print("       - {}: sim={:.4f}, reason={}".format(fname, sim, reason_str))
    print()

    print("=" * 90)
    print("FULL PIPELINE ANALYSIS (50 suggestions across 10 posts)")
    print("=" * 90)
    analysis = analyze_all_suggestions()
    print("Total suggestions:      {}".format(analysis["total"]))
    print("Accepted:               {}".format(analysis["accepted"]))
    print("Rejected:               {}".format(analysis["rejected"]))
    print("  - Similarity only:    {}".format(analysis["similarity_only"]))
    print("  - Category only:      {}".format(analysis["category_only"]))
    print("  - Confidence only:    {}".format(analysis["confidence_only"]))
    print("  - Multiple reasons:   {}".format(analysis["multiple"]))
    print()

    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)
    passed_count = sum(1 for r in results if r[1] == "PASS")
    total = len(results)
    print("Scenarios passed: {}/{}".format(passed_count, total))
    for name, status, _, _, _, _ in results:
        print("  [{}] {}".format(status, name))

    return 0 if passed_count == total else 1

if __name__ == "__main__":
    sys.exit(main())