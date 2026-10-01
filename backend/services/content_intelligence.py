from concurrent.futures import ThreadPoolExecutor
from models.schema import ManipulationResult, PropagandaResult, MisinformationResult
from services.llm_service import call_llm

executor = ThreadPoolExecutor(max_workers=4)


def analyze_manipulation(text: str) -> ManipulationResult:
    raw = call_llm("manipulation", text)
    return ManipulationResult(
        score=int(raw.get("score", 0)),
        types=raw.get("types", []),
        explanation=raw.get("explanation", ""),
        highlights=raw.get("highlights", [])
    )


def analyze_propaganda(text: str) -> PropagandaResult:
    raw = call_llm("propaganda", text)
    return PropagandaResult(
        score=int(raw.get("score", 0)),
        type=raw.get("type", "None"),
        explanation=raw.get("explanation", "")
    )


def analyze_misinformation_risk(text: str) -> MisinformationResult:
    raw = call_llm("misinformation", text)
    return MisinformationResult(
        score=int(raw.get("score", 0)),
        risk=raw.get("risk", "low"),
        explanation=raw.get("explanation", "")
    )


def classify_category(text: str) -> str:
    raw = call_llm("category", text)
    return raw.get("category", "General")


def calculate_risk_level(avg_score: int) -> str:
    if avg_score >= 70:
        return "HIGH"
    elif avg_score >= 40:
        return "MEDIUM"
    return "LOW"
