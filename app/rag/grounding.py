"""Classifica recusas e alinha citações com as fontes públicas."""

import re

from app.rag.models import RAGSource

REFUSAL_PATTERN = re.compile(
    r"(?i)(n[aã]o (?:encontrei|foi poss[ií]vel encontrar|consta|h[aá])|"
    r"informa[cç][aã]o (?:n[aã]o|insuficiente)|"
    r"n[aã]o est[aá] (?:dispon[ií]vel|no acervo))"
)
CITATION_PATTERN = re.compile(r"\[Fonte\s+(\d+)\]", re.IGNORECASE)


def is_refusal(answer: str) -> bool:
    match = REFUSAL_PATTERN.search(answer)
    return bool(match and match.start() <= 80)


def align_public_sources(
    answer: str,
    retrieved_context: list[RAGSource],
) -> tuple[str, list[RAGSource]]:
    """Remove fontes de recusas e renumera somente as fontes citadas."""
    if is_refusal(answer):
        return answer, []
    cited = [
        int(value)
        for value in CITATION_PATTERN.findall(answer)
        if 1 <= int(value) <= len(retrieved_context)
    ]
    ordered = list(dict.fromkeys(cited))
    mapping = {old: new for new, old in enumerate(ordered, 1)}

    def replace(match: re.Match[str]) -> str:
        old = int(match.group(1))
        return f"[Fonte {mapping[old]}]" if old in mapping else ""

    aligned_answer = CITATION_PATTERN.sub(replace, answer)
    return aligned_answer, [retrieved_context[index - 1] for index in ordered]
