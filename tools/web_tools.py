"""
Web search tools - wraps existing search_utils.
"""

import logging
import sys
import os

logger = logging.getLogger("tools.web")

# Import from parent directory's search_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .tool_registry import register_tool

try:
    from search_utils import perform_search as _perform_search
except ImportError as e:
    logger.warning(f"Could not import search_utils: {e}")
    def _perform_search(query, **kwargs):
        return "Search module not available. Check search_utils.py installation."


def web_search(query: str, timelimit: str = None) -> str:
    """Perform a web search."""
    if not query or not query.strip():
        return "Please provide a search query."
    
    query = query.strip()
    
    # Validate timelimit if provided
    valid_timelimits = {'d', 'w', 'm', 'y', None}
    if timelimit and timelimit not in valid_timelimits:
        logger.debug(f"Invalid timelimit '{timelimit}', ignoring")
        timelimit = None
    
    try:
        result = _perform_search(query, timelimit=timelimit)
        return result
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Search failed: {e}"


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

