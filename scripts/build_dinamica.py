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
