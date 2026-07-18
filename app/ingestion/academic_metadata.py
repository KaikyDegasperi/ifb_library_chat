"""Extração determinística de metadados dos TCCs após o Docling."""

import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.ingestion.chunking import clean_text


class AcademicMetadata(BaseModel):
    title: str | None = None
    author: str | None = None
    advisor: str | None = None
    coadvisor: str | None = None
    year: int | None = None


class _TextItem(BaseModel):
    text: str
    label: str | None
    page: int | None


_STOP_COVER = re.compile(
    r"(?i)^(?:bras[ií]lia\b|(?:19|20)\d{2}$|trabalho\s+(?:de\s+)?conclusão|"
    r"artigo\s+apresentado|monografia\s+apresentada|orientador|coorientador)"
)
_ADMINISTRATIVE_MARKERS = (
    "ficha de aprovacao em banca examinadora",
    "documento assinado eletronicamente por",
    "documento digitalizado publico",
    "codigo de autenticacao",
    "autenticar-documento",
    "verificar-documento-externo",
)


def extract_academic_metadata(document: Any, file_name: str) -> AcademicMetadata:
    """Combina rótulos, campos explícitos e o padrão das capas do IFB."""
    items = _document_items(document)
    author, author_index = _extract_author(items, file_name)
    explicit_title = _extract_prefixed_value(items, r"t[ií]tulo")
    labelled_title = next(
        (item.text for item in items if item.label == "title" and item.text),
        None,
    )
    cover_title = _extract_cover_title(items, author_index)
    title = _best_title(labelled_title, cover_title, explicit_title)

    return AcademicMetadata(
        title=_clean_metadata_value(title, prefix=r"t[ií]tulo"),
        author=_clean_metadata_value(author, prefix=r"discente|autor(?:a)?"),
        advisor=_extract_person_field(items, r"orientador(?:a)?"),
        coadvisor=_extract_person_field(items, r"coorientador(?:a)?"),
        year=_extract_year(items),
    )


def administrative_pages(document: Any) -> set[int]:
    """Identifica folhas administrativas que não devem disputar busca semântica."""
    pages: dict[int, list[str]] = defaultdict(list)
    for item in _document_items(document):
        if item.page is not None:
            pages[item.page].append(item.text)
    ignored: set[int] = set()
    for page, values in pages.items():
        text = _fold(" ".join(values))
        if any(marker in text for marker in _ADMINISTRATIVE_MARKERS):
            ignored.add(page)
    return ignored


def _document_items(document: Any) -> list[_TextItem]:
    result: list[_TextItem] = []
    for item in getattr(document, "texts", []):
        text = clean_text(getattr(item, "text", ""))
        if not text:
            continue
        label = getattr(getattr(item, "label", None), "value", None)
        provenance = getattr(item, "prov", None) or []
        page = getattr(provenance[0], "page_no", None) if provenance else None
        result.append(_TextItem(text=text, label=label, page=page))
    return result


def _extract_author(items: list[_TextItem], file_name: str) -> tuple[str | None, int | None]:
    explicit = _extract_prefixed_value(items, r"discente|autor(?:a)?", with_index=True)
    filename_tokens = {
        token
        for token in re.findall(r"[a-zà-ÿ]+", _fold(Path(file_name).stem))
        if token not in {"cest", "tcc"} and len(token) > 2
    }
    for index, item in enumerate(items):
        if item.page != 1 or not _looks_like_person(item.text):
            continue
        candidate_tokens = set(re.findall(r"[a-zà-ÿ]+", _fold(item.text)))
        if len(filename_tokens & candidate_tokens) >= min(2, len(filename_tokens)):
            return explicit[0] or item.text, index
    return explicit


def _extract_cover_title(items: list[_TextItem], author_index: int | None) -> str | None:
    if author_index is None:
        return None
    author_page = items[author_index].page
    parts: list[str] = []
    for item in items[author_index + 1 :]:
        if item.page != author_page:
            break
        if item.label in {"page_footer", "page_header"} or _STOP_COVER.search(item.text):
            break
        parts.append(item.text)
        if len(parts) == 3:
            break
    value = " ".join(parts)
    return value if len(value) >= 12 else None


def _extract_prefixed_value(
    items: list[_TextItem],
    prefix: str,
    *,
    with_index: bool = False,
) -> Any:
    pattern = re.compile(rf"(?i)^\s*(?:{prefix})\s*:\s*(.*)$")
    for index, item in enumerate(items):
        if item.page is not None and item.page > 4:
            continue
        match = pattern.match(item.text)
        if not match:
            continue
        value = match.group(1).strip()
        if not value and index + 1 < len(items) and items[index + 1].page == item.page:
            value = items[index + 1].text
            index += 1
        return (value or None, index) if with_index else value or None
    return (None, None) if with_index else None


def _extract_person_field(items: list[_TextItem], prefix: str) -> str | None:
    pattern = re.compile(
        rf"(?i)(?:^|.*\b)(?:{prefix})(?:\s*\([^)]*\))?\s*:\s*(.*)$"
    )
    stop = re.compile(
        r"(?i)^(?:(?:co)?orientador|bras[ií]lia|trabalho aprovado|banca examinadora|"
        r"discente|t[ií]tulo|avaliador|examinador|instituto federal|(?:19|20)\d{2}$)"
    )
    for index, item in enumerate(items):
        if item.page is not None and item.page > 4:
            continue
        match = pattern.match(item.text)
        if not match:
            continue
        parts = [match.group(1).strip()] if match.group(1).strip() else []
        for following in items[index + 1 : index + 7]:
            if following.page != item.page or stop.search(following.text):
                break
            if following.label in {"page_footer", "page_header"}:
                break
            parts.append(following.text)
        return _clean_metadata_value(" ".join(parts))
    return None


def _extract_year(items: list[_TextItem]) -> int | None:
    for item in items:
        if item.page not in {1, 2}:
            continue
        years = re.findall(r"\b(?:19|20)\d{2}\b", item.text)
        if years:
            return int(years[-1])
    return None


def _best_title(*values: str | None) -> str | None:
    candidates = [value for value in values if value]
    if not candidates:
        return None

    def score(value: str) -> int:
        longest_word = max((len(word) for word in value.split()), default=0)
        return (
            len(value)
            - (60 if "*" in value else 0)
            - (100 if re.search(r"(?i)\btrabalho\s+aprovado\b", value) else 0)
            - max(0, longest_word - 24) * 4
        )

    return max(candidates, key=score)


def _looks_like_person(text: str) -> bool:
    if ":" in text or any(character.isdigit() for character in text):
        return False
    words = re.findall(r"[A-Za-zÀ-ÿ]+", text)
    if not 2 <= len(words) <= 9 or len(text) > 90:
        return False
    forbidden = {
        "instituto",
        "federal",
        "campus",
        "curso",
        "licenciatura",
        "matematica",
        "ministerio",
        "educacao",
        "brasilia",
    }
    return not ({_fold(word) for word in words} & forbidden)


def _clean_metadata_value(value: str | None, prefix: str | None = None) -> str | None:
    if not value:
        return None
    cleaned = clean_text(value).replace("\n", " ")
    if prefix:
        cleaned = re.sub(rf"(?i)^\s*(?:{prefix})\s*:\s*", "", cleaned)
    cleaned = re.split(r"(?i)\btrabalho\s+aprovado\s+em\s*:", cleaned, maxsplit=1)[0]
    cleaned = re.sub(r"(?<=\w)\*(?=\w)", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" .;-")
    return cleaned or None


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))
