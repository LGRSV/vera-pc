"""
A base nova de SS com parecer — `EQP_JOAO_19082026.xlsx`, aberturas até 19/08/2026.

Substitui a `RELIGA_REGULA_2025.xlsx` (a «planilha mãe»), que fechava em 11/07/2025 e por
isso não alcançava 2026. Mesma consulta, mesmo conteúdo, um ano a mais: **10.386 SS, 10.377
com DESCRIÇÃO**, de 01/08/2020 a 19/08/2026.

**A diferença estrutural**: a mãe trazia as colunas `Primeiro` e `hierarquia` com a cadeia
já montada; esta traz `SS_APOS_REPASSE`, que é o mesmo vínculo em outro formato — o elo
para a SS seguinte. A cadeia se remonta pelo elo, e a cabeça é a SS que ninguém aponta.

**Conferido antes de confiar**: das 497 cadeias do DCMD de 2024-2025 que a mãe montava,
a reconstrução aqui acha as 497, com a mesma SS de cabeça — *zero* divergência. As 164 a
mais no mesmo recorte são todas posteriores a 11/07/2025, o corte da mãe. É o mesmo dado,
com mais horizonte.

Rodar: python3 scripts/base_eqp.py   (mostra o que a base alcança e o que falta ler)
"""

import datetime as dt
import os
import sys
from collections import Counter

from openpyxl import load_workbook

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

BASE = os.path.join(RAIZ, "data", "raw", "EQP_JOAO_19082026.xlsx")
ABA = "Exportar Planilha"

PENDENCIA_FALHA = {"INDISPONIBILIDADE PARA OPERAÇÃO", "EM OPERAÇÃO COM ANOMALIA",
                   "ANOMALIA EM RELIGADOR", "ANOMALIA EM REGULADORES", "AVISO DE ANOMALIA"}


def _limpa(t):
    if t is None:
        return ""
    return str(t).replace("_x000D_", "").replace("\r", "").strip()


def _dia(v):
    if isinstance(v, dt.datetime):
        return v.date()
    return v if isinstance(v, dt.date) else None


def ler(caminho=BASE):
    """Devolve (reg, prox, comeco) no mesmo formato que `falha_dcmd_mae.ler`, para os
    scripts de recorte, lote e consolidação servirem sem alteração."""
    wb = load_workbook(caminho, read_only=True, data_only=True)
    ws = wb[ABA]
    it = ws.iter_rows(values_only=True)
    col = {n: i for i, n in enumerate(next(it))}
    reg, prox = {}, {}
    for r in it:
        ss = _limpa(r[col["SS_ORIGINAL"]])
        if not ss:
            continue
        reg[ss] = {
            "ss": ss,
            "posto": _limpa(r[col["POSTO_SGM"]]),
            "ativo": _limpa(r[col["EQUIPAMENTO"]]),
            "cod_ele": _limpa(r[col["COD_ELE"]]),
            "tipo": _limpa(r[col["TIPO_ATIVO"]]),
            "loc": _limpa(r[col["COD_LOC"]]),
            "alimentador": _limpa(r[col["COD_ALIMENTADOR"]]),
            "ocor": _dia(r[col["DTA_OCORRENCIA"]]),
            "abert": _dia(r[col["DTA_ABERTURA"]]),
            "concl": _dia(r[col["DTA_CONCLUSAO"]]),
            "status": _limpa(r[col["STATUS"]]),
            "pend": _limpa(r[col["PENDENCIA_DO_ATIVO"]]),
            "desc": _limpa(r[col["DESCRIÇÃO"]]),
        }
        nx = _limpa(r[col["SS_APOS_REPASSE"]])
        if nx:
            prox[ss] = nx
    wb.close()
    # a cabeça é quem ninguém aponta; SS que se apontam em ciclo ficariam de fora, então
    # o que sobrar sem cabeça entra pela própria SS (monta_cadeias já barra repetição)
    alvo = set(prox.values())
    comeco = [s for s in reg if s not in alvo]
    return reg, prox, comeco


def horizonte(reg):
    ab = [d["abert"] for d in reg.values() if d["abert"]]
    return min(ab), max(ab)


def a_ler(reg, prox, comeco, ja_lidas, anos=(2024, 2025, 2026)):
    """As cadeias que interessam e ainda não foram lidas.

    O recorte é o mesmo das duas rodadas anteriores: cadeia que tocou um posto do DCMD,
    OU cadeia cuja pendência é indisponibilidade/anomalia (candidata a falha de verdade).
    O resto — ajuste, obra, comissionamento, cadastro — fica fora por definição.
    """
    import falha_dcmd_mae as fm
    fora = []
    for cad in fm.monta_cadeias(reg, prox, comeco):
        d = reg[cad[0]]
        if not d["abert"] or d["abert"].year not in anos:
            continue
        if not (fm.do_dcmd(cad, reg) or d["pend"] in PENDENCIA_FALHA):
            continue
        if cad[0] in ja_lidas:
            continue
        fora.append(cad)
    return fora


if __name__ == "__main__":
    import falha_dcmd_mae as fm
    reg, prox, comeco = ler()
    ini, fim = horizonte(reg)
    cads = fm.monta_cadeias(reg, prox, comeco)
    print("%d SS · %d com parecer · aberturas de %s a %s"
          % (len(reg), sum(1 for d in reg.values() if d["desc"]), ini, fim))
    print("%d cadeias" % len(cads))
    for ano in (2024, 2025, 2026):
        no = [c for c in cads if reg[c[0]]["abert"] and reg[c[0]]["abert"].year == ano]
        dc = [c for c in no if fm.do_dcmd(c, reg)]
        cand = [c for c in no if not fm.do_dcmd(c, reg) and reg[c[0]]["pend"] in PENDENCIA_FALHA]
        print("  %d: %4d cadeias · %3d pelo DCMD · %4d de indisp./anomalia fora do DCMD"
              % (ano, len(no), len(dc), len(cand)))
