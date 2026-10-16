"""Monta as páginas do site a partir dos arquivos didáticos, sem editá-los.

Na hora do build, copia trilhas e catálogo para docs/. Converte só a
pontuação matemática do GitHub ($`...`$) para o formato do MathJax e ajusta
links de navegação. Os originais em materias/ e catalogo/ permanecem intactos.
"""

from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

TITLES = {
    "fundamentos-de-ciencia-de-dados": "Fundamentos de Ciência de Dados",
    "estatistica-e-inferencia": "Estatística e Inferência",
    "visualizacao-e-exploracao-de-dados": "Visualização e Exploração de Dados",
    "modelos-de-regressao": "Modelos de Regressão",
    "analise-multivariada": "Análise Multivariada e Aprendizado Não-Supervisionado",
    "machine-learning": "Machine Learning",
    "gestao-da-qualidade": "Gestão da Qualidade",
    "estatistica-e-otimizacao-cdpo": "Estatística e Otimização (CDPO)",
}

NOTEBOOKLM_WARNING = """\
!!! warning "Resumos gerados com NotebookLM"

    Os resumos foram gerados com NotebookLM e podem ter imprecisões. É preciso conferir no vídeo original da Profa. Cibele Russo.
"""

ROTEIRO = """\
## Como seguir o roteiro {#roteiro}

1. **Vídeo.** Assista à aula no canal da professora: [lista de vídeos](#videos).
2. **Aula.** Leia o resumo correspondente: [guia de aulas](#aulas).
3. **Slides.** Baixe a apresentação: [slides.pdf](slides.pdf).
4. **Exercícios.** Faça os exercícios do [guia de aulas](#aulas) e confira no vídeo original.
"""

CATALOG_INTRO = """\
---
title: Catálogo de vídeos
---

!!! note "231 vídeos, apenas linkados"

    Esta página lista os 231 vídeos do canal da Profa. Cibele Russo.
    Cada item aponta para o YouTube. Este site não hospeda nem copia os vídeos.
    O mesmo catálogo está em [catalogo.csv](catalogo.csv).
    Onze vídeos de palestras e eventos ficam fora das oito trilhas e aparecem aqui.

"""

INLINE_MATH = re.compile(r"\$`([^`]*)`\$")
LINK_REWRITES = (
    (re.compile(r"\]\(\.\./\.\./README\.md(#[^)]*)?\)"), r"](../../index.md\1)"),
    (re.compile(r"\]\((?:\./)?aulas\.md(#[^)]*)?\)"), r"](#aulas\1)"),
    (re.compile(r"\]\((?:\./)?videos\.md(#[^)]*)?\)"), r"](#videos\1)"),
    (re.compile(r"\]\((?:\./)?README\.md(#[^)]*)?\)"), r"](#roteiro\1)"),
)


def on_pre_build(config, **kwargs):
    root = Path(config.config_file_path).resolve().parent
    docs = Path(config.docs_dir)
    _reset_generated(docs)
    _assert_catalog(root)
    _write_tracks(root, docs)
    _write_catalog(root, docs)


def _reset_generated(docs: Path) -> None:
    for name in ("materias", "catalogo"):
        target = docs / name
        if target.exists():
            shutil.rmtree(target)


def _assert_catalog(root: Path) -> None:
    csv_path = root / "catalogo" / "catalogo.csv"
    md_path = root / "catalogo" / "catalogo.md"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    links = md_path.read_text(encoding="utf-8").count("https://www.youtube.com/watch?")
    if len(rows) != 231 or links != 231:
        raise RuntimeError(
            f"Catálogo deveria ter 231 vídeos (csv={len(rows)}, links={links})."
        )


def _write_tracks(root: Path, docs: Path) -> None:
    source = root / "materias"
    found = sorted(path.name for path in source.iterdir() if path.is_dir())
    expected = sorted(TITLES)
    if found != expected:
        raise RuntimeError(f"Trilhas encontradas {found} diferem de {expected}.")

    for slug, title in TITLES.items():
        origin = source / slug
        dest = docs / "materias" / slug
        dest.mkdir(parents=True)
        _copy_assets(origin, dest)
        page = _compose_track(origin, title)
        (dest / "index.md").write_text(page, encoding="utf-8")


def _copy_assets(origin: Path, dest: Path) -> None:
    pdf = origin / "slides.pdf"
    images = origin / "imagens"
    if not pdf.is_file():
        raise RuntimeError(f"Slides ausentes em {origin}.")
    shutil.copy2(pdf, dest / "slides.pdf")
    if not images.is_dir():
        raise RuntimeError(f"Imagens ausentes em {origin}.")
    target = dest / "imagens"
    target.mkdir()
    svgs = sorted(images.glob("*.svg"))
    if not svgs:
        raise RuntimeError(f"Nenhum SVG em {images}.")
    for svg in svgs:
        shutil.copy2(svg, target / svg.name)


def _compose_track(origin: Path, title: str) -> str:
    readme = _prepare_markdown((origin / "README.md").read_text(encoding="utf-8"))
    videos = _prepare_markdown((origin / "videos.md").read_text(encoding="utf-8"))
    aulas = _prepare_markdown((origin / "aulas.md").read_text(encoding="utf-8"))
    quoted = title.replace('"', '\\"')
    return "\n".join(
        [
            "---",
            f'title: "{quoted}"',
            "---",
            "",
            NOTEBOOKLM_WARNING.strip(),
            "",
            ROTEIRO.strip(),
            "",
            readme.strip(),
            "",
            "---",
            "",
            "# Vídeos {#videos}",
            "",
            videos.strip(),
            "",
            "---",
            "",
            "# Aulas {#aulas}",
            "",
            NOTEBOOKLM_WARNING.strip(),
            "",
            aulas.strip(),
            "",
        ]
    )


def _prepare_markdown(text: str) -> str:
    converted = _convert_github_math(text)
    for pattern, repl in LINK_REWRITES:
        converted = pattern.sub(repl, converted)
    return converted


def _convert_github_math(text: str) -> str:
    lines = text.split("\n")
    output: list[str] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("```"):
            language = stripped[3:].strip().lower()
            if language == "math":
                index += 1
                body: list[str] = []
                while index < len(lines) and not lines[index].strip().startswith("```"):
                    body.append(lines[index])
                    index += 1
                if index >= len(lines):
                    raise RuntimeError("Bloco ```math sem fechamento.")
                output.extend(["", "\\[", *body, "\\]", ""])
                index += 1
                continue
            output.append(lines[index])
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                output.append(lines[index])
                index += 1
            if index < len(lines):
                output.append(lines[index])
                index += 1
            continue
        output.append(INLINE_MATH.sub(lambda match: r"\(" + match.group(1) + r"\)", lines[index]))
        index += 1
    return "\n".join(output)


def _write_catalog(root: Path, docs: Path) -> None:
    dest = docs / "catalogo"
    dest.mkdir(parents=True)
    shutil.copy2(root / "catalogo" / "catalogo.csv", dest / "catalogo.csv")
    original = (root / "catalogo" / "catalogo.md").read_text(encoding="utf-8")
    (dest / "index.md").write_text(CATALOG_INTRO + original, encoding="utf-8")
