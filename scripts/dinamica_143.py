"""
A dinâmica DISJUNTA dos 143 do posto do COEP em 2026 — régua do gestor de 26/08.

Cada equipamento conta UMA vez, pelo estado atual (posição 18/08). Precedência:

  1. segue_no_posto            -> «Na fila do posto»   (54)
     Quem também resolveu uma demanda no ano entra aqui marcado
     (resolvido_e_voltou), não nos resolvidos — são os −11.
  2. em pendentes_em_outra_mesa -> «Em outra mesa»     (18)
  3. nos resolvidos (conta_como_resolvido_pelo_coep)  -> «Resolvido» (82−11 = 71)

Realizado do DCMD (régua 26/08): SS atendida com equipe de campo na cadeia ou
cancelada que ficou de pé — 63 no ano, apurados em visao_consolidada.json
(concluidos_dcmd_2026). Os que voltaram para a fila saem da fatia dos 71;
o que sobra é o realizado DCMD entre os resolvidos desta partição.

A conta oficial do posto (82 resolvidos, 136 do gestor) continua valendo —
esta é outra lente da mesma base, sem dupla aparição.

Lê data/missao/coep_2026.json e data/missao/visao_consolidada.json.
Grava data/missao/dinamica_143.json. Se a partição não fechar 54+18+71=143
(ou os voltaram não forem 11), PARA com erro em vez de forçar.

Rodar: python3 scripts/dinamica_143.py
"""

import json
import os
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "data", "missao", "dinamica_143.json")

ESPERADO = {"na_fila": 54, "outra_mesa": 18, "resolvido": 71, "total": 143,
            "voltaram": 11, "dcmd_no_ano": 63}


def _data_chave(br):
    """dd/mm/aaaa -> aaaa-mm-dd, para ordenar."""
    return br[6:10] + "-" + br[3:5] + "-" + br[:2] if br else ""


def item_vazio(ativo, tipo, localidade, situacao, criticidade):
    return {"ativo": ativo, "tipo": tipo, "localidade": localidade,
            "situacao": situacao, "criticidade": criticidade or "",
            "ss": "", "desde": "", "dias": "", "resolvido_e_voltou": "",
            "como_terminou": "", "posto_que_fechou": "", "realizado_dcmd": "",
            "onde_esta": "", "etapa": "", "nota": ""}


def montar():
    with open(os.path.join(RAIZ, "data", "missao", "coep_2026.json"),
              encoding="utf-8") as fh:
        base = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "visao_consolidada.json"),
              encoding="utf-8") as fh:
        visao = json.load(fh)

    ativos = base["ativos"]
    resolvidos = {r["ativo"]: r for r in base["resolvidos_do_coep"]
                  if r.get("conta_como_resolvido_pelo_coep")}
    outra_mesa = {o["ativo"]: o for o in base["pendentes_em_outra_mesa"]}

    dcmd = visao["concluidos_dcmd_2026"]
    dcmd_ativos = {a["ativo"] for a in dcmd["ativos"]}
    if len(dcmd_ativos) != ESPERADO["dcmd_no_ano"]:
        raise SystemExit(f"FURO: realizado DCMD do ano é {len(dcmd_ativos)}, "
                         f"esperado {ESPERADO['dcmd_no_ano']} (18+45).")
    fora = dcmd_ativos - set(resolvidos)
    if fora:
        raise SystemExit(f"FURO: realizado DCMD fora dos 82 resolvidos: {sorted(fora)}")

    # SS que seguem pendentes no posto, por ativo — a demanda ATUAL de quem
    # está na fila (o agregado do ativo traz a primeira chegada do ano,
    # inclusive de demanda já resolvida de quem voltou).
    pendentes_posto = defaultdict(list)
    for s in base["ss"]:
        if s.get("segue_no_posto"):
            pendentes_posto[s["ativo"]].append(s)

    itens, voltaram = [], []
    for a in ativos:
        cod = a["ativo"]
        it = item_vazio(cod, a["tipo"], a.get("localidade", ""), "",
                        a.get("criticidade", ""))
        if a.get("segue_no_posto"):
            it["situacao"] = "Na fila do posto"
            ss_p = sorted(pendentes_posto[cod],
                          key=lambda s: _data_chave(s["chegou"]))
            if not ss_p:
                raise SystemExit(f"FURO: {cod} segue no posto sem SS pendente na lista ss.")
            it["ss"] = " | ".join(s["ss"] for s in ss_p)
            it["desde"] = ss_p[0]["chegou"]
            it["dias"] = max(s["dias_no_posto"] for s in ss_p)
            r = resolvidos.get(cod)
            if r:
                voltaram.append(cod)
                it["resolvido_e_voltou"] = True
                it["nota"] = ("resolveu uma demanda no ano e voltou — conta aqui, "
                              "não nos resolvidos. A resolvida: "
                              f"{r['como_terminou']} em {r['data_do_fechamento']} "
                              f"({r['posto_que_fechou']}).")
        elif cod in outra_mesa:
            o = outra_mesa[cod]
            it["situacao"] = "Em outra mesa"
            it["ss"] = o.get("ss_atual", "")
            it["desde"] = o.get("la_desde", "")
            it["dias"] = o.get("dias_la", "")
            it["onde_esta"] = o.get("onde_esta", "")
            it["etapa"] = o.get("etapa_da_esteira", "")
            it["nota"] = o.get("status_atual", "")
        elif cod in resolvidos:
            r = resolvidos[cod]
            it["situacao"] = "Resolvido"
            it["ss"] = r.get("ss_que_fechou", "")
            it["desde"] = r.get("data_do_fechamento", "")
            it["dias"] = r.get("dias_da_demanda", "")
            it["como_terminou"] = r.get("como_terminou", "")
            it["posto_que_fechou"] = r.get("posto_que_fechou", "")
            it["realizado_dcmd"] = cod in dcmd_ativos
            nota = r.get("prova", "")
            if r.get("tem_nota_pendente_hoje") and r.get("nota_nova_em_outro_posto"):
                nota += (f" · nota pendente em outro posto "
                         f"({r['nota_nova_em_outro_posto']}) — outra frente, "
                         "não derruba (régua 22/08)")
            it["nota"] = nota
        else:
            raise SystemExit(f"FURO: {cod} não caiu em classe nenhuma — não forço.")
        itens.append(it)

    contas = {
        "resolvido": sum(1 for i in itens if i["situacao"] == "Resolvido"),
        "na_fila": sum(1 for i in itens if i["situacao"] == "Na fila do posto"),
        "outra_mesa": sum(1 for i in itens if i["situacao"] == "Em outra mesa"),
        "total": len(itens),
        "resolvidos_que_voltaram": len(voltaram),
        "realizados_dcmd_entre_os_71": sum(1 for i in itens
                                           if i["situacao"] == "Resolvido"
                                           and i["realizado_dcmd"]),
    }
    erros = []
    for chave, quer in (("na_fila", 54), ("outra_mesa", 18), ("resolvido", 71),
                        ("total", 143), ("resolvidos_que_voltaram", 11)):
        if contas[chave] != quer:
            erros.append(f"{chave}={contas[chave]} (esperado {quer})")
    if contas["resolvido"] + contas["na_fila"] + contas["outra_mesa"] != contas["total"]:
        erros.append("a partição não soma o total")
    dcmd_que_voltou = dcmd_ativos & set(voltaram)
    if contas["realizados_dcmd_entre_os_71"] != len(dcmd_ativos) - len(dcmd_que_voltou):
        erros.append("realizado DCMD entre os 71 não bate com 63 − voltaram")
    if erros:
        raise SystemExit("FURO — a conta não fecha, não forço: " + "; ".join(erros))

    pacote = {
        "regua": ("Partição disjunta dos 143 que passaram pelo posto do COEP em "
                  "2026 — régua do gestor de 26/08: cada equipamento conta UMA "
                  "vez, pelo estado atual (posição 18/08). Precedência: na fila "
                  "do posto > em outra mesa > resolvido. Os 11 que resolveram "
                  "uma demanda no ano e voltaram para a fila contam só como "
                  "pendentes, marcados — por isso os resolvidos são 82−11=71. "
                  "Realizado do DCMD (26/08): SS atendida com equipe de campo "
                  "na cadeia ou cancelada que ficou de pé — 63 no ano "
                  f"({dcmd['atendidas_com_campo']} atendidas + "
                  f"{dcmd['canceladas_de_pe']} canceladas); "
                  f"{len(dcmd_que_voltou)} dessas voltaram para a fila, restando "
                  f"{contas['realizados_dcmd_entre_os_71']} entre os 71. A conta "
                  "oficial do posto (82 resolvidos, 136 do gestor) segue valendo "
                  "— esta é outra lente da mesma base, sem dupla aparição."),
        "gerado_em": "2026-08-26",
        "posicao": base["posicao"],
        "fonte": ("data/missao/coep_2026.json (ativos, resolvidos_do_coep com "
                  "conta_como_resolvido_pelo_coep=true, pendentes_em_outra_mesa, "
                  "ss) e data/missao/visao_consolidada.json "
                  "(concluidos_dcmd_2026)"),
        "contas": contas,
        "realizados_dcmd_que_voltaram": sorted(dcmd_que_voltou),
        "itens": itens,
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    print(f"gravado: {SAIDA}")
    print("contas:", json.dumps(contas, ensure_ascii=False))
    print("voltaram:", ", ".join(sorted(voltaram)))
    print("DCMD que voltou (saiu dos 63):", ", ".join(sorted(dcmd_que_voltou)))


if __name__ == "__main__":
    montar()
