"""
O que o trafo auxiliar dos religadores e reguladores custou em 2026.

Pedido do gestor (23/08): recorte de 2026. A obra do equipamento às vezes não está
pendurada nele, e sim no TRAFO AUXILIAR — código 51/57 com os oito dígitos finais do
pai. Como o recorte de RL/RT só guarda 79/78/58, essas SS e as obras delas ficavam
invisíveis em toda conta de custo.

A régua, aprendida no susto: o padrão do código levanta o candidato, mas NÃO prova —
os três últimos dígitos são a localidade e o miolo coincide por acaso em praça grande.
Quem confirma é a COORDENADA: trafo auxiliar de verdade fica na mesma estrutura do
pai, a poucos metros. O alimentador entra como reforço, não como requisito (muda com
remanejamento). Foi assim que caíram três falsos de Araguaína, um deles a 11 km.

O que o trafo auxiliar custa fica FORA DA TAXA DE FALHA — trafo auxiliar não é peça
grande, é a régua do gestor. Mas é custo do parque, e é isso que este script mede.

Grava data/missao/trafo_auxiliar_2026.json.
Rodar: python3 scripts/trafo_auxiliar_2026.py
"""

import json
import math
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import cadeia_obra as co  # noqa: E402
import extrai_ssos_min as em  # noqa: E402

SAIDA = os.path.join(RAIZ, "data", "missao", "trafo_auxiliar_2026.json")
PREFIXOS = ("51", "57")
ANO = "2026"
LIMITE_METROS = 50.0


def _num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def montar():
    with open(os.path.join(RAIZ, "data", "missao", "ssos_min.json"), encoding="utf-8") as fh:
        pais = {r["NUM_TRAFO"] for r in json.load(fh)}
    with open(os.path.join(RAIZ, "data", "missao", "aic_full.json"), encoding="utf-8") as fh:
        aic = json.load(fh)

    coord_pai, achados = {}, []

    def trata(bruto):
        c = em._normaliza(bruto.split("@"))
        cod = c[13].strip()
        if cod in pais:
            try:
                x, y = float(c[14].strip()), float(c[15].strip())
                if x and y:
                    coord_pai.setdefault(cod, (x, y, c[12].strip()))
            except ValueError:
                pass
        if len(cod) != 10 or cod[:2] not in PREFIXOS:
            return
        for p in ("79", "78", "58"):
            pai = p + cod[2:]
            if pai in pais:
                achados.append({"trafo_auxiliar": cod, "ativo": pai, "ss": c[0].strip(),
                                "obra": c[2].strip(), "abertura": c[19].strip()[:10],
                                "situacao": c[18].strip(), "tipo_ss": c[26].strip(),
                                "localidade": c[23].strip(), "alimentador": c[12].strip(),
                                "x": c[14].strip(), "y": c[15].strip(),
                                "texto": c[27].strip()[:300]})
                break

    base = next((p for p in co.PARTES if os.path.exists(p)), None)
    if base is None:
        raise SystemExit("base crua de SS/OS não encontrada")
    buffer = None
    with open(base, encoding="latin-1") as fh:
        for i, linha in enumerate(fh):
            linha = linha.rstrip("\r\n")
            if i == 0 and linha.startswith("NUMERO_SS@"):
                continue
            if co.RE_INICIO.match(linha):
                if buffer is not None:
                    trata(buffer)
                buffer = linha
            elif buffer is not None:
                buffer += "\n" + linha
        if buffer is not None:
            trata(buffer)

    do_ano = [a for a in achados if a["abertura"][6:10] == ANO]
    confirmados, descartados = [], []
    for a in do_ano:
        pai = coord_pai.get(a["ativo"])
        try:
            x, y = float(a["x"]), float(a["y"])
        except ValueError:
            x = y = 0.0
        if not pai or not (x and y):
            a["confirmacao"] = "sem coordenada para conferir — fica de fora"
            descartados.append(a)
            continue
        dist = math.hypot(pai[0] - x, pai[1] - y)
        a["distancia_do_pai_m"] = round(dist, 1)
        a["mesmo_alimentador"] = bool(pai[2]) and pai[2] == a["alimentador"]
        if dist <= LIMITE_METROS:
            a["confirmacao"] = f"{dist:.1f} m do pai — mesma estrutura"
            confirmados.append(a)
        else:
            a["confirmacao"] = (f"{dist:.0f} m do pai — coincidência de numeração, "
                                "não é o trafo dele")
            descartados.append(a)

    obras = {}
    for a in confirmados:
        o = a["obra"].split(".")[0].strip()
        if not (o.isdigit() and int(o) > 0):
            continue
        oid = o.zfill(10)
        r = aic.get(oid)
        obras[oid] = {
            "obra": oid, "ativo": a["ativo"], "trafo_auxiliar": a["trafo_auxiliar"],
            "ss": a["ss"], "localidade": a["localidade"],
            "no_aic": bool(r),
            "abertura": str((r or {}).get("DTH_ABERTURA", ""))[:10],
            "projeto_sigco": str((r or {}).get("NUM_PROJETO_SIGCO", "")).strip(),
            "descricao": str((r or {}).get("DESCRICAO_OBRA", ""))[:80],
            "orcado": round(_num((r or {}).get("VAL_TOTAL_ORCADO")), 2),
            "realizado": round(_num((r or {}).get("TOTAL_REALIZADO")), 2),
        }
    realizado = round(sum(o["realizado"] for o in obras.values()), 2)

    pacote = {
        "gerado_em": "2026-08-23",
        "ano": ANO,
        "regua": ("candidato pelo código 51/57 + 8 dígitos finais do pai; confirmação "
                  f"pela coordenada, até {LIMITE_METROS:.0f} m do equipamento. Fora da "
                  "taxa de falha — trafo auxiliar não é peça grande —, mas é custo."),
        "ss_no_ano": len(do_ano),
        "confirmados": len(confirmados),
        "descartados": len(descartados),
        "religadores": sorted({a["ativo"] for a in confirmados}),
        "obras": sorted(obras.values(), key=lambda x: x["obra"]),
        "obras_no_aic": sum(1 for o in obras.values() if o["no_aic"]),
        "realizado": realizado,
        "orcado": round(sum(o["orcado"] for o in obras.values()), 2),
        "ss": sorted(confirmados, key=lambda x: (x["ativo"], x["abertura"])),
        "nao_confirmados": descartados,
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar()
    print(f"SS de trafo auxiliar abertas em {ANO}: {p['ss_no_ano']} — "
          f"{p['confirmados']} confirmadas, {p['descartados']} descartadas")
    print(f"religadores atingidos: {len(p['religadores'])}")
    print(f"obras: {len(p['obras'])} ({p['obras_no_aic']} no AIC) · "
          f"realizado R$ {p['realizado']:,.2f}")
    for o in p["obras"]:
        print(f"   {o['obra']} · {o['ativo']} · {o['localidade'][:18]:<18} "
              f"SIGCO {o['projeto_sigco'] or '—':<6} R$ {o['realizado']:>10,.2f}"
              + ("" if o["no_aic"] else "  (fora do extrato do AIC)"))
    print(f"gravado: {SAIDA}")
