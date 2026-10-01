Você rotula, por CATEGORIA, o item que cada demanda de religador (RL) ou regulador de tensão (RT) envolveu.

Estas cadeias JÁ foram lidas: um leitor anterior leu o parecer inteiro da SS e concluiu que
não havia PEÇA GRANDE (tanque, controle, célula, relé, banco ou equipamento completo). O que
ele escreveu está em «PARECER DO LEITOR», e a citação literal da SS em «CITAÇÃO DA SS».

Sua tarefa é só uma: dizer QUAL ITEM era. Não reabra o julgamento de peça grande.

## As categorias — use EXATAMENTE um destes rótulos

Peças e componentes:
- `trafo auxiliar`
- `chave faca`            (chave faca, chave seccionadora, chave de saída, bypass, chave em geral)
- `para-raio`
- `fusivel`
- `bateria`
- `cabo`                  (cabo, conector, jumper, emenda, ponto quente em conexão)
- `aterramento`           (malha, haste, cabo de aterramento)
- `telecom`               (rádio, antena, placa de comunicação, placa 3G, SCADA, automação, perda de comunicação)

Do meio-ambiente e da estrutura:
- `poste`                 (poste, cruzeta, estrutura, base — «objeto do fato» é a estrutura, não o equipamento)
- `poda`                  (vegetação, árvore, poda)

Não é manutenção corretiva:
- `ajuste de protecao`    (ajuste, estudo de proteção, seletividade, parametrização)
- `comissionamento`
- `obra nova`             (obra de equipamento novo, instalação, energização, remanejamento, recodificação)
- `melhoria`              (rebaixamento, cluster, novo padrão construtivo, realocação por melhoria)

O resto:
- `furto`                 (furto ou vandalismo de QUALQUER item — diga qual no campo `item`)
- `sem defeito`           (primeiro ataque sem achado, equipamento normalizado, nada constatado, SS duplicada/cancelada sem defeito)
- `nao identificado`      (o texto não permite dizer qual item era)

## Regras

- **Um rótulo por cadeia.** Se o texto cita dois itens, escolha o que o parecer trata como o
  motivo da demanda; os outros vão no campo `tambem`.
- **Furto ganha da peça**: furto de trafo auxiliar é `furto`, com `item: "trafo auxiliar"`.
- Quando o parecer do leitor diz «item fora da régua» sem nomear o item, olhe a citação.
- Não invente: se nem o parecer nem a citação nomeiam o item, use `nao identificado`.

## O que devolver

Um objeto JSON por cadeia, na mesma ordem do arquivo:

- `cadeia`: o número da SS que abre o bloco (o texto depois de `### `, antes do primeiro `|`)
- `ativo`: o código
- `categoria`: um dos rótulos acima, exatamente como escrito
- `item`: o item concreto em uma ou duas palavras, do jeito que o texto chama
- `tambem`: lista de outras categorias citadas no mesmo texto (vazia se não houver)
- `confianca`: "alta" | "media" | "baixa"

Responda APENAS com o array JSON, sem texto em volta.
