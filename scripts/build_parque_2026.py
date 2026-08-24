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


def legenda(series):
    return ('<div class="legenda">' + "".join(
        f'<span><i style="background:{s["cor"]}"></i>{esc(s["nome"])}'
        + (f'<em>{esc(s["dica"])}</em>' if s.get("dica") else "") + "</span>"
        for s in series) + "</div>")


def tabela(linhas_dados, tipo, cum_meses):
    cab = ("<tr><th>Mês</th><th class='num'>Parque</th><th class='num'>Expansão</th>"
           "<th class='num'>Entrantes fora de operação</th><th class='num'>Realizado (DCMD)</th>"
           "<th class='num'>Falhas · peça grande</th><th class='num'>Taxa do mês</th>"
           "<th class='num'>Entraram (acum.)</th><th class='num'>Resolvidos (acum.)</th>"
           "<th class='num'>Fila</th></tr>")
    corpo = "".join(
        f"<tr><td>{esc(x['rotulo'])}</td><td class='num'>{br(x['parque'])}</td>"
        f"<td class='num'>{('+' + str(x['expansao'])) if x['expansao'] else '—'}</td>"
        f"<td class='num'>{x['entrantes'] or '—'}</td>"
        f"<td class='num'>{x['realizado'] or '—'}</td>"
        f"<td class='num'>{x['falhas'] or '—'}</td>"
        f"<td class='num'>{br(x['taxa_mes_pct'], 2)}%</td>"
        f"<td class='num'>{br(c['entraram_acumulado'])}</td>"
        f"<td class='num'>{br(c['resolvidos_acumulado'])}</td>"
        f"<td class='num'>{br(c['fila'])}</td></tr>"
        for x, c in zip(linhas_dados, cum_meses))
    return (f'<details class="tabela"><summary>Os números de {esc(NOME[tipo].lower())}, '
            f'mês a mês</summary><div class="rolagem"><table>{cab}{corpo}</table></div></details>')



def composto(dados, rotulos):
    """As quatro curvas numa figura só.

    Elas não cabem num eixo comum — o parque está na casa do milhar, a taxa em
    décimos de por cento — e forçar duas escalas no mesmo par de eixos é a mentira
    visual clássica. Então a figura é uma só, com três faixas empilhadas que
    dividem o MESMO eixo do tempo: o parque em cima, as contagens no meio, a taxa
    embaixo. Lê-se de uma vez, na vertical, sem escala falsa.
    """
    L, R = 56, 20
    W = 720
    H1, H2, H3 = 74, 210, 92          # alturas das faixas
    G = 26                              # respiro entre faixas
    H = H1 + H2 + H3 + G * 2 + 40
    pw = W - L - R
    x = lambda i: L + (pw / (len(rotulos) - 1)) * i
    partes = []

    def faixa_rotulo(y, texto):
        partes.append(f'<text x="{L}" y="{y}" class="faixa-nome">{esc(texto)}</text>')

    # ---- faixa 1: parque (linha, escala truncada e dita no rótulo)
    import math
    serie = [d["parque"] for d in dados]
    vmin, vmax = min(serie), max(serie)
    passo, _ = eixo_bonito(max(vmax - vmin, 1), alvo=2)
    base = math.floor((vmin - max((vmax - vmin) * 0.5, 1)) / passo) * passo
    topo = math.ceil((vmax + (vmax - vmin) * 0.25) / passo) * passo
    if topo <= base:
        topo = base + passo
    t0 = 16
    ey = lambda v: t0 + H1 - (v - base) / (topo - base) * H1
    faixa_rotulo(t0 - 5, f"Parque · {br(vmin)} a {br(vmax)}")
    for v in (base, topo):
        partes.append(f'<line x1="{L}" y1="{ey(v):.1f}" x2="{L+pw}" y2="{ey(v):.1f}" class="grade"/>')
        partes.append(f'<text x="{L-8}" y="{ey(v)+4:.1f}" class="rot-y">{br(v)}</text>')
    pts = " ".join(f"{x(i):.1f},{ey(v):.1f}" for i, v in enumerate(serie))
    partes.append(f'<polyline points="{pts}" fill="none" stroke="var(--serie-4)" stroke-width="2" '
                  'stroke-linejoin="round"/>')
    for i, v in enumerate(serie):
        partes.append(f'<circle cx="{x(i):.1f}" cy="{ey(v):.1f}" r="4" fill="var(--serie-4)" '
                      f'stroke="var(--fundo)" stroke-width="2"><title>{esc(rotulos[i])}: '
                      f'{br(v)} equipamentos</title></circle>')
    for i in (0, len(serie) - 1):
        anc, dx = ("start", 9) if i == 0 else ("end", -9)
        partes.append(f'<text x="{x(i)+dx:.1f}" y="{ey(serie[i])-9:.1f}" class="rot-valor" '
                      f'style="text-anchor:{anc}">{br(serie[i])}</text>')

    # ---- faixa 2: as três contagens, barras agrupadas do zero
    t1 = t0 + H1 + G
    series = [
        ("Entrantes fora de operação", "var(--serie-1)", [d["entrantes"] for d in dados]),
        ("Falhas · peça grande", "var(--serie-2)", [d["falhas"] for d in dados]),
        ("Realizado · concluído DCMD", "var(--serie-3)", [d["realizado"] for d in dados]),
    ]
    vmax2 = max(max(s[2]) for s in series) or 1
    passo2, topo2 = eixo_bonito(vmax2)
    ey2 = lambda v: t1 + H2 - v / topo2 * H2
    faixa_rotulo(t1 - 5, "Equipamentos no mês")
    v = 0
    while v <= topo2 + 1e-9:
        partes.append(f'<line x1="{L}" y1="{ey2(v):.1f}" x2="{L+pw}" y2="{ey2(v):.1f}" class="grade"/>')
        partes.append(f'<text x="{L-8}" y="{ey2(v)+4:.1f}" class="rot-y">{br(v)}</text>')
        v += passo2
    larg_grupo = pw / len(rotulos)
    larg = min(15, (larg_grupo - 12) / 3)
    for gi in range(len(rotulos)):
        x0 = L + larg_grupo * gi + (larg_grupo - (larg + 2) * 3) / 2
        for si, (nome, cor, vals) in enumerate(series):
            val = vals[gi]
            if not val:
                continue
            bx, by = x0 + si * (larg + 2), ey2(val)
            partes.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{larg:.1f}" '
                          f'height="{t1+H2-by:.1f}" rx="4" fill="{cor}">'
                          f'<title>{esc(rotulos[gi])} · {esc(nome)}: {br(val)}</title></rect>')
            partes.append(f'<text x="{bx+larg/2:.1f}" y="{by-5:.1f}" class="rot-barra">{br(val)}</text>')
    partes.append(f'<line x1="{L}" y1="{t1+H2}" x2="{L+pw}" y2="{t1+H2}" class="base"/>')

    # ---- faixa 3: taxa mensal
    t2 = t1 + H2 + G
    taxa = [d["taxa_mes_pct"] for d in dados]
    passo3, topo3 = eixo_bonito(max(taxa) or 1, alvo=2)
    ey3 = lambda v: t2 + H3 - v / topo3 * H3
    faixa_rotulo(t2 - 5, "Taxa de falha do mês · % do parque")
    v = 0
    while v <= topo3 + 1e-9:
        partes.append(f'<line x1="{L}" y1="{ey3(v):.1f}" x2="{L+pw}" y2="{ey3(v):.1f}" class="grade"/>')
        partes.append(f'<text x="{L-8}" y="{ey3(v)+4:.1f}" class="rot-y">{br(v, 2)}</text>')
        v += passo3
    pts3 = " ".join(f"{x(i):.1f},{ey3(v):.1f}" for i, v in enumerate(taxa))
    partes.append(f'<polyline points="{pts3}" fill="none" stroke="var(--serie-2)" stroke-width="2" '
                  'stroke-linejoin="round" stroke-dasharray="1 0"/>')
    for i, v in enumerate(taxa):
        partes.append(f'<circle cx="{x(i):.1f}" cy="{ey3(v):.1f}" r="4" fill="var(--serie-2)" '
                      f'stroke="var(--fundo)" stroke-width="2"><title>{esc(rotulos[i])}: '
                      f'{br(v, 2)}% do parque</title></circle>')
    ipico = taxa.index(max(taxa))
    partes.append(f'<text x="{x(ipico):.1f}" y="{ey3(taxa[ipico])-9:.1f}" class="rot-valor" '
                  f'style="text-anchor:middle">{br(taxa[ipico], 2)}%</text>')

    # ---- eixo do tempo, único para as três faixas
    for i, r in enumerate(rotulos):
        partes.append(f'<text x="{x(i):.1f}" y="{H-12}" class="rot-x">{esc(r)}</text>')
    return f'<svg viewBox="0 0 {W} {H}" class="fig" role="img">' + "".join(partes) + "</svg>"


def acumulada(meses, acervo):
    """A conta do gestor no tempo: o que entrou (já com o acervo herdado) contra o
    que foi resolvido. A distância entre as duas linhas é a fila daquele mês."""
    L, R, T, B = 56, 20, 26, 30
    W, H = 720, 250
    pw, ph = W - L - R, H - T - B
    ent = [m["entraram_acumulado"] for m in meses]
    res = [m["resolvidos_acumulado"] for m in meses]
    passo, topo = eixo_bonito(max(ent))
    x = lambda i: L + (pw / (len(meses) - 1)) * i
    y = lambda v: T + ph - v / topo * ph
    partes = []
    v = 0
    while v <= topo + 1e-9:
        partes.append(f'<line x1="{L}" y1="{y(v):.1f}" x2="{L+pw}" y2="{y(v):.1f}" class="grade"/>')
        partes.append(f'<text x="{L-8}" y="{y(v)+4:.1f}" class="rot-y">{br(v)}</text>')
        v += passo
    # a fila, pintada entre as duas linhas
    area = ([f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(ent)]
            + [f"{x(i):.1f},{y(v):.1f}" for i, v in reversed(list(enumerate(res)))])
    partes.append(f'<polygon points="{" ".join(area)}" class="fila"/>')
    for serie, cor in ((ent, "var(--serie-2)"), (res, "var(--serie-3)")):
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(serie))
        partes.append(f'<polyline points="{pts}" fill="none" stroke="{cor}" stroke-width="2" '
                      'stroke-linejoin="round"/>')
    for i, m in enumerate(meses):
        partes.append(f'<circle cx="{x(i):.1f}" cy="{y(ent[i]):.1f}" r="4" fill="var(--serie-2)" '
                      f'stroke="var(--fundo)" stroke-width="2"><title>{esc(m["rotulo"])}: '
                      f'{br(ent[i])} entraram (acervo + {br(ent[i]-acervo)} no ano) · '
                      f'fila {br(m["fila"])}</title></circle>')
        partes.append(f'<circle cx="{x(i):.1f}" cy="{y(res[i]):.1f}" r="4" fill="var(--serie-3)" '
                      f'stroke="var(--fundo)" stroke-width="2"><title>{esc(m["rotulo"])}: '
                      f'{br(res[i])} resolvidos até aqui</title></circle>')
    for serie, i, dy in ((ent, 0, -10), (ent, len(ent)-1, -10), (res, len(res)-1, 16)):
        anc, dx = ("start", 9) if i == 0 else ("end", -9)
        partes.append(f'<text x="{x(i)+dx:.1f}" y="{y(serie[i])+dy:.1f}" class="rot-valor" '
                      f'style="text-anchor:{anc}">{br(serie[i])}</text>')
    for i, m in enumerate(meses):
        partes.append(f'<text x="{x(i):.1f}" y="{H-10}" class="rot-x">{esc(m["rotulo"])}</text>')
    return f'<svg viewBox="0 0 {W} {H}" class="fig" role="img">' + "".join(partes) + "</svg>"


def bloco(tipo, dados, totais, cum):
    rot = [x["rotulo"] for x in dados]
    fluxo = [
        {"nome": "Entrantes fora de operação", "cor": "var(--serie-1)",
         "dica": "pela data da ocorrência"},
        {"nome": "Falhas — peça grande", "cor": "var(--serie-2)",
         "dica": "o que entra na taxa"},
        {"nome": "Realizado — concluído DCMD", "cor": "var(--serie-3)",
         "dica": "pelo mês do fechamento"},
        {"nome": "Parque", "cor": "var(--serie-4)", "dica": "faixa de cima"},
    ]
    exp = totais["expansao_no_ano"]
    m = cum["meses"]
    pico_fila = max(m, key=lambda x: x["fila"])
    return f"""
    <section class="bloco">
      <div class="marcador"><h2>{esc(NOME[tipo])}</h2>
        <span>{br(dados[0]['parque'])} em janeiro · {br(dados[-1]['parque'])} em agosto</span></div>

      <h3>As quatro curvas do ano</h3>
      <p class="texto">Uma figura, três faixas, o mesmo eixo do tempo. Em cima o <b>parque</b>,
      que cresce de {br(dados[0]['parque'])} para {br(dados[-1]['parque'])} com a expansão
      (+{exp} no ano). No meio, três contagens de equipamento na mesma escala: quem
      <b>saiu de operação</b>, quanto disso foi <b>falha de peça grande</b> e quanto o
      <b>DCMD concluiu</b>. Embaixo, a <b>taxa do mês</b> — as falhas divididas pelo parque
      daquele mês. As faixas são separadas de propósito: parque na casa do milhar e taxa em
      décimos de por cento não cabem num eixo comum sem distorcer alguma delas.</p>
      {legenda(fluxo)}
      {composto(dados, rot)}

      <h3>A conta acumulada, com o que veio de antes</h3>
      <p class="texto">O ano não começa do zero: <b>{br(cum['acervo_em_janeiro'])}</b> equipamentos
      já estavam fora de operação em 1º de janeiro, vindos de 2024 e 2025. A linha laranja soma
      esse acervo com quem entrou depois; a verde é o que foi resolvido. A área entre elas é a
      <b>fila</b> — pico de {br(pico_fila['fila'])} em {esc(pico_fila['rotulo'])}, fechando agosto
      em <b>{br(m[-1]['fila'])}</b>. A conta fecha:
      {br(cum['acervo_em_janeiro'])} + {br(cum['entraram_no_ano'])} − {br(cum['resolvidos_no_ano'])}
      = {br(m[-1]['fila'])}, que é exatamente o número de cadeias abertas hoje.</p>
      {legenda([
        {"nome": "Entraram — acervo + o ano", "cor": "var(--serie-2)", "dica": "acumulado"},
        {"nome": "Resolvidos", "cor": "var(--serie-3)", "dica": "acumulado"},
      ])}
      {acumulada(m, cum['acervo_em_janeiro'])}

      {tabela(dados, tipo, m)}
    </section>"""


def montar():
    with open(os.path.join(RAIZ, "data", "missao", "parque_2026.json"),
              encoding="utf-8") as fh:
        p = json.load(fh)
    corpo = "".join(bloco(t, p["series"][t], p["totais"][t], p["cumulativo"][t])
                    for t in ("RL", "RT"))
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
  --filete:#c8c2af; --serie-1:#2f56b0; --serie-2:#bc4b0e; --serie-3:#2e7f52; --serie-4:#6a4c93;
  --leitura: Spectral, Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --papel:#191713; --papel-2:#221f1a; --fundo:#1a1a19;
    --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563;
    --filete:#403a2e; --serie-1:#6b8fe0; --serie-2:#e0703a; --serie-3:#35a58c; --serie-4:#9a7bcc;
  }}
}}
:root[data-theme="dark"] {{
  --papel:#191713; --papel-2:#221f1a; --fundo:#1a1a19;
  --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563;
  --filete:#403a2e; --serie-1:#6b8fe0; --serie-2:#e0703a; --serie-3:#35a58c; --serie-4:#9a7bcc;
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
.faixa-nome {{ font-family:var(--mono); font-size:9.5px; fill:var(--tinta-3); letter-spacing:.07em;
  text-transform:uppercase; }}
.fila {{ fill:var(--serie-2); opacity:.10; }}
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
