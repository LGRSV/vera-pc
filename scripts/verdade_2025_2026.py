"""
2025 × 2026 — o que os dados provam sobre o tempo até a troca e o backlog.

Pedido do gestor (28/09): «quero uma visão de verdade provando que em 2026 a gente melhorou o
tempo até a troca de RL e RT e ainda salvamos muito o backlog que 2025 deixou, se isso for
verdade com base nos dados». RL e RT juntos, em dias, sem prazo.

TRÊS PERGUNTAS
  1. A falha de 2026 está sendo trocada mais cedo que a de 2025?
  2. 2026 trocou as falhas que 2025 deixou sem troca?
  3. A fila de indisponibilidade encolheu?

PERGUNTAS 1 E 2 — o rol da taxa (aba «Falha Equipamentos» da COEP 5), o mesmo do SLA de falhas:
53 falhas de 2025 e 37 de 2026, por peça. Data da falha e data da troca saem de
sla_falhas_regional.json, com a régua de lá (o texto manda; sem texto, a cadeia). Ficam fora as
que não têm como medir: 2 de 2025 com a troca confirmada no rol e sem data na base, e 1 de cada
ano encerrada sem troca — sobram 50 e 36. O ano é o da fatia do rol; o 7933585074 é falha de 2025
com a data em 27/01/2026, então entra no estoque em janeiro de 2026.

MESMA IDADE. A falha de 2026 é mais nova, e as duas contas fáceis enganam em sentidos opostos:
a mediana das trocadas (296 × 78 dias) favorece 2026, porque das falhas de 2026 só as rápidas
terminaram; o tempo das trocas feitas no ano (14 × 243 dias) desfavorece 2026, porque ele trocou
as velhas de 2025 — e o rol não tem as falhas de 2024 que 2025 possa ter trocado. A régua justa
compara as duas na mesma idade da falha:
  · por fase: trocadas em até 30 dias; entre 31 e 180 dias, das que passaram de 30 sem troca;
    entre 181 e 240, das que passaram de 180 — e em cada fase só entra a falha que já teve o
    tempo todo da fase (a de 2026 com 100 dias não conta na fase que vai até 180). O tempo que a
    falha teve é o do calendário, da falha até hoje; só a aberta que falhou de novo para na falha
    seguinte. Cortar também a trocada na falha seguinte (primeira versão, 28/09) tirava da conta
    quem foi trocado rápido e voltou a operar — o 5854566043, trocado em 33 dias — e baixava 2025;
  · no ritmo de 2025: se cada falha de 2026 tivesse, em cada idade, a chance de troca que a de
    2025 teve naquela idade (a curva acumulada de 2025, Nelson–Aalen), quantas trocas teria hoje;
  · o teste log-rank compara as duas curvas até a idade da falha mais velha de 2026 e dá a chance
    de a diferença ser acaso.

PERGUNTA 3 — a fila da visão ETO (ativo 58/79 com SS de INDISPONIBILIDADE PARA OPERAÇÃO em
aberto), com a montagem de backlog_mensal.py: a demanda abre na primeira SS e fecha na saída da
última; a saída é a conclusão, senão a abertura da SS seguinte do mesmo ativo, senão segue aberta;
repassada sem seguinte sai na própria abertura; SS que se sobrepõem viram um período só. A base é
a de repasse de 23/09 (RELIGA_REGULA_23092026, aberturas desde 08/2020), a mesma posição das
perguntas 1 e 2, e cobre 2025 inteiro: nenhuma demanda aberta antes de 2024 passou a virada de
2024 em aberto. Em 21/08/2026 ela dá 92 na fila, contra os 93 da visão ETO (outra base). Os dois
anos são medidos no mesmo dia, 23/09.

Grava dist/VERDADE_2025_2026.xlsx e data/missao/verdade_2025_2026.json.
Rodar: python3 scripts/verdade_2025_2026.py
"""

import datetime as dt
import json
import math
import os
import sys
from collections import Counter, defaultdict
from statistics import median

import openpyxl
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.marker import Marker
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_mensal as bm  # noqa: E402 — estilo de gráfico e cabeçalho do projeto
import sla_falhas_regional as sf  # noqa: E402 — posição e base de repasse do SLA de falhas

SAIDA = os.path.join(sf.RAIZ, "dist", "VERDADE_2025_2026.xlsx")
JSON = os.path.join(sf.RAIZ, "data", "missao", "verdade_2025_2026.json")
HOJE = sf.HOJE.date()                                  # 23/09/2026, posição da base de repasse
ANOS = (2025, 2026)
COR = {2025: bm.LARANJA, 2026: bm.VERDE}
MES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
FAIXAS = ((0, 30, "até 30 dias"), (31, 90, "31 a 90"), (91, 180, "91 a 180"),
          (181, 270, "181 a 270"), (271, 365, "271 a 365"), (366, 10 ** 6, "mais de 365"))
FASES = ((0, 30), (31, 180), (181, 240))
IND = "INDISPONIBILIDADE PARA OPERAÇÃO"
INF = dt.date(9999, 12, 31)


# ------------------------------------------------------------------ perguntas 1 e 2: o rol
def falhas():
    """As falhas do rol que dá para medir — trocadas com data ou ainda abertas — e as de fora."""
    with open(sf.JSON, encoding="utf-8") as fh:
        itens = json.load(fh)["itens"]
    dia = lambda s: dt.datetime.strptime(s, "%d/%m/%Y").date()
    medir, fora = [], []
    for x in itens:
        trocada = x["situacao"].startswith("trocada ") and x["dias"] is not None
        if not (trocada or x["situacao"].startswith("em aberto")):
            fora.append(x)
            continue
        ini = dia(x["inicio"])
        # quanto tempo a falha teve para ser trocada: da falha até hoje. A aberta que falhou de
        # novo sai na falha seguinte (é o `dias` dela); a trocada conta o calendário inteiro — cortar
        # a trocada na falha seguinte tiraria da conta justo quem foi trocado rápido e voltou a operar
        medir.append({"ativo": x["ativo"], "tipo": x["tipo"], "ano": x["ano"], "peca": x["peca"],
                      "ss": x["ss"], "municipio": x["municipio"], "regional": x["regional"],
                      "falha": ini, "troca": dia(x["troca"]) if trocada else None,
                      "dias": x["dias"], "trocada": trocada, "nota": x["nota"],
                      "seguimento": (HOJE - ini).days if trocada else x["dias"], "regra": x["regra"]})
    return medir, fora


def faixa(d):
    return next(nome for a, b, nome in FAIXAS if a <= d <= b)


def curva(xs):
    """Nelson–Aalen: a chance acumulada de troca por idade; a aberta sai da conta na idade que tem."""
    out, soma = [], 0.0
    for t in sorted({x["dias"] for x in xs if x["trocada"]}):
        n = sum(1 for x in xs if x["dias"] >= t)
        soma += sum(1 for x in xs if x["trocada"] and x["dias"] == t) / n
        out.append((t, soma))
    return out


def no_ritmo(c, t):
    return max((s for tt, s in c if tt <= t), default=0.0)


def logrank(a, b, lim):
    """Log-rank de duas curvas até `lim` dias: trocas observadas e esperadas em `b`, qui² e p."""
    obs = [(min(x["dias"], lim), x["trocada"] and x["dias"] <= lim, g)
           for g, xs in ((0, a), (1, b)) for x in xs]
    o = e = v = 0.0
    for t in sorted({t for t, ev, _ in obs if ev}):
        n = sum(1 for t2, _, _ in obs if t2 >= t)
        n1 = sum(1 for t2, _, g in obs if t2 >= t and g == 1)
        d = sum(1 for t2, ev, _ in obs if t2 == t and ev)
        o += sum(1 for t2, ev, g in obs if t2 == t and ev and g == 1)
        e += d * n1 / n
        if n > 1:
            v += d * (n1 / n) * (1 - n1 / n) * (n - d) / (n - 1)
    qui = (o - e) ** 2 / v
    return {"observadas": int(o), "esperadas_se_igual": round(e, 2), "qui2": round(qui, 2),
            "p": round(math.erfc(math.sqrt(qui / 2)), 4), "ate_dias": lim}


def tempo(fs):
    """As três leituras do tempo, as fases na mesma idade, o ritmo de 2025 e o teste."""
    g = {a: [x for x in fs if x["ano"] == a] for a in ANOS}
    out = {"leituras": {}, "fases": {}, "faixas": {}, "esperando": {}}
    for a in ANOS:
        tr = [x["dias"] for x in g[a] if x["trocada"]]
        no_ano = [x["dias"] for x in fs if x["trocada"] and x["troca"].year == a]
        out["leituras"][a] = {
            "falhas": len(g[a]), "trocadas": len(tr), "abertas": len(g[a]) - len(tr),
            "rapidas_pela_tele": sum(1 for x in g[a] if x["trocada"] and x["dias"] <= 30 and x["regra"] == 3),
            # o maior intervalo de dias sem nenhuma troca, entre a última rápida e a primeira tardia
            "vazio": max(((p + 1, q - 1) for p, q in zip(sorted(tr), sorted(tr)[1:])), key=lambda v: v[1] - v[0]),
            "mediana_trocadas": median(tr), "media_trocadas": round(sum(tr) / len(tr), 1),
            "trocas_feitas_no_ano": len(no_ano), "media_trocas_feitas_no_ano": round(sum(no_ano) / len(no_ano), 1),
            "mediana_trocas_feitas_no_ano": median(no_ano)}
        for ini, fim in FASES:
            # entra quem chegou à fase sem troca e já teve a fase inteira para ser trocado
            base = [x for x in g[a] if not (x["trocada"] and x["dias"] < ini) and x["seguimento"] >= fim]
            feitas = sum(1 for x in base if x["trocada"] and ini <= x["dias"] <= fim)
            out["fases"][(a, ini, fim)] = {"trocadas": feitas, "base": len(base),
                                          "pct": round(feitas / len(base), 4) if base else None}
        for _, _, nome in FAIXAS:
            out["faixas"][(a, nome)] = sum(1 for x in g[a] if x["trocada"] and faixa(x["dias"]) == nome)
            out["esperando"][(a, nome)] = sum(1 for x in g[a] if not x["trocada"] and faixa(x["dias"]) == nome)
    c25 = curva(g[2025])
    out["ritmo_2025"] = {"trocas_2026": sum(1 for x in g[2026] if x["trocada"]),
                         "esperadas_no_ritmo_2025": round(sum(no_ritmo(c25, x["dias"]) for x in g[2026]), 1)}
    out["teste"] = logrank(g[2025], g[2026], max(x["dias"] for x in g[2026]))
    return out


def ultimo_dia(ano, mes):
    return min(HOJE, dt.date(ano + mes // 12, mes % 12 + 1, 1) - dt.timedelta(days=1))


def backlog(fs):
    """Estoque de falhas sem troca no fim de cada mês, pelo ano da falha, e as trocas do mês."""
    meses = [(a, m) for a in ANOS for m in range(1, 13) if dt.date(a, m, 1) <= HOJE]
    linhas = []
    for a, m in meses:
        fim, ini = ultimo_dia(a, m), dt.date(a, m, 1)
        linha = {"mes": f"{MES[m - 1]}/{str(a)[2:]}", "fim_do_mes": fim.isoformat()}
        for ano in ANOS:
            xs = [x for x in fs if x["ano"] == ano]
            linha[f"sem_troca_{ano}"] = sum(1 for x in xs if x["falha"] <= fim and (x["troca"] is None or x["troca"] > fim))
            linha[f"trocas_{ano}"] = sum(1 for x in xs if x["troca"] and ini <= x["troca"] <= fim)
        linhas.append(linha)
    f25 = [x for x in fs if x["ano"] == 2025]
    deixou = [x for x in f25 if not (x["troca"] and x["troca"].year == 2025)]
    trocou = [x for x in deixou if x["troca"]]
    feitas_2026 = [x for x in fs if x["troca"] and x["troca"].year == 2026]
    resumo = {"falhas_2025": len(f25), "trocadas_em_2025": len(f25) - len(deixou), "deixou": len(deixou),
              "trocadas_em_2026": len(trocou), "seguem": len(deixou) - len(trocou),
              "mais_velha_esperando": max(x["dias"] for x in deixou if not x["troca"]),
              "trocas_de_2026": len(feitas_2026),
              "trocas_de_2026_em_falha_de_2025": sum(1 for x in feitas_2026 if x["ano"] == 2025),
              "sem_troca_hoje": sum(1 for x in fs if not x["troca"])}
    return linhas, resumo


# ------------------------------------------------------------------ pergunta 3: a fila ETO
def fila_eto():
    """As demandas de indisponibilidade de RL/RT, montadas como em backlog_mensal.py."""
    ws = openpyxl.load_workbook(sf.BASE_SS, data_only=True)["Exportar Planilha"]   # A1:A1 no cabeçalho
    linhas = ws.iter_rows(values_only=True)
    cab = next(linhas)
    reg = {}
    for r in linhas:
        d = dict(zip(cab, r))
        if d["PENDENCIA_DO_ATIVO"] == IND and str(d["COD_ELE"]) in ("79", "78", "58") and d["DTA_ABERTURA"]:
            reg.setdefault(d["SS_ORIGINAL"], d)          # a SS que bifurca vem repetida: conta uma vez
    por = defaultdict(list)
    for d in reg.values():
        conc = d["DTA_CONCLUSAO"].date() if d["DTA_CONCLUSAO"] else None
        por[sf.txt(d["EQUIPAMENTO"])].append((d["DTA_ABERTURA"].date(), conc, sf.txt(d["STATUS"])))
    dem = []
    for ativo, lista in por.items():
        lista.sort(key=lambda t: (t[0], t[1] or INF))
        brutos = []
        for i, (a, conc, st) in enumerate(lista):
            if conc:
                fim, como = conc, st
            elif st == "SS PENDENTE":
                fim, como = INF, "segue pendente"
            else:
                seg = [z for z, _, _ in lista[i + 1:] if z >= a]
                fim, como = (seg[0], "repassada") if seg else (a, "repassada sem seguinte")
            brutos.append((a, max(fim, a), como))
        brutos.sort()
        for a, fim, como in brutos:
            if dem and dem[-1]["ativo"] == ativo and a <= dem[-1]["fim"]:
                if fim > dem[-1]["fim"]:
                    dem[-1].update(fim=fim, como=como)
            else:
                dem.append({"ativo": ativo, "abertura": a, "fim": fim, "como": como})
    return dem


def ano_da_fila(dem, ano):
    virada, corte = dt.date(ano - 1, 12, 31), dt.date(ano, HOJE.month, HOJE.day)
    herd = [d for d in dem if d["abertura"] <= virada < d["fim"]]
    sairam = [d for d in herd if d["fim"] <= corte]
    novas = [d for d in dem if virada < d["abertura"] <= corte]
    mensal = []
    for m in range(1, HOJE.month + 1):
        fim = min(corte, dt.date(ano, m + 1, 1) - dt.timedelta(days=1)) if m < 12 else corte
        mensal.append({"mes": MES[m - 1], "fila": sum(1 for d in dem if d["abertura"] <= fim < d["fim"]),
                       "herdadas_na_fila": sum(1 for d in herd if d["fim"] > fim)})
    como = Counter(d["como"] for d in sairam)
    return {"virada": virada.isoformat(), "corte": corte.isoformat(), "herdadas": len(herd),
            "sairam": len(sairam), "pct_sairam": round(len(sairam) / len(herd), 4),
            "por_atendida": como["SS ATENDIDA"], "por_cancelada": como["SS CANCELADA"],
            "outras_saidas": len(sairam) - como["SS ATENDIDA"] - como["SS CANCELADA"],
            "ficaram": len(herd) - len(sairam), "entraram": len(novas),
            "saidas_no_ano": len(sairam) + sum(1 for d in novas if d["fim"] <= corte),
            "fila_no_corte": sum(1 for d in dem if d["abertura"] <= corte < d["fim"]),
            "mais_antiga_herdada": min(d["abertura"] for d in herd).isoformat(),
            "herdadas_de_antes_de_2024": sum(1 for d in herd if d["abertura"].year < 2024),
            "mensal": mensal}


# ------------------------------------------------------------------ planilha
FILETE = Side(style="thin", color="C8C2AF")


def celulas(ws, r0, dados, formatos=None, negrito_ult=False):
    for j, linha in enumerate(dados):
        for i, v in enumerate(linha, 1):
            c = ws.cell(row=r0 + j, column=i, value=v)
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left" if i == 1 else "center")
            c.border = Border(bottom=FILETE)
            if formatos and i in formatos:
                c.number_format = formatos[i]
            if j % 2:
                c.fill = PatternFill("solid", fgColor=bm.SOMBRA)
            if negrito_ult and j == len(dados) - 1:
                c.font = Font(bold=True)
    return r0 + len(dados)


def rotulo(ws, r, texto, sub=None, largura=8):
    ws.cell(row=r, column=1, value=texto).font = Font(bold=True, size=12, color=bm.SINAL)
    if sub:
        c = ws.cell(row=r + 1, column=1, value=sub)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.font = Font(italic=True, size=9)
        ws.merge_cells(start_row=r + 1, start_column=1, end_row=r + 1, end_column=largura)
        ws.row_dimensions[r + 1].height = 40
        return r + 3
    return r + 2


def serie_colorida(ch, anos):
    for s, a in zip(ch.series, anos):
        bm.cor_barra(s, COR[a])


def linha_colorida(ch, anos):
    for s, a in zip(ch.series, anos):
        s.graphicalProperties = GraphicalProperties()
        s.graphicalProperties.line = LineProperties(solidFill=COR[a], w=28000)
        s.marker = Marker(symbol="circle", size=8)
        s.marker.graphicalProperties = GraphicalProperties(solidFill=COR[a])
        s.marker.graphicalProperties.line = LineProperties(solidFill="FBFAF6", w=19050)
        s.smooth = False


def grafico_estoque(ws_dados, r_cab, r_fim):
    ch = BarChart()
    ch.type, ch.grouping, ch.overlap, ch.gapWidth = "col", "stacked", 100, 60
    ch.add_data(Reference(ws_dados, min_col=2, max_col=3, min_row=r_cab, max_row=r_fim), titles_from_data=True)
    ch.title = "Falhas de peça grande sem troca no fim de cada mês, pelo ano da falha"
    ch.y_axis.title = "falhas sem troca"
    serie_colorida(ch, ANOS)
    ch.legend.position, ch.legend.overlay = "b", False
    bm.categorias(ch, ws_dados, "$A$%d:$A$%d" % (r_cab + 1, r_fim))
    return bm.estilo(ch, 11, 30)


def aba_veredito(wb, tmp, bk, fila, ws_bk, r_bk):
    ws = wb.active
    ws.title = "Veredito"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 110
    ws["A1"] = "2025 × 2026 — o que os dados provam"
    ws["A1"].font = Font(bold=True, size=14, color=bm.SINAL)
    ws["A2"] = (f"Religador e regulador juntos, em dias, sem prazo. Posição: {HOJE:%d/%m/%Y}. "
                "Falhas de peça grande do rol da taxa (o mesmo do SLA de falhas) e a fila de "
                "indisponibilidade da visão ETO. Cada número tem a conta nas abas seguintes.")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A2:B2")
    ws.row_dimensions[2].height = 32
    L, F, R, T = tmp["leituras"], tmp["fases"], tmp["ritmo_2025"], tmp["teste"]
    f = lambda a, i, j: F[(a, i, j)]
    pct = lambda v: f"{round(100 * v)}%"
    num = lambda v: str(v).replace(".", ",")
    razao = R["trocas_2026"] / R["esperadas_no_ritmo_2025"]
    vezes = "o dobro" if 1.8 <= razao < 2.3 else f"{num(round(razao, 1))} vezes"
    rapidas = f(2025, 0, 30)["trocadas"] + f(2026, 0, 30)["trocadas"]
    tele = L[2025]["rapidas_pela_tele"] + L[2026]["rapidas_pela_tele"]
    q25, q26 = fila[2025], fila[2026]
    blocos = [
        ("1. O tempo até a troca melhorou em 2026?",
         "MELHOROU DEPOIS DO PRIMEIRO MÊS — SINAL FORTE, PROVA AINDA ABERTA",
         [f"No primeiro mês é igual: {pct(f(2025, 0, 30)['pct'])} das falhas de 2025 e {pct(f(2026, 0, 30)['pct'])} "
          f"das de 2026 trocadas em até 30 dias — a troca rápida ({tele} das {rapidas} fechadas pela TELE).",
          f"Das que passaram do primeiro mês sem troca, do 2º ao 6º mês 2026 trocou {f(2026, 31, 180)['trocadas']} "
          f"de {f(2026, 31, 180)['base']} ({pct(f(2026, 31, 180)['pct'])}); 2025, {f(2025, 31, 180)['trocadas']} de "
          f"{f(2025, 31, 180)['base']} ({pct(f(2025, 31, 180)['pct'])}). No 7º e 8º mês: {f(2026, 181, 240)['trocadas']} "
          f"de {f(2026, 181, 240)['base']} contra {f(2025, 181, 240)['trocadas']} de {f(2025, 181, 240)['base']}. "
          f"Em 2025 nenhuma falha foi trocada entre o {L[2025]['vazio'][0]}º e o {L[2025]['vazio'][1]}º dia.",
          f"Somando tudo: as falhas de 2026 tiveram {R['trocas_2026']} trocas até hoje. No ritmo de 2025, na "
          f"mesma idade, teriam {num(R['esperadas_no_ritmo_2025'])} — {vezes}.",
          f"Ainda não é prova: {L[2026]['abertas']} das {L[2026]['falhas']} falhas de 2026 esperam troca, e a "
          f"conta estatística dá {num(round(100 * T['p'], 1))}% de chance de a diferença ser acaso (o costume é "
          "exigir menos de 5%). Se as que esperam forem trocadas nos próximos meses, a diferença tende a virar "
          "prova; se esperarem como as de 2025, some."]),
        ("2. 2026 salvou o backlog que 2025 deixou?",
         "VERDADE: TROCOU QUASE METADE",
         [f"{bk['deixou']} falhas de peça grande de 2025 passaram para 2026 sem troca. Em 2026 foram "
          f"trocadas {bk['trocadas_em_2026']} ({pct(bk['trocadas_em_2026'] / bk['deixou'])}); "
          f"{bk['seguem']} seguem esperando, a mais velha há {bk['mais_velha_esperando']} dias.",
          f"{bk['trocas_de_2026_em_falha_de_2025']} das {bk['trocas_de_2026']} trocas feitas em 2026 foram em falha "
          "de 2025 — 6 em cada 10.",
          f"Por isso o tempo médio das trocas feitas no ano subiu de {round(L[2025]['media_trocas_feitas_no_ano'])} "
          f"para {round(L[2026]['media_trocas_feitas_no_ano'])} dias: é o resgate das velhas, não lentidão."]),
        ("3. A fila de indisponibilidade encolheu?",
         "NÃO — E O HERDADO CAIU NO MESMO RITMO DE 2025",
         [f"Até 23/09/2026 saíram da fila {q26['sairam']} das {q26['herdadas']} demandas herdadas de 2025 "
          f"({pct(q26['pct_sairam'])}). No mesmo dia de 2025 tinham saído {q25['sairam']} das {q25['herdadas']} "
          f"herdadas de 2024 ({pct(q25['pct_sairam'])}).",
          f"Em 2025, {q25['por_atendida']} dessas saídas foram por SS atendida; em 2026, {q26['por_atendida']} "
          f"— e {q26['por_cancelada']} por cancelamento, contra {q25['por_cancelada']}.",
          f"A fila foi de {q26['herdadas']} para {q26['fila_no_corte']} em 2026 (em 2025, de {q25['herdadas']} para "
          f"{q25['fila_no_corte']}): entraram {q26['entraram']} demandas e saíram {q26['saidas_no_ano']}.",
          f"Nas falhas de peça grande: {bk['deixou']} sem troca na virada do ano, {bk['sem_troca_hoje']} hoje."]),
    ]
    r = 4
    for pergunta, resposta, provas in blocos:
        ws.cell(row=r, column=1, value=pergunta).font = Font(bold=True, size=11)
        c = ws.cell(row=r, column=2, value=resposta)
        c.font = Font(bold=True, color=bm.PAPEL)
        c.fill = PatternFill("solid", fgColor=bm.TINTA)
        ws.cell(row=r, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        r += 1
        for p in provas:
            c = ws.cell(row=r, column=2, value="· " + p)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 15 * math.ceil(len(p) / 105) + 3
            r += 1
        r += 1
    ws.add_chart(grafico_estoque(ws_bk, r_bk[0], r_bk[1]), f"A{r + 1}")
    return blocos


def aba_tempo(wb, tmp):
    ws = wb.create_sheet("Tempo até a troca")
    for col, w in zip("ABCDEFG", (44, 16, 16, 16, 16, 30, 30)):
        ws.column_dimensions[col].width = w
    L, F = tmp["leituras"], tmp["fases"]
    r = rotulo(ws, 1, "As contas fáceis enganam — em sentidos opostos",
               "A mediana das trocadas favorece 2026 (das falhas de 2026 só as rápidas terminaram). O tempo das "
               "trocas feitas no ano desfavorece 2026 (ele trocou as velhas de 2025, e o rol não tem as falhas de "
               "2024 que 2025 possa ter trocado). Nenhuma das duas mede a mesma coisa nos dois anos.", 7)
    bm.cabecalho(ws, r, ["Conta", "2025", "2026", "O que parece", "Por que engana"])
    r = celulas(ws, r + 1, [
        ["Mediana de dias até a troca, só das trocadas, pelo ano da falha",
         L[2025]["mediana_trocadas"], L[2026]["mediana_trocadas"], "2026 muito mais rápido",
         f"{L[2026]['abertas']} das {L[2026]['falhas']} falhas de 2026 ainda esperam — só as rápidas entraram"],
        ["Média de dias das trocas feitas no ano, pelo ano da troca",
         L[2025]["media_trocas_feitas_no_ano"], L[2026]["media_trocas_feitas_no_ano"], "2026 muito mais lento",
         f"{L[2026]['trocas_feitas_no_ano']} trocas em 2026, muitas de falha de 2025; "
         f"em 2025 só {L[2025]['trocas_feitas_no_ano']}, todas rápidas"],
    ])

    r = rotulo(ws, r + 1, "A régua justa: na mesma idade da falha",
               "Em cada fase só entra a falha que chegou à fase sem troca e já teve a fase inteira para ser "
               "trocada. Ex.: a falha de 2026 com 100 dias não entra na fase que vai até 180.", 7)
    bm.cabecalho(ws, r, ["Fase depois da falha", "2025 trocadas", "2025 base", "2025 %",
                         "2026 trocadas", "2026 base", "2026 %"])
    nomes = {(0, 30): "Até 30 dias (todas)", (31, 180): "De 31 a 180 dias (as que passaram de 30 sem troca)",
             (181, 240): "De 181 a 240 dias (as que passaram de 180 sem troca)"}
    r = celulas(ws, r + 1, [[nomes[(i, j)]] + [v for a in ANOS for v in
                             (F[(a, i, j)]["trocadas"], F[(a, i, j)]["base"], F[(a, i, j)]["pct"])]
                            for i, j in FASES], {4: "0%", 7: "0%"})
    R, T = tmp["ritmo_2025"], tmp["teste"]
    r = celulas(ws, r + 1, [
        ["Trocas das falhas de 2026 até hoje", R["trocas_2026"]],
        ["No ritmo de 2025, na mesma idade, seriam", R["esperadas_no_ritmo_2025"]],
        [f"Chance de a diferença ser acaso (teste log-rank até {T['ate_dias']} dias)", T["p"]],
    ])
    for rr, formato in zip(range(r - 3, r), ("0", "0.0", "0.0%")):
        ws.cell(row=rr, column=2).number_format = formato

    v25, idade26 = L[2025]["vazio"], tmp["teste"]["ate_dias"]     # o teste vai até a falha mais velha de 2026
    r = rotulo(ws, r + 1, "Quando a peça foi trocada, contando da falha",
               f"Trocas por faixa de dias depois da falha. Em 2025 nenhuma falha foi trocada entre o {v25[0]}º e o "
               f"{v25[1]}º dia: a troca vinha nas primeiras semanas ou só depois de sete meses. Nenhuma falha de "
               f"2026 tem mais de {idade26} dias, então as duas últimas faixas ainda não podem ter falha de 2026.", 7)
    bm.cabecalho(ws, r, ["Faixa de dias", "Trocadas — falhas de 2025", "Trocadas — falhas de 2026",
                         "Esperando — falhas de 2025", "Esperando — falhas de 2026"])
    r_cab = r
    r = celulas(ws, r + 1, [[nome, tmp["faixas"][(2025, nome)], tmp["faixas"][(2026, nome)],
                             tmp["esperando"][(2025, nome)], tmp["esperando"][(2026, nome)]]
                            for _, _, nome in FAIXAS])
    ch = BarChart()
    ch.type, ch.grouping, ch.overlap, ch.gapWidth = "col", "clustered", -10, 70
    ch.add_data(Reference(ws, min_col=2, max_col=3, min_row=r_cab, max_row=r - 1), titles_from_data=True)
    ch.title = "Trocas por faixa de dias depois da falha"
    ch.y_axis.title = "trocas"
    serie_colorida(ch, ANOS)
    for s in ch.series:
        bm.rotulos(s)
    ch.legend.position, ch.legend.overlay = "b", False
    bm.categorias(ch, ws, "$A$%d:$A$%d" % (r_cab + 1, r - 1))
    ws.add_chart(bm.estilo(ch, 10, 24), f"A{r + 2}")
    ch = BarChart()
    ch.type, ch.grouping, ch.overlap, ch.gapWidth = "col", "clustered", -10, 70
    ch.add_data(Reference(ws, min_col=4, max_col=5, min_row=r_cab, max_row=r - 1), titles_from_data=True)
    ch.title = "Falhas ainda sem troca, pela idade de hoje"
    ch.y_axis.title = "falhas"
    serie_colorida(ch, ANOS)
    for s in ch.series:
        bm.rotulos(s)
    ch.legend.position, ch.legend.overlay = "b", False
    bm.categorias(ch, ws, "$A$%d:$A$%d" % (r_cab + 1, r - 1))
    ws.add_chart(bm.estilo(ch, 10, 24), f"E{r + 2}")


def aba_backlog(wb, linhas, bk):
    ws = wb.create_sheet("Backlog de 2025")
    for col, w in zip("ABCDEF", (12, 20, 20, 16, 20, 20)):
        ws.column_dimensions[col].width = w
    r = rotulo(ws, 1, "O que 2025 deixou sem troca e o que 2026 trocou",
               f"Falhas de peça grande do rol. {bk['falhas_2025']} de 2025 com como medir: {bk['trocadas_em_2025']} "
               f"trocadas em 2025, {bk['deixou']} passaram para 2026; destas, {bk['trocadas_em_2026']} trocadas em "
               f"2026 e {bk['seguem']} seguem esperando. Das {bk['trocas_de_2026']} trocas de 2026, "
               f"{bk['trocas_de_2026_em_falha_de_2025']} foram em falha de 2025. O 7933585074 é falha de 2025 com a "
               "data em 27/01/2026 e por isso entra no estoque em janeiro.", 6)
    bm.cabecalho(ws, r, ["Mês", "Falhas de 2025", "Falhas de 2026", "Total sem troca",
                         "Trocas no mês — falha de 2025", "Trocas no mês — falha de 2026"])
    r_cab = r
    r = celulas(ws, r + 1, [[x["mes"], x["sem_troca_2025"], x["sem_troca_2026"],
                             x["sem_troca_2025"] + x["sem_troca_2026"], x["trocas_2025"], x["trocas_2026"]]
                            for x in linhas])
    ws.add_chart(grafico_estoque(ws, r_cab, r - 1), f"H{r_cab}")
    ws.freeze_panes = ws.cell(row=r_cab + 1, column=1)
    return ws, (r_cab, r - 1)


def aba_fila(wb, fila):
    ws = wb.create_sheet("Fila herdada")
    for col, w in zip("ABCDE", (46, 16, 16, 16, 16)):
        ws.column_dimensions[col].width = w
    q = fila
    r = rotulo(ws, 1, "A fila de indisponibilidade herdada — 2025 × 2026, no mesmo dia do ano",
               "Visão ETO: ativo 58/79 com SS de indisponibilidade para operação em aberto, montada como no "
               "backlog mensal, na base de repasse de 23/09/2026 (desde 08/2020 — 2025 está completo). "
               "Herdada = aberta na virada do ano. Os dois anos são medidos até 23/09.", 5)
    bm.cabecalho(ws, r, ["", "2025", "2026"])
    r = celulas(ws, r + 1, [
        ["Herdadas na virada do ano", q[2025]["herdadas"], q[2026]["herdadas"]],
        ["Saíram até 23/09", q[2025]["sairam"], q[2026]["sairam"]],
        ["   por SS atendida", q[2025]["por_atendida"], q[2026]["por_atendida"]],
        ["   por SS cancelada", q[2025]["por_cancelada"], q[2026]["por_cancelada"]],
        ["   por repasse", q[2025]["outras_saidas"], q[2026]["outras_saidas"]],
        ["% das herdadas que saiu", q[2025]["pct_sairam"], q[2026]["pct_sairam"]],
        ["Herdadas ainda na fila em 23/09", q[2025]["ficaram"], q[2026]["ficaram"]],
        ["Demandas novas no ano até 23/09", q[2025]["entraram"], q[2026]["entraram"]],
        ["Saídas no ano até 23/09 (herdadas + novas)", q[2025]["saidas_no_ano"], q[2026]["saidas_no_ano"]],
        ["Fila em 23/09", q[2025]["fila_no_corte"], q[2026]["fila_no_corte"]],
    ])
    for rr in range(r - 10, r):
        if ws.cell(row=rr, column=1).value.startswith("%"):
            for c in (2, 3):
                ws.cell(row=rr, column=c).number_format = "0%"
    r = rotulo(ws, r + 1, "Mês a mês", None)
    bm.cabecalho(ws, r, ["Mês", "Herdadas na fila — 2025", "Herdadas na fila — 2026",
                         "Fila total — 2025", "Fila total — 2026"])
    r_cab = r
    r = celulas(ws, r + 1, [[a["mes"], a["herdadas_na_fila"], b["herdadas_na_fila"], a["fila"], b["fila"]]
                            for a, b in zip(q[2025]["mensal"], q[2026]["mensal"])])
    for col, titulo, ancora in ((2, "Herdadas que seguem na fila, no fim do mês", f"A{r + 2}"),
                                (4, "Fila de indisponibilidade no fim do mês", f"D{r + 2}")):
        ch = LineChart()
        ch.add_data(Reference(ws, min_col=col, max_col=col + 1, min_row=r_cab, max_row=r - 1), titles_from_data=True)
        ch.title = titulo
        ch.y_axis.title = "demandas"
        linha_colorida(ch, ANOS)
        ch.legend.position, ch.legend.overlay = "b", False
        bm.categorias(ch, ws, "$A$%d:$A$%d" % (r_cab + 1, r - 1))
        ws.add_chart(bm.estilo(ch, 9, 17), ancora)


def aba_falhas(wb, fs, fora):
    ws = wb.create_sheet("Falhas")
    cols = ["Ano da falha", "Tipo", "Ativo", "Município", "Regional", "Peça", "SS da falha", "Data da falha",
            "Troca em", "Ano da troca", "Dias até a troca ou parada até hoje", "Situação", "Faixa de dias"]
    bm.cabecalho(ws, 1, cols, [8, 6, 12, 18, 9, 10, 20, 11, 11, 8, 12, 18, 12])
    dados = [[x["ano"], x["tipo"], x["ativo"], x["municipio"].title(), x["regional"].title(), x["peca"], x["ss"],
              x["falha"], x["troca"], x["troca"].year if x["troca"] else None, x["dias"],
              "trocada" if x["trocada"] else "esperando troca", faixa(x["dias"])]
             for x in sorted(fs, key=lambda x: (x["ano"], x["falha"], x["ativo"]))]
    dados += [[x["ano"], x["tipo"], x["ativo"], x["municipio"].title(), x["regional"].title(), x["peca"], x["ss"],
               None, None, None, None, "fora da conta: " + x["situacao"], None] for x in fora]
    celulas(ws, 2, dados, {8: "DD/MM/YYYY", 9: "DD/MM/YYYY"})
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:M{1 + len(dados)}"


def aba_como(wb):
    ws = wb.create_sheet("Como foi feito")
    for linha in (__doc__ or "").strip().splitlines():
        ws.append([linha])
    ws.column_dimensions["A"].width = 110


def main():
    fs, fora = falhas()
    assert Counter(x["ano"] for x in fs) == {2025: 50, 2026: 36}, Counter(x["ano"] for x in fs)
    tmp = tempo(fs)
    linhas, bk = backlog(fs)
    assert bk["deixou"] == bk["trocadas_em_2026"] + bk["seguem"]
    assert linhas[-1]["sem_troca_2025"] + linhas[-1]["sem_troca_2026"] == bk["sem_troca_hoje"]
    dem = fila_eto()
    fila = {a: ano_da_fila(dem, a) for a in ANOS}
    for a in ANOS:
        q = fila[a]
        assert q["herdadas_de_antes_de_2024"] == 0 or a == 2026, q   # 2025 completo na base
        assert q["herdadas"] == q["sairam"] + q["ficaram"]
        assert q["fila_no_corte"] == q["herdadas"] + q["entraram"] - q["saidas_no_ano"], q
        assert q["mensal"][-1]["fila"] == q["fila_no_corte"] and q["mensal"][-1]["herdadas_na_fila"] == q["ficaram"]
    na_visao_eto = sum(1 for d in dem if d["abertura"] <= dt.date(2026, 8, 21) < d["fim"])

    wb = openpyxl.Workbook()
    aba_tempo(wb, tmp)
    ws_bk, r_bk = aba_backlog(wb, linhas, bk)
    aba_fila(wb, fila)
    aba_falhas(wb, fs, fora)
    aba_como(wb)
    blocos = aba_veredito(wb, tmp, bk, fila, ws_bk, r_bk)
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    wb.save(SAIDA)

    chave = lambda k: " ".join(str(p) for p in k) if isinstance(k, tuple) else str(k)
    with open(JSON, "w", encoding="utf-8") as fh:
        json.dump({"posicao": HOJE.isoformat(),
                   "tempo": {k: ({chave(kk): vv for kk, vv in v.items()} if isinstance(v, dict) else v)
                             for k, v in tmp.items()},
                   "backlog_do_rol": bk, "backlog_mensal_do_rol": linhas, "fila_eto": fila,
                   "fila_eto_em_21_08_2026": na_visao_eto,
                   "veredito": [{"pergunta": p, "resposta": r, "provas": pr} for p, r, pr in blocos]},
                  fh, ensure_ascii=False, indent=1, default=str)
    for p, r, pr in blocos:
        print(p, "→", r)
        for x in pr:
            print("   ·", x)
    print("fila ETO em 21/08/2026 nesta base:", na_visao_eto)


if __name__ == "__main__":
    main()
