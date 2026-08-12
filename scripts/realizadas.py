"""
Quantos equipamentos foram DE FATO realizados (tratados) — a pergunta central do gestor.

Duas vias contam um ativo como tratado:
  AIC        a obra principal do ativo está encerrada no AIC (missão M4) — a prova forte;
  Cancelado  a demanda foi cancelada porque o COI confirmou o equipamento EM OPERAÇÃO
             (missão M5, leitura das 131 SS canceladas da carteira).

Regra do gestor (12/08/2026), refinada no mesmo dia: um candidato só conta como tratado
se o ativo NÃO tiver demanda aberta — pela lógica das cadeias (demandas.py): SS PENDENTE
de qualquer idade bloqueia; SS REPASSADA consumida por sucessora não bloqueia; rotina de
bateria/cadastro não bloqueia. E, por decisão do gestor no mesmo dia: ativo com SS
cancelada e NENHUMA demanda aberta CONTA COMO cancelada em operação — o cancelamento sem
reabertura indica equipamento operando. A origem fica marcada (confirmada pelo COI, via
leitura M5, ou inferida pela não-reincidência).
"""

import datetime
import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_MISSAO = os.path.join(RAIZ, "data", "missao")

DATA_REF = datetime.date(2026, 8, 12)

PREMISSAS = [
    "Realizada (confirmada) = obra principal encerrada no AIC (M4) OU cancelamento "
    "confirmado em operação pelo COI (M5), sem demanda aberta do mesmo ativo.",
    "Cancelada em operação tem duas origens, ambas contando como realizada por decisão "
    "do gestor (12/08): confirmada pelo COI no texto do cancelamento (leitura M5) ou "
    "inferida — SS cancelada (não-rotina) sem nenhuma demanda aberta no ativo. A origem "
    "fica marcada em cada ficha.",
    "Demanda aberta = cadeia com SS PENDENTE (qualquer idade) ou repasse pendurado, "
    "excluída rotina de bateria/cadastro. Repassada consumida por sucessora não bloqueia.",
    "Cancelamentos com resposta 'FICOU EM OPERAÇÃO? NÃO' no formulário do DMSL não contam "
    "como equipamento em operação — a leitura foi feita SS a SS pela missão M5.",
    "Conclusão física sem encerramento contábil (11 ativos no M4) NÃO conta como tratado "
    "até o encerramento aparecer no AIC — régua definida pelo gestor.",
]


def _ler(nome):
    caminho = os.path.join(DIR_MISSAO, nome)
    if not os.path.exists(caminho):
        return None
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def montar(registros):
    """Anota reg['realizada'] em cada ativo e devolve o resumo para o meta.

    Depende de reg['demandas'] — o build roda demandas.py antes deste módulo.
    """
    m5 = _ler("m5_canceladas.json")

    resumo = {
        "premissas": PREMISSAS + list((m5 or {}).get("premissas", [])),
        "m5_disponivel": m5 is not None,
        "total": 0,
        "por_via": {"AIC": 0, "Cancelada em operação": 0, "Ambas": 0},
        "por_origem_cancelamento": {"COI confirmou": 0, "Sem reincidência": 0},
        "bloqueadas_por_demanda_aberta": 0,
        "lista": [],
        "bloqueadas": [],
    }

    candidatos_m5 = {
        ativo: dados
        for ativo, dados in ((m5 or {}).get("ativos") or {}).items()
        if dados.get("candidato_em_operacao")
    }

    for reg in registros:
        ativo = reg["ativo"]
        vias = []
        evidencias = []

        aic = reg.get("aic") or {}
        if aic.get("veredito") == "confirmado_aic":
            vias.append("AIC")
            evidencias.append(
                f"obra {aic.get('obra_principal') or '—'} encerrada no AIC"
                + (f" em {aic['data_encerramento']}" if aic.get("data_encerramento") else "")
            )

        m5_dado = candidatos_m5.get(ativo)
        if m5_dado:
            vias.append("Cancelada em operação")
            if m5_dado.get("evidencia"):
                evidencias.append(m5_dado["evidencia"])

        demandas = reg.get("demandas") or []
        abertas = [d for d in demandas if d.get("situacao") == "aberta" and not d.get("rotina")]
        canceladas = [d for d in demandas if d.get("situacao") == "cancelada" and not d.get("rotina")]

        origem_cancelamento = None
        if m5_dado:
            origem_cancelamento = "COI confirmou"
        elif canceladas and not abertas:
            # Decisão do gestor: cancelada sem reincidência = cancelada em operação.
            vias.append("Cancelada em operação")
            evidencias.append(
                f"{len(canceladas)} demanda(s) cancelada(s) e nenhuma demanda aberta no "
                f"ativo — sem reincidência, equipamento dado como operando"
            )
            origem_cancelamento = "Sem reincidência"

        veredito = bool(vias) and not abertas

        bloqueio = None
        if abertas:
            aberta = abertas[0]
            pendente = next((x for x in aberta.get("ss", [])
                             if x.get("situacao") in ("SS PENDENTE", "SS REPASSADA")), None)
            bloqueio = {
                "numero_ss": (pendente or {}).get("numero"),
                "equipe": (pendente or {}).get("equipe"),
                "situacao": (pendente or {}).get("situacao"),
                "abertura": (pendente or {}).get("abertura", ""),
            }

        reg["realizada"] = {
            "veredito": veredito,
            "vias": vias,
            "origem_cancelamento": origem_cancelamento,
            "evidencias": evidencias,
            "demanda_bloqueando": bloqueio,
            "confianca_m5": (m5_dado or {}).get("confianca"),
        }

        if veredito:
            resumo["total"] += 1
            chave = "Ambas" if len(set(vias)) == 2 else vias[0]
            resumo["por_via"][chave] += 1
            if origem_cancelamento:
                resumo["por_origem_cancelamento"][origem_cancelamento] += 1
            resumo["lista"].append({
                "ativo": ativo,
                "localidade": reg["localidade"],
                "tipo": reg["tipo_nome"],
                "criticidade": reg["criticidade"],
                "vias": sorted(set(vias)),
                "origem_cancelamento": origem_cancelamento,
                "evidencia": evidencias[0] if evidencias else "",
            })
        elif vias:
            resumo["bloqueadas_por_demanda_aberta"] += 1
            resumo["bloqueadas"].append({
                "ativo": ativo,
                "localidade": reg["localidade"],
                "vias": vias,
                "pendencia": bloqueio,
            })

    return resumo
