import pytest
from services.claim_extractor import extract_claims
from services.search_service import retrieve_evidence_for_claim
from services.verification_service import verify_single_claim
from services.pipeline import execute_full_pipeline


@pytest.mark.asyncio
async def test_live_claim_extraction_and_verification():
    sample_text = (
        "NASA officially announced that the Artemis program aims to land the first woman and next man on the Moon. "
        "The project collaborates with international partners and commercial space companies."
    )

    # 1. Test claim extraction
    claims_resp = extract_claims(sample_text)
    assert claims_resp.claim_count > 0
    assert len(claims_resp.claims) > 0

    first_claim = claims_resp.claims[0]
    assert first_claim.text != ""

    # 2. Test search evidence retrieval
    sources = retrieve_evidence_for_claim(first_claim.text, max_sources=3)
    assert len(sources) > 0
    assert sources[0].domain != ""

    # 3. Test verification
    verification = verify_single_claim(
        claim_text=first_claim.text,
        claim_id=first_claim.id,
        category=first_claim.category,
        importance=first_claim.importance,
        custom_sources=sources
    )
    assert verification.verdict in ["SUPPORTED", "CONTRADICTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT_EVIDENCE"]
    assert 0.0 <= verification.confidence <= 1.0
    assert len(verification.explanation) > 10


@pytest.mark.asyncio
async def test_live_full_pipeline():
    sample_input = "The Indian Space Research Organisation (ISRO) successfully launched the Chandrayaan-3 lunar mission in 2023."
    response = await execute_full_pipeline(sample_input, verify_facts=True, max_claims_to_verify=1)

    assert response.category != ""
    assert response.final_risk in ["LOW", "MEDIUM", "HIGH"]
    assert len(response.claims_verified) >= 1
    assert response.synthesis is not None
    assert response.processing_time_ms > 0
