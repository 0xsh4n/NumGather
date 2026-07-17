"""
NumGather 2.0 — Ollama client for local LLM reasoning over phone intel.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Iterator

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
# Reasoning-oriented models often work well: deepseek-r1, qwen2.5, etc.
DEFAULT_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))

SYSTEM_PROMPT = """You are NumGather Intelligence — a careful OSINT analyst specializing in telephone numbering plans.

You receive structured facts from libphonenumber and a local India MSC database.
Your job is to reason about what those facts imply.

Rules:
- Base conclusions only on the provided facts. Do not invent HLR/subscriber PII.
- Explain numbering-plan meaning: country, type, carrier signals, portability hints.
- Flag uncertainty (MNP, VoIP, incomplete validation) clearly.
- If India MSC data is present, relate circle/operator to the carrier field.
- Give practical investigator notes (what you can / cannot conclude from a number alone).
- Be concise but thorough. Use short sections with clear headings.
- Never claim you "tracked" a person or device location from the number alone.
"""


def is_available(host: str | None = None, timeout: float = 3.0) -> bool:
    """Return True if Ollama responds on /api/tags."""
    base = (host or DEFAULT_HOST).rstrip("/")
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def list_models(host: str | None = None, timeout: float = 5.0) -> list[str]:
    """List locally available Ollama model names."""
    base = (host or DEFAULT_HOST).rstrip("/")
    req = urllib.request.Request(f"{base}/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return [m.get("name", "") for m in payload.get("models", []) if m.get("name")]


def reason(
    report: dict[str, Any],
    *,
    model: str | None = None,
    host: str | None = None,
    stream: bool = False,
    timeout: int | None = None,
) -> str | Iterator[str]:
    """
    Ask Ollama to reason over a NumGather intelligence report.

    If stream=True, returns an iterator of text chunks.
    Otherwise returns the full response string.
    """
    base = (host or DEFAULT_HOST).rstrip("/")
    model_name = model or DEFAULT_MODEL
    wait = timeout if timeout is not None else DEFAULT_TIMEOUT

    user_content = (
        "Analyze this phone-number intelligence report and provide reasoned "
        "OSINT-style conclusions:\n\n"
        f"```json\n{json.dumps(report, indent=2, ensure_ascii=False)}\n```"
    )

    body = {
        "model": model_name,
        "stream": stream,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "options": {
            # Slightly lower temperature for analytical consistency
            "temperature": 0.3,
        },
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    if stream:
        return _stream_chat(req, wait)
    return _complete_chat(req, wait)


def _complete_chat(req: urllib.request.Request, timeout: int) -> str:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {req.full_url!r}. "
            "Is `ollama serve` running? "
            f"Details: {exc.reason}"
        ) from exc

    message = payload.get("message") or {}
    content = message.get("content") or payload.get("response") or ""
    # Some reasoning models put chain-of-thought in a thinking field
    thinking = message.get("thinking")
    if thinking and content:
        return f"### Reasoning\n{thinking.strip()}\n\n### Conclusion\n{content.strip()}"
    if thinking and not content:
        return thinking.strip()
    return content.strip()


def _stream_chat(req: urllib.request.Request, timeout: int) -> Iterator[str]:
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama. Is `ollama serve` running? ({exc.reason})"
        ) from exc

    def generate() -> Iterator[str]:
        with resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = chunk.get("message") or {}
                piece = msg.get("content") or chunk.get("response") or ""
                thinking = msg.get("thinking")
                if thinking:
                    yield thinking
                if piece:
                    yield piece
                if chunk.get("done"):
                    break

    return generate()
