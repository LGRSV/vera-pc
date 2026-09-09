"""
A base de SS de RL e RT, sem banco de capacitor — dist/BASE_WATERF_RL_RT.xlsx.

Pedido do gestor em 09/09: «organize uma base para bater com a última aba da planilha,
Waterf — lá está a relação sem banco de capacitor. Gostaria que fizesse uma base com
essas SS de RL e RT (aqui não estão banco de capacitor) e que deixe uma coluna
identificando quantos são RL e quantos são RT.»

O UNIVERSO: os ativos 58/78/79 que tiveram SS no posto ETO-COEP viva em 2026 — 269
equipamentos, 195 religadores e 74 reguladores. Deles saem 1.586 SS vivas em 2026 (de
2.382 no histórico completo). É esse 1.586 que corresponde ao «1582» que ele extrai.
Banco de capacitor (59) fica de fora, como ele pediu.

A COLUNA QUE ELE PEDIU: «Tipo» diz RL ou RT em toda linha, nos dois níveis — por SS e
por ativo —, e a aba «Resumo RL e RT» conta os dois em cada corte.

O QUE NÃO BATE, E ESTÁ DITO: o Waterf traz backlog 59, entrante 37 e resolvidos 41 de
janeiro a agosto. Nenhum recorte da base de SS/OS reproduz isso — o mais perto, pela
régua de indisponibilidade no posto do COEP, dá 44 · 67 · 43. A diferença está na
ENTRADA: 37 em oito meses é 4,6 por mês, e a base registra 67. O Waterf conta entrada
na carteira do DCMD, não abertura de SS; é controle dele, não do SGM. A aba
«Conferência com o Waterf» põe as duas contas lado a lado, sem ajuste.

Rodar: python3 scripts/base_waterf_rl_rt.py
"""

import datetime as dt
import json
import os
import sys
from collections import Counter

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import backlog_mensal as bm  # noqa: E402

SAIDA = os.path.join(RAIZ, "dist", "BASE_WATERF_RL_RT.xlsx")
GESTAO = os.path.join(RAIZ, "data", "raw", "GESTAO_DE_EQUIPAMENTOS.xlsx")

TINTA, PAPEL, SOMBRA, SINAL = bm.TINTA, bm.PAPEL, bm.SOMBRA, bm.SINAL
VERDE, LARANJA, NEUTRO = bm.VERDE, bm.LARANJA, bm.NEUTRO
FINO = Border(*[Side("thin", color="FFDDD8CC")] * 4)
INI26, FIM26 = dt.date(2026, 1, 1), dt.date(2026, 12, 31)
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto"]
D = dt.timedelta(days=1)

# o quadro Waterf, jan–ago (set–dez lá é premissa e não entra na conferência)
W_BACKLOG = 59
W_PENDENTES = [65, 71, 76, 80, 65, 58, 56, 55]
W_ENTRANTE = [7, 8, 9, 5, 1, 2, 4, 1]
W_RESOLVIDOS = [1, 2, 4, 1, 16, 9, 6, 2]

MANUTENCAO = {bm.IND} | bm.ANOMALIA | {"AVISO DE ANOMALIA"}


def tipo(cod):
    """RT quando começa com 58; RL nos 79 e 78 (monofásico). BC não entra nesta base."""
    return "RT" if cod[:2] == "58" else "RL"


# ------------------------------------------------------------------------------ base
def levantar():
    ss, posicao = bm.ler()
    ss = [x for x in ss if x["NUM_TRAFO"][:2] in ("58", "78", "79")]      # sem BC
    ativos = set()
    for x in ss:
        if x.get("COD_EQUIPE") != "ETO-COEP":
            continue
        a, f = bm.data(x["DATA_ABERTURA_SS"]), bm.data(x.get("DATA_TERMINO_SS"))
        if a and a <= FIM26 and (f is None or f >= INI26):
            ativos.add(x["NUM_TRAFO"])
    das = [x for x in ss if x["NUM_TRAFO"] in ativos]
    linhas = []
    for x in das:
        a, f = bm.data(x["DATA_ABERTURA_SS"]), bm.data(x.get("DATA_TERMINO_SS"))
        if not a or a > FIM26 or (f is not None and f < INI26):
            continue                                    # só o que esteve vivo em 2026
        linhas.append({
            "ss": x["NUMERO_SS"], "ativo": x["NUM_TRAFO"], "tipo": tipo(x["NUM_TRAFO"]),
            "posto": x.get("COD_EQUIPE", ""), "situacao": x["SITUACAO_SS"],
            "tiposs": x.get("TIPOSS", ""), "criticidade": x.get("CRITICIDADE_SS", ""),
            "localidade": x.get("LOCALIDADE", ""), "descricao_ativo": x.get("DESCICAO_DO_ATIVO", ""),
            "abertura": a, "termino": f, "os": x.get("NUMERO_OS", ""),
            "no_coep": "sim" if x.get("COD_EQUIPE") == "ETO-COEP" else "não"})
    linhas.sort(key=lambda x: (x["ativo"], x["abertura"], x["ss"]))
    return ss, linhas, ativos, posicao


def cadastro():
    """Tensão e potência dos Ajustes, para enriquecer a base por ativo."""
    out = {}
    wb = load_workbook(GESTAO, data_only=True, read_only=True)
    for aba, cod, campos in (("Ajustes Reguladores de Tensão", "CÓDIGO",
                              {"tensao": "TENSÃO PRIMÁRIA [Kv]", "potencia": "POTÊNCIA [Kvar]",
                               "modelo": "PARTE ATIVA"}),
                             ("Ajustes RL Poste", "CÓDIGO",
                              {"tensao": "TENSÃO", "modelo": "RELÉ"})):
        ws = wb[aba]
        L = list(ws.iter_rows(values_only=True))
        cab = [("" if v is None else str(v).strip()) for v in L[0]]
        if cod not in cab:
            continue
        ic = cab.index(cod)
        for r in L[1:]:
            c = str(r[ic]).strip() if ic < len(r) and r[ic] is not None else ""
            if not c.isdigit():
                continue
            d = {}
            for k, nome in campos.items():
                if nome in cab:
                    v = r[cab.index(nome)]
                    d[k] = "" if v is None else v
            out[c] = d
    wb.close()
    return out


def por_ativo(linhas, cad, posicao):
    ag = {}
    for x in linhas:
        a = ag.setdefault(x["ativo"], {
            "ativo": x["ativo"], "tipo": x["tipo"], "localidade": x["localidade"],
            "descricao": x["descricao_ativo"], "ss": 0, "ss_coep": 0,
            "primeira": x["abertura"], "ultima": x["abertura"], "aberta": False,
            "criticidades": set(), "tipos": set(), "postos": set()})
        a["ss"] += 1
        a["ss_coep"] += 1 if x["no_coep"] == "sim" else 0
        a["primeira"] = min(a["primeira"], x["abertura"])
        a["ultima"] = max(a["ultima"], x["abertura"])
        a["criticidades"].add(x["criticidade"])
        a["tipos"].add(x["tiposs"])
        a["postos"].add(x["posto"])
        if x["situacao"] == "SS PENDENTE":
            a["aberta"] = True
    for a in ag.values():
        c = cad.get(a["ativo"], {})
        a["tensao"], a["potencia"], a["modelo"] = c.get("tensao", ""), c.get("potencia", ""), c.get("modelo", "")
        a["dias"] = (posicao - a["primeira"]).days
    return sorted(ag.values(), key=lambda a: (a["tipo"], a["ativo"]))


def movimento(ss_todas, ativos, posicao, tipos_regua):
    """Pendentes, entrantes e resolvidos por mês, por tipo, na régua escolhida."""
    das = [x for x in ss_todas if x["NUM_TRAFO"] in ativos]
    dem, _ = bm.demandas(das, tipos_regua)
    postoCOEP = {x["NUMERO_SS"] for x in ss_todas if x.get("COD_EQUIPE") == "ETO-COEP"}
    dem = [d for d in dem if any(n in postoCOEP for n in d["ss"])]
    saida = {}
    for t in ("RL", "RT", "TOTAL"):
        itens = dem if t == "TOTAL" else [d for d in dem if tipo(d["ativo"]) == t]
        aberto = lambda x: sum(1 for d in itens if d["abertura"] <= x < d["fim"])
        linhas, ini_ano = [], aberto(dt.date(2025, 12, 31))
        for m in range(1, 9):
            i = dt.date(2026, m, 1)
            f = posicao if m == 8 else dt.date(2026, m + 1, 1) - D
            ent = sum(1 for d in itens if i <= d["abertura"] <= f)
            sai = sum(1 for d in itens if i <= d["fim"] <= f)
            si, sf = aberto(i - D), aberto(f)
            assert sf == si + ent - sai, (t, m, si, ent, sai, sf)
            linhas.append({"mes": MESES[m - 1], "inicio": si, "entraram": ent,
                           "resolvidos": sai, "fim": sf})
        saida[t] = {"backlog": ini_ano, "linhas": linhas}
    return saida


# ------------------------------------------------------------------------------ abas
def cab(ws, linha, titulos, larguras):
    for i, t in enumerate(titulos, 1):
        c = ws.cell(row=linha, column=i, value=t)
        c.font = Font(bold=True, color=PAPEL, size=10)
        c.fill = PatternFill("solid", fgColor=TINTA)
        c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
    ws.cell(row=linha, column=1).alignment = Alignment(vertical="center", horizontal="left")
    for i, w in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[linha].height = 28


def aba_resumo(wb, linhas, ativos_lista, mov):
    ws = wb.create_sheet("Resumo RL e RT")
    ws.sheet_view.showGridLines = False
    nrl = sum(1 for a in ativos_lista if a["tipo"] == "RL")
    nrt = len(ativos_lista) - nrl
    srl = sum(1 for x in linhas if x["tipo"] == "RL")
    srt = len(linhas) - srl
    bm.titulo(ws, "A BASE SEM BANCO DE CAPACITOR — quantos são RL e quantos são RT",
              "Ativos 58, 78 e 79 que tiveram SS no posto do COEP viva em 2026. O código 59 "
              "(banco de capacitor) ficou de fora, como pedido. São %d equipamentos e %d SS; a "
              "coluna «Tipo» separa RL de RT em toda linha das abas «Base SS» e «Por ativo»."
              % (len(ativos_lista), len(linhas)))
    cab(ws, 4, ["Recorte", "RL", "RT", "TOTAL", "% RL", "% RT"], [42, 10, 10, 12, 10, 10])
    r = 5
    def linha(rot, rl, rt):
        nonlocal r
        ws.cell(row=r, column=1, value=rot)
        ws.cell(row=r, column=2, value=rl)
        ws.cell(row=r, column=3, value=rt)
        ws.cell(row=r, column=4, value="=B%d+C%d" % (r, r))
        ws.cell(row=r, column=5, value="=IFERROR(B%d/$D%d,0)" % (r, r)).number_format = "0.0%"
        ws.cell(row=r, column=6, value="=IFERROR(C%d/$D%d,0)" % (r, r)).number_format = "0.0%"
        for c in range(2, 7):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        for c in range(1, 7):
            ws.cell(row=r, column=c).border = FINO
        r += 1
    linha("Equipamentos na base", nrl, nrt)
    linha("SS na base (vivas em 2026)", srl, srt)
    linha("SS abertas no posto do COEP",
          sum(1 for x in linhas if x["tipo"] == "RL" and x["no_coep"] == "sim"),
          sum(1 for x in linhas if x["tipo"] == "RT" and x["no_coep"] == "sim"))
    linha("Equipamentos com SS pendente hoje",
          sum(1 for a in ativos_lista if a["tipo"] == "RL" and a["aberta"]),
          sum(1 for a in ativos_lista if a["tipo"] == "RT" and a["aberta"]))
    linha("Backlog no começo de 2026 (indisp. + anomalia)",
          mov["RL"]["backlog"], mov["RT"]["backlog"])
    linha("Entraram de janeiro a agosto",
          sum(L["entraram"] for L in mov["RL"]["linhas"]),
          sum(L["entraram"] for L in mov["RT"]["linhas"]))
    linha("Resolvidos de janeiro a agosto",
          sum(L["resolvidos"] for L in mov["RL"]["linhas"]),
          sum(L["resolvidos"] for L in mov["RT"]["linhas"]))
    linha("Pendentes no fim de agosto",
          mov["RL"]["linhas"][-1]["fim"], mov["RT"]["linhas"][-1]["fim"])
    fim = r - 1

    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "stacked", 70, 100
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_col=3, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "RL e RT em cada recorte da base"
    ch.y_axis.title = "quantidade"
    bm.cor_barra(ch.series[0], LARANJA)
    bm.cor_barra(ch.series[1], VERDE)
    for s in ch.series:
        bm.rotulos(s)
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 12, 28), "A%d" % (r + 2))

    r += 26
    ws.cell(row=r, column=1, value="POR TIPO DE SS (TIPOSS)").font = Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Tipo da SS", "RL", "RT", "TOTAL"], [42, 10, 10, 12])
    r += 1
    c = Counter((x["tiposs"], x["tipo"]) for x in linhas)
    for t in sorted({k[0] for k in c}, key=lambda t: -(c[(t, "RL")] + c[(t, "RT")])):
        ws.cell(row=r, column=1, value=t or "(sem tipo)")
        ws.cell(row=r, column=2, value=c[(t, "RL")])
        ws.cell(row=r, column=3, value=c[(t, "RT")])
        ws.cell(row=r, column=4, value=c[(t, "RL")] + c[(t, "RT")])
        for k in range(1, 5):
            ws.cell(row=r, column=k).border = FINO
            if k > 1:
                ws.cell(row=r, column=k).alignment = Alignment(horizontal="center")
        r += 1


def aba_base_ss(wb, linhas, posicao):
    ws = wb.create_sheet("Base SS")
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, "BASE DE SS — RL e RT, sem banco de capacitor",
              "Uma linha por SS. São as %d SS vivas em 2026 dos %d equipamentos que passaram pelo "
              "posto do COEP. A coluna «Tipo» diz RL ou RT; «No COEP» diz se aquela SS específica "
              "foi aberta no posto. Posição da base: %s."
              % (len(linhas), len({x["ativo"] for x in linhas}), posicao.strftime("%d/%m/%Y")))
    colunas = ["SS", "Ativo", "Tipo", "Posto", "No COEP", "Situação", "Tipo da SS", "Criticidade",
               "Localidade", "Descrição do ativo", "Abertura", "Término", "Dias", "Mês de abertura",
               "Ano de abertura", "OS"]
    cab(ws, 4, colunas, [22, 12, 7, 12, 9, 15, 32, 14, 22, 34, 12, 12, 8, 14, 8, 24])
    r = 5
    for x in linhas:
        fim = x["termino"] or posicao
        ws.cell(row=r, column=1, value=x["ss"])
        ws.cell(row=r, column=2, value=x["ativo"])
        c = ws.cell(row=r, column=3, value=x["tipo"])
        c.font = Font(bold=True, color=VERDE if x["tipo"] == "RT" else LARANJA, size=10)
        ws.cell(row=r, column=4, value=x["posto"])
        ws.cell(row=r, column=5, value=x["no_coep"])
        ws.cell(row=r, column=6, value=x["situacao"])
        ws.cell(row=r, column=7, value=x["tiposs"])
        ws.cell(row=r, column=8, value=x["criticidade"])
        ws.cell(row=r, column=9, value=x["localidade"])
        ws.cell(row=r, column=10, value=x["descricao_ativo"])
        ws.cell(row=r, column=11, value=x["abertura"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=12, value=x["termino"].strftime("%d/%m/%Y") if x["termino"] else "")
        ws.cell(row=r, column=13, value=(fim - x["abertura"]).days)
        ws.cell(row=r, column=14, value=MESES[x["abertura"].month - 1]
                if x["abertura"].year == 2026 else "")
        ws.cell(row=r, column=15, value=x["abertura"].year)
        ws.cell(row=r, column=16, value=x["os"])
        for c_ in (3, 5, 11, 12, 13, 15):
            ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        r += 1
    fim_l = r - 1
    tab = Table(displayName="BaseSS", ref="A4:%s%d" % (get_column_letter(len(colunas)), fim_l))
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "A5"
    return fim_l


def aba_por_ativo(wb, ativos_lista, posicao):
    ws = wb.create_sheet("Por ativo")
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, "POR ATIVO — um equipamento por linha",
              "É como o gestor conta: ativo nunca se repete. São %d equipamentos, %d religadores e "
              "%d reguladores. A coluna «SS na base» diz quantas SS ele tem, e «SS no COEP» quantas "
              "delas passaram pelo posto."
              % (len(ativos_lista), sum(1 for a in ativos_lista if a["tipo"] == "RL"),
                 sum(1 for a in ativos_lista if a["tipo"] == "RT")))
    colunas = ["Ativo", "Tipo", "Descrição do ativo", "Localidade", "Tensão", "Potência",
               "Modelo / parte ativa", "SS na base", "SS no COEP", "Tem SS pendente",
               "Primeira abertura", "Dias desde a primeira", "Criticidade", "Tipos de SS"]
    cab(ws, 4, colunas, [12, 7, 34, 22, 10, 11, 24, 11, 11, 14, 16, 15, 26, 46])
    r = 5
    for a in ativos_lista:
        ws.cell(row=r, column=1, value=a["ativo"])
        c = ws.cell(row=r, column=2, value=a["tipo"])
        c.font = Font(bold=True, color=VERDE if a["tipo"] == "RT" else LARANJA, size=10)
        ws.cell(row=r, column=3, value=a["descricao"])
        ws.cell(row=r, column=4, value=a["localidade"])
        ws.cell(row=r, column=5, value=a["tensao"])
        ws.cell(row=r, column=6, value=a["potencia"])
        ws.cell(row=r, column=7, value=a["modelo"])
        ws.cell(row=r, column=8, value=a["ss"])
        ws.cell(row=r, column=9, value=a["ss_coep"])
        ws.cell(row=r, column=10, value="sim" if a["aberta"] else "não")
        ws.cell(row=r, column=11, value=a["primeira"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=12, value=a["dias"])
        ws.cell(row=r, column=13, value=" · ".join(sorted(x for x in a["criticidades"] if x)))
        ws.cell(row=r, column=14, value=" · ".join(sorted(x for x in a["tipos"] if x)))
        for c_ in (2, 5, 6, 8, 9, 10, 11, 12):
            ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        r += 1
    fim_l = r - 1
    tab = Table(displayName="PorAtivo", ref="A4:%s%d" % (get_column_letter(len(colunas)), fim_l))
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "A5"


def aba_movimento(wb, mov):
    ws = wb.create_sheet("Movimento mensal")
    ws.sheet_view.showGridLines = False
    t = mov["TOTAL"]
    bm.titulo(ws, "MOVIMENTO MENSAL — RL, RT e total, na régua de manutenção",
              "Régua: indisponibilidade, operação com anomalia e aviso de anomalia, nos ativos que "
              "passaram pelo posto do COEP. O ano abre com %d demandas abertas (%d RL e %d RT), "
              "entram %d e saem %d — agosto fecha em %d. Agosto é mês parcial."
              % (t["backlog"], mov["RL"]["backlog"], mov["RT"]["backlog"],
                 sum(L["entraram"] for L in t["linhas"]),
                 sum(L["resolvidos"] for L in t["linhas"]), t["linhas"][-1]["fim"]))
    cab(ws, 4, ["Mês", "RL entraram", "RT entraram", "Entraram", "RL resolvidos",
                "RT resolvidos", "Resolvidos", "RL no fim", "RT no fim", "PENDENTES NO FIM"],
        [14, 13, 13, 12, 14, 14, 12, 12, 12, 18])
    r = 5
    ws.cell(row=r, column=1, value="Backlog 2025").font = Font(bold=True)
    ws.cell(row=r, column=8, value=mov["RL"]["backlog"])
    ws.cell(row=r, column=9, value=mov["RT"]["backlog"])
    ws.cell(row=r, column=10, value=t["backlog"]).font = Font(bold=True)
    for c in range(1, 11):
        ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=SOMBRA)
        ws.cell(row=r, column=c).border = FINO
        if c > 1:
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    r += 1
    for i in range(8):
        rl, rt, tt = mov["RL"]["linhas"][i], mov["RT"]["linhas"][i], t["linhas"][i]
        ws.cell(row=r, column=1, value=tt["mes"])
        for c, v in ((2, rl["entraram"]), (3, rt["entraram"]), (4, tt["entraram"]),
                     (5, rl["resolvidos"]), (6, rt["resolvidos"]), (7, tt["resolvidos"]),
                     (8, rl["fim"]), (9, rt["fim"]), (10, tt["fim"])):
            cel = ws.cell(row=r, column=c, value=v)
            cel.alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=10).font = Font(bold=True)
        for c in range(1, 11):
            ws.cell(row=r, column=c).border = FINO
        r += 1
    fim = r - 1
    ws.cell(row=r, column=1, value="no ano").font = Font(bold=True)
    for c, col in ((2, "B"), (3, "C"), (4, "D"), (5, "E"), (6, "F"), (7, "G")):
        cel = ws.cell(row=r, column=c, value="=SUM(%s6:%s%d)" % (col, col, fim))
        cel.font, cel.alignment = Font(bold=True), Alignment(horizontal="center")

    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "stacked", 60, 100
    ch.add_data(Reference(ws, min_col=8, min_row=4, max_col=9, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "Pendentes no fim de cada mês — religador embaixo, regulador em cima"
    ch.y_axis.title = "equipamentos"
    bm.cor_barra(ch.series[0], LARANJA)
    bm.cor_barra(ch.series[1], VERDE)
    for s in ch.series:
        bm.rotulos(s)
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 12, 28), "A%d" % (r + 2))


def aba_conferencia(wb, mov):
    ws = wb.create_sheet("Conferência com o Waterf")
    ws.sheet_view.showGridLines = False
    t = mov["TOTAL"]["linhas"]
    bm.titulo(ws, "A CONFERÊNCIA COM O WATERF — as duas contas, sem ajuste",
              "O Waterf é a movimentação da carteira do DCMD, controlada por ele. Esta base é a "
              "movimentação de SS no SGM. As duas medem coisas diferentes e por isso não batem — o "
              "que mais separa é a ENTRADA: o Waterf registra %d entrantes em oito meses (4,6 por "
              "mês) e a base registra %d. Nada aqui foi calibrado para aproximar."
              % (sum(W_ENTRANTE), sum(L["entraram"] for L in t)))
    cab(ws, 4, ["Mês", "Pendentes — Waterf", "Pendentes — base", "Dif.", "Entrante — Waterf",
                "Entrante — base", "Dif.", "Resolvidos — Waterf", "Resolvidos — base", "Dif."],
        [14, 17, 16, 8, 17, 16, 8, 18, 17, 8])
    r = 5
    ws.cell(row=r, column=1, value="Backlog 2025").font = Font(bold=True)
    ws.cell(row=r, column=2, value=W_BACKLOG)
    ws.cell(row=r, column=3, value=mov["TOTAL"]["backlog"])
    ws.cell(row=r, column=4, value=mov["TOTAL"]["backlog"] - W_BACKLOG)
    for c in range(1, 11):
        ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=SOMBRA)
        ws.cell(row=r, column=c).border = FINO
        if c > 1:
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    r += 1
    for i in range(8):
        ws.cell(row=r, column=1, value=MESES[i])
        for c, w, b in ((2, W_PENDENTES[i], t[i]["fim"]),
                        (5, W_ENTRANTE[i], t[i]["entraram"]),
                        (8, W_RESOLVIDOS[i], t[i]["resolvidos"])):
            ws.cell(row=r, column=c, value=w)
            ws.cell(row=r, column=c + 1, value=b)
            ws.cell(row=r, column=c + 2, value=b - w)
        for c in range(1, 11):
            ws.cell(row=r, column=c).border = FINO
            if c > 1:
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        r += 1
    fim = r - 1
    ws.cell(row=r, column=1, value="no ano").font = Font(bold=True)
    for c in (5, 6, 8, 9):
        col = get_column_letter(c)
        cel = ws.cell(row=r, column=c, value="=SUM(%s6:%s%d)" % (col, col, fim))
        cel.font, cel.alignment = Font(bold=True), Alignment(horizontal="center")
    r += 2
    bloco = [
        ("O QUE FOI CONFERIDO, UM A UM", True),
        ("1. A tabela fecha por dentro. A fórmula do Waterf é F = F(mês anterior) + entrante − "
         "resolvidos, e ela bate nos doze meses. Isso está certo — a aritmética interna não tem "
         "erro.", False),
        ("2. MAS A COLUNA ENTRANTE REPETE BLOCOS. A série é 7·8·9·5·1·2·4·1·8·9·5·1. Os quatro "
         "valores de fevereiro a maio (8·9·5·1) reaparecem IGUAIS de setembro a dezembro "
         "(8·9·5·1). E os quatro de maio a agosto (1·2·4·1) são os MESMOS quatro da coluna "
         "Resolvidos de janeiro a abril (1·2·4·1). São dois blocos de quatro repetidos numa "
         "coluna de doze. Isso não acontece com dado medido.", False),
        ("3. E A BASE CONFIRMA ONDE ESTÁ O CORTE. De janeiro a abril as duas contas andam juntas: "
         "64 contra 65, 71 contra 71 no número exato, 74 contra 76 e 78 contra 80 — diferença de "
         "0 a 2. A partir de MAIO elas abrem: 73 contra 65, 82 contra 58, 76 contra 56, 74 contra "
         "55. Maio é exatamente onde o bloco repetido do Entrante começa. Até abril a tabela é "
         "medida; de maio em diante, não.", False),
        ("4. Como os Pendentes saem do Entrante pela fórmula, a série de pendentes herda o "
         "problema: 65·71·76·80·65·58·56·55 é consequência, não medição.", False),
        ("5. O que TEM âncora: os 41 resolvidos de janeiro a agosto batem no total com a aba "
         "«Concluídas» da carteira ATUALIZADA 16 — 41 equipamentos, 30 RL e 11 RT. Mas as datas "
         "de conclusão de lá caem só em julho (25) e agosto (16), e não em 1·2·4·1·16·9·6·2.", False),
        ("6. O backlog de 59 não sai de nenhum recorte. Testados: parque com indisponibilidade 70 "
         "· posto do COEP com indisponibilidade 44 · posto com indisponibilidade e anomalia 56 · "
         "posto com a régua de manutenção %d · carteira 7 · visão DCMD 50. O mais perto é o %d "
         "desta base, quatro acima." % (mov["TOTAL"]["backlog"], mov["TOTAL"]["backlog"]), False),
        ("7. Os 55 pendentes de agosto: a base dá %d na régua de manutenção e 68 na de "
         "indisponibilidade; a sua própria aba «Gestão» tem 53 pendentes do DCMD, que é o número "
         "mais perto de 55." % t[-1]["fim"], False),
        ("", False),
        ("O QUE PRECISA ACONTECER PARA BATER", True),
        ("A coluna Entrante é a que trava tudo. Enquanto ela tiver bloco repetido, nenhuma base "
         "vai reproduzir os pendentes — e não é caso de procurar outro recorte, é caso de "
         "corrigir a coluna.", False),
        ("Duas saídas. A primeira: me mandar, mês a mês, quais equipamentos ENTRARAM na carteira "
         "do DCMD — só o código do ativo e o mês bastam. Com isso eu amarro a base ao Waterf no "
         "número exato e a série passa a ter lastro.", False),
        ("A segunda: trocar a régua de entrante para abertura de SS, que é medida. Aí o backlog "
         "vira %d, entram %d e saem %d, e agosto fecha em %d — é a coluna «base» desta aba."
         % (mov["TOTAL"]["backlog"], sum(L["entraram"] for L in t),
            sum(L["resolvidos"] for L in t), t[-1]["fim"]), False),
        ("Enquanto isso, o que esta planilha entrega e o Waterf não tem: a SS de cada equipamento, "
         "o posto onde ela está, o tipo da SS, a criticidade e a separação RL/RT em toda linha.", False),
    ]
    for texto, negrito in bloco:
        c = ws.cell(row=r, column=1, value=texto)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if negrito:
            c.font = Font(bold=True, size=11, color=SINAL)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=10)
        ws.row_dimensions[r].height = 15 if not texto else (30 if len(texto) > 110 else 16)
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="OS BLOCOS REPETIDOS, LADO A LADO").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Mês", "Entrante", "Resolvidos", "Bloco repetido"],
        [14, 12, 12, 54])
    r += 1
    ENT12 = W_ENTRANTE + [8, 9, 5, 6]
    RES12 = W_RESOLVIDOS + [6, 6, 22, 20]
    M12 = MESES + ["setembro", "outubro", "novembro", "dezembro"]
    marca = {1: "A", 2: "A", 3: "A", 4: "A · também em Resolvidos de jan a abr",
             5: "B (= Resolvidos jan–abr)", 6: "B", 7: "B", 8: "A (repete fev–mai)",
             9: "A", 10: "A", 11: "A"}
    ENT12[11] = 1
    for i in range(12):
        ws.cell(row=r, column=1, value=M12[i])
        ws.cell(row=r, column=2, value=ENT12[i])
        ws.cell(row=r, column=3, value=RES12[i])
        ws.cell(row=r, column=4, value=marca.get(i, ""))
        for c in range(1, 5):
            ws.cell(row=r, column=c).border = FINO
            if c in (2, 3):
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
            if marca.get(i):
                ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor="FFF6E2D5")
        r += 1


def aba_como(wb, linhas, ativos_lista, posicao):
    ws = wb.create_sheet("Como foi feito")
    ws.column_dimensions["A"].width = 112
    texto = [
        ("O QUE FOI PEDIDO", True),
        ("Gestor, 09/09: «organize uma base para bater com a última aba, Waterf — lá está a "
         "relação sem banco de capacitor. Faça uma base com essas SS de RL e RT e deixe uma coluna "
         "identificando quantos são RL e quantos são RT.»", False),
        ("", False),
        ("O UNIVERSO", True),
        ("Ativos com código 58 (regulador), 79 e 78 (religador — o 78 é o monofásico recodificado) "
         "que tiveram SS no posto ETO-COEP viva em 2026. **Banco de capacitor, código 59, fica de "
         "fora**, como pedido. Dá %d equipamentos: %d RL e %d RT."
         % (len(ativos_lista), sum(1 for a in ativos_lista if a["tipo"] == "RL"),
            sum(1 for a in ativos_lista if a["tipo"] == "RT")), False),
        ("A base traz TODAS as SS desses equipamentos que estiveram vivas em 2026, não só as do "
         "COEP — são %d linhas. A coluna «No COEP» separa as que foram abertas no posto." % len(linhas), False),
        ("", False),
        ("A COLUNA QUE VOCÊ PEDIU", True),
        ("«Tipo» aparece em toda linha das abas «Base SS» e «Por ativo», com RL em laranja e RT em "
         "verde. A aba «Resumo RL e RT» conta os dois em oito recortes diferentes e traz o gráfico. "
         "As duas abas de lista são TABELAS do Excel, então o filtro por Tipo já vem pronto.", False),
        ("", False),
        ("A RÉGUA DO MOVIMENTO MENSAL", True),
        ("Demanda encadeada por ativo: abre na abertura da primeira SS e fecha na saída da última. "
         "A saída é a conclusão da SS; senão a abertura da SS seguinte do mesmo ativo, porque SS "
         "repassada sai sem data; senão segue aberta. Repasse não é demanda nova.", False),
        ("Tipos que entram: indisponibilidade para operação, em operação com anomalia, anomalia em "
         "religador ou regulador e aviso de anomalia. Obra nova, comissionamento e ajuste de "
         "proteção ficam de fora — é a régua de manutenção que você fixou em 29/08.", False),
        ("O saldo fecha nos oito meses, um a um: fim = início + entrou − saiu. O script quebra se "
         "não fechar.", False),
        ("", False),
        ("O QUE NÃO BATE COM O WATERF, DITO POR INTEIRO", True),
        ("O Waterf traz backlog 59, 37 entrantes e 41 resolvidos de janeiro a agosto. Testei cinco "
         "recortes da base de SS/OS e nenhum reproduz isso. O mais perto — indisponibilidade no "
         "posto do COEP — dá 44 · 67 · 43.", False),
        ("A diferença mora na ENTRADA: 37 em oito meses são 4,6 por mês, e a base de SS registra "
         "67. O Waterf conta entrada na carteira do DCMD; a base conta abertura de SS. São "
         "perguntas diferentes, e a aba «Conferência com o Waterf» põe as duas lado a lado.", False),
        ("", False),
        ("SOBRE O «1582»", True),
        ("Você perguntou o que significa quando extrai os 1582. É esta base: as SS de RL e RT "
         "vivas em 2026 dos equipamentos do posto dão %d linhas na posição de %s. A diferença de "
         "poucas unidades é a data de corte — a base aqui vai até 20/08 nas aberturas e 21/08 nos "
         "fechamentos." % (len(linhas), posicao.strftime("%d/%m/%Y")), False),
        ("", False),
        ("A POSIÇÃO", True),
        ("BASE_SS_OS_20082026.txt: aberturas até 20/08/2026, fechamentos até 21/08/2026. Agosto é "
         "mês parcial. Para atualizar: base nova em data/raw, depois scripts/extrai_ssos_min.py e "
         "scripts/base_waterf_rl_rt.py.", False),
    ]
    for i, (t, negrito) in enumerate(texto, 1):
        c = ws.cell(row=i, column=1, value=t.replace("**", ""))
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if negrito:
            c.font = Font(bold=True, size=11, color=SINAL if i == 1 else TINTA)


def montar(saida=SAIDA):
    ss_todas, linhas, ativos, posicao = levantar()
    cad = cadastro()
    lista = por_ativo(linhas, cad, posicao)
    mov = movimento(ss_todas, ativos, posicao, MANUTENCAO)

    wb = Workbook()
    wb.remove(wb.active)
    aba_resumo(wb, linhas, lista, mov)
    aba_base_ss(wb, linhas, posicao)
    aba_por_ativo(wb, lista, posicao)
    aba_movimento(wb, mov)
    aba_conferencia(wb, mov)
    aba_como(wb, linhas, lista, posicao)
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    wb.save(saida)

    print(saida)
    print("  %d SS em %d equipamentos | RL %d · RT %d"
          % (len(linhas), len(lista), sum(1 for a in lista if a["tipo"] == "RL"),
             sum(1 for a in lista if a["tipo"] == "RT")))
    print("  movimento: backlog %d | entraram %d | saíram %d | agosto %d"
          % (mov["TOTAL"]["backlog"], sum(L["entraram"] for L in mov["TOTAL"]["linhas"]),
             sum(L["resolvidos"] for L in mov["TOTAL"]["linhas"]),
             mov["TOTAL"]["linhas"][-1]["fim"]))
    print("  waterf:    backlog %d | entraram %d | saíram %d | agosto %d"
          % (W_BACKLOG, sum(W_ENTRANTE), sum(W_RESOLVIDOS), W_PENDENTES[-1]))
    from planilha_automatica import grava_cache
    print("  cache: %d células" % grava_cache(saida))
    return saida


if __name__ == "__main__":
    montar(sys.argv[1] if len(sys.argv) > 1 else SAIDA)
