# vera-pc — réguas de análise do ETO-COEP

Gestor do posto **ETO-COEP** da Energisa Tocantins. Religadores (RL, código começa
com 79) e reguladores de tensão (RT, código começa com 58). Tema visual do site:
**Prontuário Industrial**. Escrever sempre em português do Brasil, linguagem simples
e direta, sem decoração.

## O que é falha (régua do gestor, 21/08/2026)

Só conta como falha o que exigiu **peça grande**:

- **Religador** — controle, tanque/parte ativa, ou o equipamento completo.
- **Regulador** — célula, relé, o banco completo, ou furto.

Furto é decidido **pela peça, não pela causa**: furto de trafo auxiliar não conta.

**Sinônimos de controle**, que contam: «placa de alimentação CA», «relé de
sincronismo», «armário de controle», «retrofit». **Não contam**: placa de
comunicação, placa 3G, rádio, antena — são telecom. O que decide é a peça, não a
palavra «placa» nem a palavra «relé».

**Fora da taxa, em aba separada**: trafo auxiliar, chave faca, rádio, antena,
bateria, aterramento, cabo, conector, poste, poda, ajuste de proteção,
comissionamento e obra de equipamento novo.

## Como se conta

- **A taxa é divisão direta**: total de equipamentos que falharam ÷ parque. Sem
  anualizar o ano parcial; o ritmo projetado vai em nota de rodapé.
- **Conta EQUIPAMENTO, não ocorrência**: ativo que falhou duas vezes no mesmo ano
  conta uma vez naquele ano — e conta de novo se falhar em outro ano.
- **Parque**: 1.307 religadores (1.297 + 10 instalados em 2026) e 207 reguladores
  (197 + 10). Vale para os três anos. A reconstrução do parque pelo AIC foi
  **abandonada** — superconta (dava 174 RL em 2024 contra realidade de <20/ano).
- **Regulador é banco de três células.** O parque conta banco, não célula; falha de
  uma célula é uma falha do banco.
- **O ano é o da data de ocorrência**, nunca o da abertura da SS. A abertura vem em
  média 39 dias depois do fato e em 9,8% dos casos cai em outro ano. O número da SS
  também não data nada: ETO-COEP 00149/2025 foi aberta em 29/06/2026.
- **Repasse não é falha nova.** O SGM abre SS nova a cada passagem de posto; a
  cadeia inteira é uma falha só.
- **Objeto do fato** — terceiro eixo, e o que mais engana: a SS pendura no código do
  religador porque ele é o marco do trecho, mas o fato é do poste, da cruzeta, da
  vegetação. Sem separar, a taxa do ativo vira taxa do alimentador.

## Posto do COEP — passou e resolveu

- **Passou pelo posto no ano** = a SS esteve lá em algum momento, não só a que chegou
  no ano.
- **Resolvido pelo posto** = a demanda passou pelo COEP dentro do ano E a cadeia dela
  fechou dentro do ano, com SS atendida ou cancelada.
- **Régua do cancelamento (gestor, 22/08)**: cancelado é resolvido, **desde que não
  tenham aberto outra nota para aquele ativo no posto do COEP depois**. Se abriram, a
  demanda voltou para a mesa e segue pendente — não conta. Nota nova em **outro**
  posto não derruba: é outra frente de trabalho. **A nota nova só derruba o
  cancelamento**: SS **atendida** teve serviço executado — nota nova depois dela é
  **reincidência**, demanda nova, e a resolvida fica de pé.
- **Quem fecha não precisa ser o COEP.** ETO-RD-PS, ETO-PROT, ETO-RD-AR e demais
  contam igual — o posto diagnostica e despacha, a ponta executa. O **ETO-TELE**
  conta desde que haja parecer do COEP ou passagem pelo posto antes.
- **A esteira depois do COEP** (gestor, 22/08): quem sai do posto para a **PROT** está em
  ajuste de proteção e quem vai para **TELE/SE** está em comissionamento — nesses, a parte do
  COEP já está concluída. Quem está com equipe **RD** está em execução com os COCMs.
- **Visão ETO do site (gestor, 22/08)**: os ativos 58/79 com SS de **indisponibilidade
  para operação pendente na base de SS/OS** — a carteira não é a fonte («só tem 93,
  então são as 93»; 18 delas fora da carteira). O balde sai do **posto da SS pendente**:
  PROT = ajuste; TELE/SE com criticidade definida na aba de mapeamento = comissionamento,
  sem criticidade definida (fora da aba ou «Sem classificação») = 1º ataque do DMSL;
  RD = execução; COEP = aquisição, salvo «Em logística» da carteira.
- **Primeiro ataque do DMSL não conta**: a demanda morreu na mão da DMSL.
- **A carteira consolidada não serve de fonte para «resolvido»**: ela é a foto do que
  ainda está pendente; o que fechou e saiu não fica registrado nela.

## Armadilhas das bases

- **`DTA_REPASSE` não serve.** É cópia byte a byte da `DTA_ABERTURA` nas 10.386
  linhas. Diz quando a SS chegou, não quando saiu.
- **A data do repasse é a abertura da SS seguinte** (campo `SS_APOS_REPASSE`). O
  tempo parado no posto é a diferença entre as duas aberturas.
- **SS repassada não tem data de conclusão** — sai vazia. Tratar «sem conclusão» como
  «ainda no posto» arrasta SS de 2020 para dentro de 2026.
- **A descrição da SS é cumulativa**: o SGM cola parecer novo por cima do antigo, sem
  separador. Vale sempre o parecer mais recente.
- **Quando a SS e a OS discordam, vale a OS.** O parecer conta o defeito; a OS conta o
  que a obra pagou, no campo Serviço Executado.
- **Formulário DMSL**: «EQUIPAMENTO FICOU EM OPERAÇÃO? NÃO» significa que **não**
  ficou.
- **Texto de terceiro**: laudo de outro ativo colado na descrição da SS. Conferir o
  código antes de acreditar.
- **O SGM não exporta o motivo do cancelamento.** Lacuna conhecida.
- **O nome do arquivo não diz o horizonte do dado**: `EQP_SS_OCORRENCIA_11082026` tem registros
  até **19/08/2026**. Conferir a data máxima antes de fixar o corte.
- **`NUM_OBRA` vem numérico com 9 dígitos** na base de SS/OS; o AIC guarda 10 com
  zero à esquerda. Sem `.zfill(10)` nenhuma obra casa.
- **Trafo auxiliar**: código com prefixo **51** (padrão) ou **57**, com os **8 dígitos
  finais iguais aos do equipamento pai**. Validado por código, pelo texto das obras,
  pelo texto das SS e pelas coordenadas.
- **Projeto SIGCO certo**: 8495 para religador, 8481 para regulador. Trafo auxiliar
  acompanha o projeto do equipamento pai.

## Arquivos e ambiente

- **O AIC é um só**: `AIC_OBRAS_07082026.xlsx`, aba única «Export», 93 colunas,
  124.084 obras. `OBRAS_status_extracao_07082026.xlsx` é o mesmo arquivo (SHA-256
  idêntico), enviado com outro nome.
- **Base de SS/OS crua**: texto com separador `@`, encoding latin-1, descrição quebrando
  linha — remontar registros. A mais nova é `data/raw/BASE_SS_OS_20082026.txt` (gitignored,
  36 MB; aberturas até 20/08). O recorte RL/RT sai por `scripts/extrai_ssos_min.py`.
- **O começo de registro não é o formato do posto**: o código varia (ETO-COEP, DOLP-RD-PA,
  ETO-CADTOC, ETO-TEC01, DMSLETO sem hífen). O que identifica é o `@` colado no ano
  (`\d{5}/\d{4}@`). Regex estreito engoliu 192 registros numa primeira versão.
- **O número no nome da carteira não versiona**: a «ATUALIZADA_3» de 22/08 é byte a byte a
  ATUALIZADA 16 (MD5 igual). Conferir hash antes de reprocessar.
- **`dist/` está no `.gitignore`** — planilhas vão por SendUserFile, não por commit.
- **LibreOffice não roda neste ambiente** — o Excel grava valores, não fórmulas.
- Playwright: `NODE_PATH=/opt/node22/lib/node_modules /opt/node22/bin/node`,
  `executablePath: '/opt/pw-browsers/chromium'`.

## Artifacts vivos

| Página | URL |
| --- | --- |
| Painel de equipamentos especiais | https://claude.ai/code/artifact/d65c0278-32e4-47aa-815b-43abc992a630 |
| Dinâmica do posto | https://claude.ai/code/artifact/b4ef898c-efd8-4681-b996-2808001354ec |
| Taxa de falha | https://claude.ai/code/artifact/978e5138-959a-4290-b454-c83774129095 |

Antes de republicar, **ler a versão que está no ar** (`action: "read"`) e conferir o
que muda — o publish é recusado se a versão viva não foi vista.
