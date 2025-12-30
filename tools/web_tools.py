"""
Web search tools - wraps existing search_utils.
"""

import sys
import os

# Import from parent directory's search_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .tool_registry import register_tool

try:
    from search_utils import perform_search as _perform_search
except ImportError:
    def _perform_search(query, **kwargs):
        return "Search module not available."


def web_search(query: str, timelimit: str = None) -> str:
    """Perform a web search."""
    return _perform_search(query, timelimit=timelimit)


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
