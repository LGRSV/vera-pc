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
import re
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "data", "missao", "visao_orcamentaria.json")

PROJETOS = (("8495", "religador", "RL"), ("8481", "regulador", "RT"))
PROJETO_DO_TIPO = {"RL": "8495", "RT": "8481"}
# A obra que vale é a da demanda de agora. Obra concluída em 2023/2024 num ativo que
# hoje está em aquisição é de um evento anterior — o dinheiro dela já foi gasto noutra
# falha e não diz nada sobre o que falta pagar.
ANO_DA_CARTEIRA = "2026"
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


def _oid(x):
    if isinstance(x, dict):
        x = x.get("obra") or x.get("num_obra") or ""
    x = str(x).split(".")[0].strip()
    return x.zfill(10) if x.isdigit() and int(x) > 0 else ""


def obras_por_ativo(aic, ssos, descricoes, m4, ss_do_ativo):
    """Toda obra do AIC que a cadeia liga ao ativo, por três vias: o vínculo por EMD
    do m4, o NUM_OBRA das SS do próprio ativo e o número de obra citado no texto da
    SS pendente. Guarda por onde veio, para dar para conferir."""
    vinc = defaultdict(dict)
    for a, d in m4.items():
        for o in [_oid(d.get("obra_principal"))] + [_oid(x) for x in (d.get("outras_obras") or [])]:
            if o:
                vinc[a].setdefault(o, "EMD/obra do ativo")
    for r in ssos:
        o = _oid(r["NUM_OBRA"])
        if o:
            vinc[r["NUM_TRAFO"]].setdefault(o, f"obra na {r['NUMERO_SS']}")
    for ss_num, txt in descricoes.items():
        a = ss_do_ativo.get(ss_num)
        if not a:
            continue
        for m in re.findall(r"\b(\d{9,10})\b", txt or ""):
            o = _oid(m)
            if o and o in aic:
                vinc[a].setdefault(o, f"obra citada no texto da {ss_num}")
    return vinc


def valor_pela_obra(ativo, tipo, ja_trocado, vinc, aic):
    """O valor real da obra do ativo, quando o AIC tem uma que sirva.

    Em quem já foi trocado vale o REALIZADO — é o dinheiro que saiu. Em quem ainda
    espera, vale o ORÇADO da obra aberta neste ano, que é o compromisso firme; obra
    de anos anteriores fica de fora porque pagou outra falha."""
    cand = []
    for o, via in (vinc.get(ativo) or {}).items():
        r = aic.get(o)
        if not r or str(r.get("NUM_PROJETO_SIGCO", "")).strip() != PROJETO_DO_TIPO.get(tipo):
            continue
        abertura = str(r.get("DTH_ABERTURA", ""))[:10]
        orcado, realizado = _num(r.get("VAL_TOTAL_ORCADO")), _num(r.get("TOTAL_REALIZADO"))
        if ja_trocado and realizado > 0:
            cand.append((abertura, realizado, "realizado", o, via, orcado))
        elif abertura[:4] >= ANO_DA_CARTEIRA and (realizado > 0 or orcado > 0):
            cand.append((abertura, realizado if realizado > 0 else orcado,
                         "realizado" if realizado > 0 else "orçado", o, via, orcado))
    if not cand:
        return None
    abertura, valor, medida, obra, via, orcado = max(cand)
    return {"valor": round(valor, 2), "medida": medida, "obra": obra, "via": via,
            "abertura": abertura, "orcado_da_obra": round(orcado, 2)}


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
    with open(os.path.join(RAIZ, "data", "missao", "ssos_min.json"), encoding="utf-8") as fh:
        ssos = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "descricao_ss_pendentes.json"),
              encoding="utf-8") as fh:
        descricoes = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "m4_aic129.json"), encoding="utf-8") as fh:
        m4 = json.load(fh)["ativos"]

    todos = {i["ativo"]: {**i, "_ja_trocado": b not in AINDA_CUSTA}
             for b in BALDE_NOME for i in vc["visao_eto"]["baldes"][b]["ativos"]}
    ss_do_ativo = {i["ss_pendente"]: a for a, i in todos.items()}
    vinc = obras_por_ativo(aic, [r for r in ssos if r["NUM_TRAFO"] in todos],
                           descricoes, {a: d for a, d in m4.items() if a in todos},
                           ss_do_ativo)

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

    # ---- cada balde da visão ETO em dinheiro: orçado onde existe, médio onde falta.
    # Régua do gestor (22/08): em ajuste de proteção e comissionamento o equipamento JÁ
    # FOI TROCADO — o dinheiro saiu. Ali não se estima nada: vale o que estava orçado
    # para eles, e quem não tem valor na planilha fica sem valor mesmo. Aplicar o médio
    # seria inventar gasto futuro para dinheiro que já aconteceu.
    # A hierarquia do valor de cada ativo, da fonte mais forte para a mais fraca:
    #   1. a OBRA do ativo no AIC — dinheiro de verdade, realizado ou orçado;
    #   2. o valor orçado do ativo na planilha de indisponibilidade;
    #   3. o valor médio por manutenção — e só em quem ainda vai custar.
    fontes = {}
    for a, i in todos.items():
        ja = i["_ja_trocado"]
        obra = valor_pela_obra(a, i["tipo"], ja, vinc, aic)
        if obra:
            fontes[a] = {"valor": obra["valor"], "fonte": "obra", **obra}
        elif a in orcado:
            fontes[a] = {"valor": round(orcado[a], 2), "fonte": "planilha"}
        elif not ja:
            fontes[a] = {"valor": round(medio[i["tipo"]], 2), "fonte": "medio"}
        else:
            fontes[a] = {"valor": 0.0, "fonte": "sem_valor"}

    def custo(itens):
        rl = sum(1 for i in itens if i["tipo"] == "RL")
        conta = {f: 0 for f in ("obra", "planilha", "medio", "sem_valor")}
        soma = dict(conta)
        for i in itens:
            fo = fontes[i["ativo"]]
            conta[fo["fonte"]] += 1
            soma[fo["fonte"]] += fo["valor"]
        return {"qtd": len(itens), "rl": rl, "rt": len(itens) - rl,
                "n_obra": conta["obra"], "n_planilha": conta["planilha"],
                "n_medio": conta["medio"], "sem_valor": conta["sem_valor"],
                "por_obra": round(soma["obra"], 2),
                "por_planilha": round(soma["planilha"], 2),
                "estimado": round(soma["medio"], 2),
                # o que se sabe de verdade — obra ou planilha — separado do que é estimado
                "conhecido": round(soma["obra"] + soma["planilha"], 2),
                "com_orcamento": conta["obra"] + conta["planilha"],
                "sem_orcamento": conta["medio"],
                "orcado": round(soma["obra"] + soma["planilha"], 2),
                "custo": round(soma["obra"] + soma["planilha"] + soma["medio"], 2)}

    baldes = []
    for b, nome in BALDE_NOME.items():
        d = custo(vc["visao_eto"]["baldes"][b]["ativos"])
        baldes.append({"balde": b, "nome": nome, "ainda_custa": b in AINDA_CUSTA, **d})

    fila = [i for b in AINDA_CUSTA for i in vc["visao_eto"]["baldes"][b]["ativos"]]
    f = custo(fila)
    ja_gasto = [i for b in BALDE_NOME if b not in AINDA_CUSTA
                for i in vc["visao_eto"]["baldes"][b]["ativos"]]
    g = custo(ja_gasto)
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
            "n_obra": sum(b["n_obra"] for b in baldes),
            "n_planilha": sum(b["n_planilha"] for b in baldes),
            "com_orcamento": sum(b["com_orcamento"] for b in baldes),
            "sem_orcamento": sum(b["sem_orcamento"] for b in baldes),
            "sem_valor": sum(b["sem_valor"] for b in baldes),
            "por_obra": round(sum(b["por_obra"] for b in baldes), 2),
            "por_planilha": round(sum(b["por_planilha"] for b in baldes), 2),
            "orcado": round(sum(b["orcado"] for b in baldes), 2),
            "estimado": round(sum(b["estimado"] for b in baldes), 2),
            "regra": "vale primeiro a OBRA do ativo no AIC — realizado em quem já foi "
                     "trocado, orçado da obra aberta neste ano em quem ainda espera; "
                     "depois o valor orçado do ativo na planilha de indisponibilidade; "
                     "e só então o valor médio por manutenção, apenas em quem ainda vai "
                     "custar. Em ajuste de proteção e comissionamento não se estima nada: "
                     "o equipamento já foi trocado e o dinheiro já saiu",
        },
        "fontes_por_ativo": {a: v for a, v in sorted(fontes.items())},
        "ja_gasto": {**g, "regra": "ajuste de proteção + comissionamento — equipamento já "
                     "trocado; o valor é o que estava orçado para eles, e o desembolso "
                     "real está dentro do realizado do ano"},
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
    print(f"cobertura: {c['n_obra']} pela obra no AIC (R$ {c['por_obra']:,.2f}) · "
          f"{c['n_planilha']} pela planilha (R$ {c['por_planilha']:,.2f}) · "
          f"{c['sem_orcamento']} pelo médio (R$ {c['estimado']:,.2f}) · "
          f"{c['sem_valor']} sem valor")
    for b in p["por_balde"]:
        print(f"  {b['nome']:<34} {b['qtd']:>3} ({b['n_obra']} obra, {b['n_planilha']} plan, "
              f"{b['n_medio']} méd, {b['sem_valor']} s/v)  R$ {b['custo']:>14,.2f}"
              f"{'' if b['ainda_custa'] else '   (já gasto)'}")
    e = p["estimativa_dmsl"]
    print(f"1º ataque para o DCMD: R$ {e['custo']:,.2f} — {e['pct_do_saldo']}% do saldo")
    f = p["fila_que_ainda_custa"]
    print(f"fila que ainda custa ({f['qtd']}): R$ {f['custo']:,.2f} — "
          f"{f['pct_do_saldo']}% do saldo")
    print(f"gravado: {SAIDA}")
