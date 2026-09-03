#!/usr/bin/env python3
"""
Reconstrói o valor evitado dos 23 «Cancelada em operação» na convenção do Allan:
VALOR = MATERIAL + MÃO DE OBRA.

Três decisões do gestor em 13/08/2026 entram aqui:
  1. Araguaçu (5836764032): «falha na fase B é a célula» — sai de indeterminado.
  2. «Se antes estava no COEP é para contar sim» — o desconto de caixa
     (peça consumida por outra frente) deixa de abater o número.
  3. «Os outros 20 é para você estimar pelo material e a mão de obra» — todo
     ativo com peça lida recebe material de catálogo + MO da tabela.

E confirma a suspeita do gestor: «provavelmente alguns desses cancelados estão
até aqui como orçados». Estão — 11 dos 23 aparecem no ORCAMENTO_EQ_ESPECIAIS.

Uso:  python3 scripts/economia_cancelados.py
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALVO = os.path.join(RAIZ, "data", "raw", "dinamica_joa.json")

# ---------------------------------------------------------------- catálogo
# Aba «Premissas e Preços» do ORCAMENTO_EQ_ESPECIAIS (revisão de 13/08/2026).
MATERIAL = {
    "690001": ("Tanque / parte ativa — Religador 13,8 kV", 21785.72),
    "690916": ("Controle — Religador 13,8 kV", 33816.82),
    "690005": ("Tanque / parte ativa — Religador 34,5 kV", 38151.48),
    "692263": ("Controle — Religador 34,5 kV", 38094.72),
    "690236": ("Célula — Regulador 13,8 kV / 239 kVA", 61098.29),
    "690669": ("Célula — Regulador 13,8 kV / 167 kVA", 27616.62),
    "690240": ("Célula — Regulador 34,5 kV / 200 kVA", 57720.41),
    "690241": ("Célula — Regulador 34,5 kV / 400 kVA", 126893.80),
    "651638": ("Controle de regulador c/ nobreak", 29445.39),
    "90556": ("Chave seccionadora faca 36,2 kV 630 A", 736.43),
}

# Aba «Premissas e Preços», item 3. Regra do Allan lida na aba «Reguladores»:
# célula leva serviço de campo; troca de controle de regulador vai com MO zero.
MO = {
    ("RL", "13,8 kV"): 11016.94,
    ("RL", "34,5 kV"): 13209.34,
    ("RT", "13,8 kV"): 51402.14,
    ("RT", "34,5 kV"): 80318.50,
}

ORCADO = "orçamento revisado"      # linha existe no ORCAMENTO_EQ_ESPECIAIS, com custo total
PLANILHA = "planilha de gestão"    # «Valor previsto» da ATUALIZADA8
LEITURA = "leitura das SS"         # peça lida no texto, precificada no catálogo
GESTOR = "decisão do gestor"

# ------------------------------------------------------- os 23, peça a peça
# pecas: (código, quantidade). mo=False zera a mão de obra (troca de controle
# de regulador, pela regra da aba «Reguladores»).
CANCELADOS = [
    dict(
        ativo="5836764032", local="ARAGUACU", tipo="RT", tensao="34,5 kV", kva=398,
        pecas=[("690241", 1)], fonte=GESTOR, ss="ETO-COEP 00025/2026",
        peca_txt="Célula da fase B — regulador de 398 kVA",
        nota="Gestor em 13/08/2026: «falha na fase B é a célula». Sai de indeterminado. "
             "398 kVA manda no código: 690241 (400 kVA), não o 690240 dos outros três.",
    ),
    dict(
        ativo="5800291077", local="GOIATINS", tipo="RT", tensao="34,5 kV", kva=200,
        pecas=[("690240", 1)], fonte=LEITURA, ss="ETO-COEP 00066/2026",
        peca_txt="Célula da fase B, curto confirmado em ensaio de bancada",
        nota="Corrigi o código: o banco é de 200 kVA (690240 R$ 57.720,41), não de 400. "
             "Está na aba «Repassados» do orçamento revisado, sem valor lançado.",
        no_orcamento="Repassados",
    ),
    dict(
        ativo="5800440256", local="MATEIROS", tipo="RT", tensao="34,5 kV", kva=200,
        pecas=[("690240", 1), ("90556", 3)], fonte=LEITURA, ss="ETO-COEP 00034/2026",
        peca_txt="Célula do regulador + 3 chaves faca de entrada com ponto quente",
        nota="Corrigi o código para 200 kVA e passei a contar as 3 chaves faca, que "
             "antes estavam listadas mas fora da conta. Ressalva de fase segue de pé: "
             "a SS cancelada carregava o laudo da fase A; o da fase B é de 06/08/2026.",
    ),
    dict(
        ativo="5800090147", local="TAIPAS DO TOCANTINS", tipo="RT", tensao="34,5 kV", kva=200,
        pecas=[("690240", 1)], fonte=PLANILHA, ss="ETO-COEP 00023/2026",
        peca_txt="Célula da fase C",
        nota="Fecha ao centavo com a planilha de gestão: 57.720,41 + 80.318,50 = 138.038,91. "
             "Os R$ 11.145,11 que eu não rastreava eram isto — eu estava usando célula de "
             "400 kVA num regulador de 200 kVA e comparando material contra material+MO.",
    ),
    dict(
        ativo="5800366016", local="WANDERLANDIA", tipo="RT", tensao="34,5 kV", kva=200,
        pecas=[("651638", 1)], mo=False, fonte=LEITURA, ss="ETO-COEP 00016/2026",
        peca_txt="Controle completo RUA01 com nobreak",
        nota="Troca de controle de regulador vai com MO zero, como o Allan lança nas "
             "quatro linhas de controle da aba «Reguladores». Confiança média: a visita "
             "de 06/05/2026 diz que em campo está tudo correto.",
    ),
    dict(
        ativo="5850308009", local="GUARAI", tipo="RT", tensao="13,8 kV", kva=239,
        pecas=[("651638", 1)], mo=False, fonte=ORCADO, ss="ETO-COEP 00180/2025",
        peca_txt="Controle completo",
        nota="Bate nas três bases: orçamento revisado, planilha de gestão e leitura da SS, "
             "R$ 29.445,39. A nota de campo manda realocar este controle para Arapoema "
             "(5800371025) — se for, abata lá para não pagar a peça duas vezes.",
        no_orcamento="Reguladores",
    ),
    dict(
        ativo="7900505026", local="PONTE ALTA TOCANTINS", tipo="RL", tensao="34,5 kV",
        pecas=[("690005", 1), ("692263", 1)], fonte=ORCADO, ss="ETO-COEP 00042/2026",
        peca_txt="Religador completo — tanque + controle",
        nota="Orçado como equipamento completo de 34,5 kV. Status na planilha do Allan: "
             "«Reavaliar / Em processo de compra».",
        no_orcamento="Detalhe Religadores",
    ),
    dict(
        ativo="7900930040", local="ARAGOMINAS", tipo="RL", tensao="13,8 kV",
        pecas=[("690001", 1), ("690916", 1)], fonte=LEITURA, ss="ETO-COEP 00019/2026",
        peca_txt="Religador completo — tanque + controle",
    ),
    dict(
        ativo="7922995039", local="ARAGUATINS", tipo="RL", tensao="13,8 kV",
        pecas=[("690001", 1), ("690916", 1)], fonte=ORCADO, ss="ETO-COEP 00179/2025",
        peca_txt="Religador completo + troca do meio de comunicação (Orbcomm → Telespazio)",
        nota="A antena não tem código de catálogo e ficou fora do valor.",
        no_orcamento="Detalhe Religadores",
    ),
    dict(
        ativo="7903569004", local="ARAGUAINA", tipo="RL", tensao="13,8 kV",
        pecas=[("690001", 1), ("690916", 1)], fonte=ORCADO, ss="ETO-COEP 00060/2026",
        peca_txt="Religador completo",
        nota="Único dos 23 com SS ainda PENDENTE: «PARECER COEP 28/07/2026: EQUIPAMENTO "
             "SELECIONADO PARA COMPRA. Equipamento baypassado», posterior ao registro de "
             "que estava em operação. Se a compra saiu, isto vira despesa e não economia.",
        no_orcamento="Detalhe Religadores",
    ),
    dict(
        ativo="7931383086", local="MARIANOPOLIS", tipo="RL", tensao="34,5 kV",
        pecas=[("690005", 1)], fonte=LEITURA, ss="ETO-COEP 00030/2026",
        peca_txt="Tanque / parte ativa + para-raio da fase B da estrutura anterior",
        nota="O para-raio não tem código de catálogo e ficou fora do valor.",
    ),
    dict(
        ativo="7955430075", local="DOIS IRMAOS DO TOCANTINS", tipo="RL", tensao="34,5 kV",
        pecas=[("690005", 1)], fonte=ORCADO, ss="ETO-COEP 00208/2025",
        peca_txt="Tanque / parte ativa",
        nota="É o laudo que apareceu colado na SS de Caseara (7944319149). A peça é daqui, "
             "conta uma vez só.",
        no_orcamento="Detalhe Religadores",
    ),
    dict(
        ativo="7908206074", local="DIANOPOLIS", tipo="RL", tensao="34,5 kV",
        pecas=[("690005", 1)], fonte=ORCADO, ss="ETO-COEP 00063/2025",
        peca_txt="Tanque / parte ativa",
        nota="Confiança média: as SS de 2024 pedem o religador COMPLETO («tanque em curto "
             "e controle com defeito») e eu fiquei só no tanque, ancorando no laudo mais "
             "recente. O orçamento do Allan também lança só o tanque.",
        no_orcamento="Detalhe Religadores",
    ),
    dict(
        ativo="7957126085", local="MONTE SANTO DO TOCANTINS", tipo="RL", tensao="34,5 kV",
        pecas=[("692263", 1)], fonte=ORCADO, ss="ETO-COEP 00156/2025",
        peca_txt="Controle completo + cabo de alimentação da BT",
        nota="Fecha ao centavo com a planilha de gestão: 38.094,72 + 13.209,34 = 51.304,06. "
             "A diferença de R$ 13.209,34 que eu não explicava era a mão de obra. O tanque "
             "NÃO entra: o laudo manda abaixar o tanque, e o que foi enviado seguiu para "
             "Porto Nacional (7953610256).",
        no_orcamento="Detalhe Religadores",
    ),
    dict(
        ativo="7967181127", local="PALMEIRAS DO TOCANTINS", tipo="RL", tensao="34,5 kV",
        pecas=[("90556", 1)], fonte=ORCADO, ss="ETO-COEP 00073/2026",
        peca_txt="Chave faca da fase C (CH-[967181127C])",
        nota="Aqui a mão de obra é 18 vezes a peça: R$ 736,43 de chave faca contra "
             "R$ 13.209,34 de serviço de campo. É o ativo que mostra por que valorizar "
             "só material engana.",
        no_orcamento="Detalhe Religadores",
    ),
    dict(
        ativo="7900543083", local="APARECIDA DO RIO NEGRO", tipo="RL", tensao="34,5 kV",
        pecas=[], fonte=LEITURA, veredito="sem_material", ss="ETO-COEP 00013/2026",
        peca_txt="Nenhuma",
        nota="Armadilha de texto de terceiro: o laudo de tanque colado na SS é do 7900448083.",
    ),
    dict(
        ativo="7944319149", local="CASEARA", tipo="RL", tensao="34,5 kV",
        pecas=[], fonte=LEITURA, veredito="sem_material", ss="ETO-COEP 00201/2025",
        peca_txt="Nenhuma",
        nota="Armadilha de texto de terceiro: o laudo é do 7955430075, que também está "
             "nesta lista. O próprio orçamento revisado registra isso na aba «Em Análise».",
        no_orcamento="Em Análise",
    ),
    dict(
        ativo="7955523028", local="NATIVIDADE", tipo="RL", tensao="34,5 kV",
        pecas=[], fonte=LEITURA, veredito="sem_material", ss="ETO-COEP 00043/2026",
        peca_txt="Para-raios de entrada e cabo solto do isolador da fase B — sem código",
        nota="O DMSL escreveu «da parte do DMSL não há pendências».",
    ),
    dict(
        ativo="7955686076", local="DUERE", tipo="RL", tensao="13,8 kV",
        pecas=[], fonte=LEITURA, veredito="sem_material", ss="ETO-COEP 00046/2026",
        peca_txt="Nenhuma",
        nota="Caminhão bateu no poste; o pedido é refixar o controle, não trocar. A SS "
             "ETO-RD-GU 00132/2026 colada ali é de um poste em outra localidade.",
    ),
    dict(
        ativo="5820790038", local="TAGUATINGA", tipo="RT", tensao="34,5 kV", kva=200,
        pecas=[], fonte=LEITURA, veredito="sem_material", ss="ETO-COEP 00022/2026",
        peca_txt="Nenhuma",
        nota="Tinha laudo de célula queimada, mas o regulador foi substituído em "
             "06/08/2024 — contar aqui seria cobrar duas vezes.",
    ),
    dict(
        ativo="7954668084", local="DIVINOPOLIS", tipo="RL", tensao="34,5 kV",
        pecas=[], fonte=LEITURA, veredito="indeterminado", ss="ETO-COEP 00028/2026",
        peca_txt="Display queimado — provável controle, sem laudo",
        teto=[("692263", 1)],
        nota="Defeito de material confirmado, peça não nomeada. Falta o retorno da "
             "inspeção SID 4053/2026. Está na aba «Em Análise» do orçamento revisado, "
             "com a mesma dúvida: «sem parecer DMSL — provável controle, confirmar».",
        no_orcamento="Em Análise",
    ),
    dict(
        ativo="7900648055", local="ARAGUACEMA", tipo="RL", tensao="34,5 kV",
        pecas=[], fonte=LEITURA, veredito="indeterminado", ss="ETO-COEP 00014/2026",
        peca_txt="Relé apagado e HOT LINE TAG, sem diagnóstico",
        teto=[("692263", 1)],
        nota="A palavra «controle» não aparece em nenhum texto do ativo; a única hipótese "
             "escrita é troca de bateria. Falta o feedback da OS ETO-TELEPA 000289/2026.",
    ),
    dict(
        ativo="7921040031", local="RIO DOS BOIS", tipo="RL", tensao="34,5 kV",
        pecas=[], fonte=LEITURA, veredito="indeterminado", ss="ETO-COEP 00031/2026",
        peca_txt="Laudo de tanque retratado pela própria equipe",
        teto=[("690005", 1)],
        nota="A equipe desmentiu o laudo em 15/12/2025 e o equipamento passou em "
             "comissionamento completo duas vezes depois disso.",
    ),
]


def moeda(v):
    inteiro, centavos = f"{v:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def precificar(item, pecas):
    """Devolve (material, mo, linhas) na convenção do Allan."""
    material = 0.0
    linhas = []
    for cod, qtd in pecas:
        desc, unit = MATERIAL[cod]
        material += unit * qtd
        linhas.append({
            "codigo": cod, "descricao": desc, "qtd": qtd,
            "unitario": round(unit, 2), "total": round(unit * qtd, 2),
        })
    mo = 0.0
    if material and item.get("mo", True):
        mo = MO[(item["tipo"], item["tensao"])]
    return round(material, 2), round(mo, 2), linhas


def main():
    with open(ALVO, encoding="utf-8") as fh:
        d = json.load(fh)

    por_ativo = {i["ativo"]: i for i in d["lista"]}
    criticidade = {a: por_ativo[a]["criticidade"] for a in por_ativo}

    lista, total_mat, total_mo = [], 0.0, 0.0
    teto_extra = 0.0
    for item in CANCELADOS:
        material, mo, linhas = precificar(item, item["pecas"])
        veredito = item.get("veredito", "material_identificado")
        total_mat += material
        total_mo += mo

        registro = {
            "ativo": item["ativo"],
            "localidade": item["local"],
            "criticidade": criticidade.get(item["ativo"], "Sem classificação"),
            "tipo": item["tipo"],
            "classe_tensao": item["tensao"],
            "kva": item.get("kva"),
            "ss": item["ss"],
            "veredito": veredito,
            "peca": item["peca_txt"],
            "material": material,
            "mao_de_obra": mo,
            "valor": round(material + mo, 2),
            "fonte": item["fonte"],
            "no_orcamento": item.get("no_orcamento", ""),
            "linhas": linhas,
            "nota": item.get("nota", ""),
        }
        if item.get("teto"):
            tm, tmo, tlinhas = precificar(item, item["teto"])
            registro["teto"] = round(tm + tmo, 2)
            registro["teto_material"] = tm
            registro["teto_mo"] = tmo
            registro["teto_peca"] = "; ".join(l["descricao"] for l in tlinhas)
            teto_extra += tm + tmo
        lista.append(registro)

    lista.sort(key=lambda x: -x["valor"])
    total = round(total_mat + total_mo, 2)

    com_material = [x for x in lista if x["veredito"] == "material_identificado"]
    sem_material = [x for x in lista if x["veredito"] == "sem_material"]
    indeterminados = [x for x in lista if x["veredito"] == "indeterminado"]

    # Os que já estão dentro do orçamento revisado com custo lançado: dinheiro
    # reservado para equipamento que está rodando. É o que dá para liberar.
    dentro = [x for x in lista if x["no_orcamento"] in ("Detalhe Religadores", "Reguladores")]
    liberavel = round(sum(x["valor"] for x in dentro), 2)
    citados = [x for x in lista if x["no_orcamento"]]

    d["economia"] = {
        "total_ativos": len(lista),
        "total": total,
        "material": round(total_mat, 2),
        "mao_de_obra": round(total_mo, 2),
        "com_material": len(com_material),
        "sem_material": len(sem_material),
        "indeterminados": len(indeterminados),
        "base": "material + mão de obra",
        "criterio": (
            "Cancelada em operação quer dizer que a SS caiu porque o equipamento já "
            "estava operando. O valor é o que teria sido gasto se o cancelamento não "
            "tivesse acontecido, na convenção do Allan: material de catálogo mais mão "
            "de obra de campo. Peça lida no texto das SS e OS de cada ativo; preço na "
            "aba «Premissas e Preços» do ORCAMENTO_EQ_ESPECIAIS."
        ),
        "decisoes": [
            {
                "titulo": "«Falha na fase B é a célula»",
                "texto": "Araguaçu (5836764032) sai de indeterminado e entra com célula. "
                         "O banco é de 398 kVA, então o código é o 690241 (400 kVA), a "
                         f"R$ 126.893,80, e não o 690240 dos outros três reguladores. Com "
                         "a mão de obra de 34,5 kV, entra por R$ 207.212,30 — é o maior "
                         "valor da lista.",
            },
            {
                "titulo": "«Se antes estava no COEP é para contar sim»",
                "texto": "Tirei o desconto de caixa que eu tinha proposto. Em 5 ativos a "
                         "peça acabou consumida por outra frente (DCMD ou estoque) e eu "
                         "abatia R$ 261.846,58 do total por causa disso. Como a demanda "
                         "estava no COEP, esses cinco voltam a contar cheios: Goiatins, "
                         "Marianópolis, Araguatins, Guaraí e Palmeiras.",
            },
            {
                "titulo": "«Os outros 20 é para você estimar pelo material e a mão de obra»",
                "texto": "Passei os 23 para a convenção do Allan — material de catálogo "
                         "mais mão de obra de campo. Isso resolveu de quebra as duas "
                         "diferenças contra a planilha de gestão que eu não sabia explicar: "
                         "os R$ 11.145,11 de Taipas e os R$ 13.209,34 de Monte Santo eram "
                         "mão de obra e célula de 200 kVA no lugar da de 400. Agora as três "
                         "linhas que existem nas duas bases fecham ao centavo.",
            },
        ],
        "lista": lista,
        "orcado": {
            "citados": len(citados),
            "com_custo": len(dentro),
            "liberavel": liberavel,
            "ativos": [
                {"ativo": x["ativo"], "localidade": x["localidade"], "ss": x["ss"],
                 "aba": x["no_orcamento"], "soma": x in dentro,
                 # «Repassados» e «Em Análise» são abas de referência: o Allan já as
                 # deixa fora do total, então ali não há valor lançado a liberar.
                 "valor": x["valor"] if x in dentro else 0.0}
                for x in citados
            ],
        },
        "teto": {
            "valor": round(total + teto_extra, 2),
            "extra": round(teto_extra, 2),
            "ativos": len(indeterminados),
            "linhas": [
                {"ativo": x["ativo"], "localidade": x["localidade"],
                 "peca": x.get("teto_peca", ""), "valor": x.get("teto", 0),
                 "porque": x["nota"]}
                for x in indeterminados
            ],
        },
    }

    for i in d["lista"]:
        if i["etapa"] != "Cancelada em operação":
            continue
        reg = next((x for x in lista if x["ativo"] == i["ativo"]), None)
        if not reg:
            continue
        i["valor_evitado"] = reg["valor"]
        i["valor_evitado_material"] = reg["material"]
        i["valor_evitado_mo"] = reg["mao_de_obra"]
        i["material_lido"] = reg["peca"]
        i["veredito_material"] = reg["veredito"]

    with open(ALVO, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)

    print(f"23 cancelados — {moeda(total)}")
    print(f"  material    {moeda(total_mat)}")
    print(f"  mão de obra {moeda(total_mo)}")
    print(f"  já orçado   {moeda(liberavel)} em {len(dentro)} ativos "
          f"({len(citados)} citados no orçamento revisado)")
    print(f"  teto        {moeda(total + teto_extra)} (+{moeda(teto_extra)} "
          f"nos {len(indeterminados)} indeterminados)")
    print()
    for x in lista:
        if x["valor"]:
            print(f"  {x['ativo']}  {x['localidade'][:26]:<26} "
                  f"{moeda(x['material']):>16} + {moeda(x['mao_de_obra']):>14} "
                  f"= {moeda(x['valor']):>16}  [{x['fonte']}]")


if __name__ == "__main__":
    main()
