"""
A página das quatro curvas de 2026, separadas por religador e regulador.

Lê data/missao/parque_2026.json e gera dist/parque-2026.html — autocontida, tema
claro e escuro, com tabela de dados embaixo de cada bloco (o número sempre existe
sem depender da figura).

Rodar: python3 scripts/build_parque_2026.py
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "dist", "parque-2026.html")

NOME = {"RL": "Religadores", "RT": "Reguladores de tensão"}


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def br(v, casas=0):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "·").replace(".", ",").replace("·", ".")


def eixo_bonito(maximo, alvo=4):
    """Passo redondo para a escala — 1, 2, 2.5 ou 5 vezes a potência de dez."""
    if maximo <= 0:
        return 1, 1
    import math
    bruto = maximo / alvo
    p = 10 ** math.floor(math.log10(bruto))
    # 2,5 só entra quando a escala não é de contagem miúda: num eixo de 0 a 10
    # ele produz 0-2-5-8-10, que se lê como erro de impressão
    escadas = (1, 2, 5, 10) if maximo <= 12 else (1, 2, 2.5, 5, 10)
    passo = p * escadas[-1]
    for m in escadas:
        if p * m >= bruto:
            passo = p * m
            break
    topo = math.ceil(maximo / passo) * passo
    return passo, topo


def linha(serie, rotulos, cor, unidade="", casas=0, zero=True, id_=""):
    """Uma série ao longo do tempo. Quando zero=False o eixo é truncado e a figura
    diz isso — em linha é legítimo, desde que fique escrito."""
    L, R, T, B = 54, 20, 24, 30
    W, H = 720, 236
    pw, ph = W - L - R, H - T - B
    vmax, vmin = max(serie), min(serie)
    if zero:
        passo, topo = eixo_bonito(vmax)
        base = 0
    else:
        import math
        folga = max((vmax - vmin) * 0.35, 1)
        passo, _ = eixo_bonito(vmax - (vmin - folga))
        # a base tem de cair num múltiplo do passo, senão o eixo sai com marcas
        # tortas (176 · 182 · 186 · 192) e o leitor desconfia do gráfico inteiro
        base = math.floor((vmin - folga) / passo) * passo
        topo = math.ceil(vmax / passo) * passo
        if topo <= base:
            topo = base + passo
    esc_y = lambda v: T + ph - (v - base) / (topo - base) * ph
    esc_x = lambda i: L + (pw / (len(serie) - 1)) * i if len(serie) > 1 else L + pw / 2

    linhas_grade, marcas_y = [], []
    v = base
    while v <= topo + 1e-9:
        y = esc_y(v)
        linhas_grade.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" class="grade"/>')
        marcas_y.append(f'<text x="{L-8}" y="{y+4:.1f}" class="rot-y">{br(v, casas)}</text>')
        v += passo
    pontos = " ".join(f"{esc_x(i):.1f},{esc_y(v):.1f}" for i, v in enumerate(serie))
    marcadores = "".join(
        f'<circle cx="{esc_x(i):.1f}" cy="{esc_y(v):.1f}" r="4.5" fill="{cor}" '
        f'stroke="var(--fundo)" stroke-width="2"><title>{esc(rotulos[i])}: '
        f'{br(v, casas)}{esc(unidade)}</title></circle>' for i, v in enumerate(serie))
    # rótulo direto só no primeiro, no último e no pico — e nunca em cima do eixo:
    # o da ponta esquerda ancora à direita, o da ponta direita à esquerda, e valor
    # zero não ganha rótulo (colide com a linha de base e não informa nada)
    idx_pico = serie.index(max(serie))
    destaque = {0, len(serie) - 1, idx_pico}
    pedacos = []
    for i, v in enumerate(serie):
        if i not in destaque or v == 0:
            continue
        if i == 0:
            ancora, dx = "start", 9
        elif i == len(serie) - 1:
            ancora, dx = "end", -9
        else:
            ancora, dx = "middle", 0
        pedacos.append(
            f'<text x="{esc_x(i)+dx:.1f}" y="{esc_y(v)-10:.1f}" class="rot-valor" '
            f'style="text-anchor:{ancora}">{br(v, casas)}{esc(unidade)}</text>')
    rotulos_diretos = "".join(pedacos)
    eixo_x = "".join(
        f'<text x="{esc_x(i):.1f}" y="{H-10}" class="rot-x">{esc(r)}</text>'
        for i, r in enumerate(rotulos))
    return (f'<svg viewBox="0 0 {W} {H}" class="fig" role="img">'
            + "".join(linhas_grade) + "".join(marcas_y)
            + f'<polyline points="{pontos}" fill="none" stroke="{cor}" stroke-width="2" '
              'stroke-linejoin="round" stroke-linecap="round"/>'
            + marcadores + rotulos_diretos + eixo_x + "</svg>")


def barras(series, rotulos, unidade=""):
    """Barras agrupadas — mesma unidade, eixo do zero, 2px de respiro entre elas."""
    L, R, T, B = 44, 16, 22, 30
    W, H = 720, 250
    pw, ph = W - L - R, H - T - B
    vmax = max(max(s["dados"]) for s in series) or 1
    passo, topo = eixo_bonito(vmax)
    esc_y = lambda v: T + ph - v / topo * ph
    n, g = len(series), len(rotulos)
    larg_grupo = pw / g
    larg = min(16, (larg_grupo - 10) / n)
    grade, marcas = [], []
    v = 0
    while v <= topo + 1e-9:
        y = esc_y(v)
        grade.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" class="grade"/>')
        marcas.append(f'<text x="{L-8}" y="{y+4:.1f}" class="rot-y">{br(v)}</text>')
        v += passo
    corpo = []
    for gi, rot in enumerate(rotulos):
        x0 = L + larg_grupo * gi + (larg_grupo - (larg + 2) * n) / 2
        for si, s in enumerate(series):
            val = s["dados"][gi]
            x = x0 + si * (larg + 2)
            y = esc_y(val)
            alt = max(T + ph - y, 0)
            if val > 0:
                corpo.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{larg:.1f}" height="{alt:.1f}" '
                    f'rx="4" fill="{s["cor"]}"><title>{esc(rot)} · {esc(s["nome"])}: '
                    f'{br(val)}{esc(unidade)}</title></rect>')
                corpo.append(f'<text x="{x+larg/2:.1f}" y="{y-5:.1f}" class="rot-barra">{br(val)}</text>')
    eixo_x = "".join(
        f'<text x="{L + larg_grupo*(i+0.5):.1f}" y="{H-10}" class="rot-x">{esc(r)}</text>'
        for i, r in enumerate(rotulos))
    return (f'<svg viewBox="0 0 {W} {H}" class="fig" role="img">'
            + "".join(grade) + "".join(marcas) + "".join(corpo)
            + f'<line x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}" class="base"/>'
            + eixo_x + "</svg>")


def legenda(series):
    return ('<div class="legenda">' + "".join(
        f'<span><i style="background:{s["cor"]}"></i>{esc(s["nome"])}'
        + (f'<em>{esc(s["dica"])}</em>' if s.get("dica") else "") + "</span>"
        for s in series) + "</div>")


def tabela(linhas_dados, tipo):
    cab = ("<tr><th>Mês</th><th class='num'>Parque</th><th class='num'>Expansão</th>"
           "<th class='num'>Entrantes fora de operação</th><th class='num'>Realizado (DCMD)</th>"
           "<th class='num'>Falhas · peça grande</th><th class='num'>Taxa do mês</th></tr>")
    corpo = "".join(
        f"<tr><td>{esc(x['rotulo'])}</td><td class='num'>{br(x['parque'])}</td>"
        f"<td class='num'>{('+' + str(x['expansao'])) if x['expansao'] else '—'}</td>"
        f"<td class='num'>{x['entrantes'] or '—'}</td>"
        f"<td class='num'>{x['realizado'] or '—'}</td>"
        f"<td class='num'>{x['falhas'] or '—'}</td>"
        f"<td class='num'>{br(x['taxa_mes_pct'], 2)}%</td></tr>" for x in linhas_dados)
    return (f'<details class="tabela"><summary>Os números de {esc(NOME[tipo].lower())}, '
            f'mês a mês</summary><div class="rolagem"><table>{cab}{corpo}</table></div></details>')


def bloco(tipo, dados, totais):
    rot = [x["rotulo"] for x in dados]
    parque = [x["parque"] for x in dados]
    fluxo = [
        {"nome": "Entrantes fora de operação", "cor": "var(--serie-1)",
         "dados": [x["entrantes"] for x in dados],
         "dica": "pela data da ocorrência"},
        {"nome": "Falhas — peça grande", "cor": "var(--serie-2)",
         "dados": [x["falhas"] for x in dados], "dica": "o que entra na taxa"},
        {"nome": "Realizado — concluído DCMD", "cor": "var(--serie-3)",
         "dados": [x["realizado"] for x in dados], "dica": "pelo mês do fechamento"},
    ]
    taxa = [x["taxa_mes_pct"] for x in dados]
    exp = totais["expansao_no_ano"]
    return f"""
    <section class="bloco">
      <div class="marcador"><h2>{esc(NOME[tipo])}</h2>
        <span>{br(dados[0]['parque'])} em janeiro · {br(dados[-1]['parque'])} em agosto</span></div>

      <h3>O parque, crescendo com a expansão</h3>
      <p class="texto">Começa em <b>{br(dados[0]['parque'])}</b> e fecha agosto em
      <b>{br(dados[-1]['parque'])}</b> — <b>+{exp}</b> equipamentos no ano.
      O eixo não começa em zero: o crescimento é de {br(100*exp/dados[0]['parque'], 1)}% e
      desapareceria numa escala cheia.</p>
      {linha(parque, rot, "var(--serie-1)", zero=False)}

      <h3>Quem sai de operação, quem falha de verdade e quem volta</h3>
      <p class="texto">Três contagens de equipamento, na mesma escala. A azul é todo mundo que
      <b>saiu de operação</b> no mês. A laranja é a parte que foi <b>falha de peça grande</b> — a
      que entra na taxa. A verde é o que o <b>DCMD concluiu</b>. A distância entre a azul e a
      laranja é o que se resolve sem troca de peça grande: religa, ajusta, comunica.</p>
      {legenda(fluxo)}
      {barras(fluxo, rot)}

      <h3>A taxa de falha, mês a mês</h3>
      <p class="texto">Falhas de peça grande do mês dividido pelo parque daquele mês — por isso
      o denominador cresce junto. No ano fechado a conta é outra: o ativo que falha duas vezes
      conta uma vez só, então a soma dos meses passa do total anual.</p>
      {linha(taxa, rot, "var(--serie-2)", unidade="%", casas=2)}

      {tabela(dados, tipo)}
    </section>"""


def montar():
    with open(os.path.join(RAIZ, "data", "missao", "parque_2026.json"),
              encoding="utf-8") as fh:
        p = json.load(fh)
    corpo = "".join(bloco(t, p["series"][t], p["totais"][t]) for t in ("RL", "RT"))
    # sem <!doctype>, <html>, <head> ou <body>: o publish do artifact embrulha o
    # arquivo nesse esqueleto, e repetir as tags aqui quebraria a página
    html = f"""<title>Parque e falhas 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap">
<style>
:root {{
  --papel:#f2efe6; --papel-2:#e9e5d8; --fundo:#fcfcfb;
  --tinta:#211d15; --tinta-2:#57513f; --tinta-3:#8d8672;
  --filete:#c8c2af; --serie-1:#2f56b0; --serie-2:#bc4b0e; --serie-3:#2e7f52;
  --leitura: Spectral, Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --papel:#191713; --papel-2:#221f1a; --fundo:#1a1a19;
    --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563;
    --filete:#403a2e; --serie-1:#6b8fe0; --serie-2:#e0703a; --serie-3:#35a58c;
  }}
}}
:root[data-theme="dark"] {{
  --papel:#191713; --papel-2:#221f1a; --fundo:#1a1a19;
  --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563;
  --filete:#403a2e; --serie-1:#6b8fe0; --serie-2:#e0703a; --serie-3:#35a58c;
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--papel); color:var(--tinta); font-family:var(--leitura);
  font-size:16px; line-height:1.6; }}
.folha {{ max-width: 880px; margin: 0 auto; padding: 32px 20px 64px; }}
.capa {{ border-bottom:2px solid var(--tinta); padding-bottom:14px; margin-bottom:8px; }}
.capa h1 {{ margin:0; font-size:26px; letter-spacing:.06em; text-transform:uppercase;
  font-family:var(--mono); font-weight:700; }}
.capa p {{ margin:6px 0 0; color:var(--tinta-2); font-size:14.5px; }}
.bloco {{ margin-top:40px; background:var(--fundo); border:1px solid var(--filete);
  padding:20px 22px 24px; }}
.marcador {{ display:flex; flex-wrap:wrap; gap:6px 14px; align-items:baseline;
  border-bottom:1px solid var(--tinta); padding-bottom:8px; margin-bottom:16px; }}
.marcador h2 {{ margin:0; font-size:19px; font-family:var(--mono); font-weight:700;
  letter-spacing:.04em; text-transform:uppercase; }}
.marcador span {{ color:var(--tinta-3); font-family:var(--mono); font-size:12.5px; }}
h3 {{ font-size:12px; font-family:var(--mono); font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; color:var(--tinta-2); margin:26px 0 6px; }}
.bloco h3:first-of-type {{ margin-top:6px; }}
.texto {{ margin:0 0 12px; font-size:15px; color:var(--tinta-2); }}
.texto b {{ color:var(--tinta); }}
.fig {{ width:100%; height:auto; display:block; overflow:visible; }}
.grade {{ stroke:var(--filete); stroke-width:1; opacity:.5; }}
.base {{ stroke:var(--tinta-3); stroke-width:1; }}
.rot-y, .rot-x {{ font-family:var(--mono); font-size:10.5px; fill:var(--tinta-3); }}
.rot-y {{ text-anchor:end; }}
.rot-x {{ text-anchor:middle; text-transform:uppercase; letter-spacing:.06em; }}
.rot-valor {{ font-family:var(--mono); font-size:11px; fill:var(--tinta); text-anchor:middle;
  font-weight:600; }}
.rot-barra {{ font-family:var(--mono); font-size:9.5px; fill:var(--tinta-2); text-anchor:middle; }}
.legenda {{ display:flex; flex-wrap:wrap; gap:6px 20px; margin:2px 0 10px; }}
.legenda span {{ display:flex; align-items:center; gap:7px; font-family:var(--mono);
  font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--tinta-2); }}
.legenda i {{ width:11px; height:11px; border-radius:2px; flex:none; }}
.legenda em {{ font-style:italic; font-family:var(--leitura); text-transform:none;
  letter-spacing:0; color:var(--tinta-3); font-size:12.5px; }}
.tabela {{ margin-top:22px; border-top:1px solid var(--filete); padding-top:10px; }}
.tabela summary {{ cursor:pointer; font-family:var(--mono); font-size:11.5px;
  text-transform:uppercase; letter-spacing:.06em; color:var(--tinta-2); }}
.rolagem {{ overflow-x:auto; margin-top:10px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; min-width:520px; }}
th {{ text-align:left; font-family:var(--mono); font-size:10.5px; font-weight:700;
  text-transform:uppercase; letter-spacing:.05em; color:var(--tinta-2);
  border-bottom:1px solid var(--tinta); padding:6px 8px; }}
td {{ padding:6px 8px; border-bottom:1px dotted var(--filete); font-family:var(--mono);
  font-size:12.5px; }}
th.num, td.num {{ text-align:right; }}
.nota {{ margin-top:34px; border:1px solid var(--filete); border-left:3px solid var(--tinta-3);
  background:var(--papel-2); padding:14px 16px; font-size:14px; color:var(--tinta-2); }}
.nota b {{ color:var(--tinta); }}
.nota ul {{ margin:8px 0 0; padding-left:20px; }}
.nota li {{ margin:4px 0; }}
</style>
<div class="folha">
  <div class="capa">
    <h1>Parque e falhas 2026</h1>
    <p>Religadores e reguladores da ETO, mês a mês — o parque crescendo com a expansão,
    quem sai de operação, o que o DCMD concluiu e a taxa de falha mensalizada.
    Janeiro a agosto (agosto parcial, até 20/08).</p>
  </div>
  {corpo}
  <div class="nota">
    <b>De onde vem cada curva.</b>
    <ul>
      <li><b>Parque</b> — base de janeiro do gestor: {br(p['base_janeiro']['RL'])} religadores e
      {br(p['base_janeiro']['RT'])} reguladores, mais a expansão realizada, somada no próprio mês.
      Agosto repete julho porque a expansão de agosto ainda não fechou.</li>
      <li><b>Entrantes fora de operação</b> — equipamento com SS de indisponibilidade para
      operação, pela <b>data da ocorrência</b> (não a da abertura, que atrasa 39 dias em média),
      contado uma vez por mês.</li>
      <li><b>Realizado</b> — concluído pelo DCMD: equipe de campo na cadeia e demanda fechada com
      SS atendida, pelo mês do fechamento. São {p['totais']['RL']['realizado']} religadores e
      {p['totais']['RT']['realizado']} reguladores no ano.</li>
      <li><b>Taxa de falha</b> — só <b>peça grande</b> pela sua régua (controle, tanque ou
      completo no religador; célula, relé, completo ou furto no regulador), dividida pelo parque
      daquele mês. Fecha o ano em {p['totais']['RL']['falhas_somadas']} religadores e
      {p['totais']['RT']['falhas_somadas']} reguladores — os mesmos números da página da taxa.</li>
    </ul>
  </div>
</div>"""
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"OK — {SAIDA} ({len(html)//1024} KB)")


if __name__ == "__main__":
    montar()
