"""
A visão consolidada do site — o resumo mínimo que abre a página.

A pedido do gestor (22/08): primeiro a carteira consolidada, minimalista, na
visão ETO — os ativos indisponíveis ainda vivos —, repartida nas etapas dele;
depois o que o DCMD concluiu no ano, o alerta do acumulado (entraram = resolvidos
+ pendentes, lido da conta do COEP), a abertura dos pendentes do DCMD com o cruzamento
contra o plano de compras, e a taxa de falha de 2026.

Fontes: a aba de mapeamento por criticidade da Relação de Indisponíveis
(ATUALIZADA 16, via dinamica_joa), a cadeia de repasse (coep_2026), o plano de
compras de 17/07 e a leitura da taxa de falha.

Grava data/missao/visao_consolidada.json.
Rodar: python3 scripts/visao_consolidada.py
"""

import csv
import json
import os
import re
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "data", "missao", "visao_consolidada.json")

# A régua do gestor para a visão ETO: sai quem já não está indisponível.
FORA_DA_VISAO = {"Concluído", "Cancelada em operação", "Desmobilizado"}
# E o mapa das etapas da planilha para os baldes mínimos dele.
BALDE = {
    "Em ajustes": "ajuste_de_protecao",
    "Aguardando comissionamento": "comissionamento",
    "Entregue ao COCM": "dcmd_execucao",
    "Em logística": "dcmd_logistica",
    "Em compra": "dcmd_aquisicao",
    "Em análise": "dcmd_aquisicao",
    "Travado": "dcmd_aquisicao",
    "Primeiro ataque do DMSL": "dmsl_novos",
    "Com o DMSL": "dmsl_novos",
}


# Revisão da leitura (revisor Opus, 22/08): a planilha dá a etapa, mas a cadeia de
# SS no SGM às vezes conta outra história. Cada linha aqui tem a evidência lida.
MUDA_DE_BALDE = {
    "5853360007": ("dcmd_execucao", "sem compra: travado por acesso, SS pendente com equipe RD desde 10/2025"),
    "7908708116": ("ajuste_de_protecao", "SS viva é ETO-PROT 00165/2026 pendente — esteira de ajuste"),
    "5827102054": ("ajuste_de_protecao", "SS viva é ETO-PROT 00164/2026 pendente; sem SS de comissionamento"),
    "7942572059": ("ajuste_de_protecao", "SS viva é ETO-PROT 00155/2026 pendente; check da planilha diz «Em operação» — conferir"),
    "7948412064": ("dcmd_execucao", "indisponibilidade atendida em 13/07; o vivo é ETO-RD-GR 00666/2026 com equipe RD"),
    "5865120195": ("comissionamento", "saiu do PROT em 17/08; pendente agora é ETO-SE-PCM 00091/2026 — SE é comissionamento"),
    "7900230155": ("comissionamento", "saiu do PROT em 17/08; pendente é ETO-SE-PCM 00090/2026"),
    "7933726256": ("comissionamento", "saiu do PROT em 17/08; pendente é ETO-SE-PCM 00092/2026"),
}
SAI_DA_VISAO = {
    "7900532053": "parecer: operando no SCADA; cancelada encerrada 13/07 sem nota nova no COEP — resolvido pela régua",
    "7934697002": "única indisponibilidade ATENDIDA em 20/07; nada vivo",
    "7953570026": "única indisponibilidade ATENDIDA em 19/06; nada vivo",
}
VOLTA_PARA_A_VISAO = {
    "7929376022": ("comissionamento", "ETO-TELE 01107/2026 pendente 13/08; «problema no envio do controle»"),
    "7908686014": ("ajuste_de_protecao", "ETO-PROT 00159/2026 pendente 28/07"),
    "5854566043": ("ajuste_de_protecao", "ETO-PROT 00158/2026 pendente 28/07"),
    "7953610256": ("ajuste_de_protecao", "ETO-PROT 00157/2026 pendente 28/07"),
    "7903112004": ("dcmd_aquisicao", "ETO-COEP 00184/2025 pendente desde 09/2025"),
    "7930359149": ("dcmd_aquisicao", "ETO-COEP 00138/2026 pendente 13/07"),
    "7903569004": ("dcmd_aquisicao", "cancelada, mas ETO-COEP 00152/2026 aberta depois — voltou, régua do gestor"),
    "5800440256": ("dcmd_aquisicao", "cancelada, mas ETO-COEP 00169/2026 aberta depois — voltou"),
    "7967181127": ("dcmd_execucao", "parecer: «linha viva substituiu as chaves» — gestor (22/08) manda contar como em execução"),
}


def _dept(posto):
    p = (posto or "").upper()
    if "-RD-" in p or p.startswith(("ENC", "DOLP", "DLP", "DBM", "DG-")):
        return "DCMD"
    if "TELE" in p or "-SE-" in p or "SCADA" in p or "DMSL" in p:
        return "DMSL"
    return "outros"


def montar():
    with open(os.path.join(RAIZ, "data", "raw", "dinamica_joa.json"), encoding="utf-8") as fh:
        joa = {x["ativo"]: x for x in json.load(fh)["lista"]}
    with open(os.path.join(RAIZ, "data", "missao", "coep_2026.json"), encoding="utf-8") as fh:
        cp = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "leitura_ss_os.json"), encoding="utf-8") as fh:
        leitura = json.load(fh)
    with open(os.path.join(RAIZ, "data", "raw", "plano_compras.csv"), encoding="utf-8") as fh:
        plano = {m.group(1) for l in fh for m in [re.match(r"(\d{10});", l)] if m}

    # ---- a visão ETO: vivos da carteira, por balde — com a revisão da cadeia
    vivos = {c: x for c, x in joa.items() if x["etapa"] not in FORA_DA_VISAO}
    for cod in SAI_DA_VISAO:
        vivos.pop(cod, None)
    for cod in VOLTA_PARA_A_VISAO:
        if cod in joa:
            vivos[cod] = joa[cod]
    baldes = {b: [] for b in ("ajuste_de_protecao", "comissionamento", "dcmd_execucao",
                              "dcmd_logistica", "dcmd_aquisicao", "dmsl_novos")}
    sem_balde = []
    for cod, x in sorted(vivos.items()):
        motivo = ""
        if cod in VOLTA_PARA_A_VISAO:
            b, motivo = VOLTA_PARA_A_VISAO[cod]
        elif cod in MUDA_DE_BALDE:
            b, motivo = MUDA_DE_BALDE[cod]
        else:
            b = BALDE.get(x["etapa"])
        item = {"ativo": cod, "tipo": x["tipo"], "localidade": x["localidade"],
                "criticidade": x.get("criticidade", ""), "etapa_da_planilha": x["etapa"]}
        if motivo:
            item["revisao"] = motivo
        (baldes[b] if b else sem_balde).append(item)
    if sem_balde:
        raise SystemExit(f"etapa sem balde no mapa do gestor: "
                         f"{sorted({x['etapa_da_planilha'] for x in sem_balde})}")

    # ---- aquisição × plano de compras
    aq = baldes["dcmd_aquisicao"]
    for item in aq:
        item["no_plano_de_compras"] = item["ativo"] in plano

    # ---- concluídos pelo DCMD no ano. A régua do revisor (22/08): conta o
    # equipamento em que a equipe de campo trabalhou em algum ponto da cadeia E a
    # demanda terminou com serviço executado — fechar na TELE/PROT depois é
    # comissionamento e ajuste, a execução foi do campo. Fechar cancelando não é
    # entrega e fica de fora.
    res = {r["ativo"]: r for r in cp["resolvidos_do_coep"]
           if r["conta_como_resolvido_pelo_coep"]}
    with open(os.path.join(RAIZ, "data", "missao", "repasse_dos_resolvidos.json"),
              encoding="utf-8") as fh:
        saltos = json.load(fh)["saltos"]
    tocou_rd = {a for a, r in res.items() if _dept(r["posto_que_fechou"]) == "DCMD"}
    for s_ in saltos:
        if s_["ativo"] in res and (_dept(s_["posto_que_recebeu"]) == "DCMD"
                                   or _dept(s_["foi_para"]) == "DCMD"):
            tocou_rd.add(s_["ativo"])
    dcmd = [res[a] for a in sorted(tocou_rd) if res[a]["como_terminou"] == "SS ATENDIDA"]

    pacote = {
        "gerado_em": "2026-08-22",
        "fonte": "aba de mapeamento por criticidade da ATUALIZADA 16 + cadeia de repasse + "
                 "plano de compras de 17/07 + leitura da taxa de falha",
        "visao_eto": {
            "total": len(vivos),
            "nota": "a planilha conferida ativo a ativo contra a cadeia de SS no SGM "
                    f"(revisor, 22/08): {len(VOLTA_PARA_A_VISAO)} voltaram por decisão do gestor ou "
                    f"indisponibilidade pendente, {len(SAI_DA_VISAO)} saíram por já estarem operando "
                    f"ou atendidos, {len(MUDA_DE_BALDE)} trocaram de etapa",
            "revisao": {"voltaram": len(VOLTA_PARA_A_VISAO), "sairam": len(SAI_DA_VISAO),
                        "trocaram": len(MUDA_DE_BALDE)},
            "baldes": {b: {"qtd": len(v), "ativos": v} for b, v in baldes.items()},
        },
        "concluidos_dcmd_2026": {
            "qtd": len(dcmd),
            "regra": "equipe de campo na cadeia + demanda fechada com SS atendida; "
                     "cancelamento não é entrega",
            "fechadas_no_proprio_campo": sum(1 for r in dcmd
                                             if _dept(r["posto_que_fechou"]) == "DCMD"),
            "ativos": [{"ativo": r["ativo"], "tipo": r["tipo"], "localidade": r["localidade"],
                        "fechou_em": r["data_do_fechamento"], "posto": r["posto_que_fechou"],
                        "como": r["como_terminou"]} for r in
                       sorted(dcmd, key=lambda x: x["data_do_fechamento"])],
        },
        # A identidade do alerta sai da conta do COEP, não de número fixo:
        # entraram = resolvidos no ano + ainda pendentes no posto.
        "alerta_acumulado": {
            "entraram": cp["conta"]["resolvidos_pelo_coep"] + cp["conta"]["seguem_no_posto_em_18_08"],
            "resolvidos": cp["conta"]["resolvidos_pelo_coep"],
            "pendentes": cp["conta"]["seguem_no_posto_em_18_08"],
            "curva": cp.get("curva_mensal") or []},
        "pendentes_dcmd": {
            "execucao": len(baldes["dcmd_execucao"]),
            "logistica": len(baldes["dcmd_logistica"]),
            "aquisicao": len(aq),
            "aquisicao_no_plano": sum(1 for i in aq if i["no_plano_de_compras"]),
            "aquisicao_fora_do_plano": sum(1 for i in aq if not i["no_plano_de_compras"]),
        },
        "taxa_2026": {
            "religador": {"falharam": (leitura.get("total_equipamentos_que_falharam") or {})
                          .get("religador|2026", 0), "parque": 1307},
            "regulador": {"falharam": (leitura.get("total_equipamentos_que_falharam") or {})
                          .get("regulador|2026", 0), "parque": 207},
            "regua": "peça grande — controle, tanque ou completo no RL; célula, relé, "
                     "completo ou furto no RT",
        },
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar()
    v = p["visao_eto"]
    print(f"visão ETO: {v['total']} ativos")
    for b, d in v["baldes"].items():
        print(f"  {b:<20} {d['qtd']}")
    pd = p["pendentes_dcmd"]
    print(f"concluídos pelo DCMD em 2026: {p['concluidos_dcmd_2026']['qtd']}")
    print(f"aquisição no plano de compras: {pd['aquisicao_no_plano']} de {pd['aquisicao']}")
    print(f"gravado: {SAIDA}")
