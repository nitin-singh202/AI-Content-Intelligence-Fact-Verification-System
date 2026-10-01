from fastapi import APIRouter, HTTPException
from models.schema import SearchRequest, SearchResponse
from services.search_service import retrieve_evidence_for_claim

router = APIRouter(tags=["Search & Retrieval"])


@router.post("/search", response_model=SearchResponse)
async def route_search_evidence(request: SearchRequest):
    """
    Search and retrieve live external evidence for a claim or query with credibility tier scoring.
    """
    query = request.query
    if not query or len(query.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Search query must be at least 3 characters long."
        )

    try:
        sources = retrieve_evidence_for_claim(query, max_sources=request.max_results or 5)
        return SearchResponse(
            query=query,
            sources=sources,
            total_found=len(sources)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidence retrieval failed: {str(e)}")
