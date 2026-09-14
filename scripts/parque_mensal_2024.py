"""
O crescimento do parque de religador e regulador, mês a mês, de 2024 até agora.

A pergunta do gestor (14/09): mensalizar a entrada de RL e RT até fechar no parque
atual. As duas tentativas anteriores furaram por superconta — a reconstrução pelo AIC
(abandonada, dava 174 RL em 2024) e a reconstrução pela movimentação de SS (425 RL
entre 2024 e 2026, contra realidade de ~20/ano).

O QUE DESTRAVOU: a planilha de controle de abertura de SS que o gestor mandou
(3. ABERTURA DE SS 2024.1.xlsx), com uma aba por código operativo. A coluna DTA_ORIG
é a data de origem do cadastro do ativo — a única data de nascimento de equipamento
que existe em qualquer base do projeto.

MAS DTA_ORIG SOZINHA NÃO SERVE: das 556 linhas de cadastro, 151 são de ativo que já
tinha SS ANTES do próprio DTA_ORIG. Nesses o cadastro foi mexido depois (o OBS diz:
«atualização de cadastro», «RELIGADOR REMANEJADO», «já está em operação», «atualização
minsait»), e a data não marca entrada nenhuma. Dois filtros, nesta ordem:

  1. sem SS anterior ao DTA_ORIG  — se já tinha SS antes, o ativo já existia
  2. OBS não diz que é mexida     — atualização, remanejamento, ajuste de rota, minsait

Sobram 279 RL e 76 RT entrando entre janeiro de 2024 e agosto de 2026.

A CURVA É DE TRÁS PRA FRENTE: ancora no parque de agosto de 2026 que o gestor deu
(1.294 RL e 190 RT, régua de 24/08) e desconta as entradas mês a mês. Implica 1.015 RL
e 114 RT no começo de 2024.

CONFERÊNCIA CONTRA A ÂNCORA, e ela não fecha redondo: em 2026 jan–jul esta conta dá
20 RL e 14 RT, contra os 13 e 10 que o gestor deu em 24/08. Sobra em torno de 50%. A
explicação mais provável é que cadastro não é energização — o ativo entra no cadastro
antes de entrar em operação —, então a entrada aqui é sempre um pouco mais cedo e um
pouco maior que a «expansão realizada» do gestor. O RT tem ainda um segundo problema,
registrado na aba de alertas: setembro de 2022 sozinho traz 18 reguladores, cara de
migração de cadastro em lote, não de obra.

Grava dist/PARQUE_MENSAL.xlsx.
Rodar: python3 scripts/parque_mensal_2024.py [planilha_abertura_ss.xlsx]
"""

import json
import os
import sys
from collections import Counter, defaultdict

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, Reference, Series
from openpyxl.chart.data_source import AxDataSource, StrRef
from openpyxl.drawing.colors import ColorChoice
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PADRAO_ENTRADA = os.path.join(RAIZ, "data", "raw", "ABERTURA_DE_SS_2024.xlsx")
SAIDA = os.path.join(RAIZ, "dist", "PARQUE_MENSAL.xlsx")

TINTA, PAPEL, SINAL = "FF211D15", "FFF2EFE6", "FFBC4B0E"
COR_A, COR_B = "1F7C50", "B8480C"

ABAS = {"RELIGADOR - 79": "RL", "REGULADOR - 58": "RT"}
# o parque de agosto/2026 da régua do gestor (24/08) — a âncora da curva
ANCORA = {"RL": 1294, "RT": 190}
FIM = "2026-08"
# o que o OBS diz quando a linha é mexida de cadastro, não entrada de equipamento
RUIDO = ("ATUALIZAÇÃO", "ATUALIZACAO", "REMANEJ", "JÁ ESTÁ EM OPERAÇÃO",
         "JA ESTA EM OPERACAO", "AJUSTE DE ROTA", "MINSAIT")
# a expansão que o gestor deu em 24/08, para 2026 jan–jul
ANCORA_2026 = {"RL": 13, "RT": 10}


def mes_de(bruto):
    """dd/mm/aaaa… ou aaaa-mm-dd… -> aaaa-mm."""
    if not bruto or len(str(bruto)) < 10:
        return None
    s = str(bruto)
    return s[:7] if s[4:5] == "-" else f"{s[6:10]}-{s[3:5]}"


def tipo_do_codigo(cod):
    if cod.startswith(("79", "78")):
        return "RL"
    return "RT" if cod.startswith("58") else None


def ler_cadastro(caminho):
    """Menor DTA_ORIG por ativo, com o OBS daquela linha."""
    wb = load_workbook(caminho, data_only=True)
    cad, obs = {}, {}
    for aba in ABAS:
        if aba not in wb.sheetnames:
            continue
        for linha in wb[aba].iter_rows(min_row=4, values_only=True):
            cod, orig, observacao = linha[1], linha[3], linha[5]
            if not cod or not hasattr(orig, "year"):
                continue
            cod = str(cod).strip()
            if cod not in cad or orig < cad[cod]:
                cad[cod], obs[cod] = orig, (observacao or "")
    wb.close()
    return cad, obs


def primeira_ss():
    """O mês da primeira SS de cada ativo, nas duas bases que o projeto tem."""
    prim = {}

    def registra(ativo, mes):
        if ativo and mes and (ativo not in prim or mes < prim[ativo]):
            prim[ativo] = mes

    caminho = os.path.join(RAIZ, "data", "missao", "ss_ocorrencia.json")
    with open(caminho, encoding="utf-8") as fh:
        for r in json.load(fh):
            registra(str(r.get("EQUIPAMENTO", "")).strip(),
                     mes_de(r.get("DTA_ABERTURA") or ""))
    caminho = os.path.join(RAIZ, "data", "missao", "ssos_min.json")
    with open(caminho, encoding="utf-8") as fh:
        for r in json.load(fh):
            registra(r["NUM_TRAFO"], mes_de(r["DATA_ABERTURA_SS"]))
    return prim


def montar(caminho):
    cad, obs = ler_cadastro(caminho)
    prim = primeira_ss()

    novos, descartados = [], []
    for cod, orig in cad.items():
        tipo = tipo_do_codigo(cod)
        if not tipo:
            continue
        mes = f"{orig.year}-{orig.month:02d}"
        anterior = prim.get(cod)
        if anterior and anterior < mes:
            descartados.append([cod, tipo, mes, "SS anterior ao cadastro", anterior])
            continue
        sujo = next((k for k in RUIDO if k in obs[cod].upper()), None)
        if sujo:
            descartados.append([cod, tipo, mes, "OBS de mexida de cadastro",
                                obs[cod][:60]])
            continue
        novos.append({"ativo": cod, "tipo": tipo, "mes": mes,
                      "data": orig, "obs": obs[cod][:80],
                      "primeira_ss": anterior or ""})

    entrada = defaultdict(Counter)
    for n in novos:
        entrada[n["mes"]][n["tipo"]] += 1

    meses = [f"{ano}-{m:02d}" for ano in (2024, 2025, 2026)
             for m in range(1, 13) if f"{ano}-{m:02d}" <= FIM]

    # de trás pra frente: o parque no fim de cada mês
    parque, corrente = {}, dict(ANCORA)
    for mes in reversed(meses):
        parque[mes] = dict(corrente)
        for t in ("RL", "RT"):
            corrente[t] -= entrada[mes][t]
    inicio = dict(corrente)
    return novos, descartados, entrada, parque, meses, inicio


# ------------------------------------------------------------------ a planilha
def cabeca(ws, linha, titulo, cols, larguras=None):
    ws.cell(row=linha, column=1, value=titulo).font = Font(bold=True, size=11,
                                                           color=SINAL)
    ws.append(cols)
    for i in range(1, len(cols) + 1):
        c = ws.cell(row=linha + 1, column=i)
        c.font = Font(bold=True, color=PAPEL, size=10)
        c.fill = PatternFill("solid", fgColor=TINTA)
        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if larguras:
        for i, w in enumerate(larguras, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
    return linha + 2


def fecha(ws, linha, n):
    for i in range(1, n + 1):
        ws.cell(row=linha, column=i).font = Font(bold=True)
        ws.cell(row=linha, column=i).border = Border(
            top=Side(style="medium", color=TINTA))


def planilha(novos, descartados, entrada, parque, meses, inicio):
    wb = Workbook()

    # 1 — a série mensal, com o crescimento de cada mês
    ws = wb.active
    ws.title = "Parque mensal"
    r0 = cabeca(ws, 1,
                "Entrada de equipamento, parque e crescimento em cada mês",
                ["Mês", "Entrada RL", "Parque RL", "Cresce RL",
                 "Entrada RT", "Parque RT", "Cresce RT",
                 "Entrada total", "Parque total", "Cresce total",
                 "Acumulado desde jan/24"],
                [12, 11, 11, 10, 11, 11, 10, 12, 12, 11, 20])
    for i, mes in enumerate(meses):
        ant = parque[meses[i - 1]] if i else inicio
        e_rl, e_rt = entrada[mes]["RL"], entrada[mes]["RT"]
        p_rl, p_rt = parque[mes]["RL"], parque[mes]["RT"]
        ws.append([
            mes,
            e_rl, p_rl, (e_rl / ant["RL"]) if ant["RL"] else 0,
            e_rt, p_rt, (e_rt / ant["RT"]) if ant["RT"] else 0,
            e_rl + e_rt, p_rl + p_rt,
            ((e_rl + e_rt) / (ant["RL"] + ant["RT"])) if (ant["RL"] + ant["RT"]) else 0,
            ((p_rl + p_rt) / (inicio["RL"] + inicio["RT"]) - 1),
        ])
        for col in (4, 7, 10, 11):
            ws.cell(row=ws.max_row, column=col).number_format = "0.0%"
    ws.append(["TOTAL", sum(entrada[m]["RL"] for m in meses), "",
               (parque[FIM]["RL"] / inicio["RL"] - 1) if inicio["RL"] else 0,
               sum(entrada[m]["RT"] for m in meses), "",
               (parque[FIM]["RT"] / inicio["RT"] - 1) if inicio["RT"] else 0,
               sum(entrada[m]["RL"] + entrada[m]["RT"] for m in meses), "",
               ((parque[FIM]["RL"] + parque[FIM]["RT"]) /
                (inicio["RL"] + inicio["RT"]) - 1), ""])
    for col in (4, 7, 10):
        ws.cell(row=ws.max_row, column=col).number_format = "0.0%"
    fecha(ws, ws.max_row, 11)
    r1 = ws.max_row - 1
    ws.freeze_panes = f"A{r0}"
    ws.append([])
    ws.append([f"Ponto de partida — parque no início de janeiro de 2024: "
               f"RL {inicio['RL']} · RT {inicio['RT']} · "
               f"total {inicio['RL'] + inicio['RT']}"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True, size=11, color=SINAL)

    g = BarChart()
    g.type, g.grouping, g.overlap = "col", "stacked", 100
    g.title = "Entrada de equipamento por mês"
    g.height, g.width, g.gapWidth = 8, 24, 60
    for col, cor in ((2, COR_A), (5, COR_B)):
        s = Series(Reference(ws, min_col=col, min_row=r0 - 1, max_row=r1),
                   title_from_data=True)
        s.graphicalProperties.solidFill = ColorChoice(srgbClr=cor)
        s.graphicalProperties.line.noFill = True
        g.series.append(s)
    cats = AxDataSource(strRef=StrRef(f=f"'{ws.title}'!$A${r0}:$A${r1}"))
    for s in g.series:
        s.cat = cats
    g.x_axis.axPos, g.y_axis.axPos = "b", "l"
    g.x_axis.delete = g.y_axis.delete = False
    ws.add_chart(g, "I2")

    g2 = LineChart()
    g2.title = "Parque acumulado"
    g2.height, g2.width = 8, 24
    for col, cor in ((3, COR_A), (6, COR_B)):
        s = Series(Reference(ws, min_col=col, min_row=r0 - 1, max_row=r1),
                   title_from_data=True)
        s.graphicalProperties.line.solidFill = ColorChoice(srgbClr=cor)
        s.graphicalProperties.line.width = 22000
        s.smooth = False
        g2.series.append(s)
    for s in g2.series:
        s.cat = cats
    g2.x_axis.axPos, g2.y_axis.axPos = "b", "l"
    g2.x_axis.delete = g2.y_axis.delete = False
    ws.add_chart(g2, "I20")

    # 2 — o crescimento fechado por ano
    wsa = wb.create_sheet("Crescimento por ano")
    r0 = cabeca(wsa, 1, "Quanto o parque cresceu em cada ano",
                ["Ano", "Tipo", "Parque no início", "Entrou", "Parque no fim",
                 "Cresceu", "Média por mês", "Meses"],
                [10, 8, 15, 10, 14, 11, 14, 8])
    anos = [("2024", "2024-01", "2024-12"), ("2025", "2025-01", "2025-12"),
            ("2026 (até ago)", "2026-01", "2026-08")]
    for rot, ini, fim in anos:
        do_ano = [m for m in meses if ini <= m <= fim]
        n_meses = len(do_ano)
        anterior = inicio if ini == "2024-01" else parque[
            meses[meses.index(do_ano[0]) - 1]]
        for tipo in ("RL", "RT", "total"):
            if tipo == "total":
                p_ini = anterior["RL"] + anterior["RT"]
                p_fim = parque[do_ano[-1]]["RL"] + parque[do_ano[-1]]["RT"]
                ent = sum(entrada[m]["RL"] + entrada[m]["RT"] for m in do_ano)
            else:
                p_ini, p_fim = anterior[tipo], parque[do_ano[-1]][tipo]
                ent = sum(entrada[m][tipo] for m in do_ano)
            wsa.append([rot if tipo == "RL" else "", tipo.upper(), p_ini, ent,
                        p_fim, (p_fim / p_ini - 1) if p_ini else 0,
                        round(ent / n_meses, 1), n_meses])
            wsa.cell(row=wsa.max_row, column=6).number_format = "0.0%"
            if tipo == "total":
                for c in range(1, 9):
                    wsa.cell(row=wsa.max_row, column=c).font = Font(bold=True)
    fecha(wsa, wsa.max_row, 8)

    wsa.append([])
    wsa.append(["O período inteiro, de janeiro de 2024 a agosto de 2026:"])
    wsa.cell(row=wsa.max_row, column=1).font = Font(bold=True, size=11)
    for tipo in ("RL", "RT", "total"):
        if tipo == "total":
            p_ini, p_fim = inicio["RL"] + inicio["RT"], \
                parque[FIM]["RL"] + parque[FIM]["RT"]
            ent = sum(entrada[m]["RL"] + entrada[m]["RT"] for m in meses)
        else:
            p_ini, p_fim, ent = inicio[tipo], parque[FIM][tipo], \
                sum(entrada[m][tipo] for m in meses)
        wsa.append(["32 meses", tipo.upper(), p_ini, ent, p_fim,
                    (p_fim / p_ini - 1) if p_ini else 0,
                    round(ent / len(meses), 1), len(meses)])
        wsa.cell(row=wsa.max_row, column=6).number_format = "0.0%"

    # 3 — os ativos que entraram, um por linha
    ws2 = wb.create_sheet("Ativos que entraram")
    cabeca(ws2, 1, f"Os {len(novos)} ativos contados como entrada",
           ["Ativo", "Tipo", "Mês", "Data do cadastro (DTA_ORIG)",
            "OBS da planilha", "1ª SS (se houver)"],
           [14, 7, 10, 22, 50, 14])
    for n in sorted(novos, key=lambda x: (x["mes"], x["tipo"], x["ativo"])):
        ws2.append([n["ativo"], n["tipo"], n["mes"],
                    n["data"].strftime("%d/%m/%Y"), n["obs"], n["primeira_ss"]])
    ws2.freeze_panes = "A3"
    ws2.auto_filter.ref = f"A2:F{ws2.max_row}"

    # 3 — o que ficou de fora, e por quê
    ws3 = wb.create_sheet("Descartados")
    cabeca(ws3, 1,
           f"As {len(descartados)} linhas de cadastro que NÃO contam como entrada",
           ["Ativo", "Tipo", "Mês do cadastro", "Por que saiu", "Evidência"],
           [14, 7, 14, 28, 60])
    for d in sorted(descartados, key=lambda x: (x[3], x[2], x[0])):
        ws3.append(d)
    ws3.freeze_panes = "A3"
    ws3.auto_filter.ref = f"A2:E{ws3.max_row}"
    por_motivo = Counter(d[3] for d in descartados)
    ws3.append([])
    for motivo, n in por_motivo.most_common():
        ws3.append(["", "", "", motivo, n])

    # 4 — a conferência contra o que o gestor deu
    ws4 = wb.create_sheet("Confere")
    r0 = cabeca(ws4, 1, "Esta conta contra as âncoras do gestor",
                ["O que", "Esta conta", "Gestor", "Diferença"], [46, 13, 13, 13])
    jan_jul = [m for m in meses if "2026-01" <= m <= "2026-07"]
    linhas = [
        ["Parque RL em ago/2026 (âncora da curva)", parque[FIM]["RL"],
         ANCORA["RL"], parque[FIM]["RL"] - ANCORA["RL"]],
        ["Parque RT em ago/2026 (âncora da curva)", parque[FIM]["RT"],
         ANCORA["RT"], parque[FIM]["RT"] - ANCORA["RT"]],
        ["Expansão RL 2026 jan–jul", sum(entrada[m]["RL"] for m in jan_jul),
         ANCORA_2026["RL"], sum(entrada[m]["RL"] for m in jan_jul) - ANCORA_2026["RL"]],
        ["Expansão RT 2026 jan–jul", sum(entrada[m]["RT"] for m in jan_jul),
         ANCORA_2026["RT"], sum(entrada[m]["RT"] for m in jan_jul) - ANCORA_2026["RT"]],
        ["Parque RL oficial (régua dos três anos)", parque[FIM]["RL"], 1307,
         parque[FIM]["RL"] - 1307],
        ["Parque RT oficial (régua dos três anos)", parque[FIM]["RT"], 207,
         parque[FIM]["RT"] - 207],
    ]
    for linha in linhas:
        ws4.append(linha)
    fecha(ws4, ws4.max_row, 4)
    ws4.append([])
    for t in [
        "O que fecha e o que não fecha:",
        "",
        "Agosto de 2026 fecha por construção — a curva foi ancorada ali, não é prova.",
        "",
        "A prova de verdade é 2026 jan–jul: esta conta dá 20 RL e 14 RT contra os 13 e",
        "10 do gestor. Sobra em torno de 50%, e a explicação mais provável é que cadastro",
        "não é energização: o ativo entra no cadastro antes de entrar em operação, então",
        "a entrada aqui é mais cedo e um pouco maior que a «expansão realizada».",
        "",
        "Contra o parque OFICIAL (1.307 RL e 207 RT) a diferença é outra coisa: o oficial",
        "é régua fixa dos três anos, para dividir taxa de falha, e já embute os 10 que",
        "estavam previstos para 2026. Não é medição de parque em agosto.",
    ]:
        ws4.append([t])
        if t.endswith(":"):
            ws4.cell(row=ws4.max_row, column=1).font = Font(bold=True, size=11)
    ws4.column_dimensions["A"].width = 46

    # 5 — o que não fecha e só o gestor resolve
    ws5 = wb.create_sheet("Alertas")
    cabeca(ws5, 1, "O que não fecha, e que só o gestor decide",
           ["Alerta", "Onde", "O que foi encontrado"], [34, 14, 88])
    alertas = [
        ["Cadastro não é energização", "toda a série",
         "DTA_ORIG é a data em que o ativo entrou no cadastro. Entre cadastrar e "
         "energizar passa tempo, e é por isso que 2026 jan–jul dá 20 RL aqui e 13 na "
         "régua do gestor. Para bater no dia, precisaria da data de energização."],
        ["Regulador em lote antes de 2024", "RT, set/2022",
         "Setembro de 2022 sozinho traz 18 reguladores com DTA_ORIG no mesmo mês — cara "
         "de migração de cadastro, não de obra. Fica fora da janela de 2024, mas mostra "
         "que o cadastro de RT tem evento em lote."],
        ["O parque de RT cresce 67%", "RT, 2024 a 2026",
         "A curva sai de 114 reguladores no começo de 2024 e chega em 190. A régua "
         "oficial trata 207 como constante nos três anos. Ou o cadastro de RT "
         "superconta, ou a régua fixa esconde um parque que cresceu muito."],
        ["O PN 2024 domina a série de RL", "RL, set a nov/2024",
         "35, 36 e 45 religadores em três meses — 116 dos 279 do período inteiro. Bate "
         "com o que as SS dizem em texto («inserção de RL PN 2024»), então é expansão "
         "real, não ruído de cadastro."],
        ["Ativo sem SS nenhuma", "28 ativos",
         "Entraram no cadastro e nunca tiveram SS. Contados como entrada, porque não há "
         "evidência de que existissem antes — mas sem SS não dá para confirmar."],
    ]
    for a in alertas:
        ws5.append(a)
    for r in range(3, ws5.max_row + 1):
        ws5.cell(row=r, column=3).alignment = Alignment(wrap_text=True, vertical="top")
        ws5.row_dimensions[r].height = 46

    # 6 — a régua
    ws6 = wb.create_sheet("Como foi feito")
    ws6.column_dimensions["A"].width = 98
    texto = [
        "O crescimento do parque, mês a mês, de 2024 até agosto de 2026",
        "",
        "De onde vem a data de entrada:",
        "Da planilha de controle de abertura de SS do gestor (3. ABERTURA DE SS 2024.1),",
        "abas RELIGADOR - 79 e REGULADOR - 58, coluna DTA_ORIG — a data de origem do",
        "cadastro do ativo. É a única data de nascimento de equipamento que existe em",
        "qualquer base do projeto: os Ajustes RL Poste não têm coluna de data nenhuma e",
        "o cadastro de RT só tem DATA ESTUDO, que é revisada em equipamento velho.",
        "",
        "Os dois filtros, nesta ordem:",
        "1. Se o ativo já tinha SS ANTES do próprio DTA_ORIG, ele já existia — o cadastro",
        "   foi mexido depois. Sai. (151 linhas)",
        "2. Se o OBS diz «atualização», «remanejado», «já está em operação», «ajuste de",
        "   rota» ou «minsait», é mexida de cadastro. Sai.",
        "",
        "A primeira SS de cada ativo vem das duas bases juntas: ss_ocorrencia.json (a base",
        "de repasses, 2018 a 2026) e ssos_min.json (o recorte de SS/OS). Sem a base de",
        "repasses o filtro não funcionaria — ela é a única que enxerga antes de 2022.",
        "",
        "Por que a curva é de trás pra frente:",
        "O parque de agosto de 2026 é conhecido (1.294 RL e 190 RT, régua do gestor de",
        "24/08). O de janeiro de 2024 não. Então ancora no que se sabe e desconta as",
        "entradas mês a mês para achar o começo — 1.015 RL e 114 RT.",
        "",
        "O que esta conta NÃO tem:",
        "Saída de equipamento. Religador que foi desativado, retirado ou substituído por",
        "outro código não aparece em lugar nenhum das bases, então a curva só sobe. Se",
        "houve baixa no período, o parque de 2024 era maior que os 1.015 daqui.",
        "",
        "As duas tentativas que furaram antes, para não repetir:",
        "Reconstrução pelo AIC — abandonada, dava 174 RL em 2024.",
        "Reconstrução pela movimentação de SS — 425 RL entre 2024 e 2026, superconta por",
        "um fator de 3, porque primeira SS não é entrada de equipamento.",
    ]
    for t in texto:
        ws6.append([t])
    ws6["A1"].font = Font(bold=True, size=12, color=SINAL)
    for n, t in enumerate(texto, start=1):
        if t.endswith(":"):
            ws6.cell(row=n, column=1).font = Font(bold=True, size=11)

    for aba in wb.worksheets:
        for linha in aba.iter_rows():
            for c in linha:
                if c.value is not None:
                    c.font = Font(name="Arial", bold=c.font.bold,
                                  size=c.font.size or 10, color=c.font.color)

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    wb.save(SAIDA)
    return SAIDA


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else PADRAO_ENTRADA
    novos, descartados, entrada, parque, meses, inicio = montar(caminho)
    print(f"entradas contadas: {len(novos)} "
          f"(RL {sum(1 for n in novos if n['tipo'] == 'RL')} · "
          f"RT {sum(1 for n in novos if n['tipo'] == 'RT')})")
    print(f"descartadas: {len(descartados)}")
    print(f"parque no começo de 2024: RL {inicio['RL']} · RT {inicio['RT']}")
    print(f"parque em {FIM}: RL {parque[FIM]['RL']} · RT {parque[FIM]['RT']}")
    print("gravado:", planilha(novos, descartados, entrada, parque, meses, inicio))


if __name__ == "__main__":
    main()
