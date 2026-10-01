"""
Monta o dossiê de cada ativo e reparte em lotes para os analistas.

O dossiê traz **todas as SS do ativo**, não só as da cadeia em análise. Isso é de
propósito: sem ver o histórico inteiro não dá para dizer se a demanda é duplicata de
outra, se a SS foi aberta por engano, ou se o defeito já tinha voltado antes.

As **suspeitas** vêm calculadas — mas não decidem nada. Elas só dizem onde olhar, para o
analista não ter de achar duplicata por acaso.

Rodar:
    python3 .claude/skills/analise-equipamento/scripts/dossie.py <destino> [--anos 2024,2025,2026] [--lotes 12]
"""

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import base_eqp as be          # noqa: E402
import falha_dcmd_mae as fm    # noqa: E402

CORTE_TEXTO = 2600
JANELA_DUPLICATA = 30          # dias
BLOCO_CANCELAMENTO = 5         # SS canceladas no mesmo dia, em postos diferentes


# ------------------------------------------------------------------ suspeitas
def _peca_provavel(texto):
    """Palpite grosseiro só para casar duplicatas — NUNCA para classificar.

    A triagem por palavra-chave foi reprovada como classificador (29% de fuga); aqui ela
    serve de chave de agrupamento, onde um falso positivo só junta duas demandas para o
    analista olhar."""
    t = (texto or "").lower()
    for chave, palavras in [
        ("tanque", ("tanque", "parte ativa", "câmara", "camara", "bucha")),
        ("controle", ("controle", "placa de aliment", "fonte", "armário de controle")),
        ("celula", ("célula", "celula")),
        ("completo", ("equipamento completo", "substituir o equipamento", "religador completo")),
        ("furto", ("furto", "furtad", "vandalismo", "roubo")),
    ]:
        if any(p in t for p in palavras):
            return chave
    return ""


def suspeitas(cad, reg, cancelamentos, por_ativo):
    """As bandeiras automáticas de uma cadeia. Apontam, não decidem."""
    d = reg[cad[0]]
    fora = []
    textos = " ".join(reg[s]["desc"] for s in cad)

    if not textos.strip():
        fora.append("sem_parecer")

    # duplicata: outra cadeia do mesmo ativo, peça parecida, aberta perto
    minha = _peca_provavel(textos)
    if minha:
        for outra in por_ativo[d["ativo"]]:
            if outra[0] == cad[0]:
                continue
            o = reg[outra[0]]
            if not o["abert"] or not d["abert"]:
                continue
            dias = abs((o["abert"] - d["abert"]).days)
            if dias <= JANELA_DUPLICATA:
                if _peca_provavel(" ".join(reg[s]["desc"] for s in outra)) == minha:
                    fora.append("mesma_peca_em_dias:%s(%dd)" % (outra[0], dias))

    # aberta e cancelada no mesmo dia, sem parecer
    for s in cad:
        r = reg[s]
        if r["status"] == "SS CANCELADA" and r["concl"] == r["abert"] and not r["desc"].strip():
            fora.append("cancelada_no_mesmo_dia:%s" % s)

    # cancelamento em bloco — limpeza de cadastro, não conserto
    for s in cad:
        r = reg[s]
        if r["status"] == "SS CANCELADA" and r["concl"]:
            postos = cancelamentos.get(r["concl"], set())
            if len(postos) >= BLOCO_CANCELAMENTO:
                fora.append("cancelamento_em_bloco:%s(%d postos em %s)"
                            % (s, len(postos), r["concl"]))

    # código de terceiro no texto
    import re
    codigos = set(re.findall(r"\b(?:79|78|58)\d{8}\b", textos))
    if codigos and d["ativo"] not in codigos:
        fora.append("codigo_de_terceiro:" + ",".join(sorted(codigos)[:3]))

    # reincidência: mesma peça provável, mesmo ativo, outro ano
    if minha and d["abert"]:
        for outra in por_ativo[d["ativo"]]:
            o = reg[outra[0]]
            if outra[0] == cad[0] or not o["abert"] or o["abert"].year == d["abert"].year:
                continue
            if _peca_provavel(" ".join(reg[s]["desc"] for s in outra)) == minha:
                fora.append("reincidencia:%s(%d)" % (outra[0], o["abert"].year))

    return sorted(set(fora))


# ------------------------------------------------------------------ dossiê
def escreve_ativo(a, cadeias_do_ativo, todas_do_ativo, reg, susp):
    """O bloco de um ativo: as demandas a analisar, mais o histórico inteiro."""
    L = ["=" * 94, "ATIVO %s  (%s · %s)" % (a, reg[todas_do_ativo[0][0]]["tipo"],
                                            reg[todas_do_ativo[0][0]]["loc"]), "=" * 94, ""]
    L.append("HISTÓRICO COMPLETO DO ATIVO — %d demandas, %d SS" %
             (len(todas_do_ativo), sum(len(c) for c in todas_do_ativo)))
    for c in sorted(todas_do_ativo, key=lambda c: reg[c[0]]["abert"] or dt.date(1900, 1, 1)):
        d = reg[c[0]]
        marca = "  >>> A ANALISAR" if c in cadeias_do_ativo else ""
        L.append("   %s · %s · %d SS · %s%s"
                 % (c[0], d["abert"], len(c), " -> ".join(reg[s]["posto"] for s in c), marca))
    L.append("")

    for i, cad in enumerate(cadeias_do_ativo, 1):
        p = reg[cad[0]]
        L.append("")
        L.append("  >>> DEMANDA %d — primeira SS %s aberta em %s (ocorrência %s), %d SS, postos: %s"
                 % (i, cad[0], p["abert"], p["ocor"], len(cad),
                    " -> ".join(reg[s]["posto"] for s in cad)))
        s_ = susp.get(cad[0], [])
        L.append("      SUSPEITAS: %s" % (", ".join(s_) if s_ else "nenhuma"))
        L.append("")
        for s in cad:
            d = reg[s]
            L.append("    --- %s | %s | %s | %s" % (s, d["posto"], d["status"], d["pend"]))
            L.append("        aberta %s  concluída %s" % (d["abert"], d["concl"]))
            t = d["desc"][:CORTE_TEXTO]
            L.append("        " + (t or "(sem descrição)").replace("\n", "\n        "))
            L.append("")
    return L


def monta(destino, anos, n_lotes, so_falta=None):
    reg, prox, comeco = be.ler()
    todas = fm.monta_cadeias(reg, prox, comeco)

    por_ativo = defaultdict(list)
    for c in todas:
        por_ativo[reg[c[0]]["ativo"]].append(c)

    # datas de cancelamento em bloco: dia -> conjunto de postos
    cancelamentos = defaultdict(set)
    for d in reg.values():
        if d["status"] == "SS CANCELADA" and d["concl"]:
            cancelamentos[d["concl"]].add(d["posto"])

    alvo = [c for c in todas
            if reg[c[0]]["abert"] and reg[c[0]]["abert"].year in anos
            and (fm.do_dcmd(c, reg) or reg[c[0]]["pend"] in be.PENDENCIA_FALHA)]
    if so_falta:
        alvo = [c for c in alvo if c[0] not in so_falta]

    susp = {c[0]: suspeitas(c, reg, cancelamentos, por_ativo) for c in alvo}

    grupos = defaultdict(list)
    for c in alvo:
        grupos[reg[c[0]]["ativo"]].append(c)
    ativos = sorted(grupos)

    os.makedirs(destino, exist_ok=True)
    os.makedirs(os.path.join(destino, "checkpoint"), exist_ok=True)
    tam = -(-len(ativos) // n_lotes) if ativos else 1
    fila = []
    for n in range(n_lotes):
        fatia = ativos[n * tam:(n + 1) * tam]
        if not fatia:
            continue
        L = []
        for a in fatia:
            L += escreve_ativo(a, grupos[a], por_ativo[a], reg, susp)
        cam = os.path.join(destino, "lote%02d.txt" % (n + 1))
        with open(cam, "w") as f:
            f.write("\n".join(L))
        fila.append({"lote": n + 1, "arquivo": cam, "ativos": len(fatia),
                     "demandas": sum(len(grupos[a]) for a in fatia),
                     "kb": os.path.getsize(cam) // 1024})

    with open(os.path.join(destino, "fila.json"), "w") as f:
        json.dump({"lotes": fila, "total_ativos": len(ativos),
                   "total_demandas": len(alvo),
                   "suspeitas": dict(Counter(s.split(":")[0] for v in susp.values() for s in v))},
                  f, ensure_ascii=False, indent=1)

    for x in fila:
        print("lote%02d  %2d ativos  %3d demandas  %3d KB  %s"
              % (x["lote"], x["ativos"], x["demandas"], x["kb"], x["arquivo"]))
    print("\n%d ativos · %d demandas · suspeitas: %s"
          % (len(ativos), len(alvo),
             dict(Counter(s.split(":")[0] for v in susp.values() for s in v))))
    return fila


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("destino")
    ap.add_argument("--anos", default="2024,2025,2026")
    ap.add_argument("--lotes", type=int, default=12)
    ap.add_argument("--faltando", help="JSON com lista de cadeias já lidas, para pular")
    a = ap.parse_args()
    ja = set()
    if a.faltando and os.path.exists(a.faltando):
        with open(a.faltando) as f:
            ja = set(json.load(f))
    monta(a.destino, {int(x) for x in a.anos.split(",")}, a.lotes, ja)
