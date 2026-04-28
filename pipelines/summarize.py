"""Summarization pipeline: retrieve all chunks → direct or map-reduce summarize."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import tiktoken

from core.llm_client import NIMClient
from core.vectorstore import VectorStore

logger = logging.getLogger(__name__)

TOKEN_BUDGET = 6000

_encoding = tiktoken.encoding_for_model("gpt-4")


@dataclass
class SummaryResult:
    """Structured result from a summarization run."""

    summary: str
    doc_id: str
    chunk_count: int
    method: str  # "direct" or "map_reduce"
    error: str | None = None


def _count_tokens(text: str) -> int:
    """Count tokens using cl100k_base encoding."""
    return len(_encoding.encode(text))


def _load_prompt(name: str) -> str:
    """Read a prompt template from the prompts/ directory."""
    return Path(f"prompts/{name}").read_text(encoding="utf-8")


def _summarize_direct(text: str, nim_client: NIMClient) -> str:
    """Summarize text directly using the reduce/summary prompt."""
    prompt = _load_prompt("summary_reduce.txt").format(text=text)
    response = nim_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _map_reduce(chunks: list[dict], nim_client: NIMClient) -> str:
    """Summarize via map-reduce: summarize each chunk, then combine."""
    map_prompt_template = _load_prompt("summary_map.txt")

    # Map step: summarize each chunk individually
    partials: list[str] = []
    for chunk in chunks:
        prompt = map_prompt_template.format(text=chunk["text"])
        response = nim_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        partials.append(response.choices[0].message.content)

    # Reduce step: combine all partial summaries
    combined = "\n\n---\n\n".join(partials)
    reduce_prompt = _load_prompt("summary_reduce.txt").format(text=combined)
    response = nim_client.chat(
        messages=[{"role": "user", "content": reduce_prompt}],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def run_summarize(
    doc_id: str,
    vectorstore: VectorStore,
    nim_client: NIMClient,
) -> SummaryResult:
    """Run the summarization pipeline for a document.

    Uses direct summarization if total tokens fit within TOKEN_BUDGET,
    otherwise falls back to map-reduce.
    """
    try:
        chunks = vectorstore.get_all_by_doc(doc_id)
        if not chunks:
            return SummaryResult(
                summary="",
                doc_id=doc_id,
                chunk_count=0,
                method="direct",
                error="No chunks found for document.",
            )

        total_text = "\n\n".join(c["text"] for c in chunks)
        total_tokens = _count_tokens(total_text)

        if total_tokens <= TOKEN_BUDGET:
            summary = _summarize_direct(total_text, nim_client)
            method = "direct"
        else:
            summary = _map_reduce(chunks, nim_client)
            method = "map_reduce"

        return SummaryResult(
            summary=summary,
            doc_id=doc_id,
            chunk_count=len(chunks),
            method=method,
        )
    except Exception as exc:
        logger.exception("Summarization failed for doc_id=%s", doc_id)
        return SummaryResult(
            summary="",
            doc_id=doc_id,
            chunk_count=0,
            method="direct",
            error=str(exc),
        )
