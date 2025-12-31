"""
Web search tools - implements internet search functionality.
"""

import logging
from typing import Optional
from .tool_registry import register_tool

logger = logging.getLogger("tools.web")

# Try to import DuckDuckGo search library
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.error("ddgs package not installed. Run: pip install ddgs")
        DDGS = None


def perform_search(
    query: str, 
    max_results: int = 5, 
    timelimit: Optional[str] = None, 
    region: str = "wt-wt"
) -> str:
    """
    Performs a web search using DuckDuckGo (DDGS).
    
    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default: 5).
        timelimit: Time limit (d=day, w=week, m=month, y=year).
        region: Region code (e.g., "wt-wt", "us-en").
        
    Returns:
        A formatted string containing the search results.
    """
    if not DDGS:
        return "Search unavailable: duckduckgo-search package not installed."
    
    if not query or not query.strip():
        return "No search query provided."
    
    query = query.strip()
    logger.info(f"Searching: '{query}' (timelimit={timelimit}, region={region})")
    
    results = []
    
    try:
        # Primary search with provided parameters
        with DDGS() as ddgs:
            gen = ddgs.text(query, max_results=max_results, timelimit=timelimit, region=region)
            results = list(gen) if gen else []
        
        # Fallback 1: If no results with timelimit, try without
        if not results and timelimit:
            logger.debug("No results with timelimit, retrying without...")
            with DDGS() as ddgs:
                gen = ddgs.text(query, max_results=max_results, region=region)
                results = list(gen) if gen else []

        # Fallback 2: If no results in current region, try us-en
        if not results and region != "us-en":
            logger.debug("No results in region, retrying with 'us-en'...")
            with DDGS() as ddgs:
                gen = ddgs.text(query, max_results=max_results, region="us-en")
                results = list(gen) if gen else []

        if not results:
            return f"No search results found for: {query}"
        
        # Format results for TTS-friendly output
        formatted_results = [f"Search results for: {query}\n"]
        
        for i, result in enumerate(results):
            title = result.get("title", "").strip()
            body = result.get("body", "").strip()
            # href = result.get("href", "") # Link not needed for voice output usually
            
            if not title or not body:
                continue
            
            # Truncate body if too long for TTS
            if len(body) > 200:
                body = body[:197] + "..."
                
            formatted_results.append(f"{i + 1}. {title}\n   {body}\n")
            
        return "\n".join(formatted_results)

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Search failed: {str(e)}"


def web_search(query: str, timelimit: str = None) -> str:
    """Perform a web search."""
    if not query or not query.strip():
        return "Please provide a search query."
    
    # Validate timelimit if provided
    valid_timelimits = {'d', 'w', 'm', 'y', None}
    if timelimit and timelimit not in valid_timelimits:
        logger.debug(f"Invalid timelimit '{timelimit}', ignoring")
        timelimit = None
    
    return perform_search(query, timelimit=timelimit)


# ============================================================
# Register web search tool
# ============================================================

register_tool(
    name="web_search",
    description="Search the internet for current information like weather, news, sports scores, or stocks.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "timelimit": {
                "type": "string",
                "enum": ["d", "w", "m", "y"],
                "description": "Time limit: 'd' (day), 'w' (week), 'm' (month), 'y' (year). Use 'd' or 'w' for recent news."
            }
        },
        "required": ["query"]
    },
    func=web_search
)
