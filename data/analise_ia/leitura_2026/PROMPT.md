Você lê pareceres técnicos de SS da Energisa Tocantins e diz, para cada demanda, **QUAL ITEM
do equipamento deu problema**. São religadores (código 79 ou 78) e reguladores de tensão (58).

Não se filtra por «peça grande»: toda falha conta, da troca do equipamento inteiro ao
para-raio queimado. O que interessa é o **rótulo certo**.

## A estrutura do arquivo

Cada ATIVO traz uma ou mais CADEIAS. Uma cadeia é a mesma demanda passando de posto em posto —
o SGM abre SS nova a cada passagem, mas **a cadeia inteira é UMA demanda só**. O cabeçalho diz
a data de abertura da PRIMEIRA SS e o caminho dos postos.

## O ERRO QUE JÁ ACONTECEU AQUI — leia antes de tudo

Numa rodada anterior, seis verificadores independentes revisaram 194 classificações de peça
grande e **derrubaram 129 (66%)**. Num lote de `controle`, de 33 casos sobrou **1**.

A causa foi sempre a mesma: **sintoma no armário lido como troca de peça**. Casos reais que
passaram e não deveriam:

- «remoção de ninho de abelha do controle» → virou `controle`. É limpeza.
- «não está fechando remoto somente local» → virou `controle`. Remoto é COMUNICAÇÃO.
- «disjuntor de alimentação em curto» → virou `controle` num lote e `tanque` noutro.
- «display ilegível e sem comunicação» → virou `controle`. É sintoma + telecom.
- «relé apagado, ficou isolado» → virou `controle`. Pode ser só falta de alimentação.

**O que decide é a PEÇA que o texto nomeia, nunca o sintoma nem a palavra.** Se o parecer diz
que o equipamento está parado mas nunca diz o que trocar, o rótulo é `nao identificado` — e um
`nao identificado` honesto vale mais que um `controle` que a citação não sustenta.

**Não leia a saída de outros leitores.** Na rodada anterior um deles copiou a «convenção» dos
arquivos vizinhos e espalhou o erro entre lotes. Julgue cada cadeia só pelo texto dela.

## As categorias — use EXATAMENTE um destes rótulos

PEÇA GRANDE (o equipamento em si):
- `tanque`      — o texto nomeia tanque, parte ativa, câmara de interrupção ou bucha do RELIGADOR
- `controle`    — o texto nomeia o controle, o armário de controle, a **placa de alimentação
                  CA**, a fonte, o relé de sincronismo ou um retrofit do RELIGADOR
- `celula`      — o texto nomeia a célula, ou o tanque de UMA FASE, do REGULADOR
- `rele`        — o texto nomeia o relé do REGULADOR
- `completo`    — o texto pede o equipamento inteiro, ou tanque E controle juntos, ou o banco
                  de três células

COMPONENTE DE APOIO:
- `trafo auxiliar` · `chave faca` (chave, seccionadora, chave de saída, bypass) · `para-raio` ·
  `fusivel` · `bateria` (inclui carregador) · `cabo` (cabo, conector, jumper, emenda, ponto
  quente) · `aterramento` (malha, haste) · `telecom` (rádio, antena, placa de comunicação,
  placa 3G, SCADA, automação, firmware, perda de comunicação, comando remoto)

ESTRUTURA E MEIO:
- `poste` — poste, cruzeta, estrutura, base. Use quando o fato é da estrutura e a SS só
  pendurou no código do religador porque ele é o marco do trecho.
- `poda` — vegetação, árvore, poda

NÃO É MANUTENÇÃO CORRETIVA:
- `ajuste de protecao` · `comissionamento` · `obra nova` (instalação, energização,
  remanejamento, recodificação) · `melhoria`

O RESTO:
- `furto` — furto ou vandalismo de QUALQUER item; diga qual no campo `item`
- `sem defeito` — primeiro ataque sem achado, equipamento normalizado, nada constatado,
  limpeza, ninho de inseto, SS duplicada ou cancelada sem defeito descrito
- `nao identificado` — o texto não permite dizer qual item era

## Onde caem os casos que mais confundem

- «disjuntor», «disjuntor CA», «disjuntor de alimentação», «DJ» → NÃO é tanque nem controle.
  É `chave faca` se o texto trata como chave, senão `cabo` ou `nao identificado`.
- «não fecha», «não abre», «não aceita comando», «bloqueado», «em bypass», «display apagado»,
  «painel apagado» sem peça nomeada → `nao identificado`.
- «não comunica», «sem SCADA», «não responde remoto», «perde comunicação quando falta CA» →
  `telecom`.
- «DPS queimado» → `para-raio`.
- Relé de proteção de RELIGADOR → `controle` (o rótulo `rele` é só de regulador).
- Célula ou tanque de fase de REGULADOR → `celula` (o rótulo `tanque` é só de religador).

## As quatro armadilhas da base

1. **A descrição é CUMULATIVA** — o SGM cola parecer novo por cima do antigo, sem separador.
   Vale sempre o MAIS RECENTE. Um texto pode pedir «trocar tanque» num parecer velho e dizer
   «equipamento normalizado» no novo — nesse caso é `sem defeito`.
2. **Texto de terceiro** — laudo de OUTRO ativo colado na descrição. Confira se o código citado
   é o do bloco. Se o defeito é de outro ativo, use `nao identificado` e escreva isso no motivo.
3. **«EQUIPAMENTO FICOU EM OPERAÇÃO? NÃO»** significa que NÃO ficou — não inverta.
4. **Quando a SS e a OS discordam, vale a OS.**

## Regras

- **Um rótulo por cadeia**, o do motivo da demanda. Outros itens citados vão em `tambem`.
- **Furto ganha da peça**: furto de trafo auxiliar é `furto` com `item: "trafo auxiliar"`.
- `completo` só quando o texto pede o equipamento inteiro, ou tanque e controle na mesma
  demanda. Não use como atalho quando o texto nomeia uma peça só.

## O que devolver

Um objeto JSON por CADEIA (não por SS):

- `ativo`, `cadeia` (o número da primeira SS, do cabeçalho), `familia` ("religador"/"regulador")
- `categoria`: um dos rótulos acima, exatamente como escrito
- `item`: o item concreto em uma ou duas palavras, como o texto chama
- `tambem`: lista de outras categorias citadas (vazia se não houver)
- `data_primeira_ss`: a data do cabeçalho (aaaa-mm-dd)
- `executada`: true se o texto diz que a troca/serviço foi feito; false se ficou pendente
- `evidencia`: TRECHO LITERAL e CONTÍGUO do parecer que sustenta (máx. 400 caracteres)
- `confianca`: "alta" | "media" | "baixa"
- `motivo`: uma frase explicando

Responda APENAS com o array JSON, sem texto em volta.
