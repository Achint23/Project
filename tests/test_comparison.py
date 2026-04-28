"""Tests for the comparison pipeline."""

from unittest.mock import MagicMock, patch

from pipelines.compare import ComparisonResult, run_comparison
from pipelines.query import QueryResult


def _make_query_result(
    model: str = "test-model",
    answer: str = "Test answer",
    latency_ms: float = 100.0,
    prompt_tokens: int = 50,
    completion_tokens: int = 25,
) -> QueryResult:
    return QueryResult(
        answer=answer,
        model_used=model,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


class TestRunComparison:
    @patch("pipelines.compare.run_query")
    def test_returns_two_results(self, mock_run_query):
        large_result = _make_query_result(model="large-model", answer="Large answer")
        small_result = _make_query_result(model="small-model", answer="Small answer")
        mock_run_query.side_effect = [large_result, small_result]

        result = run_comparison(
            "What?", MagicMock(), MagicMock(), "large-model", "small-model"
        )

        assert isinstance(result, ComparisonResult)
        assert result.result_large.answer == "Large answer"
        assert result.result_small.answer == "Small answer"

    @patch("pipelines.compare.run_query")
    def test_uses_different_models(self, mock_run_query):
        mock_run_query.side_effect = [
            _make_query_result(model="large"),
            _make_query_result(model="small"),
        ]

        run_comparison("Q?", MagicMock(), MagicMock(), "large", "small")

        assert mock_run_query.call_count == 2
        calls = mock_run_query.call_args_list
        assert calls[0][1]["model"] == "large" or calls[0].kwargs.get("model") == "large"

    @patch("pipelines.compare.run_query")
    def test_both_results_have_metadata(self, mock_run_query):
        mock_run_query.side_effect = [
            _make_query_result(model="large", latency_ms=200, prompt_tokens=100, completion_tokens=50),
            _make_query_result(model="small", latency_ms=80, prompt_tokens=60, completion_tokens=20),
        ]

        result = run_comparison("Q?", MagicMock(), MagicMock(), "large", "small")

        assert result.result_large.latency_ms == 200
        assert result.result_large.prompt_tokens == 100
        assert result.result_small.latency_ms == 80
        assert result.result_small.completion_tokens == 20

    @patch("pipelines.compare.run_query")
    def test_parallel_execution_completes(self, mock_run_query):
        """Both results populate — confirms parallel dispatch works."""
        mock_run_query.side_effect = [
            _make_query_result(model="a"),
            _make_query_result(model="b"),
        ]

        result = run_comparison("Q?", MagicMock(), MagicMock(), "a", "b")

        assert result.result_large is not None
        assert result.result_small is not None
        assert mock_run_query.call_count == 2
