"""
As datas certas de uma SS: quando ela CHEGOU ao posto e quando SAIU.

O export do SGM (`RELIGA_REGULA_*`, `EQP_JOAO_*`) SOBRESCREVE a DTA_ABERTURA — e a DTA_REPASSE, que é
cópia dela — no instante em que a SS é repassada. Para SS com status REPASSADA, a «abertura» é a
SAÍDA do posto, não a chegada. Provado comparando exports da mesma SS:
  - as 63 SS pendentes no export de 11/07/2025 que foram repassadas depois aparecem no de 23/09/2026
    com a abertura igual ao instante do repasse (63 de 63);
  - as 21 repassadas entre 19/08 e 23/09/2026, idem (ETO-COEP 174/2026: abertura 11/08 no export de
    19/08, 04/09 08:40 no de 23/09 — o instante em que foi para o ETO-RD-PO);
  - na base de 23/09, a SS repassada cuja seguinte não andou mais tem a mesma abertura que ela, no
    segundo (ATENDIDA 1.248 de 1.262, PENDENTE 85 de 86).
A DTA_OCORRENCIA é copiada para a cadeia inteira (2.846 de 2.847 iguais à da anterior); na cabeça não
repassada ela é igual à abertura.

Então:
  chegada  = a abertura da SS anterior (o instante em que ela repassou); na cabeça, a DTA_OCORRENCIA
             se a cabeça foi repassada, senão a DTA_ABERTURA;
  saída    = REPASSADA: a própria DTA_ABERTURA (o repasse, exato); ATENDIDA/CANCELADA: a conclusão;
             PENDENTE: segue no posto.

O que isso desmente: «a data do repasse é a abertura da SS seguinte» (só quando a seguinte não andou
mais), «o tempo no posto é a diferença entre as duas aberturas» (dá o tempo no posto SEGUINTE), «SS com
número de 2025 aberta em 2026 foi recriada» (foi repassada em 2026) e a leitura do número da SS como
data de abertura falsa.
"""

import re


def _txt(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""


def status(k, por):
    return _txt(por[k][0]["STATUS"]).upper()


def chegada(k, por, antes):
    ants = [a for a in antes.get(k, ()) if a in por]
    if ants:
        return min(por[a][0]["DTA_ABERTURA"] for a in ants)
    # cabeça: a abertura também se move quando a SS anda dentro do posto antes de ser cancelada (29 cabeças
    # canceladas da retrospectiva têm a ocorrência dias antes da abertura; a ETO-TELE 294/2025, um ano antes)
    d0 = por[k][0]
    return min(x for x in (d0["DTA_ABERTURA"], d0["DTA_OCORRENCIA"]) if x)


def saida(k, por):
    """(data, como, destino) — como: REPASSADA, ATENDIDA, CANCELADA ou PENDENTE (data None)."""
    d0, st = por[k][0], status(k, por)
    if st in ("SS ATENDIDA", "SS CANCELADA"):
        return d0["DTA_CONCLUSAO"], st.split()[-1], ""
    if st == "SS PENDENTE":
        return None, "PENDENTE", ""
    segs = sorted({_txt(por[d["_seg"]][0]["POSTO_SGM"]) for d in por[k] if d["_seg"] and d["_seg"] in por})
    return d0["DTA_ABERTURA"], "REPASSADA", " e ".join(segs)


def seguintes(k, por):
    """As SS para onde esta foi repassada (o repasse pode bifurcar)."""
    return sorted({d["_seg"] for d in por[k] if d["_seg"] and d["_seg"] in por})


def ordena(cad, por, antes):
    """A cadeia na ordem dos repasses: pela profundidade, e no empate pela chegada."""
    cad = set(cad)
    fundo = {}

    def prof(x, caminho=()):
        if x not in fundo:
            ants = [a for a in antes.get(x, ()) if a in cad and a not in caminho]
            fundo[x] = 1 + max((prof(a, caminho + (x,)) for a in ants), default=-1)
        return fundo[x]
    return sorted(cad, key=lambda x: (prof(x), chegada(x, por, antes), x))


def textos_export_1908():
    """{SS: texto} do export de 19/08/2026 (EQP_JOAO_19082026), para saber o que entrou no texto depois dele."""
    import base_eqp as be
    import sla_manutencao as sm
    reg, _, _ = be.ler()
    return {sm.norm(k): _txt(str(v["desc"]).replace("_x000D_", " ")) for k, v in reg.items()}


def textos_export_mae():
    """{SS: texto} do export de 11/07/2025 (RELIGA_REGULA_2025, a «planilha mãe»)."""
    import os
    import openpyxl
    import sla_manutencao as sm
    cam = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "RELIGA_REGULA_2025.xlsx")
    wb = openpyxl.load_workbook(cam, read_only=True, data_only=True)
    it = wb["Exportar Planilha (2)"].iter_rows(values_only=True)
    cab = next(it)
    i_ss, i_d = cab.index("SS_ORIGINAL"), cab.index("DESCRIÇÃO")
    out = {sm.norm(_txt(r[i_ss])): _txt(str(r[i_d] or "").replace("_x000D_", " ")) for r in it if r[i_ss]}
    wb.close()
    return out
