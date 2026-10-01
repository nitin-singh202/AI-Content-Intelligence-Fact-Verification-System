from typing import List, Optional
from models.schema import ClaimVerificationResult, SourceEvidence
from services.llm_service import call_llm
from services.evidence_service import format_evidence_for_prompt, calculate_evidence_strength
from services.search_service import retrieve_evidence_for_claim


def calibrate_confidence(
    llm_confidence: float,
    verdict: str,
    sources: List[SourceEvidence],
    disagreement_detected: bool
) -> float:
    """
    Calibrate the final confidence score combining LLM self-assessment,
    number of independent sources, average domain authority, and source agreement.
    """
    if not sources:
        return 0.15 if verdict == "INSUFFICIENT_EVIDENCE" else 0.25

    stats = calculate_evidence_strength(sources)
    source_count = stats["source_count"]
    avg_trust = stats["avg_trust_score"]
    has_primary = stats["has_primary_source"]

    # Source quantity factor (up to +0.15 for 4+ sources)
    quantity_bonus = min(0.15, (source_count - 1) * 0.05) if source_count > 1 else -0.10

    # Domain authority factor (centered around 0.70)
    trust_adjustment = (avg_trust - 0.70) * 0.25

    # Primary source bonus
    primary_bonus = 0.08 if has_primary else 0.0

    # Disagreement penalty
    disagreement_penalty = -0.20 if disagreement_detected else 0.0

    # Base LLM confidence
    base_conf = max(0.1, min(0.95, float(llm_confidence)))

    calibrated = base_conf + quantity_bonus + trust_adjustment + primary_bonus + disagreement_penalty

    # Hard bounds based on verdict type
    if verdict == "INSUFFICIENT_EVIDENCE":
        calibrated = min(0.45, calibrated)
    elif verdict in ["SUPPORTED", "CONTRADICTED"]:
        if source_count >= 2 and avg_trust >= 0.75:
            calibrated = max(0.65, min(0.98, calibrated))
        else:
            calibrated = max(0.40, min(0.85, calibrated))
    elif verdict == "PARTIALLY_SUPPORTED":
        calibrated = max(0.45, min(0.80, calibrated))

    return round(max(0.05, min(0.99, calibrated)), 2)


def verify_single_claim(
    claim_text: str,
    claim_id: str = "claim_1",
    category: str = "General Fact",
    importance: int = 3,
    custom_sources: Optional[List[SourceEvidence]] = None
) -> ClaimVerificationResult:
    """
    Verify a single factual claim by retrieving evidence and calling the grounded LLM verification engine.
    """
    # 1. Retrieve evidence if not provided
    sources = custom_sources if custom_sources is not None else retrieve_evidence_for_claim(claim_text, max_sources=5)

    if not sources:
        return ClaimVerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            category=category,
            importance=importance,
            verdict="INSUFFICIENT_EVIDENCE",
            confidence=0.20,
            explanation="No external web sources or primary documentation could be retrieved for this claim.",
            supporting_evidence=[],
            refuting_evidence=[],
            disagreement_detected=False,
            sources=[],
            primary_source_cited=None
        )

    # 2. Build grounded prompt payload
    prompt_context = format_evidence_for_prompt(claim_text, sources)

    try:
        raw_res = call_llm("verification", prompt_context, temperature=0.1)

        verdict = raw_res.get("verdict", "INSUFFICIENT_EVIDENCE").upper()
        if verdict not in ["SUPPORTED", "CONTRADICTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT_EVIDENCE"]:
            verdict = "INSUFFICIENT_EVIDENCE"

        raw_conf = float(raw_res.get("confidence", 0.60))
        disagreement = bool(raw_res.get("disagreement_detected", False))

        final_confidence = calibrate_confidence(raw_conf, verdict, sources, disagreement)

        return ClaimVerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            category=category,
            importance=importance,
            verdict=verdict,
            confidence=final_confidence,
            explanation=raw_res.get("explanation", "Verification completed against retrieved evidence."),
            supporting_evidence=raw_res.get("supporting_evidence", []),
            refuting_evidence=raw_res.get("refuting_evidence", []),
            disagreement_detected=disagreement,
            disagreement_details=raw_res.get("disagreement_details"),
            sources=sources,
            primary_source_cited=raw_res.get("primary_source_cited")
        )
    except Exception as e:
        return ClaimVerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            category=category,
            importance=importance,
            verdict="INSUFFICIENT_EVIDENCE",
            confidence=0.25,
            explanation=f"Verification encountered reasoning error: {str(e)}",
            supporting_evidence=[],
            refuting_evidence=[],
            disagreement_detected=False,
            sources=sources,
            primary_source_cited=None
        )
