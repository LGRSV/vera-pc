# As armadilhas — todas já derrubaram uma leitura aqui

## Da base

**1. A descrição é CUMULATIVA.** O SGM cola parecer novo por cima do antigo, sem
separador. Vale sempre o **mais recente**. Um texto pode pedir «trocar tanque» num parecer
velho e dizer «equipamento normalizado» no novo — nesse caso é `sem defeito`.

**2. Texto de terceiro.** Laudo de OUTRO ativo colado na descrição. Confira se o código
citado é o do bloco antes de acreditar. Se o defeito é de outro ativo, use
`nao identificado` e escreva isso no motivo.
*Casos reais*: 7900543083 trazia o laudo do 7900448083; 7944319149 trazia o do 7955430075
(SID 4589 contra 4590); 7905359122 cita 7909593122 e nunca o próprio código.

**3. «EQUIPAMENTO FICOU EM OPERAÇÃO? NÃO»** significa que **não** ficou. Não inverta.

**4. Quando a SS e a OS discordam, vale a OS.** O parecer conta o defeito; a OS conta o
que a obra pagou, no campo Serviço Executado.

**5. Status ATENDIDA não é prova de conserto.** Há SS marcadas ATENDIDA cujo texto diz
«primeiro ataque sem sucesso» ou «não retornou». O texto vale mais que o status.

**6. `DTA_REPASSE` não serve** — é cópia byte a byte da `DTA_ABERTURA`. A data real do
repasse é a abertura da SS seguinte.

**7. SS repassada não tem data de conclusão** — sai vazia. Tratar «sem conclusão» como
«ainda no posto» arrasta SS de 2020 para dentro do ano corrente.

**8. O SGM não exporta o motivo do cancelamento.** Lacuna conhecida: cancelada não diz
por quê.

## Da leitura — o erro que já custou caro

Numa rodada, seis verificadores independentes revisaram 194 classificações de peça grande
e **derrubaram 129 (66%)**. Num lote de `controle`, de 33 casos sobrou **1**.

A causa foi sempre a mesma: **sintoma no armário lido como troca de peça**.

| passou como | era |
| --- | --- |
| «remoção de ninho de abelha do controle» → `controle` | limpeza, `sem defeito` |
| «não está fechando remoto somente local» → `controle` | remoto é `telecom` |
| «disjuntor de alimentação em curto» → `controle` num lote, `tanque` noutro | nem um nem outro |
| «display ilegível e sem comunicação» → `controle` | sintoma + `telecom` |
| «relé apagado, ficou isolado» → `controle` | pode ser só falta de alimentação |

**E o vetor de propagação**: um dos leitores escreveu que olhou a saída dos arquivos
vizinhos «para manter a convenção» — e espalhou o erro entre lotes.

> **Regra dura**: o analista nunca lê a saída de outro analista. Cada dossiê se julga
> sozinho. O revisor e o verificador leem o dossiê e o veredito do anterior, e só.

## Da triagem

**Palavra-chave não serve.** O regex de peça foi testado e reprovado: deixou escapar 6 das
21 falhas conhecidas de 2025, **29% de fuga**. Todo texto tem de ser lido.

## Da duplicata e da SS aberta sem querer

O dossiê já traz as suspeitas calculadas (`suspeitas` em cada demanda). Elas **não
decidem** — apontam onde olhar:

| bandeira | o que significa |
| --- | --- |
| `mesma_peca_em_dias` | outra demanda do mesmo ativo, mesma peça, aberta em ≤ 30 dias — provável duplicata |
| `cancelada_no_mesmo_dia` | aberta e cancelada no mesmo dia, sem parecer — provável abertura por engano |
| `cancelamento_em_bloco` | cancelada no mesmo dia que ≥ 5 outras SS de postos diferentes — limpeza de cadastro, não conserto |
| `sem_parecer` | cadeia inteira sem uma linha de descrição |
| `codigo_de_terceiro` | o texto cita código de ativo diferente do dono da SS |
| `reincidencia` | mesma peça, mesmo ativo, em ano diferente — demanda que voltou por não ter sido resolvida |

**A régua de julgamento**: duplicata é uma demanda só. Se duas cadeias descrevem o mesmo
evento físico, a que tem a peça confirmada e a execução é a que vale; a outra sai como
`duplicata_de` apontando para ela. SS aberta por engano sai como `sem defeito` com o
motivo escrito.
