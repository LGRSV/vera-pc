# vera-pc — réguas de análise do ETO-COEP

Gestor do posto **ETO-COEP** da Energisa Tocantins. Religadores (RL, código começa
com 79 — e **78 no monofásico**, recodificado por decisão de cadastro: «RELIGADOR
MONOFASICO ALTERAR A SUA CODIFICAÇÃO DE 79 PARA 78», ETO-CADTOC 00140/2024; são 6
ativos, 10 SS) e reguladores de tensão (RT, código começa com 58). Tema visual do site:
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
  (197 + 10). Vale para os três anos. **Para a série mensal de 2026 o gestor deu outra
  base (24/08)**: janeiro com **1.281 RL** e **180 RT**, mais a expansão realizada
  somada no próprio mês (RL 2·0·2·2·3·1·3 · RT 0·3·3·1·1·1·1, jan–jul) — fecha agosto
  em 1.294 e 190. É essa que vale no `parque_2026.py`. A reconstrução do parque pelo AIC foi
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
- **A partição dos 143 (`particao_coep.py`)** parte em quatro. **Quem voltou não conta**
  (gestor, 28/08): resolveu no ano e voltou para a fila é pendente, não resolvido — tira
  11. **Resolvido é o que acabou** (gestor, 29/08): os 18 de «outra mesa» passaram
  **todos** por um COCM antes, e em 15 a peça foi trocada e o campo devolveu — mas o
  equipamento **segue com SS aberta** na mesa seguinte (PROT, TELE, SE), de 1 a 41 dias
  lá. A parte do COEP acabou, o serviço não; ficam em **balde próprio**, não nos
  resolvidos. Somá-los levava a 86, e o gestor não reconhece o número: «nem eu acho que
  resolvi 86, no máximo 72». Os **3 que ainda estão num COCM** (7905357122 Palmas,
  7908705049 Aurora, 5856070091 Almas) ficam em **execução no campo**. Fecha em
  **71 resolvidos (45 RL + 26 RT) · 54 na fila · 15 despachados · 3 em execução = 143**,
  e a conta do posto em **71 + 54 = 125** — que é onde a memória do gestor sempre esteve
  («125 passaram, resolvemos 72, estamos com 53», 21/08).
- **«Resolvido» tem duas leituras, e as duas ficam à vista** (gestor, 29/08: «esses 15
  deveriam estar dentro dos 71 já que o COEP já resolveu»). Não estão dentro — são 15
  ativos **diferentes**, interseção zero com os 71, conferido. O que muda é a pergunta:
  **trabalho do COEP concluído = 86** (71 + 15), o escopo do posto, para cobrar o COEP; e
  **demanda encerrada = 71**, de ponta a ponta, para dizer o que o parque ganhou de volta.
  O painel mostra as duas, com o 86 como **recorte** por cima dos baldes — não soma com
  eles. Na cadeia dos 15 a SS do COEP foi repassada e fechada, o COCM devolveu, e a SS
  segue **aberta** na PROT/TELE/SE (1 a 41 dias lá).
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
  RD = execução; COEP = aquisição, salvo «Em logística» da carteira. **Por cima da
  esteira entram as decisões pontuais do gestor** (`DECISOES_DO_GESTOR` em
  `visao_consolidada.py`, com motivo e data): 26/08 devolveu três para aquisição —
  7908705049 (Artech sem suporte de instalação), 5836786094 (célula de 200 kVA para
  equipamento de 400) e 5800961074 (peças realocadas para os Muito Alta).
- **«Resolvido» não é «consertado» — separar pelo TIPOSS** (gestor, 29/08: «nem fudendo
  eu consertei 86 equipamentos»). Ele estava certo. Dos 143 que passaram pelo posto,
  **102 são INDISPONIBILIDADE PARA OPERAÇÃO** (saiu de operação) e **7 EM OPERAÇÃO COM
  ANOMALIA** (roda com defeito); os outros 32 são **obra de equipamento novo (13),
  comissionamento (9), solicitação de serviço (4), aviso de anomalia (4) e ajuste de
  proteção (2)** — não são falha. Nos 71 encerrados só **34** eram indisponibilidade, e
  destes **26 com SS atendida**; somando as **14 despachadas** com peça já trocada, a
  **troca confirmada do ano é 40**. `tipo_da_demanda.py` monta,
  `planilha_tipo_da_demanda.py` entrega em `dist/TIPO_DA_DEMANDA.xlsx`. **Régua**: o tipo do ativo é o da SS **mais pesada** que ele teve no COEP
  (indisponibilidade > anomalia > aviso > o resto); 9 ativos têm tipos misturados. As SS
  **ETO-COEP 00011/2023, 00013/2023 e 00063/2023 não estão na base de SS/OS** — o export
  só alcança 24 SS do COEP de 2023 —, então 7915029003 e 7923674004 ficam sem tipo.
- **O que não é manutenção sai da conta** — duas decisões do gestor em 29/08, na ordem
  em que vieram: «tipo de SS de obras novos equipamentos nem contabilizando deveriam
  estar» e «retira esses de ajuste de proteção e comissionamento». Instalar, energizar e
  ajustar não é consertar. Saem **25**: obra de equipamento novo (13), comissionamento (9),
  ajuste de proteção (2) e **aviso proteção & seletividade (1)** — «tem outro ajuste de
  proteção aí», que é proteção com outro nome. O filtro mora em
  `tipo_da_demanda.FORA_DA_CONTA` e `particao_coep.py` importa dele — mexer no conjunto
  refaz a partição inteira sozinha. **Passaram 143 pelo posto; a conta de manutenção é
  sobre 118**: **48 encerrados (32 RL + 16 RT) · 54 na fila · 14 despachados · 2 em
  execução**, trabalho do COEP concluído **62** e conta do posto **48 + 54 = 102**. Os 25
  continuam na planilha, marcados «Fora da conta». Seguem **dentro** da conta solicitação
  de serviço (4), aviso de anomalia (2) e anomalia em religador (1) — 7 que também não são
  falha, à espera da palavra do gestor.
- **O tipo mente no 7900001227 (Recursolândia)**: TIPOSS diz «aviso proteção &
  seletividade», mas o parecer mais recente da DMSL na ETO-COEP 00100/2025 diz **sensor
  interno de corrente com defeito, Cooper Form6 de 2009, obsoleto, com pedido de
  substituição ao DCMD**. Pelo texto é falha de equipamento; pelo tipo, não. Saiu da conta
  **pelo tipo** — a régua é o TIPOSS —, com a ressalva escrita na aba «Como foi feito».
- **Ativo nunca se repete** (gestor, 29/08). Conferido nas quatro listas: 143 ativos
  distintos em 143 linhas, baldes disjuntos, nenhum código em dois lugares. Equipamento
  que saiu de operação duas vezes no ano conta uma vez; a coluna «SS no COEP» diz quantas
  SS ele teve (vai até 5).
- **Primeiro ataque do DMSL não conta**: a demanda morreu na mão da DMSL.
- **Realizado do DCMD no ano (gestor, 26/08)**: SS **atendida** com equipe de campo na
  cadeia **+ cancelada que ficou de pé** (sem nota nova no COEP depois; nota pendente em
  outro posto não derruba). 2026: 18 + 45 = **63**. Atendida fechada só na TELE/PROT sem
  campo na cadeia é execução do DMSL/DEOP, fica fora (19 casos).
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
- **Códigos operativos, pela consulta SQL da base de repasses** (aba «SQL»): **79** e **78**
  religador (78 = monofásico), **58** regulador, **59 capacitor** e **BR reator**. A consulta
  monta os cinco e depois joga fora os dois últimos — `AND COD_ELE NOT IN ('59','BR')`. Para
  ter capacitor, é só tirar esse filtro: a base de SS/OS tem **242 SS de capacitor em 102
  ativos** (66 de indisponibilidade), e **nenhuma** de reator. A consulta também exclui o
  posto **ETO-CADTOC** (`DEPARTCODE <> 'ETO-CADTOC'`, 1.020 SS na base de SS/OS) e exige
  código com **10 dígitos**; a janela começa em 01/08/2020.
- **`NUM_OBRA` vem numérico com 9 dígitos** na base de SS/OS; o AIC guarda 10 com
  zero à esquerda. Sem `.zfill(10)` nenhuma obra casa.
- **Trafo auxiliar**: código com prefixo **51** (padrão) ou **57**, com os **8 dígitos
  finais iguais aos do equipamento pai** — mas **o padrão do código sozinho não prova**:
  os 3 últimos dígitos são a localidade, e em praça grande o miolo coincide por acaso.
  **Confirmar sempre pela COORDENADA**: no trafo auxiliar de verdade a distância até o
  pai é 0 a 4,5 m (mesma estrutura) e o alimentador é o mesmo. Dos 49 pais achados pelo
  padrão, **46 confirmam** (16 na coordenada exata, 30 a até 4,5 m) e **3 são falsos**:
  7900018004 (11,3 km e outro alimentador), 7900182004 (2,2 km, outro alimentador, e o
  ativo é poste) e 7900003060 (180 m — duvidoso). O texto confirma junto: das 64 SS, 48
  citam religador e 45 citam o código do pai («Trafo auxiliar do religador 7900388094»).
- **A base de repasses não traz 51/57** — a consulta dela só aceita 78/79/58. Na base de
  SS/OS há 16.151 códigos 51/57 de 10 dígitos (a maioria trafo de distribuição comum),
  dos quais **64 SS são trafo auxiliar, em 49 pais** (2024: 21 · 2025: 25 · 2026: 18);
  já sem os 3 falsos, **39 obras no AIC somam R$ 341.952 realizados**.
- **Projeto SIGCO certo**: 8495 para religador, 8481 para regulador. Trafo auxiliar
  acompanha o projeto do equipamento pai — **na teoria**: na prática as obras de trafo
  auxiliar caem no **61993** (18 das 41), no 8812 e no 8385. Quem filtra pelo projeto do
  equipamento não enxerga essas obras.

## Arquivos e ambiente

- **GESTÃO DE EQUIPAMENTOS: vale a de 27/08** («essa é a verdade a partir de hoje», gestor).
  Mesma estrutura da de 12/08; o que mudou foi a posição da carteira na aba 1007ALLan
  (SS aberta atualizada em 55 ativos + pareceres novos) — conferida contra a base:
  114 de 116 batem; as 2 diferenças são a cadeia andando depois de 20/08 (SE-PCM→TELE).
  **Armadilha**: na Planilha1 a coluna Criticidade foi sobrescrita por textos de parecer
  em 63 linhas — a criticidade ali se perdeu; a válida segue na aba de mapeamento da
  carteira (ATUALIZADA 16). O painel lê só BASE SS_OS, Planilha1 (modelo/status/valor),
  Plan1 e os dois cadastros de Ajustes — nenhuma dessas colunas mudou.

- **O AIC é um só**: `AIC_OBRAS_07082026.xlsx`, aba única «Export», 93 colunas,
  124.084 obras. `OBRAS_status_extracao_07082026.xlsx` é o mesmo arquivo (SHA-256
  idêntico), enviado com outro nome.
- **Orçamento** (tudo em `data/raw/realizado_capex_2026.json`, contas em
  `scripts/visao_orcamentaria.py`): orçado 2026 = **R$ 6.062.323,84** (8495 R$ 4,50 mi
  + 8481 R$ 1,57 mi). **O realizado é o total do Power BI — R$ 1.573.958,37 (25,96%)**,
  o 8481 somado ao 8495, jan–ago; saldo R$ 4.488.365,47. A coluna Realizado do quadro
  Orçamento 2026 (export de 21/08) traz R$ 1.365.345 — apuração mais atrasada, **não
  usar** (régua do gestor, 22/08). Do quadro vale só a coluna Orçado.
- **Valor de cada ativo, na ordem**: 1) a **obra do ativo no AIC** no projeto certo —
  realizado em quem já foi trocado, orçado da obra **aberta no ano** em quem ainda
  espera (obra velha pagou outra falha, não entra); 2) o valor orçado do ativo na
  planilha de indisponibilidade; 3) o médio, só em quem ainda vai custar.
- **A obra chega ao ativo por oito vias** (`visao_orcamentaria.py`): EMD (`m4_aic129`),
  planilha de EMD, `NUM_OBRA` da SS, número citado no texto do parecer, cadeia
  SS→OS→obra, **código do ativo na descrição da obra** (busca reversa no AIC — a que
  mais rende), **SS do trafo auxiliar** (`ss_trafo_auxiliar_93.py`; 51/57 + 8 finais —
  o recorte RL/RT não enxerga) e, por último, obra de substituição da mesma praça sem
  dono, marcada como **inferida**. Cruzar por OS não rende: o AIC quase não preenche
  `NUM_OS`. **SIGCO trocado não descarta obra** (RT no 8495, RL no 8481, troca no 8389);
  obra que cita outro código no texto, sim. Obra compartilhada tem valor **rateado**.
- **O preço é o valor médio por manutenção do gestor**: **RL R$ 58.543,21** e
  **RT R$ 167.280,98** (22/08). O médio por obra do AIC (RL R$ 39 mil, RT R$ 47,7 mil)
  **não serve de preço** — nem toda obra do projeto troca o equipamento inteiro; no RT,
  muitas trocam uma célula e não o banco de três. Fica só como referência.
- **Base de SS/OS crua**: texto com separador `@`, encoding latin-1, descrição quebrando
  linha — remontar registros. A mais nova é `data/raw/BASE_SS_OS_20082026.txt` (gitignored,
  36 MB; aberturas até 20/08). O recorte RL/RT sai por `scripts/extrai_ssos_min.py`.
- **Base nova de SS/OS → visão ETO**: largar `BASE_SS_OS_ddmmaaaa.txt` em `data/raw`
  (o `cadeia_obra.PARTES` escolhe a mais nova pela data do nome) e rodar
  `python3 scripts/atualiza_visao_eto.py` — extrai o recorte, refaz a visão ETO pela
  régua do gestor, a `dist/VISAO_ETO.xlsx` e o painel; falta só republicar o artifact
  do painel. A régua está escrita na home do painel («Como esta visão é montada») e na
  aba «Como foi feito» da planilha. A corrente NÃO refaz conta do posto, concluídos
  DCMD nem taxa de falha (essas são de `coep_2026.py`/`taxa_falha.py`).
- **O começo de registro não é o formato do posto**: o código varia (ETO-COEP, DOLP-RD-PA,
  ETO-CADTOC, ETO-TEC01, DMSLETO sem hífen). O que identifica é o `@` colado no ano
  (`\d{5}/\d{4}@`). Regex estreito engoliu 192 registros numa primeira versão.
- **O número no nome da carteira não versiona**: a «ATUALIZADA_3» de 22/08 é byte a byte a
  ATUALIZADA 16 (MD5 igual). Conferir hash antes de reprocessar.
- **`dist/` está no `.gitignore`** — planilhas vão por SendUserFile, não por commit.
- **LibreOffice não roda neste ambiente** — o Excel grava valores, não fórmulas.
- Playwright: `NODE_PATH=/opt/node22/lib/node_modules /opt/node22/bin/node`,
  `executablePath: '/opt/pw-browsers/chromium'`.

## A planilha base — o que os artifacts devem mostrar

**`GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP.xlsx`** (gestor, 27/08: «essa é a planilha base»)
é a consolidação de tudo e **define o conteúdo dos artifacts**. Dez abas, e a ordem
delas é a ordem da história:

| Aba | O que traz |
| --- | --- |
| **Gestão** | os 53 pendentes do DCMD com a **esteira de execução**: PMA → Entregue N1 → Gerado Obra → Gerado EMD → Entregue N3 → Concluído COCM → Cadastro → Estudo Proteção → Repassado DMSL → Comissionado. Mais orçamento MO/MAT/Total por ativo, dias pendente e Status Prazo |
| **Orçamento** | pivô por tipo e status: R$ 4,97 mi nos 53, e o painel do DCMD (backlog · saiu · entrou · pendente) contra os R$ 6,1 mi orçados |
| **Taxa de Falha** | pivô por ano, equipamento e **tensão** |
| **Falha Equipamentos** | o rol de causa raiz com citação, revisão, tensão e Concat |
| **Base** | a tabela mensal achatada de taxa (chave Concat) |
| **Resolvidos** | a dinâmica disjunta: 71 resolvidos · 54 na fila · 18 em outra mesa |
| **SLA por equipe** | o SLA de manutenção |
| **BASE SS_OS** · Planilha1 · Planilha2 | recorte e apoio de pivô |

**O Prontuário do COEP sai daqui** (`base_coep.py` extrai, `build_painel_coep.py` desenha):
a ordem das seções é a ordem das abas. Duas armadilhas achadas ao montar: na aba **Base**
as colunas de regulador estão vazias e a rotulada «Qtd RT 13» guarda o **parque 180** — o
mensal tem de sair da aba **Falha Equipamentos**; e nela o ano vem da **fatia** («RL 2025»),
não da coluna Ano, porque numa das 90 as duas discordam (7933585074, falha de 2025 com
ocorrência em 27/01/2026).

**A esteira da aba Gestão é a novidade que o painel ainda não mostra**: dez marcos por
ativo, do PMA ao comissionamento — hoje todos vazios, é o que o gestor vai preencher.
**Status** ali tem cinco valores (Avaliar compra 22 · Gerado PMA 20 · Em logística N1>N3
6 · Em execução 3 · Reforma 2) e **Criticidade tem «Falta definir»** (4 ativos), que é
diferente de «Sem classificação».

## Artifacts vivos

| Página | URL |
| --- | --- |
| **Prontuário do COEP** (da planilha base, 28/08) | https://claude.ai/code/artifact/cd7d36b6-9e66-4451-b663-13e3b4462e0e |
| **A apuração dos 143** (método e linha do tempo, 29/08) | https://claude.ai/code/artifact/299529d3-86f6-4623-9562-e4add456c6e8 |
| Painel de equipamentos especiais | https://claude.ai/code/artifact/d65c0278-32e4-47aa-815b-43abc992a630 |
| Dinâmica do posto | https://claude.ai/code/artifact/b4ef898c-efd8-4681-b996-2808001354ec |
| Taxa de falha | https://claude.ai/code/artifact/978e5138-959a-4290-b454-c83774129095 |
| Parque e falhas 2026 | https://claude.ai/code/artifact/1e03c93b-1b45-417b-8bd5-9f6fc7aa8709 |

Antes de republicar, **ler a versão que está no ar** (`action: "read"`) e conferir o
que muda — o publish é recusado se a versão viva não foi vista.
