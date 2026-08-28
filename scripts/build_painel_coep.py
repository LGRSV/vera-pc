"""
O painel do COEP, refeito a partir da planilha base.

«Essa é a planilha base de equipamentos especiais, tudo que tiver nela é a nova
verdade — refaça os artifacts a partir dela» (gestor, 28/08).

A página segue a ORDEM DAS ABAS da planilha, que é a ordem da história: a esteira dos
53 que o DCMD deve, o dinheiro, a taxa de falha, o porquê de cada falha, a dinâmica do
posto e o SLA do campo.

Tema: Prontuário Industrial (assets/TEMA.md) — papel técnico, filete duplo, leader
pontilhado, cantos retos. A cor é sinal, não decoração: aparece na criticidade, no
atraso e no laranja de destaque.

Uma ressalva que a página declara: a aba «SLA por equipe» da planilha está na régua
antiga (8/15/30/50). O SLA mostrado aqui é o da proposta DCMD que o gestor fechou
depois — 11/20/40/60, e 60 sem classificação.

Grava dist/painel-coep.html.
Rodar: python3 scripts/build_painel_coep.py
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "dist", "painel-coep.html")
BASE = os.path.join(RAIZ, "data", "missao", "base_coep.json")
SLA = os.path.join(RAIZ, "data", "missao", "sla_coep.json")
PARTICAO = os.path.join(RAIZ, "data", "missao", "particao_coep.json")

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
CURTO = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
CRIT = ["Muito Alta", "Alta", "Média", "Baixa", "Falta definir"]
COR_CRIT = {"Muito Alta": "muito-alta", "Alta": "alta", "Média": "media",
            "Baixa": "baixa", "Falta definir": "sem", "Sem classificação": "sem",
            "—": "sem", "": "sem"}


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def br(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "·").replace(".", ",").replace("·", ".")


def moeda(v):
    if v >= 1e6:
        return f"R$ {br(v / 1e6, 2)} mi"
    return f"R$ {br(v / 1e3, 0)} mil"


def pct(v, casas=1):
    return f"{br(100 * v, casas)}%"


def marcador(titulo, nota=""):
    return (f'<div class="marcador"><h2>{esc(titulo)}</h2>'
            + (f"<span>{esc(nota)}</span>" if nota else "") + "</div>")


def numero(rotulo, valor, nota="", tom=""):
    return (f'<div class="num{" " + tom if tom else ""}">'
            f'<b>{valor}</b><span>{esc(rotulo)}</span>'
            + (f'<i>{esc(nota)}</i>' if nota else "") + "</div>")


def barras(itens, total=None, classe=""):
    """Barra horizontal com rótulo e valor — o leader pontilhado do formulário."""
    total = total or max((v for _, v, *_ in itens), default=1) or 1
    linhas = []
    for item in itens:
        rot, val = item[0], item[1]
        tom = item[2] if len(item) > 2 else ""
        largura = max(1.5, 100 * val / total)
        linhas.append(
            f'<div class="barra{" " + tom if tom else ""}">'
            f'<span class="barra-rot">{esc(rot)}</span>'
            f'<span class="barra-trilho"><i style="width:{largura:.1f}%"></i></span>'
            f'<b class="barra-val">{br(val)}</b></div>')
    return f'<div class="barras {classe}">' + "".join(linhas) + "</div>"


# ---------------------------------------------------------------- 1. a esteira
def bloco_esteira(g):
    marcos = g["marcos"]
    preenchidos = g["marcos_preenchidos"]
    total = g["qtd"]
    trilho_legenda = "".join(
        f'<li><i class="casa"></i><span>{esc(m)}</span>'
        f'<b>{preenchidos[m]}<em>/{total}</em></b></li>' for m in marcos)

    linhas = []
    for a in g["ativos"]:
        casas = "".join(
            f'<i class="casa{" cheia" if m["valor"] else ""}" '
            f'title="{esc(m["nome"])}{": " + esc(m["valor"]) if m["valor"] else " — em branco"}">'
            "</i>" for m in a["marcos"])
        atraso = "atrasado" if a["dias_pendente"] >= 180 else (
            "atencao" if a["dias_pendente"] >= 90 else "")
        linhas.append(
            f'<tr data-status="{esc(a["status"])}" data-crit="{esc(a["criticidade"])}">'
            f'<td class="cod">{esc(a["ativo"])}</td>'
            f'<td><span class="etiqueta {a["tipo"].lower()}">{esc(a["tipo"])}</span></td>'
            f'<td class="praca">{esc(a["municipio"] or "—")}</td>'
            f'<td><span class="pastilha {COR_CRIT.get(a["criticidade"], "sem")}">'
            f'{esc(a["criticidade"])}</span></td>'
            f'<td class="estado">{esc(a["status"])}</td>'
            f'<td class="defeito">{esc(a["defeito"] or "—")}</td>'
            f'<td class="num-col">{moeda(a["total"])}</td>'
            f'<td class="num-col {atraso}">{br(a["dias_pendente"])}</td>'
            f'<td class="trilho"><span>{casas}</span></td></tr>')

    status = [(s, n) for s, n in g["por_status"].items()]
    crit = [(c, g["por_criticidade"].get(c, 0), COR_CRIT[c])
            for c in CRIT if g["por_criticidade"].get(c)]

    return f"""<section class="bloco" id="esteira">
  {marcador("A esteira dos 53", f"o que o DCMD deve · {moeda(g['orcamento_total'])} parados")}
  <p class="texto">A planilha base trouxe uma coisa que nenhuma versão anterior tinha:
  <b>dez marcos de execução por ativo</b>, do PMA ao comissionamento. Hoje estão todos em
  branco — é o trilho que o gestor vai preencher, e cada casa acesa passa a contar uma
  etapa vencida.</p>
  <ul class="legenda-trilho">{trilho_legenda}</ul>
  <div class="duas">
    <div><h3>Onde estão hoje</h3>{barras([(s, n) for s, n in status])}</div>
    <div><h3>Criticidade da operação</h3>
      {barras([(c, n, t) for c, n, t in crit], classe="cor")}</div>
  </div>
  <div class="filtros" role="group" aria-label="Filtrar a lista">
    <button class="chip ativo" data-filtro="todos">Todos os {total}</button>
    {"".join(f'<button class="chip" data-filtro="status:{esc(s)}">{esc(s)} <em>{n}</em></button>' for s, n in status)}
    {"".join(f'<button class="chip" data-filtro="crit:{esc(c)}">{esc(c)} <em>{n}</em></button>' for c, n, _ in crit)}
  </div>
  <div class="rolagem">
  <table class="tabela" id="tab-esteira">
    <thead><tr><th>Ativo</th><th>Tipo</th><th>Praça</th><th>Criticidade</th>
      <th>Status</th><th>Peça</th><th class="num-col">Orçamento</th>
      <th class="num-col">Dias</th><th>Esteira</th></tr></thead>
    <tbody>{"".join(linhas)}</tbody>
  </table></div>
  <p class="rodape-nota">Dias em <b class="atrasado">vermelho</b> passam de 180;
  em <b class="atencao">ocre</b>, de 90. O trilho tem uma casa por marco, na ordem da
  esteira — passe o cursor para ver qual.</p>
</section>"""


# ------------------------------------------------------------- 2. o orçamento
def bloco_orcamento(g):
    ORCADO = 6_100_000
    por_status = {}
    for a in g["ativos"]:
        d = por_status.setdefault(a["status"], {"n": 0, "v": 0.0})
        d["n"] += 1
        d["v"] += a["total"]
    ordem = sorted(por_status.items(), key=lambda x: -x[1]["v"])
    mo = sum(a["mo"] for a in g["ativos"])
    mat = sum(a["mat"] for a in g["ativos"])
    tot = g["orcamento_total"]
    linhas = "".join(
        f'<tr><td>{esc(s)}</td><td class="num-col">{d["n"]}</td>'
        f'<td class="num-col">{moeda(d["v"])}</td>'
        f'<td class="num-col">{pct(d["v"] / tot)}</td></tr>' for s, d in ordem)
    return f"""<section class="bloco" id="orcamento">
  {marcador("O dinheiro parado", f"{moeda(tot)} nos 53 · {moeda(ORCADO)} orçados no ano")}
  <div class="numeros">
    {numero("Nos 53 pendentes", moeda(tot), f"{pct(tot / ORCADO)} do orçado", "sinal")}
    {numero("Material", moeda(mat), f"{pct(mat / tot)} do total")}
    {numero("Mão de obra", moeda(mo), f"{pct(mo / tot)} do total")}
  </div>
  <div class="rolagem"><table class="tabela">
    <thead><tr><th>Status</th><th class="num-col">Ativos</th>
      <th class="num-col">Orçamento</th><th class="num-col">Fatia</th></tr></thead>
    <tbody>{linhas}</tbody></table></div>
  <p class="texto">O material responde por <b>{pct(mat / tot)}</b> do valor parado. É a
  compra que trava a fila — não a mão de obra.</p>
</section>"""


# --------------------------------------------------------- 3. a taxa de falha
def figura_mensal(serie, parque_label, cor):
    """Uma linha por ano, no eixo dos doze meses — SVG, sem biblioteca."""
    W, H, L, R, T, B = 720, 190, 46, 16, 18, 34
    vals = [d["falhas"] for d in serie]
    topo = max(max(vals, default=0), 1)
    topo = topo + (2 - topo % 2 if topo % 2 else 0)
    x = lambda i: L + (W - L - R) / 11 * i
    y = lambda v: T + (H - T - B) * (1 - v / topo)
    grade, rot = [], []
    passo = max(1, topo // 4)
    v = 0
    while v <= topo:
        grade.append(f'<line x1="{L}" y1="{y(v):.1f}" x2="{W-R}" y2="{y(v):.1f}" class="grade"/>')
        rot.append(f'<text x="{L-7}" y="{y(v)+4:.1f}" class="rot-y">{v}</text>')
        v += passo
    pts = " ".join(f"{x(i):.1f},{y(d['falhas']):.1f}" for i, d in enumerate(serie))
    bolas = "".join(
        f'<circle cx="{x(i):.1f}" cy="{y(d["falhas"]):.1f}" r="3.5" fill="{cor}" '
        f'stroke="var(--papel)" stroke-width="1.5"><title>{esc(CURTO[i])}: '
        f'{d["falhas"]} falha(s) · parque {br(d["parque"])}</title></circle>'
        for i, d in enumerate(serie))
    meses = "".join(f'<text x="{x(i):.1f}" y="{H-12}" class="rot-x">{CURTO[i]}</text>'
                    for i in range(12))
    return (f'<svg viewBox="0 0 {W} {H}" class="fig" role="img" '
            f'aria-label="Falhas por mês, {esc(parque_label)}">'
            + "".join(grade) + "".join(rot)
            + f'<polyline points="{pts}" fill="none" stroke="{cor}" stroke-width="2" '
              'stroke-linejoin="round"/>' + bolas + meses + "</svg>")


def bloco_taxa(mensal, falhas):
    partes = []
    for chave, rotulo, cor in (("RL|2025", "Religador · 2025", "var(--sinal)"),
                               ("RL|2026", "Religador · 2026", "var(--sinal)"),
                               ("RT|2025", "Regulador · 2025", "var(--oliva)"),
                               ("RT|2026", "Regulador · 2026", "var(--oliva)")):
        serie = mensal.get(chave)
        if not serie:
            continue
        serie = sorted(serie, key=lambda d: MESES.index(d["mes"]) if d["mes"] in MESES else 99)
        while len(serie) < 12:
            serie.append({"mes": MESES[len(serie)], "falhas": 0, "parque": serie[-1]["parque"]})
        total = sum(d["falhas"] for d in serie)
        parque = max(d["parque"] for d in serie) or 1
        partes.append(
            f'<div class="figura"><h3>{esc(rotulo)}</h3>'
            f'<p class="sub">{total} ocorrências · parque {br(parque)} · '
            f'{pct(total / parque, 2)}</p>'
            + figura_mensal(serie, rotulo, cor) + "</div>")
    tensao = [(t, n) for t, n in falhas["por_tensao"].items()]
    return f"""<section class="bloco" id="taxa">
  {marcador("Taxa de falha", "ocorrência lida na SS ÷ parque do ano")}
  <p class="texto">A conta aqui é de <b>ocorrência</b>, como na planilha base: cada falha
  lida e revisada na descrição da SS. A taxa anual oficial soma ainda o complemento por
  obra direta do AIC — falha provada pela obra, sem narrativa de SS, que não tem mês para
  cair.</p>
  <div class="figuras">{"".join(partes)}</div>
  <h3>Por classe de tensão</h3>
  {barras([(t, n) for t, n in tensao])}
  <p class="texto"><b>{br(falhas["por_tensao"].get("34.500", 0))}</b> das
  {falhas["qtd"]} ocorrências são em 34,5 kV. O parque cadastrado tem 832 religadores e
  137 reguladores nessa classe — a falha acompanha o tamanho do parque, não o inverso.</p>
</section>"""


# ------------------------------------------------------ 4. por que falharam
def bloco_causas(f):
    causas = [(c, n, "sem" if "SEM CAUSA" in c else "") for c, n in f["por_causa"].items()]
    fatias = sorted(f["causa_por_fatia"])
    colunas = []
    for fatia in fatias:
        d = f["causa_por_fatia"][fatia]
        tot = sum(d.values())
        sem = d.get("SEM CAUSA DESCRITA NO TEXTO", 0)
        colunas.append(
            f'<div class="fatia"><h4>{esc(fatia)}</h4>'
            f'<p class="sub">{tot} ocorrências · <b>{pct(sem / tot, 0)}</b> sem causa</p>'
            + "".join(f'<div class="linha-causa"><span>{esc(c)}</span><b>{n}</b></div>'
                      for c, n in list(d.items())[:6]) + "</div>")
    exemplos = [i for i in f["itens"] if i["citacao"] and "SEM CAUSA" not in i["causa"]][:6]
    citacoes = "".join(
        f'<li><b class="cod">{esc(i["ativo"])}</b> <span class="causa-tag">'
        f'{esc(i["causa"])}</span><q>{esc(i["citacao"][:190])}</q>'
        f'<i>{esc(i["ss"])} · {esc(i["data"])}</i></li>' for i in exemplos)
    sem_total = f["por_causa"].get("SEM CAUSA DESCRITA NO TEXTO", 0)
    return f"""<section class="bloco" id="causas">
  {marcador("Por que falharam", f"{f['qtd']} ocorrências lidas e revisadas")}
  <p class="texto">Modo de falha é a peça que quebrou; <b>causa raiz é por que ela
  quebrou</b>. A causa só entra com citação do texto da SS — quem só descreve o modo fica
  como «sem causa descrita». Nenhum laudo foi chutado.</p>
  {barras(causas)}
  <p class="texto destaque"><b>{sem_total} das {f["qtd"]}</b> ocorrências fecham sem dizer
  por que a peça quebrou. Sem causa registrada não há prevenção possível — é o achado que
  mais pede ação, e ele é de processo, não de equipamento.</p>
  <div class="fatias">{"".join(colunas)}</div>
  <h3>A prova, no texto da própria SS</h3>
  <ul class="citacoes">{citacoes}</ul>
</section>"""


# ------------------------------------------------------- 5. a dinâmica dos 143
def bloco_dinamica(r, pc):
    """A dinâmica na régua de 28/08 — a partição de particao_coep.py."""
    c = pc["contas"]
    itens = r["itens"]
    parados = sorted((i for i in itens if i["situacao"] == "Na fila do posto"),
                     key=lambda x: -x["dias"])[:10]
    linhas = "".join(
        f'<tr><td class="cod">{esc(i["ativo"])}</td>'
        f'<td class="praca">{esc(i["localidade"])}</td>'
        f'<td><span class="pastilha {COR_CRIT.get(i["criticidade"], "sem")}">'
        f'{esc(i["criticidade"])}</span></td>'
        f'<td class="cod">{esc(i["ss"])}</td>'
        f'<td class="num-col atrasado">{br(i["dias"])}</td></tr>' for i in parados)
    fora = "".join(
        f'<li><b class="cod">{esc(x["ativo"])}</b>'
        f'<span>{esc(x["localidade"])}</span>'
        f'<i>{esc(x["onde_esta"])} · {br(x["dias_la"])} dia{"s" if x["dias_la"] != 1 else ""} lá · '
        f'{esc(x["etapa"].split("—")[0].strip())}</i></li>'
        for x in sorted(pc["resolvidos_por_outra_mesa"] + pc["em_execucao"],
                        key=lambda z: -z["dias_la"]))
    return f"""<section class="bloco" id="dinamica">
  {marcador("A dinâmica do posto",
            f"{c['passaram']} passaram · conta do posto {c['conta_do_posto']}")}
  <div class="numeros">
    {numero("Trabalho do COEP concluído", br(c["trabalho_do_coep_concluido"]), f"{c['resolvidos']} encerradas + {c['despachados_para_outra_mesa']} despachadas", "bom")}
    {numero("Demanda encerrada", br(c["resolvidos"]), f"{pc['por_tipo'].get('RL', 0)} RL · {pc['por_tipo'].get('RT', 0)} RT", "bom")}
    {numero("Na fila do posto", br(c["na_fila"]), "esperando o posto", "atento")}
    {numero("Em execução no campo", br(c["em_execucao_no_campo"]), "obra acontecendo agora")}
  </div>
  <p class="texto">Cada equipamento conta <b>uma vez</b>. Quem resolveu uma demanda no ano
  e <b>voltou</b> para a fila conta como pendente, não como resolvido — são
  <b>{c["voltaram_para_a_fila"]}</b> nessa situação.</p>
  <p class="texto destaque">São <b>duas leituras</b> de «resolvido», e as duas estão
  certas — respondem a perguntas diferentes. <b>{c["trabalho_do_coep_concluido"]}</b> é o
  <b>escopo do posto</b>: o COEP diagnosticou, despachou e a peça foi trocada. Desses,
  <b>{c["resolvidos"]}</b> tiveram a <b>demanda encerrada</b> de ponta a ponta; os outros
  <b>{c["despachados_para_outra_mesa"]}</b> saíram para ajuste de proteção ou
  comissionamento e <b>seguem com SS aberta</b> na mesa seguinte — de 1 a 41 dias lá.
  Para cobrar o posto, vale {c["trabalho_do_coep_concluido"]}; para dizer o que o parque
  ganhou de volta, vale {c["resolvidos"]}.</p>
  <p class="texto">A <b>conta do posto</b> — o que ainda é do COEP ou passou por ele e
  acabou — é <b>{c["conta_do_posto"]}</b>: {c["resolvidos"]} encerradas mais
  {c["na_fila"]} na fila. Os outros <b>{c["fora_do_posto"]}</b> estão fora da mesa,
  esperando outro braço.</p>
  <h3>Os {c["fora_do_posto"]} que estão fora do posto</h3>
  <p class="texto">Saíram da fila do COEP e ainda não fecharam. Os
  <b>{c["despachados_para_outra_mesa"]}</b> que já voltaram do campo entram no trabalho
  concluído do posto e passam para <b>demanda encerrada</b> quando a mesa seguinte fechar
  a SS. Os <b>{c["em_execucao_no_campo"]}</b> em execução ainda estão com um COCM: não
  entram em nenhuma das duas contas até a equipe devolver.</p>
  <ul class="no-campo">{fora}</ul>
  <h3>Os dez mais parados na fila</h3>
  <div class="rolagem"><table class="tabela">
    <thead><tr><th>Ativo</th><th>Praça</th><th>Criticidade</th><th>SS</th>
      <th class="num-col">Dias</th></tr></thead><tbody>{linhas}</tbody></table></div>
  <p class="rodape-nota">Os dois primeiros esperam desde janeiro de 2023 — mais de mil e
  duzentos dias.</p>
</section>"""


def bloco_quadro(pc):
    """Os 143 pelo ANO DA DEMANDA, com tipo nas linhas.

    O passivo aqui é o que importa: demanda nascida em 2023, 2024 ou 2025 que ainda
    estava viva quando o ano virou — não o ano em que o equipamento chegou à mesa.
    """
    q = pc["quadro_ano"]
    anos = pc["anos"]
    ROT = {"RL": "Religador", "RT": "Regulador", "Total": "Total"}

    def celulas(tipo, grupo):
        d = q[tipo][grupo]
        return ("".join(f'<td class="num-col{" passivo" if a != "2026" else ""}">'
                        f'{br(d[a]) if d[a] else "—"}</td>' for a in anos[:3])
                + f'<td class="num-col forte passivo">{br(d["passivo"]) if d["passivo"] else "—"}</td>'
                + f'<td class="num-col">{br(d["2026"]) if d["2026"] else "—"}</td>'
                + f'<td class="num-col forte">{br(d["total"]) if d["total"] else "—"}</td>')

    def faixa(grupo, rotulo, classe=""):
        linhas = "".join(
            f'<tr class="{classe}{" total" if t == "Total" else ""}">'
            f'<td class="rot">{esc(ROT[t])}</td>{celulas(t, grupo)}</tr>'
            for t in ("RL", "RT", "Total"))
        marca = " recorte" if "recorte" in classe else ""
        return (f'<tr class="faixa{marca}"><td colspan="7">{esc(rotulo)}</td></tr>'
                + linhas)

    cabeca = ("".join(f'<th class="num-col{" passivo" if a != "2026" else ""}">{a}</th>'
                      for a in anos[:3])
              + '<th class="num-col passivo">Passivo<br><em>23+24+25</em></th>'
              + '<th class="num-col">2026</th><th class="num-col">Total</th>')

    p_res = q["Total"]["resolvidos"]["passivo"] / q["Total"]["geral"]["passivo"]
    n_res = q["Total"]["resolvidos"]["2026"] / q["Total"]["geral"]["2026"]
    vezes = p_res / n_res
    velhos = pc["passivo_na_fila"][:6]
    lista = "".join(
        f'<li><b class="cod">{esc(x["ativo"])}</b><span>{esc(x["localidade"])}</span>'
        f'<i>desde {esc(x["desde"])} · {br(x["dias"])} dias</i></li>' for x in velhos)

    return f"""<section class="bloco" id="quadro">
  {marcador("O quadro por ano da demanda",
            f"{q['Total']['geral']['total']} passaram · conta do posto "
            f"{q['Total']['resolvidos']['total'] + q['Total']['fila']['total']}")}
  <p class="texto">O ano é o da <b>demanda</b>, não o da chegada à mesa: uma falha de 2025
  que só foi resolvida agora conta em 2025. É assim que o <b>passivo</b> aparece — o que
  o ano herdou vivo.</p>
  <p class="texto">A primeira faixa é o <b>escopo do posto</b> e abre nas duas de baixo:
  o COEP concluiu o trabalho dele em <b>{q["Total"]["coep_concluiu"]["total"]}</b>
  equipamentos, dos quais <b>{q["Total"]["resolvidos"]["total"]}</b> tiveram a demanda
  encerrada de ponta a ponta e <b>{q["Total"]["despachados"]["total"]}</b> seguem com SS
  aberta na mesa seguinte. Ela <b>não entra na soma</b> das outras — é um recorte por
  cima delas.</p>
  <div class="rolagem"><table class="tabela quadro-ano">
    <thead><tr><th>&nbsp;</th>{cabeca}</tr></thead>
    <tbody>
      {faixa("coep_concluiu", "Trabalho do COEP concluído · recorte, não soma com as de baixo", "bom recorte")}
      {faixa("resolvidos", "├ demanda encerrada de ponta a ponta", "bom sub")}
      {faixa("despachados", "└ despachados, SS aberta na mesa seguinte", "sub")}
      {faixa("fila", "Na fila do posto")}
      {faixa("execucao", "Em execução no campo")}
      {faixa("geral", "Passaram pelo posto", "geral")}
    </tbody>
  </table></div>
  <p class="texto destaque">O passivo é <b>{br(q["Total"]["geral"]["passivo"])} dos
  {br(q["Total"]["geral"]["total"])}</b>, e o posto liquidou <b>{pct(p_res, 0)}</b> dele —
  contra <b>{pct(n_res, 0)}</b> do que nasceu em 2026. O antigo saiu com quase
  <b>{vezes:.0f} vezes</b> a eficácia do novo, que é o inverso do que uma fila costuma
  fazer. <b>2024 foi zerado</b>: as doze demandas daquele ano fecharam todas.</p>
  <h3>O que resiste do passivo</h3>
  <p class="texto">Sobram <b>{br(q["Total"]["fila"]["passivo"])}</b> demandas antigas na
  fila — quase todas de 2025, e duas de 2023 que passam de mil e trezentos dias.</p>
  <ul class="no-campo">{lista}</ul>
</section>"""

# ------------------------------------------------------------------ 6. o SLA
def bloco_sla(s):
    t = s["total"]
    equipes = sorted(s["por_equipe"].items(), key=lambda x: -x[1]["entregas"])
    linhas = "".join(
        f'<tr><td class="cod">{esc(q)}</td>'
        f'<td class="num-col">{d["entregas"]}</td>'
        f'<td class="num-col">{d["no_prazo"]}</td>'
        f'<td class="num-col"><span class="pastilha {"baixa" if d["cumprimento"] >= .8 else ("media" if d["cumprimento"] >= .6 else "muito-alta")}">'
        f'{pct(d["cumprimento"], 0)}</span></td>'
        f'<td class="num-col">{br(d["mediana"])}</td>'
        f'<td class="num-col {"atrasado" if d["indice"] > 1 else ""}">{br(d["indice"], 2)}</td>'
        f'<td class="num-col">{br(d["pior"])}</td></tr>' for q, d in equipes)
    regua = " · ".join(f"{k} {v}" for k, v in s["regua"].items())
    return f"""<section class="bloco" id="sla">
  {marcador("SLA de manutenção", "do repasse ao COCM até a saída do DCMD")}
  <p class="texto">Prazo pela proposta do DCMD: <b>{esc(regua)}</b> dias. O índice é
  <b>dias gastos ÷ prazo concedido</b> — abaixo de 1,00 sobrou prazo, acima estourou.</p>
  <div class="numeros">
    {numero("Entregas ao campo", br(t["entregas"]), "2025 e 2026")}
    {numero("Cumprimento", pct(t["cumprimento"], 1), f'{t["no_prazo"]} de {t["entregas"]}', "bom")}
    {numero("Índice do parque", br(t["indice"], 2), "gasta 81% do prazo", "bom")}
    {numero("Mediana", f'{t["mediana"]} dias', "o serviço normal é rápido")}
  </div>
  <div class="rolagem"><table class="tabela">
    <thead><tr><th>Equipe</th><th class="num-col">Entregas</th><th class="num-col">No prazo</th>
      <th class="num-col">Cumpre</th><th class="num-col">Mediana</th>
      <th class="num-col">Índice</th><th class="num-col">Pior atraso</th></tr></thead>
    <tbody>{linhas}</tbody></table></div>
  <p class="texto destaque">A mediana de <b>{t["mediana"]} dias</b> contra prazos de 11 a 60
  diz que o campo não é o gargalo. O que derruba o número é a cauda: equipes com mediana de
  1 dia carregam atrasos de mais de 200. É acompanhamento, não capacidade.</p>
  <p class="rodape-nota">A aba «SLA por equipe» da planilha base está na régua anterior
  (8·15·30·50 e 26 sem classificação). Os números acima usam a proposta que o gestor
  fechou depois.</p>
</section>"""


CSS = """
:root {
  --papel:#f2efe6; --campo:#e9e5d8; --fundo:#fbfaf6;
  --tinta:#211d15; --tinta-2:#57513f; --tinta-3:#8d8672; --filete:#c8c2af;
  --sinal:#bc4b0e; --carimbo:#a33327; --ocre:#996c15; --oliva:#75681a;
  --campo-verde:#3e6b4c; --grafite:#6d675a;
  --titulo:"Barlow Condensed", "Arial Narrow", sans-serif;
  --leitura:Spectral, Georgia, "Times New Roman", serif;
  --dado:"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --papel:#191713; --campo:#221f1a; --fundo:#1c1a16;
    --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563; --filete:#403a2e;
    --sinal:#e0703a; --carimbo:#d2695c; --ocre:#c69a3f; --oliva:#a39a45;
    --campo-verde:#6ba37c; --grafite:#9a9384;
  }
}
:root[data-theme="dark"] {
  --papel:#191713; --campo:#221f1a; --fundo:#1c1a16;
  --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563; --filete:#403a2e;
  --sinal:#e0703a; --carimbo:#d2695c; --ocre:#c69a3f; --oliva:#a39a45;
  --campo-verde:#6ba37c; --grafite:#9a9384;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--papel); color:var(--tinta);
  font-family:var(--leitura); font-size:16px; line-height:1.62; }
.folha { max-width:1000px; margin:0 auto; padding:34px 22px 72px; }

.capa { border-bottom:3px double var(--tinta); padding-bottom:16px; }
.capa .selo { font-family:var(--titulo); font-size:12px; letter-spacing:.22em;
  text-transform:uppercase; color:var(--sinal); font-weight:700; }
.capa h1 { margin:6px 0 0; font-family:var(--titulo); font-weight:700; font-size:44px;
  line-height:1.02; letter-spacing:.02em; text-transform:uppercase;
  text-wrap:balance; }
.capa p { margin:10px 0 0; color:var(--tinta-2); font-size:16px; max-width:62ch; }
.capa .carimbo { margin-top:14px; display:flex; flex-wrap:wrap; gap:8px 10px; }
.capa .carimbo span { font-family:var(--dado); font-size:11.5px; letter-spacing:.04em;
  border:1px solid var(--filete); padding:3px 9px; color:var(--tinta-2);
  background:var(--campo); }

.bloco { margin-top:44px; }
.marcador { display:flex; flex-wrap:wrap; gap:4px 16px; align-items:baseline;
  border-bottom:1px solid var(--tinta); padding-bottom:7px; margin-bottom:18px; }
.marcador h2 { margin:0; font-family:var(--titulo); font-weight:700; font-size:26px;
  letter-spacing:.05em; text-transform:uppercase; }
.marcador span { font-family:var(--dado); font-size:11.5px; color:var(--tinta-3);
  letter-spacing:.03em; }
h3 { font-family:var(--titulo); font-weight:600; font-size:14px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--tinta-2); margin:26px 0 10px; }
h4 { font-family:var(--titulo); font-weight:700; font-size:15px; letter-spacing:.1em;
  text-transform:uppercase; margin:0 0 2px; }
.texto { margin:0 0 14px; font-size:15.5px; color:var(--tinta-2); max-width:70ch; }
.texto b { color:var(--tinta); }
.texto.destaque { border-left:3px solid var(--sinal); padding-left:14px;
  font-style:italic; }
.sub { margin:0 0 8px; font-family:var(--dado); font-size:11.5px; color:var(--tinta-3); }
.rodape-nota { margin:12px 0 0; font-size:13.5px; color:var(--tinta-3);
  font-style:italic; max-width:70ch; }
.rodape-nota b { font-style:normal; }

.numeros { display:flex; flex-wrap:wrap; gap:14px; margin:4px 0 18px; }
.num { flex:1 1 170px; border:1px solid var(--filete); border-top:3px solid var(--tinta-3);
  background:var(--fundo); padding:12px 14px 13px; }
.num b { display:block; font-family:var(--dado); font-weight:600; font-size:27px;
  line-height:1.1; font-variant-numeric:tabular-nums; }
.num span { display:block; margin-top:4px; font-family:var(--titulo); font-size:12.5px;
  letter-spacing:.13em; text-transform:uppercase; color:var(--tinta-2); }
.num i { display:block; margin-top:3px; font-size:12.5px; color:var(--tinta-3);
  font-style:italic; }
.num.sinal { border-top-color:var(--sinal); } .num.sinal b { color:var(--sinal); }
.num.bom { border-top-color:var(--campo-verde); } .num.bom b { color:var(--campo-verde); }
.num.atento { border-top-color:var(--ocre); } .num.atento b { color:var(--ocre); }

.duas { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:8px 34px; }
.barras { display:flex; flex-direction:column; gap:7px; margin:0 0 16px; }
.barra { display:grid; grid-template-columns:minmax(90px,auto) 1fr auto; gap:10px;
  align-items:center; }
.barra-rot { font-size:13.5px; color:var(--tinta-2); }
.barra-trilho { height:11px; background:var(--campo); border:1px solid var(--filete);
  position:relative; }
.barra-trilho i { display:block; height:100%; background:var(--tinta-3); }
.barra-val { font-family:var(--dado); font-size:13px; font-weight:600;
  font-variant-numeric:tabular-nums; }
.barras.cor .barra:nth-child(1) .barra-trilho i { background:var(--carimbo); }
.barras.cor .barra:nth-child(2) .barra-trilho i { background:var(--ocre); }
.barras.cor .barra:nth-child(3) .barra-trilho i { background:var(--oliva); }
.barras.cor .barra:nth-child(4) .barra-trilho i { background:var(--campo-verde); }
.barras.cor .barra:nth-child(5) .barra-trilho i { background:var(--grafite); }
.barra.sem .barra-trilho i { background:var(--grafite); }

.legenda-trilho { list-style:none; margin:0 0 20px; padding:0; display:grid;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:6px 16px; }
.legenda-trilho li { display:flex; align-items:center; gap:8px;
  border-bottom:1px dotted var(--filete); padding-bottom:4px; }
.legenda-trilho span { font-family:var(--titulo); font-size:12px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--tinta-2); flex:1; }
.legenda-trilho b { font-family:var(--dado); font-size:12.5px; font-weight:600;
  color:var(--tinta-3); }
.legenda-trilho b em { font-style:normal; opacity:.6; }

.casa { width:11px; height:11px; flex:none; border:1px solid var(--tinta-3);
  background:var(--papel); display:inline-block; }
.casa.cheia { background:var(--sinal); border-color:var(--sinal); }

.filtros { display:flex; flex-wrap:wrap; gap:7px; margin:16px 0 12px; }
.chip { font-family:var(--titulo); font-size:12.5px; letter-spacing:.1em;
  text-transform:uppercase; padding:5px 11px; border:1px solid var(--filete);
  background:var(--fundo); color:var(--tinta-2); cursor:pointer; }
.chip em { font-style:normal; font-family:var(--dado); font-size:11px; opacity:.7;
  margin-left:4px; }
.chip:hover { border-color:var(--tinta-3); }
.chip.ativo { background:var(--tinta); color:var(--papel); border-color:var(--tinta); }
.chip:focus-visible { outline:2px solid var(--sinal); outline-offset:2px; }

.rolagem { overflow-x:auto; border:1px solid var(--filete); background:var(--fundo); }
.tabela { width:100%; border-collapse:collapse; font-size:13.5px; }
.tabela th { font-family:var(--titulo); font-size:11.5px; letter-spacing:.11em;
  text-transform:uppercase; text-align:left; padding:9px 11px; color:var(--papel);
  background:var(--tinta); font-weight:600; white-space:nowrap; }
.tabela td { padding:7px 11px; border-bottom:1px solid var(--filete);
  vertical-align:middle; }
.tabela tbody tr:last-child td { border-bottom:0; }
.tabela tbody tr:hover { background:var(--campo); }
.cod { font-family:var(--dado); font-size:12.5px; white-space:nowrap; }
.praca { color:var(--tinta-2); }
.defeito { color:var(--tinta-2); font-size:13px; }
.estado { font-family:var(--titulo); font-size:13px; letter-spacing:.06em;
  text-transform:uppercase; }
.num-col { text-align:right; font-family:var(--dado); font-variant-numeric:tabular-nums;
  white-space:nowrap; }
.trilho span { display:inline-flex; gap:2px; align-items:center; }
.atrasado { color:var(--carimbo); font-weight:600; }
.atencao { color:var(--ocre); font-weight:600; }

.etiqueta { font-family:var(--dado); font-size:11px; font-weight:600; padding:1px 6px;
  border:1px solid var(--filete); }
.pastilha { font-family:var(--titulo); font-size:11.5px; letter-spacing:.07em;
  text-transform:uppercase; padding:2px 8px; border:1px solid currentColor;
  white-space:nowrap; }
.pastilha.muito-alta { color:var(--carimbo); } .pastilha.alta { color:var(--ocre); }
.pastilha.media { color:var(--oliva); } .pastilha.baixa { color:var(--campo-verde); }
.pastilha.sem { color:var(--grafite); }

.figuras { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
  gap:22px 30px; margin-bottom:10px; }
.figura h3 { margin-top:0; }
.fig { width:100%; height:auto; display:block; overflow:visible; }
.grade { stroke:var(--filete); stroke-width:1; opacity:.6; }
.rot-y, .rot-x { font-family:var(--dado); font-size:10.5px; fill:var(--tinta-3); }
.rot-y { text-anchor:end; }
.rot-x { text-anchor:middle; text-transform:uppercase; letter-spacing:.05em; }

.fatias { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:18px 26px; margin:18px 0; }
.fatia { border-top:2px solid var(--tinta); padding-top:8px; }
.linha-causa { display:flex; justify-content:space-between; gap:10px; align-items:baseline;
  border-bottom:1px dotted var(--filete); padding:3px 0; font-size:13px;
  color:var(--tinta-2); }
.linha-causa b { font-family:var(--dado); font-size:12.5px; color:var(--tinta); }

.citacoes { list-style:none; margin:0; padding:0; display:grid;
  grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px 24px; }
.citacoes li { border-left:2px solid var(--filete); padding-left:14px; }
.citacoes q { display:block; margin:6px 0 4px; font-size:14px; color:var(--tinta-2);
  font-style:italic; }
.citacoes i { font-family:var(--dado); font-size:11px; color:var(--tinta-3);
  font-style:normal; }
.quadro-ano td.rot { font-size:14px; padding-left:22px; }
.quadro-ano tr.faixa td { font-family:var(--titulo); font-size:12.5px;
  letter-spacing:.13em; text-transform:uppercase; color:var(--tinta-2);
  background:var(--campo); padding:7px 11px; border-top:2px solid var(--tinta); }
.quadro-ano tr.total td { font-weight:600; border-bottom:2px solid var(--filete); }
.quadro-ano tr.geral td { color:var(--tinta-2); }
.quadro-ano tr.sub td.rot { padding-left:34px; color:var(--tinta-2); }
.quadro-ano tr.faixa.recorte td { border-left:3px solid var(--sinal);
  color:var(--sinal); }
.quadro-ano tr.bom td.forte { color:var(--campo-verde); }
.quadro-ano td.passivo { background:rgba(188,75,14,.06); }
.quadro-ano th.passivo { background:linear-gradient(rgba(224,112,58,.26),rgba(224,112,58,.26)), var(--tinta); }
.quadro-ano th em { font-family:var(--dado); font-size:9.5px; font-weight:400;
  letter-spacing:0; text-transform:none; opacity:.75; }
.quadro td.rot { font-size:14px; }
.quadro tr.topo td { border-top:2px solid var(--tinta); padding-top:10px; }
.quadro tr.grupo td.rot, .quadro tr.fraca td.rot { color:var(--tinta-2); }
.quadro tr.fraca td { font-size:12.5px; color:var(--tinta-3); }
.quadro tr.bom td.forte { color:var(--campo-verde); }
.quadro tr.total td { border-top:3px double var(--tinta); font-weight:600;
  font-family:var(--titulo); letter-spacing:.06em; text-transform:uppercase; }
.quadro tr.total td.num-col { font-family:var(--dado); font-size:15px;
  text-transform:none; letter-spacing:0; }
.quadro td.forte { font-weight:600; color:var(--tinta); }
.no-campo { list-style:none; margin:0 0 6px; padding:0; display:grid;
  grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px 18px; }
.no-campo li { border:1px solid var(--filete); border-left:3px solid var(--ocre);
  background:var(--fundo); padding:10px 13px; display:flex; flex-direction:column;
  gap:2px; }
.no-campo b { font-size:13.5px; }
.no-campo span { font-family:var(--titulo); font-size:13.5px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--tinta-2); }
.no-campo i { font-family:var(--dado); font-size:11.5px; color:var(--tinta-3);
  font-style:normal; }
.causa-tag { font-family:var(--titulo); font-size:11.5px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--sinal); margin-left:6px; }

.fim { margin-top:48px; border-top:3px double var(--tinta); padding-top:14px;
  font-size:13.5px; color:var(--tinta-3); }
.fim b { color:var(--tinta-2); }
@media (prefers-reduced-motion:reduce) { * { transition:none !important; } }
@media (max-width:640px) {
  .capa h1 { font-size:32px; }
  .marcador h2 { font-size:21px; }
}
"""

JS = """
(function () {
  var chips = document.querySelectorAll('.chip');
  var linhas = document.querySelectorAll('#tab-esteira tbody tr');
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      chips.forEach(function (o) { o.classList.remove('ativo'); });
      c.classList.add('ativo');
      var f = c.dataset.filtro;
      linhas.forEach(function (tr) {
        var mostra = f === 'todos'
          || (f.indexOf('status:') === 0 && tr.dataset.status === f.slice(7))
          || (f.indexOf('crit:') === 0 && tr.dataset.crit === f.slice(5));
        tr.style.display = mostra ? '' : 'none';
      });
    });
  });
})();
"""


def montar():
    with open(BASE, encoding="utf-8") as fh:
        b = json.load(fh)
    with open(SLA, encoding="utf-8") as fh:
        s = json.load(fh)
    with open(PARTICAO, encoding="utf-8") as fh:
        pc = json.load(fh)
    g = b["gestao"]
    html = f"""<title>Prontuário do COEP</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@400;600&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap">
<style>{CSS}</style>
<div class="folha">
  <header class="capa">
    <div class="selo">Energisa Tocantins · posto ETO-COEP</div>
    <h1>Prontuário do COEP</h1>
    <p>Religadores e reguladores de tensão: o que o posto deve, o que o parque
    quebrou e por quê, e quanto tempo o campo leva para devolver. Tudo sai da
    planilha base de equipamentos especiais.</p>
    <div class="carimbo">
      <span>{g['qtd']} pendentes no DCMD</span>
      <span>{moeda(g['orcamento_total'])} parados</span>
      <span>{b['falhas']['qtd']} falhas lidas</span>
      <span>{pc["contas"]["conta_do_posto"]} na conta do posto</span>
      <span>posição 18/08/2026</span>
    </div>
  </header>
  {bloco_esteira(g)}
  {bloco_orcamento(g)}
  {bloco_taxa(b['mensal'], b['falhas'])}
  {bloco_causas(b['falhas'])}
  {bloco_dinamica(b['resolvidos'], pc)}
  {bloco_quadro(pc)}
  {bloco_sla(s)}
  <footer class="fim">
    <p><b>De onde vem.</b> A planilha base de equipamentos especiais do COEP —
    esteira, orçamento, taxa de falha, causa raiz e dinâmica saem dela, aba por aba.
    O SLA é recalculado da base de repasse na proposta do DCMD, porque a aba da
    planilha ainda está na régua anterior.</p>
    <p><b>O que é falha.</b> Só peça grande: no religador controle, tanque ou
    equipamento completo; no regulador célula, relé, banco completo ou furto. Trafo
    auxiliar, rádio, antena, bateria e aterramento ficam fora da taxa.</p>
  </footer>
</div>
<script>{JS}</script>
"""
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as fh:
        fh.write(html)
    return html


if __name__ == "__main__":
    h = montar()
    print(f"gravado: {SAIDA} — {len(h) / 1024:.0f} KB")
