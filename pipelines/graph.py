"""Graph extraction pipeline: extract entities, relationships, and structure from document chunks."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from rapidfuzz import fuzz

from core.llm_client import NIMClient
from core.vectorstore import VectorStore

logger = logging.getLogger(__name__)

DEDUP_THRESHOLD = 85


# ---------------------------------------------------------------------------
# Pydantic models — field aliases align with the LLM prompt template schema
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    """A named entity extracted from the document."""

    name: str
    type: str  # PERSON, ORG, PROCESS, SYSTEM, CONCEPT, DOCUMENT, ROLE
    description: str


class Relationship(BaseModel):
    """A directed relationship between two entities."""

    source: str
    target: str
    relation: str
    description: str = ""


class ProcessStep(BaseModel):
    """A step in a process extracted from the document."""

    model_config = ConfigDict(populate_by_name=True)

    step_number: int = Field(alias="step")
    name: str = ""
    description: str
    actors: list[str] = Field(default_factory=list)


class DecisionPoint(BaseModel):
    """A decision point with possible outcomes."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(default="", alias="condition")
    description: str = ""
    options: list[str] = Field(default_factory=list, alias="outcomes")


class BusinessRule(BaseModel):
    """A business rule extracted from the document."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(default="", alias="rule")
    description: str = ""
    condition: str = ""
    action: str = ""


class GraphExtraction(BaseModel):
    """Complete graph extraction result from a document."""

    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    process_steps: list[ProcessStep] = Field(default_factory=list)
    decision_points: list[DecisionPoint] = Field(default_factory=list)
    business_rules: list[BusinessRule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class GraphResult:
    """Structured result from a graph extraction run."""

    extraction: GraphExtraction | None = None
    doc_id: str = ""
    chunk_count: int = 0
    entity_count: int = 0
    dedup_merges: int = 0
    method: str = "single_pass"
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(name: str) -> str:
    """Read a prompt template from the prompts/ directory."""
    return Path(f"prompts/{name}").read_text(encoding="utf-8")


def _format_pydantic_errors(e: Exception) -> str:
    """Convert Pydantic validation errors to human-readable sentences."""
    if isinstance(e, ValidationError):
        parts: list[str] = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            parts.append(f"Field '{loc}': {err['msg']} (type={err['type']})")
        return "; ".join(parts)
    return str(e)


def _extract_with_retry(
    context: str, nim_client: NIMClient
) -> GraphExtraction:
    """Extract graph from context with one self-correction retry on parse failure."""
    prompt = _load_prompt("graph_extract.txt").format(context=context)
    response = nim_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4096,
        json_mode=True,
    )
    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
        return GraphExtraction.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as first_error:
        logger.warning("First extraction attempt failed: %s — retrying with correction prompt", first_error)
        correction_prompt = _load_prompt("graph_correct.txt").format(
            original_output=raw,
            error_message=_format_pydantic_errors(first_error),
        )
        retry_response = nim_client.chat(
            messages=[{"role": "user", "content": correction_prompt}],
            temperature=0.1,
            max_tokens=4096,
            json_mode=True,
        )
        retry_raw = retry_response.choices[0].message.content
        retry_data = json.loads(retry_raw)
        return GraphExtraction.model_validate(retry_data)


def deduplicate_entities(
    entities: list[Entity],
) -> tuple[list[Entity], dict[str, str]]:
    """Merge similar entities within the same type using fuzzy matching.

    Returns:
        Tuple of (canonical entities, name_map) where name_map maps
        old names to their canonical (longer) form.
    """
    name_map: dict[str, str] = {}
    canonical: list[Entity] = []

    # Group by type
    by_type: dict[str, list[Entity]] = {}
    for ent in entities:
        by_type.setdefault(ent.type, []).append(ent)

    for _etype, group in by_type.items():
        merged_indices: set[int] = set()
        for i in range(len(group)):
            if i in merged_indices:
                continue
            keeper = group[i]
            for j in range(i + 1, len(group)):
                if j in merged_indices:
                    continue
                score = fuzz.token_sort_ratio(keeper.name, group[j].name)
                if score >= DEDUP_THRESHOLD:
                    merged_indices.add(j)
                    # Keep the longer name as canonical
                    if len(group[j].name) > len(keeper.name):
                        name_map[keeper.name] = group[j].name
                        keeper = group[j]
                    else:
                        name_map[group[j].name] = keeper.name
            canonical.append(keeper)

    return canonical, name_map


def _apply_dedup_to_graph(
    extraction: GraphExtraction, name_map: dict[str, str]
) -> GraphExtraction:
    """Replace merged entity names in relationships and process step actors."""
    updated_rels = []
    for rel in extraction.relationships:
        updated_rels.append(
            Relationship(
                source=name_map.get(rel.source, rel.source),
                target=name_map.get(rel.target, rel.target),
                relation=rel.relation,
                description=rel.description,
            )
        )

    updated_steps = []
    for step in extraction.process_steps:
        updated_steps.append(
            ProcessStep(
                step_number=step.step_number,
                name=step.name,
                description=step.description,
                actors=[name_map.get(a, a) for a in step.actors],
            )
        )

    return GraphExtraction(
        entities=extraction.entities,
        relationships=updated_rels,
        process_steps=updated_steps,
        decision_points=extraction.decision_points,
        business_rules=extraction.business_rules,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_graph_extraction(
    doc_id: str,
    vectorstore: VectorStore,
    nim_client: NIMClient,
) -> GraphResult:
    """Run the graph extraction pipeline for a document.

    Retrieves all chunks, concatenates them, runs LLM extraction
    with self-correction, and deduplicates entities via fuzzy matching.
    """
    try:
        chunks = vectorstore.get_all_by_doc(doc_id)
        if not chunks:
            return GraphResult(
                doc_id=doc_id,
                error="No chunks found for document.",
            )

        context = "\n\n".join(c["text"] for c in chunks)
        extraction = _extract_with_retry(context, nim_client)

        canonical_entities, name_map = deduplicate_entities(extraction.entities)
        dedup_merges = len(extraction.entities) - len(canonical_entities)
        extraction = extraction.model_copy(update={"entities": canonical_entities})
        extraction = _apply_dedup_to_graph(extraction, name_map)

        return GraphResult(
            extraction=extraction,
            doc_id=doc_id,
            chunk_count=len(chunks),
            entity_count=len(canonical_entities),
            dedup_merges=dedup_merges,
            method="single_pass",
        )
    except Exception as exc:
        logger.exception("Graph extraction failed for doc_id=%s", doc_id)
        return GraphResult(
            doc_id=doc_id,
            error=str(exc),
        )
