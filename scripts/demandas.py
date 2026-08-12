"""
Demandas encadeadas — a lógica que junta as "SS gêmeas" numa demanda só.

O problema (do gestor, 12/08): o mesmo defeito gera SS em série conforme o posto muda —
a TELE repassa ao COEP, o COEP repassa ao COCM quando o material chega — e cada repasse
vira uma SS nova no SGM. Contar SS infla; o que interessa é a DEMANDA e o posto atual.

A regra de encadeamento, verificada na própria base:
  1. Repasse explícito: o SGM cria a SS de destino com o MESMO carimbo de data/hora da
     SS de origem (194 pares e 2 trios na base de RL/RT). Mesmo ativo + mesma data/hora
     de abertura = mesma demanda.
  2. Continuidade de posto: SS do mesmo ativo aberta em até 7 dias depois de uma SS
     REPASSADA é a continuação dela (o repasse que demorou a virar SS).
  3. Janela de ciclo: aberturas do mesmo ativo a mais de 180 dias de distância sem elo
     dos tipos 1-2 são demandas (ciclos) diferentes — defeito de 2024 não se soma ao
     de 2026.

Departamento de cada equipe — REGRA DO GESTOR (12/08):
  DCMD  = tudo que tem RD no código (ETO-RD-*, DOLP-RD-*, DG-RD-*, ENC-*) — a execução
  DMSL  = tudo que tem TELE, mais ETO-DMSL-*, DMSLETO e equipes de SE (ETO-SE-*)
  DEOP  = ETO-DEOP, COI e tudo que tem PROT (a Proteção faz os ajustes pós-substituição)
  COEP  = ETO-COEP (engenharia; compra o material)
  Fora  = CADTOC/CADCH (cadastro), SCADA/AUTOM (supervisório), demais administrativas
"""

import datetime
import json
import os
import re
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ_MIN = os.path.join(RAIZ, "data", "missao", "ssos_min.json")

DATA_REF = datetime.date(2026, 8, 12)

PREMISSAS = [
    "Demanda = cadeia de SS do mesmo ativo ligadas por repasse (mesmo carimbo de "
    "data/hora de abertura — padrão do SGM verificado em 194 pares) ou por SS aberta em "
    "até 7 dias após uma SS REPASSADA; aberturas a mais de 180 dias sem elo são ciclos "
    "(demandas) distintos.",
    "Departamento por equipe — regra do gestor (12/08): RD/ENC/DOLP = DCMD; TELE, "
    "DMSL e SE = DMSL; DEOP, COI e PROT = DEOP; COEP = COEP; cadastro e SCADA fora do fluxo.",
    "Troca preventiva de bateria, atualização cadastral, uso mútuo e comissionamento de "
    "obra nova não são ação do DCMD — ficam fora do recorte do gestor (regra de 12/08: "
    "se foi só bateria pelo DMSL, o ativo nem passou pelo posto).",
    "Posto atual da demanda = departamento da SS PENDENTE mais recente. SS REPASSADA é "
    "elo: consumida quando existe SS posterior na cadeia; quando é a última, a demanda "
    "parou no repasse (repasse pendurado — a quebra clássica) e conta como aberta no "
    "posto que repassou.",
    "Passou pelo COEP = alguma SS da demanda em equipe ETO-COEP.",
]

ROTINA = re.compile(
    r"PREVNP|SUBSTITUI[ÇC][ÃA]O DE BATERIA|ATUALIZA[ÇC][ÃA]O CADASTRAL|USO M[ÚU]TUO|CADASTR",
    re.I,
)


def departamento(equipe):
    e = (equipe or "").upper()
    if "CADTOC" in e or "CADCH" in e or "SCADA" in e or "AUTOM" in e:
        return "Fora do fluxo"
    if "TELE" in e or "DMSL" in e or re.search(r"\bETO-SE\b|ETO-SE-", e):
        return "DMSL"
    if "COEP" in e:
        return "COEP"
    if "DEOP" in e or e == "COI" or "PROT" in e:
        return "DEOP"
    if "-RD" in e or e.startswith("RD") or "ENC" in e or "DOLP" in e or "-LV" in e or "-OP" in e:
        return "DCMD"
    return "Outros"


def _dt(texto):
    try:
        return datetime.datetime.strptime(texto.strip(), "%d/%m/%Y %H:%M:%S")
    except (ValueError, AttributeError):
        try:
            return datetime.datetime.strptime(texto.strip()[:10], "%d/%m/%Y")
        except (ValueError, AttributeError):
            return None


def eh_rotina(linha):
    campos = " ".join([linha.get("ESQUEMA") or "", linha.get("TIPOSS") or ""])
    return bool(ROTINA.search(campos))


def encadear(linhas):
    """Agrupa as SS de UM ativo em demandas, pelas regras 1-3."""
    ordenadas = sorted(linhas, key=lambda l: _dt(l.get("DATA_ABERTURA_SS", "")) or datetime.datetime.min)
    demandas = []
    for linha in ordenadas:
        aberta_em = _dt(linha.get("DATA_ABERTURA_SS", ""))
        alvo = None
        for dem in demandas:
            if aberta_em is None or dem["fim"] is None:
                continue
            mesmo_carimbo = any(aberta_em == e for e in dem["carimbos"])
            pos_repasse = (
                dem["tem_repassada"]
                and datetime.timedelta(0) <= aberta_em - dem["fim"] <= datetime.timedelta(days=7)
            )
            mesmo_ciclo = aberta_em - dem["fim"] <= datetime.timedelta(days=180)
            if mesmo_carimbo or pos_repasse or (mesmo_ciclo and dem["aberta"]):
                alvo = dem
                break
        if alvo is None:
            alvo = {"ss": [], "carimbos": [], "fim": None, "tem_repassada": False, "aberta": False}
            demandas.append(alvo)
        alvo["ss"].append(linha)
        if aberta_em:
            alvo["carimbos"].append(aberta_em)
            alvo["fim"] = max(alvo["fim"] or aberta_em, aberta_em)
        alvo["tem_repassada"] = alvo["tem_repassada"] or linha.get("SITUACAO_SS") == "SS REPASSADA"
        alvo["aberta"] = alvo["aberta"] or linha.get("SITUACAO_SS") in ("SS PENDENTE", "SS REPASSADA")
    return demandas


def resumir_demanda(dem):
    ss = dem["ss"]
    postos = []
    for linha in ss:
        d = departamento(linha.get("COD_EQUIPE"))
        if not postos or postos[-1] != d:
            postos.append(d)
    atendidas = [l for l in ss if l.get("SITUACAO_SS") == "SS ATENDIDA"]
    pendentes = [l for l in ss if l.get("SITUACAO_SS") == "SS PENDENTE"]
    # REPASSADA é elo: se há SS posterior na cadeia, o repasse foi consumido; se a
    # repassada é a ÚLTIMA da cadeia, a demanda parou no repasse (quebra clássica).
    ultima = ss[-1]
    repasse_pendurado = ultima.get("SITUACAO_SS") == "SS REPASSADA"
    if pendentes:
        posto_atual = departamento(pendentes[-1].get("COD_EQUIPE"))
        situacao = "aberta"
    elif repasse_pendurado:
        posto_atual = departamento(ultima.get("COD_EQUIPE"))
        situacao = "aberta"
    elif atendidas:
        posto_atual = None
        situacao = "concluída"
    else:
        posto_atual = None
        situacao = "cancelada"
    termino = max(
        (_dt(l.get("DATA_TERMINO_SS", "")) for l in atendidas if _dt(l.get("DATA_TERMINO_SS", ""))),
        default=None,
    )
    abertura = min((c for c in dem["carimbos"]), default=None)
    return {
        "ss": [
            {
                "numero": l.get("NUMERO_SS"),
                "equipe": l.get("COD_EQUIPE"),
                "departamento": departamento(l.get("COD_EQUIPE")),
                "situacao": l.get("SITUACAO_SS"),
                "abertura": (_dt(l.get("DATA_ABERTURA_SS", "")) or datetime.datetime.min).strftime("%Y-%m-%d"),
            }
            for l in ss
        ],
        "postos": postos,
        "posto_atual": posto_atual,
        "situacao": situacao,
        "rotina": all(eh_rotina(l) for l in ss),
        "passou_coep": any("COEP" in (l.get("COD_EQUIPE") or "").upper() for l in ss),
        "abertura": abertura.strftime("%Y-%m-%d") if abertura else "",
        "termino": termino.strftime("%Y-%m-%d") if termino else "",
        "repasse_pendurado": repasse_pendurado and not pendentes,
    }


def montar(registros):
    """Encadeia a base inteira de RL/RT e anota as demandas dos 129."""
    with open(ARQ_MIN, encoding="utf-8") as fh:
        base = json.load(fh)

    por_ativo = {}
    for linha in base:
        por_ativo.setdefault(linha.get("NUM_TRAFO"), []).append(linha)

    demandas = []
    for ativo, linhas in por_ativo.items():
        for dem in encadear(linhas):
            resumo = resumir_demanda(dem)
            resumo["ativo"] = ativo
            resumo["tipo"] = "Religador" if ativo.startswith("79") else "Regulador de Tensão"
            demandas.append(resumo)

    uteis = [d for d in demandas if not d["rotina"]]

    # Recontagem pela regra do gestor: concluída pelo DCMD = demanda não-rotina cujo
    # término em 2026 veio de SS ATENDIDA em equipe DCMD (RD/ENC/DOLP).
    def concluida_dcmd_2026(d):
        if d["situacao"] != "concluída" or not d["termino"].startswith("2026"):
            return False
        return any(
            s["departamento"] == "DCMD" and s["situacao"] == "SS ATENDIDA" for s in d["ss"]
        )

    concluidas_dcmd = [d for d in uteis if concluida_dcmd_2026(d)]
    abertas = [d for d in uteis if d["situacao"] == "aberta"]

    resumo = {
        "premissas": PREMISSAS,
        "total_ss": len(base),
        "total_demandas": len(demandas),
        "demandas_nao_rotina": len(uteis),
        "ss_por_demanda_media": round(len(base) / len(demandas), 2),
        "concluidas_dcmd_2026": {
            "total": len(concluidas_dcmd),
            "por_tipo": dict(Counter(d["tipo"] for d in concluidas_dcmd)),
            "passaram_pelo_coep": sum(1 for d in concluidas_dcmd if d["passou_coep"]),
            "por_mes": dict(sorted(Counter(d["termino"][:7] for d in concluidas_dcmd).items())),
        },
        "abertas": {
            "total": len(abertas),
            "por_posto_atual": dict(Counter(d["posto_atual"] for d in abertas).most_common()),
            "por_tipo": dict(Counter(d["tipo"] for d in abertas)),
            "com_coep_no_caminho": sum(1 for d in abertas if d["passou_coep"]),
            "repasses_pendurados": sum(1 for d in abertas if d.get("repasse_pendurado")),
        },
        "caminhos_mais_comuns": [
            {"caminho": " → ".join(c), "demandas": n}
            for c, n in Counter(tuple(d["postos"]) for d in uteis).most_common(12)
        ],
    }

    ativos_carteira = {r["ativo"] for r in registros}
    for reg in registros:
        minhas = [d for d in demandas if d["ativo"] == reg["ativo"]]
        minhas.sort(key=lambda d: d["abertura"], reverse=True)
        reg["demandas"] = minhas

    resumo["abertas"]["na_carteira_129"] = len(
        {d["ativo"] for d in abertas if d["ativo"] in ativos_carteira}
    )
    return resumo
