"""
A página das quatro figuras de 2026 — duas para religador, duas para regulador.

Pedido do gestor (24/08): por tipo, uma figura mensal e uma cumulativa, tudo em
linha. Só isso na página.

  MENSAL — parque, entrantes fora de operação, resolvidos e taxa de falha do mês.
  CUMULATIVO — parque, indisponibilidade acumulada do ano, entrantes já com o
  acervo herdado, resolvidos (todas as cadeias) e resolvidos pelo posto do COEP.

Por que cada figura tem faixas em vez de um eixo só: parque na casa do milhar,
contagem nas dezenas e taxa em décimos de por cento não convivem num mesmo eixo —
duas escalas no mesmo par de eixos é a distorção clássica. As faixas dividem o
MESMO eixo do tempo, então a figura é uma e se lê na vertical.

Rodar: python3 scripts/build_parque_2026.py
"""

import json
import math
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "dist", "parque-2026.html")

NOME = {"RL": "Religadores", "RT": "Reguladores de tensão"}
W = 720
L, R = 58, 22


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def br(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "·").replace(".", ",").replace("·", ".")


def escada(maximo, alvo=4):
    if maximo <= 0:
        return 1, 1
    bruto = maximo / alvo
    p = 10 ** math.floor(math.log10(bruto))
    opcoes = (1, 2, 5, 10) if maximo <= 12 else (1, 2, 2.5, 5, 10)
    passo = p * opcoes[-1]
    for m in opcoes:
        if p * m >= bruto:
            passo = p * m
            break
    return passo, math.ceil(maximo / passo) * passo


def _serie_svg(partes, pontos, cor, tracejado=False):
    dash = ' stroke-dasharray="7 4"' if tracejado else ""
    partes.append(f'<polyline points="{pontos}" fill="none" stroke="{cor}" stroke-width="2" '
                  f'stroke-linejoin="round" stroke-linecap="round"{dash}/>')


def faixa_parque(partes, dados, x, topo_y, altura, rotulos):
    """O parque, numa faixa própria: escala truncada, dita no rótulo da faixa."""
    serie = [d["parque"] for d in dados]
    vmin, vmax = min(serie), max(serie)
    passo, _ = escada(max(vmax - vmin, 1), alvo=2)
    base = math.floor((vmin - max((vmax - vmin) * 0.55, 1)) / passo) * passo
    topo = math.ceil((vmax + (vmax - vmin) * 0.3) / passo) * passo
    if topo <= base:
        topo = base + passo
    y = lambda v: topo_y + altura - (v - base) / (topo - base) * altura
    partes.append(f'<text x="{L}" y="{topo_y-6}" class="faixa-nome">Parque · escala própria, '
                  f'de {br(vmin)} a {br(vmax)}</text>')
    for v in (base, topo):
        partes.append(f'<line x1="{L}" y1="{y(v):.1f}" x2="{W-R}" y2="{y(v):.1f}" class="grade"/>')
        partes.append(f'<text x="{L-8}" y="{y(v)+4:.1f}" class="rot-y">{br(v)}</text>')
    _serie_svg(partes, " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(serie)),
               "var(--serie-4)")
    for i, v in enumerate(serie):
        partes.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4" fill="var(--serie-4)" '
                      f'stroke="var(--fundo)" stroke-width="2"><title>{esc(rotulos[i])}: '
                      f'{br(v)} equipamentos</title></circle>')
    for i, anc, dx in ((0, "start", 9), (len(serie) - 1, "end", -9)):
        partes.append(f'<text x="{x(i)+dx:.1f}" y="{y(serie[i])-9:.1f}" class="rot-valor" '
                      f'style="text-anchor:{anc}">{br(serie[i])}</text>')


def faixa_series(partes, series, x, topo_y, altura, rotulos, nome_faixa,
                 casas=0, unidade=""):
    """Várias linhas na mesma unidade, eixo do zero."""
    vmax = max(max(s["dados"]) for s in series) or 1
    passo, topo = escada(vmax, alvo=4 if altura > 120 else 2)
    y = lambda v: topo_y + altura - v / topo * altura
    partes.append(f'<text x="{L}" y="{topo_y-6}" class="faixa-nome">{esc(nome_faixa)}</text>')
    v = 0
    while v <= topo + 1e-9:
        partes.append(f'<line x1="{L}" y1="{y(v):.1f}" x2="{W-R}" y2="{y(v):.1f}" class="grade"/>')
        partes.append(f'<text x="{L-8}" y="{y(v)+4:.1f}" class="rot-y">{br(v, casas)}</text>')
        v += passo
    for s in series:
        _serie_svg(partes, " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(s["dados"])),
                   s["cor"], s.get("tracejado"))
    for s in series:
        for i, v in enumerate(s["dados"]):
            partes.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4" fill="{s["cor"]}" '
                          f'stroke="var(--fundo)" stroke-width="2"><title>{esc(rotulos[i])} · '
                          f'{esc(s["nome"])}: {br(v, casas)}{esc(unidade)}</title></circle>')
        i = len(s["dados"]) - 1
        # valor final zero não ganha rótulo: cairia em cima da linha de base do eixo
        if s["dados"][i]:
            partes.append(f'<text x="{x(i)-9:.1f}" y="{y(s["dados"][i])+(-9 if s.get("acima", True) else 17):.1f}" '
                          f'class="rot-valor" style="text-anchor:end">{br(s["dados"][i], casas)}{esc(unidade)}</text>')


def figura(dados, rotulos, faixas):
    """Uma figura, N faixas, um só eixo do tempo embaixo."""
    G, PE, PB = 30, 18, 40
    altura_total = sum(f["altura"] for f in faixas) + G * (len(faixas) - 1) + PE + PB
    x = lambda i: L + ((W - L - R) / (len(rotulos) - 1)) * i
    partes, topo_y = [], PE
    for f in faixas:
        f["desenha"](partes, x, topo_y, f["altura"])
        topo_y += f["altura"] + G
    for i, r in enumerate(rotulos):
        partes.append(f'<text x="{x(i):.1f}" y="{altura_total-14}" class="rot-x">{esc(r)}</text>')
    return (f'<svg viewBox="0 0 {W} {altura_total}" class="fig" role="img">'
            + "".join(partes) + "</svg>")


def legenda(itens):
    return ('<div class="legenda">' + "".join(
        f'<span><i style="background:{i["cor"]}"'
        + (' class="tracejo"' if i.get("tracejado") else "") + f'></i>{esc(i["nome"])}'
        + (f'<em>{esc(i["dica"])}</em>' if i.get("dica") else "") + "</span>"
        for i in itens) + "</div>")


def fig_mensal(dados, rotulos):
    ent = [d["entrantes"] for d in dados]
    res = [d["resolvidos_no_mes"] for d in dados]
    taxa = [d["taxa_mes_pct"] for d in dados]
    return figura(dados, rotulos, [
        {"altura": 70, "desenha": lambda p, x, t, a: faixa_parque(p, dados, x, t, a, rotulos)},
        {"altura": 180, "desenha": lambda p, x, t, a: faixa_series(p, [
            {"nome": "Entrantes fora de operação", "cor": "var(--serie-1)", "dados": ent},
            {"nome": "Resolvidos", "cor": "var(--serie-3)", "dados": res, "acima": False},
        ], x, t, a, rotulos, "Equipamentos no mês")},
        {"altura": 92, "desenha": lambda p, x, t, a: faixa_series(p, [
            {"nome": "Taxa de falha do mês", "cor": "var(--serie-2)", "dados": taxa},
        ], x, t, a, rotulos, "Taxa de falha do mês · % do parque", casas=2, unidade="%")},
    ])


def fig_cumulativa(dados, rotulos, meses, acervo):
    ind = [m["entraram_acumulado"] - acervo for m in meses]
    com_acervo = [m["entraram_acumulado"] for m in meses]
    resolvidos = [m["resolvidos_acumulado"] for m in meses]
    coep = [m["resolvidos_coep_acumulado"] for m in meses]
    return figura(dados, rotulos, [
        {"altura": 70, "desenha": lambda p, x, t, a: faixa_parque(p, dados, x, t, a, rotulos)},
        {"altura": 235, "desenha": lambda p, x, t, a: faixa_series(p, [
            {"nome": "Entrantes — com o acervo herdado", "cor": "var(--serie-2)", "dados": com_acervo},
            {"nome": "Indisponibilidade acumulada — só 2026", "cor": "var(--serie-1)", "dados": ind},
            {"nome": "Resolvidos — todas as cadeias", "cor": "var(--serie-3)", "dados": resolvidos},
            {"nome": "Resolvidos pelo COEP", "cor": "var(--serie-3)", "dados": coep,
             "tracejado": True, "acima": False},
        ], x, t, a, rotulos, "Equipamentos, acumulado no ano")},
    ])


def tabela(dados, meses, tipo):
    cab = ("<tr><th>Mês</th><th class='num'>Parque</th><th class='num'>Entrantes</th>"
           "<th class='num'>Resolvidos</th><th class='num'>Falhas</th>"
           "<th class='num'>Taxa do mês</th><th class='num'>Indisp. acum.</th>"
           "<th class='num'>Com acervo</th><th class='num'>Resolv. acum.</th>"
           "<th class='num'>Pelo COEP</th><th class='num'>Fila</th></tr>")
    linhas = "".join(
        f"<tr><td>{esc(d['rotulo'])}</td><td class='num'>{br(d['parque'])}</td>"
        f"<td class='num'>{d['entrantes'] or '—'}</td>"
        f"<td class='num'>{m['resolvidos_no_mes'] or '—'}</td>"
        f"<td class='num'>{d['falhas'] or '—'}</td>"
        f"<td class='num'>{br(d['taxa_mes_pct'], 2)}%</td>"
        f"<td class='num'>{br(m['entraram_acumulado'] - acervo)}</td>"
        f"<td class='num'>{br(m['entraram_acumulado'])}</td>"
        f"<td class='num'>{br(m['resolvidos_acumulado'])}</td>"
        f"<td class='num'>{br(m['resolvidos_coep_acumulado'])}</td>"
        f"<td class='num'>{br(m['fila'])}</td></tr>"
        for d, m, acervo in ((d, m, meses[0]["entraram_acumulado"] - dados[0]["entrantes"])
                             for d, m in zip(dados, meses)))
    return (f'<details class="tabela"><summary>Os números de {esc(NOME[tipo].lower())}, '
            f'mês a mês</summary><div class="rolagem"><table>{cab}{linhas}</table></div></details>')


def bloco(tipo, dados, cum):
    rot = [d["rotulo"] for d in dados]
    m = cum["meses"]
    acervo = cum["acervo_em_janeiro"]
    ent_ano = cum["entraram_no_ano"]
    pico_ent = max(dados, key=lambda d: d["entrantes"])
    pico_taxa = max(dados, key=lambda d: d["taxa_mes_pct"])
    return f"""
    <section class="bloco">
      <div class="marcador"><h2>{esc(NOME[tipo])}</h2>
        <span>parque de {br(dados[0]['parque'])} a {br(dados[-1]['parque'])} ·
        fila de {br(acervo)} a {br(m[-1]['fila'])}</span></div>

      <h3>2026, mês a mês</h3>
      <p class="texto">O parque sobe de <b>{br(dados[0]['parque'])}</b> para
      <b>{br(dados[-1]['parque'])}</b> com a expansão. No meio, quem <b>saiu de operação</b> contra
      quem foi <b>resolvido</b> — pico de entrada em {esc(pico_ent['rotulo'])}
      ({br(pico_ent['entrantes'])}). Embaixo, a <b>taxa de falha do mês</b>: só peça grande,
      dividida pelo parque daquele mês, com máxima de {br(pico_taxa['taxa_mes_pct'], 2)}% em
      {esc(pico_taxa['rotulo'])}.</p>
      {legenda([
        {"nome": "Parque", "cor": "var(--serie-4)", "dica": "faixa de cima"},
        {"nome": "Entrantes fora de operação", "cor": "var(--serie-1)", "dica": "pela ocorrência"},
        {"nome": "Resolvidos", "cor": "var(--serie-3)", "dica": "cadeia fechada no mês"},
        {"nome": "Taxa de falha", "cor": "var(--serie-2)", "dica": "faixa de baixo"},
      ])}
      {fig_mensal(dados, rot)}

      <h3>2026 acumulado, com o que veio de antes</h3>
      <p class="texto">O ano não começa do zero: <b>{br(acervo)}</b> equipamentos já estavam fora
      de operação em 1º de janeiro, herdados de 2024 e 2025. A laranja é a fila inteira — acervo
      mais os <b>{br(ent_ano)}</b> que entraram no ano; a azul mostra só o que entrou em 2026, e a
      distância entre as duas é exatamente o acervo. Em verde, o que foi resolvido:
      <b>{br(cum['resolvidos_no_ano'])}</b> cadeias fechadas por qualquer posto, e tracejado o que
      o <b>COEP resolveu</b> — <b>{br(cum['resolvidos_coep_no_ano'])}</b> dos 82 do posto são
      {esc(NOME[tipo].lower().split()[0])}. A conta fecha: {br(acervo)} + {br(ent_ano)} −
      {br(cum['resolvidos_no_ano'])} = <b>{br(m[-1]['fila'])}</b>, o número de cadeias abertas
      hoje.</p>
      {legenda([
        {"nome": "Parque", "cor": "var(--serie-4)", "dica": "faixa de cima"},
        {"nome": "Entrantes — com o acervo herdado", "cor": "var(--serie-2)"},
        {"nome": "Indisponibilidade acumulada — só 2026", "cor": "var(--serie-1)"},
        {"nome": "Resolvidos — todas as cadeias", "cor": "var(--serie-3)"},
        {"nome": "Resolvidos pelo COEP", "cor": "var(--serie-3)", "tracejado": True,
         "dica": "a régua do posto"},
      ])}
      {fig_cumulativa(dados, rot, m, acervo)}

      {tabela(dados, m, tipo)}
    </section>"""


def montar():
    with open(os.path.join(RAIZ, "data", "missao", "parque_2026.json"),
              encoding="utf-8") as fh:
        p = json.load(fh)
    # o mensal precisa dos resolvidos do mês, que moram na série cumulativa
    for t in ("RL", "RT"):
        for d, m in zip(p["series"][t], p["cumulativo"][t]["meses"]):
            d["resolvidos_no_mes"] = m["resolvidos_no_mes"]
    corpo = "".join(bloco(t, p["series"][t], p["cumulativo"][t]) for t in ("RL", "RT"))
    html = f"""<title>Parque e falhas 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap">
<style>
:root {{
  --papel:#f2efe6; --papel-2:#e9e5d8; --fundo:#fcfcfb;
  --tinta:#211d15; --tinta-2:#57513f; --tinta-3:#8d8672; --filete:#c8c2af;
  --serie-1:#2f56b0; --serie-2:#bc4b0e; --serie-3:#2e7f52; --serie-4:#6a4c93;
  --leitura: Spectral, Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --papel:#191713; --papel-2:#221f1a; --fundo:#1a1a19;
    --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563; --filete:#403a2e;
    --serie-1:#6b8fe0; --serie-2:#e0703a; --serie-3:#35a58c; --serie-4:#9a7bcc;
  }}
}}
:root[data-theme="dark"] {{
  --papel:#191713; --papel-2:#221f1a; --fundo:#1a1a19;
  --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563; --filete:#403a2e;
  --serie-1:#6b8fe0; --serie-2:#e0703a; --serie-3:#35a58c; --serie-4:#9a7bcc;
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--papel); color:var(--tinta); font-family:var(--leitura);
  font-size:16px; line-height:1.6; }}
.folha {{ max-width:880px; margin:0 auto; padding:32px 20px 64px; }}
.capa {{ border-bottom:2px solid var(--tinta); padding-bottom:14px; }}
.capa h1 {{ margin:0; font-size:26px; letter-spacing:.06em; text-transform:uppercase;
  font-family:var(--mono); font-weight:700; }}
.capa p {{ margin:6px 0 0; color:var(--tinta-2); font-size:14.5px; }}
.bloco {{ margin-top:38px; background:var(--fundo); border:1px solid var(--filete);
  padding:20px 22px 24px; }}
.marcador {{ display:flex; flex-wrap:wrap; gap:6px 14px; align-items:baseline;
  border-bottom:1px solid var(--tinta); padding-bottom:8px; margin-bottom:16px; }}
.marcador h2 {{ margin:0; font-size:19px; font-family:var(--mono); font-weight:700;
  letter-spacing:.04em; text-transform:uppercase; }}
.marcador span {{ color:var(--tinta-3); font-family:var(--mono); font-size:12.5px; }}
h3 {{ font-size:12px; font-family:var(--mono); font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; color:var(--tinta-2); margin:30px 0 6px; }}
.bloco h3:first-of-type {{ margin-top:4px; }}
.texto {{ margin:0 0 12px; font-size:15px; color:var(--tinta-2); }}
.texto b {{ color:var(--tinta); }}
.fig {{ width:100%; height:auto; display:block; overflow:visible; }}
.grade {{ stroke:var(--filete); stroke-width:1; opacity:.5; }}
.rot-y, .rot-x {{ font-family:var(--mono); font-size:10.5px; fill:var(--tinta-3); }}
.rot-y {{ text-anchor:end; }}
.rot-x {{ text-anchor:middle; text-transform:uppercase; letter-spacing:.06em; }}
.rot-valor {{ font-family:var(--mono); font-size:11px; fill:var(--tinta); font-weight:600; }}
.faixa-nome {{ font-family:var(--mono); font-size:9.5px; fill:var(--tinta-3);
  letter-spacing:.07em; text-transform:uppercase; }}
.legenda {{ display:flex; flex-wrap:wrap; gap:6px 18px; margin:2px 0 12px; }}
.legenda span {{ display:flex; align-items:center; gap:7px; font-family:var(--mono);
  font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--tinta-2); }}
.legenda i {{ width:14px; height:3px; border-radius:2px; flex:none; }}
.legenda i.tracejo {{ background:none !important; border-top:3px dashed var(--serie-3); height:0; }}
.legenda em {{ font-style:italic; font-family:var(--leitura); text-transform:none;
  letter-spacing:0; color:var(--tinta-3); font-size:12.5px; }}
.tabela {{ margin-top:24px; border-top:1px solid var(--filete); padding-top:10px; }}
.tabela summary {{ cursor:pointer; font-family:var(--mono); font-size:11.5px;
  text-transform:uppercase; letter-spacing:.06em; color:var(--tinta-2); }}
.rolagem {{ overflow-x:auto; margin-top:10px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; min-width:660px; }}
th {{ text-align:left; font-family:var(--mono); font-size:10px; font-weight:700;
  text-transform:uppercase; letter-spacing:.04em; color:var(--tinta-2);
  border-bottom:1px solid var(--tinta); padding:6px 7px; }}
td {{ padding:6px 7px; border-bottom:1px dotted var(--filete); font-family:var(--mono);
  font-size:12.5px; }}
th.num, td.num {{ text-align:right; }}
.nota {{ margin-top:34px; border:1px solid var(--filete); border-left:3px solid var(--tinta-3);
  background:var(--papel-2); padding:14px 16px; font-size:14px; color:var(--tinta-2); }}
.nota b {{ color:var(--tinta); }}
.nota ul {{ margin:8px 0 0; padding-left:20px; }}
.nota li {{ margin:5px 0; }}
</style>
<div class="folha">
  <div class="capa">
    <h1>Parque e falhas 2026</h1>
    <p>Religador e regulador, cada um com duas leituras do ano: o mês a mês e o acumulado
    com o que veio de antes. Janeiro a agosto — agosto parcial, até 20/08.</p>
  </div>
  {corpo}
  <div class="nota">
    <b>De onde vem cada linha.</b>
    <ul>
      <li><b>Parque</b> — base de janeiro do gestor ({br(p['base_janeiro']['RL'])} religadores,
      {br(p['base_janeiro']['RT'])} reguladores) mais a expansão realizada, somada no próprio mês.
      Agosto repete julho porque a expansão do mês ainda não fechou. A faixa tem escala própria:
      um crescimento de 1% sumiria numa escala que começasse em zero.</li>
      <li><b>Entrantes</b> — equipamento com SS de indisponibilidade para operação, pela
      <b>data da ocorrência</b>, não a da abertura (que atrasa 39 dias em média).</li>
      <li><b>Resolvidos</b> — a cadeia de SS fechada, atendida ou cancelada, por qualquer posto.
      Cadeia cancelada não tem data de conclusão no SGM, então é datada pela abertura da última
      SS dela: é aproximação, e é o que existe.</li>
      <li><b>Resolvidos pelo COEP</b> — a régua do posto: a demanda passou pelo COEP dentro de
      2026 e a cadeia fechou dentro de 2026. São 82 no total, {br(p['cumulativo']['RL']['resolvidos_coep_no_ano'])}
      religadores e {br(p['cumulativo']['RT']['resolvidos_coep_no_ano'])} reguladores.</li>
      <li><b>Taxa de falha</b> — só <b>peça grande</b> (controle, tanque ou completo no religador;
      célula, relé, completo ou furto no regulador), dividida pelo parque daquele mês. Fecha o ano
      em {p['totais']['RL']['falhas_somadas']} religadores e {p['totais']['RT']['falhas_somadas']}
      reguladores — os mesmos números da página da taxa. Somar os meses passa do total do ano:
      no ano, o ativo que falha duas vezes conta uma vez só.</li>
    </ul>
  </div>
</div>"""
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"OK — {SAIDA} ({len(html)//1024} KB)")


if __name__ == "__main__":
    montar()
