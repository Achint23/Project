"""ChromaDB vector store wrapper with model validation."""

import chromadb
from chromadb.config import Settings as ChromaSettings

from core.embedder import Embedder


class VectorStore:
    """ChromaDB wrapper with add, query, delete, and model validation."""

    def __init__(self, persist_path: str = "data/chroma", embedder: Embedder | None = None):
        self._embedder = embedder or Embedder()
        self._client = chromadb.PersistentClient(
            path=persist_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """Get or create the documents collection with embedding metadata."""
        return self._client.get_or_create_collection(
            name="documents",
            metadata={
                "embedding_model": self._embedder.model,
                "embedding_dim": self._embedder.dim,
                "hnsw:space": "cosine",
            },
        )

    def validate_model(self):
        """Check that stored embedding model matches current config.

        Raises RuntimeError on mismatch.
        """
        meta = self._collection.metadata
        if not meta:
            return  # New collection — no stored metadata to check

        stored_model = meta.get("embedding_model")
        stored_dim = meta.get("embedding_dim")

        if stored_model and stored_model != self._embedder.model:
            raise RuntimeError(
                f"Collection was built with '{stored_model}' but current config "
                f"uses '{self._embedder.model}'. Delete data/chroma/ and re-ingest, "
                f"or update NVIDIA_EMBED_MODEL."
            )
        if stored_dim and int(stored_dim) != self._embedder.dim:
            raise RuntimeError(
                f"Collection was built with dim={stored_dim} but current config "
                f"uses dim={self._embedder.dim}. Delete data/chroma/ and re-ingest."
            )

    def add(self, chunks: list[dict], doc_id: str):
        """Add chunks to the collection with embeddings and metadata."""
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        embeddings = self._embedder.embed(texts)
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "page_num": c["page_num"],
                "chunk_type": c.get("chunk_type", "text"),
                "chunk_index": c.get("chunk_index", i),
            }
            for i, c in enumerate(chunks)
        ]
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def query(self, query_text: str, n_results: int = 5, doc_id: str | None = None) -> dict:
        """Query the collection by text similarity.

        Args:
            query_text: The query string.
            n_results: Number of results to return (default 5).
            doc_id: Optional filter to a specific document.

        Returns:
            Raw ChromaDB query result dict.
        """
        embedding = self._embedder.embed_single(query_text)
        where = {"doc_id": doc_id} if doc_id else None
        return self._collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where,
        )

    def delete_by_doc(self, doc_id: str):
        """Delete all chunks for a given document."""
        self._collection.delete(where={"doc_id": doc_id})

    def count(self) -> int:
        """Return total number of chunks in the collection."""
        return self._collection.count()
