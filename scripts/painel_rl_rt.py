"""
O painel RL × RT do posto — dist/PAINEL_RL_RT.xlsx.

Seis visões pedidas pelo gestor em 29/08, todas na régua de 28/08 (71 resolvidos ·
54 na fila · 125 na conta do posto), separadas por religador e regulador:

  1. Os 125: resolvidos e pendentes, por tipo
  2. O passivo — quantos vinham de anos anteriores, por tipo e por grupo
  3. Os 54 pendentes, por tipo, abertos pelo ano da ocorrência
  4. Os 125, por tipo e por ano da ocorrência
  5. Falha em 2026, mês a mês, da taxa de falha da planilha base
  6. O passivo mês a mês, pela data da ocorrência inicial

REGRA DO ANO: vale sempre a DATA DE OCORRÊNCIA, nunca a abertura da SS nem o número
dela. Nos 71 é a ocorrência da demanda que o posto fechou; nos 54, a da demanda que
segue aberta — não a mais antiga do ativo, que pode ser de um ciclo já encerrado.

Rodar: python3 scripts/painel_rl_rt.py
"""

import json
import os
import sys
from collections import Counter, defaultdict

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference, Series
from openpyxl.chart.data_source import AxDataSource, StrRef
from openpyxl.drawing.colors import ColorChoice
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import sla_manutencao as base  # noqa: E402
import sla_por_equipe as eq  # noqa: E402

COEP = os.path.join(RAIZ, "data", "missao", "coep_2026.json")
OCORR = os.path.join(RAIZ, "data", "missao", "ss_ocorrencia.json")
BASE = os.path.join(RAIZ, "data", "missao", "base_coep.json")
SAIDA = os.path.join(RAIZ, "dist", "PAINEL_RL_RT.xlsx")

TINTA, PAPEL, SINAL = "FF211D15", "FFF2EFE6", "FFBC4B0E"
# as duas séries, conferidas com o validador do dataviz sobre o papel claro
COR_RL, COR_RT = "1F7C50", "B8480C"
MES = ["jan", "fev", "mar", "abr", "mai", "jun",
       "jul", "ago", "set", "out", "nov", "dez"]
ANOS = ["2023", "2024", "2025", "2026"]


def apurar():
    reg = base.base_de_repasse(None)
    anterior = eq.raizes(reg)
    oc_ss = {}
    with open(OCORR, encoding="utf-8") as fh:
        for r in json.load(fh):
            k = base.norm(r["SS_ORIGINAL"])
            d = base.data(r.get("DTA_OCORRENCIA"))
            if k and d:
                oc_ss.setdefault(k, d)
    with open(COEP, encoding="utf-8") as fh:
        cp = json.load(fh)

    at = {a["ativo"]: a for a in cp["ativos"]}
    ss_info = {s["ss"]: s for s in cp["ss"]}
    res82 = {r["ativo"]: r for r in cp["resolvidos_do_coep"]
             if r["conta_como_resolvido_pelo_coep"]}
    fila = {a for a, v in at.items() if v["segue_no_posto"]}
    r71 = sorted(set(res82) - fila)
    assert len(res82) == 82 and len(r71) == 71 and len(fila) == 54, \
        f"esperado 82-11=71 e 54, veio {len(res82)}/{len(r71)}/{len(fila)}"

    def mes_da_demanda(ativo, pendente):
        if not pendente:
            d = res82[ativo].get("ocorrencia_da_demanda")   # dd/mm/aaaa
            if d:
                return f"{d[6:10]}-{d[3:5]}"
        melhor = None
        for p in str(at[ativo].get("ss") or "").split("|"):
            k = base.norm(p)
            if not k:
                continue
            s = ss_info.get(p.strip())
            if pendente and s and not s.get("segue_no_posto"):
                continue      # na fila só vale a cadeia da SS que segue aberta
            for c in (eq.do_comeco(k, anterior), k):
                d = oc_ss.get(c)
                if d and (melhor is None or d < melhor):
                    melhor = d
        return melhor.strftime("%Y-%m") if melhor else None

    mes = {a: mes_da_demanda(a, False) for a in r71}
    mes.update({a: mes_da_demanda(a, True) for a in fila})
    assert all(mes.values()), "ativo sem data de ocorrência"

    sig = {a: ("RL" if at[a]["tipo"] == "religador" else "RT") for a in mes}
    return {"resolvidos": r71, "fila": sorted(fila), "mes": mes, "sig": sig,
            "localidade": {a: at[a]["localidade"] for a in mes}}


def quadro(conj, sig, mes):
    """{tipo: {ano: n, passivo, total}} — o ano é o da ocorrência."""
    q = {}
    for t in ("RL", "RT", "Total"):
        d = {y: sum(1 for a in conj
                    if (sig[a] == t or t == "Total") and mes[a][:4] == y)
             for y in ANOS}
        d["passivo"] = sum(d[y] for y in ANOS if y != "2026")
        d["total"] = sum(d[y] for y in ANOS)
        q[t] = d
    return q


# ------------------------------------------------------------------ a planilha
def cabeca(ws, linha, titulo, cols):
    c = ws.cell(row=linha, column=1, value=titulo)
    c.font = Font(bold=True, size=11, color=SINAL)
    ws.append(cols)
    for i in range(1, len(cols) + 1):
        cel = ws.cell(row=linha + 1, column=i)
        cel.font = Font(bold=True, color=PAPEL, size=10)
        cel.fill = PatternFill("solid", fgColor=TINTA)
        cel.alignment = Alignment(horizontal="left", vertical="center",
                                  wrap_text=True)
    return linha + 2


def negrito(ws, linha, n):
    for i in range(1, n + 1):
        ws.cell(row=linha, column=i).font = Font(bold=True)
        ws.cell(row=linha, column=i).border = Border(
            top=Side(style="medium", color=TINTA))


def montar():
    d = apurar()
    sig, mes = d["sig"], d["mes"]
    res, fila = d["resolvidos"], d["fila"]
    todos = res + fila
    q_res, q_fila, q_125 = (quadro(res, sig, mes), quadro(fila, sig, mes),
                            quadro(todos, sig, mes))

    wb = Workbook()
    ws = wb.active
    ws.title = "Visão do posto"
    ws.column_dimensions["A"].width = 30
    for c in "BCDEFG":
        ws.column_dimensions[c].width = 13

    # 1 — os 125: resolvidos e pendentes
    r = cabeca(ws, 1, "1 · Os 125 do posto em 2026",
               ["", "Resolvidos", "Na fila", "Total", "% resolvido"])
    for t in ("RL", "RT", "Total"):
        a, b = q_res[t]["total"], q_fila[t]["total"]
        ws.append(["Religador" if t == "RL" else
                   "Regulador" if t == "RT" else "Total", a, b, a + b,
                   round(a / (a + b), 4)])
        ws.cell(row=ws.max_row, column=5).number_format = "0.0%"
    negrito(ws, ws.max_row, 5)

    # 2 — o passivo
    r = cabeca(ws, ws.max_row + 2, "2 · Quantos vinham de anos anteriores",
               ["", "Passivo 23+24+25", "De 2026", "Total", "% passivo"])
    for rot, q in (("Resolvidos", q_res), ("Na fila", q_fila), ("Os 125", q_125)):
        for t in ("RL", "RT", "Total"):
            nome = ("Religador" if t == "RL" else
                    "Regulador" if t == "RT" else "Total")
            ws.append([f"{rot} · {nome}", q[t]["passivo"], q[t]["2026"],
                       q[t]["total"],
                       round(q[t]["passivo"] / q[t]["total"], 4) if q[t]["total"] else 0])
            ws.cell(row=ws.max_row, column=5).number_format = "0.0%"
            if t == "Total":
                negrito(ws, ws.max_row, 5)

    # 3 — os 54 pendentes
    r = cabeca(ws, ws.max_row + 2, "3 · Os 54 que estão na fila do posto",
               [""] + ANOS + ["Passivo", "Total"])
    for t in ("RL", "RT", "Total"):
        q = q_fila[t]
        ws.append(["Religador" if t == "RL" else
                   "Regulador" if t == "RT" else "Total"]
                  + [q[y] or "—" for y in ANOS] + [q["passivo"], q["total"]])
    negrito(ws, ws.max_row, 7)

    # 4 — os 125 por ano
    r = cabeca(ws, ws.max_row + 2, "4 · Os 125 pelo ano da ocorrência",
               [""] + ANOS + ["Passivo", "Total"])
    for t in ("RL", "RT", "Total"):
        q = q_125[t]
        ws.append(["Religador" if t == "RL" else
                   "Regulador" if t == "RT" else "Total"]
                  + [q[y] or "—" for y in ANOS] + [q["passivo"], q["total"]])
    negrito(ws, ws.max_row, 7)

    # 5 — falha em 2026, mês a mês, da taxa de falha
    with open(BASE, encoding="utf-8") as fh:
        bc = json.load(fh)
    ws2 = wb.create_sheet("Falha 2026 mensal")
    ws2.column_dimensions["A"].width = 12
    for c in "BCDE":
        ws2.column_dimensions[c].width = 13
    cabeca(ws2, 1, "5 · Quantos RL e RT falharam em 2026 (taxa de falha)",
           ["Mês", "Religador", "Regulador", "Total", "Acumulado"])
    rl = [x["falhas"] for x in bc["mensal"]["RL|2026"]][:8]
    rt = [x["falhas"] for x in bc["mensal"]["RT|2026"]][:8]
    ac = 0
    for i in range(8):
        ac += rl[i] + rt[i]
        ws2.append([MES[i] + "/26", rl[i], rt[i], rl[i] + rt[i], ac])
    ws2.append(["Total", sum(rl), sum(rt), sum(rl) + sum(rt), ""])
    negrito(ws2, ws2.max_row, 5)
    grafico(ws2, "Falhas de 2026 por mês", 2, 3, ws2.max_row - 1, "G2")

    # 6 — o passivo mês a mês, pela ocorrência inicial
    ws3 = wb.create_sheet("Passivo mensal")
    ws3.column_dimensions["A"].width = 12
    for c in "BCDE":
        ws3.column_dimensions[c].width = 13
    cabeca(ws3, 1, "6 · O passivo pela data da ocorrência inicial",
           ["Mês", "Religador", "Regulador", "Total", "Acumulado"])
    passivo = [a for a in todos if mes[a][:4] != "2026"]
    c = Counter((mes[a], sig[a]) for a in passivo)
    ac = 0
    for m in sorted({k[0] for k in c}):
        a, b = c.get((m, "RL"), 0), c.get((m, "RT"), 0)
        ac += a + b
        ws3.append([f"{MES[int(m[5:7]) - 1]}/{m[2:4]}", a, b, a + b, ac])
    ws3.append(["Total", sum(1 for a in passivo if sig[a] == "RL"),
                sum(1 for a in passivo if sig[a] == "RT"), len(passivo), ""])
    negrito(ws3, ws3.max_row, 5)
    grafico(ws3, "Passivo por mês da ocorrência", 2, 3, ws3.max_row - 1, "G2")

    # a régua
    ws4 = wb.create_sheet("Como foi feito")
    ws4.column_dimensions["A"].width = 98
    for t in TEXTO:
        ws4.append([t])
    ws4["A1"].font = Font(bold=True, size=12, color=SINAL)
    for i, t in enumerate(TEXTO, start=1):
        if t and not t.startswith(" ") and t.endswith(":"):
            ws4.cell(row=i, column=1).font = Font(bold=True, size=11)

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    wb.save(SAIDA)
    return SAIDA, q_res, q_fila, q_125, len(passivo)


def grafico(ws, titulo, cab, r0, r1, onde):
    """cab = linha do cabeçalho (de onde sai o nome da série); r0..r1 = os dados."""
    g = BarChart()
    g.type, g.grouping, g.overlap = "col", "stacked", 100
    g.title, g.height, g.width, g.gapWidth = titulo, 8.5, 22, 70
    for col, cor in ((2, COR_RL), (3, COR_RT)):
        s = Series(Reference(ws, min_col=col, min_row=cab, max_row=r1),
                   title_from_data=True)
        s.graphicalProperties.solidFill = ColorChoice(srgbClr=cor)
        s.graphicalProperties.line.noFill = True
        g.series.append(s)
    # mês é texto: sem StrRef o Excel numera as categorias
    cats = AxDataSource(strRef=StrRef(f=f"'{ws.title}'!$A${r0}:$A${r1}"))
    for s in g.series:
        s.cat = cats
    ws.add_chart(g, onde)


TEXTO = [
    "O painel RL × RT do posto do COEP",
    "",
    "A régua:",
    "Tudo aqui está na conta de 28/08: 71 resolvidos, 54 na fila, 125 na conta do",
    "posto. São 82 ativos que fecharam a demanda no ano, menos os 11 que resolveram e",
    "voltaram para a fila — pela decisão do gestor, quem voltou não conta como",
    "resolvido.",
    "",
    "O ano é sempre o da OCORRÊNCIA:",
    "Nunca a abertura da SS, nunca o número dela. A abertura vem em média 39 dias",
    "depois do fato e em 9,8% dos casos cai em outro ano; e a ETO-COEP 00149/2025 foi",
    "aberta em 29/06/2026. Numerar não é abrir, e abrir não é o fato acontecer.",
    "",
    "Qual ocorrência, quando o ativo tem várias:",
    "Nos 71 resolvidos vale a ocorrência da demanda que o posto FECHOU. Nos 54 da fila",
    "vale a da demanda que SEGUE ABERTA — não a mais antiga do ativo, que pode ser de",
    "um ciclo já encerrado. Equipamento reincidente tem mais de uma cadeia, e misturar",
    "as duas envelhece o passivo artificialmente.",
    "",
    "As abas 5 e 6 respondem a perguntas diferentes:",
    "A aba 5 é a TAXA DE FALHA: quantos equipamentos falharam em 2026, da planilha base",
    "de equipamentos especiais. Conta falha do parque inteiro, tenha ela passado pelo",
    "COEP ou não.",
    "",
    "A aba 6 é o PASSIVO DO POSTO: dos 125 que passaram pelo COEP, quantos vinham de",
    "ocorrência de 2023, 2024 ou 2025, e em que mês esse fato aconteceu. É a idade da",
    "fila, não a taxa.",
    "",
    "Os dois números não se somam nem se comparam direto: o primeiro é do parque, o",
    "segundo é da mesa.",
    "",
    "Cada ativo conta uma vez:",
    "125 ativos distintos em 125 linhas. Equipamento que passou pelo posto duas vezes",
    "no ano ocupa uma linha só.",
]


if __name__ == "__main__":
    caminho, q_res, q_fila, q_125, npas = montar()
    print("gravado:", caminho)
    print(f"  resolvidos {q_res['Total']['total']} "
          f"(RL {q_res['RL']['total']} · RT {q_res['RT']['total']})")
    print(f"  na fila    {q_fila['Total']['total']} "
          f"(RL {q_fila['RL']['total']} · RT {q_fila['RT']['total']})")
    print(f"  os 125     RL {q_125['RL']['total']} · RT {q_125['RT']['total']}")
    print(f"  passivo    {npas} de {q_125['Total']['total']} "
          f"(RL {q_125['RL']['passivo']} · RT {q_125['RT']['passivo']})")
