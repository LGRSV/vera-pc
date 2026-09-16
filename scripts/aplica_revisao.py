"""
Aplica a revisão 2024-2025 sobre a base consolidada e mede o que ela muda.

A revisão é a segunda opinião, item a item, gravada pela skill `checkpoint` em
`.analise/revisao-2425`. Ela manda sobre a leitura e sobre a verificação: foi quem olhou
por último, com o histórico inteiro do ativo à vista.

**O que ela corrige, em ordem de impacto:**

1. **Duplicata.** Duas cadeias que descrevem o MESMO evento físico. O padrão dominante é a
   SS que o RD abre para executar o serviço, contada à parte da cadeia que o pediu — a SS
   do RD não é repasse, é nota nova, e a base não liga as duas. A cadeia marcada
   `duplicata_de` sai da contagem; a que tem a peça e a execução fica.
2. **Rótulo que a citação não sustenta**, com o destino que o revisor indicou.
3. **`executada`** — vale o texto, não o status da SS.

Rodar: python3 scripts/aplica_revisao.py
"""

import json
import os
import sys
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import falha_completa as fc   # noqa: E402

BASE = os.path.join(RAIZ, "data", "missao", "falha_total.json")
REVISAO = os.path.join(RAIZ, ".analise", "revisao-2425", "revisao.json")
SAIDA = os.path.join(RAIZ, "data", "missao", "falha_revisada.json")


def carrega_revisao(caminho=REVISAO):
    """{cadeia: veredito} — o que a revisão decidiu para cada cadeia."""
    if not os.path.exists(caminho):
        return {}, 0
    with open(caminho) as f:
        ativos = json.load(f)
    fora = {}
    for o in ativos:
        for d in (o.get("demandas") or []):
            if d.get("cadeia"):
                fora[d["cadeia"]] = d
    return fora, len(ativos)


def aplica(pacote, rev):
    linhas, dup, mudou, exe = [], [], [], 0
    for e in pacote["equipamentos"]:
        v = rev.get(e["cadeia"])
        if not v:
            linhas.append(e)
            continue
        if v.get("duplicata_de"):
            dup.append({**e, "duplicata_de": v["duplicata_de"],
                        "porque": v.get("porque", "")})
            continue                      # sai da contagem: é o mesmo fato de outra cadeia
        novo = dict(e)
        cat = fc.normaliza_cat(v.get("categoria_final"), e["fam"])
        if cat and cat != e["categoria"]:
            mudou.append({"ativo": e["ativo"], "cadeia": e["cadeia"],
                          "de": e["categoria"], "para": cat,
                          "porque": v.get("porque", "")})
            novo["categoria"] = cat
            novo["classe"] = fc.CLASSE[cat]
            novo["categoria_fonte"] = "revisao"
        if "executada" in v and bool(v["executada"]) != e["executada"]:
            exe += 1
            novo["executada"] = bool(v["executada"])
        linhas.append(novo)
    return linhas, dup, mudou, exe


def reconsolida(linhas):
    """Refaz «um fato por ativo + ano + item» DEPOIS do rótulo novo.

    A consolidação de `falha_total.equipamento_ano` roda antes da revisão. Quando o
    revisor muda o rótulo de uma cadeia para um item que o ativo JÁ tinha naquele ano,
    nascem duas linhas da mesma chave — e o mesmo equipamento passa a contar duas vezes,
    que é exatamente o que a régua do gestor proíbe. Achado no 5863887001 (célula duas
    vezes em 2025, uma delas peça grande) e em mais quatro chaves de apoio.

    `demandas` aqui SOMA, não conta linhas: cada linha já é um grupo de demandas.
    A reincidência também se refaz — ela depende do rótulo, e 80 rótulos mudaram.
    """
    por = defaultdict(list)
    for l in linhas:
        por[(l["ativo"], l["ano"], l["categoria"])].append(l)
    fora, juntadas = [], []
    for (ativo, ano, cat), g in sorted(por.items()):
        if len(g) == 1:
            fora.append(g[0])
            continue
        g.sort(key=lambda x: x["abert"])
        esc = next((x for x in g if x["executada"]), g[0])
        juntadas.append({"ativo": ativo, "ano": ano, "categoria": cat,
                         "cadeias": [x["cadeia"] for x in g],
                         "classe": g[0]["classe"]})
        fora.append({**g[0],
                     "demandas": sum(x.get("demandas", 1) for x in g),
                     "item": esc["item"],
                     "executada": any(x["executada"] for x in g),
                     "dcmd": any(x["dcmd"] for x in g)})
    return fc.reincidencia(fora), juntadas


if __name__ == "__main__":
    with open(BASE) as f:
        pacote = json.load(f)
    rev, n_ativos = carrega_revisao()
    if not rev:
        raise SystemExit("erro: revisão ainda não tem nada fechado")

    antes = pacote["equipamentos"]
    depois, dup, mudou, exe = aplica(pacote, rev)
    depois, juntadas = reconsolida(depois)

    pacote["equipamentos"] = depois
    pacote["duplicatas"] = dup
    pacote["mudados_na_revisao"] = mudou
    pacote["revisao_ativos"] = n_ativos
    pacote["juntadas_na_revisao"] = juntadas
    with open(SAIDA, "w") as f:
        json.dump(pacote, f, ensure_ascii=False, indent=1)

    ga = [e for e in antes if e["classe"] == "grande"]
    gd = [e for e in depois if e["classe"] == "grande"]
    print("revisão aplicada · %d ativos revisados · %d cadeias com veredito"
          % (n_ativos, len(rev)))
    print("  duplicatas removidas: %d · rótulos mudados: %d · executada corrigida: %d"
          % (len(dup), len(mudou), exe))
    print("  fatos juntados por virarem a mesma chave: %d (%d de peça grande)"
          % (len(juntadas), sum(1 for j in juntadas if j["classe"] == "grande")))
    print()
    print("PEÇA GRANDE: %d → %d  (%+d)" % (len(ga), len(gd), len(gd) - len(ga)))
    for ano in (2024, 2025, 2026):
        for fam in ("RL", "RT"):
            a = sum(1 for e in ga if e["ano"] == ano and e["fam"] == fam)
            b = sum(1 for e in gd if e["ano"] == ano and e["fam"] == fam)
            print("  %d %s: %3d → %3d  %s" % (ano, fam, a, b,
                  "(%+d)" % (b - a) if b != a else ""))
    print()
    print("por peça:", dict(Counter(e["categoria"] for e in gd).most_common()))
    print(SAIDA)
