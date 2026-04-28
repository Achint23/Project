"""Unit tests for core/vectorstore.py."""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestVectorStoreCreatesCollection:
    @patch("core.vectorstore.chromadb")
    def test_creates_collection_with_metadata(self, mock_chromadb):
        """VectorStore creates a 'documents' collection with correct metadata."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_embedder = MagicMock()
        mock_embedder.model = "nvidia/nv-embedqa-e5-v5"
        mock_embedder.dim = 1024

        from core.vectorstore import VectorStore
        vs = VectorStore(persist_path="test_chroma", embedder=mock_embedder)

        mock_client.get_or_create_collection.assert_called_once_with(
            name="documents",
            metadata={
                "embedding_model": "nvidia/nv-embedqa-e5-v5",
                "embedding_dim": 1024,
                "hnsw:space": "cosine",
            },
        )


class TestVectorStoreValidateModel:
    @patch("core.vectorstore.chromadb")
    def test_validate_model_match(self, mock_chromadb):
        """validate_model() does not raise when model matches."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_collection = MagicMock()
        mock_collection.metadata = {
            "embedding_model": "nvidia/nv-embedqa-e5-v5",
            "embedding_dim": 1024,
        }
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_embedder = MagicMock()
        mock_embedder.model = "nvidia/nv-embedqa-e5-v5"
        mock_embedder.dim = 1024

        from core.vectorstore import VectorStore
        vs = VectorStore(persist_path="test_chroma", embedder=mock_embedder)
        vs.validate_model()  # Should not raise

    @patch("core.vectorstore.chromadb")
    def test_validate_model_mismatch(self, mock_chromadb):
        """validate_model() raises RuntimeError on model mismatch."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_collection = MagicMock()
        mock_collection.metadata = {
            "embedding_model": "old-model",
            "embedding_dim": 1024,
        }
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_embedder = MagicMock()
        mock_embedder.model = "nvidia/nv-embedqa-e5-v5"
        mock_embedder.dim = 1024

        from core.vectorstore import VectorStore
        vs = VectorStore(persist_path="test_chroma", embedder=mock_embedder)

        with pytest.raises(RuntimeError, match="old-model"):
            vs.validate_model()


class TestVectorStoreAdd:
    @patch("core.vectorstore.chromadb")
    def test_add_chunks(self, mock_chromadb):
        """add() calls embed and collection.add with correct args."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_embedder = MagicMock()
        mock_embedder.model = "nvidia/nv-embedqa-e5-v5"
        mock_embedder.dim = 1024
        mock_embedder.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        from core.vectorstore import VectorStore
        vs = VectorStore(persist_path="test_chroma", embedder=mock_embedder)

        chunks = [
            {"text": "chunk1", "page_num": 1, "chunk_type": "text", "chunk_index": 0},
            {"text": "chunk2", "page_num": 2, "chunk_type": "table", "chunk_index": 1},
        ]
        vs.add(chunks, doc_id="doc1")

        mock_embedder.embed.assert_called_once_with(["chunk1", "chunk2"])
        mock_collection.add.assert_called_once()
        call_kwargs = mock_collection.add.call_args
        assert call_kwargs[1]["ids"] == ["doc1_chunk_0", "doc1_chunk_1"]
        assert call_kwargs[1]["documents"] == ["chunk1", "chunk2"]
        assert call_kwargs[1]["metadatas"][0]["doc_id"] == "doc1"
        assert call_kwargs[1]["metadatas"][1]["chunk_type"] == "table"


class TestVectorStoreQuery:
    @patch("core.vectorstore.chromadb")
    def test_query_with_doc_filter(self, mock_chromadb):
        """query() passes where filter when doc_id is provided."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_collection = MagicMock()
        mock_collection.query.return_value = {"ids": [["id1"]], "documents": [["text1"]]}
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_embedder = MagicMock()
        mock_embedder.model = "nvidia/nv-embedqa-e5-v5"
        mock_embedder.dim = 1024
        mock_embedder.embed_single.return_value = [0.1, 0.2]

        from core.vectorstore import VectorStore
        vs = VectorStore(persist_path="test_chroma", embedder=mock_embedder)
        vs.query("test query", doc_id="test_doc")

        mock_collection.query.assert_called_once()
        call_kwargs = mock_collection.query.call_args
        assert call_kwargs[1]["where"] == {"doc_id": "test_doc"}


class TestVectorStoreDelete:
    @patch("core.vectorstore.chromadb")
    def test_delete_by_doc(self, mock_chromadb):
        """delete_by_doc() calls collection.delete with correct where."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_embedder = MagicMock()
        mock_embedder.model = "nvidia/nv-embedqa-e5-v5"
        mock_embedder.dim = 1024

        from core.vectorstore import VectorStore
        vs = VectorStore(persist_path="test_chroma", embedder=mock_embedder)
        vs.delete_by_doc("doc1")

        mock_collection.delete.assert_called_once_with(where={"doc_id": "doc1"})


class TestVectorStoreDocIdFilter:
    """IDX-05: Verify doc_id filtering returns only matching documents."""

    @patch("core.vectorstore.chromadb")
    def test_query_with_doc_id_filter(self, mock_chromadb):
        """query(doc_id='doc_a') only returns chunks from doc_a."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_collection = MagicMock()
        # Simulate filtered result — only doc_a chunks
        mock_collection.query.return_value = {
            "ids": [["doc_a_chunk_0", "doc_a_chunk_1"]],
            "documents": [["text from a1", "text from a2"]],
            "metadatas": [[{"doc_id": "doc_a"}, {"doc_id": "doc_a"}]],
        }
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_embedder = MagicMock()
        mock_embedder.model = "nvidia/nv-embedqa-e5-v5"
        mock_embedder.dim = 1024
        mock_embedder.embed_single.return_value = [0.1, 0.2]

        from core.vectorstore import VectorStore

        vs = VectorStore(persist_path="test_chroma", embedder=mock_embedder)
        result = vs.query("test query", doc_id="doc_a")

        # Verify where filter was passed
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs["where"] == {"doc_id": "doc_a"}

        # Verify results contain only doc_a
        for meta in result["metadatas"][0]:
            assert meta["doc_id"] == "doc_a"

    @patch("core.vectorstore.chromadb")
    def test_query_without_doc_id_no_filter(self, mock_chromadb):
        """query() without doc_id passes where=None (no filtering)."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["doc_a_chunk_0", "doc_b_chunk_0"]],
            "documents": [["text a", "text b"]],
            "metadatas": [[{"doc_id": "doc_a"}, {"doc_id": "doc_b"}]],
        }
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_embedder = MagicMock()
        mock_embedder.model = "nvidia/nv-embedqa-e5-v5"
        mock_embedder.dim = 1024
        mock_embedder.embed_single.return_value = [0.1, 0.2]

        from core.vectorstore import VectorStore

        vs = VectorStore(persist_path="test_chroma", embedder=mock_embedder)
        result = vs.query("test query")

        # Verify no where filter
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs["where"] is None

        # Results may contain mixed doc_ids
        doc_ids = {m["doc_id"] for m in result["metadatas"][0]}
        assert "doc_a" in doc_ids
        assert "doc_b" in doc_ids
