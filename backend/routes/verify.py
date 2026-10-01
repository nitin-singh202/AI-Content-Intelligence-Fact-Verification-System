from fastapi import APIRouter, HTTPException
from models.schema import VerifyClaimRequest, VerifyClaimResponse
from services.verification_service import verify_single_claim

router = APIRouter(tags=["Verification"])


@router.post("/verify", response_model=VerifyClaimResponse)
async def route_verify_claim(request: VerifyClaimRequest):
    """
    Verify a single claim against retrieved live web evidence using grounded LLM verification.
    """
    claim = request.claim
    if not claim or len(claim.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Claim text must be at least 5 characters long."
        )

    try:
        result = verify_single_claim(
            claim_text=claim.strip(),
            claim_id=request.claim_id or "claim_1",
            category=request.category or "General Fact",
            importance=request.importance or 3,
            custom_sources=request.custom_sources
        )
        return VerifyClaimResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
