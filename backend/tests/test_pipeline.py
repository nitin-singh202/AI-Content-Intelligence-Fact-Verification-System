import pytest
from fastapi.testclient import TestClient
from main import app
from services.search_service import evaluate_domain_credibility, HIGH_TRUST_DOMAINS
from services.evidence_service import format_evidence_for_prompt, calculate_evidence_strength
from services.verification_service import calibrate_confidence
from models.schema import SourceEvidence

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "endpoints" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Claim Extraction" in data["features"]


def test_models_endpoint():
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "primary_model" in data


def test_domain_credibility_scoring():
    tier, trust, is_primary, domain = evaluate_domain_credibility("https://www.nasa.gov/mission/artemis")
    assert "Tier 1" in tier
    assert trust >= 0.95
    assert is_primary is True
    assert domain == "nasa.gov"

    tier, trust, is_primary, domain = evaluate_domain_credibility("https://www.reuters.com/world/us/article-123")
    assert "Tier 2" in tier
    assert trust >= 0.85
    assert domain == "reuters.com"

    tier, trust, is_primary, domain = evaluate_domain_credibility("https://random-unverified-blog.xyz/post")
    assert "Tier 4" in tier
    assert trust <= 0.60


def test_evidence_strength_calculation():
    sources = [
        SourceEvidence(
            title="NASA Artemis Update",
            url="https://www.nasa.gov/artemis",
            domain="nasa.gov",
            snippet="NASA is targeting 2026 for crewed lunar landing.",
            reliability_tier="Tier 1: Official / Government",
            domain_trust_score=0.98,
            is_primary_source=True
        ),
        SourceEvidence(
            title="Reuters Space Report",
            url="https://www.reuters.com/space",
            domain="reuters.com",
            snippet="NASA Artemis mission details.",
            reliability_tier="Tier 2: Major News",
            domain_trust_score=0.90,
            is_primary_source=False
        )
    ]

    stats = calculate_evidence_strength(sources)
    assert stats["source_count"] == 2
    assert stats["avg_trust_score"] == 0.94
    assert stats["has_primary_source"] is True


def test_confidence_calibration():
    sources = [
        SourceEvidence(
            title="NASA Artemis",
            url="https://www.nasa.gov/artemis",
            domain="nasa.gov",
            snippet="Official announcement",
            reliability_tier="Tier 1: Official",
            domain_trust_score=0.98,
            is_primary_source=True
        ),
        SourceEvidence(
            title="BBC News",
            url="https://www.bbc.com/news/123",
            domain="bbc.com",
            snippet="BBC report",
            reliability_tier="Tier 2: News",
            domain_trust_score=0.90,
            is_primary_source=False
        )
    ]

    # Supported with high-trust sources should calibrate to a high confidence score
    calibrated = calibrate_confidence(0.85, "SUPPORTED", sources, disagreement_detected=False)
    assert 0.75 <= calibrated <= 0.99

    # Insufficient evidence should be bounded
    calibrated_insufficient = calibrate_confidence(0.80, "INSUFFICIENT_EVIDENCE", [], disagreement_detected=False)
    assert calibrated_insufficient <= 0.45


def test_evidence_formatting_for_prompt():
    sources = [
        SourceEvidence(
            title="WHO Official Notice",
            url="https://www.who.int/news/item",
            domain="who.int",
            snippet="No new pandemic declared in 2026.",
            reliability_tier="Tier 1: Primary International Org",
            domain_trust_score=0.98,
            is_primary_source=True
        )
    ]
    formatted = format_evidence_for_prompt("WHO declared a pandemic.", sources)
    assert "CLAIM TO VERIFY:" in formatted
    assert "who.int" in formatted
    assert "WHO Official Notice" in formatted


def test_validation_errors():
    resp = client.post("/extract-claims", json={"text": ""})
    assert resp.status_code == 400

    resp2 = client.post("/search", json={"query": "a"})
    assert resp2.status_code == 400

    resp3 = client.post("/verify", json={"claim": "no"})
    assert resp3.status_code == 400
