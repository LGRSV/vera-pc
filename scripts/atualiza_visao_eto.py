"""
Atualiza a visão ETO de ponta a ponta a partir da base de SS/OS.

O caminho feliz: largar a base nova (BASE_SS_OS_ddmmaaaa.txt, texto com «@»,
latin-1) em data/raw e rodar

    python3 scripts/atualiza_visao_eto.py

Sem argumento, usa a BASE_SS_OS*.txt mais nova de data/raw (pela data do nome);
com argumento, usa o arquivo apontado. Daí a corrente roda sozinha:

  1. extrai o recorte RL/RT da base crua  → data/missao/ssos_min.json
  2. refaz a visão ETO pela régua do gestor → data/missao/visao_consolidada.json
  3. regrava a planilha                     → dist/VISAO_ETO.xlsx
  4. reconstrói o painel                    → dist/equipamentos-especiais.html

No fim, imprime o horizonte real do dado (maior data de abertura — o nome do
arquivo não diz isso) e a distribuição dos baldes. Falta só republicar o
artifact do painel, que é ação de quem roda.

O que esta corrente NÃO refaz: a conta do posto (136 − 82), os concluídos do
DCMD e a taxa de falha — essas saem da análise completa da cadeia
(scripts/coep_2026.py e scripts/taxa_falha.py) e seguem com os números da
última rodada até alguém rodá-las de novo.
"""

import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))


def rodar():
    import json

    import cadeia_obra as co
    import extrai_ssos_min as em
    import planilha_visao_eto
    import visao_consolidada

    caminhos = sys.argv[1:] or co.PARTES
    for c in caminhos:
        if not os.path.exists(c):
            raise SystemExit(f"base não encontrada: {c} — largar a BASE_SS_OS_*.txt "
                             f"em data/raw ou passar o caminho como argumento")
    print(f"base: {', '.join(caminhos)}")

    # 1. o recorte RL/RT
    registros = em.extrair(caminhos)
    datas = sorted(f"{d[6:10]}-{d[3:5]}-{d[:2]}" for r in registros
                   for d in [r["DATA_ABERTURA_SS"]] if len(d) >= 10)
    print(f"1. recorte RL/RT: {len(registros)} SS · aberturas até {datas[-1]} "
          f"(o nome do arquivo não vale como horizonte)")
    with open(em.SAIDA, "w", encoding="utf-8") as fh:
        json.dump(registros, fh, ensure_ascii=False)

    # 2. a visão pela régua do gestor
    pacote = visao_consolidada.montar()
    v = pacote["visao_eto"]
    print(f"2. visão ETO: {v['total']} ativos ({v['fora_da_carteira']} fora da carteira)")
    for b, d in v["baldes"].items():
        print(f"   {b:<20} {d['qtd']}")

    # 3. a planilha, com a descrição das SS
    planilha_visao_eto.montar()

    # 4. o painel
    for script in ("build_data.py", "build_single_file.py"):
        print(f"4. {script}…")
        subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", script)],
                       check=True, stdout=subprocess.DEVNULL)
    print("pronto — falta republicar o artifact do painel "
          "(dist/equipamentos-especiais.html).")


if __name__ == "__main__":
    rodar()
