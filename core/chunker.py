"""Structure-aware text chunking with token-based sizing."""

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    """Count tokens using cl100k_base encoding."""
    return len(_ENCODING.encode(text))


def _is_heading(line: str) -> bool:
    """Heuristic: short line, no trailing punctuation, not whitespace-only."""
    stripped = line.strip()
    if not stripped or len(stripped) >= 80:
        return False
    if stripped[-1] in ".!?;:,":
        return False
    return True


def _split_oversized(text: str, max_tokens: int) -> list[str]:
    """Split text that exceeds max_tokens by lines, then sentences."""
    # Try splitting by lines first
    lines = text.split("\n")
    if len(lines) > 1:
        chunks = []
        current = []
        current_tokens = 0
        for line in lines:
            line_tokens = _count_tokens(line)
            if current_tokens + line_tokens > max_tokens and current:
                chunks.append("\n".join(current))
                current = [line]
                current_tokens = line_tokens
            else:
                current.append(line)
                current_tokens += line_tokens
        if current:
            chunks.append("\n".join(current))
        return chunks

    # Fall back to sentence splitting
    sentences = text.split(". ")
    if len(sentences) > 1:
        chunks = []
        current = []
        current_tokens = 0
        for sent in sentences:
            sent_tokens = _count_tokens(sent)
            if current_tokens + sent_tokens > max_tokens and current:
                chunks.append(". ".join(current) + ".")
                current = [sent]
                current_tokens = sent_tokens
            else:
                current.append(sent)
                current_tokens += sent_tokens
        if current:
            chunks.append(". ".join(current))
        return chunks

    # Cannot split further — return as-is
    return [text]


def chunk_text(
    text: str,
    doc_id: str,
    page_num: int,
    max_tokens: int = 450,
    overlap_tokens: int = 50,
) -> list[dict]:
    """Split text into chunks respecting structure boundaries.

    Args:
        text: The text to chunk.
        doc_id: Document identifier for metadata.
        page_num: Page number for metadata.
        max_tokens: Maximum tokens per chunk (default 450, keeps under embedding model 512 limit).
        overlap_tokens: Token overlap between consecutive chunks (default 50).

    Returns:
        List of chunk dicts with text, doc_id, page_num, chunk_type, chunk_index.
    """
    if not text or not text.strip():
        return []

    # Split into paragraphs on double newlines
    paragraphs = text.split("\n\n")
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    # Attach headings to following paragraphs
    merged = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        # Check if this paragraph is a heading (single line, short, no trailing punct)
        lines = para.split("\n")
        if len(lines) == 1 and _is_heading(lines[0]) and i + 1 < len(paragraphs):
            # Attach heading to next paragraph
            merged.append(para + "\n\n" + paragraphs[i + 1])
            i += 2
        else:
            merged.append(para)
            i += 1

    paragraphs = merged

    chunks: list[dict] = []
    current_parts: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _count_tokens(para)

        # If single paragraph exceeds max, split it
        if para_tokens > max_tokens:
            # Flush current chunk first
            if current_parts:
                chunks.append(
                    {
                        "text": "\n\n".join(current_parts),
                        "doc_id": doc_id,
                        "page_num": page_num,
                        "chunk_type": "text",
                        "chunk_index": len(chunks),
                    }
                )
                current_parts = []
                current_tokens = 0

            # Split the oversized paragraph
            sub_chunks = _split_oversized(para, max_tokens)
            for sub in sub_chunks:
                chunks.append(
                    {
                        "text": sub,
                        "doc_id": doc_id,
                        "page_num": page_num,
                        "chunk_type": "text",
                        "chunk_index": len(chunks),
                    }
                )
            continue

        if current_tokens + para_tokens > max_tokens and current_parts:
            # Emit current chunk
            chunk_text_str = "\n\n".join(current_parts)
            chunks.append(
                {
                    "text": chunk_text_str,
                    "doc_id": doc_id,
                    "page_num": page_num,
                    "chunk_type": "text",
                    "chunk_index": len(chunks),
                }
            )

            # Build overlap from end of current chunk
            overlap_parts: list[str] = []
            overlap_count = 0
            for part in reversed(current_parts):
                part_tokens = _count_tokens(part)
                if overlap_count + part_tokens <= overlap_tokens:
                    overlap_parts.insert(0, part)
                    overlap_count += part_tokens
                else:
                    break

            current_parts = overlap_parts + [para]
            current_tokens = sum(_count_tokens(p) for p in current_parts)
        else:
            current_parts.append(para)
            current_tokens += para_tokens

    # Flush remaining
    if current_parts:
        chunks.append(
            {
                "text": "\n\n".join(current_parts),
                "doc_id": doc_id,
                "page_num": page_num,
                "chunk_type": "text",
                "chunk_index": len(chunks),
            }
        )

    return chunks


def chunk_document(pages: list[dict], doc_id: str) -> list[dict]:
    """Chunk all pages from extract_document output.

    Args:
        pages: Output from extract_document() — list of dicts with text, chunk_type, page_num.
        doc_id: Document identifier.

    Returns:
        Flat list of chunk dicts with sequential chunk_index.
    """
    all_chunks: list[dict] = []
    chunk_index = 0

    for item in pages:
        if item.get("chunk_type") == "table":
            # Tables are atomic — never split
            all_chunks.append(
                {
                    "text": item["text"],
                    "doc_id": doc_id,
                    "page_num": item["page_num"],
                    "chunk_type": "table",
                    "chunk_index": chunk_index,
                }
            )
            chunk_index += 1
        elif item.get("chunk_type") in ("text", "ocr"):
            text_chunks = chunk_text(
                item["text"], doc_id, item["page_num"]
            )
            for tc in text_chunks:
                tc["chunk_index"] = chunk_index
                if item.get("chunk_type") == "ocr":
                    tc["chunk_type"] = "ocr"
                all_chunks.append(tc)
                chunk_index += 1

    return all_chunks
