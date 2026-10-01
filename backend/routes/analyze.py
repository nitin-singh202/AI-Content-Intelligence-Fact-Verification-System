from fastapi import APIRouter, HTTPException
from models.schema import AnalyzeRequest, AnalyzeResponse
from services.pipeline import execute_full_pipeline
from utils.preprocess import prepare

router = APIRouter(tags=["Analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Unified Intelligence & Fact Verification endpoint.
    Extracts claims, retrieves web evidence, verifies veracity, and evaluates psychological manipulation.
    """
    text = request.text
    if not text or len(text.strip()) < 15:
        raise HTTPException(
            status_code=400,
            detail="Text must be at least 15 characters long."
        )

    cleaned = prepare(text)

    try:
        result = await execute_full_pipeline(
            text=cleaned,
            verify_facts=request.verify_facts if request.verify_facts is not None else True,
            max_claims_to_verify=request.max_claims_to_verify or 4
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")
