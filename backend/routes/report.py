import os
from fastapi import APIRouter, HTTPException
from models.schema import ReportRequest, AnalyzeResponse, HealthCheckResponse
from services.pipeline import execute_full_pipeline
from utils.preprocess import prepare

router = APIRouter(tags=["System & Reports"])


@router.post("/report", response_model=AnalyzeResponse)
async def generate_full_report(request: ReportRequest):
    """
    Generate a comprehensive intelligence and fact verification report.
    """
    text = request.text
    if not text or len(text.strip()) < 15:
        raise HTTPException(status_code=400, detail="Text must be at least 15 characters long.")

    cleaned = prepare(text)
    return await execute_full_pipeline(text=cleaned, verify_facts=True, max_claims_to_verify=6)


@router.get("/health", response_model=HealthCheckResponse)
def health_check():
    """
    Health check and system capability overview.
    """
    return HealthCheckResponse(
        status="healthy",
        model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
        search_provider="DuckDuckGo Search + Wikipedia Fallback",
        features=[
            "Claim Extraction",
            "Multi-Tier Web Retrieval",
            "Domain Credibility Scoring",
            "Grounded Fact Verification",
            "Contradiction & Disagreement Detection",
            "Psychological Manipulation Analysis",
            "Propaganda Detection",
            "Misinformation Linguistic Risk",
            "Calibrated Confidence Engine"
        ]
    )


@router.get("/models")
def list_available_models():
    """
    List configured models and fallback configuration.
    """
    return {
        "primary_model": os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
        "fallback_models": [
            "anthropic/claude-3.5-haiku",
            "google/gemini-2.0-flash-001",
            "nvidia/nemotron-3-ultra-550b-a55b"
        ],
        "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY"))
    }
