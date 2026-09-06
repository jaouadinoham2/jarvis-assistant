# 🤖 JARVIS — Local AI Voice Assistant

A fully local, GPU-accelerated AI assistant with a futuristic web HUD. Runs 100% offline on your personal workstation with zero cloud dependency.

[![Report](https://img.shields.io/badge/Project%20Report-12%20Pages%20PDF-blue.svg)](docs/jarvis_detail.pdf)
[![Python](https://img.shields.io/badge/Python-3.12+-yellow.svg)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)](#)
[![Ollama](https://img.shields.io/badge/Ollama-Phi--4%20Mini-orange.svg)](#)
[![Whisper](https://img.shields.io/badge/Speech--to--Text-faster--whisper-brightgreen.svg)](#)
[![Kokoro](https://img.shields.io/badge/Text--to--Speech-Kokoro%20TTS-purple.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📸 Interface Preview

### 🛡️ Iron Man Holographic HUD & Real-Time Status
![JARVIS Actual Interface](docs/jarvis_actual_interface.png)

### 🖐️ Biometric Hand Authentication Screen
![JARVIS Login Screen](docs/jarvis_login_page.png)

---

## 📑 Project Report & Architecture Whitepaper

The full 12-page comprehensive technical project report by Sahil is included directly in this repository:
📄 **[Download & Read Project Report (PDF)](docs/jarvis_detail.pdf)**

### Key Architecture Highlights:
- **100% Offline & Private**: Zero data leaves your machine; no external API calls.
- **Biometric Security**: Hand gesture detection via Google MediaPipe Hands model.
- **Zero-Latency Response**: Parallel text typing effect and Kokoro neural audio synthesis using `asyncio.gather()`.
- **Command Engine**: 50+ built-in system shortcuts for app launching, math, utilities, and diagnostics.
- **Background Startup**: Asynchronous model loading ensures port 8000 binds in <0.5s with non-blocking UI.

---

## ⚡ 1-Click Zero-Effort Installation (Recommended for Windows)

> [!TIP]
> **You do NOT need to install Python, Ollama, or AI models manually!**  
> The automated installer handles 100% of the downloads, dependencies, models, and shortcuts automatically in a single click.

### 🚀 Just 2 Steps:
1. **Download & Extract** [`JARVIS_Setup.zip`](JARVIS_Setup.zip) (or clone the repository).
2. **Double-click `Install_JARVIS.exe`** (or `Install_JARVIS.bat`).

### 🤖 What the Installer Does Automatically For You:
* ✅ **Checks Python:** Detects Python 3.12+ (installs it via Windows package manager if missing).
* ✅ **Sets Up Ollama:** Downloads and installs Ollama local AI server in the background.
* ✅ **Downloads Phi-4 Mini:** Pulls the official ~2.5 GB local model (`ollama pull phi4-mini`).
* ✅ **GPU PyTorch & Audio:** Creates a virtual environment and installs PyTorch with CUDA, `faster-whisper`, and `kokoro` TTS.
* ✅ **Creates Desktop Shortcut:** Generates `Start_JARVIS.bat` on your Desktop for 1-click launching!

---

<details>
<summary><b>🔧 Advanced: Optional Manual Step-by-Step Installation (For Developers / Linux / Custom Setups)</b></summary>

<br>

If you prefer to inspect and run every command manually instead of using the 1-click installer:

### Step 1: Install Ollama (Your AI Brain)
1. Go to **https://ollama.com/download** and download the Windows installer
2. Run the installer and pull the AI model:
   ```powershell
   ollama pull phi4-mini
   ```

### Step 2: Install espeak-ng (Required for Voice Output)
1. Download from **https://github.com/espeak-ng/espeak-ng/releases**
2. Install with default settings and add `C:\Program Files\eSpeak NG` to your system `PATH`.

### Step 3: Set Up Python Environment
1. Clone the repository:
   ```powershell
   git clone https://github.com/theviralcode-labs/jarvis-assistant.git
   cd jarvis-assistant
   ```
2. Create and activate virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r backend\requirements.txt
   ```

### Step 4: Launch JARVIS Manually
```powershell
cd backend
python main.py
```
Open **http://localhost:8000** in your browser.

</details>

---

## 🎯 How to Use

### ⌨️ Text Mode
- Type your message in the input box
- Press **Enter** or click the **Send** button
- JARVIS will respond with text AND voice

### 🎤 Voice Mode
- **Hold** the microphone button and speak
- **Release** when done — JARVIS will:
  1. Transcribe your speech
  2. Think of a response
  3. Speak back to you

### 🧹 Clear Memory
- Click the **trash icon** in the top-right to reset the conversation

---

## 🔧 Troubleshooting

### "Ollama not available"
- Make sure Ollama is installed and running
- Try: `ollama serve` in a separate terminal
- Then: `ollama pull phi4-mini`

### "STT failed to load on CUDA"
- The system will automatically fall back to CPU mode
- For GPU: ensure NVIDIA drivers and CUDA toolkit are installed
- Check: `nvidia-smi` in terminal should show your GPU

### "Kokoro TTS failed to load"
- Make sure `espeak-ng` is installed and in your PATH
- Restart your terminal after installing espeak-ng
- Test: `espeak-ng "hello"` should produce speech

### "Cannot access microphone"
- Allow microphone access in your browser
- Use Chrome or Edge for best compatibility
- The site must be accessed via `localhost` (not an IP address) for mic to work

### Slow responses?
- The first response may be slow (model loading into VRAM)
- Subsequent responses should be much faster
- Check GPU usage: `nvidia-smi` — the model should be in GPU memory

---

## 📁 Project Structure

```
jarvis/
├── backend/
│   ├── main.py              # FastAPI server + WebSocket handler
│   ├── llm_engine.py        # Ollama LLM integration
│   ├── stt_engine.py        # faster-whisper speech-to-text
│   ├── tts_engine.py        # Kokoro TTS text-to-speech
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # JARVIS web UI
│   ├── style.css            # Futuristic dark theme
│   ├── app.js               # WebSocket client + audio logic
│   └── assets/
│       └── jarvis-logo.jpg  # JARVIS logo
└── README.md                # This file
```

---

## 🖥️ System Requirements

| Component | Minimum | Recommended |
|:---|:---|:---|
| GPU | NVIDIA GTX 1060 6GB | RTX 3050 6GB+ |
| RAM | 8 GB | 16 GB |
| Storage | 10 GB free | 20 GB free |
| Python | 3.10+ | 3.11+ |
| OS | Windows 10/11 | Windows 11 |

---

Made with 💙 — Your local AI, your rules.


---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details. Free and open-source for developers worldwide.
