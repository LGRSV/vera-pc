"""
Consolida a leitura das SS e OS pelos agentes — data/missao/leitura_ss_os.json.

Entrada: os três blocos crus em data/analise_ia/leitura_ss_os/shard{1,2,3}.json —
cada um com as falhas apontadas pelos leitores e o veredito dos revisores
adversariais. Só entra o que sobreviveu à revisão.

A conta segue a fórmula do gestor (21/08):

    RL que falharam (controle, tanque ou completo) ÷ parque do ano
    RT que falharam (célula, relé, completo ou furto) ÷ parque do ano

O numerador é EQUIPAMENTO que falhou no ano, não ocorrência: ativo que falhou
duas vezes no mesmo ano conta uma vez naquele ano (e conta de novo se falhar em
outro ano). As ocorrências são publicadas ao lado, como detalhe.

Para o rol de ocorrências há uma consolidação mínima, em código: dentro do mesmo
ativo, ano e peça, entradas cujo motivo de revisão é idêntico e NÃO afirma serem
eventos distintos («segundo», «distinto», «segunda falha») colapsam numa só —
é o caso do episódio de controle de jun–jul/2026 do 5848305116, que o revisor
descreveu como um episódio único mas manteve nas duas SS. Dois furtos com B.O.
distintos, ou duas células em meses diferentes, seguem como dois eventos.

Rodar: python3 scripts/consolida_leitura.py
"""

import json
import os
import re
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_SHARDS = os.path.join(RAIZ, "data", "analise_ia", "leitura_ss_os")
SAIDA = os.path.join(RAIZ, "data", "missao", "leitura_ss_os.json")

RE_DISTINTO = re.compile(r"segundo|distint|segunda falha|nao e repasse|não é repasse", re.I)
ARQ_AIC = os.path.join(RAIZ, "data", "missao", "aic_rlrt.json")
RE_OBRA_SUBST = re.compile(
    r"SUBSTITUI[ÇC][ÃA]O\s+D[EO]\s*(?:\d+\s+)?(?:CH\.?\s+)?(?:ATIVO\s+D[EO]\s+)?"
    r"(RELIGADOR|REGULADOR)", re.I)
RE_COD_ATIVO = re.compile(r"\b(\d{10})\b")


def complemento_aic(equipamentos):
    """Trocas por obra direta, fora da carteira lida — {familia|ano: n}.

    Premissa: o ano é o da conclusão física da obra (a troca direta costuma sair na
    semana da falha). Obra cujo texto cita um ativo já contado pela leitura — no
    mesmo ano ou em outro — é descontada: a leitura, que data pela ocorrência,
    manda sobre o cronograma da obra.
    """
    with open(ARQ_AIC, encoding="utf-8") as fh:
        obras = json.load(fh)
    lidos = set()
    for v in equipamentos.values():
        lidos |= set(v)
    comp, desc = Counter(), Counter()
    for obra in obras:
        texto = obra.get("DESCRICAO_OBRA") or ""
        m = RE_OBRA_SUBST.search(texto)
        if not m:
            continue
        familia = "religador" if m.group(1).upper().startswith("RELIG") else "regulador"
        ano = (obra.get("DATA_CONCLUSAO_FISICA") or "")[:4]
        if ano not in ("2024", "2025", "2026"):
            continue
        chave = f"{familia}|{ano}"
        if set(RE_COD_ATIVO.findall(texto)) & lidos:
            desc[chave] += 1
        else:
            comp[chave] += 1
    return dict(comp), dict(desc)


def carregar():
    blocos = []
    for nome in sorted(os.listdir(DIR_SHARDS)):
        if nome.startswith("shard") and nome.endswith(".json"):
            with open(os.path.join(DIR_SHARDS, nome), encoding="utf-8") as fh:
                blocos.append(json.load(fh))
    return blocos


def consolidar_ocorrencias(falhas):
    """Colapsa o mesmo episódio relatado em duas SS; preserva eventos distintos."""
    grupos = defaultdict(list)
    for f in falhas:
        grupos[(f["ativo"], f["ano"], f["peca"])].append(f)
    saida, colapsadas = [], []
    for chave, grupo in grupos.items():
        if len(grupo) == 1:
            saida.extend(grupo)
            continue
        motivos = {(g.get("revisao_motivo") or "").strip() for g in grupo}
        mesmo_episodio = len(motivos) == 1 and not RE_DISTINTO.search(next(iter(motivos)))
        if mesmo_episodio:
            # fica a entrada com melhor âncora de data (ocorrência > parecer > os > abertura)
            ordem = {"ocorrencia": 0, "parecer": 1, "os": 2, "abertura": 3}
            grupo.sort(key=lambda g: ordem.get(g.get("base_da_data"), 9))
            eleito = dict(grupo[0])
            eleito["ss_do_episodio"] = [g["ss"] for g in grupo]
            saida.append(eleito)
            colapsadas.append({"ativo": chave[0], "ano": chave[1], "peca": chave[2],
                               "ss": [g["ss"] for g in grupo]})
        else:
            saida.extend(grupo)
    return saida, colapsadas


def main():
    blocos = carregar()
    falhas, descartes, resumos = [], [], []
    for b in blocos:
        falhas.extend(f for f in b.get("detalhe", []) if f.get("precisa_troca") is not False)
        descartes.extend(b.get("descartes", []))
        resumos.extend(b.get("resumos", []))
    # o leitor às vezes devolve o apontamento negativo confirmado (precisa_troca=false
    # mantido pela revisão) — está em detalhe mas não é falha; o filtro acima já tira.

    ocorrencias, colapsadas = consolidar_ocorrencias(falhas)

    # A fórmula do gestor: equipamentos distintos que falharam, por família e ano
    equipamentos = defaultdict(set)
    contagem_oc = Counter()
    por_peca = Counter()
    for f in ocorrencias:
        chave = f"{f['familia']}|{f['ano']}"
        equipamentos[chave].add(f["ativo"])
        contagem_oc[chave] += 1
        por_peca[f"{f['familia']}|{f['ano']}|{f['peca']}"] += 1

    # A leitura cobre a carteira do COEP. Equipamento que falhou e foi trocado por
    # obra direta, sem nunca entrar na carteira, também falhou — entra pelo AIC
    # (obra de substituição do próprio equipamento, concluída fisicamente no ano),
    # descontando a obra cujo texto cita ativo já contado pela leitura.
    complemento, descontadas = complemento_aic(equipamentos)

    total = {}
    for fam in ("religador", "regulador"):
        for ano in (2024, 2025, 2026):
            k = f"{fam}|{ano}"
            total[k] = len(equipamentos.get(k, set())) + complemento.get(k, 0)

    pacote = {
        "fonte": "leitura integral das SS e OS dos 129 ativos da carteira por agentes, "
                 "com revisão adversarial de cada falha apontada",
        "formula": "equipamentos que falharam no ano ÷ parque do ano — ativo que falhou "
                   "duas vezes no mesmo ano conta uma vez; as ocorrências vão ao lado",
        "ativos_lidos": sum(b.get("ativos_lidos", 0) for b in blocos),
        "falhas_apontadas": sum(b.get("falhas_apontadas", 0) for b in blocos),
        "confirmadas_pela_revisao": sum(b.get("confirmadas", 0) for b in blocos),
        "derrubadas_pela_revisao": sum(b.get("derrubadas", 0) for b in blocos),
        "episodios_colapsados": colapsadas,
        "contagem": {k: len(v) for k, v in equipamentos.items()},
        "complemento_obra_direta": complemento,
        "obras_descontadas_por_sobreposicao": descontadas,
        "total_equipamentos_que_falharam": total,
        "ocorrencias": dict(contagem_oc),
        "por_peca": dict(por_peca),
        "equipamentos": {k: sorted(v) for k, v in equipamentos.items()},
        "detalhe": ocorrencias,
        "descartes": descartes,
        "resumos": resumos,
    }
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, indent=1)

    print(f"gravado: {SAIDA}")
    print(f"  lidos {pacote['ativos_lidos']} ativos | apontadas {pacote['falhas_apontadas']} "
          f"| confirmadas {pacote['confirmadas_pela_revisao']} "
          f"| derrubadas {pacote['derrubadas_pela_revisao']} "
          f"| episódios colapsados {len(colapsadas)}")
    for fam in ("religador", "regulador"):
        linha = "  " + fam + ":"
        for ano in (2024, 2025, 2026):
            k = f"{fam}|{ano}"
            linha += (f"  {ano}: {pacote['contagem'].get(k, 0)}+{complemento.get(k, 0)}"
                      f"={total.get(k, 0)}")
        print(linha)


if __name__ == "__main__":
    main()
