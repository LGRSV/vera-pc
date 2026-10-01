"""
Conferência dirigida das SS IRMÃS — prova de serviço que o dossiê mostrou cortada.

O dossiê da retrospectiva traz por inteiro só as cadeias que passaram pelo COEP; as outras cadeias do
mesmo ativo aparecem numa linha, com o fim do último texto. Mas o serviço muitas vezes é registrado numa
SS que nasce FORA da cadeia — a de comissionamento aberta pela TELE depois da troca, a nota de linha viva
do COCM. Na verificação, prova de SS fora do dossiê não vale, e o serviço some.

Este script lista, para cada demanda sem execução provada, as SS do mesmo ativo FORA da cadeia, abertas
depois do começo dela, cujo texto tem frase de serviço feito. Não decide nada: o orquestrador lê cada
trecho e grava a correção (com a frase literal) em <run>/correcoes.json, que o juntar_retro.py aplica por
cima da verificação.

Rodar: python3 .claude/skills/analise-equipamento/scripts/irmas_retro.py .analise/retro2026
"""

import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import sla_falhas_regional as sf    # noqa: E402
import tempo_ss as ts               # noqa: E402

SERVICO = re.compile(r"(?:FOI|FORAM|FOI FEITO|FOI FEITA|FOI REALIZAD[OA])\s+(?:\w+\s+){0,3}?(?:SUBSTITU[IÍ]D|TROCAD|INSTALAD)|"
                     r"(?:SUBSTITU[IÍ]D[OA]S?|TROCAD[OA]S?|INSTALAD[OA]S?)\s+(?:EM CAMPO|NA OBRA|NA OS|PELA O)|"
                     r"SERVI?[ÇC]?O REALIZADO|EQUIPAMENTO SUBSTITU[IÍ]D|C[ÉE]LULA SUBSTITU[IÍ]D|TANQUE SUBSTITU[IÍ]D|"
                     r"CONTROLE SUBSTITU[IÍ]D|LIBERADO PARA SER COLOCADO EM OPERA", re.I)


def candidatos(run):
    with open(os.path.join(run, "retro.json"), encoding="utf-8") as fh:
        dem = json.load(fh)["demandas"]
    por, antes, _ = sf.base()
    do_ativo = {}
    for k, v in por.items():
        do_ativo.setdefault(sf.txt(v[0]["EQUIPAMENTO"]), []).append(k)
    out = []
    for r in dem:
        if r.get("executada") or (r.get("desfecho") or "").startswith("duplicada"):
            continue
        cad = {x["ss"] for x in (r.get("estrutura") or {}).get("ss", [])}
        if not cad:
            continue
        inicio = min(ts.chegada(k, por, antes) for k in cad if k in por)
        for k in do_ativo.get(r["ativo"], []):
            if k in cad or ts.chegada(k, por, antes) < inicio:
                continue
            t = sf.txt(por[k][0]["DESCRIÇÃO"])
            for m in SERVICO.finditer(t):
                if re.search(r"N[ÃA]O\s*$|AINDA\s+N[ÃA]O\s+\w*\s*$", t[max(0, m.start() - 20):m.start()], re.I):
                    continue                     # «ainda não foi substituído» não é serviço feito
                out.append({"ativo": r["ativo"], "cadeia": r.get("cadeia"), "desfecho": r.get("desfecho"), "ss_irma": k,
                            "posto": sf.txt(por[k][0]["POSTO_SGM"]), "status": ts.status(k, por),
                            "chegada": ts.chegada(k, por, antes).strftime("%d/%m/%Y"),
                            "saida": (ts.saida(k, por)[0] or sf.HOJE).strftime("%d/%m/%Y"),
                            "trecho": t[max(0, m.start() - 160): m.end() + 120]})
                break
    return out


if __name__ == "__main__":
    for c in candidatos(sys.argv[1] if len(sys.argv) > 1 else ".analise/retro2026"):
        print(f"\n{c['ativo']} · {c['cadeia']} · {c['desfecho']}\n   irmã {c['ss_irma']} ({c['posto']}, {c['status']}, "
              f"{c['chegada']} → {c['saida']})\n   «{c['trecho']}»")
