# 🌱 Eco-Helper: Sustainability Concierge

A Telegram chatbot powered by local AI (Ollama + LLaVA) that analyzes photos of products and packaging to provide recycling guidance, carbon footprint estimates, and greener alternatives. Features weekly eco-streak tracking and a community leaderboard to encourage sustainable habits.

---

## Table of Contents

- [Motivation](#motivation)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Technical Highlights](#technical-highlights)
- [Getting Started](#getting-started)
- [Screenshots](#screenshots)
- [Roadmap](#roadmap)
- [License](#license)

---

## Motivation

Sustainability starts with awareness. Most people want to recycle correctly and reduce their carbon footprint but don't know where to start when holding a random product. Eco-Helper bridges that gap — snap a photo, get instant actionable guidance, and build a habit through gamification. The project runs entirely locally, keeping user data private and demonstrating that useful AI applications don't require expensive cloud APIs.

---

## Features

- **📸 Multimodal Image Analysis** — Send a photo of any product or packaging for instant eco-guidance
- **♻️ Recycling Guidance** — Step-by-step instructions on how to properly recycle the item
- **🏭 Carbon Footprint Estimates** — AI-estimated CO₂e footprint for awareness
- **🌿 Greener Alternatives** — Specific suggestions for more sustainable options
- **🔥 Weekly Eco-Streak Tracker** — Gamification that rewards consistent scanning habits
- **🏆 Community Leaderboard** — Compete with friends to be the top eco-warrior
- **📬 Automated Weekly Summaries** — Sunday recaps of your eco-impact sent via Telegram
- **🔒 Fully Local** — All AI processing happens on your machine, no data leaves your PC

---

## Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Telegram  │  photo  │   Python Bot     │  image  │   Ollama API    │
│    User     │────────▶│  (python-telegram │────────▶│  (LLaVA model)  │
│             │◀────────│   -bot)           │◀────────│  localhost:11434 │
└─────────────┘  reply  └──────────────────┘  JSON   └─────────────────┘
                                │
                                │ log action
                                ▼
                        ┌──────────────────┐
                        │   SQLite DB      │
                        │  (users, actions,│
                        │   streaks)       │
                        └──────────────────┘
```

**Data Flow:**
1. User sends a photo via Telegram
2. Bot downloads the image and encodes it as base64
3. Image + prompt sent to Ollama's LLaVA vision model
4. Model returns structured JSON (product, category, guidance, carbon, alternatives)
5. Bot parses response, formats it, and replies to the user
6. Action is logged to SQLite for streak tracking and leaderboard

---

## Project Structure

```
eco-helper/
├── main.py                  # Entry point — starts bot and initializes DB
├── config.py                # Environment configuration (tokens, URLs)
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore
├── bot/
│   ├── __init__.py
│   ├── app.py               # Bot application setup, handler registration
│   └── handlers.py          # Command handlers (/start, /stats, /streak, etc.)
├── database/
│   ├── __init__.py
│   ├── engine.py            # SQLAlchemy engine, session management
│   └── models.py            # ORM models: User, EcoAction, WeeklyStreak
└── services/
    ├── __init__.py
    ├── ollama_service.py    # Ollama API client, prompt, response parsing
    ├── streak_service.py    # Streak logic, stats, leaderboard queries
    └── scheduler_service.py # APScheduler for weekly summary broadcasts
```

---

## Technical Highlights

| Area | Detail |
|------|--------|
| **Multimodal AI** | LLaVA vision model processes both image and text prompt simultaneously |
| **Structured Output Parsing** | JSON extraction from LLM responses with fallback flattening for nested structures |
| **Prompt Engineering** | Carefully crafted prompt that enforces flat JSON output for reliable parsing |
| **Async Architecture** | Fully async bot using `python-telegram-bot` + `httpx` for non-blocking I/O |
| **ORM & Migrations** | SQLAlchemy 2.0 declarative models with relationship mapping |
| **Gamification** | Streak algorithm tracks consecutive active weeks with automatic reset logic |
| **Scheduled Tasks** | APScheduler cron job for automated weekly community broadcasts |
| **Graceful Error Handling** | Connection failures, parse errors, and model issues all produce user-friendly messages |
| **Privacy-First** | Zero cloud dependencies — all AI inference runs locally via Ollama |

---

## Getting Started

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- A Telegram account

### 1. Pull the vision model

```bash
ollama pull llava
```

### 2. Create your Telegram bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot`, follow the prompts
3. Copy the bot token

### 3. Install dependencies

```bash
cd eco-helper
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env and paste your Telegram bot token
```

### 5. Run

```bash
python main.py
```

Open your bot in Telegram, send `/start`, and snap a photo!

---

## Screenshots

> *Add screenshots of your bot conversations here*

| Image Analysis | Stats Dashboard | Leaderboard |
|:-:|:-:|:-:|
| ![analysis](screenshots/analysis.png) | ![stats](screenshots/stats.png) | ![leaderboard](screenshots/leaderboard.png) |

---

## Roadmap

- [ ] `/history` command — view past scans with pagination
- [ ] Docker deployment setup for 24/7 hosting
- [ ] Support for multiple vision models (Bakllava, Gemma vision)
- [ ] Barcode scanning for precise product lookup
- [ ] Location-aware recycling rules (by city/country)
- [ ] Export eco-report as PDF
- [ ] Group chat support for team challenges
- [ ] Web dashboard with charts and analytics

---

## License

MIT
