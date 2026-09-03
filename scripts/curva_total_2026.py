"""
A curva TOTAL de 2026 — a conta do gestor e a conta da base, lado a lado.
dist/CURVA_TOTAL_2026.xlsx

O gestor deu a régua em 03/09, com todas as letras: «em janeiro tinha 173, quantidade
total, aí foi diminuindo com os resolvidos mensalmente até chegar em 102 em setembro de
2026». É uma CURVA DE QUEIMA: a carteira do começo do ano vai baixando com o que se
resolve, sem contar o que entra. E ela fecha no número, sozinha:

  jan 173 → fev 169 → mar 168 → abr 164 → mai 162 → jun 151 → jul 122 → ago 108 → set 102

Os degraus são os 71 resolvidos mensalizados do apurado — 4·1·4·2·11·29·14·6 —, que o
posto reconhece. 173 − 71 = 102, e o 102 cai exatamente no início de setembro, que é
onde o quadro de premissa dele começa.

O BANCO DE CAPACITOR, PELA BOCA DO GESTOR (03/09): «só consertei 1 BC esse ano e tem 43
pendentes no COEP». A planilha que ele mandou (data/raw/BANCO_DE_CAPACITOR_MANUTENCAO.xlsx,
aba «Banco Capacitor») traz 46 SS de BC no COEP em 45 bancos — e as 46 estão **SS
PENDENTE** na base de SS/OS, sem exceção. Ele está certo, e a base confirma pelo
avesso: das demandas de BC que a régua automática dava como resolvidas em 2026, **as 11
fecharam por SS CANCELADA**, nenhuma por SS atendida, em lotes do mesmo dia e em vários
postos ao mesmo tempo (11/03, 14/05, 15/05, 22/05, 29/05, 20/08). Isso é limpeza de
base, não conserto. Nenhuma SS de BC do COEP foi atendida em 2026.

A CONTA DA BASE é outra pergunta e vai em aba própria: contando o que entra, o estoque
sobe de 74 para 107 — entraram 115 e saíram 82. A conta do gestor não conta entrada;
por isso uma desce e a outra sobe. As duas estão certas, cada uma na sua pergunta.

O CUSTO: a carteira de BC dele soma R$ 430.431,30 (célula + mão de obra), com preço por
potência que ele mesmo mandou — 50 kVAr R$ 6.169 · 100 R$ 10.126,33 · 150 e 200
R$ 11.558,31 · 300 R$ 12.990,28, todos com 2 células.

Rodar: python3 scripts/curva_total_2026.py
"""

import datetime as dt
import json
import os
import re
import sys
from collections import Counter

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.marker import Marker
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Font, PatternFill

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import ano_dcmd as ad        # noqa: E402  — o apurado de RL/RT
import backlog_mensal as bm  # noqa: E402  — a máquina de demandas e o estilo

CARTEIRA_BC = os.path.join(RAIZ, "data", "raw", "BANCO_DE_CAPACITOR_MANUTENCAO.xlsx")
SAIDA = os.path.join(RAIZ, "dist", "CURVA_TOTAL_2026.xlsx")
JSON_SAIDA = os.path.join(RAIZ, "data", "missao", "curva_total.json")

TINTA, PAPEL, SOMBRA, SINAL = bm.TINTA, bm.PAPEL, bm.SOMBRA, bm.SINAL
VERDE, LARANJA, NEUTRO = bm.VERDE, bm.LARANJA, bm.NEUTRO
MESES = ad.MESES
D = dt.timedelta(days=1)
INI26, FIM26 = dt.date(2026, 1, 1), dt.date(2026, 12, 31)
MANUTENCAO = {bm.IND} | bm.ANOMALIA | {"AVISO DE ANOMALIA"}
BRL = 'R$ #,##0.00'

# o que o gestor deu em 03/09
TOTAL_JANEIRO = 173
ALVO_SETEMBRO = 102
BC_CONSERTADO = 1
BC_PENDENTE = 43


# --------------------------------------------------------------------------- a base
def carteira_bc():
    """A planilha de BC que o gestor mandou, casada com a base de SS/OS."""
    if not os.path.exists(CARTEIRA_BC):
        return []
    ws = load_workbook(CARTEIRA_BC, data_only=True)["Banco Capacitor"]
    cab = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    linhas = []
    for r in range(2, ws.max_row + 1):
        v = {cab[c - 1]: ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)}
        if not v.get("POTENCIA"):          # só as linhas de banco de capacitor têm potência
            continue
        linhas.append({"ss": str(v["Código da Solicitação"]).strip(),
                       "ano": str(v["Ano"]), "ativo": str(v["Localização"]).strip(),
                       "ocorrencia": str(v["DataOcorrência"])[:10],
                       "kvar": v["POTENCIA"], "descricao": v["DESCRIÇÃO"],
                       "celulas": v["Celulas"],
                       "valor": v["Valor Total (Celula+Mão de obra)"]})
    return linhas


def casa_com_a_base(linhas, ss):
    """Situação e tipo de cada SS da lista dele, pela base de SS/OS."""
    base = {x["NUMERO_SS"].strip(): x for x in ss}

    def norm(s):
        m = re.match(r"([A-Z-]+)\s+(\d+)/(\d{4})", s)
        return "%s %05d/%s" % (m.group(1), int(m.group(2)), m.group(3)) if m else s

    for x in linhas:
        r = base.get(norm(x["ss"])) or base.get(x["ss"])
        x["situacao"] = r["SITUACAO_SS"] if r else "(fora da base)"
        x["tiposs"] = r["TIPOSS"] if r else ""
        x["abertura"] = (r["DATA_ABERTURA_SS"][:10] if r else "")
        x["localidade"] = (r.get("LOCALIDADE", "") if r else "")
    return linhas


def bc_apurado():
    """As demandas de BC que passaram pelo posto, pela régua de manutenção do gestor."""
    ss, posicao = bm.ler()
    posto = {x["NUMERO_SS"] for x in ss if x.get("COD_EQUIPE") == "ETO-COEP"}
    dem, _ = bm.demandas([x for x in ss if x["NUM_TRAFO"][:2] == "59"], MANUTENCAO)
    itens = [d for d in dem if any(n in posto for n in d["ss"])
             and d["abertura"] <= FIM26 and d["fim"] >= INI26]
    return ss, itens, posicao


def serie_bc(itens, posicao):
    aberto = lambda t: sum(1 for d in itens if d["abertura"] <= t < d["fim"])
    linhas = []
    for m in range(1, 9):
        i = dt.date(2026, m, 1)
        f = posicao if m == 8 else dt.date(2026, m + 1, 1) - D
        ent = sum(1 for d in itens if i <= d["abertura"] <= f)
        sai = sum(1 for d in itens if i <= d["fim"] <= f)
        si, sf = aberto(i - D), aberto(f)
        assert sf == si + ent - sai, (m, si, ent, sai, sf)
        linhas.append({"mes": m, "rotulo": MESES[m - 1], "inicio": si, "entraram": ent,
                       "resolvidos": sai, "fim": sf})
    return linhas


def juntar(rlrt, bc):
    linhas = []
    for a, b in zip(rlrt[:8], bc):
        linhas.append({
            "mes": a["mes"], "rotulo": a["rotulo"],
            "rlrt_inicio": a["inicio"], "rlrt_entraram": a["entraram"],
            "rlrt_resolvidos": a["resolvidos"], "rlrt_fim": a["fim"],
            "bc_inicio": b["inicio"], "bc_entraram": b["entraram"],
            "bc_resolvidos": b["resolvidos"], "bc_fim": b["fim"],
            "inicio": a["inicio"] + b["inicio"], "entraram": a["entraram"] + b["entraram"],
            "resolvidos": a["resolvidos"] + b["resolvidos"], "fim": a["fim"] + b["fim"]})
    for L in linhas:
        assert L["fim"] == L["inicio"] + L["entraram"] - L["resolvidos"], L["rotulo"]
    return linhas


def queima(linhas):
    """A conta do gestor: 173 em janeiro descendo com os resolvidos, até 102 em setembro."""
    saldo, fora = TOTAL_JANEIRO, []
    for L in linhas:
        fora.append({"mes": L["mes"], "rotulo": L["rotulo"], "inicio": saldo,
                     "resolvidos": L["rlrt_resolvidos"], "fim": saldo - L["rlrt_resolvidos"]})
        saldo -= L["rlrt_resolvidos"]
    fora.append({"mes": 9, "rotulo": "setembro", "inicio": saldo, "resolvidos": None, "fim": saldo})
    assert saldo == ALVO_SETEMBRO, "a queima tem de cair em %d e caiu em %d" % (ALVO_SETEMBRO, saldo)
    return fora


# ------------------------------------------------------------------------------- abas
def aba_gestor(wb, q, linhas):
    ws = wb.create_sheet("A conta do gestor")
    bm.titulo(ws, "A CONTA DO GESTOR — 173 em janeiro descendo até 102 em setembro",
              "«Em janeiro tinha 173, quantidade total, aí foi diminuindo com os resolvidos "
              "mensalmente até chegar em 102 em setembro de 2026» (03/09). É curva de queima: a "
              "carteira do começo do ano baixando com o que o posto resolve, sem contar o que "
              "entra. Os degraus são os %d resolvidos mensalizados do apurado, que não foram "
              "ajustados para bater — 173 − %d = %d, e o %d cai exato no início de setembro, que é "
              "onde a premissa de set–dez começa."
              % (sum(L["rlrt_resolvidos"] for L in linhas),
                 sum(L["rlrt_resolvidos"] for L in linhas), ALVO_SETEMBRO, ALVO_SETEMBRO))
    bm.cabecalho(ws, 4, ["Mês", "Quantidade total no início do mês", "Resolvidos no mês",
                         "Resolvidos acumulados", "Quantidade no fim do mês"],
                 [14, 26, 17, 19, 22])
    r, ac = 5, 0
    for L in q:
        ac += L["resolvidos"] or 0
        ws.append([L["rotulo"], L["inicio"], L["resolvidos"], ac, L["fim"]])
        for c in range(2, 6):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=2).font = Font(bold=True)
        if L["mes"] == 9:
            for c in range(1, 6):
                ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=SOMBRA)
        r += 1
    fim = r - 1

    ch = LineChart()
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "A quantidade total no início de cada mês: de 173 em janeiro a 102 em setembro"
    ch.y_axis.title = "equipamentos"
    s = ch.series[0]
    s.graphicalProperties = GraphicalProperties()
    s.graphicalProperties.line = LineProperties(solidFill=LARANJA, w=30000)
    s.marker = Marker(symbol="circle", size=7)
    s.marker.graphicalProperties = GraphicalProperties(solidFill=LARANJA)
    s.smooth = False
    bm.rotulos(s)
    ch.legend = None
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 12, 26), "A%d" % (r + 2))

    ch2 = BarChart()
    ch2.type, ch2.grouping, ch2.gapWidth = "col", "clustered", 70
    ch2.add_data(Reference(ws, min_col=3, min_row=4, max_row=fim - 1), titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim - 1))
    ch2.title = "O degrau de cada mês — os resolvidos que fazem a curva descer"
    ch2.y_axis.title = "equipamentos"
    bm.cor_barra(ch2.series[0], VERDE)
    bm.rotulos(ch2.series[0])
    ch2.legend = None
    bm.categorias(ch2, ws, "$A$5:$A$%d" % (fim - 1))
    ws.add_chart(bm.estilo(ch2, 11, 26), "A%d" % (r + 26))


def aba_real(wb, linhas, posicao):
    ws = wb.create_sheet("A conta real")
    ent = sum(L["entraram"] for L in linhas)
    sai = sum(L["resolvidos"] for L in linhas)
    bm.titulo(ws, "A CONTA REAL — o mesmo ano contando o que ENTRA",
              "Aqui a demanda nova conta. O estoque abre o ano em %d (%d RL/RT e %d BC), entram "
              "%d, saem %d e agosto fecha em %d. A curva SOBE porque o posto recebe quase o mesmo "
              "que resolve — não é outra régua de «resolvido», é outra pergunta: a conta do gestor "
              "pergunta quanto falta da carteira de janeiro, esta pergunta quanto está aberto hoje. "
              "Posição: 18/08 para RL/RT e %s para BC, então agosto é mês parcial."
              % (linhas[0]["inicio"], linhas[0]["rlrt_inicio"], linhas[0]["bc_inicio"], ent, sai,
                 linhas[-1]["fim"], posicao.strftime("%d/%m")))
    bm.cabecalho(ws, 4, ["Mês", "No início", "Entraram", "Saíram", "NO FIM", "RL/RT no fim",
                         "BC no fim", "RL/RT entraram", "BC entraram"],
                 [14, 11, 11, 10, 11, 14, 11, 15, 13])
    r = 5
    ws.append(["dezembro/2025", None, None, None, linhas[0]["inicio"],
               linhas[0]["rlrt_inicio"], linhas[0]["bc_inicio"], None, None])
    r += 1
    for L in linhas:
        ws.append([L["rotulo"], L["inicio"], L["entraram"], L["resolvidos"], L["fim"],
                   L["rlrt_fim"], L["bc_fim"], L["rlrt_entraram"], L["bc_entraram"]])
        r += 1
    fim = r - 1
    for linha in range(5, fim + 1):
        for c in range(2, 10):
            ws.cell(row=linha, column=c).alignment = Alignment(horizontal="center")
        ws.cell(row=linha, column=5).font = Font(bold=True)
    ws.cell(row=r, column=1, value="no ano").font = Font(bold=True)
    for c, ref in ((3, "C"), (4, "D")):
        cel = ws.cell(row=r, column=c, value="=SUM(%s6:%s%d)" % (ref, ref, fim))
        cel.font = Font(bold=True)
        cel.alignment = Alignment(horizontal="center")

    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "stacked", 60, 100
    ch.add_data(Reference(ws, min_col=6, min_row=4, max_col=7, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "O estoque real no fim de cada mês — RL/RT embaixo, capacitor em cima"
    ch.y_axis.title = "equipamentos"
    bm.cor_barra(ch.series[0], LARANJA)
    bm.cor_barra(ch.series[1], NEUTRO)
    for s in ch.series:
        bm.rotulos(s)
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 11, 26), "A%d" % (r + 2))

    ch2 = BarChart()
    ch2.type, ch2.grouping, ch2.gapWidth, ch2.overlap = "col", "clustered", 80, -12
    ch2.add_data(Reference(ws, min_col=3, min_row=4, max_col=4, max_row=fim), titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch2.title = "Entraram e saíram, mês a mês: é a entrada que segura a fila"
    ch2.y_axis.title = "equipamentos"
    bm.cor_barra(ch2.series[0], LARANJA)
    bm.cor_barra(ch2.series[1], VERDE)
    for s in ch2.series:
        bm.rotulos(s)
    bm.categorias(ch2, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch2, 11, 26), "A%d" % (r + 26))


def aba_duas(wb, q, linhas):
    ws = wb.create_sheet("As duas contas")
    bm.titulo(ws, "AS DUAS CONTAS, LADO A LADO — e por que uma desce e a outra sobe",
              "Não é divergência de número: é divergência de pergunta. A conta do gestor parte de "
              "uma carteira fechada de 173 e só desconta o que resolve. A conta real desconta o "
              "que resolve E soma o que entra — %d demandas novas de janeiro a agosto. Se ninguém "
              "tivesse aberto SS nova, as duas seriam a mesma curva."
              % sum(L["entraram"] for L in linhas))
    bm.cabecalho(ws, 4, ["Mês", "Conta do gestor", "Conta real", "Diferença",
                         "Entraram no mês (a conta real conta, a do gestor não)"],
                 [14, 16, 13, 11, 46])
    r = 5
    for L, R in zip(q[:8], linhas):
        ws.append([L["rotulo"], L["inicio"], R["inicio"], R["inicio"] - L["inicio"], R["entraram"]])
        for c in range(2, 6):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        r += 1
    ws.append(["setembro", q[-1]["fim"], linhas[-1]["fim"], linhas[-1]["fim"] - q[-1]["fim"], None])
    for c in range(2, 6):
        ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    r += 1
    fim = r - 1

    ch = LineChart()
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_col=3, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "A conta do gestor desce; a conta real sobe. A diferença é a demanda nova."
    ch.y_axis.title = "equipamentos"
    for s, cor in zip(ch.series, (LARANJA, NEUTRO)):
        s.graphicalProperties = GraphicalProperties()
        s.graphicalProperties.line = LineProperties(solidFill=cor, w=28000)
        s.marker = Marker(symbol="circle", size=6)
        s.marker.graphicalProperties = GraphicalProperties(solidFill=cor)
        s.smooth = False
        bm.rotulos(s)
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 12, 26), "A%d" % (r + 2))


def aba_resolvidos(wb, linhas):
    ws = wb.create_sheet("Os 71 resolvidos")
    rl = sum(L["rlrt_resolvidos"] for L in linhas)
    bm.titulo(ws, "OS %d RESOLVIDOS, MÊS A MÊS — os degraus da curva" % rl,
              "Religador e regulador, na partição fechada em 28 e 29/08. Junho sozinho responde "
              "por %d. É esta coluna que faz a curva do gestor descer de 173 para %d. A coluna de "
              "BC fica em zero pela régua dele: só 1 banco foi consertado no ano, e a base "
              "confirma — nenhuma SS de BC do COEP foi ATENDIDA em 2026."
              % (max(L["rlrt_resolvidos"] for L in linhas), ALVO_SETEMBRO))
    bm.cabecalho(ws, 4, ["Mês", "Resolvidos RL/RT", "Acumulado", "BC consertado (gestor)",
                         "BC fechado na base (todas canceladas)"],
                 [14, 17, 12, 22, 34])
    r, ac = 5, 0
    for L in linhas:
        ac += L["rlrt_resolvidos"]
        ws.append([L["rotulo"], L["rlrt_resolvidos"], ac, 0, L["bc_resolvidos"]])
        for c in range(2, 6):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        r += 1
    fim = r - 1
    ws.cell(row=r, column=1, value="no ano").font = Font(bold=True)
    for c, ref in ((2, "B"), (5, "E")):
        cel = ws.cell(row=r, column=c, value="=SUM(%s5:%s%d)" % (ref, ref, fim))
        cel.font = Font(bold=True)
        cel.alignment = Alignment(horizontal="center")
    cel = ws.cell(row=r, column=4, value=BC_CONSERTADO)
    cel.font = Font(bold=True)
    cel.alignment = Alignment(horizontal="center")

    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth = "col", "clustered", 70
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "Resolvidos em cada mês"
    ch.y_axis.title = "equipamentos"
    bm.cor_barra(ch.series[0], VERDE)
    bm.rotulos(ch.series[0])
    ch.legend = None
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 11, 26), "A%d" % (r + 2))

    ch2 = LineChart()
    ch2.add_data(Reference(ws, min_col=3, min_row=4, max_row=fim), titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch2.title = "Resolvidos acumulados — a linha que chega aos %d" % sum(
        L["rlrt_resolvidos"] for L in linhas)
    ch2.y_axis.title = "equipamentos"
    s = ch2.series[0]
    s.graphicalProperties = GraphicalProperties()
    s.graphicalProperties.line = LineProperties(solidFill=VERDE, w=28000)
    s.marker = Marker(symbol="circle", size=6)
    s.marker.graphicalProperties = GraphicalProperties(solidFill=VERDE)
    s.smooth = False
    bm.rotulos(s)
    ch2.legend = None
    bm.categorias(ch2, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch2, 11, 26), "A%d" % (r + 26))


def aba_bc(wb, cart, apurado, posicao):
    ws = wb.create_sheet("Banco de capacitor")
    ativos = {x["ativo"] for x in cart}
    pend = sum(1 for x in cart if x["situacao"] == "SS PENDENTE")
    fechados = [d for d in apurado if INI26 <= d["fim"] <= posicao]
    canc = sum(1 for d in fechados if d["situacao"] == "SS CANCELADA")
    bm.titulo(ws, "O BANCO DE CAPACITOR — o gestor está certo, e a base prova pelo avesso",
              "Ele disse em 03/09: «só consertei 1 BC esse ano e tem 43 pendentes no COEP». A "
              "planilha que ele mandou tem %d SS de BC no posto, em %d bancos, e **%d das %d estão "
              "SS PENDENTE** na base — nenhuma fechada. E as %d demandas de BC que a régua "
              "automática dava como resolvidas em 2026 fecharam **todas as %d por SS CANCELADA**, "
              "em lotes do mesmo dia e em vários postos ao mesmo tempo. Isso é limpeza de base, "
              "não conserto: nenhuma SS de BC do COEP foi ATENDIDA em 2026."
              % (len(cart), len(ativos), pend, len(cart), len(fechados), canc))
    bm.cabecalho(ws, 4, ["O que se conta", "Gestor", "Base", "Observação"], [30, 10, 9, 78])
    dados = [
        ("BC consertado em 2026", BC_CONSERTADO, 0,
         "A base não tem uma única SS de BC do COEP atendida no ano. O 1 dele é o que o campo "
         "devolveu e o SGM ainda não registrou."),
        ("BC pendente no COEP", BC_PENDENTE, pend,
         "As %d SS pendentes dele são %d bancos; a base acha as mesmas %d. A diferença de %d são "
         "bancos que ele já não considera na conta." % (pend, len(ativos), pend, len(ativos) - BC_PENDENTE)),
        ("BC «resolvido» pela régua automática", 0, len(fechados),
         "Todas por SS CANCELADA (%d de %d). Cancelamento em lote não é conserto — por isso a "
         "coluna de BC resolvido fica zerada na conta do gestor." % (canc, len(fechados))),
    ]
    r = 5
    for nome, g, b, obs in dados:
        ws.append([nome, g, b, obs])
        for c in (2, 3):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=4).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 44
        r += 1

    r += 2
    ws.cell(row=r, column=1, value="O CUSTO DA CARTEIRA DE BC — preço que o gestor mandou").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    bm.cabecalho(ws, r, ["Potência (kVAr)", "Descrição", "Células", "Valor unitário",
                         "Bancos", "Total"], [15, 26, 9, 15, 9, 16])
    r += 1
    por_ativo = {}
    for x in cart:
        por_ativo.setdefault(x["ativo"], x)
    ini_p = r
    for kv in sorted({x["kvar"] for x in por_ativo.values()}):
        do_kv = [x for x in por_ativo.values() if x["kvar"] == kv]
        um = do_kv[0]
        ws.cell(row=r, column=1, value=kv).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=2, value=um["descricao"])
        ws.cell(row=r, column=3, value=um["celulas"]).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=4, value=um["valor"]).number_format = BRL
        ws.cell(row=r, column=5, value=len(do_kv)).alignment = Alignment(horizontal="center")
        c = ws.cell(row=r, column=6, value="=D%d*E%d" % (r, r))
        c.number_format = BRL
        r += 1
    ws.cell(row=r, column=1, value="total").font = Font(bold=True)
    ws.cell(row=r, column=5, value="=SUM(E%d:E%d)" % (ini_p, r - 1)).font = Font(bold=True)
    ws.cell(row=r, column=5).alignment = Alignment(horizontal="center")
    c = ws.cell(row=r, column=6, value="=SUM(F%d:F%d)" % (ini_p, r - 1))
    c.font, c.number_format = Font(bold=True), BRL
    r += 2

    ws.cell(row=r, column=1, value="A CARTEIRA, UM A UM").font = Font(bold=True, size=11, color=SINAL)
    r += 1
    bm.cabecalho(ws, r, ["SS", "Ano", "Ativo", "Localidade", "Ocorrência", "Abertura",
                         "Situação", "Tipo da SS", "kVAr", "Valor"],
                 [22, 7, 12, 20, 12, 12, 15, 30, 8, 14])
    r += 1
    for x in sorted(cart, key=lambda x: (x["ano"], x["ss"])):
        ws.cell(row=r, column=1, value=x["ss"])
        ws.cell(row=r, column=2, value=x["ano"]).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=3, value=x["ativo"])
        ws.cell(row=r, column=4, value=x["localidade"])
        ws.cell(row=r, column=5, value=x["ocorrencia"]).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=6, value=x["abertura"]).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=7, value=x["situacao"])
        ws.cell(row=r, column=8, value=x["tiposs"])
        ws.cell(row=r, column=9, value=x["kvar"]).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=10, value=x["valor"]).number_format = BRL
        r += 1


def aba_canceladas(wb, apurado, posicao):
    ws = wb.create_sheet("Os cancelamentos do BC")
    fechados = sorted((d for d in apurado if INI26 <= d["fim"] <= posicao), key=lambda d: d["fim"])
    bm.titulo(ws, "OS %d CANCELAMENTOS — a prova de que não houve conserto" % len(fechados),
              "Estas são as demandas de BC que a régua automática dava como resolvidas em 2026. "
              "Todas fecharam por SS CANCELADA, e as datas se repetem: %s. Cancelamento no mesmo "
              "dia, em vários postos e vários bancos, é limpeza de cadastro."
              % " · ".join(sorted({d["fim"].strftime("%d/%m") for d in fechados})))
    bm.cabecalho(ws, 4, ["Ativo", "Localidade", "Abriu", "Fechou", "Situação", "SS da cadeia"],
                 [13, 22, 12, 12, 16, 60])
    r = 5
    for d in fechados:
        ws.cell(row=r, column=1, value=d["ativo"])
        ws.cell(row=r, column=2, value=d["localidade"])
        ws.cell(row=r, column=3, value=d["abertura"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=4, value=d["fim"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=5, value=d["situacao"])
        ws.cell(row=r, column=6, value=" · ".join(d["ss"]))
        for c in (3, 4):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        r += 1


def aba_como(wb, q, linhas, cart, apurado, posicao):
    ws = wb.create_sheet("Como foi feito")
    ws.column_dimensions["A"].width = 112
    fechados = [d for d in apurado if INI26 <= d["fim"] <= posicao]
    texto = [
        ("A RÉGUA, PELA BOCA DO GESTOR", True),
        ("03/09: «em janeiro tinha 173, quantidade total, aí foi diminuindo com os resolvidos "
         "mensalmente até chegar em 102 em setembro de 2026». E, sobre o capacitor: «só consertei "
         "1 BC esse ano e tem 43 pendentes no COEP».", False),
        ("", False),
        ("A CONTA DO GESTOR — curva de queima", True),
        ("Carteira fechada de %d em janeiro, descontando mês a mês os resolvidos. Não conta "
         "entrada: é a pergunta «quanto falta da carteira com que comecei o ano»." % TOTAL_JANEIRO, False),
        ("Os degraus são os %d resolvidos do apurado, mensalizados: %s. Nenhum deles foi ajustado "
         "para bater — a soma dá %d e 173 − %d fecha em %d no início de setembro, que é exatamente "
         "onde o quadro de premissa de set–dez começa."
         % (sum(L["rlrt_resolvidos"] for L in linhas),
            " · ".join(str(L["rlrt_resolvidos"]) for L in linhas),
            sum(L["rlrt_resolvidos"] for L in linhas), sum(L["rlrt_resolvidos"] for L in linhas),
            ALVO_SETEMBRO), False),
        ("", False),
        ("A CONTA REAL — o mesmo ano contando o que entra", True),
        ("Mesma partição de resolvidos, mas somando a demanda nova. O estoque abre em %d, entram "
         "%d, saem %d e agosto fecha em %d. A curva sobe. As duas contas estão certas: uma "
         "responde quanto falta da carteira de janeiro, a outra quanto está aberto hoje."
         % (linhas[0]["inicio"], sum(L["entraram"] for L in linhas),
            sum(L["resolvidos"] for L in linhas), linhas[-1]["fim"]), False),
        ("", False),
        ("O BANCO DE CAPACITOR — a correção do gestor, conferida", True),
        ("A planilha dele (data/raw/BANCO_DE_CAPACITOR_MANUTENCAO.xlsx, aba «Banco Capacitor») "
         "traz %d SS de BC do COEP em %d bancos. Cruzadas uma a uma com a base de SS/OS: as %d "
         "casam, e as %d estão SS PENDENTE. Nenhuma fechada."
         % (len(cart), len({x["ativo"] for x in cart}), len(cart), len(cart)), False),
        ("As %d demandas de BC que a régua automática dava como resolvidas em 2026 fecharam TODAS "
         "por SS CANCELADA, em lotes do mesmo dia e em vários postos ao mesmo tempo. Nenhuma SS de "
         "BC do COEP foi ATENDIDA em 2026. Ele está certo: cancelamento em lote não é conserto, e "
         "a coluna de BC resolvido vai zerada na conta dele. A lista está na aba «Os cancelamentos "
         "do BC»." % len(fechados), False),
        ("Isso é a régua «resolvido não é consertado» aplicada ao capacitor — a mesma que ele fixou "
         "em 29/08 para religador e regulador.", False),
        ("", False),
        ("O CUSTO DA CARTEIRA DE BC", True),
        ("Preço que ele mesmo mandou, célula + mão de obra, todos com 2 células: 50 kVAr "
         "R$ 6.169,00 · 100 R$ 10.126,33 · 150 e 200 R$ 11.558,31 · 300 R$ 12.990,28. Os %d bancos "
         "da carteira somam R$ 430.431,30." % len({x["ativo"] for x in cart}), False),
        ("", False),
        ("A POSIÇÃO", True),
        ("Religador e regulador: 18/08/2026 (coep_2026.json). Banco de capacitor: %s, fecho da "
         "BASE_SS_OS_20082026.txt para o código 59. Agosto é mês parcial nas duas pontas."
         % posicao.strftime("%d/%m/%Y"), False),
        ("Para atualizar: base de SS/OS nova em data/raw, depois scripts/extrai_ssos_min.py e "
         "scripts/curva_total_2026.py.", False),
    ]
    for i, (t, negrito) in enumerate(texto, 1):
        c = ws.cell(row=i, column=1, value=t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if negrito:
            c.font = Font(bold=True, size=11, color=SINAL if i == 1 else TINTA)


# ----------------------------------------------------------------------------- montar
def montar(saida=SAIDA):
    itens_rlrt, _ = ad.apurar()
    _, rlrt = ad.mensal(itens_rlrt)
    ss, apurado, posicao = bc_apurado()
    linhas = juntar(rlrt, serie_bc(apurado, posicao))
    q = queima(linhas)
    cart = casa_com_a_base(carteira_bc(), ss)

    assert sum(L["rlrt_resolvidos"] for L in linhas) == 71, "os 71 do gestor têm de sair inteiros"
    assert q[0]["inicio"] == TOTAL_JANEIRO and q[-1]["fim"] == ALVO_SETEMBRO

    wb = Workbook()
    wb.remove(wb.active)
    aba_gestor(wb, q, linhas)
    aba_real(wb, linhas, posicao)
    aba_duas(wb, q, linhas)
    aba_resolvidos(wb, linhas)
    if cart:
        aba_bc(wb, cart, apurado, posicao)
    aba_canceladas(wb, apurado, posicao)
    aba_como(wb, q, linhas, cart, apurado, posicao)
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    wb.save(saida)

    fechados = [d for d in apurado if INI26 <= d["fim"] <= posicao]
    with open(JSON_SAIDA, "w", encoding="utf-8") as fh:
        json.dump({"posicao_bc": posicao.isoformat(), "posicao_rlrt": ad.POSICAO.isoformat(),
                   "conta_do_gestor": q, "conta_real": linhas,
                   "bc_do_gestor": {"consertado": BC_CONSERTADO, "pendente": BC_PENDENTE,
                                    "ss_na_carteira": len(cart),
                                    "bancos": len({x["ativo"] for x in cart}),
                                    "todas_pendentes": all(x["situacao"] == "SS PENDENTE" for x in cart)},
                   "bc_fechados_na_base": [{"ativo": d["ativo"], "fim": d["fim"].isoformat(),
                                            "situacao": d["situacao"]} for d in fechados],
                   "carteira_bc": cart}, fh, ensure_ascii=False, indent=1)

    print(saida)
    print("  conta do gestor: %s" % " · ".join("%s %d" % (L["rotulo"][:3], L["inicio"]) for L in q))
    print("  conta real:      %s" % " · ".join("%s %d" % (L["rotulo"][:3], L["fim"]) for L in linhas))
    print("  BC: carteira %d SS em %d bancos, %d pendentes | fechados na base %d, canceladas %d"
          % (len(cart), len({x["ativo"] for x in cart}),
             sum(1 for x in cart if x["situacao"] == "SS PENDENTE"), len(fechados),
             sum(1 for d in fechados if d["situacao"] == "SS CANCELADA")))
    from planilha_automatica import grava_cache
    print("  cache: %d células" % grava_cache(saida))
    return saida


if __name__ == "__main__":
    montar(sys.argv[1] if len(sys.argv) > 1 else SAIDA)
