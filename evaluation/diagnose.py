"""Diagnóstico estrutural do acervo de PDFs."""

import argparse
import json
import re
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium

from app.config import get_settings
from evaluation.io import write_csv, write_json


def load_processed_metadata(processed_dir: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in processed_dir.glob("*.chunks.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            chunks = payload.get("chunks", [])
            if not chunks:
                continue
            metadata = chunks[0].get("metadata", {})
            file_name = metadata.get("file_name")
            if file_name:
                result[file_name] = {"chunks": chunks, "metadata": metadata}
        except (OSError, ValueError, TypeError):
            continue
    return result


def diagnose_pdf(path: Path, processed: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {
        "file_name": path.name,
        "size_bytes": path.stat().st_size,
        "page_count": 0,
        "approximate_characters": 0,
        "average_characters_per_page": 0.0,
        "extractable_text": False,
        "likely_ocr_needed": False,
        "empty_pages": [],
        "title": None,
        "author": None,
        "year": None,
        "abstract": None,
        "keywords": [],
        "sections": [],
        "status": "ok",
        "reason": "",
    }
    try:
        document = pdfium.PdfDocument(path)
        page_texts: list[str] = []
        try:
            for page_index in range(len(document)):
                page = document[page_index]
                try:
                    text_page = page.get_textpage()
                    try:
                        page_texts.append(text_page.get_text_range() or "")
                    finally:
                        text_page.close()
                finally:
                    page.close()
        finally:
            document.close()
        counts = [len(re.sub(r"\s+", " ", text).strip()) for text in page_texts]
        base["page_count"] = len(counts)
        base["approximate_characters"] = sum(counts)
        base["average_characters_per_page"] = round(sum(counts) / len(counts), 2) if counts else 0.0
        base["empty_pages"] = [index + 1 for index, count in enumerate(counts) if count < 20]
        base["extractable_text"] = sum(counts) >= max(100, len(counts) * 50)
        empty_ratio = len(base["empty_pages"]) / len(counts) if counts else 1.0
        base["likely_ocr_needed"] = not base["extractable_text"] or empty_ratio > 0.35
        if base["likely_ocr_needed"]:
            base["status"] = "warning"
            base["reason"] = "Pouco texto extraível; OCR provavelmente necessário."
        elif base["empty_pages"]:
            base["status"] = "warning"
            base["reason"] = "Há páginas sem texto extraível."
    except Exception as exc:
        base["status"] = "error"
        base["reason"] = f"{type(exc).__name__}: não foi possível ler o PDF"

    if processed:
        chunks = processed.get("chunks", [])
        metadata = processed.get("metadata", {})
        base.update(
            title=metadata.get("title"),
            author=metadata.get("author"),
            year=metadata.get("year"),
            abstract=_extract_abstract(chunks),
            keywords=_extract_keywords(chunks),
            sections=_sections(chunks),
        )
    elif base["status"] == "ok":
        base["status"] = "warning"
        base["reason"] = "PDF ainda não possui artefato processado pelo Docling."
    return base


def _extract_abstract(chunks: list[dict[str, Any]]) -> str | None:
    for chunk in chunks:
        text = str(chunk.get("text", "")).strip()
        section = str(chunk.get("metadata", {}).get("section", ""))
        if re.search(r"(?i)\b(resumo|abstract)\b", section) or re.match(r"(?i)^resumo\b", text):
            cleaned = re.sub(r"(?i)^\s*resumo\s*", "", text).strip()
            cleaned = re.split(r"(?i)\bpalavras[- ]chave\s*:", cleaned, maxsplit=1)[0]
            return cleaned[:2_000] or None
    return None


def _extract_keywords(chunks: list[dict[str, Any]]) -> list[str]:
    for chunk in chunks:
        match = re.search(r"(?is)palavras[- ]chave\s*:\s*([^\n]+)", str(chunk.get("text", "")))
        if match:
            return [item.strip(" .") for item in re.split(r"[;,]", match.group(1)) if item.strip()][:12]
    return []


def _sections(chunks: list[dict[str, Any]]) -> list[str]:
    values = [
        str(chunk.get("metadata", {}).get("section", "")).strip()
        for chunk in chunks
    ]
    return list(dict.fromkeys(value for value in values if value))[:50]


def diagnose_corpus(input_dir: Path, processed_dir: Path) -> list[dict[str, Any]]:
    processed = load_processed_metadata(processed_dir)
    return [diagnose_pdf(path, processed.get(path.name)) for path in sorted(input_dir.glob("*.pdf"))]


def render_html(rows: list[dict[str, Any]]) -> str:
    statuses = Counter(row["status"] for row in rows)
    body = []
    for row in rows:
        body.append(
            "<tr data-status='{status}'><td>{file}</td><td>{status}</td><td>{pages}</td>"
            "<td>{chars}</td><td>{ocr}</td><td>{title}</td><td>{author}</td><td>{year}</td>"
            "<td>{empty}</td><td>{reason}</td></tr>".format(
                status=escape(row["status"]), file=escape(row["file_name"]),
                pages=row["page_count"], chars=row["approximate_characters"],
                ocr="sim" if row["likely_ocr_needed"] else "não",
                title=escape(str(row["title"] or "")), author=escape(str(row["author"] or "")),
                year=escape(str(row["year"] or "")), empty=escape(", ".join(map(str, row["empty_pages"]))),
                reason=escape(row["reason"]),
            )
        )
    return f"""<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Diagnóstico do acervo</title>
<style>body{{font:14px system-ui;margin:2rem;color:#17202a}}.cards{{display:flex;gap:1rem}}.card{{padding:1rem;border:1px solid #ccd;border-radius:8px}}table{{border-collapse:collapse;width:100%;margin-top:1rem}}th,td{{border:1px solid #ddd;padding:.5rem;text-align:left;vertical-align:top}}th{{background:#163a5f;color:white;position:sticky;top:0}}select{{padding:.5rem}}</style>
<h1>Diagnóstico do acervo</h1><div class='cards'><div class='card'>PDFs: <strong>{len(rows)}</strong></div><div class='card'>OK: <strong>{statuses['ok']}</strong></div><div class='card'>Avisos: <strong>{statuses['warning']}</strong></div><div class='card'>Erros: <strong>{statuses['error']}</strong></div></div>
<p><label>Status <select id='filter'><option value=''>todos</option><option>ok</option><option>warning</option><option>error</option></select></label></p>
<table><thead><tr><th>Arquivo</th><th>Status</th><th>Páginas</th><th>Caracteres</th><th>OCR?</th><th>Título</th><th>Autor</th><th>Ano</th><th>Páginas vazias</th><th>Motivo</th></tr></thead><tbody>{''.join(body)}</tbody></table>
<script>document.querySelector('#filter').onchange=e=>document.querySelectorAll('tbody tr').forEach(r=>r.hidden=e.target.value&&r.dataset.status!==e.target.value)</script></html>"""


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Diagnostica os PDFs do acervo")
    parser.add_argument("--input", type=Path, default=settings.documents_dir)
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results"))
    args = parser.parse_args()
    if not args.input.is_dir():
        parser.error(f"Pasta inexistente: {args.input}")
    rows = diagnose_corpus(args.input, settings.processed_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "corpus_diagnostics.json", {"summary": dict(Counter(row["status"] for row in rows)), "documents": rows})
    write_csv(args.output_dir / "corpus_diagnostics.csv", rows)
    (args.output_dir / "corpus_diagnostics.html").write_text(render_html(rows), encoding="utf-8")
    print(f"Diagnosticados {len(rows)} PDFs em {args.output_dir}")


if __name__ == "__main__":
    main()
