"""
Planilha da taxa de falha — dist/TAXA_DE_FALHA_RL_RT.xlsx.

Espelha a página dist/taxa-falha.html, em linguagem simples:

  Taxa de falha    religador e regulador, 2024/2025/2026, na fórmula do gestor:
                   equipamentos que falharam (peça grande) ÷ parque do ano
  O que falhou     a peça de cada família por ano, e o rol das ocorrências
                   confirmadas, uma a uma, com a evidência e o motivo da revisão
  Resolvidos       o contraponto: o que o posto tirou da mesa em cada ano
  Como foi feito   o passo a passo e as premissas

Grava valores, não fórmulas: LibreOffice não sobe neste ambiente.

Rodar: python3 scripts/taxa_falha_excel.py
"""

import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ_TAXA = os.path.join(RAIZ, "data", "missao", "taxa_falha.json")
ARQ_LEITURA = os.path.join(RAIZ, "data", "missao", "leitura_ss_os.json")
SAIDA = os.path.join(RAIZ, "dist", "TAXA_DE_FALHA_RL_RT.xlsx")

ANOS = ("2024", "2025", "2026")
ROT = {"religador": "RELIGADORES", "regulador": "REGULADORES"}
FATOR = {"2024": 1.0, "2025": 1.0, "2026": 0.611}

TINTA = "1A1A1A"
FAIXA = "E8E4DC"
DESTAQUE = "C8442A"

fina = Side(style="thin", color="8A8577")
grossa = Side(style="medium", color=TINTA)
GRADE = Border(left=fina, right=fina, top=fina, bottom=fina)


def _ler(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def _titulo(ws, texto, sub, largura):
    ws["A1"] = texto
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=TINTA)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=largura)
    ws["A2"] = sub
    ws["A2"].font = Font(name="Calibri", size=11, italic=True, color="5A5347")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=largura)
    ws.row_dimensions[2].height = 32
    return 4


def _cab(ws, linha, colunas):
    for i, nome in enumerate(colunas, start=1):
        c = ws.cell(row=linha, column=i, value=nome)
        c.font = Font(name="Calibri", size=11, bold=True, color=TINTA)
        c.fill = PatternFill("solid", fgColor=FAIXA)
        c.border = Border(left=fina, right=fina, top=grossa, bottom=grossa)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[linha].height = 30
    return linha + 1


def _lin(ws, linha, valores, negrito=True, destaque_col=None, quebra=False):
    for i, v in enumerate(valores, start=1):
        c = ws.cell(row=linha, column=i, value=v)
        cor = DESTAQUE if destaque_col is not None and i == destaque_col else TINTA
        c.font = Font(name="Calibri", size=12, bold=negrito, color=cor)
        c.border = GRADE
        c.alignment = Alignment(
            horizontal="left" if isinstance(v, str) else "center",
            vertical="top" if quebra else "center", wrap_text=quebra)
    return linha + 1


def _larguras(ws, ls):
    for i, w in enumerate(ls, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def aba_taxa(wb, taxa, leitura):
    ws = wb.create_sheet("Taxa de falha")
    _larguras(ws, [16, 14, 13, 16, 18, 14, 22, 10])
    linha = _titulo(
        ws, "Taxa de falha — religadores e reguladores da ETO",
        "Fórmula: equipamentos que falharam no ano ÷ parque do ano. Falha é o que exigiu peça "
        "grande — religador: controle, tanque ou completo; regulador: célula, relé, completo ou "
        "furto. Fonte: leitura das SS e OS pelos agentes, revisada, mais a troca por obra direta "
        "do AIC. Posição de 12/08/2026; 2026 ajustado pela fração decorrida (61%).", 8)

    ppa = taxa.get("parque_por_ano") or {}
    for fam in ("religador", "regulador"):
        linha = _lin(ws, linha, [ROT[fam]], negrito=True)
        linha = _cab(ws, linha, ["Ano", "Parque do ano", "Novos no ano", "Na carteira lida",
                                 "Troca por obra direta", "Ocorrências",
                                 "Equipamentos que falharam", "Taxa"])
        for ano in ANOS:
            p = (ppa.get(fam) or {}).get(ano, {})
            k = f"{fam}|{ano}"
            carteira = (leitura.get("contagem") or {}).get(k, 0)
            obra = (leitura.get("complemento_obra_direta") or {}).get(k, 0)
            n = (leitura.get("total_equipamentos_que_falharam") or {}).get(k, carteira + obra)
            eq = (p.get("medio") or 0) * FATOR[ano]
            taxa_pct = round(100.0 * n / eq, 1) if eq else None
            linha = _lin(ws, linha, [
                f"{ano}" + (" (até 12/08)" if ano == "2026" else ""),
                p.get("medio"), f"+{p.get('instalados_no_ano')}",
                carteira, obra, (leitura.get("ocorrencias") or {}).get(k, 0),
                n, f"{taxa_pct}%".replace(".", ",")], destaque_col=8)
        linha += 1
    return ws


def aba_o_que_falhou(wb, leitura):
    ws = wb.create_sheet("O que falhou")
    _larguras(ws, [13, 12, 7, 12, 26, 11, 12, 60, 70])
    linha = _titulo(
        ws, "O que falhou — peça a peça, e cada ocorrência confirmada",
        "Cada linha do rol é uma falha que sobreviveu à revisão: a SS que sustenta, a data que "
        "ancorou o ano, se a troca já foi executada, o trecho do texto que prova e o motivo do "
        "revisor para manter.", 9)

    pp = leitura.get("por_peca") or {}
    for fam in ("religador", "regulador"):
        pecas = sorted({ch.split("|")[2] for ch in pp if ch.startswith(fam + "|")})
        linha = _lin(ws, linha, [ROT[fam] + " — por peça"], negrito=True)
        linha = _cab(ws, linha, ["Ano"] + [p.title() for p in pecas] + ["Total"])
        for ano in ANOS:
            vals = [pp.get(f"{fam}|{ano}|{p}", 0) for p in pecas]
            linha = _lin(ws, linha, [ano] + vals + [sum(vals)])
        linha += 1

    linha += 1
    linha = _lin(ws, linha, ["ROL DAS OCORRÊNCIAS CONFIRMADAS"], negrito=True)
    linha = _cab(ws, linha, ["Ativo", "Família", "Ano", "Peça", "SS", "Data",
                             "Troca executada?", "Evidência no texto", "O que o revisor conferiu"])
    detalhe = sorted(leitura.get("detalhe") or [],
                     key=lambda f: (f["familia"], f["ano"], f["ativo"]))
    for f in detalhe:
        linha = _lin(ws, linha, [
            f.get("ativo"), f.get("familia"), f.get("ano"), f.get("peca"),
            f.get("ss"), f.get("data"), "sim" if f.get("executada") else "não",
            (f.get("evidencia") or "")[:280], (f.get("revisao_motivo") or "")[:300],
        ], negrito=False, quebra=True)

    linha += 1
    descartes = leitura.get("descartes") or []
    if descartes:
        linha = _lin(ws, linha, [f"O QUE A REVISÃO DERRUBOU ({len(descartes)})"], negrito=True)
        linha = _cab(ws, linha, ["Ativo", "Família", "Ano", "Peça", "SS", "", "", "Motivo", ""])
        for d in descartes:
            linha = _lin(ws, linha, [
                d.get("ativo"), d.get("familia"), d.get("ano"), d.get("peca"),
                d.get("ss"), "", "", (d.get("motivo") or "")[:300], ""],
                negrito=False, quebra=True)
    return ws


def aba_resolvidos(wb, taxa):
    ws = wb.create_sheet("Resolvidos")
    _larguras(ws, [16, 30, 26, 28])
    linha = _titulo(
        ws, "O contraponto — o que o posto resolveu em cada ano",
        "Demandas de falha encerradas é a SS que terminou (atendida ou cancelada) — a única "
        "comparável entre anos. Obra encerrada no contábil vem sempre atrasada: as obras de "
        "2026 ainda não fecharam no sistema — é atraso de papel, não queda de produção.", 4)
    res = taxa.get("resolvidos_por_ano") or {}
    dem = res.get("demandas_de_falha_encerradas") or {}
    campo = res.get("obra_de_substituicao_concluida_em_campo") or {}
    contab = res.get("obra_de_substituicao_encerrada_no_contabil") or {}
    linha = _cab(ws, linha, ["Ano", "Demandas de falha encerradas", "Obra concluída em campo",
                             "Obra encerrada no contábil"])
    for ano in ANOS:
        d = dem.get(ano) or {}
        linha = _lin(ws, linha, [
            f"{ano}" + (" (até 12/08)" if ano == "2026" else ""),
            f"{sum(d.values())}  ({d.get('religador', 0)} RL · {d.get('regulador', 0)} RT)",
            sum((campo.get(ano) or {}).values()),
            sum((contab.get(ano) or {}).values())])
    linha += 1
    proj = round(sum((dem.get("2026") or {}).values()) / 0.611)
    linha = _lin(ws, linha, [
        "2026 está no ritmo mais alto já registrado: mantido o ritmo, fecha em torno de "
        f"{proj} — empata com 2025 e fica bem acima de 2024."], quebra=True)
    ws.merge_cells(start_row=linha - 1, start_column=1, end_row=linha - 1, end_column=4)
    ws.row_dimensions[linha - 1].height = 30
    return ws


def aba_como(wb, taxa, leitura):
    ws = wb.create_sheet("Como foi feito")
    _larguras(ws, [5, 120])
    linha = _titulo(
        ws, "Como foi feito — o passo a passo e as premissas",
        "Cada número da planilha depende do que está escrito aqui. "
        "Premissa que muda, número que muda.", 2)

    passos = [
        "Separar o que é falha do que é serviço: ajustes, comissionamentos, obras novas, "
        "cadastro e preventivas ficam de fora.",
        "Juntar as SS gêmeas: o mesmo defeito repassado de equipe em equipe gera SS nova a "
        "cada passagem — todas viram uma falha só.",
        f"Ler o texto: agentes leram a SS e a OS dos {leitura.get('ativos_lidos')} ativos da "
        f"carteira e apontaram {leitura.get('falhas_apontadas')} falhas. Revisores conferiram "
        f"cada uma contra o texto original e derrubaram {leitura.get('derrubadas_pela_revisao')} "
        f"— ficaram {leitura.get('confirmadas_pela_revisao')}.",
        "Somar quem não passou pela carteira: equipamento trocado por obra direta entra pela "
        "obra de substituição do AIC, descontando quem a leitura já contou.",
        "Datar pela ocorrência: o ano da falha é quando ela aconteceu, não quando a SS foi "
        "aberta — a abertura vem em média 65 dias depois.",
        "Dividir pelo parque do ano: o parque de hoje (1.297 religadores e 197 reguladores) "
        "menos o que foi instalado depois, na média do ano.",
    ]
    linha = _lin(ws, linha, ["O PASSO A PASSO"], negrito=True)
    for i, p in enumerate(passos, start=1):
        c1 = ws.cell(row=linha, column=1, value=i)
        c1.font = Font(size=12, bold=True, color=DESTAQUE)
        c1.alignment = Alignment(horizontal="center", vertical="top")
        c2 = ws.cell(row=linha, column=2, value=p)
        c2.font = Font(size=11, color=TINTA)
        c2.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[linha].height = max(18, 14 * (len(p) // 110 + 1))
        linha += 1

    linha += 1
    linha = _lin(ws, linha, ["AS PREMISSAS"], negrito=True)
    for i, p in enumerate(taxa.get("premissas") or [], start=1):
        c1 = ws.cell(row=linha, column=1, value=i)
        c1.font = Font(size=12, bold=True, color=DESTAQUE)
        c1.alignment = Alignment(horizontal="center", vertical="top")
        c2 = ws.cell(row=linha, column=2, value=p)
        c2.font = Font(size=11, color=TINTA)
        c2.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[linha].height = max(18, 14 * (len(p) // 110 + 1))
        linha += 1
    return ws


def main():
    taxa = _ler(ARQ_TAXA)
    leitura = _ler(ARQ_LEITURA)
    wb = Workbook()
    wb.remove(wb.active)
    aba_taxa(wb, taxa, leitura)
    aba_o_que_falhou(wb, leitura)
    aba_resolvidos(wb, taxa)
    aba_como(wb, taxa, leitura)
    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    wb.save(SAIDA)
    print("gravado:", SAIDA)
    for ws in wb.worksheets:
        print(f"  aba {ws.title}: {ws.max_row} linhas")


if __name__ == "__main__":
    main()
