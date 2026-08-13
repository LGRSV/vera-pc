"""
Carteira consolidada — as duas fotos fundidas numa lista só, com o ponto exato de cada ativo.

O gestor tem duas listas do mesmo posto em momentos diferentes:
  · a foto de entrada (junho): o que estava pendente no ETO-COEP quando ele assumiu — 117 ativos;
  · a lista de hoje (planilha ATUALIZADA6): o que está sendo acompanhado — 129 ativos.

Elas se cruzam em 87 ativos. Somadas sem repetir, são 159 equipamentos que passaram pelo posto.
Este módulo funde as duas e responde, por ativo, uma pergunta só: EM QUE PONTO ELE ESTÁ.

A escada de situações, do fim para o começo do fluxo:

  Em operação                  o equipamento está operando — check Ok/Em operação na planilha,
                               ou saiu da carteira por ter sido resolvido
  Executado, aguardando cauda  a troca foi feita; falta o ajuste da Proteção ou o comissionamento
                               do DMSL (regra do gestor: em ajuste ou comissionamento = já
                               manutencionado; bateria pelo DMSL é rotina e não conta)
  Em execução                  material entregue, obra em curso, check «Em andamento»
  Pendente no COEP             esperando compra ou logística — na mão do posto
  Pendente com outra equipe    parado no DMSL, DEOP ou DCMD
  Cancelada errada pelo DMSL   SS encerrada no sistema sem o serviço; conta como pendência
  Em análise                   primeiro ataque, sem parecer ainda
  Sem ação do COEP             desmobilizado — não era caso do posto
  Fora da análise              excluído por decisão do gestor

Precedência das fontes, na ordem: decisão do gestor > planilha de hoje (parecer, observação e
check) > base de SS/OS > veredito da carteira de entrada. Ativo que saiu da lista de hoje é lido
pela entrada e pela base.
"""

import json
import os
from collections import Counter, defaultdict

import demandas as D

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ_MIN = os.path.join(RAIZ, "data", "missao", "ssos_min.json")
ARQ_DECISOES = os.path.join(RAIZ, "data", "raw", "decisoes_gestor.json")

ESCADA = [
    "Em operação",
    "Executado, aguardando cauda",
    "Em execução",
    "Pendente no COEP",
    "Pendente com outra equipe",
    "Cancelada errada pelo DMSL",
    "Em análise",
    "Sem ação do COEP",
    "Fora da análise",
]

RESOLVIDAS = ("Em operação", "Executado, aguardando cauda", "Sem ação do COEP")
PENDENTES = ("Pendente no COEP", "Pendente com outra equipe", "Cancelada errada pelo DMSL")

PREMISSAS = [
    "Carteira consolidada = foto de entrada (junho, 117 ativos) ∪ lista de hoje (ATUALIZADA6, "
    "129 ativos), sem repetir ativo. O cruzamento é pelo CÓDIGO OPERATIVO.",
    "Precedência das fontes: decisão do gestor > planilha de hoje (parecer COEP, observação e "
    "check de concluídas) > base de SS/OS > veredito da carteira de entrada.",
    "Regra do gestor (13/08): equipamento em comissionamento ou em ajuste já foi manutencionado "
    "— o serviço foi feito e falta a cauda. Troca de bateria pelo DMSL é rotina e não conta.",
    "Ativo que saiu da lista de hoje e estava dado como resolvido na entrada conta como "
    "resolvido: ele deixou de ser acompanhado porque foi tratado.",
    "«Cancelada errada pelo DMSL» é pendência: a SS foi encerrada no sistema sem o serviço.",
    "Resolvido = em operação + executado aguardando cauda + sem ação do COEP. Pendente = no "
    "COEP + com outra equipe + cancelada errada. Em análise e em execução ficam à parte, "
    "porque não são nem uma coisa nem outra.",
]


def _decisoes():
    if not os.path.exists(ARQ_DECISOES):
        return {}
    with open(ARQ_DECISOES, encoding="utf-8") as fh:
        return {d["ativo"]: d for d in json.load(fh)}


def _posto(resumo_cadeia):
    return (resumo_cadeia or {}).get("posto_atual")


def montar(registros, entrada, acompanhamento):
    """Funde as duas carteiras e devolve a situação consolidada por ativo."""
    decisoes = _decisoes()

    with open(ARQ_MIN, encoding="utf-8") as fh:
        base = json.load(fh)
    por_ativo = defaultdict(list)
    for linha in base:
        por_ativo[(linha.get("NUM_TRAFO") or "").strip()].append(linha)

    hoje = {}
    for situacao, lista in (acompanhamento or {}).get("listas", {}).items():
        for item in lista:
            hoje[item["ativo"]] = {**item, "situacao_planilha": situacao}

    da_entrada = {}
    for chave in ("resolvidos", "verificar", "em_andamento"):
        for item in ((entrada or {}).get(chave) or {}).get("lista", []):
            da_entrada.setdefault(item["ativo"], {**item, "balde": chave})

    excluidos = {x["ativo"] for x in ((entrada or {}).get("excluidos") or [])}
    ficha = {r["ativo"]: r for r in registros}

    consolidado = []
    for ativo in sorted(set(hoje) | set(da_entrada) | excluidos):
        na_lista_hoje = ativo in hoje
        veio_da_entrada = ativo in da_entrada
        h = hoje.get(ativo, {})
        e = da_entrada.get(ativo, {})
        reg = ficha.get(ativo, {})
        decisao = decisoes.get(ativo)

        linhas = por_ativo.get(ativo, [])
        resumos = [D.resumir_demanda(c) for c in D.encadear(linhas)] if linhas else []
        aberta = next((r for r in resumos if r["situacao"] == "aberta" and not r["rotina"]), None)
        posto = _posto(aberta)

        origem = ("Nas duas listas" if na_lista_hoje and veio_da_entrada
                  else "Só na lista de hoje" if na_lista_hoje
                  else "Saiu da lista de hoje")

        # --- a escada ---
        situacao, porque = None, ""

        if ativo in excluidos:
            situacao = "Fora da análise"
            porque = (decisao or {}).get("nota", "excluído por decisão do gestor")

        elif decisao and decisao.get("decisao") == "pendente":
            situacao = ("Cancelada errada pelo DMSL"
                        if h.get("situacao_planilha") == "Cancelada errada pelo DMSL"
                        else "Pendente no COEP" if (posto or "COEP") == "COEP"
                        else "Pendente com outra equipe")
            porque = "decisão do gestor: segue pendente"

        elif decisao and decisao.get("decisao") == "executado":
            situacao = "Executado, aguardando cauda" if posto in ("DEOP", "DMSL") else "Em execução"
            porque = "decisão do gestor: execução confirmada em campo"

        elif h.get("sem_acao_coep"):
            situacao = "Sem ação do COEP"
            porque = "desmobilizado na planilha — não era caso do posto"

        elif h.get("situacao_planilha") == "Em operação":
            situacao = "Em operação"
            porque = f"check de concluídas «{h.get('check')}» na planilha de hoje"

        elif h.get("situacao_planilha") == "Cancelada errada pelo DMSL":
            situacao = "Cancelada errada pelo DMSL"
            porque = "SS dada como concluída no sistema com o check apontando pendência"

        elif h.get("situacao_planilha") == "Pendente no fluxo":
            situacao = "Pendente no COEP" if (posto or "COEP") == "COEP" else "Pendente com outra equipe"
            porque = f"check pendente na planilha; demanda {('no ' + posto) if posto else 'sem SS aberta na base'}"

        elif h.get("situacao_planilha") == "Em andamento":
            bucket = (h.get("bucket_parecer") or "")
            parecer = (h.get("parecer_coep") or "").upper()
            if "AJUSTE" in parecer or "COMISSION" in parecer or posto in ("DEOP", "DMSL"):
                situacao = "Executado, aguardando cauda"
                porque = "parecer de ajuste/comissionamento — o serviço já foi feito"
            else:
                situacao = "Em execução"
                porque = "check «Em andamento» — execução em curso"

        elif h.get("situacao_planilha") == "Em análise":
            situacao = "Em análise"
            porque = "check em branco na planilha de hoje"

        elif not na_lista_hoje:
            # saiu da lista: vale o que a entrada concluiu, conferido na base
            if e.get("balde") == "resolvidos":
                if aberta:
                    situacao = ("Executado, aguardando cauda" if posto in ("DEOP", "DMSL")
                                else "Pendente no COEP" if posto == "COEP"
                                else "Pendente com outra equipe")
                    porque = f"saiu da lista de acompanhamento, mas a base ainda mostra demanda no {posto}"
                else:
                    situacao = "Em operação"
                    porque = f"saiu da lista de acompanhamento — {e.get('motivo', 'resolvido na carteira de entrada')}"
            else:
                situacao = ("Pendente no COEP" if (posto or "COEP") == "COEP"
                            else "Pendente com outra equipe")
                porque = "saiu da lista de hoje sem ter sido dado por resolvido"
        else:
            situacao = "Em análise"
            porque = "sem sinal suficiente nas fontes"

        consolidado.append({
            "ativo": ativo,
            "localidade": reg.get("localidade") or h.get("localidade") or e.get("localidade") or "",
            "tipo": reg.get("tipo_nome") or h.get("tipo") or e.get("tipo") or "",
            "criticidade": reg.get("criticidade") or h.get("criticidade") or "",
            "situacao": situacao,
            "porque": porque,
            "origem": origem,
            "na_lista_hoje": na_lista_hoje,
            "veio_da_entrada": veio_da_entrada,
            "check": h.get("check", ""),
            "parecer_coep": h.get("parecer_coep") or reg.get("parecer_coep") or "",
            "observacao": h.get("observacao") or reg.get("observacao") or "",
            "ss_planilha": h.get("ss_planilha") or "",
            "posto_atual": posto,
            "ss_mais_recente": (h.get("na_base") or {}).get("ss_mais_recente")
                               or ((linhas[-1].get("NUMERO_SS") if linhas else "")),
            "entrada_balde": e.get("balde"),
            "entrada_motivo": e.get("motivo", ""),
            "decisao_gestor": (decisao or {}).get("decisao"),
        })

    # --- o corte que o gestor pediu: foi manutencionado? o que falta? ---
    for i in consolidado:
        parecer = (i["parecer_coep"] or "").upper()
        situacao = i["situacao"]
        posto = i["posto_atual"]

        manutencionado = situacao in ("Em operação", "Executado, aguardando cauda") or (
            i["decisao_gestor"] == "executado"
        )
        i["manutencionado"] = manutencionado

        if manutencionado:
            if situacao == "Em operação":
                i["falta"] = "Nada — em operação"
            elif posto == "DEOP":
                i["falta"] = "Ajuste da Proteção"
            elif posto == "DMSL":
                i["falta"] = "Comissionamento do DMSL"
            elif posto in ("COEP", "DCMD"):
                i["falta"] = "Baixa da SS no sistema"
            else:
                i["falta"] = "Nada — em operação"
            i["espera"] = ""
        else:
            i["falta"] = ""
            if situacao == "Cancelada errada pelo DMSL":
                i["espera"] = "Reabrir a SS que foi cancelada errada"
            elif situacao == "Em análise":
                i["espera"] = "Análise / primeiro ataque"
            elif "AQUISI" in parecer:
                i["espera"] = "Compra do material (aquisição)"
            elif "LOGIST" in parecer or "LOGISTICA" in parecer:
                i["espera"] = "Logística — material comprado, a caminho"
            elif "ENTREGUE" in parecer or "COCM" in parecer:
                i["espera"] = "Execução pelo COCM/DCMD — material já entregue"
            elif posto == "DMSL":
                i["espera"] = "Laudo do DMSL"
            elif posto == "Cadastro":
                i["espera"] = "Atualização cadastral"
            elif posto:
                i["espera"] = f"Com o {posto}"
            else:
                i["espera"] = "Sem SS aberta — indefinido"

    manutencionados = [i for i in consolidado if i["manutencionado"]]
    nao = [i for i in consolidado if not i["manutencionado"] and i["situacao"] != "Fora da análise"]

    resposta = {
        "manutencionados": {
            "total": len(manutencionados),
            "por_falta": dict(Counter(i["falta"] for i in manutencionados)),
            "listas": {
                f: [
                    {k: i[k] for k in ("ativo", "localidade", "tipo", "criticidade",
                                       "parecer_coep", "posto_atual", "origem", "porque")}
                    for i in sorted(manutencionados, key=lambda x: (x["localidade"] or "", x["ativo"]))
                    if i["falta"] == f
                ]
                for f in dict(Counter(i["falta"] for i in manutencionados))
            },
        },
        "nao_manutencionados": {
            "total": len(nao),
            "por_espera": dict(Counter(i["espera"] for i in nao).most_common()),
            "listas": {
                e: [
                    {k: i[k] for k in ("ativo", "localidade", "tipo", "criticidade",
                                       "parecer_coep", "posto_atual", "origem", "situacao")}
                    for i in sorted(nao, key=lambda x: (x["localidade"] or "", x["ativo"]))
                    if i["espera"] == e
                ]
                for e in dict(Counter(i["espera"] for i in nao))
            },
        },
    }

    por_situacao = Counter(i["situacao"] for i in consolidado)
    resolvidos = [i for i in consolidado if i["situacao"] in RESOLVIDAS]
    pendentes = [i for i in consolidado if i["situacao"] in PENDENTES]

    resumo = {
        "premissas": PREMISSAS,
        "total": len(consolidado),
        "por_situacao": {s: por_situacao.get(s, 0) for s in ESCADA},
        "por_origem": dict(Counter(i["origem"] for i in consolidado)),
        "resolvidos": len(resolvidos),
        "pendentes": len(pendentes),
        "em_execucao": por_situacao.get("Em execução", 0),
        "em_analise": por_situacao.get("Em análise", 0),
        "por_situacao_origem": [
            {"situacao": s, "origem": o, "total": n}
            for (s, o), n in sorted(Counter((i["situacao"], i["origem"]) for i in consolidado).items())
        ],
        "por_tipo": {
            s: dict(Counter(i["tipo"] for i in consolidado if i["situacao"] == s)) for s in ESCADA
        },
        "lista": sorted(
            consolidado,
            key=lambda i: (ESCADA.index(i["situacao"]), i["localidade"] or "", i["ativo"]),
        ),
    }
    resumo["resposta"] = resposta
    resumo["percentual_resolvido"] = round(100 * len(resolvidos) / max(len(consolidado), 1), 1)
    resumo["percentual_manutencionado"] = round(
        100 * resposta["manutencionados"]["total"] / max(len(consolidado) - por_situacao.get("Fora da análise", 0), 1), 1
    )

    for reg in registros:
        meu = next((i for i in consolidado if i["ativo"] == reg["ativo"]), None)
        if meu:
            reg["consolidado"] = {k: meu[k] for k in ("situacao", "porque", "origem",
                                                      "posto_atual", "manutencionado",
                                                      "falta", "espera")}

    return resumo
