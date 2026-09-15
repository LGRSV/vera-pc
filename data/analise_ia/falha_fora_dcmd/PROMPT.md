Você lê pareceres técnicos de SS da Energisa Tocantins e diz, para cada demanda, **QUAL ITEM
do equipamento deu problema**. São religadores (código 79 ou 78) e reguladores de tensão (58).

Diferente de leituras anteriores, aqui **NÃO se filtra por peça grande**: toda falha conta, da
troca do equipamento inteiro ao para-raio queimado. O que interessa é o rótulo certo.

## A estrutura do arquivo

Cada ATIVO traz uma ou mais CADEIAS. Uma cadeia é a mesma demanda passando de posto em posto —
o SGM abre SS nova a cada passagem, mas **a cadeia inteira é UMA demanda só**, nunca várias. O
cabeçalho diz a data de abertura da PRIMEIRA SS e o caminho dos postos.

## As categorias — use EXATAMENTE um destes rótulos

PEÇA GRANDE (o equipamento em si):
- `tanque`      — tanque, parte ativa, câmara de interrupção, bucha (só religador)
- `controle`    — controle, armário de controle, placa de alimentação CA, fonte, relé de
                  sincronismo, retrofit (só religador). **Placa de comunicação e placa 3G NÃO
                  são controle — são `telecom`.**
- `celula`      — célula ou tanque de uma fase do regulador (só regulador)
- `rele`        — relé do regulador (só regulador)
- `completo`    — o equipamento inteiro, ou tanque E controle juntos, ou o banco de três células

COMPONENTE DE APOIO:
- `trafo auxiliar`
- `chave faca`  — chave faca, seccionadora, chave de saída, bypass
- `para-raio`
- `fusivel`
- `bateria`
- `cabo`        — cabo, conector, jumper, emenda, ponto quente em conexão
- `aterramento` — malha, haste, cabo de aterramento
- `telecom`     — rádio, antena, placa de comunicação, placa 3G, SCADA, automação, perda de
                  comunicação

ESTRUTURA E MEIO:
- `poste`       — poste, cruzeta, estrutura, base. Use quando o fato é da estrutura e a SS só
                  pendurou no código do religador porque ele é o marco do trecho.
- `poda`        — vegetação, árvore, poda

NÃO É MANUTENÇÃO CORRETIVA:
- `ajuste de protecao`
- `comissionamento`
- `obra nova`   — obra de equipamento novo, instalação, energização, remanejamento, recodificação
- `melhoria`

O RESTO:
- `furto`       — furto ou vandalismo de QUALQUER item; diga qual no campo `item`
- `sem defeito` — primeiro ataque sem achado, equipamento normalizado, nada constatado, SS
                  duplicada ou cancelada sem defeito descrito
- `nao identificado` — o texto não permite dizer qual item era

## Quatro armadilhas que já derrubaram leituras aqui

1. **A descrição é CUMULATIVA** — o SGM cola parecer novo por cima do antigo, sem separador.
   Vale sempre o parecer MAIS RECENTE. Um texto pode pedir «trocar tanque» num parecer velho e
   dizer «equipamento normalizado» no novo — nesse caso é `sem defeito`.
2. **Texto de terceiro** — laudo de OUTRO ativo colado na descrição. Confira se o código citado
   é o do bloco antes de acreditar. Se o defeito é de outro ativo, use `nao identificado` e
   escreva isso no motivo.
3. **«EQUIPAMENTO FICOU EM OPERAÇÃO? NÃO»** significa que NÃO ficou — não inverta.
4. **Quando a SS e a OS discordam, vale a OS.**

## Regras

- **Um rótulo por cadeia**, o do motivo da demanda. Outros itens citados vão em `tambem`.
- **Furto ganha da peça**: furto de trafo auxiliar é `furto` com `item: "trafo auxiliar"`.
- `completo` só quando o texto pede o equipamento inteiro, ou tanque e controle na mesma
  demanda. Não use como atalho quando o texto nomeia uma peça só.
- Seja cético: se o texto não sustenta um item, `nao identificado` é a resposta honesta.

## O que devolver

Um objeto JSON por CADEIA (não por SS):

- `ativo`, `cadeia` (o número da primeira SS, do cabeçalho), `familia` ("religador"/"regulador")
- `categoria`: um dos rótulos acima, exatamente como escrito
- `item`: o item concreto em uma ou duas palavras, como o texto chama
- `tambem`: lista de outras categorias citadas (vazia se não houver)
- `data_primeira_ss`: a data do cabeçalho (aaaa-mm-dd)
- `executada`: true se o texto diz que a troca/serviço foi feito; false se ficou pendente
- `evidencia`: TRECHO LITERAL do parecer que sustenta (máx. 400 caracteres)
- `confianca`: "alta" | "media" | "baixa"
- `motivo`: uma frase explicando

Responda APENAS com o array JSON, sem texto em volta.
