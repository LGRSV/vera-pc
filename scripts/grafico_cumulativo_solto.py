"""
A figura cumulativa do religador, solta — em SVG e em PNG.

Pedido do gestor (25/08): ele apontou para a figura do acumulado na página e disse
«quero esse gráfico». Solto quer dizer fora da página: um arquivo que entra em
apresentação, em ofício, em e-mail.

O SVG sai com as cores resolvidas em hexadecimal e o estilo embutido — na página as
cores são variáveis de CSS, que não sobrevivem fora dela. O PNG é o mesmo SVG
fotografado pelo Chromium em escala 3x.

Grava dist/grafico-cumulativo-<tipo>.svg e .png (claro e escuro).
Rodar: python3 scripts/grafico_cumulativo_solto.py [RL|RT]
"""

import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import build_parque_2026 as bp  # noqa: E402

DIST = os.path.join(RAIZ, "dist")
NODE = "/opt/node22/bin/node"
# o NODE_PATH não vale para import de ESM — o caminho tem de ser absoluto
PLAYWRIGHT = "/opt/node22/lib/node_modules/playwright/index.js"
BROWSER = "/opt/pw-browsers/chromium"

# Todas as variáveis que o SVG da página usa. Faltar uma não pode passar batido: o
# anel dos pontos é desenhado com stroke=var(--fundo), e com a cor errada ele vira
# um aro cinza em volta de cada marcador.
TEMAS = {
    "claro": {"papel": "#f2efe6", "papel-2": "#e9e5d8", "fundo": "#fcfcfb",
              "tinta": "#211d15", "tinta-2": "#57513f", "tinta-3": "#8d8672",
              "filete": "#c8c2af", "serie-1": "#2f56b0", "serie-2": "#bc4b0e",
              "serie-3": "#2e7f52", "serie-4": "#6a4c93"},
    "escuro": {"papel": "#191713", "papel-2": "#221f1a", "fundo": "#1a1a19",
               "tinta": "#e8e3d4", "tinta-2": "#b3ac97", "tinta-3": "#7c7563",
               "filete": "#403a2e", "serie-1": "#6b8fe0", "serie-2": "#e0703a",
               "serie-3": "#35a58c", "serie-4": "#9a7bcc"},
}

L_LEG = 58   # alinhado com o eixo, como na página

LEGENDA = [
    {"nome": "Entrantes — com o acervo herdado", "cor": "serie-2"},
    {"nome": "Indisponibilidade acumulada — só 2026", "cor": "serie-1"},
    {"nome": "Resolvidos — todas as cadeias", "cor": "serie-3"},
    {"nome": "Resolvidos pelo COEP", "cor": "serie-3", "tracejado": True},
]


def estilo(t):
    """As classes que a página dá ao SVG, embutidas para ele andar sozinho."""
    return f"""
  .fundo {{ fill:{t['fundo']}; }}
  .grade {{ stroke:{t['filete']}; stroke-width:1; opacity:.5; }}
  .rot-y, .rot-x {{ font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;
    font-size:10.5px; fill:{t['tinta-3']}; }}
  .rot-y {{ text-anchor:end; }}
  .rot-x {{ text-anchor:middle; text-transform:uppercase; letter-spacing:.06em; }}
  .rot-valor {{ font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;
    font-size:11px; fill:{t['tinta']}; font-weight:600; }}
  .faixa-nome {{ font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;
    font-size:9.5px; fill:{t['tinta-3']}; letter-spacing:.07em;
    text-transform:uppercase; }}
  .titulo {{ font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;
    font-size:13px; font-weight:700; fill:{t['tinta']}; letter-spacing:.05em;
    text-transform:uppercase; }}
  .leg {{ font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;
    font-size:10.5px; fill:{t['tinta-2']}; text-transform:uppercase;
    letter-spacing:.05em; }}"""


def resolve(svg, t):
    """Troca as variáveis de CSS pelas cores de verdade. Variável desconhecida
    estoura — cor silenciosamente errada é pior que erro."""
    def troca(m):
        if m.group(1) not in t:
            raise KeyError(f"cor sem tradução no tema: --{m.group(1)}")
        return t[m.group(1)]
    return re.sub(r"var\(--([a-z0-9-]+)\)", troca, svg)


def legenda_svg(t, largura, y):
    """Uma linha por série. Estimar largura de texto para acomodar em colunas é
    chute — e chute errado sobrepõe rótulo, que foi o que aconteceu."""
    partes = []
    for item in LEGENDA:
        cor = t[item["cor"]]
        traco = ' stroke-dasharray="5 3"' if item.get("tracejado") else ""
        partes.append(f'<line x1="{L_LEG}" y1="{y}" x2="{L_LEG+16}" y2="{y}" '
                      f'stroke="{cor}" stroke-width="3" stroke-linecap="round"{traco}/>')
        partes.append(f'<text x="{L_LEG+24}" y="{y+3.7}" class="leg">'
                      f'{bp.esc(item["nome"])}</text>')
        y += 16
    return "".join(partes), y - 16


def montar(tipo="RL"):
    with open(os.path.join(RAIZ, "data", "missao", "parque_2026.json"),
              encoding="utf-8") as fh:
        p = json.load(fh)
    dados, cum = p["series"][tipo], p["cumulativo"][tipo]
    rotulos = [d["rotulo"] for d in dados]
    bruto = bp.fig_cumulativa(dados, rotulos, cum["meses"], cum["acervo_em_janeiro"])

    corpo = re.search(r'role="img">(.*)</svg>', bruto, re.S).group(1)
    alt = float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', bruto).group(1))
    titulo = (f"{bp.NOME[tipo]} · 2026 acumulado, com o que veio de antes")

    saidas = {}
    for nome, t in TEMAS.items():
        leg, ultimo = legenda_svg(t, bp.W, alt + 22)
        altura = ultimo + 16
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {bp.W} '
               f'{altura + 30}" width="{bp.W}" height="{altura + 30}">'
               f"<style>{estilo(t)}</style>"
               f'<rect class="fundo" x="0" y="0" width="{bp.W}" height="{altura + 30}"/>'
               f'<text x="4" y="16" class="titulo">{bp.esc(titulo)}</text>'
               f'<g transform="translate(0,26)">{resolve(corpo, t)}</g>'
               f'<g transform="translate(0,26)">{leg}</g></svg>')
        caminho = os.path.join(DIST, f"grafico-cumulativo-{tipo.lower()}"
                                     + ("" if nome == "claro" else f"-{nome}") + ".svg")
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write(svg)
        saidas[nome] = caminho
    return saidas


def para_png(svgs, escala=3):
    roteiro = os.path.join(DIST, "_tira_foto.mjs")
    lista = json.dumps([{"svg": c, "png": c[:-4] + ".png"} for c in svgs.values()])
    with open(roteiro, "w", encoding="utf-8") as fh:
        fh.write(f"""
import pw from '{PLAYWRIGHT}';   // pacote CommonJS: só o default export
const {{ chromium }} = pw;
import {{ readFileSync }} from 'fs';
const alvos = {lista};
const nav = await chromium.launch({{ executablePath: '{BROWSER}' }});
for (const a of alvos) {{
  const svg = readFileSync(a.svg, 'utf8');
  const m = svg.match(/width="(\\d+)" height="([\\d.]+)"/);
  const pg = await nav.newPage({{
    viewport: {{ width: +m[1], height: Math.ceil(+m[2]) }},
    deviceScaleFactor: {escala},
  }});
  await pg.setContent(`<body style="margin:0">${{svg}}</body>`);
  await pg.waitForTimeout(250);
  await pg.screenshot({{ path: a.png, omitBackground: false }});
  await pg.close();
  console.log('png:', a.png);
}}
await nav.close();
""")
    env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules")
    subprocess.run([NODE, roteiro], check=True, env=env, cwd=RAIZ)
    os.remove(roteiro)


if __name__ == "__main__":
    tipo = (sys.argv[1] if len(sys.argv) > 1 else "RL").upper()
    svgs = montar(tipo)
    for nome, caminho in svgs.items():
        print(f"svg {nome}: {caminho}")
    para_png(svgs)
