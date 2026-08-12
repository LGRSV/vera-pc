#!/usr/bin/env python3
"""
Gera uma versão de arquivo único do site, com CSS, JavaScript e dados embutidos.

Serve para publicar ou enviar o painel sem depender de servidor HTTP: a página abre
direto do disco e não faz nenhuma requisição de rede.

Uso:  python3 scripts/build_single_file.py [destino.html]
"""

import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO_PADRAO = os.path.join(RAIZ, "dist", "equipamentos-especiais.html")

ARQUIVOS_DADOS = {
    "equipamentos": "equipamentos.json",
    "alertas": "alertas_coep.json",
    "divergencias": "divergencias_emd.json",
    "compras": "plano_compras.json",
    "meta": "meta.json",
}


def ler(*partes):
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def corpo_da_pagina(html):
    """Extrai o conteúdo entre <body> e </body>, sem o link de CSS nem o script."""
    corpo = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    if not corpo:
        raise SystemExit("index.html sem <body> — nada a extrair")
    return re.sub(r'\s*<script src="[^"]*"></script>', "", corpo.group(1)).strip()


def main():
    destino = sys.argv[1] if len(sys.argv) > 1 else DESTINO_PADRAO
    os.makedirs(os.path.dirname(destino), exist_ok=True)

    html = ler("index.html")
    titulo = re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()

    dados = {
        chave: json.loads(ler("data", nome)) for chave, nome in ARQUIVOS_DADOS.items()
    }
    # </script> dentro de uma string JSON encerraria o bloco antes da hora.
    json_embutido = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )

    pagina = (
        f"<title>{titulo}</title>\n"
        f"<style>\n{ler('assets', 'css', 'fontes.css')}\n</style>\n"
        f"<style>\n{ler('assets', 'css', 'styles.css')}\n</style>\n\n"
        f"{corpo_da_pagina(html)}\n\n"
        f"<script>\nconst DADOS_EMBUTIDOS = {json_embutido};\n</script>\n"
        f"<script>\n{ler('assets', 'js', 'app.js')}\n</script>\n"
    )

    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(pagina)

    tamanho = os.path.getsize(destino) / 1024
    print(f"OK — {destino} ({tamanho:.0f} KB)")
    print(f"     {len(dados['equipamentos'])} equipamentos, "
          f"{len(dados['alertas'])} alertas, {len(dados['divergencias'])} divergências, "
          f"{len(dados['compras'])} achados de compra.")


if __name__ == "__main__":
    main()
