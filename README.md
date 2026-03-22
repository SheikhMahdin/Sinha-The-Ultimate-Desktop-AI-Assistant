<div align="center">

# 🎙️ SINHA — Advanced AI Voice Assistant

**A full-featured, offline-capable AI desktop assistant powered by Groq, Cohere, and Edge TTS**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3-orange?style=for-the-badge)](https://groq.com)
[![Cohere](https://img.shields.io/badge/Cohere-Command_A-blueviolet?style=for-the-badge)](https://cohere.com)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green?style=for-the-badge)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 📌 Overview

JARVIS is a production-grade AI voice assistant for Windows that listens, thinks, and acts — all in real time. It combines large language models, live web search, browser automation, image generation, and text-to-speech into a single cohesive desktop application with a custom PyQt5 GUI.

Unlike simple chatbot wrappers, JARVIS features a **two-layer decision architecture**: a fast Cohere model classifies every query into the right action type, and then routes it to the appropriate engine — whether that's a conversational LLM, a live web search, a browser automation task, or system control.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗣️ **Speech Recognition** | Browser-based microphone input via Selenium WebDriver with multilingual support |
| 🔊 **Text to Speech** | Microsoft Edge TTS with adjustable pitch, rate, and voice selection |
| 🧠 **AI Chatbot** | Persistent conversation memory via `ChatLog.json` using LLaMA 3.3 70B on Groq |
| 🔍 **Realtime Search** | Live web + weather + IP data gathering with parallel fetching and fallback APIs |
| 🤖 **Decision Model** | Two-layer query classifier using Cohere `command-a-03-2025` to route all intents |
| 🌐 **Browser Automation** | Selenium-powered Chrome automation using your own logged-in profile |
| 🖼️ **Image Generation** | AI image generation triggered by natural language, displayed in GUI |
| 📝 **Content Writing** | AI-generated letters, essays, emails, code snippets saved to `.txt` files |
| ⚙️ **System Control** | Volume mute/unmute/up/down via keyboard shortcuts |
| 😴 **Wake Word** | Sleep/wake system — say the wake word to activate, "sleep" to deactivate |
| 🖥️ **Custom GUI** | PyQt5 dark-themed interface with animated status, chat history, and mic toggle |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Main.py (Orchestrator)            │
│  VoiceAssistantApp → AssistantEngine → ThreadManager │
└──────────────────────────┬──────────────────────────┘
                           │
          ┌────────────────▼─────────────────┐
          │      Model.py (Decision Layer)    │
          │   Cohere → classifies every query │
          └──┬──────┬──────┬──────┬──────┬───┘
             │      │      │      │      │
      general│ real- │ open/│image │system│
             │ time  │close │ gen  │      │
             ▼      ▼      ▼      ▼      ▼
        Chatbot  Realtime  Auto-  Image  System
         .py    Search.py  mation  Gen   Commands
                           .py    .py
```

**Flow:**
1. `SpeechToText.py` captures microphone input via a headless Chrome WebDriver
2. `Model.py` (Cohere) classifies the query into: `general`, `realtime`, `open`, `close`, `play`, `system`, `content`, `google search`, `youtube search`, `generate image`, `reminder`, or `exit`
3. The classified task is routed to the correct backend module
4. The response is spoken aloud via `TextToSpeech.py` and displayed in the GUI

---

## 📁 Project Structure

```
JARVIS/
│
├── Main.py                     # Entry point & application orchestrator
│
├── Backend/
│   ├── Chatbot.py              # Groq LLaMA conversational AI with chat memory
│   ├── Model.py                # Cohere decision-making model (query classifier)
│   ├── Automation.py           # Browser & system task automation (Selenium)
│   ├── RealtimeSearchEngine.py # Live web search + weather + location data
│   ├── ImageGeneration.py      # AI image generation pipeline
│   ├── SpeechToText.py         # Browser-based speech recognition
│   └── TextToSpeech.py         # Edge TTS with multilingual support
│
├── Frontend/
│   ├── GUI.py                  # PyQt5 dark UI with animated status display
│   ├── Graphics/               # Icons, GIFs, and UI assets
│   └── Files/                  # Runtime state files (mic, status, responses)
│
├── Data/
│   ├── ChatLog.json            # Persistent conversation history
│   └── Voice.html              # Auto-generated speech recognition HTML
│
├── logs/
│   └── assistant.log           # Rotating application log
│
├── .env                        # Environment variables (API keys, config)
└── requirements.txt
```

---

## 🔧 Setup & Installation

### Prerequisites

- Python 3.10+
- Google Chrome installed
- Windows 10/11 (primary target; Linux/macOS partially supported)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/jarvis-voice-assistant.git
cd jarvis-voice-assistant
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the root directory:

```env
Username=YourName
Assistantname=Jarvis
GroqAPIKey=your_groq_api_key_here
CohereAPIKey=your_cohere_api_key_here
InputLanguage=en-US
AssistantVoice=en-US-AriaNeural
```

> **Get API keys:**
> - Groq (free): https://console.groq.com
> - Cohere (free tier): https://dashboard.cohere.com

### 4. Run

```bash
python Main.py
```

---

## 🔑 Environment Variables

| Variable | Description | Example |
|---|---|---|
| `Username` | Your display name | `Alex` |
| `Assistantname` | Assistant's name | `Jarvis` |
| `GroqAPIKey` | Groq API key for LLaMA | `gsk_...` |
| `CohereAPIKey` | Cohere API key for classifier | `...` |
| `InputLanguage` | Speech recognition language | `en-US` |
| `AssistantVoice` | Edge TTS voice name | `en-US-AriaNeural` |

---

## 💬 Example Commands

| You say | What happens |
|---|---|
| *"Jarvis"* | Wakes from sleep mode |
| *"What is quantum computing?"* | Answers via LLaMA chatbot |
| *"What's the weather in Dhaka today?"* | Live web search + weather API |
| *"Open YouTube"* | Launches YouTube in browser |
| *"Play Shape of You"* | Plays song on YouTube |
| *"Search Python tutorials on Google"* | Opens Google search results |
| *"Generate image of a sunset over mountains"* | Creates AI image |
| *"Write a business email for a client"* | Generates content, opens in editor |
| *"Mute the volume"* | System volume control |
| *"Sleep"* | Assistant enters sleep mode |
| *"Exit"* | Closes the application |

---

## 🧩 Module Details

### `Model.py` — Decision Engine
Uses Cohere's `command-a-03-2025` with a detailed preamble to classify any natural language input into structured action commands. Handles multi-task queries like *"Open Chrome and tell me about Gandhi"* → `open chrome, general tell me about Gandhi`.

### `Chatbot.py` — Conversational AI
Maintains full conversation history in `ChatLog.json`. Uses Groq's `llama-3.3-70b-versatile` for fast, high-quality responses. Includes real-time date/time injection into each request.

### `RealtimeSearchEngine.py` — Live Data
Fetches live results using multiple parallel API sources with fallback chains — never fails silently. Supports weather, news, IP location, and general web queries.

### `Automation.py` — Task Engine
Combines Selenium-powered real browser control (using your actual Chrome profile, so you're already logged in) with lightweight `pywhatkit`/`AppOpener` for system tasks. Supports YouTube interactions including search, play, like, and comment.

### `SpeechToText.py` — Voice Input
Launches a headless Chrome instance running the Web Speech API. Supports multilingual input with automatic English translation via `mtranslate`.

### `TextToSpeech.py` — Voice Output
Uses Microsoft Edge TTS (`edge-tts`) with `pygame` for audio playback. Automatically truncates very long responses and adds a natural spoken summary for readability.

### `GUI.py` — Interface
Custom PyQt5 dark-themed GUI with animated GIF status indicators, a chat history panel, mic toggle button, and real-time response streaming display.

---

## 📦 Dependencies

```
groq
cohere
edge-tts
pygame
PyQt5
selenium
webdriver-manager
mtranslate
langdetect
duckduckgo-search
requests
Pillow
python-dotenv
rich
keyboard
pywhatkit
AppOpener
```

Install all at once:
```bash
pip install groq cohere edge-tts pygame PyQt5 selenium webdriver-manager mtranslate langdetect duckduckgo-search requests Pillow python-dotenv rich keyboard pywhatkit AppOpener
```

---

## 🛣️ Roadmap

- [ ] Linux & macOS full support
- [ ] Reminder/calendar integration
- [ ] Plugin system for custom commands
- [ ] Local LLM support (Ollama)
- [ ] Mobile companion app
- [ ] Multi-assistant voice profiles

---

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss changes, then submit a pull request.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with Python, curiosity, and too many late nights.**

⭐ Star this repo if you found it useful!

</div>
