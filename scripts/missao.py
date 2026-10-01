"""
Missão DCMD — integra ao site as quatro análises produzidas sobre a base SS/OS
completa e o extrato do AIC (07/08/2026):

  m1_dcmd.json    quantas SS de RL/RT o fluxo DCMD concluiu em 2026 e quantas vão entrar
  m2_sigco.json   auditoria de SIGCO das obras (8481 = regulador, 8495 = religador)
  m3_fluxo.json   reconstrução do fluxo COI→DEOP→DMSL→COEP→COCM dos 129 da carteira
  m4_aic129.json  vínculo obra×ativo no AIC e veredito de conclusão dos 129

Os arquivos vivem em data/missao/. Cada análise carrega as próprias premissas,
que o site exibe junto dos números.
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(RAIZ, "data", "missao")


def _ler(nome):
    caminho = os.path.join(DIR, nome)
    if not os.path.exists(caminho):
        return None
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def carregar():
    """Devolve o pacote da missão para o meta.json (None nos módulos ausentes)."""
    return {
        "dcmd": _ler("m1_dcmd.json"),
        "sigco": _ler("m2_sigco.json"),
        "fluxo": _ler("m3_fluxo.json"),
        "aic129": _ler("m4_aic129.json"),
    }


def _sem_listas(recorte):
    """Mantém os agregados de um recorte do M1 e troca as listas por contagem."""
    saida = {}
    for nome, blocox in (recorte or {}).items():
        if not isinstance(blocox, dict):
            saida[nome] = blocox
            continue
        saida[nome] = {
            k: (len(v) if isinstance(v, list) else v) if k == "lista" else v
            for k, v in blocox.items()
            if k != "lista" or True
        }
        if isinstance(blocox.get("lista"), list):
            saida[nome]["lista"] = len(blocox["lista"])
    return saida


def enxugar(pacote):
    """Versão leve para o meta.json — o detalhe por ativo já vive em equipamentos.json."""
    leve = {}

    d = pacote.get("dcmd")
    if d:
        leve["dcmd"] = {
            "premissas": d.get("premissas", []),
            "recorte_estrito": _sem_listas(d.get("recorte_estrito")),
            "recorte_amplo": _sem_listas(d.get("recorte_amplo")),
        }

    s = pacote.get("sigco")
    if s:
        erradas = [
            {k: o.get(k) for k in ("num_obra", "tipo", "sigco", "sigco_certo",
                                   "status", "descricao_curta", "ativo_ligado",
                                   "valor_orcado", "dth_encerramento")}
            for o in s.get("obras", [])
            if o.get("veredito") == "sigco_errado"
        ]
        leve["sigco"] = {
            "premissas": s.get("premissas", []),
            "resumo": s.get("resumo", {}),
            "obras": [{**o, "veredito": "sigco_errado"} for o in erradas],
        }

    f = pacote.get("fluxo")
    if f:
        leve["fluxo"] = {
            "premissas": f.get("premissas", []),
            "agregado": f.get("agregado", {}),
        }

    a = pacote.get("aic129")
    if a:
        leve["aic129"] = {
            "premissas": a.get("premissas", []),
            "resumo": a.get("resumo", {}),
        }

    m8 = _ler("m8_coep2025.json")
    if m8:
        leve["coep2025"] = {
            "premissas": m8.get("premissas", []),
            "resumo": m8.get("resumo", {}),
            "ativos": [
                {"ativo": ativo, **{k: v for k, v in dados.items()
                                    if k in ("veredito", "posto_hoje", "historia",
                                             "dias_parado", "reincidencia",
                                             "conflito_com_site", "na_carteira")}}
                for ativo, dados in sorted((m8.get("ativos") or {}).items())
            ],
        }

    return leve


def anotar_registros(registros, pacote):
    """Leva o fluxo (M3) e o veredito do AIC (M4) para dentro de cada ativo."""
    fluxo = ((pacote.get("fluxo") or {}).get("ativos")) or {}
    aic = ((pacote.get("aic129") or {}).get("ativos")) or {}
    sigco_129 = {
        item.get("ativo"): item
        for item in ((pacote.get("sigco") or {}).get("carteira_129")) or []
        if item.get("ativo")
    }

    for reg in registros:
        ativo = reg["ativo"]
        if ativo in fluxo:
            reg["fluxo"] = fluxo[ativo]
        if ativo in aic:
            reg["aic"] = aic[ativo]
        if ativo in sigco_129:
            reg["sigco"] = sigco_129[ativo]
