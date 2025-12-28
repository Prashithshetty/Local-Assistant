# 🎙️ Local-Assistant

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-GPL--3.0-green.svg" alt="GPL-3.0">
  <img src="https://img.shields.io/badge/model-LFM2--Audio--1.5B-purple.svg" alt="LFM2-Audio">
</p>

A **voice-interactive AI assistant** powered by the LFM2-Audio model. Speak to the assistant, and it responds with synthesized speech in real-time using streaming audio generation.

## ✨ Features

- 🎤 **Voice Recording** — Record 5-second audio clips directly from your microphone
- 🧠 **LFM2-Audio Model** — Uses Liquid's state-of-the-art 1.5B audio language model
- ⚡ **GPU/CPU Offloading** — Automatically balances model across GPU and CPU memory
- 🔊 **Streaming Audio** — Real-time audio generation with low latency
- 💬 **Conversation Memory** — Maintains context across multiple turns

## 📋 Requirements

### Hardware
- **RAM**: 16GB minimum, 32GB recommended
- **GPU**: NVIDIA GPU with 4GB+ VRAM (optional, falls back to CPU)

### Software
- Python 3.9+
- CUDA Toolkit (for GPU acceleration)
- PortAudio (for audio I/O)

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/Prashithshetty/Local-Assistant.git
cd Local-Assistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install liquid-audio accelerate sounddevice numpy

# Download the LFM2-Audio model to models/ directory
# (Model files should be placed in models/LFM2-Audio-1.5B/)
```

## 💻 Usage

```bash
python run_lfm.py
```

**How it works:**
1. Press **Enter** to start recording
2. Speak for **5 seconds** (recording stops automatically)
3. Wait for the AI to generate a response
4. Listen to the audio response
5. Repeat! Press **Ctrl+C** to exit

## ⚙️ Configuration

Edit the constants at the top of `run_lfm.py` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_ID` | `models/LFM2-Audio-1.5B` | Path to model |
| `SAMPLE_RATE` | `16000` | Input audio sample rate |
| `RECORD_DURATION` | `5` | Recording length (seconds) |
| `max_gpu_memory_gb` | `4.5` | GPU memory limit (in `main()`) |

## 🏗️ Project Structure

```
Local-Assistant/
├── run_lfm.py          # Main application
├── models/
│   └── LFM2-Audio-1.5B/  # Model files
├── LICENSE             # GPL-3.0 License
└── README.md           # This file
```

## 📝 License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Prashith Shetty** — [@Prashithshetty](https://github.com/Prashithshetty)

---

<p align="center">Made with ❤️ using <a href="https://www.liquid.ai/">Liquid AI</a>'s LFM2-Audio model</p>
