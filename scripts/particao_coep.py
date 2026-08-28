"""
A partição dos 143 na régua fechada em 28/08.

Duas decisões do gestor, no mesmo dia, que mudam as duas pontas da conta:

1. QUEM VOLTOU NÃO CONTA COMO RESOLVIDO. «Se voltaram eu não resolvi» — o equipamento
   que resolveu uma demanda no ano e voltou para a fila conta só como pendente. Tira
   os 11 sobrepostos dos resolvidos.

2. QUEM SAIU DO CAMPO CONTA. Os que estão em ajuste de proteção ou comissionamento
   tiveram a peça trocada e o campo devolveu: a parte do COEP e a do COCM terminaram,
   falta o braço seguinte. Conferido na cadeia — todos os 18 passaram por um COCM
   antes, e em 15 deles a cadeia já saiu do campo.

   Os 3 que ainda ESTÃO num COCM ficam de fora: a obra está acontecendo agora. Eles
   entram assim que a equipe devolver.

Resultado: 86 resolvidos · 54 na fila · 3 em execução no campo = 143, e a conta do
posto fecha em 86 + 54 = 140.

Grava data/missao/particao_coep.json.
Rodar: python3 scripts/particao_coep.py [base_de_repasse.xlsx]
"""

import json
import os
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import sla_manutencao as base  # noqa: E402
import sla_por_equipe as eq  # noqa: E402

SAIDA = os.path.join(RAIZ, "data", "missao", "particao_coep.json")
COEP = os.path.join(RAIZ, "data", "missao", "coep_2026.json")


def ainda_no_campo(ss_atual, reg, anterior):
    """A cadeia termina numa equipe de campo? Então a obra ainda está acontecendo."""
    cad = base.cadeia(eq.do_comeco(base.norm(ss_atual), anterior), reg)
    ultimo = cad[-1][1]["posto"] if cad and cad[-1][1] else ""
    postos = [x[1]["posto"] for x in cad if x[1]]
    return "-RD-" in ultimo, [p for p in postos if "-RD-" in p]


def montar(caminho=None):
    reg = base.base_de_repasse(caminho)
    anterior = eq.raizes(reg)
    with open(COEP, encoding="utf-8") as fh:
        cp = json.load(fh)

    at = {a["ativo"]: a for a in cp["ativos"]}
    res = {r["ativo"]: r for r in cp["resolvidos_do_coep"]
           if r["conta_como_resolvido_pelo_coep"]}
    fila = {a for a, v in at.items() if v["segue_no_posto"]}
    voltaram = set(res) & fila

    itens, execucao = [], []
    for r in cp["pendentes_em_outra_mesa"]:
        no_campo, passou = ainda_no_campo(r["ss_atual"], reg, anterior)
        registro = {
            "ativo": r["ativo"], "tipo": r["tipo"], "localidade": r["localidade"],
            "ss_atual": r["ss_atual"], "onde_esta": r["onde_esta"],
            "etapa": r["etapa_da_esteira"], "dias_la": r["dias_la"],
            "passou_por_cocm": passou,
        }
        if no_campo:
            registro["situacao"] = "Em execução no campo"
            registro["nota"] = ("a cadeia termina num COCM — a obra está acontecendo "
                                "agora; entra nos resolvidos quando a equipe devolver")
            execucao.append(registro)
        else:
            registro["situacao"] = "Resolvido"
            registro["nota"] = ("peça trocada e campo devolveu; falta o braço seguinte "
                                f"({r['etapa_da_esteira'].split('—')[0].strip()})")
            itens.append(registro)

    resolvidos = sorted((set(res) - voltaram) | {x["ativo"] for x in itens})
    pacote = {
        "regua": "gestor, 28/08: quem voltou para a fila não conta como resolvido; quem "
                 "saiu do campo para ajuste ou comissionamento conta. Os que ainda estão "
                 "num COCM ficam em execução até a equipe devolver.",
        "contas": {
            "passaram": len(at),
            "resolvidos": len(resolvidos),
            "na_fila": len(fila),
            "em_execucao_no_campo": len(execucao),
            "conta_do_posto": len(resolvidos) + len(fila),
            "voltaram_para_a_fila": len(voltaram),
            "vieram_de_outra_mesa": len(itens),
        },
        "por_tipo": dict(Counter(
            "RL" if a[:2] in ("79", "78") else "RT" for a in resolvidos)),
        "resolvidos_por_outra_mesa": itens,
        "em_execucao": execucao,
        "voltaram": sorted(voltaram),
    }
    assert (pacote["contas"]["resolvidos"] + pacote["contas"]["na_fila"]
            + pacote["contas"]["em_execucao_no_campo"] == len(at)), "a partição não fecha"
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar(sys.argv[1] if len(sys.argv) > 1 else None)
    c = p["contas"]
    print(f"gravado: {SAIDA}")
    print(f"  {c['resolvidos']} resolvidos · {c['na_fila']} na fila · "
          f"{c['em_execucao_no_campo']} em execução = {c['passaram']}")
    print(f"  conta do posto: {c['resolvidos']} + {c['na_fila']} = {c['conta_do_posto']}")
    print(f"  dos resolvidos, {c['vieram_de_outra_mesa']} vieram de outra mesa · "
          f"{c['voltaram_para_a_fila']} voltaram e saíram da conta")
    print(f"  por tipo: {p['por_tipo']}")
    for x in p["em_execucao"]:
        print(f"    em execução: {x['ativo']} · {x['localidade']} · {x['onde_esta']} · "
              f"{x['dias_la']}d")
