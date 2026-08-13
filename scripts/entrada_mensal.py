"""
Carteira de entrada, mês a mês — os 117 ativos da foto de junho distribuídos
pela data de abertura da SS.

Regra do gestor (13/08): SS aberta antes de 2026 entra em janeiro de 2026. O
mês de janeiro passa a ser, na prática, «o que eu já herdei velho», e os meses
seguintes mostram o que chegou depois.

A data sai da coluna DATA_ABERTURA_SS da aba «Dados» da planilha de entrada.
Quando a SS só existe na aba «Dados Tratados», que não traz abertura, a data
vem do cruzamento pelo número da SS com a base de SS/OS cheia — o caminho que
o gestor mandou usar.

Ativo com mais de uma SS na foto entra pela mais antiga: é quando a demanda
chegou ao posto.
"""

import datetime
import json
import os
from collections import Counter, defaultdict

import openpyxl

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(RAIZ, "data", "raw", "BASE_SS_OS_EQ_ESPECIAIS_ENTRADA.xlsx")
ARQ_MIN = os.path.join(RAIZ, "data", "missao", "ssos_min.json")

CORTE = 2026
MES_CORTE = "2026-01"
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]

PLANILHA = "planilha de entrada"
CRUZAMENTO = "cruzamento pela SS na base de SS/OS"

FORMATOS = ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y")


def _data(texto):
    t = str(texto or "").strip()
    if not t:
        return None
    for f in FORMATOS:
        try:
            return datetime.datetime.strptime(t[:19] if " " in t else t[:10], f).date()
        except ValueError:
            continue
    return None


def _aberturas_da_planilha():
    """NUMERO_SS → data de abertura, da aba «Dados» (extrato cru do SGM)."""
    if not os.path.exists(XLSX):
        return {}
    ws = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)["Dados"]
    linhas = ws.iter_rows(values_only=True)
    cabecalho = list(next(linhas))
    try:
        i_ss = cabecalho.index("NUMERO_SS")
        i_ab = cabecalho.index("DATA_ABERTURA_SS")
    except ValueError:
        return {}
    fora = {}
    for r in linhas:
        ss = str(r[i_ss] or "").strip()
        if ss and ss not in fora:
            fora[ss] = _data(r[i_ab])
    return {k: v for k, v in fora.items() if v}


def _aberturas_da_base():
    """NUMERO_SS → data de abertura, da base de SS/OS cheia."""
    if not os.path.exists(ARQ_MIN):
        return {}
    with open(ARQ_MIN, encoding="utf-8") as fh:
        linhas = json.load(fh)
    fora = {}
    for r in linhas:
        ss = str(r.get("NUMERO_SS") or "").strip()
        if ss and ss not in fora:
            d = _data(r.get("DATA_ABERTURA_SS"))
            if d:
                fora[ss] = d
    return fora


def rotulo(mes):
    ano, m = mes.split("-")
    return f"{MESES_PT[int(m) - 1]}/{ano}"


def montar(entrada):
    if not entrada:
        return None

    itens = []
    for balde in ("resolvidos", "verificar", "em_andamento"):
        for x in (entrada.get(balde) or {}).get("lista", []):
            itens.append({**x, "balde": balde})
    if not itens:
        return None

    da_planilha = _aberturas_da_planilha()
    da_base = _aberturas_da_base()

    for i in itens:
        ss = i["numero_ss"]
        d, fonte = da_planilha.get(ss), PLANILHA
        if not d:
            d, fonte = da_base.get(ss), CRUZAMENTO
        i["abertura"] = d
        i["fonte_data"] = fonte if d else "não encontrada"

    sem_data = [i for i in itens if not i["abertura"]]

    # Um ativo pode ter mais de uma SS na foto; vale a mais antiga.
    por_ativo = {}
    ss_por_ativo = defaultdict(list)
    for i in itens:
        if not i["abertura"]:
            continue
        ss_por_ativo[i["ativo"]].append(i)
        atual = por_ativo.get(i["ativo"])
        if not atual or i["abertura"] < atual["abertura"]:
            por_ativo[i["ativo"]] = i

    lista, meses = [], defaultdict(list)
    por_ano_legado = Counter()
    fonte = Counter()
    for ativo, i in sorted(por_ativo.items()):
        d = i["abertura"]
        legado = d.year < CORTE
        mes = MES_CORTE if legado else f"{d.year}-{d.month:02d}"
        if legado:
            por_ano_legado[d.year] += 1
        fonte[i["fonte_data"]] += 1
        outras = [o["numero_ss"] for o in ss_por_ativo[ativo] if o is not i]
        registro = {
            "ativo": ativo,
            "numero_ss": i["numero_ss"],
            "tipo": i.get("tipo", ""),
            "localidade": i.get("localidade", ""),
            "abertura": d.isoformat(),
            "mes": mes,
            "legado": legado,
            "resolvido": i["balde"] == "resolvidos",
            "balde": i["balde"],
            # ativo que saiu da lista de hoje não tem ficha no painel — a carta dele
            # não pode virar botão, senão o clique não faz nada.
            "na_carteira": bool(i.get("na_carteira")),
            "motivo": i.get("motivo", ""),
            "parecer_coep": i.get("parecer_coep", ""),
            "situacao_hoje": i.get("situacao_hoje", ""),
            "fonte_data": i["fonte_data"],
            "outras_ss": outras,
        }
        lista.append(registro)
        meses[mes].append(registro)

    blocos = []
    for mes in sorted(meses):
        g = meses[mes]
        resolvidos = sum(1 for x in g if x["resolvido"])
        blocos.append({
            "mes": mes,
            "rotulo": rotulo(mes),
            "qtd": len(g),
            "legado": sum(1 for x in g if x["legado"]),
            "no_mes": sum(1 for x in g if not x["legado"]),
            "resolvidos": resolvidos,
            "em_andamento": len(g) - resolvidos,
            "percentual": round(100 * resolvidos / len(g), 1) if g else 0.0,
            "ativos": [x["ativo"] for x in g],
        })

    mais_antiga = min(lista, key=lambda x: x["abertura"]) if lista else None
    total = len(lista)
    resolvidos = sum(1 for x in lista if x["resolvido"])

    return {
        "total": total,
        "total_ss": len(itens),
        "resolvidos": resolvidos,
        "em_andamento": total - resolvidos,
        "fora_da_carteira": sum(1 for x in lista if not x["na_carteira"]),
        "meses": blocos,
        "lista": sorted(lista, key=lambda x: (x["mes"], x["abertura"], x["ativo"])),
        "legado": {
            "qtd": sum(1 for x in lista if x["legado"]),
            "por_ano": [{"ano": a, "qtd": q} for a, q in sorted(por_ano_legado.items())],
            "mais_antiga": mais_antiga if mais_antiga and mais_antiga["legado"] else None,
        },
        "fonte_data": [{"fonte": f, "qtd": q} for f, q in fonte.most_common()],
        "multiplas_ss": [
            {"ativo": a, "ss": sorted(o["numero_ss"] for o in g),
             "usada": por_ativo[a]["numero_ss"]}
            for a, g in sorted(ss_por_ativo.items()) if len(g) > 1
        ],
        "sem_data": [x["numero_ss"] for x in sem_data],
        "regra": (
            "Mês da carteira de entrada = mês em que a SS foi aberta. SS aberta antes de "
            "2026 cai em janeiro de 2026, por decisão do gestor — janeiro concentra o que "
            "já era antigo quando o posto assumiu. Ativo com mais de uma SS na foto entra "
            "pela mais antiga."
        ),
    }


if __name__ == "__main__":
    with open(os.path.join(RAIZ, "data", "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    d = montar(meta.get("entrada"))
    print(f"{d['total']} ativos em {len(d['meses'])} meses "
          f"({d['resolvidos']} resolvidos, {d['em_andamento']} em andamento)")
    for b in d["meses"]:
        extra = f"  ({b['legado']} vieram de antes de 2026)" if b["legado"] else ""
        print(f"  {b['rotulo']}  {b['qtd']:>3}  resolvidos {b['resolvidos']:>3} "
              f"({b['percentual']:>5.1f}%){extra}")
    print("  legado por ano:", {x["ano"]: x["qtd"] for x in d["legado"]["por_ano"]})
    print("  origem da data:", {x["fonte"]: x["qtd"] for x in d["fonte_data"]})
    print("  ativos com mais de uma SS:", len(d["multiplas_ss"]))
