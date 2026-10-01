from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ClaimItem(BaseModel):
    id: str
    text: str
    category: str = "General Fact"
    importance: int = Field(default=3, ge=1, le=5)
    verifiable: bool = True


class ExtractClaimsRequest(BaseModel):
    text: str


class ExtractClaimsResponse(BaseModel):
    claims: List[ClaimItem] = []
    claim_count: int = 0
    summary: Optional[str] = ""


class SourceEvidence(BaseModel):
    title: str
    url: str
    domain: str
    snippet: str
    reliability_tier: str = "General / Unverified"  # "Tier 1: Official/Gov/Org", "Tier 2: Major News/Journalism", "Tier 3: Academic/Scientific", "Tier 4: General/Blog"
    domain_trust_score: float = 0.5  # 0.0 - 1.0
    is_primary_source: bool = False
    relevance_score: Optional[float] = 0.8


class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5


class SearchResponse(BaseModel):
    query: str
    sources: List[SourceEvidence] = []
    total_found: int = 0


class ClaimVerificationResult(BaseModel):
    claim_id: str
    claim_text: str
    category: Optional[str] = "General Fact"
    importance: Optional[int] = 3
    verdict: str = "INSUFFICIENT_EVIDENCE"  # SUPPORTED, CONTRADICTED, PARTIALLY_SUPPORTED, INSUFFICIENT_EVIDENCE
    confidence: float = 0.0  # 0.0 to 1.0
    explanation: str
    supporting_evidence: List[str] = []
    refuting_evidence: List[str] = []
    disagreement_detected: bool = False
    disagreement_details: Optional[str] = None
    sources: List[SourceEvidence] = []
    primary_source_cited: Optional[str] = None


class VerifyClaimRequest(BaseModel):
    claim: str
    claim_id: Optional[str] = "claim_1"
    category: Optional[str] = "General Fact"
    importance: Optional[int] = 3
    custom_sources: Optional[List[SourceEvidence]] = None


class VerifyClaimResponse(BaseModel):
    result: ClaimVerificationResult


class ManipulationResult(BaseModel):
    score: int
    types: List[str] = []
    explanation: str
    highlights: List[str] = []


class PropagandaResult(BaseModel):
    score: int
    type: str
    explanation: str


class MisinformationResult(BaseModel):
    score: int
    risk: str
    explanation: str


class IntelligenceSynthesis(BaseModel):
    overall_verdict: str
    factual_integrity_score: int
    content_intent: str
    executive_summary: str
    key_takeaways: List[str] = []


class AnalyzeRequest(BaseModel):
    text: str
    verify_facts: Optional[bool] = True
    max_claims_to_verify: Optional[int] = 4


class AnalyzeResponse(BaseModel):
    input_text: str
    category: str
    final_risk: str
    avg_score: int
    manipulation: ManipulationResult
    propaganda: PropagandaResult
    misinformation: MisinformationResult
    claims_verified: List[ClaimVerificationResult] = []
    synthesis: Optional[IntelligenceSynthesis] = None
    processing_time_ms: Optional[float] = 0.0


class ReportRequest(BaseModel):
    text: str
    include_full_sources: Optional[bool] = True


class HealthCheckResponse(BaseModel):
    status: str
    model: str
    search_provider: str
    features: List[str]
