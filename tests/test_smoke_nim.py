"""Smoke test: JSON-mode chat round-trip against NVIDIA NIM."""

import json

import pytest

from core.llm_client import NIMClient


@pytest.fixture
def nim_client():
    """Create a NIMClient instance (requires .env.local with valid NVIDIA_API_KEY)."""
    return NIMClient()


@pytest.mark.integration
def test_json_mode_roundtrip(nim_client):
    """Verify NIM responds with valid JSON when json_mode=True."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Reply in JSON only."},
        {"role": "user", "content": 'Reply with exactly: {"status": "ok", "service": "nim"}'},
    ]
    response = nim_client.chat(
        messages=messages,
        json_mode=True,
        temperature=0.1,
        max_tokens=32,
    )
    content = response.choices[0].message.content
    parsed = json.loads(content)
    assert "status" in parsed, f"Expected 'status' key in response, got: {parsed}"
    assert parsed["status"] == "ok", f"Expected status=ok, got: {parsed['status']}"


@pytest.mark.integration
def test_chat_basic(nim_client):
    """Verify basic chat completion without JSON mode."""
    messages = [
        {"role": "user", "content": "Say hello in exactly one word."},
    ]
    response = nim_client.chat(
        messages=messages,
        temperature=0.1,
        max_tokens=16,
    )
    content = response.choices[0].message.content
    assert len(content.strip()) > 0, "Expected non-empty response"
