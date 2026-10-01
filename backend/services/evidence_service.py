from typing import List, Dict, Any
from models.schema import SourceEvidence


def format_evidence_for_prompt(claim_text: str, sources: List[SourceEvidence]) -> str:
    """
    Format retrieved sources into a clean, numbered context block for LLM verification.
    """
    if not sources:
        return f"CLAIM: {claim_text}\n\nRETRIEVED EVIDENCE:\nNo external sources could be retrieved."

    evidence_lines = [f"CLAIM TO VERIFY:\n\"{claim_text}\"\n", "RETRIEVED EXTERNAL EVIDENCE:"]

    for idx, s in enumerate(sources, start=1):
        tier_label = f"[{s.reliability_tier} | Trust: {int(s.domain_trust_score * 100)}%]"
        evidence_lines.append(
            f"Source [{idx}] {tier_label}:\n"
            f"  Title: {s.title}\n"
            f"  Domain: {s.domain} ({s.url})\n"
            f"  Snippet: \"{s.snippet}\"\n"
        )

    return "\n".join(evidence_lines)


def calculate_evidence_strength(sources: List[SourceEvidence]) -> Dict[str, Any]:
    """
    Calculate aggregate source credibility and diversity statistics.
    """
    if not sources:
        return {
            "source_count": 0,
            "avg_trust_score": 0.0,
            "has_primary_source": False,
            "tier_distribution": {}
        }

    total_trust = sum(s.domain_trust_score for s in sources)
    avg_trust = total_trust / len(sources)
    has_primary = any(s.is_primary_source for s in sources)

    tier_dist: Dict[str, int] = {}
    for s in sources:
        tier_dist[s.reliability_tier] = tier_dist.get(s.reliability_tier, 0) + 1

    return {
        "source_count": len(sources),
        "avg_trust_score": round(avg_trust, 2),
        "has_primary_source": has_primary,
        "tier_distribution": tier_dist
    }
