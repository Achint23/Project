"""Query pipeline: embed → retrieve → prompt → LLM → parse → validate citations."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from core.llm_client import NIMClient
from core.retriever import RetrievedChunk, retrieve
from core.vectorstore import VectorStore

_CHUNK_ID_RE = re.compile(r"^[a-f0-9]+_chunk_\d+$")


@dataclass
class QueryResult:
    """Structured result from a Q&A query."""

    answer: str
    citations: list[dict] = field(default_factory=list)
    hallucinated_ids: list[str] = field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    route_reason: str = ""


def _load_prompt_template() -> str:
    """Read the QA prompt template from disk."""
    return Path("prompts/qa.txt").read_text(encoding="utf-8")


def _format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into the context block for the prompt."""
    parts = []
    for chunk in chunks:
        parts.append(f"[{chunk.chunk_id}] (page {chunk.page_num}):\n{chunk.text}")
    return "\n\n".join(parts)


def _parse_citations(answer: str) -> list[str]:
    """Extract valid chunk IDs from bracketed references in the answer.

    Filters out markdown links, numeric references like [1], and other
    non-chunk-ID bracketed text.
    """
    raw = re.findall(r"\[([^\[\]]+)\]", answer)
    return [ref for ref in raw if _CHUNK_ID_RE.match(ref)]


def _validate_citations(
    cited_ids: list[str], retrieved_ids: set[str]
) -> tuple[list[str], list[str]]:
    """Split cited IDs into valid (in retrieval set) and hallucinated."""
    valid = [cid for cid in cited_ids if cid in retrieved_ids]
    hallucinated = [cid for cid in cited_ids if cid not in retrieved_ids]
    return valid, hallucinated


def run_query(
    question: str,
    vectorstore: VectorStore,
    nim_client: NIMClient,
    n_results: int = 5,
    doc_id: str | None = None,
    model: str | None = None,
) -> QueryResult:
    """Run the full Q&A pipeline: retrieve → prompt → LLM → parse → validate.

    Args:
        question: User's natural-language question.
        vectorstore: VectorStore instance for retrieval.
        nim_client: NIMClient for LLM chat completion.
        n_results: Number of chunks to retrieve (default 5).
        doc_id: Optional filter to a specific document.

    Returns:
        QueryResult with answer, validated citations, hallucinated IDs,
        and retrieved chunks.
    """
    chunks = retrieve(vectorstore, question, n_results=n_results, doc_id=doc_id)

    if not chunks:
        return QueryResult(
            answer="No relevant content found. Please make sure documents are indexed."
        )

    template = _load_prompt_template()
    prompt = template.format(context=_format_context(chunks), question=question)

    t0 = time.perf_counter()
    response = nim_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
        model=model,
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    answer = response.choices[0].message.content

    usage = response.usage
    p_tokens = usage.prompt_tokens if usage else 0
    c_tokens = usage.completion_tokens if usage else 0
    model_used = response.model or ""

    cited_ids = _parse_citations(answer)
    retrieved_ids = {c.chunk_id for c in chunks}
    valid_ids, hallucinated_ids = _validate_citations(cited_ids, retrieved_ids)

    # Build citation detail dicts for valid IDs
    chunk_lookup = {c.chunk_id: c for c in chunks}
    citations = [
        {
            "chunk_id": cid,
            "text": chunk_lookup[cid].text,
            "page_num": chunk_lookup[cid].page_num,
            "chunk_type": chunk_lookup[cid].chunk_type,
        }
        for cid in valid_ids
        if cid in chunk_lookup
    ]

    # Deduplicate hallucinated IDs while preserving order
    seen = set()
    deduped_hallucinated = []
    for hid in hallucinated_ids:
        if hid not in seen:
            seen.add(hid)
            deduped_hallucinated.append(hid)

    return QueryResult(
        answer=answer,
        citations=citations,
        hallucinated_ids=deduped_hallucinated,
        retrieved_chunks=chunks,
        model_used=model_used,
        prompt_tokens=p_tokens,
        completion_tokens=c_tokens,
        latency_ms=latency_ms,
    )
