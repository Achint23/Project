"""Thin embedding wrapper over NIMClient.embed()."""

from core.config import Settings, get_settings
from core.llm_client import NIMClient


class Embedder:
    """Binds embedding model config and delegates to NIMClient."""

    def __init__(self, nim_client: NIMClient | None = None, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._nim_client = nim_client or NIMClient(self._settings)
        self.model = self._settings.nvidia_embed_model
        self.dim = 1024  # nv-embedqa-e5-v5 output dimension

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        """Embed a batch of texts. Retry/batching handled by NIMClient.

        Args:
            texts: List of texts to embed.
            input_type: 'passage' for indexing, 'query' for search queries.
        """
        return self._nim_client.embed(texts, model=self.model, input_type=input_type)

    def embed_single(self, text: str, input_type: str = "query") -> list[float]:
        """Embed a single text and return its vector.

        Default input_type is 'query' since single embeds are typically search queries.
        """
        return self.embed([text], input_type=input_type)[0]
