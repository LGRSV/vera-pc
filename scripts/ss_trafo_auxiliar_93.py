"""
As SS do trafo auxiliar dos ativos da visão ETO.

Pista do gestor (22/08): a obra pode não estar pendurada no religador, e sim no
TRAFO AUXILIAR dele. O trafo auxiliar tem código próprio — prefixo 51 (padrão) ou
57, com os oito dígitos finais iguais aos do equipamento pai —, e o recorte de
RL/RT (ssos_min) só guarda códigos 79 e 58, então essas SS ficavam invisíveis.

Este script varre a base crua atrás delas e grava o resultado, para a visão
orçamentária usar sem reabrir os 36 MB toda vez.

Grava data/missao/ss_trafo_auxiliar_93.json.
Rodar: python3 scripts/ss_trafo_auxiliar_93.py
"""

import json
import math
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import cadeia_obra as co  # noqa: E402
import extrai_ssos_min as em  # noqa: E402

SAIDA = os.path.join(RAIZ, "data", "missao", "ss_trafo_auxiliar_93.json")
PREFIXOS = ("51", "57")


def montar():
    with open(os.path.join(RAIZ, "data", "missao", "visao_consolidada.json"),
              encoding="utf-8") as fh:
        vc = json.load(fh)
    alvos = {i["ativo"] for b, d in vc["visao_eto"]["baldes"].items() for i in d["ativos"]}
    aux = {p + a[2:]: a for a in alvos for p in PREFIXOS}

    achados = []
    coord_do_pai = {}

    def trata(bruto):
        c = em._normaliza(bruto.split("@"))
        cod = c[13].strip()
        if cod in alvos:                      # guarda a coordenada do equipamento pai
            try:
                x, y = float(c[14].strip()), float(c[15].strip())
                if x and y:
                    coord_do_pai.setdefault(cod, (x, y, c[12].strip()))
            except ValueError:
                pass
        if cod not in aux:
            return
        achados.append({"trafo_auxiliar": cod, "ativo": aux[cod], "ss": c[0].strip(),
                        "os": c[1].strip(), "obra": c[2].strip(), "situacao": c[18].strip(),
                        "tipo_ss": c[26].strip(), "abertura": c[19].strip(),
                        "localidade": c[23].strip(), "coord_x": c[14].strip(),
                        "coord_y": c[15].strip(), "alimentador": c[12].strip(),
                        "texto": c[27].strip()[:400]})

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

    # O padrão do código não basta: os 3 últimos dígitos são a localidade e o miolo
    # coincide por acaso em praça grande. O que confirma é a COORDENADA — trafo
    # auxiliar de verdade fica na mesma estrutura do pai, a poucos metros — e o
    # alimentador. Quem não confirmar sai marcado, não silenciosamente descartado.
    LIMITE_METROS = 50.0
    for a in achados:
        pai = coord_do_pai.get(a["ativo"])
        try:
            x, y = float(a["coord_x"]), float(a["coord_y"])
        except ValueError:
            x = y = 0.0
        if not pai or not (x and y):
            a["confirmacao"] = "sem coordenada para conferir"
            a["confirmado"] = None
            continue
        dist = math.hypot(pai[0] - x, pai[1] - y)
        mesmo_alim = bool(pai[2]) and pai[2] == a["alimentador"]
        a["distancia_do_pai_m"] = round(dist, 1)
        a["mesmo_alimentador"] = mesmo_alim
        # quem manda é a coordenada: mesma estrutura é prova de que o trafo é daquele
        # equipamento. O alimentador é reforço, não requisito — ele muda com
        # remanejamento e derrubava caso com coordenada idêntica ao pai.
        a["confirmado"] = dist <= LIMITE_METROS
        a["confirmacao"] = (f"{dist:.1f} m do pai, "
                            f"{'mesmo' if mesmo_alim else 'outro'} alimentador — "
                            + ("é o trafo do equipamento" if a["confirmado"]
                               else "NÃO é trafo auxiliar, é coincidência de numeração"))

    pacote = {
        "gerado_em": "2026-08-23",
        "regua": "o padrão 51/57 + 8 dígitos finais do pai levanta o candidato; a "
                 f"coordenada confirma — até {LIMITE_METROS:.0f} m do pai e mesmo "
                 "alimentador. Sem isso, é coincidência de numeração.",
        "confirmados": sum(1 for a in achados if a.get("confirmado")),
        "descartados": sum(1 for a in achados if a.get("confirmado") is False),
        "fonte": f"{os.path.basename(base)} — SS cujo NUM_TRAFO é o trafo auxiliar "
                 "(51/57 + os 8 dígitos finais do pai) de um ativo da visão ETO",
        "qtd": len(achados),
        "ativos_com_ss_no_auxiliar": sorted({a["ativo"] for a in achados}),
        "com_obra": sorted({a["obra"].strip("0 ") and a["ativo"] for a in achados
                            if a["obra"].strip("0 ")}),
        "ss": sorted(achados, key=lambda x: (x["ativo"], x["abertura"][-4:], x["abertura"])),
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar()
    print(f"SS no trafo auxiliar: {p['qtd']} em {len(p['ativos_com_ss_no_auxiliar'])} ativos")
    print(f"com número de obra: {len(p['com_obra'])} — {', '.join(p['com_obra'])}")
    print(f"gravado: {SAIDA}")
