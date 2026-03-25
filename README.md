---
title: Anagram Quest — Word Guessing Environment
emoji: 🔤
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 8000
tags:
  - openenv
---

# 🔤 Anagram Quest — Word Guessing Environment

An RL-ready word guessing environment with 5 progressive difficulty levels, a strategic banking system, and dense reward shaping. Built with the OpenEnv framework for the Meta × PyTorch Hackathon 2026.

**👉 Open this Space to play the interactive game directly in your browser!**

## Game Overview

| Feature | Details |
|---------|---------|
| **Levels** | 5 levels (3→7 letter words) |
| **Objective** | Unscramble letters to find ALL valid anagram words |
| **Attempts** | Dynamic per level: `2 × total words in level` |
| **Banking** | Level 3+: a perfect opening guess can trigger a bank choice (`preserve` or `current`) |
| **Auto-progression** | Advances to next level when all words found or attempts exhausted |

## Reward System

| Event | Reward |
|-------|--------|
| First correct guess of a level with no prior mistakes | **+1.0** |
| Any other valid, unfound anagram | **+0.5** |
| Close guess (right letters, wrong word) | **+0.1** |
| Wrong guess | **-0.1** |
| All words in level found | **+2.0 bonus** |
| Perfect game (all 5 levels, no failures) | **+5.0 bonus** |
| Recovered word via bank | **+0.5** |

## Quick Start

### Play in Browser

Open this Hugging Face Space — the interactive game UI loads automatically.

### Use as RL Environment

```python
from word_guessing_env import WordGuessingAction, WordGuessingEnv

with WordGuessingEnv(base_url="<HF_SPACE_URL>") as env:
    result = env.reset()
    print(f"Level {result.observation.current_level}")
    print(f"Letters: {result.observation.scrambled_letters}")

    # Guess a word
    result = env.step(WordGuessingAction(word_guess="CARS"))
    print(f"Reward: {result.reward}")

    # Spend a banked chance on a failed LEVEL (Level 3+)
    result = env.step(WordGuessingAction(use_bank_on="3"))
```

### Run Locally

```bash
# Install dependencies
uv sync

# Start the server
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000

# Open http://localhost:8000/play in your browser
```

## Action Space

The agent can perform four action types:

```python
# Guess a word
WordGuessingAction(word_guess="CARS")

# Spend a banked chance to start recovery on a failed level (Level 3+)
WordGuessingAction(use_bank_on="3")

# Resolve a bank choice or spend action
WordGuessingAction(bank_decision="preserve")  # or "current", "boost_current", "cancel_recovery"

# Submit a recovery challenge guess
WordGuessingAction(recovery_guess="SCAR")
```

## Observation Space

Each observation contains:
- `scrambled_letters`: List of letters to unscramble
- `words_found`: Words successfully guessed so far
- `words_remaining`: How many words are left to find
- `current_level`: Current level (1-5)
- `attempts_left_for_word`: Remaining guess budget in the current level
- `banked_chances`: Available banked chances
- `failed_words`: Redacted failed entries recoverable via bank (e.g., `??? (L3)`)
- `message`: Human-readable feedback
- `reward`: Reward for this action
- `done`: Whether the game is over

## Project Structure

```
word_guessing_env/
├── README.md              # This file
├── openenv.yaml           # OpenEnv manifest
├── pyproject.toml         # Dependencies
├── models.py              # Action & Observation Pydantic models
├── client.py              # WordGuessingEnv client
├── static/
│   └── index.html         # Interactive game UI
└── server/
    ├── word_guessing_env_environment.py  # Core game logic
    ├── app.py             # FastAPI server + game API
    └── Dockerfile         # Container image
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/play` | GET | Interactive game UI |
| `/api/reset` | POST | Reset game (stateful) |
| `/api/step` | POST | Submit guess (stateful) |
| `/reset` | POST | OpenEnv reset (stateless) |
| `/step` | POST | OpenEnv step (stateless) |
| `/ws` | WS | WebSocket for persistent sessions |
| `/docs` | GET | Swagger API docs |
| `/health` | GET | Health check |

## Team

Built by **Yash & Divyansh** for the Meta × PyTorch OpenEnv Hackathon 2026.

## Contributors

- [Divyansh Ailani](https://github.com/divyanshailani)
- [Yash Bajpai](https://github.com/Yash1bajpai)
