"""
Tool Registry - Central hub for all assistant tools.
Manages tool definitions (for LLM) and execution routing.
"""

from typing import Any, Callable, Dict, List

# Tool implementations will be registered here
_TOOL_FUNCTIONS: Dict[str, Callable] = {}
_TOOL_SCHEMAS: List[Dict] = []


def register_tool(name: str, description: str, parameters: Dict, func: Callable):
    """Register a tool with its schema and implementation."""
    _TOOL_FUNCTIONS[name] = func
    _TOOL_SCHEMAS.append({
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters
        }
    })


def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Execute a tool by name with given arguments."""
    if tool_name not in _TOOL_FUNCTIONS:
        return f"Unknown tool: {tool_name}"
    
    try:
        return _TOOL_FUNCTIONS[tool_name](**tool_args)
    except Exception as e:
        return f"Tool '{tool_name}' failed: {str(e)}"


def get_all_tools() -> List[Dict]:
    """Get all registered tool schemas for LLM."""
    return _TOOL_SCHEMAS.copy()


# Alias for backwards compatibility
TOOL_DEFINITIONS = property(lambda self: get_all_tools())


# ============================================================
# Auto-import all tool modules to trigger registration
# ============================================================

def _load_all_tools():
    """Import all tool modules to register their tools."""
    from . import system_tools
    from . import file_tools
    from . import network_tools
    from . import app_tools
    from . import web_tools


# Load tools when module is imported
_load_all_tools()
