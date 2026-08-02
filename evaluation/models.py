"""Modelos persistidos pelo pipeline de avaliação."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


Split = Literal["development", "final"]
ReviewStatus = Literal["pending_review", "approved", "rejected"]


class BenchmarkQuestion(BaseModel):
    id: str
    question: str
    answerable: bool
    question_type: str
    difficulty: Literal["facil", "media", "dificil"]
    expected_answer: str
    required_facts: list[str] = Field(default_factory=list)
    expected_document: str | None = None
    expected_pages: list[int] = Field(default_factory=list)
    printed_pages: list[str] = Field(default_factory=list)
    evidence: str = ""
    section: str | None = None
    split: Split
    status: ReviewStatus = "pending_review"
    rationale: str = ""
    unanswerable_reason: str | None = None
    review_notes: str = ""

    @model_validator(mode="after")
    def check_source_shape(self) -> "BenchmarkQuestion":
        if self.answerable and (not self.expected_document or not self.expected_pages):
            raise ValueError(
                "Pergunta com resposta no acervo precisa de documento e página"
            )
        if not self.answerable and (self.expected_document or self.expected_pages):
            raise ValueError("Pergunta sem resposta não pode ter fonte esperada")
        return self


class Benchmark(BaseModel):
    benchmark_version: str = "1.0"
    seed: int = 42
    excluded_documents: dict[str, str] = Field(default_factory=dict)
    questions: list[BenchmarkQuestion]


class HumanScores(BaseModel):
    correctness: int | None = Field(default=None, ge=0, le=2)
    faithfulness: int | None = Field(default=None, ge=0, le=2)
    completeness: int | None = Field(default=None, ge=0, le=2)
    citation_quality: int | None = Field(default=None, ge=0, le=2)
    human_notes: str = ""


class RunRecord(HumanScores):
    id: str
    question: str
    answerable: bool
    question_type: str
    difficulty: str
    expected_answer: str
    required_facts: list[str]
    produced_answer: str = ""
    expected_document: str | None
    expected_pages: list[int]
    retrieved_documents: list[str] = Field(default_factory=list)
    retrieved_pages: list[int] = Field(default_factory=list)
    similarities: list[float] = Field(default_factory=list)
    returned_passages: list[str] = Field(default_factory=list)
    retrieval_results: list[dict] = Field(default_factory=list)
    context_results: list[dict] = Field(default_factory=list)
    context_documents: list[str] = Field(default_factory=list)
    context_pages: list[int] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    top_k: int
    similarity_threshold: float
    total_time_ms: int = 0
    retrieval_time_ms: int | None = None
    generation_time_ms: int | None = None
    refused: bool = False
    error: str | None = None
    timeout: bool = False
    timestamp: str
    split: Split
    settings: dict
    llm_judge_score: dict | None = None


class RunOutput(BaseModel):
    run_version: str = "1.0"
    benchmark_version: str
    split: Split
    started_at: str
    completed_at: str
    settings: dict
    records: list[RunRecord]
