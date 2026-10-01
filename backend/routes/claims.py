from fastapi import APIRouter, HTTPException
from models.schema import ExtractClaimsRequest, ExtractClaimsResponse
from services.claim_extractor import extract_claims
from utils.preprocess import prepare

router = APIRouter(tags=["Claims"])


@router.post("/extract-claims", response_model=ExtractClaimsResponse)
async def route_extract_claims(request: ExtractClaimsRequest):
    """
    Extract discrete, atomic, and verifiable factual claims from content.
    """
    text = request.text
    if not text or len(text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Text must be at least 10 characters long."
        )

    cleaned = prepare(text)

    try:
        response = extract_claims(cleaned)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claim extraction failed: {str(e)}")
