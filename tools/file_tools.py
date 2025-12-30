"""
File system tools - find, list, read files.
"""

import os
import glob
import logging
import stat
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from .tool_registry import register_tool

logger = logging.getLogger("tools.file")

# Safety limits
MAX_FILE_SIZE = 50 * 1024  # 50KB max for reading files
MAX_RESULTS = 20  # Max search results

# Get home directory safely
def _get_home_dir() -> str:
    return os.environ.get('HOME', os.path.expanduser("~"))

HOME_DIR = _get_home_dir()

# Directories to exclude from searches
EXCLUDED_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 
                 '.cache', '.local/share/Trash', '.npm', '.cargo'}


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 0:
        return "0B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def _is_excluded_path(path: str) -> bool:
    """Check if path contains any excluded directories."""
    path_parts = path.split(os.sep)
    return any(excluded in path_parts for excluded in EXCLUDED_DIRS)


def _expand_path(path: str) -> str:
    """Safely expand user paths and handle common LLM hallucinations."""
    if not path:
        return HOME_DIR
    
    # Replace common LLM hallucinations
    path = path.replace('/home/yourname/', '~/')
    path = path.replace('/home/username/', '~/')
    path = path.replace('/home/user/', '~/')
    
    # Expand ~ to actual home directory
    path = os.path.expanduser(path)
    
    return path


def find_files(pattern: str, directory: str = None, file_type: str = None) -> str:
    """Find files matching a pattern. Returns TTS-friendly output."""
    # Default to home directory. Also treat '.' as home (LLM often passes '.')
    search_dir = _expand_path(directory) if directory and directory != '.' else HOME_DIR
    
    if not os.path.isdir(search_dir):
        return f"Directory not found: {search_dir}"
    
    results: List[str] = []
    
    # Build search pattern - handle both exact and wildcard patterns
    if pattern.startswith("*") or pattern.startswith("**"):
        search_pattern = f"**/{pattern}"
    else:
        search_pattern = f"**/*{pattern}*"
    
    try:
        for path in Path(search_dir).glob(search_pattern):
            # Skip excluded directories efficiently
            if _is_excluded_path(str(path)):
                continue
            
            # Filter by type if specified
            if file_type:
                if file_type == "file" and not path.is_file():
                    continue
                if file_type == "directory" and not path.is_dir():
                    continue
            
            results.append(str(path))
            if len(results) >= MAX_RESULTS:
                break
                
    except PermissionError:
        logger.debug(f"Permission denied searching in {search_dir}")
    except Exception as e:
        logger.error(f"find_files error: {e}")
        return f"Search error: {e}"
    
    if not results:
        return f"No files found matching '{pattern}'."
    
    # Build simple, TTS-friendly output
    result = f"Found {len(results)} files:\n"
    
    for i, path in enumerate(results, 1):
        filename = os.path.basename(path)
        parent_dir = os.path.dirname(path)
        folder = os.path.basename(parent_dir) if parent_dir else ""
        # Simple format: "1. filename in folder"
        result += f"{i}. {filename} in {folder}\n"
    
    if len(results) >= MAX_RESULTS:
        result += f"Showing first {MAX_RESULTS} results.\n"
    
    result += "Say 'open the first one' or use find_and_open_file tool."
    return result.strip()


def list_directory(path: str = None, show_hidden: bool = False) -> str:
    """List contents of a directory."""
    target_dir = _expand_path(path) if path else HOME_DIR
    
    if not os.path.exists(target_dir):
        return f"Path not found: {target_dir}"
    
    if not os.path.isdir(target_dir):
        return f"Not a directory: {target_dir}. Use read_file for files."
    
    try:
        items = os.listdir(target_dir)
    except PermissionError:
        return f"Permission denied: {target_dir}"
    except Exception as e:
        logger.error(f"list_directory error for {target_dir}: {e}")
        return f"Could not list directory: {e}"
    
    # Filter hidden files if not requested
    if not show_hidden:
        items = [item for item in items if not item.startswith('.')]
    
    items.sort(key=str.lower)
    
    # Categorize into files and directories
    dirs: List[str] = []
    files: List[str] = []
    
    for item in items:
        full_path = os.path.join(target_dir, item)
        try:
            if os.path.isdir(full_path):
                dirs.append(f"📁 {item}/")
            else:
                # Get file size
                size = os.path.getsize(full_path)
                size_str = _format_size(size)
                files.append(f"📄 {item} ({size_str})")
        except (OSError, PermissionError):
            files.append(f"📄 {item}")
    
    display_path = target_dir.replace(HOME_DIR, "~") if target_dir.startswith(HOME_DIR) else target_dir
    result = f"Contents of {display_path}:\n"
    
    # Show directories first, then files
    shown_items = 0
    max_per_type = MAX_RESULTS // 2
    
    for item in dirs[:max_per_type]:
        result += f"  {item}\n"
        shown_items += 1
    for item in files[:max_per_type]:
        result += f"  {item}\n"
        shown_items += 1
    
    total = len(dirs) + len(files)
    if total > MAX_RESULTS:
        result += f"  ... and {total - shown_items} more items"
    
    return result.strip()


def read_file(path: str, max_lines: int = 50) -> str:
    """Read contents of a text file (limited for safety)."""
    target_path = _expand_path(path)
    
    if not os.path.exists(target_path):
        return f"File not found: {path}"
    
    if os.path.isdir(target_path):
        return f"Path is a directory, not a file: {path}. Use list_directory instead."
    
    # Validate max_lines
    max_lines = max(1, min(max_lines or 50, 200))
    
    # Security: check file size
    try:
        size = os.path.getsize(target_path)
        if size > MAX_FILE_SIZE:
            return f"File too large ({_format_size(size)}). Max allowed: {_format_size(MAX_FILE_SIZE)}"
    except OSError as e:
        return f"Cannot access file: {e}"
    
    # Try to read as text
    try:
        with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        display_path = path.replace(HOME_DIR, "~") if path.startswith(HOME_DIR) else path
        
        if len(lines) > max_lines:
            content = ''.join(lines[:max_lines])
            return f"File: {display_path} (showing first {max_lines} of {len(lines)} lines)\n\n{content}"
        else:
            return f"File: {display_path}\n\n{''.join(lines)}"
            
    except UnicodeDecodeError:
        return f"Cannot read file: {path} appears to be binary, not text."
    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        logger.error(f"read_file error for {path}: {e}")
        return f"Could not read file: {e}"


def get_file_info(path: str) -> str:
    """Get detailed information about a file."""
    target_path = _expand_path(path)
    
    if not os.path.exists(target_path):
        return f"Path not found: {path}"
    
    try:
        stat_info = os.stat(target_path)
        
        file_type = 'Directory' if os.path.isdir(target_path) else 'File'
        display_path = path.replace(HOME_DIR, "~") if path.startswith(HOME_DIR) else path
        
        result = f"File Info: {display_path}\n"
        result += f"Type: {file_type}\n"
        result += f"Size: {_format_size(stat_info.st_size)}\n"
        result += f"Modified: {datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"Created: {datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"Permissions: {stat.filemode(stat_info.st_mode)}"
        
        return result
        
    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        logger.error(f"get_file_info error for {path}: {e}")
        return f"Could not get file info: {e}"


def get_recent_files(directory: str = None, hours: int = 24, limit: int = 10) -> str:
    """Get recently modified files in a directory."""
    search_dir = _expand_path(directory) if directory else HOME_DIR
    
    if not os.path.isdir(search_dir):
        return f"Directory not found: {search_dir}"
    
    # Validate inputs
    hours = max(1, min(hours or 24, 168))  # 1 hour to 1 week
    limit = max(1, min(limit or 10, 50))
    
    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    recent_files: List[tuple] = []
    max_depth = 4  # Configurable depth
    
    try:
        for root, dirs, files in os.walk(search_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                full_path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(full_path)
                    if mtime > cutoff_time:
                        recent_files.append((full_path, mtime))
                except (OSError, PermissionError):
                    continue
            
            # Limit depth to avoid too deep traversal
            if root.count(os.sep) - search_dir.count(os.sep) > max_depth:
                dirs.clear()
                
    except PermissionError:
        logger.debug(f"Permission denied walking {search_dir}")
    except Exception as e:
        logger.error(f"get_recent_files error: {e}")
        return f"Could not search for recent files: {e}"
    
    if not recent_files:
        return f"No files modified in the last {hours} hours in {search_dir}"
    
    # Sort by modification time (most recent first)
    recent_files.sort(key=lambda x: x[1], reverse=True)
    
    result = f"Files modified in the last {hours} hours:\n"
    for path, mtime in recent_files[:limit]:
        display_path = path.replace(HOME_DIR, "~") if path.startswith(HOME_DIR) else path
        time_str = datetime.fromtimestamp(mtime).strftime('%H:%M')
        result += f"  {time_str} - {display_path}\n"
    
    if len(recent_files) > limit:
        result += f"  ... and {len(recent_files) - limit} more files"
    
    return result.strip()


def find_and_open_file(pattern: str, which: int = 1, directory: str = None) -> str:
    """Find files and open the Nth matching one."""
    # Default to home directory, treat '.' as home
    search_dir = _expand_path(directory) if directory and directory != '.' else HOME_DIR
    
    if not os.path.isdir(search_dir):
        return f"Directory not found: {search_dir}"
    
    results: List[str] = []
    
    # Build search pattern
    if pattern.startswith("*") or pattern.startswith("**"):
        search_pattern = f"**/{pattern}"
    else:
        search_pattern = f"**/*{pattern}*"
    
    try:
        for path in Path(search_dir).glob(search_pattern):
            if _is_excluded_path(str(path)):
                continue
            if path.is_file():
                results.append(str(path))
                if len(results) >= MAX_RESULTS:
                    break
    except PermissionError:
        logger.debug(f"Permission denied searching in {search_dir}")
    except Exception as e:
        logger.error(f"find_and_open_file search error: {e}")
        return f"Search error: {e}"
    
    if not results:
        return f"No files found matching '{pattern}'."
    
    # Validate 'which' index
    which = which or 1
    if which < 1 or which > len(results):
        return f"Found {len(results)} files, but you asked for #{which}. Please choose 1 to {len(results)}."
    
    # Open the requested file
    target_file = results[which - 1]  # Convert to 0-indexed
    filename = os.path.basename(target_file)
    folder = os.path.basename(os.path.dirname(target_file))
    
    try:
        subprocess.Popen(
            ['xdg-open', target_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info(f"Opened file: {target_file}")
        return f"Opened {filename} from {folder} folder."
        
    except FileNotFoundError:
        return "Could not open file: xdg-open not found. Are you on Linux?"
    except Exception as e:
        logger.error(f"find_and_open_file open error: {e}")
        return f"Failed to open file: {e}"


# ============================================================
# Register all file tools
# ============================================================

register_tool(
    name="find_and_open_file",
    description="Find files matching a pattern and open the Nth one. Use this when user says 'find and open' or 'open a PDF'. Example: find PDFs and open the 4th one.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "File pattern (e.g., '*.pdf', 'report', '*.txt')"},
            "which": {"type": "integer", "description": "Which file to open (1=first, 2=second, etc). Default: 1"},
            "directory": {"type": "string", "description": "Directory to search (default: home)"}
        },
        "required": ["pattern"]
    },
    func=find_and_open_file
)

register_tool(
    name="find_files",
    description="Search for files by name pattern. Use this to LIST files without opening. For finding AND opening, use find_and_open_file instead.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "File name pattern to search for (e.g., '*.pdf', 'report', 'notes.txt')"},
            "directory": {"type": "string", "description": "Directory to search in (default: home directory)"},
            "file_type": {"type": "string", "enum": ["file", "directory"], "description": "Filter by type: 'file' or 'directory'"}
        },
        "required": ["pattern"]
    },
    func=find_files
)

register_tool(
    name="list_directory",
    description="List contents of a directory. Shows files and folders with sizes.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path to list (default: home directory)"},
            "show_hidden": {"type": "boolean", "description": "Include hidden files (default: false)"}
        },
        "required": []
    },
    func=list_directory
)

register_tool(
    name="read_file",
    description="Read the contents of a text file. Limited to small files for safety.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to read"},
            "max_lines": {"type": "integer", "description": "Maximum lines to read (default: 50, max: 200)"}
        },
        "required": ["path"]
    },
    func=read_file
)

register_tool(
    name="get_file_info",
    description="Get detailed information about a file including size, dates, and permissions.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file or directory"}
        },
        "required": ["path"]
    },
    func=get_file_info
)

register_tool(
    name="get_recent_files",
    description="Find recently modified files. Good for 'what did I work on today' type questions.",
    parameters={
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Directory to search (default: home)"},
            "hours": {"type": "integer", "description": "Look back this many hours (default: 24, max: 168)"},
            "limit": {"type": "integer", "description": "Max files to return (default: 10, max: 50)"}
        },
        "required": []
    },
    func=get_recent_files
)

