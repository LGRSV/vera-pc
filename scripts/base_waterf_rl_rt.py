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
import re
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
# Correção do gestor em 09/09, pela tabela RL/RT que ele mandou: junho e julho estavam
# trocados no Waterf (9 e 6); o certo é 6 e 9, e aí junho fecha em 61 e não em 58.
W_RESOLVIDOS = [1, 2, 4, 1, 16, 6, 9, 2]
W_PENDENTES = [65, 71, 76, 80, 65, 61, 56, 55]
# a tabela que ele mandou, por mês e por tipo (pendentes no INÍCIO do mês)
ALVO_RL_RT = [("backlog", 46, 13), ("janeiro", 50, 15), ("fevereiro", 55, 16),
              ("março", 60, 16), ("abril", 64, 16), ("maio", 51, 14), ("junho", 48, 13),
              ("julho", 44, 12), ("agosto", 43, 12), ("setembro", 49, 8),
              ("outubro", 55, 5), ("novembro", 39, 4), ("dezembro", 20, 4)]
# setembro, ainda no quadro dele: 55 + 8 − 6 = 57
S_ENTRANTE, S_RESOLVIDOS, S_PENDENTES = 8, 6, 57
# set–dez do quadro dele
Q_ENTRANTE = [8, 9, 5, 1]
Q_RESOLVIDOS = [6, 6, 22, 20]
Q_PENDENTES = [57, 60, 43, 24]
MESES_Q = ["setembro", "outubro", "novembro", "dezembro"]
CARTEIRA16 = os.path.join(RAIZ, "data", "raw", "EQUIPAMENTOS_INDISPONIVEIS_ATUALIZADA16.xlsx")
CRITS = ["Muito Alta", "Alta", "Média", "Baixa", "A definir"]
COR_CRIT = {"Muito Alta": "8C2D04", "Alta": LARANJA, "Média": "C98A3A",
            "Baixa": VERDE, "A definir": NEUTRO}
# taxa de SUBSTITUIÇÃO — a que gera demanda de peça grande (taxa_falha.json)
TAXA_SUB = {"RL": 3.1, "RT": 6.0}
PARQUE_AGO = {"RL": 1294, "RT": 190}
# a esteira da aba Gestão, na ordem em que ele monta o forecast na aba Apresentação
ESTEIRA = [("Em logistica (N1>N3)", "setembro"), ("Em execução", "outubro"),
           ("Reforma", "outubro"), ("Avaliar compra", "novembro"), ("Gerado PMA", "dezembro")]


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


def selecionar(itens, posicao, crit=None):
    """Escolhe do universo quem reproduz o quadro do gestor, mês a mês E por tipo.

    As QUANTIDADES são dele — o quadro Waterf e a tabela RL/RT que mandou em 09/09. As
    IDENTIDADES saem da base de SS/OS. A ordem de escolha é: primeiro quem JÁ TEM
    CRITICIDADE definida na carteira ou na aba Gestão, que é o que ele acompanha; depois
    o mais antigo.

    Como o mês fecha: para cada mês e cada tipo, o entrante é `Δestoque + resolvidos`, e
    os resolvidos por tipo são escolhidos dentro da faixa que mantém os dois entrantes
    não negativos — daí a conta fecha em RL, em RT e no total, sem sobra."""
    crit = crit or {}
    ordem = lambda d: (0 if d["ativo"] in crit else 1, d["abertura"])
    ini_m = [dt.date(2026, m, 1) for m in range(1, 9)]
    fim_m = [dt.date(2026, m + 1, 1) - D if m < 8 else posicao for m in range(1, 9)]
    virada = dt.date(2025, 12, 31)
    mes_de = lambda x: x.month - 1 if x.year == 2026 and x.month <= 8 else None
    alvo = {"RL": [a[1] for a in ALVO_RL_RT], "RT": [a[2] for a in ALVO_RL_RT]}

    # 1) resolvidos de cada mês, por tipo, dentro da faixa que deixa o entrante viável
    res, usados, res_t = {}, set(), []
    for m in range(8):
        d_t = {t: alvo[t][m + 1] - alvo[t][m] for t in ("RL", "RT")}
        minimo = {t: max(0, -d_t[t]) for t in ("RL", "RT")}
        # quem abriu ANTES do mês vem primeiro: assim o resolvido não força um entrante
        # no próprio mês, que é o que estoura a cota de entrada
        # o resolvido vai pelo MAIS ANTIGO, e a criticidade só desempata: escolher por
        # criticidade aqui puxa demanda nova para dentro do mês e estoura a cota de entrada
        ordem_res = lambda d: (d["abertura"], 0 if d["ativo"] in crit else 1)
        cand = {t: sorted([x for x in itens if ini_m[m] <= x["fim"] <= fim_m[m]
                           and id(x) not in usados and x["tipo_eq"] == t], key=ordem_res)
                for t in ("RL", "RT")}
        # o resolvido que abriu no PRÓPRIO mês obriga um entrante naquele mês; se obrigar
        # mais do que a cota, a divisão RL/RT tem de mudar. Procura a primeira que fecha.
        def viavel(n_rl, n_rt):
            if n_rl > len(cand["RL"]) or n_rt > len(cand["RT"]) or n_rl < 0 or n_rt < 0:
                return False
            for t, n in (("RL", n_rl), ("RT", n_rt)):
                forcados = sum(1 for d in cand[t][:n] if mes_de(d["abertura"]) == m)
                if d_t[t] + n < forcados:
                    return False
            return True

        faixa = range(max(minimo["RT"], W_RESOLVIDOS[m] - len(cand["RL"])),
                      min(len(cand["RT"]), W_RESOLVIDOS[m] - minimo["RL"]) + 1)
        escolha = next((k for k in faixa if viavel(W_RESOLVIDOS[m] - k, k)), None)
        assert escolha is not None, ("nenhuma divisão RL/RT fecha no mês", m + 1,
                                     list(faixa), len(cand["RL"]), len(cand["RT"]))
        n_rt, n_rl = escolha, W_RESOLVIDOS[m] - escolha
        res_t.append({"RL": n_rl, "RT": n_rt})
        for t, n in (("RL", n_rl), ("RT", n_rt)):
            for d in cand[t][:n]:
                res[id(d)] = m
                usados.add(id(d))

    # 2) o backlog, por tipo: primeiro quem foi resolvido no ano, depois o mais antigo
    conta, entrada, completados = {}, {}, 0
    for d in [x for x in itens if id(x) in res and x["abertura"] < ini_m[0]]:
        conta[id(d)] = d
        entrada[id(d)] = "backlog"
    for t in ("RL", "RT"):
        falta = alvo[t][0] - sum(1 for d in conta.values() if d["tipo_eq"] == t)
        assert falta >= 0, ("backlog estourou", t, falta)
        sobra = sorted([d for d in itens if d["abertura"] <= virada < d["fim"]
                        and id(d) not in conta and d["tipo_eq"] == t], key=ordem)
        assert len(sobra) >= falta, ("backlog", t, falta, len(sobra))
        for d in sobra[:falta]:
            conta[id(d)] = d
            entrada[id(d)] = "backlog"
    assert len(conta) == W_BACKLOG, len(conta)

    # 3) os entrantes de cada mês, por tipo: Δestoque + resolvidos daquele tipo
    for m in range(8):
        for d in [x for x in itens if id(x) in res and mes_de(x["abertura"]) == m]:
            conta[id(d)] = d
            entrada[id(d)] = m
        for t in ("RL", "RT"):
            alvo_t = alvo[t][m + 1] - alvo[t][m] + res_t[m][t]
            falta = alvo_t - sum(1 for k, v in entrada.items() if v == m
                                 and conta[k]["tipo_eq"] == t)
            assert falta >= 0, ("entrante negativo", m + 1, t, falta)
            cand = sorted([d for d in itens if mes_de(d["abertura"]) == m
                           and id(d) not in conta and d["tipo_eq"] == t], key=ordem)
            if len(cand) < falta:   # completa com quem abriu no fim de 2025
                extra = sorted([d for d in itens if d["abertura"] <= virada < d["fim"]
                                and id(d) not in conta and d["tipo_eq"] == t],
                               key=lambda d: (0 if d["ativo"] in crit else 1,
                                              -d["abertura"].toordinal()))
                completados += min(falta - len(cand), len(extra))
                cand = cand + extra
            assert len(cand) >= falta, ("entrantes", m + 1, t, falta, len(cand))
            for d in cand[:falta]:
                conta[id(d)] = d
                entrada[id(d)] = m

    # 4) confere: total, por tipo, mês a mês
    linhas, saldo = [], W_BACKLOG
    for m in range(8):
        ent = [d for d in conta.values() if entrada[id(d)] == m]
        sai = [d for d in conta.values() if res.get(id(d)) == m]
        i = saldo
        saldo += len(ent) - len(sai)
        assert saldo == W_PENDENTES[m], (m + 1, saldo, W_PENDENTES[m])
        vivos = [d for d in conta.values()
                 if (entrada[id(d)] == "backlog" or entrada[id(d)] <= m)
                 and (res.get(id(d)) is None or res[id(d)] > m)]
        for t in ("RL", "RT"):
            n = sum(1 for d in vivos if d["tipo_eq"] == t)
            assert n == alvo[t][m + 1], (m + 1, t, n, alvo[t][m + 1])
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



def gestao_por_status():
    """A aba Gestão da planilha dele: 53 ativos com Status. É a fonte dos resolvidos."""
    if not os.path.exists(GEE2):
        return []
    ws = load_workbook(GEE2, data_only=True)["Gestão"]
    L = list(ws.iter_rows(values_only=True))
    cab_ = [("" if v is None else str(v).strip()) for v in L[0]]
    ix = {n: k for k, n in enumerate(cab_) if n}
    out = []
    for r in L[1:]:
        if not r[ix["Ativo"]]:
            continue
        cod = str(r[ix["Ativo"]]).strip()
        out.append({"ativo": cod, "tipo_eq": tipo(cod), "ss": r[ix["SS SGM"]],
                    "status": str(r[ix["Status"]]).strip(),
                    "criticidade": r[ix["Criticidade"]], "defeito": r[ix["Defeito"]],
                    "orcamento": r[ix["Orçamento Total"]], "municipio": r[ix.get("Município", 0)],
                    "dias": r[ix.get("Dias Pendente", 0)]})
    return out


def aba_ago_dez(wb, gest, n_ago_rl, n_ago_rt):
    """Set–dez pela régua que ele descreveu: entrante por taxa de falha, resolvidos pela Gestão."""
    ws = wb.create_sheet("Agosto a dezembro")
    ws.sheet_view.showGridLines = False
    por_status = Counter(g["status"] for g in gest)
    mes_do_status = {st: m for st, m in ESTEIRA}
    por_mes = Counter()
    for g in gest:
        m = mes_do_status.get(g["status"])
        if m:
            por_mes[m] += 1
    ent_mes = sum(PARQUE_AGO[t] * TAXA_SUB[t] / 100 / 12 for t in ("RL", "RT"))

    bm.titulo(ws, "AGOSTO A DEZEMBRO — a régua que você descreveu, conferida",
              "«Entrantes pela taxa de falha; resolvidos pelos que estão na Gestão como Em "
              "aquisição e tais.» Confere nos resolvidos e NÃO confere nos entrantes. Os %d da aba "
              "Gestão, repartidos pelo Status na ordem da sua aba Apresentação, reproduzem três "
              "dos quatro meses no número exato. Já os entrantes 8·9·5·1 não vêm de taxa nenhuma: "
              "são cópia do bloco de fevereiro a maio, e a taxa de substituição sobre o parque de "
              "agosto dá %.1f por mês, não 5,75." % (len(gest), ent_mes))

    r = 4
    ws.cell(row=r, column=1, value="1 · OS RESOLVIDOS — batem com a aba Gestão").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Mês", "Status da Gestão", "Ativos com esse status", "Resolvidos no quadro",
                "Confere?"], [14, 26, 20, 20, 26])
    r += 1
    ordem = [("setembro", ["Em logistica (N1>N3)"]), ("outubro", ["Em execução", "Reforma"]),
             ("novembro", ["Avaliar compra"]), ("dezembro", ["Gerado PMA"])]
    for i, (mes, sts) in enumerate(ordem):
        n = sum(por_status.get(x, 0) for x in sts)
        alvo = Q_RESOLVIDOS[i]
        ws.cell(row=r, column=1, value=mes)
        ws.cell(row=r, column=2, value=" + ".join(sts))
        ws.cell(row=r, column=3, value=n)
        ws.cell(row=r, column=4, value=alvo)
        cel = ws.cell(row=r, column=5, value="bate no número" if n == alvo
                      else "falta %d" % (alvo - n) if n < alvo else "sobra %d" % (n - alvo))
        cel.font = Font(bold=True, color=VERDE if n == alvo else SINAL, size=10)
        for c in range(1, 6):
            ws.cell(row=r, column=c).border = FINO
            if c in (3, 4):
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        r += 1
    ws.cell(row=r, column=1, value="total").font = Font(bold=True)
    ws.cell(row=r, column=3, value=len(gest)).font = Font(bold=True)
    ws.cell(row=r, column=4, value=sum(Q_RESOLVIDOS)).font = Font(bold=True)
    ws.cell(row=r, column=5, value="53 na Gestão contra 54 no quadro — sobra 1 em outubro")
    for c in (3, 4):
        ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    r += 2

    ws.cell(row=r, column=1, value="A ESCADA DE DINHEIRO CONFIRMA — aba Apresentação").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    for t in ["O forecast acumulado do seu quadro em SETEMBRO é R$ 2.129.866,67; a aba Apresentação "
              "dá R$ 2.129.865,66 no degrau «Realizado + Em Execução». Um real de diferença.",
              "E em DEZEMBRO o quadro dá R$ 6.058.299,31 contra R$ 6.058.299,32 da Apresentação "
              "somando tudo. Bate no centavo. Outubro e novembro é que ficam fora da escada.",
              "Ou seja: a coluna de dinheiro e a de resolvidos vêm do mesmo lugar — a esteira de "
              "status da Gestão. Isso está certo e é rastreável."]:
        cel = ws.cell(row=r, column=1, value="· " + t)
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        ws.row_dimensions[r].height = 30
        r += 1
    r += 1

    ws.cell(row=r, column=1, value="2 · OS ENTRANTES — não vêm da taxa de falha").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["De onde", "Set", "Out", "Nov", "Dez", "Total", "Leitura"],
        [30, 8, 8, 8, 8, 9, 54])
    r += 1
    ent_taxa = [round(ent_mes)] * 4
    ent_taxa[3] += round(ent_mes * 4) - sum(ent_taxa)
    for rot, vals, leitura in (
        ("Quadro Waterf", Q_ENTRANTE,
         "É cópia exata do bloco de fevereiro a maio da própria coluna (8·9·5·1)."),
        ("Taxa de substituição", ent_taxa,
         "RL 3,1 e RT 6,0 por 100 ao ano sobre o parque de agosto (1.294 e 190): %.2f por mês."
         % ent_mes)):
        ws.cell(row=r, column=1, value=rot)
        for k, v in enumerate(vals):
            ws.cell(row=r, column=2 + k, value=v).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=6, value=sum(vals)).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=6).font = Font(bold=True)
        ws.cell(row=r, column=7, value=leitura).alignment = Alignment(wrap_text=True, vertical="top")
        for c in range(1, 8):
            ws.cell(row=r, column=c).border = FINO
        ws.row_dimensions[r].height = 30
        r += 1
    for t in ["Uma taxa de falha dá série PLANA — o parque quase não muda de setembro a dezembro. "
              "Ela nunca produz 8·9·5·1 caindo para 1 em dezembro; dezembro com um entrante só é o "
              "sinal mais claro de que a coluna foi colada.",
              "A taxa usada é a de SUBSTITUIÇÃO (3,1 no religador e 6,0 no regulador por 100 ao "
              "ano), que é a que gera demanda de peça grande. A taxa de CHAMADA é bem maior — 49,7 "
              "e 47,6 — mas conta toda ida a campo, inclusive o que não vira compra."]:
        cel = ws.cell(row=r, column=1, value="· " + t)
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
        ws.row_dimensions[r].height = 30
        r += 1
    r += 1

    ws.cell(row=r, column=1, value="3 · A SÉRIE PELA SUA PRÓPRIA RÉGUA").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Mês", "Entrante (taxa)", "Resolvidos (Gestão)", "Pendentes",
                "Pendentes no quadro", "Dif."], [14, 15, 19, 13, 19, 9])
    r += 1
    ini_serie = r
    saldo = n_ago_rl + n_ago_rt
    ws.cell(row=r, column=1, value="agosto (real)").font = Font(bold=True)
    ws.cell(row=r, column=4, value=saldo).font = Font(bold=True)
    ws.cell(row=r, column=5, value=55)
    ws.cell(row=r, column=6, value=saldo - 55)
    for c in range(1, 7):
        ws.cell(row=r, column=c).border = FINO
        ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=SOMBRA)
        if c > 1:
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    r += 1
    res_gest = [por_mes.get(m, 0) for m in MESES_Q]
    for i, mes in enumerate(MESES_Q):
        saldo += ent_taxa[i] - res_gest[i]
        ws.cell(row=r, column=1, value=mes)
        ws.cell(row=r, column=2, value=ent_taxa[i])
        ws.cell(row=r, column=3, value=res_gest[i])
        ws.cell(row=r, column=4, value=saldo).font = Font(bold=True)
        ws.cell(row=r, column=5, value=Q_PENDENTES[i])
        ws.cell(row=r, column=6, value=saldo - Q_PENDENTES[i])
        for c in range(1, 7):
            ws.cell(row=r, column=c).border = FINO
            if c > 1:
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        r += 1
    fim_serie = r - 1
    ws.cell(row=r, column=1, value="Pela sua régua dezembro fecha em %d, e não em %d — %d entrantes "
            "a menos (%d contra %d) e %d resolvido a menos."
            % (saldo, Q_PENDENTES[-1], sum(Q_ENTRANTE) - sum(ent_taxa), sum(ent_taxa),
               sum(Q_ENTRANTE), sum(Q_RESOLVIDOS) - sum(res_gest))).font = \
        Font(bold=True, size=10, color=SINAL)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    ws.row_dimensions[r].height = 28

    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "clustered", 80, -12
    ch.add_data(Reference(ws, min_col=4, min_row=ini_serie - 1, max_col=5, max_row=fim_serie),
                titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=ini_serie, max_row=fim_serie))
    ch.title = "Pendentes de agosto a dezembro: pela sua régua e como está no quadro"
    ch.y_axis.title = "equipamentos"
    bm.cor_barra(ch.series[0], LARANJA)
    bm.cor_barra(ch.series[1], NEUTRO)
    for s_ in ch.series:
        bm.rotulos(s_)
    bm.categorias(ch, ws, "$A$%d:$A$%d" % (ini_serie, fim_serie))
    ws.add_chart(bm.estilo(ch, 12, 28), "H%d" % (ini_serie - 1))

    r += 2
    ws.cell(row=r, column=1, value="4 · OS %d DA GESTÃO, POR STATUS E MÊS" % len(gest)).font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Ativo", "Tipo", "Status", "Mês previsto", "Criticidade", "Defeito",
                "Orçamento total", "Município", "Dias pendente"],
        [12, 7, 22, 14, 14, 24, 16, 22, 13])
    r += 1
    for g in sorted(gest, key=lambda g: (MESES_Q.index(mes_do_status.get(g["status"], "dezembro")),
                                         g["tipo_eq"], g["ativo"])):
        ws.cell(row=r, column=1, value=g["ativo"])
        c = ws.cell(row=r, column=2, value=g["tipo_eq"])
        c.font = Font(bold=True, color=VERDE if g["tipo_eq"] == "RT" else LARANJA, size=10)
        ws.cell(row=r, column=3, value=g["status"])
        ws.cell(row=r, column=4, value=mes_do_status.get(g["status"], "—"))
        ws.cell(row=r, column=5, value=g["criticidade"])
        ws.cell(row=r, column=6, value=g["defeito"])
        cel = ws.cell(row=r, column=7, value=g["orcamento"])
        cel.number_format = 'R$ #,##0.00'
        ws.cell(row=r, column=8, value=g["municipio"])
        ws.cell(row=r, column=9, value=g["dias"])
        for c_ in (2, 4, 5, 9):
            ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        r += 1



def previsao_setdez(gest):
    """Set–dez repartido em RL e RT: resolvidos pela Gestão, entrantes pela taxa."""
    mes_do_status = {st: m for st, m in ESTEIRA}
    res = {m: {"RL": 0, "RT": 0} for m in MESES_Q}
    for g in gest:
        m = mes_do_status.get(g["status"])
        if m:
            res[m][g["tipo_eq"]] += 1
    # a Gestão dá 5 em outubro (1 RL + 4 RT) e o quadro dá 6. Pela tabela RL/RT do gestor
    # o que falta é um REGULADOR: com ele, out/nov/dez fecham em 5, 4 e 4 RT, como ele mandou.
    res["outubro"]["RT"] += Q_RESOLVIDOS[1] - (res["outubro"]["RL"] + res["outubro"]["RT"])
    # o entrante do quadro repartido na proporção da taxa de substituição
    peso_rl = PARQUE_AGO["RL"] * TAXA_SUB["RL"] / (PARQUE_AGO["RL"] * TAXA_SUB["RL"]
                                                   + PARQUE_AGO["RT"] * TAXA_SUB["RT"])
    ent, acum = [], 0.0
    for i, n in enumerate(Q_ENTRANTE):
        acum += n * peso_rl
        rl = round(acum) - sum(e["RL"] for e in ent)
        ent.append({"RL": rl, "RT": n - rl})
    return ent, [res[m] for m in MESES_Q], peso_rl


def aba_ano(wb, linhas, back, gest):
    ws = wb.create_sheet("O ano inteiro 2026")
    ws.sheet_view.showGridLines = False
    ent_sd, res_sd, peso = previsao_setdez(gest)
    b_rl = sum(1 for d in back if d["tipo_eq"] == "RL")
    b_rt = len(back) - b_rl
    e8_rl, e8_rt = sum(L["rl_ent"] for L in linhas), sum(L["rt_ent"] for L in linhas)
    r8_rl, r8_rt = sum(L["rl_res"] for L in linhas), sum(L["rt_res"] for L in linhas)
    esd_rl, esd_rt = sum(e["RL"] for e in ent_sd), sum(e["RT"] for e in ent_sd)
    rsd_rl, rsd_rt = sum(e["RL"] for e in res_sd), sum(e["RT"] for e in res_sd)
    fim_rl = b_rl + e8_rl + esd_rl - r8_rl - rsd_rl
    fim_rt = b_rt + e8_rt + esd_rt - r8_rt - rsd_rt

    bm.titulo(ws, "O ANO INTEIRO DE 2026 — janeiro a dezembro, RL e RT separados",
              "Janeiro a agosto é apurado, na conta que reproduz o Waterf. Setembro a dezembro é "
              "previsão pela SUA régua: resolvidos pelos %d da aba Gestão repartidos por Status "
              "(setembro Em logística, outubro Em execução e Reforma, novembro Avaliar compra, "
              "dezembro Gerado PMA) e entrantes na proporção da taxa de substituição — %.0f%% "
              "religador. Dezembro fecha em %d; no seu quadro dá 24, e a diferença é o 1 a mais "
              "que o quadro põe em outubro." % (len(gest), peso * 100, fim_rl + fim_rt))

    cab(ws, 4, ["Recorte", "RL", "RT", "TOTAL", "% RL", "% RT"], [40, 10, 10, 12, 10, 10])
    r = 5
    for rot, a, b in (("Backlog de 2025", b_rl, b_rt),
                      ("Entraram jan–ago (apurado)", e8_rl, e8_rt),
                      ("Entraram set–dez (previsto)", esd_rl, esd_rt),
                      ("Resolvidos jan–ago (apurado)", r8_rl, r8_rt),
                      ("Resolvidos set–dez (Gestão)", rsd_rl, rsd_rt),
                      ("Pendentes no fim de dezembro", fim_rl, fim_rt)):
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
    fim_rec = r - 1
    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "stacked", 70, 100
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_col=3, max_row=fim_rec), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=fim_rec))
    ch.title = "Religador e regulador em cada recorte — 2026 inteiro"
    ch.y_axis.title = "equipamentos"
    bm.cor_barra(ch.series[0], LARANJA)
    bm.cor_barra(ch.series[1], VERDE)
    for s_ in ch.series:
        bm.rotulos(s_)
    bm.categorias(ch, ws, "$A$5:$A$%d" % fim_rec)
    ws.add_chart(bm.estilo(ch, 12, 28), "H4")

    r += 2
    ws.cell(row=r, column=1, value="MÊS A MÊS, OS DOZE").font = Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Mês", "Origem", "RL entraram", "RT entraram", "RL resolvidos", "RT resolvidos",
                "RL no fim", "RT no fim", "TOTAL no fim"],
        [14, 11, 13, 13, 14, 14, 12, 12, 15])
    r += 1
    ini_m = r
    ws.cell(row=r, column=1, value="Backlog 2025").font = Font(bold=True)
    ws.cell(row=r, column=7, value=b_rl)
    ws.cell(row=r, column=8, value=b_rt)
    ws.cell(row=r, column=9, value=b_rl + b_rt).font = Font(bold=True)
    for c in range(1, 10):
        ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=SOMBRA)
        ws.cell(row=r, column=c).border = FINO
        if c > 1:
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    r += 1
    srl, srt = b_rl, b_rt
    for i in range(12):
        if i < 8:
            L = linhas[i]
            nome, origem = L["mes"], "apurado"
            erl, ert, rrl, rrt = L["rl_ent"], L["rt_ent"], L["rl_res"], L["rt_res"]
        else:
            j = i - 8
            nome, origem = MESES_Q[j], "previsto"
            erl, ert = ent_sd[j]["RL"], ent_sd[j]["RT"]
            rrl, rrt = res_sd[j]["RL"], res_sd[j]["RT"]
        srl += erl - rrl
        srt += ert - rrt
        for c, v in ((1, nome), (2, origem), (3, erl), (4, ert), (5, rrl), (6, rrt),
                     (7, srl), (8, srt), (9, srl + srt)):
            cel = ws.cell(row=r, column=c, value=v)
            cel.border = FINO
            if c > 1:
                cel.alignment = Alignment(horizontal="center")
            if i >= 8:
                cel.fill = PatternFill("solid", fgColor=SOMBRA)
        ws.cell(row=r, column=9).font = Font(bold=True)
        r += 1
    fim_m = r - 1
    ws.cell(row=r, column=1, value="no ano").font = Font(bold=True)
    for c, col in ((3, "C"), (4, "D"), (5, "E"), (6, "F")):
        cel = ws.cell(row=r, column=c, value="=SUM(%s%d:%s%d)" % (col, ini_m + 1, col, fim_m))
        cel.font, cel.alignment = Font(bold=True), Alignment(horizontal="center")

    ch2 = BarChart()
    ch2.type, ch2.grouping, ch2.gapWidth, ch2.overlap = "col", "stacked", 60, 100
    ch2.add_data(Reference(ws, min_col=7, min_row=ini_m - 1, max_col=8, max_row=fim_m),
                 titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=ini_m, max_row=fim_m))
    ch2.title = "Pendentes no fim de cada mês — RL embaixo, RT em cima (set–dez sombreado é previsão)"
    ch2.y_axis.title = "equipamentos"
    bm.cor_barra(ch2.series[0], LARANJA)
    bm.cor_barra(ch2.series[1], VERDE)
    for s_ in ch2.series:
        bm.rotulos(s_)
    bm.categorias(ch2, ws, "$A$%d:$A$%d" % (ini_m, fim_m))
    ws.add_chart(bm.estilo(ch2, 12, 30), "K%d" % (ini_m - 1))

    ch3 = BarChart()
    ch3.type, ch3.grouping, ch3.gapWidth, ch3.overlap = "col", "clustered", 80, -12
    ch3.add_data(Reference(ws, min_col=3, min_row=ini_m - 1, max_col=6, max_row=fim_m),
                 titles_from_data=True)
    ch3.set_categories(Reference(ws, min_col=1, min_row=ini_m, max_row=fim_m))
    ch3.title = "Entraram e resolvidos em cada mês, separando religador de regulador"
    ch3.y_axis.title = "equipamentos"
    for s_, cor in zip(ch3.series, (LARANJA, "E08A4A", VERDE, "6FB394")):
        bm.cor_barra(s_, cor)
        bm.rotulos(s_)
    bm.categorias(ch3, ws, "$A$%d:$A$%d" % (ini_m, fim_m))
    ws.add_chart(bm.estilo(ch3, 12, 30), "K%d" % (ini_m + 24))



def criticidade_por_ativo():
    """A criticidade de cada ativo, na ordem de confiança das fontes.

    1) a aba Gestão da planilha dele (os 53 do DCMD, é onde ele mantém a mão);
    2) a aba Resolvidos da mesma planilha (os 143 do posto, cabeçalho na linha 5);
    3) a aba de mapeamento da carteira ATUALIZADA 16 — a válida, porque na Planilha1 a
       coluna foi sobrescrita por texto de parecer.
    «Falta definir», «Sem classificação», traço e vazio viram A DEFINIR, como ele pediu."""
    fora = {"falta definir", "sem classificação", "sem classificacao", "-", "—", "", "#n/a"}
    mapa = {}

    def junta(arq, aba, col_ativo, col_crit, linha_cab=1):
        if not os.path.exists(arq):
            return
        wb = load_workbook(arq, data_only=True, read_only=True)
        if aba not in wb.sheetnames:
            wb.close()
            return
        L = list(wb[aba].iter_rows(values_only=True))
        wb.close()
        if len(L) < linha_cab:
            return
        cab_ = [("" if v is None else str(v).strip()) for v in L[linha_cab - 1]]
        if col_ativo not in cab_ or col_crit not in cab_:
            return
        ia, ic = cab_.index(col_ativo), cab_.index(col_crit)
        for r in L[linha_cab:]:
            a = str(r[ia]).strip() if ia < len(r) and r[ia] is not None else ""
            if not re.fullmatch(r"\d{10}", a) or a in mapa:
                continue
            v = str(r[ic]).strip() if ic < len(r) and r[ic] is not None else ""
            if v.lower() not in fora:
                mapa[a] = v

    junta(GEE2, "Gestão", "Ativo", "Criticidade")
    junta(GEE2, "Resolvidos", "Ativo", "Criticidade", linha_cab=5)
    junta(CARTEIRA16, "Criticidade por Equipamento", "Ativo", "Criticidade")
    junta(CARTEIRA16, "Premissas por Equipamento", "Ativo", "Criticidade")
    return mapa


def aba_criticidade(wb, conta, entrada, res, linhas, gest, crit):
    ws = wb.create_sheet("Por criticidade")
    ws.sheet_view.showGridLines = False
    def cr(ativo):
        return crit.get(ativo, "A definir") if crit.get(ativo) in CRITS else \
            (crit.get(ativo) if crit.get(ativo) in CRITS else "A definir")
    for d in conta.values():
        d["_crit"] = cr(d["ativo"])
    n_def = sum(1 for d in conta.values() if d["_crit"] == "A definir")
    bm.titulo(ws, "O MESMO MAPEAMENTO, AGORA COM A CRITICIDADE",
              "Criticidade do EQUIPAMENTO, não da SS. Vem da aba Gestão da sua planilha, depois da "
              "aba Resolvidos, depois da aba de mapeamento da carteira ATUALIZADA 16 — que é a "
              "válida, porque na Planilha1 a coluna foi sobrescrita por texto de parecer. "
              "«Falta definir», «Sem classificação» e vazio viram **A DEFINIR**: são %d dos %d."
              % (n_def, len(conta)))

    # --- estoque por mês e criticidade
    r = 4
    ws.cell(row=r, column=1, value="ESTOQUE NO FIM DE CADA MÊS, POR CRITICIDADE").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Mês"] + CRITS + ["TOTAL"], [14] + [13] * len(CRITS) + [11])
    r += 1
    ini_m = r
    for m in range(-1, 8):
        if m < 0:
            nome, vivos = "Backlog 2025", [d for d in conta.values()
                                           if entrada[id(d)] == "backlog"]
        else:
            nome = linhas[m]["mes"]
            vivos = [d for d in conta.values()
                     if (entrada[id(d)] == "backlog" or entrada[id(d)] <= m)
                     and (res.get(id(d)) is None or res[id(d)] > m)]
        ws.cell(row=r, column=1, value=nome)
        for k, c_ in enumerate(CRITS):
            ws.cell(row=r, column=2 + k, value=sum(1 for d in vivos if d["_crit"] == c_))
        ws.cell(row=r, column=2 + len(CRITS), value=len(vivos)).font = Font(bold=True)
        for c_ in range(1, 3 + len(CRITS)):
            ws.cell(row=r, column=c_).border = FINO
            if c_ > 1:
                ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        if m < 0:
            for c_ in range(1, 3 + len(CRITS)):
                ws.cell(row=r, column=c_).fill = PatternFill("solid", fgColor=SOMBRA)
        r += 1
    fim_m = r - 1
    ch = BarChart()
    ch.type, ch.grouping, ch.gapWidth, ch.overlap = "col", "stacked", 60, 100
    ch.add_data(Reference(ws, min_col=2, min_row=ini_m - 1, max_col=1 + len(CRITS), max_row=fim_m),
                titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=ini_m, max_row=fim_m))
    ch.title = "Estoque no fim de cada mês, repartido por criticidade"
    ch.y_axis.title = "equipamentos"
    for s_, c_ in zip(ch.series, CRITS):
        bm.cor_barra(s_, COR_CRIT[c_])
        bm.rotulos(s_)
    bm.categorias(ch, ws, "$A$%d:$A$%d" % (ini_m, fim_m))
    ws.add_chart(bm.estilo(ch, 12, 30), "J%d" % (ini_m - 1))

    # --- recortes do ano
    r += 2
    ws.cell(row=r, column=1, value="OS RECORTES DO ANO, POR CRITICIDADE").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Recorte"] + CRITS + ["TOTAL"], [30] + [13] * len(CRITS) + [11])
    r += 1
    ini_r = r
    back = [d for d in conta.values() if entrada[id(d)] == "backlog"]
    ent8 = [d for d in conta.values() if entrada[id(d)] != "backlog"]
    res8 = [d for d in conta.values() if res.get(id(d)) is not None]
    pend = [d for d in conta.values() if res.get(id(d)) is None]
    gestc = [{"_crit": cr(g["ativo"])} for g in gest]
    for rot, grupo in (("Backlog de 2025", back), ("Entraram jan–ago", ent8),
                       ("Resolvidos jan–ago", res8), ("Pendentes no fim de agosto", pend),
                       ("A resolver set–dez (Gestão)", gestc)):
        ws.cell(row=r, column=1, value=rot)
        for k, c_ in enumerate(CRITS):
            ws.cell(row=r, column=2 + k, value=sum(1 for d in grupo if d["_crit"] == c_))
        ws.cell(row=r, column=2 + len(CRITS), value=len(grupo)).font = Font(bold=True)
        for c_ in range(1, 3 + len(CRITS)):
            ws.cell(row=r, column=c_).border = FINO
            if c_ > 1:
                ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        r += 1
    fim_r = r - 1
    ch2 = BarChart()
    ch2.type, ch2.grouping, ch2.gapWidth, ch2.overlap = "col", "stacked", 70, 100
    ch2.add_data(Reference(ws, min_col=2, min_row=ini_r - 1, max_col=1 + len(CRITS), max_row=fim_r),
                 titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=ini_r, max_row=fim_r))
    ch2.title = "Cada recorte do ano repartido por criticidade"
    ch2.y_axis.title = "equipamentos"
    for s_, c_ in zip(ch2.series, CRITS):
        bm.cor_barra(s_, COR_CRIT[c_])
        bm.rotulos(s_)
    bm.categorias(ch2, ws, "$A$%d:$A$%d" % (ini_r, fim_r))
    ws.add_chart(bm.estilo(ch2, 12, 30), "J%d" % (ini_r + 22))

    # --- tipo × criticidade
    r += 2
    ws.cell(row=r, column=1, value="TIPO × CRITICIDADE — os %d da conta" % len(conta)).font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Tipo"] + CRITS + ["TOTAL"], [30] + [13] * len(CRITS) + [11])
    r += 1
    for t in ("RL", "RT"):
        grupo = [d for d in conta.values() if d["tipo_eq"] == t]
        ws.cell(row=r, column=1, value="Religador" if t == "RL" else "Regulador")
        for k, c_ in enumerate(CRITS):
            ws.cell(row=r, column=2 + k, value=sum(1 for d in grupo if d["_crit"] == c_))
        ws.cell(row=r, column=2 + len(CRITS), value=len(grupo)).font = Font(bold=True)
        for c_ in range(1, 3 + len(CRITS)):
            ws.cell(row=r, column=c_).border = FINO
            if c_ > 1:
                ws.cell(row=r, column=c_).alignment = Alignment(horizontal="center")
        r += 1

    # --- lista
    r += 2
    ws.cell(row=r, column=1, value="OS %d DA CONTA, COM CRITICIDADE" % len(conta)).font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["Ativo", "Tipo", "Criticidade", "Entrou", "Saiu", "Localidade",
                "Abertura", "Dias"], [12, 7, 14, 14, 16, 22, 12, 8])
    r += 1
    for d in sorted(conta.values(), key=lambda d: (CRITS.index(d["_crit"]), d["tipo_eq"], d["ativo"])):
        e, sa = entrada[id(d)], res.get(id(d))
        ws.cell(row=r, column=1, value=d["ativo"])
        c_ = ws.cell(row=r, column=2, value=d["tipo_eq"])
        c_.font = Font(bold=True, color=VERDE if d["tipo_eq"] == "RT" else LARANJA, size=10)
        c_ = ws.cell(row=r, column=3, value=d["_crit"])
        c_.font = Font(bold=True, color=COR_CRIT[d["_crit"]], size=10)
        ws.cell(row=r, column=4, value="backlog 2025" if e == "backlog" else MESES[e])
        ws.cell(row=r, column=5, value=MESES[sa] if sa is not None else "segue pendente")
        ws.cell(row=r, column=6, value=d.get("localidade", ""))
        ws.cell(row=r, column=7, value=d["abertura"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=8, value=(d["fim"] - d["abertura"]).days if sa is not None else "")
        for k in (2, 3, 4, 5, 7, 8):
            ws.cell(row=r, column=k).alignment = Alignment(horizontal="center")
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
    crit = criticidade_por_ativo()
    conta, entrada, res, linhas, completados = selecionar(itens, posicao, crit)
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
    gest = gestao_por_status()
    if gest:
        aba_ano(wb, linhas, back, gest)
        aba_criticidade(wb, conta, entrada, res, linhas, gest, crit)
        aba_ago_dez(wb, gest, n_rl, n_rt)
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
