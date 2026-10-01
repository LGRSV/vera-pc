"""
Dossiê da RETROSPECTIVA — o que foi feito com cada equipamento a partir de abril de 2026.

Variante do `dossie.py` para outra pergunta: não «qual peça falhou», e sim «o que o COEP e a
cadeia fizeram com a demanda, quando, e se o equipamento foi atendido de verdade».

O universo é toda demanda (cadeia de repasses) de RL/RT que passou pelo posto do COEP e:
  - esteve no COEP em algum momento entre 01/04/2026 e a posição da base, OU
  - teve SS aberta ou concluída nesse intervalo depois de passar pelo COEP.
O dossiê traz, para cada uma, TODAS as SS em ordem, e de cada SS só o texto que ELA
acrescentou (o SGM é cumulativo: repetir o texto inteiro a cada SS esconde o que é novo).

Para datar as tratativas, cada SS traz:
  - a data de abertura (o repasse) e a de saída (conclusão, ou abertura da SS seguinte);
  - o cancelamento com data e hora, e quantas SS de RL/RT foram canceladas no mesmo dia;
  - o que o texto da SS ganhou depois do export de 19/08/2026 (comparando com o de 23/09) e se
    o texto já existia no export de 11/07/2025 (a «planilha mãe»);
  - a OS da base de SS/OS (até 20/08/2026): número, esquema, obra, fabricante retirado/instalado;
  - as assinaturas com data escritas no texto novo («29/06 PARECER COEP», «DMSL 16/07»…).

Rodar:
    python3 .claude/skills/analise-equipamento/scripts/dossie_retro.py .analise/retro2026 --lotes 12
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

import openpyxl

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import base_eqp as be                # noqa: E402 — export de 19/08/2026
import sla_falhas_regional as sf     # noqa: E402 — export de 23/09/2026, cadeia e saída
import sla_manutencao as sm          # noqa: E402 — norm() do número da SS

INICIO = dt.datetime(2026, 4, 1)
HOJE = sf.HOJE
MAE = os.path.join(RAIZ, "data", "raw", "RELIGA_REGULA_2025.xlsx")        # export de 11/07/2025
SSOS = os.path.join(RAIZ, "data", "missao", "ssos_min.json")             # base de SS/OS até 20/08/2026
CORTE = 1800                         # caracteres do texto novo de uma SS no dossiê
ASSINA = re.compile(r"(?:(\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)\s*[-–.]?\s*)?"
                    r"((?:PARECER|PARECE)\s*(?:D[OA]S?\s*)?[A-ZÇÃÉÊÍÓÚ/ -]{2,30}?|COEP|COCMS?|DMSL|DCMD|DEOP|COI|PROTE[ÇC][ÃA]O)"
                    r"\s*(?:-|–)?\s*(\(?\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\)?)?\s*[:\-–]", re.I)


def txt(v):
    """Texto limpo: o export de 11/07/2025 traz a quebra de linha como «_x000D_» literal."""
    return re.sub(r"\s+", " ", str(v).replace("_x000D_", " ")).strip() if v is not None else ""


def fmt(d, hora=False):
    if not d:
        return "—"
    return d.strftime("%d/%m/%Y %H:%M" if hora and isinstance(d, dt.datetime) else "%d/%m/%Y")


def novo(texto, anterior):
    """Os trechos de `texto` que não estão em `anterior`, por diferença de palavras."""
    if not anterior:
        return texto
    if anterior in texto:
        return texto.replace(anterior, " ¦ ", 1).strip(" ¦")
    a, b = anterior.split(), texto.split()
    sm_ = SequenceMatcher(None, a, b, autojunk=False)
    partes = [" ".join(b[j1:j2]) for op, i1, i2, j1, j2 in sm_.get_opcodes() if op in ("insert", "replace")]
    return " ¦ ".join(p for p in partes if p)


# ------------------------------------------------------------------ exports antigos
def export_mae():
    """{SS: texto} do export de 11/07/2025."""
    wb = openpyxl.load_workbook(MAE, read_only=True, data_only=True)
    ws = wb["Exportar Planilha (2)"]
    it = ws.iter_rows(values_only=True)
    cab = next(it)
    i_ss, i_d, i_st = cab.index("SS_ORIGINAL"), cab.index("DESCRIÇÃO"), cab.index("STATUS")
    out = {}
    for r in it:
        if r[i_ss]:
            out[sm.norm(txt(r[i_ss]))] = (txt(r[i_d]), txt(r[i_st]))
    wb.close()
    return out


def export_1908():
    """{SS: (texto, status)} do export de 19/08/2026."""
    reg, _, _ = be.ler()
    return {sm.norm(k): (txt(v["desc"]), v["status"]) for k, v in reg.items()}


def os_da_base():
    with open(SSOS, encoding="utf-8") as fh:
        linhas = json.load(fh)
    out = defaultdict(list)
    for x in linhas:
        out[sm.norm(x["NUMERO_SS"])].append(x)
    return out


# ------------------------------------------------------------------ cadeias
def componentes(por):
    pai = {k: k for k in por}

    def acha(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x
    for k, v in por.items():
        for d in v:
            if d["_seg"] and d["_seg"] in por:
                a, b = acha(k), acha(d["_seg"])
                if a != b:
                    pai[b] = a
    grupos = defaultdict(list)
    for k in por:
        grupos[acha(k)].append(k)
    return list(grupos.values())


# ------------------------------------------------------------------ as datas certas
# O export do SGM SOBRESCREVE a DTA_ABERTURA (e a DTA_REPASSE, que é cópia dela) da SS no momento em
# que ela é repassada. Prova: as 63 SS pendentes no export de 11/07/2025 que foram repassadas depois
# aparecem no de 23/09/2026 com a abertura igual ao instante do repasse; idem as 21 repassadas entre
# 19/08 e 23/09/2026. Então, para SS REPASSADA, a «abertura» é a SAÍDA; a chegada é o repasse da SS
# anterior (a abertura dela). Na cabeça repassada, a chegada é a DTA_OCORRENCIA, que o SGM copia
# para a cadeia inteira e que nas cabeças não repassadas é igual à abertura.
def status(k, por):
    return txt(por[k][0]["STATUS"]).upper()


def chegada(k, por, antes):
    ants = [a for a in antes.get(k, ()) if a in por]
    if ants:
        return min(por[a][0]["DTA_ABERTURA"] for a in ants)
    d0 = por[k][0]
    if status(k, por) == "SS REPASSADA" and d0["DTA_OCORRENCIA"]:
        return d0["DTA_OCORRENCIA"]
    return d0["DTA_ABERTURA"]


def saida(k, por):
    """(data, como, destino). REPASSADA: a própria abertura é o instante do repasse."""
    d0, st = por[k][0], status(k, por)
    if st in ("SS ATENDIDA", "SS CANCELADA"):
        return d0["DTA_CONCLUSAO"], st.split()[-1], ""
    if st == "SS PENDENTE":
        return None, "PENDENTE", ""
    segs = sorted({txt(por[d["_seg"]][0]["POSTO_SGM"]) for d in por[k] if d["_seg"] and d["_seg"] in por})
    return d0["DTA_ABERTURA"], "REPASSADA", " e ".join(segs) if segs else "(SS seguinte fora da base)"


def vida(k, por, antes):
    """(chegada, saída) da SS no posto; saída None = segue lá."""
    sai, como, _ = saida(k, por)
    return chegada(k, por, antes), (None if como == "PENDENTE" else sai)


def ordena(cad, por, antes):
    """A cadeia na ordem em que as SS chegaram; no empate, quem repassou antes de quem recebeu."""
    fundo = {}

    def prof(x, caminho=()):
        if x not in fundo:
            ants = [a for a in antes.get(x, ()) if a in cad and a not in caminho]
            fundo[x] = 1 + max((prof(a, caminho + (x,)) for a in ants), default=-1)
        return fundo[x]
    return sorted(cad, key=lambda x: (prof(x), chegada(x, por, antes), x))


def no_periodo(cad, por, antes):
    """Esteve no COEP entre 01/04/2026 e a posição, ou teve movimento nesse intervalo depois de passar pelo COEP."""
    coep = [k for k in cad if "COEP" in txt(por[k][0]["POSTO_SGM"])]
    if not coep:
        return False
    for k in coep:
        e, s = vida(k, por, antes)
        if e <= HOJE and (s is None or s >= INICIO):
            return True
    primeiro_coep = min(chegada(k, por, antes) for k in coep)
    for k in cad:
        e, s = vida(k, por, antes)
        if e >= primeiro_coep and (INICIO <= e <= HOJE or (s and INICIO <= s <= HOJE)):
            return True
    return False


# ------------------------------------------------------------------ texto do dossiê
def bloco_ss(k, por, antes, mae, s1908, oss, cancel_dia):
    d0 = por[k][0]
    posto, st = txt(d0["POSTO_SGM"]), txt(d0["STATUS"]).upper()
    sai, como, dest = saida(k, por)
    cheg = chegada(k, por, antes)
    t = txt(d0["DESCRIÇÃO"])
    ants = sorted((a for a in antes.get(k, ()) if a in por), key=lambda a: chegada(a, por, antes))
    ant = ants[0] if ants else None
    tn = novo(t, txt(por[ant][0]["DESCRIÇÃO"]) if ant else "")
    L = [f"    --- {k} | {posto} | {st} | {txt(d0['PENDENCIA_DO_ATIVO'])}"]
    linha = f"        chegou {fmt(cheg, True)}" + (" (cabeça: data de ocorrência)" if not ant and cheg != d0["DTA_ABERTURA"] else "")
    if como in ("ATENDIDA", "CANCELADA"):
        linha += f" · {como.lower()} em {fmt(sai, True)}"
        if como == "CANCELADA":
            n, postos = cancel_dia.get(sai.date(), (0, set())) if sai else (0, set())
            linha += f" (neste dia, {n} SS de RL/RT canceladas em {len(postos)} postos)"
    elif como == "REPASSADA":
        linha += f" · repassada em {fmt(sai, True)} para {dest}"
    elif como == "PENDENTE":
        linha += " · SEGUE PENDENTE neste posto na posição da base"
    else:
        linha += f" · {como.lower()}"
    if cheg:
        linha += f" · {((sai or HOJE) - cheg).days} dias no posto" + ("" if sai else " até 23/09")
    if d0["DTA_CONCLUSAO"] and como == "ATENDIDA" and cheg and d0["DTA_CONCLUSAO"] < cheg:
        linha += " · ATENÇÃO: conclusão ANTES da abertura (SS aberta depois do serviço)"
    L.append(linha)
    if ant:
        L.append(f"        veio de {ant} ({txt(por[ant][0]['POSTO_SGM'])})")
    # exports antigos
    marcas = []
    if k in mae:
        marcas.append("já existia no export de 11/07/2025" + (", com o mesmo texto" if mae[k][0] == t else ", com texto MENOR (ganhou texto depois de 11/07/2025)"))
    if k in s1908:
        t1, st1 = s1908[k]
        if t1 != t:
            add = novo(t, t1)
            marcas.append(f"no export de 19/08/2026 estava «{st1}»; TEXTO ACRESCENTADO ENTRE 19/08 E 23/09/2026: «{add[:600]}»")
        elif st1.upper() != st:
            marcas.append(f"no export de 19/08/2026 estava «{st1}», mesmo texto")
    elif cheg and cheg <= dt.datetime(2026, 8, 19, 12, 0):
        marcas.append("NÃO estava no export de 19/08/2026")
    for m in marcas:
        L.append("        export: " + m)
    for o in oss.get(k, []):
        partes = [f"OS {txt(o['NUMERO_OS'])}" if o["NUMERO_OS"] else "sem OS", f"esquema «{txt(o['ESQUEMA'])}»" if o["ESQUEMA"] else "",
                  f"obra {o['NUM_OBRA']}" if o["NUM_OBRA"] else "", f"equipe {o['COD_EQUIPE']}" if o["COD_EQUIPE"] else "",
                  f"fabricante retirado {o['FABRICANTE_RETIRADO']}" if o["FABRICANTE_RETIRADO"] else "",
                  f"fabricante instalado {o['FABRICANTE_INSTALADO']}" if o["FABRICANTE_INSTALADO"] else "",
                  f"tipo {o['TIPOSS']}"]
        L.append("        base SS/OS (20/08): " + " · ".join(p for p in partes if p))
    assin = []
    for m in ASSINA.finditer(tn):
        quando = m.group(1) or (m.group(3) or "").strip("()")
        if quando:
            assin.append(f"{quando} {m.group(2).strip()}")
    if assin:
        L.append("        assinaturas com data no texto novo: " + " · ".join(dict.fromkeys(assin)))
    corpo = tn if len(tn) <= CORTE else tn[:CORTE] + f" […+{len(tn) - CORTE} caracteres]"
    rot = "TEXTO COMPLETO (primeira SS da cadeia)" if not ant else "TEXTO NOVO DESTA SS (o que ela acrescentou à anterior)"
    L.append(f"        {rot}:")
    L.append("        «" + (corpo or "(nada novo)") + "»")
    L.append("")
    return L


def resumo_cadeia(cad, por, antes):
    d0 = por[cad[0]][0]
    ult = por[cad[-1]][0]
    postos = " → ".join(dict.fromkeys(re.sub(r"^ETO-|^DOLP-|^ENC-|^DG-", "", txt(por[k][0]["POSTO_SGM"])) for k in cad))
    return (f"{cad[0]} · aberta {fmt(chegada(cad[0], por, antes))} · {len(cad)} SS · {postos} · última: "
            f"{txt(ult['STATUS'])} ({txt(ult['POSTO_SGM'])}) · {txt(d0['PENDENCIA_DO_ATIVO'])}")


def escreve_ativo(a, alvo, todas, por, antes, mae, s1908, oss, cancel_dia, rol, gest):
    t0 = por[alvo[0][0]][0]
    L = ["=" * 100, f"ATIVO {a}  ({txt(t0['TIPO_ATIVO'])} · {txt(t0['COD_LOC'])} · alimentador {txt(t0['COD_ALIMENTADOR'])})", "=" * 100]
    if a in gest:
        L.append(f"Gestão COEP 5 (28/09): criticidade «{gest[a]['criticidade']}», status «{gest[a]['status']}»")
    for x in rol.get(a, []):
        L.append(f"ROL DE FALHAS: {x['tipo']} {x['ano']} · peça {x['peca']} · ocorrência {x['ocorrencia']} · SS {x['ss']} · "
                 f"troca: {x['troca'] or 'sem troca registrada'} ({x['situacao']}; {x['evidencia'][:120]})")
    L.append("")
    L.append(f"HISTÓRICO COMPLETO DO ATIVO — {len(todas)} demandas desde 2024")
    for c in sorted(todas, key=lambda c: chegada(c[0], por, antes)):
        L.append("   " + resumo_cadeia(c, por, antes) + ("   >>> A ANALISAR" if c in alvo else ""))
        if c not in alvo:
            ult = txt(por[c[-1]][0]["DESCRIÇÃO"])
            if ult:
                L.append("        último texto: «" + ult[:280] + ("…" if len(ult) > 280 else "") + "»")
    virada = dt.datetime(2026, 1, 1)
    for i, cad in enumerate(alvo, 1):
        d0 = por[cad[0]][0]
        ini = chegada(cad[0], por, antes)
        aberta_virada = ini < virada and any(e < virada and (s is None or s >= virada)
                                             for e, s in (vida(k, por, antes) for k in cad))
        L += ["", f"  >>> DEMANDA {i} — cabeça {cad[0]}, aberta {fmt(ini)} (ocorrência {fmt(d0['DTA_OCORRENCIA'])}), "
                  f"{len(cad)} SS", f"      ORIGEM: aberta em {ini.year}"
                  + (" — seguia aberta na virada para 2026 (backlog de 2025)" if aberta_virada else ""), ""]
        for k in cad:
            L += bloco_ss(k, por, antes, mae, s1908, oss, cancel_dia)
    L.append("")
    return L


def monta(destino, n_lotes):
    por, antes, _ = sf.base()
    mae, s1908, oss = export_mae(), export_1908(), os_da_base()
    with open(sf.JSON, encoding="utf-8") as fh:
        rol = defaultdict(list)
        for x in json.load(fh)["itens"]:
            rol[x["ativo"]].append(x)
    gest = sf.gestao()
    cancel_dia = defaultdict(lambda: [0, set()])
    for k, v in por.items():
        d0 = v[0]
        if txt(d0["STATUS"]).upper() == "SS CANCELADA" and d0["DTA_CONCLUSAO"]:
            c = cancel_dia[d0["DTA_CONCLUSAO"].date()]
            c[0] += 1
            c[1].add(txt(d0["POSTO_SGM"]))
    cancel_dia = {k: (v[0], v[1]) for k, v in cancel_dia.items()}

    cadeias = [ordena(set(g), por, antes) for g in componentes(por)]
    por_ativo = defaultdict(list)
    for c in cadeias:
        if any((vida(k, por, antes)[1] or HOJE) >= dt.datetime(2024, 1, 1) for k in c):
            por_ativo[txt(por[c[0]][0]["EQUIPAMENTO"])].append(c)
    alvo = defaultdict(list)
    for a, cs in por_ativo.items():
        for c in cs:
            if no_periodo(c, por, antes):
                alvo[a].append(c)
    ativos = sorted(alvo)

    os.makedirs(destino, exist_ok=True)
    blocos = {a: "\n".join(escreve_ativo(a, alvo[a], por_ativo[a], por, antes, mae, s1908, oss, cancel_dia, rol, gest))
              for a in ativos}
    # lotes do mesmo tamanho em texto, não em número de ativos
    total = sum(len(b) for b in blocos.values())
    meta, fila, atual, n = total / n_lotes, [], [], 1
    for a in ativos:
        atual.append(a)
        if sum(len(blocos[x]) for x in atual) >= meta and n < n_lotes:
            fila.append(atual)
            atual, n = [], n + 1
    if atual:
        fila.append(atual)
    lotes = []
    for i, lote in enumerate(fila, 1):
        cam = os.path.join(destino, f"lote{i:02d}.txt")
        with open(cam, "w", encoding="utf-8") as fh:
            fh.write("\n".join(blocos[a] for a in lote))
        lotes.append({"lote": i, "arquivo": cam, "ativos": lote, "demandas": sum(len(alvo[a]) for a in lote),
                      "kb": os.path.getsize(cam) // 1024})
    with open(os.path.join(destino, "ativos.json"), "w", encoding="utf-8") as fh:
        json.dump(ativos, fh)
    with open(os.path.join(destino, "partes.json"), "w", encoding="utf-8") as fh:
        json.dump({a: x["lote"] for x in lotes for a in x["ativos"]}, fh)
    # a estrutura das cadeias, para o compilador não depender do texto
    estrutura = {}
    for a in ativos:
        estrutura[a] = []
        for c in alvo[a]:
            ss = []
            for k in c:
                d0 = por[k][0]
                sai, como, dest = saida(k, por)
                ss.append({"ss": k, "posto": txt(d0["POSTO_SGM"]), "status": txt(d0["STATUS"]), "tipo": txt(d0["PENDENCIA_DO_ATIVO"]),
                           "chegada": chegada(k, por, antes).isoformat(), "saida": sai.isoformat() if sai else None,
                           "como": como, "destino": dest})
            estrutura[a].append({"cabeca": c[0], "ss": ss})
    with open(os.path.join(destino, "estrutura.json"), "w", encoding="utf-8") as fh:
        json.dump(estrutura, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(destino, "fila.json"), "w", encoding="utf-8") as fh:
        json.dump({"lotes": [{k: v for k, v in x.items() if k != "ativos"} | {"n_ativos": len(x["ativos"])} for x in lotes],
                   "total_ativos": len(ativos), "total_demandas": sum(len(v) for v in alvo.values())}, fh, ensure_ascii=False, indent=1)
    for x in lotes:
        print(f"lote{x['lote']:02d}  {len(x['ativos']):3d} ativos  {x['demandas']:3d} demandas  {x['kb']:4d} KB")
    print(f"\n{len(ativos)} ativos · {sum(len(v) for v in alvo.values())} demandas")
    return lotes


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("destino")
    ap.add_argument("--lotes", type=int, default=12)
    a = ap.parse_args()
    monta(a.destino, a.lotes)
