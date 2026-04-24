from __future__ import annotations

import argparse
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_PAGE = (
    "https://www.ibge.gov.br/estatisticas/sociais/populacao/"
    "38734-cadastro-nacional-de-enderecos-para-fins-estatisticos.html?=&t=downloads"
)
FTP_FALLBACK = (
    "https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/"
    "Censo_Demografico_2022/Arquivos_CNEFE/CSV/UF/"
)

UF_SIGLAS = {
    "RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB", "PE",
    "AL", "SE", "BA", "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO", "DF"
}


def log(msg: str) -> None:
    print(msg, flush=True)


def normalizar_filtros_ufs(ufs: Optional[Iterable[str]]) -> Optional[Set[str]]:
    if not ufs:
        return None
    saida = {uf.strip().upper() for uf in ufs if uf and uf.strip()}
    invalidas = sorted(saida - UF_SIGLAS)
    if invalidas:
        raise ValueError(f"UF(s) inválida(s): {', '.join(invalidas)}")
    return saida


def inferir_uf_do_nome(nome_arquivo: str) -> Optional[str]:
    m = re.search(r"(?:^|[_-])(\d{2})_([A-Z]{2})\.zip$", nome_arquivo.upper())
    if m:
        return m.group(2)
    return None


def link_eh_zip_cnefe_uf(url: str) -> bool:
    url_upper = url.upper()
    return (
        url_upper.endswith(".ZIP")
        and "/ARQUIVOS_CNEFE/CSV/UF/" in url_upper
    )


def coletar_links_via_playwright(headless: bool = False, timeout_ms: int = 60000) -> List[str]:
    links: Set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=headless)
        page = browser.new_page()

        try:
            log(f"Abrindo página: {BASE_PAGE}")
            page.goto(BASE_PAGE, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(3000)

            # Em muitos casos o IBGE renderiza a árvore de downloads após a interação.
            textos_expansao = [
                "Censo_Demografico_2022",
                "Arquivos_CNEFE",
                "CSV",
                "UF",
            ]

            for texto in textos_expansao:
                try:
                    locator = page.locator(f"text={texto}").first
                    locator.wait_for(timeout=5000)
                    locator.click(timeout=5000)
                    page.wait_for_timeout(1200)
                except Exception:
                    # Não falha por isso, pois às vezes a pasta já está aberta.
                    pass

            # Captura todos os hrefs possíveis após abrir a árvore.
            hrefs = page.locator("a").evaluate_all(
                "els => els.map(e => e.href).filter(Boolean)"
            )
            for href in hrefs:
                if isinstance(href, str) and link_eh_zip_cnefe_uf(href):
                    links.add(href)

            # Fallback de parsing do HTML caso o href esteja em atributos ou scripts.
            html = page.content()
            for match in re.findall(r'https?://[^\"\'\s>]+?\.zip', html, flags=re.IGNORECASE):
                if link_eh_zip_cnefe_uf(match):
                    links.add(match)

        except PlaywrightTimeoutError as e:
            log(f"Timeout ao navegar na página do IBGE: {e}")
        finally:
            browser.close()

    return sorted(links)


def coletar_links_via_ftp_index(timeout: int = 60) -> List[str]:
    log(f"Lendo índice FTP: {FTP_FALLBACK}")
    resp = requests.get(FTP_FALLBACK, timeout=timeout)
    resp.raise_for_status()

    links: Set[str] = set()
    for href in re.findall(r'href=["\']([^"\']+\.zip)["\']', resp.text, flags=re.IGNORECASE):
        url = urljoin(FTP_FALLBACK, href)
        if link_eh_zip_cnefe_uf(url):
            links.add(url)

    # Se o índice vier em texto simples sem href clássico.
    for nome in re.findall(r'(\d{2}_[A-Z]{2}\.zip)', resp.text, flags=re.IGNORECASE):
        url = urljoin(FTP_FALLBACK, nome)
        if link_eh_zip_cnefe_uf(url):
            links.add(url)

    return sorted(links)


def filtrar_links_por_uf(links: Iterable[str], filtro_ufs: Optional[Set[str]]) -> List[str]:
    filtrados = []
    for link in links:
        nome = Path(urlparse(link).path).name
        uf = inferir_uf_do_nome(nome)
        if filtro_ufs is None or (uf in filtro_ufs):
            filtrados.append(link)
    return sorted(set(filtrados))


def baixar_arquivo(url: str, destino: Path, timeout: int = 120, chunk_size: int = 1024 * 1024) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0:
        log(f"[skip] Já existe: {destino.name}")
        return

    log(f"[down] {destino.name}")
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        baixado = 0
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                baixado += len(chunk)
                if total:
                    pct = (baixado / total) * 100
                    print(f"\r    {baixado/1024/1024:.1f} MB / {total/1024/1024:.1f} MB ({pct:.1f}%)", end="", flush=True)
        if total:
            print()


def extrair_zip(zip_path: Path, pasta_destino: Path) -> List[Path]:
    pasta_destino.mkdir(parents=True, exist_ok=True)
    extraidos: List[Path] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(pasta_destino)
        for nome in zf.namelist():
            extraidos.append(pasta_destino / nome)
    return extraidos


def escrever_manifesto(caminho: Path, links: List[str], pastas_extraidas: List[Path]) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("LINKS BAIXADOS\n")
        f.write("=" * 80 + "\n")
        for link in links:
            f.write(link + "\n")
        f.write("\nPASTAS EXTRAIDAS\n")
        f.write("=" * 80 + "\n")
        for pasta in pastas_extraidas:
            f.write(str(pasta) + "\n")




def resolver_pasta_padrao() -> Path:
    """
    Define a pasta padrão de saída de forma robusta.

    Casos tratados:
    - execução normal do arquivo .py -> usa a pasta do script
    - execução via terminal interativo / notebook / stdin -> usa a pasta atual
    - execução com sys.argv[0] apontando para um arquivo -> usa a pasta desse arquivo
    """
    arquivo_atual = globals().get("__file__")
    if arquivo_atual:
        try:
            return Path(arquivo_atual).resolve().parent / "saida_cnefe_uf"
        except Exception:
            pass

    argv0 = sys.argv[0] if sys.argv else ""
    if argv0 and argv0 not in ("-c", "-m", "<stdin>"):
        try:
            caminho_argv = Path(argv0).resolve()
            if caminho_argv.suffix:
                return caminho_argv.parent / "saida_cnefe_uf"
        except Exception:
            pass

    return Path.cwd().resolve() / "saida_cnefe_uf"

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Baixa os arquivos CNEFE 2022 por UF do IBGE usando Playwright + Edge e fallback FTP."
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Pasta de saída. Se omitido, salva em uma pasta 'saida_cnefe_uf' ao lado do script."
    )
    parser.add_argument("--headless", action="store_true", help="Executa o Edge sem interface")
    parser.add_argument(
        "--ufs",
        nargs="*",
        default=None,
        help="Filtro opcional de UF, ex.: --ufs SP RJ MG"
    )
    parser.add_argument(
        "--nao-extrair",
        action="store_true",
        help="Baixa os ZIPs, mas não extrai"
    )
    args = parser.parse_args()

    if args.outdir:
        outdir = Path(args.outdir).expanduser().resolve()
    else:
        outdir = resolver_pasta_padrao().resolve()

    log(f"Pasta de saída: {outdir}")
    pasta_zips = outdir / "zips"
    pasta_extraidos = outdir / "extraido"
    manifesto = outdir / "manifesto_cnefe_uf.txt"
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        filtro_ufs = normalizar_filtros_ufs(args.ufs)
    except ValueError as e:
        log(str(e))
        return 2

    # 1) Tenta capturar a árvore/renderização da página.
    links = []
    try:
        links = coletar_links_via_playwright(headless=args.headless)
        if links:
            log(f"Links encontrados via Playwright: {len(links)}")
    except Exception as e:
        log(f"Falha na coleta via Playwright: {e}")

    # 2) Se não encontrar, usa o índice FTP oficial.
    if not links:
        links = coletar_links_via_ftp_index()
        log(f"Links encontrados via FTP: {len(links)}")

    links = filtrar_links_por_uf(links, filtro_ufs)
    if not links:
        log("Nenhum link encontrado após aplicar os filtros.")
        return 1

    pastas_extraidas: List[Path] = []

    for link in links:
        nome_zip = Path(urlparse(link).path).name
        uf = inferir_uf_do_nome(nome_zip) or "SEM_UF"
        zip_destino = pasta_zips / nome_zip
        baixar_arquivo(link, zip_destino)

        if not args.nao_extrair:
            destino_uf = pasta_extraidos / uf
            extrair_zip(zip_destino, destino_uf)
            pastas_extraidas.append(destino_uf)
            log(f"[ok] Extraído em: {destino_uf}")

    escrever_manifesto(manifesto, links, sorted(set(pastas_extraidas)))
    log(f"Manifesto salvo em: {manifesto}")
    log("Concluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
