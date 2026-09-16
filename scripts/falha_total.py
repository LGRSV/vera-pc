"""
Os três anos numa base só — 2024, 2025 e 2026, sobre a base nova.

Junta tudo o que foi lido até aqui, remapeando para `EQP_JOAO_19082026.xlsx`:

  falha_dcmd_mae.json        497 cadeias do DCMD, 2024-25, régua de peça grande
  categoria_dcmd/            as 373 dessas sem peça grande, rotuladas por item
  falha_fora_dcmd/         1.137 de indisponibilidade/anomalia fora do DCMD, 2024-25
  verificacao_peca_grande/   a verificação adversarial dessas — derrubou 129 de 194
  leitura_2026/              912 da base nova, com 2026 dentro
  verificacao_2026/          a verificação adversarial dessas

**Por que dá para juntar**: as cadeias da planilha mãe e as da base nova têm a MESMA SS de
cabeça — conferido nas 497 do DCMD de 2024-25, zero divergência. A chave é a cabeça, então
a leitura antiga continua valendo sobre a base nova.

**A precedência é sempre verificação > leitura.** Quem olhou depois, com a pergunta
invertida, manda. Cada linha guarda `categoria_fonte`, para a discordância ficar auditável
em vez de sumir.

**Horizonte**: 19/08/2026. Agosto de 2026 é mês parcial.

Rodar: python3 scripts/falha_total.py
"""

import glob
import json
import os
import sys
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import base_eqp as be          # noqa: E402
import falha_dcmd_mae as fm    # noqa: E402
import falha_completa as fc    # noqa: E402

IA = os.path.join(RAIZ, "data", "analise_ia")
SAIDA = os.path.join(RAIZ, "data", "missao", "falha_total.json")
CORTE = "2026-08-19"
ANOS = (2024, 2025, 2026)


def _le(pasta, padrao="*.json"):
    fora = []
    for f in sorted(glob.glob(os.path.join(IA, pasta, padrao))):
        with open(f) as fh:
            fora += json.load(fh)
    return fora


def veredito(pasta):
    """{cadeia: (categoria_final, porque)} para o que os céticos mexeram."""
    fora = {}
    for o in _le(pasta):
        if not o.get("mantem") or o.get("categoria_final"):
            fora[o.get("cadeia")] = (o.get("categoria_final") or "nao identificado",
                                     o.get("porque") or "")
    return fora


def monta():
    reg, prox, comeco = be.ler()
    todas = fm.monta_cadeias(reg, prox, comeco)
    cabeca = {c[0]: c for c in todas}
    # Depois que a cadeia passou a seguir os ramos do repasse bifurcado, uma SS que ERA
    # cabeça virou elo do meio de outra cadeia. A leitura dela está guardada por aquela
    # chave — resolver só por cabeça a jogaria fora (75 leituras sumiam). `dono` acha a
    # cadeia por QUALQUER SS dela; a preferência pela cabeça fica na ordem do despacho.
    dono = {s: c for c in todas for s in c}
    marca, praca = fm.marcas(), fm.localidades()

    corrigido = {}
    corrigido.update(veredito("verificacao_peca_grande"))
    corrigido.update(veredito("verificacao_2026"))

    linhas, vistos, derrubados = [], set(), []

    pedidos = []

    def poe(o, cat_bruta, item, dcmd_flag=None):
        """Só enfileira. O despacho vem depois, com a cabeça na frente."""
        pedidos.append((o, cat_bruta, item, dcmd_flag))

    def emite(o, cat_bruta, item, dcmd_flag=None):
        cad = cabeca.get(o.get("cadeia")) or dono.get(o.get("cadeia"))
        if not cad or cad[0] in vistos:
            return
        d = reg[cad[0]]
        if not d["abert"] or d["abert"].year not in ANOS:
            return
        vistos.add(cad[0])
        fam = fm.familia(d["tipo"], d["cod_ele"])
        cat = fc.normaliza_cat(cat_bruta, fam)
        fonte = "leitura"
        if cad[0] in corrigido:
            novo = fc.normaliza_cat(corrigido[cad[0]][0], fam)
            if novo != cat:
                derrubados.append({"ativo": d["ativo"], "cadeia": cad[0],
                                   "de": cat, "para": novo,
                                   "porque": corrigido[cad[0]][1]})
                cat, fonte = novo, "verificacao"
        linhas.append({
            "ativo": d["ativo"], "fam": fam,
            # **O ano é o da ABERTURA DA PRIMEIRA SS** — a original, antes de a cadeia de
            # repasse começar (gestor, 16/09). O SGM abre SS nova a cada passagem de posto
            # e a data vai andando; só a primeira marca quando a demanda nasceu.
            # Conferido nas 7.563 cadeias da base: a cabeça da cadeia é SEMPRE a
            # abertura mais antiga, zero exceção — então `cad[0]` é a original.
            # A ocorrência fica ao lado: divergem em 59 fatos, 22 de peça grande (10%,
            # batendo com os 9,8% já registrados).
            "ano": d["abert"].year, "mes": d["abert"].month,
            "ocor": str(d["ocor"]) if d["ocor"] else "",
            "ano_ocor": d["ocor"].year if d["ocor"] else d["abert"].year,
            "mes_ocor": d["ocor"].month if d["ocor"] else d["abert"].month,
            "ano_diverge": bool(d["ocor"] and d["ocor"].year != d["abert"].year),
            "cadeia": cad[0], "abert": str(d["abert"]), "n_ss": len(cad),
            "postos": " -> ".join(reg[s]["posto"] for s in cad),
            "pend": d["pend"],
            "dcmd": fm.do_dcmd(cad, reg) if dcmd_flag is None else dcmd_flag,
            "categoria": cat, "categoria_fonte": fonte,
            "classe": fc.CLASSE[cat], "item": item or "",
            "executada": bool(o.get("executada")),
            "marca": fm.marca_limpa(marca.get(d["ativo"], {}).get("marca")),
            "marca_bruta": marca.get(d["ativo"], {}).get("marca", ""),
            "loc": (marca.get(d["ativo"], {}).get("loc")
                    or praca.get(d["ativo"]) or d["loc"]),
            "confianca": o.get("confianca") or "",
            "evidencia": (o.get("evidencia") or "")[:400],
            "motivo": o.get("motivo") or "",
        })

    # 1) a leitura de peça grande do DCMD, com a categoria dos 373 por cima
    cat2 = {o.get("cadeia"): o for o in _le("categoria_dcmd", "out*.json")}
    with open(os.path.join(IA, "falha_dcmd_mae.json")) as f:
        for l in json.load(f)["linhas"]:
            if l["falha"]:
                poe({**l, "cadeia": l["cadeia"]}, l["peca"], l["peca"])
            else:
                c2 = cat2.get(l["cadeia"], {})
                poe({**l, "cadeia": l["cadeia"]}, c2.get("categoria"), c2.get("item"))

    # 2) fora do DCMD, 2024-25
    for o in _le("falha_fora_dcmd", "f*.json"):
        poe(o, o.get("categoria"), o.get("item"))

    # 3) a base nova — 2026 e o que a mãe não alcançava
    for o in _le("leitura_2026", "n*.json"):
        poe(o, o.get("categoria"), o.get("item"))

    # Despacho: primeiro quem foi lido PELA CABEÇA da cadeia — é quem viu o parecer
    # original —, depois quem foi lido por um elo do meio. `sorted` é estável, então a
    # ordem das três fontes se mantém dentro de cada grupo.
    for o, cb, it, df in sorted(pedidos,
                                key=lambda x: 0 if x[0].get("cadeia") in cabeca else 1):
        emite(o, cb, it, df)

    return linhas, derrubados, reg, todas


def equipamento_ano(linhas):
    """Ativo + ano + item. O mesmo religador pode ter perdido o tanque numa demanda e o
    para-raio noutra — são dois fatos, e juntá-los apagaria um."""
    por = defaultdict(list)
    for l in linhas:
        por[(l["ativo"], l["ano"], l["categoria"])].append(l)
    fora = []
    for (ativo, ano, cat), g in sorted(por.items()):
        g.sort(key=lambda x: x["abert"])
        esc = next((x for x in g if x["executada"]), g[0])
        fora.append({**g[0], "demandas": len(g), "item": esc["item"],
                     "executada": any(x["executada"] for x in g),
                     "dcmd": any(x["dcmd"] for x in g)})
    return fc.reincidencia(fora)


if __name__ == "__main__":
    linhas, derrubados, reg, todas = monta()
    eqs = equipamento_ano(linhas)

    universo = [c for c in todas if reg[c[0]]["abert"] and reg[c[0]]["abert"].year in ANOS]
    pacote = {
        "linhas_n": len(linhas), "equipamentos": eqs,
        "categorias": [{"k": k, "rot": r, "classe": c} for k, r, c in fc.CATEGORIAS],
        "parque_marca": fm.parque_por_marca(),
        "universo": len(universo),
        "no_dcmd": sum(1 for c in universo if fm.do_dcmd(c, reg)),
        "fora_dcmd": sum(1 for c in universo if not fm.do_dcmd(c, reg)),
        "fora_sem_falha": sum(1 for c in universo if not fm.do_dcmd(c, reg)
                              and reg[c[0]]["pend"] not in be.PENDENCIA_FALHA),
        "derrubados": derrubados, "corte": CORTE,
    }
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w") as f:
        json.dump(pacote, f, ensure_ascii=False, indent=1)

    div = [e for e in eqs if e.get("ano_diverge")]
    print("datado pela ABERTURA DA PRIMEIRA SS (a original, antes do repasse)")
    print("  diverge da ocorrência em %d fatos (%d de peça grande)"
          % (len(div), sum(1 for e in div if e["classe"] == "grande")))
    print("universo 2024-2026: %d cadeias · lidas %d · fatos %d"
          % (len(universo), len(linhas), len(eqs)))
    print("derrubados pela verificação: %d" % len(derrubados))
    print()
    for classe in ("grande", "apoio", "meio", "fora", "nada"):
        sub = [e for e in eqs if e["classe"] == classe]
        if sub:
            print("  %-8s %4d — %s" % (classe, len(sub), ", ".join(
                "%s %d" % (fc.ROTULO[k], n) for k, n in
                sorted(Counter(e["categoria"] for e in sub).items(), key=lambda x: -x[1]))))
    print()
    print("  PEÇA GRANDE por ano e tipo:")
    for ano in ANOS:
        for fam in ("RL", "RT"):
            s = [e for e in eqs if e["ano"] == ano and e["fam"] == fam and e["classe"] == "grande"]
            print("    %d %s: %3d — %s" % (ano, fam, len(s),
                  dict(Counter(e["categoria"] for e in s))))
    print(SAIDA)
