"""Thin Mistral chat client + model-backed tools, so a route becomes actionable.

The router says "this needs Magistral / Pixtral"; these helpers let the
orchestrator actually reach that model for a subtask, even though its own session
model is fixed. Zero dependencies (stdlib urllib); the HTTP call is injectable so
the tools are testable with no network.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

CHAT_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

# A chat backend: (messages, model, opts) -> assistant text.
ChatFn = Callable[..., str]


class ModelError(Exception):
    pass


def chat(messages: list, *, model: str, api_key: str | None = None,
         temperature: float = 0.0, reasoning_effort: str | None = None,
         max_tokens: int = 2048, timeout_s: int = 120) -> str:
    """One Mistral chat completion. Returns the assistant text."""
    api_key = api_key or os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        raise ModelError("MISTRAL_API_KEY is not set (and no api_key was provided).")
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        CHAT_ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise ModelError(f"Mistral HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise ModelError(f"Mistral request failed: {exc}") from exc
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelError(f"unexpected Mistral response: {data}") from exc


def _image_part(image: str) -> dict:
    """Build a Pixtral image content part from a local path or an http(s) URL."""
    if image.startswith(("http://", "https://", "data:")):
        return {"type": "image_url", "image_url": image}
    path = Path(image)
    if not path.exists():
        raise ModelError(f"image not found: {image}")
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": f"data:{mime};base64,{b64}"}


def reason(question: str, context: str = "", *, chat_fn: ChatFn | None = None) -> str:
    """Hard reasoning / root-cause / design via Magistral. Magistral reasons
    natively (do NOT pass reasoning_effort — the API rejects it for this model)
    and is deliberately slow, so we give it a long timeout."""
    chat_fn = chat_fn or chat
    user = question if not context else f"{question}\n\nContext:\n{context}"
    return chat_fn(
        [{"role": "system", "content": "Reason step by step. Be rigorous; state "
          "assumptions; give a clear final answer."},
         {"role": "user", "content": user}],
        model="magistral-medium-latest", timeout_s=240)


def vision(image: str, question: str, *, chat_fn: ChatFn | None = None) -> str:
    """Analyse an image / screenshot / UI via Pixtral."""
    chat_fn = chat_fn or chat
    return chat_fn(
        [{"role": "user", "content": [
            {"type": "text", "text": question},
            _image_part(image)]}],
        model="pixtral-latest")


def quick(task: str, *, chat_fn: ChatFn | None = None) -> str:
    """Cheap, low-latency transform (extract / classify / reformat) via Ministral."""
    chat_fn = chat_fn or chat
    return chat_fn(
        [{"role": "user", "content": task}],
        model="ministral-3b-latest")
