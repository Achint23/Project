"""Unit tests for core/embedder.py."""

from unittest.mock import MagicMock, patch

from core.embedder import Embedder


class TestEmbedder:
    def _make_embedder(self):
        """Create an Embedder with mocked NIMClient and settings."""
        mock_settings = MagicMock()
        mock_settings.nvidia_embed_model = "nvidia/nv-embedqa-e5-v5"
        mock_nim = MagicMock()
        return Embedder(nim_client=mock_nim, settings=mock_settings), mock_nim

    def test_embedder_uses_settings_model(self):
        """Embedder uses the model name from settings."""
        embedder, mock_nim = self._make_embedder()
        mock_nim.embed.return_value = [[0.1, 0.2, 0.3]]
        embedder.embed(["hello"])
        mock_nim.embed.assert_called_once_with(["hello"], model="nvidia/nv-embedqa-e5-v5", input_type="passage")

    def test_embedder_embed_delegates(self):
        """embed() returns whatever NIMClient.embed returns."""
        embedder, mock_nim = self._make_embedder()
        fake_vectors = [[0.1, 0.2], [0.3, 0.4]]
        mock_nim.embed.return_value = fake_vectors
        result = embedder.embed(["a", "b"])
        assert result == fake_vectors

    def test_embedder_embed_single(self):
        """embed_single returns the first vector from embed([text])."""
        embedder, mock_nim = self._make_embedder()
        mock_nim.embed.return_value = [[0.5, 0.6, 0.7]]
        result = embedder.embed_single("test")
        assert result == [0.5, 0.6, 0.7]
        mock_nim.embed.assert_called_once_with(["test"], model="nvidia/nv-embedqa-e5-v5", input_type="query")

    def test_embedder_dim(self):
        """Embedder dim is 1024 for nv-embedqa-e5-v5."""
        embedder, _ = self._make_embedder()
        assert embedder.dim == 1024
