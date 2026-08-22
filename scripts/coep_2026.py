"""
Quem passou pelo posto do COEP em 2026 — a conta de verdade.

O que atrapalha essa conta: SS repassada não tem data de conclusão. Sai vazia na
base. Quem contar «SS do COEP ainda sem conclusão» como se estivesse no posto hoje
puxa para 2026 uma SS de 2020 que saiu do COEP no mesmo ano. Foi o que deu 442 SS
herdadas numa primeira contagem — número falso.

A saída certa vem da cadeia de repasse: quando a SS foi repassada, ela saiu do posto
no dia em que a SS seguinte foi aberta. Então, para cada SS do COEP:

    saída  =  data de conclusão, se houver
              senão, abertura da SS seguinte (SS_APOS_REPASSE)
              senão, ainda está no posto

E «passou pelo COEP em 2026» é a SS cujo intervalo [chegada, saída] cruza o ano.

A conta principal é de EQUIPAMENTO, não de SS: o mesmo religador pode ter três SS no
posto no mesmo ano e continua sendo um equipamento.

Grava data/missao/coep_2026.json e dist/COEP_2026.xlsx.

Rodar: python3 scripts/coep_2026.py
"""

import csv
import datetime
import json
import os
import re
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ_SS = os.path.join(RAIZ, "data", "missao", "ss_ocorrencia.json")
ARQ_CARTEIRA = os.path.join(RAIZ, "data", "raw", "equipamentos_especiais.csv")
SAIDA_JSON = os.path.join(RAIZ, "data", "missao", "coep_2026.json")
SAIDA_XLSX = os.path.join(RAIZ, "dist", "COEP_2026.xlsx")

POSTO = "ETO-COEP"
INICIO = datetime.datetime(2026, 1, 1)
FIM = datetime.datetime(2026, 8, 18, 23, 59)
RE_SS = re.compile(r"([A-Z][A-Z-]*)\s+0*(\d+)/(\d{4})")


def norm(numero):
    m = RE_SS.match((numero or "").strip().upper())
    return f"{m.group(1)} {int(m.group(2))}/{m.group(3)}" if m else (numero or "").strip().upper()


def dia(texto):
    try:
        return datetime.datetime.strptime((texto or "")[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def indexar():
    with open(ARQ_SS, encoding="utf-8") as fh:
        base = json.load(fh)
    idx = {}
    for x in base:
        x["_id"] = norm(x["SS_ORIGINAL"])
        x["_abriu"] = dia(x.get("DTA_ABERTURA"))
        x["_concluiu"] = dia(x.get("DTA_CONCLUSAO"))
        antes = idx.get(x["_id"])
        if antes is None or (x["_abriu"] and antes["_abriu"] and x["_abriu"] > antes["_abriu"]):
            idx[x["_id"]] = x
    seguinte = {x["_id"]: norm(x["SS_APOS_REPASSE"]) for x in idx.values()
                if x.get("SS_APOS_REPASSE")}
    return idx, seguinte


def carteira():
    """A carteira consolidada do gestor — 129 ativos, com o marcador de concluída."""
    with open(ARQ_CARTEIRA, encoding="utf-8") as fh:
        linhas = [x for x in csv.DictReader(fh, delimiter=";")
                  if (x.get("Ativo") or "").strip().isdigit()]
    todos, resolvidos = {}, set()
    for x in linhas:
        cod = x["Ativo"].strip()
        todos[cod] = {
            "tipo": "religador" if (x.get("Tipo") or "").strip() == "79" else "regulador",
            "localidade": (x.get("Localidade") or "").strip(),
            "ss_da_carteira": (x.get("SS aberta") or "").strip(),
            "parecer_coep": (x.get("Parecer COEP") or "").strip(),
            "check": (x.get("Check de concluídas") or "").strip(),
            "criticidade": (x.get("Criticidade") or "").strip(),
        }
        if (x.get("SS aberta") or "").strip().upper() == "CONCLUÍDA":
            resolvidos.add(cod)
    return todos, resolvidos


def montar():
    idx, seguinte = indexar()
    cart, resolvidos = carteira()

    def saida(x):
        if x["_concluiu"]:
            return x["_concluiu"], "conclusão da SS", ""
        prox = seguinte.get(x["_id"])
        if prox and prox in idx and idx[prox]["_abriu"]:
            return idx[prox]["_abriu"], "repasse — abertura da SS seguinte", idx[prox]["POSTO_SGM"]
        return None, "ainda no posto", ""

    no_posto, por_ativo = [], defaultdict(list)
    for x in idx.values():
        if x["POSTO_SGM"] != POSTO or not x["_abriu"]:
            continue
        quando, como, destino = saida(x)
        limite = quando or FIM
        if not (x["_abriu"] <= FIM and limite >= INICIO):
            continue
        item = {
            "ss": x["SS_ORIGINAL"], "ativo": x["EQUIPAMENTO"],
            "tipo": x["TIPO_ATIVO"].lower(), "status": x["STATUS"],
            "chegou": x["_abriu"].strftime("%d/%m/%Y"),
            "saiu": quando.strftime("%d/%m/%Y") if quando else "",
            "como_apurou_a_saida": como, "foi_para": destino,
            "dias_no_posto": (limite - x["_abriu"]).days,
            "chegou_em_2026": x["_abriu"] >= INICIO,
            "saiu_em_2026": bool(quando and INICIO <= quando <= FIM),
            "segue_no_posto": quando is None or quando > FIM,
            "pendencia": x.get("PENDENCIA_DO_ATIVO", ""),
            "ano_da_ss": x["ANO_SS"],
        }
        no_posto.append(item)
        por_ativo[x["EQUIPAMENTO"]].append(item)

    ativos = []
    for cod, itens in sorted(por_ativo.items()):
        c = cart.get(cod)
        ativos.append({
            "ativo": cod, "tipo": itens[0]["tipo"], "ss_no_coep_em_2026": len(itens),
            "ss": " | ".join(i["ss"] for i in itens),
            "primeira_chegada": min(i["chegou"] for i in itens),
            "dias_no_posto": max(i["dias_no_posto"] for i in itens),
            "chegou_em_2026": any(i["chegou_em_2026"] for i in itens),
            "ja_estava_de_antes": any(not i["chegou_em_2026"] for i in itens),
            "saiu_em_2026": any(i["saiu_em_2026"] for i in itens),
            "segue_no_posto": any(i["segue_no_posto"] for i in itens),
            "na_carteira": bool(c),
            "resolvido_na_carteira": cod in resolvidos,
            "parecer_coep": (c or {}).get("parecer_coep", ""),
            "criticidade": (c or {}).get("criticidade", ""),
            "localidade": (c or {}).get("localidade", ""),
            "ss_da_carteira": (c or {}).get("ss_da_carteira", ""),
        })

    codigos = {a["ativo"] for a in ativos}
    # já passou pelo COEP alguma vez, em qualquer ano?
    coep_de_sempre = defaultdict(set)
    for x in idx.values():
        if x["POSTO_SGM"] == POSTO and x["_abriu"]:
            coep_de_sempre[x["EQUIPAMENTO"]].add(x["_abriu"].year)
    resolvidos_fora = []
    for cod in sorted(resolvidos - codigos):
        c = cart[cod]
        ultima = [x for x in idx.values() if x["EQUIPAMENTO"] == cod]
        ultima.sort(key=lambda x: x["_abriu"] or INICIO, reverse=True)
        u = ultima[0] if ultima else None
        anos = sorted(coep_de_sempre.get(cod, ()))
        if anos:
            motivo = ("passou pelo COEP em " + ", ".join(str(a) for a in anos) +
                      " — saiu do posto antes de 2026 e só o fechamento veio depois")
        elif u:
            motivo = (f"nunca teve SS no COEP; a demanda ficou no {u['POSTO_SGM']} "
                      "e foi resolvida por lá")
        else:
            motivo = "sem SS de religador ou regulador nesta base"
        resolvidos_fora.append({
            "ativo": cod, "tipo": c["tipo"], "localidade": c["localidade"],
            "parecer_coep": c["parecer_coep"],
            "passou_pelo_coep_em": ", ".join(str(a) for a in anos) or "nunca",
            "ultima_ss_conhecida": u["SS_ORIGINAL"] if u else "",
            "posto_da_ultima_ss": u["POSTO_SGM"] if u else "",
            "abertura_da_ultima_ss": (u["DTA_ABERTURA"] or "")[:10] if u else "",
            "motivo": motivo,
        })

    conta = {
        "equipamentos_que_passaram": len(ativos),
        "por_tipo": dict(Counter(a["tipo"] for a in ativos)),
        "ss_no_posto": len(no_posto),
        "chegaram_em_2026": sum(1 for a in ativos if a["chegou_em_2026"]),
        "ja_estavam_de_antes": sum(1 for a in ativos if a["ja_estava_de_antes"]),
        "sairam_do_posto_em_2026": sum(1 for a in ativos if a["saiu_em_2026"]),
        "seguem_no_posto_em_18_08": sum(1 for a in ativos if a["segue_no_posto"]),
        "na_carteira_consolidada": sum(1 for a in ativos if a["na_carteira"]),
        "fora_da_carteira": sum(1 for a in ativos if not a["na_carteira"]),
        "resolvidos_na_carteira": sum(1 for a in ativos if a["resolvido_na_carteira"]),
        "resolvidos_na_carteira_total": len(resolvidos),
        "resolvidos_sem_passagem_pelo_coep_em_2026": len(resolvidos_fora),
    }

    pacote = {
        "gerado_em": "2026-08-22", "posicao": "18/08/2026",
        "fonte": "EQP_SS_OCORRENCIA_11082026 (10.386 SS de religador e regulador) e a carteira "
                 "consolidada do gestor (Relação dos Equipamentos Indisponíveis ETO, "
                 "ATUALIZADA 16 — 129 ativos)",
        "premissas": PREMISSAS,
        "conta": conta,
        "ativos": ativos,
        "ss": no_posto,
        "resolvidos_sem_passagem": resolvidos_fora,
    }
    with open(SAIDA_JSON, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


PREMISSAS = [
    "Passou pelo COEP em 2026 é a SS que esteve no posto em algum momento do ano — não só a "
    "que chegou em 2026. SS que chegou em 2025 e só saiu em março de 2026 passou pelo posto.",
    "A data de saída não está na base para SS repassada: o campo de conclusão vem vazio. A saída "
    "é a abertura da SS seguinte, aquela gravada em SS_APOS_REPASSE. Sem isso a conta erra feio "
    "— SS de 2020 e 2021 entram como se ainda estivessem no posto.",
    "Ordem de apuração da saída: conclusão da SS, se houver; senão a abertura da SS seguinte; "
    "senão a SS ainda está no posto. Das 694 SS do COEP na base: 153 pela conclusão, 486 pelo "
    "repasse, 55 ainda no posto.",
    "A conta principal é de EQUIPAMENTO, não de SS. O mesmo religador com três SS no posto no "
    "mesmo ano é um equipamento. O número de SS vai ao lado.",
    "O ano vai até 18/08/2026, a posição do relatório. Quem ainda está no posto nessa data conta "
    "como tendo passado.",
    "Chegou em 2026 e já estava de antes somam mais que o total porque o mesmo equipamento pode "
    "ter uma SS herdada e outra nova no mesmo ano.",
    "A carteira consolidada é a Relação dos Equipamentos Indisponíveis ETO, versão ATUALIZADA 16, "
    "com 129 ativos. Resolvido é o ativo cuja coluna «SS aberta» está marcada CONCLUÍDA — 52.",
    "Resolvido na carteira sem SS no COEP dentro de 2026 não é erro: ou o equipamento passou pelo "
    "posto em ano anterior e o fechamento veio depois, ou quem resolveu foi outro posto.",
    "Só religador e regulador. A base de ocorrência traz 8.835 SS de religador e 1.551 de "
    "regulador, com data de ocorrência em 100% das linhas.",
]


def planilha(pacote):
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    tit = Font(bold=True, color="FFFFFF", size=10)
    fundo = PatternFill("solid", fgColor="1F3864")
    borda = Border(*[Side(style="thin", color="BFBFBF")] * 4)
    forte = Font(bold=True)

    def cabecalho(ws, colunas, larguras):
        ws.append(colunas)
        for c, (col, larg) in enumerate(zip(colunas, larguras), 1):
            cel = ws.cell(row=1, column=c)
            cel.font, cel.fill = tit, fundo
            cel.alignment = Alignment(vertical="center", wrap_text=True)
            ws.column_dimensions[cel.column_letter].width = larg
        ws.freeze_panes = "A2"

    def fechar(ws):
        for linha in ws.iter_rows(min_row=2):
            for cel in linha:
                cel.border = borda
                cel.alignment = Alignment(vertical="top", wrap_text=True)

    sn = lambda v: "sim" if v else "não"
    c = pacote["conta"]

    ws = wb.active
    ws.title = "A conta"
    cabecalho(ws, ["O que está sendo contado", "Equipamentos", "Observação"], [46, 14, 78])
    for rot, val, obs in [
        ("Passaram pelo posto do COEP em 2026", c["equipamentos_que_passaram"],
         f"{c['ss_no_posto']} SS no posto — {c['por_tipo'].get('religador',0)} religadores e "
         f"{c['por_tipo'].get('regulador',0)} reguladores"),
        ("   dos quais chegaram em 2026", c["chegaram_em_2026"], "SS aberta no COEP dentro do ano"),
        ("   dos quais já estavam de antes", c["ja_estavam_de_antes"],
         "chegaram em ano anterior e ainda estavam no posto em 2026"),
        ("   saíram do posto dentro de 2026", c["sairam_do_posto_em_2026"],
         "por conclusão da SS ou por repasse para outro posto"),
        ("   seguem no posto em 18/08/2026", c["seguem_no_posto_em_18_08"],
         "sem conclusão e sem SS seguinte"),
        ("Estão na carteira consolidada", c["na_carteira_consolidada"],
         "dos 129 ativos da carteira ATUALIZADA 16"),
        ("Não estão na carteira", c["fora_da_carteira"],
         "passaram pelo posto mas nunca entraram na planilha de acompanhamento"),
        ("Passaram pelo COEP E estão resolvidos na carteira", c["resolvidos_na_carteira"],
         f"de {c['resolvidos_na_carteira_total']} resolvidos na carteira inteira"),
        ("Resolvidos na carteira sem passar pelo COEP em 2026",
         c["resolvidos_sem_passagem_pelo_coep_em_2026"],
         "passaram em ano anterior, ou foram resolvidos por outro posto"),
    ]:
        ws.append([rot, val, obs])
    ws.cell(row=2, column=1).font = forte
    ws.cell(row=2, column=2).font = forte
    fechar(ws)

    ws = wb.create_sheet("Passaram pelo COEP em 2026")
    cabecalho(ws, ["Ativo", "Tipo", "SS no COEP em 2026", "Quantas SS", "Primeira chegada",
                   "Dias no posto", "Chegou em 2026", "Já estava de antes", "Saiu em 2026",
                   "Segue no posto", "Está na carteira", "Resolvido na carteira",
                   "Parecer COEP", "Criticidade", "Localidade"],
              [14, 12, 40, 10, 14, 12, 11, 12, 11, 11, 12, 13, 24, 12, 20])
    for a in pacote["ativos"]:
        ws.append([a["ativo"], a["tipo"], a["ss"], a["ss_no_coep_em_2026"], a["primeira_chegada"],
                   a["dias_no_posto"], sn(a["chegou_em_2026"]), sn(a["ja_estava_de_antes"]),
                   sn(a["saiu_em_2026"]), sn(a["segue_no_posto"]), sn(a["na_carteira"]),
                   sn(a["resolvido_na_carteira"]), a["parecer_coep"], a["criticidade"],
                   a["localidade"]])
    fechar(ws)

    ws = wb.create_sheet("COEP 2026 x carteira resolvida")
    cabecalho(ws, ["Ativo", "Tipo", "SS no COEP em 2026", "Primeira chegada", "Dias no posto",
                   "Saiu em 2026", "Segue no posto", "SS na carteira", "Parecer COEP",
                   "Criticidade", "Localidade"],
              [14, 12, 40, 14, 12, 11, 12, 14, 26, 12, 20])
    for a in pacote["ativos"]:
        if not a["resolvido_na_carteira"]:
            continue
        ws.append([a["ativo"], a["tipo"], a["ss"], a["primeira_chegada"], a["dias_no_posto"],
                   sn(a["saiu_em_2026"]), sn(a["segue_no_posto"]), a["ss_da_carteira"],
                   a["parecer_coep"], a["criticidade"], a["localidade"]])
    fechar(ws)

    ws = wb.create_sheet("Resolvidos sem passar em 2026")
    cabecalho(ws, ["Ativo", "Tipo", "Localidade", "Parecer COEP", "Passou pelo COEP em",
                   "Última SS conhecida", "Posto dessa SS", "Abertura dessa SS",
                   "Por que não aparece"],
              [14, 12, 20, 26, 18, 22, 16, 15, 62])
    for r in pacote["resolvidos_sem_passagem"]:
        ws.append([r["ativo"], r["tipo"], r["localidade"], r["parecer_coep"],
                   r["passou_pelo_coep_em"], r["ultima_ss_conhecida"], r["posto_da_ultima_ss"],
                   r["abertura_da_ultima_ss"], r["motivo"]])
    fechar(ws)

    ws = wb.create_sheet("SS no COEP em 2026")
    cabecalho(ws, ["SS", "Ativo", "Tipo", "Status", "Chegou", "Saiu",
                   "Como se apurou a saída", "Foi para", "Dias no posto", "Pendência"],
              [22, 14, 12, 16, 12, 12, 30, 14, 12, 26])
    for i in sorted(pacote["ss"], key=lambda x: -x["dias_no_posto"]):
        ws.append([i["ss"], i["ativo"], i["tipo"], i["status"], i["chegou"], i["saiu"],
                   i["como_apurou_a_saida"], i["foi_para"], i["dias_no_posto"], i["pendencia"]])
    fechar(ws)

    ws = wb.create_sheet("Como foi feito")
    cabecalho(ws, ["Passo", "O que foi feito"], [8, 130])
    for n, texto in enumerate(pacote["premissas"], 1):
        ws.append([n, texto])
    fechar(ws)

    os.makedirs(os.path.dirname(SAIDA_XLSX), exist_ok=True)
    wb.save(SAIDA_XLSX)


def main():
    pacote = montar()
    c = pacote["conta"]
    print(f"passaram pelo COEP em 2026........ {c['equipamentos_que_passaram']} equipamentos "
          f"({c['por_tipo']}) em {c['ss_no_posto']} SS")
    print(f"  chegaram em 2026................ {c['chegaram_em_2026']}")
    print(f"  já estavam de antes............. {c['ja_estavam_de_antes']}")
    print(f"  saíram do posto em 2026......... {c['sairam_do_posto_em_2026']}")
    print(f"  seguem no posto em 18/08........ {c['seguem_no_posto_em_18_08']}")
    print(f"na carteira consolidada........... {c['na_carteira_consolidada']} "
          f"(fora: {c['fora_da_carteira']})")
    print(f"resolvidos na carteira e que passaram: {c['resolvidos_na_carteira']} "
          f"de {c['resolvidos_na_carteira_total']}")
    print(f"resolvidos sem passar pelo COEP em 2026: "
          f"{c['resolvidos_sem_passagem_pelo_coep_em_2026']}")
    print(f"gravado: {SAIDA_JSON}")
    planilha(pacote)
    print(f"gravado: {SAIDA_XLSX}")


if __name__ == "__main__":
    main()
