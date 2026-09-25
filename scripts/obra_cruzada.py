"""
Obra × ativo pelos caminhos inversos — pedido do gestor (12/08, à noite).

Até aqui o vínculo foi ativo→obra (EMD, SS do ativo, descrição da obra). Este módulo
anda ao contrário: parte de cada NÚMERO DE OBRA que aparece na base de SS/OS e pergunta
em quais ativos 58/79 ele aparece, cruzando com o EMD, com a obra principal do M4 e com
o índice completo do AIC (124.084 obras).

Achados que procura:
  obra_em_dois_ativos      o mesmo número de obra registrado em SS de ativos diferentes
  obra_ss_vs_emd           a obra está na SS do ativo A, mas o EMD a atribui ao ativo B
  emd_vs_descricao_aic     o EMD atribui ao ativo A e a descrição da obra no AIC cita
                           outro ativo 58/79 (generalização do caso 0712600318)
  obra_fantasma            número de obra declarado em SS/EMD que não existe no AIC
  m4_vs_ssos               a obra principal do M4 para o ativo X aparece na base de
                           SS/OS sob o ativo Y

Normalização: a base de SS/OS grava NUM_OBRA sem o zero à esquerda; o AIC e o EMD gravam
com. Tudo é comparado com zero à esquerda reposto (10 dígitos).
"""

import csv
import json
import os
import re
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_MISSAO = os.path.join(RAIZ, "data", "missao")
CSV_EMD = os.path.join(RAIZ, "data", "raw", "obras_eq_especial.csv")

PREMISSAS = [
    "Caminho inverso: parte-se do número de obra (NUM_OBRA da base SS/OS, OBRA do EMD, "
    "obra principal do M4) e pergunta-se a quais ativos 58/79 ele está preso em cada fonte.",
    "NUM_OBRA da base SS/OS vem sem o zero à esquerda; comparações repõem o zero (10 dígitos).",
    "Obra fantasma = número declarado em SS ou EMD que não existe entre as 124.084 obras "
    "do extrato do AIC de 07/08/2026 — ou o número foi digitado errado, ou a obra nunca "
    "foi criada.",
    "Citação de ativo na descrição da obra usa o texto do AIC restrito às 2.386 obras "
    "ligadas a RL/RT; ativo citado precisa ter 10 dígitos com prefixo 79/58.",
]


def _norm_obra(texto):
    dig = re.sub(r"\D", "", texto or "")
    if not dig or len(dig) < 6:
        return ""
    return dig.zfill(10)


def _ler(nome):
    caminho = os.path.join(DIR_MISSAO, nome)
    if not os.path.exists(caminho):
        return None
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def montar(registros):
    ssos = _ler("ssos_min.json") or []
    aic_index = _ler("aic_index.json") or {}
    m4 = _ler("m4_aic129.json") or {}

    carteira = {r["ativo"] for r in registros}
    achados = []

    # obra -> ativos na base de SS/OS
    obra_ss = defaultdict(set)
    for linha in ssos:
        obra = _norm_obra(linha.get("NUM_OBRA"))
        if obra:
            obra_ss[obra].add(linha.get("NUM_TRAFO"))

    # obra -> ativo no EMD
    obra_emd = {}
    with open(CSV_EMD, encoding="utf-8") as fh:
        for linha in csv.DictReader(fh, delimiter=";"):
            obra = _norm_obra(linha.get("OBRA"))
            if obra:
                obra_emd.setdefault(obra, set()).add((linha.get("Ativo") or "").strip())

    # obra -> ativos citados na descrição (AIC, universo RL/RT)
    obra_desc = defaultdict(set)
    aic_sel = None
    caminho_sel = os.path.join(
        os.path.dirname(DIR_MISSAO), "..",
        "..", "", "")
    # As descrições vivem no recorte usado pelas missões; quando ausente, o achado
    # emd_vs_descricao_aic simplesmente não é produzido.
    try:
        with open(os.path.join(RAIZ, "data", "missao", "aic_rlrt.json"), encoding="utf-8") as fh:
            aic_sel = json.load(fh)
    except FileNotFoundError:
        aic_sel = None
    if aic_sel:
        for obra_reg in aic_sel:
            obra = _norm_obra(obra_reg.get("NUM_OBRA"))
            texto = f"{obra_reg.get('DESCRICAO', '')} {obra_reg.get('DESCRICAO_OBRA', '')}"
            for ativo in re.findall(r"\b(79\d{8}|58\d{8})\b", texto):
                obra_desc[obra].add(ativo)

    def registrar(tipo, obra, detalhe, ativos):
        achados.append({
            "tipo": tipo,
            "obra": obra,
            "detalhe": detalhe,
            "ativos": sorted(a for a in ativos if a),
            "na_carteira": sorted(a for a in ativos if a in carteira),
            "aic": aic_index.get(obra) or aic_index.get(obra.lstrip("0")) or None,
        })

    # 1. mesma obra em SS de ativos diferentes
    for obra, ativos in sorted(obra_ss.items()):
        if len(ativos) > 1:
            registrar(
                "obra_em_dois_ativos", obra,
                f"O número de obra {obra} aparece em SS de {len(ativos)} ativos "
                f"diferentes na base de SS/OS: {', '.join(sorted(ativos))}.",
                ativos,
            )

    # 2. SS diz um ativo, EMD diz outro
    for obra, ativos_emd in sorted(obra_emd.items()):
        ativos_na_ss = obra_ss.get(obra, set())
        divergentes = ativos_na_ss - ativos_emd
        if ativos_na_ss and divergentes:
            registrar(
                "obra_ss_vs_emd", obra,
                f"No EMD a obra {obra} pertence a {', '.join(sorted(ativos_emd))}; na base "
                f"de SS/OS ela aparece na SS de {', '.join(sorted(ativos_na_ss))}.",
                ativos_emd | ativos_na_ss,
            )

    # 3. EMD diz um ativo, descrição da obra no AIC cita outro
    for obra, ativos_emd in sorted(obra_emd.items()):
        citados = obra_desc.get(obra, set())
        outros = citados - ativos_emd
        if outros:
            registrar(
                "emd_vs_descricao_aic", obra,
                f"O EMD atribui a obra {obra} a {', '.join(sorted(ativos_emd))}, mas a "
                f"descrição da obra no AIC cita {', '.join(sorted(outros))}.",
                ativos_emd | citados,
            )

    # 4. obra declarada que não existe no AIC
    def existe(obra):
        return obra in aic_index or obra.lstrip("0") in aic_index

    for obra, ativos in sorted(obra_ss.items()):
        if not existe(obra):
            registrar(
                "obra_fantasma", obra,
                f"A obra {obra}, declarada em SS de {', '.join(sorted(ativos))}, não existe "
                f"entre as 124.084 obras do extrato do AIC.",
                ativos,
            )
    for obra, ativos in sorted(obra_emd.items()):
        if not existe(obra) and obra not in obra_ss:
            registrar(
                "obra_fantasma", obra,
                f"A obra {obra}, registrada no EMD para {', '.join(sorted(ativos))}, não "
                f"existe entre as 124.084 obras do extrato do AIC.",
                ativos,
            )

    # 5. obra principal do M4 aparecendo em SS de outro ativo
    for ativo, dados in (m4.get("ativos") or {}).items():
        obra = _norm_obra(dados.get("obra_principal") or "")
        if not obra:
            continue
        na_ss = obra_ss.get(obra, set())
        outros = na_ss - {ativo}
        if outros:
            registrar(
                "m4_vs_ssos", obra,
                f"A obra principal do ativo {ativo} (vínculo {dados.get('via')}) também "
                f"aparece na base de SS/OS sob {', '.join(sorted(outros))}.",
                {ativo} | na_ss,
            )

    resumo = {
        "premissas": PREMISSAS,
        "obras_na_base_ss": len(obra_ss),
        "obras_no_emd": len(obra_emd),
        "total_achados": len(achados),
        "por_tipo": {},
        "achados": achados,
    }
    for a in achados:
        resumo["por_tipo"][a["tipo"]] = resumo["por_tipo"].get(a["tipo"], 0) + 1
    return resumo
