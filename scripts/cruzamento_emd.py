"""
Cruzamento entre a planilha de EMD (OBRAS_EQ_ESPECIAL) e a planilha de criticidade.

A chave de ligação é o CÓDIGO DO ATIVO. Os números de SS das duas planilhas
pertencem a universos diferentes — o EMD registra a SS de requisição do COEP
(ETO-COEP …) e a planilha de criticidade registra a SS de campo/manutenção
(ETO-RD-…, ETO-PROT-…, ETO-TELE-…) — então casar por SS produz falso negativo.
Por isso o casamento é por ativo, e a diferença de SS vira um achado.
"""

import csv
import datetime
import os
import re
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_EMD = os.path.join(RAIZ, "data", "raw", "obras_eq_especial.csv")

DATA_REF = datetime.date(2026, 8, 12)

ORDEM_CRITICIDADE = ["Muito Alta", "Alta", "Média", "Baixa", "Sem classificação"]

# Gravidade de cada tipo de divergência, usada para ordenar a lista no site.
GRAVIDADE = {
    "Em aquisição, ainda sem EMD": "Baixa",
    "SS atribuída a outro ativo": "Crítica",
    "Ativo divergente dentro do EMD": "Crítica",
    "Substituição feita, SS aberta": "Alta",
    "SS concluída, EMD pendente": "Alta",
    "Número de SS divergente": "Alta",
    "Defeito divergente": "Média",
    "Criticidade divergente": "Média",
    "Localidade ou polo divergente": "Média",
    "Entrega atrasada": "Média",
    "Cadastro incompleto no EMD": "Baixa",
    "Incoerência interna do EMD": "Baixa",
}


def normalizar(texto):
    """Maiúsculas, sem acento e sem pontuação — para comparar textos digitados à mão."""
    texto = unicodedata.normalize("NFD", (texto or "").upper())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9]", "", texto)


def normalizar_ss(ss):
    """`SS ETO-RD-PO 00208/2026` e `ETO-RD-PO 208/2026` são a mesma SS."""
    if not ss:
        return ""
    limpo = ss.upper().replace("SS ", "").replace(" - ", "-").strip()
    achado = re.search(r"([A-Z]+-[A-Z]+(?:-[A-Z]+)?)\s*0*(\d+)/(\d{4})", limpo)
    return f"{achado.group(1)}-{int(achado.group(2))}/{achado.group(3)}" if achado else limpo


def data_iso(valor):
    return valor if re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor or "") else None


def ler_emd():
    with open(CSV_EMD, encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh, delimiter=";"))
    registros = []
    for indice, linha in enumerate(linhas):
        registro = {k: (v or "").strip() for k, v in linha.items()}
        if not registro.get("Ativo"):
            continue
        registro["linha_emd"] = indice + 3  # cabeçalho duplo na planilha original
        registros.append(registro)
    return registros


def cruzar(registros_criticidade, registros_emd):
    """Devolve (lista de divergências, índice do EMD por ativo)."""
    por_ativo = {r["ativo"]: r for r in registros_criticidade}
    emd_por_ativo = {e["Ativo"]: e for e in registros_emd}

    # SS de campo -> ativo, para detectar a mesma SS apontando para ativos diferentes.
    ss_para_ativo = {
        normalizar_ss(r["ss"]): r["ativo"]
        for r in registros_criticidade
        if r["ss"] and "CONCLU" not in r["ss"].upper()
    }

    divergencias = []

    def registrar(ativo, tipo, campo, valor_emd, valor_crit, detalhe, extra=None):
        base = por_ativo.get(ativo, {})
        divergencias.append({
            "ativo": ativo,
            "localidade": base.get("localidade", ""),
            "polo": base.get("polo", ""),
            "regional": base.get("regional", ""),
            "criticidade": base.get("criticidade", "Sem classificação"),
            "tipo": tipo,
            "gravidade": GRAVIDADE[tipo],
            "campo": campo,
            "valor_emd": valor_emd,
            "valor_criticidade": valor_crit,
            "detalhe": detalhe,
            **(extra or {}),
        })

    for emd in registros_emd:
        ativo = emd["Ativo"]
        crit = por_ativo.get(ativo)
        if not crit:
            continue  # cobertura tratada no bloco seguinte

        concluida_crit = "CONCLU" in crit["ss"].upper()
        ss_emd = normalizar_ss(emd.get("SS aberta", ""))
        ss_crit = normalizar_ss(crit["ss"])
        os_assoc = normalizar_ss(emd.get("OS Associada", ""))
        posto = normalizar_ss(emd.get("Posto COEP", ""))

        # 1. número de SS divergente entre as duas planilhas
        if not concluida_crit and ss_emd and ss_emd != ss_crit:
            if os_assoc == ss_crit or posto == ss_crit:
                onde = "OS Associada" if os_assoc == ss_crit else "Posto COEP"
                detalhe = (
                    f"A SS principal do EMD ({emd['SS aberta']}) não é a mesma da planilha "
                    f"de criticidade ({crit['ss']}); o vínculo só aparece no campo {onde}."
                )
            else:
                detalhe = (
                    f"O EMD registra {emd['SS aberta']} e a planilha de criticidade registra "
                    f"{crit['ss']}. Nenhum campo do EMD (OS Associada, Posto COEP) referencia "
                    f"a SS de campo — não há chave comum entre as duas planilhas além do ativo."
                )
            registrar(ativo, "Número de SS divergente", "SS aberta",
                      emd.get("SS aberta", "—"), crit["ss"], detalhe)

        # 2. SS do EMD que na planilha de criticidade pertence a outro ativo
        for campo in ("SS aberta", "OS Associada", "Posto COEP"):
            valor = normalizar_ss(emd.get(campo, ""))
            dono = ss_para_ativo.get(valor)
            if valor and dono and dono != ativo:
                registrar(ativo, "SS atribuída a outro ativo", campo,
                          emd.get(campo), f"pertence ao ativo {dono}",
                          f"A SS {emd.get(campo)} aparece no EMD do ativo {ativo}, mas na "
                          f"planilha de criticidade essa mesma SS está registrada no ativo "
                          f"{dono} ({por_ativo[dono]['localidade']}). Uma das duas está errada.")

        # 3. status de substituição x situação da SS de campo
        status_sub = normalizar(emd.get("Status da Substituição", ""))
        if status_sub == "CONCLUIDA" and not concluida_crit:
            registrar(ativo, "Substituição feita, SS aberta", "Status da Substituição",
                      f"Concluída em {emd.get('Data da Substituição') or 'data não informada'}",
                      f"{crit['ss']} · check {crit['check'] or '—'}",
                      f"O EMD dá a substituição como concluída, mas a SS {crit['ss']} continua "
                      f"aberta com Parecer COEP «{crit['parecer_coep'] or '—'}». Se a troca "
                      f"ocorreu mesmo, a SS de campo está pendente só de baixa.")

        if concluida_crit and status_sub in ("PENDENTE", "NA", ""):
            registrar(ativo, "SS concluída, EMD pendente", "Status da Substituição",
                      emd.get("Status da Substituição") or "(vazio)", "SS CONCLUÍDA",
                      f"A planilha de criticidade dá a SS como concluída, mas o EMD mantém a "
                      f"substituição como «{emd.get('Status da Substituição') or 'vazio'}» e a "
                      f"entrega como «{emd.get('Status Entrega') or '—'}»."
                      + (f" Observação do EMD: {emd['Observação']}" if emd.get("Observação") else ""))

        # 4. defeito identificado
        defeito_emd, defeito_crit = emd.get("Defeito identificado", ""), crit["defeito_planilha"]
        if defeito_emd and normalizar(defeito_emd)[:7] != normalizar(defeito_crit)[:7]:
            registrar(ativo, "Defeito divergente", "Defeito identificado",
                      defeito_emd, defeito_crit or "(vazio)",
                      f"O material a requisitar é definido pelo defeito. O EMD descreve "
                      f"«{defeito_emd}» e a planilha de criticidade «{defeito_crit or 'nada'}».")

        # 5. criticidade
        crit_emd = emd.get("Criticidade", "")
        if crit_emd and normalizar(crit_emd) != normalizar(crit["criticidade"]):
            registrar(ativo, "Criticidade divergente", "Criticidade", crit_emd,
                      crit["criticidade"],
                      f"O EMD classifica como «{crit_emd}» e a planilha de criticidade como "
                      f"«{crit['criticidade']}» — a fila de prioridade muda conforme a planilha usada.")
        elif not crit_emd:
            registrar(ativo, "Cadastro incompleto no EMD", "Criticidade", "(vazio)",
                      crit["criticidade"],
                      f"O EMD não tem criticidade preenchida; na planilha de criticidade o "
                      f"equipamento é «{crit['criticidade']}».")

        # 6. localidade e polo
        if (normalizar(emd.get("Localidade")) != normalizar(crit["localidade"])
                or normalizar(emd.get("POLO")) != normalizar(crit["polo"])):
            registrar(ativo, "Localidade ou polo divergente", "Localidade / POLO",
                      f"{emd.get('Localidade') or '—'} / {emd.get('POLO') or '—'}",
                      f"{crit['localidade'] or '—'} / {crit['polo'] or '—'}",
                      "Localidade ou polo diferentes entre as planilhas — afeta o depósito de "
                      "destino e a equipe acionada.")

        # 7. entrega atrasada
        previsto, entregue = data_iso(emd.get("Previsão de entrega")), data_iso(emd.get("Data Entrega"))
        if previsto and entregue:
            atraso = (datetime.date.fromisoformat(entregue) - datetime.date.fromisoformat(previsto)).days
            if atraso > 0:
                registrar(ativo, "Entrega atrasada", "Previsão x Data de entrega",
                          f"previsto {previsto}, entregue {entregue}", "—",
                          f"Material entregue {atraso} dias depois do previsto.",
                          {"dias_atraso": atraso})

        # 8. campos de controle do EMD em branco ou inválidos
        faltas = []
        if not emd.get("SS aberta"):
            faltas.append("sem SS")
        if not emd.get("EMD"):
            faltas.append("sem número de EMD")
        if not emd.get("OBRA"):
            faltas.append("sem obra")
        if emd.get("MODELO") == "#N/A":
            faltas.append("modelo #N/A")
        if emd.get("Data Entrega") and not data_iso(emd.get("Data Entrega")):
            faltas.append(f"data de entrega malformada ({emd['Data Entrega']})")
        if faltas:
            registrar(ativo, "Cadastro incompleto no EMD", "Campos de controle",
                      ", ".join(faltas), "—",
                      f"A linha do EMD está com {', '.join(faltas)} — sem isso a requisição "
                      f"não é rastreável até a entrega.")

        # 9. incoerência dentro da própria linha do EMD
        if status_sub == "CONCLUIDA" and normalizar(emd.get("Equipamento Entregue ?")) == "NAO":
            registrar(ativo, "Incoerência interna do EMD", "Substituição x Entrega",
                      "substituição concluída, equipamento não entregue", "—",
                      "A linha do EMD marca a substituição como concluída e, ao mesmo tempo, "
                      "o equipamento como não entregue.")

        if "/2024" in emd.get("SS aberta", ""):
            registrar(ativo, "Incoerência interna do EMD", "SS aberta",
                      emd["SS aberta"], crit["ss"],
                      f"A SS do EMD é de 2024 — mais de um exercício em aberto.")

        # A planilha de EMD tem duas colunas "Ativo". Quando elas discordam,
        # não dá para saber a qual equipamento a requisição pertence.
        ativo_2 = emd.get("Ativo (2)", "")
        if ativo_2 and ativo_2 != ativo:
            registrar(ativo, "Ativo divergente dentro do EMD", "Ativo (colunas C e K)",
                      f"coluna C = {ativo} · coluna K = {ativo_2}",
                      f"{crit['localidade']} ({crit['criticidade']})",
                      f"A linha do EMD traz dois códigos de ativo diferentes: {ativo} e "
                      f"{ativo_2}. Os dois existem na planilha de criticidade e ficam na "
                      f"mesma localidade, então a requisição pode estar atrelada ao "
                      f"equipamento errado. O campo Posto COEP «{emd.get('Posto COEP') or '—'}» "
                      f"é o desempate.")

    # 10. declarado em aquisição e ainda sem linha no EMD.
    # Premissa do usuário (12/08): "Em processo de aquisição" NÃO implica EMD emitida —
    # a EMD só nasce quando a compra vira requisição de material. Portanto isso não é
    # divergência crítica; é acompanhamento do funil de compra.
    for crit in registros_criticidade:
        em_aquisicao = "aquisi" in crit["parecer_coep"].lower()
        if em_aquisicao and crit["ativo"] not in emd_por_ativo:
            registrar(crit["ativo"], "Em aquisição, ainda sem EMD", "Parecer COEP",
                      "sem linha na planilha de EMD", crit["parecer_coep"],
                      f"O Parecer COEP diz «{crit['parecer_coep']}» e o ativo ainda não tem "
                      f"linha de EMD. Pela regra do fluxo isso é esperado durante a compra — "
                      f"a EMD nasce quando o material vira requisição. Vale acompanhar a "
                      f"conversão, não tratar como erro.")

    divergencias.sort(key=lambda d: (
        ["Crítica", "Alta", "Média", "Baixa"].index(d["gravidade"]),
        ORDEM_CRITICIDADE.index(d["criticidade"] if d["criticidade"] in ORDEM_CRITICIDADE else "Sem classificação"),
        d["ativo"],
    ))
    return divergencias, emd_por_ativo
