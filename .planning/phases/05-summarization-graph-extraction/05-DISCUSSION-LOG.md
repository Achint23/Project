# Phase 5: Summarization + Graph Extraction - Discussion Log

**Date:** 2026-04-28
**Mode:** --auto (fully autonomous — agent selected recommended defaults)
**Duration:** Single pass

## Areas Discussed

### 1. Summary Presentation Format
- **Options:** Bullet points / Flowing prose / Structured sections
- **Selected:** Flowing prose with key points bolded (recommended default)
- **Rationale:** Most business-readable; matches what non-technical stakeholders expect from a document summary

### 2. Graph Extraction Prompt Strategy
- **Options:** Single mega-prompt / Separate per-category prompts
- **Selected:** Single mega-prompt (recommended default per RESEARCH.md)
- **Rationale:** Fewer LLM calls, better cross-referencing between entities and relationships, simpler pipeline code

### 3. Graph Visualization Primary View
- **Options:** Interactive node-edge only / Mermaid flowchart only / Both
- **Selected:** Both — node-edge for entities/relationships, mermaid for process steps (recommended default)
- **Rationale:** Each visualization serves a different purpose; node-edge for exploration, mermaid for sequential understanding

### 4. Summarization Trigger UX
- **Options:** Button per document / Auto-on-select / Tab-based layout
- **Selected:** Tab-based layout — Summary and Graph tabs alongside Chat (recommended default)
- **Rationale:** Consistent Streamlit pattern, non-blocking, users can switch views freely

### 5. Entity Type Granularity
- **Options:** Broad (3-4) / Medium (7) / Fine (15+)
- **Selected:** 7 types: PERSON, ORG, PROCESS, SYSTEM, CONCEPT, DOCUMENT, ROLE (recommended default per RESEARCH.md)
- **Rationale:** Enough coverage for document analysis without confusing the LLM; types are listed in the prompt

### 6. Long-Document Extraction Strategy
- **Options:** All chunks / Representative subset / Sliding window
- **Selected:** All chunks concatenated, map-reduce fallback if token limit exceeded (recommended default)
- **Rationale:** Full document coverage is important for completeness; map-reduce handles overflow

## Deferred Ideas
- Streaming summarization progress — Phase 7 polish
- Graph export to JSON/GraphML — v2
- Hierarchical map-reduce for 100+ page docs — revisit if needed
- Cross-document graph comparison — v2

## Notes
All decisions were auto-selected using recommended defaults from RESEARCH.md and established codebase patterns. No user interaction was required.
