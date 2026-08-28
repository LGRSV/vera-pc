"""
A partição dos 143 na régua fechada em 28/08, corrigida em 29/08.

Três decisões do gestor, nas duas pontas da conta:

1. QUEM VOLTOU NÃO CONTA COMO RESOLVIDO. «Se voltaram eu não resolvi» — o equipamento
   que resolveu uma demanda no ano e voltou para a fila conta só como pendente. Tira
   os 11 sobrepostos dos resolvidos.

2. QUEM SAIU DO CAMPO TAMBÉM NÃO ENTRA NOS RESOLVIDOS. Os 15 que estão em ajuste de
   proteção ou comissionamento tiveram a peça trocada e o campo devolveu — a parte do
   COEP acabou —, mas o equipamento segue com SS aberta em outra mesa, de 1 a 41 dias
   lá. Contá-los como resolvidos inflava o ano para 86, e o gestor não reconhece esse
   número: «nem eu acho que resolvi 86». Ficam em balde próprio, à vista.

3. OS 3 QUE AINDA ESTÃO NUM COCM ficam em execução no campo: a obra está acontecendo
   agora.

Resultado: 71 resolvidos · 54 na fila · 15 despachados · 3 em execução = 143, e a conta
do posto fecha em 71 + 54 = 125 — que é onde a memória do gestor sempre esteve
(«125 que passaram pelo COEP, desses resolvemos 72 e estamos com 53»).

Grava data/missao/particao_coep.json.
Rodar: python3 scripts/particao_coep.py [base_de_repasse.xlsx]
"""

import datetime as dt
import json
import os
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import sla_manutencao as base  # noqa: E402
import sla_por_equipe as eq  # noqa: E402

SAIDA = os.path.join(RAIZ, "data", "missao", "particao_coep.json")
COEP = os.path.join(RAIZ, "data", "missao", "coep_2026.json")


def ainda_no_campo(ss_atual, reg, anterior):
    """A cadeia termina numa equipe de campo? Então a obra ainda está acontecendo."""
    cad = base.cadeia(eq.do_comeco(base.norm(ss_atual), anterior), reg)
    ultimo = cad[-1][1]["posto"] if cad and cad[-1][1] else ""
    postos = [x[1]["posto"] for x in cad if x[1]]
    return "-RD-" in ultimo, [p for p in postos if "-RD-" in p]


def montar(caminho=None):
    reg = base.base_de_repasse(caminho)
    anterior = eq.raizes(reg)
    with open(COEP, encoding="utf-8") as fh:
        cp = json.load(fh)

    at = {a["ativo"]: a for a in cp["ativos"]}
    res = {r["ativo"]: r for r in cp["resolvidos_do_coep"]
           if r["conta_como_resolvido_pelo_coep"]}
    fila = {a for a, v in at.items() if v["segue_no_posto"]}
    voltaram = set(res) & fila

    itens, execucao = [], []
    for r in cp["pendentes_em_outra_mesa"]:
        no_campo, passou = ainda_no_campo(r["ss_atual"], reg, anterior)
        registro = {
            "ativo": r["ativo"], "tipo": r["tipo"], "localidade": r["localidade"],
            "ss_atual": r["ss_atual"], "onde_esta": r["onde_esta"],
            "etapa": r["etapa_da_esteira"], "dias_la": r["dias_la"],
            "passou_por_cocm": passou,
        }
        if no_campo:
            registro["situacao"] = "Em execução no campo"
            registro["nota"] = ("a cadeia termina num COCM — a obra está acontecendo "
                                "agora; entra nos resolvidos quando a equipe devolver")
            execucao.append(registro)
        else:
            registro["situacao"] = "Despachado para outra mesa"
            registro["nota"] = ("peça trocada e campo devolveu; a parte do COEP acabou, "
                                "mas a SS segue aberta no braço seguinte "
                                f"({r['etapa_da_esteira'].split('—')[0].strip()})")
            itens.append(registro)

    resolvidos = sorted(set(res) - voltaram)
    despachados = sorted(x["ativo"] for x in itens)
    pacote = {
        "regua": "gestor, 28/08 e 29/08: quem voltou para a fila não conta como "
                 "resolvido. Quem saiu do campo para ajuste ou comissionamento também "
                 "não entra nos resolvidos — a parte do COEP acabou, mas o equipamento "
                 "segue com SS aberta em outra mesa; fica em balde próprio. E quem ainda "
                 "está num COCM fica em execução no campo.",
        "contas": {
            "passaram": len(at),
            "resolvidos": len(resolvidos),
            "na_fila": len(fila),
            "despachados_para_outra_mesa": len(despachados),
            "em_execucao_no_campo": len(execucao),
            "trabalho_do_coep_concluido": len(resolvidos) + len(despachados),
            "conta_do_posto": len(resolvidos) + len(fila),
            "fora_do_posto": len(despachados) + len(execucao),
            "voltaram_para_a_fila": len(voltaram),
        },
        "por_tipo": dict(Counter(
            "RL" if a[:2] in ("79", "78") else "RT" for a in resolvidos)),
        "resolvidos_por_outra_mesa": itens,
        "em_execucao": execucao,
        "voltaram": sorted(voltaram),
    }
    # O passivo: quem já estava na mesa em 1º de janeiro, pelo ano em que chegou.
    # Entra como informativo — não muda conta nenhuma, mas responde de onde vem a fila.
    def ano_de(txt):
        try:
            return dt.datetime.strptime(txt, "%d/%m/%Y").year
        except (TypeError, ValueError):
            return None

    sig = lambda a: "RL" if at[a]["tipo"] == "religador" else "RT"
    herdados = {a for a, v in at.items() if v["ja_estava_de_antes"]}
    novos = set(at) - herdados
    res = set(resolvidos)
    execs = {x["ativo"] for x in execucao}

    def conta(conj):
        c = Counter(sig(a) for a in conj)
        return {"RL": c.get("RL", 0), "RT": c.get("RT", 0), "total": len(conj)}

    pacote["quadro"] = {
        "passaram": conta(set(at)),
        "passivo": conta(herdados),
        "passivo_por_ano": {str(y): conta({a for a in herdados
                                           if ano_de(at[a]["primeira_chegada"]) == y})
                            for y in (2023, 2024, 2025)},
        "chegaram_em_2026": conta(novos),
        "resolvidos": conta(res),
        "resolvidos_do_passivo": conta(herdados & res),
        "resolvidos_dos_novos": conta(novos & res),
        "na_fila": conta(fila),
        "fila_do_passivo": conta(herdados & fila),
        "despachados": conta(set(despachados)),
        "coep_concluiu": conta(set(resolvidos) | set(despachados)),
        "em_execucao": conta(execs),
        "conta_do_posto": conta(res | fila),
    }
    # O quadro pelo ANO DA DEMANDA — o passivo de verdade: demanda nascida em 2023,
    # 2024 ou 2025 que ainda estava viva quando o ano virou. Não confundir com o ano em
    # que o equipamento chegou à mesa, que é outra coisa.
    def ano_da_demanda(a):
        r = res.get(a) if isinstance(res, dict) else None
        r = {x["ativo"]: x for x in cp["resolvidos_do_coep"]}.get(a)
        if r and r.get("ano_da_demanda"):
            return int(r["ano_da_demanda"])
        return ano_de(at[a]["primeira_chegada"])

    anos = ["2023", "2024", "2025", "2026"]
    grupos = {"resolvidos": set(resolvidos), "fila": set(fila),
              "despachados": set(despachados), "execucao": execs}
    # a leitura do escopo do posto: encerradas + despachadas. Não entra na soma dos
    # 143 — é um recorte por cima dos dois primeiros baldes, não um quinto balde.
    coep = {"coep_concluiu": set(resolvidos) | set(despachados)}
    quadro_ano = {}
    for tipo in ("RL", "RT"):
        quadro_ano[tipo] = {}
        for nome, conj in grupos.items():
            por_ano = {y: sum(1 for a in conj
                              if sig(a) == tipo and str(ano_da_demanda(a)) == y)
                       for y in anos}
            por_ano["passivo"] = sum(por_ano[y] for y in ("2023", "2024", "2025"))
            por_ano["total"] = sum(por_ano[y] for y in anos)
            quadro_ano[tipo][nome] = por_ano
    for tipo in ("RL", "RT"):
        for nome, conj in coep.items():
            por_ano = {y: sum(1 for a in conj
                              if sig(a) == tipo and str(ano_da_demanda(a)) == y)
                       for y in anos}
            por_ano["passivo"] = sum(por_ano[y] for y in ("2023", "2024", "2025"))
            por_ano["total"] = sum(por_ano[y] for y in anos)
            quadro_ano[tipo][nome] = por_ano
    quadro_ano["Total"] = {
        nome: {k: quadro_ano["RL"][nome][k] + quadro_ano["RT"][nome][k]
               for k in list(anos) + ["passivo", "total"]}
        for nome in list(grupos) + list(coep)}
    for tipo in quadro_ano:
        quadro_ano[tipo]["geral"] = {
            k: sum(quadro_ano[tipo][n][k] for n in grupos)
            for k in list(anos) + ["passivo", "total"]}
    pacote["quadro_ano"] = quadro_ano
    pacote["anos"] = anos

    pacote["passivo_na_fila"] = sorted(
        ({"ativo": a, "tipo": sig(a), "localidade": at[a]["localidade"],
          "desde": at[a]["primeira_chegada"], "dias": at[a]["dias_no_posto"]}
         for a in herdados & fila), key=lambda x: -x["dias"])

    assert (pacote["contas"]["resolvidos"] + pacote["contas"]["na_fila"]
            + pacote["contas"]["despachados_para_outra_mesa"]
            + pacote["contas"]["em_execucao_no_campo"] == len(at)), "a partição não fecha"
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar(sys.argv[1] if len(sys.argv) > 1 else None)
    c = p["contas"]
    print(f"gravado: {SAIDA}")
    print(f"  {c['resolvidos']} resolvidos · {c['na_fila']} na fila · "
          f"{c['despachados_para_outra_mesa']} despachados · "
          f"{c['em_execucao_no_campo']} em execução = {c['passaram']}")
    print(f"  conta do posto: {c['resolvidos']} + {c['na_fila']} = {c['conta_do_posto']}")
    print(f"  fora do posto: {c['fora_do_posto']} · "
          f"{c['voltaram_para_a_fila']} voltaram e saíram dos resolvidos")
    print(f"  por tipo: {p['por_tipo']}")
    for x in p["em_execucao"]:
        print(f"    em execução: {x['ativo']} · {x['localidade']} · {x['onde_esta']} · "
              f"{x['dias_la']}d")
