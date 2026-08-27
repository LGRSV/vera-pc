"""
O SLA de manutenção dos COCM's — 2025 e 2026, mês a mês e por equipe.

Régua do gestor (27/08, fechada em duas rodadas):

  UNIVERSO   toda entrega ao COCM — cada vez que o posto despachou uma demanda para
             uma equipe de campo. O compromisso nasce na entrega, independente de a
             demanda ter virado «resolvida» depois.
  JANELA     do repasse AO COCM até o repasse DO COCM para outro posto. Quando o
             campo fecha sem repassar, a janela termina na conclusão da SS.
  PRAZO      pela criticidade da operação — Muito Alta 8, Alta 15, Média 30,
             Baixa 50 — e 26 dias para quem não tem criticidade definida.
  SÉRIE      mensal pelo mês da ENTREGA (coorte de entrada), com a devolução em
             coluna própria.

Nenhuma das duas datas vem de graça. A ENTREGA é a ABERTURA da SS no posto do COCM:
o campo DTA_REPASSE é cópia byte a byte da DTA_ABERTURA e não data o repasse. A
DEVOLUÇÃO é a abertura da SS seguinte — SS repassada sai da base sem conclusão, e
quem esperar a conclusão dela espera para sempre.

A varredura de cada demanda começa na SS DO COEP, não no início dela. Muita demanda
nasce no campo, e essa passagem inicial não é entrega para executar: o posto ainda
não tinha diagnosticado nem comprado nada.

Grava dist/SLA_MANUTENCAO.xlsx.
Rodar: python3 scripts/sla_por_equipe.py [base_de_repasse.xlsx]
"""

import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict

import openpyxl
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.data_source import AxDataSource, StrRef
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import sla_manutencao as base  # noqa: E402 — a leitura da base e a régua de prazo

SAIDA = os.path.join(RAIZ, "dist", "SLA_MANUTENCAO.xlsx")
ANOS = (2025, 2026)
MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]

TITULO = Font(bold=True, color="FFFFFF", size=10)
FUNDO = PatternFill("solid", fgColor="1F3864")
BORDA = Border(*[Side(style="thin", color="BFBFBF")] * 4)
VERDE = PatternFill("solid", fgColor="E2EFDA")
VERMELHO = PatternFill("solid", fgColor="FCE4E4")
AMARELO = PatternFill("solid", fgColor="FFF2CC")


def entregas_ao_cocm(reg, crit, ativos):
    """Toda entrega COEP → COCM da base, com a janela e o veredicto de cada uma."""
    saida, vistas = [], set()
    for ss, r in reg.items():
        if "COEP" not in r["posto"]:
            continue
        p = base.passagem_pelo_cocm(ss, reg)
        if not p or p["entrada"] is None or p["ss"] in vistas:
            continue
        vistas.add(p["ss"])
        ativo = ativos.get(ss, {})
        cod = ativo.get("equipamento", "")
        c = crit.get(cod, "")
        prazo = base.PRAZO.get(c, base.PRAZO_SEM_CRITICIDADE)
        aberto = p["saida"] is None
        fim = p["saida"] or base.HOJE
        # dias de CALENDÁRIO, não períodos de 24h: SLA de negócio conta o dia, e a
        # base guarda hora — entregue dia 6 às 14h e devolvido dia 8 às 9h é 2 dias.
        dias = (fim.date() - p["entrada"].date()).days
        # 18 SS da base fecham ANTES de abrir: o campo executou e o SGM abriu a SS
        # depois, para regularizar. Conta 0 dia e fica marcado — não é giro relâmpago.
        retroativa = dias < 0
        if retroativa:
            dias = 0
        dentro = dias <= prazo
        saida.append({
            "ano": p["entrada"].year, "mes": p["entrada"].month,
            "equipe": p["posto"], "ativo": cod,
            "tipo": "RL" if cod[:2] in ("79", "78") else ("RT" if cod[:2] == "58" else ""),
            "localidade": ativo.get("localidade", ""),
            "ss_coep": ss, "ss_cocm": p["ss"],
            "criticidade": c or "Sem classificação", "prazo": prazo,
            "entrega": p["entrada"], "devolucao": p["saida"],
            "dias": dias, "atraso": max(0, dias - prazo),
            "dentro_do_prazo": dentro, "em_curso": aberto,
            "veredicto": ("em curso, dentro do prazo" if dentro else "em curso, ESTOURADO")
            if aberto else ("dentro do prazo" if dentro else "ESTOURADO"),
            "destino": (p["base_da_saida"] + " · SS fechada antes de abrir (serviço "
                        "regularizado depois) — conta 0 dia") if retroativa
                       else p["base_da_saida"],
            "retroativa": retroativa, "status_no_cocm": p["status"],
        })
    return sorted(saida, key=lambda x: (x["entrega"], x["equipe"]))


def dados_do_ativo(caminho):
    """{SS: {equipamento, localidade}} — para a entrega saber de quem ela é."""
    d = {}
    if caminho and caminho.lower().endswith(".xlsx"):
        ws = openpyxl.load_workbook(caminho, read_only=True,
                                    data_only=True)["Exportar Planilha"]
        for r in list(ws.iter_rows(values_only=True))[1:]:
            k = base.norm(r[1])
            if k:
                d.setdefault(k, {"equipamento": str(r[3] or "").strip(),
                                 "localidade": str(r[15] or "").strip()})
    return d


def cabecalho(ws, colunas):
    ws.append([c[0] for c in colunas])
    linha = ws.max_row
    for i, (_, larg) in enumerate(colunas, 1):
        cel = ws.cell(row=linha, column=i)
        cel.font, cel.fill = TITULO, FUNDO
        cel.alignment = Alignment(vertical="center", wrap_text=True, horizontal="center")
        if ws.column_dimensions[get_column_letter(i)].width in (None, 13):
            ws.column_dimensions[get_column_letter(i)].width = larg
    ws.row_dimensions[linha].height = 32
    return linha


def bordar(ws, de, ate):
    for linha in ws.iter_rows(min_row=de, max_row=ate):
        for cel in linha:
            cel.border = BORDA


COLS = [("Ano", 7), ("Mês nº", 7), ("Mês", 8), ("Equipe (COCM)", 14), ("Ativo", 13),
        ("Tipo", 7), ("Localidade", 22), ("SS do COEP", 20), ("SS do COCM", 20),
        ("Criticidade", 14), ("Prazo SLA (dias)", 10), ("Entrega ao COCM", 13),
        ("Devolução", 12), ("Dias de manutenção", 11), ("Atraso (dias)", 10),
        ("Dentro do prazo", 10), ("Em curso", 9), ("SLA de manutenção", 22),
        ("Como a devolução foi apurada", 26)]


def linha_de(e):
    return [e["ano"], e["mes"], MESES[e["mes"] - 1], e["equipe"], e["ativo"], e["tipo"],
            e["localidade"], e["ss_coep"], e["ss_cocm"], e["criticidade"], e["prazo"],
            e["entrega"].strftime("%d/%m/%Y"),
            e["devolucao"].strftime("%d/%m/%Y") if e["devolucao"] else "",
            e["dias"], e["atraso"], "sim" if e["dentro_do_prazo"] else "não",
            "sim" if e["em_curso"] else "", e["veredicto"], e["destino"]]


def aba_entregas(wb, entregas):
    ws = wb.active
    ws.title = f"1 · Entregas ao COCM ({len(entregas)})"
    prim = cabecalho(ws, COLS) + 1
    for e in entregas:
        ws.append(linha_de(e))
        cel = ws.cell(row=ws.max_row, column=18)
        cel.fill = AMARELO if e["em_curso"] else (VERDE if e["dentro_do_prazo"] else VERMELHO)
    bordar(ws, prim, ws.max_row)
    ws.freeze_panes = f"A{prim}"
    ws.auto_filter.ref = f"A{prim - 1}:S{ws.max_row}"
    return ws


def quadro(ws, titulo, cabecalhos, linhas, pct_col=None):
    ws.append([titulo])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True, size=11)
    ws.append(cabecalhos)
    for cel in ws[ws.max_row]:
        if cel.value is not None:
            cel.font, cel.fill = TITULO, FUNDO
            cel.alignment = Alignment(horizontal="center", wrap_text=True)
    cab = ws.max_row
    prim = cab + 1
    for l in linhas:
        ws.append(l)
        if pct_col:
            ws.cell(row=ws.max_row, column=pct_col).number_format = "0.0%"
    bordar(ws, prim, ws.max_row)
    return cab, prim, ws.max_row


def resumo(grupo):
    """entregas · no prazo · estourou · em curso · cumprimento · mediana."""
    n = len(grupo)
    ok = sum(1 for e in grupo if e["dentro_do_prazo"])
    curso = sum(1 for e in grupo if e["em_curso"])
    dias = sorted(e["dias"] for e in grupo)
    return [n, ok, n - ok, curso, (ok / n) if n else 0,
            dias[len(dias) // 2] if dias else 0]


def aba_mensal(wb, entregas):
    ws = wb.create_sheet("2 · SLA mensal")
    ws.column_dimensions["A"].width = 22
    for c in "BCDEFGHIJKLM":
        ws.column_dimensions[c].width = 10
    ws.append(["SLA DE MANUTENÇÃO — MÊS A MÊS, PELO MÊS DA ENTREGA AO COCM"])
    ws.cell(row=1, column=1).font = Font(bold=True, size=12)
    ws.append(["A demanda entra no mês em que foi entregue. «Em curso» conta os dias "
               "até 18/08/2026 e já aparece estourada quando passou do prazo."])
    faixas = []
    for ano in ANOS:
        ws.append([])
        por_mes = defaultdict(list)
        for e in entregas:
            if e["ano"] == ano:
                por_mes[e["mes"]].append(e)
        linhas = []
        for nome, i in ((n, i + 1) for i, n in enumerate(MESES)):
            g = por_mes.get(i, [])
            r = resumo(g)
            linhas.append([nome] + r)
        total = resumo([e for e in entregas if e["ano"] == ano])
        linhas.append(["ANO"] + total)
        cab, prim, fim = quadro(
            ws, f"{ano}", ["Mês", "Entregas", "No prazo", "Estourou", "Em curso",
                           "Cumprimento", "Mediana de dias"], linhas, pct_col=6)
        for cel in ws[fim]:
            cel.font = Font(bold=True)
        faixas.append((ano, cab, prim, fim - 1))
    for ano, cab, prim, fim in faixas:
        ch = LineChart()
        ch.title = f"{ano} — entregas e cumprimento do SLA"
        ch.height, ch.width, ch.style = 7.5, 17, 2
        ch.add_data(Reference(ws, min_col=2, min_row=cab, max_row=fim),
                    titles_from_data=True)
        ch.add_data(Reference(ws, min_col=3, min_row=cab, max_row=fim),
                    titles_from_data=True)
        ref = f"'{ws.title}'!$A${prim}:$A${fim}"
        for s in ch.series:
            s.cat = AxDataSource(strRef=StrRef(f=ref))
            s.smooth = False
            s.marker.symbol, s.marker.size = "circle", 6
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.axPos, ch.y_axis.axPos = "b", "l"
        ws.add_chart(ch, f"J{cab - 1}")
    return ws


def aba_equipe(wb, entregas):
    ws = wb.create_sheet("3 · SLA por equipe")
    ws.column_dimensions["A"].width = 20
    for c in "BCDEFGHI":
        ws.column_dimensions[c].width = 12
    ws.append(["SLA DE MANUTENÇÃO — POR EQUIPE DE CAMPO"])
    ws.cell(row=1, column=1).font = Font(bold=True, size=12)
    ws.append(["Equipe é o posto do COCM que recebeu a demanda. A mediana diz o ritmo "
               "normal; o pior atraso diz a cauda."])
    faixas = []
    for ano in list(ANOS) + ["2025 + 2026"]:
        ws.append([])
        sel = [e for e in entregas
               if (e["ano"] == ano if isinstance(ano, int) else True)]
        equipes = sorted({e["equipe"] for e in sel})
        linhas = []
        for q in equipes:
            g = [e for e in sel if e["equipe"] == q]
            if not g:
                continue
            r = resumo(g)
            linhas.append([q] + r + [max(e["atraso"] for e in g)])
        linhas.sort(key=lambda l: (-l[1], l[0]))
        linhas.append(["TOTAL"] + resumo(sel) + [max((e["atraso"] for e in sel), default=0)])
        cab, prim, fim = quadro(
            ws, f"{ano}", ["Equipe", "Entregas", "No prazo", "Estourou", "Em curso",
                           "Cumprimento", "Mediana de dias", "Pior atraso"],
            linhas, pct_col=6)
        for cel in ws[fim]:
            cel.font = Font(bold=True)
        if isinstance(ano, str):
            faixas.append((cab, prim, fim - 1))
    for cab, prim, fim in faixas:
        ch = BarChart()
        ch.type, ch.gapWidth, ch.style = "bar", 40, 2
        ch.title = "Cumprimento do SLA por equipe · 2025 + 2026"
        ch.height, ch.width = 10, 15
        ch.add_data(Reference(ws, min_col=6, min_row=cab, max_row=fim),
                    titles_from_data=True)
        ch.series[0].cat = AxDataSource(strRef=StrRef(f"'{ws.title}'!$A${prim}:$A${fim}"))
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.y_axis.numFmt = "0%"
        ch.legend = None
        ws.add_chart(ch, f"K{cab - 1}")
    return ws


def aba_criticidade(wb, entregas):
    ws = wb.create_sheet("4 · SLA por criticidade")
    ws.column_dimensions["A"].width = 20
    for c in "BCDEFGH":
        ws.column_dimensions[c].width = 12
    ws.append(["SLA DE MANUTENÇÃO — POR CRITICIDADE DA OPERAÇÃO"])
    ws.cell(row=1, column=1).font = Font(bold=True, size=12)
    ordem = ["Muito Alta", "Alta", "Média", "Baixa", "Sem classificação"]
    for ano in list(ANOS) + ["2025 + 2026"]:
        ws.append([])
        sel = [e for e in entregas if (e["ano"] == ano if isinstance(ano, int) else True)]
        linhas = []
        for c in ordem:
            g = [e for e in sel if e["criticidade"] == c]
            if g:
                linhas.append([c, base.PRAZO.get(c, base.PRAZO_SEM_CRITICIDADE)] + resumo(g))
        linhas.append(["TOTAL", ""] + resumo(sel))
        cab, prim, fim = quadro(
            ws, f"{ano}", ["Criticidade", "Prazo", "Entregas", "No prazo", "Estourou",
                           "Em curso", "Cumprimento", "Mediana de dias"],
            linhas, pct_col=7)
        for cel in ws[fim]:
            cel.font = Font(bold=True)
    return ws


def aba_resolvidos(wb, entregas, caminho_base):
    """A aba de resolvidos de 2026, com as colunas de SLA para a dinâmica."""
    reg = base.base_de_repasse(caminho_base)
    crit = base.criticidades()
    with open(base.COEP, encoding="utf-8") as fh:
        cp = json.load(fh)
    por_ss = {e["ss_coep"]: e for e in entregas}
    res = [r for r in cp["resolvidos_do_coep"] if r["conta_como_resolvido_pelo_coep"]]
    ws = wb.create_sheet(f"5 · Resolvidos 2026 ({len(res)})")
    colunas = [("Ativo", 13), ("Tipo", 7), ("Localidade", 22), ("SS no COEP", 20),
               ("Como terminou", 14), ("Fechou em", 12), ("Posto que fechou", 15),
               ("Passou por COCM", 11), ("Ano da entrega", 8), ("Mês nº", 7),
               ("Mês", 8), ("Equipe (COCM)", 14), ("Criticidade", 14),
               ("Prazo SLA (dias)", 10), ("Entrega ao COCM", 13), ("Devolução", 12),
               ("Dias de manutenção", 11), ("Atraso (dias)", 10),
               ("Dentro do prazo", 10), ("SLA de manutenção", 22)]
    prim = cabecalho(ws, colunas) + 1
    for r in sorted(res, key=lambda x: x["ativo"]):
        k = base.norm(r["ss_no_coep"])
        e = por_ss.get(k)
        c = crit.get(r["ativo"], "") or "Sem classificação"
        if e:
            ws.append([r["ativo"], "RL" if r["tipo"] == "religador" else "RT",
                       r["localidade"], k, r["como_terminou"], r["data_do_fechamento"],
                       r["posto_que_fechou"], "sim", e["ano"], e["mes"],
                       MESES[e["mes"] - 1], e["equipe"], e["criticidade"], e["prazo"],
                       e["entrega"].strftime("%d/%m/%Y"),
                       e["devolucao"].strftime("%d/%m/%Y") if e["devolucao"] else "",
                       e["dias"], e["atraso"],
                       "sim" if e["dentro_do_prazo"] else "não", e["veredicto"]])
            cel = ws.cell(row=ws.max_row, column=20)
            cel.fill = AMARELO if e["em_curso"] else (VERDE if e["dentro_do_prazo"] else VERMELHO)
        else:
            ws.append([r["ativo"], "RL" if r["tipo"] == "religador" else "RT",
                       r["localidade"], k, r["como_terminou"], r["data_do_fechamento"],
                       r["posto_que_fechou"], "não", "", "", "", "", c,
                       base.PRAZO.get(c, base.PRAZO_SEM_CRITICIDADE), "", "", "", "",
                       "", "não passou por COCM depois do posto"])
    bordar(ws, prim, ws.max_row)
    ws.freeze_panes = f"A{prim}"
    ws.auto_filter.ref = f"A{prim - 1}:T{ws.max_row}"
    return ws, sum(1 for r in res if base.norm(r["ss_no_coep"]) in por_ss)


def como_foi_feito(entregas, com_cocm):
    por_ano = Counter(e["ano"] for e in entregas)
    return [
        "SLA DE MANUTENÇÃO — 2025 e 2026, mês a mês e por equipe.",
        "",
        "O UNIVERSO (escolha do gestor, 27/08): toda entrega ao COCM — cada vez que o "
        "posto despachou uma demanda para uma equipe de campo. O compromisso nasce na "
        f"entrega, independente de a demanda ter virado «resolvida» depois. São "
        f"{por_ano.get(2025, 0)} entregas em 2025 e {por_ano.get(2026, 0)} em 2026.",
        "",
        "A JANELA (régua do gestor): do repasse AO COCM até o repasse DO COCM para outro "
        "posto. Quando o campo fecha sem repassar, a janela termina na conclusão da SS.",
        "",
        "AS DUAS DATAS, e por que nenhuma vem de graça: a ENTREGA é a ABERTURA da SS no "
        "posto do COCM — o campo DTA_REPASSE da base é cópia byte a byte da DTA_ABERTURA "
        "e não data o repasse. A DEVOLUÇÃO é a abertura da SS seguinte, porque SS "
        "repassada sai da base sem data de conclusão: quem esperar a conclusão dela "
        "espera para sempre.",
        "",
        "O PRAZO, pela criticidade da operação (aba de mapeamento por criticidade da "
        "Relação de Indisponíveis): Muito Alta 8 dias, Alta 15, Média 30, Baixa 50. Sem "
        "criticidade definida, 26 dias — o prazo médio.",
        "",
        "A SÉRIE MENSAL é pelo mês da ENTREGA (coorte de entrada): a demanda entra no mês "
        "em que o compromisso foi assumido. A data de devolução está em coluna própria, "
        "para quem quiser a leitura pelo outro eixo.",
        "",
        "EM CURSO ENTRAM NA CONTA, com os dias corridos até 18/08/2026, e já aparecem "
        "estouradas quando passaram do prazo. Tirá-las faria o mês recente parecer bom "
        "só porque o que atrasou ainda não fechou — viés de sobrevivência.",
        "",
        "POR QUE A VARREDURA COMEÇA NA SS DO COEP: muita demanda nasce no campo — a "
        "equipe abre a SS e repassa para o posto —, e essa passagem inicial não é entrega "
        "para executar: o posto ainda não tinha diagnosticado nem comprado nada. Contar a "
        "cadeia inteira inflaria o número com serviço que ninguém mandou fazer.",
        "",
        "EQUIPE é o posto do COCM que recebeu (ETO-RD-*, ENC-RD-*, DOLP-RD-*, DG-RD-*, "
        "ESO-RD-*). Cada entrega conta uma vez, pela primeira equipe que recebeu depois "
        "do posto.",
        "",
        "SS FECHADA ANTES DE ABRIR: 18 SS da base inteira têm data de conclusão anterior "
        "à de abertura — o campo executou e o SGM abriu a SS depois, para regularizar. "
        "Contam 0 dia e ficam marcadas na coluna «Como a devolução foi apurada», para "
        "ninguém ler como giro relâmpago.",
        "",
        "DIAS DE CALENDÁRIO, não períodos de 24 horas: a base guarda hora, e entregue "
        "dia 6 às 14h com devolução dia 8 às 9h é 2 dias de SLA, não 1.",
        "",
        "PREMISSA REGISTRADA: a criticidade é a de hoje, aplicada também a 2025 — não "
        "existe histórico de criticidade na base. Quem foi reclassificado desde então "
        "carrega o prazo de agora.",
        "",
        f"A ABA 5 traz as 82 resolvidas de 2026 com as colunas de SLA anexadas "
        f"({com_cocm} delas passaram por COCM depois do posto); as demais ficam marcadas "
        "«não passou por COCM», porque fecharam na TELE ou na PROT — execução de outro "
        "braço, sem SLA de manutenção a cobrar do campo.",
        "",
        "TODAS AS ABAS DE LISTA TÊM FILTRO E COLUNAS CRUAS (ano, mês nº, mês, equipe, "
        "criticidade, prazo, dias, atraso, dentro do prazo) — é só selecionar e inserir "
        "tabela dinâmica para conferir qualquer corte.",
        "",
        "Fonte das datas: base de repasse (Eqp_joao / EQP_SS_OCORRENCIA), a única que "
        "traz a cadeia SS a SS. Posição de 18/08/2026.",
    ]


def montar(caminho=None):
    reg = base.base_de_repasse(caminho)
    crit = base.criticidades()
    ativos = dados_do_ativo(caminho)
    todas = entregas_ao_cocm(reg, crit, ativos)
    entregas = [e for e in todas if e["ano"] in ANOS]

    wb = openpyxl.Workbook()
    aba_entregas(wb, entregas)
    aba_mensal(wb, entregas)
    aba_equipe(wb, entregas)
    aba_criticidade(wb, entregas)
    _, com_cocm = aba_resolvidos(wb, entregas, caminho)
    ws = wb.create_sheet("Como foi feito")
    ws.column_dimensions["A"].width = 112
    for t in como_foi_feito(entregas, com_cocm):
        ws.append([t])
        ws.cell(row=ws.max_row, column=1).alignment = Alignment(wrap_text=True, vertical="top")
    ws.cell(row=1, column=1).font = Font(bold=True, size=12)

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    wb.save(SAIDA)
    return entregas, todas


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else None
    entregas, todas = montar(caminho)
    print(f"gravado: {SAIDA}")
    print(f"  entregas na base inteira: {len(todas)} · em 2025-2026: {len(entregas)}")
    for ano in ANOS:
        g = [e for e in entregas if e["ano"] == ano]
        ok = sum(1 for e in g if e["dentro_do_prazo"])
        curso = sum(1 for e in g if e["em_curso"])
        dias = sorted(e["dias"] for e in g)
        print(f"  {ano}: {len(g)} entregas · {ok} no prazo ({100*ok/len(g):.1f}%) · "
              f"{curso} em curso · mediana {dias[len(dias)//2]}d")
