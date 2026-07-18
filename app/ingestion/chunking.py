"""Chunking estrutural sobre os blocos produzidos pelo Docling."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StructuredPiece:
    text: str
    section: str | None
    page_start: int | None
    page_end: int | None


def clean_text(text: str) -> str:
    """Normaliza somente espaços acidentais, preservando quebras semânticas."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def pages_from_items(items: Iterable[Any]) -> tuple[int | None, int | None]:
    pages = sorted(
        {
            provenance.page_no
            for item in items
            for provenance in getattr(item, "prov", [])
            if getattr(provenance, "page_no", None) is not None
        }
    )
    if not pages:
        return None, None
    return pages[0], pages[-1]


def split_with_overlap(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Divide blocos grandes por palavras; nunca combina seções distintas."""
    if chunk_size <= 0:
        raise ValueError("chunk_size deve ser maior que zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap deve ser >= 0 e menor que chunk_size")

    words = text.split()
    if len(words) <= chunk_size:
        return [text] if text else []

    step = chunk_size - overlap
    parts: list[str] = []
    for start in range(0, len(words), step):
        part = " ".join(words[start : start + chunk_size])
        if part:
            parts.append(part)
        if start + chunk_size >= len(words):
            break
    return parts


def structured_pieces(
    document: Any,
    chunker: Any,
    chunk_size: int,
    overlap: int,
    ignored_pages: set[int] | None = None,
) -> list[StructuredPiece]:
    pieces: list[StructuredPiece] = []
    ignored_pages = ignored_pages or set()
    for base_chunk in chunker.chunk(dl_doc=document):
        text = clean_text(chunker.contextualize(base_chunk))
        headings = getattr(base_chunk.meta, "headings", None) or []
        section = " > ".join(clean_text(value) for value in headings) or None
        page_start, page_end = pages_from_items(base_chunk.meta.doc_items)
        if (
            page_start is not None
            and page_end is not None
            and set(range(page_start, page_end + 1)) <= ignored_pages
        ):
            continue
        for part in split_with_overlap(text, chunk_size, overlap):
            pieces.append(
                StructuredPiece(
                    text=part,
                    section=section,
                    page_start=page_start,
                    page_end=page_end,
                )
            )
    return pieces
