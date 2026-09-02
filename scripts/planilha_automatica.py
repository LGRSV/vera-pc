"""
A planilha base com fórmulas automáticas e validação — dist/GESTAO_AUTOMATICA.xlsx.

O pedido do gestor (01/09): «se eu selecionar que o defeito é o Tanque ele já traz
Tanque da 34,5 Noja código 690005; se eu disser que é uma célula de 400 kVA 90.230,
se for 2, 180.460 — usando valores reais».

A planilha base (GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP.xlsx) faz isso hoje com XLOOKUP em
DOIS arquivos externos: a carteira do SharePoint (Defeito, MAT e MO da aba «Criticidade
por Equipamento», colunas RL Auto / Valor Material / Valor mão de obra estimado) e a
GESTÃO DE EQUIPAMENTOS.xlsx (tensão pelos Ajustes). Fora da rede da Energisa esses
vínculos quebram e ficam os valores em cache. Esta planilha é autocontida: as três
tabelas de apoio moram dentro dela.

  Catálogo   — a peça com código de material, descrição, preço de material e mão de
               obra. É o ÚNICO lugar para mexer em preço.
  Cadastro   — todo religador e regulador do parque, com tensão, modelo e potência,
               vindos dos ajustes da proteção (1.292 RL + 189 RT).
  Lançamento — a folha de entrada: digita o ativo, escolhe a peça na lista, dá a
               quantidade. O resto é fórmula.
  Gestão     — os 53 pendentes do DCMD, refeitos com as mesmas fórmulas e conferidos
               contra o que a carteira dizia.
  Falha Equipamentos — o rol de 90 falhas de 2025 e 2026 com peça em lista e custo.
  Resumo     — contagem por peça e taxa, em fórmula (sem dinâmica para atualizar).

Preço: vale a CARTEIRA DE 27/08 (é a que o gestor usa; a célula de 400 é R$ 90.230
lá). Onde a carteira não tem linha, vale «Premissas e Preços» do orçamento de 16/07.
Os códigos de material vêm do orçamento e do plano de compras (690001, 690005,
690916, 692263, 690236, 690240, 690241, 690669, 651638, 625510, 647641, 90556).

Rodar: python3 scripts/planilha_automatica.py
"""

import os
import re
import sys
from collections import Counter
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, "data", "raw", "GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP.xlsx")
AJUSTES = os.path.join(RAIZ, "data", "raw", "GESTAO_DE_EQUIPAMENTOS.xlsx")
SAIDA = os.path.join(RAIZ, "dist", "GESTAO_AUTOMATICA.xlsx")

# Prontuário Industrial — papel, tinta, laranja-sinal
TINTA, PAPEL, SOMBRA, SINAL, APAGADA = "FF211D15", "FFF2EFE6", "FFE9E5D8", "FFBC4B0E", "FF8D8672"
MOEDA = '#,##0.00'
N_LANC = 300            # linhas prontas na folha de lançamento
N_CAD_MAX = 1600        # teto do intervalo de busca no cadastro

MO_RL = {"13,8": 11016.94, "34,5": 13209.34}
MO_RT = {"13,8": 51402.14, "34,5": 80318.50}
CLASSES_KVA = (167, 200, 239, 400)      # as que têm código de célula

# ----------------------------------------------------------------------------- catálogo
# (tipo, peça, classe, código, descrição, material, mo_13_8, mo_34_5, fonte, observação)
# classe = tensão no RL; kVA na célula/completo do RT; vazio no controle/acessório do RT
F_ORC = "Premissas e Preços (ORCAMENTO_EQ_ESPECIAIS, 16/07)"
F_CART = "carteira 27/08, coluna RL Auto / Valor Material / Valor mão de obra"
F_PLANO = "plano de compras MA+Alta (16/07)"


def _rl(peca, classe, cod, desc, mat, fonte, obs=""):
    return ("RL", peca, classe, cod, desc, mat, MO_RL["13,8"], MO_RL["34,5"], fonte, obs)


CATALOGO = [
    _rl("Completo", "13,8", "690001 + 690916", "Religador completo (tanque + controle) — 13,8 kV",
        55602.54, f"{F_ORC} · {F_CART} («RL Completo 13,8») · {F_PLANO}", "= 690001 + 690916"),
    _rl("Completo", "34,5", "690005 + 692263", "Religador completo (tanque + controle) — 34,5 kV",
        76246.20, f"{F_ORC} · {F_CART} («RL Completo 34,5») · {F_PLANO}", "= 690005 + 692263"),
    _rl("Tanque", "13,8", "690001", "Tanque / Parte ativa — Religador 13,8 kV", 21785.72,
        f"{F_ORC} · {F_CART} («Tanque 13,8») · {F_PLANO}"),
    _rl("Tanque", "34,5", "690005", "Tanque / Parte ativa — Religador 34,5 kV", 38151.48,
        f"{F_ORC} · {F_CART} («Tanque 34,5») · {F_PLANO}"),
    _rl("Controle", "13,8", "690916", "Controle — Religador 13,8 kV", 33816.82,
        f"{F_ORC} · {F_CART} («Controle 13,8») · {F_PLANO}"),
    _rl("Controle", "34,5", "692263", "Controle — Religador 34,5 kV", 38094.72,
        f"{F_ORC} · {F_CART} («Controle 34,5») · {F_PLANO}"),
    _rl("Relé", "13,8", "625510", "Relé de proteção multifunção 50/51 (relé do religador)",
        10454.01, f"{F_ORC}, item granular (VALOR EM ESTOQUE)", "confiança VERIFICAR no orçamento"),
    _rl("Relé", "34,5", "625510", "Relé de proteção multifunção 50/51 (relé do religador)",
        10454.01, f"{F_ORC}, item granular (VALOR EM ESTOQUE)", "confiança VERIFICAR no orçamento"),
    _rl("Placa de alimentação CA", "13,8", "647641",
        "Placa de circuito impresso — religador RC10 (placa de alimentação CA)", 1999.00,
        f"{F_ORC}, item granular (VALOR EM ESTOQUE)", "confiança VERIFICAR no orçamento"),
    _rl("Placa de alimentação CA", "34,5", "647641",
        "Placa de circuito impresso — religador RC10 (placa de alimentação CA)", 1999.00,
        f"{F_ORC}, item granular (VALOR EM ESTOQUE)", "confiança VERIFICAR no orçamento"),
    _rl("Bateria + rádio", "13,8", "647877 + 649399", "Bateria de lítio + rádio GE Orbit",
        14612.08, f"{F_ORC}, item granular · {F_PLANO}", "confiança VERIFICAR no orçamento; fora da taxa"),
    _rl("Bateria + rádio", "34,5", "647877 + 649399", "Bateria de lítio + rádio GE Orbit",
        14612.08, f"{F_ORC}, item granular · {F_PLANO}", "confiança VERIFICAR no orçamento; fora da taxa"),
    _rl("Chave faca", "13,8", "90556", "Chave seccionadora de distribuição tipo faca 36,2 kV 630 A",
        736.43, f"{F_ORC}, item granular · {F_PLANO}", "fora da taxa"),
    _rl("Chave faca", "34,5", "90556", "Chave seccionadora de distribuição tipo faca 36,2 kV 630 A",
        736.43, f"{F_ORC}, item granular · {F_PLANO}", "fora da taxa"),
    ("RL", "Acessório", "13,8", "", "Acessório / serviço sem código (valor fechado da carteira)",
     15000.00, 0.0, 0.0, f"{F_CART} («Acessório 34,5»)", "sem mão de obra na carteira"),
    ("RL", "Acessório", "34,5", "", "Acessório / serviço sem código (valor fechado da carteira)",
     15000.00, 0.0, 0.0, f"{F_CART} («Acessório 34,5»)", "sem mão de obra na carteira"),
    ("RT", "Célula", "167", "690669", "Célula — Regulador 13,8 kV / 167 kVA", 27616.62,
     MO_RT["13,8"], MO_RT["34,5"], f"{F_ORC}, item 4", "a carteira 27/08 não tem linha de 167 kVA"),
    ("RT", "Célula", "200", "690240", "Célula — Regulador 34,5 kV / 200 kVA", 51705.75,
     MO_RT["13,8"], MO_RT["34,5"], f"{F_CART} («Célula 200 34,5»)",
     "o orçamento de 16/07 trazia R$ 57.720,41"),
    ("RT", "Célula", "239", "690236", "Célula — Regulador 13,8 kV / 239 kVA", 62113.20,
     MO_RT["13,8"], MO_RT["34,5"], f"{F_CART} («Célula 200 13,8», ativo 5844630060 — 239 kVA no cadastro)",
     "o orçamento de 16/07 trazia R$ 61.098,29"),
    ("RT", "Célula", "400", "690241", "Célula — Regulador 34,5 kV / 400 kVA", 90230.00,
     MO_RT["13,8"], MO_RT["34,5"], f"{F_CART} («Célula 400 34,5»)",
     "o orçamento de 16/07 e o plano de compras traziam R$ 126.893,80"),
    ("RT", "Controle", "", "651638", "Controle de regulador c/ nobreak", 23259.60, 20000.0, 20000.0,
     f"{F_CART} («Controle 167/200 13,8/34,5»)", "o orçamento de 16/07 trazia R$ 29.445,39 e MO 0"),
    ("RT", "Completo", "400", "3 × 690241 + 651638", "Regulador completo 400 kVA (3 células + controle)",
     293949.60, 200637.0, 200637.0, f"{F_CART} («RT Completo 400 34,5»)",
     "material = 3 × 90.230 + 23.259,60; mão de obra como está na carteira. "
     "Para outra potência, lançar 3 células + 1 controle"),
    ("RT", "Acessório", "", "", "Acessório / serviço sem código (valor fechado da carteira)",
     15000.00, 0.0, 0.0, f"{F_CART} («Acessório 400 34,5»)", "sem mão de obra na carteira"),
]
PECAS_RL = ["Completo", "Tanque", "Controle", "Relé", "Placa de alimentação CA",
            "Bateria + rádio", "Chave faca", "Acessório"]
PECAS_RT = ["Célula", "Controle", "Completo", "Acessório"]
PECAS_TODAS = PECAS_RL + [p for p in PECAS_RT if p not in PECAS_RL]
TENSOES = ["13,8", "34,5"]
CRITICIDADES = ["Muito Alta", "Alta", "Média", "Baixa", "Falta definir", "Sem classificação"]
STATUS = ["Avaliar compra", "Gerado PMA", "Em compra", "Em logistica (N1>N3)",
          "A realizar (COCM)", "Em execução", "Reforma", "Realizado"]
SIM_NAO = ["sim", "não"]


def chave(tipo, peca, classe):
    return f"{tipo}|{peca}|{classe}"


# ----------------------------------------------------------------------------- leitura
def texto(v):
    return "" if v is None else str(v).strip()


def faixa(bruto):
    t = texto(bruto).replace(".", "").replace(",", "").replace(" ", "")
    if t.startswith("138"):
        return "13,8"
    if t.startswith("345"):
        return "34,5"
    return ""


def classe_kva(bruto):
    """A classe com código de célula mais próxima; num banco misto, a potência que mais
    aparece (empate: a maior). Devolve (classe, desviou)."""
    partes = [p for p in texto(bruto).replace("/", " ").split() if p]
    nums = []
    for p in partes:
        try:
            nums.append(float(p.replace(",", ".")))
        except ValueError:
            pass
    if not nums:
        return "", False
    c = Counter(nums)
    valor = max(c, key=lambda x: (c[x], x))
    classe = min(CLASSES_KVA, key=lambda k: abs(k - valor))
    return str(classe), classe != valor


def ler_cadastro():
    wb = load_workbook(AJUSTES, read_only=True, data_only=True)
    cad = {}
    for r in list(wb["Ajustes RL Poste"].iter_rows(values_only=True))[1:]:
        a = texto(r[0])
        if a[:2] in ("78", "79") and a not in cad:
            cad[a] = {"tipo": "RL", "tensao": faixa(r[12]), "modelo": texto(r[10]),
                      "potencia": "", "classe": "", "desvio": False,
                      "localidade": texto(r[13]), "alimentador": texto(r[11]),
                      "origem": "Ajustes RL Poste"}
    for r in list(wb["Ajustes Reguladores de Tensão"].iter_rows(values_only=True))[1:]:
        a = texto(r[0])
        if a[:2] == "58" and a not in cad:
            classe, desviou = classe_kva(r[4])
            modelo = " / ".join(x for x in (texto(r[3]), texto(r[2])) if x)
            cad[a] = {"tipo": "RT", "tensao": faixa(r[8]), "modelo": modelo,
                      "potencia": texto(r[4]), "classe": classe, "desvio": desviou,
                      "localidade": texto(r[14]), "alimentador": texto(r[7]),
                      "origem": "Ajustes Reguladores de Tensão"}
    return cad


def ler_modelos_carteira():
    """Modelo por ativo na Planilha1 da GESTÃO DE EQUIPAMENTOS (carteira de 12/08)."""
    wb = load_workbook(AJUSTES, read_only=True, data_only=True)
    m = {}
    for r in list(wb["Planilha1"].iter_rows(values_only=True))[1:]:
        if r[1] and texto(r[2]) not in ("", "#N/A"):
            m.setdefault(texto(r[1]), texto(r[2]))
    return m


def ler_base():
    wb = load_workbook(BASE, data_only=True)
    ws = wb["Gestão"]
    gestao = []
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if not r[0]:
            continue
        gestao.append({"ativo": texto(r[0]), "ss": texto(r[2]), "criticidade": texto(r[3]),
                       "status": texto(r[4]), "defeito": texto(r[5]),
                       "mo": r[6] or 0, "mat": r[7] or 0, "total": r[8] or 0,
                       "esteira": list(r[9:19]), "indice": r[19], "sla": r[20],
                       "dias": r[21], "atendimento": texto(r[22]), "resp": texto(r[23]),
                       "prazo": texto(r[24]), "alimentador": texto(r[26]),
                       "municipio": texto(r[27]), "polo": texto(r[28]), "regional": texto(r[29])})
    ws = wb["Falha Equipamentos"]
    falhas = []
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if not (texto(r[0]) and r[4]):
            continue
        falhas.append({"fatia": texto(r[0]), "ativo": texto(r[4]), "ss": texto(r[5]),
                       "tensao": faixa(r[6]), "data": texto(r[7]), "peca": texto(r[11]).lower(),
                       "troca": texto(r[12]), "causa": texto(r[13]), "citacao": texto(r[14]),
                       "nota": texto(r[15]), "revisao": texto(r[16])})
    return gestao, falhas


def interpreta_defeito(defeito):
    """«Célula 400 34,5» → (peça, classe kVA, tensão). É o texto da carteira."""
    d = defeito.strip()
    tensao = "13,8" if d.endswith("13,8") else ("34,5" if d.endswith("34,5") else "")
    kva = ""
    m = re.search(r"\b(167|200|239|400)\b", d)
    if m:
        kva = m.group(1)
    if d.startswith("RL Completo") or d.startswith("RT Completo"):
        peca = "Completo"
    elif d.startswith("Tanque"):
        peca = "Tanque"
    elif d.startswith("Controle"):
        peca = "Controle"
    elif d.startswith("Célula"):
        peca = "Célula"
    elif d.startswith("Acessório"):
        peca = "Acessório"
    else:
        peca = ""
    return peca, kva, tensao


PECA_ROL = {"completo": "Completo", "tanque": "Tanque", "controle": "Controle",
            "celula": "Célula", "rele": "Relé", "furto": "Célula"}


def data_pt(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except ValueError:
        return s


# ----------------------------------------------------------------------------- estilo
def cabecalho(ws, linha, titulos, larguras=None):
    for i, t in enumerate(titulos, 1):
        c = ws.cell(row=linha, column=i, value=t)
        c.font = Font(bold=True, color=PAPEL, size=10)
        c.fill = PatternFill("solid", fgColor=TINTA)
        c.alignment = Alignment(vertical="center", wrap_text=True)
    if larguras:
        for i, w in enumerate(larguras, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[linha].height = 30


def marca_entrada(ws, col, r0, r1):
    """Campo de formulário: fundo papel-sombreado, é onde o gestor digita."""
    for r in range(r0, r1 + 1):
        ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=SOMBRA)


def marca_apoio(ws, col, r0, r1):
    for r in range(r0, r1 + 1):
        ws.cell(row=r, column=col).font = Font(color=APAGADA, size=8)


def moeda(ws, col, r0, r1):
    for r in range(r0, r1 + 1):
        ws.cell(row=r, column=col).number_format = MOEDA


def lista(ws, ref, sqref, titulo=None):
    # no XML a fórmula da validação vai SEM o «=» inicial
    dv = DataValidation(type="list", formula1=ref.lstrip("="), allow_blank=True, showDropDown=False)
    dv.error = "Escolha um valor da lista"
    dv.errorTitle = titulo or "Valor fora da lista"
    dv.errorStyle = "stop"
    dv.showErrorMessage = True
    ws.add_data_validation(dv)
    dv.add(sqref)
    return dv


# ----------------------------------------------------------------------------- abas
def aba_catalogo(wb):
    ws = wb.active
    ws.title = "Catálogo"
    ws["A1"] = "CATÁLOGO DE PEÇAS — o único lugar para mexer em preço e código"
    ws["A1"].font = Font(bold=True, size=12, color=SINAL)
    ws["A2"] = ("Chave = Tipo | Peça | Classe. No religador a classe é a tensão; na célula e no "
                "regulador completo é a potência em kVA; no controle e no acessório do regulador "
                "fica vazia. Mão de obra é por serviço (uma vez por lançamento), não por peça.")
    ws["A2"].font = Font(italic=True, size=9)
    cab = ["Chave", "Tipo", "Peça", "Classe (kV ou kVA)", "Código de material", "Descrição",
           "Material unitário (R$)", "Mão de obra 13,8 (R$)", "Mão de obra 34,5 (R$)",
           "Fonte", "Observação"]
    cabecalho(ws, 4, cab, [24, 6, 22, 12, 18, 52, 16, 15, 15, 60, 52])
    r = 5
    for tipo, peca, classe, cod, desc, mat, mo1, mo2, fonte, obs in CATALOGO:
        ws.append([chave(tipo, peca, classe), tipo, peca, classe, cod, desc, mat, mo1, mo2, fonte, obs])
        for col in (7, 8, 9):
            ws.cell(row=r, column=col).number_format = MOEDA
            ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=SOMBRA)
        ws.cell(row=r, column=5).fill = PatternFill("solid", fgColor=SOMBRA)
        r += 1
    fim = r - 1
    ws.freeze_panes = "A5"

    # listas de validação, num bloco à direita
    col0 = 13
    listas = [("Pecas_RL", "Peças RL", PECAS_RL), ("Pecas_RT", "Peças RT", PECAS_RT),
              ("Pecas_Todas", "Peças (todas)", PECAS_TODAS), ("Tensoes", "Tensão", TENSOES),
              ("Potencias", "Potência kVA", [str(k) for k in CLASSES_KVA]),
              ("Criticidades", "Criticidade", CRITICIDADES), ("Status_DCMD", "Status", STATUS),
              ("Sim_Nao", "Sim / não", SIM_NAO)]
    ws.cell(row=3, column=col0, value="LISTAS DE VALIDAÇÃO (as caixas de seleção leem daqui)").font = \
        Font(bold=True, size=10, color=SINAL)
    refs = {}
    for j, (nome, rotulo, valores) in enumerate(listas):
        col = col0 + j
        letra = get_column_letter(col)
        c = ws.cell(row=4, column=col, value=rotulo)
        c.font, c.fill = Font(bold=True, color=PAPEL, size=10), PatternFill("solid", fgColor=TINTA)
        for i, v in enumerate(valores):
            ws.cell(row=5 + i, column=col, value=v)
        ws.column_dimensions[letra].width = max(14, len(rotulo) + 2)
        ref = f"'Catálogo'!${letra}$5:${letra}${4 + len(valores)}"
        refs[nome] = ref
        wb.defined_names[nome] = DefinedName(nome, attr_text=ref)
    return fim, refs


def aba_cadastro(wb, cad, extras):
    ws = wb.create_sheet("Cadastro")
    cab = ["Ativo", "Tipo", "Tensão (kV)", "Modelo", "Potência (kVA, cadastro)",
           "Classe kVA (catálogo)", "Localidade", "Alimentador", "Origem", "Observação"]
    cabecalho(ws, 1, cab, [13, 6, 11, 26, 16, 12, 24, 14, 30, 44])
    r = 2
    for a in sorted(cad, key=lambda x: (cad[x]["tipo"], x)):
        d = cad[a]
        obs = ""
        if d["desvio"]:
            obs = f"potência {d['potencia']} fora das classes com código; classificada em {d['classe']} pela mais próxima"
        if not d["tensao"]:
            obs = (obs + "; " if obs else "") + "sem tensão no cadastro"
        ws.append([a, d["tipo"], d["tensao"], d["modelo"], d["potencia"], d["classe"],
                   d["localidade"], d["alimentador"], d["origem"], obs])
        r += 1
    for a, d in extras:
        ws.append([a, d["tipo"], d["tensao"], d["modelo"], d["potencia"], d["classe"],
                   d["localidade"], d["alimentador"], d["origem"], d["obs"]])
        r += 1
    fim = r - 1
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:J{fim}"
    return fim


def formulas_auto(L, r, cad_fim, cat_fim, col):
    """As fórmulas do bloco automático. `col` diz a letra de cada campo nesta aba:
    ativo, peca, qtd, tipo, tensao, modelo, kva, codigo, desc, preco, mat, mo, total,
    tensao_manual, kva_manual, localidade, chave."""
    A = col["ativo"]
    CAD = "'Cadastro'!"
    CAT = "'Catálogo'!"
    busca_cad = lambda letra: (f'IFERROR(INDEX({CAD}${letra}$2:${letra}${cad_fim},'
                               f'MATCH({A}{r}&"",{CAD}$A$2:$A${cad_fim},0)),"")')
    busca_cat = lambda letra: (f'IFERROR(INDEX({CAT}${letra}$5:${letra}${cat_fim},'
                               f'MATCH({col["chave"]}{r},{CAT}$A$5:$A${cat_fim},0)),"")')
    f = {}
    f["tipo"] = (f'=IF({A}{r}="","",IF(LEFT({A}{r}&"",2)="58","RT",'
                 f'IF(OR(LEFT({A}{r}&"",2)="79",LEFT({A}{r}&"",2)="78"),"RL","")))')
    f["tensao"] = f'=IF({col["tensao_manual"]}{r}<>"",{col["tensao_manual"]}{r},{busca_cad("C")})'
    f["modelo"] = f"={busca_cad('D')}"
    f["kva"] = (f'=IF({col["tipo"]}{r}<>"RT","",IF({col["kva_manual"]}{r}<>"",'
                f'{col["kva_manual"]}{r}&"",{busca_cad("F")}))')
    f["localidade"] = f"={busca_cad('G')}"
    f["chave"] = (f'=IF(OR({A}{r}="",{col["peca"]}{r}="",{col["tipo"]}{r}=""),"",'
                  f'{col["tipo"]}{r}&"|"&{col["peca"]}{r}&"|"&IF({col["tipo"]}{r}="RL",{col["tensao"]}{r},'
                  f'IF(OR({col["peca"]}{r}="Célula",{col["peca"]}{r}="Completo"),{col["kva"]}{r},"")))')
    f["codigo"] = f'=IF({col["chave"]}{r}="","",{busca_cat("E")})'
    f["desc"] = (f'=IF({col["chave"]}{r}="","",IF({busca_cat("F")}="","PEÇA SEM LINHA NO CATÁLOGO — conferir tensão/potência",'
                 f'{busca_cat("F")}&IF({col["modelo"]}{r}<>""," · "&{col["modelo"]}{r},"")'
                 f'&IF({col["codigo"]}{r}<>""," · cód. "&{col["codigo"]}{r},"")))')
    f["preco"] = f'=IF({col["chave"]}{r}="","",{busca_cat("G")})'
    f["mat"] = (f'=IF(OR({col["preco"]}{r}="",{col["preco"]}{r}=0),IF({col["preco"]}{r}="","",0),'
                f'{col["preco"]}{r}*IF({col["qtd"]}{r}="",1,{col["qtd"]}{r}))')
    f["mo"] = (f'=IF({col["chave"]}{r}="","",IF({col["tensao"]}{r}="13,8",{busca_cat("H")},'
               f'IF({col["tensao"]}{r}="34,5",{busca_cat("I")},"")))')
    f["total"] = (f'=IF({col["mat"]}{r}="","",{col["mat"]}{r}+IF(ISNUMBER({col["mo"]}{r}),{col["mo"]}{r},0))')
    return f


def escreve_auto(ws, r, f, col):
    for campo, letra in col.items():
        if campo in f:
            ws[f"{letra}{r}"] = f[campo]


def aba_lancamento(wb, cad_fim, cat_fim, refs, exemplos):
    ws = wb.create_sheet("Lançamento")
    ws["A1"] = "LANÇAMENTO — digite o ativo, escolha a peça, dê a quantidade. O resto é fórmula."
    ws["A1"].font = Font(bold=True, size=12, color=SINAL)
    ws["A2"] = ("Campos sombreados são de entrada. Tensão e potência saem do cadastro; se o cadastro "
                "estiver errado ou faltar, preencha «Tensão manual» ou «Potência manual» e elas mandam. "
                "Quantidade vazia vale 1. Mão de obra entra uma vez por linha.")
    ws["A2"].font = Font(italic=True, size=9)
    cab = ["Ativo", "Peça", "Qtd", "Tipo", "Tensão (kV)", "Modelo (cadastro)", "kVA",
           "Código de material", "Descrição", "Preço unitário (R$)", "Material (R$)",
           "Mão de obra (R$)", "Total (R$)", "Tensão manual", "Potência manual", "Localidade",
           "SS", "Data", "Observação", "Chave"]
    cabecalho(ws, 4, cab, [13, 22, 6, 6, 10, 20, 7, 18, 60, 16, 15, 15, 15, 12, 12, 22, 20, 11, 30, 22])
    col = dict(ativo="A", peca="B", qtd="C", tipo="D", tensao="E", modelo="F", kva="G",
               codigo="H", desc="I", preco="J", mat="K", mo="L", total="M",
               tensao_manual="N", kva_manual="O", localidade="P", chave="T")
    r0, r1 = 5, 4 + N_LANC
    for r in range(r0, r1 + 1):
        escreve_auto(ws, r, formulas_auto("L", r, cad_fim, cat_fim, col), col)
    for i, (ativo, peca, qtd, obs) in enumerate(exemplos):
        r = r0 + i
        ws[f"A{r}"], ws[f"B{r}"], ws[f"C{r}"], ws[f"S{r}"] = ativo, peca, qtd, obs
    for c in ("A", "B", "C", "N", "O", "Q", "R", "S"):
        marca_entrada(ws, ws[c + "4"].column, r0, r1)
    marca_apoio(ws, 20, r0, r1)
    for c in ("J", "K", "L", "M"):
        moeda(ws, ws[c + "4"].column, r0, r1)
    for r in range(r0, r1 + 1):
        ws[f"I{r}"].alignment = Alignment(wrap_text=False)
    ws.freeze_panes = "C5"
    # validações
    lista(ws, f'=INDIRECT(IF($D5="","Pecas_Todas","Pecas_"&$D5))', f"B{r0}:B{r1}", "Peça")
    lista(ws, refs["Tensoes"], f"N{r0}:N{r1}", "Tensão")
    lista(ws, refs["Potencias"], f"O{r0}:O{r1}", "Potência")
    dv = DataValidation(type="whole", operator="greaterThan", formula1="0", allow_blank=True)
    dv.error, dv.errorTitle = "Quantidade inteira, maior que zero", "Quantidade"
    dv.showErrorMessage = True
    ws.add_data_validation(dv)
    dv.add(f"C{r0}:C{r1}")
    tab = Table(displayName="Lancamento", ref=f"A4:T{r1}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    return ws


def aba_gestao(wb, gestao, cad, cad_fim, cat_fim, refs):
    ws = wb.create_sheet("Gestão")
    ws["A1"] = "GESTÃO — os 53 pendentes do DCMD, com a peça em lista e o orçamento em fórmula"
    ws["A1"].font = Font(bold=True, size=12, color=SINAL)
    ws["A2"] = ("Peça e Qtd vieram do campo «Defeito» da carteira de 27/08 (quantidade 1 em todos, "
                "que é como a carteira orçou). As colunas «carteira» guardam o que ela dizia; "
                "«Bate?» confere o total novo contra o dela.")
    ws["A2"].font = Font(italic=True, size=9)
    cab = ["Ativo", "Tipo", "SS SGM", "Criticidade", "Status", "Peça", "Qtd", "Tensão (kV)",
           "Modelo (cadastro)", "kVA", "Código de material", "Descrição", "Preço unitário (R$)",
           "Orçamento MAT (R$)", "Orçamento MO (R$)", "Orçamento Total (R$)",
           "Tensão manual", "Potência manual", "Defeito (carteira 27/08)", "MAT carteira (R$)",
           "MO carteira (R$)", "Total carteira (R$)", "Bate?",
           "PMA", "Entregue N1?", "Gerado Obra?", "Gerado EMD?", "Entregue N3?", "Concluído COCM?",
           "Enviado para Cadastro", "Estudo Proteção", "Repassado ao DMSL?", "Comissionado?",
           "Índice", "SLA_Total", "Dias Pendente", "Status Atendimento", "Responsável",
           "Status Prazo", "Alimentador", "Município", "Polo", "Regional", "Localidade (cadastro)", "Chave"]
    larg = [13, 6, 21, 12, 20, 20, 5, 10, 20, 6, 18, 58, 15, 15, 15, 15, 11, 11, 22, 14, 14, 14, 7] + \
           [10] * 10 + [7, 9, 11, 26, 12, 24, 30, 20, 18, 10, 22, 22]
    cabecalho(ws, 4, cab, larg)
    col = dict(ativo="A", peca="F", qtd="G", tipo="B", tensao="H", modelo="I", kva="J",
               codigo="K", desc="L", preco="M", mat="N", mo="O", total="P",
               tensao_manual="Q", kva_manual="R", localidade="AR", chave="AS")
    r = 5
    for g in gestao:
        peca, kva, tensao = interpreta_defeito(g["defeito"])
        ws[f"A{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"] = g["ativo"], g["ss"], g["criticidade"], g["status"]
        ws[f"F{r}"], ws[f"G{r}"] = peca, 1
        c = cad.get(g["ativo"], {})
        # se o cadastro discorda da carteira (ou falta), a carteira manda pela coluna manual
        if tensao and c.get("tensao") != tensao:
            ws[f"Q{r}"] = tensao
        if kva and peca in ("Célula", "Completo") and c.get("classe") != kva:
            ws[f"R{r}"] = kva
        ws[f"S{r}"], ws[f"T{r}"], ws[f"U{r}"], ws[f"V{r}"] = g["defeito"], g["mat"], g["mo"], g["total"]
        ws[f"W{r}"] = f'=IF(P{r}="","",IF(ABS(P{r}-V{r})<0.01,"sim","NÃO"))'
        for i, v in enumerate(g["esteira"]):
            ws.cell(row=r, column=24 + i, value=v)
        for i, v in enumerate([g["indice"], g["sla"], g["dias"], g["atendimento"], g["resp"],
                               g["prazo"], g["alimentador"], g["municipio"], g["polo"], g["regional"]]):
            ws.cell(row=r, column=34 + i, value=v)
        escreve_auto(ws, r, formulas_auto("G", r, cad_fim, cat_fim, col), col)
        r += 1
    r1 = r - 1
    for c in ("D", "E", "F", "G", "Q", "R"):
        marca_entrada(ws, ws[c + "4"].column, 5, r1)
    for i in range(24, 34):
        marca_entrada(ws, i, 5, r1)
    for c in ("M", "N", "O", "P", "T", "U", "V"):
        moeda(ws, ws[c + "4"].column, 5, r1)
    marca_apoio(ws, 45, 5, r1)
    ws.freeze_panes = "C5"
    lista(ws, f'=INDIRECT(IF($B5="","Pecas_Todas","Pecas_"&$B5))', f"F5:F{r1}", "Peça")
    lista(ws, refs["Criticidades"], f"D5:D{r1}", "Criticidade")
    lista(ws, refs["Status_DCMD"], f"E5:E{r1}", "Status")
    lista(ws, refs["Tensoes"], f"Q5:Q{r1}", "Tensão")
    lista(ws, refs["Potencias"], f"R5:R{r1}", "Potência")
    # totais
    ws[f"L{r1 + 2}"] = "TOTAL dos pendentes"
    ws[f"L{r1 + 2}"].font = Font(bold=True)
    for c in ("N", "O", "P", "T", "U", "V"):
        ws[f"{c}{r1 + 2}"] = f"=SUM({c}5:{c}{r1})"
        ws[f"{c}{r1 + 2}"].number_format = MOEDA
        ws[f"{c}{r1 + 2}"].font = Font(bold=True)
    ws[f"W{r1 + 2}"] = f'=COUNTIF(W5:W{r1},"sim")&" de "&COUNTA(A5:A{r1})'
    tab = Table(displayName="Gestao", ref=f"A4:AS{r1}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    return r1


def aba_falhas(wb, falhas, cad_fim, cat_fim, refs):
    ws = wb.create_sheet("Falha Equipamentos")
    ws["A1"] = "FALHA EQUIPAMENTOS — o rol de 2025 e 2026 com a peça em lista e o custo em fórmula"
    ws["A1"].font = Font(bold=True, size=12, color=SINAL)
    ws["A2"] = ("«Peça (rol)» é a classificação original. Nas linhas de furto a peça de custo foi "
                "pré-preenchida como 3 células — conferir a quantidade; relé de regulador virou "
                "Controle (relé de sincronismo é controle, régua do gestor).")
    ws["A2"].font = Font(italic=True, size=9)
    cab = ["Fatia (ano/tipo)", "Tipo", "Ativo", "SS", "Data", "Mês", "Ano", "Peça (rol)",
           "Peça (custo)", "Qtd", "Troca feita", "Causa raiz", "Tensão (kV)", "Modelo (cadastro)",
           "kVA", "Código de material", "Descrição", "Preço unitário (R$)", "Material (R$)",
           "Mão de obra (R$)", "Total (R$)", "Tensão manual", "Potência manual",
           "Citação do texto da SS", "Nota do analista", "Revisão", "Localidade (cadastro)", "Chave"]
    larg = [11, 6, 13, 21, 11, 6, 6, 11, 22, 5, 10, 34, 10, 20, 6, 18, 58, 15, 15, 15, 15, 11, 11, 60, 60, 40, 22, 22]
    cabecalho(ws, 4, cab, larg)
    col = dict(ativo="C", peca="I", qtd="J", tipo="B", tensao="M", modelo="N", kva="O",
               codigo="P", desc="Q", preco="R", mat="S", mo="T", total="U",
               tensao_manual="V", kva_manual="W", localidade="AA", chave="AB")
    r = 5
    causas = []
    for f in falhas:
        ws[f"A{r}"], ws[f"C{r}"], ws[f"D{r}"] = f["fatia"], f["ativo"], f["ss"]
        ws[f"B{r}"] = f'=LEFT(A{r},2)'
        d = data_pt(f["data"])
        ws[f"E{r}"] = d
        if isinstance(d, datetime):
            ws[f"E{r}"].number_format = "dd/mm/yyyy"
            ws[f"F{r}"], ws[f"G{r}"] = f"=MONTH(E{r})", f"=YEAR(E{r})"
        ws[f"H{r}"] = f["peca"]
        peca_custo = PECA_ROL.get(f["peca"], "")
        tipo = f["fatia"][:2]
        if f["peca"] == "rele" and tipo == "RT":
            peca_custo = "Controle"
        ws[f"I{r}"] = peca_custo
        ws[f"J{r}"] = 3 if f["peca"] == "furto" else 1
        ws[f"K{r}"], ws[f"L{r}"] = f["troca"], f["causa"]
        if f["causa"] and f["causa"] not in causas:
            causas.append(f["causa"])
        if f["tensao"] and f["ativo"] == "7930359149":
            pass
        ws[f"X{r}"], ws[f"Y{r}"], ws[f"Z{r}"] = f["citacao"], f["nota"], f["revisao"]
        escreve_auto(ws, r, formulas_auto("F", r, cad_fim, cat_fim, col), col)
        r += 1
    r1 = r - 1
    for c in ("I", "J", "K", "L", "V", "W"):
        marca_entrada(ws, ws[c + "4"].column, 5, r1)
    for c in ("R", "S", "T", "U"):
        moeda(ws, ws[c + "4"].column, 5, r1)
    marca_apoio(ws, 28, 5, r1)
    ws.freeze_panes = "D5"
    # lista de causas, ao lado do catálogo de listas
    wc = wb["Catálogo"]
    colc = 21
    c = wc.cell(row=4, column=colc, value="Causa raiz")
    c.font, c.fill = Font(bold=True, color=PAPEL, size=10), PatternFill("solid", fgColor=TINTA)
    for i, v in enumerate(sorted(causas)):
        wc.cell(row=5 + i, column=colc, value=v)
    wc.column_dimensions[get_column_letter(colc)].width = 44
    ref_causas = f"'Catálogo'!${get_column_letter(colc)}$5:${get_column_letter(colc)}${4 + len(causas)}"
    wb.defined_names["Causas"] = DefinedName("Causas", attr_text=ref_causas)
    lista(ws, f'=INDIRECT(IF($B5="","Pecas_Todas","Pecas_"&$B5))', f"I5:I{r1}", "Peça")
    lista(ws, refs["Sim_Nao"], f"K5:K{r1}", "Troca feita")
    lista(ws, ref_causas, f"L5:L{r1}", "Causa raiz")
    lista(ws, refs["Tensoes"], f"V5:V{r1}", "Tensão")
    lista(ws, refs["Potencias"], f"W5:W{r1}", "Potência")
    tab = Table(displayName="Falhas", ref=f"A4:AB{r1}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(tab)
    return r1


def aba_resumo(wb, f1):
    ws = wb.create_sheet("Resumo")
    ws["A1"] = "RESUMO — contagem por peça e taxa, em fórmula sobre a aba Falha Equipamentos"
    ws["A1"].font = Font(bold=True, size=12, color=SINAL)
    ws["A2"] = ("Conta LINHAS do rol (por peça). Por equipamento, ativo repetido no mesmo ano "
                "conta uma vez — 90 linhas são 87 pares ativo-ano. Parque é editável.")
    ws["A2"].font = Font(italic=True, size=9)
    ws["A4"], ws["B4"] = "Parque RL", 1307
    ws["A5"], ws["B5"] = "Parque RT", 207
    for r in (4, 5):
        ws[f"B{r}"].fill = PatternFill("solid", fgColor=SOMBRA)
        ws[f"A{r}"].font = Font(bold=True)
    cab = ["Peça (rol)", "RL 2025", "RL 2026", "RT 2025", "RT 2026"]
    cabecalho(ws, 7, cab, [26, 12, 12, 12, 12])
    pecas = ["completo", "tanque", "controle", "celula", "rele", "furto"]
    F = "'Falha Equipamentos'!"
    r = 8
    for p in pecas:
        ws[f"A{r}"] = p
        for j, (tipo, ano) in enumerate([("RL", 2025), ("RL", 2026), ("RT", 2025), ("RT", 2026)]):
            ws.cell(row=r, column=2 + j,
                    value=f'=COUNTIFS({F}$A$5:$A${f1},"{tipo} {ano}",{F}$H$5:$H${f1},"{p}")')
        r += 1
    ws[f"A{r}"] = "Falhas (linhas)"
    for j in range(4):
        L = get_column_letter(2 + j)
        ws[f"{L}{r}"] = f"=SUM({L}8:{L}{r - 1})"
        ws[f"{L}{r}"].font = Font(bold=True)
    ws[f"A{r}"].font = Font(bold=True)
    r += 1
    ws[f"A{r}"] = "Taxa sobre o parque"
    for j, tipo in enumerate(["RL", "RL", "RT", "RT"]):
        L = get_column_letter(2 + j)
        parque = "$B$4" if tipo == "RL" else "$B$5"
        ws[f"{L}{r}"] = f"={L}{r - 1}/{parque}"
        ws[f"{L}{r}"].number_format = "0.0%"
    r += 1
    ws[f"A{r}"] = "Custo estimado (R$)"
    for j, (tipo, ano) in enumerate([("RL", 2025), ("RL", 2026), ("RT", 2025), ("RT", 2026)]):
        L = get_column_letter(2 + j)
        ws[f"{L}{r}"] = f'=SUMIFS({F}$U$5:$U${f1},{F}$A$5:$A${f1},"{tipo} {ano}")'
        ws[f"{L}{r}"].number_format = MOEDA
    return ws


def aba_como(wb, avisos):
    ws = wb.create_sheet("Como foi feito")
    ws.column_dimensions["A"].width = 110
    linhas = [
        ("COMO ESTA PLANILHA FUNCIONA", True),
        ("Três tabelas de apoio moram aqui dentro — Catálogo, Cadastro e as listas de validação —, então "
         "nada depende de arquivo externo. A planilha base fazia o mesmo com XLOOKUP na carteira do "
         "SharePoint e na GESTÃO DE EQUIPAMENTOS.xlsx; fora da rede esses vínculos ficam congelados.", False),
        ("", False),
        ("O FLUXO, EM QUALQUER ABA COM PEÇA", True),
        ("1) O ativo diz o tipo pelo prefixo: 58 regulador; 78 e 79 religador.", False),
        ("2) O cadastro dá tensão, modelo e potência do ativo (ajustes da proteção: Ajustes RL Poste e "
         "Ajustes Reguladores de Tensão). Se faltar ou estiver errado, «Tensão manual» e «Potência manual» mandam.", False),
        ("3) A peça escolhida na lista, mais a tensão (religador) ou a potência (célula), monta a chave "
         "«RL|Tanque|34,5» ou «RT|Célula|400» e busca no Catálogo o código, a descrição, o preço de material e a mão de obra.", False),
        ("4) Material = preço unitário × quantidade (vazia vale 1). Mão de obra entra uma vez por linha. "
         "Total = material + mão de obra.", False),
        ("5) A descrição sai como «Tanque / Parte ativa — Religador 34,5 kV · NOJA RC10 · cód. 690005». "
         "O modelo é o do ATIVO no cadastro; o código é o item de estoque, que não muda com a marca do que falhou.", False),
        ("", False),
        ("DE ONDE VÊM OS PREÇOS", True),
        ("Vale a carteira de 27/08 (coluna RL Auto / Valor Material / Valor mão de obra estimado da aba "
         "«Criticidade por Equipamento», lida do cache da planilha base). É a que o gestor usa: célula de "
         "400 kVA a R$ 90.230, célula de 200 a R$ 51.705,75, controle de regulador a R$ 23.259,60 com "
         "R$ 20.000 de mão de obra, regulador completo de 400 a R$ 293.949,60 + R$ 200.637.", False),
        ("Onde a carteira não tem linha vale «Premissas e Preços» do ORCAMENTO_EQ_ESPECIAIS (16/07): célula "
         "de 167 kVA (690669, R$ 27.616,62), relé 50/51 (625510, R$ 10.454,01), placa RC10 (647641, R$ 1.999), "
         "bateria + rádio (647877 + 649399, R$ 14.612,08), chave faca (90556, R$ 736,43).", False),
        ("No religador as duas fontes e o plano de compras batem no centavo. No regulador a carteira "
         "de 27/08 é mais barata que o orçamento de 16/07 (célula de 400: 90.230 contra 126.893,80; "
         "de 200: 51.705,75 contra 57.720,41; controle: 23.259,60 contra 29.445,39). A coluna "
         "Observação do Catálogo guarda o valor antigo.", False),
        ("Mão de obra por serviço: religador 13,8 kV R$ 11.016,94 e 34,5 kV R$ 13.209,34; regulador "
         "13,8 kV R$ 51.402,14 e 34,5 kV R$ 80.318,50; controle de regulador R$ 20.000; acessório R$ 0.", False),
        ("", False),
        ("CLASSES DE POTÊNCIA", True),
        ("Só quatro potências têm código de célula: 167 (690669), 200 (690240), 239 (690236) e 400 (690241). "
         "O cadastro traz também 250, 300, 398 e 667 e bancos mistos; a coluna «Classe kVA (catálogo)» leva "
         "cada um para a classe mais próxima (398 → 400, 250 → 239) e a Observação do Cadastro marca o desvio.", False),
        ("Regulador completo só tem linha para 400 kVA (é a que a carteira orça). Para outra potência, "
         "lance 3 células mais 1 controle.", False),
        ("", False),
        ("O QUE FOI PRÉ-PREENCHIDO", True),
        ("Gestão: a peça e a quantidade (1) vieram do campo «Defeito» da carteira; onde o cadastro discorda "
         "da carteira em tensão ou potência, a carteira foi posta na coluna manual, para o total bater. "
         "«Bate?» compara o total novo com o da carteira.", False),
        ("Falha Equipamentos: «Peça (custo)» vem da «Peça (rol)»; furto virou 3 células (conferir a "
         "quantidade — furto é decidido pela peça); relé de regulador virou Controle.", False),
        ("", False),
        ("PARA LEVAR PARA A PLANILHA BASE", True),
        ("Selecione as abas Catálogo, Cadastro e Lançamento juntas (Ctrl + clique), botão direito, «Mover "
         "ou copiar», destino GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP.xlsx, marque «Criar uma cópia». Movidas "
         "juntas, as fórmulas entre elas continuam válidas. As listas de validação (nomes Pecas_RL, "
         "Pecas_RT, Tensoes, Potencias…) vão junto.", False),
        ("", False),
        ("AVISOS", True),
    ] + [(a, False) for a in avisos] + [
        ("", False),
        ("As fórmulas foram conferidas por um motor de cálculo em Python (biblioteca formulas), não pelo "
         "Excel — LibreOffice não roda neste ambiente. Ao abrir, o Excel recalcula tudo.", False),
    ]
    for i, (t, negrito) in enumerate(linhas, 1):
        c = ws.cell(row=i, column=1, value=t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if negrito:
            c.font = Font(bold=True, size=11, color=SINAL if i == 1 else TINTA)
    return ws


# ----------------------------------------------------------------------------- montagem
def montar(saida=SAIDA):
    cad = ler_cadastro()
    modelos = ler_modelos_carteira()
    gestao, falhas = ler_base()
    avisos = []

    # ativos da planilha base que o cadastro dos ajustes não tem
    extras = []
    vistos = set()
    for g in gestao:
        a = g["ativo"]
        if a in cad or a in vistos:
            continue
        vistos.add(a)
        peca, kva, tensao = interpreta_defeito(g["defeito"])
        tipo = "RT" if a[:2] == "58" else "RL"
        extras.append((a, {"tipo": tipo, "tensao": tensao, "modelo": modelos.get(a, ""),
                           "potencia": kva, "classe": kva, "localidade": g["municipio"],
                           "alimentador": g["alimentador"],
                           "origem": "planilha base (Gestão, cache da carteira 27/08)",
                           "obs": "sem cadastro nos ajustes da proteção; tensão e potência pelo texto do Defeito"}))
    for f in falhas:
        a = f["ativo"]
        if a in cad or a in vistos:
            continue
        vistos.add(a)
        tipo = f["fatia"][:2]
        tensao = f["tensao"]
        obs = "sem cadastro nos ajustes da proteção; tensão pelo rol de falhas"
        if not tensao and a == "7930359149":
            tensao, obs = "34,5", ("sem cadastro nos ajustes e «#N/A» no rol; 34,5 inferida pela praça "
                                   "(os outros seis religadores de Caseara são 34.500)")
        extras.append((a, {"tipo": tipo, "tensao": tensao, "modelo": modelos.get(a, ""),
                           "potencia": "", "classe": "", "localidade": "", "alimentador": "",
                           "origem": "planilha base (Falha Equipamentos)", "obs": obs}))
    if extras:
        avisos.append(f"{len(extras)} ativo(s) da planilha base não estão nos ajustes da proteção e "
                      f"entraram no Cadastro com origem marcada: " + ", ".join(a for a, _ in extras) + ".")
    desvios = [a for a, d in cad.items() if d["desvio"]]
    avisos.append(f"{len(desvios)} reguladores têm potência fora das quatro classes com código "
                  f"(250, 300, 398, 667 ou banco misto) e foram levados à classe mais próxima — ver "
                  f"Observação no Cadastro.")
    sem_tensao = [a for a, d in cad.items() if not d["tensao"]]
    if sem_tensao:
        avisos.append(f"{len(sem_tensao)} ativo(s) do cadastro sem tensão: " + ", ".join(sem_tensao))
    furtos = [f["ativo"] for f in falhas if f["peca"] == "furto"]
    avisos.append("Linhas de furto na aba Falha Equipamentos pré-preenchidas com 3 células: "
                  + ", ".join(furtos) + ". Conferir a quantidade em cada uma.")

    wb = Workbook()
    cat_fim, refs = aba_catalogo(wb)
    cad_fim = aba_cadastro(wb, cad, extras)
    exemplos = [("7925744087", "Tanque", 1, "exemplo do gestor: tanque de religador 34,5 kV"),
                ("5840227063", "Célula", 2, "exemplo do gestor: duas células de 400 kVA"),
                ("7923673004", "Completo", 1, "exemplo: religador completo 13,8 kV (ARTECHE P500)"),
                ("5803327001", "Controle", 1, "exemplo: controle de regulador")]
    aba_lancamento(wb, cad_fim, cat_fim, refs, exemplos)
    g1 = aba_gestao(wb, gestao, cad, cad_fim, cat_fim, refs)
    f1 = aba_falhas(wb, falhas, cad_fim, cat_fim, refs)
    aba_resumo(wb, f1)
    aba_como(wb, avisos)
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    wb.save(saida)
    print(f"{saida}: catálogo {cat_fim - 4} linhas · cadastro {cad_fim - 1} ativos "
          f"({len(extras)} fora dos ajustes) · gestão {g1 - 4} · falhas {f1 - 4} · "
          f"lançamento {N_LANC} linhas prontas")
    return saida


if __name__ == "__main__":
    montar(sys.argv[1] if len(sys.argv) > 1 else SAIDA)
