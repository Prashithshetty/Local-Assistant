# Local-Assistant

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-GPL--3.0-green.svg" alt="GPL-3.0">
  <img src="https://img.shields.io/badge/model-Qwen2.5--3B-purple.svg" alt="Qwen2.5-3B">
</p>

A **voice-interactive AI assistant** for Linux. Speak naturally, and it responds with synthesized speech — powered by Whisper, Qwen2.5-3B, and Piper TTS.

## Features

- **Voice Input** — Record audio directly from your microphone
- **Llama-3.2-3B** — Lightweight local LLM optimized for instruction following and tool calling
- **Kokoro TTS** — High-quality, natural-sounding ~82M parameter text-to-speech
- **Tool Calling** — Execute system commands, open apps, search files, browse the web
- **Conversation Memory** — Maintains context with automatic history compression

## Requirements

### Hardware
- **RAM**: 8GB minimum (16GB recommended)
- **GPU**: NVIDIA (with CUDA) or any GPU supported by llama-cpp-python (optional, runs on CPU too)
- **VRAM**: 4GB+ recommended for faster inference

### Software
- Python 3.9+
- Linux (tested on Arch/CachyOS)
- PortAudio (for audio I/O)
- espeak-ng (required for Kokoro TTS)

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

**Note:** Models are downloaded automatically on first run. If you want to pre-download them:
```bash
python model_downloader.py
```

## Usage

```bash
python run_assistant.py
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
├── run_assistant.py        # Main lightweight application (Llama-3.2 + Kokoro)
├── model_downloader.py     # Auto-downloads required models
├── search_utils.py         # Web search utilities
├── cli_animations.py       # CLI animations
├── tools/                  # Tool implementations
│   ├── system_tools.py
│   ├── app_tools.py
│   ├── file_tools.py
│   ├── web_tools.py
│   └── tool_registry.py
├── models/                 # Model files (auto-downloaded)
└── requirements.txt
```

## Future Scope

This project aims to become **the native AI assistant for Linux machines** — a truly universal "Copilot" for the open-source world. Unlike cloud-based assistants (Siri, Gemini, Copilot), this project focuses on:

1.  **Privacy First**: 100% local processing. Your voice and data never leave your machine.
2.  **OS Integration**: Deep integration with the Linux desktop (KDE, GNOME, Hyprland) to control settings, windows, and workflow.
3.  **Universal Compatibility**: Designed to run on everything from powerful workstations to low-power handhelds (Steam Deck, ROG Ally) and older laptops.

**Planned Roadmap:**
- **Vision Capabilities**: Integration of Vision-Language Models (VLM) like Qwen2-VL to "see" your screen and answer questions about it.
- **Hands-Free Activation**: efficient wake-word detection (e.g., "Hey Assistant") running in the background.
- **Desktop Awareness**: Ability to interact with running applications, move windows, and automate GUI tasks.
- **Plugin System**: A modular API for community-created tools and skills.
- **Multi-Language Support**: Expanding beyond English for global accessibility.

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

## Author

**Prashith Shetty** — [@Prashithshetty](https://github.com/Prashithshetty)

---

<p align="center">Made with care for the Linux community</p>
