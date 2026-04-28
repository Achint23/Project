"""Tests for the pure-function model router."""

from routers.model_router import RouteDecision, TaskType, route

LARGE = "meta/llama-3.1-70b-instruct"
SMALL = "meta/llama-3.1-8b-instruct"


def test_graph_extract_always_large():
    """Graph extraction always routes to the large model."""
    decision = route(TaskType.GRAPH_EXTRACT, LARGE, SMALL, doc_length=100, chunk_count=2)
    assert decision.model == LARGE


def test_large_doc_uses_large_model():
    """Documents over 10,000 chars route to the large model."""
    decision = route(TaskType.QA, LARGE, SMALL, doc_length=15000, chunk_count=5)
    assert decision.model == LARGE


def test_many_chunks_uses_large_model():
    """More than 15 chunks routes to the large model."""
    decision = route(TaskType.SUMMARY, LARGE, SMALL, doc_length=5000, chunk_count=20)
    assert decision.model == LARGE


def test_short_qa_uses_route_model():
    """Short Q&A routes to the smaller model."""
    decision = route(TaskType.QA, LARGE, SMALL, doc_length=3000, chunk_count=5)
    assert decision.model == SMALL


def test_short_summary_uses_route_model():
    """Short summary routes to the smaller model."""
    decision = route(TaskType.SUMMARY, LARGE, SMALL, doc_length=5000, chunk_count=10)
    assert decision.model == SMALL


def test_reason_is_nonempty_string():
    """Every route call returns a non-empty reason."""
    for task in TaskType:
        decision = route(task, LARGE, SMALL, doc_length=500, chunk_count=3)
        assert isinstance(decision.reason, str)
        assert len(decision.reason) > 0


def test_model_names_come_from_params():
    """Returned model matches injected param, not a hardcoded value."""
    custom_large = "custom/large-model"
    custom_small = "custom/small-model"

    decision_large = route(TaskType.GRAPH_EXTRACT, custom_large, custom_small)
    assert decision_large.model == custom_large

    decision_small = route(TaskType.QA, custom_large, custom_small, doc_length=100, chunk_count=2)
    assert decision_small.model == custom_small


def test_boundary_doc_length_10000():
    """Exactly 10,000 chars does NOT trigger large model (> not >=)."""
    decision = route(TaskType.QA, LARGE, SMALL, doc_length=10000, chunk_count=5)
    assert decision.model == SMALL


def test_boundary_chunk_count_15():
    """Exactly 15 chunks does NOT trigger large model (> not >=)."""
    decision = route(TaskType.QA, LARGE, SMALL, doc_length=5000, chunk_count=15)
    assert decision.model == SMALL
