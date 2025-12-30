"""
Search utilities for the Local Assistant.
Uses DuckDuckGo (via ddgs library) for fast, free internet searches.
"""

import logging
from typing import Optional

logger = logging.getLogger("search_utils")

try:
    from ddgs import DDGS
except ImportError:
    logger.error("ddgs package not installed. Run: pip install duckduckgo-search")
    DDGS = None


def perform_search(
    query: str, 
    max_results: int = 5, 
    timelimit: Optional[str] = None, 
    region: str = "wt-wt"
) -> str:
    """
    Performs a web search using DuckDuckGo (ddgs) library.
    
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
            href = result.get("href", "")
            
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


def needs_search(text: str) -> tuple:
    """
    Checks if the generated text contains a search request pattern.
    Pattern: [SEARCH: query]
    
    Returns:
        Tuple of (bool, str|None) - (needs_search, query)
    """
    import re
    pattern = r'\[SEARCH:\s*(.+?)\]'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        return True, match.group(1).strip()
    return False, None


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    print(perform_search("current prime minister of Russia"))
    print("-" * 20)
    print(perform_search("weather in Tokyo"))

