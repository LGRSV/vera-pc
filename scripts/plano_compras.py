"""
Plano de compras pedido em 17/07/2026 — prazos contratuais e conferência
contra a planilha de criticidade e a planilha de EMD.

Prazos acordados, contados a partir da data do pedido:
  Religador (RL)          120 dias  ->  14/11/2026
  Regulador de Tensão (RT) 180 dias ->  13/01/2027
"""

import csv
import datetime
import os
import re
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PLANO = os.path.join(RAIZ, "data", "raw", "plano_compras.csv")

DATA_PEDIDO = datetime.date(2026, 7, 17)
DATA_REF = datetime.date(2026, 8, 12)
PRAZO_DIAS = {"Religador": 120, "Regulador": 180}

ORDEM_CRITICIDADE = ["Muito Alta", "Alta", "Média", "Baixa", "Sem classificação"]

GRAVIDADE = {
    "Compra possivelmente desnecessária": "Crítica",
    "Comprado sem requisição de EMD": "Alta",
    "Status do plano desatualizado": "Média",
    "SS divergente no plano": "Baixa",
}


def normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").upper())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9]", "", texto)


def normalizar_ss(ss):
    if not ss:
        return ""
    limpo = ss.upper().replace("SS ", "").strip()
    achado = re.search(r"([A-Z]+-[A-Z]+(?:-[A-Z]+)?)\s*0*(\d+)/(\d{4})", limpo)
    return f"{achado.group(1)}-{int(achado.group(2))}/{achado.group(3)}" if achado else limpo


def moeda(valor):
    """R$ no formato brasileiro. Formata só o número — nunca o texto ao redor."""
    inteiro, centavos = f"{valor:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def prazo_de(tipo):
    """Data limite de entrega para o tipo de equipamento."""
    dias = PRAZO_DIAS.get(tipo, 120)
    return DATA_PEDIDO + datetime.timedelta(days=dias), dias


def ler_plano():
    with open(CSV_PLANO, encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh, delimiter=";"))

    itens = []
    for linha in linhas:
        registro = {k: (v or "").strip() for k, v in linha.items()}
        if not registro.get("Ativo"):
            continue
        limite, dias = prazo_de(registro["Tipo"])
        registro["qtd"] = int(float(registro["Qtd"] or 0))
        registro["valor_unitario"] = float(registro["Valor Unitário"] or 0)
        registro["valor_total"] = float(registro["Valor Total"] or 0)
        registro["prazo_dias"] = dias
        registro["data_limite"] = limite.isoformat()
        registro["dias_restantes"] = (limite - DATA_REF).days
        registro["dias_decorridos"] = (DATA_REF - DATA_PEDIDO).days
        itens.append(registro)
    return itens


def conferir(itens, registros_criticidade, emd_por_ativo):
    """Compara o plano com o estado atual da SS e com a existência de EMD."""
    por_ativo = {r["ativo"]: r for r in registros_criticidade}
    achados = []

    # Sinais de que o equipamento foi resolvido depois do pedido de 17/07.
    def resolvido_apos_pedido(crit):
        parecer = crit["parecer_coep"]
        if re.search(r"substitu[ií]do|conclu[ií]d", parecer, re.I):
            achado = re.search(r"(\d{1,2})/(\d{1,2})", parecer)
            if achado:
                try:
                    data = datetime.date(2026, int(achado.group(2)), int(achado.group(1)))
                except ValueError:
                    return parecer, None
                return parecer, data
            return parecer, None
        return None, None

    ativos = sorted({i["Ativo"] for i in itens})
    for ativo in ativos:
        crit = por_ativo.get(ativo)
        if not crit:
            continue
        do_ativo = [i for i in itens if i["Ativo"] == ativo]
        valor = sum(i["valor_total"] for i in do_ativo)
        materiais = ", ".join(sorted({i["Material"].split(" · ")[-1].strip() for i in do_ativo}))

        def registrar(tipo, detalhe, extra=None):
            achados.append({
                "ativo": ativo,
                "localidade": crit["localidade"],
                "polo": crit["polo"],
                "regional": crit["regional"],
                "criticidade": crit["criticidade"],
                "tipo": tipo,
                "gravidade": GRAVIDADE[tipo],
                "valor_envolvido": round(valor, 2),
                "materiais": materiais,
                "detalhe": detalhe,
                **(extra or {}),
            })

        parecer, data_conclusao = resolvido_apos_pedido(crit)
        if parecer:
            quando = (
                f" em {data_conclusao.strftime('%d/%m/%Y')}, "
                f"{'depois' if data_conclusao > DATA_PEDIDO else 'antes'} do pedido"
                if data_conclusao else ""
            )
            registrar(
                "Compra possivelmente desnecessária",
                f"O plano pediu {materiais} ({moeda(valor)}), mas o Parecer COEP já registra "
                f"«{parecer}»{quando}. Vale confirmar com o COCM antes de a compra avançar — "
                f"se o equipamento já foi trocado, o material vira sobressalente.",
            )

        if ativo not in emd_por_ativo:
            registrar(
                "Comprado sem requisição de EMD",
                f"O ativo entrou no plano de compras ({moeda(valor)}) mas não tem linha na "
                f"planilha de EMD. A compra foi pedida sem a requisição formal correspondente "
                f"no arquivo analisado.",
            )

        status_plano = do_ativo[0]["Status"]
        if status_plano and normalizar(status_plano) != normalizar(crit["parecer_coep"]):
            registrar(
                "Status do plano desatualizado",
                f"O plano registra «{status_plano}» e o Parecer COEP atual é "
                f"«{crit['parecer_coep'] or '—'}». O plano é uma foto de 17/07/2026.",
            )

        ss_plano = do_ativo[0]["SS"]
        if ss_plano and normalizar_ss(ss_plano) != normalizar_ss(crit["ss"]):
            registrar(
                "SS divergente no plano",
                f"O plano cita a SS {ss_plano} e a planilha de criticidade a SS {crit['ss']} "
                f"para o mesmo ativo.",
            )

    achados.sort(key=lambda a: (
        ["Crítica", "Alta", "Média", "Baixa"].index(a["gravidade"]),
        -a["valor_envolvido"],
    ))
    return achados


def montar_resumo(itens, achados, emd_por_ativo):
    ativos = {i["Ativo"] for i in itens}
    por_material = {}
    for item in itens:
        chave = item["Código"]
        alvo = por_material.setdefault(chave, {
            "codigo": chave,
            "descricao": item["Material"].split(" · ")[-1].strip(),
            "tipo": item["Tipo"],
            "qtd": 0,
            "valor_unitario": item["valor_unitario"],
            "valor_total": 0.0,
        })
        alvo["qtd"] += item["qtd"]
        alvo["valor_total"] += item["valor_total"]

    prazos = {}
    for tipo, dias in PRAZO_DIAS.items():
        limite = DATA_PEDIDO + datetime.timedelta(days=dias)
        do_tipo = [i for i in itens if i["Tipo"] == tipo]
        prazos[tipo] = {
            "prazo_dias": dias,
            "data_limite": limite.isoformat(),
            "dias_restantes": (limite - DATA_REF).days,
            "itens": len(do_tipo),
            "pecas": sum(i["qtd"] for i in do_tipo),
            "valor": round(sum(i["valor_total"] for i in do_tipo), 2),
        }

    return {
        "data_pedido": DATA_PEDIDO.isoformat(),
        "dias_decorridos": (DATA_REF - DATA_PEDIDO).days,
        "total_itens": len(itens),
        "total_pecas": sum(i["qtd"] for i in itens),
        "total_ativos": len(ativos),
        "valor_total": round(sum(i["valor_total"] for i in itens), 2),
        "ativos_sem_emd": sum(1 for a in ativos if a not in emd_por_ativo),
        "total_achados": len(achados),
        "valor_em_revisao": round(
            sum(a["valor_envolvido"] for a in achados
                if a["tipo"] == "Compra possivelmente desnecessária"), 2),
        "prazos": prazos,
        "por_material": sorted(por_material.values(), key=lambda m: -m["valor_total"]),
        "por_tipo": [
            {"rotulo": tipo, "total": sum(i["qtd"] for i in itens if i["Tipo"] == tipo)}
            for tipo in PRAZO_DIAS
        ],
        "por_achado": [
            {"rotulo": tipo, "total": sum(1 for a in achados if a["tipo"] == tipo)}
            for tipo in GRAVIDADE
            if any(a["tipo"] == tipo for a in achados)
        ],
    }
