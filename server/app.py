# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Word Guessing Env Environment.

This module creates an HTTP server that exposes the WordGuessingEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import WordGuessingAction, WordGuessingObservation
    from .word_guessing_env_environment import WordGuessingEnvironment
except (ModuleNotFoundError, ImportError):
    from models import WordGuessingAction, WordGuessingObservation
    from server.word_guessing_env_environment import WordGuessingEnvironment


import os
from pathlib import Path
from threading import Lock
from uuid import uuid4
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Create the app with web interface and README integration
app = create_app(
    WordGuessingEnvironment,
    WordGuessingAction,
    WordGuessingObservation,
    env_name="word_guessing_env",
    max_concurrent_envs=1,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve interactive game UI
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

    @app.get("/play")
    async def play_game():
        """Serve the interactive game UI."""
        return FileResponse(str(_static_dir / "index.html"))

    @app.get("/web")
    async def web_game():
        """Serve the game UI at /web (HF Spaces loads this path)."""
        return FileResponse(str(_static_dir / "index.html"))

    @app.get("/")
    async def root_redirect():
        """Redirect root to the game UI."""
        return RedirectResponse(url="/play")


# ── Stateful Game API for the interactive UI ──
# Session-scoped envs so multiple users do not share progress.

SESSION_COOKIE = "anagram_session_id"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days
_game_sessions: dict[str, WordGuessingEnvironment] = {}
_session_lock = Lock()


def _get_or_create_session_env(request: Request) -> tuple[str, WordGuessingEnvironment, bool]:
    """Return (session_id, env, created_new_env)."""
    session_id = request.cookies.get(SESSION_COOKIE) or str(uuid4())
    created = False
    with _session_lock:
        env = _game_sessions.get(session_id)
        if env is None:
            env = WordGuessingEnvironment()
            _game_sessions[session_id] = env
            created = True
    return session_id, env, created


def _json_with_session(payload: dict, session_id: str) -> JSONResponse:
    """Attach session cookie to JSON payload."""
    response = JSONResponse(content=payload)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return response


def _obs_to_dict(obs):
    """Convert observation to safe JSON dict."""
    return {
        "observation": {
            "scrambled_letters": obs.scrambled_letters,
            "words_found": obs.words_found,
            "words_remaining": obs.words_remaining,
            "current_level": obs.current_level,
            "attempts_left_for_word": obs.attempts_left_for_word,
            "banked_chances": obs.banked_chances,
            "failed_words": obs.failed_words,
            "message": obs.message,
            "metadata": obs.metadata if hasattr(obs, 'metadata') and obs.metadata else {},
        },
        "reward": obs.reward or 0.0,
        "done": obs.done,
    }


@app.post("/api/reset")
async def api_reset(request: Request):
    """Reset the game — returns fresh Level 1 puzzle."""
    session_id, env, _ = _get_or_create_session_env(request)
    obs = env.reset()
    return _json_with_session(_obs_to_dict(obs), session_id)


@app.post("/api/step")
async def api_step(request: Request):
    """Process a guess, bank action, or bank decision."""
    session_id, env, created = _get_or_create_session_env(request)
    if created:
        # If step is called before reset, initialize a valid level first.
        env.reset()

    body = await request.json()
    action_data = body.get("action", body)

    action = WordGuessingAction(
        word_guess=action_data.get("word_guess"),
        use_bank_on=action_data.get("use_bank_on"),
        bank_decision=action_data.get("bank_decision"),
        recovery_guess=action_data.get("recovery_guess"),
    )
    obs = env.step(action)
    return _json_with_session(_obs_to_dict(obs), session_id)


# ── Patch 3: Backend model proxy (HF token stays server-side) ──

@app.post("/api/model/suggest")
async def model_suggest(request: Request):
    """Proxy to HF Inference API — token never exposed to browser."""
    hf_token = os.environ.get("HF_API_TOKEN", "")
    if not hf_token:
        return JSONResponse(
            status_code=503,
            content={"error": "Model not configured. Set HF_API_TOKEN env var."},
        )
    body = await request.json()
    prompt = body.get("prompt", "")

    import httpx
    model_id = os.environ.get("HF_MODEL_ID", "divyanshailani/anagram-quest-agent")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api-inference.huggingface.co/models/{model_id}",
            headers={"Authorization": f"Bearer {hf_token}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": 100, "return_full_text": False}},
        )
    return JSONResponse(content=resp.json(), status_code=resp.status_code)


def main():
    """
    Entry point for direct execution via uv run or python -m.

    This keeps CLI usage simple and validator-friendly:
        uv run --project . server
        uv run --project . server --port 8001
        python -m word_guessing_env.server.app
    """
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
