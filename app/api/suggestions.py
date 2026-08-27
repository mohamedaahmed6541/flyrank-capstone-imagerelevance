"""API endpoints for image suggestions and approvals."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_session
from app.models.suggestion import Suggestion
from app.models.approval import Approval
from app.services.matching import get_suggestions_for_post, get_suggestions_for_post as get_suggestions

router = APIRouter(prefix="/posts", tags=["suggestions"])


@router.get("/{post_id}/suggestions")
async def get_post_suggestions(post_id: str, top_k: int = 5):
    """
    Get ranked image suggestions for a post with mismatch guard evaluation.
    """
    result = get_suggestions_for_post(post_id, top_k)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/suggestions/{suggestion_id}/approve")
async def approve_suggestion(suggestion_id: str, reason: str = ""):
    """
    Approve a suggested image for a post.
    """
    from app.db.session import get_session
    from app.models.suggestion import Suggestion
    from app.models.approval import Approval
    import uuid
    
    with get_session() as session:
        suggestion = session.get(Suggestion, suggestion_id)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        approval = Approval(
            id=uuid.uuid4(),
            suggestion_id=suggestion.id,
            decision="approved",
            reason=reason,
        )
        session.add(approval)
        session.commit()
        
        return {"message": "Suggestion approved", "approval_id": str(approval.id)}


@router.post("/suggestions/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: str, reason: str):
    """
    Reject a suggested image for a post.
    """
    from app.db.session import get_session
    from app.models.suggestion import Suggestion
    from app.models.approval import Approval
    import uuid
    
    with get_session() as session:
        suggestion = session.get(Suggestion, suggestion_id)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        approval = Approval(
            id=uuid.uuid4(),
            suggestion_id=suggestion.id,
            decision="rejected",
            reason=reason,
        )
        session.add(approval)
        session.commit()
        
        return {"message": "Suggestion rejected", "approval_id": str(approval.id)}


@router.get("/{post_id}/approved-image")
async def get_approved_image(post_id: str):
    """
    Get the approved image for a post (if any).
    """
    from app.db.session import get_session
    from app.models.suggestion import Suggestion
    from app.models.approval import Approval
    from app.models.image import Image
    
    with get_session() as session:
        # Find approved suggestion for this post
        approval = session.query(Approval).join(Suggestion).filter(
            Suggestion.post_id == post_id,
            Approval.decision == "approved"
        ).first()
        
        if not approval:
            return {"approved_image": None}
        
        suggestion = session.get(Suggestion, approval.suggestion_id)
        image = session.get(Image, suggestion.image_id)
        
        return {
            "approved_image": {
                "image_id": str(image.id),
                "filename": image.filename,
                "url": image.url,
                "subject": image.subject,
                "category": image.category,
                "confidence": image.confidence,
                "similarity_score": float(approval.suggestion.similarity_score),
            }
        }