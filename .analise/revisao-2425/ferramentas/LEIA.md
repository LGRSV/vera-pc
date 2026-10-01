Retomar a revisão 2024-25 (etapa `revisao`):

    S=.claude/skills/checkpoint/scripts/ckpt.py
    python3 $S todo .analise/revisao-2425 revisao            # o que falta
    python3 .analise/revisao-2425/ferramentas/next.py 40    # próximo pacote (40 KB) da fila ordem_A.json → pk.txt no mesmo diretório
    # ler pk.txt, escrever um JSON com a lista de vereditos por ativo (formato dos demandas[] em revisao.json)
    python3 .analise/revisao-2425/ferramentas/grava.py vereditos.json   # valida rótulo/cadeias e faz um put por ativo
    python3 $S fecha .analise/revisao-2425 revisao --parcial -o .analise/revisao-2425/revisao.json

`estado_2425.json` = rótulo vigente por cadeia (verificação > leitura; inclui verif2 da leitura_2026).
`tiers_2425.json` = nível (A/B/C/D/E) e suspeitas por ativo. `ordem_A.json` = fila do nível A, RL com peça grande da `mae` primeiro.
`pack.py ATIVO...` gera o pacote de ativos específicos.
