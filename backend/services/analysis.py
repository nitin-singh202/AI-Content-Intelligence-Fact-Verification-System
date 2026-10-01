from services.pipeline import execute_full_pipeline, calculate_risk_level
from models.schema import AnalyzeResponse


async def run_analysis(text: str, verify_facts: bool = True) -> AnalyzeResponse:
    """
    Main entry point for analyzing text, extracting claims, retrieving evidence,
    and verifying factual accuracy alongside psychological manipulation analysis.
    """
    return await execute_full_pipeline(text=text, verify_facts=verify_facts)
