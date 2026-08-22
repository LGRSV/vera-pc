"""
A planilha da visão ETO — o filtro do gestor em Excel, com o balde de cada um.

Lê data/missao/visao_consolidada.json (rodar scripts/visao_consolidada.py antes)
e grava dist/VISAO_ETO.xlsx com duas abas: a lista dos ativos e o passo a passo
de como o filtro foi feito, para conferência direta no SGM.

Rodar: python3 scripts/planilha_visao_eto.py
"""

import json
import os

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "dist", "VISAO_ETO.xlsx")

BALDE_NOME = {
    "ajuste_de_protecao": "Em fase de ajuste de proteção",
    "comissionamento": "Aguardando comissionamento",
    "dcmd_execucao": "DCMD — em execução (COCM's)",
    "dcmd_logistica": "DCMD — em logística",
    "dcmd_aquisicao": "DCMD — em processo de aquisição",
    "dmsl_novos": "1º ataque do DMSL",
}

COMO_FOI_FEITO = [
    "O FILTRO — na base de SS/OS (a de 20/08/2026), três cortes, nesta ordem:",
    "1. Código do equipamento (NUM_TRAFO) começando com 79 (religador) ou 58 (regulador).",
    "2. Tipo da SS (TIPOSS) = INDISPONIBILIDADE PARA OPERAÇÃO.",
    "3. Situação (SITUACAO_SS) = SS PENDENTE.",
    "Resultado: 93 SS pendentes, uma por ativo — 93 equipamentos.",
    "",
    "Por que REPASSADA não conta: quando a SS é repassada, o SGM abre outra SS no posto "
    "seguinte — a viva é a nova, e é ela que aparece como pendente. Atendida e cancelada "
    "são cadeia fechada.",
    "",
    "O BALDE — sai do POSTO onde a SS pendente está (o prefixo do número da SS), que é a "
    "régua da esteira:",
    "• ETO-PROT → em fase de ajuste de proteção.",
    "• ETO-TELE / ETO-SE com CRITICIDADE DEFINIDA na aba de mapeamento por criticidade → "
    "aguardando comissionamento.",
    "• ETO-TELE / ETO-SE SEM criticidade definida (fora da aba, ou «Sem classificação») → "
    "1º ataque do DMSL — régua do gestor, 22/08: são os novos, que ainda não passaram "
    "pelo COEP.",
    "• ETO-RD-* (equipe de campo) → DCMD em execução, com os COCM's.",
    "• ETO-COEP → DCMD: quem a aba marca «Em logística» está em logística (material "
    "comprado, esperando chegar); todo o restante pendente no posto está em processo de "
    "aquisição.",
    "",
    "A aba de mapeamento por criticidade (Relação de Indisponíveis, ATUALIZADA 16) entra "
    "como ANOTAÇÃO: dá a criticidade, a etapa que ela dizia e mostra quem ela nem lista — "
    "18 dos 93 estão fora dela.",
    "",
    "Os de aquisição foram cruzados com o plano de compras de 17/07 pelo código do ativo: "
    "11 dos 46 estão no plano.",
    "",
    "A régua de quem entra é a BASE, não a carteira (gestor, 22/08): «só tem 93, então são "
    "as 93». Quem está na carteira sem SS de indisponibilidade pendente fica de fora — e "
    "quem tem SS pendente fica dentro mesmo sem estar na carteira.",
]


def montar():
    with open(os.path.join(RAIZ, "data", "missao", "visao_consolidada.json"),
              encoding="utf-8") as fh:
        vc = json.load(fh)
    v = vc["visao_eto"]

    wb = openpyxl.Workbook()
    tit = Font(bold=True, color="FFFFFF", size=10)
    fundo = PatternFill("solid", fgColor="1F3864")
    borda = Border(*[Side(style="thin", color="BFBFBF")] * 4)

    ws = wb.active
    ws.title = f"Visão ETO ({v['total']})"
    colunas = ["Balde", "Ativo", "Tipo", "Localidade", "SS pendente", "Posto da SS",
               "Criticidade (aba de mapeamento)", "Etapa na aba", "Está na aba",
               "No plano de compras"]
    larguras = [30, 14, 8, 24, 22, 14, 16, 24, 10, 12]
    ws.append(colunas)
    for c, larg in enumerate(larguras, 1):
        cel = ws.cell(row=1, column=c)
        cel.font, cel.fill = tit, fundo
        cel.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[cel.column_letter].width = larg
    ws.freeze_panes = "A2"

    sn = lambda b: "sim" if b else "não"
    for balde in BALDE_NOME:
        for i in v["baldes"][balde]["ativos"]:
            ws.append([
                BALDE_NOME[balde], i["ativo"], i["tipo"], i["localidade"],
                i["ss_pendente"], i["ss_pendente"].split()[0],
                i["criticidade"] or "—", i["etapa_da_planilha"], sn(i["na_carteira"]),
                (sn(i["no_plano_de_compras"]) if "no_plano_de_compras" in i else "—"),
            ])
    for linha in ws.iter_rows(min_row=2):
        for cel in linha:
            cel.border = borda
            cel.alignment = Alignment(vertical="top")

    ws2 = wb.create_sheet("Como foi feito")
    ws2.column_dimensions["A"].width = 110
    for txt in COMO_FOI_FEITO:
        ws2.append([txt])
        ws2.cell(row=ws2.max_row, column=1).alignment = Alignment(wrap_text=True,
                                                                  vertical="top")

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    wb.save(SAIDA)
    print(f"gravado: {SAIDA} — {v['total']} ativos")


if __name__ == "__main__":
    montar()
