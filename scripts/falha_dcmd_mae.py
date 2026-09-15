"""
Falha de equipamentos especiais que passaram pelo DCMD — lida na planilha mãe.

`data/raw/RELIGA_REGULA_2025.xlsx`, aba «Exportar Planilha», é a única base que traz a
DESCRIÇÃO da SS junto da CADEIA montada: 7.638 linhas, 7.634 com parecer. As bases locais
(`ssos_min.json`) não têm texto, e a base crua de 36 MB está fora do repositório — sem
esta planilha não há como ler falha de 2024.

A cadeia vem pronta em duas colunas: `Primeiro == 'primeiro'` marca o começo e
`hierarquia` (formato «SSa->SSb») dá o próximo elo. **A cadeia inteira é UMA falha só** —
o SGM abre SS nova a cada passagem de posto, e repasse não é falha nova.

Régua da data, que foi o pedido do gestor: a falha é datada pela **abertura da PRIMEIRA
SS da cadeia**, antes de a demanda chegar ao posto do DCMD. Não pela SS do DCMD, que é
sempre posterior.

DCMD = posto com «-RD-» no nome.

Três passos, e só o do meio sai daqui:

  1. `lotes()` monta os arquivos de leitura em scratchpad/mae_lotes/ (10 lotes + PROMPT.md)
  2. os agentes leem cada lote e gravam out/loteN.json — um objeto por CADEIA
  3. `consolida()` junta, confere e escreve dist/FALHA_DCMD_MAE.xlsx

A triagem por palavra-chave foi TESTADA E REPROVADA: o regex de peça deixou escapar 6 das
21 falhas conhecidas de 2025 (29%). Todo texto tem de ser lido.

Rodar: python3 scripts/falha_dcmd_mae.py            (consolida o que os agentes gravaram)
       python3 scripts/falha_dcmd_mae.py lotes      (refaz os lotes para uma nova leitura)
"""

import datetime as dt
import glob
import json
import os
import sys
from collections import Counter, defaultdict

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAE = os.path.join(RAIZ, "data", "raw", "RELIGA_REGULA_2025.xlsx")
LOTES = os.path.join(RAIZ, "scratchpad", "mae_lotes")
CACHE = os.path.join(RAIZ, "data", "analise_ia", "falha_dcmd_mae")   # o que os leitores devolveram
LEITURA = os.path.join(RAIZ, "data", "analise_ia", "falha_dcmd_mae.json")
SAIDA = os.path.join(RAIZ, "dist", "FALHA_DCMD_MAE.xlsx")

TINTA, PAPEL, SOMBRA, SINAL, APAGADA = "FF211D15", "FFF2EFE6", "FFE9E5D8", "FFBC4B0E", "FF8D8672"

ANOS = {2024, 2025}
N_LOTES = 10
CORTE_TEXTO = 2600

PECAS_RL = {"tanque", "controle", "completo"}
PECAS_RT = {"celula", "rele", "completo", "furto"}


# ------------------------------------------------------------------ a planilha mãe
def _limpa(t):
    if t is None:
        return ""
    return str(t).replace("_x000D_", "").replace("\r", "").strip()


def _dia(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return None


def ler(caminho=MAE):
    """Devolve (reg, prox): o registro de cada SS e o elo para a SS seguinte."""
    wb = load_workbook(caminho, read_only=True, data_only=True)
    ws = wb["Exportar Planilha"]
    it = ws.iter_rows(values_only=True)
    next(it)
    reg, prox, comeco = {}, {}, []
    for r in it:
        ss = _limpa(r[1])
        if not ss:
            continue
        reg[ss] = {
            "ss": ss,
            "posto": _limpa(r[7]),
            "ativo": _limpa(r[8]),
            "cod_ele": _limpa(r[9]),
            "tipo": _limpa(r[10]),
            "loc": _limpa(r[21]),
            "alimentador": _limpa(r[22]),
            "ocor": _dia(r[11]),
            "abert": _dia(r[12]),
            "concl": _dia(r[16]),
            "status": _limpa(r[20]),
            "pend": _limpa(r[24]),
            "desc": _limpa(r[23]),
        }
        h = _limpa(r[6])
        if "->" in h:
            a, b = h.split("->", 1)
            a, b = a.strip(), b.strip()
            if a and b:
                prox[a] = b
        if _limpa(r[5]).lower() == "primeiro":
            comeco.append(ss)
    wb.close()
    return reg, prox, comeco


def monta_cadeias(reg, prox, comeco):
    """Do começo até o fim do elo, sem repetir SS (guarda contra ciclo)."""
    cadeias = []
    for ss in comeco:
        if ss not in reg:
            continue
        cad, visto, atual = [], set(), ss
        while atual and atual in reg and atual not in visto:
            visto.add(atual)
            cad.append(atual)
            atual = prox.get(atual)
        cadeias.append(cad)
    return cadeias


def do_dcmd(cad, reg):
    return any("-RD-" in reg[s]["posto"] for s in cad)


def recorte(reg, prox, comeco, anos=ANOS):
    """As cadeias que tocaram o DCMD e começaram nos anos pedidos."""
    fora = []
    for cad in monta_cadeias(reg, prox, comeco):
        if not do_dcmd(cad, reg):
            continue
        ab = reg[cad[0]]["abert"]
        if ab and ab.year in anos:
            fora.append(cad)
    fora.sort(key=lambda c: (reg[c[0]]["ativo"], reg[c[0]]["abert"] or dt.date(1900, 1, 1)))
    return fora


# ------------------------------------------------------------------ o que o leitor recebe
PROMPT = """Você lê pareceres técnicos de SS (Solicitações de Serviço) da Energisa Tocantins para decidir se cada equipamento teve FALHA no sentido estrito que o gestor do posto ETO-COEP definiu, e QUAL PEÇA precisava ser trocada.

São religadores (código começa com 79 ou 78) e reguladores de tensão (código 58), todos ativos cuja demanda chegou em algum momento a um posto do DCMD (posto com "-RD-" no nome).

## A régua do gestor (21/08/2026) — o que é falha

Só conta como falha o que exigiu PEÇA GRANDE:
- RELIGADOR: **controle**, **tanque/parte ativa**, ou o **equipamento completo**
- REGULADOR: **célula**, **relé**, o **banco completo**, ou **furto**

Sinônimos de CONTROLE que CONTAM: «placa de alimentação CA», «relé de sincronismo», «armário de controle», «retrofit».
NÃO contam, é telecom: placa de comunicação, placa 3G, rádio, antena. **O que decide é a PEÇA, não a palavra «placa» nem a palavra «relé».**

NÃO é falha, fica de fora: trafo auxiliar, chave faca, rádio, antena, bateria, aterramento, cabo, conector, poste, poda, ajuste de proteção, comissionamento e obra de equipamento novo. Fusível também não é peça grande.

Furto é decidido PELA PEÇA, não pela causa: furto de trafo auxiliar não conta; furto que levou célula ou o equipamento, conta.

## A estrutura do arquivo

Cada ATIVO traz uma ou mais CADEIAS. Uma cadeia é a mesma demanda passando de posto em posto — o sistema abre SS nova a cada passagem, mas **a cadeia inteira é UMA falha só**, nunca várias. O cabeçalho de cada cadeia já diz a data de abertura da PRIMEIRA SS e o caminho dos postos.

## Quatro armadilhas que já derrubaram leituras

1. **A descrição é CUMULATIVA** — o sistema cola parecer novo por cima do antigo, sem separador. Vale sempre o parecer MAIS RECENTE. Um texto pode pedir «trocar tanque» num parecer velho e dizer «equipamento normalizado» no novo.
2. **Texto de terceiro** — laudo de OUTRO ativo colado na descrição. Confira se o código citado é o do bloco antes de acreditar. Já derrubou duas leituras aqui.
3. **«EQUIPAMENTO FICOU EM OPERAÇÃO? NÃO»** significa que NÃO ficou — não inverta.
4. **Quando a SS e a OS discordam, vale a OS** — o parecer conta o defeito, a OS conta o que a obra pagou.

## O que devolver

Um objeto JSON por CADEIA (não por SS). Se o ativo tem três cadeias, devolva três objetos.

- `ativo`: código
- `familia`: "religador" ou "regulador"
- `cadeia`: o número da primeira SS da cadeia (está no cabeçalho ">>> CADEIA n — primeira SS ...")
- `houve_falha`: true/false
- `peca`: "tanque" | "controle" | "completo" | "celula" | "rele" | "furto" — só se houve_falha
- `data_primeira_ss`: a data de abertura da primeira SS da cadeia, como está no cabeçalho (aaaa-mm-dd)
- `executada`: true se o texto diz que a troca foi feita; false se ficou pendente
- `evidencia`: TRECHO LITERAL do parecer que sustenta, copiado do texto (máx. 400 caracteres)
- `confianca`: "alta" | "media" | "baixa"
- `motivo`: uma frase explicando, inclusive quando houve_falha for false

Seja cético: se o texto não sustenta peça grande, `houve_falha` é false. Um "false" honesto vale mais que um "true" que a citação não sustenta.

Responda APENAS com o array JSON, sem texto em volta.
"""


# ------------------------------------------------------------------ passo 1: lotes
def lotes(destino=None):
    reg, prox, comeco = ler()
    cads = recorte(reg, prox, comeco)
    por_ativo = defaultdict(list)
    for c in cads:
        por_ativo[reg[c[0]]["ativo"]].append(c)

    destino = destino or LOTES
    os.makedirs(destino, exist_ok=True)
    ativos = sorted(por_ativo)
    tam = -(-len(ativos) // N_LOTES)
    for n in range(N_LOTES):
        fatia = ativos[n * tam:(n + 1) * tam]
        if not fatia:
            continue
        linhas = []
        for a in fatia:
            linhas.append("ATIVO %s  (%s)" % (a, reg[por_ativo[a][0][0]]["tipo"]))
            linhas.append("#" * 92)
            for i, cad in enumerate(por_ativo[a], 1):
                p = reg[cad[0]]
                linhas.append("")
                linhas.append(
                    "  >>> CADEIA %d — primeira SS %s aberta em %s (ocorrência %s), %d SS, postos: %s"
                    % (i, cad[0], p["abert"], p["ocor"], len(cad),
                       " -> ".join(reg[s]["posto"] for s in cad)))
                linhas.append("")
                for s in cad:
                    d = reg[s]
                    linhas.append("    --- %s | %s | %s | %s" % (s, d["posto"], d["status"], d["pend"]))
                    linhas.append("        aberta %s  concluída %s" % (d["abert"], d["concl"]))
                    t = d["desc"]
                    if len(t) > CORTE_TEXTO:
                        t = t[:CORTE_TEXTO] + " …[texto cortado]"
                    linhas.append("        " + (t or "(sem descrição)").replace("\n", "\n        "))
                    linhas.append("")
        with open(os.path.join(destino, "lote%d.txt" % (n + 1)), "w") as f:
            f.write("\n".join(linhas))
    with open(os.path.join(destino, "PROMPT.md"), "w") as f:
        f.write(PROMPT)
    print("%d cadeias em %d ativos, %d lotes em %s" % (len(cads), len(ativos), N_LOTES, destino))
    return destino


# ------------------------------------------------------------------ passo 3: junta
def junta(pasta=None, cads=None):
    """Junta os lotes lidos. Se a leitura apontou uma SS do MEIO da cadeia em vez da
    primeira, remapeia para a cabeça — aconteceu uma vez e o veredito não muda."""
    pasta = pasta or CACHE
    cabeca = {}
    for c in (cads or []):
        for ss in c:
            cabeca[ss] = c[0]
    saida, vistos, remap = [], set(), []
    for f in sorted(glob.glob(os.path.join(pasta, "lote*.json")),
                    key=lambda p: int("".join(c for c in os.path.basename(p) if c.isdigit()))):
        with open(f) as fh:
            for o in json.load(fh):
                ss = o.get("cadeia")
                if cabeca and ss in cabeca and cabeca[ss] != ss:
                    remap.append((ss, cabeca[ss]))
                    o["cadeia"] = cabeca[ss]
                chave = (o.get("ativo"), o.get("cadeia"))
                if chave in vistos:
                    continue
                vistos.add(chave)
                saida.append(o)
    for de, para in remap:
        print("  cadeia remapeada: %s -> %s (SS do meio apontada como cabeça)" % (de, para))
    return saida


def confere(leitura, reg, cads):
    """Toda cadeia do recorte tem de ter exatamente uma leitura."""
    esperado = {(reg[c[0]]["ativo"], c[0]) for c in cads}
    lido = {(o.get("ativo"), o.get("cadeia")) for o in leitura}
    return sorted(esperado - lido), sorted(lido - esperado)


def familia(tipo, cod):
    if cod == "58" or (tipo or "").upper().startswith("REGULADOR"):
        return "RT"
    return "RL"


def normaliza(o, d):
    """A peça tem de caber na família; peça fora da régua derruba a falha."""
    fam = familia(d["tipo"], d["cod_ele"])
    peca = (o.get("peca") or "").strip().lower().replace("é", "e").replace("ú", "u")
    peca = {"célula": "celula", "relé": "rele", "parte ativa": "tanque",
            "tanque/parte ativa": "tanque", "equipamento completo": "completo"}.get(peca, peca)
    ok = bool(o.get("houve_falha")) and peca in (PECAS_RL if fam == "RL" else PECAS_RT)
    return fam, (peca if ok else ""), ok


# ------------------------------------------------------------------ a planilha
def _titulo(ws, texto, sub=""):
    ws["A1"] = texto
    ws["A1"].font = Font(bold=True, size=13, color=SINAL)
    if sub:
        ws["A2"] = sub
        ws["A2"].font = Font(italic=True, size=9)
        ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[2].height = 46


def _cab(ws, linha, titulos, larguras=None):
    for i, t in enumerate(titulos, 1):
        c = ws.cell(row=linha, column=i, value=t)
        c.font = Font(bold=True, color=PAPEL, size=10)
        c.fill = PatternFill("solid", fgColor=TINTA)
        c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
    ws.cell(row=linha, column=1).alignment = Alignment(vertical="center", horizontal="left")
    if larguras:
        for i, w in enumerate(larguras, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[linha].height = 30
    return linha + 1


def _zebra(ws, linha, n):
    if linha % 2 == 0:
        for i in range(1, n + 1):
            ws.cell(row=linha, column=i).fill = PatternFill("solid", fgColor=SOMBRA)


def monta(linhas, faltando, sobrando, saida=SAIDA):
    wb = Workbook()

    # --------------------------------------------------------- falhas
    ws = wb.active
    ws.title = "Falhas"
    falhas = [l for l in linhas if l["falha"]]
    _titulo(ws, "Falha de equipamentos especiais que passaram pelo DCMD",
            "Uma linha por CADEIA com peça grande. A data é a da abertura da PRIMEIRA SS "
            "da cadeia — antes de a demanda chegar ao DCMD. Fonte: RELIGA_REGULA_2025.xlsx, "
            "aba «Exportar Planilha», lida parecer a parecer.")
    cols = ["Ano", "Ativo", "Tipo", "Peça", "Trocado?", "Primeira SS", "Aberta em",
            "Ocorrência", "SS na cadeia", "Postos", "Localidade", "Alimentador",
            "Confiança", "Evidência do parecer", "Motivo"]
    lin = _cab(ws, 4, cols, [7, 13, 7, 11, 10, 22, 12, 12, 12, 40, 12, 14, 10, 70, 46])
    for f in sorted(falhas, key=lambda x: (x["ano"], x["fam"], x["ativo"])):
        ws.cell(row=lin, column=1, value=f["ano"])
        ws.cell(row=lin, column=2, value=f["ativo"])
        ws.cell(row=lin, column=3, value=f["fam"])
        ws.cell(row=lin, column=4, value=f["peca"])
        ws.cell(row=lin, column=5, value="sim" if f["executada"] else "não")
        ws.cell(row=lin, column=6, value=f["cadeia"])
        ws.cell(row=lin, column=7, value=f["abert"])
        ws.cell(row=lin, column=8, value=f["ocor"])
        ws.cell(row=lin, column=9, value=f["n_ss"])
        ws.cell(row=lin, column=10, value=f["postos"])
        ws.cell(row=lin, column=11, value=f["loc"])
        ws.cell(row=lin, column=12, value=f["alimentador"])
        ws.cell(row=lin, column=13, value=f["confianca"])
        ws.cell(row=lin, column=14, value=f["evidencia"]).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=lin, column=15, value=f["motivo"]).alignment = Alignment(wrap_text=True, vertical="top")
        _zebra(ws, lin, len(cols))
        lin += 1
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = "A4:%s%d" % (get_column_letter(len(cols)), lin - 1)

    # --------------------------------------------------------- resumo
    ws = wb.create_sheet("Resumo")
    _titulo(ws, "Quantas falhas, por ano e por peça",
            "Conta EQUIPAMENTO, não ocorrência: ativo que falhou duas vezes no mesmo ano "
            "conta uma vez naquele ano — e conta de novo se falhar em outro ano.")
    anos = sorted({l["ano"] for l in linhas})
    lin = _cab(ws, 4, ["Ano", "Tipo", "Cadeias lidas", "Cadeias com falha",
                       "Equipamentos que falharam", "Trocas executadas"],
               [8, 8, 15, 18, 26, 18])
    for a in anos:
        for fam in ("RL", "RT"):
            reto = [l for l in linhas if l["ano"] == a and l["fam"] == fam]
            fal = [l for l in reto if l["falha"]]
            ws.cell(row=lin, column=1, value=a)
            ws.cell(row=lin, column=2, value=fam)
            ws.cell(row=lin, column=3, value=len(reto))
            ws.cell(row=lin, column=4, value=len(fal))
            ws.cell(row=lin, column=5, value=len({l["ativo"] for l in fal}))
            ws.cell(row=lin, column=6, value=sum(1 for l in fal if l["executada"]))
            _zebra(ws, lin, 6)
            lin += 1
    lin += 2
    ws.cell(row=lin, column=1, value="Por peça").font = Font(bold=True, color=SINAL)
    lin += 1
    pecas = sorted({l["peca"] for l in linhas if l["falha"]})
    lin = _cab(ws, lin, ["Peça"] + [str(a) for a in anos] + ["Total"],
               [14] + [9] * len(anos) + [9])
    for p in pecas:
        ws.cell(row=lin, column=1, value=p)
        tot = 0
        for i, a in enumerate(anos, 2):
            n = sum(1 for l in linhas if l["falha"] and l["peca"] == p and l["ano"] == a)
            ws.cell(row=lin, column=i, value=n)
            tot += n
        ws.cell(row=lin, column=2 + len(anos), value=tot).font = Font(bold=True)
        _zebra(ws, lin, 2 + len(anos))
        lin += 1

    # --------------------------------------------------------- lidas sem falha
    ws = wb.create_sheet("Lidas sem falha")
    _titulo(ws, "Cadeias que passaram pelo DCMD e NÃO são falha pela régua",
            "O parecer foi lido e não sustenta peça grande. Fica registrado para nada "
            "sumir — trafo auxiliar, chave faca, bateria, ajuste de proteção, "
            "comissionamento e obra de equipamento novo entram aqui.")
    cols = ["Ano", "Ativo", "Tipo", "Primeira SS", "Aberta em", "SS na cadeia",
            "Postos", "Pendência", "Confiança", "Motivo"]
    lin = _cab(ws, 4, cols, [7, 13, 7, 22, 12, 12, 40, 30, 10, 70])
    for f in sorted([l for l in linhas if not l["falha"]],
                    key=lambda x: (x["ano"], x["fam"], x["ativo"])):
        for i, v in enumerate([f["ano"], f["ativo"], f["fam"], f["cadeia"], f["abert"],
                               f["n_ss"], f["postos"], f["pend"], f["confianca"]], 1):
            ws.cell(row=lin, column=i, value=v)
        ws.cell(row=lin, column=10, value=f["motivo"]).alignment = Alignment(wrap_text=True, vertical="top")
        _zebra(ws, lin, len(cols))
        lin += 1
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = "A4:%s%d" % (get_column_letter(len(cols)), lin - 1)

    # --------------------------------------------------------- método
    ws = wb.create_sheet("Como foi feito")
    ws.column_dimensions["A"].width = 118
    _titulo(ws, "Como esta leitura foi feita")
    texto = [
        "A FONTE",
        "data/raw/RELIGA_REGULA_2025.xlsx, aba «Exportar Planilha» — a planilha mãe. 7.638 linhas de SS,",
        "7.634 com DESCRIÇÃO. É a única base disponível que traz o parecer técnico junto da cadeia montada;",
        "o recorte local (ssos_min.json) não tem texto e a base crua de 36 MB está fora do repositório.",
        "",
        "A CADEIA",
        "A coluna «Primeiro» marca o começo e a coluna «hierarquia» («SSa->SSb») dá o elo seguinte. O SGM abre",
        "SS nova a cada passagem de posto, mas repasse não é falha nova: A CADEIA INTEIRA É UMA FALHA SÓ.",
        "",
        "O RECORTE",
        "Cadeias que em algum momento tocaram um posto do DCMD (posto com «-RD-» no nome) e cuja PRIMEIRA SS",
        "foi aberta em 2024 ou 2025.",
        "",
        "A DATA — o pedido do gestor",
        "A falha é datada pela ABERTURA DA PRIMEIRA SS DA CADEIA, antes de a demanda chegar ao DCMD.",
        "A SS do DCMD é sempre posterior; datar por ela joga a falha para a frente.",
        "",
        "A RÉGUA DE FALHA (gestor, 21/08/2026)",
        "Só conta o que exigiu PEÇA GRANDE. Religador: controle, tanque/parte ativa, equipamento completo.",
        "Regulador: célula, relé, banco completo, furto. Contam como controle: placa de alimentação CA,",
        "relé de sincronismo, armário de controle, retrofit. NÃO contam (telecom): placa de comunicação,",
        "placa 3G, rádio, antena. O que decide é a PEÇA, não a palavra «placa» nem a palavra «relé».",
        "Fora da conta: trafo auxiliar, chave faca, bateria, aterramento, cabo, conector, poste, poda,",
        "ajuste de proteção, comissionamento e obra de equipamento novo. Fusível também não é peça grande.",
        "",
        "A LEITURA",
        "Cada cadeia foi lida por inteiro, parecer por parecer — não por palavra-chave. A triagem por regex",
        "de peça foi testada e REPROVADA: deixou escapar 6 das 21 falhas conhecidas de 2025, 29% de fuga.",
        "",
        "AS QUATRO ARMADILHAS",
        "1. A descrição é CUMULATIVA — o SGM cola parecer novo por cima do antigo, sem separador. Vale o mais",
        "   recente: um texto pode pedir «trocar tanque» num parecer velho e dizer «normalizado» no novo.",
        "2. TEXTO DE TERCEIRO — laudo de outro ativo colado na descrição. Conferir o código antes de acreditar.",
        "3. «EQUIPAMENTO FICOU EM OPERAÇÃO? NÃO» significa que NÃO ficou.",
        "4. Quando a SS e a OS discordam, vale a OS.",
        "",
        "A CONFERÊNCIA",
        "Peça que não cabe na família derruba a falha (célula em religador, tanque em regulador).",
        "Toda cadeia do recorte tem de ter exatamente uma leitura — o script confere e aponta o que falta.",
    ]
    lin = 4
    for t in texto:
        c = ws.cell(row=lin, column=1, value=t)
        if t.isupper() or t.startswith("A ") and t == t.upper():
            c.font = Font(bold=True, color=SINAL, size=10)
        elif t and t[0].isupper() and t == t.upper():
            c.font = Font(bold=True, color=SINAL, size=10)
        lin += 1
    if faltando or sobrando:
        lin += 1
        ws.cell(row=lin, column=1, value="PENDÊNCIAS DA CONFERÊNCIA").font = Font(bold=True, color=SINAL)
        lin += 1
        for a, c in faltando:
            ws.cell(row=lin, column=1, value="sem leitura: %s cadeia %s" % (a, c))
            lin += 1
        for a, c in sobrando:
            ws.cell(row=lin, column=1, value="leitura sem cadeia no recorte: %s %s" % (a, c))
            lin += 1

    os.makedirs(os.path.dirname(saida), exist_ok=True)
    wb.save(saida)
    return saida


# ------------------------------------------------------------------ orquestra
def consolida():
    reg, prox, comeco = ler()
    cads = recorte(reg, prox, comeco)
    por_primeira = {c[0]: c for c in cads}
    leitura = junta(cads=cads)
    faltando, sobrando = confere(leitura, reg, cads)

    linhas = []
    for o in leitura:
        cad = por_primeira.get(o.get("cadeia"))
        if not cad:
            continue
        d = reg[cad[0]]
        fam, peca, falha = normaliza(o, d)
        linhas.append({
            "ano": d["abert"].year,
            "ativo": d["ativo"],
            "fam": fam,
            "peca": peca,
            "falha": falha,
            "executada": bool(o.get("executada")),
            "cadeia": cad[0],
            "abert": d["abert"],
            "ocor": d["ocor"],
            "n_ss": len(cad),
            "postos": " -> ".join(reg[s]["posto"] for s in cad),
            "loc": d["loc"],
            "alimentador": d["alimentador"],
            "pend": d["pend"],
            "confianca": o.get("confianca") or "",
            "evidencia": (o.get("evidencia") or "")[:400],
            "motivo": o.get("motivo") or "",
        })

    os.makedirs(os.path.dirname(LEITURA), exist_ok=True)
    with open(LEITURA, "w") as f:
        json.dump({"linhas": [{**l, "abert": str(l["abert"]), "ocor": str(l["ocor"])} for l in linhas],
                   "faltando": faltando, "sobrando": sobrando},
                  f, ensure_ascii=False, indent=1)

    saida = monta(linhas, faltando, sobrando)

    print("cadeias no recorte: %d · lidas: %d · sem leitura: %d · sobrando: %d"
          % (len(cads), len(linhas), len(faltando), len(sobrando)))
    for a in sorted({l["ano"] for l in linhas}):
        for fam in ("RL", "RT"):
            fal = [l for l in linhas if l["ano"] == a and l["fam"] == fam and l["falha"]]
            print("  %d %s: %d cadeias com falha em %d equipamentos — %s"
                  % (a, fam, len(fal), len({l["ativo"] for l in fal}),
                     dict(Counter(l["peca"] for l in fal))))
    print(saida)
    return linhas


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "lotes":
        lotes()
    else:
        consolida()
