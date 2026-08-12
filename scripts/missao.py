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
