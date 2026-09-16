---
name: checkpoint
description: Trabalho longo que não se perde quando o contexto acaba. Grava cada item assim que fica pronto, num JSONL à prova de queda, e responde «o que falta?» para retomar de onde parou. Use sempre que uma tarefa percorrer dezenas ou centenas de itens — ler arquivos, classificar registros, migrar código, auditar, revisar —, sozinho ou com vários agentes em paralelo, e principalmente quando houver mais de uma passada sobre os mesmos itens (leitura, revisão, conferência).
---

# checkpoint

## O que resolve

Um agente processa 80 itens e guarda tudo na cabeça para gravar no fim. No item 79 o
contexto estoura. Perdem-se os 79, e quem retoma não sabe onde parou.

Esta skill troca isso por: **grave cada item assim que ele fica pronto.** O pior caso
passa a ser perder um item. Retomar vira uma pergunta que o próprio arquivo responde.

## Quando usar

- A tarefa tem **muitos itens** e o resultado de cada um importa.
- São **várias passadas** sobre os mesmos itens (ler → revisar → conferir).
- Há **vários agentes** trabalhando em paralelo sobre fatias diferentes.
- O trabalho pode **atravessar sessões** — hoje começa, amanhã continua.

Não use para tarefa de um passo só, nem quando o resultado cabe numa resposta.

## Como funciona

Um diretório com arquivos de texto. Sem banco, sem servidor, sem dependência.

```
run/
  manifesto.json                 o que precisa ser feito, e em quais etapas
  dados/<etapa>/<parte>.jsonl    uma linha por item pronto (append-only, fsync)
  notas/<etapa>/<parte>.log      diário de bordo
  <etapa>.json                   o consolidado, quando a etapa fecha
```

### As garantias, e por que valem

Todas foram atacadas por uma auditoria adversarial — truncamento byte a byte, `kill -9`
no meio da gravação, disco cheio, concorrência real, registros hostis. O que quebrou
está consertado; o que sobrou de pé está medido.

| garantia | como |
| --- | --- |
| **Nada se perde em silêncio** | cada `put` é um `write()` único com `O_APPEND` + `fsync`, **e confere quantos bytes entraram**. Gravação parcial (disco cheio, `ulimit -f`) falha alto com rc 1, em vez de responder «gravado» com o dado perdido. |
| **Queda no meio da linha não contamina** | o `put` escreve `\n` **antes** da linha, sempre. A linha quebrada de quem morreu fica isolada; o registro novo entra inteiro. |
| **Linha quebrada é ignorada, não fatal** | a leitura descarta linha inválida — truncada, ou JSON válido que não é objeto — e segue. O item dela volta a aparecer em `todo`. |
| **Refazer é seguro** | a chave manda, e «último vence» é o **mais recente pelo carimbo**, não o de nome alfabeticamente maior. Item refeito não vira dois nem volta para a versão velha. |
| **Paralelo é seguro** | cada trabalhador na sua **parte**. Medido: 4 processos × 150 registros de 50 KB simultâneos, 600 de 600 íntegros. |
| **O escopo não escorrega** | `put` recusa chave fora do manifesto, etapa fora do manifesto e parte que não existe. Nome de etapa ou parte com `/` ou `..` é recusado — sem isso dava para gravar fora do run. |
| **O run não é reaberto por engano** | `init` sobre um run que já tem dados é recusado (salvo `--forcar`): repartir de novo faria o `todo` comparar com a lista errada. |
| **`todo` serve de condição** | sai com rc 1 quando falta item, então dá para encadear `todo … && fecha …`. |

**O que ainda NÃO está coberto, e você precisa saber:** dois trabalhadores na **mesma
parte** continuam desaconselhados. O dano catastrófico foi consertado, mas a disciplina
de uma parte por trabalhador é o que torna o paralelo previsível.

## Uso

`S=.claude/skills/checkpoint/scripts/ckpt.py`

### 1. Declare o trabalho
```bash
python3 $S init .analise/run1 --itens-de lista.txt \
        --etapas leitura,revisao,conferencia --partes 8 \
        --descricao "classificar as SS de 2026"
```
`--itens` (a,b,c), `--itens-de` (um por linha) ou `--itens-json`. As **partes** repartem
os itens entre os trabalhadores.

### 2. Grave item a item — nunca em bloco no fim
```bash
python3 $S put .analise/run1 leitura --chave 7926089013 --dados '{"falha":true,"peca":"tanque"}'
```
Também aceita `--de-arquivo resposta.json` ou o JSON por stdin. Ele carimba `_chave`,
`_etapa` e `_em` sozinho.

### 3. Retome sem pensar
```bash
python3 $S todo .analise/run1 leitura --parte 3      # o que falta na minha parte
python3 $S status .analise/run1                      # painel de todas as etapas
```

### 4. Feche a etapa
```bash
python3 $S fecha .analise/run1 leitura -o leitura.json
```
Recusa fechar com item faltando, a não ser com `--parcial`. A saída sai **na ordem do
manifesto**, não na ordem em que foi gravada.

### Os outros
```bash
python3 $S ler   .analise/run1 leitura --chave 7926089013   # o que já gravei disto?
python3 $S nota  .analise/run1 leitura --parte 3 "parei no 40, textos longos"
python3 $S sweep .analise/run1                              # há linha corrompida?
python3 $S init  .analise/run1 --itens … --forcar            # repartir um run já iniciado
```

## A disciplina que o agente precisa seguir

Estas cinco regras é que fazem a garantia valer. A ferramenta não consegue impor
sozinha — quem chama tem de cumprir.

1. **`todo` antes de começar.** Sempre. Mesmo na primeira vez: se a sessão anterior
   morreu, metade já pode estar pronta.
2. **`put` a cada item**, na hora. Nunca acumule «para gravar tudo no fim» — é
   exatamente o hábito que a skill existe para quebrar.
3. **Uma parte por trabalhador.** Dois agentes na mesma parte é a única forma de
   corromper o arquivo.
4. **Não leia a saída dos outros trabalhadores.** Numa rodada real deste projeto, um
   leitor copiou a «convenção» dos arquivos vizinhos e espalhou um erro por vários
   lotes. Cada item se julga sozinho.
5. **`fecha` só quando `todo` estiver vazio.** Se usar `--parcial`, diga no relatório
   quantos ficaram de fora — silêncio aqui vira número errado depois.

## Várias passadas sobre os mesmos itens

As etapas existem para isso. Cada uma tem seu próprio JSONL, então a revisão nunca
sobrescreve a leitura — dá para comparar as duas e medir quanto a revisão derrubou.

```bash
python3 $S fecha .analise/run1 leitura   -o leitura.json
python3 $S fecha .analise/run1 revisao   -o revisao.json
# as duas lado a lado mostram o que mudou, e por quê
```

Um padrão que funcionou aqui: a etapa de **conferência** é adversarial — o agente é
instruído a *derrubar* a classificação anterior, e só mantém o que a evidência sustenta.
Numa rodada real isso derrubou 66% das classificações, e evitou publicar um número errado.
