# Revisão 2024-2025 — instruções do trabalhador

Você revisa uma PARTE da fila. É a segunda opinião sobre classificações que já existem:
não é refazer a leitura, é perguntar **o que a evidência sustenta?**

## Leia antes

    cat /home/user/vera-pc/.claude/skills/analise-equipamento/referencia/regua.md
    cat /home/user/vera-pc/.claude/skills/analise-equipamento/referencia/armadilhas.md

## O ciclo — repita até acabar a sua parte ou o seu contexto

    R=/home/user/vera-pc/.analise/revisao-2425
    S=/home/user/vera-pc/.claude/skills/checkpoint/scripts/ckpt.py

    python3 $S todo $R revisao --parte <SUA_PARTE>        # o que falta na sua parte
    python3 $R/ferramentas/pack.py --parte <SUA_PARTE> --kb 40 > /tmp/pk<SUA_PARTE>.txt
    #   lê o pacote inteiro; escreve /tmp/ver<SUA_PARTE>.json
    python3 $R/ferramentas/grava.py /tmp/ver<SUA_PARTE>.json

`grava.py` **valida antes de gravar** — rótulo fora da lista, cadeia que não é do ativo,
`mantem=true` com rótulo mudado, tudo isso ele recusa e diz o porquê. Corrija e rode de
novo; ele faz um `put` por ativo, então o que passou está salvo.

**Nunca acumule para gravar no fim.** Um pacote de cada vez, grava, próximo. Se o contexto
acabar no meio, o que está gravado está salvo e outro retoma pelo `todo`.

**Não leia o arquivo de outro trabalhador** (`dados/revisao/*.jsonl` que não seja o seu,
nem `/tmp/ver*` alheio). Numa rodada anterior um leitor copiou a «convenção» dos vizinhos e
espalhou o erro por vários lotes.

## O formato de cada ativo

```json
{"ativo":"7900001234",
 "demandas":[
   {"cadeia":"ETO-TELE 00123/2024",
    "mantem": true,
    "categoria_final":"tanque",
    "duplicata_de": null,
    "aberta_por_engano": false,
    "executada": true,
    "porque":"o parecer nomeia a parte ativa e confirma a troca em 12/11",
    "confianca":"alta"}
 ]}
```

Uma entrada para **cada** cadeia do ativo — `grava.py` confere que não falta nenhuma.

## O que procurar, nesta ordem

1. **Duplicata.** Duas cadeias do mesmo ativo que descrevem o MESMO evento físico. O padrão
   que mais aparece: **a SS que o RD abre para executar o serviço, contada à parte da cadeia
   que o pediu** — a SS do RD não é repasse, é nota nova, então a base não liga as duas.
   Exemplo real: 7909599004 teve um evento (buchas danificadas no remanejamento) contado em
   três cadeias. A que tem a peça confirmada e a execução é a que vale; na outra ponha
   `duplicata_de` com o número dela e `mantem: false`.
2. **SS aberta por engano** — sem defeito descrito. Cuidado: cancelamento em bloco de cadeia
   **com** defeito real não é engano, é fila abandonada; marque `executada: false`.
3. **Rótulo que a citação não sustenta.** Sintoma não é peça: «não fecha», «não aceita
   comando», «disjuntor não arma», «display apagado» → `nao identificado`. «Não comunica»,
   «não responde remoto» → `telecom`. Ninho de inseto → `sem defeito`.

Se o rótulo está certo e não há duplicata, `mantem: true` e siga. A leitura anterior estava
boa no rótulo — o que ela errou foi a contagem.

## Ao terminar

Responda em texto só com: quantos ativos revisou, quantas duplicatas achou, quantas SS por
engano, quantos rótulos derrubou, e quantos ficaram faltando na sua parte. Nada mais.
