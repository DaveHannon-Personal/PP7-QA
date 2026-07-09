"""
Ollama client service — wraps Ollama's OpenAI-compatible REST API.

Configuration is loaded from the DB at call time.
Supports streaming and non-streaming chat completions.
"""
from __future__ import annotations

import json
import httpx
from collections.abc import AsyncIterator
from sqlalchemy.orm import Session
from app.models.config import AppConfig
from app.config import settings


def _get_config(db: Session) -> tuple[str, str]:
    """Return (ollama_url, ollama_model) from DB config (falls back to env)."""
    cfg = db.query(AppConfig).filter(AppConfig.id == 1).first()
    if cfg:
        return cfg.ollama_url, cfg.ollama_model
    return settings.ollama_url, settings.ollama_model


# System prompt injected on every conversation
_SYSTEM_PROMPT = """You are PP7-QA Assistant — an expert in ProPresenter 7 presentation software.

You help users:
1. Create QA rules to ensure presentation compliance (looks, themes, formatting, etc.)
2. Understand audit results and compliance reports
3. Decide which items to fix and how
4. Understand ProPresenter 7 features and best practices

When a user asks you to create a rule, respond with a JSON block in this exact format:
```json
{
  "action": "create_rule",
  "rule": {
    "name": "<descriptive rule name>",
    "description": "<what this rule checks>",
    "target": "<presentation|slide|look|theme|prop|macro|message>",
    "severity": "<error|warning|info>",
    "condition": {
      "field": "<dot.notation.field>",
      "operator": "<equals|not_equals|contains|not_contains|exists|not_exists|matches_regex>",
      "value": "<expected value or null>"
    },
    "fix_action": {
      "type": "<set_field|trigger_look|assign_theme|noop>",
      "field": "<field to set, if applicable>",
      "value": "<new value, if applicable>"
    }
  }
}
```

Always be concise. When showing audit results, use clear pass/fail language.
If you cannot determine a fix, set fix_action.type to "noop".
"""


async def chat(
    db: Session,
    messages: list[dict],
    stream: bool = True,
) -> AsyncIterator[str] | dict:
    """
    Send a chat completion request to Ollama.
    If stream=True, yields text chunks. Otherwise returns the full response dict.
    """
    ollama_url, model = _get_config(db)
    url = f"{ollama_url}/v1/chat/completions"

    full_messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + messages
    payload = {"model": model, "messages": full_messages, "stream": stream}

    if stream:
        return _stream_chat(url, payload)
    else:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()


async def _stream_chat(url: str, payload: dict) -> AsyncIterator[str]:
    """Yield token strings from a streaming Ollama response."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


async def list_models(db: Session) -> list[str]:
    """Return list of available model names from Ollama."""
    ollama_url, _ = _get_config(db)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{ollama_url}/v1/models")
        r.raise_for_status()
        data = r.json()
        return [m["id"] for m in data.get("data", [])]
