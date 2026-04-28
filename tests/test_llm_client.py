"""Unit tests for NIMClient (no live API required)."""

import time
from unittest.mock import MagicMock, patch

import pytest

from core.llm_client import NIMClient


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.nvidia_api_key = "nvapi-test-key-1234"
    settings.nvidia_base_url = "https://integrate.api.nvidia.com/v1"
    settings.nvidia_model = "meta/llama-3.1-70b-instruct"
    settings.nvidia_route_model = "meta/llama-3.1-8b-instruct"
    settings.nvidia_embed_model = "nvidia/nv-embedqa-e5-v5"
    return settings


@patch("core.llm_client.OpenAI")
def test_client_initializes_with_settings(mock_openai_cls, mock_settings):
    """Verify client passes correct params to OpenAI constructor."""
    client = NIMClient(settings=mock_settings)
    mock_openai_cls.assert_called_once_with(
        api_key="nvapi-test-key-1234",
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=60,
    )


@patch("core.llm_client.OpenAI")
def test_chat_calls_completions_create(mock_openai_cls, mock_settings):
    """Verify chat() calls the OpenAI completions API."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    client = NIMClient(settings=mock_settings)
    result = client.chat(messages=[{"role": "user", "content": "hi"}])

    assert result == mock_response
    mock_client.chat.completions.create.assert_called_once_with(
        model="meta/llama-3.1-70b-instruct",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.7,
        max_tokens=1024,
    )


@patch("core.llm_client.OpenAI")
def test_chat_json_mode(mock_openai_cls, mock_settings):
    """Verify json_mode=True adds response_format."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock()

    client = NIMClient(settings=mock_settings)
    client.chat(messages=[{"role": "user", "content": "hi"}], json_mode=True)

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["response_format"] == {"type": "json_object"}


@patch("core.llm_client.OpenAI")
def test_embed_batches_correctly(mock_openai_cls, mock_settings):
    """Verify embed() batches texts at EMBED_BATCH_SIZE."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    def make_response(batch_size):
        items = []
        for _ in range(batch_size):
            item = MagicMock()
            item.embedding = [0.1, 0.2, 0.3]
            items.append(item)
        resp = MagicMock()
        resp.data = items
        return resp

    # 33 texts should produce 2 batches (32 + 1)
    mock_client.embeddings.create.side_effect = [
        make_response(32),
        make_response(1),
    ]

    client = NIMClient(settings=mock_settings)
    texts = [f"text {i}" for i in range(33)]
    result = client.embed(texts)

    assert mock_client.embeddings.create.call_count == 2
    assert len(result) == 33


@patch("core.llm_client.OpenAI")
@patch("core.llm_client.time.sleep")
def test_retry_on_rate_limit(mock_sleep, mock_openai_cls, mock_settings):
    """Verify retry with backoff on 429."""
    import openai as openai_module

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    rate_limit_error = openai_module.RateLimitError(
        message="rate limited",
        response=MagicMock(status_code=429),
        body=None,
    )
    mock_response = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        rate_limit_error,
        mock_response,
    ]

    client = NIMClient(settings=mock_settings)
    result = client.chat(messages=[{"role": "user", "content": "hi"}])

    assert result == mock_response
    assert mock_sleep.call_count == 1


@patch("core.llm_client.OpenAI")
def test_non_retryable_error_raises_immediately(mock_openai_cls, mock_settings):
    """Verify non-429/504 errors are not retried."""
    import openai as openai_module

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    auth_error = openai_module.AuthenticationError(
        message="invalid key",
        response=MagicMock(status_code=401),
        body=None,
    )
    mock_client.chat.completions.create.side_effect = auth_error

    client = NIMClient(settings=mock_settings)
    with pytest.raises(openai_module.AuthenticationError):
        client.chat(messages=[{"role": "user", "content": "hi"}])
