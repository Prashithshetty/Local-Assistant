"""
File system tools - find, list, read files.
"""

import os
import glob
import stat
from datetime import datetime
from pathlib import Path
from typing import Optional
from .tool_registry import register_tool

# Safety limits
MAX_FILE_SIZE = 50 * 1024  # 50KB max for reading files
MAX_RESULTS = 20  # Max search results
HOME_DIR = os.path.expanduser("~")

# Directories to exclude from searches
EXCLUDED_DIRS = {'.git', '.venv', 'node_modules', '__pycache__', '.cache', '.local/share/Trash'}


def find_files(pattern: str, directory: str = None, file_type: str = None) -> str:
    """Find files matching a pattern."""
    search_dir = directory or HOME_DIR
    search_dir = os.path.expanduser(search_dir)
    
    if not os.path.isdir(search_dir):
        return f"Directory not found: {search_dir}"
    
    results = []
    search_pattern = f"**/*{pattern}*" if not pattern.startswith("*") else f"**/{pattern}"
    
    try:
        for path in Path(search_dir).glob(search_pattern):
            # Skip excluded directories
            if any(excluded in str(path) for excluded in EXCLUDED_DIRS):
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
        pass
    
    if not results:
        return f"No files found matching '{pattern}' in {search_dir}"
    
    result = f"Found {len(results)} items matching '{pattern}':\n"
    for path in results:
        # Show relative path if in home
        display_path = path.replace(HOME_DIR, "~") if path.startswith(HOME_DIR) else path
        result += f"  {display_path}\n"
    
    if len(results) >= MAX_RESULTS:
        result += f"  ... (showing first {MAX_RESULTS} results)"
    
    return result.strip()


def list_directory(path: str = None, show_hidden: bool = False) -> str:
    """List contents of a directory."""
    target_dir = path or HOME_DIR
    target_dir = os.path.expanduser(target_dir)
    
    if not os.path.isdir(target_dir):
        return f"Directory not found: {target_dir}"
    
    try:
        items = os.listdir(target_dir)
    except PermissionError:
        return f"Permission denied: {target_dir}"
    
    # Filter hidden files if not requested
    if not show_hidden:
        items = [item for item in items if not item.startswith('.')]
    
    items.sort(key=str.lower)
    
    # Categorize into files and directories
    dirs = []
    files = []
    
    for item in items:
        full_path = os.path.join(target_dir, item)
        if os.path.isdir(full_path):
            dirs.append(f"📁 {item}/")
        else:
            # Get file size
            try:
                size = os.path.getsize(full_path)
                size_str = _format_size(size)
                files.append(f"📄 {item} ({size_str})")
            except:
                files.append(f"📄 {item}")
    
    display_path = target_dir.replace(HOME_DIR, "~") if target_dir.startswith(HOME_DIR) else target_dir
    result = f"Contents of {display_path}:\n"
    
    # Show directories first, then files
    for item in dirs[:MAX_RESULTS//2]:
        result += f"  {item}\n"
    for item in files[:MAX_RESULTS//2]:
        result += f"  {item}\n"
    
    total = len(dirs) + len(files)
    if total > MAX_RESULTS:
        result += f"  ... and {total - MAX_RESULTS} more items"
    
    return result.strip()


def read_file(path: str, max_lines: int = 50) -> str:
    """Read contents of a text file (limited for safety)."""
    target_path = os.path.expanduser(path)
    
    if not os.path.isfile(target_path):
        return f"File not found: {path}"
    
    # Security: check file size
    try:
        size = os.path.getsize(target_path)
        if size > MAX_FILE_SIZE:
            return f"File too large ({_format_size(size)}). Max allowed: {_format_size(MAX_FILE_SIZE)}"
    except:
        return f"Cannot access file: {path}"
    
    # Try to read as text
    try:
        with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        if len(lines) > max_lines:
            content = ''.join(lines[:max_lines])
            return f"File: {path} (showing first {max_lines} of {len(lines)} lines)\n\n{content}"
        else:
            return f"File: {path}\n\n{''.join(lines)}"
    except Exception as e:
        return f"Could not read file: {e}"


def get_file_info(path: str) -> str:
    """Get detailed information about a file."""
    target_path = os.path.expanduser(path)
    
    if not os.path.exists(target_path):
        return f"Path not found: {path}"
    
    try:
        stat_info = os.stat(target_path)
        
        result = f"File Info: {path}\n"
        result += f"Type: {'Directory' if os.path.isdir(target_path) else 'File'}\n"
        result += f"Size: {_format_size(stat_info.st_size)}\n"
        result += f"Modified: {datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"Created: {datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"Permissions: {stat.filemode(stat_info.st_mode)}"
        
        return result
    except Exception as e:
        return f"Could not get file info: {e}"


def get_recent_files(directory: str = None, hours: int = 24, limit: int = 10) -> str:
    """Get recently modified files in a directory."""
    search_dir = directory or HOME_DIR
    search_dir = os.path.expanduser(search_dir)
    
    if not os.path.isdir(search_dir):
        return f"Directory not found: {search_dir}"
    
    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    recent_files = []
    
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
                except:
                    pass
            
            # Limit depth to avoid too deep traversal
            if root.count(os.sep) - search_dir.count(os.sep) > 3:
                dirs.clear()
    except PermissionError:
        pass
    
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


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


# ============================================================
# Register all file tools
# ============================================================

register_tool(
    name="find_files",
    description="Search for files by name pattern. Supports wildcards like *.pdf or report*.",
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
            "max_lines": {"type": "integer", "description": "Maximum lines to read (default: 50)"}
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
            "hours": {"type": "integer", "description": "Look back this many hours (default: 24)"},
            "limit": {"type": "integer", "description": "Max files to return (default: 10)"}
        },
        "required": []
    },
    func=get_recent_files
)
