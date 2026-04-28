"""Unit tests for pipelines/ingest.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipelines.ingest import (
    IngestResult,
    compute_content_hash,
    delete_document,
    ingest_document,
    is_already_indexed,
    save_upload,
)


class TestComputeContentHash:
    def test_same_bytes_same_hash(self):
        data = b"hello world"
        assert compute_content_hash(data) == compute_content_hash(data)

    def test_different_bytes_different_hash(self):
        assert compute_content_hash(b"aaa") != compute_content_hash(b"bbb")


class TestSaveUpload:
    def test_saves_to_expected_path(self, tmp_path):
        data = b"pdf-content"
        result = save_upload(data, "abc123", upload_dir=str(tmp_path))
        expected = tmp_path / "abc123.pdf"
        assert result == expected
        assert expected.exists()
        assert expected.read_bytes() == data

    def test_creates_parent_directory(self, tmp_path):
        dest = tmp_path / "nested" / "dir"
        save_upload(b"data", "xyz", upload_dir=str(dest))
        assert (dest / "xyz.pdf").exists()


class TestIsAlreadyIndexed:
    def test_returns_true_when_found(self):
        vs = MagicMock()
        vs._collection.get.return_value = {"ids": ["x"]}
        assert is_already_indexed(vs, "doc1") is True

    def test_returns_false_when_not_found(self):
        vs = MagicMock()
        vs._collection.get.return_value = {"ids": []}
        assert is_already_indexed(vs, "doc1") is False


class TestIngestDocument:
    @patch("pipelines.ingest.chunk_document")
    @patch("pipelines.ingest.extract_document")
    def test_success(self, mock_extract, mock_chunk, tmp_path):
        mock_extract.return_value = [
            {"text": "page1", "page_num": 1, "chunk_type": "text"},
            {"text": "page2", "page_num": 2, "chunk_type": "text"},
        ]
        mock_chunk.return_value = [
            {"text": "c1", "doc_id": "d", "page_num": 1, "chunk_type": "text", "chunk_index": 0},
            {"text": "c2", "doc_id": "d", "page_num": 1, "chunk_type": "text", "chunk_index": 1},
            {"text": "c3", "doc_id": "d", "page_num": 2, "chunk_type": "text", "chunk_index": 2},
        ]
        vs = MagicMock()
        vs._collection.get.return_value = {"ids": []}

        result = ingest_document(tmp_path / "test.pdf", "d", "test.pdf", vs)

        assert isinstance(result, IngestResult)
        assert result.chunk_count == 3
        assert result.page_count == 2
        assert result.already_indexed is False
        assert result.error is None
        vs.add.assert_called_once()

    def test_already_indexed(self, tmp_path):
        vs = MagicMock()
        vs._collection.get.return_value = {"ids": ["existing"]}

        result = ingest_document(tmp_path / "test.pdf", "d", "test.pdf", vs)

        assert result.already_indexed is True
        assert result.chunk_count == 0
        vs.add.assert_not_called()

    @patch("pipelines.ingest.extract_document", side_effect=RuntimeError("bad pdf"))
    def test_error_handling(self, mock_extract, tmp_path):
        vs = MagicMock()
        vs._collection.get.return_value = {"ids": []}

        result = ingest_document(tmp_path / "test.pdf", "d", "test.pdf", vs)

        assert result.error == "bad pdf"
        assert result.chunk_count == 0


class TestDeleteDocument:
    def test_deletes_vectors_and_file(self, tmp_path):
        upload_file = tmp_path / "d.pdf"
        upload_file.write_bytes(b"data")

        vs = MagicMock()
        delete_document("d", vs, upload_dir=str(tmp_path))

        vs.delete_by_doc.assert_called_once_with("d")
        assert not upload_file.exists()

    def test_deletes_vectors_when_no_file(self, tmp_path):
        vs = MagicMock()
        delete_document("d", vs, upload_dir=str(tmp_path))

        vs.delete_by_doc.assert_called_once_with("d")
