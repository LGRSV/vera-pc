"""
Quantos equipamentos foram DE FATO realizados (tratados) — a pergunta central do gestor.

Duas vias contam um ativo como tratado:
  AIC        a obra principal do ativo está encerrada no AIC (missão M4) — a prova forte;
  Cancelado  a demanda foi cancelada porque o COI confirmou o equipamento EM OPERAÇÃO
             (missão M5, leitura das 131 SS canceladas da carteira).

Regra do gestor (12/08/2026): um candidato só conta como tratado se NÃO existir outra SS
pendente do mesmo ativo aberta recentemente. "Recente" adotado como premissa: SS PENDENTE
ou SS REPASSADA aberta nos últimos 365 dias. Uma pendência antiga (fila histórica) não
derruba a via do AIC nem o cancelamento em operação — mas fica registrada na ficha.
"""

import datetime
import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_MISSAO = os.path.join(RAIZ, "data", "missao")

DATA_REF = datetime.date(2026, 8, 12)
JANELA_RECENTE_DIAS = 365

PREMISSAS = [
    "Tratado = obra principal encerrada no AIC (M4) OU cancelamento confirmado em operação "
    "pelo COI (M5), sem SS pendente recente do mesmo ativo.",
    f"SS pendente recente = SITUACAO_SS em (SS PENDENTE, SS REPASSADA) com abertura nos "
    f"últimos {JANELA_RECENTE_DIAS} dias contados de {DATA_REF.isoformat()}. Pendências mais "
    f"antigas não bloqueiam o veredito, mas ficam anotadas na ficha.",
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


def _data_br(texto):
    try:
        return datetime.datetime.strptime(texto.strip()[:10], "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return None


def _pendencias(ssos):
    """Por ativo: SS pendentes/repassadas, separadas em recentes e antigas."""
    corte = DATA_REF - datetime.timedelta(days=JANELA_RECENTE_DIAS)
    saida = {}
    for linha in ssos or []:
        if linha.get("SITUACAO_SS") not in ("SS PENDENTE", "SS REPASSADA"):
            continue
        abertura = _data_br(linha.get("DATA_ABERTURA_SS", ""))
        registro = {
            "numero_ss": linha.get("NUMERO_SS"),
            "equipe": linha.get("COD_EQUIPE"),
            "situacao": linha.get("SITUACAO_SS"),
            "abertura": abertura.isoformat() if abertura else "",
        }
        balde = saida.setdefault(linha.get("NUM_TRAFO"), {"recentes": [], "antigas": []})
        balde["recentes" if abertura and abertura >= corte else "antigas"].append(registro)
    return saida


def montar(registros):
    """Anota reg['realizada'] em cada ativo e devolve o resumo para o meta."""
    m5 = _ler("m5_canceladas.json")
    ssos = _ler("ssos_129.json")
    pend = _pendencias(ssos)

    resumo = {
        "premissas": PREMISSAS + list((m5 or {}).get("premissas", [])),
        "m5_disponivel": m5 is not None,
        "total": 0,
        "por_via": {"AIC": 0, "Cancelada em operação": 0, "Ambas": 0},
        "bloqueadas_por_pendencia_recente": 0,
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

        pendencia = pend.get(ativo, {"recentes": [], "antigas": []})
        recentes = pendencia["recentes"]

        veredito = bool(vias) and not recentes
        reg["realizada"] = {
            "veredito": veredito,
            "vias": vias,
            "evidencias": evidencias,
            "pendencias_recentes": recentes,
            "pendencias_antigas": len(pendencia["antigas"]),
            "confianca_m5": (m5_dado or {}).get("confianca"),
        }

        if veredito:
            resumo["total"] += 1
            chave = "Ambas" if len(vias) == 2 else vias[0]
            resumo["por_via"][chave] += 1
            resumo["lista"].append({
                "ativo": ativo,
                "localidade": reg["localidade"],
                "tipo": reg["tipo_nome"],
                "criticidade": reg["criticidade"],
                "vias": vias,
                "evidencia": evidencias[0] if evidencias else "",
            })
        elif vias:
            resumo["bloqueadas_por_pendencia_recente"] += 1
            resumo["bloqueadas"].append({
                "ativo": ativo,
                "localidade": reg["localidade"],
                "vias": vias,
                "pendencia": recentes[0] if recentes else None,
            })

    return resumo
