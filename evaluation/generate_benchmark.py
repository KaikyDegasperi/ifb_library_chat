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
    ("Quais estudantes estão atualmente com livros atrasados na biblioteca?", "Registros atuais de empréstimo são dados administrativos e pessoais fora do acervo."),
    ("Qual é o inventário atualizado dos computadores dos laboratórios?", "O inventário patrimonial atual não integra os TCCs."),
    ("Quais serão as próximas aquisições da biblioteca e suas datas exatas?", "Planejamento futuro de compras não pode ser determinado pelo acervo estático."),
    ("Quais são as notas atuais de cada estudante matriculado no curso?", "Notas individuais atuais são dados pessoais protegidos e não pertencem ao acervo."),
    ("Qual é a escala de trabalho dos servidores da biblioteca nesta semana?", "Escalas atuais de pessoal são dados operacionais que não integram os TCCs."),
    ("Quantas pessoas estão dentro da biblioteca neste momento?", "Ocupação em tempo real não pode ser obtida de um acervo documental estático."),
]


def generate_corpus_benchmark(processed_dir: Path, seed: int = 42) -> Benchmark:
    """Gera dois casos verificáveis por documento e 14 casos sem resposta."""
    randomizer = random.Random(seed)
    documents = load_chunks(processed_dir)
    if len(documents) != 43:
        raise ValueError(
            f"O benchmark 2.0 exige 43 documentos processados; encontrados {len(documents)}"
        )

    development: list[BenchmarkQuestion] = []
    final: list[BenchmarkQuestion] = []
    excluded_documents: dict[str, str] = {}
    for index, name in enumerate(sorted(documents)):
        candidates = eligible_chunks(documents[name])
        if len(candidates) < 2:
            excluded_documents[name] = (
                "Conteúdo insuficiente para duas perguntas verificáveis: "
                f"{len(candidates)} trecho(s) elegível(is) após extração/OCR."
            )
            continue
        randomizer.shuffle(candidates)
        first_type = QUESTION_TYPES[index % len(QUESTION_TYPES)]
        second_type = QUESTION_TYPES[(index + 3) % len(QUESTION_TYPES)]
        first = max(candidates, key=lambda chunk: _candidate_score(chunk, first_type))
        remaining = [chunk for chunk in candidates if chunk is not first]
        second = max(remaining, key=lambda chunk: _candidate_score(chunk, second_type))
        development.append(build_answerable("", first, index))
        final.append(build_answerable("", second, index + len(documents)))

    if len(development) != 42 or len(excluded_documents) != 1:
        raise ValueError(
            "O benchmark 2.0 exige 42 TCCs avaliáveis e uma exclusão documental "
            f"justificada; obtidos {len(development)} e {len(excluded_documents)}"
        )
    negatives = [
        BenchmarkQuestion(
            id="",
            question=question,
            answerable=False,
            question_type="pergunta sem resposta no acervo",
            difficulty=DIFFICULTIES[index % 3],
            expected_answer=(
                "O sistema deve recusar claramente e informar que a resposta não foi "
                "encontrada no acervo."
            ),
            required_facts=["Informar que a resposta não foi encontrada no acervo."],
            expected_document=None,
            expected_pages=[],
            evidence="",
            section=None,
            split="development",
            status="pending_review",
            rationale=reason,
            unanswerable_reason=reason,
        )
        for index, (question, reason) in enumerate(UNANSWERABLES)
    ]
    ordered = development + negatives[:8] + final + negatives[8:16]
    for index, item in enumerate(ordered, 1):
        item.id = f"Q{index:03d}"
        item.split = "development" if index <= 50 else "final"
    return Benchmark(
        benchmark_version="2.0",
        seed=seed,
        excluded_documents=excluded_documents,
        questions=ordered,
    )


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
        ) for index, (question, reason) in enumerate(UNANSWERABLES[:unanswerable_count])
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
    parser.add_argument(
        "--full-corpus",
        action="store_true",
        help="Gera o benchmark 2.0 com 100 perguntas e cobertura dos 43 TCCs",
    )
    args = parser.parse_args()
    benchmark = (
        generate_corpus_benchmark(args.processed_dir, args.seed)
        if args.full_corpus
        else generate_benchmark(
            args.processed_dir, args.questions, args.unanswerable_ratio, args.seed
        )
    )
    suffix = "full_corpus_draft" if args.full_corpus else "benchmark_draft"
    write_benchmark(args.output_dir / f"{suffix}.json", benchmark)
    write_benchmark_xlsx(
        args.output_dir / f"{suffix}.xlsx", benchmark, settings.documents_dir
    )
    print(
        f"Gerados {len(benchmark.questions)} candidatos do benchmark "
        f"{benchmark.benchmark_version}, todos pending_review."
    )


if __name__ == "__main__":
    main()
