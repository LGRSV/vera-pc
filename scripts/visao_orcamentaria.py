"""
A visão orçamentária dos dois projetos — orçamento × realizado × o que falta,
e quanto custa a fila que está na mesa.

Régua do gestor (22/08): o valor que vale é o VALOR MÉDIO POR MANUTENÇÃO dele —
RL R$ 58.543,21 e RT R$ 167.280,98 —, não o médio por obra que o AIC devolve
(esse fica só como referência, e é menor porque nem toda obra do projeto troca o
equipamento inteiro: no regulador, muitas trocam uma célula, não o banco de três).

Com esse preço, cada balde da visão ETO vira dinheiro. O pedido principal: se
todo o 1º ataque do DMSL entrasse para o DCMD, quanto ficaria.

Fontes (todas do gestor, em data/raw/realizado_capex_2026.json):
  - quadro Orçamento 2026 — orçado e realizado contábil por projeto, export 21/08;
  - Power BI do Capex — o mesmo dinheiro por mês e por natureza, jan–ago;
  - o valor médio por manutenção.
As duas apurações de realizado não batem (R$ 1,57 mi no Power BI × R$ 1,37 mi no
contábil) e ficam as duas à vista: uma é lançamento, a outra é o que já entrou na
contabilidade do projeto.

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

    medio = caixa["valor_medio_por_manutencao"]
    orc = caixa["orcamento_2026"]
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

    # ---- cada balde da visão ETO em dinheiro, pelo médio do gestor
    def custo(itens):
        rl = sum(1 for i in itens if i["tipo"] == "RL")
        rt = len(itens) - rl
        return rl, rt, round(rl * medio["RL"] + rt * medio["RT"], 2)

    baldes = []
    for b, nome in BALDE_NOME.items():
        itens = vc["visao_eto"]["baldes"][b]["ativos"]
        rl, rt, v = custo(itens)
        baldes.append({"balde": b, "nome": nome, "qtd": len(itens), "rl": rl, "rt": rt,
                       "custo": v, "ainda_custa": b in AINDA_CUSTA})

    fila = [i for b in AINDA_CUSTA for i in vc["visao_eto"]["baldes"][b]["ativos"]]
    f_rl, f_rt, f_custo = custo(fila)
    dmsl = vc["visao_eto"]["baldes"]["dmsl_novos"]["ativos"]
    d_rl, d_rt, d_custo = custo(dmsl)

    pct = lambda v, base: round(100 * v / base, 1) if base else 0.0
    pacote = {
        "gerado_em": "2026-08-22",
        "orcamento": {**orc, "saldo": saldo},
        "caixa": {k: caixa[k] for k in ("fonte", "janela", "total", "por_mes", "por_natureza")},
        "valor_medio": medio,
        "referencia_aic": referencia,
        "por_balde": baldes,
        "estimativa_dmsl": {
            "qtd": len(dmsl), "rl": d_rl, "rt": d_rt, "custo": d_custo,
            "pct_do_saldo": pct(d_custo, saldo),
            "pct_do_orcamento": pct(d_custo, orc["total_orcado"]),
            "como": (f"{d_rl} religadores × R$ {medio['RL']:,.2f} + {d_rt} reguladores × "
                     f"R$ {medio['RT']:,.2f}, pelo valor médio por manutenção do gestor"),
        },
        "fila_que_ainda_custa": {
            "qtd": len(fila), "rl": f_rl, "rt": f_rt, "custo": f_custo,
            "pct_do_saldo": pct(f_custo, saldo),
            "regra": "execução + logística + aquisição + 1º ataque; ajuste de proteção e "
                     "comissionamento ficam fora — nesses o equipamento já foi trocado e "
                     "o dinheiro já saiu",
        },
        "nota": ("o realizado tem duas apurações do próprio gestor e as duas ficam à "
                 "vista: R$ 1,37 mi no quadro Orçamento 2026 (contábil, export de 21/08) "
                 "e R$ 1,57 mi no Power BI por natureza (lançamentos de jan–ago). O "
                 "médio por obra do AIC não serve de preço: nem toda obra do projeto "
                 "troca o equipamento inteiro."),
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
    for b in p["por_balde"]:
        print(f"  {b['nome']:<34} {b['qtd']:>3} ({b['rl']} RL + {b['rt']} RT)  "
              f"R$ {b['custo']:>14,.2f}{'' if b['ainda_custa'] else '   (já gasto)'}")
    e = p["estimativa_dmsl"]
    print(f"1º ataque para o DCMD: R$ {e['custo']:,.2f} — {e['pct_do_saldo']}% do saldo")
    f = p["fila_que_ainda_custa"]
    print(f"fila que ainda custa ({f['qtd']}): R$ {f['custo']:,.2f} — "
          f"{f['pct_do_saldo']}% do saldo")
    print(f"gravado: {SAIDA}")
