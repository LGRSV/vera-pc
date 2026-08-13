#!/usr/bin/env python3
"""
Gera a página da dinâmica do posto — arquivo único, sem requisição de rede.

É um recorte só: onde cada equipamento está hoje, pelo parecer COEP da aba
«Criticidade por Equipamento Joa» da ATUALIZADA7, com o valor previsto da
planilha de gestão do Allan quando o ativo está lá.

Uso:  python3 scripts/build_dinamica.py [destino.html]
"""

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "dist", "dinamica-posto.html")

TOM = {
    "Concluído": "bom",
    "Cancelada em operação": "bom",
    "Em ajustes": "bom",
    "Aguardando comissionamento": "bom",
    "Entregue ao COCM": "atento",
    "Em logística": "atento",
    "Em compra": "critico",
    "Com o DMSL": "",
    "Travado": "critico",
    "Desmobilizado": "",
    "Outros": "",
    "Sem parecer": "",
}


def ler(*p):
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def moeda(v):
    inteiro, centavos = f"{v:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def main():
    destino = sys.argv[1] if len(sys.argv) > 1 else DESTINO
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(os.path.join(RAIZ, "data", "raw", "dinamica_joa.json"), encoding="utf-8") as fh:
        d = json.load(fh)

    # Ajustes ativo a ativo que o gestor manda: o que trocar e quanto vale.
    # A planilha de gestão só cobre 65 dos 129, então é aqui que entra o resto.
    arq = os.path.join(RAIZ, "data", "raw", "ajustes_dinamica.json")
    if os.path.exists(arq):
        with open(arq, encoding="utf-8") as fh:
            ajustes = {a["ativo"]: a for a in json.load(fh)}
        d["ajustes"] = list(ajustes.values())
        for item in d["lista"]:
            a = ajustes.get(item["ativo"])
            if not a:
                continue
            item["valor"] = a["valor"]
            item["o_que_trocar"] = a["o_que_trocar"]
            item["ajuste_do_gestor"] = a["motivo"]
        # os agregados precisam refletir o ajuste
        por = {}
        for item in d["lista"]:
            e = por.setdefault(item["etapa"], {"etapa": item["etapa"], "qtd": 0, "valor": 0.0, "ativos": []})
            e["qtd"] += 1
            e["valor"] = round(e["valor"] + item["valor"], 2)
            e["ativos"].append(item["ativo"])
        ordem = [e["etapa"] for e in d["por_etapa"]]
        d["por_etapa"] = [por[e] for e in ordem if e in por]
        for m in d["matriz"]:
            g = [i for i in d["lista"] if i["etapa"] == m["etapa"] and i["criticidade"] == m["criticidade"]]
            m["valor"] = round(sum(i["valor"] for i in g), 2)
        feitos = [i for i in d["lista"] if i["etapa"] in d["feito"]["etapas"]]
        d["feito"]["valor"] = round(sum(i["valor"] for i in feitos), 2)
        d["com_valor"] = sum(1 for i in d["lista"] if i["valor"] > 0)
        d["valor_total"] = round(sum(i["valor"] for i in d["lista"]), 2)

    # Cancelado em operacao nao consome orcamento: o valor nao entra em nenhuma soma.
    # Ele vira "valor evitado" — o que teria sido gasto se a SS nao tivesse caido.
    # Reporte de campo entregue: a planilha pede «Construir Reporte» em vários ativos,
    # e o reporte é a prova mais forte que existe. Marca quem já tem, com quantas fotos.
    arq_rep = os.path.join(RAIZ, "data", "raw", "reportes_campo.json")
    if os.path.exists(arq_rep):
        with open(arq_rep, encoding="utf-8") as fh:
            reportes = json.load(fh)
        por_ativo = {}
        for r in reportes:
            e = por_ativo.setdefault(r["ativo"], {"qtd": 0, "fotos": 0, "data": ""})
            e["qtd"] += 1
            e["fotos"] += r["anexo"]["fotos"] if r.get("anexo") else bool(r.get("imagem"))
            e["data"] = max(e["data"], r.get("data", ""))
        for item in d["lista"]:
            r = por_ativo.get(item["ativo"])
            if r:
                item["reporte_campo"] = r
        d["com_reporte"] = sum(1 for i in d["lista"] if i.get("reporte_campo"))

        # As fotos entram como data URI: a página é um arquivo só e não busca nada
        # na rede. São ~1,7 MB, o preço de ter a prova junto do número.
        imagens = {}
        arq_img = os.path.join(RAIZ, "data", "reportes_imagens.json")
        if os.path.exists(arq_img):
            with open(arq_img, encoding="utf-8") as fh:
                imagens = json.load(fh)
        onde = {i["ativo"]: i for i in d["lista"]}
        d["reportes"] = {
            "total": len(reportes),
            "ativos": sorted(por_ativo),
            "fotos": sum(r["anexo"]["fotos"] if r.get("anexo") else bool(r.get("imagem"))
                         for r in reportes),
            "lista": [{**r,
                       "localidade_carteira": onde.get(r["ativo"], {}).get("localidade", ""),
                       "etapa": onde.get(r["ativo"], {}).get("etapa", "")}
                      for r in sorted(reportes, key=lambda x: (x.get("data", ""), x["ativo"]),
                                      reverse=True)],
            "imagens": {k: v for k, v in imagens.items()},
        }

    # O valor evitado de cada cancelado vem de scripts/economia_cancelados.py, que
    # o monta peça a peça na convenção material + mão de obra. Se algum ativo ainda
    # não tiver passado por lá, cai no valor da planilha de gestão.
    EVITADA = "Cancelada em operação"
    evitado = 0.0
    for item in d["lista"]:
        if item["etapa"] == EVITADA:
            item["valor_evitado"] = item.get("valor_evitado") or item["valor"]
            evitado += item["valor_evitado"]
            item["valor"] = 0.0
    for e in d["por_etapa"]:
        if e["etapa"] == EVITADA:
            e["valor_evitado"] = round(e["valor"], 2)
            e["valor"] = 0.0
    for m in d["matriz"]:
        if m["etapa"] == EVITADA:
            m["valor_evitado"] = m["valor"]
            m["valor"] = 0.0
    # o evitado inclui a estimativa dos que nao tem valor orcado, senao a escada
    # mostra um numero menor do que o do topo da pagina
    evitado = sum(i.get("valor_evitado", 0) for i in d["lista"])
    for e in d["por_etapa"]:
        if e["etapa"] == EVITADA:
            e["valor_evitado"] = round(evitado, 2)
    for m in d["matriz"]:
        if m["etapa"] == EVITADA:
            g = [i for i in d["lista"] if i["etapa"] == EVITADA and i["criticidade"] == m["criticidade"]]
            m["valor_evitado"] = round(sum(i.get("valor_evitado", 0) for i in g), 2)
    d["valor_evitado_total"] = round(evitado, 2)
    d["valor_total"] = round(sum(i["valor"] for i in d["lista"]), 2)
    d["com_valor"] = sum(1 for i in d["lista"] if i["valor"] > 0)
    feitos = [i for i in d["lista"] if i["etapa"] in d["feito"]["etapas"]]
    d["feito"]["valor"] = round(sum(i["valor"] for i in feitos), 2)

    # A entrada do posto mês a mês vem pronta do build principal: as três colunas
    # (estoque herdado, entrantes e tratativas) e as tabelas que as sustentam.
    arq = os.path.join(RAIZ, "data", "meta.json")
    if os.path.exists(arq):
        with open(arq, encoding="utf-8") as fh:
            mm = json.load(fh).get("entrada_mensal") or {}
        if mm.get("curva"):
            d["mes_a_mes"] = {
                "total": mm["total"],
                "recorte": mm.get("recorte", ""),
                "fora_do_recorte": mm.get("fora_do_recorte"),
                "janela": mm.get("janela", ""),
                "apos_janela": mm.get("apos_janela"),
                "curva": mm["curva"],
                "saldo": mm.get("saldo", []),
                "abertura": mm.get("abertura", 0),
                "fora_do_livro": mm.get("fora_do_livro", 0),
                "legado": mm["legado"],
                "serie_coep": [x for x in mm["serie_coep"]
                               if "2026-01" <= x["mes"] <= "2026-07"],
                "tratativas": [t for t in mm["tratativas"] if t["mes_resolucao"]],
                "regra": mm["regra"],
            }

    dados = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    pagina = (
        '<meta charset="utf-8">\n'
        "<title>Dinâmica do Posto</title>\n"
        f"<style>\n{ler('assets', 'css', 'fontes.css')}\n</style>\n"
        f"<style>\n{ler('assets', 'css', 'styles.css')}\n</style>\n"
        f"<style>\n{ler('assets', 'css', 'dinamica.css')}\n</style>\n"
        '<main id="pagina"></main>\n'
        f"<script>\nconst DINAMICA = {dados};\n</script>\n"
        f"<script>\n{ler('assets', 'js', 'dinamica.js')}\n</script>\n"
    )
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(pagina)

    print(f"OK — {destino} ({os.path.getsize(destino) / 1024:.0f} KB)")
    print(f"     {d['total']} equipamentos em {len(d['por_etapa'])} etapas, "
          f"{moeda(d['valor_total'])} de valor previsto.")


if __name__ == "__main__":
    main()
