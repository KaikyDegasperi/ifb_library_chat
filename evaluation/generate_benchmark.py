"""Geração determinística de candidatos, sempre sujeitos à revisão humana."""

import argparse
import json
import random
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from app.config import get_settings
from evaluation.models import Benchmark, BenchmarkQuestion
from evaluation.io import write_benchmark, write_benchmark_xlsx


QUESTION_TYPES = [
    "informação factual", "objetivo do trabalho", "metodologia",
    "resultado ou conclusão", "definição conceitual", "comparação",
    "síntese limitada a um documento",
]
DIFFICULTIES = ["facil", "media", "dificil"]
EXCLUDED_SECTIONS = re.compile(
    r"(?i)(refer[eê]ncias|bibliografia|folha de aprova|instituto federal|trabalho de conclus[aã]o|"
    r"\banexo\b|\bap[eê]ndice\b|\bsum[aá]rio\b|lista de|banca examinadora)"
)
STOPWORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "esse", "esta", "este", "foi", "mais", "na", "nas", "no", "nos",
    "o", "os", "para", "por", "que", "se", "sua", "um", "uma",
}


def load_chunks(processed_dir: Path) -> dict[str, list[dict[str, Any]]]:
    documents: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(processed_dir.glob("*.chunks.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            chunks = payload.get("chunks", [])
            if chunks:
                file_name = chunks[0].get("metadata", {}).get("file_name")
                if file_name:
                    documents[file_name] = chunks
        except (OSError, ValueError, TypeError):
            continue
    return documents


def eligible_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for chunk in chunks:
        text = re.sub(r"\s+", " ", str(chunk.get("text", ""))).strip()
        metadata = chunk.get("metadata", {})
        section = str(metadata.get("section") or "")
        page = metadata.get("page_start")
        if len(text) < 220 or not isinstance(page, int) or EXCLUDED_SECTIONS.search(section):
            continue
        if re.search(r"(?i)documento assinado|c[oó]digo de autentica[cç][aã]o", text) or text.count(". .") > 4:
            continue
        result.append(chunk)
    return result


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _topic(text: str) -> str:
    words = re.findall(r"[a-zà-ÿ]{4,}", _fold(text))
    common = [word for word, _ in Counter(word for word in words if word not in STOPWORDS).most_common(3)]
    return ", ".join(common) or "o tema investigado"


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    values = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])", cleaned)
    return [value.strip() for value in values if 45 <= len(value.strip()) <= 500]


def _question_type(section: str, index: int) -> str:
    del section
    return QUESTION_TYPES[index % len(QUESTION_TYPES)]


def build_answerable(identifier: str, chunk: dict[str, Any], index: int) -> BenchmarkQuestion:
    metadata = chunk["metadata"]
    text = re.sub(r"\s+", " ", str(chunk["text"])).strip()
    sentences = _sentences(text)
    evidence = " ".join(sentences[:2])[:700] if sentences else text[:700]
    facts = sentences[:2] if sentences else [evidence]
    section = str(metadata.get("section") or "seção indicada")
    body = re.sub(rf"(?i)^\s*{re.escape(section)}\s*", "", text).strip()
    if len(body) >= 100:
        text = body
        sentences = _sentences(text)
        evidence = " ".join(sentences[:2])[:700] if sentences else text[:700]
        facts = sentences[:2] if sentences else [evidence]
    title = str(metadata.get("title") or metadata["file_name"])
    question_type = _question_type(section, index)
    topic = _topic(evidence)
    stems = {
        "informação factual": f"Qual informação o trabalho “{title}” apresenta sobre {topic}?",
        "objetivo do trabalho": f"Qual objetivo ou propósito o trabalho “{title}” associa a {topic}?",
        "metodologia": f"Como o trabalho “{title}” investigou {topic}?",
        "resultado ou conclusão": f"Que resultado ou conclusão o trabalho “{title}” apresenta sobre {topic}?",
        "definição conceitual": f"Como o trabalho “{title}” caracteriza {topic}?",
        "comparação": f"Que relação ou contraste o trabalho “{title}” estabelece ao discutir {topic}?",
        "síntese limitada a um documento": f"Segundo apenas o trabalho “{title}”, como pode ser sintetizada a discussão sobre {topic}?",
    }
    page_start = int(metadata["page_start"])
    page_end = int(metadata.get("page_end") or page_start)
    return BenchmarkQuestion(
        id=identifier, question=stems[question_type], answerable=True,
        question_type=question_type, difficulty=DIFFICULTIES[index % 3],
        expected_answer=evidence, required_facts=facts,
        expected_document=metadata["file_name"],
        expected_pages=list(range(page_start, page_end + 1)), evidence=evidence,
        section=metadata.get("section"), split="development", status="pending_review",
        rationale="Candidato derivado de trecho processado pelo Docling; exige conferência manual no PDF.",
    )


UNANSWERABLES = [
    ("Qual foi o consumo mensal de energia elétrica do laboratório de informática do campus em 2025?", "Dados operacionais de consumo do campus não integram o acervo de TCCs."),
    ("Qual é a senha atual da rede sem fio administrativa do campus?", "Credenciais administrativas não pertencem ao acervo e não devem ser fornecidas."),
    ("Qual será o cardápio completo do restaurante estudantil na próxima semana?", "Informação futura e operacional não consta dos TCCs."),
    ("Qual é a lotação em tempo real do estacionamento do campus?", "Dado em tempo real não está contido no acervo estático."),
    ("Qual foi a temperatura registrada no campus às 14h de ontem?", "Medição meteorológica pontual não pertence ao acervo."),
    ("Quais são os telefones pessoais atuais de todos os autores dos TCCs?", "Dados pessoais atuais não são conteúdo acadêmico necessário nem verificável no acervo."),
    ("Qual será a data exata da próxima manutenção do elevador do campus?", "Agenda operacional futura não pertence ao acervo."),
    ("Qual é o saldo bancário atual da associação de estudantes?", "Informação financeira atual e privada não integra os TCCs."),
    ("Quem vencerá a próxima eleição para a direção do campus?", "Previsão de evento futuro não pode ser sustentada pelo acervo."),
    ("Qual é a localização em tempo real de cada servidor do campus?", "Rastreamento pessoal em tempo real não pertence ao acervo e é inadequado."),
]


def generate_benchmark(processed_dir: Path, questions: int, unanswerable_ratio: float, seed: int) -> Benchmark:
    unanswerable_count = round(questions * unanswerable_ratio)
    answerable_count = questions - unanswerable_count
    if questions != 50 or unanswerable_count != 10:
        raise ValueError("Este benchmark versionado exige exatamente 50 perguntas, sendo 10 sem resposta")
    randomizer = random.Random(seed)
    documents = load_chunks(processed_dir)
    candidates: list[tuple[str, dict[str, Any]]] = []
    names = sorted(documents)
    randomizer.shuffle(names)
    pools = {name: eligible_chunks(documents[name]) for name in names}
    for index, name in enumerate(names):
        if pools[name]:
            target_type = QUESTION_TYPES[index % len(QUESTION_TYPES)]
            preferred = sorted(pools[name], key=lambda chunk: _candidate_score(chunk, target_type), reverse=True)
            top = preferred[: min(4, len(preferred))]
            candidates.append((name, randomizer.choice(top)))
    offset = 0
    while len(candidates) < answerable_count:
        usable = [name for name in names if pools[name]]
        if not usable:
            break
        name = usable[offset % len(usable)]
        candidates.append((name, pools[name][offset % len(pools[name])]))
        offset += 1
    if len(candidates) < answerable_count:
        raise ValueError(f"Apenas {len(candidates)} candidatos verificáveis foram encontrados")
    answerables = [build_answerable("", chunk, index) for index, (_, chunk) in enumerate(candidates[:answerable_count])]
    unanswerables = [
        BenchmarkQuestion(
            id="", question=question, answerable=False, question_type="pergunta sem resposta no acervo",
            difficulty=DIFFICULTIES[index % 3],
            expected_answer="O sistema deve recusar claramente e informar que a resposta não foi encontrada no acervo.",
            required_facts=["Informar que a resposta não foi encontrada no acervo."],
            expected_document=None, expected_pages=[], evidence="", section=None,
            split="development", status="pending_review", rationale=reason,
            unanswerable_reason=reason,
        ) for index, (question, reason) in enumerate(UNANSWERABLES)
    ]
    # Cada metade recebe 20 respondíveis e 5 não respondíveis.
    ordered = answerables[:20] + unanswerables[:5] + answerables[20:] + unanswerables[5:]
    for index, item in enumerate(ordered, 1):
        item.id = f"Q{index:03d}"
        item.split = "development" if index <= 25 else "final"
    return Benchmark(seed=seed, questions=ordered)


def _candidate_score(chunk: dict[str, Any], question_type: str) -> tuple[int, int]:
    section = _fold(str(chunk.get("metadata", {}).get("section") or ""))
    text = _fold(str(chunk.get("text", "")))
    markers = {
        "informação factual": ("resumo", "resultado", "analise"),
        "objetivo do trabalho": ("objetiv", "introdu", "resumo"),
        "metodologia": ("metod", "materiais", "procedimento"),
        "resultado ou conclusão": ("resultado", "conclu", "considera"),
        "definição conceitual": ("fundament", "referencial", "conceito", "teorico"),
        "comparação": ("compar", "diferenc", "relacao", "contraste"),
        "síntese limitada a um documento": ("resumo", "conclu", "considera"),
    }[question_type]
    score = sum(10 for marker in markers if marker in section) + sum(2 for marker in markers if marker in text)
    return score, min(len(text), 2_000)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Gera candidatos ao benchmark")
    parser.add_argument("--questions", type=int, default=50)
    parser.add_argument("--unanswerable-ratio", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--processed-dir", type=Path, default=settings.processed_dir)
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/benchmark"))
    args = parser.parse_args()
    benchmark = generate_benchmark(args.processed_dir, args.questions, args.unanswerable_ratio, args.seed)
    write_benchmark(args.output_dir / "benchmark_draft.json", benchmark)
    write_benchmark_xlsx(args.output_dir / "benchmark_draft.xlsx", benchmark, settings.documents_dir)
    print("Gerados 50 candidatos (40 respondíveis, 10 sem resposta), todos pending_review.")


if __name__ == "__main__":
    main()
