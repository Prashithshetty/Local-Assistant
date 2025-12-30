"""
Application control tools - open apps, files, URLs.
"""

import os
import subprocess
import shutil
from .tool_registry import register_tool

# Whitelist of safe applications (can be expanded)
ALLOWED_APPS = {
    # Browsers
    'firefox', 'chromium', 'brave', 'brave-browser', 'google-chrome', 'google-chrome-stable', 'chrome', 'vivaldi', 'opera',
    # Development
    'code', 'codium', 'sublime_text', 'gedit', 'kate', 'nvim', 'vim',
    # Utilities
    'nautilus', 'dolphin', 'thunar', 'nemo',  # File managers
    'gnome-terminal', 'konsole', 'alacritty', 'kitty',  # Terminals
    'gnome-calculator', 'kcalc', 'speedcrunch',  # Calculators
    # Media
    'vlc', 'mpv', 'totem', 'rhythmbox', 'spotify',
    # Office
    'libreoffice', 'okular', 'evince', 'gimp', 'inkscape',
    # System
    'gnome-system-monitor', 'htop', 'ksysguard',
    # Communication
    'discord', 'telegram-desktop', 'signal-desktop', 'slack',
    # Gaming
    'steam', 'lutris',
}


def open_application(app_name: str) -> str:
    """Open an application by name."""
    app_lower = app_name.lower().replace(' ', '-')
    
    # Common app name aliases
    aliases = {
        'google-chrome': 'google-chrome-stable',
        'chrome': 'google-chrome-stable',
        'vscode': 'code',
        'vs-code': 'code',
        'file-manager': 'nautilus',
        'files': 'nautilus',
        'terminal': 'gnome-terminal',
        'calculator': 'gnome-calculator',
        'brave-browser': 'brave',
    }
    
    # Apply alias if exists
    if app_lower in aliases:
        app_lower = aliases[app_lower]
    
    # Check common app name variations
    possible_names = [
        app_lower,
        app_lower.replace('-', '_'),
        app_lower.replace('-', ''),
        f"org.gnome.{app_lower.capitalize()}",
    ]
    
    # Try to find the application
    for name in possible_names:
        if name in ALLOWED_APPS or _is_safe_app(name):
            app_path = shutil.which(name)
            if app_path:
                try:
                    subprocess.Popen(
                        [app_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    return f"Opened {app_name}."
                except Exception as e:
                    return f"Failed to open {app_name}: {e}"
    
    # Try xdg-open for .desktop files
    try:
        result = subprocess.run(
            ['gtk-launch', app_lower],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return f"Opened {app_name}."
    except:
        pass
    
    return f"Could not find application: {app_name}. Make sure it's installed."


def open_file(path: str) -> str:
    """Open a file with its default application."""
    HOME_DIR = os.path.expanduser("~")
    
    # Handle various path formats the LLM might pass
    target_path = path
    
    # Replace common LLM hallucinations
    target_path = target_path.replace('/home/yourname/', '~/')
    target_path = target_path.replace('/home/username/', '~/')
    
    # Expand ~ to actual home directory
    target_path = os.path.expanduser(target_path)
    
    # If it's a relative path (like "Downloads/file.pdf"), prepend home
    if not os.path.isabs(target_path):
        target_path = os.path.join(HOME_DIR, target_path)
    
    if not os.path.exists(target_path):
        return f"File not found: {path}. Hint: Use the exact path from find_files (e.g., ~/Downloads/file.pdf)"
    
    try:
        subprocess.Popen(
            ['xdg-open', target_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return f"Successfully opened {os.path.basename(path)}."
    except Exception as e:
        return f"Failed to open file: {e}"


def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    # Basic URL validation
    if not url.startswith(('http://', 'https://', 'www.')):
        url = f"https://{url}"
    
    try:
        subprocess.Popen(
            ['xdg-open', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return f"Opened {url} in browser."
    except Exception as e:
        return f"Failed to open URL: {e}"


def _is_safe_app(name: str) -> bool:
    """Check if an app is safe to run (basic check)."""
    # Block obviously dangerous commands
    dangerous = ['rm', 'dd', 'mkfs', 'shutdown', 'reboot', 'poweroff', 
                 'sudo', 'su', 'chmod', 'chown', 'passwd', 'kill']
    return name not in dangerous


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
