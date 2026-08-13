"""
Base de entrada — quanto da carteira herdada já foi reduzido.

A foto de entrada é a aba «Dados» da planilha 1_Base_SS_OS_Equipamentos_especiais.xlsx:
todas as SS do posto ETO-COEP que estavam PENDENTES quando o gestor assumiu. Recorte do
gestor (13/08): só religador (ativo 79…) e regulador de tensão (ativo 58…) — 100 SS em
99 ativos, todas SS PENDENTE, todas no COEP.

A pergunta: dessas, quantas já foram embora? As sete réguas são do gestor:

  1. canceladas                    a SS de entrada está cancelada hoje;
  2. tratativa com equipamento     houve intervenção física registrada no ativo;
  3. em fase de ajustes            parecer COEP de ajuste conta como resolvido, mas fica
                                   marcado «ainda na Proteção» se a base de SS/OS mostra
                                   SS aberta em equipe PROT;
  4. concluída                     conta como resolvida se NÃO houver outra SS aberta do
                                   tipo INDISPONIBILIDADE PARA OPERAÇÃO no mesmo ativo;
                                   havendo, vai para a lista de verificação;
  5. aguardando comissionamento    mesma regra do item 4;
  6. cancelada sem reincidência    cancelada e sem SS de indisponibilidade PENDENTE;
  7. obra encerrada                obra do ativo encerrada no AIC.

Fonte de verdade da situação atual é a base de SS/OS (a mais atualizada); o parecer COEP
vem da planilha de criticidade. Hierarquia definida pelo gestor em 12/08.
"""

import datetime
import json
import os
import re
from collections import Counter, defaultdict

import demandas as D

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(RAIZ, "data", "raw", "BASE_SS_OS_EQ_ESPECIAIS_ENTRADA.xlsx")
ARQ_MIN = os.path.join(RAIZ, "data", "missao", "ssos_min.json")
ARQ_AIC = os.path.join(RAIZ, "data", "missao", "aic_index.json")
ARQ_AIC_RLRT = os.path.join(RAIZ, "data", "missao", "aic_rlrt.json")

TIPO_INDISPONIBILIDADE = "INDISPONIBILIDADE PARA OPERA"
ENCERRADA = "ENCERRAMENTO"

PREMISSAS = [
    "Foto de entrada = aba «Dados» da planilha 1_Base_SS_OS_Equipamentos_especiais.xlsx: "
    "170 SS do posto ETO-COEP, todas SS PENDENTE. O recorte do gestor (13/08) fica com as "
    "100 de religador (79…) e regulador (58…), em 99 ativos.",
    "Situação atual de cada SS vem da base de SS/OS completa — a mais atualizada, conforme "
    "a hierarquia de fontes do gestor. O parecer COEP vem da planilha de criticidade e só "
    "existe para os ativos da carteira dos 129.",
    "Bloqueio dos itens 4, 5 e 6: outra SS do MESMO ativo, do tipo INDISPONIBILIDADE PARA "
    "OPERAÇÃO, em situação SS PENDENTE, diferente da SS de entrada. Havendo, o ativo não "
    "entra como resolvido e vai para a lista de verificação.",
    "Item 3 (ajustes): o parecer de ajuste conta como resolvido pelo gestor; a marca "
    "«ainda na Proteção» sai da base de SS/OS — SS PENDENTE ou REPASSADA em equipe PROT.",
    "Item 7 (obra): obra encerrada no AIC (status começa com ENCERRAMENTO) E ligada a ESTA "
    "demanda — número da obra escrito na SS, descrição da obra citando a SS, ou descrição "
    "citando o ativo com ação no equipamento e encerramento posterior à abertura da SS. "
    "Obra que só cita o ativo (limpeza de faixa, cruzeta, isolador, às vezes de 2019) fica "
    "registrada como descartada e não conta.",
    "Item 2 (tratativa com equipamento): intervenção NO EQUIPAMENTO — SS atendida por "
    "equipe do DCMD (execução em campo), obra de substituição/instalação em construção ou "
    "encerrada, ou parecer COEP registrando substituição, entrega ao COCM ou instalação. "
    "SS atendida pelo DMSL (laudo, primeiro ataque) e pelo DEOP (ajustes) contam à parte, "
    "como atendimento técnico — não são troca de equipamento.",
    "Um ativo resolvido por mais de uma régua é contado uma vez só; o motivo registrado é "
    "o mais forte, na ordem obra encerrada → concluída → comissionamento → cancelada → "
    "ajustes.",
    "Três SS de 2023 da foto de entrada (ETO-COEP 00011, 00013 e 00063/2023) não existem "
    "na base de SS/OS de hoje — sumiram do SGM entre as duas fotos. Ficam listadas à parte, "
    "sem veredito.",
]

MOTIVOS = {
    "obra_encerrada": "Obra encerrada no AIC",
    "concluida": "SS concluída, sem indisponibilidade aberta",
    "comissionamento": "Aguardando comissionamento, sem indisponibilidade aberta",
    "cancelada": "Cancelada, sem indisponibilidade aberta",
    "ajustes": "Em fase de ajustes de proteção",
}


def _txt(valor):
    return str(valor).strip() if valor is not None else ""


def ler_foto():
    """Devolve as SS de RL/RT da foto de entrada."""
    import openpyxl

    livro = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    linhas = list(livro["Dados"].iter_rows(values_only=True))
    cabecalho = [_txt(c) for c in linhas[0]]
    registros = [dict(zip(cabecalho, linha)) for linha in linhas[1:] if any(linha)]

    foto = []
    for reg in registros:
        ativo = _txt(reg.get("PLACEMENTDESC"))
        if not re.fullmatch(r"(79|58)\d{8}", ativo):
            continue
        foto.append({
            "numero_ss": _txt(reg.get("NUMERO_SS")),
            "ativo": ativo,
            "tipo": "Religador" if ativo.startswith("79") else "Regulador de Tensão",
            "tiposs": _txt(reg.get("TIPOSS")),
            "criticidade_ss": _txt(reg.get("CRITICIDADE_SS")),
            "localidade": _txt(reg.get("LOCALIDADE")),
            "abertura": _txt(reg.get("DATA_ABERTURA_SS"))[:10],
            "limite": _txt(reg.get("DATA_LIMITE_SS"))[:10],
            "ano": _txt(reg.get("ANO")),
            "descricao_ativo": _txt(reg.get("OBJSPECDESC")),
        })
    return foto, len(registros)


ACAO_NO_EQUIPAMENTO = re.compile(
    r"SUBSTITU|INSTALA|RETIRAD|TROCA|REMANEJ|RECUPERA|MANUTEN[ÇC][ÃA]O CORRET", re.I
)
EQUIPAMENTO_CITADO = re.compile(r"RELIGADOR|REGULADOR|\bRL\b|\bRT\b|RLG", re.I)


def _data(texto):
    texto = (texto or "").strip()
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(texto[:19], formato).date()
        except ValueError:
            continue
    return None


def _indice_aic():
    """Índice de status por obra + o detalhe das 2.386 obras ligadas a RL/RT."""
    with open(ARQ_AIC, encoding="utf-8") as fh:
        indice = json.load(fh)

    detalhe = {}
    por_ativo = defaultdict(set)
    if os.path.exists(ARQ_AIC_RLRT):
        with open(ARQ_AIC_RLRT, encoding="utf-8") as fh:
            for obra in json.load(fh):
                numero = re.sub(r"\D", "", _txt(obra.get("NUM_OBRA")))
                if not numero:
                    continue
                chave = numero.zfill(10)
                detalhe[chave] = obra
                texto = f"{obra.get('DESCRICAO', '')} {obra.get('DESCRICAO_OBRA', '')}"
                for ativo in re.findall(r"\b(79\d{8}|58\d{8})\b", texto):
                    por_ativo[ativo].add(chave)
    return indice, detalhe, por_ativo


def _status_obra(indice, numero):
    digitos = re.sub(r"\D", "", numero or "")
    if not digitos:
        return None
    for chave in (digitos.zfill(10), digitos.lstrip("0")):
        if chave in indice:
            return indice[chave].get("st", "")
    return None


def _classificar_obra(obra, numero_na_ss, ss_da_cadeia, abertura_ss):
    """Diz se uma obra encerrada é DESTA demanda — e com que força.

    A citação do ativo na descrição, sozinha, não serve: o extrato do AIC tem limpeza de
    faixa, troca de cruzeta e isolador citando o mesmo religador, às vezes de 2019. Vale:
      vinculo_direto  o número da obra está escrito numa SS da cadeia, ou a descrição da
                      obra cita o número de uma SS da cadeia;
      indicio_forte   a descrição cita o ativo, fala de ação no equipamento (substituição,
                      instalação, remanejamento) e a obra foi encerrada DEPOIS que a SS de
                      entrada foi aberta;
      descartada      o resto — fica registrada, mas não conta como resolução.
    """
    texto = f"{(obra or {}).get('DESCRICAO', '')} {(obra or {}).get('DESCRICAO_OBRA', '')}"
    encerrada_em = _data((obra or {}).get("DTH_ENCERRAMENTO")) or _data(
        (obra or {}).get("DTH_ENCERRAMENTO_TECNICO")
    )
    if numero_na_ss:
        return "vinculo_direto", encerrada_em, "número da obra escrito na SS"
    for numero_ss in ss_da_cadeia:
        if numero_ss and numero_ss.replace(" ", "") in texto.replace(" ", ""):
            return "vinculo_direto", encerrada_em, f"descrição da obra cita a SS {numero_ss}"
    if not encerrada_em or not abertura_ss or encerrada_em < abertura_ss:
        return "descartada", encerrada_em, "obra encerrada antes da SS de entrada"
    if ACAO_NO_EQUIPAMENTO.search(texto) and EQUIPAMENTO_CITADO.search(texto):
        return "indicio_forte", encerrada_em, "descrição cita o ativo e ação no equipamento"
    return "descartada", encerrada_em, "descrição cita o ativo, mas o serviço é de rede"


def _categoria_parecer(parecer):
    p = (parecer or "").upper()
    if not p:
        return ""
    if "AJUSTE" in p:
        return "ajustes"
    if "COMISSIONAMENTO" in p:
        return "comissionamento"
    if "CONCLU" in p:
        return "concluido"
    if "AQUISI" in p:
        return "aquisicao"
    if "LOG" in p or "ENTREGA" in p or "COCM" in p:
        return "logistica"
    if "CANCELAD" in p or "OPERANDO" in p or "EM OPERA" in p:
        return "operando"
    return "outros"


def _tratativa(ss_cadeia, obras_status, parecer):
    """Separa o que foi mexer NO EQUIPAMENTO do que foi atendimento técnico.

    O gestor perguntou por «tratativas com equipamentos»: troca, entrega, instalação. Uma
    SS atendida pelo DMSL costuma ser laudo ou primeiro ataque — importante, mas não é
    intervenção no equipamento. As duas listas saem separadas.
    """
    equipamento, tecnico = [], []
    for linha in ss_cadeia:
        if linha.get("SITUACAO_SS") != "SS ATENDIDA":
            continue
        depto = D.departamento(linha.get("COD_EQUIPE"), linha.get("TIPOSS"))
        marca = f"SS {linha.get('NUMERO_SS')} atendida pelo {depto}"
        if depto == "DCMD":
            equipamento.append(marca + " (execução em campo)")
        elif depto in ("DMSL", "DEOP"):
            tecnico.append(marca + (" (laudo/primeiro ataque)" if depto == "DMSL" else " (ajustes)"))
    for obra in obras_status:
        status = obra.get("status") or ""
        if obra.get("vinculo") in ("vinculo_direto", "indicio_forte") and (
            status.startswith(ENCERRADA) or status.startswith("CONSTRU")
        ):
            equipamento.append(f"obra {obra['numero']} em {status.split(':')[-1].lower()}")
    texto = (parecer or "").upper()
    if any(m in texto for m in ("SUBSTITU", "ENTREGUE", "INSTALAD", "COMISSIONAMENTO")):
        equipamento.append(f"parecer COEP: {parecer}")
    return equipamento, tecnico


def montar(registros):
    """Classifica a foto de entrada e devolve o resumo para o meta.json."""
    if not os.path.exists(XLSX):
        return None

    foto, total_foto = ler_foto()
    with open(ARQ_MIN, encoding="utf-8") as fh:
        base = json.load(fh)

    por_ativo = defaultdict(list)
    for linha in base:
        por_ativo[_txt(linha.get("NUM_TRAFO"))].append(linha)

    indice_aic, detalhe_aic, obras_por_ativo = _indice_aic()
    parecer_por_ativo = {r["ativo"]: (r.get("parecer_coep") or "") for r in registros}
    carteira = {r["ativo"] for r in registros}
    localidade_carteira = {r["ativo"]: r.get("localidade", "") for r in registros}

    itens = []
    sem_rastro = []

    for entrada in foto:
        ativo = entrada["ativo"]
        linhas = por_ativo.get(ativo, [])
        minha = next(
            (l for l in linhas if _txt(l.get("NUMERO_SS")) == entrada["numero_ss"]), None
        )
        if minha is None:
            sem_rastro.append({**entrada, "motivo": "SS não existe mais na base de SS/OS"})
            continue

        cadeias = D.encadear(linhas)
        cadeia = next(
            (c for c in cadeias
             if any(_txt(l.get("NUMERO_SS")) == entrada["numero_ss"] for l in c["ss"])),
            None,
        )
        resumo_cadeia = D.resumir_demanda(cadeia) if cadeia else None
        ss_cadeia = cadeia["ss"] if cadeia else [minha]

        # bloqueio: outra SS de indisponibilidade PENDENTE no mesmo ativo
        indisponibilidades = [
            {
                "numero": _txt(l.get("NUMERO_SS")),
                "equipe": _txt(l.get("COD_EQUIPE")),
                "departamento": D.departamento(l.get("COD_EQUIPE"), l.get("TIPOSS")),
                "abertura": _txt(l.get("DATA_ABERTURA_SS"))[:10],
                "limite": _txt(l.get("DATA_LIMITE_SS"))[:10],
            }
            for l in linhas
            if TIPO_INDISPONIBILIDADE in (l.get("TIPOSS") or "").upper()
            and l.get("SITUACAO_SS") == "SS PENDENTE"
            and _txt(l.get("NUMERO_SS")) != entrada["numero_ss"]
        ]

        # obras do ativo: as escritas nas SS (vínculo direto) e as que citam o ativo no AIC
        obras_na_ss = {
            re.sub(r"\D", "", _txt(l.get("NUM_OBRA"))).zfill(10)
            for l in ss_cadeia
            if _txt(l.get("NUM_OBRA"))
        }
        numeros_obra = obras_na_ss | obras_por_ativo.get(ativo, set())
        numeros_ss_cadeia = [_txt(l.get("NUMERO_SS")) for l in ss_cadeia]
        abertura_ss = _data(entrada["abertura"])

        obras_status, encerradas, obras_descartadas = [], [], []
        for numero in sorted(numeros_obra):
            status = _status_obra(indice_aic, numero)
            forca, encerrada_em, explicacao = _classificar_obra(
                detalhe_aic.get(numero), numero in obras_na_ss, numeros_ss_cadeia, abertura_ss
            )
            registro_obra = {
                "numero": numero,
                "status": status or "não existe no AIC",
                "encerrada_em": encerrada_em.isoformat() if encerrada_em else "",
                "vinculo": forca,
                "explicacao": explicacao,
                "descricao": (detalhe_aic.get(numero, {}).get("DESCRICAO_OBRA") or "")[:120],
            }
            obras_status.append(registro_obra)
            if status and status.startswith(ENCERRADA):
                if forca in ("vinculo_direto", "indicio_forte"):
                    encerradas.append(registro_obra)
                else:
                    obras_descartadas.append(registro_obra)

        parecer = parecer_por_ativo.get(ativo, "")
        categoria = _categoria_parecer(parecer)
        situacao_ss = _txt(minha.get("SITUACAO_SS"))
        situacao_cadeia = (resumo_cadeia or {}).get("situacao")
        na_protecao = any(
            "PROT" in (l.get("COD_EQUIPE") or "").upper()
            and l.get("SITUACAO_SS") in ("SS PENDENTE", "SS REPASSADA")
            for l in ss_cadeia
        )
        comissionamento = categoria == "comissionamento" or any(
            "COMISSIONAMENTO" in (l.get("TIPOSS") or "").upper() for l in ss_cadeia
        )
        concluida = situacao_cadeia == "concluída" or categoria == "concluido"
        cancelada = situacao_ss == "SS CANCELADA" or situacao_cadeia == "cancelada"
        tratativa, atendimento_tecnico = _tratativa(ss_cadeia, obras_status, parecer)

        # veredito, na ordem de força definida nas premissas
        veredito, motivo, regra = "em_andamento", "", None
        if encerradas:
            veredito, motivo, regra = "resolvido", MOTIVOS["obra_encerrada"], 7
        elif concluida and not indisponibilidades:
            veredito, motivo, regra = "resolvido", MOTIVOS["concluida"], 4
        elif comissionamento and not indisponibilidades:
            veredito, motivo, regra = "resolvido", MOTIVOS["comissionamento"], 5
        elif cancelada and not indisponibilidades:
            veredito, motivo, regra = "resolvido", MOTIVOS["cancelada"], 6
        elif categoria == "ajustes":
            veredito, motivo, regra = "resolvido", MOTIVOS["ajustes"], 3
        elif (concluida or comissionamento or cancelada) and indisponibilidades:
            veredito, regra = "verificar", 4 if concluida else (5 if comissionamento else 6)
            motivo = (
                f"{'Concluída' if concluida else ('Aguardando comissionamento' if comissionamento else 'Cancelada')}, "
                f"mas há {len(indisponibilidades)} SS de indisponibilidade aberta no ativo"
            )
        else:
            motivo = f"Ainda no fluxo — posto atual {(resumo_cadeia or {}).get('posto_atual') or '—'}"

        itens.append({
            **entrada,
            "na_carteira": ativo in carteira,
            "localidade": entrada["localidade"] or localidade_carteira.get(ativo, ""),
            "situacao_hoje": situacao_ss,
            "situacao_cadeia": situacao_cadeia,
            "posto_atual": (resumo_cadeia or {}).get("posto_atual"),
            "postos": (resumo_cadeia or {}).get("postos") or [],
            "repasse_pendurado": (resumo_cadeia or {}).get("repasse_pendurado", False),
            "parecer_coep": parecer,
            "categoria_parecer": categoria,
            "na_protecao": na_protecao,
            "cancelada": cancelada,
            "concluida": concluida,
            "comissionamento": comissionamento,
            "tratativa": tratativa,
            "atendimento_tecnico": atendimento_tecnico,
            "indisponibilidades_abertas": indisponibilidades,
            "obras": obras_status,
            "obras_encerradas": [o["numero"] for o in encerradas],
            "obras_da_demanda": encerradas,
            "obras_descartadas": obras_descartadas,
            "veredito": veredito,
            "motivo": motivo,
            "regra": regra,
            "ss_cadeia": (resumo_cadeia or {}).get("ss") or [],
        })

    resolvidos = [i for i in itens if i["veredito"] == "resolvido"]
    verificar = [i for i in itens if i["veredito"] == "verificar"]
    andamento = [i for i in itens if i["veredito"] == "em_andamento"]

    def ativos(lista):
        return {i["ativo"] for i in lista}

    por_regra = Counter(i["regra"] for i in resolvidos if i["regra"])
    ajustes = [i for i in itens if i["categoria_parecer"] == "ajustes"]

    resumo = {
        "premissas": PREMISSAS,
        "total_foto": total_foto,
        "total_ss": len(itens) + len(sem_rastro),
        "total_ativos": len({i["ativo"] for i in itens} | {s["ativo"] for s in sem_rastro}),
        "por_tipo": dict(Counter(i["tipo"] for i in itens)),
        "sem_rastro": sem_rastro,
        "resolvidos": {
            "ss": len(resolvidos),
            "ativos": len(ativos(resolvidos)),
            "por_regra": {str(k): v for k, v in sorted(por_regra.items())},
            "por_motivo": dict(Counter(i["motivo"] for i in resolvidos)),
            "lista": [
                {k: i[k] for k in ("numero_ss", "ativo", "tipo", "localidade", "motivo",
                                   "regra", "parecer_coep", "na_carteira", "na_protecao",
                                   "obras_encerradas", "situacao_hoje")}
                for i in sorted(resolvidos, key=lambda x: (x["regra"] or 9, x["ativo"]))
            ],
        },
        "verificar": {
            "ss": len(verificar),
            "ativos": len(ativos(verificar)),
            "lista": [
                {k: i[k] for k in ("numero_ss", "ativo", "tipo", "localidade", "motivo",
                                   "parecer_coep", "indisponibilidades_abertas",
                                   "na_carteira", "situacao_hoje")}
                for i in sorted(verificar, key=lambda x: x["ativo"])
            ],
        },
        "em_andamento": {
            "ss": len(andamento),
            "ativos": len(ativos(andamento)),
            "por_posto": dict(Counter(i["posto_atual"] or "—" for i in andamento)),
            "lista": [
                {k: i[k] for k in ("numero_ss", "ativo", "tipo", "localidade", "posto_atual",
                                   "parecer_coep", "repasse_pendurado", "na_carteira",
                                   "situacao_hoje", "abertura")}
                for i in sorted(andamento, key=lambda x: (x["posto_atual"] or "", x["ativo"]))
            ],
        },
        "canceladas": {
            "ss": sum(1 for i in itens if i["situacao_hoje"] == "SS CANCELADA"),
            "ativos": len({i["ativo"] for i in itens if i["situacao_hoje"] == "SS CANCELADA"}),
            "sem_reincidencia": sum(1 for i in itens
                                    if i["situacao_hoje"] == "SS CANCELADA"
                                    and not i["indisponibilidades_abertas"]),
        },
        "tratativas": {
            "ss": sum(1 for i in itens if i["tratativa"]),
            "ativos": len({i["ativo"] for i in itens if i["tratativa"]}),
            "atendimento_tecnico_ss": sum(
                1 for i in itens if i["atendimento_tecnico"] and not i["tratativa"]
            ),
            "por_veredito": dict(Counter(i["veredito"] for i in itens if i["tratativa"])),
            "lista": [
                {"numero_ss": i["numero_ss"], "ativo": i["ativo"], "tipo": i["tipo"],
                 "localidade": i["localidade"], "evidencias": i["tratativa"],
                 "veredito": i["veredito"], "motivo": i["motivo"]}
                for i in sorted((x for x in itens if x["tratativa"]), key=lambda x: x["ativo"])
            ],
            "so_atendimento_tecnico": [
                {"numero_ss": i["numero_ss"], "ativo": i["ativo"], "localidade": i["localidade"],
                 "evidencias": i["atendimento_tecnico"], "posto_atual": i["posto_atual"]}
                for i in sorted((x for x in itens if x["atendimento_tecnico"] and not x["tratativa"]),
                                key=lambda x: x["ativo"])
            ],
        },
        "ajustes": {
            "ss": len(ajustes),
            "ainda_na_protecao": sum(1 for i in ajustes if i["na_protecao"]),
            "lista": [
                {"numero_ss": i["numero_ss"], "ativo": i["ativo"], "localidade": i["localidade"],
                 "na_protecao": i["na_protecao"], "posto_atual": i["posto_atual"],
                 "parecer_coep": i["parecer_coep"]}
                for i in sorted(ajustes, key=lambda x: x["ativo"])
            ],
        },
    }
    resumo["reducao_percentual"] = round(
        100 * resumo["resolvidos"]["ativos"] / max(resumo["total_ativos"], 1), 1
    )

    # leva o recorte para dentro da ficha de cada ativo da carteira
    por_ativo_entrada = defaultdict(list)
    for item in itens:
        por_ativo_entrada[item["ativo"]].append(item)
    for reg in registros:
        meus = por_ativo_entrada.get(reg["ativo"])
        if meus:
            reg["entrada"] = [
                {k: m[k] for k in ("numero_ss", "abertura", "tiposs", "situacao_hoje",
                                   "veredito", "motivo", "regra", "posto_atual",
                                   "indisponibilidades_abertas", "obras_encerradas",
                                   "tratativa")}
                for m in meus
            ]

    return resumo
