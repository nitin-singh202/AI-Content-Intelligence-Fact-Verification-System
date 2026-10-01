import urllib.parse
import re
from typing import List, Dict, Any, Tuple
import requests
from models.schema import SourceEvidence, SearchResponse
from services.llm_service import call_llm

try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None

# Known domain credibility mapping
HIGH_TRUST_DOMAINS = {
    # Government & International bodies
    ".gov": ("Tier 1: Official / Government", 0.98, True),
    ".gov.in": ("Tier 1: Official / Government", 0.98, True),
    ".edu": ("Tier 1: Academic / Educational", 0.95, True),
    ".mil": ("Tier 1: Official / Military", 0.95, True),
    "who.int": ("Tier 1: Primary International Org", 0.98, True),
    "un.org": ("Tier 1: Primary International Org", 0.98, True),
    "nasa.gov": ("Tier 1: Primary Space Agency", 0.99, True),
    "cdc.gov": ("Tier 1: Official Health Agency", 0.98, True),
    "nih.gov": ("Tier 1: Official Medical Research", 0.98, True),
    "isro.gov.in": ("Tier 1: Official Space Agency", 0.98, True),
    "pib.gov.in": ("Tier 1: Official Govt Press Bureau", 0.98, True),
    "europa.eu": ("Tier 1: Official EU Institution", 0.97, True),

    # Fact-checking & Primary Journalism
    "reuters.com": ("Tier 2: Major Wire / News", 0.92, False),
    "apnews.com": ("Tier 2: Major Wire / News", 0.92, False),
    "bbc.com": ("Tier 2: Major Journalism", 0.90, False),
    "bbc.co.uk": ("Tier 2: Major Journalism", 0.90, False),
    "bloomberg.com": ("Tier 2: Major Financial Journalism", 0.90, False),
    "nature.com": ("Tier 2: Scientific Journal", 0.95, True),
    "science.org": ("Tier 2: Scientific Journal", 0.95, True),
    "snopes.com": ("Tier 2: Dedicated Fact-Checker", 0.90, False),
    "politifact.com": ("Tier 2: Dedicated Fact-Checker", 0.90, False),
    "factcheck.org": ("Tier 2: Dedicated Fact-Checker", 0.90, False),
    "thehindu.com": ("Tier 2: Reputable News", 0.88, False),
    "indianexpress.com": ("Tier 2: Reputable News", 0.88, False),
    "nytimes.com": ("Tier 2: Major News", 0.88, False),
    "wsj.com": ("Tier 2: Major News", 0.88, False),

    # Reference & Knowledge Bases
    "wikipedia.org": ("Tier 3: Encyclopedic Reference", 0.80, False),
    "britannica.com": ("Tier 3: Encyclopedic Reference", 0.85, False),
    "investopedia.com": ("Tier 3: Domain Reference", 0.82, False),
}


def evaluate_domain_credibility(url: str) -> Tuple[str, float, bool, str]:
    """
    Evaluate domain authority, trust score (0-1), and whether it is a primary source.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
    except Exception:
        return ("Tier 4: Unverified / Web", 0.50, False, "unknown")

    # Check exact domain and suffix matches
    for key, (tier, score, is_primary) in HIGH_TRUST_DOMAINS.items():
        if key.startswith("."):
            if domain.endswith(key):
                return (tier, score, is_primary, domain)
        elif domain == key or domain.endswith("." + key):
            return (tier, score, is_primary, domain)

    # General heuristic
    if domain.endswith(".org"):
        return ("Tier 3: Organization / Non-Profit", 0.72, False, domain)
    if any(news_word in domain for news_word in ["times", "post", "tribune", "daily", "guardian", "herald", "telegraph", "news"]):
        return ("Tier 2: General News Outlet", 0.78, False, domain)

    return ("Tier 4: General Web / Blog", 0.55, False, domain)


def generate_search_queries(claim_text: str) -> List[str]:
    """
    Generate optimized search queries for a claim using LLM or fallback heuristics.
    """
    try:
        res = call_llm("query_generation", claim_text, temperature=0.1)
        queries = res.get("queries", [])
        if queries and isinstance(queries, list):
            valid_q = [str(q).strip() for q in queries if len(str(q).strip()) > 3]
            if valid_q:
                return valid_q[:3]
    except Exception:
        pass

    # Heuristic fallback query generation
    clean = re.sub(r"[^\w\s]", "", claim_text)
    words = clean.split()
    primary_q = " ".join(words[:8])
    fact_check_q = f"{' '.join(words[:6])} fact check"
    return [primary_q, fact_check_q]


def search_duckduckgo(query: str, max_results: int = 5) -> List[SourceEvidence]:
    """
    Search DuckDuckGo for live web evidence.
    """
    sources: List[SourceEvidence] = []
    if not DDGS:
        return sources

    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))
        for item in results:
            url = item.get("href") or item.get("link") or ""
            title = item.get("title") or "Source Result"
            snippet = item.get("body") or item.get("snippet") or ""

            if not url or not snippet:
                continue

            tier, trust_score, is_primary, domain = evaluate_domain_credibility(url)

            sources.append(
                SourceEvidence(
                    title=title,
                    url=url,
                    domain=domain,
                    snippet=snippet,
                    reliability_tier=tier,
                    domain_trust_score=trust_score,
                    is_primary_source=is_primary,
                    relevance_score=0.85
                )
            )
    except Exception as e:
        # Silently catch rate-limit or network issues
        pass

    return sources


def search_wikipedia_fallback(query: str, max_results: int = 2) -> List[SourceEvidence]:
    """
    Wikipedia API search fallback for encyclopedic context.
    """
    sources: List[SourceEvidence] = []
    try:
        endpoint = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": max_results
        }
        headers = {"User-Agent": "AIContentIntelligenceBot/2.0"}
        resp = requests.get(endpoint, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            search_items = data.get("query", {}).get("search", [])
            for item in search_items:
                title = item.get("title", "")
                snippet_raw = item.get("snippet", "")
                clean_snippet = re.sub(r"<.*?>", "", snippet_raw)
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

                sources.append(
                    SourceEvidence(
                        title=f"Wikipedia: {title}",
                        url=page_url,
                        domain="wikipedia.org",
                        snippet=clean_snippet,
                        reliability_tier="Tier 3: Encyclopedic Reference",
                        domain_trust_score=0.80,
                        is_primary_source=False,
                        relevance_score=0.78
                    )
                )
    except Exception:
        pass

    return sources


def retrieve_evidence_for_claim(claim_text: str, max_sources: int = 6) -> List[SourceEvidence]:
    """
    Retrieve external evidence for a claim by generating queries and searching multiple channels.
    Deduplicates URLs and ranks by domain authority & relevance.
    """
    queries = generate_search_queries(claim_text)
    seen_urls = set()
    all_sources: List[SourceEvidence] = []

    for q in queries:
        ddg_results = search_duckduckgo(q, max_results=4)
        for s in ddg_results:
            if s.url not in seen_urls:
                seen_urls.add(s.url)
                all_sources.append(s)

        if len(all_sources) >= max_sources:
            break

    # If web search returned fewer than 2 results, supplement with Wikipedia
    if len(all_sources) < 2:
        wiki_results = search_wikipedia_fallback(claim_text, max_results=2)
        for s in wiki_results:
            if s.url not in seen_urls:
                seen_urls.add(s.url)
                all_sources.append(s)

    # Sort sources: prioritize Primary/High-Trust domain scores
    all_sources.sort(key=lambda s: (s.is_primary_source, s.domain_trust_score), reverse=True)

    return all_sources[:max_sources]
