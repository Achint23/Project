"""Retriever module — top-k retrieval with anti-'lost in the middle' reordering."""

from dataclasses import dataclass

from core.vectorstore import VectorStore


@dataclass
class RetrievedChunk:
    """A single retrieved chunk with metadata and similarity distance."""

    chunk_id: str
    text: str
    doc_id: str
    page_num: int
    chunk_type: str
    distance: float


def reorder_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Reorder chunks so the highest-scored chunk appears first AND last.

    ChromaDB returns results sorted by ascending distance (cosine space),
    so index 0 is the best match.  Duplicating it at the end combats the
    "lost in the middle" phenomenon in long-context LLM prompts.
    """
    if len(chunks) <= 1:
        return list(chunks)
    return list(chunks) + [chunks[0]]


def retrieve(
    vectorstore: VectorStore,
    query_text: str,
    n_results: int = 5,
    doc_id: str | None = None,
) -> list[RetrievedChunk]:
    """Retrieve and reorder chunks from the vector store.

    Args:
        vectorstore: VectorStore instance to query.
        query_text: User's natural-language question.
        n_results: Number of results to fetch (default 5).
        doc_id: Optional filter to a specific document.

    Returns:
        List of RetrievedChunk objects, reordered (best first AND last).
    """
    raw = vectorstore.query(query_text, n_results=n_results, doc_id=doc_id)

    if not raw["ids"] or not raw["ids"][0]:
        return []

    chunks = [
        RetrievedChunk(
            chunk_id=cid,
            text=doc,
            doc_id=meta["doc_id"],
            page_num=meta["page_num"],
            chunk_type=meta.get("chunk_type", "text"),
            distance=dist,
        )
        for cid, doc, meta, dist in zip(
            raw["ids"][0],
            raw["documents"][0],
            raw["metadatas"][0],
            raw["distances"][0],
        )
    ]

    return reorder_chunks(chunks)
