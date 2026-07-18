from types import SimpleNamespace

from app.ingestion.academic_metadata import (
    administrative_pages,
    extract_academic_metadata,
)


def item(text: str, label: str = "text", page: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        label=SimpleNamespace(value=label),
        prov=[SimpleNamespace(page_no=page)],
    )


def test_extracts_fragmented_cover_and_academic_people() -> None:
    document = SimpleNamespace(
        texts=[
            item("Instituto Federal de Brasília"),
            item("ADAN CARDOSO FRANCO VIANA", "section_header"),
            item("DISCALCULIA NA REALIDADE ESCOLAR:", "section_header"),
            item("A percepção docente na educação básica"),
            item("BRASÍLIA 2022", "page_footer"),
            item("Orientadora: Dra. Ana Maria Libório de Oliveira", page=2),
            item("Coorientador: Me. Pedro Carvalho Brom", page=2),
            item("Discente: Adan Cardoso Franco Viana", page=3),
            item(
                "Título: DISCALCULIA NA REALIDADE ESCOLAR: a percepção "
                "docente na educação básica Trabalho aprovado em: 21/07/2022",
                page=3,
            ),
        ]
    )

    metadata = extract_academic_metadata(document, "Adan_Viana_CEST.pdf")

    assert metadata.title == (
        "DISCALCULIA NA REALIDADE ESCOLAR: "
        "A percepção docente na educação básica"
    )
    assert metadata.author == "Adan Cardoso Franco Viana"
    assert metadata.advisor == "Dra. Ana Maria Libório de Oliveira"
    assert metadata.coadvisor == "Me. Pedro Carvalho Brom"
    assert metadata.year == 2022


def test_identifies_administrative_pages() -> None:
    document = SimpleNamespace(
        texts=[
            item("1 INTRODUÇÃO", "section_header", page=4),
            item("Documento assinado eletronicamente por:", page=3),
            item("Código de Autenticação: abc123", page=3),
            item("Documento Digitalizado Público", page=18),
        ]
    )

    assert administrative_pages(document) == {3, 18}
