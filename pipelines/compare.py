"""Parallel comparison pipeline: run the same question through two models side-by-side."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from core.llm_client import NIMClient
from core.vectorstore import VectorStore
from pipelines.query import QueryResult, run_query


@dataclass
class ComparisonResult:
    """Side-by-side results from two models."""

    result_large: QueryResult
    result_small: QueryResult


def run_comparison(
    question: str,
    vectorstore: VectorStore,
    nim_client: NIMClient,
    large_model: str,
    small_model: str,
    n_results: int = 5,
    doc_id: str | None = None,
) -> ComparisonResult:
    """Run the same question through two models in parallel.

    Both calls use identical inputs (prompt, chunks, temperature).
    Only the model differs.
    """

    async def _run_parallel() -> ComparisonResult:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as pool:
            large_future = loop.run_in_executor(
                pool,
                lambda: run_query(
                    question, vectorstore, nim_client,
                    n_results=n_results, doc_id=doc_id, model=large_model,
                ),
            )
            small_future = loop.run_in_executor(
                pool,
                lambda: run_query(
                    question, vectorstore, nim_client,
                    n_results=n_results, doc_id=doc_id, model=small_model,
                ),
            )
            result_large, result_small = await asyncio.gather(
                large_future, small_future
            )
        return ComparisonResult(result_large=result_large, result_small=result_small)

    return asyncio.run(_run_parallel())
