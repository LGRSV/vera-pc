"""
A visão orçamentária dos dois projetos — orçamento × realizado × o que falta,
e quanto custa a fila que está na mesa.

Régua do gestor (22/08): o valor que vale é o VALOR MÉDIO POR MANUTENÇÃO dele —
RL R$ 58.543,21 e RT R$ 167.280,98 —, não o médio por obra que o AIC devolve
(esse fica só como referência, e é menor porque nem toda obra do projeto troca o
equipamento inteiro: no regulador, muitas trocam uma célula, não o banco de três).

Cada balde da visão ETO vira dinheiro assim (pergunta do gestor, 22/08: «não é
pelo custo médio, todos já estão orçados?» — nem todos): vale o VALOR ORÇADO do
ativo na planilha de indisponibilidade onde ele existe, e só onde falta entra o
valor médio por manutenção. Dos 93, 54 têm orçamento próprio; 39 não — e os 20 do
1º ataque do DMSL são justamente os que não têm nenhum, por serem novos. Por isso
a estimativa deles é inteiramente pelo médio.

Fontes (todas do gestor, em data/raw/realizado_capex_2026.json):
  - quadro Orçamento 2026 — a coluna ORÇADO por projeto;
  - Power BI do Capex — o REALIZADO do ano, 8481 e 8495 somados, por mês e por
    natureza. É esta a medida do realizado (régua do gestor, 22/08): a coluna
    Realizado do quadro do export de 21/08 trazia R$ 1.365.345 e não vale;
  - o valor médio por manutenção.

Grava data/missao/visao_orcamentaria.json.
Rodar: python3 scripts/visao_orcamentaria.py
"""

import json
import os
import re
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "data", "missao", "visao_orcamentaria.json")

PROJETOS = (("8495", "religador", "RL"), ("8481", "regulador", "RT"))
PROJETO_DO_TIPO = {"RL": "8495", "RT": "8481"}
# Os dois projetos de equipamento especial. Aceitar os dois, e não só o do tipo, é
# reconhecer o que a análise do SIGCO já mostrou: obra de regulador lançada no 8495 e
# religador no 8481 acontecem. O projeto que não bate vai marcado, não descartado.
PROJETOS_ESPECIAIS = {"8495", "8481"}
# A obra de substituição também aparece fora dos dois projetos — quase sempre no 8389,
# o balde de manutenção corretiva. Nesses, só o texto decide: tem de dizer que trocou
# o equipamento (ou a célula, ou o controle) e ser do ano corrente.
RE_SUBSTITUICAO = re.compile(
    r"(SUBST|TROCA|RETROFIT).{0,40}(RELIGADOR|REGULADOR|C[ÉE]LULA|CONTROLE|RL\b|RT\b)",
    re.IGNORECASE)
# E o que nunca é manutenção do ativo: obra de rede, de expansão, de deslocamento.
RE_EXPANSAO = re.compile(r"(CONSTRU[ÇC][ÃA]O|DESLOCAMENTO|IMPLANTA[ÇC][ÃA]O|"
                         r"INSTALA[ÇC][ÃA]O DE \d+|RDR|RD MT|EXPANS)", re.IGNORECASE)
# A obra que vale é a da demanda de agora. Obra concluída em 2023/2024 num ativo que
# hoje está em aquisição é de um evento anterior — o dinheiro dela já foi gasto noutra
# falha e não diz nada sobre o que falta pagar.
ANO_DA_CARTEIRA = "2026"
# O extrato do AIC é uma foto: obra aberta depois dele não tem como aparecer.
EXTRATO_DO_AIC = "07/08/2026"
# O que o parecer diz que foi feito. Aterramento é serviço de rede, do COCM ou da
# equipe de linha — não gera obra de manutenção do equipamento, e é o próprio COEP que
# manda tirar do fluxo de aquisição («melhoria de aterramento não passa pelo COEP»).
RE_ATERRAMENTO = re.compile(r"MELHORIA (DE|NO) ATERRAMENTO|MALHA DE ATERRAMENTO|"
                            r"ATERRAMENTO QUE SE ENCONTRA ALTA", re.IGNORECASE)
RE_OBRA_NO_TEXTO = re.compile(r"OBRA[:\s]*(\d{9,10})", re.IGNORECASE)
BALDE_NOME = {
    "ajuste_de_protecao": "Em fase de ajuste de proteção",
    "comissionamento": "Aguardando comissionamento",
    "dcmd_execucao": "DCMD · em execução",
    "dcmd_logistica": "DCMD · em logística",
    "dcmd_aquisicao": "DCMD · em processo de aquisição",
    "dmsl_novos": "1º ataque do DMSL",
}
# O que ainda vai custar dinheiro novo: quem está em ajuste ou comissionamento já
# teve o equipamento trocado — o gasto foi feito.
AINDA_CUSTA = ("dcmd_execucao", "dcmd_logistica", "dcmd_aquisicao", "dmsl_novos")


def _num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _oid(x):
    if isinstance(x, dict):
        x = x.get("obra") or x.get("num_obra") or ""
    x = str(x).split(".")[0].strip()
    return x.zfill(10) if x.isdigit() and int(x) > 0 else ""


def obra_orfa_da_localidade(ativo, item, aic, donos, alvos):
    """Último recurso, e só para quem a cadeia diz que JÁ FOI TROCADO sem obra achada:
    a obra de substituição do projeto certo, na mesma localidade, aberta neste ano e
    que ainda não é de ninguém. Se houver mais de uma candidata, não atribui — duas
    candidatas é ambiguidade, não descoberta. Vai marcada como inferida."""
    loc = (item.get("localidade") or "").strip().upper()
    if not loc:
        return None
    cand = []
    for o, r in aic.items():
        if o in donos:
            continue
        if str(r.get("NUM_PROJETO_SIGCO", "")).strip() != PROJETO_DO_TIPO.get(item["tipo"]):
            continue
        if str(r.get("NOMELOC", "")).strip().upper() != loc:
            continue
        if str(r.get("DTH_ABERTURA", ""))[:4] != ANO_DA_CARTEIRA:
            continue
        texto = f"{r.get('DESCRICAO_OBRA', '')} {r.get('DESCRICAO', '')}"
        if not RE_SUBSTITUICAO.search(texto):
            continue
        # se a obra escreve o código de um equipamento e não é o nosso (nem o trafo
        # auxiliar dele), a obra é de outro ativo — inferir aqui seria roubar a obra
        citados = set(re.findall(r"\b(?:79|58|51|57)\d{8}\b", texto))
        if citados and not citados & {ativo, "51" + ativo[2:], "57" + ativo[2:]}:
            continue
        orcado, realizado = _num(r.get("VAL_TOTAL_ORCADO")), _num(r.get("TOTAL_REALIZADO"))
        if not (orcado or realizado):
            continue
        cand.append({"valor": round(realizado or orcado, 2),
                     "medida": "realizado" if realizado else "orçado", "obra": o,
                     "via": "obra de substituição da mesma localidade, ainda sem dono",
                     "abertura": str(r.get("DTH_ABERTURA", ""))[:10],
                     "orcado_da_obra": round(orcado, 2),
                     "ressalva": "vínculo INFERIDO por localidade, projeto e data — "
                                 "conferir no SGM antes de usar como oficial"})
    return cand[0] if len(cand) == 1 else None


def obras_por_ativo(aic, ssos, descricoes, m4, ss_do_ativo, emd, cadeia, alvos, aux):
    """Toda obra do AIC que alguma base liga ao ativo. Seis vias, e cada vínculo
    guarda por onde veio para dar para conferir na mão:

      1. o vínculo por EMD do cruzamento obra×ativo (m4);
      2. a planilha de EMD (OBRAS_EQ_ESPECIAL);
      3. o NUM_OBRA das SS do próprio ativo;
      4. o número de obra citado no texto do parecer;
      5. a cadeia SS→OS→obra já montada;
      6. o código do ativo escrito na descrição da obra, no próprio AIC — a busca
         ao contrário, que é a que mais rende quando a obra não cita SS nenhuma.
    """
    vinc = defaultdict(dict)

    def liga(ativo, obra, via):
        if ativo in alvos and obra:
            vinc[ativo].setdefault(obra, via)

    for a, d in m4.items():
        for o in [_oid(d.get("obra_principal"))] + [_oid(x) for x in (d.get("outras_obras") or [])]:
            liga(a, o, "EMD/obra do ativo")
    for l in (emd.get("linhas") or []):
        liga(str(l.get("ativo") or ""), _oid(l.get("obra") or l.get("num_obra")),
             "planilha de EMD")
    for r in ssos:
        liga(r["NUM_TRAFO"], _oid(r["NUM_OBRA"]), f"obra na {r['NUMERO_SS']}")
    for ss_num, txt in descricoes.items():
        a = ss_do_ativo.get(ss_num)
        if not a:
            continue
        for m in re.findall(r"\b(\d{9,10})\b", txt or ""):
            o = _oid(m)
            if o and o in aic:
                liga(a, o, f"obra citada no texto da {ss_num}")
    for ob in (cadeia.get("obras") or []):
        for a in (ob.get("ativos") or []):
            liga(a, _oid(ob.get("obra")), "cadeia SS→OS→obra")
    for s in (aux.get("ss") or []):
        liga(s["ativo"], _oid(s.get("obra")),
             f"obra na SS do trafo auxiliar {s['trafo_auxiliar']} ({s['ss']})")
    achar_cod = re.compile(r"\b(79\d{8}|58\d{8})\b")
    for o, r in aic.items():
        txt = f"{r.get('DESCRICAO_OBRA', '')} {r.get('DESCRICAO', '')}"
        if "79" not in txt and "58" not in txt:
            continue
        for cod in achar_cod.findall(txt):
            liga(cod, o, "código do ativo na descrição da obra")
    return vinc


def valor_pela_obra(ativo, tipo, ja_trocado, vinc, aic):
    """O valor real da obra do ativo, quando o AIC tem uma que sirva.

    Em quem já foi trocado vale o REALIZADO — é o dinheiro que saiu. Em quem ainda
    espera, vale o ORÇADO da obra aberta neste ano, que é o compromisso firme; obra
    de anos anteriores fica de fora porque pagou outra falha."""
    cand = []
    for o, via in (vinc.get(ativo) or {}).items():
        r = aic.get(o)
        if not r:
            continue
        projeto = str(r.get("NUM_PROJETO_SIGCO", "")).strip()
        texto = f"{r.get('DESCRICAO_OBRA', '')} {r.get('DESCRICAO', '')}"
        abertura = str(r.get("DTH_ABERTURA", ""))[:10]
        if projeto in PROJETOS_ESPECIAIS:
            # dentro do projeto de equipamento especial o texto não precisa passar por
            # filtro: «RDR» ali é o alimentador onde o equipamento está, não obra de rede
            ressalva = ("" if projeto == PROJETO_DO_TIPO.get(tipo)
                        else f"obra no projeto {projeto}, o do outro tipo — SIGCO trocado")
        elif RE_EXPANSAO.search(texto):
            # fora dos dois projetos, obra de rede, expansão ou deslocamento não é a
            # manutenção deste ativo — mesmo quando cita o código dele
            continue
        elif RE_SUBSTITUICAO.search(texto) and abertura[:4] >= ANO_DA_CARTEIRA:
            ressalva = (f"obra fora dos projetos de equipamento especial (SIGCO {projeto or '—'}), "
                        "aceita pelo texto de substituição")
        else:
            continue
        orcado, realizado = _num(r.get("VAL_TOTAL_ORCADO")), _num(r.get("TOTAL_REALIZADO"))
        if ja_trocado and realizado > 0:
            cand.append((abertura, realizado, "realizado", o, via, orcado, ressalva))
        elif abertura[:4] >= ANO_DA_CARTEIRA and (realizado > 0 or orcado > 0):
            # obra aberta neste ano sem realizado lançado ainda: vale o orçado dela,
            # que é dinheiro comprometido — melhor que o previsto da planilha
            cand.append((abertura, realizado if realizado > 0 else orcado,
                         "realizado" if realizado > 0 else "orçado", o, via, orcado, ressalva))
    if not cand:
        return None
    abertura, valor, medida, obra, via, orcado, ressalva = max(cand)
    saida = {"valor": round(valor, 2), "medida": medida, "obra": obra, "via": via,
             "abertura": abertura, "orcado_da_obra": round(orcado, 2)}
    if ressalva:
        saida["ressalva"] = ressalva
    return saida


def montar():
    with open(os.path.join(RAIZ, "data", "raw", "realizado_capex_2026.json"),
              encoding="utf-8") as fh:
        caixa = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "aic_full.json"), encoding="utf-8") as fh:
        aic = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "visao_consolidada.json"),
              encoding="utf-8") as fh:
        vc = json.load(fh)
    with open(os.path.join(RAIZ, "data", "raw", "dinamica_joa.json"), encoding="utf-8") as fh:
        orcado = {x["ativo"]: x.get("valor") or 0.0
                  for x in json.load(fh)["lista"] if (x.get("valor") or 0) > 0}
    with open(os.path.join(RAIZ, "data", "missao", "ssos_min.json"), encoding="utf-8") as fh:
        ssos = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "descricao_ss_pendentes.json"),
              encoding="utf-8") as fh:
        descricoes = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "m4_aic129.json"), encoding="utf-8") as fh:
        m4 = json.load(fh)["ativos"]
    with open(os.path.join(RAIZ, "data", "raw", "emd_no_aic.json"), encoding="utf-8") as fh:
        emd = json.load(fh)
    with open(os.path.join(RAIZ, "data", "missao", "cadeia_obra.json"), encoding="utf-8") as fh:
        cadeia = json.load(fh)
    arq_aux = os.path.join(RAIZ, "data", "missao", "ss_trafo_auxiliar_93.json")
    with open(arq_aux, encoding="utf-8") as fh:
        aux = json.load(fh)

    todos = {i["ativo"]: {**i, "_ja_trocado": b not in AINDA_CUSTA}
             for b in BALDE_NOME for i in vc["visao_eto"]["baldes"][b]["ativos"]}
    ss_do_ativo = {i["ss_pendente"]: a for a, i in todos.items()}
    vinc = obras_por_ativo(aic, [r for r in ssos if r["NUM_TRAFO"] in todos],
                           descricoes, {a: d for a, d in m4.items() if a in todos},
                           ss_do_ativo, emd, cadeia, todos, aux)

    medio = caixa["valor_medio_por_manutencao"]
    orc = dict(caixa["orcamento_2026"])
    # o realizado do ano é o total do Power BI, não a coluna do quadro
    orc["total_realizado"] = caixa["total"]
    orc["pct_realizado"] = round(100 * caixa["total"] / orc["total_orcado"], 2)
    saldo = round(orc["total_orcado"] - orc["total_realizado"], 2)

    # ---- referência: o médio por obra concluída do projeto no AIC (fica de nota)
    referencia = {}
    for proj, nome, sigla in PROJETOS:
        concl = [r for r in aic.values()
                 if str(r.get("NUM_PROJETO_SIGCO", "")).strip() == proj
                 and (str(r.get("DTH_ABERTURA", "")).startswith("2026")
                      or str(r.get("DATA_CONCLUSAO_FISICA", "")).startswith("2026")
                      or str(r.get("DTH_ENCERRAMENTO", "")).startswith("2026"))
                 and (r.get("DATA_CONCLUSAO_FISICA") or r.get("DTH_ENCERRAMENTO"))]
        realizado = round(sum(_num(r["TOTAL_REALIZADO"]) for r in concl), 2)
        referencia[sigla] = {
            "projeto": proj, "nome": nome,
            "obras_concluidas_2026": len(concl),
            "realizado_acumulado": realizado,
            "medio_por_obra": round(realizado / len(concl), 2) if concl else 0.0,
        }

    # ---- cada balde da visão ETO em dinheiro: orçado onde existe, médio onde falta.
    # Régua do gestor (22/08): em ajuste de proteção e comissionamento o equipamento JÁ
    # FOI TROCADO — o dinheiro saiu. Ali não se estima nada: vale o que estava orçado
    # para eles, e quem não tem valor na planilha fica sem valor mesmo. Aplicar o médio
    # seria inventar gasto futuro para dinheiro que já aconteceu.
    # A hierarquia do valor de cada ativo, da fonte mais forte para a mais fraca:
    #   1. a OBRA do ativo no AIC — dinheiro de verdade, realizado ou orçado;
    #   2. o valor orçado do ativo na planilha de indisponibilidade;
    #   3. o valor médio por manutenção — e só em quem ainda vai custar.
    fontes = {}
    for a, i in todos.items():
        ja = i["_ja_trocado"]
        obra = valor_pela_obra(a, i["tipo"], ja, vinc, aic)
        if obra:
            fontes[a] = {"valor": obra["valor"], "fonte": "obra", **obra}
            continue
        # a cadeia diz que trocou e nenhuma via achou a obra: procura a órfã da praça
        if ja:
            ja_donos = {d["obra"] for d in fontes.values() if d.get("fonte") == "obra"}
            ja_donos |= {o for v in vinc.values() for o in v}
            inferida = obra_orfa_da_localidade(a, i, aic, ja_donos, todos)
            if inferida:
                fontes[a] = {"valor": inferida["valor"], "fonte": "obra", **inferida}
                continue
        if a in orcado:
            fontes[a] = {"valor": round(orcado[a], 2), "fonte": "planilha"}
        elif not ja:
            fontes[a] = {"valor": round(medio[i["tipo"]], 2), "fonte": "medio"}
        else:
            fontes[a] = {"valor": 0.0, "fonte": "sem_valor"}

    # Quem já foi trocado e mesmo assim não recebeu valor de obra: o gestor pediu para
    # procurar em todas as bases, então cada ausência vem com o motivo apurado, para
    # dar para ir atrás no SGM ou no AIC.
    sem_obra = []
    for a, i in todos.items():
        if not i["_ja_trocado"] or fontes[a]["fonte"] == "obra":
            continue
        candidatas = []
        for o in (vinc.get(a) or {}):
            r = aic.get(o)
            if not r:
                candidatas.append({"obra": o, "porque": "obra não está no extrato do AIC "
                                   "de 07/08 — foi criada depois"})
                continue
            texto = f"{r.get('DESCRICAO_OBRA', '')} {r.get('DESCRICAO', '')}".strip()
            proj = str(r.get("NUM_PROJETO_SIGCO", "")).strip()
            if not (_num(r.get("VAL_TOTAL_ORCADO")) or _num(r.get("TOTAL_REALIZADO"))):
                porque = f"obra sem valor lançado no AIC (SIGCO {proj or 'em branco'})"
            elif RE_EXPANSAO.search(texto):
                porque = (f"obra de rede ou instalação nova, de {str(r.get('DTH_ABERTURA',''))[:4]} "
                          f"(SIGCO {proj or '—'}) — não é a manutenção deste ativo")
            else:
                porque = (f"obra de {str(r.get('DTH_ABERTURA', ''))[:4]}, SIGCO {proj or '—'}, "
                          "sem texto de substituição")
            candidatas.append({"obra": o, "porque": porque, "descricao": texto[:90]})
        # o que o parecer da SS pendente diz que foi feito — é o que decide se a obra
        # de manutenção deveria existir
        texto = descricoes.get(i["ss_pendente"], "") or ""
        obra_no_texto = RE_OBRA_NO_TEXTO.search(texto)
        if RE_ATERRAMENTO.search(texto):
            leitura = {"classe": "melhoria de aterramento",
                       "conclusao": "serviço de rede, não manutenção do equipamento — "
                                    "obra de manutenção não deveria existir mesmo"}
        elif obra_no_texto:
            leitura = {"classe": "obra citada no próprio parecer",
                       "obra_citada": obra_no_texto.group(1).zfill(10),
                       "conclusao": "a obra está identificada; o que falta é valor "
                                    "lançado nela no AIC"}
        elif candidatas and all("não está no extrato" in c["porque"] for c in candidatas):
            leitura = {"classe": "obra posterior ao extrato do AIC",
                       "obra_citada": candidatas[0]["obra"],
                       "conclusao": f"a obra existe na SS mas o extrato do AIC é de "
                                    f"{EXTRATO_DO_AIC} e não a alcança — sai no próximo"}
        else:
            leitura = {"classe": "substituição sem obra localizada",
                       "conclusao": "cobrar no SGM qual obra pagou o serviço"}
        trecho = ""
        for m in (RE_ATERRAMENTO.search(texto), obra_no_texto):
            if m:
                trecho = texto[max(0, m.start() - 90):m.end() + 90].strip()
                break
        if trecho:
            leitura["trecho_do_parecer"] = trecho
        sem_obra.append({"ativo": a, "balde": [b for b in BALDE_NOME
                                               if a in {x["ativo"] for x in vc["visao_eto"]["baldes"][b]["ativos"]}][0],
                         "localidade": i.get("localidade", ""),
                         "valor_usado": fontes[a]["valor"], "fonte": fontes[a]["fonte"],
                         "obras_descartadas": candidatas, "leitura_do_parecer": leitura,
                         "porque": ("nenhuma obra ligada a este ativo em nenhuma das bases"
                                    if not candidatas else candidatas[0]["porque"])})
    sem_obra.sort(key=lambda x: x["ativo"])

    # A investigação por agentes (23/08) leu a cadeia inteira de cada um destes e as
    # obras candidatas do AIC. Onde ela achou a obra, o número entra aqui — mas sem
    # valor, porque nos dois casos a cifra não está lançada: uma obra está em projeto
    # e a outra é posterior ao extrato do AIC.
    investigacao = {}
    arq_inv = os.path.join(RAIZ, "data", "missao", "investigacao_obras.json")
    if os.path.exists(arq_inv):
        with open(arq_inv, encoding="utf-8") as fh:
            inv = json.load(fh)
        investigacao = {c["ativo"]: c for c in inv["casos"]}
        for s in sem_obra:
            c = investigacao.get(s["ativo"])
            if not c:
                continue
            s["investigacao"] = {
                "classe": c["classe_do_servico"], "veredito": c["veredito"],
                "obra": c["obra"], "confianca": c["confianca"],
                "executado_em": c.get("data_da_execucao", ""),
                "deveria_ter_obra": c.get("deveria_ter_obra_de_manutencao"),
                "refutado_pelo_cetico": (c.get("verificacao") or {}).get("refutado"),
                "resumo": c["o_que_foi_feito"][:400],
            }

    # Uma obra pode atender mais de um ativo — acontece de a mesma troca cobrir dois
    # equipamentos do mesmo trecho. Contar o valor cheio nos dois infla a conta, então
    # o valor da obra é rateado entre eles e a divisão vai anotada.
    donos = defaultdict(list)
    for a, d in fontes.items():
        if d["fonte"] == "obra":
            donos[d["obra"]].append(a)
    for obra_id, ativos_da_obra in donos.items():
        if len(ativos_da_obra) < 2:
            continue
        for a in ativos_da_obra:
            d = fontes[a]
            d["valor_cheio_da_obra"] = d["valor"]
            d["valor"] = round(d["valor"] / len(ativos_da_obra), 2)
            d["rateio"] = (f"obra dividida com {len(ativos_da_obra) - 1} outro ativo"
                           + ("s" if len(ativos_da_obra) > 2 else "")
                           + f" ({', '.join(x for x in ativos_da_obra if x != a)})")

    def custo(itens):
        rl = sum(1 for i in itens if i["tipo"] == "RL")
        conta = {f: 0 for f in ("obra", "planilha", "medio", "sem_valor")}
        soma = dict(conta)
        for i in itens:
            fo = fontes[i["ativo"]]
            conta[fo["fonte"]] += 1
            soma[fo["fonte"]] += fo["valor"]
        return {"qtd": len(itens), "rl": rl, "rt": len(itens) - rl,
                "n_obra": conta["obra"], "n_planilha": conta["planilha"],
                "n_medio": conta["medio"], "sem_valor": conta["sem_valor"],
                "por_obra": round(soma["obra"], 2),
                "por_planilha": round(soma["planilha"], 2),
                "estimado": round(soma["medio"], 2),
                # o que se sabe de verdade — obra ou planilha — separado do que é estimado
                "conhecido": round(soma["obra"] + soma["planilha"], 2),
                "com_orcamento": conta["obra"] + conta["planilha"],
                "sem_orcamento": conta["medio"],
                "orcado": round(soma["obra"] + soma["planilha"], 2),
                "custo": round(soma["obra"] + soma["planilha"] + soma["medio"], 2)}

    baldes = []
    for b, nome in BALDE_NOME.items():
        d = custo(vc["visao_eto"]["baldes"][b]["ativos"])
        baldes.append({"balde": b, "nome": nome, "ainda_custa": b in AINDA_CUSTA, **d})

    fila = [i for b in AINDA_CUSTA for i in vc["visao_eto"]["baldes"][b]["ativos"]]
    f = custo(fila)
    ja_gasto = [i for b in BALDE_NOME if b not in AINDA_CUSTA
                for i in vc["visao_eto"]["baldes"][b]["ativos"]]
    g = custo(ja_gasto)
    dmsl = vc["visao_eto"]["baldes"]["dmsl_novos"]["ativos"]
    d = custo(dmsl)
    f_rl, f_rt, f_custo = f["rl"], f["rt"], f["custo"]
    d_rl, d_rt, d_custo = d["rl"], d["rt"], d["custo"]

    pct = lambda v, base: round(100 * v / base, 1) if base else 0.0
    pacote = {
        "gerado_em": "2026-08-22",
        "orcamento": {**orc, "saldo": saldo},
        "caixa": {k: caixa[k] for k in ("fonte", "janela", "total", "por_mes", "por_natureza")},
        "valor_medio": medio,
        "referencia_aic": referencia,
        "por_balde": baldes,
        "cobertura": {
            "n_obra": sum(b["n_obra"] for b in baldes),
            "n_planilha": sum(b["n_planilha"] for b in baldes),
            "com_orcamento": sum(b["com_orcamento"] for b in baldes),
            "sem_orcamento": sum(b["sem_orcamento"] for b in baldes),
            "sem_valor": sum(b["sem_valor"] for b in baldes),
            "por_obra": round(sum(b["por_obra"] for b in baldes), 2),
            "por_planilha": round(sum(b["por_planilha"] for b in baldes), 2),
            "orcado": round(sum(b["orcado"] for b in baldes), 2),
            "estimado": round(sum(b["estimado"] for b in baldes), 2),
            "regra": "vale primeiro a OBRA do ativo no AIC — realizado em quem já foi "
                     "trocado, orçado da obra aberta neste ano em quem ainda espera; "
                     "depois o valor orçado do ativo na planilha de indisponibilidade; "
                     "e só então o valor médio por manutenção, apenas em quem ainda vai "
                     "custar. Em ajuste de proteção e comissionamento não se estima nada: "
                     "o equipamento já foi trocado e o dinheiro já saiu",
        },
        "fontes_por_ativo": {a: v for a, v in sorted(fontes.items())},
        "sem_obra": sem_obra,
        "investigacao": investigacao,
        "ja_gasto": {**g, "regra": "ajuste de proteção + comissionamento — equipamento já "
                     "trocado; o valor é o que estava orçado para eles, e o desembolso "
                     "real está dentro do realizado do ano"},
        "estimativa_dmsl": {
            **d, "pct_do_saldo": pct(d_custo, saldo),
            "pct_do_orcamento": pct(d_custo, orc["total_orcado"]),
            "como": (f"{d_rl} religadores × R$ {medio['RL']:,.2f} + {d_rt} reguladores × "
                     f"R$ {medio['RT']:,.2f}: nenhum dos {d['qtd']} tem orçamento próprio "
                     "na planilha — são novos, e é por isso que aqui tudo é pelo médio"),
        },
        "fila_que_ainda_custa": {
            **f, "pct_do_saldo": pct(f_custo, saldo),
            "regra": "execução + logística + aquisição + 1º ataque; ajuste de proteção e "
                     "comissionamento ficam fora — nesses o equipamento já foi trocado e "
                     "o dinheiro já saiu",
        },
        "nota": ("o realizado do ano é o total do Power BI — 8481 e 8495 somados, "
                 "jan–ago —, régua do gestor (22/08). A coluna Realizado do quadro "
                 "Orçamento 2026 (export de 21/08) trazia R$ 1.365.345, uma apuração "
                 "mais atrasada, e não é usada aqui. O orçado por projeto vem do mesmo "
                 "quadro e continua valendo. O médio por obra do AIC não serve de preço: "
                 "nem toda obra do projeto troca o equipamento inteiro."),
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)
    return pacote


if __name__ == "__main__":
    p = montar()
    o = p["orcamento"]
    print(f"orçamento 2026: R$ {o['total_orcado']:,.2f} · realizado R$ "
          f"{o['total_realizado']:,.2f} ({o['pct_realizado']}%) · saldo R$ {o['saldo']:,.2f}")
    print(f"médio por manutenção: RL R$ {p['valor_medio']['RL']:,.2f} · "
          f"RT R$ {p['valor_medio']['RT']:,.2f}")
    c = p["cobertura"]
    print(f"cobertura: {c['n_obra']} pela obra no AIC (R$ {c['por_obra']:,.2f}) · "
          f"{c['n_planilha']} pela planilha (R$ {c['por_planilha']:,.2f}) · "
          f"{c['sem_orcamento']} pelo médio (R$ {c['estimado']:,.2f}) · "
          f"{c['sem_valor']} sem valor")
    for b in p["por_balde"]:
        print(f"  {b['nome']:<34} {b['qtd']:>3} ({b['n_obra']} obra, {b['n_planilha']} plan, "
              f"{b['n_medio']} méd, {b['sem_valor']} s/v)  R$ {b['custo']:>14,.2f}"
              f"{'' if b['ainda_custa'] else '   (já gasto)'}")
    e = p["estimativa_dmsl"]
    print(f"1º ataque para o DCMD: R$ {e['custo']:,.2f} — {e['pct_do_saldo']}% do saldo")
    f = p["fila_que_ainda_custa"]
    print(f"fila que ainda custa ({f['qtd']}): R$ {f['custo']:,.2f} — "
          f"{f['pct_do_saldo']}% do saldo")
    print(f"gravado: {SAIDA}")
