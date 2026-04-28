"""NVIDIA NIM LLM client with retry, JSON mode, and batched embeddings."""

import random
import time

import openai
from openai import OpenAI

from core.config import Settings, get_settings


class NIMClient:
    """NVIDIA NIM client with retry, JSON mode, and batched embeddings."""

    MAX_RETRIES = 4
    BASE_DELAY = 1.0  # seconds
    TIMEOUT = 60  # seconds
    EMBED_BATCH_SIZE = 32

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._client = OpenAI(
            api_key=self._settings.nvidia_api_key,
            base_url=self._settings.nvidia_base_url,
            timeout=self.TIMEOUT,
        )

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ):
        """Send chat completion with retry on 429/504."""
        model = model or self._settings.nvidia_model
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return self._call_with_retry(
            lambda: self._client.chat.completions.create(**kwargs)
        )

    def embed(self, texts: list[str], model: str | None = None, input_type: str = "passage") -> list[list[float]]:
        """Batch embedding calls at EMBED_BATCH_SIZE chunks per request with retry.

        Args:
            texts: List of texts to embed.
            model: Override embedding model name.
            input_type: 'passage' for indexing, 'query' for search queries.
                        Required by asymmetric models like nv-embedqa-e5-v5.
        """
        model = model or self._settings.nvidia_embed_model
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.EMBED_BATCH_SIZE):
            batch = texts[i : i + self.EMBED_BATCH_SIZE]
            response = self._call_with_retry(
                lambda b=batch: self._client.embeddings.create(
                    model=model, input=b, extra_body={"input_type": input_type}
                )
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings

    def _call_with_retry(self, fn):
        """Exponential backoff with jitter on 429/504, up to MAX_RETRIES within TIMEOUT."""
        start = time.time()
        for attempt in range(self.MAX_RETRIES):
            try:
                return fn()
            except (openai.RateLimitError, openai.APIStatusError) as e:
                # Only retry on 429 and 504
                status = getattr(e, "status_code", None)
                if status not in (429, 504) and isinstance(e, openai.APIStatusError):
                    raise
                elapsed = time.time() - start
                if elapsed >= self.TIMEOUT or attempt == self.MAX_RETRIES - 1:
                    raise
                delay = self.BASE_DELAY * (2**attempt) + random.uniform(0, 1)
                remaining = self.TIMEOUT - elapsed
                time.sleep(min(delay, remaining))
        raise RuntimeError("Max retries exceeded")
