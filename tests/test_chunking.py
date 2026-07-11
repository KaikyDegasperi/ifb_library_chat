import pytest

from app.ingestion.chunking import clean_text, split_with_overlap


def test_split_respects_size_and_overlap() -> None:
    text = " ".join(f"palavra-{index}" for index in range(12))

    chunks = split_with_overlap(text, chunk_size=5, overlap=2)

    assert len(chunks) == 4
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError, match="menor que chunk_size"):
        split_with_overlap("texto", chunk_size=10, overlap=10)


def test_clean_text_is_minimal() -> None:
    assert clean_text("Linha 1  \r\n\r\n\r\nLinha 2") == "Linha 1\n\nLinha 2"
