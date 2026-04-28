"""Pure-function model router — no I/O, no side effects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Types of LLM tasks the router can evaluate."""

    QA = "qa"
    SUMMARY = "summary"
    GRAPH_EXTRACT = "graph_extract"


@dataclass
class RouteDecision:
    """Router output: which model to use and why."""

    model: str
    reason: str


def route(
    task: TaskType,
    settings_large_model: str,
    settings_route_model: str,
    doc_length: int = 0,
    chunk_count: int = 0,
) -> RouteDecision:
    """Decide which model to use for a given task and document signals.

    Args:
        task: The type of LLM task.
        settings_large_model: Name of the large (direct) model from config.
        settings_route_model: Name of the smaller (route) model from config.
        doc_length: Total document character count (optional signal).
        chunk_count: Number of chunks in the document (optional signal).

    Returns:
        RouteDecision with the chosen model name and human-readable reason.
    """
    if task == TaskType.GRAPH_EXTRACT:
        return RouteDecision(
            model=settings_large_model,
            reason="Graph extraction requires JSON-mode reliability — routed to large model",
        )

    if doc_length > 10_000:
        return RouteDecision(
            model=settings_large_model,
            reason=f"Document length ({doc_length:,} chars) exceeds 10,000 — routed to large model for accuracy",
        )

    if chunk_count > 15:
        return RouteDecision(
            model=settings_large_model,
            reason=f"High chunk count ({chunk_count}) exceeds 15 — routed to large model for accuracy",
        )

    return RouteDecision(
        model=settings_route_model,
        reason=f"Short {task.value} task ({doc_length:,} chars, {chunk_count} chunks) — routed to smaller model for faster response",
    )
