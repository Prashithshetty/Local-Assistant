# Local-Assistant

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-GPL--3.0-green.svg" alt="GPL-3.0">
  <img src="https://img.shields.io/badge/model-Qwen2.5--3B-purple.svg" alt="Qwen2.5-3B">
</p>

A **voice-interactive AI assistant** for Linux. Speak naturally, and it responds with synthesized speech — powered by Whisper, Qwen2.5-3B, and Piper TTS.

## Features

- **Voice Input** — Record audio directly from your microphone
- **Qwen2.5-3B** — Local LLM with 4-bit quantization for efficient inference
- **Piper TTS** — Fast, high-quality text-to-speech
- **Tool Calling** — Execute system commands, open apps, search files, browse the web
- **Conversation Memory** — Maintains context with automatic history compression

## Requirements

### Hardware
- **RAM**: 16GB minimum
- **GPU**: NVIDIA GPU with 4GB+ VRAM (recommended)

### Software
- Python 3.9+
- CUDA Toolkit (for GPU acceleration)
- PortAudio (for audio I/O)

## Installation

```bash
# Clone the repository
git clone https://github.com/Prashithshetty/Local-Assistant.git
cd Local-Assistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python run_qwen_assistant.py
```

**How it works:**
1. Press **Enter** to start recording
2. Speak your query
3. Wait for the AI to process and respond
4. Listen to the audio response
5. Repeat! Press **Ctrl+C** to exit

## Available Tools

| Tool | Description |
|------|-------------|
| `system_info` | Get system information (CPU, RAM, GPU) |
| `open_app` | Open applications |
| `find_file` | Search for files |
| `open_file` | Open files with default application |
| `web_search` | Search the web |
| `run_command` | Execute shell commands |

## Project Structure

```
Local-Assistant/
├── run_qwen_assistant.py   # Main application
├── search_utils.py         # Web search utilities
├── cli_animations.py       # CLI animations
├── tools/                  # Tool implementations
│   ├── system_tools.py
│   ├── app_tools.py
│   ├── file_tools.py
│   ├── web_tools.py
│   └── tool_registry.py
├── models/                 # Model files (download separately)
└── requirements.txt
```

## Future Scope

This project aims to become **the native AI assistant for Linux machines** — just like Copilot on Windows, Siri on macOS/iOS, and Google Assistant on Android. The goal is to provide Linux users with a fully local, privacy-respecting, voice-controlled assistant that deeply integrates with the Linux desktop environment.

Planned features:
- Desktop environment integration (notifications, system controls)
- Vision capabilities with VLM models
- Plugin system for community extensions
- Multi-language support
- Wake word detection for hands-free activation

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

## Author

**Prashith Shetty** — [@Prashithshetty](https://github.com/Prashithshetty)

---

<p align="center">Made with care for the Linux community</p>
