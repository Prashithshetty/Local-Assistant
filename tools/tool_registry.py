"""
Tool Registry - Central hub for all assistant tools.
Manages tool definitions (for LLM) and execution routing.
"""

import logging
import time
from typing import Any, Callable, Dict, List

# Configure logging for tools
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tools")

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
    logger.debug(f"Registered tool: {name}")


def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Execute a tool by name with given arguments."""
    if tool_name not in _TOOL_FUNCTIONS:
        logger.warning(f"Unknown tool requested: {tool_name}")
        return f"Unknown tool: {tool_name}"
    
    start_time = time.perf_counter()
    try:
        result = _TOOL_FUNCTIONS[tool_name](**tool_args)
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"Tool '{tool_name}' completed in {elapsed:.0f}ms")
        return result
    except TypeError as e:
        # Handle missing/wrong arguments gracefully
        logger.error(f"Tool '{tool_name}' argument error: {e}")
        return f"Tool '{tool_name}' received invalid arguments: {e}"
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.error(f"Tool '{tool_name}' failed after {elapsed:.0f}ms: {e}")
        return f"Tool '{tool_name}' failed: {str(e)}"


def get_all_tools() -> List[Dict]:
    """Get all registered tool schemas for LLM."""
    return _TOOL_SCHEMAS.copy()


def get_tool_names() -> List[str]:
    """Get list of all registered tool names."""
    return list(_TOOL_FUNCTIONS.keys())


# Alias for backwards compatibility (fixed from broken property syntax)
TOOL_DEFINITIONS = get_all_tools


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

