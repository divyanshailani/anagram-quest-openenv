# Word Guessing Env - Codex Patch Sheet

This file captures the hardening patches we discussed after the first deployed version of `word_guessing_env`.

## Patch 1 - Make UI game state session-scoped (not global)

### Why
Current UI endpoints use a single shared object:
- `_game_env = WordGuessingEnvironment()` in `server/app.py`

On a public HF Space, different users can overwrite each other's progress.

### Target file
- `server/app.py`

### Patch intent
Replace one global env with a per-session env map keyed by cookie/session id.

### Implementation outline
1. Add a session store:
   - `game_sessions: dict[str, WordGuessingEnvironment] = {}`
2. Generate/reuse session ids in `/api/reset` and `/api/step`.
3. Read/write the env from `game_sessions[session_id]`.
4. Return the session cookie to the browser.
5. Add TTL cleanup later if needed.

### Pseudocode
```python
from uuid import uuid4
from fastapi import Request, Response, HTTPException

SESSION_COOKIE = "anagram_session_id"
game_sessions: dict[str, WordGuessingEnvironment] = {}

def _get_or_create_session_env(request: Request, response: Response) -> WordGuessingEnvironment:
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        sid = str(uuid4())
        response.set_cookie(SESSION_COOKIE, sid, httponly=True, samesite="lax")
    if sid not in game_sessions:
        game_sessions[sid] = WordGuessingEnvironment()
    return game_sessions[sid]
```

---

## Patch 2 - Stop leaking answers via public state

### Why
`WordGuessingState` currently includes:
- `valid_anagrams`

Any client reading `/state` can inspect the answer set and cheat.

### Target files
- `models.py`
- `server/word_guessing_env_environment.py`

### Patch intent
Keep answer data private in environment internals, not in `WordGuessingState`.

### Implementation outline
1. Remove `valid_anagrams` from `WordGuessingState` in `models.py`.
2. In the environment class, store answers in a private attribute:
   - `self._valid_anagrams_private: list[str]`
3. Update guess logic to reference private attribute.
4. Keep only safe gameplay metadata in public state.

### Notes
- This preserves game integrity for both API clients and UI users.
- If debug access is needed, gate it behind an explicit debug flag.

---

## Patch 3 - Move HF token usage behind backend proxy

### Why
If frontend JS directly calls HF Inference with a bearer token, the token can be extracted from browser traffic.

### Target files
- `server/app.py` (or new `server/model_proxy.py`)
- `static/index.html` (or frontend JS module)
- `.env.example` (new)

### Patch intent
Frontend calls your own backend endpoint; backend calls HF API with server-side token.

### Implementation outline
1. Add env var `HF_API_TOKEN` on server.
2. Add backend endpoint, e.g. `POST /api/model/suggest`.
3. Frontend calls `/api/model/suggest` (no bearer token in browser).
4. Backend forwards prompt to HF Inference API.

### Minimal endpoint shape
```python
@app.post("/api/model/suggest")
async def model_suggest(payload: dict):
    # read letters from payload
    # call HF with server-side token
    # return model output
```

---

## Patch 4 - Fix duplicate key in anagram dictionary

### Why
`ANAGRAM_GROUPS` contains duplicate key `AEPRST`; the later entry silently overwrites the earlier one.

### Target file
- `server/word_guessing_env_environment.py`

### Patch intent
Deduplicate keys and merge values intentionally.

### Action
- Keep one `AEPRST` entry only.
- Ensure merged list is unique and valid.

---

## Patch 5 - Keep `openenv validate` friendly entrypoint

### Why
OpenEnv validator checks for a callable `main()` pattern in `server/app.py`.

### Target file
- `server/app.py`

### Patch intent
Use a simple module entrypoint:
```python
if __name__ == "__main__":
    main()
```

---

## Suggested patch order
1. Patch 2 (answer leakage)  
2. Patch 1 (session isolation)  
3. Patch 4 (dictionary hygiene)  
4. Patch 5 (validator stability)  
5. Patch 3 (model-proxy security before AI-thinking rollout)

---

## Validation checklist after patching
- `openenv validate --verbose` passes.
- Two separate browser sessions do not share progress.
- `/state` does not reveal answer words.
- UI gameplay still works at `/play` and `/web`.
- HF deployment still starts and serves correctly.
