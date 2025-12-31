#!/usr/bin/env python3
"""
Automatic Model Downloader for Local-Assistant.
Downloads required models if they don't exist.
"""

import os
import sys
import subprocess
import urllib.request
import shutil
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")

# Model configurations
MODELS_CONFIG = {
    "llama-3.2-3b-instruct": {
        "type": "gguf",
        "repo_id": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "description": "Llama-3.2-3B-Instruct - Lightweight LLM optimized for tool calling"
    },
    "piper": {
        "type": "piper",
        "model_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
        "model_file": "en_US-amy-medium.onnx",
        "config_file": "en_US-amy-medium.onnx.json",
        "description": "Piper TTS - Text-to-speech model"
    },
    "kokoro": {
        "type": "kokoro",
        "description": "Kokoro TTS - 82M parameter high-quality TTS (auto-downloads on first use)",
        "notes": "Requires espeak-ng system package. Model weights download automatically from HuggingFace."
    }
}



def print_status(message, status_type="info"):
    """Print colored status messages."""
    colors = {
        "info": "\033[94m",      # Blue
        "success": "\033[92m",   # Green
        "warning": "\033[93m",   # Yellow
        "error": "\033[91m",     # Red
        "download": "\033[96m",  # Cyan
    }
    reset = "\033[0m"
    icons = {
        "info": "ℹ️ ",
        "success": "✅",
        "warning": "⚠️ ",
        "error": "❌",
        "download": "⬇️ ",
    }
    color = colors.get(status_type, "")
    icon = icons.get(status_type, "")
    print(f"{color}{icon} {message}{reset}")


def check_huggingface_cli():
    """Check if huggingface-cli is available."""
    try:
        result = subprocess.run(
            ["huggingface-cli", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def download_huggingface_model(repo_id: str, target_dir: str, model_name: str):
    """Download a model from Hugging Face Hub."""
    print_status(f"Downloading {model_name} from Hugging Face...", "download")
    print_status(f"Repository: {repo_id}", "info")
    print_status(f"Target: {target_dir}", "info")
    
    # Ensure models directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    # Method 1: Use huggingface_hub Python library (preferred)
    try:
        from huggingface_hub import snapshot_download
        
        print_status("Using huggingface_hub for download...", "info")
        snapshot_download(
            repo_id=repo_id,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print_status(f"Successfully downloaded {model_name}!", "success")
        return True
        
    except ImportError:
        print_status("huggingface_hub not found, trying CLI...", "warning")
    except Exception as e:
        print_status(f"huggingface_hub error: {e}", "warning")
        print_status("Trying CLI method...", "info")
    
    # Method 2: Use huggingface-cli
    if check_huggingface_cli():
        try:
            result = subprocess.run(
                ["huggingface-cli", "download", repo_id, "--local-dir", target_dir],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print_status(f"Successfully downloaded {model_name}!", "success")
                return True
            else:
                print_status(f"CLI error: {result.stderr}", "error")
        except Exception as e:
            print_status(f"CLI error: {e}", "error")
    
    # Method 3: Install huggingface_hub and retry
    print_status("Installing huggingface_hub...", "info")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"], 
                      check=True, capture_output=True)
        
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=repo_id,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print_status(f"Successfully downloaded {model_name}!", "success")
        return True
        
    except Exception as e:
        print_status(f"Failed to download {model_name}: {e}", "error")
        return False


def download_file(url: str, destination: str, description: str = "file"):
    """Download a file with progress indication."""
    print_status(f"Downloading {description}...", "download")
    print_status(f"URL: {url}", "info")
    
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    try:
        # Use urllib with progress
        def report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, (downloaded / total_size) * 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r  Progress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="", flush=True)
        
        urllib.request.urlretrieve(url, destination, report_progress)
        print()  # New line after progress
        print_status(f"Downloaded: {os.path.basename(destination)}", "success")
        return True
        
    except Exception as e:
        print_status(f"Failed to download: {e}", "error")
        return False


def download_piper_model(target_dir: str):
    """Download Piper TTS model files."""
    config = MODELS_CONFIG["piper"]
    
    print_status("Downloading Piper TTS model...", "download")
    os.makedirs(target_dir, exist_ok=True)
    
    model_path = os.path.join(target_dir, config["model_file"])
    config_path = os.path.join(target_dir, config["config_file"])
    
    success = True
    
    # Download model file
    if not os.path.exists(model_path):
        if not download_file(config["model_url"], model_path, "Piper ONNX model"):
            success = False
    else:
        print_status(f"Model file already exists: {config['model_file']}", "info")
    
    # Download config file
    if not os.path.exists(config_path):
        if not download_file(config["config_url"], config_path, "Piper config"):
            success = False
    else:
        print_status(f"Config file already exists: {config['config_file']}", "info")
    
    return success


def check_model_exists(model_name: str) -> bool:
    """Check if a model exists and has required files."""
    config = MODELS_CONFIG.get(model_name, {})
    
    # For GGUF models, check if the single .gguf file exists
    if config.get("type") == "gguf":
        model_path = os.path.join(MODELS_DIR, model_name, config.get("filename", ""))
        return os.path.exists(model_path)
    
    model_dir = os.path.join(MODELS_DIR, model_name)
    
    if not os.path.exists(model_dir):
        return False
    
    # For Hugging Face models, check for required files
    if config.get("type") == "huggingface":
        required_files = config.get("required_files", [])
        for req_file in required_files:
            if not os.path.exists(os.path.join(model_dir, req_file)):
                return False
        return True
    
    # For Piper, check for ONNX and JSON files
    if config.get("type") == "piper":
        model_file = os.path.join(model_dir, config.get("model_file", ""))
        config_file = os.path.join(model_dir, config.get("config_file", ""))
        return os.path.exists(model_file) and os.path.exists(config_file)
    
    # If directory exists but no config, assume it's valid
    return len(os.listdir(model_dir)) > 0


def download_gguf_model(repo_id: str, filename: str, target_dir: str, model_name: str) -> bool:
    """Download a single GGUF file from Hugging Face."""
    print_status(f"Downloading {model_name} (GGUF)...", "download")
    print_status(f"Repository: {repo_id}", "info")
    print_status(f"File: {filename}", "info")
    
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, filename)
    
    try:
        from huggingface_hub import hf_hub_download
        
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print_status(f"Successfully downloaded {model_name}!", "success")
        return True
        
    except ImportError:
        print_status("huggingface_hub not installed. Installing...", "warning")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"], 
                          check=True, capture_output=True)
            from huggingface_hub import hf_hub_download
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=target_dir,
                local_dir_use_symlinks=False,
                resume_download=True
            )
            print_status(f"Successfully downloaded {model_name}!", "success")
            return True
        except Exception as e:
            print_status(f"Failed to download {model_name}: {e}", "error")
            return False
    except Exception as e:
        print_status(f"Failed to download {model_name}: {e}", "error")
        return False


def ensure_models_exist():
    """
    Check and download all required models (Llama-3.2 + Piper).
    Returns True if all models are ready, False otherwise.
    """
    return ensure_llama_models_exist()


def get_model_status():
    """Get the status of all required models."""
    status = {}
    
    for model_name, config in MODELS_CONFIG.items():
        model_dir = os.path.join(MODELS_DIR, model_name)
        exists = check_model_exists(model_name)
        
        status[model_name] = {
            "exists": exists,
            "path": model_dir,
            "description": config.get("description", ""),
            "type": config.get("type", "unknown")
        }
    
    return status


def ensure_llama_models_exist() -> bool:
    """
    Ensure only the Llama-3.2-3B and Piper models are downloaded.
    This is for the new lightweight assistant (run_assistant.py).
    Returns True if ready, False otherwise.
    """
    print_status("Checking models for Llama-3.2 assistant...", "info")
    
    os.makedirs(MODELS_DIR, exist_ok=True)
    all_success = True
    
    # Only download llama and piper
    required_models = ["llama-3.2-3b-instruct", "piper"]
    
    for model_name in required_models:
        config = MODELS_CONFIG.get(model_name)
        if not config:
            print_status(f"Model config not found: {model_name}", "error")
            all_success = False
            continue
        
        model_dir = os.path.join(MODELS_DIR, model_name)
        
        if check_model_exists(model_name):
            print_status(f"✓ {model_name}: Ready", "success")
            continue
        
        print_status(f"✗ {model_name}: Downloading...", "warning")
        
        if config["type"] == "gguf":
            success = download_gguf_model(
                repo_id=config["repo_id"],
                filename=config["filename"],
                target_dir=model_dir,
                model_name=model_name
            )
        elif config["type"] == "piper":
            success = download_piper_model(model_dir)
        else:
            print_status(f"Unknown model type: {config['type']}", "error")
            success = False
        
        if not success:
            all_success = False
    
    # Note about Whisper
    print_status("Note: Whisper model will be downloaded on first use", "info")
    
    if all_success:
        print_status("Llama-3.2 assistant models ready!", "success")
    
    return all_success


def get_llama_model_path() -> str:
    """Get the path to the Llama GGUF model file."""
    config = MODELS_CONFIG.get("llama-3.2-3b-instruct", {})
    return os.path.join(MODELS_DIR, "llama-3.2-3b-instruct", config.get("filename", ""))


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Local-Assistant Model Downloader")
    print("=" * 60 + "\n")
    
    success = ensure_models_exist()
    
    print("\n" + "=" * 60)
    if success:
        print("  All models ready! You can now run: python run_assistant.py")
    else:
        print("  Some downloads failed. Please check errors and retry.")
    print("=" * 60 + "\n")
    
    sys.exit(0 if success else 1)
