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
  Executado — falta ajuste     a troca foi feita; falta o ajuste da Proteção ou o comissionamento
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
import unicodedata
from collections import Counter, defaultdict

import demandas as D

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ_MIN = os.path.join(RAIZ, "data", "missao", "ssos_min.json")
ARQ_DECISOES = os.path.join(RAIZ, "data", "raw", "decisoes_gestor.json")

ESCADA = [
    "Em operação",
    "Executado — falta ajuste ou comissionamento",
    "Em execução",
    "Pendente no COEP",
    "Pendente com outra equipe",
    "Cancelada errada pelo DMSL",
    "Em análise",
    "Sem ação do COEP",
    "Fora da análise",
]

RESOLVIDAS = ("Em operação", "Executado — falta ajuste ou comissionamento", "Sem ação do COEP")
PENDENTES = ("Pendente no COEP", "Pendente com outra equipe", "Cancelada errada pelo DMSL")

PREMISSAS = [
    "Carteira consolidada = foto de entrada (junho, 117 ativos) ∪ lista de hoje (ATUALIZADA6, "
    "129 ativos), sem repetir ativo. O cruzamento é pelo CÓDIGO OPERATIVO.",
    "Precedência das fontes: decisão do gestor > planilha de hoje (parecer COEP, observação e "
    "check de concluídas) > base de SS/OS > veredito da carteira de entrada.",
    "Regra do gestor (13/08): equipamento em comissionamento ou em ajuste já foi manutencionado "
    "— o serviço foi feito e falta a etapa seguinte do fluxo. Troca de bateria pelo DMSL é "
    "rotina e não conta.",
    "Ativo que saiu da lista de hoje e estava dado como resolvido na entrada conta como "
    "resolvido: ele deixou de ser acompanhado porque foi tratado.",
    "«Cancelada errada pelo DMSL» é pendência: a SS foi encerrada no sistema sem o serviço.",
    "Primeiro ataque é decidido pela DEMANDA ABERTA, não pelo histórico do ativo: se a cadeia "
    "aberta só passou pelo DMSL e nunca pelo COEP, é diagnóstico de campo — mesmo que o ativo "
    "tenha passado pelo posto numa demanda antiga, já encerrada (correção do gestor, 13/08, "
    "sobre o 7900275024 de Itaporã).",
    "Resolvido = em operação + executado esperando ajuste ou comissionamento + sem ação do "
    "COEP. Pendente = no "
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



# Marcadores de decisão de compra no texto do parecer, em ordem de firmeza.
_MARCA_FIRME = ("SELECIONADO PARA COMPRA", "SELECIONADO  PARA COMPRA", "SLEECIONADO")
_MARCA_FRACA = ("PARA COMPRA", "PARA A COMPRA", "PARA AQUISICAO", "PARA COMPRA / AQUISICAO")


def _sem_acento(texto):
    texto = unicodedata.normalize("NFD", (texto or "").upper())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _decisao_de_compra(aquisicao, ficha):
    """Separa quem já tem decisão de compra escrita no parecer de quem não tem.

    O gestor pergunta quantos dos que aguardam compra já foram pedidos. A resposta não está
    em nenhuma coluna: está no texto do parecer COEP, onde o posto escreve «EQUIPAMENTO
    SELECIONADO PARA COMPRA». Contamos o marcador firme separado do fraco (o COEP pedindo
    modelo e tensão para comprar), porque um é decisão tomada e o outro é decisão começando.
    """
    firmes, fracos, sem = [], [], []
    for item in aquisicao:
        reg = ficha.get(item["ativo"], {})
        texto = _sem_acento(
            " ".join([reg.get("descricao_ss") or "", item.get("parecer_coep") or "",
                      item.get("observacao") or ""])
        )
        resumo = {"ativo": item["ativo"], "localidade": item["localidade"],
                  "criticidade": item["criticidade"] or "Sem classificação",
                  "tipo": item["tipo"]}
        if any(m in texto for m in _MARCA_FIRME):
            firmes.append({**resumo, "marcador": "Equipamento selecionado para compra"})
        elif any(m in texto for m in _MARCA_FRACA):
            # O parecer pede modelo e tensão, mas o gestor confirmou em 13/08 que a
            # especificação já existe — o que falta nesses é só o pedido de compra.
            fracos.append({**resumo, "marcador": "Compra citada, sem pedido registrado"})
        else:
            sem.append({**resumo, "marcador": ""})

    # Regra do gestor (13/08): pedir modelo e tensão ainda não é compra pedida — é o COEP
    # levantando a especificação. Esses contam com quem ainda não tem pedido nenhum.
    ordenar = lambda l: sorted(l, key=lambda x: (x["localidade"] or "", x["ativo"]))
    return {
        "com_decisao": len(firmes),
        "decisao_firme": len(firmes),
        "aguardando_especificacao": len(fracos),
        "sem_pedido": len(fracos) + len(sem),
        "lista_decisao_firme": ordenar(firmes),
        "lista_aguardando_especificacao": ordenar(fracos),
        "lista_sem_pedido": ordenar(fracos + sem),
        "criterio_do_corte": (
            "Compra pedida é quem carrega «equipamento selecionado para compra» no parecer do "
            "COEP. O plano de compras cobre só a criticidade Muito Alta e Alta."
        ),
    }


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
    fora_da_analise = []
    for ativo in sorted(set(hoje) | set(da_entrada) | excluidos):
        if ativo in excluidos:
            fora_da_analise.append({
                "ativo": ativo,
                "localidade": (decisoes.get(ativo) or {}).get("localidade", ""),
                "nota": (decisoes.get(ativo) or {}).get("nota", ""),
                "data": (decisoes.get(ativo) or {}).get("data", ""),
            })
            continue
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
        # Cadastro (CADTOC) não é etapa do fluxo de manutenção: SS de atualização cadastral
        # não segura equipamento no poste. Pedido do gestor em 13/08 — tirar esse balde.
        if posto == "Cadastro":
            aberta, posto = None, None
        # A demanda ABERTA é que conta para dizer se é primeiro ataque. O ativo pode ter
        # passado pelo COEP numa demanda antiga, já encerrada — como o 7900275024 (Itaporã),
        # cuja SS de 2025 foi cancelada e a SS aberta é uma da TELE de 10/08/2026, sozinha
        # na cadeia. Correção apontada pelo gestor em 13/08.
        cadeia_passou_coep = bool(aberta) and any(
            "COEP" in (s.get("equipe") or "").upper() for s in (aberta.get("ss") or [])
        )
        cadeia_so_dmsl = bool(aberta) and set(aberta.get("postos") or []) == {"DMSL"}

        origem = ("Nas duas listas" if na_lista_hoje and veio_da_entrada
                  else "Só na lista de hoje" if na_lista_hoje
                  else "Saiu da lista de hoje")

        # --- a escada ---
        situacao, porque = None, ""

        if decisao and decisao.get("decisao") == "pendente":
            situacao = ("Cancelada errada pelo DMSL"
                        if h.get("situacao_planilha") == "Cancelada errada pelo DMSL"
                        else "Pendente no COEP" if (posto or "COEP") == "COEP"
                        else "Pendente com outra equipe")
            porque = "decisão do gestor: segue pendente"

        elif decisao and decisao.get("decisao") == "executado":
            situacao = "Executado — falta ajuste ou comissionamento" if posto in ("DEOP", "DMSL") else "Em execução"
            porque = "decisão do gestor: execução confirmada em campo"

        elif h.get("sem_acao_coep"):
            situacao = "Sem ação do COEP"
            porque = "desmobilizado na planilha — não era caso do posto"

        elif h.get("situacao_planilha") == "Em operação":
            # Leitura dos 3 revisores (13/08): o check «Ok» conta a troca, não o fecho do
            # processo. Palmeiras (7967181127) está com a chave faca trocada em 01/07 e a
            # ETO-TELE 01035/2026 PENDENTE de comissionamento — é executado, não fechado.
            if posto in ("DEOP", "DMSL"):
                situacao = "Executado — falta ajuste ou comissionamento"
                porque = (f"check «{h.get('check')}» na planilha, mas a base mostra SS aberta "
                          f"no {posto} — falta o ajuste/comissionamento")
            else:
                situacao = "Em operação"
                porque = f"check de concluídas «{h.get('check')}» na planilha de hoje"

        elif h.get("situacao_planilha") == "Cancelada errada pelo DMSL":
            situacao = "Cancelada errada pelo DMSL"
            porque = "SS dada como concluída no sistema com o check apontando pendência"

        elif h.get("situacao_planilha") == "Pendente no fluxo":
            situacao = "Pendente no COEP" if (posto or "COEP") == "COEP" else "Pendente com outra equipe"
            porque = f"check pendente na planilha; demanda {('no ' + posto) if posto else 'sem SS aberta na base'}"

        elif h.get("situacao_planilha") == "Em andamento":
            parecer = (h.get("parecer_coep") or "").upper()
            executado_no_parecer = any(
                x in parecer for x in ("AJUSTE", "COMISSION", "CONCLU", "SUBSTITU", "MELHORIA")
            )
            # Contraprova dos revisores (13/08): o parecer é a última DECISÃO conhecida, não o
            # estado do ativo. Quando existe SS aberta depois dele, quem manda é a SS — foi o
            # que pegou o furto de cabo de Ponte Alta (30/07) e o comissionamento pendente de
            # Palmeiras. Sem SS aberta, aí sim o parecer decide.
            if not posto:
                situacao = "Em operação" if executado_no_parecer else "Em execução"
                porque = ("parecer registra o serviço feito e não há SS aberta no ativo"
                          if executado_no_parecer else "check «Em andamento», sem SS aberta")
            elif posto in ("DEOP", "DMSL"):
                situacao = "Executado — falta ajuste ou comissionamento"
                porque = f"serviço feito; SS aberta no {posto} — ajuste ou comissionamento"
            elif posto in ("DCMD", "COEP") and executado_no_parecer:
                situacao = "Em execução"
                porque = (f"parecer registra serviço feito, mas há SS aberta no {posto} — "
                          "ciclo novo ou execução em curso")
            else:
                situacao = "Em execução"
                porque = "check «Em andamento» — execução em curso"

        elif h.get("situacao_planilha") == "Em análise":
            situacao = "Em análise"
            porque = "check em branco na planilha de hoje"

        elif not na_lista_hoje:
            # saiu da lista: vale o que a entrada concluiu, conferido na base
            if e.get("balde") == "resolvidos":
                if aberta and cadeia_so_dmsl and not cadeia_passou_coep:
                    situacao = "Em análise"
                    porque = ("a demanda antiga foi encerrada; a SS aberta é nova, sozinha no DMSL — "
                              "primeiro ataque")
                elif aberta:
                    situacao = ("Executado — falta ajuste ou comissionamento" if posto in ("DEOP", "DMSL")
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
            "cadeia_passou_coep": cadeia_passou_coep,
            "cadeia_so_dmsl": cadeia_so_dmsl,
        })

    # --- o corte que o gestor pediu: foi manutencionado? o que falta? ---
    for i in consolidado:
        parecer = (i["parecer_coep"] or "").upper()
        situacao = i["situacao"]
        posto = i["posto_atual"]

        motivo_entrada = (i.get("entrada_motivo") or "").lower()
        so_cancelamento = (
            "cancelada" in motivo_entrada
            and "obra" not in motivo_entrada
            and not any(x in parecer for x in ("CONCLU", "SUBSTITU", "AJUSTE", "COMISSION"))
        )
        resolvido = situacao in ("Em operação", "Executado — falta ajuste ou comissionamento",
                                 "Sem ação do COEP") or i["decisao_gestor"] == "executado"
        # Contraprova dos revisores: cancelamento não é manutenção. O ativo pode estar
        # resolvido (operando) sem que ninguém tenha subido no poste.
        manutencionado = resolvido and not so_cancelamento
        i["resolvido"] = resolvido
        i["manutencionado"] = manutencionado
        i["resolvido_por_cancelamento"] = resolvido and so_cancelamento

        if manutencionado:
            if situacao == "Em operação" or not posto:
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
                i["espera"] = "Primeiro ataque / Laudo do DMSL"
            elif "AQUISI" in parecer:
                i["espera"] = "Compra do material (aquisição)"
            elif "LOGIST" in parecer or "LOGISTICA" in parecer:
                i["espera"] = "Logística — material comprado, a caminho"
            elif "ENTREGUE" in parecer or "COCM" in parecer:
                i["espera"] = "Execução pelo COCM/DCMD — material já entregue"
            elif posto == "DMSL":
                i["espera"] = "Primeiro ataque / Laudo do DMSL"
            elif posto:
                i["espera"] = f"Com o {posto}"
            elif situacao == "Pendente no COEP":
                i["espera"] = "Com o COEP"
            else:
                i["espera"] = "Sem SS aberta — indefinido"

    for i in consolidado:
        if not i["manutencionado"]:
            i["como_resolveu"] = ""
            continue
        motivo = (i.get("entrada_motivo") or "").lower()
        parecer = (i["parecer_coep"] or "").upper()
        porque = (i["porque"] or "").lower()
        if i["falta"] == "Ajuste da Proteção":
            i["como_resolveu"] = "Trocado — falta o ajuste da Proteção"
        elif i["falta"] == "Comissionamento do DMSL":
            i["como_resolveu"] = "Trocado — falta o comissionamento do DMSL"
        elif i["falta"] == "Baixa da SS no sistema":
            i["como_resolveu"] = "Trocado — falta só baixar a SS"
        elif "cancelad" in motivo or "cancelad" in porque:
            i["como_resolveu"] = "Cancelada — equipamento operando, sem precisar de SS nova"
        elif "obra encerrada" in motivo:
            i["como_resolveu"] = "Obra encerrada no AIC"
        elif "comissionamento" in motivo:
            i["como_resolveu"] = "Comissionamento concluído"
        elif "desmobilizado" in porque or i["situacao"] == "Sem ação do COEP":
            i["como_resolveu"] = "Desmobilizado — não era caso do posto"
        elif "check de concluídas" in porque:
            i["como_resolveu"] = "Check de concluídas «Ok» na planilha de hoje"
        elif "concluída" in motivo or "CONCLU" in parecer or "SUBSTITU" in parecer:
            i["como_resolveu"] = "Serviço concluído e registrado"
        else:
            i["como_resolveu"] = "Resolvido — origem registrada na ficha"

    manutencionados = [i for i in consolidado if i["manutencionado"]]
    por_cancelamento = [i for i in consolidado if i.get("resolvido_por_cancelamento")]
    nao = [i for i in consolidado if not i["resolvido"] and i["situacao"] != "Fora da análise"]

    resposta = {
        "resolvidos_total": len([i for i in consolidado if i.get("resolvido")]),
        "por_cancelamento": {
            "total": len(por_cancelamento),
            "lista": [
                {k: i[k] for k in ("ativo", "localidade", "tipo", "criticidade", "parecer_coep",
                                   "entrada_motivo", "origem")}
                for i in sorted(por_cancelamento, key=lambda x: (x["localidade"] or "", x["ativo"]))
            ],
        },
        "manutencionados": {
            "total": len(manutencionados),
            "por_falta": dict(Counter(i["falta"] for i in manutencionados)),
            "por_como_resolveu": dict(Counter(i["como_resolveu"] for i in manutencionados).most_common()),
            "listas_como": {
                k: [
                    {kk: i[kk] for kk in ("ativo", "localidade", "tipo", "criticidade",
                                          "parecer_coep", "posto_atual", "origem")}
                    for i in sorted(manutencionados, key=lambda x: (x["localidade"] or "", x["ativo"]))
                    if i["como_resolveu"] == k
                ]
                for k in dict(Counter(i["como_resolveu"] for i in manutencionados))
            },
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
        "fora_da_analise": fora_da_analise,
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
    # --- recorte DCMD: tira o primeiro ataque, que ainda não é do posto ---
    # Regra do gestor (13/08): equipamento parado no DMSL sem ter passado pelo COEP, ou
    # marcado «Novo», está em primeiro ataque — diagnóstico de campo. Não é análise do DCMD.
    for i in consolidado:
        i["primeiro_ataque"] = (
            not i["manutencionado"]
            and i["situacao"] != "Fora da análise"
            and (i["espera"] == "Primeiro ataque / Laudo do DMSL"
                 or i["posto_atual"] == "DMSL")
            and not i.get("cadeia_passou_coep")
        )

    recorte = [i for i in consolidado if not i["primeiro_ataque"] and i["situacao"] != "Fora da análise"]
    ataque = [i for i in consolidado if i["primeiro_ataque"]]
    # não-resolvidos do recorte: cancelamento também tira o ativo da fila do DCMD
    nao_rec = [i for i in recorte if not i["resolvido"]]

    resumo["recorte_dcmd"] = {
        "total": len(recorte),
        "manutencionados": sum(1 for i in recorte if i["manutencionado"]),
        "resolvidos": sum(1 for i in recorte if i["resolvido"]),
        "por_cancelamento": sum(1 for i in recorte if i.get("resolvido_por_cancelamento")),
        "nao_manutencionados": len(nao_rec),
        "por_espera": dict(Counter(i["espera"] for i in nao_rec).most_common()),
        "por_posto": dict(Counter(i["posto_atual"] or "sem SS aberta" for i in nao_rec).most_common()),
        "no_coep": sum(1 for i in nao_rec if (i["posto_atual"] or "COEP") == "COEP"),
        "nos_cocm": sum(1 for i in nao_rec if i["posto_atual"] == "DCMD"),
        "primeiro_ataque": {
            "total": len(ataque),
            "novos": sum(1 for i in ataque if (i["parecer_coep"] or "").upper() == "NOVO"),
            "lista": [
                {k: i[k] for k in ("ativo", "localidade", "tipo", "criticidade", "parecer_coep",
                                   "posto_atual", "ss_planilha")}
                for i in sorted(ataque, key=lambda x: (x["localidade"] or "", x["ativo"]))
            ],
        },
        "percentual_manutencionado": round(
            100 * sum(1 for i in recorte if i["manutencionado"]) / max(len(recorte), 1), 1
        ),
        "percentual_resolvido": round(
            100 * sum(1 for i in recorte if i["resolvido"]) / max(len(recorte), 1), 1
        ),
    }

    # --- auditoria da base: de onde vêm os números e se há repetição ---
    import re as _re

    validos = [i["ativo"] for i in consolidado if _re.fullmatch(r"(79|58)\d{8}", i["ativo"])]
    repetidos = {a: n for a, n in Counter(i["ativo"] for i in consolidado).items() if n > 1}
    universo_2026 = set()
    for ativo, linhas in por_ativo.items():
        if not _re.fullmatch(r"(79|58)\d{8}", ativo):
            continue
        for l in linhas:
            data = l.get("DATA_ABERTURA_SS") or ""
            ano = data[6:10] if "/" in data else data[:4]
            if ano == "2026":
                universo_2026.add(ativo)
                break
    quase_iguais = []
    ordenados = sorted({i["ativo"] for i in consolidado})
    for x in range(len(ordenados)):
        for y in range(x + 1, len(ordenados)):
            a, b = ordenados[x], ordenados[y]
            if sum(1 for p1, p2 in zip(a, b) if p1 != p2) == 1:
                quase_iguais.append([a, b])

    resumo["auditoria"] = {
        "entrada_distintos": len(set(da_entrada) | excluidos),
        "excluidos": len(excluidos),
        "hoje_distintos": len(hoje),
        "em_comum": len((set(da_entrada) | excluidos) & set(hoje)),
        "uniao": len(consolidado) + len(excluidos),
        "na_analise": len(consolidado),
        "linhas": len(consolidado),
        "distintos": len({i["ativo"] for i in consolidado}),
        "codigos_validos": len(validos),
        "repetidos": repetidos,
        "quase_iguais": quase_iguais,
        "universo_2026": len(universo_2026),
        "universo_2026_na_carteira": len(universo_2026 & {i["ativo"] for i in consolidado}),
    }
    plano = os.path.join(RAIZ, "data", "raw", "plano_compras.csv")
    if os.path.exists(plano):
        import csv as _csv

        por_ativo_plano = defaultdict(lambda: {"itens": 0, "valor": 0.0, "materiais": []})
        with open(plano, encoding="utf-8") as fh:
            for item in _csv.DictReader(fh, delimiter=";"):
                ativo_item = (item.get("Ativo") or "").strip()
                if not ativo_item:
                    continue
                alvo = por_ativo_plano[ativo_item]
                alvo["itens"] += 1
                try:
                    alvo["valor"] += float(item.get("Valor Total") or 0)
                except ValueError:
                    pass
                alvo["materiais"].append((item.get("Material") or "").split("·")[-1].strip())
        aquisicao = [i for i in consolidado if i.get("espera") == "Compra do material (aquisição)"]
        dentro = [i for i in aquisicao if i["ativo"] in por_ativo_plano]
        fora_plano = [i for i in aquisicao if i["ativo"] not in por_ativo_plano]
        resposta["aquisicao_x_plano"] = {
            "em_aquisicao": len(aquisicao),
            "no_plano": len(dentro),
            "fora_do_plano": len(fora_plano),
            "valor_no_plano": round(sum(por_ativo_plano[i["ativo"]]["valor"] for i in dentro), 2),
            "lista_no_plano": [
                {"ativo": i["ativo"], "localidade": i["localidade"], "criticidade": i["criticidade"],
                 "valor": round(por_ativo_plano[i["ativo"]]["valor"], 2),
                 "itens": por_ativo_plano[i["ativo"]]["itens"],
                 "materiais": por_ativo_plano[i["ativo"]]["materiais"]}
                for i in sorted(dentro, key=lambda x: -por_ativo_plano[x["ativo"]]["valor"])
            ],
            "lista_fora": [
                {"ativo": i["ativo"], "localidade": i["localidade"], "criticidade": i["criticidade"],
                 "tipo": i["tipo"], "parecer_coep": i["parecer_coep"]}
                for i in sorted(fora_plano, key=lambda x: (x["localidade"] or "", x["ativo"]))
            ],
        }
        resposta["aquisicao_x_plano"].update(_decisao_de_compra(aquisicao, ficha))
        # O plano só cobre Muito Alta e Alta. Quem tem compra pedida e ficou fora dele é,
        # por construção, Média ou Baixa — vale dizer isso em número, não em suposição.
        _apx = resposta["aquisicao_x_plano"]
        _no_plano = {i["ativo"] for i in dentro}
        _pedidos = {i["ativo"] for i in _apx["lista_decisao_firme"]}
        _apx["no_plano_com_pedido"] = len(_no_plano & _pedidos)
        _apx["fora_do_plano_com_pedido"] = len(_pedidos - _no_plano)
        _apx["fora_do_plano_com_pedido_lista"] = [
            i for i in _apx["lista_decisao_firme"] if i["ativo"] not in _no_plano
        ]

    resumo["resposta"] = resposta
    # o percentual segue a mesma régua do balde "Resolvidos" da primeira visão:
    # manutencionados + resolvidos por cancelamento + decisão do gestor.
    resumo["percentual_resolvido"] = round(
        100 * resposta["resolvidos_total"] / max(len(consolidado), 1), 1
    )
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
