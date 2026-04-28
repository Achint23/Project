"""Unit tests for pipelines/query.py."""

from unittest.mock import MagicMock, patch

import pytest

from core.retriever import RetrievedChunk
from pipelines.query import (
    QueryResult,
    _format_context,
    _parse_citations,
    _validate_citations,
    run_query,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_chunk(
    chunk_id: str = "abc123_chunk_0",
    text: str = "Some chunk text",
    doc_id: str = "docA",
    page_num: int = 1,
    chunk_type: str = "text",
    distance: float = 0.1,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        doc_id=doc_id,
        page_num=page_num,
        chunk_type=chunk_type,
        distance=distance,
    )


SAMPLE_CHUNKS = [
    _make_chunk("abc123_chunk_0", "First chunk content", page_num=1, distance=0.1),
    _make_chunk("def456_chunk_1", "Second chunk content", page_num=2, chunk_type="heading", distance=0.3),
    _make_chunk("abc123_chunk_2", "Third chunk content", page_num=3, distance=0.5),
]


def _mock_llm_response(content: str, prompt_tokens: int = 0, completion_tokens: int = 0, model: str = "") -> MagicMock:
    """Create a mock ChatCompletion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    if prompt_tokens or completion_tokens:
        response.usage.prompt_tokens = prompt_tokens
        response.usage.completion_tokens = completion_tokens
        response.usage.total_tokens = prompt_tokens + completion_tokens
    else:
        response.usage = None
    response.model = model or None
    return response


# ---------------------------------------------------------------------------
# _parse_citations tests
# ---------------------------------------------------------------------------

class TestParseCitations:
    def test_extracts_valid_chunk_ids(self):
        answer = "Based on [abc123_chunk_0] and [def456_chunk_2], the answer is clear."
        result = _parse_citations(answer)
        assert result == ["abc123_chunk_0", "def456_chunk_2"]

    def test_ignores_markdown_links(self):
        answer = "See [this link](http://example.com) and [1] for details."
        result = _parse_citations(answer)
        assert result == []

    def test_ignores_numeric_brackets(self):
        answer = "Reference [1] and [page 4] are not chunk IDs."
        result = _parse_citations(answer)
        assert result == []

    def test_mixed_valid_and_invalid(self):
        answer = "Mixed [abc123_chunk_0] and [not-a-chunk] references."
        result = _parse_citations(answer)
        assert result == ["abc123_chunk_0"]

    def test_empty_answer(self):
        assert _parse_citations("") == []

    def test_no_brackets(self):
        assert _parse_citations("A plain answer with no citations.") == []

    def test_multiple_same_id(self):
        answer = "Mentioned [abc123_chunk_0] twice [abc123_chunk_0]."
        result = _parse_citations(answer)
        assert result == ["abc123_chunk_0", "abc123_chunk_0"]


# ---------------------------------------------------------------------------
# _validate_citations tests
# ---------------------------------------------------------------------------

class TestValidateCitations:
    def test_splits_valid_and_hallucinated(self):
        cited = ["a_chunk_0", "b_chunk_1"]
        retrieved = {"a_chunk_0"}
        valid, hallucinated = _validate_citations(cited, retrieved)
        assert valid == ["a_chunk_0"]
        assert hallucinated == ["b_chunk_1"]

    def test_all_valid(self):
        cited = ["a_chunk_0", "b_chunk_1"]
        retrieved = {"a_chunk_0", "b_chunk_1"}
        valid, hallucinated = _validate_citations(cited, retrieved)
        assert valid == ["a_chunk_0", "b_chunk_1"]
        assert hallucinated == []

    def test_all_hallucinated(self):
        cited = ["x_chunk_9"]
        retrieved = {"a_chunk_0"}
        valid, hallucinated = _validate_citations(cited, retrieved)
        assert valid == []
        assert hallucinated == ["x_chunk_9"]

    def test_empty_cited(self):
        valid, hallucinated = _validate_citations([], {"a_chunk_0"})
        assert valid == []
        assert hallucinated == []


# ---------------------------------------------------------------------------
# _format_context tests
# ---------------------------------------------------------------------------

class TestFormatContext:
    def test_single_chunk(self):
        chunks = [_make_chunk("abc123_chunk_0", "Hello world", page_num=1)]
        result = _format_context(chunks)
        assert "[abc123_chunk_0] (page 1):" in result
        assert "Hello world" in result

    def test_two_chunks_joined(self):
        chunks = [
            _make_chunk("abc123_chunk_0", "First text", page_num=1),
            _make_chunk("def456_chunk_1", "Second text", page_num=2),
        ]
        result = _format_context(chunks)
        assert "[abc123_chunk_0] (page 1):\nFirst text" in result
        assert "[def456_chunk_1] (page 2):\nSecond text" in result
        # Chunks separated by double newline
        assert "\n\n" in result

    def test_empty_chunks(self):
        assert _format_context([]) == ""


# ---------------------------------------------------------------------------
# run_query tests
# ---------------------------------------------------------------------------

class TestRunQuery:
    @patch("pipelines.query.retrieve")
    def test_empty_retrieval_returns_no_content_message(self, mock_retrieve):
        mock_retrieve.return_value = []
        vs = MagicMock()
        nim = MagicMock()

        result = run_query("What is X?", vs, nim)

        assert isinstance(result, QueryResult)
        assert "No relevant content found" in result.answer
        assert result.citations == []
        assert result.hallucinated_ids == []
        assert result.retrieved_chunks == []
        # LLM should NOT be called when retrieval is empty
        nim.chat.assert_not_called()

    @patch("pipelines.query._load_prompt_template")
    @patch("pipelines.query.retrieve")
    def test_successful_query_with_valid_citations(self, mock_retrieve, mock_template):
        mock_retrieve.return_value = SAMPLE_CHUNKS
        mock_template.return_value = "Context: {context}\nQuestion: {question}"

        llm_answer = "The answer is here [abc123_chunk_0] and also [def456_chunk_1]."
        nim = MagicMock()
        nim.chat.return_value = _mock_llm_response(llm_answer)
        vs = MagicMock()

        result = run_query("What is the answer?", vs, nim)

        assert isinstance(result, QueryResult)
        assert result.answer == llm_answer
        assert len(result.citations) == 2
        assert result.citations[0]["chunk_id"] == "abc123_chunk_0"
        assert result.citations[0]["page_num"] == 1
        assert result.citations[1]["chunk_id"] == "def456_chunk_1"
        assert result.citations[1]["chunk_type"] == "heading"
        assert result.hallucinated_ids == []
        assert len(result.retrieved_chunks) == 3

    @patch("pipelines.query._load_prompt_template")
    @patch("pipelines.query.retrieve")
    def test_hallucinated_citations_detected(self, mock_retrieve, mock_template):
        mock_retrieve.return_value = SAMPLE_CHUNKS
        mock_template.return_value = "Context: {context}\nQuestion: {question}"

        # LLM cites a chunk ID that was NOT retrieved
        llm_answer = "Based on [abc123_chunk_0] and [face99_chunk_7], the answer is..."
        nim = MagicMock()
        nim.chat.return_value = _mock_llm_response(llm_answer)
        vs = MagicMock()

        result = run_query("Question?", vs, nim)

        assert len(result.citations) == 1
        assert result.citations[0]["chunk_id"] == "abc123_chunk_0"
        assert result.hallucinated_ids == ["face99_chunk_7"]

    @patch("pipelines.query._load_prompt_template")
    @patch("pipelines.query.retrieve")
    def test_citation_details_populated(self, mock_retrieve, mock_template):
        mock_retrieve.return_value = SAMPLE_CHUNKS
        mock_template.return_value = "Context: {context}\nQuestion: {question}"

        llm_answer = "See [abc123_chunk_0] for details."
        nim = MagicMock()
        nim.chat.return_value = _mock_llm_response(llm_answer)
        vs = MagicMock()

        result = run_query("What?", vs, nim)

        assert len(result.citations) == 1
        cite = result.citations[0]
        assert cite["chunk_id"] == "abc123_chunk_0"
        assert cite["text"] == "First chunk content"
        assert cite["page_num"] == 1
        assert cite["chunk_type"] == "text"

    @patch("pipelines.query._load_prompt_template")
    @patch("pipelines.query.retrieve")
    def test_llm_called_with_correct_params(self, mock_retrieve, mock_template):
        mock_retrieve.return_value = SAMPLE_CHUNKS
        mock_template.return_value = "Context: {context}\nQuestion: {question}"

        nim = MagicMock()
        nim.chat.return_value = _mock_llm_response("answer")
        vs = MagicMock()

        run_query("My question", vs, nim)

        nim.chat.assert_called_once()
        call_kwargs = nim.chat.call_args
        assert call_kwargs[1]["temperature"] == 0.3
        assert call_kwargs[1]["max_tokens"] == 1024
        messages = call_kwargs[1]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "My question" in messages[0]["content"]

    @patch("pipelines.query.retrieve")
    def test_doc_id_forwarded_to_retrieve(self, mock_retrieve):
        mock_retrieve.return_value = []
        vs = MagicMock()
        nim = MagicMock()

        run_query("Q?", vs, nim, doc_id="specific_doc")

        mock_retrieve.assert_called_once_with(
            vs, "Q?", n_results=5, doc_id="specific_doc"
        )

    @patch("pipelines.query.retrieve")
    def test_n_results_forwarded_to_retrieve(self, mock_retrieve):
        mock_retrieve.return_value = []
        vs = MagicMock()
        nim = MagicMock()

        run_query("Q?", vs, nim, n_results=3)

        mock_retrieve.assert_called_once_with(
            vs, "Q?", n_results=3, doc_id=None
        )

    @patch("pipelines.query._load_prompt_template")
    @patch("pipelines.query.retrieve")
    def test_duplicate_hallucinated_ids_deduplicated(self, mock_retrieve, mock_template):
        mock_retrieve.return_value = SAMPLE_CHUNKS
        mock_template.return_value = "Context: {context}\nQuestion: {question}"

        # Same hallucinated ID cited twice
        llm_answer = "See [face00_chunk_9] and again [face00_chunk_9]."
        nim = MagicMock()
        nim.chat.return_value = _mock_llm_response(llm_answer)
        vs = MagicMock()

        result = run_query("Q?", vs, nim)

        assert result.hallucinated_ids == ["face00_chunk_9"]


# ---------------------------------------------------------------------------
# Metadata extraction tests
# ---------------------------------------------------------------------------

class TestRunQueryMetadata:
    @patch("pipelines.query._load_prompt_template")
    @patch("pipelines.query.retrieve")
    def test_run_query_returns_metadata(self, mock_retrieve, mock_template):
        mock_retrieve.return_value = SAMPLE_CHUNKS
        mock_template.return_value = "Context: {context}\nQuestion: {question}"

        nim = MagicMock()
        nim.chat.return_value = _mock_llm_response(
            "Answer [abc123_chunk_0].", prompt_tokens=100, completion_tokens=50, model="test-model"
        )
        vs = MagicMock()

        result = run_query("What?", vs, nim)

        assert result.model_used == "test-model"
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 50
        assert result.latency_ms > 0

    @patch("pipelines.query._load_prompt_template")
    @patch("pipelines.query.retrieve")
    def test_run_query_with_explicit_model(self, mock_retrieve, mock_template):
        mock_retrieve.return_value = SAMPLE_CHUNKS
        mock_template.return_value = "Context: {context}\nQuestion: {question}"

        nim = MagicMock()
        nim.chat.return_value = _mock_llm_response("Answer.", prompt_tokens=10, completion_tokens=5, model="custom-model")
        vs = MagicMock()

        run_query("What?", vs, nim, model="custom-model")

        call_kwargs = nim.chat.call_args[1]
        assert call_kwargs["model"] == "custom-model"

    @patch("pipelines.query._load_prompt_template")
    @patch("pipelines.query.retrieve")
    def test_run_query_handles_missing_usage(self, mock_retrieve, mock_template):
        mock_retrieve.return_value = SAMPLE_CHUNKS
        mock_template.return_value = "Context: {context}\nQuestion: {question}"

        nim = MagicMock()
        nim.chat.return_value = _mock_llm_response("Answer.")  # usage=None
        vs = MagicMock()

        result = run_query("What?", vs, nim)

        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
