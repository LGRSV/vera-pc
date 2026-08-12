"""
Enriquecimento a partir da planilha GESTÃO DE EQUIPAMENTOS.

Cinco abas entram aqui:
  BASE SS_OS                    coordenadas, alimentador e as datas reais da SS
  Planilha1                     modelo, status de gestão, descrição de compra e valor previsto
  Plan1                         dias pendente e status de atendimento
  Ajustes RL Poste              especificação e ajustes de proteção dos religadores
  Ajustes Reguladores de Tensão especificação dos reguladores

As coordenadas vêm projetadas em SIRGAS 2000 / UTM 22S (EPSG:31982) — inclusive os pontos a
leste do limite da zona, que a distribuidora mantém na mesma projeção. A conversão inversa
para latitude e longitude é feita aqui em Python puro, sem dependência de biblioteca de
geoprocessamento.
"""

import datetime
import math
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(RAIZ, "data", "raw", "GESTAO_DE_EQUIPAMENTOS.xlsx")

DATA_REF = datetime.date(2026, 8, 12)

# SIRGAS 2000 — mesmo elipsoide do WGS 84.
SEMI_EIXO = 6378137.0
ACHATAMENTO = 1 / 298.257222101
FATOR_ESCALA = 0.9996
MERIDIANO_CENTRAL = -51.0          # zona 22
FALSO_LESTE = 500000.0
FALSO_NORTE = 10000000.0           # hemisfério sul


def utm_para_latlon(leste, norte):
    """Inversa da projeção transversa de Mercator. Devolve (lat, lon) em graus."""
    e2 = ACHATAMENTO * (2 - ACHATAMENTO)
    e_linha2 = e2 / (1 - e2)

    x = leste - FALSO_LESTE
    y = norte - FALSO_NORTE

    m = y / FATOR_ESCALA
    mu = m / (SEMI_EIXO * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))

    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    lat1 = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
        + (1097 * e1**4 / 512) * math.sin(8 * mu)
    )

    sin1, cos1, tan1 = math.sin(lat1), math.cos(lat1), math.tan(lat1)
    c1 = e_linha2 * cos1**2
    t1 = tan1**2
    n1 = SEMI_EIXO / math.sqrt(1 - e2 * sin1**2)
    r1 = SEMI_EIXO * (1 - e2) / (1 - e2 * sin1**2) ** 1.5
    d = x / (n1 * FATOR_ESCALA)

    lat = lat1 - (n1 * tan1 / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * e_linha2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * e_linha2 - 3 * c1**2) * d**6 / 720
    )
    lon = (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * e_linha2 + 24 * t1**2) * d**5 / 120
    ) / cos1

    return math.degrees(lat), MERIDIANO_CENTRAL + math.degrees(lon)


def faixa_de_potencia(bruto):
    """
    Classifica a potência do regulador. O campo aceita valor único ("400") ou um por fase
    ("167/250/167") nos bancos montados com células de capacidades diferentes — nesse caso
    a faixa não é um número só, e o banco é marcado como misto.
    """
    numeros = [float(n) for n in re.findall(r"\d+(?:[.,]\d+)?", (bruto or "").replace(",", "."))]
    if not numeros:
        return "", None
    if len(set(numeros)) > 1:
        return "Banco misto", max(numeros)
    valor = numeros[0]
    if valor <= 200:
        return "até 200 kvar", valor
    if valor <= 300:
        return "201 a 300 kvar", valor
    return "301 a 400 kvar", valor


def classe_de_tensao(bruto):
    """Normaliza «34.500», «34,5» e «34.5» para a mesma classe."""
    achado = re.search(r"\d+(?:[.,]\d+)?", (bruto or "").replace(".", "").replace(",", "."))
    if not achado:
        return ""
    valor = float(achado.group())
    while valor >= 1000:
        valor /= 1000
    if 12 <= valor <= 15:
        return "13,8 kV"
    if 30 <= valor <= 40:
        return "34,5 kV"
    return f"{valor:g} kV".replace(".", ",")


def texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, datetime.datetime):
        return valor.date().isoformat()
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def data_de(valor):
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, str) and re.match(r"\d{4}-\d{2}-\d{2}", valor):
        return datetime.date.fromisoformat(valor[:10])
    return None


def _linhas(planilha):
    """Lê a aba assumindo cabeçalho na primeira linha."""
    bruto = list(planilha.iter_rows(values_only=True))
    if not bruto:
        return []
    cabecalho = [texto(c) for c in bruto[0]]
    return [
        {cabecalho[i]: linha[i] for i in range(len(cabecalho)) if cabecalho[i]}
        for linha in bruto[1:]
    ]


def carregar(ativos_validos):
    """Devolve {ativo: {geo, ss, gestao, especificacao}} e um resumo agregado."""
    try:
        import openpyxl
    except ImportError:
        print("  aviso: openpyxl ausente, enriquecimento ignorado")
        return {}, {}

    livro = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    por_ativo = {}

    def alvo(ativo):
        ativo = texto(ativo)
        if ativo not in ativos_validos:
            return None
        return por_ativo.setdefault(ativo, {})

    # --- coordenadas e datas reais da SS ---
    for linha in _linhas(livro["BASE SS_OS"]):
        registro = alvo(linha.get("NUM_TRAFO"))
        if registro is None:
            continue

        leste, norte = linha.get("COORD_X"), linha.get("COORD_Y")
        if leste and norte:
            lat, lon = utm_para_latlon(float(leste), float(norte))
            registro["geo"] = {
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "coord_x": int(leste),
                "coord_y": int(norte),
                "cod_gis": texto(linha.get("COD_GIS")),
                "alimentador": texto(linha.get("ALIMENTADOR")),
            }

        abertura = data_de(linha.get("DATA_ABERTURA_SS"))
        limite = data_de(linha.get("DATA_LIMITE_SS"))
        termino = data_de(linha.get("DATA_TERMINO_SS"))
        dados_ss = {
            "numero": texto(linha.get("NUMERO_SS")),
            "criticidade_ss": texto(linha.get("CRITICIDADE_SS")),
            "situacao": texto(linha.get("SITUACAO_SS")),
            "org_solicitante": texto(linha.get("ORG_SOLIC")),
            "data_abertura": abertura.isoformat() if abertura else "",
            "data_limite": limite.isoformat() if limite else "",
            "data_termino": termino.isoformat() if termino else "",
        }
        if abertura:
            dados_ss["dias_aberta"] = (DATA_REF - abertura).days
        if limite and not termino:
            dados_ss["dias_sla"] = (DATA_REF - limite).days
            dados_ss["sla_estourado"] = limite < DATA_REF
        registro["ss"] = dados_ss

    # --- modelo, status de gestão e valor previsto ---
    for linha in _linhas(livro["Planilha1"]):
        registro = alvo(linha.get("Ativo"))
        if registro is None:
            continue
        gestao = {
            "modelo": texto(linha.get("Modelo")),
            "status": texto(linha.get("Status")),
            "status_apresentacao": texto(linha.get("Status (apresentação)")),
            "responsavel": texto(linha.get("Responsável")),
            "descricao_compra": texto(linha.get("Descrição compra")),
            "ss_sgm": texto(linha.get("SS SGM")),
        }
        valor = linha.get("Valor previsto")
        if isinstance(valor, (int, float)):
            gestao["valor_previsto"] = round(float(valor), 2)
        registro.setdefault("gestao", {}).update({k: v for k, v in gestao.items() if v})

    # --- dias pendente ---
    for linha in _linhas(livro["Plan1"]):
        registro = alvo(linha.get("Ativo"))
        if registro is None:
            continue
        gestao = registro.setdefault("gestao", {})
        dias = linha.get("Dias Pendente")
        if isinstance(dias, (int, float)):
            gestao["dias_pendente"] = int(dias)
        for chave, coluna in (("status_atendimento", "Status Atendimento"), ("municipio", "Município")):
            if texto(linha.get(coluna)):
                gestao[chave] = texto(linha.get(coluna))

    # --- especificação e ajustes: religadores ---
    for linha in _linhas(livro["Ajustes RL Poste"]):
        registro = alvo(linha.get("EQUIPAMENTO"))
        if registro is None:
            continue
        especificacao = {
            "familia": "Religador",
            "marca_modelo": texto(linha.get("RELE")),
            "tipo_instalacao": texto(linha.get("TIPO")),
            "alimentador": texto(linha.get("ALIMENTADOR")),
            "tensao_kv": texto(linha.get("TENSÃO")),
            "classe_tensao": classe_de_tensao(texto(linha.get("TENSÃO"))),
            "faixa_potencia": "Não se aplica",
            "estudo": texto(linha.get("ESTUDO")),
            "ajustes": {
                "Religamentos": texto(linha.get("RELIGAMENTOS")),
                "4 grupos": texto(linha.get("4 GRUPOS")),
                "Curva rápida": texto(linha.get("CURVA RÁPIDA")),
                "46 (I2/I1)": texto(linha.get("46 (I2/I1)")),
                "67 (direcional)": texto(linha.get("67 (DIRECIONAL)")),
                "27 (subtensão)": texto(linha.get("27 (SUBTENSÃO)")),
                "SEF": texto(linha.get("SEF")),
            },
        }
        registro["especificacao"] = {k: v for k, v in especificacao.items() if v}

    # --- especificação: reguladores de tensão ---
    for linha in _linhas(livro["Ajustes Reguladores de Tensão"]):
        registro = alvo(linha.get("CÓDIGO"))
        if registro is None:
            continue
        parte_ativa = texto(linha.get("PARTE ATIVA"))
        controlador = texto(linha.get("CONTROLADOR"))
        potencia_bruta = texto(linha.get("POTÊNCIA [Kvar]"))
        faixa, potencia_max = faixa_de_potencia(potencia_bruta)
        especificacao = {
            "familia": "Regulador de Tensão",
            "marca_modelo": " / ".join(filter(None, [parte_ativa, controlador])),
            "parte_ativa": parte_ativa,
            "controlador": controlador,
            "potencia_kvar": potencia_bruta,
            "faixa_potencia": faixa,
            "potencia_max_kvar": potencia_max,
            "classe_tensao": classe_de_tensao(texto(linha.get("TENSÃO PRIMÁRIA [Kv]"))),
            "corrente_a": texto(linha.get("CORRENTE [A]")),
            "tensao_controle_v": texto(linha.get("TENSÃO CONTROLE [V]")),
            "tensao_primaria": texto(linha.get("TENSÃO PRIMÁRIA [Kv]")),
            "alimentador": texto(linha.get("ALIMENTADOR")),
            "automatizado": texto(linha.get("AUTOMATIZADO")),
            "descricao": texto(linha.get("DESCRIÇÃO")),
            "estudo": texto(linha.get("ESTUDO")),
            "autor_estudo": texto(linha.get("AUTOR")),
            "data_estudo": texto(linha.get("DATA ESTUDO"))[:10],
        }
        registro["especificacao"] = {k: v for k, v in especificacao.items() if v}

    livro.close()
    return por_ativo, resumir(por_ativo)


def resumir(por_ativo):
    from collections import Counter

    com_geo = [d for d in por_ativo.values() if d.get("geo")]
    com_ss = [d for d in por_ativo.values() if d.get("ss")]
    estourados = [d for d in com_ss if d["ss"].get("sla_estourado")]
    modelos = Counter(
        d["especificacao"]["marca_modelo"]
        for d in por_ativo.values()
        if d.get("especificacao", {}).get("marca_modelo")
    )
    familias = Counter(
        d["especificacao"]["familia"]
        for d in por_ativo.values()
        if d.get("especificacao", {}).get("familia")
    )
    valores = [
        d["gestao"]["valor_previsto"]
        for d in por_ativo.values()
        if d.get("gestao", {}).get("valor_previsto")
    ]
    dias = [
        d["gestao"]["dias_pendente"]
        for d in por_ativo.values()
        if d.get("gestao", {}).get("dias_pendente") is not None
    ]

    def contar(campo, filtro=None):
        contagem = Counter(
            d["especificacao"][campo]
            for d in por_ativo.values()
            if d.get("especificacao", {}).get(campo)
            and (filtro is None or d["especificacao"].get("familia") == filtro)
        )
        return [{"rotulo": k, "total": v} for k, v in contagem.most_common()]

    ordem_faixa = ["até 200 kvar", "201 a 300 kvar", "301 a 400 kvar", "Banco misto"]
    por_faixa = sorted(
        contar("faixa_potencia", "Regulador de Tensão"),
        key=lambda i: ordem_faixa.index(i["rotulo"]) if i["rotulo"] in ordem_faixa else 99,
    )

    return {
        "por_faixa_potencia": por_faixa,
        "por_classe_tensao": contar("classe_tensao"),
        "com_especificacao": sum(1 for d in por_ativo.values() if d.get("especificacao")),
        "com_coordenada": len(com_geo),
        "com_data_ss": len(com_ss),
        "sla_estourado": len(estourados),
        "maior_atraso_sla": max((d["ss"]["dias_sla"] for d in estourados), default=0),
        "maior_dias_aberta": max((d["ss"].get("dias_aberta", 0) for d in com_ss), default=0),
        "media_dias_pendente": round(sum(dias) / len(dias)) if dias else 0,
        "valor_previsto_total": round(sum(valores), 2),
        "com_valor_previsto": len(valores),
        "por_modelo": [{"rotulo": k, "total": v} for k, v in modelos.most_common()],
        "por_familia": [{"rotulo": k, "total": v} for k, v in familias.most_common()],
    }
