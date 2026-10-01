from typing import List
from models.schema import ClaimItem, ExtractClaimsResponse
from services.llm_service import call_llm


def extract_claims(text: str) -> ExtractClaimsResponse:
    """
    Extract atomic, verifiable factual claims from user text using LLM.
    """
    if not text or len(text.strip()) < 10:
        return ExtractClaimsResponse(claims=[], claim_count=0, summary="Text is too short for claim extraction.")

    try:
        raw_res = call_llm("claim_extraction", text)
        claims_data = raw_res.get("claims", [])

        extracted_claims: List[ClaimItem] = []
        for idx, item in enumerate(claims_data):
            if isinstance(item, dict) and item.get("text"):
                claim_id = item.get("id") or f"claim_{idx+1}"
                extracted_claims.append(
                    ClaimItem(
                        id=claim_id,
                        text=item.get("text", "").strip(),
                        category=item.get("category", "General Fact"),
                        importance=int(item.get("importance", 3)),
                        verifiable=bool(item.get("verifiable", True))
                    )
                )

        # Sort claims by importance descending
        extracted_claims.sort(key=lambda c: c.importance, reverse=True)

        return ExtractClaimsResponse(
            claims=extracted_claims,
            claim_count=len(extracted_claims),
            summary=raw_res.get("summary", "")
        )
    except Exception as e:
        # Fallback heuristic claim extractor if LLM parsing hit an edge case
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 15]
        fallback_claims = [
            ClaimItem(id=f"claim_{i+1}", text=sent, category="General Fact", importance=3, verifiable=True)
            for i, sent in enumerate(sentences[:3])
        ]
        return ExtractClaimsResponse(
            claims=fallback_claims,
            claim_count=len(fallback_claims),
            summary=f"Extraction completed with fallback ({str(e)})"
        )
