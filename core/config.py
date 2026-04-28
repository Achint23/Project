"""Configuration management via Pydantic settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env.local."""

    nvidia_api_key: str
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.1-70b-instruct"
    nvidia_route_model: str = "meta/llama-3.1-8b-instruct"
    nvidia_embed_model: str = "nvidia/nv-embedqa-e5-v5"

    model_config = {"env_file": ".env.local", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
