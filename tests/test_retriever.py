"""Unit tests for core/retriever.py."""

from unittest.mock import MagicMock

import pytest

from core.retriever import RetrievedChunk, reorder_chunks, retrieve


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_chunk(chunk_id: str = "docA_chunk_0", distance: float = 0.1) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=f"text for {chunk_id}",
        doc_id="docA",
        page_num=1,
        chunk_type="text",
        distance=distance,
    )


def _mock_vectorstore(raw_result: dict) -> MagicMock:
    vs = MagicMock()
    vs.query.return_value = raw_result
    return vs


SAMPLE_RAW = {
    "ids": [["docA_chunk_0", "docA_chunk_1", "docA_chunk_2"]],
    "documents": [["text0", "text1", "text2"]],
    "metadatas": [[
        {"doc_id": "docA", "page_num": 1, "chunk_type": "text", "chunk_index": 0},
        {"doc_id": "docA", "page_num": 1, "chunk_type": "text", "chunk_index": 1},
        {"doc_id": "docA", "page_num": 2, "chunk_type": "heading", "chunk_index": 2},
    ]],
    "distances": [[0.1, 0.3, 0.5]],
}

EMPTY_RAW = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
EMPTY_RAW_NO_OUTER = {"ids": [], "documents": [], "metadatas": [], "distances": []}


# ---------------------------------------------------------------------------
# reorder_chunks tests
# ---------------------------------------------------------------------------

class TestReorderChunks:
    def test_empty_list(self):
        assert reorder_chunks([]) == []

    def test_single_chunk_no_duplication(self):
        c = _make_chunk()
        result = reorder_chunks([c])
        assert len(result) == 1
        assert result[0] is c

    def test_multi_chunks_best_first_and_last(self):
        c0 = _make_chunk("docA_chunk_0", 0.1)
        c1 = _make_chunk("docA_chunk_1", 0.3)
        c2 = _make_chunk("docA_chunk_2", 0.5)
        result = reorder_chunks([c0, c1, c2])
        assert len(result) == 4
        assert result[0].chunk_id == "docA_chunk_0"
        assert result[-1].chunk_id == "docA_chunk_0"
        assert result[1].chunk_id == "docA_chunk_1"
        assert result[2].chunk_id == "docA_chunk_2"

    def test_two_chunks_duplicates_first(self):
        c0 = _make_chunk("a", 0.1)
        c1 = _make_chunk("b", 0.2)
        result = reorder_chunks([c0, c1])
        assert len(result) == 3
        assert result[0].chunk_id == result[-1].chunk_id == "a"


# ---------------------------------------------------------------------------
# retrieve tests
# ---------------------------------------------------------------------------

class TestRetrieve:
    def test_empty_result_returns_empty(self):
        vs = _mock_vectorstore(EMPTY_RAW)
        assert retrieve(vs, "anything") == []

    def test_empty_outer_list_returns_empty(self):
        vs = _mock_vectorstore(EMPTY_RAW_NO_OUTER)
        assert retrieve(vs, "anything") == []

    def test_populated_result_returns_reordered_chunks(self):
        vs = _mock_vectorstore(SAMPLE_RAW)
        result = retrieve(vs, "test query")
        # 3 chunks + 1 reordered = 4
        assert len(result) == 4
        assert all(isinstance(c, RetrievedChunk) for c in result)
        # Best first AND last
        assert result[0].chunk_id == "docA_chunk_0"
        assert result[-1].chunk_id == "docA_chunk_0"

    def test_chunk_fields_populated(self):
        vs = _mock_vectorstore(SAMPLE_RAW)
        result = retrieve(vs, "test query")
        c = result[0]
        assert c.chunk_id == "docA_chunk_0"
        assert c.text == "text0"
        assert c.doc_id == "docA"
        assert c.page_num == 1
        assert c.chunk_type == "text"
        assert c.distance == 0.1

    def test_heading_chunk_type_preserved(self):
        vs = _mock_vectorstore(SAMPLE_RAW)
        result = retrieve(vs, "test query")
        assert result[2].chunk_type == "heading"
        assert result[2].page_num == 2

    def test_doc_id_filter_forwarded(self):
        vs = _mock_vectorstore(EMPTY_RAW)
        retrieve(vs, "query", doc_id="specific_doc")
        vs.query.assert_called_once_with("query", n_results=5, doc_id="specific_doc")

    def test_n_results_forwarded(self):
        vs = _mock_vectorstore(EMPTY_RAW)
        retrieve(vs, "query", n_results=3)
        vs.query.assert_called_once_with("query", n_results=3, doc_id=None)

    def test_default_args_forwarded(self):
        vs = _mock_vectorstore(EMPTY_RAW)
        retrieve(vs, "query")
        vs.query.assert_called_once_with("query", n_results=5, doc_id=None)
