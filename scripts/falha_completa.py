"""
Todas as falhas de RL e RT em 2024-2025, por categoria — dentro e fora do DCMD.

Junta três leituras da planilha mãe numa base só:

  1. as 497 cadeias que passaram pelo DCMD, lidas pela régua de PEÇA GRANDE
     (`falha_dcmd_mae.py`, cache em `data/analise_ia/falha_dcmd_mae/`) — 124 com peça grande;
  2. as 373 dessas mesmas 497 que NÃO eram peça grande, rotuladas por item numa segunda
     passada (`data/analise_ia/categoria_dcmd/`);
  3. as 1.137 cadeias de indisponibilidade ou anomalia que NUNCA tocaram o DCMD, lidas do
     zero já com a taxonomia inteira (`data/analise_ia/falha_fora_dcmd/`).

**Por que a 3 existe**: o recorte do DCMD cobria 21% do universo. Das 2.384 cadeias de
2024-2025, 1.887 nunca passaram por um posto com «-RD-» — morreram na TELE (1.335) ou na
PROT (502). Dessas, 1.137 são de indisponibilidade ou anomalia, ou seja, candidatas a falha
de verdade. Ficar só nas 497 dava a resposta de uma pergunta mais estreita do que a feita.

A coluna `dcmd` guarda a diferença, então as duas leituras nunca viram uma só por acidente.

**Horizonte**: a planilha mãe fecha em 11/07/2025. Agosto de 2025 em diante não existe na
base — não é fila que cedeu.

Rodar: python3 scripts/falha_completa.py
"""

import datetime as dt
import glob
import json
import os
import sys
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import falha_dcmd_mae as fm  # noqa: E402

CAT_DCMD = os.path.join(RAIZ, "data", "analise_ia", "categoria_dcmd")
FORA = os.path.join(RAIZ, "data", "analise_ia", "falha_fora_dcmd")
SAIDA = os.path.join(RAIZ, "data", "missao", "falha_completa.json")

PENDENCIA_FALHA = {"INDISPONIBILIDADE PARA OPERAÇÃO", "EM OPERAÇÃO COM ANOMALIA",
                   "ANOMALIA EM RELIGADOR", "ANOMALIA EM REGULADORES", "AVISO DE ANOMALIA"}

# a ordem é a da conversa do gestor: primeiro o equipamento, depois o apoio, depois o resto
CATEGORIAS = [
    ("tanque", "Tanque / parte ativa", "grande"),
    ("controle", "Controle", "grande"),
    ("completo", "Equipamento completo", "grande"),
    ("celula", "Célula", "grande"),
    ("rele", "Relé", "grande"),
    ("furto", "Furto", "grande"),
    ("trafo auxiliar", "Trafo auxiliar", "apoio"),
    ("chave faca", "Chave faca", "apoio"),
    ("para-raio", "Para-raio", "apoio"),
    ("fusivel", "Fusível", "apoio"),
    ("bateria", "Bateria", "apoio"),
    ("cabo", "Cabo / conector", "apoio"),
    ("aterramento", "Aterramento", "apoio"),
    ("telecom", "Telecom", "apoio"),
    ("poste", "Poste / estrutura", "meio"),
    ("poda", "Poda / vegetação", "meio"),
    ("ajuste de protecao", "Ajuste de proteção", "fora"),
    ("comissionamento", "Comissionamento", "fora"),
    ("obra nova", "Obra nova", "fora"),
    ("melhoria", "Melhoria", "fora"),
    ("sem defeito", "Sem defeito", "nada"),
    ("nao identificado", "Não identificado", "nada"),
]
ROTULO = {k: r for k, r, _ in CATEGORIAS}
CLASSE = {k: c for k, _, c in CATEGORIAS}
ORDEM = {k: i for i, (k, _, _) in enumerate(CATEGORIAS)}


def _le(pasta, padrao="*.json"):
    fora = []
    for f in sorted(glob.glob(os.path.join(pasta, padrao))):
        with open(f) as fh:
            fora += json.load(fh)
    return fora


def normaliza_cat(bruta, fam):
    """Rótulo fora da lista vira 'nao identificado'; peça que não cabe na família também.
    Tanque em regulador e célula em religador são erro de rotulagem, não achado."""
    c = (bruta or "").strip().lower()
    c = {"célula": "celula", "relé": "rele", "parte ativa": "tanque",
         "chave": "chave faca", "para raio": "para-raio", "pararaio": "para-raio",
         "conector": "cabo", "jumper": "cabo", "ajuste de proteção": "ajuste de protecao",
         "fusível": "fusivel", "não identificado": "nao identificado"}.get(c, c)
    if c not in ORDEM:
        return "nao identificado"
    if fam == "RT" and c in ("tanque", "controle"):
        return "celula" if c == "tanque" else "nao identificado"
    if fam == "RL" and c in ("celula", "rele"):
        return "nao identificado"
    return c


def monta():
    reg, prox, comeco = fm.ler()
    todas = fm.monta_cadeias(reg, prox, comeco)
    cabeca = {c[0]: c for c in todas}
    marca, praca = fm.marcas(), fm.localidades()

    # --- 1 e 2: as 497 do DCMD ------------------------------------------------
    dcmd_cads = fm.recorte(reg, prox, comeco)
    leitura = fm.junta(cads=dcmd_cads)
    cat2 = {(o.get("cadeia")): o for o in _le(CAT_DCMD)}
    linhas = []
    for o in leitura:
        cad = cabeca.get(o.get("cadeia"))
        if not cad:
            continue
        d = reg[cad[0]]
        fam = fm.familia(d["tipo"], d["cod_ele"])
        if o.get("houve_falha"):
            cat, item = normaliza_cat(o.get("peca"), fam), (o.get("peca") or "")
        else:
            c2 = cat2.get(cad[0], {})
            cat = normaliza_cat(c2.get("categoria"), fam)
            item = c2.get("item") or ""
        linhas.append(_linha(d, cad, reg, fam, cat, item, o, True, marca, praca))

    # --- 3: as 1.137 de fora --------------------------------------------------
    vistos = {l["cadeia"] for l in linhas}
    for o in _le(FORA):
        cad = cabeca.get(o.get("cadeia"))
        if not cad or cad[0] in vistos:
            continue
        vistos.add(cad[0])
        d = reg[cad[0]]
        fam = fm.familia(d["tipo"], d["cod_ele"])
        cat = normaliza_cat(o.get("categoria"), fam)
        linhas.append(_linha(d, cad, reg, fam, cat, o.get("item") or "", o, False, marca, praca))

    return linhas, reg, todas


def _linha(d, cad, reg, fam, cat, item, o, dcmd, marca, praca):
    return {
        "ativo": d["ativo"], "fam": fam, "ano": d["abert"].year, "mes": d["abert"].month,
        "cadeia": cad[0], "abert": str(d["abert"]), "n_ss": len(cad),
        "postos": " -> ".join(reg[s]["posto"] for s in cad),
        "pend": d["pend"], "dcmd": dcmd,
        "categoria": cat, "classe": CLASSE[cat], "item": item,
        "executada": bool(o.get("executada")),
        "marca": fm.marca_limpa(marca.get(d["ativo"], {}).get("marca")),
        "marca_bruta": marca.get(d["ativo"], {}).get("marca", ""),
        "loc": (marca.get(d["ativo"], {}).get("loc") or praca.get(d["ativo"]) or d["loc"]),
        "confianca": o.get("confianca") or "",
        "evidencia": (o.get("evidencia") or "")[:400],
        "motivo": o.get("motivo") or "",
    }


def equipamento_ano(linhas):
    """A régua do gestor: ativo que falhou duas vezes no ano conta uma vez naquele ano.
    Aqui a chave é ativo+ano+CATEGORIA — o mesmo religador pode ter perdido o tanque e,
    noutra demanda, o para-raio; são dois fatos, não um."""
    por = defaultdict(list)
    for l in linhas:
        por[(l["ativo"], l["ano"], l["categoria"])].append(l)
    fora = []
    for (ativo, ano, cat), g in sorted(por.items()):
        g.sort(key=lambda x: x["abert"])
        esc = next((x for x in g if x["executada"]), g[0])
        fora.append({**g[0], "cadeias": len(g),
                     "executada": any(x["executada"] for x in g),
                     "item": esc["item"],
                     "dcmd": any(x["dcmd"] for x in g)})
    return fora


def grava(linhas, eqs, reg, todas, saida=SAIDA):
    universo = [c for c in todas if reg[c[0]]["abert"] and reg[c[0]]["abert"].year in (2024, 2025)]
    fora_dcmd = [c for c in universo if not fm.do_dcmd(c, reg)]
    pacote = {
        "linhas": linhas, "equipamentos": eqs,
        "categorias": [{"k": k, "rot": r, "classe": c} for k, r, c in CATEGORIAS],
        "parque_marca": fm.parque_por_marca(),
        "universo": len(universo),
        "no_dcmd": len(universo) - len(fora_dcmd),
        "fora_dcmd": len(fora_dcmd),
        "fora_sem_falha": sum(1 for c in fora_dcmd if reg[c[0]]["pend"] not in PENDENCIA_FALHA),
        "corte": "2025-07-11",
    }
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w") as f:
        json.dump(pacote, f, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    linhas, reg, todas = monta()
    eqs = equipamento_ano(linhas)
    p = grava(linhas, eqs, reg, todas)
    print("universo 2024-2025: %d cadeias · %d passaram pelo DCMD · %d não"
          % (p["universo"], p["no_dcmd"], p["fora_dcmd"]))
    print("lidas e rotuladas: %d cadeias → %d equipamento-ano-categoria"
          % (len(linhas), len(eqs)))
    print()
    for classe in ("grande", "apoio", "meio", "fora", "nada"):
        sub = [e for e in eqs if e["classe"] == classe]
        if not sub:
            continue
        print("  %-8s %4d — %s" % (classe, len(sub),
              ", ".join("%s %d" % (ROTULO[k], n) for k, n in
                        sorted(Counter(e["categoria"] for e in sub).items(),
                               key=lambda x: -x[1]))))
    print()
    for ano in (2024, 2025):
        for fam in ("RL", "RT"):
            sub = [e for e in eqs if e["ano"] == ano and e["fam"] == fam and e["classe"] in ("grande", "apoio", "meio")]
            print("  %d %s: %d equipamentos com falha (%d no DCMD, %d fora)"
                  % (ano, fam, len(sub), sum(1 for e in sub if e["dcmd"]),
                     sum(1 for e in sub if not e["dcmd"])))
    print(SAIDA)
