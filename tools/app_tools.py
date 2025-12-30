"""
Application control tools - open apps, files, URLs.
"""

import logging
import os
import subprocess
import shutil
from typing import Optional
from .tool_registry import register_tool

logger = logging.getLogger("tools.app")

# Get home directory safely
HOME_DIR = os.environ.get('HOME', os.path.expanduser("~"))

# Whitelist of safe applications (can be expanded)
ALLOWED_APPS = {
    # Browsers
    'firefox', 'chromium', 'brave', 'brave-browser', 'google-chrome', 
    'google-chrome-stable', 'chrome', 'vivaldi', 'opera', 'librewolf',
    # Development
    'code', 'codium', 'vscodium', 'sublime_text', 'gedit', 'kate', 
    'nvim', 'vim', 'neovim', 'cursor',
    # Utilities
    'nautilus', 'dolphin', 'thunar', 'nemo', 'pcmanfm',  # File managers
    'gnome-terminal', 'konsole', 'alacritty', 'kitty', 'wezterm', 'foot',  # Terminals
    'gnome-calculator', 'kcalc', 'speedcrunch', 'qalculate-gtk',  # Calculators
    # Media
    'vlc', 'mpv', 'totem', 'rhythmbox', 'spotify', 'elisa', 'celluloid',
    # Office
    'libreoffice', 'okular', 'evince', 'gimp', 'inkscape', 'krita',
    # System
    'gnome-system-monitor', 'htop', 'ksysguard', 'btop', 'mission-center',
    # Communication
    'discord', 'telegram-desktop', 'signal-desktop', 'slack', 'element-desktop',
    # Gaming
    'steam', 'lutris', 'heroic',
}

# Common app name aliases for better matching
APP_ALIASES = {
    'google-chrome': 'google-chrome-stable',
    'chrome': 'google-chrome-stable',
    'vscode': 'code',
    'vs-code': 'code',
    'visual-studio-code': 'code',
    'file-manager': 'nautilus',
    'files': 'nautilus',
    'terminal': 'gnome-terminal',
    'calculator': 'gnome-calculator',
    'calc': 'gnome-calculator',
    'brave-browser': 'brave',
    'text-editor': 'gedit',
    'editor': 'gedit',
    'music': 'rhythmbox',
    'video-player': 'vlc',
    'movies': 'vlc',
}

# Dangerous commands to never execute
DANGEROUS_COMMANDS = frozenset([
    'rm', 'dd', 'mkfs', 'shutdown', 'reboot', 'poweroff', 
    'sudo', 'su', 'chmod', 'chown', 'passwd', 'kill', 'pkill',
    'killall', 'init', 'systemctl', 'service', 'mount', 'umount',
    'fdisk', 'parted', 'wipefs', 'shred'
])


def _is_safe_app(name: str) -> bool:
    """Check if an app is safe to run."""
    if not name:
        return False
    name_lower = name.lower()
    return name_lower not in DANGEROUS_COMMANDS


def _find_app_executable(app_name: str) -> Optional[str]:
    """Find the executable path for an app, trying various name variations."""
    app_lower = app_name.lower().replace(' ', '-')
    
    # Apply alias if exists
    if app_lower in APP_ALIASES:
        app_lower = APP_ALIASES[app_lower]
    
    # Check common app name variations
    possible_names = [
        app_lower,
        app_lower.replace('-', '_'),
        app_lower.replace('-', ''),
        app_lower.replace('_', '-'),
    ]
    
    for name in possible_names:
        if name in ALLOWED_APPS or _is_safe_app(name):
            app_path = shutil.which(name)
            if app_path:
                return app_path
    
    return None


def open_application(app_name: str) -> str:
    """Open an application by name."""
    if not app_name or not app_name.strip():
        return "Please specify an application name."
    
    app_name = app_name.strip()
    
    # Try to find the executable
    app_path = _find_app_executable(app_name)
    
    if app_path:
        try:
            subprocess.Popen(
                [app_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            logger.info(f"Opened application: {app_name} ({app_path})")
            return f"Opened {app_name}."
        except Exception as e:
            logger.error(f"Failed to open {app_name}: {e}")
            return f"Failed to open {app_name}: {e}"
    
    # Try gtk-launch for .desktop files
    app_lower = app_name.lower().replace(' ', '-')
    try:
        result = subprocess.run(
            ['gtk-launch', app_lower],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logger.info(f"Opened application via gtk-launch: {app_name}")
            return f"Opened {app_name}."
    except FileNotFoundError:
        logger.debug("gtk-launch not found")
    except subprocess.TimeoutExpired:
        logger.debug("gtk-launch timed out")
    except Exception as e:
        logger.debug(f"gtk-launch error: {e}")
    
    return f"Could not find application: {app_name}. Make sure it's installed."


def open_file(path: str) -> str:
    """Open a file with its default application."""
    if not path or not path.strip():
        return "Please specify a file path."
    
    # Handle various path formats the LLM might pass
    target_path = path.strip()
    
    # Replace common LLM hallucinations
    target_path = target_path.replace('/home/yourname/', '~/')
    target_path = target_path.replace('/home/username/', '~/')
    target_path = target_path.replace('/home/user/', '~/')
    
    # Expand ~ to actual home directory
    target_path = os.path.expanduser(target_path)
    
    # If it's a relative path, prepend home
    if not os.path.isabs(target_path):
        target_path = os.path.join(HOME_DIR, target_path)
    
    if not os.path.exists(target_path):
        return f"File not found: {path}. Hint: Use the exact path from find_files."
    
    try:
        subprocess.Popen(
            ['xdg-open', target_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        filename = os.path.basename(target_path)
        logger.info(f"Opened file: {target_path}")
        return f"Successfully opened {filename}."
        
    except FileNotFoundError:
        return "Could not open file: xdg-open not found. Are you on Linux?"
    except Exception as e:
        logger.error(f"Failed to open file {path}: {e}")
        return f"Failed to open file: {e}"


def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    if not url or not url.strip():
        return "Please specify a URL."
    
    url = url.strip()
    
    # Basic URL validation and fixing
    if not url.startswith(('http://', 'https://')):
        if url.startswith('www.'):
            url = f"https://{url}"
        elif '.' in url:  # Looks like a domain
            url = f"https://{url}"
        else:
            return f"Invalid URL: {url}. Please provide a valid web address."
    
    # Basic sanitization - remove dangerous characters
    if any(char in url for char in [';', '|', '&', '$', '`', '\n', '\r']):
        return f"Invalid URL: contains unsafe characters."
    
    try:
        subprocess.Popen(
            ['xdg-open', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info(f"Opened URL: {url}")
        return f"Opened {url} in browser."
        
    except FileNotFoundError:
        return "Could not open URL: xdg-open not found. Are you on Linux?"
    except Exception as e:
        logger.error(f"Failed to open URL {url}: {e}")
        return f"Failed to open URL: {e}"


# ============================================================
# Register all app tools
# ============================================================

register_tool(
    name="open_application",
    description="Open an application by name. Examples: Firefox, VS Code, Terminal, Calculator, File Manager.",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name of the application to open"}
        },
        "required": ["app_name"]
    },
    func=open_application
)

register_tool(
    name="open_file",
    description="Open a file with its default application.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to open"}
        },
        "required": ["path"]
    },
    func=open_file
)

register_tool(
    name="open_url",
    description="Open a URL in the default web browser.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to open (e.g., github.com, google.com)"}
        },
        "required": ["url"]
    },
    func=open_url
)

