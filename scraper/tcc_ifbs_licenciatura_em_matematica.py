from pathlib import Path
from urllib.parse import urljoin
import math
import re
import time

from playwright.sync_api import sync_playwright


URL_BASE = "https://repositorio.ifb.edu.br"

URL_LISTAGEM = (
    "https://repositorio.ifb.edu.br/browse/program?"
    "scope=def25d48-ac31-4be7-a9ba-ae77c02a1e3e&"
    "value=Licenciatura%20em%20Matem%C3%A1tica&"
    "bbm.page={pagina}"
)

PASTA_DOWNLOADS = Path("pdfs_ifb")
ITENS_POR_PAGINA = 20


def limpar_nome_arquivo(nome: str) -> str:
    nome = re.sub(r'[<>:"/\\|?*]', "_", nome)
    nome = nome.strip()

    if not nome.lower().endswith(".pdf"):
        nome += ".pdf"

    return nome


def obter_total_paginas(page) -> int:
    info = page.locator("div.pagination-info")
    info.wait_for(state="visible")

    texto = info.inner_text().strip()

    match = re.search(r"(\d+)\s*-\s*(\d+)\s*de\s*(\d+)", texto)

    if not match:
        raise RuntimeError(
            f"Não foi possível extrair a paginação de: {texto}"
        )

    inicio = int(match.group(1))
    fim = int(match.group(2))
    total_itens = int(match.group(3))

    quantidade_pagina_atual = fim - inicio + 1

    if quantidade_pagina_atual <= 0:
        quantidade_pagina_atual = ITENS_POR_PAGINA

    total_paginas = math.ceil(total_itens / ITENS_POR_PAGINA)

    print(f"Total de itens: {total_itens}")
    print(f"Total de páginas: {total_paginas}")

    return total_paginas


def coletar_links_trabalhos(page) -> list[str]:
    seletor = 'a.item-list-title[href^="/items/"]'

    page.locator(seletor).first.wait_for(state="visible")

    links = []

    for elemento in page.locator(seletor).all():
        href = elemento.get_attribute("href")

        if not href:
            continue

        url = urljoin(URL_BASE, href)

        if url not in links:
            links.append(url)

    return links


def baixar_pdf_da_pagina(page, url_trabalho: str) -> Path | None:
    print(f"\nAbrindo trabalho: {url_trabalho}")

    page.goto(
        url_trabalho,
        wait_until="domcontentloaded",
        timeout=60_000,
    )

    seletor_pdf = (
        'ds-file-download-link a[href*="/bitstreams/"], '
        'a[href*="/bitstreams/"][href$="/download"]'
    )

    link_pdf = page.locator(seletor_pdf).first

    try:
        link_pdf.wait_for(state="attached", timeout=20_000)
    except Exception:
        print("Nenhum PDF encontrado nessa página.")
        return None

    href = link_pdf.get_attribute("href")

    if not href:
        print("O link do PDF não possui href.")
        return None

    nome_arquivo = ""

    spans = link_pdf.locator("span")

    if spans.count() > 0:
        nome_arquivo = spans.first.inner_text().strip()

    if not nome_arquivo:
        nome_arquivo = href.rstrip("/").split("/")[-2] + ".pdf"

    nome_arquivo = limpar_nome_arquivo(nome_arquivo)

    PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)

    caminho = PASTA_DOWNLOADS / nome_arquivo

    if caminho.exists() and caminho.stat().st_size > 0:
        print(f"Já existe, pulando: {caminho.name}")
        return caminho

    url_download = urljoin(page.url, href)

    resposta = page.request.get(
        url_download,
        timeout=60_000,
    )

    if not resposta.ok:
        raise RuntimeError(
            f"Erro HTTP {resposta.status} ao baixar {url_download}"
        )

    conteudo = resposta.body()

    if not conteudo.startswith(b"%PDF"):
        content_type = resposta.headers.get("content-type", "")

        print(
            "Aviso: o arquivo não começa com assinatura PDF. "
            f"Content-Type: {content_type}"
        )

    caminho.write_bytes(conteudo)

    print(f"Baixado: {caminho.name}")

    return caminho


def executar():
    PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=50,
        )

        context = browser.new_context(
            accept_downloads=True,
        )

        pagina_listagem = context.new_page()
        pagina_trabalho = context.new_page()

        primeira_url = URL_LISTAGEM.format(pagina=1)

        pagina_listagem.goto(
            primeira_url,
            wait_until="domcontentloaded",
            timeout=60_000,
        )

        total_paginas = obter_total_paginas(pagina_listagem)

        todos_links = []

        for numero_pagina in range(1, total_paginas + 1):
            url_pagina = URL_LISTAGEM.format(
                pagina=numero_pagina
            )

            print(f"\nLendo página {numero_pagina}/{total_paginas}")

            pagina_listagem.goto(
                url_pagina,
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            links_pagina = coletar_links_trabalhos(
                pagina_listagem
            )

            print(
                f"Trabalhos encontrados nesta página: "
                f"{len(links_pagina)}"
            )

            for link in links_pagina:
                if link not in todos_links:
                    todos_links.append(link)

        print(f"\nTotal de trabalhos coletados: {len(todos_links)}")

        baixados = 0
        falhas = 0

        for indice, url_trabalho in enumerate(
            todos_links,
            start=1,
        ):
            print(
                f"\n[{indice}/{len(todos_links)}]"
            )

            try:
                arquivo = baixar_pdf_da_pagina(
                    pagina_trabalho,
                    url_trabalho,
                )

                if arquivo:
                    baixados += 1

            except Exception as erro:
                falhas += 1
                print(f"Erro ao processar trabalho: {erro}")

            time.sleep(0.5)

        print("\n" + "=" * 50)
        print(f"Trabalhos encontrados: {len(todos_links)}")
        print(f"PDFs baixados ou já existentes: {baixados}")
        print(f"Falhas: {falhas}")
        print(
            f"Pasta: {PASTA_DOWNLOADS.resolve()}"
        )
        print("=" * 50)

        browser.close()


if __name__ == "__main__":
    executar()