"""
Retrospectiva do posto do COEP — o que mudou a partir de abril de 2026, mês a mês, contra 2025.

Pedido do gestor (01/10): «coloque em pauta com base em dados o que melhorou a partir de abril de 2026
mês a mês e o que o COEP avançou que pela base não parece ter sido feito em 2025»; e depois: «ler as SS e
ver a cadeia real, verificar se o equipamento foi atendido mesmo», notando que muito do que andou em
2026 era backlog de 2025 e que dá para rastrear quando as tratativas foram feitas.

AS DATAS CERTAS (scripts/tempo_ss.py)
  O export do SGM sobrescreve a abertura da SS no instante em que ela é repassada: para SS repassada, a
  «abertura» é a SAÍDA do posto. Provado pelos exports de 11/07/2025, 19/08/2026 e 23/09/2026. A chegada
  é o repasse da SS anterior; a saída é o repasse, a conclusão ou o cancelamento. Sem isso a fila do
  COEP parecia igual no começo e no fim do ano e o despacho de 23/04 parecia entrada.

QUATRO FONTES, TODAS DA BASE DE REPASSES DE 23/09 (RELIGA_REGULA_23092026)
1. A PASSAGEM PELO COEP — cada SS do posto: de onde veio, quando chegou e saiu, para onde, e o que o
   COCM fez com a SS seguinte (executou, devolveu, cancelou). Devolveu DEPOIS de executar conta como
   executado, com prova: troca do rol entre o despacho e a volta, parecer do COEP confirmando, ou o texto
   da volta. Dá a fila mês a mês.
2. A LEITURA DAS CADEIAS (skill analise-equipamento, .analise/retro2026) — toda demanda de RL/RT que
   esteve no COEP ou andou depois dele de 01/04 a 23/09/2026: um analista por lote lê TODAS as SS da
   cadeia (o texto que cada uma acrescentou, a chegada e a saída certas, cancelamentos com data e o que
   mudou entre os exports) e monta a linha do tempo das tratativas, se era backlog de 2025, se houve
   tratativa real em 2025 (o diagnóstico que abriu a demanda não conta), se o serviço foi feito (só com
   frase literal) e o desfecho em 23/09. Um verificador adversarial por lote tenta derrubar cada leitura;
   o que ele muda, vale (juntar_retro.py). Status ATENDIDA sem texto, comissionamento sem texto, «favor
   substituir» e «material entregue» não são serviço feito.
3. O PARECER DO COEP — o trecho assinado pelo COEP («PARECER COEP», «COEP:», e o formato antigo «COEP -
   Gerado a EMD…», «COEP (25/07/25) - …»), procurado em todas as SS de RL/RT, sem o texto colado de quem
   abriu a nota e sem repetição. Data escrita manda; sem ela, uma janela — da chegada à saída da SS em
   que o trecho apareceu, apertada pelos exports (se já estava no de 11/07/2025, é de antes) — e o que
   cruza a virada do ano fica fora das contas de 2025 e de 2026. Classificado pelo que faz. «PARECER
   DCMD» vai à parte: os COCMs também assinam assim.
4. O RITMO DE TROCA — do rol da taxa: trocas de falha parada há mais de 30 dias ÷ falha-mês parada. O
   rol começa nas falhas de 2025: troca feita em 2025 de falha de 2024 não aparece, então a contagem de
   2025 é piso; o ritmo por falha parada não depende disso.

Grava dist/RETROSPECTIVA_COEP_2026.xlsx e data/missao/retrospectiva_coep.json.
Rodar: python3 scripts/retrospectiva_coep.py
"""

import datetime as dt
import json
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from statistics import median

import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_mensal as bm  # noqa: E402 — estilo de gráfico e cabeçalho do projeto
import sla_falhas_regional as sf  # noqa: E402 — base de repasses e cadeia
import tempo_ss as ts  # noqa: E402 — chegada e saída certas (o export sobrescreve a abertura no repasse)
import retro_cadeias as rcad  # noqa: E402 — a leitura das cadeias pela skill analise-equipamento

SAIDA = os.path.join(sf.RAIZ, "dist", "RETROSPECTIVA_COEP_2026.xlsx")
JSON = os.path.join(sf.RAIZ, "data", "missao", "retrospectiva_coep.json")
HOJE = sf.HOJE
MES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
MESES = [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, HOJE.month + 1)]
EXECUTA = re.compile(r"PROT|TELE|SE-")             # o COCM passou adiante: ajuste ou comissionamento


def txt(v):
    return re.sub(r"\s+", " ", sf.txt(v)).strip()


def grupo(posto):
    if re.search(r"-RD-", posto):
        return "COCM"
    for chave, nome in (("COEP", "COEP"), ("TELE", "TELE"), ("PROT", "PROT")):
        if chave in posto:
            return nome
    return "SE/outros" if posto else ""


def fim_do_mes(a, m):
    return min(HOJE, dt.datetime(a + m // 12, m % 12 + 1, 1) - dt.timedelta(seconds=1))


# ------------------------------------------------------------------ passagens pelo COEP
def passagens(por, antes):
    out = []
    for k, v in por.items():
        d0 = v[0]
        if "COEP" not in txt(d0["POSTO_SGM"]):
            continue
        ants = [a for a in antes.get(k, ()) if a in por]
        ant = min(ants, key=lambda a: ts.chegada(a, por, antes)) if ants else None
        sai, como, dest = ts.saida(k, por)
        p = {"ss": k, "ativo": txt(d0["EQUIPAMENTO"]), "tipo": txt(d0["PENDENCIA_DO_ATIVO"]),
             "entrada": ts.chegada(k, por, antes), "origem": grupo(txt(por[ant][0]["POSTO_SGM"])) if ant else "aberta no COEP",
             "saida": sai, "como": como, "destino": grupo(dest) if como == "REPASSADA" else como.lower()}
        # depois do COEP: o que o COCM fez com a SS seguinte
        p["depois"], p["execucao"] = "", None
        if p["destino"] == "COCM":
            segs = ts.seguintes(k, por)
            if segs:
                s = segs[0]
                s_sai, s_como, s_dest = ts.saida(s, por)
                if s_como == "ATENDIDA" or (s_como == "REPASSADA" and EXECUTA.search(s_dest)):
                    p["depois"], p["execucao"] = "executou", max(s_sai, sai)   # SS aberta depois do serviço: 0 dia
                elif s_como == "REPASSADA" and "COEP" in s_dest:
                    p["depois"], p["volta"] = "devolveu ao COEP", (s, s_sai)
                elif s_como == "CANCELADA":
                    p["depois"] = "cancelou"
                elif s_como == "REPASSADA":
                    p["depois"] = "passou para outro COCM"
                else:
                    p["depois"] = "segue com o COCM"
        out.append(p)
    return out


SERVICO = re.compile(r"SERVI?[ÇC]?O REALIZADO|FOI SUBSTITU[IÍ]D|EQUIPAMENTO SUBSTITU[IÍ]D|PARA COMISSIONAR|FAVOR COMISSIONAR", re.I)
TROCOU = re.compile(r"FOI TROCAD|FOI SUBSTITU|INSTALADO COM SUCESSO|J[ÁA] INSTALADO", re.I)


def volta_executada(pas, por, antes, acoes, trocas):
    """Despacho que o COCM devolveu ao COEP DEPOIS de executar conta como executado. Prova, nesta ordem: troca do
    rol entre o despacho e a volta; parecer do COEP confirmando a troca nesse intervalo; o texto da SS da volta
    («serviço realizado, favor comissionar»). Sem prova, segue «devolveu ao COEP»."""
    folga = dt.timedelta(days=3)
    for p in pas:
        if p["depois"] != "devolveu ao COEP":
            continue
        s, volta = p["volta"]
        tr = [t for t in trocas.get(p["ativo"], ()) if p["saida"] - folga <= t <= volta + folga]
        conf = [y["data"] for y in acoes if p["ativo"] in y["ativos"] and TROCOU.search(y["texto"])
                and p["saida"].date() <= y["data"] <= (volta + folga).date()]
        seg = [x for x in (d["_seg"] for d in por[s]) if x in por and "COEP" in txt(por[x][0]["POSTO_SGM"])]
        texto = texto_novo(seg[0], por, antes) if seg else ""
        for corpo, _ in segmentos(texto):
            texto = texto.replace(corpo, " ")
        if tr or conf or SERVICO.search(texto):
            quando = min(tr) if tr else volta
            p["depois"], p["execucao"] = "executou e devolveu ao COEP", max(quando, p["saida"])


# ------------------------------------------------------------------ pareceres do COEP
# assinatura do COEP: «PARECER (DO) COEP», «COEP:», «COEP 30/06:» e — o formato de 2023 a 2025 — «COEP - Gerado a
# EMD…» e «COEP (25/07/25) - …». «REPASSADO PARA O COEP - …» é o nome do posto no texto de outro, não assinatura.
INI = re.compile(r"(?:(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?\s*[-–.]?\s*)?(?:PARECER\s*(?:DO\s*)?COEP|"
                 r"(?<![A-Z-])(?<!PARA O )(?<!P/ O )(?<!DO )(?<!PELO )(?<!POSTO )"
                 r"COEP(?=\s*\(?(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)?\)?\s*(?::|[-–]\s)))\s*"
                 r"\(?(?:(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?)?\)?\s*[:\-–]?", re.I)
FIM = re.compile(r"(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\s*[-–.]?\s*)?(?:PARECER\b|PARECE\s+COCM|COCMS?\s*:|"
                 r"DMSL\s*(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)?\s*:|DCMD\s*(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\s*[-:.]|[-:])|"
                 r"\*FEEDBACK|-{5,}|_{5,}|SEGUE (?:NOTA|SS)\b|SOLICITA[ÇC][ÃA]O DE SERVI[ÇC]O|FAVOR PROVIDENCIAR MANUTEN|"
                 r"ENVIAR EQUIPE PARA|NOTA PARA (?:MANUTEN|SUBSTITU)|(?:RELIGADOR|REGULADOR) N[°º])", re.I)
# «PARECER DCMD» / «DCMD 26.03.2026.»: assinatura que aparece em SS da TELE, RD e PROT — fica à parte, só para
# conferir se o que parece novo em 2026 já existia em 2025 com outra assinatura.
DCMD = re.compile(r"()()()(?:PARECER\s*(?:DO\s*)?DCMD|(?<![A-Z-])DCMD(?=\s*(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)?\s*[-:.]))\s*"
                  r"(?:(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?)?\s*[-:.]?", re.I)
TIPOS = [
    ("Compra ou reforma: seleção e andamento", r"SELECIONAD[OA] PARA (?:COMPRA|REFORMA)|COMPRA REALIZADA|\bPMA\b|EM PROCESSO DE AQUISI|POSS[ÍI]VEL REFORMA|"
                                                r"ABRIR PARA COMPRA"),
    ("Entrega do material ao COCM", r"(?:ENTREGUE|FORNECIDO)S? (?:AO|AOS|PARA O|PARA OS) COCM|J[ÁA] ENTREGUE|MATERIAL ENTREGUE|EQUIPAMENTO ENTREGUE"),
    ("Acompanhamento da logística", r"LOG[IÍ]STICA|MATERIAL ENVIADO|\bENVIO\b|\bEMD\b|DEP[ÓO]SITO|GERA[ÇC][ÃA]O DE OBRA|GERAREM (?:AS )?OBRAS?|CRIAREM OBRA|"
                                    r"ABERTURA (?:DE OBRA|CONT[ÁA]BIL)|REQUISI[ÇC][ÃA]O DO MATERIAL|CHEGOU|PREVIS[ÃA]O DE (?:CHEGADA|SUBSTITUI)|EM ROTA"),
    ("Remanejamento de peça", r"REMANEJ|APROVEITAR|SOBRESSALENTE|UTILIZAREMOS|USAREMOS|PEGAREMOS|ORIGINALMENTE|REALOC|(?:PE[ÇC]AS?|MATERIA[LI]S?|CONTROLE|TANQUE|C[ÉE]LULAS?) REDIRECIONAD|PARA UTILIZAR|"
                              r"REMOVEMOS"),
    ("Despacho para execução", r"COCM|SEGUE SS PARA|REALIZAR (?:A )?SUBSTI|FAVOR,? (?:REALIZAR|SUBSTI)|SUBSTIUIR|SUBSTITUIR|REALIZAR (?:O )?ATENDIMENTO"),
    ("Cobrança de registro do campo", r"(?:ESCREVER|ADICIONAR|PREENCHER|DESCREVER)[^.]{0,40}(?:PARECER|PLANILHA|DESCRI|SS\b|SERVI)|INFORMAR (?:O )?PRAZO|INFORMAR PREVIS|EXPLICAR O QUE FOI"),
    ("Confirmação de execução ou operação", r"FOI TROCAD|CONFIRMAM|CONFIRMAD|INSTALADO COM SUCESSO|J[ÁA] INSTALADO|FOI SUBSTITU|CONFORME CONVERSADO|ENCONTRA-SE EM OPERA"),
    ("Triagem do que não é do COEP", r"ABERTURA INCORRETA|NOTA ERRAD|ABRIU (?:NOTA )?ERRAD|REPASSE ERRAD|[ÁA]REA RESPONS|DIRET(?:AMENTE|O) (?:COM|PARA) OS COCM|[ÉE] COM OS COCM|"
                                     r"PARA (?:FAZER )?(?:O )?PRIMEIRO ATAQUE|N[ÃA]O TEM COMPRA DE EQUIPAMENTO|ENVIAR EQUIPE DA TELE"),
    ("Alinhamento e cobrança de prazo", r"J[ÁA] ERA PRA TER|ALINHA(?:MOS|DO)|CONFORME CONVERSADO|URG[ÊE]NCIA|URGENTE|PRIORIDADE|NO M[ÁA]XIMO AT[ÉE]"),
    ("Visita do COEP ao equipamento", r"FIZEMOS UMA VISITA|VISITAMOS|ESTIVEMOS (?:NO|EM)|FOMOS AO"),   # «equipe esteve no local» é do campo
    ("Decisão de não manter ou desativar", r"DESMOBILIZ|N[ÃA]O SER[ÁA] MANTIDO|N[ÃA]O REPOR|N[ÃA]O VAMOS CONSEGUIR MANUTENCION|PODEMOS DESATIVAR"),
    ("Pergunta devolvida ao campo", r"\?|\bQUAL\b|N[ÃA]O FOI ESPECIFICADO|ESPECIFI|REAVALIAR|REVISITAR|EXPLICAR|NECESSITAMOS DO MODELO|FORNECER MODELO"),
    ("SCADA como argumento", r"SCADA|ADMS"),
]


def segmentos(t, marca=INI):
    for m in marca.finditer(t):
        fim = min(next((n.start() for n in FIM.finditer(t, m.end())), len(t)),
                  next((n.start() for n in INI.finditer(t, m.end())), len(t)),    # ou no próximo parecer do COEP
                  next((n.start() for n in marca.finditer(t, m.end())), len(t)))
        fim = min(fim, t.find(" ¦ ", m.end()) if " ¦ " in t[m.end():] else fim)   # começa o texto antigo
        corpo = t[m.end():fim].strip(" :-–,.")
        g = m.groups()
        d, mes, a = (g[0], g[1], g[2]) if g[0] else (g[3], g[4], g[5])
        data = (int(d), int(mes), (int(a) + (2000 if len(a) == 2 else 0)) if a else None) if d else None
        yield corpo, data


def texto_novo(k, por, antes):
    """O que a SS acrescentou ao texto da anterior (o SGM cola o novo antes ou depois do antigo)."""
    t = txt(por[k][0]["DESCRIÇÃO"])
    for a in sorted((a for a in antes.get(k, ()) if a in por), key=lambda a: ts.chegada(a, por, antes)):
        ta = txt(por[a][0]["DESCRIÇÃO"])
        if ta and ta in t:
            t = t.replace(ta, " ¦ ", 1)
    return t


def sem_texto_velho(corpo, velhos):
    """Corta o trecho onde começa texto que já estava numa SS anterior do mesmo ativo — a SS recriada no COEP
    traz colado o texto de quem abriu, e ele não é do COEP. Só corta quando o resto do trecho inteiro (ou 60
    caracteres dele) já estava lá, e quando o que vem antes, na SS velha, não é este mesmo parecer com outra
    digitação («CURSINO» numa, «CURCINO» na outra)."""
    for p in range(8, len(corpo) - 25 + 1):
        for t in velhos:
            i = t.find(corpo[p:p + 25])
            while i >= 0:
                n = 25
                while p + n < len(corpo) and i + n < len(t) and corpo[p + n] == t[i + n]:
                    n += 1
                cabeca = corpo[:p].upper()
                if n >= min(len(corpo) - p, 60) and \
                        SequenceMatcher(None, cabeca, t[max(0, i - len(cabeca)):i].upper()).ratio() < 0.6:
                    return corpo[:p].strip(" :-–,.")
                i = t.find(corpo[p:p + 25], i + 1)
    return corpo


MAE_DATA, D1908 = dt.datetime(2025, 7, 11, 23, 59), dt.datetime(2026, 8, 19, 12, 0)


def pareceres(por, antes, marca=INI, t1908=None, tmae=None):
    """Sem data escrita, o parecer tem uma JANELA: da chegada à saída da primeira SS em que aparece (o texto da
    SS congela quando ela sai), apertada pelos exports — se o trecho já estava no export de 11/07/2025 (ou de
    19/08/2026), foi escrito antes; se a SS já existia e o trecho não estava, foi escrito depois. A data que vai
    para o mês é o fim da janela (o parecer de repasse é escrito no repasse); «certo» diz se a janela inteira
    cai num ano só."""
    acoes = {}
    t1908, tmae = t1908 or {}, tmae or {}
    por_ativo = defaultdict(list)
    for k, v in por.items():
        por_ativo[txt(v[0]["EQUIPAMENTO"])].append((ts.chegada(k, por, antes), txt(v[0]["DESCRIÇÃO"])))
    for k, v in por.items():
        t = texto_novo(k, por, antes)
        if not marca.search(t):
            continue
        ini = ts.chegada(k, por, antes)
        fim = ts.saida(k, por)[0] or HOJE
        velhos = [tv for ab, tv in por_ativo[txt(v[0]["EQUIPAMENTO"])] if ab < ini]
        for corpo, data in segmentos(t, marca):
            corpo = sem_texto_velho(corpo, velhos)
            chave = (re.sub(r"[^A-Z0-9]", "", corpo.upper())[:160], txt(v[0]["EQUIPAMENTO"]))
            if len(chave[0]) < 8:
                continue
            cand = set()
            if data:
                dd, mm, aa = data
                for ano in ([aa] if aa else range(ini.year, fim.year + 1)):
                    try:
                        x = dt.datetime(ano, mm, dd)
                    except ValueError:
                        continue
                    if aa or ini - dt.timedelta(days=3) <= x <= fim + dt.timedelta(days=3):
                        cand.add(x.date())
            r = acoes.setdefault(chave, {"texto": corpo, "cands": [], "ss": set(), "ativos": set(), "primeira": ini,
                                         "saidas": [], "depois_1908": False, "lo": [], "hi": []})
            if cand:
                r["cands"].append(cand)
            r["ss"].add(k)
            r["ativos"].add(txt(v[0]["EQUIPAMENTO"]))
            r["primeira"] = min(r["primeira"], ini)
            sai = ts.saida(k, por)[0]
            if sai:
                r["saidas"].append(sai)
            elif k in t1908 and corpo[:60] not in t1908[k]:
                r["depois_1908"] = True
            lo, hi = ini, sai or HOJE
            for corte, textos in ((MAE_DATA, tmae), (D1908, t1908)):
                if k in textos and ini <= corte:
                    if corpo[:60] in textos[k]:
                        hi = min(hi, corte)
                    else:
                        lo = max(lo, corte)
            r["lo"].append(lo)
            r["hi"].append(hi)
    # o mesmo parecer, no mesmo ativo, com outra digitação («ESTÁ» numa SS, «ESTÃO» na outra) conta uma vez
    chaves = sorted(acoes, key=lambda c: (c[1], -len(acoes[c]["ss"]), c[0]))
    for i, a in enumerate(chaves):
        if a not in acoes:
            continue
        for b in chaves[i + 1:]:
            if b[1] != a[1]:
                break
            if b in acoes and SequenceMatcher(None, a[0], b[0]).ratio() >= 0.9:
                r, x = acoes[a], acoes.pop(b)
                r["cands"] += x["cands"]
                r["ss"] |= x["ss"]
                r["primeira"] = min(r["primeira"], x["primeira"])
                r["saidas"] += x["saidas"]
                r["depois_1908"] |= x["depois_1908"]
                r["lo"] += x["lo"]
                r["hi"] += x["hi"]
    out = []
    for r in acoes.values():
        comum = set.intersection(*r["cands"]) if r["cands"] else set()
        escolha = comum or (set().union(*r["cands"]) if r["cands"] else set())
        if escolha:
            data = max(escolha)
            lo = hi = data
            como = "escrita no texto"
        else:
            # o texto apareceu na SS que chegou primeiro; a janela é a dela, apertada pelos exports
            hi = min(r["hi"]).date()
            lo = min(max(r["lo"]).date(), hi)
            data = hi
            como = f"janela de {lo:%d/%m/%Y} a {hi:%d/%m/%Y}" if lo != hi else "saída da SS"
        tipos = [nome for nome, rx in TIPOS if re.search(rx, r["texto"][:240], re.I)]
        out.append({"data": data, "inicio_janela": lo, "datado": bool(escolha), "como_datou": como,
                    "ano_certo": lo.year == hi.year, "texto": r["texto"], "tipos": tipos,
                    "ativos": sorted(r["ativos"]), "ss": sorted(r["ss"])})
    return sorted(out, key=lambda a: a["data"])


# ------------------------------------------------------------------ o mês
def do_rol():
    """Trocas de peça grande por mês e estoque sem troca no fim do mês, do rol da taxa."""
    with open(sf.JSON, encoding="utf-8") as fh:
        itens = json.load(fh)["itens"]
    dia = lambda s: dt.datetime.strptime(s, "%d/%m/%Y")
    fs = [(dia(x["inicio"]), dia(x["troca"]) if x["troca"] else None, x["dias"]) for x in itens
          if (x["situacao"].startswith("trocada ") and x["dias"] is not None) or x["situacao"].startswith("em aberto")]
    out = {}
    for a, m in MESES:
        ini, fim = dt.datetime(a, m, 1), fim_do_mes(a, m)
        out[(a, m)] = {"trocas": sum(1 for f, t, d in fs if t and ini <= t <= fim),
                       "trocas_lentas": sum(1 for f, t, d in fs if t and ini <= t <= fim and d > 30),
                       "sem_troca": sum(1 for f, t, d in fs if f <= fim and (t is None or t > fim))}
    return out


def mensal(pas, acoes, rol):
    linhas = []
    for a, m in MESES:
        ini, fim = dt.datetime(a, m, 1), fim_do_mes(a, m)
        no_mes = lambda d: d is not None and ini <= d <= fim
        ent = [p for p in pas if no_mes(p["entrada"])]
        sai = [p for p in pas if no_mes(p["saida"]) and p["destino"] != "pendente"]
        fila = [p for p in pas if p["entrada"] <= fim and (p["saida"] is None or p["saida"] > fim)]
        desp = [p for p in sai if p["destino"] == "COCM"]
        exe = [p for p in desp if p["depois"].startswith("executou")]
        dias_exe = [(p["execucao"] - p["saida"]).days for p in exe]
        par = [x for x in acoes if ini.date() <= x["data"] <= fim.date()]
        tipos = Counter(t for x in par for t in x["tipos"])
        L = {"ano": a, "mes": m, "rotulo": f"{MES[m - 1]}/{str(a)[2:]}",
             "entradas": len(ent),
             "de_indisponibilidade": sum(1 for p in ent if p["tipo"] == "INDISPONIBILIDADE PARA OPERAÇÃO"),
             "devolvidas_pelo_cocm": sum(1 for p in ent if p["origem"] == "COCM"),
             "saidas": len(sai), "para_cocm": len(desp),
             "para_tele": sum(1 for p in sai if p["destino"] == "TELE"),
             "para_prot": sum(1 for p in sai if p["destino"] == "PROT"),
             "canceladas": sum(1 for p in sai if p["destino"] == "cancelada"),
             "dias_no_coep": median([(p["saida"] - p["entrada"]).days for p in sai]) if sai else None,
             "fila_no_fim": len(fila),
             "idade_da_fila": median([(fim - p["entrada"]).days for p in fila]) if fila else None,
             "cocm_executou": len(exe), "cocm_devolveu": sum(1 for p in desp if p["depois"] == "devolveu ao COEP"),
             "dias_ate_executar": median(dias_exe) if dias_exe else None,
             "pareceres": len(par), "pareceres_datados": sum(1 for x in par if x["datado"]),
             **{f"tipo:{nome}": tipos[nome] for nome, _ in TIPOS},
             **rol[(a, m)]}
        linhas.append(L)
    return linhas


# ------------------------------------------------------------------ planilha
FILETE = Side(style="thin", color="C8C2AF")


def celulas(ws, r0, dados, negrito=()):
    for j, linha in enumerate(dados):
        for i, v in enumerate(linha, 1):
            c = ws.cell(row=r0 + j, column=i, value=v)
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left" if i == 1 else "center")
            c.border = Border(bottom=FILETE)
            if j % 2:
                c.fill = PatternFill("solid", fgColor=bm.SOMBRA)
            if j in negrito:
                c.font = Font(bold=True)
    return r0 + len(dados)


def titulo(ws, r, texto, sub=None, cols=8):
    ws.cell(row=r, column=1, value=texto).font = Font(bold=True, size=12, color=bm.SINAL)
    if not sub:
        return r + 2
    c = ws.cell(row=r + 1, column=1, value=sub)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    c.font = Font(italic=True, size=9)
    ws.merge_cells(start_row=r + 1, start_column=1, end_row=r + 1, end_column=cols)
    ws.row_dimensions[r + 1].height = 15 * (len(sub) // 140 + 2)
    return r + 3


def aba_pauta(wb, pauta):
    ws = wb.active
    ws.title = "Pauta"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 120
    ws["A1"] = "Retrospectiva do COEP — o que mudou a partir de abril de 2026"
    ws["A1"].font = Font(bold=True, size=14, color=bm.SINAL)
    ws["A2"] = (f"Religador e regulador, base de repasses de {HOJE:%d/%m/%Y}. Cada item tem a conta nas abas "
                "seguintes. Setembro vai até o dia 23.")
    ws.merge_cells("A2:B2")
    r = 4
    for bloco, itens in pauta:
        c = ws.cell(row=r, column=1, value=bloco)
        c.font = Font(bold=True, color=bm.PAPEL)
        c.fill = PatternFill("solid", fgColor=bm.TINTA)
        ws.cell(row=r, column=2).fill = PatternFill("solid", fgColor=bm.TINTA)
        r += 1
        for rot, texto in itens:
            ws.cell(row=r, column=1, value=rot).font = Font(bold=True)
            ws.cell(row=r, column=1).alignment = Alignment(vertical="top", wrap_text=True)
            c = ws.cell(row=r, column=2, value=texto)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 15 * (len(texto) // 115 + 1) + 3
            r += 1
        r += 1


COLS = [("Mês", "rotulo"), ("Entradas no COEP", "entradas"),
        ("Devolvidas por um COCM", "devolvidas_pelo_cocm"), ("Saídas do COEP", "saidas"),
        ("Para o COCM", "para_cocm"), ("Para a TELE", "para_tele"), ("Para a PROT", "para_prot"),
        ("Canceladas no COEP", "canceladas"), ("Dias no COEP (mediana)", "dias_no_coep"),
        ("Fila do COEP no fim do mês", "fila_no_fim"), ("Idade da fila (mediana, dias)", "idade_da_fila"),
        ("Despachos que o COCM já executou", "cocm_executou"), ("Despachos devolvidos ao COEP", "cocm_devolveu"),
        ("Dias do despacho à execução (mediana)", "dias_ate_executar"),
        ("Pareceres do COEP", "pareceres"), ("Pareceres com data", "pareceres_datados"),
        ("Trocas de peça grande", "trocas"), ("Trocas de falha esperando +30 dias", "trocas_lentas"),
        ("Falhas de peça grande sem troca no fim do mês", "sem_troca")]


def aba_mensal(wb, linhas):
    ws = wb.create_sheet("Mês a mês")
    r = titulo(ws, 1, "O posto mês a mês — 2025 inteiro e 2026 até 23/09",
               "Entrada e saída contam SS do posto ETO-COEP. Entrada é o repasse da SS anterior; saída é o repasse da própria SS "
               "(o export grava o instante do repasse na abertura dela), a conclusão ou o cancelamento. «Despachos que o "
               "COCM já executou»: das SS que saíram do COEP para um COCM no mês, quantas o COCM fechou atendida ou passou para "
               "PROT/TELE/SE (a régua 1 do SLA de falhas). As três últimas colunas vêm do rol da taxa (falhas de peça grande).",
               len(COLS))
    bm.cabecalho(ws, r, [c for c, _ in COLS], [10] + [11] * (len(COLS) - 1))
    ws.row_dimensions[r].height = 58
    celulas(ws, r + 1, [[L[k] for _, k in COLS] for L in linhas])
    ws.freeze_panes = ws.cell(row=r + 1, column=2)
    # gráfico: pareceres do COEP e trocas de peça grande por mês
    ch = BarChart()
    ch.type, ch.grouping, ch.overlap, ch.gapWidth = "col", "clustered", -10, 60
    cp = [k for _, k in COLS].index("pareceres") + 1
    ch.add_data(Reference(ws, min_col=cp, max_col=cp, min_row=r, max_row=r + len(linhas)), titles_from_data=True)
    ct = [k for _, k in COLS].index("trocas") + 1
    ch.add_data(Reference(ws, min_col=ct, max_col=ct, min_row=r, max_row=r + len(linhas)), titles_from_data=True)
    ch.title = "Pareceres do COEP e trocas de peça grande, por mês"
    ch.y_axis.title = "quantidade"
    bm.cor_barra(ch.series[0], bm.LARANJA)
    bm.cor_barra(ch.series[1], bm.VERDE)
    ch.legend.position, ch.legend.overlay = "b", False
    bm.categorias(ch, ws, "$A$%d:$A$%d" % (r + 1, r + len(linhas)))
    ws.add_chart(bm.estilo(ch, 10, 30), f"A{r + len(linhas) + 3}")


def aba_novo(wb, novo):
    ws = wb.create_sheet("O que é novo")
    r = titulo(ws, 1, "O que o COEP passou a fazer — pareceres por tipo, 2025 × 2026",
               "Cada parecer do COEP contado uma vez, pela data escrita nele. Um parecer pode fazer mais de uma coisa. "
               "«PARECER DCMD» vai em coluna à parte: a assinatura aparece também em SS da TELE, RD e PROT, e não dá para dizer "
               "que é do COEP. O exemplo é um parecer real de abr–set/2026.", 8)
    bm.cabecalho(ws, r, ["O que o parecer faz", "Antes de 2025", "2025 (12 meses)", "jan–mar/2026", "abr–set/2026",
                         "Sem data certa (janela cruza a virada)", "«PARECER DCMD» em 2025", "«PARECER DCMD» em abr–set/2026",
                         "Exemplo de 2026"],
                 [34, 10, 12, 12, 12, 13, 13, 13, 100])
    ws.row_dimensions[r].height = 45
    celulas(ws, r + 1, [[x["tipo"], x["antes de 2025"], x["2025"], x["jan-mar/26"], x["abr-set/26"], x["incerto"], x["dcmd 2025"],
                         x["dcmd abr-set/26"], x["exemplo"]] for x in novo])


def aba_pareceres(wb, acoes):
    ws = wb.create_sheet("Pareceres do COEP")
    bm.cabecalho(ws, 1, ["Data (fim da janela)", "Como foi datado", "O que faz", "Ativos", "Parecer"], [11, 24, 40, 24, 120])
    celulas(ws, 2, [[x["data"], x["como_datou"], " · ".join(x["tipos"]),
                     ", ".join(x["ativos"][:4]) + (" …" if len(x["ativos"]) > 4 else ""), x["texto"][:600]]
                    for x in acoes if x["data"].year >= 2025])
    for row in ws.iter_rows(min_row=2, min_col=1, max_col=1):
        row[0].number_format = "DD/MM/YYYY"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:E{ws.max_row}"


def aba_passagens(wb, pas):
    ws = wb.create_sheet("Passagens")
    bm.cabecalho(ws, 1, ["SS do COEP", "Ativo", "Tipo da SS", "Entrou", "Veio de", "Saiu", "Para onde",
                         "Dias no COEP", "Depois, no COCM", "Executou em"],
                 [20, 12, 26, 11, 12, 11, 12, 9, 18, 11])
    celulas(ws, 2, [[p["ss"], p["ativo"], p["tipo"], p["entrada"], p["origem"], p["saida"], p["destino"],
                     (p["saida"] - p["entrada"]).days if p["saida"] else (HOJE - p["entrada"]).days,
                     p["depois"], p["execucao"]]
                    for p in sorted(pas, key=lambda p: p["entrada"])])
    for col in ("D", "F", "J"):
        for c in ws[col][1:]:
            c.number_format = "DD/MM/YYYY"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:J{ws.max_row}"


def aba_como(wb):
    ws = wb.create_sheet("Como foi feito")
    for linha in (__doc__ or "").strip().splitlines():
        ws.append([linha])
    ws.column_dimensions["A"].width = 110


# ------------------------------------------------------------------ montagem
def soma(linhas, chave, ano, meses):
    return sum(L[chave] or 0 for L in linhas if L["ano"] == ano and L["mes"] in meses)


# nome de pessoa no exemplo: «COM O FULANO», «FULANO INFORMOU» — o exemplo da pauta prefere o parecer sem nome
NOME = re.compile(r"(?:COM|PELO|PELA)\s+(?:O\s+|A\s+)?(?!COCM|COI\b|DMSL|DCMD|TELE|PROT|COEP|ASPO|OPERA|EQUIPE|POSTO|SCADA|FALTA|"
                  r"[ÁA]REA|NOTA|OBRA|PE[ÇC]A|PARTE|PRIORIDADE|URG[ÊE]NCIA|SUCESSO|DEFEITO|ASSUNTO|LAUDO|FOTOS?\b)[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,}|"
                  r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,} INFORMOU")


def faixa(d):
    if d.year < 2025:
        return "antes de 2025"
    if d.year == 2025:
        return "2025"
    return "jan-mar/26" if d.month <= 3 else "abr-set/26"


def novidades(acoes, dcmd):
    norm = lambda x: re.sub(r"[^A-Z]", "", x["texto"].upper())[:60]
    out, usados = [], set()
    for nome, _ in TIPOS:
        xs = [x for x in acoes if nome in x["tipos"]]
        c = Counter(faixa(x["data"]) for x in xs if faixa(x["data"]) == faixa(x["inicio_janela"]))
        incerto = sum(1 for x in xs if faixa(x["data"]) != faixa(x["inicio_janela"]) and x["data"] >= dt.date(2025, 1, 1))
        cd = Counter(faixa(x["data"]) for x in dcmd if nome in x["tipos"])
        # o exemplo: parecer datado de abr–set/2026, sem nome de pessoa quando der, o texto que mais se repete entre equipamentos
        cand = [x for x in xs if x["data"] >= dt.date(2026, 4, 1) and x["datado"]]
        freq = Counter(norm(x) for x in cand)
        ex = sorted(cand, key=lambda x: (norm(x) in usados, bool(NOME.search(x["texto"].upper())), -freq[norm(x)], len(x["tipos"]),
                                         -min(len(x["texto"]), 200)))
        exemplo = ""
        if ex:
            e = ex[0]
            usados.add(norm(e))
            exemplo = (f"{e['data']:%d/%m}: «{e['texto'][:220]}»"
                       + (f" (o mesmo texto aparece em {freq[norm(e)]} equipamentos)" if freq[norm(e)] > 1 else ""))
        out.append({"tipo": nome, **{k: c[k] for k in ("antes de 2025", "2025", "jan-mar/26", "abr-set/26")}, "incerto": incerto,
                    "dcmd 2025": cd["2025"], "dcmd abr-set/26": cd["abr-set/26"], "exemplo": exemplo})
    return out


def compras():
    """As requisições de compra da aba Estoque da COEP 5 (Tabela7): data, itens, quantidade, valor, status."""
    ws = openpyxl.load_workbook(os.path.join(sf.RAW, "GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP_5.xlsx"), data_only=True)["Estoque"]
    req = {}
    for r in ws.iter_rows(min_row=36, max_row=100, max_col=13, values_only=True):
        if r[0] is None or r[9] is None:
            continue
        x = req.setdefault(r[9], {"data": r[8].date() if r[8] else None, "itens": {}, "status": r[11]})
        x["itens"].setdefault((r[1], r[2]), [0, r[5]])[0] += 1          # uma linha por peça
    out = []
    for numero, x in sorted(req.items(), key=lambda kv: kv[1]["data"]):
        qtd = sum(q for q, _ in x["itens"].values())
        valor = sum(q * u for q, u in x["itens"].values())
        rt = any(str(c).startswith(("651638", "6902", "690669")) for c, _ in x["itens"])
        out.append({"requisicao": numero, "data": x["data"], "pecas": qtd, "valor": round(valor, 2),
                    "status": x["status"], "tem_regulador": rt})
    return out


COMPRA, ENTREGA, LOGIST, REMANEJ = ("Compra ou reforma: seleção e andamento", "Entrega do material ao COCM",
                                     "Acompanhamento da logística", "Remanejamento de peça")
MATERIAL = {COMPRA, ENTREGA, LOGIST, REMANEJ}
PERGUNTA = {"Pergunta devolvida ao campo", "SCADA como argumento"}
FALTA = re.compile(r"N[ÃA]O RECEBEMOS (?:O )?MATERIAL|VEIO ERRAD|REQUISI[ÇC][ÃA]O (?:DE |DO )?MATERIAL|N[ÃA]O TEMOS O MATERIAL|"
                   r"PROVIDENCIAR MATERIAL|FALTA DE MATERIAL|AGUARDANDO (?:O )?MATERIAL", re.I)
IND = "INDISPONIBILIDADE PARA OPERAÇÃO"
CURTO = {IND: "fora de operação", "OBRAS (NOVOS EQUIPAMENTOS)": "obra nova", "EM OPERAÇÃO COM ANOMALIA": "anomalia",
         "AVISO DE ANOMALIA": "aviso", "AVISO PROTEÇÃO & SELETIVIDADE": "aviso", "COMISSIONAMENTO": "comissionamento",
         "AJUSTE DE PROTEÇÃO": "ajuste de proteção", "SOLICITAÇÃO DE SERVIÇO": "solicitação de serviço"}


def lista(c):
    """Counter → «obra nova (5), anomalia (2) e aviso (3)»."""
    partes = [f"{k} ({n})" for k, n in c.most_common()]
    return " e ".join([", ".join(partes[:-1]), partes[-1]]) if len(partes) > 1 else (partes[0] if partes else "")


def pct(x):
    return f"{100 * x:.1f}".replace(".", ",") + "%"


def plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def pauta(pas, acoes, linhas, novo, extra):
    L = {(l["ano"], l["mes"]): l for l in linhas}
    t = lambda a, m, nome: L[(a, m)][f"tipo:{nome}"]
    soma = lambda chave, ano: sum(l[chave] or 0 for l in linhas if l["ano"] == ano and 4 <= l["mes"] <= 9)
    X = extra
    C = X.get("cadeias")                     # a leitura das cadeias pela skill (None se ainda não rodou)
    lote, trocados, volta = X["lote_2304"], X["lote_trocados"], X["lote_volta"]
    dez, abr, mai, jun, jul, ago, st = L[(2025, 12)], *(L[(2026, m)] for m in (4, 5, 6, 7, 8, 9))
    serie = [l for l in linhas if (l["ano"], l["mes"]) <= (2026, 9)]
    NOMES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
    pico = max(serie, key=lambda l: l["fila_no_fim"])
    menor_desde = next((f"{NOMES[l['mes'] - 1]} de {l['ano']}" for l in reversed(serie[:-1]) if l["sem_troca"] <= st["sem_troca"]), None)
    reqs = lambda mes: [r for r in X["compras"] if r["data"] and (r["data"].year, r["data"].month) == (2026, mes)]
    datas = lambda rs: ", ".join(sorted({r["data"].strftime("%d/%m") for r in rs}))
    sai_25 = sum(L[(2025, m)]["saidas"] for m in range(1, 13))
    ent_25 = sum(L[(2025, m)]["entradas"] for m in range(1, 13))
    sai_ago_dez = [L[(2025, m)]["saidas"] for m in range(8, 13)]
    abr_set = lambda chave: sum(L[(2026, m)][chave] for m in range(4, 10))
    fila = [
        ("A curva", f"{X['fila_fim_2024']} SS paradas no COEP no fim de 2024 → {dez['fila_no_fim']} no fim de 2025 → "
                    f"{pico['fila_no_fim']} no fim de {NOMES[pico['mes'] - 1]} de {pico['ano']}, o pico, com idade mediana de "
                    f"{pico['idade_da_fila']:.0f} dias → {st['fila_no_fim']} em 23/09/2026, idade mediana de {st['idade_da_fila']:.0f} dias."),
        ("2025 encheu", f"Em 2025 o posto recebeu {ent_25} SS e despachou {sai_25}. De agosto a dezembro de 2025 as saídas quase "
                        f"pararam: {' · '.join(str(x) for x in sai_ago_dez)} por mês."),
        ("Abril a setembro esvaziou", f"Saíram {abr_set('saidas')} SS do COEP: {abr_set('para_cocm')} mandadas ao COCM, "
                                      f"{abr_set('para_tele')} devolvidas à TELE, {abr_set('para_prot')} à PROT e {abr_set('canceladas')} "
                                      f"canceladas. Entraram {abr_set('entradas')}."),
        ("A data certa", "O export do SGM grava o instante do repasse por cima da abertura da SS. Lida pela abertura, a fila parecia "
                         "igual no começo e no fim do ano e o «lote de 23/04» parecia entrada; com a chegada certa (o repasse da SS "
                         "anterior), a fila tem esta curva."),
    ]
    pm = C["pm"] if C else {}

    def cadeias_no_mes(m):
        c = pm.get((2026, m))
        if not c:
            return ""
        top = ", ".join(f"{n} {a}" for a, n in c["acoes"].most_common(4))
        txt_ = f" Nas cadeias: {plural(c['tratativas'], 'tratativa', 'tratativas')} em {plural(c['demandas'], 'demanda', 'demandas')} ({top})."
        if c["execucoes"]:
            txt_ += (f" {plural(c['execucoes'], 'execução', 'execuções')} com prova escrita ({c['execucoes_backlog']} do backlog de 2025"
                     + (f"; {c['execucoes_com_operacao']} com a volta à operação provada" if c["execucoes_com_operacao"] else "") + ").")
        else:
            txt_ += " Nenhuma execução com prova escrita."
        if c["backlog_primeira_tratativa"]:
            txt_ += f" {plural(c['backlog_primeira_tratativa'], 'demanda do backlog de 2025 teve', 'demandas do backlog de 2025 tiveram')} a primeira tratativa do ano."
        return txt_

    def posto_no_mes(l):
        return (f" No posto: saíram {l['saidas']} SS ({l['para_cocm']} ao COCM, {l['para_tele']} à TELE, {l['canceladas']} canceladas) e "
                f"entraram {l['entradas']}; a fila fechou em {l['fila_no_fim']}. Trocas de peça grande no rol: {l['trocas']}.")

    meses = [
        ("Abril", f"Em 23/04 o COEP despachou {plural(len(lote), 'SS', 'SS')} para os COCMs, paradas no posto havia "
                  f"{X['lote_dias_parado']:.0f} dias (mediana), {X['lote_desde_2025']} delas desde 2025 ou antes."
                  + cadeias_no_mes(4) + posto_no_mes(abr)),
        ("Maio", f"Cancelamentos em lote começaram: {mai['canceladas']} no COEP." + cadeias_no_mes(5) + posto_no_mes(mai)),
        ("Junho", f"Saneamento: em 29/06 o COEP devolveu SS à TELE com pergunta ou pedido de reavaliação ({X['perguntas_2906']} "
                  f"pareceres naquele dia) e em 30/06 cancelou {X['cancel_3006']} SS de uma vez, no mesmo dia em que outros postos "
                  f"cancelaram em bloco ({X['cancel_3006_total']} SS de RL/RT canceladas no SGM em 30/06)."
                  + cadeias_no_mes(6) + posto_no_mes(jun)),
        ("Julho", f"O mês da execução e do material: {jul['para_cocm']} SS mandadas ao COCM, o maior número da série; o COEP registrou "
                  f"{t(2026, 7, ENTREGA) + t(2026, 7, LOGIST)} pareceres de entrega e logística e {t(2026, 7, COMPRA)} de compra."
                  + cadeias_no_mes(7) + posto_no_mes(jul)
                  + (f" Fora da base: {plural(len(reqs(7)), 'requisição de compra', 'requisições de compra')} em {datas(reqs(7))}." if reqs(7) else "")),
        ("Agosto", "Mês de pouca entrada e pouca execução." + cadeias_no_mes(8) + posto_no_mes(ago)
                   + (" O COEP registrou um erro no envio de material: o controle enviado não era o do equipamento porque a SS não "
                      "trazia o modelo." if X["envio_errado"] else "")),
        ("Setembro (até 23/09)", f"Logística e remanejamento de peça no texto do COEP ({t(2026, 9, LOGIST)} e {t(2026, 9, REMANEJ)} "
                                 f"pareceres), {t(2026, 9, 'Decisão de não manter ou desativar')} decisão de não manter um regulador este ano."
                                 + cadeias_no_mes(9) + posto_no_mes(st)
                                 + (f" Falhas de peça grande sem troca: {st['sem_troca']}, o menor número desde {menor_desde}." if menor_desde else "")
                                 + (f" Fora da base: requisição de compra de {datas(reqs(9))}." if reqs(9) else "")),
    ]
    backlog, verdade = [], []
    if C:
        R, rel = C["res"], C["rel"]
        backlog = [
            ("Quanto era backlog", f"Das {R['demandas']} demandas que estiveram no COEP ou andaram depois dele de abril a setembro "
                                   f"({R['ativos']} equipamentos), {R['backlog']} vinham de 2025 ou antes e seguiam abertas na virada do ano. "
                                   f"Outras {R['duplicadas']} cadeias eram a mesma demanda reaberta ou aberta por engano e não entram na conta."),
            ("Andou em 2025?", f"Em {R['backlog_sem_tratativa_em_2025']} dessas {R['backlog']}, nada foi feito em 2025 depois do diagnóstico "
                               f"que abriu a demanda: a primeira tratativa veio em 2026. {R['backlog_com_tratativa_em_2026']} das "
                               f"{R['backlog']} tiveram alguma tratativa em 2026."),
            ("Como o backlog estava em 23/09", lista(R["desfecho_backlog"]) + "."),
        ]
        verdade = [
            ("Serviço feito, com prova escrita", f"{R['executadas']} das {R['demandas']} demandas ({R['executadas_no_periodo']} de abril em "
                                                 f"diante; {R['executadas_backlog']} do backlog de 2025). Em {R['operando_provado']} o texto prova "
                                                 f"que o equipamento voltou a operar depois do serviço"
                                                 + (f"; em {R['nao_voltou']} diz que não voltou" if R["nao_voltou"] else "") + "."),
            ("Desfecho de todas em 23/09", lista(R["desfecho"]) + "."),
            ("Feito, mas sem registro no SGM", f"Em {plural(len(R['gestao_sem_frase']), 'equipamento', 'equipamentos')} a Gestão marca "
                                               f"«Realizado» e nenhuma SS da cadeia tem frase que prove o serviço ({', '.join(R['gestao_sem_frase'])}). "
                                               f"Aqui a lacuna é de registro, não necessariamente de execução — mas, pela base, não dá para contar."
             if R["gestao_sem_frase"] else "Nenhum equipamento com «Realizado» na Gestão ficou sem frase de serviço no SGM."),
            ("O que a verificação derrubou", f"O verificador adversarial mudou {rel['derrubadas']} das {rel['verificadas']} leituras do analista"
                                             + (": " + lista(Counter({k: v for k, v in rel["mudou_por_campo"].items() if v})) if rel["mudou_por_campo"] else "")
                                             + ". Status ATENDIDA sem texto, comissionamento sem texto e «favor substituir» não contam como serviço feito."),
        ]
    r25, r26 = X["ritmo_abr_set_25"], X["ritmo_abr_set_26"]
    ra, rd = X["ritmo_ate_abr_26"], X["ritmo_mai_set_26"]
    nao_ind = Counter(CURTO.get(p, p.lower()) for p in X["exec_tipos_2025"] if p != IND)
    comparar = [
        ("Trocas de peça grande", f"{soma('trocas', 2025)} em abr–set/2025 → {soma('trocas', 2026)} em abr–set/2026 "
                                  f"({soma('trocas_lentas', 2025)} → {soma('trocas_lentas', 2026)} de falha parada havia mais de 30 dias). "
                                  f"O {soma('trocas', 2025)} é piso: o rol de falhas começa nas de 2025, então troca feita em 2025 de falha "
                                  f"de 2024 não aparece. Por falha parada, a conta que não depende disso, a chance de troca no mês foi "
                                  f"{pct(r25[0] / r25[1])} em abr–set/2025 (só {r25[0]} trocas, amostra fraca) e {pct(r26[0] / r26[1])} em "
                                  f"abr–set/2026. A virada firme é maio de 2026: {pct(ra[0] / ra[1])} ao mês de jan/2025 a abr/2026, "
                                  f"{pct(rd[0] / rd[1])} de maio a setembro."),
        ("Material antes da troca", f"Das {X['mat_26'][1]} trocas de abr–set/2026, {X['mat_26'][0]} tiveram antes um parecer do COEP sobre "
                                    f"o material (compra, entrega, logística ou remanejamento); das {X['mat_25'][1]} de abr–set/2025, "
                                    f"{X['mat_25'][0]}."),
        ("Despacho que vira execução", f"Das SS que o COEP mandou ao COCM em abr–set, o COCM executou {soma('cocm_executou', 2025)} em 2025 e "
                                       f"{soma('cocm_executou', 2026)} em 2026, contando quem executou e devolveu a SS ao COEP. A diferença está "
                                       f"no que é: em 2026, {X['exec_ind_2026']} das {soma('cocm_executou', 2026)} eram equipamento fora de "
                                       f"operação; em 2025, {X['exec_ind_2025']} das {soma('cocm_executou', 2025)} — o resto era "
                                       f"{lista(nao_ind)}."),
        ("Parecer do COEP", f"{X['par_2025']} em 2025 inteiro ({X['datados_2025']} com data escrita) → {X['par_abrset26']} em abr–set/2026 "
                            f"({soma('pareceres_datados', 2026)} com data escrita), contando só os que caem com certeza no período; "
                            f"{X['par_incertos']} têm a janela cruzando a virada do ano ou o começo de abril e ficam de fora das duas contas."),
        ("O caminho da SS mudou", f"Em abr–set/2025, {soma('para_prot', 2025)} SS saíram do COEP direto para a PROT — "
                                  f"{X['prot_da_tele_2025']} tinham chegado da TELE, e em {X['prot_trocado_2025']} o texto já dizia que o "
                                  f"equipamento foi trocado e pedia o comissionamento: o COEP era passagem entre a troca e a PROT. Em "
                                  f"abr–set/2026, {soma('para_prot', 2026)}. Obra de equipamento novo entrando no posto: {X['obras_2025']} → "
                                  f"{X['obras_2026']}. Dos despachos do COEP ao COCM, os que o COCM levou direto para PROT, TELE ou SE foram "
                                  f"{X['cocm_adiante_2025']} em 2025 e {X['cocm_adiante_2026']} em 2026."),
    ]
    def item(x):
        txt_ = (f"{x['2025']} em 2025" + (f", {x['jan-mar/26']} em jan–mar/2026" if x["jan-mar/26"] else "")
                + f" → {x['abr-set/26']} em abr–set/2026.")
        if x["antes de 2025"]:
            txt_ += f" Antes de 2025, {x['antes de 2025']}."
        if x["incerto"]:
            txt_ += f" Mais {x['incerto']} sem data certa: a janela em que foram escritos cruza a virada de 2025 para 2026 ou abril."
        if x["dcmd 2025"]:
            txt_ += f" Em 2025 houve mais {x['dcmd 2025']} com a assinatura «PARECER DCMD», que não dá para dizer se é do COEP."
        return x["tipo"], txt_ + (f" Ex.: {x['exemplo']}" if x["exemplo"] else "")
    fora = PERGUNTA
    sem_2025 = [x for x in novo if x["2025"] == 0 and x["dcmd 2025"] == 0 and x["abr-set/26"] >= 3 and x["tipo"] not in fora]
    cresceu = [x for x in novo if x not in sem_2025 and x["abr-set/26"] > x["2025"] and x["abr-set/26"] >= 3 and x["tipo"] not in fora]
    P = X["perguntas"]
    V25, V26 = X["voltas_2025"], X["voltas_2026"]
    atencao = [
        ("Perguntas que o cadastro já respondia", f"{P['n']} pareceres de abr–set/2026 devolveram pergunta ao campo ou usaram o SCADA "
                                                  f"para questionar a troca, {P['em_2906']} deles em 29/06. {P['modelo']} pediam modelo, marca, "
                                                  f"tensão ou potência; {P['placa']} deles, o modelo ou o código da placa, que o cadastro não "
                                                  f"traz — os outros {P['modelo'] - P['placa']} pediam modelo ou tensão que o cadastro de ajustes da proteção "
                                                  f"já tem preenchido (relé e tensão do religador, controlador e potência do regulador) para "
                                                  f"{P['no_cadastro']} dos {P['ativos']} equipamentos perguntados. Em 23/09, desses "
                                                  f"{P['ativos']}: {P['desfecho'].get('segue aberta no COEP', 0)} seguiam abertos no COEP, "
                                                  f"{P['desfecho'].get('saiu do COEP sem troca no rol', 0)} tinham saído do COEP sem troca "
                                                  f"registrada, {P['desfecho'].get('trocada depois', 0)} tiveram a peça trocada e "
                                                  f"{P['desfecho'].get('cancelada', 0)} foram cancelados."),
        ("SS que voltam do COCM sem serviço registrado", f"Voltaram do COCM para o COEP sem registro de serviço feito "
                                              f"{sum(V25.values()) - V25['serviço feito']} "
                                              f"SS em abr–set/2025 e {sum(V26.values()) - V26['serviço feito']} em 2026, com o despacho ao "
                                              f"COCM indo de {soma('para_cocm', 2025)} para {soma('para_cocm', 2026)}. O SGM não guarda o "
                                              f"motivo da volta; pelo texto, em 2026, {V26['faltou material']} foram por falta de material, "
                                              f"material errado ou obra de requisição e {V26['sem motivo escrito']} não têm motivo escrito "
                                              f"({X['lote_sem_motivo']} delas do lote de 23/04). Outras {V26['serviço feito']} voltaram com o "
                                              f"serviço feito, para seguir ao comissionamento ({V25['serviço feito']} em 2025)."),
        ("Cancelamento sem motivo escrito", f"{soma('canceladas', 2025)} cancelamentos no posto em abr–set/2025 → {soma('canceladas', 2026)} em "
                                            f"2026. Dos {X['canc_resolvidos']} «resolvidos» por cancelamento de mai–jul, só "
                                            f"{X['canc_com_prova']} têm no texto a prova de que o equipamento voltou a operar."),
    ]
    if C:
        R = C["res"]
        d = R["desfecho"]
        atencao.insert(0, ("O que segue aberto", f"{d.get('pendente: compra ou material', 0)} demandas esperando compra ou material, "
                                                 f"{d.get('pendente: no campo', 0)} com o campo sem execução registrada, "
                                                 f"{d.get('pendente: parada no COEP', 0)} paradas no COEP sem tratativa; "
                                                 f"{d.get('executado, falta comissionar ou ajustar', 0)} com o serviço feito esperando "
                                                 f"comissionamento ou ajuste; {d.get('executado, sem prova de operação', 0)} executadas sem "
                                                 f"prova de que voltaram a operar; {d.get('cancelado sem prova', 0)} canceladas sem prova."))
    blocos = [("A fila do COEP, com as datas certas", fila), ("Abril a setembro de 2026, mês a mês", meses)]
    if C:
        blocos += [("O backlog de 2025 tratado em 2026", backlog), ("Atendido de verdade?", verdade)]
    return blocos + [("Contra os mesmos meses de 2025", comparar),
                     ("O que o COEP passou a fazer e a base não mostra em 2025", [item(x) for x in sem_2025]),
                     ("O que já existia em 2025 e cresceu", [item(x) for x in cresceu]),
                     ("O que falta", atencao)]


def ritmo(itens, a, b):
    """Trocas de falha parada há mais de 30 dias ÷ falha-mês parada (dias depois do 30º, inclusive, ÷ 30,4) entre a e b."""
    dia = lambda s: dt.datetime.strptime(s, "%d/%m/%Y").date()
    fs = [(dia(x["inicio"]), dia(x["troca"]) if x["troca"] else None, x["dias"]) for x in itens
          if (x["situacao"].startswith("trocada ") and x["dias"] is not None) or x["situacao"].startswith("em aberto")]
    ev = sum(1 for f, tr, d in fs if tr and d > 30 and a <= tr <= b)
    exp = sum(max(0, (min(b, tr or HOJE.date()) - max(a, f + dt.timedelta(days=31))).days + 1) for f, tr, d in fs)
    return ev, exp / 30.4


def motivo_da_volta(p, por, antes, trocas, acoes):
    """Por que a SS voltou do COCM ao COEP, pelo que está escrito: serviço feito, faltou material ou sem motivo."""
    ants = [a for a in antes.get(p["ss"], ()) if a in por]
    ant = min(ants, key=lambda a: ts.chegada(a, por, antes))
    texto = texto_novo(p["ss"], por, antes) + " ¦ " + texto_novo(ant, por, antes)
    for corpo, _ in segmentos(texto):
        texto = texto.replace(corpo, " ")
    folga, ini = dt.timedelta(days=3), ts.chegada(ant, por, antes)
    tr = [x for x in trocas.get(p["ativo"], ()) if ini - folga <= x <= p["entrada"] + folga]
    conf = [y for y in acoes if p["ativo"] in y["ativos"] and TROCOU.search(y["texto"]) and ini.date() <= y["data"] <= (p["entrada"] + folga).date()]
    if tr or conf or SERVICO.search(texto):
        return "serviço feito"
    return "faltou material" if FALTA.search(texto) else "sem motivo escrito"


def main():
    por, antes, _ = sf.base()
    pas = passagens(por, antes)
    t1908, tmae = ts.textos_export_1908(), ts.textos_export_mae()
    acoes = pareceres(por, antes, t1908=t1908, tmae=tmae)
    dcmd = pareceres(por, antes, DCMD, t1908=t1908, tmae=tmae)
    with open(sf.JSON, encoding="utf-8") as fh:
        itens = json.load(fh)["itens"]
    dia = lambda s: dt.datetime.strptime(s, "%d/%m/%Y").date()
    trocas = defaultdict(list)
    for x in itens:
        if x["troca"]:
            trocas[x["ativo"]].append(dt.datetime.strptime(x["troca"], "%d/%m/%Y"))
    volta_executada(pas, por, antes, acoes, trocas)
    rol = do_rol()
    linhas = mensal(pas, acoes, rol)
    novo = novidades(acoes, dcmd)
    # a fila do posto fecha mês a mês: fim = anterior + entradas − saídas
    anterior = sum(1 for p in pas if p["entrada"] < dt.datetime(2025, 1, 1) and (p["saida"] is None or p["saida"] >= dt.datetime(2025, 1, 1)))
    fila_fim_2024 = anterior
    for l in linhas:
        assert l["fila_no_fim"] == anterior + l["entradas"] - l["saidas"], (l["rotulo"], anterior, l)
        anterior = l["fila_no_fim"]
    # o que a pauta cita e não está na tabela do mês
    abr_set = lambda d, ano: d is not None and d.year == ano and 4 <= d.month <= 9
    lote = [p for p in pas if p["saida"] and p["saida"].date() == dt.date(2026, 4, 23) and p["destino"] == "COCM"]
    trocados = {x["ativo"]: dia(x["troca"]) for x in itens if x["troca"] and any(p["ativo"] == x["ativo"] and p["destino"] == "COCM" for p in lote)
                and dia(x["troca"]) >= dt.date(2026, 4, 23)}
    volta = []
    for p in lote:
        if p["destino"] == "COCM":
            volta.append(ts.saida(ts.seguintes(p["ss"], por)[0], por)[0])
    # troca do rol com parecer do COEP sobre o material entre a falha e a troca
    def material_antes(ano):
        tr = [x for x in itens if x["troca"] and abr_set(dia(x["troca"]), ano)]
        com = [x for x in tr if any(x["ativo"] in y["ativos"] and set(y["tipos"]) & MATERIAL and dia(x["inicio"]) <= y["data"] <= dia(x["troca"])
                                    for y in acoes)]
        return len(com), len(tr)
    exe = lambda ano: [p for p in pas if p["depois"].startswith("executou") and abr_set(p["saida"], ano)]
    jul = [p for p in exe(2026) if p["saida"].month == 7]
    jul_mat = [p for p in jul if any(p["ativo"] in y["ativos"] and set(y["tipos"]) & MATERIAL
                                     and dt.date(2026, 1, 1) <= y["data"] <= p["saida"].date() for y in acoes)]
    adiante = lambda ano: sum(1 for p in exe(ano) if p["depois"] == "executou" and p["execucao"] and
                              ts.saida(ts.seguintes(p["ss"], por)[0], por)[1] == "REPASSADA")
    wa = openpyxl.load_workbook(sf.AJUSTES, read_only=True, data_only=True)
    # no cadastro de ajustes COM o dado preenchido: relé e tensão do RL; controlador e potência do RT
    cadastro = set()
    for aba, campos in (("Ajustes RL Poste", ("RELE", "TENSÃO")), ("Ajustes Reguladores de Tensão", ("CONTROLADOR", "POTÊNCIA [Kvar]"))):
        linhas_aba = wa[aba].iter_rows(values_only=True)
        cab = next(linhas_aba)
        ix = [cab.index(c) for c in campos]
        cadastro |= {str(r[0]).strip() for r in linhas_aba if r[0] and all(r[i] not in (None, "") for i in ix)}
    # as perguntas de abr–set/2026 e o que aconteceu depois com o equipamento
    perg = [y for y in acoes if y["data"] >= dt.date(2026, 4, 1) and PERGUNTA & set(y["tipos"])]
    quando = {}
    for y in perg:
        for a in y["ativos"]:
            quando[a] = min(quando.get(a, y["data"]), y["data"])
    desfecho = Counter()
    for a, d0 in quando.items():
        if any(dia(x["troca"]) >= d0 for x in itens if x["ativo"] == a and x["troca"]):
            desfecho["trocada depois"] += 1
        elif any(p["ativo"] == a and p["saida"] is None for p in pas):
            desfecho["segue aberta no COEP"] += 1
        elif any(p["ativo"] == a and p["destino"] == "cancelada" and p["saida"].date() >= d0 for p in pas):
            desfecho["cancelada"] += 1
        else:
            desfecho["saiu do COEP sem troca no rol"] += 1
    modelo = [y for y in perg if re.search(r"MODELO|MARCA|TENS[ÃA]O|POT[ÊE]NCIA", y["texto"], re.I)]
    c26 = json.load(open(os.path.join(sf.RAIZ, "data", "missao", "coep_2026.json"), encoding="utf-8"))
    volt = set(json.load(open(os.path.join(sf.RAIZ, "data", "missao", "particao_coep.json"), encoding="utf-8"))["voltaram"])
    canc = [x for x in c26["resolvidos_do_coep"] if x["conta_como_resolvido_pelo_coep"] and x["ativo"] not in volt
            and x["como_terminou"] == "SS CANCELADA" and dia(x["data_do_fechamento"]).month in (5, 6, 7)]
    motivos = {p["ss"]: motivo_da_volta(p, por, antes, trocas, acoes) for p in pas if p["origem"] == "COCM"
               and (abr_set(p["entrada"], 2025) or abr_set(p["entrada"], 2026))}
    voltas = {ano: Counter(m for k, m in motivos.items() if abr_set(next(p for p in pas if p["ss"] == k)["entrada"], ano)) for ano in (2025, 2026)}
    # as SS da volta do lote de 23/04: a seguinte da SS do COCM
    lote_cocm = [ts.seguintes(p["ss"], por)[0] for p in lote]
    lote_volta_ss = {x for s in lote_cocm for x in (d["_seg"] for d in por[s]) if x in por and "COEP" in txt(por[x][0]["POSTO_SGM"])}
    req = compras()
    # a leitura das cadeias (analista + verificador adversarial), quando já rodou
    cadeias = None
    if os.path.exists(rcad.RETRO):
        R = rcad.carrega()
        cadeias = {"dem": R["demandas"], "rel": R["relatorio"], "pm": rcad.por_mes(R["demandas"]), "res": rcad.resumo(R["demandas"])}
        # a Gestão do gestor marca «Realizado», mas o SGM não tem frase de serviço: lacuna de registro
        gest = sf.gestao()
        cadeias["res"]["gestao_sem_frase"] = sorted({r["ativo"] for r in R["demandas"] if "REALIZ" in gest.get(r["ativo"], {}).get("status", "").upper()
                                                     and not any(x.get("executada") for x in R["demandas"] if x["ativo"] == r["ativo"])})
    cancel_3006_total = sum(1 for k, v in por.items() if ts.status(k, por) == "SS CANCELADA" and v[0]["DTA_CONCLUSAO"]
                            and v[0]["DTA_CONCLUSAO"].date() == dt.date(2026, 6, 30))
    extra = {"lote_2304": lote, "lote_trocados": trocados, "lote_volta": volta, "cadeias": cadeias,
             "fila_fim_2024": fila_fim_2024, "cancel_3006_total": cancel_3006_total,
             "lote_desde_2025": sum(1 for p in lote if p["entrada"].year <= 2025),
             "lote_dias_parado": median([(p["saida"] - p["entrada"]).days for p in lote]) if lote else 0,
             "jul_com_material": len(jul_mat), "mat_25": material_antes(2025), "mat_26": material_antes(2026),
             "ritmo_abr_set_25": ritmo(itens, dt.date(2025, 4, 1), dt.date(2025, 9, 30)),
             "ritmo_abr_set_26": ritmo(itens, dt.date(2026, 4, 1), HOJE.date()),
             "ritmo_ate_abr_26": ritmo(itens, dt.date(2025, 1, 1), dt.date(2026, 4, 30)),
             "ritmo_mai_set_26": ritmo(itens, dt.date(2026, 5, 1), HOJE.date()),
             "prot_ind_2025": sum(1 for p in pas if p["destino"] == "PROT" and abr_set(p["saida"], 2025) and p["tipo"] == IND),
             "prot_da_tele_2025": sum(1 for p in pas if p["destino"] == "PROT" and abr_set(p["saida"], 2025) and p["origem"] == "TELE"),
             "prot_trocado_2025": sum(1 for p in pas if p["destino"] == "PROT" and abr_set(p["saida"], 2025)
                                      and re.search(r"SUBSTITU[IÍ]D|COMISSION|SERVI[ÇC]O EXECUTADO", texto_novo(p["ss"], por, antes), re.I)),
             "cocm_adiante_2025": adiante(2025), "cocm_adiante_2026": adiante(2026),
             **{f"obras_{ano}": sum(1 for p in pas if abr_set(p["entrada"], ano) and p["tipo"].startswith("OBRAS")) for ano in (2025, 2026)},
             "envio_errado": any(y["data"].year == 2026 and y["data"].month == 8 and "PROBLEMA NO ENVIO" in y["texto"].upper() for y in acoes),
             "cancel_3006": sum(1 for p in pas if p["destino"] == "cancelada" and p["saida"] and p["saida"].date() == dt.date(2026, 6, 30)),
             "perguntas_2906": sum(1 for y in perg if y["data"] == dt.date(2026, 6, 29)),
             "perguntas": {"n": len(perg), "em_2906": sum(1 for y in perg if y["data"] == dt.date(2026, 6, 29)), "ativos": len(quando),
                           "no_cadastro": len(set(quando) & cadastro), "modelo": len(modelo),
                           "placa": sum(1 for y in modelo if re.search(r"PLACA|C[ÓO]DIGO", y["texto"], re.I)), "desfecho": dict(desfecho)},
             "exec_ind_2025": sum(1 for p in exe(2025) if p["tipo"] == IND), "exec_ind_2026": sum(1 for p in exe(2026) if p["tipo"] == IND),
             "exec_tipos_2025": [p["tipo"] for p in exe(2025)],
             "pareceres_2025": sum(l["pareceres"] for l in linhas if l["ano"] == 2025),
             "par_2025": sum(1 for y in acoes if y["inicio_janela"].year == 2025 and y["data"].year == 2025),
             "par_abrset26": sum(1 for y in acoes if y["inicio_janela"] >= dt.date(2026, 4, 1) and y["data"] <= HOJE.date()),
             "par_incertos": sum(1 for y in acoes if y["data"] >= dt.date(2025, 1, 1) and not (
                 (y["inicio_janela"].year == 2025 and y["data"].year == 2025) or y["inicio_janela"] >= dt.date(2026, 4, 1)
                 or (y["inicio_janela"] >= dt.date(2026, 1, 1) and y["data"] < dt.date(2026, 4, 1)))),
             "datados_2025": sum(l["pareceres_datados"] for l in linhas if l["ano"] == 2025),
             "voltas_2025": voltas[2025], "voltas_2026": voltas[2026], "compras": req,
             "lote_sem_motivo": sum(1 for k in lote_volta_ss if motivos.get(k) == "sem motivo escrito"),
             "canc_resolvidos": len(canc), "canc_com_prova": sum(1 for x in canc if "volta à operação" in x["prova"])}
    assert extra["perguntas_2906"] == extra["perguntas"]["em_2906"]
    pt = pauta(pas, acoes, linhas, novo, extra)

    wb = openpyxl.Workbook()
    aba_pauta(wb, pt)
    aba_mensal(wb, linhas)
    if cadeias:
        rcad.aba_tratativas_mes(wb, cadeias["dem"], cadeias["pm"], bm.cabecalho, celulas, titulo)
        rcad.aba_por_demanda(wb, cadeias["dem"], bm.cabecalho, celulas)
        rcad.aba_linha_do_tempo(wb, cadeias["dem"], bm.cabecalho, celulas)
    aba_novo(wb, novo)
    aba_pareceres(wb, acoes)
    aba_passagens(wb, [p for p in pas if p["entrada"].year >= 2025])
    ws = wb.create_sheet("Compras")
    titulo(ws, 1, "Requisições de compra registradas na aba Estoque da COEP 5",
           "Fora da base de SS — a base não registra compra. Uma linha da Tabela7 é uma peça; o valor é a soma das linhas.", 6)
    bm.cabecalho(ws, 4, ["Requisição Web Supply", "Data", "Peças", "Valor (R$)", "Status", "Tem regulador?"], [22, 12, 9, 16, 26, 12])
    celulas(ws, 5, [[x["requisicao"], x["data"], x["pecas"], x["valor"], x["status"], "sim" if x["tem_regulador"] else "não"] for x in req])
    for row in ws.iter_rows(min_row=5, min_col=2, max_col=4):
        row[0].number_format, row[2].number_format = "DD/MM/YYYY", "#,##0.00"
    aba_como(wb)
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    wb.save(SAIDA)
    with open(JSON, "w", encoding="utf-8") as fh:
        json.dump({"posicao": HOJE.strftime("%Y-%m-%d"), "mensal": linhas, "novidades": novo, "compras": req,
                   "pauta": [{"bloco": b, "itens": [{"tema": a, "texto": t} for a, t in i]} for b, i in pt],
                   "lote_2304": {"ss": [p["ss"] for p in lote], "trocados": trocados, "voltaram": volta},
                   "perguntas": extra["perguntas"], "voltas_do_cocm": {"2025": voltas[2025], "2026": voltas[2026]},
                   "cadeias": ({"relatorio": cadeias["rel"], "resumo": {k: v for k, v in cadeias["res"].items() if k != "dias_ate_executar"},
                                "por_mes": {f"{a}-{m:02d}": {k: (dict(v) if isinstance(v, Counter) else v) for k, v in x.items()}
                                            for (a, m), x in cadeias["pm"].items()}} if cadeias else None),
                   "ritmo_de_troca": {k: {"trocas": extra[k][0], "falha_meses": round(extra[k][1], 1)}
                                      for k in ("ritmo_abr_set_25", "ritmo_abr_set_26", "ritmo_ate_abr_26", "ritmo_mai_set_26")},
                   "pareceres": [{**y, "data": y["data"].isoformat()} for y in acoes if y["data"].year >= 2025],
                   "pareceres_dcmd": [{**y, "data": y["data"].isoformat()} for y in dcmd if y["data"].year >= 2025]},
                  fh, ensure_ascii=False, indent=1, default=str)
    return pt


if __name__ == "__main__":
    for bloco, itens in main():
        print("\n##", bloco)
        for a, t in itens:
            print(f"  · {a}: {t}")
