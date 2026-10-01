"""
Junta a análise e a verificação da RETROSPECTIVA num registro por demanda.

Precedência: verificação > análise. A verificação é adversarial — o que ela derruba, cai; o que ela
acha faltando, entra. O relatório diz quanto ela mudou: esse número é resultado, não ruído.

Rodar (depois de `ckpt.py fecha` nas duas etapas):
    python3 .claude/skills/analise-equipamento/scripts/juntar_retro.py .analise/retro2026
Grava <run>/retro.json.
"""

import datetime as dt
import json
import re
import os
import sys
from collections import Counter

CAMPOS = (("desfecho", "desfecho_final"), ("executada", "executada_final"), ("data_execucao", "data_execucao_final"),
          ("voltou_a_operar", "voltou_a_operar_final"), ("backlog_2025", "backlog_2025_final"),
          ("tratada_em_2025", "tratada_em_2025_final"))


def dia(s):
    """A data da tratativa. Quando o agente escreveu uma janela («08/07/2026 a 19/08/2026»), vale o fim dela —
    o «no mais tardar», como no parecer datado pelo repasse."""
    datas = re.findall(r"\d{2}/\d{2}/\d{4}", s or "")
    if not datas:
        return None
    try:
        return dt.datetime.strptime(datas[-1], "%d/%m/%Y").date()
    except ValueError:
        return None


def chave_tratativa(t):
    return ((t.get("data") or "").strip(), (t.get("acao") or "").strip().lower())


def junta(run):
    an = json.load(open(os.path.join(run, "analise.json"), encoding="utf-8"))
    ve = json.load(open(os.path.join(run, "verificacao.json"), encoding="utf-8"))
    estrutura = json.load(open(os.path.join(run, "estrutura.json"), encoding="utf-8"))
    lista = lambda x: x if isinstance(x, list) else list(x.values()) if isinstance(x, dict) else []
    an = {r.get("_chave") or r.get("ativo"): r for r in lista(an)}
    ve = {r.get("_chave") or r.get("ativo"): r for r in lista(ve)}
    out, mudou = [], Counter()
    for ativo, a in an.items():
        v = {d.get("cadeia"): d for d in (ve.get(ativo) or {}).get("demandas", [])}
        cabecas = {c["cabeca"]: c for c in estrutura.get(ativo, [])}
        for d in a.get("demandas", []):
            r = dict(d)
            r["ativo"], r["familia"] = ativo, a.get("familia")
            r["estrutura"] = cabecas.get(d.get("cadeia"))
            x = v.get(d.get("cadeia"))
            r["verificada"] = x is not None
            r["mantida"] = bool(x.get("mantem")) if x else None
            if x:
                for campo, final in CAMPOS:
                    if final in x and x[final] != d.get(campo):
                        mudou[campo] += 1
                        r[campo + "_analista"] = d.get(campo)
                        r[campo] = x[final]
                if x.get("prova_final"):
                    r["prova_execucao"] = x["prova_final"]
                if not r.get("executada"):
                    r["prova_execucao"] = ""            # sem execução, «prova» não pode ser «selecionado para compra»
                erradas = {chave_tratativa(t) for t in x.get("tratativas_erradas", []) or []}
                tr = [t for t in d.get("tratativas", []) if chave_tratativa(t) not in erradas]
                mudou["tratativas retiradas"] += len(d.get("tratativas", [])) - len(tr)
                faltando = x.get("tratativas_faltando", []) or []
                tr += [dict(t, incluida_na_verificacao=True) for t in faltando]
                mudou["tratativas incluídas"] += len(faltando)
                r["tratativas"] = sorted(tr, key=lambda t: (dia(t.get("data")) or dt.date(1900, 1, 1)))
                r["porque_verificacao"], r["confianca_verificacao"] = x.get("porque"), x.get("confianca")
            out.append(r)
    # correções do orquestrador: prova de serviço numa SS irmã, fora da cadeia (irmas_retro.py), com a frase literal
    cam = os.path.join(run, "correcoes.json")
    if os.path.exists(cam):
        corr = {(c["ativo"], c["cadeia"]): c for c in json.load(open(cam, encoding="utf-8"))}
        for r in out:
            c = corr.get((r["ativo"], r.get("cadeia")))
            if not c:
                continue
            for campo in ("desfecho", "executada", "data_execucao", "como_datou_execucao", "voltou_a_operar",
                          "tratada_em_2025"):
                if campo in c and c[campo] != r.get(campo):
                    r.setdefault(campo + "_verificador", r.get(campo))
                    r[campo] = c[campo]
            r["prova_execucao"] = c.get("prova", r.get("prova_execucao"))
            r["correcao_irma"] = f"{c['ss_irma']}: {c['porque']}"
            mudou["corrigidas pela SS irmã"] += 1
    sem_verif = sum(1 for r in out if not r["verificada"])
    rel = {"demandas": len(out), "ativos": len(an), "verificadas": len(out) - sem_verif,
           "mantidas": sum(1 for r in out if r["mantida"]), "derrubadas": sum(1 for r in out if r["mantida"] is False),
           "mudou_por_campo": dict(mudou)}
    with open(os.path.join(run, "retro.json"), "w", encoding="utf-8") as fh:
        json.dump({"relatorio": rel, "demandas": out}, fh, ensure_ascii=False, indent=1)
    print(json.dumps(rel, ensure_ascii=False, indent=1))
    return out, rel


if __name__ == "__main__":
    junta(sys.argv[1] if len(sys.argv) > 1 else ".analise/retro2026")
