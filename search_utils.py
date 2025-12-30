"""
Search utilities for the Local Assistant.
Uses DuckDuckGo (via ddgs library) for fast, free internet searches.
"""

from ddgs import DDGS

def perform_search(query: str, max_results: int = 3, timelimit: str = None, region: str = "wt-wt") -> str:
    """
    Performs a web search using DuckDuckGo (ddgs) library.
    
    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        timelimit: Time limit (d, w, m, y).
        region: Region code (e.g., "wt-wt", "us-en").
        
    Returns:
        A formatted string containing the search results.
    """
    print(f"Searching: {query} (Time: {timelimit}, Region: {region})...")
    results = []
    
    try:
        # Use DDGS context manager
        with DDGS() as ddgs:
            # Try text search
            gen = ddgs.text(query, max_results=max_results, timelimit=timelimit, region=region)
            results = list(gen) if gen else []
            
        # Fallback Strategy: If no results, try broader searches
        if not results and timelimit:
             print("No results with timelimit, retrying without...")
             with DDGS() as ddgs:
                 gen = ddgs.text(query, max_results=max_results, region=region)
                 results = list(gen) if gen else []

        if not results and region != "us-en":
             print("No results in region, retrying with 'us-en'...")
             with DDGS() as ddgs:
                 gen = ddgs.text(query, max_results=max_results, region="us-en")
                 results = list(gen) if gen else []

        if not results:
            return f"No search results found for: {query}"
        
        formatted_results = [f"Search results for: {query}\n"]
        
        for i, result in enumerate(results):
            title = result.get("title", "").strip()
            body = result.get("body", "").strip()
            href = result.get("href", "")
            
            if not title or not body:
                continue
                
            formatted_results.append(f"{i + 1}. {title}\n   {body}\n   Source: {href}\n")
            
        return "\n".join(formatted_results)

    except Exception as e:
        return f"Search failed: {str(e)}"


def needs_search(text: str) -> tuple[bool, str | None]:
    """
    Checks if the generated text contains a search request pattern.
    Pattern: [SEARCH: query]
    """
    import re
    pattern = r'\[SEARCH:\s*(.+?)\]'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        return True, match.group(1).strip()
    return False, None


if __name__ == "__main__":
    # Quick test
    print(perform_search("current prime minister of Russia"))
    print("-" * 20)
    print(perform_search("weather in Tokyo"))
