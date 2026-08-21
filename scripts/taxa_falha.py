"""
Taxa de falha de religadores e reguladores — lógica em quatro camadas.

A pergunta do gestor (21/08): como medir a taxa de falha do parque de RL/RT usando a
base de SS/OS, o tipo de fato e o que foi substituído.

O problema é que a base SS/OS não é um registro de falhas: é um registro de SOLICITAÇÕES.
Uma falha pode gerar quatro SS (repasse a repasse) e uma SS pode não ter falha nenhuma
por trás (ajuste de proteção, comissionamento, obra nova). Medir "SS por equipamento"
dá 4,9 SS/ativo/ano, número que não significa nada. A lógica abaixo separa as camadas:

  C1  EVENTO      a SS vira evento de falha (régua de tipo) e as SS gêmeas colapsam
                  numa demanda só (demandas.encadear) — 1 demanda = 1 evento
  C2  EXPOSIÇÃO   o denominador é equipamento-ano do parque informado pelo gestor
                  (1.297 religadores, 197 reguladores), não a carteira de
                  indisponíveis (que já é o resultado, não a população)
  C3  MODO        o par ORIGEM_SS × DEFEITO_SS diz QUAL fato; cobertura parcial, então
                  a distribuição vale sobre os declarados e isso é dito no número
  C4  CONSEQUÊNCIA  o que foi substituído vem do OBRAS_EQ_ESPECIAL (peça + código de
                  material + data), nunca dos campos FABRICANTE_* da SS, que estão vazios

λ = eventos de falha ÷ equipamento-ano. Reportado por 100 equipamentos-ano para não
trabalhar com três zeros à direita da vírgula.

Rodar: python3 scripts/taxa_falha.py
Grava: data/missao/taxa_falha.json
"""

import datetime
import json
import os
import re
import sys
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import demandas  # noqa: E402  — reaproveita a regra de SS gêmeas já validada

ARQ_MIN = os.path.join(RAIZ, "data", "missao", "ssos_min.json")
XLSX_GESTAO = os.path.join(RAIZ, "data", "raw", "GESTAO_DE_EQUIPAMENTOS.xlsx")
XLSX_OBRAS = os.path.join(RAIZ, "data", "raw", "OBRAS_EQ_ESPECIAL.xlsx")
XLSX_ENTRADA = os.path.join(RAIZ, "data", "raw", "BASE_SS_OS_EQ_ESPECIAIS_ENTRADA.xlsx")
SAIDA = os.path.join(RAIZ, "data", "missao", "taxa_falha.json")

# A base de SS/OS só tem lastro a partir de 2024: 2 SS em 2022 e 58 em 2023 contra
# 2.197 em 2024. Não é queda de falha, é extrato truncado. 2026 entra à parte porque
# está aberto — anualizar ano parcial junto dos cheios mistura duas coisas.
ANOS_CHEIOS = (2024, 2025)
ANO_PARCIAL = 2026
FIM_DO_PARCIAL = datetime.date(2026, 8, 12)  # data da foto da base

# Parque informado pelo gestor em 21/08 — é a autoridade sobre a população exposta.
# O cadastro de ajustes de GESTÃO DE EQUIPAMENTOS chega a 1.292 religadores e 189
# reguladores com código válido (mais o "RT SE CRISTALÂNDIA", sem código): faltam 5
# religadores e 8 reguladores que operam sem estudo de ajuste cadastrado. A diferença
# não é erro de contagem, é lacuna de cadastro — e vale como achado por si.
PARQUE = {"religador": 1297, "regulador": 197}

PREMISSAS = [
    "O evento se ancora na DATA DE OCORRÊNCIA, não na abertura da SS — regra do "
    "gestor em 21/08. Abertura é o carimbo do registro: vem depois da falha (mediana "
    "de 21 dias, p75 de 63, cauda de 734) e o SGM ainda a reescreve ao reabrir ou "
    "repassar. Como a defasagem nunca é negativa, usar abertura erra sempre para o "
    "mesmo lado: infla o ano corrente e esvazia os anteriores.",
    "Cobertura da ocorrência é a limitação de hoje: o extrato de 6.305 SS de RL/RT no "
    "repositório não traz a coluna DATA_OCORRENCIA_SS — ela só existe no extrato do "
    "COEP (211 SS, 120 casando com a base). O evento sem ocorrência declarada fica "
    "ancorado na abertura e MARCADO como tal; a taxa por ano só fecha de verdade com "
    "o extrato completo trazendo a coluna.",
    "Janela 2024–2025 para taxa fechada. 2022 (2 SS) e 2023 (58 SS) são extrato "
    "truncado, não parque saudável; 2026 é ano aberto e vai em separado, anualizado "
    "pela fração decorrida até 12/08.",
    "SS não é falha. Ajuste de proteção, comissionamento, obra nova, atualização "
    "cadastral, inspeção preventiva e troca programada de bateria saem do numerador — "
    "são 2.362 das 6.305 SS de RL/RT da base.",
    "SS não é evento. O repasse do SGM cria SS nova com o mesmo carimbo de abertura; "
    "as SS gêmeas colapsam numa demanda (regra já validada em demandas.py) e cada "
    "demanda de falha conta UM evento.",
    "O denominador é o parque informado pelo gestor em 21/08: 1.297 religadores e 197 "
    "reguladores. Não é a carteira de indisponíveis — a carteira é o resultado que se "
    "quer medir, usá-la como base daria taxa perto de 100%.",
    "O cadastro de ajustes de GESTÃO DE EQUIPAMENTOS alcança 1.292 religadores e 189 "
    "reguladores: 5 religadores e 8 reguladores do parque não têm estudo de ajuste "
    "cadastrado. A lacuna não muda a conta (o denominador é o parque do gestor), mas "
    "limita a estratificação por modelo, que só existe nesse cadastro.",
    "O parque é foto de hoje aplicada ao passado: equipamento instalado em 2025 entra "
    "na exposição de 2024. Isso infla o denominador dos anos antigos e portanto "
    "SUBESTIMA a taxa de 2024. É viés conhecido e de sinal conhecido.",
    "Regulador é banco de três células. O parque conta banco (197) e a SS quase sempre "
    "é do banco; falha de célula única (Araguaçu, fase "
    "B) é evento do banco, com o componente registrado na camada de modo de falha.",
    "Ativo com SS que o cadastro de ajustes não tem entra no numerador com a família "
    "lida na descrição do ativo na própria SS — ele faz parte do parque do gestor, que "
    "é o denominador. Só fica de fora quem nem cadastro nem descrição identificam.",
    "ORIGEM_SS e DEFEITO_SS são de preenchimento opcional no SGM. A distribuição de "
    "modo de falha vale sobre as SS que declararam o par, e a cobertura é publicada "
    "junto do percentual — não se extrapola o silêncio.",
    "FABRICANTE_INSTALADO e FABRICANTE_RETIRADO não servem: 25 e 4 preenchimentos em "
    "6.305 SS, vários deles com texto de e-mail colado. O que foi substituído sai de "
    "OBRAS_EQ_ESPECIAL (peça, código de material, data da substituição).",
    "A SS pendura no código do religador mesmo quando o fato é do poste, da cruzeta ou "
    "da vegetação — o equipamento é o marco do trecho. Só entra no numerador a SS cujo "
    "objeto do fato é o equipamento (ORIGEM_SS do equipamento, ou esquema que não nomeia "
    "componente de rede). Sem esse filtro a taxa do ativo vira taxa do alimentador.",
    "Taxa de falha e taxa de substituição são indicadores diferentes: nem toda falha "
    "vira troca de equipamento (parte é ajuste, religamento, reaperto) e a troca é a "
    "parcela cara. As duas são reportadas lado a lado.",
]

# ── Camada 1: o que é evento de falha ────────────────────────────────────────────
FALHA_TIPOSS = {
    "INDISPONIBILIDADE PARA OPERAÇÃO",
    "EM OPERAÇÃO COM ANOMALIA",
    "ANOMALIA EM RELIGADOR",
    "ANOMALIA EM REGULADORES",
    "AVISO DE ANOMALIA",
    "AVISO DE EMERGÊNCIA",
    "AVISO ELEMENTO REINCIDENTE",
}
NAO_FALHA_TIPOSS = {
    "AJUSTES DE PROTEÇÃO",
    "AJUSTE DE RELÉ",
    "COMISSIONAMENTO",
    "OBRAS (NOVOS EQUIPAMENTOS)",
    "AVISO DE CADASTRO",
    "AVISO PROTEÇÃO & SELETIVIDADE",
    "AVISO DE INCONSISTÊNCIA",
    "CLUSTER",
    "MELHORIA POSTO DE TRANSFORMAÇÃO",
}
# Indisponibilidade é falha funcional (parou); anomalia é degradação (opera com defeito).
FUNCIONAL = {"INDISPONIBILIDADE PARA OPERAÇÃO", "AVISO DE EMERGÊNCIA", "FORA DE SERVIÇO"}

# Terceiro eixo, e o que mais engana nesta base: a SS pendura no código do religador
# porque ele é o marco do trecho, mas o fato é do POSTE, da cruzeta, do conector, da
# vegetação. Sem separar objeto do fato, a taxa de falha do equipamento vira taxa de
# ocorrência do alimentador — 88 SS de POSTE e 41 de ATERRAMENTO entravam como falha
# de religador. Só conta como falha quem tem o fato NO equipamento.
ORIGEM_DA_REDE = {
    "POSTE", "ESTRUTURA", "ESTRUTURA PRIMÁRIA", "CRUZETA", "ATERRAMENTO", "CONECTOR",
    "CONECTOR DERIVAÇÃO CUNHA", "JUMPER MT/CONECTOR JUMPER MT", "CABOS MT", "CABOS BT",
    "CABOS DE LIGAÇOES MT", "PÁRA-RAIOS", "ISOLADOR", "CHAVE", "CHAVE FUSÍVEL",
    "EMENDAS", "ESTAI", "ESPAÇADOR", "VEGETAÇÃO PODA DE ÁRVORE",
    "REDE PRIMÁRIA PODA DE ÁRVORE",
}
ORIGEM_ADMINISTRATIVA = {
    "INEXISTENTE", "INCONSISTÊNCIA CADASTRAL", "PLACA DE IDENTIFICAÇÃO", "INSPEÇÃO VISUAL",
}
RE_ESQUEMA_DE_REDE = re.compile(
    r"POSTE|PODA|CONDUTOR|ISOLADOR|CONEX[ÃA]O MT|CRUZETA|P[ÁA]RA-?RAIOS|ATERRAMENTO|"
    r"SUBSTITUI[ÇC][ÃA]O DE CHAVE|LINHA VIVA|EMENDA",
    re.I,
)
TIPOSS_DE_REDE = {
    "NOTA DE SERVIÇO (NS) - LINHA VIVA", "NOTA DE SERVIÇO (NS) - PODA",
    "FORMS SUBST DE POSTES", "FORMS CHAVE INST DEOP",
}

RE_MC = re.compile(r"^MC\s*-|^MC-|MANUTEN[ÇC][ÃA]O CORRETIVA", re.I)
RE_PROGRAMADA = re.compile(
    r"^MP\s*-|^PREVNP|^COM\s*-|^INSP|ATUALIZA[ÇC][ÃA]O CADASTRAL|INSP\w* PREV", re.I
)


def objeto_do_fato(ss):
    """equipamento | rede | administrativo — de quem é o defeito, afinal."""
    origem = (ss.get("ORIGEM_SS") or "").strip().upper()
    esquema = (ss.get("ESQUEMA") or "").strip().upper()
    tiposs = (ss.get("TIPOSS") or "").strip().upper()
    if origem in ORIGEM_DA_REDE:
        return "rede"
    if origem in ORIGEM_ADMINISTRATIVA:
        return "administrativo"
    if tiposs in TIPOSS_DE_REDE:
        return "rede"
    # origem em branco: o esquema desempata. "MC - POSTES" no código do religador é
    # serviço de poste, não falha de equipamento.
    if not origem and RE_ESQUEMA_DE_REDE.search(esquema):
        return "rede"
    return "equipamento"


def classificar(ss):
    """falha | programada | rede | indefinida — a régua de numerador."""
    tiposs = (ss.get("TIPOSS") or "").strip().upper()
    esquema = (ss.get("ESQUEMA") or "").strip().upper()
    objeto = objeto_do_fato(ss)
    if objeto != "equipamento":
        return objeto if objeto == "rede" else "programada"
    if tiposs in FALHA_TIPOSS:
        return "falha"
    if tiposs in NAO_FALHA_TIPOSS:
        return "programada"
    if RE_MC.search(esquema):
        return "falha"
    if RE_PROGRAMADA.search(esquema):
        return "programada"
    if tiposs.startswith("FORMS") or tiposs.startswith("NOTA DE SERVIÇO"):
        return "programada"
    return "indefinida"


def severidade(ss_da_demanda):
    tipos = {(s.get("TIPOSS") or "").strip().upper() for s in ss_da_demanda}
    origens = {(s.get("ORIGEM_SS") or "").strip().upper() for s in ss_da_demanda}
    return "funcional" if (tipos | origens) & FUNCIONAL else "anomalia"


# ── Camada 2: o parque ───────────────────────────────────────────────────────────
def _celulas(ws, max_col=None):
    return list(ws.iter_rows(min_row=2, max_col=max_col, values_only=True))


def parque():
    """Devolve {codigo: {familia, marca}} a partir do cadastro de ajustes."""
    import openpyxl

    wb = openpyxl.load_workbook(XLSX_GESTAO, read_only=True, data_only=False)
    frota = {}
    for linha in _celulas(wb["Ajustes RL Poste"], 14):
        cod = str(linha[0] or "").strip()
        if not cod.isdigit():
            continue
        marca = str(linha[10] or "").strip().upper() or "SEM CADASTRO"
        frota[cod] = {"familia": "religador", "marca": marca.split()[0] if marca else "SEM CADASTRO"}
    for linha in _celulas(wb["Ajustes Reguladores de Tensão"], 12):
        cod = str(linha[0] or "").strip()
        if not cod.isdigit():
            continue
        parte = str(linha[3] or "").strip().upper() or "SEM CADASTRO"
        frota[cod] = {"familia": "regulador", "marca": parte.split("/")[0].split()[0]}
    return frota


RE_FAMILIA_RT = re.compile(r"REGULADOR", re.I)
RE_FAMILIA_RL = re.compile(r"RELIGADOR", re.I)


def familia_pela_ss(linhas):
    """Família do ativo que o cadastro de ajustes não tem, lida na descrição da SS."""
    texto = " ".join((l.get("DESCICAO_DO_ATIVO") or "") for l in linhas)
    if RE_FAMILIA_RT.search(texto):
        return "regulador"
    if RE_FAMILIA_RL.search(texto):
        return "religador"
    return None


def exposicao(frota):
    """equipamento-ano por família e por marca, nos anos cheios e no parcial.

    A família usa o parque do gestor (PARQUE). A marca só pode usar o cadastro de
    ajustes, que é a única fonte que diz o modelo — por isso a soma das marcas fica
    abaixo do parque, e a diferença é publicada como 'sem modelo cadastrado'.
    """
    anos_cheios = len(ANOS_CHEIOS)
    fracao_parcial = (FIM_DO_PARCIAL - datetime.date(ANO_PARCIAL, 1, 1)).days / 365.0
    cadastradas = Counter(v["familia"] for v in frota.values())
    por_marca = Counter((v["familia"], v["marca"]) for v in frota.values())
    return {
        "anos_cheios": anos_cheios,
        "fracao_parcial": round(fracao_parcial, 4),
        "familia": dict(PARQUE),
        "no_cadastro_de_ajustes": dict(cadastradas),
        "sem_estudo_cadastrado": {
            f: PARQUE[f] - cadastradas.get(f, 0) for f in PARQUE
        },
        "marca": {f"{f}|{m}": n for (f, m), n in por_marca.items()},
    }


# ── Camada 4: o que foi substituído ──────────────────────────────────────────────
# Objeto DIRETO da substituição. "SUBSTITUIÇÃO DE 02 POSTES E INSTALAÇÃO DE RELIGADOR"
# é obra de poste; só conta quando o equipamento é o que está sendo trocado.
RE_OBRA_SUBST = re.compile(
    r"SUBSTITUI[ÇC][ÃA]O\s+D[EO]\s*(?:\d+\s+)?(?:CH\.?\s+)?(?:ATIVO\s+D[EO]\s+)?"
    r"(RELIGADOR|REGULADOR)",
    re.I,
)
ARQ_AIC_RLRT = os.path.join(RAIZ, "data", "missao", "aic_rlrt.json")
RE_NAO_E_PECA = re.compile(r"REQUISITAR|APROVEITAR|VAMOS|VERIFICAR|AGUARD|^NA$|^N/?A$", re.I)


def trocas_no_aic():
    """Taxa de substituição: obra do AIC cujo objeto é o próprio equipamento."""
    if not os.path.exists(ARQ_AIC_RLRT):
        return None
    with open(ARQ_AIC_RLRT, encoding="utf-8") as fh:
        obras = json.load(fh)
    por_ano = defaultdict(Counter)
    total = Counter()
    for obra in obras:
        m = RE_OBRA_SUBST.search(obra.get("DESCRICAO_OBRA") or "")
        if not m:
            continue
        familia = "religador" if m.group(1).upper().startswith("RELIG") else "regulador"
        total[familia] += 1
        ano = (obra.get("DATA_CONCLUSAO_FISICA") or "")[:4]
        if ano.isdigit():
            por_ano[ano][familia] += 1
    return {
        "obras_de_substituicao": dict(total),
        "por_ano_de_conclusao_fisica": {a: dict(c) for a, c in sorted(por_ano.items())},
    }


def substituicoes():
    import openpyxl

    wb = openpyxl.load_workbook(XLSX_OBRAS, read_only=True, data_only=True)
    linhas = list(wb["Planilha1"].iter_rows(values_only=True))
    cab = [str(c).strip() if c else "" for c in linhas[1]]
    idx = {nome: i for i, nome in enumerate(cab) if nome}
    peca, material, concluidas, familia = Counter(), Counter(), 0, Counter()
    total = 0
    for linha in linhas[2:]:
        ativo = str(linha[idx.get("Ativo", 2)] or "").strip()
        if not ativo.isdigit():
            continue
        total += 1
        d = str(linha[idx["Defeito identificado"]] or "").strip()
        if d and d.lower() != "none":
            for parte in re.split(r"[,/]| e ", d):
                parte = parte.strip().strip(".").title()
                # o campo é livre: o COEP às vezes escreve o encaminhamento em vez da
                # peça ("Vamos requisitar", "Aproveitar do 79000...").
                if len(parte) > 2 and not RE_NAO_E_PECA.search(parte):
                    peca[parte] += 1
        cod = str(linha[idx["Cod Material P/ Requisitar"]] or "").strip()
        if cod.isdigit():
            material[cod] += 1
        status = str(linha[idx["Status da Substituição"]] or "").strip().lower()
        if status.startswith("conclu"):
            concluidas += 1
        eq = str(linha[idx["Equipamento"]] or "").strip().lower()
        if eq:
            familia[eq] += 1
    return {
        "registros": total,
        "peca_substituida": peca.most_common(),
        "codigo_material": material.most_common(),
        "substituicoes_concluidas": concluidas,
        "por_familia": familia.most_common(),
    }


# ── Montagem ─────────────────────────────────────────────────────────────────────
def _norm_ss(numero):
    """ETO-COEP 00092/2023 e ETO-COEP 92/2023 são a mesma SS."""
    texto = re.sub(r"\s+", " ", str(numero or "").strip().upper())
    m = re.match(r"^([A-Z\-]+)\s*0*(\d+)/(\d{4})$", texto)
    return f"{m.group(1)} {int(m.group(2))}/{m.group(3)}" if m else texto


def datas_de_ocorrencia():
    """{SS: datetime da ocorrência} — a data em que o equipamento falhou de fato.

    Regra do gestor (21/08): o evento se ancora na OCORRÊNCIA, não na abertura da SS.
    Abertura é o carimbo do registro, que vem depois — mediana de 21 dias e cauda de
    até 734 — e o SGM ainda reescreve a abertura ao reabrir/repassar.
    """
    import openpyxl

    wb = openpyxl.load_workbook(XLSX_ENTRADA, read_only=True)
    ocorrencias = {}
    linhas = list(wb["Dados"].iter_rows(values_only=True))
    cab = [str(c).strip() if c else "" for c in linhas[0]]
    i_oc, i_ss = cab.index("DATA_OCORRENCIA_SS"), cab.index("NUMERO_SS")
    for linha in linhas[1:]:
        if isinstance(linha[i_oc], datetime.datetime):
            ocorrencias[_norm_ss(linha[i_ss])] = linha[i_oc]
    # a aba tratada traz a mesma data em texto e alcança SS que a outra não tem
    tratadas = list(wb["Dados Tratados"].iter_rows(values_only=True))
    cab2 = [str(c).strip() if c else "" for c in tratadas[0]]
    i_oc2, i_ss2 = cab2.index("DataOcorrência"), cab2.index("SS")
    for linha in tratadas[1:]:
        chave = _norm_ss(linha[i_ss2])
        if chave in ocorrencias or not linha[i_oc2]:
            continue
        try:
            ocorrencias[chave] = datetime.datetime.strptime(
                str(linha[i_oc2]).strip(), "%d/%m/%Y %H:%M:%S"
            )
        except ValueError:
            continue
    return ocorrencias


def defasagem_medida():
    """Quanto a abertura atrasa em relação à ocorrência, nas SS que têm as duas datas."""
    import openpyxl

    wb = openpyxl.load_workbook(XLSX_ENTRADA, read_only=True)
    linhas = list(wb["Dados"].iter_rows(values_only=True))
    cab = [str(c).strip() if c else "" for c in linhas[0]]
    i_oc, i_ab = cab.index("DATA_OCORRENCIA_SS"), cab.index("DATA_ABERTURA_SS")
    dias, troca_de_ano, por_ano_oc, por_ano_ab = [], 0, Counter(), Counter()
    for linha in linhas[1:]:
        oc, ab = linha[i_oc], linha[i_ab]
        if not (isinstance(oc, datetime.datetime) and isinstance(ab, datetime.datetime)):
            continue
        dias.append((ab - oc).days)
        por_ano_oc[oc.year] += 1
        por_ano_ab[ab.year] += 1
        if oc.year != ab.year:
            troca_de_ano += 1
    dias.sort()
    if not dias:
        return None
    n = len(dias)
    return {
        "ss_com_as_duas_datas": n,
        "dias": {
            "min": dias[0],
            "p25": dias[n // 4],
            "mediana": dias[n // 2],
            "p75": dias[3 * n // 4],
            "max": dias[-1],
            "media": round(sum(dias) / n, 1),
        },
        "mesmo_dia": sum(1 for d in dias if d == 0),
        "acima_de_180_dias": sum(1 for d in dias if d > 180),
        "trocam_de_ano": troca_de_ano,
        "trocam_de_ano_pct": round(100.0 * troca_de_ano / n, 1),
        "serie_por_ocorrencia": dict(sorted(por_ano_oc.items())),
        "serie_por_abertura": dict(sorted(por_ano_ab.items())),
        "leitura": (
            "A defasagem nunca é negativa: a abertura sempre vem depois. O erro de usar "
            "abertura é portanto SISTEMÁTICO e direcional — empurra falha antiga para o "
            "ano corrente, inflando o ano recente e esvaziando os anteriores. Nesta "
            "amostra a abertura tira 8 eventos de 2024 e 13 de 2025 e joga 21 em 2026."
        ),
    }


def montar():
    with open(ARQ_MIN, encoding="utf-8") as fh:
        base = json.load(fh)

    frota = parque()
    exp = exposicao(frota)

    # Separa a base por ativo. O denominador agora é o parque do gestor, que é o total
    # real — logo o ativo com SS que o cadastro de ajustes não tem NÃO pode ser
    # descartado: ele é parte do parque, só não tem estudo cadastrado. Entra com a
    # família lida na descrição da SS e sem modelo, marcado como fora do cadastro.
    bruto = defaultdict(list)
    for ss in base:
        cod = str(ss.get("NUM_TRAFO") or "").strip()
        if cod.isdigit():
            bruto[cod].append(ss)

    por_ativo, fora_do_cadastro, sem_familia = {}, set(), set()
    for cod, linhas in bruto.items():
        if cod in frota:
            por_ativo[cod] = linhas
            continue
        familia = familia_pela_ss(linhas)
        if familia is None:
            sem_familia.add(cod)  # nem cadastro nem descrição dizem o que é
            continue
        frota[cod] = {"familia": familia, "marca": "SEM CADASTRO"}
        fora_do_cadastro.add(cod)
        por_ativo[cod] = linhas

    triagem = Counter(classificar(ss) for ss in base)
    ocorrencias = datas_de_ocorrencia()

    eventos = []  # um por demanda de falha
    for cod, linhas in por_ativo.items():
        for dem in demandas.encadear(linhas):
            classes = [classificar(s) for s in dem["ss"]]
            if "falha" not in classes:
                continue
            # Âncora do evento: a OCORRÊNCIA mais antiga entre as SS da demanda. A
            # abertura só entra quando nenhuma SS da cadeia declara ocorrência — e
            # nesse caso o evento fica marcado, para o número dizer em que pé está.
            ocorreu = min(
                (ocorrencias[_norm_ss(s.get("NUMERO_SS"))] for s in dem["ss"]
                 if _norm_ss(s.get("NUMERO_SS")) in ocorrencias),
                default=None,
            )
            abertura = min(
                (demandas._dt(s.get("DATA_ABERTURA_SS", "")) for s in dem["ss"] if s.get("DATA_ABERTURA_SS")),
                default=None,
            )
            marco = ocorreu or abertura
            if marco is None:
                continue
            eventos.append(
                {
                    "ativo": cod,
                    "familia": frota[cod]["familia"],
                    "marca": frota[cod]["marca"],
                    "ano": marco.year,
                    "data": marco.date().isoformat(),
                    "ancora": "ocorrencia" if ocorreu else "abertura",
                    "atraso_do_registro": (abertura - ocorreu).days if (ocorreu and abertura) else None,
                    "severidade": severidade(dem["ss"]),
                    "ss": len(dem["ss"]),
                    "origem": sorted({(s.get("ORIGEM_SS") or "").strip().upper() for s in dem["ss"] if s.get("ORIGEM_SS")}),
                }
            )

    def taxa(filtro, expostos, anos):
        n = sum(1 for e in eventos if filtro(e))
        if not expostos or not anos:
            return {"eventos": n, "taxa_100": None}
        return {
            "eventos": n,
            "equipamento_ano": round(expostos * anos, 1),
            "taxa_100": round(100.0 * n / (expostos * anos), 1),
            "mtbf_anos": round((expostos * anos) / n, 1) if n else None,
        }

    cheios = {}
    for fam, expostos in exp["familia"].items():
        cheios[fam] = {
            "geral": taxa(lambda e, f=fam: e["familia"] == f and e["ano"] in ANOS_CHEIOS, expostos, exp["anos_cheios"]),
            "funcional": taxa(
                lambda e, f=fam: e["familia"] == f and e["ano"] in ANOS_CHEIOS and e["severidade"] == "funcional",
                expostos,
                exp["anos_cheios"],
            ),
            "anomalia": taxa(
                lambda e, f=fam: e["familia"] == f and e["ano"] in ANOS_CHEIOS and e["severidade"] == "anomalia",
                expostos,
                exp["anos_cheios"],
            ),
            "parque": expostos,
        }

    parcial = {
        fam: taxa(
            lambda e, f=fam: e["familia"] == f and e["ano"] == ANO_PARCIAL,
            expostos,
            exp["fracao_parcial"],
        )
        for fam, expostos in exp["familia"].items()
    }

    por_marca = {}
    for chave, expostos in exp["marca"].items():
        fam, marca = chave.split("|", 1)
        if expostos < 20:  # amostra pequena não vira taxa publicável
            continue
        por_marca[chave] = taxa(
            lambda e, f=fam, m=marca: e["familia"] == f and e["marca"] == m and e["ano"] in ANOS_CHEIOS,
            expostos,
            exp["anos_cheios"],
        ) | {"parque": expostos}

    # ── Série ano a ano ──────────────────────────────────────────────────────────
    # 2024 e 2025 são anos cheios (fator 1,0); 2026 vale a fração decorrida até a foto,
    # senão a taxa de um ano pela metade sairia pela metade e pareceria queda.
    aic_ano = (trocas_no_aic() or {}).get("por_ano_de_conclusao_fisica", {})
    serie = {}
    for ano in list(ANOS_CHEIOS) + [ANO_PARCIAL]:
        fator = exp["fracao_parcial"] if ano == ANO_PARCIAL else 1.0
        do_ano = [e for e in eventos if e["ano"] == ano]
        bloco = {}
        for fam, expostos in exp["familia"].items():
            eq_ano = expostos * fator
            desta = [e for e in do_ano if e["familia"] == fam]
            ativos = {e["ativo"] for e in desta}
            trocas = aic_ano.get(str(ano), {}).get(fam, 0)
            bloco[fam] = {
                "parque": expostos,
                "equipamento_ano": round(eq_ano, 1),
                "eventos": len(desta),
                "taxa_100": round(100.0 * len(desta) / eq_ano, 1) if eq_ano else None,
                "funcional_100": round(
                    100.0 * sum(1 for e in desta if e["severidade"] == "funcional") / eq_ano, 1
                ) if eq_ano else None,
                "anomalia_100": round(
                    100.0 * sum(1 for e in desta if e["severidade"] == "anomalia") / eq_ano, 1
                ) if eq_ano else None,
                "mtbf_anos": round(eq_ano / len(desta), 1) if desta else None,
                "ativos_distintos": len(ativos),
                "incidencia_pct": round(100.0 * len(ativos) / expostos, 1) if expostos else None,
                "trocas_confirmadas": trocas,
                "taxa_substituicao_100": round(100.0 * trocas / eq_ano, 1) if eq_ano else None,
                "chamadas_por_troca": round(len(desta) / trocas, 1) if trocas else None,
            }
        modo = Counter()
        for e in do_ano:
            for o in e["origem"]:
                modo[o] += 1
        bloco["_modo_declarado"] = {
            "eventos_com_origem": sum(1 for e in do_ano if e["origem"]),
            "cobertura_pct": round(100.0 * sum(1 for e in do_ano if e["origem"]) / len(do_ano), 1)
            if do_ano else None,
            "top": modo.most_common(8),
        }
        bloco["_ancora"] = {
            "por_ocorrencia": sum(1 for e in do_ano if e["ancora"] == "ocorrencia"),
            "por_abertura": sum(1 for e in do_ano if e["ancora"] == "abertura"),
            "cobertura_pct": round(
                100.0 * sum(1 for e in do_ano if e["ancora"] == "ocorrencia") / len(do_ano), 1
            ) if do_ano else None,
        }
        bloco["_fator_de_exposicao"] = fator
        serie[str(ano)] = bloco

    # reincidência: ativo com mais de um evento dentro da janela cheia
    por_ativo_evt = Counter(e["ativo"] for e in eventos if e["ano"] in ANOS_CHEIOS)
    reincidentes = {a: n for a, n in por_ativo_evt.items() if n > 1}

    # Incidência ≠ frequência. Frequência é evento/eq-ano (média do parque); incidência
    # é quantos equipamentos DISTINTOS falharam ao menos uma vez. O parque não falha
    # parelho: a cauda de reincidentes carrega a média e é ela que se ataca primeiro.
    incidencia = {}
    for fam, expostos in exp["familia"].items():
        ativos = [a for a, n in por_ativo_evt.items() if frota[a]["familia"] == fam]
        dist = Counter(por_ativo_evt[a] for a in ativos)
        cauda = [a for a in ativos if por_ativo_evt[a] >= 3]
        incidencia[fam] = {
            "parque": expostos,
            "ativos_com_ao_menos_um_evento": len(ativos),
            "incidencia_pct_em_2_anos": round(100.0 * len(ativos) / expostos, 1) if expostos else None,
            "distribuicao_eventos_por_ativo": dict(sorted(dist.items())),
            "ativos_com_3_ou_mais": len(cauda),
            "eventos_vindos_da_cauda": sum(por_ativo_evt[a] for a in cauda),
            "pct_dos_eventos_na_cauda": round(
                100.0 * sum(por_ativo_evt[a] for a in cauda) / sum(por_ativo_evt[a] for a in ativos), 1
            ) if ativos else None,
        }

    # modo de falha declarado (camada 3)
    declarados = Counter()
    sem_declaracao = 0
    for e in eventos:
        if e["origem"]:
            for o in e["origem"]:
                declarados[o] += 1
        else:
            sem_declaracao += 1

    pacote = {
        "premissas": PREMISSAS,
        "janela": {"cheios": list(ANOS_CHEIOS), "parcial": ANO_PARCIAL, "corte": FIM_DO_PARCIAL.isoformat()},
        "triagem_ss": dict(triagem),
        "parque": {
            "religador": PARQUE["religador"],
            "regulador": PARQUE["regulador"],
            "fonte": "informado pelo gestor em 21/08/2026",
            "no_cadastro_de_ajustes": exp["no_cadastro_de_ajustes"],
            "sem_estudo_de_ajuste_cadastrado": exp["sem_estudo_cadastrado"],
            "ativos_com_ss_fora_do_cadastro": len(fora_do_cadastro),
            "ativos_sem_familia_identificavel": len(sem_familia),
        },
        "eventos": len(eventos),
        "eventos_na_janela_cheia": sum(1 for e in eventos if e["ano"] in ANOS_CHEIOS),
        "taxa_anos_cheios": cheios,
        "taxa_2026_anualizada": parcial,
        "taxa_por_marca": por_marca,
        "reincidencia": {
            "ativos_com_mais_de_um_evento": len(reincidentes),
            "eventos_desses_ativos": sum(reincidentes.values()),
            "pior": sorted(reincidentes.items(), key=lambda kv: -kv[1])[:8],
        },
        "modo_de_falha_declarado": {
            "eventos_com_origem": sum(1 for e in eventos if e["origem"]),
            "eventos_sem_origem": sem_declaracao,
            "cobertura_pct": round(100.0 * sum(1 for e in eventos if e["origem"]) / len(eventos), 1) if eventos else None,
            "top": declarados.most_common(15),
        },
        "ancoragem": {
            "por_ocorrencia": sum(1 for e in eventos if e["ancora"] == "ocorrencia"),
            "por_abertura": sum(1 for e in eventos if e["ancora"] == "abertura"),
            "cobertura_pct": round(
                100.0 * sum(1 for e in eventos if e["ancora"] == "ocorrencia") / len(eventos), 1
            ) if eventos else None,
        },
        "defasagem_ocorrencia_abertura": defasagem_medida(),
        "impacto_da_ancora": {
            "eventos_conferiveis": sum(1 for e in eventos if e["atraso_do_registro"] is not None),
            "mudaram_de_ano": sum(
                1 for e in eventos
                if e["atraso_do_registro"] is not None
                and datetime.date.fromisoformat(e["data"]).year
                != (datetime.date.fromisoformat(e["data"])
                    + datetime.timedelta(days=e["atraso_do_registro"])).year
            ),
            "atraso_mediano_dias": sorted(
                e["atraso_do_registro"] for e in eventos if e["atraso_do_registro"] is not None
            )[sum(1 for e in eventos if e["atraso_do_registro"] is not None) // 2]
            if any(e["atraso_do_registro"] is not None for e in eventos) else None,
            "leitura": (
                "Nos eventos em que dá para conferir as duas datas, mais de um terço "
                "estava no ano errado pela abertura. A série por abertura não serve para "
                "ler tendência; serve só para medir o próprio atraso de registro."
            ),
        },
        "serie_por_ano": serie,
        "incidencia": incidencia,
        "substituicao": substituicoes(),
        "trocas_no_aic": trocas_no_aic(),
    }

    # O contraste que dá sentido à métrica: quantas chamadas atribuídas ao equipamento
    # para cada troca efetivamente executada. Religador resolve muito em campo;
    # regulador converte chamada em peça com muito mais frequência — e peça de
    # regulador 34,5 kV custa R$ 57 mil a R$ 127 mil.
    aic = pacote["trocas_no_aic"]
    if aic:
        conversao = {}
        for fam, expostos in exp["familia"].items():
            trocas = sum(
                aic["por_ano_de_conclusao_fisica"].get(str(a), {}).get(fam, 0) for a in ANOS_CHEIOS
            )
            eventos_fam = cheios[fam]["geral"]["eventos"]
            eq_ano = expostos * exp["anos_cheios"]
            conversao[fam] = {
                "chamadas_atribuidas_ao_equipamento": eventos_fam,
                "trocas_confirmadas": trocas,
                "taxa_chamada_100": cheios[fam]["geral"]["taxa_100"],
                "taxa_substituicao_100": round(100.0 * trocas / eq_ano, 1) if eq_ano else None,
                "chamadas_por_troca": round(eventos_fam / trocas, 1) if trocas else None,
            }
        pacote["conversao_chamada_troca"] = conversao
    return pacote


if __name__ == "__main__":
    p = montar()
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(p, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in p.items() if k != "premissas"}, ensure_ascii=False, indent=1))
