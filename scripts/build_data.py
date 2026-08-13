#!/usr/bin/env python3
"""
Gera os JSONs que alimentam o site de Equipamentos Especiais.

Entradas
  data/raw/equipamentos_especiais.csv   planilha exportada (aba Criticidade por Equipamento)
  data/raw/obras_eq_especial.csv        planilha de EMD (requisição de material)
  data/analise_ia/result_*.json         categorização das descrições de SS (10 lotes)

Saídas
  data/equipamentos.json      registro consolidado por ativo
  data/alertas_coep.json      pendências do Parecer COEP (o que já deveria estar concluído)
  data/divergencias_emd.json  divergências entre o EMD e a planilha de criticidade
  data/meta.json              agregados usados no painel

Uso:  python3 scripts/build_data.py
"""

import csv
import datetime
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conclusoes import montar as montar_conclusoes  # noqa: E402
from cruzamento_emd import cruzar, ler_emd  # noqa: E402
from acompanhamento import montar as montar_acompanhamento  # noqa: E402
from entrada import montar as montar_entrada  # noqa: E402
from gestao_equipamentos import carregar as carregar_gestao  # noqa: E402
from missao import anotar_registros, carregar as carregar_missao, enxugar  # noqa: E402
from obra_cruzada import montar as montar_obra_cruzada  # noqa: E402
from plano_compras import conferir, ler_plano, montar_resumo  # noqa: E402
from demandas import montar as montar_demandas  # noqa: E402
from realizadas import montar as montar_realizadas  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_ENTRADA = os.path.join(RAIZ, "data", "raw", "equipamentos_especiais.csv")
DIR_ANALISE = os.path.join(RAIZ, "data", "analise_ia")
DIR_SAIDA = os.path.join(RAIZ, "data")

# Data de referência da análise. As previsões da planilha vêm só como dd/mm.
DATA_REF = datetime.date(2026, 8, 12)

TIPO_EQUIPAMENTO = {"79": "Religador", "58": "Regulador de Tensão"}

ORDEM_CRITICIDADE = ["Muito Alta", "Alta", "Média", "Baixa", "Sem classificação"]
ORDEM_GRAVIDADE = ["Crítica", "Alta", "Média", "Baixa"]


def limpo(valor):
    return (valor or "").strip()


def concluida(registro):
    return "CONCLU" in registro["ss"].upper()


def ler_planilha():
    """Lê o CSV e devolve um registro por ativo, na ordem original da planilha."""
    with open(CSV_ENTRADA, encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh, delimiter=";"))

    registros = []
    for indice, linha in enumerate(linhas):
        ativo = limpo(linha.get("Ativo"))
        if not ativo:
            continue  # rodapé da planilha

        premissas = {}
        for n in range(1, 9):
            bruto = limpo(linha.get(f"Premissa {n}"))
            premissas[f"P{n}"] = None if bruto in ("", "-") else int(bruto)

        tipo = limpo(linha.get("Tipo"))
        registros.append(
            {
                "linha_planilha": indice + 2,
                "ativo": ativo,
                "tipo": tipo,
                "tipo_nome": TIPO_EQUIPAMENTO.get(tipo, "Não informado"),
                "localidade": limpo(linha.get("Localidade")),
                "polo": limpo(linha.get("Polo")),
                "regional": limpo(linha.get("Regional")),
                "ss": limpo(linha.get("SS aberta")),
                "parecer_coep": limpo(linha.get("Parecer COEP")),
                "observacao": limpo(linha.get("Observação")),
                "check": limpo(linha.get("Check de concluídas")),
                "defeito_planilha": limpo(linha.get("Defeito identificado")),
                "quantidade": limpo(linha.get("Quantidade")),
                "descricao_ss": limpo(linha.get("Descrição SS")),
                "premissas": premissas,
                "priorizacao": int(limpo(linha.get("Priorização")) or 0),
                "criticidade": limpo(linha.get("Criticidade")) or "Sem classificação",
                "obs_analise": limpo(linha.get("Observação após análise")),
            }
        )
    return registros


def ler_categorizacao():
    """Junta os 10 lotes de categorização das descrições de SS, indexados por ativo."""
    por_ativo = {}
    arquivos = sorted(glob.glob(os.path.join(DIR_ANALISE, "result_*.json")))
    for caminho in arquivos:
        with open(caminho, encoding="utf-8") as fh:
            for item in json.load(fh):
                por_ativo[str(item["ativo"]).strip()] = item
    return por_ativo, len(arquivos)


def ano_da_ss(ss):
    achado = re.search(r"/(\d{4})$", ss)
    return int(achado.group(1)) if achado else None


def dataBR(iso):
    ano, mes, dia = str(iso)[:10].split("-")
    return f"{dia}/{mes}/{ano}"


def previsao_da_observacao(observacao):
    """Extrai a data prometida no campo Observação (vem como dd/mm, sem ano)."""
    achado = re.search(r"(\d{1,2})/(\d{1,2})", observacao)
    if not achado:
        return None
    dia, mes = int(achado.group(1)), int(achado.group(2))
    try:
        return datetime.date(DATA_REF.year, mes, dia)
    except ValueError:
        return None


def montar_alertas(registros):
    """Análise 2 — Parecer COEP: o que já deveria estar concluído e não está."""
    alertas = []

    def registrar(reg, tipo, gravidade, detalhe, dias=None):
        alertas.append(
            {
                "ativo": reg["ativo"],
                "linha_planilha": reg["linha_planilha"],
                "localidade": reg["localidade"],
                "polo": reg["polo"],
                "regional": reg["regional"],
                "ss": reg["ss"],
                "criticidade": reg["criticidade"],
                "parecer_coep": reg["parecer_coep"],
                "check": reg["check"],
                "observacao": reg["observacao"],
                "tipo_alerta": tipo,
                "gravidade": gravidade,
                "detalhe": detalhe,
                "dias_atraso": dias,
            }
        )

    for reg in registros:
        prevista = previsao_da_observacao(reg["observacao"])
        if prevista and prevista < DATA_REF and reg["check"] != "Ok":
            registrar(
                reg,
                "Prazo de previsão vencido",
                "Alta",
                f"Previsão registrada para {prevista.strftime('%d/%m/%Y')} "
                f"(«{reg['observacao']}») e nada indica conclusão.",
                (DATA_REF - prevista).days,
            )

        if concluida(reg) and (
            reg["parecer_coep"] or reg["check"] not in ("Ok", "Desmobilizado", "")
        ):
            registrar(
                reg,
                "SS fechada com pendência aberta",
                "Alta",
                f"SS marcada como CONCLUÍDA, mas o Parecer COEP é "
                f"«{reg['parecer_coep'] or '—'}» e o Check é «{reg['check'] or '—'}».",
            )

        if "Conclu" in reg["parecer_coep"] and reg["check"] != "Ok":
            registrar(
                reg,
                "Concluído pelo COEP, não fechado",
                "Média",
                f"Parecer COEP «{reg['parecer_coep']}», porém o Check segue "
                f"«{reg['check'] or '—'}». Pendência: {reg['observacao'] or '—'}.",
            )

        ano = ano_da_ss(reg["ss"])
        if ano and ano < DATA_REF.year and not concluida(reg):
            abertura = reg.get("ss_sgm", {}).get("data_abertura")
            if abertura:
                # A planilha de gestão traz a data real de abertura.
                dias = reg["ss_sgm"]["dias_aberta"]
                quanto = f"aberta em {dataBR(abertura)} — {dias} dias em aberto"
            else:
                # Sem data real, a numeração só dá o ano: conta-se pelo piso,
                # a partir de 31/12 do ano da SS (o caso mais recente possível).
                meses = (DATA_REF - datetime.date(ano, 12, 31)).days // 30
                quanto = f"aberta em {ano} — no mínimo {meses} meses em aberto"
            registrar(
                reg,
                f"SS de {ano} ainda aberta",
                "Crítica",
                f"SS {reg['ss']} {quanto}, sem conclusão. "
                f"Situação COEP: «{reg['parecer_coep'] or '—'}».",
            )

        # Prazo-limite da própria SS no sistema, quando a planilha de gestão o traz.
        dados_ss = reg.get("ss_sgm") or {}
        if dados_ss.get("sla_estourado") and not concluida(reg):
            registrar(
                reg,
                "Prazo-limite da SS estourado",
                "Alta",
                f"A SS {dados_ss['numero'] or reg['ss']} ({dados_ss.get('criticidade_ss') or 'sem classe'}) "
                f"tinha prazo-limite em {dataBR(dados_ss['data_limite'])} e segue "
                f"«{dados_ss.get('situacao') or 'pendente'}» — "
                f"{dados_ss['dias_sla']} dias além do prazo do sistema.",
                dados_ss["dias_sla"],
            )

        if "ubstitu" in reg["parecer_coep"] and "laudo" in reg["parecer_coep"].lower():
            registrar(
                reg,
                "Substituído, pendente laudo",
                "Média",
                f"«{reg['parecer_coep']}» — equipamento já trocado em campo; "
                f"falta o laudo da empreiteira para encerrar a SS.",
            )

    alertas.sort(
        key=lambda a: (
            ORDEM_GRAVIDADE.index(a["gravidade"]),
            -(a["dias_atraso"] or 0),
            ORDEM_CRITICIDADE.index(a["criticidade"]),
        )
    )
    return alertas


def contar(registros, campo, ordem=None):
    contagem = Counter(reg[campo] or "Não informado" for reg in registros)
    itens = [{"rotulo": k, "total": v} for k, v in contagem.items()]
    if ordem:
        itens.sort(key=lambda i: ordem.index(i["rotulo"]) if i["rotulo"] in ordem else 99)
    else:
        itens.sort(key=lambda i: -i["total"])
    return itens


def montar_meta(registros, alertas, divergencias, emd_por_ativo, lotes):
    abertos = [r for r in registros if not concluida(r)]
    categorias = Counter(
        r["analise"]["categoria_primaria"]
        for r in registros
        if r.get("analise", {}).get("categoria_primaria")
    )
    responsaveis = Counter(
        r["analise"]["responsavel_atual"]
        for r in registros
        if r.get("analise", {}).get("responsavel_atual")
    )
    status_op = Counter(
        r["analise"]["status_operacional"]
        for r in registros
        if r.get("analise", {}).get("status_operacional")
    )

    matriz = defaultdict(Counter)
    for reg in registros:
        cat = reg.get("analise", {}).get("categoria_primaria")
        if cat:
            matriz[cat][reg["criticidade"]] += 1

    em_aquisicao = [r for r in registros if "aquisi" in r["parecer_coep"].lower()]

    return {
        "gerado_em": DATA_REF.isoformat(),
        "total_equipamentos": len(registros),
        "total_abertos": len(abertos),
        "total_concluidos": len(registros) - len(abertos),
        "total_com_descricao": sum(1 for r in registros if r["descricao_ss"]),
        "lotes_analisados": lotes,
        "total_alertas": len(alertas),
        "equipamentos_com_alerta": len({a["ativo"] for a in alertas}),
        "total_emd": len(emd_por_ativo),
        "total_divergencias": len(divergencias),
        "equipamentos_com_divergencia": len({d["ativo"] for d in divergencias}),
        "em_aquisicao": len(em_aquisicao),
        "em_aquisicao_sem_emd": sum(1 for r in em_aquisicao if r["ativo"] not in emd_por_ativo),
        "abertos_sem_emd": sum(1 for r in abertos if r["ativo"] not in emd_por_ativo),
        "por_divergencia": [
            {"rotulo": k, "total": v}
            for k, v in Counter(d["tipo"] for d in divergencias).most_common()
        ],
        "por_criticidade": contar(registros, "criticidade", ORDEM_CRITICIDADE),
        "por_regional": contar(registros, "regional"),
        "por_polo": contar(registros, "polo"),
        "por_tipo": contar(registros, "tipo_nome"),
        "por_categoria": [
            {"rotulo": k, "total": v} for k, v in categorias.most_common()
        ],
        "por_responsavel": [
            {"rotulo": k, "total": v} for k, v in responsaveis.most_common()
        ],
        "por_status_operacional": [
            {"rotulo": k, "total": v} for k, v in status_op.most_common()
        ],
        "por_alerta": [
            {"rotulo": k, "total": v}
            for k, v in Counter(a["tipo_alerta"] for a in alertas).most_common()
        ],
        "matriz_categoria_criticidade": [
            {"categoria": cat, **{c: linha.get(c, 0) for c in ORDEM_CRITICIDADE}}
            for cat, linha in sorted(matriz.items(), key=lambda i: -sum(i[1].values()))
        ],
    }


def validar(registros, categorizacao):
    """Barreiras que impedem publicar um dataset silenciosamente quebrado."""
    problemas = []

    ativos = [r["ativo"] for r in registros]
    duplicados = [a for a, n in Counter(ativos).items() if n > 1]
    if duplicados:
        problemas.append(f"ativos duplicados: {duplicados}")

    fora_padrao = [a for a in ativos if not re.fullmatch(r"\d{10}", a)]
    if fora_padrao:
        problemas.append(f"ativo fora do padrão de 10 dígitos: {fora_padrao}")

    prefixo = [
        r["ativo"] for r in registros if r["tipo"] and r["ativo"][:2] != r["tipo"]
    ]
    if prefixo:
        problemas.append(f"prefixo do ativo diverge do tipo: {prefixo}")

    ss_abertas = [r["ss"] for r in registros if r["ss"] and not concluida(r)]
    ss_ruins = [
        s
        for s in ss_abertas
        if not re.fullmatch(r"[A-Z]{2,3}-[A-Z]{2,4}(-[A-Z]{2})? \d{5}/\d{4}", s)
    ]
    if ss_ruins:
        problemas.append(f"SS fora do padrão: {ss_ruins}")

    duplicadas = [s for s, n in Counter(ss_abertas).items() if n > 1]
    if duplicadas:
        problemas.append(f"SS duplicadas: {duplicadas}")

    com_descricao = {r["ativo"] for r in registros if r["descricao_ss"]}
    faltando = com_descricao - set(categorizacao)
    if faltando:
        problemas.append(f"descrições sem categorização: {sorted(faltando)}")

    sobrando = set(categorizacao) - com_descricao
    if sobrando:
        problemas.append(f"categorização sem registro correspondente: {sorted(sobrando)}")

    return problemas


def main():
    registros = ler_planilha()
    categorizacao, lotes = ler_categorizacao()

    for reg in registros:
        analise = categorizacao.get(reg["ativo"])
        if analise:
            reg["analise"] = {
                k: v for k, v in analise.items() if k not in ("ativo", "linha", "ss")
            }

    problemas = validar(registros, categorizacao)
    if problemas:
        print("Falhas de validação:")
        for p in problemas:
            print("  -", p)
        raise SystemExit(1)

    gestao, resumo_gestao = carregar_gestao({r["ativo"] for r in registros})
    for reg in registros:
        extra = gestao.get(reg["ativo"])
        if not extra:
            continue
        if extra.get("geo"):
            reg["geo"] = extra["geo"]
        if extra.get("ss"):
            reg["ss_sgm"] = extra["ss"]
        if extra.get("gestao"):
            reg["gestao"] = extra["gestao"]
        if extra.get("especificacao"):
            reg["especificacao"] = extra["especificacao"]

    alertas = montar_alertas(registros)
    divergencias, emd_por_ativo = cruzar(registros, ler_emd())
    itens_compra = ler_plano()
    achados_compra = conferir(itens_compra, registros, emd_por_ativo)
    meta = montar_meta(registros, alertas, divergencias, emd_por_ativo, lotes)
    meta["compras"] = montar_resumo(itens_compra, achados_compra, emd_por_ativo)
    meta["gestao"] = resumo_gestao
    pacote_missao = carregar_missao()
    anotar_registros(registros, pacote_missao)
    meta["missao"] = enxugar(pacote_missao)
    meta["conclusao"] = montar_conclusoes(registros)
    meta["demandas"] = montar_demandas(registros)
    meta["realizadas"] = montar_realizadas(registros)
    meta["obra_cruzada"] = montar_obra_cruzada(registros)
    entrada = montar_entrada(registros)
    if entrada:
        meta["entrada"] = entrada
    meta["acompanhamento"] = montar_acompanhamento(registros, entrada)

    ativos_com_alerta = {a["ativo"] for a in alertas}
    ativos_com_divergencia = {d["ativo"] for d in divergencias}
    ativos_no_plano = {i["Ativo"] for i in itens_compra}
    for reg in registros:
        reg["tem_alerta"] = reg["ativo"] in ativos_com_alerta
        reg["tem_divergencia"] = reg["ativo"] in ativos_com_divergencia
        reg["no_plano_compras"] = reg["ativo"] in ativos_no_plano
        emd = emd_por_ativo.get(reg["ativo"])
        if emd:
            reg["emd"] = {k: v for k, v in emd.items() if v}
        itens = [i for i in itens_compra if i["Ativo"] == reg["ativo"]]
        if itens:
            reg["compras"] = [
                {
                    "material": i["Material"].split(" · ")[-1].strip(),
                    "codigo": i["Código"],
                    "qtd": i["qtd"],
                    "valor_total": i["valor_total"],
                    "data_limite": i["data_limite"],
                    "dias_restantes": i["dias_restantes"],
                    "prazo_dias": i["prazo_dias"],
                }
                for i in itens
            ]

    for nome, conteudo in (
        ("equipamentos.json", registros),
        ("alertas_coep.json", alertas),
        ("divergencias_emd.json", divergencias),
        ("plano_compras.json", achados_compra),
        ("meta.json", meta),
    ):
        destino = os.path.join(DIR_SAIDA, nome)
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(conteudo, fh, ensure_ascii=False, separators=(",", ":"))
        print(f"  {nome}: {os.path.getsize(destino) / 1024:.1f} KB")

    print(
        f"OK — {meta['total_equipamentos']} equipamentos, "
        f"{meta['total_com_descricao']} descrições categorizadas em {lotes} lotes, "
        f"{meta['total_alertas']} alertas COEP, "
        f"{meta['total_divergencias']} divergências contra {meta['total_emd']} linhas de EMD."
    )


if __name__ == "__main__":
    main()
