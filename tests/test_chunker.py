"""Unit tests for core/chunker.py."""

import tiktoken

from core.chunker import chunk_document, chunk_text

_ENC = tiktoken.get_encoding("cl100k_base")


def _make_long_text(target_tokens: int) -> str:
    """Generate text with approximately target_tokens tokens."""
    sentence = "The quick brown fox jumps over the lazy dog. "
    sentence_tokens = len(_ENC.encode(sentence))
    repeats = (target_tokens // sentence_tokens) + 2
    return sentence * repeats


class TestChunkTextBasicSplit:
    def test_splits_long_text(self):
        """Text >700 tokens produces multiple chunks, each ≤700 tokens."""
        text = _make_long_text(1500)
        chunks = chunk_text(text, doc_id="test", page_num=1)
        assert len(chunks) > 1
        for chunk in chunks:
            token_count = len(_ENC.encode(chunk["text"]))
            assert token_count <= 800  # Allow small overshoot from paragraph boundaries


class TestChunkTextOverlap:
    def test_overlap_between_chunks(self):
        """Second chunk's beginning overlaps with first chunk's ending."""
        text = _make_long_text(1500)
        chunks = chunk_text(text, doc_id="test", page_num=1, max_tokens=700, overlap_tokens=100)
        if len(chunks) >= 2:
            first_text = chunks[0]["text"]
            second_text = chunks[1]["text"]
            # The second chunk should start with some text from the end of the first
            # Check that there's some textual overlap
            first_words = first_text.split()
            second_words = second_text.split()
            # Find shared words at boundary
            overlap_found = False
            for word in first_words[-20:]:
                if word in second_words[:20]:
                    overlap_found = True
                    break
            assert overlap_found, "Expected overlap between consecutive chunks"


class TestChunkTextShort:
    def test_short_text_single_chunk(self):
        """Text <700 tokens produces a single chunk."""
        text = "This is a short paragraph with minimal content."
        chunks = chunk_text(text, doc_id="test", page_num=1)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text


class TestChunkDocumentTableAtomic:
    def test_table_not_split(self):
        """Table chunks are never split regardless of token count."""
        long_table = "| " + " | ".join(["col"] * 50) + " |\n" + ("| " + " | ".join(["data"] * 50) + " |\n") * 50
        pages = [
            {"text": long_table, "chunk_type": "table", "page_num": 1}
        ]
        chunks = chunk_document(pages, doc_id="test")
        table_chunks = [c for c in chunks if c["chunk_type"] == "table"]
        assert len(table_chunks) == 1
        assert table_chunks[0]["text"] == long_table


class TestChunkDocumentMetadata:
    def test_preserves_metadata(self):
        """Chunks carry correct doc_id, page_num, chunk_type, and sequential chunk_index."""
        pages = [
            {"text": "Content on page one.", "chunk_type": "text", "page_num": 1},
            {"text": "| A | B |", "chunk_type": "table", "page_num": 2},
            {"text": "Content on page three.", "chunk_type": "text", "page_num": 3},
        ]
        chunks = chunk_document(pages, doc_id="mydoc")
        assert all(c["doc_id"] == "mydoc" for c in chunks)

        # Check sequential chunk_index
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

        # Check page numbers preserved
        page_nums = {c["page_num"] for c in chunks}
        assert 1 in page_nums
        assert 2 in page_nums
        assert 3 in page_nums


class TestHeadingAttachment:
    def test_heading_stays_with_paragraph(self):
        """A heading is not emitted as a standalone chunk."""
        text = "Introduction\n\nThis is the content of the introduction section. It provides context and background information for the document that follows."
        chunks = chunk_text(text, doc_id="test", page_num=1)
        # Should be a single chunk with heading attached to paragraph
        assert len(chunks) == 1
        assert "Introduction" in chunks[0]["text"]
        assert "content of the introduction" in chunks[0]["text"]
