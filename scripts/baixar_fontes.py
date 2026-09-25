#!/usr/bin/env python3
"""
Baixa as fontes do tema (subset latino, woff2) e escreve assets/css/fontes.css com
cada arquivo embutido como data URI.

O site publicado é autocontido e não pode fazer requisição externa — nem para fontes.
Este script roda uma vez (ou quando o tema mudar); o CSS gerado é versionado no repo.

Uso:  python3 scripts/baixar_fontes.py
"""

import base64
import os
import re
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "assets", "css", "fontes.css")

FAMILIAS = (
    "family=Barlow+Condensed:wght@600;700"
    "&family=Spectral:ital,wght@0,400;0,600;1,400"
    "&family=IBM+Plex+Mono:wght@400;600"
)
URL_CSS = f"https://fonts.googleapis.com/css2?{FAMILIAS}&display=swap"

# Com um user-agent moderno o Google serve woff2 e divide por subset de escrita.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")


def baixar(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(pedido, timeout=60) as resposta:
        return resposta.read()


def main():
    css = baixar(URL_CSS).decode("utf-8")

    # O CSS vem em blocos comentados por subset: /* latin */, /* latin-ext */ etc.
    # Português cabe no subset latino; os demais são descartados.
    blocos = re.findall(r"/\*\s*([a-z-]+)\s*\*/\s*(@font-face\s*{[^}]+})", css)
    saida = [
        "/* Fontes do tema Prontuário Industrial (assets/TEMA.md), embutidas como",
        "   data URI pelo scripts/baixar_fontes.py — subset latino, woff2. */",
        "",
    ]
    total = 0

    for subset, bloco in blocos:
        if subset != "latin":
            continue
        url = re.search(r"url\((https://[^)]+)\)", bloco).group(1)
        binario = baixar(url)
        total += len(binario)
        codificado = base64.b64encode(binario).decode("ascii")
        embutido = bloco.replace(
            url, f"data:font/woff2;base64,{codificado}"
        )
        saida.append(embutido)
        nome = re.search(r"font-family:\s*'([^']+)'", bloco).group(1)
        peso = re.search(r"font-weight:\s*(\d+)", bloco).group(1)
        estilo = re.search(r"font-style:\s*(\w+)", bloco).group(1)
        print(f"  {nome} {peso} {estilo}: {len(binario) / 1024:.0f} KB")

    with open(DESTINO, "w", encoding="utf-8") as fh:
        fh.write("\n".join(saida) + "\n")

    print(f"OK — {DESTINO} ({os.path.getsize(DESTINO) / 1024:.0f} KB, "
          f"{total / 1024:.0f} KB de woff2)")


if __name__ == "__main__":
    main()
