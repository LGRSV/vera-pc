"""
Lê a planilha base do COEP e devolve tudo em JSON.

«Essa é a planilha base de equipamentos especiais, tudo que tiver nela é a nova
verdade» (gestor, 28/08). Este script é a porta de entrada: cada aba vira uma
estrutura, e é dela que os artifacts passam a sair.

O que cada aba dá:
  Gestão              os 53 pendentes com a esteira de execução e o orçamento
  Orçamento           o pivô por tipo e status
  Falha Equipamentos  as 90 ocorrências com causa raiz, tensão e citação
  Base                a tabela mensal de taxa, por classe de tensão
  Resolvidos          a dinâmica disjunta dos 143
  SLA por equipe      o SLA — mas a aba está na régua ANTIGA; o número vivo sai
                      do sla_por_equipe.py, com a proposta DCMD de 11/20/40/60

Grava data/missao/base_coep.json.
Rodar: python3 scripts/base_coep.py
"""

import json
import os
from collections import Counter, defaultdict

import openpyxl

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(RAIZ, "data", "raw", "GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP.xlsx")
SAIDA = os.path.join(RAIZ, "data", "missao", "base_coep.json")

# os dez marcos da esteira, na ordem em que acontecem
ESTEIRA = ["PMA", "Entregue N1?", "Gerado Obra?", "Gerado EMD?", "Entregue N3?",
           "Concluído COCM?", "Enviado para Cadastro", "Estudo Proteção",
           "Repassado ao DMSL?", "Comissionado?"]
ROTULO_ESTEIRA = ["PMA", "Entregue N1", "Gerado obra", "Gerado EMD", "Entregue N3",
                  "Concluído COCM", "Cadastro", "Estudo de proteção",
                  "Repassado DMSL", "Comissionado"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def txt(v):
    s = "" if v is None else str(v).strip()
    return "" if s.lower() in ("none", "#n/a", "—") else s


def num(v):
    return float(v) if isinstance(v, (int, float)) else 0.0


def linhas(ws, largura):
    return list(ws.iter_rows(max_col=largura, values_only=True))


def gestao(wb):
    """Os 53 pendentes do DCMD, com a esteira marco a marco."""
    ws = wb["Gestão"]
    L = linhas(ws, 30)
    cab = [txt(c) for c in L[0]]
    col = {c: i for i, c in enumerate(cab)}
    itens = []
    for r in L[1:]:
        if not txt(r[0]):
            continue
        marcos = [{"nome": ROTULO_ESTEIRA[i], "valor": txt(r[col[m]]) if m in col else ""}
                  for i, m in enumerate(ESTEIRA)]
        itens.append({
            "ativo": txt(r[0]), "tipo": "RT" if txt(r[1]) == "58" else "RL",
            "ss": txt(r[col.get("SS SGM", 2)]),
            "criticidade": txt(r[col["Criticidade"]]) or "Falta definir",
            "status": txt(r[col["Status"]]), "defeito": txt(r[col["Defeito"]]),
            "mo": num(r[col["Orçamento MO"]]), "mat": num(r[col["Orçamento MAT"]]),
            "total": num(r[col["Orçamento Total"]]),
            "dias_pendente": int(num(r[col["Dias Pendente"]])),
            "responsavel": txt(r[col.get("Responsável", 23)]),
            "status_prazo": txt(r[col.get("Status Prazo", 24)]),
            "municipio": txt(r[col.get("Município", 27)]),
            "polo": txt(r[col.get("Polo", 28)]),
            "regional": txt(r[col.get("Regional", 29)]),
            "marcos": marcos,
            "andou": sum(1 for m in marcos if m["valor"]),
        })
    return itens


def falhas(wb):
    """As 90 ocorrências com causa raiz — o rol lido e revisado."""
    ws = wb["Falha Equipamentos"]
    L = linhas(ws, 20)
    cab = [txt(c) for c in L[0]]
    col = {c: i for i, c in enumerate(cab)}
    itens = []
    for r in L[1:]:
        if not txt(r[0]):
            continue
        itens.append({
            "fatia": txt(r[0]), "tipo": txt(r[1]), "ativo": txt(r[4]),
            "ss": txt(r[col["SS"]]), "tensao": txt(r[col["Tensão"]]) or "sem cadastro",
            "data": txt(r[col["Data"]]), "mes": txt(r[col["Mês"]]),
            "ano": txt(r[col["Ano"]]), "peca": txt(r[col["Peça (modo)"]]),
            "troca": txt(r[col["Troca feita"]]), "causa": txt(r[col["Causa raiz"]]),
            "citacao": txt(r[col["Citação do texto da SS"]]),
            "nota": txt(r[col["Nota do analista"]]),
            "revisao": txt(r[col.get("Revisão", 16)]),
        })
    return itens


def mensal(wb):
    """A série mensal de falhas por tipo e ano.

    A CONTAGEM sai da aba «Falha Equipamentos», não da aba «Base»: na Base as colunas
    de regulador ficaram vazias (a coluna rotulada «Qtd RT 13» guarda, na verdade, o
    parque 180) e só o religador está preenchido. A aba de falhas tem as 90 ocorrências
    com tipo, mês e ano — está completa e é da própria planilha.

    O PARQUE vem da aba Base quando ela traz, e do parque do gestor (base de janeiro
    mais a expansão do ano) no resto.
    """
    ws = wb["Falha Equipamentos"]
    L = linhas(ws, 20)
    col = {txt(c): i for i, c in enumerate(L[0])}
    # O ano vem da FATIA («RL 2025»), não da coluna Ano: numa das 90 as duas
    # discordam — o 7933585074 é falha de 2025 com data de ocorrência em 27/01/2026,
    # e a fatia é a atribuição que o revisor bateu. O mês vem da coluna Mês.
    conta, divergentes = Counter(), []
    for r in L[1:]:
        fatia = txt(r[0])
        if not fatia:
            continue
        tipo, ano = fatia.split()[0], fatia.split()[-1]
        mes = txt(r[col["Mês"]]).lower()
        if mes in MESES:
            conta[(tipo, ano, mes)] += 1
        if txt(r[col["Ano"]]) and txt(r[col["Ano"]]) != ano:
            divergentes.append(txt(r[4]))

    parque_base = {}
    for r in linhas(wb["Base"], 15)[1:]:
        tipo, ano, mes = txt(r[3]), txt(r[4]), txt(r[5]).lower()
        v = int(num(r[8])) if tipo == "RL" else 0
        if tipo and ano and mes and v:
            parque_base[(tipo, ano, mes)] = v

    caminho = os.path.join(RAIZ, "data", "missao", "parque_2026.json")
    expansao = {}
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as fh:
            p26 = json.load(fh)
        for t in ("RL", "RT"):
            for i, d in enumerate(p26["series"][t]):
                expansao[(t, "2026", MESES[i])] = d["parque"]
    base_jan = {"RL": 1281, "RT": 180}

    saida = {}
    for tipo in ("RL", "RT"):
        for ano in ("2025", "2026"):
            serie = []
            for mes in MESES:
                pq = (parque_base.get((tipo, ano, mes))
                      or expansao.get((tipo, ano, mes))
                      or (serie[-1]["parque"] if serie else base_jan[tipo]))
                serie.append({"mes": mes, "falhas": conta[(tipo, ano, mes)], "parque": pq})
            saida[f"{tipo}|{ano}"] = serie
    saida["_divergentes"] = divergentes
    return saida


def resolvidos(wb):
    """A dinâmica disjunta dos 143 — o cabeçalho traz as três contas."""
    ws = wb["Resolvidos"]
    L = linhas(ws, 18)
    contas = {}
    inicio = None
    for i, r in enumerate(L):
        if txt(r[0]) == "Situação":
            inicio = i
            break
        if txt(r[0]) and isinstance(r[1], (int, float)):
            contas[txt(r[0])] = int(r[1])
    cab = [txt(c) for c in L[inicio]]
    col = {c: i for i, c in enumerate(cab)}
    itens = []
    for r in L[inicio + 1:]:
        if not txt(r[0]):
            continue
        itens.append({
            "situacao": txt(r[0]), "ativo": txt(r[1]), "tipo": txt(r[2]),
            "localidade": txt(r[3]), "criticidade": txt(r[4]) or "Falta definir",
            "ss": txt(r[5]), "desde": txt(r[col.get("Desde", 8)]),
            "ano": txt(r[col.get("Ano", 9)]),
            "dias": int(num(r[col.get("Dias", 10)])),
            "voltou": bool(txt(r[col.get("Resolveu e voltou", 11)])),
            "como_terminou": txt(r[col.get("Como terminou", 12)]),
            "posto_que_fechou": txt(r[col.get("Posto que fechou", 13)]),
            "realizado_dcmd": bool(txt(r[col.get("Realizado DCMD", 14)])),
            "onde_esta": txt(r[col.get("Onde está", 15)]),
            "etapa": txt(r[col.get("Etapa", 16)]),
        })
    return contas, itens


def montar():
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    g = gestao(wb)
    f = falhas(wb)
    contas, r = resolvidos(wb)
    pacote = {
        "fonte": "GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP.xlsx — a planilha base do gestor "
                 "(28/08): «tudo que tiver nela é a nova verdade»",
        "gestao": {
            "qtd": len(g),
            "orcamento_total": round(sum(x["total"] for x in g), 2),
            "por_status": dict(Counter(x["status"] for x in g).most_common()),
            "por_criticidade": dict(Counter(x["criticidade"] for x in g).most_common()),
            "por_tipo": dict(Counter(x["tipo"] for x in g)),
            "por_defeito": dict(Counter(x["defeito"] for x in g).most_common(12)),
            "marcos": ROTULO_ESTEIRA,
            "marcos_preenchidos": {
                nome: sum(1 for x in g if x["marcos"][i]["valor"])
                for i, nome in enumerate(ROTULO_ESTEIRA)},
            "ativos": sorted(g, key=lambda x: (-x["dias_pendente"], x["ativo"])),
        },
        "falhas": {
            "qtd": len(f),
            "por_fatia": dict(Counter(x["fatia"] for x in f)),
            "por_causa": dict(Counter(x["causa"] for x in f).most_common()),
            "por_tensao": dict(Counter(x["tensao"] for x in f).most_common()),
            "por_peca": dict(Counter(x["peca"] for x in f).most_common()),
            "causa_por_fatia": {
                fatia: dict(Counter(x["causa"] for x in f if x["fatia"] == fatia)
                            .most_common())
                for fatia in sorted({x["fatia"] for x in f})},
            "itens": f,
        },
        "mensal": {k: v for k, v in mensal(wb).items() if not k.startswith("_")},
        "resolvidos": {"contas": contas, "itens": r,
                       "por_situacao": dict(Counter(x["situacao"] for x in r)),
                       "por_tipo": dict(Counter(x["tipo"] for x in r))},
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar()
    g = p["gestao"]
    print(f"gravado: {SAIDA}")
    print(f"  Gestão: {g['qtd']} ativos · R$ {g['orcamento_total']:,.2f}")
    print(f"    status: {g['por_status']}")
    print(f"    criticidade: {g['por_criticidade']}")
    print(f"    marcos preenchidos: {g['marcos_preenchidos']}")
    print(f"  Falhas: {p['falhas']['qtd']} · {p['falhas']['por_fatia']}")
    print(f"    tensão: {p['falhas']['por_tensao']}")
    print(f"  Resolvidos: {p['resolvidos']['contas']} · {p['resolvidos']['por_situacao']}")
    print(f"  Mensal: {list(p['mensal'])}")
