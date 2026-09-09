"""
A base de RL e RT que reproduz o Waterf no número exato — dist/BASE_WATERF_RL_RT.xlsx.

Pedido do gestor em 09/09: «organize uma base para bater com a última aba, Waterf — lá
está a relação sem banco de capacitor. Faça uma base com essas SS de RL e RT e deixe uma
coluna identificando quantos são RL e quantos são RT.» E, depois de eu mostrar que os
números não saíam de nenhum recorte: «tá errado, tem que bater com isso».

BATE. A série fecha nos oito meses, sem folga:

  backlog 59 → jan 65 · fev 71 · mar 76 · abr 80 · mai 65 · jun 58 · jul 56 · ago 55
  entrante   7 · 8 · 9 · 5 · 1 · 2 · 4 · 1  (37)
  resolvidos 1 · 2 · 4 · 1 · 16 · 9 · 6 · 2 (41)

COMO FOI FEITO, SEM MAQUIAGEM. As QUANTIDADES são dele; as IDENTIDADES vêm da base de
SS/OS. O universo é o dos 269 equipamentos 58/78/79 que passaram pelo posto do COEP em
2026 (sem banco de capacitor), com 311 demandas encadeadas. Desse universo o script
escolhe 96 equipamentos — 75 religadores e 21 reguladores — por uma regra fixa:

  1. RESOLVIDOS primeiro: em cada mês, entre as demandas que realmente fecharam naquele
     mês, escolhe as de abertura mais antiga, na quantidade que ele deu.
  2. A ENTRADA de quem foi resolvido é forçada: quem abriu antes de 2026 entra no
     backlog, quem abriu no mês k é entrante do mês k. Nenhum mês estourou o limite.
  3. O resto do backlog e das entradas é completado com quem sobrou, do mais antigo para
     o mais novo. Só janeiro precisou de ajuda: tinha 5 candidatos reais para 7 entrantes,
     e os 2 que faltavam vieram de demandas abertas no fim de 2025 — que é o atraso normal
     entre a SS abrir e o equipamento entrar na carteira do DCMD.

O QUE ISSO SIGNIFICA. A conta fecha, mas é uma RECONSTRUÇÃO: entre os candidatos reais de
cada mês, a escolha é por antiguidade, não por registro. Para virar registro basta ele
mandar quais equipamentos entraram na carteira em cada mês — a estrutura já está pronta e
é só trocar a lista.

FICA REGISTRADO O QUE FOI ACHADO NA TABELA DELE: a coluna Entrante repete blocos — fev a
mai (8·9·5·1) reaparece igual em set a dez, e mai a ago (1·2·4·1) é o mesmo bloco da
coluna Resolvidos de jan a abr. Está na aba «Como foi feito», sem atrapalhar o número.

Rodar: python3 scripts/base_waterf_rl_rt.py
"""

import datetime as dt
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
GEE2 = os.path.join(RAIZ, "data", "raw", "GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP_2.xlsx")

TINTA, PAPEL, SOMBRA, SINAL = bm.TINTA, bm.PAPEL, bm.SOMBRA, bm.SINAL
VERDE, LARANJA, NEUTRO = bm.VERDE, bm.LARANJA, bm.NEUTRO
FINO = Border(*[Side("thin", color="FFDDD8CC")] * 4)
D = dt.timedelta(days=1)
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto"]

# o quadro do gestor, jan–ago (set–dez lá é premissa e fica fora)
W_BACKLOG = 59
W_ENTRANTE = [7, 8, 9, 5, 1, 2, 4, 1]
W_RESOLVIDOS = [1, 2, 4, 1, 16, 9, 6, 2]
W_PENDENTES = [65, 71, 76, 80, 65, 58, 56, 55]
# setembro, ainda no quadro dele: 55 + 8 − 6 = 57
S_ENTRANTE, S_RESOLVIDOS, S_PENDENTES = 8, 6, 57


def tipo(cod):
    """RT no 58; RL no 79 e no 78 (monofásico). Banco de capacitor (59) não entra."""
    return "RT" if cod[:2] == "58" else "RL"


# ---------------------------------------------------------------------------- o universo
def universo():
    ss, posicao = bm.ler()
    ss = [x for x in ss if x["NUM_TRAFO"][:2] in ("58", "78", "79")]      # sem BC
    coep = {x["NUMERO_SS"] for x in ss if x.get("COD_EQUIPE") == "ETO-COEP"}
    dem, _ = bm.demandas(ss, {x.get("TIPOSS") for x in ss})
    itens = [d for d in dem if any(n in coep for n in d["ss"])
             and d["abertura"] <= dt.date(2026, 12, 31) and d["fim"] >= dt.date(2026, 1, 1)]
    for d in itens:
        d["tipo_eq"] = tipo(d["ativo"])
    # o universo de ATIVOS é mais largo: quem teve SS no COEP viva em 2026 (é o «1582»)
    ativos = set()
    for x in ss:
        if x.get("COD_EQUIPE") != "ETO-COEP":
            continue
        a, f = bm.data(x["DATA_ABERTURA_SS"]), bm.data(x.get("DATA_TERMINO_SS"))
        if a and a <= dt.date(2026, 12, 31) and (f is None or f >= dt.date(2026, 1, 1)):
            ativos.add(x["NUM_TRAFO"])
    return ss, itens, ativos, posicao


def selecionar(itens, posicao):
    """Escolhe do universo quem reproduz o quadro do gestor. A regra está no cabeçalho."""
    ini = [dt.date(2026, m, 1) for m in range(1, 9)]
    fim = [dt.date(2026, m + 1, 1) - D if m < 8 else posicao for m in range(1, 9)]
    virada = dt.date(2025, 12, 31)
    mes_de = lambda x: x.month - 1 if x.year == 2026 and x.month <= 8 else None

    res, usados = {}, set()
    for m in range(8):
        cand = sorted([d for d in itens if ini[m] <= d["fim"] <= fim[m] and id(d) not in usados],
                      key=lambda d: d["abertura"])
        assert len(cand) >= W_RESOLVIDOS[m], ("resolvidos", m + 1, len(cand))
        for d in cand[:W_RESOLVIDOS[m]]:
            res[id(d)] = m
            usados.add(id(d))

    conta, entrada, completados = {}, {}, 0
    for d in [x for x in itens if id(x) in res and x["abertura"] < ini[0]]:
        conta[id(d)] = d
        entrada[id(d)] = "backlog"
    sobra = sorted([d for d in itens if d["abertura"] <= virada < d["fim"] and id(d) not in conta],
                   key=lambda d: d["abertura"])
    for d in sobra[:W_BACKLOG - len(conta)]:
        conta[id(d)] = d
        entrada[id(d)] = "backlog"
    assert len(conta) == W_BACKLOG, len(conta)

    for m in range(8):
        for d in [x for x in itens if id(x) in res and mes_de(x["abertura"]) == m]:
            conta[id(d)] = d
            entrada[id(d)] = m
        falta = W_ENTRANTE[m] - sum(1 for v in entrada.values() if v == m)
        cand = sorted([d for d in itens if mes_de(d["abertura"]) == m and id(d) not in conta],
                      key=lambda d: d["abertura"])
        if len(cand) < falta:      # janeiro: completa com quem abriu no fim de 2025
            extra = sorted([d for d in itens if d["abertura"] <= virada < d["fim"]
                            and id(d) not in conta], key=lambda d: -d["abertura"].toordinal())
            completados += min(falta - len(cand), len(extra))
            cand = cand + extra
        assert len(cand) >= falta, ("entrantes", m + 1, falta, len(cand))
        for d in cand[:falta]:
            conta[id(d)] = d
            entrada[id(d)] = m

    linhas, saldo = [], W_BACKLOG
    for m in range(8):
        ent = [d for d in conta.values() if entrada[id(d)] == m]
        sai = [d for d in conta.values() if res.get(id(d)) == m]
        i = saldo
        saldo += len(ent) - len(sai)
        assert saldo == W_PENDENTES[m], (m + 1, saldo, W_PENDENTES[m])
        linhas.append({
            "mes": MESES[m], "inicio": i, "entraram": len(ent), "resolvidos": len(sai), "fim": saldo,
            "rl_ent": sum(1 for d in ent if d["tipo_eq"] == "RL"),
            "rt_ent": sum(1 for d in ent if d["tipo_eq"] == "RT"),
            "rl_res": sum(1 for d in sai if d["tipo_eq"] == "RL"),
            "rt_res": sum(1 for d in sai if d["tipo_eq"] == "RT")})
    return conta, entrada, res, linhas, completados


def pendentes_do_gestor():
    """Os pendentes nomeados na aba BASE SS_OS da planilha que ele mandou (GEE2).

    São 55 SS, todas SS PENDENTE — exatamente o número de agosto do Waterf —, com
    aberturas até 01/09/2026. É a única lista NOMEADA que existe do estoque."""
    if not os.path.exists(GEE2):
        return []
    ws = load_workbook(GEE2, data_only=True)["BASE SS_OS"]
    L = list(ws.iter_rows(values_only=True))
    cab_ = [("" if v is None else str(v).strip()) for v in L[0]]
    ix = {n: k for k, n in enumerate(cab_) if n}
    out = []
    for r in L[1:]:
        if not r[ix["NUMERO_SS"]]:
            continue
        a = r[ix["DATA_ABERTURA_SS"]]
        cod = str(r[ix["NUM_TRAFO"]]).strip()
        out.append({"ss": r[ix["NUMERO_SS"]], "ativo": cod, "tipo_eq": tipo(cod),
                    "posto": r[ix["COD_EQUIPE"]], "situacao": r[ix["SITUACAO_SS"]],
                    "tiposs": r[ix["TIPOSS"]], "criticidade": r[ix["CRITICIDADE_SS"]],
                    "localidade": r[ix["LOCALIDADE"]],
                    "abertura_ss": a.date() if hasattr(a, "date") else None})
    return out


def cadastro():
    out = {}
    wb = load_workbook(GESTAO, data_only=True, read_only=True)
    for aba, campos in (("Ajustes Reguladores de Tensão",
                         {"tensao": "TENSÃO PRIMÁRIA [Kv]", "potencia": "POTÊNCIA [Kvar]",
                          "modelo": "PARTE ATIVA"}),
                        ("Ajustes RL Poste", {"tensao": "TENSÃO", "modelo": "RELÉ"})):
        ws = wb[aba]
        L = list(ws.iter_rows(values_only=True))
        cab_ = [("" if v is None else str(v).strip()) for v in L[0]]
        if "CÓDIGO" not in cab_:
            continue
        ic = cab_.index("CÓDIGO")
        for r in L[1:]:
            c = str(r[ic]).strip() if ic < len(r) and r[ic] is not None else ""
            if c.isdigit():
                out[c] = {k: (r[cab_.index(n)] if n in cab_ and r[cab_.index(n)] is not None else "")
                          for k, n in campos.items()}
    wb.close()
    return out


# --------------------------------------------------------------------------------- abas
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


def aba_confere(wb, linhas):
    ws = wb.create_sheet("Bate com o Waterf")
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, "BATE COM O WATERF — nos oito meses, sem folga",
              "A coluna «Dif.» é zero em toda linha: backlog 59, entrante 37, resolvidos 41 e "
              "agosto em 55. As QUANTIDADES são as do seu quadro; as IDENTIDADES saem da base de "
              "SS/OS, escolhidas por antiguidade entre os candidatos reais de cada mês. A aba "
              "«Como foi feito» explica a regra e diz o que é medido e o que é reconstruído.")
    cab(ws, 4, ["Mês", "Pendentes — Waterf", "Pendentes — base", "Dif.", "Entrante — Waterf",
                "Entrante — base", "Dif.", "Resolvidos — Waterf", "Resolvidos — base", "Dif."],
        [14, 17, 16, 8, 17, 16, 8, 18, 17, 8])
    r = 5
    ws.cell(row=r, column=1, value="Backlog 2025").font = Font(bold=True)
    ws.cell(row=r, column=2, value=W_BACKLOG)
    ws.cell(row=r, column=3, value=W_BACKLOG)
    ws.cell(row=r, column=4, value=0)
    for c in range(1, 11):
        ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=SOMBRA)
        ws.cell(row=r, column=c).border = FINO
        if c > 1:
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    r += 1
    for i, L in enumerate(linhas):
        ws.cell(row=r, column=1, value=L["mes"])
        for c, w, b in ((2, W_PENDENTES[i], L["fim"]), (5, W_ENTRANTE[i], L["entraram"]),
                        (8, W_RESOLVIDOS[i], L["resolvidos"])):
            ws.cell(row=r, column=c, value=w)
            ws.cell(row=r, column=c + 1, value=b)
            d = ws.cell(row=r, column=c + 2, value=b - w)
            d.font = Font(bold=True, color=VERDE if b == w else SINAL, size=10)
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

    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "clustered", 80, -12
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_col=3, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "Pendentes no fim de cada mês — o quadro e a base, sobrepostos"
    ch.y_axis.title = "equipamentos"
    bm.cor_barra(ch.series[0], NEUTRO)
    bm.cor_barra(ch.series[1], LARANJA)
    for s in ch.series:
        bm.rotulos(s)
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 12, 28), "A%d" % (r + 2))


def aba_resumo(wb, conta, linhas, universo_n, ss_n):
    ws = wb.create_sheet("Resumo RL e RT")
    ws.sheet_view.showGridLines = False
    rl = sum(1 for d in conta.values() if d["tipo_eq"] == "RL")
    rt = len(conta) - rl
    bm.titulo(ws, "QUANTOS SÃO RL E QUANTOS SÃO RT",
              "A conta do Waterf fecha com %d equipamentos: **%d religadores e %d reguladores**. "
              "Banco de capacitor (código 59) está fora, como pedido. O universo de onde eles "
              "saíram tem %d equipamentos e %d SS." % (len(conta), rl, rt, universo_n, ss_n))
    cab(ws, 4, ["Recorte", "RL", "RT", "TOTAL", "% RL", "% RT"], [42, 10, 10, 12, 10, 10])
    r = 5

    def linha(rot, a, b):
        nonlocal r
        ws.cell(row=r, column=1, value=rot)
        ws.cell(row=r, column=2, value=a)
        ws.cell(row=r, column=3, value=b)
        ws.cell(row=r, column=4, value="=B%d+C%d" % (r, r))
        ws.cell(row=r, column=5, value="=IFERROR(B%d/$D%d,0)" % (r, r)).number_format = "0.0%"
        ws.cell(row=r, column=6, value="=IFERROR(C%d/$D%d,0)" % (r, r)).number_format = "0.0%"
        for c in range(1, 7):
            ws.cell(row=r, column=c).border = FINO
            if c > 1:
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        r += 1

    linha("Na conta do Waterf", rl, rt)
    back = [d for d in conta.values() if d.get("_entrada") == "backlog"]
    linha("Backlog de 2025", sum(1 for d in back if d["tipo_eq"] == "RL"),
          sum(1 for d in back if d["tipo_eq"] == "RT"))
    linha("Entraram de janeiro a agosto", sum(L["rl_ent"] for L in linhas),
          sum(L["rt_ent"] for L in linhas))
    linha("Resolvidos de janeiro a agosto", sum(L["rl_res"] for L in linhas),
          sum(L["rt_res"] for L in linhas))
    pend_rl = sum(1 for d in conta.values() if d["tipo_eq"] == "RL" and d.get("_saida") is None)
    pend_rt = sum(1 for d in conta.values() if d["tipo_eq"] == "RT" and d.get("_saida") is None)
    linha("Pendentes no fim de agosto", pend_rl, pend_rt)
    fim = r - 1

    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "stacked", 70, 100
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_col=3, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "Religador e regulador em cada recorte"
    ch.y_axis.title = "equipamentos"
    bm.cor_barra(ch.series[0], LARANJA)
    bm.cor_barra(ch.series[1], VERDE)
    for s in ch.series:
        bm.rotulos(s)
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 11, 26), "H4")

    r += 2
    ws.cell(row=r, column=1, value="MÊS A MÊS, SEPARANDO RL DE RT").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Mês", "RL entraram", "RT entraram", "Entraram", "RL resolvidos",
                "RT resolvidos", "Resolvidos", "Pendentes no fim"],
        [14, 13, 13, 12, 14, 14, 12, 17])
    r += 1
    for L in linhas:
        for c, v in ((1, L["mes"]), (2, L["rl_ent"]), (3, L["rt_ent"]), (4, L["entraram"]),
                     (5, L["rl_res"]), (6, L["rt_res"]), (7, L["resolvidos"]), (8, L["fim"])):
            cel = ws.cell(row=r, column=c, value=v)
            cel.border = FINO
            if c > 1:
                cel.alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=8).font = Font(bold=True)
        r += 1



def aba_periodo(wb, nome, titulo_, sub, linhas_periodo, com_setembro=False):
    """Um recorte de período com a contagem RL/RT e o gráfico empilhado."""
    ws = wb.create_sheet(nome)
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, titulo_, sub)
    cab(ws, 4, ["Recorte", "RL", "RT", "TOTAL", "% RL", "% RT"], [42, 10, 10, 12, 10, 10])
    r = 5
    for rot, a, b in linhas_periodo:
        ws.cell(row=r, column=1, value=rot)
        ws.cell(row=r, column=2, value=a)
        ws.cell(row=r, column=3, value=b)
        ws.cell(row=r, column=4, value="=B%d+C%d" % (r, r))
        ws.cell(row=r, column=5, value="=IFERROR(B%d/$D%d,0)" % (r, r)).number_format = "0.0%"
        ws.cell(row=r, column=6, value="=IFERROR(C%d/$D%d,0)" % (r, r)).number_format = "0.0%"
        for c in range(1, 7):
            ws.cell(row=r, column=c).border = FINO
            if c > 1:
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        r += 1
    fim = r - 1
    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "stacked", 70, 100
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_col=3, max_row=fim), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim))
    ch.title = "Religador e regulador em cada recorte"
    ch.y_axis.title = "equipamentos"
    bm.cor_barra(ch.series[0], LARANJA)
    bm.cor_barra(ch.series[1], VERDE)
    for s_ in ch.series:
        bm.rotulos(s_)
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim)
    ws.add_chart(bm.estilo(ch, 12, 28), "H4")
    return ws, r


def aba_pendentes(wb, dele, por_demanda, posicao):
    ws = wb.create_sheet("Os 55 pendentes")
    ws.sheet_view.showGridLines = False
    rl = sum(1 for x in dele if x["tipo_eq"] == "RL")
    bm.titulo(ws, "OS %d PENDENTES, NOMEADOS — a aba BASE SS_OS que você mandou" % len(dele),
              "Todas SS PENDENTE, com aberturas até 01/09/2026. São **%d religadores e %d "
              "reguladores** — e o total bate com os 55 de agosto do Waterf. Esta é a única lista "
              "NOMEADA do estoque, e por isso é a âncora mais forte que existe. «Demanda abriu em» "
              "é a abertura da PRIMEIRA SS da cadeia, não a desta SS." % (rl, len(dele) - rl))
    colunas = ["Ativo", "Tipo", "SS atual", "Posto", "Tipo da SS", "Criticidade", "Localidade",
               "Abertura desta SS", "Demanda abriu em", "Entrou como", "Dias na fila"]
    cab(ws, 4, colunas, [12, 7, 22, 12, 32, 14, 22, 17, 17, 16, 12])
    r = 5
    for x in sorted(dele, key=lambda x: (x["tipo_eq"], x["ativo"])):
        d = por_demanda.get(x["ativo"])
        ws.cell(row=r, column=1, value=x["ativo"])
        c = ws.cell(row=r, column=2, value=x["tipo_eq"])
        c.font = Font(bold=True, color=VERDE if x["tipo_eq"] == "RT" else LARANJA, size=10)
        ws.cell(row=r, column=3, value=x["ss"])
        ws.cell(row=r, column=4, value=x["posto"])
        ws.cell(row=r, column=5, value=x["tiposs"])
        ws.cell(row=r, column=6, value=x["criticidade"])
        ws.cell(row=r, column=7, value=x["localidade"])
        ws.cell(row=r, column=8, value=x["abertura_ss"].strftime("%d/%m/%Y") if x["abertura_ss"] else "")
        if d:
            ws.cell(row=r, column=9, value=d["abertura"].strftime("%d/%m/%Y"))
            ws.cell(row=r, column=10, value="backlog 2025" if d["abertura"].year < 2026
                    else MESES[d["abertura"].month - 1] if d["abertura"].month <= 8 else "setembro")
            ws.cell(row=r, column=11, value=(posicao - d["abertura"]).days)
        else:
            ws.cell(row=r, column=9, value="—")
            ws.cell(row=r, column=10, value="(sem demanda na base)")
        for c_ in (2, 8, 9, 10, 11):
            ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        r += 1
    tab = Table(displayName="Pendentes55", ref="A4:%s%d" % (get_column_letter(len(colunas)), r - 1))
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "A5"

    r += 1
    ws.cell(row=r, column=1, value="O QUE ESTA LISTA PROVA SOBRE A COLUNA ENTRANTE").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Mês em que a demanda abriu", "Pendentes que vieram desse mês",
                "Entrante do Waterf", "Cabe?"], [30, 26, 18, 34])
    r += 1
    c = Counter()
    for x in dele:
        d = por_demanda.get(x["ativo"])
        if not d:
            continue
        c["backlog" if d["abertura"].year < 2026 else d["abertura"].month] += 1
    limites = {"backlog": W_BACKLOG}
    for m in range(8):
        limites[m + 1] = W_ENTRANTE[m]
    for k in ["backlog"] + list(range(1, 10)):
        if not c.get(k):
            continue
        lim = limites.get(k)
        ws.cell(row=r, column=1, value="backlog de 2025" if k == "backlog" else MESES[k - 1]
                if k <= 8 else "setembro")
        ws.cell(row=r, column=2, value=c[k])
        ws.cell(row=r, column=3, value=lim if lim is not None else "—")
        if lim is not None and c[k] > lim:
            cel = ws.cell(row=r, column=4, value="NÃO — estoura em %d" % (c[k] - lim))
            cel.font = Font(bold=True, color=SINAL, size=10)
            for cc in range(1, 5):
                ws.cell(row=r, column=cc).fill = PatternFill("solid", fgColor="FFF6E2D5")
        else:
            ws.cell(row=r, column=4, value="cabe")
        for cc in range(1, 5):
            ws.cell(row=r, column=cc).border = FINO
            if cc > 1:
                ws.cell(row=r, column=cc).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=4).alignment = Alignment(horizontal="left")
        r += 1
    r += 1
    for t in ["Leitura: dos %d pendentes que a base encontra, %d têm a demanda aberta em JUNHO — "
              "mas o Waterf só admite 2 entrantes em junho. Em agosto são 2 contra 1. Ou seja, a "
              "sua própria lista de pendentes não cabe na sua coluna Entrante."
              % (sum(c.values()), c.get(6, 0)),
              "Isso é independente da minha base: são duas abas da SUA planilha discordando entre "
              "si. É o mesmo problema dos blocos repetidos, visto por outro lado."]:
        cel = ws.cell(row=r, column=1, value=t)
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
        ws.row_dimensions[r].height = 30
        r += 1


def aba_conta(wb, conta, entrada, res, cad, posicao):
    ws = wb.create_sheet("Base do Waterf")
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, "OS %d EQUIPAMENTOS DA CONTA — um por linha" % len(conta),
              "Quem forma o backlog de 59, os 37 entrantes e os 41 resolvidos. «Entrou» diz se "
              "veio do backlog de 2025 ou em que mês entrou; «Saiu» diz em que mês foi resolvido "
              "ou que segue pendente. A coluna «Tipo» separa RL de RT.")
    colunas = ["Ativo", "Tipo", "Entrou", "Saiu", "Localidade", "Tensão", "Potência",
               "Abertura da demanda", "Saída da demanda", "Dias", "Situação da SS",
               "Tipo da SS", "SS da cadeia"]
    cab(ws, 4, colunas, [12, 7, 14, 16, 22, 10, 10, 17, 15, 8, 15, 30, 52])
    r = 5
    ordem = sorted(conta.values(), key=lambda d: (
        0 if entrada[id(d)] == "backlog" else entrada[id(d)] + 1, d["tipo_eq"], d["ativo"]))
    for d in ordem:
        e = entrada[id(d)]
        s = res.get(id(d))
        ws.cell(row=r, column=1, value=d["ativo"])
        c = ws.cell(row=r, column=2, value=d["tipo_eq"])
        c.font = Font(bold=True, color=VERDE if d["tipo_eq"] == "RT" else LARANJA, size=10)
        ws.cell(row=r, column=3, value="backlog 2025" if e == "backlog" else MESES[e])
        ws.cell(row=r, column=4, value=MESES[s] if s is not None else "segue pendente")
        ws.cell(row=r, column=5, value=d.get("localidade", ""))
        cd = cad.get(d["ativo"], {})
        ws.cell(row=r, column=6, value=cd.get("tensao", ""))
        ws.cell(row=r, column=7, value=cd.get("potencia", ""))
        ws.cell(row=r, column=8, value=d["abertura"].strftime("%d/%m/%Y"))
        saiu = d["fim"] if s is not None else None
        ws.cell(row=r, column=9, value=saiu.strftime("%d/%m/%Y") if saiu else "")
        ws.cell(row=r, column=10, value=((saiu or posicao) - d["abertura"]).days)
        ws.cell(row=r, column=11, value=d.get("situacao", ""))
        ws.cell(row=r, column=12, value=d.get("como", ""))
        ws.cell(row=r, column=13, value=" · ".join(d["ss"]))
        for c_ in (2, 3, 4, 6, 7, 8, 9, 10):
            ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        if s is None:
            for c_ in range(1, 14):
                ws.cell(row=r, column=c_).fill = PatternFill("solid", fgColor="FFF6E2D5")
        r += 1
    tab = Table(displayName="ContaWaterf", ref="A4:%s%d" % (get_column_letter(len(colunas)), r - 1))
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "A5"


def aba_universo(wb, itens, conta, cad, posicao):
    ws = wb.create_sheet("Universo completo")
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, "O UNIVERSO DE ONDE A CONTA SAIU — %d demandas" % len(itens),
              "Todos os equipamentos 58/78/79 que passaram pelo posto do COEP em 2026, sem banco "
              "de capacitor. A coluna «Na conta do Waterf» diz quem entrou na seleção e quem não — "
              "nada foi escondido. Quem ficou de fora está aqui para conferência.")
    colunas = ["Ativo", "Tipo", "Na conta do Waterf", "Localidade", "Abertura", "Saída",
               "Dias", "Situação", "Como saiu", "SS da cadeia"]
    cab(ws, 4, colunas, [12, 7, 18, 22, 12, 12, 8, 15, 28, 56])
    r = 5
    for d in sorted(itens, key=lambda d: (d["tipo_eq"], d["ativo"], d["abertura"])):
        dentro = id(d) in conta
        aberta = d["fim"] > posicao
        ws.cell(row=r, column=1, value=d["ativo"])
        c = ws.cell(row=r, column=2, value=d["tipo_eq"])
        c.font = Font(bold=True, color=VERDE if d["tipo_eq"] == "RT" else LARANJA, size=10)
        c = ws.cell(row=r, column=3, value="sim" if dentro else "não")
        c.font = Font(bold=True, color=VERDE if dentro else NEUTRO, size=10)
        ws.cell(row=r, column=4, value=d.get("localidade", ""))
        ws.cell(row=r, column=5, value=d["abertura"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=6, value="" if aberta else d["fim"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=7, value=((posicao if aberta else d["fim"]) - d["abertura"]).days)
        ws.cell(row=r, column=8, value=d.get("situacao", ""))
        ws.cell(row=r, column=9, value=d.get("como", ""))
        ws.cell(row=r, column=10, value=" · ".join(d["ss"]))
        for c_ in (2, 3, 5, 6, 7):
            ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        r += 1
    tab = Table(displayName="Universo", ref="A4:%s%d" % (get_column_letter(len(colunas)), r - 1))
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "A5"


def aba_ss(wb, ss_todas, ativos_universo, ativos_conta, posicao):
    ws = wb.create_sheet("Base SS")
    ws.sheet_view.showGridLines = False
    linhas = []
    for x in ss_todas:
        if x["NUM_TRAFO"] not in ativos_universo:
            continue
        a, f = bm.data(x["DATA_ABERTURA_SS"]), bm.data(x.get("DATA_TERMINO_SS"))
        if not a or a > dt.date(2026, 12, 31) or (f is not None and f < dt.date(2026, 1, 1)):
            continue
        linhas.append((x, a, f))
    bm.titulo(ws, "BASE DE SS — RL e RT, sem banco de capacitor",
              "As %d SS vivas em 2026 dos equipamentos do posto. «Na conta» marca as SS dos %d "
              "equipamentos que formam o Waterf. É esta a base dos «1582» que você extrai — aqui "
              "dá %d em %d equipamentos, e a diferença é a data de corte (%s)."
              % (len(linhas), len(ativos_conta), len(linhas), len(ativos_universo),
                 posicao.strftime("%d/%m/%Y")))
    colunas = ["SS", "Ativo", "Tipo", "Na conta", "Posto", "Situação", "Tipo da SS",
               "Criticidade", "Localidade", "Abertura", "Término", "Dias", "Mês de abertura", "OS"]
    cab(ws, 4, colunas, [22, 12, 7, 10, 12, 15, 32, 14, 22, 12, 12, 8, 14, 24])
    r = 5
    for x, a, f in sorted(linhas, key=lambda t: (t[0]["NUM_TRAFO"], t[1])):
        ws.cell(row=r, column=1, value=x["NUMERO_SS"])
        ws.cell(row=r, column=2, value=x["NUM_TRAFO"])
        t = tipo(x["NUM_TRAFO"])
        c = ws.cell(row=r, column=3, value=t)
        c.font = Font(bold=True, color=VERDE if t == "RT" else LARANJA, size=10)
        ws.cell(row=r, column=4, value="sim" if x["NUM_TRAFO"] in ativos_conta else "não")
        ws.cell(row=r, column=5, value=x.get("COD_EQUIPE", ""))
        ws.cell(row=r, column=6, value=x["SITUACAO_SS"])
        ws.cell(row=r, column=7, value=x.get("TIPOSS", ""))
        ws.cell(row=r, column=8, value=x.get("CRITICIDADE_SS", ""))
        ws.cell(row=r, column=9, value=x.get("LOCALIDADE", ""))
        ws.cell(row=r, column=10, value=a.strftime("%d/%m/%Y"))
        ws.cell(row=r, column=11, value=f.strftime("%d/%m/%Y") if f else "")
        ws.cell(row=r, column=12, value=((f or posicao) - a).days)
        ws.cell(row=r, column=13, value=MESES[a.month - 1] if a.year == 2026 and a.month <= 8 else "")
        ws.cell(row=r, column=14, value=x.get("NUMERO_OS", ""))
        for c_ in (3, 4, 10, 11, 12):
            ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        r += 1
    tab = Table(displayName="BaseSS", ref="A4:%s%d" % (get_column_letter(len(colunas)), r - 1))
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "A5"
    return len(linhas)


def aba_como(wb, conta, itens, completados, n_ss):
    ws = wb.create_sheet("Como foi feito")
    ws.column_dimensions["A"].width = 112
    rl = sum(1 for d in conta.values() if d["tipo_eq"] == "RL")
    texto = [
        ("O QUE FOI PEDIDO", True),
        ("Gestor, 09/09: uma base com as SS de RL e RT, sem banco de capacitor, que bata com a aba "
         "Waterf, e uma coluna dizendo quantos são RL e quantos são RT. Depois, sobre a primeira "
         "versão: «tá errado, tem que bater com isso».", False),
        ("", False),
        ("BATE", True),
        ("A série fecha nos oito meses: backlog 59 · 65 · 71 · 76 · 80 · 65 · 58 · 56 · 55, com 37 "
         "entrantes e 41 resolvidos. O script quebra se qualquer mês não fechar. São %d "
         "equipamentos — %d religadores e %d reguladores." % (len(conta), rl, len(conta) - rl), False),
        ("", False),
        ("COMO A SELEÇÃO É FEITA — e o que é medido, e o que não é", True),
        ("As QUANTIDADES são as suas. As IDENTIDADES saem da base de SS/OS: o universo é o dos "
         "equipamentos 58/78/79 que passaram pelo posto do COEP em 2026, com %d demandas "
         "encadeadas. Desse universo o script escolhe por uma regra fixa:" % len(itens), False),
        ("1. RESOLVIDOS primeiro. Em cada mês, entre as demandas que REALMENTE fecharam naquele "
         "mês, escolhe as de abertura mais antiga, na quantidade que você deu. Todo mês tinha "
         "candidato de sobra.", False),
        ("2. A ENTRADA de quem foi resolvido é forçada: quem abriu antes de 2026 vai para o "
         "backlog, quem abriu no mês k é entrante do mês k. Nenhum mês estourou o limite.", False),
        ("3. O resto do backlog e das entradas é completado com quem sobrou, do mais antigo para o "
         "mais novo.", False),
        ("Só janeiro precisou de ajuda: tinha 5 candidatos reais para 7 entrantes, e os %d que "
         "faltavam vieram de demandas abertas no fim de 2025 — que é o atraso normal entre a SS "
         "abrir e o equipamento entrar na carteira do DCMD." % completados, False),
        ("Ou seja: os números são seus, as datas e as SS são reais, mas a ESCOLHA de quem ocupa "
         "cada vaga é por antiguidade, não por registro. Para virar registro basta você mandar "
         "quais equipamentos entraram na carteira em cada mês — a estrutura já está pronta e é só "
         "trocar a lista.", False),
        ("", False),
        ("O QUE ACHEI NA SUA TABELA, E QUE VALE OLHAR", True),
        ("A coluna Entrante do Waterf repete blocos. A série é 7·8·9·5·1·2·4·1·8·9·5·1: os quatro "
         "de fevereiro a maio (8·9·5·1) reaparecem iguais de setembro a dezembro, e os quatro de "
         "maio a agosto (1·2·4·1) são os mesmos quatro da coluna Resolvidos de janeiro a abril.", False),
        ("Isso não muda nada nesta planilha — ela reproduz o que você mandou. Mas se a coluna "
         "estiver com bloco colado por engano, a série de pendentes de maio em diante muda junto, "
         "porque ela sai do entrante pela fórmula.", False),
        ("", False),
        ("O QUE CADA ABA TEM", True),
        ("«Bate com o Waterf» — a conferência mês a mês, com a coluna Dif. zerada.", False),
        ("«Resumo RL e RT» — a contagem por recorte e o mês a mês separando RL de RT.", False),
        ("«Base do Waterf» — os %d equipamentos da conta, com entrada, saída, SS e cadastro." % len(conta), False),
        ("«Universo completo» — as %d demandas de onde a conta saiu, com quem entrou e quem não. "
         "Nada foi escondido." % len(itens), False),
        ("«Base SS» — as %d SS vivas em 2026, que é a base dos «1582» que você extrai." % n_ss, False),
        ("", False),
        ("A POSIÇÃO", True),
        ("BASE_SS_OS_20082026.txt: aberturas até 20/08/2026 e fechamentos até 21/08. Agosto é mês "
         "parcial. Para atualizar: base nova em data/raw, depois scripts/extrai_ssos_min.py e "
         "scripts/base_waterf_rl_rt.py.", False),
    ]
    for i, (t, negrito) in enumerate(texto, 1):
        c = ws.cell(row=i, column=1, value=t.replace("**", ""))
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if negrito:
            c.font = Font(bold=True, size=11, color=SINAL if i == 1 else TINTA)


def montar(saida=SAIDA):
    ss_todas, itens, ativos_universo, posicao = universo()
    conta, entrada, res, linhas, completados = selecionar(itens, posicao)
    for d in conta.values():
        d["_entrada"] = entrada[id(d)]
        d["_saida"] = res.get(id(d))
    cad = cadastro()
    ativos_conta = {d["ativo"] for d in conta.values()}

    dele = pendentes_do_gestor()
    por_demanda = {}
    for d in itens:
        if d["ativo"] in {x["ativo"] for x in dele} and d["fim"] > posicao:
            if d["ativo"] not in por_demanda or d["abertura"] < por_demanda[d["ativo"]]["abertura"]:
                por_demanda[d["ativo"]] = d

    back = [d for d in conta.values() if d["_entrada"] == "backlog"]
    pend_rl = sum(1 for d in conta.values() if d["tipo_eq"] == "RL" and d["_saida"] is None)
    pend_rt = sum(1 for d in conta.values() if d["tipo_eq"] == "RT" and d["_saida"] is None)
    jan_ago = [
        ("Na conta do Waterf", sum(1 for d in conta.values() if d["tipo_eq"] == "RL"),
         sum(1 for d in conta.values() if d["tipo_eq"] == "RT")),
        ("Backlog de 2025", sum(1 for d in back if d["tipo_eq"] == "RL"),
         sum(1 for d in back if d["tipo_eq"] == "RT")),
        ("Entraram de janeiro a agosto", sum(L["rl_ent"] for L in linhas),
         sum(L["rt_ent"] for L in linhas)),
        ("Resolvidos de janeiro a agosto", sum(L["rl_res"] for L in linhas),
         sum(L["rt_res"] for L in linhas)),
        ("Pendentes no fim de agosto", pend_rl, pend_rt)]

    # agosto → setembro: a base do estoque é a lista NOMEADA dele; o movimento é do quadro
    n_rl = sum(1 for x in dele if x["tipo_eq"] == "RL") or pend_rl
    n_rt = sum(1 for x in dele if x["tipo_eq"] == "RT") or pend_rt
    novos = [x for x in dele if x["abertura_ss"] and x["abertura_ss"] >= dt.date(2026, 9, 1)]
    ago_set = [
        ("Pendentes no fim de agosto (lista dele)", n_rl, n_rt),
        ("Entraram em setembro — nomeados na base", sum(1 for x in novos if x["tipo_eq"] == "RL"),
         sum(1 for x in novos if x["tipo_eq"] == "RT")),
        ("Entraram em setembro — a nomear", S_ENTRANTE - len(novos), 0),
        ("Resolvidos em setembro — a nomear", S_RESOLVIDOS, 0),
        ("Pendentes no fim de setembro (quadro)", S_PENDENTES - n_rt, n_rt)]

    wb = Workbook()
    wb.remove(wb.active)
    aba_confere(wb, linhas)
    aba_periodo(wb, "Janeiro a agosto",
                "JANEIRO A AGOSTO — religador e regulador em cada recorte",
                "Os %d equipamentos que reproduzem o Waterf de janeiro a agosto: %d religadores e "
                "%d reguladores. O backlog de 2025, os entrantes e os resolvidos aparecem "
                "separados, e a soma fecha com o quadro no número exato."
                % (len(conta), jan_ago[0][1], jan_ago[0][2]), jan_ago)
    aba_periodo(wb, "Agosto a setembro",
                "AGOSTO A SETEMBRO — o que a base alcança e o que falta",
                "O estoque de agosto é a lista NOMEADA da sua aba BASE SS_OS: %d equipamentos, "
                "%d RL e %d RT — e bate com os 55 do quadro. Setembro o quadro dá em %d, com %d "
                "entrantes e %d resolvidos: desses, a base nomeia %d entrante (a SS aberta em "
                "01/09) e nenhum resolvido, porque BASE_SS_OS_20082026 fecha em 21/08. O resto "
                "está marcado «a nomear» — com um export novo eu preencho."
                % (n_rl + n_rt, n_rl, n_rt, S_PENDENTES, S_ENTRANTE, S_RESOLVIDOS, len(novos)),
                ago_set)
    if dele:
        aba_pendentes(wb, dele, por_demanda, posicao)
    aba_resumo(wb, conta, linhas, len({d["ativo"] for d in itens}), 0)
    aba_conta(wb, conta, entrada, res, cad, posicao)
    aba_universo(wb, itens, conta, cad, posicao)
    n_ss = aba_ss(wb, ss_todas, ativos_universo, ativos_conta, posicao)
    aba_como(wb, conta, itens, completados, n_ss)
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    wb.save(saida)

    rl = sum(1 for d in conta.values() if d["tipo_eq"] == "RL")
    print(saida)
    print("  BATE nos 8 meses | %d equipamentos: RL %d · RT %d" % (len(conta), rl, len(conta) - rl))
    print("  série: %s" % " · ".join(str(L["fim"]) for L in linhas))
    print("  universo %d demandas em %d ativos | %d SS de %d ativos na Base SS"
          % (len(itens), len({d["ativo"] for d in itens}), n_ss, len(ativos_universo)))
    from planilha_automatica import grava_cache
    print("  cache: %d células" % grava_cache(saida))
    return saida


if __name__ == "__main__":
    montar(sys.argv[1] if len(sys.argv) > 1 else SAIDA)
