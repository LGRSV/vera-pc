"""
Ficha do regulador 5800440256 (Mateiros) — dist/FICHA_5800440256.xlsx.

Pedido do gestor em 09/09: a linha do tempo de manutenção do ativo em Excel, com as
datas de repasse entre os postos e de cancelamento.

A REGRA DO REPASSE (CLAUDE.md): SS repassada sai da base SEM data de conclusão, então
a data em que ela deixou o posto é a ABERTURA DA SS SEGUINTE do mesmo ativo. O tempo
parado num posto é a diferença entre as duas aberturas. Quem tem data de término saiu
por conclusão — atendida ou cancelada.

O QUE A FICHA MOSTRA: 24 SS entre 09/01/2024 e 06/08/2026, seis eventos de manutenção,
o tempo de cada SS em cada posto, os tempos médios por desfecho e os pareceres na
íntegra. Duas coisas que a ficha deixa à vista: o cancelamento em BLOCO de 30/03/2026,
que fechou 9 SS no mesmo dia sem o equipamento voltar a operar, e o aterramento, aberto
desde janeiro de 2024.

Rodar: python3 scripts/ficha_5800440256.py
"""

import datetime as dt
import os
import re
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import cadeia_obra as co        # noqa: E402  — escolhe a base de SS/OS mais nova
import extrai_ssos_min as ex    # noqa: E402  — o remontador de registros
import backlog_mensal as bm     # noqa: E402  — estilo de gráfico

ATIVO = "5800440256"
SAIDA = os.path.join(RAIZ, "dist", "FICHA_%s.xlsx" % ATIVO)
CARTEIRA = os.path.join(RAIZ, "data", "raw", "EQUIPAMENTOS_INDISPONIVEIS_ATUALIZADA16.xlsx")
GESTAO = os.path.join(RAIZ, "data", "raw", "GESTAO_DE_EQUIPAMENTOS.xlsx")
BASE_COEP = os.path.join(RAIZ, "data", "raw", "GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP.xlsx")

TINTA, PAPEL, SOMBRA, SINAL = bm.TINTA, bm.PAPEL, bm.SOMBRA, bm.SINAL
VERDE, LARANJA, NEUTRO, GRADE = bm.VERDE, bm.LARANJA, bm.NEUTRO, bm.GRADE
POSICAO = dt.date(2026, 8, 21)     # fecho da BASE_SS_OS_20082026 (aberturas 20/08, términos 21/08)
HOJE = dt.date(2026, 9, 9)
FINO = Border(*[Side("thin", color="FFDDD8CC")] * 4)

COR_SIT = {"SS ATENDIDA": "FF1F7C50", "SS CANCELADA": "FFB8480C",
           "SS REPASSADA": "FF6D675A", "SS PENDENTE": "FFBC4B0E"}

# os seis eventos, na leitura fechada com o gestor em 09/09
EVENTOS = [
    ("jan/2024", dt.date(2024, 1, 9), "Fase C",
     "Baixa isolação na fase C, radiador amassado, nível de óleo muito baixo e malha de "
     "aterramento com resistência muito alta. Pedido: trocar o tanque da fase C.",
     "Melhoria de aterramento com terra gel (OS ETO-RD-PO 983/2024). Ajuste de proteção "
     "revisado em 31/01/2024, conforme dados de placa.",
     "ETO-TELE 00100/2024 atendida em 9 dias — mas o tanque da fase C nunca foi trocado.",
     "ETO-TELE 00841/2023 · ETO-COEP 00003/2024 · ETO-RD-PO 00041/2024 · "
     "ETO-PROT 00040/2024 · ETO-TELE 00100/2024"),
    ("set/2024", dt.date(2024, 9, 3), "Duas fases",
     "Duas fases com tensões discrepantes, causando oscilação na LD e nas cidades de "
     "Mateiros e São Félix.", "—",
     "Duas SS atendidas em 244 e 247 dias, só em maio de 2025.",
     "ETO-TELE 00731/2024 · ETO-TELE 00732/2024"),
    ("abr/2025 → mar/2026", dt.date(2025, 4, 23), "Fase A",
     "Comissionamento e ensaios de isolação nas três células: fase A com isolação muito "
     "baixa e necessidade de substituição; malha de aterramento com resistência ruim.",
     "Comissionamento da célula da fase A (comunicação restaurada), troca do nobreak "
     "danificado, testes funcionais com o operador do COS, equipamento em tap 0, "
     "bloqueado e remoto. COCM trocou a fase C e refez o aterramento.",
     "«Equipamento ficou em operação? Não». Encerrada no cancelamento em bloco de "
     "30/03/2026 — 9 SS fechadas no mesmo dia.",
     "ETO-PROT 00158/2025 · ETO-TELE 00418/2025 · ETO-RD-PA 00800/2025 · "
     "ETO-COEP 00227/2025 · ETO-RD-PO 00007/2026 · ETO-COEP 00022/2026 · "
     "ETO-PROT 00062/2026 · ETO-RD-PO 00072/2026 · ETO-RD-PA 00190/2026 · "
     "ETO-RD-PO 00092/2026 · ETO-TELE 00357/2026"),
    ("nov/2025", dt.date(2025, 11, 30), "Célula (vazamento)",
     "Uma das células apresentando vazamento de óleo; o equipamento ficou bypassado por "
     "ter causado o desarme da LD Ponte Alta–Mateiros.", "—",
     "Cancelada em 13/01/2026, em 44 dias. É a falha deste ativo no rol de 2025.",
     "ETO-TELE 01431/2025"),
    ("jun–ago/2026", dt.date(2026, 6, 19), "Relé, chaves e aterramento",
     "Regulador travado com comunicação intermitente; três chaves de entrada com ponto "
     "quente em 34,5 kV; medição de aterramento pendente.",
     "OS ETO-TELEPA 000406/2026 e ETO-TELEPA 000118/2026.",
     "Atendidas em 7 e 27 dias. A nota de linha viva (DG-RD-PO 00432/2026) foi repassada "
     "para a TELE em 14 dias, sem registro de execução das chaves.",
     "ETO-TELE 00947/2026 · DG-RD-PO 00432/2026 · ETO-TELE 00996/2026"),
    ("ago/2026", dt.date(2026, 8, 6), "Fase B",
     "Flutuação de tensão oscilando de 16 kV a 23 kV, com reclamação diária do cliente "
     "BRK. Defeito registrado: comutação indevida.",
     "Parecer DMSL 06/08: substituir a célula da fase B e melhorar a malha de "
     "aterramento. Parecer COEP 24/08: equipamento em logística, pendente de abertura "
     "de obra para requisição do material pelos COCM.",
     "Aberta há %d dias (%d até o fecho da base). SLA de 12 dias." % (
         (HOJE - dt.date(2026, 8, 6)).days, (POSICAO - dt.date(2026, 8, 6)).days),
     "ETO-COEP 00169/2026 · ETO-TELE 01034/2026"),
]


# ------------------------------------------------------------------------------ base
def data(s):
    s = (s or "").strip()
    try:
        return dt.datetime.strptime(s[:10], "%d/%m/%Y").date()
    except ValueError:
        return None


def ler_ss():
    """As 24 SS do ativo, remontadas da base crua."""
    caminho = co.PARTES[0] if isinstance(co.PARTES, (list, tuple)) else co.PARTES
    regs, buffer = [], None
    with open(caminho, encoding="latin-1") as fh:
        for i, linha in enumerate(fh):
            linha = linha.rstrip("\r\n")
            if i == 0 and linha.startswith("NUMERO_SS@"):
                continue
            if co.RE_INICIO.match(linha):
                if buffer is not None and ("@%s@" % ATIVO) in buffer:
                    regs.append(buffer)
                buffer = linha
            elif buffer is not None:
                buffer += "\n" + linha
        if buffer is not None and ("@%s@" % ATIVO) in buffer:
            regs.append(buffer)
    ss = []
    for b in regs:
        c = ex._normaliza(b.split("@"))
        if c[13].strip() != ATIVO:
            continue
        ss.append({"ss": c[0].strip(), "os": c[1].strip(), "origem": c[3].strip(),
                   "defeito": c[4].strip(), "posto": c[11].strip(),
                   "criticidade": c[17].strip(), "situacao": c[18].strip(),
                   "abertura": data(c[19]), "termino": data(c[20]), "limite": data(c[21]),
                   "tipo": c[26].strip(), "solicitante": c[24].strip(),
                   "desc": c[27].strip()})
    ss.sort(key=lambda x: (x["abertura"], x["ss"]))
    return ss


def encadear(ss):
    """Quando cada SS saiu do posto, e para onde foi.

    Régua da casa, nesta ordem: quem tem término saiu por conclusão (atendida ou cancelada);
    quem está SS PENDENTE segue no posto; quem foi repassada sai sem data — a saída dela é a
    ABERTURA DA SS SEGUINTE do ativo, e o posto dessa SS seguinte é o destino; quem não tem
    seguinte segue no posto."""
    for i, x in enumerate(ss):
        seg = next((y for y in ss[i + 1:] if y["abertura"] >= x["abertura"]), None)
        if x["termino"]:
            x["saida"], x["destino"] = x["termino"], "—"
            x["como"] = "cancelada" if x["situacao"] == "SS CANCELADA" else "concluída"
        elif x["situacao"] == "SS PENDENTE":
            x["saida"], x["destino"], x["como"] = None, "—", "segue no posto"
        elif seg:
            x["saida"], x["destino"] = seg["abertura"], seg["posto"]
            x["como"] = "repassada"
        else:
            x["saida"], x["destino"] = None, "—"
            x["como"] = "segue no posto"
        fim = x["saida"] or POSICAO
        x["dias"] = (fim - x["abertura"]).days
        x["aberta"] = x["saida"] is None
        x["dias_hoje"] = (HOJE - x["abertura"]).days if x["aberta"] else x["dias"]
    return ss


def ficha_cadastro():
    """Cadastro dos Ajustes de RT, carteira e orçamento — o que existe do ativo."""
    out = []
    wb = load_workbook(GESTAO, data_only=True, read_only=True)
    ws = wb["Ajustes Reguladores de Tensão"]
    L = list(ws.iter_rows(values_only=True))
    cab = [("" if v is None else str(v).strip()) for v in L[0]]
    for r in L[1:]:
        if any(str(v).strip() == ATIVO for v in r if v is not None):
            for nome, v in zip(cab, r):
                if nome and v not in (None, ""):
                    v = v.strftime("%d/%m/%Y") if isinstance(v, dt.datetime) else v
                    out.append(("Ajustes de RT", nome, v))
            break
    wb.close()
    for arq, aba, rot in ((CARTEIRA, "Criticidade por Equipamento", "Carteira (ATUALIZADA 16)"),
                          (BASE_COEP, "Gestão", "Planilha base — aba Gestão")):
        wb = load_workbook(arq, data_only=True, read_only=True)
        ws = wb[aba]
        L = list(ws.iter_rows(values_only=True))
        cab = [("" if v is None else str(v).strip()) for v in L[0]]
        for r in L[1:]:
            if any(str(v).strip() == ATIVO for v in r if v is not None):
                for nome, v in zip(cab, r):
                    if nome and v not in (None, "") and nome != "Descrição SS":
                        v = v.strftime("%d/%m/%Y") if isinstance(v, dt.datetime) else v
                        out.append((rot, nome, v))
                break
        wb.close()
    return out


def parecer_coep():
    """O parecer do COEP mora na aba BASE SS_OS da planilha base (24/08)."""
    wb = load_workbook(BASE_COEP, data_only=True, read_only=True)
    ws = wb["BASE SS_OS"]
    L = list(ws.iter_rows(values_only=True))
    cab = [("" if v is None else str(v).strip()) for v in L[0]]
    i = cab.index("DESCRIPTION_SS")
    for r in L[1:]:
        if any(str(v).strip() == ATIVO for v in r if v is not None):
            wb.close()
            return str(r[i] or "")
    wb.close()
    return ""


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
    ws.row_dimensions[linha].height = 30


def aba_linha(wb, ss):
    ws = wb.create_sheet("Linha do tempo")
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, "REGULADOR %s — MATEIROS · 34,5 kV · 200 kVAr" % ATIVO,
              "Seis eventos de manutenção em %d dias, de 09/01/2024 a 06/08/2026, em %d SS. "
              "O defeito só muda de fase — C em 2024, A em 2026, célula vazando em novembro e B "
              "agora — e a única troca confirmada foi a da fase C pelo COCM, num serviço que "
              "terminou com o equipamento fora de operação. O aterramento está aberto desde "
              "janeiro de 2024. Nenhuma obra no AIC: nada foi capitalizado contra este ativo."
              % ((HOJE - dt.date(2024, 1, 9)).days, len(ss)))
    cab(ws, 4, ["Quando", "Peça / frente", "O que foi", "O que a equipe fez", "Como terminou",
                "SS da cadeia"], [20, 20, 46, 46, 42, 40])
    r = 5
    for quando, _, peca, oque, fez, fim, sss in EVENTOS:
        ws.cell(row=r, column=1, value=quando).font = Font(bold=True, size=10)
        ws.cell(row=r, column=2, value=peca).font = Font(bold=True, size=10, color=SINAL)
        ws.cell(row=r, column=3, value=oque)
        ws.cell(row=r, column=4, value=fez)
        ws.cell(row=r, column=5, value=fim)
        ws.cell(row=r, column=6, value=sss)
        for c in range(1, 7):
            cel = ws.cell(row=r, column=c)
            cel.alignment = Alignment(wrap_text=True, vertical="top")
            cel.border = FINO
            if r % 2:
                cel.fill = PatternFill("solid", fgColor=SOMBRA)
        ws.row_dimensions[r].height = 78
        r += 1
    return ws


def aba_postos(wb, ss):
    ws = wb.create_sheet("Passagem pelos postos")
    ws.sheet_view.showGridLines = False
    rep = sum(1 for x in ss if x["como"] == "repassada")
    canc = sum(1 for x in ss if x["como"] == "cancelada")
    bm.titulo(ws, "A PASSAGEM PELOS POSTOS — quando cada SS entrou, quanto ficou e para onde foi",
              "SS repassada sai da base SEM data de conclusão: a data em que ela deixou o posto é "
              "a ABERTURA DA SS SEGUINTE do ativo, e é assim que a coluna «Saiu» é montada nas %d "
              "repassadas. As %d canceladas saíram por conclusão — e %d delas no MESMO DIA, "
              "30/03/2026, num cancelamento em bloco em que o equipamento não voltou a operar."
              % (rep, canc, sum(1 for x in ss if x["saida"] == dt.date(2026, 3, 30))))
    cab(ws, 4, ["#", "SS", "Posto", "Tipo da SS", "Criticidade", "Situação", "Entrou", "Saiu",
                "Dias no posto", "Como saiu", "Foi para", "OS"],
        [4, 22, 12, 32, 13, 15, 12, 12, 12, 15, 12, 24])
    r = 5
    for i, x in enumerate(ss, 1):
        ws.cell(row=r, column=1, value=i)
        ws.cell(row=r, column=2, value=x["ss"])
        ws.cell(row=r, column=3, value=x["posto"])
        ws.cell(row=r, column=4, value=x["tipo"])
        ws.cell(row=r, column=5, value=x["criticidade"])
        c = ws.cell(row=r, column=6, value=x["situacao"])
        c.font = Font(bold=True, color=COR_SIT.get(x["situacao"], TINTA), size=10)
        ws.cell(row=r, column=7, value=x["abertura"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=8, value=x["saida"].strftime("%d/%m/%Y") if x["saida"] else "—")
        ws.cell(row=r, column=9, value=x["dias_hoje"])
        ws.cell(row=r, column=10, value=x["como"] if not x["aberta"] else "segue no posto")
        ws.cell(row=r, column=11, value=x["destino"])
        ws.cell(row=r, column=12, value=x["os"] or "—")
        for c_ in range(1, 13):
            cel = ws.cell(row=r, column=c_)
            cel.border = FINO
            if c_ in (1, 3, 5, 6, 7, 8, 9, 10, 11):
                cel.alignment = Alignment(horizontal="center")
            if x["aberta"]:
                cel.fill = PatternFill("solid", fgColor="FFF6E2D5")
            elif x["saida"] == dt.date(2026, 3, 30):
                cel.fill = PatternFill("solid", fgColor=SOMBRA)
        r += 1
    fim = r - 1

    # Gantt: base invisível (dias desde o início) + a barra do tempo no posto
    r += 2
    ws.cell(row=r, column=1, value="DADOS DO GRÁFICO — dias desde 09/01/2024").font = \
        Font(bold=True, size=11, color=SINAL)
    r += 1
    ini_g = r
    cab(ws, r, ["SS", "Antes", "Atendida", "Cancelada", "Repassada", "Aberta"],
        [4, 22, 12, 32, 13, 15])
    r += 1
    zero = ss[0]["abertura"]
    for x in ss:
        col = {"SS ATENDIDA": 3, "SS CANCELADA": 4, "SS REPASSADA": 5, "SS PENDENTE": 6}
        ws.cell(row=r, column=1, value=x["ss"])
        ws.cell(row=r, column=2, value=(x["abertura"] - zero).days)
        for c_ in range(3, 7):
            ws.cell(row=r, column=c_, value=0)
        alvo = 6 if x["aberta"] else col.get(x["situacao"], 5)
        ws.cell(row=r, column=alvo, value=max(x["dias_hoje"], 1))
        r += 1
    fim_g = r - 1

    ch = BarChart()
    ch.type, ch.grouping, ch.overlap, ch.gapWidth = "bar", "stacked", 100, 40
    ch.add_data(Reference(ws, min_col=2, min_row=ini_g, max_col=6, max_row=fim_g),
                titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=ini_g + 1, max_row=fim_g))
    base = ch.series[0]
    base.graphicalProperties = GraphicalProperties(noFill=True)
    base.graphicalProperties.line = LineProperties(noFill=True)
    for s, cor in zip(ch.series[1:], (VERDE, LARANJA, NEUTRO, SINAL[2:])):
        bm.cor_barra(s, cor)
    ch.title = "Quanto tempo cada SS ficou aberta, na ordem em que foram abertas"
    # em barra horizontal os papéis trocam: x_axis é a categoria (as SS) e y_axis é o valor
    ch.y_axis.title = "dias desde 09/01/2024"
    ch.x_axis.scaling.orientation = "maxMin"        # a primeira SS no topo
    bm.categorias(ch, ws, "$A$%d:$A$%d" % (ini_g + 1, fim_g))
    ch = bm.estilo(ch, 16, 30)
    ch.x_axis.axPos, ch.y_axis.axPos = "l", "b"
    ws.add_chart(ch, "N4")
    return fim


def aba_tempos(wb, ss):
    ws = wb.create_sheet("Tempos")
    ws.sheet_view.showGridLines = False
    at = [x for x in ss if x["situacao"] == "SS ATENDIDA"]
    ca = [x for x in ss if x["situacao"] == "SS CANCELADA"]
    ab = [x for x in ss if x["aberta"]]
    curtas = [x for x in at if x["dias"] < 100]
    bm.titulo(ws, "TEMPO DE CONSERTO — depende do que se chama de conserto",
              "Só a SS ATENDIDA teve serviço executado. A CANCELADA saiu da base sem que nada "
              "fosse feito, e %d das %d canceladas morreram juntas no bloco de 30/03/2026. "
              "A leitura honesta está na última linha: este banco nunca foi consertado — em %d "
              "dias o defeito só mudou de fase."
              % (sum(1 for x in ca if x["saida"] == dt.date(2026, 3, 30)), len(ca),
                 (HOJE - ss[0]["abertura"]).days))
    cab(ws, 4, ["Recorte", "SS", "Média (dias)", "Mediana", "Mínimo", "Máximo", "Leitura"],
        [40, 6, 13, 11, 10, 10, 62])

    def linha(r, rot, itens, leitura):
        v = sorted(x["dias"] for x in itens)
        ws.cell(row=r, column=1, value=rot)
        ws.cell(row=r, column=2, value=len(v))
        ws.cell(row=r, column=3, value=round(sum(v) / len(v), 1) if v else None)
        ws.cell(row=r, column=4, value=v[len(v) // 2] if v else None)
        ws.cell(row=r, column=5, value=min(v) if v else None)
        ws.cell(row=r, column=6, value=max(v) if v else None)
        ws.cell(row=r, column=7, value=leitura)
        for c in range(1, 8):
            cel = ws.cell(row=r, column=c)
            cel.border = FINO
            if c in range(2, 7):
                cel.alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=7).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 34

    r = 5
    linha(r, "SS ATENDIDA — serviço executado", at,
          "É o que mais se aproxima de conserto. Puxada pelos dois casos de 2024 que ficaram "
          "oito meses parados."); r += 1
    linha(r, "SS ATENDIDA, sem os dois casos de 2024", curtas,
          "Tirando as duas SS de anomalia de setembro/2024 (244 e 247 dias), o atendimento é "
          "rápido: 9, 7 e 27 dias."); r += 1
    linha(r, "SS CANCELADA", ca,
          "Não é conserto. Nove delas foram fechadas no mesmo dia, 30/03/2026, e o parecer "
          "diz «equipamento ficou em operação? Não»."); r += 1
    linha(r, "Todas as SS fechadas", [x for x in ss if not x["aberta"]],
          "Média de todo mundo, para referência. Mistura serviço com cancelamento."); r += 1

    r += 1
    ws.cell(row=r, column=1, value="AS QUE SEGUEM ABERTAS").font = Font(bold=True, size=11, color=SINAL)
    r += 1
    cab(ws, r, ["SS", "Posto", "Situação", "Aberta em", "Dias até a base", "Dias até hoje"],
        [24, 12, 15, 13, 15, 14])
    r += 1
    for x in sorted(ab, key=lambda x: x["abertura"]):
        ws.cell(row=r, column=1, value=x["ss"])
        ws.cell(row=r, column=2, value=x["posto"])
        ws.cell(row=r, column=3, value=x["situacao"])
        ws.cell(row=r, column=4, value=x["abertura"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=5, value=(POSICAO - x["abertura"]).days)
        ws.cell(row=r, column=6, value=(HOJE - x["abertura"]).days)
        for c in range(1, 7):
            cel = ws.cell(row=r, column=c)
            cel.border = FINO
            if c > 1:
                cel.alignment = Alignment(horizontal="center")
        r += 1

    r += 1
    for t in [
        "A DEMANDA ENCADEADA — repasse não é falha nova, então a cadeia inteira é uma manutenção só:",
        "· 09/01/2024 → 30/03/2026: 811 dias, 19 SS, terminou em CANCELAMENTO e o equipamento não voltou.",
        "· 19/06/2026 → 05/08/2026: 47 dias, 3 SS, terminou ATENDIDA.",
        "· 06/08/2026 → hoje: 2 SS, aberta há %d dias, contra SLA de 12." % (HOJE - dt.date(2026, 8, 6)).days,
    ]:
        c = ws.cell(row=r, column=1, value=t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if r == r:
            c.font = Font(bold=True, size=11, color=SINAL) if t.startswith("A DEMANDA") else Font(size=10)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
        r += 1


def aba_pareceres(wb, ss, coep):
    ws = wb.create_sheet("Pareceres")
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, "OS PARECERES, NA ÍNTEGRA",
              "A descrição da SS é CUMULATIVA: o SGM cola o parecer novo por cima do antigo, sem "
              "separador — por isso o texto se repete de SS para SS. Vale sempre o mais recente, "
              "que está no topo de cada texto. O parecer do COEP de 24/08 só existe na planilha "
              "base; a base crua de SS/OS é de 20/08 e não o alcança.")
    ws.cell(row=4, column=1, value="PARECER COEP 24/08 — o mais recente de todos").font = \
        Font(bold=True, size=11, color=SINAL)
    c = ws.cell(row=5, column=1, value=coep or "(não encontrado)")
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=4)
    ws.row_dimensions[5].height = 60
    cab(ws, 7, ["SS", "Posto", "Aberta em", "Descrição da SS (parecer mais recente no topo)"],
        [24, 12, 13, 150])
    r = 8
    for x in ss:
        ws.cell(row=r, column=1, value=x["ss"])
        ws.cell(row=r, column=2, value=x["posto"])
        ws.cell(row=r, column=3, value=x["abertura"].strftime("%d/%m/%Y"))
        ws.cell(row=r, column=4, value=x["desc"] or "—")
        for c_ in range(1, 5):
            cel = ws.cell(row=r, column=c_)
            cel.alignment = Alignment(wrap_text=True, vertical="top")
            cel.border = FINO
        ws.cell(row=r, column=3).alignment = Alignment(horizontal="center", vertical="top")
        ws.row_dimensions[r].height = 96
        r += 1


def aba_ficha(wb, dados):
    ws = wb.create_sheet("Ficha do ativo")
    ws.sheet_view.showGridLines = False
    bm.titulo(ws, "A FICHA — cadastro, carteira e orçamento",
              "Cadastro dos Ajustes de RT, posição na carteira ATUALIZADA 16 e a linha da aba "
              "Gestão da planilha base. A célula de 200 kVAr em 34,5 kV é o código 690240: "
              "R$ 51.705,75 de material e R$ 80.318,50 de mão de obra, R$ 132.024,25 no total.")
    cab(ws, 4, ["Fonte", "Campo", "Valor"], [28, 30, 66])
    r = 5
    for fonte, campo, valor in dados:
        ws.cell(row=r, column=1, value=fonte)
        ws.cell(row=r, column=2, value=campo)
        ws.cell(row=r, column=3, value=valor)
        for c in range(1, 4):
            cel = ws.cell(row=r, column=c)
            cel.border = FINO
            cel.alignment = Alignment(wrap_text=True, vertical="top")
        r += 1


def aba_como(wb, ss):
    ws = wb.create_sheet("Como foi feito")
    ws.column_dimensions["A"].width = 112
    texto = [
        ("DE ONDE VEM CADA COISA", True),
        ("As %d SS vêm da base crua data/raw/BASE_SS_OS_20082026.txt, remontadas registro a "
         "registro (o texto quebra linha e o separador é «@»). O cadastro vem da aba «Ajustes "
         "Reguladores de Tensão» da GESTÃO DE EQUIPAMENTOS; a criticidade, da carteira ATUALIZADA "
         "16; o orçamento e o parecer COEP, da GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP." % len(ss), False),
        ("", False),
        ("A DATA DE REPASSE", True),
        ("SS repassada sai da base SEM data de conclusão — o campo vem vazio. A data em que ela "
         "deixou o posto é a ABERTURA DA SS SEGUINTE do mesmo ativo, e o posto dessa SS seguinte "
         "é o destino. O tempo parado num posto é a diferença entre as duas aberturas.", False),
        ("Quem tem data de término saiu por conclusão: atendida (houve serviço) ou cancelada "
         "(saiu da base sem serviço). Quem não tem término nem SS seguinte segue no posto.", False),
        ("", False),
        ("O CANCELAMENTO EM BLOCO", True),
        ("Em 30/03/2026 nove SS deste ativo foram canceladas no mesmo dia, em cinco postos "
         "diferentes. O SGM não exporta o motivo do cancelamento — é lacuna conhecida. O parecer "
         "que estava aberto naquele momento diz «Equipamento ficou em operação? Não» e lista duas "
         "pendências: substituir a célula da fase A e melhorar a malha de aterramento. Nenhuma "
         "das duas aparece resolvida depois.", False),
        ("", False),
        ("A POSIÇÃO", True),
        ("A base tem aberturas até 20/08/2026 e términos até 21/08/2026 — é essa a posição das "
         "colunas «Dias até a base». O parecer COEP é de 24/08. A coluna «Dias até hoje» usa "
         "%s. Se alguma SS fechou depois de 21/08, esta ficha não sabe." % HOJE.strftime("%d/%m/%Y"), False),
        ("", False),
        ("O QUE NÃO EXISTE", True),
        ("Nenhuma obra no AIC para este ativo: a visão orçamentária cai no valor médio de RT "
         "(R$ 167.280,98) por falta de obra própria. Em dois anos e meio de manutenção nada foi "
         "capitalizado contra ele — tudo foi OS de manutenção da TELE e das RD.", False),
        ("O campo «Descrição do defeito» da base não serve aqui: 15 SS trazem «ILEGÍVEL» e 5 "
         "trazem «QUEIMADO». O diagnóstico de verdade só existe no texto do parecer.", False),
    ]
    for i, (t, negrito) in enumerate(texto, 1):
        c = ws.cell(row=i, column=1, value=t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if negrito:
            c.font = Font(bold=True, size=11, color=SINAL if i == 1 else TINTA)


def montar(saida=SAIDA):
    ss = encadear(ler_ss())
    assert len(ss) == 24, len(ss)
    coep = parecer_coep()
    wb = Workbook()
    wb.remove(wb.active)
    aba_linha(wb, ss)
    aba_postos(wb, ss)
    aba_tempos(wb, ss)
    aba_pareceres(wb, ss, coep)
    aba_ficha(wb, ficha_cadastro())
    aba_como(wb, ss)
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    wb.save(saida)
    print(saida)
    print("  %d SS | repassadas %d · canceladas %d · atendidas %d · abertas %d"
          % (len(ss), sum(1 for x in ss if x["como"] == "repassada"),
             sum(1 for x in ss if x["situacao"] == "SS CANCELADA"),
             sum(1 for x in ss if x["situacao"] == "SS ATENDIDA"),
             sum(1 for x in ss if x["aberta"])))
    print("  parecer COEP: %s" % (coep[:70] + "…" if coep else "(não achado)"))
    return saida


if __name__ == "__main__":
    montar(sys.argv[1] if len(sys.argv) > 1 else SAIDA)
