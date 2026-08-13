"""
Acompanhamento atual — a categorização que o gestor pediu em 13/08, sobre a planilha
ATUALIZADA6 (aba «Criticidade por Equipamento»), que é o parecer mais recente.

As réguas, na ordem em que são aplicadas:

  Check «Ok», «Em operação» ou «Desmobilizado»      → EM OPERAÇÃO
      (Desmobilizado ainda ganha a marca «não deveria ter ação do COEP»)
  Check «Pendente» com a SS marcada CONCLUÍDA       → CANCELADA ERRADA PELO DMSL
  Check «Pendente» com a SS ainda aberta            → PENDENTE NO FLUXO
  Check «Em andamento»                              → EM ANDAMENTO
  Check em branco                                   → EM ANÁLISE

Por que o Check só vira «cancelada errada» quando a SS está CONCLUÍDA: a coluna é a
conferência das SS que o sistema deu por encerradas. Com a SS aberta, «Pendente» quer dizer
apenas que a pendência continua. As quatro linhas em que o próprio gestor escreveu
«Cancelada errada pelo DMSL» na Observação têm exatamente esse par — SS CONCLUÍDA + Check
Pendente —, o que confirma a leitura.

Cada ativo é conferido contra a base de SS/OS pelo código operativo: a SS mais recente do
ativo, a situação dela e o posto onde a demanda está. Quando a planilha e a base discordam,
a divergência é listada com as duas versões.
"""

import json
import os
import re
from collections import Counter, defaultdict

import demandas as D

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ_MIN = os.path.join(RAIZ, "data", "missao", "ssos_min.json")
ARQ_SS_129 = os.path.join(RAIZ, "data", "missao", "ssos_129.json")
ARQ_DECISOES = os.path.join(RAIZ, "data", "raw", "decisoes_gestor.json")

SITUACOES = [
    "Em operação",
    "Cancelada errada pelo DMSL",
    "Pendente no fluxo",
    "Em andamento",
    "Em análise",
]

PREMISSAS = [
    "Fonte: planilha «Relação dos Equipamentos Indisponíveis ETO ATUALIZADA6», aba "
    "«Criticidade por Equipamento» — o parecer COEP mais recente (13/08). Os 129 ativos são "
    "os mesmos da versão anterior; 25 pareceres mudaram e entraram 13 marcados «Novo».",
    "Check em branco NÃO significa automaticamente «em análise»: quando há parecer COEP, é ele "
    "que manda (correção apontada pelo gestor em 13/08 no ativo 7953610256, que tinha parecer "
    "«Concluído DCMD» e caiu em análise por causa do check vazio). Em análise fica quem não tem "
    "check nem parecer — os marcados «Novo», do primeiro ataque.",
    "Régua do gestor (13/08) sobre a coluna «Check de concluídas»: Ok, Em operação ou "
    "Desmobilizado = equipamento em operação; Pendente com a SS dada como CONCLUÍDA = "
    "cancelada errada pelo DMSL; Pendente com a SS ainda aberta = pendência seguindo no "
    "fluxo; Em andamento = execução em curso; em branco = em análise.",
    "Desmobilizado é caso em que não deveria ter havido ação do COEP — o equipamento saiu de "
    "operação por decisão de rede, não por defeito.",
    "Cada ativo é casado com a base de SS/OS pelo CÓDIGO OPERATIVO (NUM_TRAFO), não pelo "
    "número da SS: a SS da planilha pode estar defasada, e o mesmo defeito troca de número a "
    "cada repasse.",
    "Divergência = a planilha diz uma coisa e a base de SS/OS mostra outra (SS dada como "
    "concluída com demanda aberta na base, ou pendência declarada sem nenhuma SS aberta). "
    "São indícios para conferência, não conclusões.",
    "Parecer «Novo» são as SS de primeiro ataque abertas pela TELE que ainda não passaram "
    "pelo COEP — por isso não têm parecer nem criticidade calculada.",
    "Regra do gestor (13/08): equipamento em COMISSIONAMENTO ou em AJUSTE já foi manutencionado "
    "— alguém foi ao ativo e fez o serviço. A exceção é troca de bateria pelo DMSL, que é rotina "
    "e não conta como ação do posto.",
    "Cancelada errada pelo DMSL é uma forma de PENDÊNCIA (decisão do gestor, 13/08): a SS foi "
    "encerrada no sistema sem o serviço ter sido feito, então o equipamento continua pendente. "
    "As duas categorias somam a pendência total.",
    "As decisões do gestor (data/raw/decisoes_gestor.json) valem aqui também: «pendente» força o "
    "ativo para a pendência mesmo quando a planilha o daria por resolvido.",
]


def _txt(valor):
    return str(valor).strip() if valor is not None else ""


def _situacao(check, ss_aberta, parecer=""):
    """A régua do gestor. Quando o check está em branco, quem manda é o PARECER.

    Defeito corrigido em 13/08, apontado pelo gestor no ativo 7953610256: o check vazio
    estava atropelando um parecer «Concluído DCMD» e jogando o ativo em «Em análise».
    Em branco só significa «em análise» quando o parecer também não diz nada — que é o caso
    dos marcados «Novo», o primeiro ataque da TELE.
    """
    c = check.strip().lower()
    ss = ss_aberta.strip().upper()
    p = (parecer or "").strip().upper()
    concluida = "CONCLU" in ss

    if c in ("ok", "em operação", "em operacao", "desmobilizado"):
        return "Em operação"
    if c == "pendente":
        return "Cancelada errada pelo DMSL" if concluida else "Pendente no fluxo"
    if c == "em andamento":
        return "Em andamento"

    # check em branco: o parecer decide
    if not p or p == "NOVO":
        return "Em análise"
    if "CONCLU" in p or "SUBSTITU" in p or "MELHORIA" in p and "CONCLU" in p:
        return "Em andamento"       # serviço feito; o que falta é a etapa seguinte do fluxo
    if "COMISSION" in p or "AJUSTE" in p:
        return "Em andamento"
    if "OPERANDO" in p or "EM OPERA" in p or "LINHA VIVA" in p:
        return "Em operação"
    if "AQUISI" in p or "LOG" in p or "ENTREGUE" in p or "COCM" in p:
        return "Pendente no fluxo"
    if "ATAQUE" in p or "DMSL" in p:
        return "Em análise"
    return "Pendente no fluxo"


def _bucket_parecer(parecer):
    p = (parecer or "").upper()
    if not p.strip():
        return "Sem parecer"
    if "NOVO" in p:
        return "Novo — primeiro ataque"
    if "AQUISI" in p:
        return "Em aquisição"
    if "LOG" in p or "ENTREGUE" in p or "COCM" in p:
        return "Logística / entregue ao COCM"
    if "AJUSTE" in p:
        return "Em ajustes"
    if "COMISSION" in p:
        return "Aguardando comissionamento"
    if "CONCLU" in p or "SUBSTITU" in p:
        return "Concluído / substituído"
    if "DMSL" in p or "ATAQUE" in p:
        return "Com o DMSL"
    return "Outros"


def _decisoes():
    if not os.path.exists(ARQ_DECISOES):
        return {}
    with open(ARQ_DECISOES, encoding="utf-8") as fh:
        return {d["ativo"]: d for d in json.load(fh)}


def montar(registros, entrada=None):
    """Classifica os 129 e confere cada um contra a base de SS/OS."""
    decisoes = _decisoes()
    with open(ARQ_MIN, encoding="utf-8") as fh:
        base = json.load(fh)
    textos = {}
    if os.path.exists(ARQ_SS_129):
        with open(ARQ_SS_129, encoding="utf-8") as fh:
            for linha in json.load(fh):
                textos[_txt(linha.get("NUMERO_SS"))] = " ".join(
                    f"{linha.get('DESCRIPTION_SS') or ''} {linha.get('DESCRICAO_OS') or ''}".split()
                )

    por_ativo = defaultdict(list)
    for linha in base:
        por_ativo[_txt(linha.get("NUM_TRAFO"))].append(linha)

    entrada_por_ativo = {}
    for chave in ("resolvidos", "verificar", "em_andamento"):
        for item in ((entrada or {}).get(chave) or {}).get("lista", []):
            entrada_por_ativo.setdefault(item["ativo"], chave)

    itens, divergencias = [], []

    for reg in registros:
        ativo = reg["ativo"]
        check = _txt(reg.get("check"))
        ss_planilha = _txt(reg.get("ss"))
        parecer = _txt(reg.get("parecer_coep"))
        observacao = _txt(reg.get("observacao"))
        situacao = _situacao(check, ss_planilha, parecer)
        decisao = decisoes.get(ativo)
        if decisao and decisao.get("decisao") == "pendente" and situacao not in (
            "Cancelada errada pelo DMSL", "Pendente no fluxo"
        ):
            situacao = "Pendente no fluxo"
        if decisao and decisao.get("decisao") == "executado" and situacao == "Em análise":
            situacao = "Em andamento"

        linhas = por_ativo.get(ativo, [])
        ordenadas = sorted(linhas, key=lambda l: _txt(l.get("DATA_ABERTURA_SS")))
        ultima = ordenadas[-1] if ordenadas else None
        abertas = [l for l in linhas if l.get("SITUACAO_SS") == "SS PENDENTE"]
        cadeias = D.encadear(linhas) if linhas else []
        resumos = [D.resumir_demanda(c) for c in cadeias]
        aberta_agora = next((r for r in resumos if r["situacao"] == "aberta" and not r["rotina"]), None)

        na_base = {
            "ss_mais_recente": _txt((ultima or {}).get("NUMERO_SS")),
            "equipe": _txt((ultima or {}).get("COD_EQUIPE")),
            "situacao": _txt((ultima or {}).get("SITUACAO_SS")),
            "abertura": _txt((ultima or {}).get("DATA_ABERTURA_SS"))[:10],
            "ss_abertas": len(abertas),
            "posto_atual": (aberta_agora or {}).get("posto_atual"),
            "demanda_aberta": bool(aberta_agora),
        }

        # divergências entre a planilha e a base
        alertas = []
        if situacao == "Em operação" and aberta_agora:
            alertas.append(
                f"a planilha dá como em operação, mas a base tem demanda aberta no "
                f"{aberta_agora['posto_atual']} (SS {na_base['ss_mais_recente']})"
            )
        if situacao == "Cancelada errada pelo DMSL" and not aberta_agora:
            alertas.append(
                "marcada como cancelada errada pelo DMSL, mas a base não mostra nenhuma "
                "demanda aberta — a reabertura ainda não foi feita"
            )
        if situacao in ("Pendente no fluxo", "Em andamento") and not aberta_agora:
            alertas.append(
                "a planilha trata como pendência viva, mas na base de SS/OS não há demanda "
                "aberta neste ativo"
            )
        if "CONCLU" in ss_planilha.upper() and aberta_agora:
            alertas.append(
                f"SS dada como CONCLUÍDA na planilha, com demanda aberta na base "
                f"({aberta_agora['posto_atual']})"
            )
        if not linhas:
            alertas.append("ativo sem nenhuma SS na base de SS/OS")

        item = {
            "ativo": ativo,
            "tipo": reg.get("tipo_nome"),
            "localidade": reg.get("localidade"),
            "polo": reg.get("polo"),
            "criticidade": reg.get("criticidade"),
            "situacao": situacao,
            "sem_acao_coep": check.strip().lower() == "desmobilizado",
            "check": check or "(em branco)",
            "ss_planilha": ss_planilha,
            "parecer_coep": parecer,
            "bucket_parecer": _bucket_parecer(parecer),
            "observacao": observacao,
            "na_base": na_base,
            "alertas": alertas,
            "na_carteira_entrada": entrada_por_ativo.get(ativo),
            "decisao_gestor": decisao,
            "texto_ultima_ss": textos.get(na_base["ss_mais_recente"], "")[:400],
        }
        itens.append(item)
        if alertas:
            divergencias.append(item)

    repetidos = {a: n for a, n in Counter(i["ativo"] for i in itens).items() if n > 1}

    def lista(situacao):
        return [
            {k: i[k] for k in ("ativo", "tipo", "localidade", "criticidade", "check",
                               "ss_planilha", "parecer_coep", "observacao", "na_base",
                               "alertas", "sem_acao_coep", "na_carteira_entrada",
                               "decisao_gestor")}
            for i in sorted(itens, key=lambda x: (x["localidade"] or "", x["ativo"]))
            if i["situacao"] == situacao
        ]

    resumo = {
        "premissas": PREMISSAS,
        "total": len(itens),
        "por_situacao": {s: sum(1 for i in itens if i["situacao"] == s) for s in SITUACOES},
        "por_situacao_tipo": {
            s: dict(Counter(i["tipo"] for i in itens if i["situacao"] == s)) for s in SITUACOES
        },
        "por_parecer": dict(Counter(i["bucket_parecer"] for i in itens).most_common()),
        "sem_acao_coep": sum(1 for i in itens if i["sem_acao_coep"]),
        "ativos_repetidos": repetidos,
        "listas": {s: lista(s) for s in SITUACOES},
        "divergencias": [
            {k: i[k] for k in ("ativo", "localidade", "situacao", "check", "ss_planilha",
                               "parecer_coep", "observacao", "na_base", "alertas",
                               "texto_ultima_ss")}
            for i in sorted(divergencias, key=lambda x: (x["situacao"], x["ativo"]))
        ],
        "total_divergencias": len(divergencias),
        "pendencia_total": sum(
            1 for i in itens if i["situacao"] in ("Pendente no fluxo", "Cancelada errada pelo DMSL")
        ),
        "decisoes_gestor": [
            {"ativo": i["ativo"], "localidade": i["localidade"], "situacao": i["situacao"],
             "decisao": (i["decisao_gestor"] or {}).get("decisao"),
             "nota": (i["decisao_gestor"] or {}).get("nota", "")}
            for i in sorted(itens, key=lambda x: x["ativo"]) if i.get("decisao_gestor")
        ],
    }

    # ponte entre as duas fotos: quem veio da entrada, quem saiu, quem é novo
    if entrada:
        entrada_todos = {}
        for chave in ("resolvidos", "verificar", "em_andamento"):
            for item in (entrada.get(chave) or {}).get("lista", []):
                entrada_todos.setdefault(item["ativo"], {**item, "balde": chave})
        atuais = {i["ativo"] for i in itens}
        sairam = [v for a, v in sorted(entrada_todos.items()) if a not in atuais]
        novos = [i for i in itens if i["ativo"] not in entrada_todos]
        resumo["reconciliacao"] = {
            "entrada_total": len(entrada_todos),
            "continuam": len(entrada_todos) - len(sairam),
            "sairam": len(sairam),
            "sairam_resolvidos": sum(1 for v in sairam if v["balde"] == "resolvidos"),
            "novos": len(novos),
            "novos_por_situacao": dict(Counter(i["situacao"] for i in novos)),
            "lista_sairam": [
                {"ativo": v["ativo"], "localidade": v.get("localidade"), "tipo": v.get("tipo"),
                 "balde": v["balde"], "motivo": v.get("motivo", "")}
                for v in sorted(sairam, key=lambda x: (x.get("localidade") or "", x["ativo"]))
            ],
            "lista_novos": [
                {"ativo": i["ativo"], "localidade": i["localidade"], "tipo": i["tipo"],
                 "situacao": i["situacao"], "check": i["check"], "parecer_coep": i["parecer_coep"],
                 "ss_planilha": i["ss_planilha"]}
                for i in sorted(novos, key=lambda x: (x["situacao"], x["localidade"] or "", x["ativo"]))
            ],
        }

    # confronto com a carteira de entrada
    if entrada:
        confronto = Counter()
        for i in itens:
            de_onde = i["na_carteira_entrada"]
            if de_onde:
                confronto[(de_onde, i["situacao"])] += 1
        resumo["confronto_entrada"] = [
            {"entrada": k[0], "acompanhamento": k[1], "total": v}
            for k, v in sorted(confronto.items())
        ]
        resumo["fora_da_entrada"] = sum(1 for i in itens if not i["na_carteira_entrada"])

    for reg in registros:
        meu = next((i for i in itens if i["ativo"] == reg["ativo"]), None)
        if meu:
            reg["acompanhamento"] = {
                "situacao": meu["situacao"],
                "check": meu["check"],
                "sem_acao_coep": meu["sem_acao_coep"],
                "na_base": meu["na_base"],
                "alertas": meu["alertas"],
            }

    return resumo
