---
name: analise-equipamento
description: Analisa falhas de religadores e reguladores lendo TODAS as SS de cada ativo, com quatro papéis encadeados — analista, revisor, verificador de execução e compilador — e checkpoint por ativo para nada se perder quando o contexto acaba. Use para apurar taxa de falha, classificar defeito por peça, achar SS duplicada ou aberta por engano, conferir se a troca foi mesmo executada, e alimentar o painel.
---

# Análise de falha de equipamento especial

Quatro papéis, em sequência, sobre os mesmos ativos. Cada um grava item a item pela skill
`checkpoint` — nenhum guarda resultado na cabeça para gravar no fim.

```
dossiê  →  ANALISTA  →  REVISOR  →  VERIFICADOR  →  COMPILADOR  →  painel
           (lê tudo)   (2ª opinião) (foi feito?)   (junta e conta)
```

## Antes de tudo

Leia as duas referências. Elas são a régua, não sugestão:

- `referencia/regua.md` — o que conta como falha, os 22 rótulos, como se conta
- `referencia/armadilhas.md` — as armadilhas da base e o erro que já custou 66% de uma leitura

## 1. Montar o dossiê

```bash
python3 .claude/skills/analise-equipamento/scripts/dossie.py .analise/run1 \
        --anos 2024,2025,2026 --lotes 12
```

O dossiê traz **todas as SS do ativo**, não só as da demanda em análise — sem o histórico
inteiro não dá para dizer se é duplicata, se a SS foi aberta por engano, ou se o defeito
já tinha voltado antes. Cada demanda vem com as **suspeitas** já calculadas
(`mesma_peca_em_dias`, `cancelada_no_mesmo_dia`, `cancelamento_em_bloco`, `sem_parecer`,
`codigo_de_terceiro`, `reincidencia`). Elas apontam onde olhar; **não decidem**.

Depois, declare o trabalho no checkpoint:

```bash
S=.claude/skills/checkpoint/scripts/ckpt.py
python3 $S init .analise/run1 --itens-json .analise/run1/ativos.json \
        --etapas analise,revisao,verificacao --partes 12
```

## 2. ANALISTA — lê tudo e classifica

Um agente por parte. Cada um recebe: as duas referências, o seu lote, e a instrução de
**não ler a saída de nenhum outro analista**.

Por ativo, devolve um objeto com uma entrada por demanda:

| campo | o que é |
| --- | --- |
| `ativo`, `familia` | o código e RL/RT |
| `demandas[]` | uma por cadeia: `cadeia`, `data_primeira_ss`, `categoria`, `item`, `tambem[]` |
| `demandas[].duplicata_de` | se é a mesma demanda de outra cadeia, o número dela; senão `null` |
| `demandas[].aberta_por_engano` | true quando a SS não descreve defeito nenhum |
| `demandas[].executada` | true só se o texto diz que foi feito |
| `demandas[].evidencia` | trecho **literal e contíguo** do parecer, até 400 caracteres |
| `demandas[].confianca` | alta · media · baixa |
| `demandas[].motivo` | uma frase |

**Grave assim que terminar cada ativo**, nunca em bloco:

```bash
python3 $S put .analise/run1 analise --parte 3 --chave 7926089013 --de-arquivo /tmp/a.json
```

## 3. REVISOR — a segunda opinião, com o mesmo contexto

Recebe o dossiê **e** o veredito do analista. Mesma régua, pergunta diferente:
*o que a evidência sustenta?*

- Rótulo que a citação não sustenta **cai** — e o revisor diz para onde vai.
- Duplicata não vista pelo analista **entra**.
- Duplicata vista onde não havia **sai**.

Devolve `mantem`, `categoria_final`, `duplicata_de`, `porque`, `confianca`. Grava na etapa
`revisao`, item a item.

> **A passada mais rentável deste fluxo é adversarial.** Numa rodada real, seis revisores
> instruídos a *derrubar* a classificação anterior derrubaram **129 de 194 (66%)** — e num
> lote de `controle`, de 33 casos sobrou 1. Sem eles, o painel teria dito que controle era
> a maior causa de falha do parque. Era artefato da leitura.

## 4. VERIFICADOR — a capacidade real e o que foi mesmo executado

A pergunta aqui não é qual peça, é **o que de fato aconteceu com o equipamento**:

- A troca foi **executada**? Quem diz — a SS, a OS, o laudo, a foto de campo?
- O equipamento **voltou a operar**? («FICOU EM OPERAÇÃO? NÃO» significa que não ficou.)
- A SS está **ATENDIDA mas o texto nega o conserto**? O texto vale mais que o status.
- **Cancelada**: resolveu, ou foi limpeza de cadastro em bloco?
- Sobrou **pendência** depois da troca — comissionamento, aterramento, ajuste?

Devolve `executada`, `voltou_a_operar`, `prova` (onde está escrito), `pendencia_restante`,
`divergencia_ss_os`, `confianca`. Grava na etapa `verificacao`, item a item.

## 5. COMPILADOR — junta, conta e publica

```bash
python3 $S fecha .analise/run1 analise     -o .analise/run1/analise.json
python3 $S fecha .analise/run1 revisao     -o .analise/run1/revisao.json
python3 $S fecha .analise/run1 verificacao -o .analise/run1/verificacao.json
python3 .claude/skills/analise-equipamento/scripts/juntar.py .analise/run1
```

`juntar.py` aplica a ordem de precedência — **verificação > revisão > análise** —, tira as
duplicatas, conta por equipamento-ano-item e escreve o JSON do painel. Ele também relata
**quanto a revisão derrubou**: esse número é resultado, não ruído, e vai no painel.

Só então republique o artifact. Antes de publicar, leia a versão no ar (`action: "read"`).

## As regras que não se negociam

1. **`todo` antes de começar**, em toda etapa e toda parte.
2. **Um `put` por ativo, na hora.** Nunca acumular para o fim.
3. **Nenhum papel lê a saída de um colega da mesma etapa.** Revisor e verificador leem a
   etapa anterior — nunca os vizinhos da própria.
4. **Peça que não cabe na família cai**: tanque ou controle em regulador, célula ou relé
   em religador.
5. **Na dúvida, `nao identificado`.** Um «não identificado» honesto mede a lacuna do SGM;
   um `controle` sem evidência mente no painel.
6. **Nada de triagem por palavra-chave.** Testada e reprovada: 29% de fuga.
