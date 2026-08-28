"""
O TIPOSS de cada um dos 143 — o que o COEP realmente resolveu.

O gestor, 29/08: «nem fudendo eu consertei 86 equipamentos». Ele está certo, e o que
faltava era o TIPO da SS. «Resolvido» estava somando coisas que não são conserto:

  INDISPONIBILIDADE PARA OPERAÇÃO   o equipamento saiu de operação — é falha
  EM OPERAÇÃO COM ANOMALIA          o equipamento está rodando com defeito — é falha
  AVISO DE ANOMALIA / ANOMALIA EM RELIGADOR / AVISO PROTEÇÃO   aviso, não parada
  OBRAS (NOVOS EQUIPAMENTOS)        instalação de equipamento novo — não é conserto
  COMISSIONAMENTO / AJUSTES DE PROTEÇÃO / SOLICITAÇÃO DE SERVIÇO   idem

O tipo do ativo é o da SS mais pesada que ele teve no COEP (a régua PESO abaixo): se
o equipamento chegou a sair de operação, a demanda é de indisponibilidade, mesmo que
depois tenha aberto uma SS mais leve.

Duas SS de janeiro de 2023 (7915029003 e 7923674004) não estão na base de SS/OS — o
export só alcança 24 SS do COEP daquele ano. Ficam como «sem SS na base», sem chute.

Grava data/missao/tipo_da_demanda.json e dist/TIPO_DA_DEMANDA.xlsx.
Rodar: python3 scripts/tipo_da_demanda.py
"""

import json
import os
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import cadeia_obra as co  # noqa: E402

COEP = os.path.join(RAIZ, "data", "missao", "coep_2026.json")
PARTICAO = os.path.join(RAIZ, "data", "missao", "particao_coep.json")
SAIDA = os.path.join(RAIZ, "data", "missao", "tipo_da_demanda.json")
PLANILHA = os.path.join(RAIZ, "dist", "TIPO_DA_DEMANDA.xlsx")

SEM_SS = "(sem SS na base)"

# A ordem é a régua: a mais pesada ganha quando o ativo tem várias.
PESO = [
    "INDISPONIBILIDADE PARA OPERAÇÃO",
    "EM OPERAÇÃO COM ANOMALIA",
    "ANOMALIA EM RELIGADOR",
    "AVISO DE ANOMALIA",
    "AVISO PROTEÇÃO & SELETIVIDADE",
    "AJUSTES DE PROTEÇÃO",
    "COMISSIONAMENTO",
    "SOLICITAÇÃO DE SERVIÇO",
    "OBRAS (NOVOS EQUIPAMENTOS)",
]
ORDEM = {t: i for i, t in enumerate(PESO)}

FAMILIA = {
    "INDISPONIBILIDADE PARA OPERAÇÃO": "Falha — saiu de operação",
    "EM OPERAÇÃO COM ANOMALIA": "Falha — rodando com defeito",
    "ANOMALIA EM RELIGADOR": "Aviso de anomalia",
    "AVISO DE ANOMALIA": "Aviso de anomalia",
    "AVISO PROTEÇÃO & SELETIVIDADE": "Aviso de anomalia",
    "AJUSTES DE PROTEÇÃO": "Não é conserto",
    "COMISSIONAMENTO": "Não é conserto",
    "SOLICITAÇÃO DE SERVIÇO": "Não é conserto",
    "OBRAS (NOVOS EQUIPAMENTOS)": "Não é conserto",
    SEM_SS: "Sem SS na base",
}
BALDES = ["resolvidos", "despachados", "fila", "execucao"]
ROTULO_BALDE = {
    "resolvidos": "Demanda encerrada",
    "despachados": "Despachado para outra mesa",
    "fila": "Na fila do posto",
    "execucao": "Em execução no campo",
}


def mapa_tiposs():
    """NUMERO_SS -> TIPOSS, da base de SS/OS mais nova."""
    m = {}
    for reg in co.registros():
        num = (reg.get("NUMERO_SS") or "").strip()
        if num:
            m[num] = (reg.get("TIPOSS") or "").strip().upper()
    return m


def montar():
    tiposs = mapa_tiposs()
    with open(COEP, encoding="utf-8") as fh:
        cp = json.load(fh)
    with open(PARTICAO, encoding="utf-8") as fh:
        pc = json.load(fh)

    at = {a["ativo"]: a for a in cp["ativos"]}
    fila = {a for a, v in at.items() if v["segue_no_posto"]}
    desp = {x["ativo"] for x in pc["resolvidos_por_outra_mesa"]}
    exe = {x["ativo"] for x in pc["em_execucao"]}
    res = {r["ativo"] for r in cp["resolvidos_do_coep"]
           if r["conta_como_resolvido_pelo_coep"]} - fila
    desfecho = {r["ativo"]: r["como_terminou"] for r in cp["resolvidos_do_coep"]
                if r["ativo"] in res}
    onde = {}
    for nome, conj in (("resolvidos", res), ("despachados", desp),
                       ("fila", fila), ("execucao", exe)):
        for a in conj:
            onde[a] = nome

    linhas = []
    for a, v in at.items():
        ss = [s.strip() for s in (v["ss"] or "").split("|") if s.strip()]
        tipos = [tiposs[s] for s in ss if tiposs.get(s)]
        principal = min(tipos, key=lambda t: ORDEM.get(t, 99)) if tipos else SEM_SS
        linhas.append({
            "ativo": a,
            "sigla": "RL" if v["tipo"] == "religador" else "RT",
            "tipo": v["tipo"],
            "localidade": v["localidade"],
            "criticidade": v.get("criticidade") or "",
            "balde": onde[a],
            "balde_rotulo": ROTULO_BALDE[onde[a]],
            "tipo_da_demanda": principal,
            "familia": FAMILIA.get(principal, "Outro"),
            "todos_os_tipos": " | ".join(sorted(set(tipos))),
            "qtd_ss_no_coep": len(ss),
            "como_terminou": desfecho.get(a, ""),
            "ss": v["ss"],
            "dias_no_posto": v["dias_no_posto"],
        })
    linhas.sort(key=lambda x: (BALDES.index(x["balde"]),
                               ORDEM.get(x["tipo_da_demanda"], 99), x["ativo"]))

    tipos_vistos = sorted({x["tipo_da_demanda"] for x in linhas},
                          key=lambda t: ORDEM.get(t, 99))
    cruzado = {t: {b: sum(1 for x in linhas
                          if x["tipo_da_demanda"] == t and x["balde"] == b)
                   for b in BALDES} for t in tipos_vistos}
    for t in cruzado:
        cruzado[t]["total"] = sum(cruzado[t][b] for b in BALDES)

    por_familia = {}
    for f in dict.fromkeys(FAMILIA.values()):
        sub = [x for x in linhas if x["familia"] == f]
        if sub:
            por_familia[f] = {b: sum(1 for x in sub if x["balde"] == b)
                              for b in BALDES}
            por_familia[f]["total"] = len(sub)

    desfecho_por_tipo = {
        t: {"atendida": sum(1 for x in linhas if x["tipo_da_demanda"] == t
                            and x["como_terminou"] == "SS ATENDIDA"),
            "cancelada": sum(1 for x in linhas if x["tipo_da_demanda"] == t
                             and x["como_terminou"] == "SS CANCELADA"),
            "total": cruzado[t]["resolvidos"]}
        for t in tipos_vistos}

    indisp = "INDISPONIBILIDADE PARA OPERAÇÃO"
    anomalia = "EM OPERAÇÃO COM ANOMALIA"
    resumo = {
        "passaram": len(linhas),
        "indisponibilidade": cruzado.get(indisp, {}).get("total", 0),
        "em_operacao_com_anomalia": cruzado.get(anomalia, {}).get("total", 0),
        "indisponibilidade_resolvida": cruzado.get(indisp, {}).get("resolvidos", 0),
        "anomalia_resolvida": cruzado.get(anomalia, {}).get("resolvidos", 0),
        "indisponibilidade_atendida": desfecho_por_tipo.get(indisp, {}).get("atendida", 0),
        "indisponibilidade_cancelada": desfecho_por_tipo.get(indisp, {}).get("cancelada", 0),
        "indisponibilidade_despachada": cruzado.get(indisp, {}).get("despachados", 0),
        "nao_e_conserto": sum(v["total"] for f, v in por_familia.items()
                              if f in ("Não é conserto", "Aviso de anomalia")),
    }
    # o que o parque de fato ganhou de volta: saiu de operação, SS atendida
    resumo["troca_confirmada"] = (resumo["indisponibilidade_atendida"]
                                  + resumo["indisponibilidade_despachada"])

    pacote = {
        "regua": ("o tipo do ativo é o da SS mais pesada que ele teve no COEP; "
                  "indisponibilidade > em operação com anomalia > aviso > o resto"),
        "fonte": os.path.basename(co.PARTES[0]),
        "resumo": resumo,
        "cruzado": cruzado,
        "por_familia": por_familia,
        "desfecho_por_tipo": desfecho_por_tipo,
        "baldes": BALDES,
        "rotulo_balde": ROTULO_BALDE,
        "por_ativo": linhas,
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar()
    r = p["resumo"]
    print(f"gravado: {SAIDA}")
    print(f"  {r['passaram']} ativos · {r['indisponibilidade']} de indisponibilidade · "
          f"{r['em_operacao_com_anomalia']} em operação com anomalia")
    print(f"  nos encerrados: {r['indisponibilidade_resolvida']} de indisponibilidade "
          f"({r['indisponibilidade_atendida']} atendidas · "
          f"{r['indisponibilidade_cancelada']} canceladas) · "
          f"{r['anomalia_resolvida']} em operação com anomalia")
    print(f"  troca confirmada (saiu de operação e a SS foi atendida ou despachada): "
          f"{r['troca_confirmada']}")
    print()
    larg = max(len(t) for t in p["cruzado"])
    print(f"  {'TIPOSS':{larg}s} " + " ".join(f"{b[:9]:>9s}" for b in p["baldes"])
          + f" {'TOTAL':>6s}")
    for t, d in p["cruzado"].items():
        print(f"  {t:{larg}s} " + " ".join(f"{d[b]:9d}" for b in p["baldes"])
              + f" {d['total']:6d}")
