"""
Marca e faixa de tensão dos 53 ativos da carteira do DCMD.

Pedido do gestor (16/09): a lista dos 53 com marca e faixa de tensão.

**De onde vem cada coisa, e por que só de lá:**

- **Marca** — só existe no **cadastro de ajustes da proteção**
  (`GESTAO_DE_EQUIPAMENTOS.xlsx`): coluna `RELE` em «Ajustes RL Poste» e
  `PARTE ATIVA` em «Ajustes Reguladores de Tensão». A coluna **Marca da aba Gestão
  está vazia** nos 53 — é campo a preencher, como a esteira — e a base de SS/OS traz
  `FABRICANTE_INSTALADO` em branco para todos eles.
- **Tensão** — três fontes independentes, e elas **concordam nos 53**: a coluna `TENSÃO`
  do ajuste, a coluna `Tensão` da aba «Falha Equipamentos» e o texto da coluna `Defeito`
  da aba «Gestão» («Tanque 13,8», «RT Completo 400 34,5»).

**O único buraco é o 7930359149** (Caseara): fora do cadastro de ajustes, sem Modelo na
Planilha1, `#N/A` na aba de falhas e sem fabricante na base de SS/OS. A tensão dele está
confirmada pelo Defeito da aba Gestão (34,5); a **marca fica inferida** pelos seis
religadores de Caseara no cadastro, todos NOJA RC10, dois no mesmo alimentador.

**Armadilhas que custaram uma passada errada e ficam registradas:**

1. Guardar a ÚLTIMA linha de cada código apaga o valor bom: a Planilha1 tem 152 linhas
   para 65 modelos, e a linha repetida vem vazia. Guardar o primeiro valor NÃO vazio.
2. Na aba «Falha Equipamentos» a coluna do código é `Ativo`, não `Equipamento` — esta
   guarda «RL»/«RT» e vem antes.
3. Procurar a coluna de tensão por `TENS` pega **`27 (SUBTENSÃO)`** antes de `TENSÃO`.

Rodar: python3 scripts/marca_tensao_53.py
"""

import os
import re
from collections import Counter, defaultdict

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AJUSTES = os.path.join(RAIZ, "data", "raw", "GESTAO_DE_EQUIPAMENTOS.xlsx")
CARTEIRA = os.path.join(RAIZ, "data", "raw",
                        "GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP_2.xlsx")
SAIDA = os.path.join(RAIZ, "dist", "MARCA_TENSAO_53.xlsx")

TINTA, PAPEL, SINAL = "FF211D15", "FFF2EFE6", "FFBC4B0E"
PAPEL2, FILETE = "FFE9E5D8", "FFC8C2AF"

ATIVOS = """
7923673004 7931608059 7947203070 5856070091 7903569004 7925744087 7908705049
7927413001 5800440256 7900453110 7925871077 5803327001 7926089013 5853360007
5840227063 7903112004 7920024127 7927646026 7930428001 7900535058 7927713200
7937102148 7944559149 5800961074 7908249152 7925733015 7927396052 7933585074
7955986084 7900525015 7928564039 5855411017 7908196047 7921202014 7923927122
7927446001 7928241200 7942485096 7955946007 7901110084 7910027196 7913662076
5862236091 5836786094 7919270014 7926442035 7938137007 5856156091 5858783119
7930359149 7953211079 5825703064 7931219078
""".split()

# o que o cadastro não tem, e de onde veio o palpite
INFERIDO = {
    "7930359149": ("NOJA RC10",
                   "fora do cadastro de ajustes; os 6 religadores de Caseara no "
                   "cadastro são todos NOJA RC10, dois no mesmo alimentador "
                   "(LD03414149). Inferência, não cadastro — confirmar no cadastro."),
}

# praça e alimentador de quem não está no cadastro de ajustes: vêm da base de SS,
# onde COD_LOC guarda só o sufixo do código (149 = Caseara)
FORA_DO_CADASTRO = {"7930359149": ("Caseara", "LD03414149")}


def txt(v):
    return str(v).strip() if v is not None else ""


def faixa(bruto):
    """13.800 / 34.500 / 34500 → a faixa que o gestor usa."""
    v = txt(bruto).replace(".", "").replace(",", "")
    if v.startswith("138"):
        return "13,8 kV"
    if v.startswith("345"):
        return "34,5 kV"
    return ""


def _col(cab, *nomes):
    """Índice da coluna pelo nome EXATO. Nunca por `in`: procurar «TENS» acha
    «27 (SUBTENSÃO)» antes de «TENSÃO»."""
    for n in nomes:
        if n in cab:
            return cab.index(n)
    raise KeyError("coluna não encontrada: %s em %s" % (nomes, cab[:12]))


def _varre(ws, alvo, cod, campos):
    """{ativo: {campo: primeiro valor NÃO vazio}} — a linha repetida costuma vir
    vazia e sobrescreveria a boa."""
    fora = defaultdict(dict)
    cab = None
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            cab = [txt(c) for c in r]
            ic = _col(cab, cod)
            idx = {k: _col(cab, *v) for k, v in campos.items()}
            continue
        a = txt(r[ic])
        if a not in alvo:
            continue
        for k, j in idx.items():
            v = txt(r[j])
            if v and not fora[a].get(k):
                fora[a][k] = v
    return fora


def ler():
    alvo = set(ATIVOS)
    wb = load_workbook(AJUSTES, read_only=True, data_only=True)
    rl = _varre(wb["Ajustes RL Poste"], alvo, "EQUIPAMENTO",
                {"marca": ("RELE",), "tensao": ("TENSÃO",),
                 "alim": ("ALIMENTADOR",), "loc": ("LOCALIDADE",)})
    rt = _varre(wb["Ajustes Reguladores de Tensão"], alvo, "CÓDIGO",
                {"marca": ("PARTE ATIVA",), "tensao": ("TENSÃO PRIMÁRIA [Kv]",),
                 "kva": ("POTÊNCIA [Kvar]",), "ctrl": ("CONTROLADOR",),
                 "alim": ("ALIMENTADOR",), "loc": ("LOCALIDADE",)})
    p1 = _varre(wb["Planilha1"], alvo, "Ativo", {"modelo": ("Modelo",)})
    wb.close()

    wb = load_workbook(CARTEIRA, read_only=True, data_only=True)
    ge = _varre(wb["Gestão"], alvo, "Ativo",
                {"defeito": ("Defeito",), "crit": ("Criticidade",),
                 "status": ("Status",), "ss": ("SS SGM",),
                 "total": ("Orçamento Total",)})
    fe = _varre(wb["Falha Equipamentos"], alvo, "Ativo", {"tensao": ("Tensão",)})
    wb.close()
    return rl, rt, p1, ge, fe


def monta():
    rl, rt, p1, ge, fe = ler()
    linhas, confere = [], []
    for a in ATIVOS:
        c = dict(rl.get(a) or rt.get(a) or {})
        tipo = "RL" if a in rl else ("RT" if a in rt else
                                     ("RL" if a[:2] in ("79", "78") else "RT"))
        g = ge.get(a, {})
        marca, fonte_marca = c.get("marca", ""), "cadastro de ajustes"
        if not marca and a in INFERIDO:
            marca, fonte_marca = INFERIDO[a][0] + " (inferido)", "inferido"
        if a in FORA_DO_CADASTRO:
            c.setdefault("loc", FORA_DO_CADASTRO[a][0])
            c.setdefault("alim", FORA_DO_CADASTRO[a][1])

        # a tensão por três caminhos; o do Defeito é texto («Tanque 34,5»)
        t_aj = faixa(c.get("tensao"))
        t_fe = faixa(fe.get(a, {}).get("tensao"))
        m = re.search(r"(13,8|34,5)", g.get("defeito", ""))
        t_ge = (m.group(1) + " kV") if m else ""
        vistos = [x for x in (t_aj, t_fe, t_ge) if x]
        tensao = vistos[0] if vistos else ""
        bate = "sim" if len(set(vistos)) == 1 else (
            "—" if len(vistos) < 2 else "NÃO")

        linhas.append([
            a, tipo, marca, tensao,
            (c.get("kva") + " kVA") if c.get("kva") else "",
            c.get("ctrl", ""), g.get("defeito", ""), g.get("crit", ""),
            g.get("status", ""), (c.get("loc") or "").title(),
            c.get("alim", ""), g.get("ss", ""),
            float(g["total"]) if g.get("total") else None, fonte_marca,
        ])
        confere.append([a, tipo, c.get("marca", "") or "(sem cadastro)",
                        p1.get(a, {}).get("modelo", "") or "—",
                        t_aj or "—", t_fe or "—", t_ge or "—", bate])
    return linhas, confere


# ------------------------------------------------------------------ a planilha
def cabeca(ws, linha, titulo, cols, larguras=None):
    ws.cell(row=linha, column=1, value=titulo).font = Font(bold=True, size=11,
                                                           color=SINAL)
    for i, t in enumerate(cols, start=1):
        cel = ws.cell(row=linha + 1, column=i, value=t)
        cel.font = Font(bold=True, color=PAPEL, size=10)
        cel.fill = PatternFill("solid", fgColor=TINTA)
        cel.alignment = Alignment(horizontal="left", vertical="center",
                                  wrap_text=True)
    if larguras:
        for i, w in enumerate(larguras, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
    return linha + 2


def zebra(ws, r0, r1, ncol):
    lado = Side(style="thin", color=FILETE)
    for r in range(r0, r1):
        for i in range(1, ncol + 1):
            cel = ws.cell(row=r, column=i)
            cel.border = Border(bottom=lado)
            if (r - r0) % 2:
                cel.fill = PatternFill("solid", fgColor=PAPEL2)


def escreve():
    linhas, confere = monta()
    wb = Workbook()

    # ---- aba 1: os 53
    ws = wb.active
    ws.title = "Marca e tensão"
    cols = ["Ativo", "Tipo", "Marca", "Tensão", "Potência", "Controlador",
            "Defeito orçado", "Criticidade", "Status", "Praça", "Alimentador",
            "SS no SGM", "Orçamento total", "Fonte da marca"]
    r = cabeca(ws, 1, "Os 53 ativos da carteira do DCMD · marca e faixa de tensão",
               cols, [12, 6, 17, 9, 10, 12, 21, 13, 16, 22, 13, 21, 15, 18])
    r0 = r
    for ln in linhas:
        for i, v in enumerate(ln, start=1):
            cel = ws.cell(row=r, column=i, value=v)
            if i == 13 and v is not None:
                cel.number_format = "R$ #,##0.00"   # formato SEMPRE em convenção US
            if i in (1, 11, 12):
                cel.font = Font(name="Consolas", size=10)
            if ln[13] == "inferido":
                cel.font = Font(name="Consolas" if i in (1, 11, 12) else "Calibri",
                                size=10, italic=True, color=SINAL)
        r += 1
    zebra(ws, r0, r, len(cols))
    ws.freeze_panes = "A3"
    ws.auto_filter.ref = "A2:N%d" % (r - 1)

    # ---- aba 2: a conferência fonte a fonte
    ws = wb.create_sheet("Conferência")
    r = cabeca(ws, 1, "Marca e tensão conferidas contra cada fonte, ativo a ativo",
               ["Ativo", "Tipo", "Marca (ajustes)", "Modelo (Planilha1)",
                "Tensão (ajustes)", "Tensão (Falha Eq.)", "Tensão (Defeito)",
                "As fontes batem?"],
               [12, 6, 18, 18, 15, 16, 15, 15])
    r0 = r
    for ln in confere:
        for i, v in enumerate(ln, start=1):
            cel = ws.cell(row=r, column=i, value=v)
            if i == 1:
                cel.font = Font(name="Consolas", size=10)
            if i == 8 and v == "NÃO":
                cel.font = Font(bold=True, color=SINAL)
        r += 1
    zebra(ws, r0, r, 8)
    ws.freeze_panes = "A3"
    r += 1
    n_marca = sum(1 for x in confere if x[2] != "(sem cadastro)" and x[3] != "—")
    d_marca = sum(1 for x in confere
                  if x[2] != "(sem cadastro)" and x[3] != "—"
                  and x[2].split()[0].upper() != x[3].split()[0].upper())
    d_ten = sum(1 for x in confere if x[7] == "NÃO")
    for t in ("Marca — ajustes contra o Modelo da Planilha1: %d comparados, "
              "%d divergentes." % (n_marca, d_marca),
              "Tensão — ajustes contra Falha Equipamentos contra o Defeito da aba "
              "Gestão: 53 ativos, %d divergentes." % d_ten,
              "Nenhum código se repete nas abas de ajuste (1.292 RL · 190 RT)."):
        ws.cell(row=r, column=1, value=t).font = Font(bold=True, size=10)
        r += 1

    # ---- aba 3: resumo
    ws = wb.create_sheet("Resumo")
    r = cabeca(ws, 1, "Marca", ["Marca", "Ativos", "RL", "RT"], [22, 9, 7, 7])
    r0 = r
    cm = Counter(x[2].replace(" (inferido)", "") for x in linhas)
    for marca, n in cm.most_common():
        ws.cell(row=r, column=1, value=marca)
        ws.cell(row=r, column=2, value=n)
        ws.cell(row=r, column=3,
                value=sum(1 for x in linhas
                          if x[2].replace(" (inferido)", "") == marca
                          and x[1] == "RL"))
        ws.cell(row=r, column=4,
                value=sum(1 for x in linhas
                          if x[2].replace(" (inferido)", "") == marca
                          and x[1] == "RT"))
        r += 1
    zebra(ws, r0, r, 4)
    ws.cell(row=r, column=1, value="Total").font = Font(bold=True)
    ws.cell(row=r, column=2, value=len(linhas)).font = Font(bold=True)
    r += 2

    r = cabeca(ws, r, "Faixa de tensão", ["Tipo", "13,8 kV", "34,5 kV", "Total"])
    r0 = r
    for tipo in ("RL", "RT"):
        sub = [x for x in linhas if x[1] == tipo]
        ws.cell(row=r, column=1, value=tipo)
        ws.cell(row=r, column=2,
                value=sum(1 for x in sub if x[3] == "13,8 kV"))
        ws.cell(row=r, column=3,
                value=sum(1 for x in sub if x[3] == "34,5 kV"))
        ws.cell(row=r, column=4, value=len(sub))
        r += 1
    zebra(ws, r0, r, 4)
    r += 2

    r = cabeca(ws, r, "Potência dos reguladores",
               ["Potência", "Bancos"], [22, 9])
    r0 = r
    for kva, n in Counter(x[4] for x in linhas if x[1] == "RT").most_common():
        ws.cell(row=r, column=1, value=kva or "(sem cadastro)")
        ws.cell(row=r, column=2, value=n)
        r += 1
    zebra(ws, r0, r, 2)

    # ---- aba 4: método
    ws = wb.create_sheet("Como foi feito")
    ws.column_dimensions["A"].width = 118
    r = 1
    for tit, corpo in [
        ("De onde vem a MARCA",
         "Só do cadastro de ajustes da proteção (GESTAO_DE_EQUIPAMENTOS.xlsx): coluna "
         "RELE em «Ajustes RL Poste» e PARTE ATIVA em «Ajustes Reguladores de Tensão». "
         "A coluna Marca da aba Gestão está VAZIA nos 53 — é campo a preencher, como a "
         "esteira — e FABRICANTE_INSTALADO da base de SS/OS vem em branco para todos."),
        ("De onde vem a TENSÃO",
         "Três fontes independentes, e elas concordam nos 53: a coluna TENSÃO do "
         "cadastro de ajustes, a coluna Tensão da aba «Falha Equipamentos» e o texto "
         "da coluna Defeito da aba «Gestão» («Tanque 13,8», «RT Completo 400 34,5»). "
         "A aba Conferência mostra as três, ativo a ativo."),
        ("O único buraco",
         "7930359149 (Caseara) não está no cadastro de ajustes, não tem Modelo na "
         "Planilha1, sai «#N/A» na aba de falhas e não tem fabricante na base de SS/OS. "
         "A TENSÃO dele está confirmada pelo Defeito da aba Gestão (34,5 kV). A MARCA "
         "é inferência: os 6 religadores de Caseara no cadastro são todos NOJA RC10, "
         "dois deles no mesmo alimentador (LD03414149). Vai em itálico laranja."),
        ("Três armadilhas de leitura, registradas",
         "1. Guardar a ÚLTIMA linha de cada código apaga o valor bom — a Planilha1 tem "
         "152 linhas para 65 modelos, e a repetida vem vazia. Vale o primeiro valor "
         "não vazio.  2. Na aba «Falha Equipamentos» a coluna do código é «Ativo», não "
         "«Equipamento» — esta guarda RL/RT e vem antes.  3. Procurar a coluna de "
         "tensão por «TENS» pega «27 (SUBTENSÃO)» antes de «TENSÃO»."),
        ("O que salta aos olhos",
         "O COOPER F6 é 9 dos 41 religadores desta lista (22%) contra 10,3% do parque "
         "— é o modelo que a DMSL chamou de obsoleto no 7900001227 e que tem índice de "
         "falha 2,19. Três potências de RT estão fora das três classes do gestor "
         "(167/200/400): dois cadastrados como 398 kVA (é 400) e um como 250 kVA — e "
         "250 é rating padrão de 13,8 kV, então pode ser a régua que está incompleta."),
        ("Refazer", "python3 scripts/marca_tensao_53.py"),
    ]:
        ws.cell(row=r, column=1, value=tit).font = Font(bold=True, size=11,
                                                        color=SINAL)
        c = ws.cell(row=r + 1, column=1, value=corpo)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r + 1].height = 15 * (len(corpo) // 108 + 1)
        r += 3

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    wb.save(SAIDA)
    return linhas, confere


if __name__ == "__main__":
    linhas, confere = escreve()
    print("%s · %d ativos" % (SAIDA, len(linhas)))
    print("  marcas:", dict(Counter(x[2].replace(" (inferido)", "")
                                    for x in linhas).most_common()))
    for tipo in ("RL", "RT"):
        sub = [x for x in linhas if x[1] == tipo]
        print("  %s %d: 13,8 kV %d · 34,5 kV %d"
              % (tipo, len(sub), sum(1 for x in sub if x[3] == "13,8 kV"),
                 sum(1 for x in sub if x[3] == "34,5 kV")))
    print("  divergências de tensão entre as três fontes:",
          sum(1 for x in confere if x[7] == "NÃO"))
    sem = [x[0] for x in linhas if x[13] == "inferido"]
    print("  marca sem cadastro (inferida):", sem or "nenhuma")
