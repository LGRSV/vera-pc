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

    # Visão 2: quem o COEP resolveu em 2026. Resolvido no primeiro ataque do DMSL não
    # conta — a demanda morreu na mão da DMSL, o posto não trabalhou nela.
    resolvidos_do_coep = []
    dentro = {a["ativo"]: a for a in ativos}
    for cod in sorted(resolvidos):
        c = cart[cod]
        a = dentro.get(cod)
        primeiro_ataque = "primeiro ataque" in (c["parecer_coep"] or "").lower()
        if primeiro_ataque:
            entra, porque = False, "resolvido no primeiro ataque do DMSL — não é trabalho do posto"
        elif a is None:
            entra, porque = False, "não teve SS no COEP dentro de 2026 — quem resolveu foi outro posto"
        else:
            entra, porque = True, "passou pelo posto em 2026 e a carteira registra concluída"
        resolvidos_do_coep.append({
            "ativo": cod, "tipo": c["tipo"], "localidade": c["localidade"],
            "parecer_coep": c["parecer_coep"], "criticidade": c["criticidade"],
            "passou_pelo_coep_em_2026": bool(a),
            "ss_no_coep_em_2026": (a or {}).get("ss", ""),
            "dias_no_posto": (a or {}).get("dias_no_posto", ""),
            "primeiro_ataque_dmsl": primeiro_ataque,
            "conta_como_resolvido_pelo_coep": entra, "porque": porque,
        })

    conta = {
        "equipamentos_que_passaram": len(ativos),
        "resolvidos_pelo_coep": sum(1 for r in resolvidos_do_coep
                                    if r["conta_como_resolvido_pelo_coep"]),
        "tirados_por_primeiro_ataque_dmsl": sum(1 for r in resolvidos_do_coep
                                                if r["primeiro_ataque_dmsl"]),
        "tirados_por_nao_passar_pelo_coep": sum(
            1 for r in resolvidos_do_coep
            if not r["conta_como_resolvido_pelo_coep"] and not r["primeiro_ataque_dmsl"]),
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
        "resolvidos_do_coep": resolvidos_do_coep,
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
    "VISÃO 2 — resolvido pelo COEP em 2026: o ativo está marcado CONCLUÍDA na carteira "
    "consolidada E teve SS no COEP dentro de 2026.",
    "Resolvido no primeiro ataque do DMSL NÃO conta. A demanda morreu na mão da DMSL; o posto "
    "não trabalhou nela. São 15 dos 52 concluídos da carteira — 14 nunca tiveram SS no COEP e "
    "1 chegou a passar pelo posto.",
    "Concluído da carteira que nunca teve SS no COEP dentro de 2026 também não conta como "
    "resolvido pelo posto — quem resolveu foi outro.",
]


def planilha(pacote):
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    tit = Font(bold=True, color="FFFFFF", size=10)
    fundo = PatternFill("solid", fgColor="1F3864")
    borda = Border(*[Side(style="thin", color="BFBFBF")] * 4)
    cinza = PatternFill("solid", fgColor="EFEFEF")

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

    # VISÃO 1 — quem passou pelo posto em 2026
    ws = wb.active
    ws.title = f"1 · Passaram pelo COEP ({c['equipamentos_que_passaram']})"
    cabecalho(ws, ["Ativo", "Tipo", "Localidade", "SS no COEP em 2026", "Quantas SS",
                   "Primeira chegada", "Dias no posto", "Ainda no posto em 18/08",
                   "Está na carteira", "Parecer COEP", "Criticidade"],
              [14, 12, 20, 40, 10, 14, 12, 14, 12, 26, 12])
    for a in sorted(pacote["ativos"], key=lambda x: -x["dias_no_posto"]):
        ws.append([a["ativo"], a["tipo"], a["localidade"], a["ss"], a["ss_no_coep_em_2026"],
                   a["primeira_chegada"], a["dias_no_posto"], sn(a["segue_no_posto"]),
                   sn(a["na_carteira"]), a["parecer_coep"], a["criticidade"]])
    fechar(ws)

    # VISÃO 2 — quem o COEP resolveu em 2026
    ws = wb.create_sheet(f"2 · Resolvidos pelo COEP ({c['resolvidos_pelo_coep']})")
    cabecalho(ws, ["Ativo", "Tipo", "Localidade", "Conta como resolvido pelo COEP",
                   "Por quê", "Passou pelo COEP em 2026", "Primeiro ataque DMSL",
                   "SS no COEP em 2026", "Dias no posto", "Parecer COEP", "Criticidade"],
              [14, 12, 20, 16, 54, 14, 14, 36, 12, 26, 12])
    ordem = sorted(pacote["resolvidos_do_coep"],
                   key=lambda r: (not r["conta_como_resolvido_pelo_coep"], r["ativo"]))
    for r in ordem:
        ws.append([r["ativo"], r["tipo"], r["localidade"],
                   sn(r["conta_como_resolvido_pelo_coep"]), r["porque"],
                   sn(r["passou_pelo_coep_em_2026"]), sn(r["primeiro_ataque_dmsl"]),
                   r["ss_no_coep_em_2026"], r["dias_no_posto"], r["parecer_coep"],
                   r["criticidade"]])
    fechar(ws)
    for n, r in enumerate(ordem, 2):
        if not r["conta_como_resolvido_pelo_coep"]:
            for cel in ws[n]:
                cel.fill = cinza

    # o método, para as duas
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
    print(f"VISÃO 1 — passaram pelo COEP em 2026: {c['equipamentos_que_passaram']} equipamentos "
          f"({c['por_tipo']['religador']} RL + {c['por_tipo']['regulador']} RT) em "
          f"{c['ss_no_posto']} SS; {c['seguem_no_posto_em_18_08']} ainda no posto em 18/08")
    print(f"VISÃO 2 — resolvidos PELO COEP em 2026: {c['resolvidos_pelo_coep']}")
    print(f"  de {c['resolvidos_na_carteira_total']} concluídos na carteira")
    print(f"  tirados por primeiro ataque do DMSL...: {c['tirados_por_primeiro_ataque_dmsl']}")
    print(f"  tirados por não passar pelo COEP.....: {c['tirados_por_nao_passar_pelo_coep']}")
    print(f"gravado: {SAIDA_JSON}")
    planilha(pacote)
    print(f"gravado: {SAIDA_XLSX}")


if __name__ == "__main__":
    main()
