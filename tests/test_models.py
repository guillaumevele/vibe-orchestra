"""Tests for the model-backed tools. No network: chat_fn / urlopen are faked."""
from __future__ import annotations

import contextlib
import io
import json
import urllib.request

import pytest

from vibe_orchestra import models


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@contextlib.contextmanager
def _urlopen(fake):
    orig = urllib.request.urlopen
    urllib.request.urlopen = fake
    try:
        yield
    finally:
        urllib.request.urlopen = orig


def _capture():
    calls = {}

    def fake(messages, *, model, **opts):
        calls["messages"] = messages
        calls["model"] = model
        calls["opts"] = opts
        return "OUT"
    return calls, fake


def test_reason_uses_magistral_without_reasoning_effort():
    # magistral-medium-latest REJECTS reasoning_effort (400); it reasons natively.
    calls, fake = _capture()
    assert models.reason("why does it crash?", chat_fn=fake) == "OUT"
    assert calls["model"] == "magistral-medium-latest"
    assert "reasoning_effort" not in calls["opts"]
    assert calls["opts"].get("timeout_s") == 240


def test_vision_builds_multimodal_message_with_image_url():
    calls, fake = _capture()
    models.vision("https://x/y.png", "what's wrong?", chat_fn=fake)
    assert calls["model"] == "pixtral-latest"
    parts = calls["messages"][0]["content"]
    assert any(p.get("type") == "image_url" and p["image_url"] == "https://x/y.png" for p in parts)
    assert any(p.get("type") == "text" for p in parts)


def test_quick_uses_ministral():
    calls, fake = _capture()
    models.quick("extract emails", chat_fn=fake)
    assert calls["model"] == "ministral-3b-latest"


def test_image_part_local_file_becomes_data_url(tmp_path):
    img = tmp_path / "p.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n fake")
    part = models._image_part(str(img))
    assert part["image_url"].startswith("data:image/png;base64,")


def test_image_part_missing_file_raises():
    with pytest.raises(models.ModelError, match="image not found"):
        models._image_part("/no/such/image.png")


def test_chat_happy_path():
    def fake(req, timeout=None):
        return _Resp(json.dumps({"choices": [{"message": {"content": "hi"}}]}).encode())
    with _urlopen(fake):
        assert models.chat([{"role": "user", "content": "x"}], model="m", api_key="k") == "hi"


def test_chat_missing_key_raises(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(models.ModelError, match="MISTRAL_API_KEY"):
        models.chat([{"role": "user", "content": "x"}], model="m")


def test_chat_http_error_surfaces_status():
    import urllib.error

    def fake(req, timeout=None):
        raise urllib.error.HTTPError("https://x", 429, "rate", {}, io.BytesIO(b"{}"))
    with _urlopen(fake):
        with pytest.raises(models.ModelError, match="HTTP 429"):
            models.chat([{"role": "user", "content": "x"}], model="m", api_key="k")
