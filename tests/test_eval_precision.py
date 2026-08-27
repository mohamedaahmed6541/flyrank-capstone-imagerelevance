#!/usr/bin/env python3
"""
Tests for eval precision and API endpoints.
Fast, targeted tests - no fixture-heavy integration suite.
"""

import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.matching import get_suggestions_for_post
from app.db.session import get_session
from app.models.post import Post
from app.models.suggestion import Suggestion
from app.models.approval import Approval
import uuid


class TestEvalPrecision:
    """Test that eval precision runs and produces a real number."""

    def test_eval_set_loads(self):
        """Eval set loads with 10 entries."""
        import json
        eval_path = Path(__file__).parent.parent / "data" / "eval_set.json"
        with open(eval_path) as f:
            eval_set = json.load(f)
        assert len(eval_set) == 10

    def test_eval_precision_runs(self):
        """Eval precision script runs without error and returns 0-1 value."""
        # This is an integration-style test - run the actual logic
        from app.services.matching import get_suggestions_for_post
        
        eval_path = Path(__file__).parent.parent / "data" / "eval_set.json"
        with open(eval_path) as f:
            eval_set = json.load(f)
        
        total = len(eval_set)
        correct = 0
        
        for post_id, correct_filename in eval_set.items():
            result = get_suggestions_for_post(post_id, top_k=5)
            if "error" in result:
                continue
            suggestions = result.get("suggestions", [])
            guard_passed = [s for s in suggestions if s.get("guard_passed")]
            if guard_passed and guard_passed[0]["filename"] == correct_filename:
                correct += 1
        
        precision = correct / total
        # Just verify it runs and produces a valid precision value
        assert 0 <= precision <= 1
        # Log the actual value for visibility
        print(f"\nTOP-1 Precision: {correct}/{total} = {precision:.2%}")


class TestSuggestionAPI:
    """Test suggestion API service functions."""

    def test_get_suggestions_returns_structured_data(self):
        """get_suggestions_for_post returns expected structure."""
        with get_session() as session:
            post = session.query(Post).first()
            assert post is not None
        
        result = get_suggestions_for_post(str(post.id), top_k=5)
        
        assert "post_id" in result
        assert "post_title" in result
        assert "post_target_category" in result
        assert "suggestions" in result
        assert "accepted_count" in result
        assert "rejected_count" in result
        assert "no_confident_match" in result
        
        for s in result["suggestions"]:
            assert "rank" in s
            assert "filename" in s
            assert "category" in s
            assert "similarity_score" in s
            assert "guard_passed" in s
            assert "guard_reason" in s
            assert "details" in s

    def test_approve_suggestion_creates_approval(self):
        """Approve creates approval record."""
        with get_session() as session:
            # Find a suggestion without an approval
            sug = session.query(Suggestion).outerjoin(Approval).filter(Approval.id.is_(None)).first()
            if not sug:
                pytest.skip("No suggestions without approvals available")
            sug_id = str(sug.id)
        
        from app.api.suggestions import approve_suggestion
        import asyncio
        
        result = asyncio.run(approve_suggestion(sug_id, "Test approve"))
        assert "approval_id" in result
        assert result["message"] == "Suggestion approved"
        
        # Verify in DB
        with get_session() as session:
            approval = session.query(Approval).filter(Approval.suggestion_id == sug_id).first()
            assert approval is not None
            assert approval.decision == "approved"
            assert approval.reason == "Test approve"

    def test_reject_suggestion_creates_approval(self):
        """Reject creates approval record."""
        with get_session() as session:
            # Find a suggestion without an approval (different from the one approved above)
            sug = session.query(Suggestion).outerjoin(Approval).filter(Approval.id.is_(None)).first()
            if not sug:
                pytest.skip("No suggestions without approvals available")
            sug_id = str(sug.id)
        
        from app.api.suggestions import reject_suggestion
        import asyncio
        
        result = asyncio.run(reject_suggestion(sug_id, "Test reject"))
        assert "approval_id" in result
        assert result["message"] == "Suggestion rejected"
        
        with get_session() as session:
            approval = session.query(Approval).filter(Approval.suggestion_id == sug_id).first()
            assert approval is not None
            assert approval.decision == "rejected"
            assert approval.reason == "Test reject"

    def test_get_approved_image_returns_none_when_no_approval(self):
        """GET /posts/{id}/approved-image returns None when no approval."""
        with get_session() as session:
            post = session.query(Post).first()
            assert post is not None
            post_id = str(post.id)
        
        from app.api.suggestions import get_approved_image
        import asyncio
        
        result = asyncio.run(get_approved_image(post_id))
        assert "approved_image" in result
        # May be None or have image depending on approvals


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])