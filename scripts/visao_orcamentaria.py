"""
A visão orçamentária dos dois projetos — realizado × quantidade, e a conta
do 1º ataque.

Pedido do gestor (22/08): combinar o realizado dos projetos SIGCO 8495
(religador) e 8481 (regulador) com a quantidade entregue, tirar um valor
médio de RL para RL e um de RT para RT, e estimar quanto custaria se tudo
que está no 1º ataque do DMSL entrasse para o DCMD.

As duas pontas do valor médio:
  - REALIZADO por obra concluída do projeto no AIC em 2026 — o piso: é o
    que uma intervenção paga pelo projeto custou de fato (nem toda obra
    troca o equipamento inteiro; no RT, muitas trocam uma célula, não o
    banco de três).
  - PREVISTO médio por ativo na planilha de indisponibilidade do gestor —
    o teto: orça a solução completa do ativo.

O caixa oficial do ano é o Power BI do gestor (transcrito em
data/raw/realizado_capex_2026.json): lançamentos de jan–ago/2026. O AIC
soma o ACUMULADO das obras concluídas em 2026, que inclui lançamentos de
2025 — por isso as duas somas não batem e as duas ficam à vista.

Grava data/missao/visao_orcamentaria.json.
Rodar: python3 scripts/visao_orcamentaria.py
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "data", "missao", "visao_orcamentaria.json")

PROJETOS = (("8495", "religador", "RL"), ("8481", "regulador", "RT"))


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
        joa = json.load(fh)["lista"]

    # ---- o realizado por projeto, pelas obras concluídas de 2026 no AIC
    por_tipo = {}
    for proj, nome, sigla in PROJETOS:
        concl = [r for r in aic.values()
                 if str(r.get("NUM_PROJETO_SIGCO", "")).strip() == proj
                 and (str(r.get("DTH_ABERTURA", "")).startswith("2026")
                      or str(r.get("DATA_CONCLUSAO_FISICA", "")).startswith("2026")
                      or str(r.get("DTH_ENCERRAMENTO", "")).startswith("2026"))
                 and (r.get("DATA_CONCLUSAO_FISICA") or r.get("DTH_ENCERRAMENTO"))]
        realizado = round(sum(_num(r["TOTAL_REALIZADO"]) for r in concl), 2)
        previstos = [x["valor"] for x in joa if x["tipo"] == sigla and x.get("valor", 0) > 0]
        por_tipo[sigla] = {
            "projeto": proj,
            "nome": nome,
            "obras_concluidas_2026": len(concl),
            "realizado_acumulado": realizado,
            "medio_por_obra": round(realizado / len(concl), 2) if concl else 0.0,
            "previsto_medio_planilha": round(sum(previstos) / len(previstos), 2)
                                       if previstos else 0.0,
            "previstos_com_valor": len(previstos),
        }

    # ---- a estimativa do 1º ataque: se todos entrassem para o DCMD
    dmsl = vc["visao_eto"]["baldes"]["dmsl_novos"]["ativos"]
    n_rl = sum(1 for a in dmsl if a["tipo"] == "RL")
    n_rt = len(dmsl) - n_rl
    piso = round(n_rl * por_tipo["RL"]["medio_por_obra"]
                 + n_rt * por_tipo["RT"]["medio_por_obra"], 2)
    teto = round(n_rl * por_tipo["RL"]["previsto_medio_planilha"]
                 + n_rt * por_tipo["RT"]["previsto_medio_planilha"], 2)

    pacote = {
        "gerado_em": "2026-08-22",
        "caixa": caixa,
        "por_tipo": por_tipo,
        "estimativa_dmsl": {
            "qtd": len(dmsl), "rl": n_rl, "rt": n_rt,
            "piso_pelo_realizado": piso,
            "teto_pelo_previsto": teto,
            "como": (f"piso: {n_rl} RL × médio realizado por obra do 8495 + {n_rt} RT × "
                     f"médio do 8481; teto: os mesmos {len(dmsl)} pelo previsto médio da "
                     "planilha de indisponibilidade (que orça a solução completa — no RT, "
                     "o banco de três células, não uma célula só)"),
        },
        "nota": ("o caixa é o Power BI (lançamentos de jan–ago/2026, os dois projetos "
                 "juntos); o AIC soma o acumulado das obras concluídas em 2026, que "
                 "carrega lançamentos de 2025 — por isso as somas não batem. O projeto "
                 "SIGCO é balde orçamentário: carrega alguma obra de outro objeto."),
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar()
    print(f"caixa 2026 (Power BI): R$ {p['caixa']['total']:,.2f}")
    for s, d in p["por_tipo"].items():
        print(f"{s}: {d['obras_concluidas_2026']} obras · R$ {d['realizado_acumulado']:,.2f} "
              f"· médio/obra R$ {d['medio_por_obra']:,.2f} · previsto médio "
              f"R$ {d['previsto_medio_planilha']:,.2f}")
    e = p["estimativa_dmsl"]
    print(f"1º ataque ({e['rl']} RL + {e['rt']} RT): R$ {e['piso_pelo_realizado']:,.2f} "
          f"a R$ {e['teto_pelo_previsto']:,.2f}")
    print(f"gravado: {SAIDA}")
