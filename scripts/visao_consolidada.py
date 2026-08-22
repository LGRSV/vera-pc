"""
A visão consolidada do site — o resumo mínimo que abre a página.

Régua do gestor (22/08, revista no mesmo dia): a visão ETO sai DA BASE DE
SS/OS, não da carteira. São os ativos 58/79 com SS de INDISPONIBILIDADE PARA
OPERAÇÃO pendente na base — «só tem 93, então são as 93».

O balde de cada um sai do POSTO onde a SS pendente está, que é a régua da
esteira do gestor:
  - ETO-PROT                          → em fase de ajuste de proteção
  - TELE/SE, com criticidade definida na aba de mapeamento por criticidade
                                      → aguardando comissionamento
  - TELE/SE, sem criticidade definida (fora da aba ou «Sem classificação»)
                                      → 1º ataque do DMSL (gestor, 22/08)
  - equipe RD (ETO-RD-*)              → DCMD em execução, com os COCMs
  - ETO-COEP                          → DCMD em aquisição — salvo quem a
    carteira marca «Em logística» (material comprado, esperando chegar)

A carteira (ATUALIZADA 16) vira anotação: a etapa que ela dizia e quem ela
nem lista. Os dicionários de revisão manual da régua antiga foram embora —
a base decide quem entra, o posto decide o balde.

Fontes: recorte da base de SS/OS de 20/08 (ssos_min), a aba de mapeamento
por criticidade (via dinamica_joa), a cadeia de repasse (coep_2026), o plano
de compras de 17/07 e a leitura da taxa de falha.

Grava data/missao/visao_consolidada.json.
Rodar: python3 scripts/visao_consolidada.py
"""

import csv
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "data", "missao", "visao_consolidada.json")

POSICAO = "base de SS/OS de 20/08"


def _dept(posto):
    p = (posto or "").upper()
    if "-RD-" in p or p.startswith(("ENC", "DOLP", "DLP", "DBM", "DG-")):
        return "DCMD"
    if "TELE" in p or "-SE-" in p or "SCADA" in p or "DMSL" in p:
        return "DMSL"
    return "outros"


def montar():
    with open(os.path.join(RAIZ, "data", "missao", "ssos_min.json"), encoding="utf-8") as fh:
        ssos = json.load(fh)
    with open(os.path.join(RAIZ, "data", "raw", "dinamica_joa.json"), encoding="utf-8") as fh:
        joa = {x["ativo"]: x for x in json.load(fh)["lista"]}
    with open(os.path.join(RAIZ, "data", "missao", "coep_2026.json"), encoding="utf-8") as fh:
        cp = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "leitura_ss_os.json"), encoding="utf-8") as fh:
        leitura = json.load(fh)
    with open(os.path.join(RAIZ, "data", "raw", "plano_compras.csv"), encoding="utf-8") as fh:
        plano = {m.group(1) for l in fh for m in [re.match(r"(\d{10});", l)] if m}

    # ---- a visão ETO: o filtro do gestor, ao pé da letra
    pendentes = [r for r in ssos
                 if r["NUM_TRAFO"].startswith(("58", "79"))
                 and r["TIPOSS"] == "INDISPONIBILIDADE PARA OPERAÇÃO"
                 and r["SITUACAO_SS"] == "SS PENDENTE"]

    def tem_criticidade(cod):
        crit = (joa.get(cod, {}).get("criticidade") or "").strip().lower()
        return crit not in ("", "sem classificação")

    def balde_de(r):
        posto = r["NUMERO_SS"].split()[0]
        etapa = joa.get(r["NUM_TRAFO"], {}).get("etapa", "")
        if posto.startswith("ETO-PROT"):
            return "ajuste_de_protecao"
        if posto.startswith(("ETO-TELE", "ETO-SE", "ETO-SCADA")) or "DMSL" in posto:
            if tem_criticidade(r["NUM_TRAFO"]) and "DMSL" not in posto:
                return "comissionamento"
            return "dmsl_novos"
        if _dept(posto) == "DCMD":
            return "dcmd_execucao"
        if posto.startswith("ETO-COEP"):
            return "dcmd_logistica" if etapa == "Em logística" else "dcmd_aquisicao"
        raise SystemExit(f"posto sem balde na régua da esteira: {posto} ({r['NUM_TRAFO']})")

    baldes = {b: [] for b in ("ajuste_de_protecao", "comissionamento", "dcmd_execucao",
                              "dcmd_logistica", "dcmd_aquisicao", "dmsl_novos")}
    for r in sorted(pendentes, key=lambda x: x["NUM_TRAFO"]):
        cod = r["NUM_TRAFO"]
        na_carteira = cod in joa
        x = joa.get(cod, {})
        item = {
            "ativo": cod,
            "tipo": x.get("tipo") or ("RT" if cod.startswith("58") else "RL"),
            "localidade": x.get("localidade") or r["LOCALIDADE"].strip(),
            "criticidade": (x.get("criticidade") or "").strip(),
            "ss_pendente": r["NUMERO_SS"],
            "na_carteira": na_carteira,
            "etapa_da_planilha": x.get("etapa") if na_carteira else "(fora da carteira)",
        }
        baldes[balde_de(r)].append(item)
    total = sum(len(v) for v in baldes.values())
    fora_da_carteira = sum(1 for v in baldes.values() for i in v if not i["na_carteira"])

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
        "fonte": f"SS de indisponibilidade pendentes na {POSICAO} + mapeamento por "
                 "criticidade da ATUALIZADA 16 como anotação + cadeia de repasse + "
                 "plano de compras de 17/07 + leitura da taxa de falha",
        "visao_eto": {
            "total": total,
            "posicao": POSICAO,
            "fora_da_carteira": fora_da_carteira,
            "nota": "régua do gestor (22/08): a visão são os ativos 58/79 com SS de "
                    "indisponibilidade para operação pendente na base — o balde sai do "
                    "posto onde a SS está (PROT = ajuste; TELE/SE com criticidade definida "
                    "na aba de mapeamento = comissionamento, sem criticidade definida = "
                    "1º ataque do DMSL; RD = execução; COEP = aquisição, salvo «Em "
                    f"logística» da carteira). {fora_da_carteira} não estão na carteira.",
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
    print(f"visão ETO: {v['total']} ativos ({v['fora_da_carteira']} fora da carteira)")
    for b, d in v["baldes"].items():
        print(f"  {b:<20} {d['qtd']}")
    pd = p["pendentes_dcmd"]
    print(f"concluídos pelo DCMD em 2026: {p['concluidos_dcmd_2026']['qtd']}")
    print(f"aquisição no plano de compras: {pd['aquisicao_no_plano']} de {pd['aquisicao']}")
    print(f"gravado: {SAIDA}")
