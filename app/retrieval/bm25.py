"""Recuperação lexical BM25 sobre os chunks processados."""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import time
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from threading import RLock
from typing import Any

from app.vectorstore.models import (
    IndexFileResult,
    IndexReport,
    SearchResult,
    SearchTimings,
)

TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return TOKEN_PATTERN.findall(normalized)


class BM25IndexService:
    """Índice BM25 atualizável e compatível com o contrato do RAG."""

    def __init__(
        self,
        processed_dir: Path | str,
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 deve ser maior que zero")
        if not 0 <= b <= 1:
            raise ValueError("b deve estar entre zero e um")
        self.processed_dir = Path(processed_dir)
        self.k1 = k1
        self.b = b
        self._lock = RLock()
        self._by_document: dict[str, list[SearchResult]] = {}
        self._chunks: tuple[SearchResult, ...] = ()
        self._frequencies: tuple[Counter[str], ...] = ()
        self._lengths: tuple[int, ...] = ()
        self._average_length = 0.0
        self._postings: dict[str, tuple[tuple[int, int], ...]] = {}

    @property
    def count(self) -> int:
        return len(self._chunks)

    def index(
        self,
        input_path: Path | str,
        *,
        allowed_document_ids: set[str] | None = None,
    ) -> IndexReport:
        started = time.perf_counter()
        path = Path(input_path)
        files = self._discover(path)
        if path.is_dir():
            files = self._select_latest_versions(files)
        results: list[IndexFileResult] = []
        indexed: dict[str, list[SearchResult]] = {}
        for file_path in files:
            try:
                document_id, chunks = self._read_chunks(file_path)
                if (
                    allowed_document_ids is not None
                    and document_id not in allowed_document_ids
                ):
                    continue
                indexed[document_id] = chunks
                results.append(
                    IndexFileResult(
                        file_path=str(file_path.resolve()),
                        document_id=document_id,
                        status="indexed",
                        chunks=len(chunks),
                    )
                )
            except Exception as exc:
                results.append(
                    IndexFileResult(
                        file_path=str(file_path.resolve()),
                        document_id=None,
                        status="error",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

        with self._lock:
            if path.is_dir():
                self._by_document = indexed
            else:
                self._by_document.update(indexed)
            self._rebuild()
            collection_count = len(self._chunks)
        return IndexReport(
            documents_indexed=sum(item.status == "indexed" for item in results),
            documents_skipped=0,
            documents_failed=sum(item.status == "error" for item in results),
            chunks_indexed=sum(item.chunks for item in results if item.status == "indexed"),
            chunks_removed=0,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            collection_count=collection_count,
            results=results,
        )

    def delete(self, document_id: str) -> int:
        with self._lock:
            removed = len(self._by_document.pop(document_id, []))
            if removed:
                self._rebuild()
            return removed

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        title: str | None = None,
        timings: SearchTimings | None = None,
    ) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("A consulta não pode ser vazia")
        if top_k < 1:
            raise ValueError("top_k deve ser maior que zero")
        started = time.perf_counter()
        with self._lock:
            chunks = self._chunks
            lengths = self._lengths
            average_length = self._average_length
            postings = self._postings
        if not chunks:
            return []

        scores: dict[int, float] = defaultdict(float)
        corpus_size = len(chunks)
        for term in dict.fromkeys(tokenize(query)):
            matches = postings.get(term, ())
            document_frequency = len(matches)
            if not document_frequency:
                continue
            inverse_document_frequency = math.log(
                1
                + (corpus_size - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            for chunk_index, term_frequency in matches:
                length_normalization = 1 - self.b + (
                    self.b * lengths[chunk_index] / average_length
                )
                scores[chunk_index] += inverse_document_frequency * (
                    term_frequency * (self.k1 + 1)
                ) / (term_frequency + self.k1 * length_normalization)

        allowed = [
            index
            for index, chunk in enumerate(chunks)
            if (document_id is None or chunk.document_id == document_id)
            and (title is None or chunk.title == title)
        ]
        ranked = sorted(
            allowed,
            key=lambda index: (
                -scores.get(index, 0.0),
                chunks[index].file_name.casefold(),
                chunks[index].chunk_index,
                chunks[index].chunk_id,
            ),
        )[: min(top_k, len(allowed))]
        if timings is not None:
            timings.vector_search_time_ms = self._elapsed_ms(started)
        return [
            chunks[index].model_copy(
                update={
                    "similarity": round(
                        self._normalized_score(scores.get(index, 0.0)),
                        6,
                    )
                }
            )
            for index in ranked
        ]

    def search_with_timings(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        title: str | None = None,
    ) -> tuple[list[SearchResult], SearchTimings]:
        timings = SearchTimings()
        results = self.search(query, top_k, document_id, title, timings=timings)
        return results, timings

    def suggest_query(self, query: str) -> str:
        """Sugere correções sem modificar a busca ou o índice BM25 oficial."""
        with self._lock:
            vocabulary = tuple(self._postings)
            document_frequencies = {
                term: len(matches) for term, matches in self._postings.items()
            }
        if not vocabulary:
            return query

        known = set(vocabulary)
        replacements: dict[str, str] = {}
        for term in dict.fromkeys(tokenize(query)):
            if term in known or len(term) < 4:
                continue
            candidates = [
                candidate
                for candidate in vocabulary
                if abs(len(candidate) - len(term)) <= 2
                and candidate[0] == term[0]
            ]
            if not candidates:
                continue
            scored = [
                (
                    SequenceMatcher(None, term, candidate).ratio(),
                    document_frequencies[candidate],
                    candidate,
                )
                for candidate in candidates
            ]
            ratio, _, replacement = max(scored)
            cutoff = 0.8 if len(term) <= 4 else 0.74
            if ratio >= cutoff:
                replacements[term] = replacement

        if not replacements:
            return query
        return TOKEN_PATTERN.sub(
            lambda match: replacements.get(match.group(0).casefold(), match.group(0)),
            query,
        )

    def _rebuild(self) -> None:
        chunks = tuple(
            chunk
            for document_id in sorted(self._by_document)
            for chunk in sorted(
                self._by_document[document_id],
                key=lambda item: (item.chunk_index, item.chunk_id),
            )
        )
        frequencies = tuple(Counter(tokenize(chunk.content)) for chunk in chunks)
        lengths = tuple(sum(items.values()) for items in frequencies)
        postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for chunk_index, items in enumerate(frequencies):
            for term, frequency in items.items():
                postings[term].append((chunk_index, frequency))
        self._chunks = chunks
        self._frequencies = frequencies
        self._lengths = lengths
        self._average_length = statistics.fmean(lengths) if lengths else 0.0
        self._postings = {
            term: tuple(matches) for term, matches in postings.items()
        }

    @staticmethod
    def _normalized_score(score: float) -> float:
        return score / (score + 1.0) if score > 0 else 0.0

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((time.perf_counter() - started) * 1000))

    @staticmethod
    def _discover(path: Path) -> list[Path]:
        if not path.exists():
            raise FileNotFoundError(f"Caminho de chunks inexistente: {path}")
        if path.is_file():
            if not path.name.endswith(".chunks.json"):
                raise ValueError("O arquivo deve terminar com .chunks.json")
            return [path]
        return sorted(path.glob("*.chunks.json"))

    @staticmethod
    def _select_latest_versions(files: list[Path]) -> list[Path]:
        latest: dict[str, tuple[str, Path]] = {}
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw_chunks = payload.get("chunks", [])
            if not raw_chunks:
                continue
            metadata = raw_chunks[0].get("metadata", {})
            source = str(metadata.get("file_path") or metadata.get("file_name") or path)
            processed_at = str(metadata.get("processed_at") or "")
            current = latest.get(source)
            if current is None or processed_at > current[0]:
                latest[source] = (processed_at, path)
        return sorted(item[1] for item in latest.values())

    @staticmethod
    def _read_chunks(path: Path) -> tuple[str, list[SearchResult]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        document_id = str(payload.get("document_id") or "")
        document_hash = str(payload.get("document_hash") or "")
        if not document_id or not document_hash:
            raise ValueError("Arquivo de chunks incompleto")
        chunks: list[SearchResult] = []
        for position, item in enumerate(payload.get("chunks", [])):
            metadata: dict[str, Any] = item.get("metadata", {})
            content = str(item.get("text") or "")
            if not content.strip():
                continue
            chunk_index = int(metadata.get("chunk_index", position))
            chunks.append(
                SearchResult(
                    chunk_id=hashlib.sha256(
                        f"{document_hash}:{chunk_index}:{content}".encode("utf-8")
                    ).hexdigest(),
                    content=content,
                    similarity=0.0,
                    document_id=document_id,
                    title=metadata.get("title") or None,
                    file_name=str(metadata.get("file_name") or ""),
                    file_path=str(metadata.get("file_path") or ""),
                    page_start=metadata.get("page_start"),
                    page_end=metadata.get("page_end"),
                    section=metadata.get("section") or None,
                    chunk_index=chunk_index,
                    document_hash=document_hash,
                    processed_at=str(metadata.get("processed_at") or ""),
                )
            )
        if not chunks:
            raise ValueError("Arquivo sem chunks textuais")
        return document_id, chunks
