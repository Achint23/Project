"""Unit tests for core/config.py."""

import os
from unittest.mock import patch

import pytest

from core.config import Settings


def test_settings_loads_from_env_vars():
    """Verify Settings picks up environment variables."""
    env = {
        "NVIDIA_API_KEY": "nvapi-test-123",
        "NVIDIA_BASE_URL": "https://test.example.com/v1",
        "NVIDIA_MODEL": "test-model",
        "NVIDIA_ROUTE_MODEL": "test-route-model",
        "NVIDIA_EMBED_MODEL": "test-embed-model",
    }
    with patch.dict(os.environ, env, clear=False):
        settings = Settings(_env_file=None)
        assert settings.nvidia_api_key == "nvapi-test-123"
        assert settings.nvidia_base_url == "https://test.example.com/v1"
        assert settings.nvidia_model == "test-model"
        assert settings.nvidia_route_model == "test-route-model"
        assert settings.nvidia_embed_model == "test-embed-model"


def test_settings_defaults():
    """Verify default values are set correctly."""
    env = {"NVIDIA_API_KEY": "nvapi-required"}
    with patch.dict(os.environ, env, clear=False):
        settings = Settings(_env_file=None)
        assert settings.nvidia_base_url == "https://integrate.api.nvidia.com/v1"
        assert settings.nvidia_model == "meta/llama-3.1-70b-instruct"
        assert settings.nvidia_route_model == "meta/llama-3.1-8b-instruct"
        assert settings.nvidia_embed_model == "nvidia/nv-embedqa-e5-v5"


def test_settings_requires_api_key():
    """Verify validation error if NVIDIA_API_KEY is missing."""
    from pydantic import ValidationError

    env = {k: v for k, v in os.environ.items() if k != "NVIDIA_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
