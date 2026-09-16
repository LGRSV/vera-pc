"""
Quantos equipamentos já foram concluídos — e com que grau de certeza.

A regra combinada é do próprio COEP: só há certeza depois que a obra aparece no AIC como
encerrada. Enquanto o extrato do AIC não entra em data/raw/aic_obras.csv, nenhum
equipamento é contado como confirmado; o que existe são indícios, com força diferente
conforme quantas fontes concordam e se alguma delas contradiz as outras.

Fontes de indício, por ordem de peso:
  SGM       a SS tem data de término registrada no sistema
  EMD       a linha de requisição marca a substituição como concluída
  Check     a planilha de criticidade marca o Check de conclusão como Ok
  SS        a planilha de criticidade traz CONCLUÍDA no lugar do número da SS
  COEP      o Parecer COEP diz concluído ou substituído

Formato esperado de data/raw/aic_obras.csv (separador ';'):
  ativo;obra;situacao;data_encerramento
Qualquer situação que contenha "encerrad" conta como encerramento.
"""

import csv
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_AIC = os.path.join(RAIZ, "data", "raw", "aic_obras.csv")

PESO = {"SGM": 4, "EMD": 3, "Check": 2, "SS": 2, "COEP": 1}


def ler_aic():
    """Extrato do AIC, se já tiver sido enviado. Devolve {ativo: {...}}."""
    if not os.path.exists(CSV_AIC):
        return {}, False

    encerradas = {}
    with open(CSV_AIC, encoding="utf-8") as fh:
        for linha in csv.DictReader(fh, delimiter=";"):
            registro = {k.strip().lower(): (v or "").strip() for k, v in linha.items() if k}
            ativo = registro.get("ativo", "")
            if not ativo:
                continue
            if "encerrad" in registro.get("situacao", "").lower():
                encerradas[ativo] = {
                    "obra": registro.get("obra", ""),
                    "situacao": registro.get("situacao", ""),
                    "data_encerramento": registro.get("data_encerramento", ""),
                }
    return encerradas, True


def indicios_de(reg):
    """Sinais de conclusão presentes no registro, com a fonte de cada um."""
    achados = []

    if (reg.get("ss_sgm") or {}).get("data_termino"):
        achados.append(("SGM", f"SS encerrada no sistema em {reg['ss_sgm']['data_termino']}"))

    emd = reg.get("emd") or {}
    if emd.get("Status da Substituição", "").strip().lower() == "concluída":
        quando = emd.get("Data da Substituição", "")
        achados.append(("EMD", f"substituição concluída{f' em {quando}' if quando else ''}"))

    if reg["check"] == "Ok":
        achados.append(("Check", "Check de conclusão marcado como Ok"))

    if "CONCLU" in reg["ss"].upper():
        achados.append(("SS", "planilha de criticidade traz CONCLUÍDA no lugar da SS"))

    if re.search(r"conclu[íi]d|substitu[íi]do", reg["parecer_coep"], re.I):
        achados.append(("COEP", f"Parecer COEP: «{reg['parecer_coep']}»"))

    return achados


def contradicoes_de(reg, indicios):
    """O que, no mesmo registro, desmente os indícios de conclusão."""
    fontes = {f for f, _ in indicios}
    contra = []

    if not fontes:
        return contra

    emd = reg.get("emd") or {}
    situacao_ss = (reg.get("ss_sgm") or {}).get("situacao", "")

    if "SS" in fontes and reg["parecer_coep"] and "conclu" not in reg["parecer_coep"].lower():
        contra.append(f"SS marcada CONCLUÍDA, mas o Parecer COEP é «{reg['parecer_coep']}»")

    if "SS" in fontes and reg["check"] not in ("Ok", "Desmobilizado", ""):
        contra.append(f"SS marcada CONCLUÍDA, mas o Check é «{reg['check']}»")

    if "EMD" in fontes and "CONCLU" not in reg["ss"].upper():
        contra.append(f"EMD dá a substituição como concluída, mas a SS {reg['ss']} segue aberta")

    if "EMD" in fontes and emd.get("Equipamento Entregue ?", "").strip().lower() == "não":
        contra.append("EMD marca substituição concluída com equipamento não entregue")

    if fontes and situacao_ss and "pendente" in situacao_ss.lower():
        contra.append(f"a SS continua «{situacao_ss}» no sistema")

    if fontes and (reg.get("ss_sgm") or {}).get("sla_estourado"):
        contra.append("a SS está além do prazo-limite do sistema, sem encerramento")

    return contra


def classificar(reg, aic, aic_disponivel):
    """Devolve o veredito de conclusão de um equipamento."""
    indicios = indicios_de(reg)
    contra = contradicoes_de(reg, indicios)
    pontos = sum(PESO[f] for f, _ in indicios)

    if reg["ativo"] in aic:
        situacao = "Confirmada no AIC"
    elif not indicios:
        situacao = "Sem indício de conclusão"
    elif contra:
        situacao = "Indício contestado"
    elif pontos >= 4:
        situacao = "Indício forte"
    else:
        situacao = "Indício isolado"

    return {
        "situacao": situacao,
        "pontos": pontos,
        "fontes": [f for f, _ in indicios],
        "indicios": [{"fonte": f, "texto": t} for f, t in indicios],
        "contradicoes": contra,
        "aic": aic.get(reg["ativo"]),
        "aic_disponivel": aic_disponivel,
    }


ORDEM = [
    "Confirmada no AIC",
    "Indício forte",
    "Indício contestado",
    "Indício isolado",
    "Sem indício de conclusão",
]


def montar(registros):
    """Anota cada registro e devolve o resumo da carteira."""
    aic, aic_disponivel = ler_aic()

    for reg in registros:
        reg["conclusao"] = classificar(reg, aic, aic_disponivel)

    from collections import Counter

    contagem = Counter(r["conclusao"]["situacao"] for r in registros)
    confirmadas = contagem.get("Confirmada no AIC", 0)

    fontes = Counter()
    for reg in registros:
        fontes.update(reg["conclusao"]["fontes"])

    return {
        "aic_disponivel": aic_disponivel,
        "total_ativos_aic": len(aic),
        "confirmadas": confirmadas,
        "com_algum_indicio": sum(
            1 for r in registros if r["conclusao"]["fontes"] and not r["conclusao"]["aic"]
        ),
        "contestadas": contagem.get("Indício contestado", 0),
        "sem_indicio": contagem.get("Sem indício de conclusão", 0),
        "por_situacao": [
            {"rotulo": s, "total": contagem.get(s, 0)} for s in ORDEM if contagem.get(s, 0)
        ],
        "por_fonte": [{"rotulo": f, "total": n} for f, n in fontes.most_common()],
    }
