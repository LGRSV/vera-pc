"""
A visão orçamentária dos dois projetos — orçamento × realizado × o que falta,
e quanto custa a fila que está na mesa.

Régua do gestor (22/08): o valor que vale é o VALOR MÉDIO POR MANUTENÇÃO dele —
RL R$ 58.543,21 e RT R$ 167.280,98 —, não o médio por obra que o AIC devolve
(esse fica só como referência, e é menor porque nem toda obra do projeto troca o
equipamento inteiro: no regulador, muitas trocam uma célula, não o banco de três).

Cada balde da visão ETO vira dinheiro assim (pergunta do gestor, 22/08: «não é
pelo custo médio, todos já estão orçados?» — nem todos): vale o VALOR ORÇADO do
ativo na planilha de indisponibilidade onde ele existe, e só onde falta entra o
valor médio por manutenção. Dos 93, 54 têm orçamento próprio; 39 não — e os 20 do
1º ataque do DMSL são justamente os que não têm nenhum, por serem novos. Por isso
a estimativa deles é inteiramente pelo médio.

Fontes (todas do gestor, em data/raw/realizado_capex_2026.json):
  - quadro Orçamento 2026 — a coluna ORÇADO por projeto;
  - Power BI do Capex — o REALIZADO do ano, 8481 e 8495 somados, por mês e por
    natureza. É esta a medida do realizado (régua do gestor, 22/08): a coluna
    Realizado do quadro do export de 21/08 trazia R$ 1.365.345 e não vale;
  - o valor médio por manutenção.

Grava data/missao/visao_orcamentaria.json.
Rodar: python3 scripts/visao_orcamentaria.py
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "data", "missao", "visao_orcamentaria.json")

PROJETOS = (("8495", "religador", "RL"), ("8481", "regulador", "RT"))
BALDE_NOME = {
    "ajuste_de_protecao": "Em fase de ajuste de proteção",
    "comissionamento": "Aguardando comissionamento",
    "dcmd_execucao": "DCMD · em execução",
    "dcmd_logistica": "DCMD · em logística",
    "dcmd_aquisicao": "DCMD · em processo de aquisição",
    "dmsl_novos": "1º ataque do DMSL",
}
# O que ainda vai custar dinheiro novo: quem está em ajuste ou comissionamento já
# teve o equipamento trocado — o gasto foi feito.
AINDA_CUSTA = ("dcmd_execucao", "dcmd_logistica", "dcmd_aquisicao", "dmsl_novos")


def _num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def montar():
    with open(os.path.join(RAIZ, "data", "raw", "realizado_capex_2026.json"),
              encoding="utf-8") as fh:
        caixa = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "aic_full.json"), encoding="utf-8") as fh:
        aic = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "visao_consolidada.json"),
              encoding="utf-8") as fh:
        vc = json.load(fh)
    with open(os.path.join(RAIZ, "data", "raw", "dinamica_joa.json"), encoding="utf-8") as fh:
        orcado = {x["ativo"]: x.get("valor") or 0.0
                  for x in json.load(fh)["lista"] if (x.get("valor") or 0) > 0}

    medio = caixa["valor_medio_por_manutencao"]
    orc = dict(caixa["orcamento_2026"])
    # o realizado do ano é o total do Power BI, não a coluna do quadro
    orc["total_realizado"] = caixa["total"]
    orc["pct_realizado"] = round(100 * caixa["total"] / orc["total_orcado"], 2)
    saldo = round(orc["total_orcado"] - orc["total_realizado"], 2)

    # ---- referência: o médio por obra concluída do projeto no AIC (fica de nota)
    referencia = {}
    for proj, nome, sigla in PROJETOS:
        concl = [r for r in aic.values()
                 if str(r.get("NUM_PROJETO_SIGCO", "")).strip() == proj
                 and (str(r.get("DTH_ABERTURA", "")).startswith("2026")
                      or str(r.get("DATA_CONCLUSAO_FISICA", "")).startswith("2026")
                      or str(r.get("DTH_ENCERRAMENTO", "")).startswith("2026"))
                 and (r.get("DATA_CONCLUSAO_FISICA") or r.get("DTH_ENCERRAMENTO"))]
        realizado = round(sum(_num(r["TOTAL_REALIZADO"]) for r in concl), 2)
        referencia[sigla] = {
            "projeto": proj, "nome": nome,
            "obras_concluidas_2026": len(concl),
            "realizado_acumulado": realizado,
            "medio_por_obra": round(realizado / len(concl), 2) if concl else 0.0,
        }

    # ---- cada balde da visão ETO em dinheiro: orçado onde existe, médio onde falta
    def custo(itens):
        rl = sum(1 for i in itens if i["tipo"] == "RL")
        com = [i for i in itens if i["ativo"] in orcado]
        sem = [i for i in itens if i["ativo"] not in orcado]
        s_orcado = round(sum(orcado[i["ativo"]] for i in com), 2)
        s_medio = round(sum(medio[i["tipo"]] for i in sem), 2)
        return {"qtd": len(itens), "rl": rl, "rt": len(itens) - rl,
                "com_orcamento": len(com), "sem_orcamento": len(sem),
                "orcado": s_orcado, "estimado": s_medio,
                "custo": round(s_orcado + s_medio, 2)}

    baldes = []
    for b, nome in BALDE_NOME.items():
        d = custo(vc["visao_eto"]["baldes"][b]["ativos"])
        baldes.append({"balde": b, "nome": nome, "ainda_custa": b in AINDA_CUSTA, **d})

    fila = [i for b in AINDA_CUSTA for i in vc["visao_eto"]["baldes"][b]["ativos"]]
    f = custo(fila)
    dmsl = vc["visao_eto"]["baldes"]["dmsl_novos"]["ativos"]
    d = custo(dmsl)
    f_rl, f_rt, f_custo = f["rl"], f["rt"], f["custo"]
    d_rl, d_rt, d_custo = d["rl"], d["rt"], d["custo"]

    pct = lambda v, base: round(100 * v / base, 1) if base else 0.0
    pacote = {
        "gerado_em": "2026-08-22",
        "orcamento": {**orc, "saldo": saldo},
        "caixa": {k: caixa[k] for k in ("fonte", "janela", "total", "por_mes", "por_natureza")},
        "valor_medio": medio,
        "referencia_aic": referencia,
        "por_balde": baldes,
        "cobertura": {
            "com_orcamento": sum(b["com_orcamento"] for b in baldes),
            "sem_orcamento": sum(b["sem_orcamento"] for b in baldes),
            "orcado": round(sum(b["orcado"] for b in baldes), 2),
            "estimado": round(sum(b["estimado"] for b in baldes), 2),
            "regra": "vale o valor orçado do ativo na planilha de indisponibilidade; "
                     "onde não há orçamento, entra o valor médio por manutenção",
        },
        "estimativa_dmsl": {
            **d, "pct_do_saldo": pct(d_custo, saldo),
            "pct_do_orcamento": pct(d_custo, orc["total_orcado"]),
            "como": (f"{d_rl} religadores × R$ {medio['RL']:,.2f} + {d_rt} reguladores × "
                     f"R$ {medio['RT']:,.2f}: nenhum dos {d['qtd']} tem orçamento próprio "
                     "na planilha — são novos, e é por isso que aqui tudo é pelo médio"),
        },
        "fila_que_ainda_custa": {
            **f, "pct_do_saldo": pct(f_custo, saldo),
            "regra": "execução + logística + aquisição + 1º ataque; ajuste de proteção e "
                     "comissionamento ficam fora — nesses o equipamento já foi trocado e "
                     "o dinheiro já saiu",
        },
        "nota": ("o realizado do ano é o total do Power BI — 8481 e 8495 somados, "
                 "jan–ago —, régua do gestor (22/08). A coluna Realizado do quadro "
                 "Orçamento 2026 (export de 21/08) trazia R$ 1.365.345, uma apuração "
                 "mais atrasada, e não é usada aqui. O orçado por projeto vem do mesmo "
                 "quadro e continua valendo. O médio por obra do AIC não serve de preço: "
                 "nem toda obra do projeto troca o equipamento inteiro."),
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar()
    o = p["orcamento"]
    print(f"orçamento 2026: R$ {o['total_orcado']:,.2f} · realizado R$ "
          f"{o['total_realizado']:,.2f} ({o['pct_realizado']}%) · saldo R$ {o['saldo']:,.2f}")
    print(f"médio por manutenção: RL R$ {p['valor_medio']['RL']:,.2f} · "
          f"RT R$ {p['valor_medio']['RT']:,.2f}")
    c = p["cobertura"]
    print(f"cobertura: {c['com_orcamento']} orçados (R$ {c['orcado']:,.2f}) + "
          f"{c['sem_orcamento']} pelo médio (R$ {c['estimado']:,.2f})")
    for b in p["por_balde"]:
        print(f"  {b['nome']:<34} {b['qtd']:>3} ({b['com_orcamento']} orç + "
              f"{b['sem_orcamento']} méd)  R$ {b['custo']:>14,.2f}"
              f"{'' if b['ainda_custa'] else '   (já gasto)'}")
    e = p["estimativa_dmsl"]
    print(f"1º ataque para o DCMD: R$ {e['custo']:,.2f} — {e['pct_do_saldo']}% do saldo")
    f = p["fila_que_ainda_custa"]
    print(f"fila que ainda custa ({f['qtd']}): R$ {f['custo']:,.2f} — "
          f"{f['pct_do_saldo']}% do saldo")
    print(f"gravado: {SAIDA}")
