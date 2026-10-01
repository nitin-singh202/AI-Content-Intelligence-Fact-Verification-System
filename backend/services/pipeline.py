import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

from models.schema import (
    AnalyzeResponse,
    ClaimVerificationResult,
    IntelligenceSynthesis,
    ManipulationResult,
    PropagandaResult,
    MisinformationResult,
)
from services.content_intelligence import (
    analyze_manipulation,
    analyze_propaganda,
    analyze_misinformation_risk,
    classify_category,
    calculate_risk_level,
)
from services.claim_extractor import extract_claims
from services.verification_service import verify_single_claim
from services.llm_service import call_llm

thread_pool = ThreadPoolExecutor(max_workers=8)


def _synthesize_intelligence(
    text: str,
    claims_verified: List[ClaimVerificationResult],
    manipulation: ManipulationResult,
    propaganda: PropagandaResult,
    misinformation: MisinformationResult
) -> IntelligenceSynthesis:
    """
    Synthesize all factual verification verdicts and psychological metrics into a unified summary.
    """
    if not claims_verified:
        # Fallback synthesis based solely on psychological analysis
        manip_score = manipulation.score
        if manip_score > 70:
            verdict = "HIGH_MANIPULATION_RISK"
            score = 35
            intent = "Sensationalist"
        elif manip_score > 40:
            verdict = "MODERATE_BIAS"
            score = 65
            intent = "Opinionated"
        else:
            verdict = "UNVERIFIED"
            score = 75
            intent = "Informative"

        return IntelligenceSynthesis(
            overall_verdict=verdict,
            factual_integrity_score=score,
            content_intent=intent,
            executive_summary="No discrete verifiable factual claims were extracted. Psychological patterns were analyzed.",
            key_takeaways=["Text relies primarily on subjective/persuasive framing.", "No major verifiable factual statements detected."]
        )

    # Calculate factual integrity score based on verified claims
    total_weight = 0
    weighted_score_sum = 0

    verdict_counts = {"SUPPORTED": 0, "CONTRADICTED": 0, "PARTIALLY_SUPPORTED": 0, "INSUFFICIENT_EVIDENCE": 0}

    for c in claims_verified:
        v = c.verdict
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
        weight = c.importance or 3
        total_weight += weight

        if v == "SUPPORTED":
            weighted_score_sum += 100 * weight
        elif v == "PARTIALLY_SUPPORTED":
            weighted_score_sum += 60 * weight
        elif v == "INSUFFICIENT_EVIDENCE":
            weighted_score_sum += 50 * weight
        elif v == "CONTRADICTED":
            weighted_score_sum += 0 * weight

    factual_integrity_score = int(weighted_score_sum / total_weight) if total_weight > 0 else 50

    # Build synthesis context for LLM
    claims_summary = "\n".join([
        f"- Claim: \"{c.claim_text}\" | Verdict: {c.verdict} (Confidence: {int(c.confidence*100)}%) | Explanation: {c.explanation}"
        for c in claims_verified
    ])

    synthesis_payload = (
        f"INPUT TEXT:\n{text}\n\n"
        f"FACTUAL VERIFICATION RESULTS:\n{claims_summary}\n\n"
        f"PSYCHOLOGICAL & MANIPULATION SCORES:\n"
        f"- Manipulation Score: {manipulation.score}/100 ({', '.join(manipulation.types) if manipulation.types else 'none'})\n"
        f"- Propaganda Score: {propaganda.score}/100 ({propaganda.type})\n"
        f"- Misinformation Linguistic Risk: {misinformation.score}/100 ({misinformation.risk})"
    )

    try:
        raw = call_llm("intelligence_synthesis", synthesis_payload, temperature=0.1)
        return IntelligenceSynthesis(
            overall_verdict=raw.get("overall_verdict", "MIXED_ACCURACY"),
            factual_integrity_score=int(raw.get("factual_integrity_score", factual_integrity_score)),
            content_intent=raw.get("content_intent", "Informative"),
            executive_summary=raw.get("executive_summary", "Analysis completed across factual and psychological dimensions."),
            key_takeaways=raw.get("key_takeaways", [])
        )
    except Exception:
        # Robust rule-based fallback
        if verdict_counts["CONTRADICTED"] > 0:
            overall = "MOSTLY_FALSE" if verdict_counts["CONTRADICTED"] >= len(claims_verified) / 2 else "MIXED_ACCURACY"
        elif verdict_counts["SUPPORTED"] == len(claims_verified):
            overall = "CONFIRMED_TRUE"
        elif verdict_counts["SUPPORTED"] > 0:
            overall = "MOSTLY_TRUE"
        else:
            overall = "UNVERIFIED"

        return IntelligenceSynthesis(
            overall_verdict=overall,
            factual_integrity_score=factual_integrity_score,
            content_intent="Informative" if manipulation.score < 40 else "Misleading",
            executive_summary=f"Analysis of {len(claims_verified)} claims found {verdict_counts['SUPPORTED']} supported, {verdict_counts['CONTRADICTED']} contradicted, and {verdict_counts['INSUFFICIENT_EVIDENCE']} unverified.",
            key_takeaways=[
                f"{verdict_counts['SUPPORTED']} of {len(claims_verified)} claims verified as supported by external sources.",
                f"Manipulation score of {manipulation.score}/100 observed."
            ]
        )


async def execute_full_pipeline(
    text: str,
    verify_facts: bool = True,
    max_claims_to_verify: int = 4
) -> AnalyzeResponse:
    """
    Execute the unified content intelligence and fact-verification pipeline.
    Runs psychological modules, claim extraction, and web verification concurrently.
    """
    start_time = time.time()
    loop = asyncio.get_event_loop()

    # 1. Launch Content Intelligence tasks concurrently
    manip_fut = loop.run_in_executor(thread_pool, analyze_manipulation, text)
    prop_fut = loop.run_in_executor(thread_pool, analyze_propaganda, text)
    misinfo_fut = loop.run_in_executor(thread_pool, analyze_misinformation_risk, text)
    cat_fut = loop.run_in_executor(thread_pool, classify_category, text)

    # 2. Launch Claim Extraction
    claims_extract_fut = loop.run_in_executor(thread_pool, extract_claims, text)

    # Gather initial results
    manip, prop, misinfo, category, claims_resp = await asyncio.gather(
        manip_fut, prop_fut, misinfo_fut, cat_fut, claims_extract_fut
    )

    claims_verified: List[ClaimVerificationResult] = []

    # 3. If fact verification enabled, verify top extracted claims concurrently
    if verify_facts and claims_resp.claims:
        top_claims = claims_resp.claims[:max_claims_to_verify]

        # Launch each claim verification in thread pool
        verify_futs = [
            loop.run_in_executor(
                thread_pool,
                verify_single_claim,
                c.text,
                c.id,
                c.category,
                c.importance
            )
            for c in top_claims
        ]

        claims_verified = await asyncio.gather(*verify_futs)

    # 4. Synthesize final intelligence report
    synthesis = await loop.run_in_executor(
        thread_pool,
        _synthesize_intelligence,
        text,
        claims_verified,
        manip,
        prop,
        misinfo
    )

    avg_score = (manip.score + prop.score + misinfo.score) // 3
    final_risk = calculate_risk_level(avg_score)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    return AnalyzeResponse(
        input_text=text,
        category=category,
        final_risk=final_risk,
        avg_score=avg_score,
        manipulation=manip,
        propaganda=prop,
        misinformation=misinfo,
        claims_verified=claims_verified,
        synthesis=synthesis,
        processing_time_ms=duration_ms
    )
