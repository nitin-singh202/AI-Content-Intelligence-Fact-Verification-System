from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.analyze import router as analyze_router
from routes.claims import router as claims_router
from routes.search import router as search_router
from routes.verify import router as verify_router
from routes.report import router as report_router

app = FastAPI(
    title="AI Content Intelligence & Fact Verification System",
    description="LLM-Powered Retrieval-Augmented Fact Verification and Content Intelligence API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(claims_router)
app.include_router(search_router)
app.include_router(verify_router)
app.include_router(report_router)


@app.get("/")
def root():
    return {
        "system": "AI Content Intelligence & Fact Verification System",
        "status": "online",
        "version": "2.0.0",
        "docs_url": "/docs",
        "endpoints": [
            "POST /analyze (Full Intelligence & Verification Pipeline)",
            "POST /extract-claims (Claim Extraction)",
            "POST /search (Web Evidence Retrieval)",
            "POST /verify (Single Claim Grounded Verification)",
            "POST /report (Comprehensive Executive Report)",
            "GET /health (System Health & Features)",
            "GET /models (Model Configuration)"
        ]
    }
