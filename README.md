# ⚡ Figma AI Prompt Optimizer Bot

> **An AI-powered prompt compressor and design generator for Figma AI, First Draft, and Generative UI tools. Transforms raw requirements into ultra-dense, token-efficient design prompts powered by NVIDIA NIM.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM%20API-76B900.svg)](https://build.nvidia.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 The Problem

Generative UI engines like **Figma AI**, **First Draft**, and **Claude/GPT UI generators** consume large token budgets when prompted with conversational English. Conversational filler (*"Please design a modern screen where users can..."*) wastes tokens, introduces layout hallucinations, and frequently ignores visual hierarchy.

## 💡 The Solution

This tool acts as a **structural prompt compiler**:
1. Strips all conversational fluff.
2. Enforces **Atomic Design taxonomy** and **Figma Auto-Layout constraints**.
3. Emits compact declarative bracket tokens: `[Frame: ...] [Layout: ...] [Header: ...] [Hero: ...] [Tokens: ...]`.
4. **Reduces downstream token consumption by 60% – 75%** while increasing Figma design fidelity.

```
[Raw User Input] (45 verbose tokens)
  │
  ▼
[NVIDIA NIM Engine (Llama 3.1 8B / Mixtral)]
  │
  ▼
[Declarative Token Syntax] (16 dense tokens) ──► [Figma AI First Draft]
```

---

## 🚀 Key Features

* **⚡ Ultra-Dense Prompt Compression:** Translates natural language requirements into strict Figma AI bracket grammar.
* **📊 Live Token Reduction Gauge:** Real-time analytics showing tokens saved, percentage reduction, and latency.
* **🖼️ Interactive Wireframe Previewer:** Parses generated tokens into an interactive device mockup before you open Figma.
* **🎨 Preset Matrix:**
  * **Frames:** Desktop (1440px), Mobile iOS (375px), Tablet (834px), Smartwatch (390px).
  * **Themes:** SaaS Modern (Slate), Minimalist Dark (OLED), Clean Light, Glassmorphism, Neo-Brutalism.
* **🤖 Powered by NVIDIA NIM:** Uses high-throughput, low-latency models from the NVIDIA API Catalog (`meta/llama-3.1-8b-instruct`, `mistralai/mixtral-8x7b-instruct`, `nvidia/nemotron-mini-4b-instruct`).
* **📦 Zero-Dependency Core:** Runs out of the box using built-in Python standard library or Node.js.
* **💾 Local History & Export:** 1-Click copy for Figma, JSON export, and persistent history in browser storage.

---

## 🛠️ Quick Start

### 1. Clone & Navigate
```bash
git clone https://github.com/<your-username>/figma-prompt-bot.git
cd figma-prompt-bot
```

### 2. Configure Your NVIDIA API Key (Optional for live LLM)
Get a free API key with 1,000 free credits at **[build.nvidia.com](https://build.nvidia.com)**.

Create a `.env` file from the template:
```bash
cp .env.example .env
```
Add your key inside `.env`:
```env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PORT=8080
```
*(Note: If no API key is provided, the app automatically runs in **Offline Demonstration Mode** using the built-in rule synthesizer).*

---

### 3. Run the Web Server

#### Option A: Python (Zero external dependencies needed)
```bash
python3 server.py
```

#### Option B: Node.js (Zero external dependencies needed)
```bash
node server.js
```

#### Option C: Docker / Docker Compose
```bash
docker-compose up --build
```

Open your browser at **[http://localhost:8080](http://localhost:8080)**.

---

## 📂 Project Architecture

```
figma-prompt-bot/
├── app/
│   ├── __init__.py
│   ├── engine.py          # Core Prompt Optimization & Compilation Engine
│   ├── nvidia_client.py   # NVIDIA NIM API integration & Offline Fallback
│   ├── presets.py         # UI/UX Device, Style & Component Presets
│   └── tokenizer_sim.py   # BPE Token estimation & reduction metrics
├── public/
│   ├── index.html         # Modern Web UI Dashboard
│   ├── css/
│   │   └── style.css      # Dark/Light responsive theme & Glassmorphic UI
│   └── js/
│       ├── app.js         # Frontend controller, shortcuts, copy & state
│       ├── visualizer.js  # Live Wireframe Mockup Canvas
│       └── presets.js     # Client templates and quick chips
├── tests/
│   └── test_engine.py     # Unit test suite
├── server.py              # Zero-dependency Python server
├── server.js              # Zero-dependency Node.js server
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Multi-container config
├── requirements.txt       # Python dependencies
├── package.json           # Node scripts & metadata
└── README.md              # Project documentation
```

---

## 🎨 How to Use with Figma AI

1. Open the Web UI at `http://localhost:8080`.
2. Type or select a quick requirement (e.g. *"Mobile food delivery page with categories scroll, food cards with photo & price, and sticky bottom cart summary"*).
3. Select your target frame (**Mobile 375px**) and style (**Clean Light**).
4. Click **Generate Optimized Figma Prompt** (or press `Ctrl + Enter`).
5. Click **Copy Prompt**.
6. Open **Figma** ➔ launch **Figma AI (First Draft)** or paste into your Figma generative plugin.

---

## 🚢 Publishing to Your Git Repository

To publish this project to your own GitHub / GitLab account:

```bash
# 1. Initialize git (if not already initialized)
git init

# 2. Stage all files
git add .

# 3. Create your initial commit
git commit -m "feat: initial release of Figma AI Prompt Optimizer Bot"

# 4. Rename default branch to main
git branch -M main

# 5. Link to your remote GitHub repository
git remote add origin https://github.com/<your-username>/figma-prompt-bot.git

# 6. Push code to your repository
git push -u origin main
```

---

## 🧪 Running Unit Tests

```bash
python3 tests/test_engine.py
```

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
