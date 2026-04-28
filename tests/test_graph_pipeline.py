"""Tests for the graph extraction pipeline."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from pipelines.graph import (
    DEDUP_THRESHOLD,
    Entity,
    GraphExtraction,
    GraphResult,
    ProcessStep,
    Relationship,
    _apply_dedup_to_graph,
    _format_pydantic_errors,
    deduplicate_entities,
    run_graph_extraction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_EXTRACTION_DICT = {
    "entities": [
        {"name": "HR Manager", "type": "ROLE", "description": "Reviews requests"},
        {"name": "LeaveTracker", "type": "SYSTEM", "description": "Sends notifications"},
    ],
    "relationships": [
        {"source": "HR Manager", "target": "LeaveTracker", "relation": "uses"},
    ],
    "process_steps": [
        {"step": 1, "description": "Review leave request", "actors": ["HR Manager"]},
    ],
    "decision_points": [
        {"condition": "Leave exceeds 5 days", "outcomes": ["Approve", "Deny"]},
    ],
    "business_rules": [
        {"rule": "Extended leave requires VP approval"},
    ],
}


def _make_mock_chat(return_text: str, prompt_tokens: int = 0, completion_tokens: int = 0, model: str = ""):
    """Create a mock chat response object."""
    msg = MagicMock()
    msg.content = return_text
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    if prompt_tokens or completion_tokens:
        response.usage.prompt_tokens = prompt_tokens
        response.usage.completion_tokens = completion_tokens
        response.usage.total_tokens = prompt_tokens + completion_tokens
    else:
        response.usage = None
    response.model = model or None
    return response


def _make_chunks(texts: list[str], doc_id: str = "doc1") -> list[dict]:
    return [
        {
            "chunk_id": f"{doc_id}_chunk_{i}",
            "text": t,
            "doc_id": doc_id,
            "page_num": i + 1,
            "chunk_type": "text",
        }
        for i, t in enumerate(texts)
    ]


# ---------------------------------------------------------------------------
# 1. Pydantic validation
# ---------------------------------------------------------------------------

class TestGraphExtractionPydanticValidation:
    def test_valid_dict_succeeds(self):
        result = GraphExtraction.model_validate(VALID_EXTRACTION_DICT)
        assert len(result.entities) == 2
        assert result.entities[0].name == "HR Manager"
        assert len(result.relationships) == 1
        assert len(result.process_steps) == 1
        assert result.process_steps[0].step_number == 1
        assert len(result.decision_points) == 1
        assert result.decision_points[0].name == "Leave exceeds 5 days"
        assert len(result.business_rules) == 1
        assert result.business_rules[0].name == "Extended leave requires VP approval"


# ---------------------------------------------------------------------------
# 2. Invalid JSON raises ValidationError
# ---------------------------------------------------------------------------

class TestGraphExtractionInvalidJsonRaises:
    def test_invalid_entity_type_field_missing(self):
        bad = {
            "entities": [{"name": "Test"}],  # missing type and description
        }
        with pytest.raises(ValidationError):
            GraphExtraction.model_validate(bad)


# ---------------------------------------------------------------------------
# 3. Dedup merges similar entities
# ---------------------------------------------------------------------------

class TestDeduplicateEntitiesMergesSimilar:
    def test_merges_similar_names_same_type(self):
        entities = [
            Entity(name="US Dept of Energy", type="ORG", description="Short name"),
            Entity(name="US Department of Energy", type="ORG", description="Full name"),
        ]
        canonical, name_map = deduplicate_entities(entities)
        assert len(canonical) == 1
        # Longer name is kept as canonical
        assert canonical[0].name == "US Department of Energy"
        assert "US Dept of Energy" in name_map
        assert name_map["US Dept of Energy"] == "US Department of Energy"


# ---------------------------------------------------------------------------
# 4. No cross-type merge
# ---------------------------------------------------------------------------

class TestDeduplicateEntitiesNoCrossTypeMerge:
    def test_same_name_different_types_not_merged(self):
        entities = [
            Entity(name="Mercury", type="CONCEPT", description="A planet"),
            Entity(name="Mercury", type="SYSTEM", description="A messaging system"),
        ]
        canonical, name_map = deduplicate_entities(entities)
        assert len(canonical) == 2
        assert len(name_map) == 0


# ---------------------------------------------------------------------------
# 5. Preserves unique entities
# ---------------------------------------------------------------------------

class TestDeduplicateEntitiesPreservesUnique:
    def test_three_distinct_entities_remain(self):
        entities = [
            Entity(name="Alice", type="PERSON", description="Engineer"),
            Entity(name="Bob", type="PERSON", description="Manager"),
            Entity(name="Acme Corp", type="ORG", description="Company"),
        ]
        canonical, name_map = deduplicate_entities(entities)
        assert len(canonical) == 3
        assert len(name_map) == 0


# ---------------------------------------------------------------------------
# 6. Apply dedup updates relationships and actors
# ---------------------------------------------------------------------------

class TestApplyDedupUpdatesRelationships:
    def test_relationship_source_target_updated(self):
        extraction = GraphExtraction(
            entities=[
                Entity(name="US Department of Energy", type="ORG", description="Full"),
            ],
            relationships=[
                Relationship(source="US Dept of Energy", target="EPA", relation="funds"),
            ],
            process_steps=[
                ProcessStep(step_number=1, name="", description="Review", actors=["US Dept of Energy"]),
            ],
        )
        name_map = {"US Dept of Energy": "US Department of Energy"}

        updated = _apply_dedup_to_graph(extraction, name_map)

        assert updated.relationships[0].source == "US Department of Energy"
        assert updated.process_steps[0].actors[0] == "US Department of Energy"


# ---------------------------------------------------------------------------
# 7. No chunks → error
# ---------------------------------------------------------------------------

class TestRunGraphExtractionNoChunks:
    def test_returns_error_when_no_chunks(self):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = []
        mock_nim = MagicMock()

        result = run_graph_extraction("doc123", mock_vs, mock_nim)

        assert isinstance(result, GraphResult)
        assert result.error is not None
        assert "No chunks" in result.error
        assert result.chunk_count == 0
        mock_nim.chat.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Success path
# ---------------------------------------------------------------------------

class TestRunGraphExtractionSuccess:
    @patch("pipelines.graph._load_prompt", return_value="{context}")
    def test_returns_populated_result(self, _mock_prompt):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = _make_chunks(["The HR Manager reviews leave."])

        valid_json = json.dumps(VALID_EXTRACTION_DICT)
        mock_nim = MagicMock()
        mock_nim.chat.return_value = _make_mock_chat(valid_json)

        result = run_graph_extraction("doc1", mock_vs, mock_nim)

        assert result.error is None
        assert result.extraction is not None
        assert result.chunk_count == 1
        assert result.entity_count > 0
        assert result.method == "single_pass"


# ---------------------------------------------------------------------------
# 9. Self-correction path
# ---------------------------------------------------------------------------

class TestRunGraphExtractionSelfCorrection:
    @patch("pipelines.graph._load_prompt", return_value="{context}")
    def test_self_correction_recovers(self, _mock_prompt):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = _make_chunks(["Some text."])

        # First call returns invalid JSON, second returns valid
        invalid_response = _make_mock_chat("not valid json {{{")
        valid_response = _make_mock_chat(json.dumps(VALID_EXTRACTION_DICT))
        mock_nim = MagicMock()
        mock_nim.chat.side_effect = [invalid_response, valid_response]

        # Patch _load_prompt to return format-safe templates
        with patch(
            "pipelines.graph._load_prompt",
            side_effect=[
                "{context}",  # graph_extract.txt
                "{original_output} {error_message}",  # graph_correct.txt
            ],
        ):
            result = run_graph_extraction("doc1", mock_vs, mock_nim)

        assert result.error is None
        assert result.extraction is not None
        assert mock_nim.chat.call_count == 2


# ---------------------------------------------------------------------------
# 10. Error handling
# ---------------------------------------------------------------------------

class TestRunGraphExtractionErrorHandling:
    def test_nim_exception_returns_error_result(self):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = _make_chunks(["Some text."])

        mock_nim = MagicMock()
        mock_nim.chat.side_effect = RuntimeError("API unavailable")

        with patch("pipelines.graph._load_prompt", return_value="{context}"):
            result = run_graph_extraction("doc1", mock_vs, mock_nim)

        assert result.error is not None
        assert "API unavailable" in result.error
        assert result.extraction is None


# ---------------------------------------------------------------------------
# 11. Format pydantic errors
# ---------------------------------------------------------------------------

class TestFormatPydanticErrors:
    def test_validation_error_produces_readable_string(self):
        try:
            Entity.model_validate({"name": "Test"})  # missing type and description
        except ValidationError as e:
            result = _format_pydantic_errors(e)
            assert "type" in result
            assert "description" in result
            assert isinstance(result, str)

    def test_non_validation_error_returns_str(self):
        result = _format_pydantic_errors(ValueError("something broke"))
        assert result == "something broke"


# ---------------------------------------------------------------------------
# 12. Metadata extraction tests
# ---------------------------------------------------------------------------

class TestRunGraphExtractionMetadata:
    @patch("pipelines.graph._load_prompt", return_value="{context}")
    def test_run_graph_returns_metadata(self, _mock_prompt):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = _make_chunks(["The HR Manager reviews leave."])

        valid_json = json.dumps(VALID_EXTRACTION_DICT)
        mock_nim = MagicMock()
        mock_nim.chat.return_value = _make_mock_chat(
            valid_json, prompt_tokens=200, completion_tokens=100, model="graph-model"
        )

        result = run_graph_extraction("doc1", mock_vs, mock_nim)

        assert result.model_used == "graph-model"
        assert result.prompt_tokens == 200
        assert result.completion_tokens == 100
        assert result.latency_ms > 0

    @patch("pipelines.graph._load_prompt", return_value="{context}")
    def test_run_graph_with_explicit_model(self, _mock_prompt):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = _make_chunks(["Some text."])

        valid_json = json.dumps(VALID_EXTRACTION_DICT)
        mock_nim = MagicMock()
        mock_nim.chat.return_value = _make_mock_chat(
            valid_json, prompt_tokens=10, completion_tokens=5, model="explicit-model"
        )

        run_graph_extraction("doc1", mock_vs, mock_nim, model="explicit-model")

        call_kwargs = mock_nim.chat.call_args[1]
        assert call_kwargs["model"] == "explicit-model"
