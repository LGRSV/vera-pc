"""
Junta as três passadas numa base só e conta.

Precedência, sempre nesta ordem: **verificação > revisão > análise**. Quem olhou por
último, com mais contexto, manda. Cada campo guarda de onde veio, para a discordância
ficar auditável em vez de sumir na média.

Duas contas que o painel precisa e que só existem aqui:

- **O que a revisão derrubou.** Não é ruído: numa rodada real foram 66% das
  classificações de peça grande, e sem isso o painel publicaria controle como maior
  causa de falha do parque. Vai para o painel como número.
- **A duplicata resolvida.** Duas cadeias que descrevem o mesmo evento viram um fato só;
  a que tem peça confirmada e execução é a que fica.

Rodar: python3 .claude/skills/analise-equipamento/scripts/juntar.py <run> [-o saida.json]
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))


def _carrega(run, etapa):
    cam = os.path.join(run, "%s.json" % etapa)
    if not os.path.exists(cam):
        return {}
    with open(cam) as f:
        return {o["_chave"]: o for o in json.load(f)}


def junta(run):
    analise = _carrega(run, "analise")
    revisao = _carrega(run, "revisao")
    verific = _carrega(run, "verificacao")
    if not analise:
        raise SystemExit("erro: %s/analise.json não existe — feche a etapa primeiro" % run)

    fatos, derrubados, duplicatas = [], [], []
    for ativo, a in sorted(analise.items()):
        rev = {d.get("cadeia"): d for d in (revisao.get(ativo, {}).get("demandas") or [])}
        ver = {d.get("cadeia"): d for d in (verific.get(ativo, {}).get("demandas") or [])}
        for d in a.get("demandas") or []:
            c = d.get("cadeia")
            cat, fonte = d.get("categoria"), "analise"
            r = rev.get(c)
            if r and not r.get("mantem", True):
                antes = cat
                cat, fonte = r.get("categoria_final") or "nao identificado", "revisao"
                derrubados.append({"ativo": ativo, "cadeia": c, "de": antes, "para": cat,
                                   "porque": r.get("porque", "")})
            dup = (r or {}).get("duplicata_de") or d.get("duplicata_de")
            if dup:
                duplicatas.append({"ativo": ativo, "cadeia": c, "duplicata_de": dup})
                continue
            v = ver.get(c) or {}
            fatos.append({
                "ativo": ativo, "familia": a.get("familia"), "cadeia": c,
                "data": d.get("data_primeira_ss"),
                "categoria": cat, "categoria_fonte": fonte,
                "item": d.get("item", ""),
                "executada": v.get("executada", d.get("executada", False)),
                "executada_fonte": "verificacao" if "executada" in v else "analise",
                "voltou_a_operar": v.get("voltou_a_operar"),
                "prova": v.get("prova", ""),
                "pendencia_restante": v.get("pendencia_restante", ""),
                "aberta_por_engano": bool(d.get("aberta_por_engano")),
                "evidencia": (d.get("evidencia") or "")[:400],
                "confianca": min([x for x in (d.get("confianca"), (r or {}).get("confianca"),
                                              v.get("confianca")) if x] or ["media"],
                                 key=lambda x: {"alta": 0, "media": 1, "baixa": 2}.get(x, 1)),
                "motivo": d.get("motivo", ""),
            })

    # equipamento-ano-item: a régua do gestor
    por = defaultdict(list)
    for f in fatos:
        ano = int((f["data"] or "0000")[:4])
        por[(f["ativo"], ano, f["categoria"])].append(f)
    eqs = []
    for (ativo, ano, cat), g in sorted(por.items()):
        g.sort(key=lambda x: x["data"] or "")
        esc = next((x for x in g if x["executada"]), g[0])
        eqs.append({**g[0], "ano": ano, "demandas": len(g),
                    "executada": any(x["executada"] for x in g),
                    "item": esc["item"]})

    return {
        "fatos": fatos, "equipamentos": eqs,
        "derrubados_na_revisao": derrubados,
        "duplicatas": duplicatas,
        "cobertura": {"analise": len(analise), "revisao": len(revisao),
                      "verificacao": len(verific)},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("-o", "--saida")
    a = ap.parse_args()
    d = junta(a.run)
    saida = a.saida or os.path.join(a.run, "consolidado.json")
    with open(saida, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

    c = d["cobertura"]
    print("ativos — análise %d · revisão %d · verificação %d" % (c["analise"], c["revisao"], c["verificacao"]))
    if c["revisao"] < c["analise"] or c["verificacao"] < c["analise"]:
        print("  ⚠ etapa incompleta: o consolidado usa a análise onde falta revisão/verificação")
    print("%d fatos · %d equipamento-ano-item" % (len(d["fatos"]), len(d["equipamentos"])))
    print("duplicatas removidas: %d" % len(d["duplicatas"]))
    n = len(d["derrubados_na_revisao"])
    print("derrubados na revisão: %d%s" % (n, "" if not n else " — %s" % dict(
        Counter("%s→%s" % (x["de"], x["para"]) for x in d["derrubados_na_revisao"]).most_common(6))))
    print(dict(Counter(e["categoria"] for e in d["equipamentos"]).most_common()))
    print(saida)
