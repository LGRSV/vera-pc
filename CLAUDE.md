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
- **A série do ano é UMA conta só, cortada no meio** (gestor, 02/09, dito duas vezes): o
  apurado de jan–ago **tem de bater com os números de setembro em diante**. O que fecha
  agosto é o que abre setembro. Por isso a premissa de set–dez foi reancorada no estoque
  apurado; número novo que chegar para set–dez tem de fechar contra o saldo de agosto, e
  se não fechar é sinal de que as duas metades estão em réguas diferentes.
- **Banco de capacitor entra nas contas** (gestor, 02/09: «tem que ter a visão de BC, que
  começa com código operativo 59»). Ele nunca aparecia porque a consulta da base de repasse
  o descarta (`AND COD_ELE NOT IN ('59','BR')`) — só sai indo direto na base de SS/OS.
  `data/missao/ssos_bc.json` (gerado com o remontador de `extrai_ssos_min.py` e o regex
  `59\d{8}$`): **242 SS em 102 ativos**, aberturas de 03/01/2024 a **22/08/2026** — dois
  dias além do RL/RT, então a posição do recorte inteiro passa a ser 22/08. Backlog de BC
  pela régua de indisponibilidade: **23 · 23 · 22 · 20 · 20 · 16 · 16 · 16 · 13** (início do
  ano a agosto). Com BC o backlog do parque vai de 93 para **106**; o 93 do gestor é RL+RT.
  Cuidado: BC com **qualquer** SS pendente são 52, e só 13 são de indisponibilidade — a
  carteira do gestor traz 23 BC, que é outra régua.
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
- **LibreOffice não roda neste ambiente**: o binário existe (`/usr/bin/soffice` 24.2.7.2) mas
  recusa qualquer xlsx, inclusive um mínimo do openpyxl e um gravado pelo Excel. Para ver
  um gráfico, renderizar SVG por Playwright. O Excel grava valores, não fórmulas.
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

- **Taxa de falha POR PEÇA** (`taxa_por_peca.py` → `dist/TAXA_POR_PECA.xlsx`, 31/08). O rol
  de falhas dá SS, ativo, tensão e peça; o que falta vem dos **ajustes da proteção** em
  `GESTAO_DE_EQUIPAMENTOS.xlsx`: a aba **Ajustes Reguladores de Tensão** (426 linhas) traz
  POTÊNCIA e CONTROLADOR do RT, e **Ajustes RL Poste** (1.292) traz TENSÃO e RELÉ do RL.
  Casam 27/27 RT e 62/63 RL — o único de fora, 7930359149 (Caseara), é o mesmo que tem
  tensão «#N/A» no rol; fica **inferido** em 34,5 pelos seis vizinhos da praça.
  **O sinal está no modelo, não na peça**: 25 das 26 falhas de tanque são NOJA RC10, mas
  isso é volume — ele é 78,6% do parque e tem índice **0,88**, abaixo da média. Quem falha
  acima é o **COOPER F6: 10,3% do parque, 22,6% das falhas, índice 2,19** — o mesmo modelo
  que a DMSL chama de obsoleto no 7900001227. ARTECHE P500 (5 unidades) e TAVRIDA (27) dão
  índice alto com amostra pequena demais.
- **A taxa por CLASSE, não pelo tipo inteiro** (aba «Taxa por classe»): a classe de
  potência e a faixa de tensão só existem nos ajustes, então o denominador é o parque
  **desses cadastros** — 190 RT e 1.292 RL, não os 207 e 1.307 oficiais. Parque de RT por
  potência: **167 → 25 · 200 → 67 · 400 → 98**. Parque de RL por tensão: **13,8 → 460 ·
  34,5 → 832**. **A célula de 200 kVA falha 2,5× mais**: 7 falhas em 67 (10,4%) contra 4
  em 98 na de 400 (4,1%) e 1 em 25 na de 167 (4,0%, amostra pequena). No religador, o
  **34,5 kV falha 1,6× mais** que o 13,8 (5,7% contra 3,5%).
- **Duas ressalvas do rol de falhas**, registradas na aba «Alertas»: a **potência** de 4
  reguladores está fora das três classes que o gestor reconhece (398 → é 400; 239 em dois
  e 250 em um — e 250 kVA é rating padrão de 13,8 kV, então pode ser a régua que está
  incompleta, não o cadastro); e **3 ativos se repetem no mesmo ano** — 7908708116 na
  MESMA SS com tanque e controle, 5841308190 com dois furtos e 5854566043 com duas
  células. Por peça as 90 linhas contam; por equipamento seriam **87**.

- **A planilha automática** (`planilha_automatica.py` → `dist/GESTAO_AUTOMATICA.xlsx`, 01–02/09;
  `confere_planilha_automatica.py` calcula as fórmulas com a biblioteca `formulas` — pip — e
  checa 112 pontos, inclusive seis cenários de borda numa cópia). Pedido do gestor, como foi dito:
  «se eu selecionar que o defeito é o Tanque ele já traz Tanque da 34,5 Noja Código 69001
  (exemplo, não me recordo se é isso mesmo); se eu disser que é uma célula de 400 kVA 90.000,
  se for 2, 180.000, usando valores reais» — com os reais: tanque 34,5 é o **690005** e a célula
  de 400 é a **690241 a R$ 90.230** (duas, 180.460). A planilha base faz isso com **XLOOKUP em
  dois arquivos externos** (carteira do SharePoint: aba «Criticidade por Equipamento», colunas AS
  «RL Auto», AT «Valor Material», AU «Valor mão de obra estimado»; e GESTÃO DE EQUIPAMENTOS.xlsx
  para a tensão) — fora da rede ficam só os valores em cache, que estão em
  `xl/externalLinks/externalLink1.xml` dentro do xlsx. A automática é autocontida: **Catálogo**
  (chave `Tipo|Peça|Tensão|kVA`; kVA só na célula e no RT completo; completos em fórmula sobre as
  peças), **Cadastro** (1.292 RL + 189 RT dos ajustes, mais 7930359149 com tensão pelo alimentador
  LD03414149), **Lançamento** (300 linhas: ativo → peça em lista dependente do tipo via
  `INDIRECT("Pecas_"&tipo)` → qtd; colunas manuais de tensão e potência mandam sobre o cadastro),
  **Gestão** (53, «Bate?» 53 de 53 contra a carteira) e **Falha Equipamentos** (90; furto orçado
  pela carteira só na falha mais recente do ativo — 5836786094 célula ×1, 5856070091/5856156091/
  5858783119 completo —, o resto em branco «definir»). **Preço: vale a carteira de 27/08**; onde
  ela não tem linha, «Premissas e Preços» do ORCAMENTO_EQ_ESPECIAIS (16/07). No RL as três fontes
  batem no centavo (690001 tanque 13,8 R$ 21.785,72 · 690005 tanque 34,5 R$ 38.151,48 · 690916
  controle 13,8 R$ 33.816,82 · 692263 controle 34,5 R$ 38.094,72; MO 11.016,94 / 13.209,34). **No
  RT a carteira é mais barata que o orçamento**: célula 400 (690241) R$ 90.230 contra 126.893,80;
  célula 200 em 34,5 (690240) 51.705,75 contra 57.720,41; célula «200» em 13,8 = **690236, que o
  orçamento chama de 239 kVA**, 62.113,20 contra 61.098,29; controle (651638) 23.259,60 + MO
  20.000 contra 29.445,39 + 0; célula 167 (690669) só no orçamento, R$ 27.616,62; MO de célula
  51.402,14 (13,8) / 80.318,50 (34,5); **RT completo 400 = 293.949,60 (= 3 × 90.230 + 23.259,60)
  + MO 200.637, que é 2 × (80.318,50 + 20.000)** — essa regra vale para as outras classes, a
  confirmar. **Só quatro códigos de célula** (690669, 690236, 690240, 690241); a classe é a do
  gestor (167/200/400): 398 → 400, 239 e 250 → 200, com aviso; 300 e 667 são os desvios graves.
  Mão de obra é por serviço, uma vez por linha. A auditoria por workflow (4 lentes + 2 céticos por
  achado, 02/09) confirmou e o script corrigiu: tensão manual virava número e apagava a MO
  (formato `@` + `&""`); INDEX em célula vazia dá **0** (usar `T(INDEX(...))`); furto ×3 era chute;
  completos eram constantes; intervalos fixos (agora 3.000/200/1.000); ativo fora do cadastro e
  prefixo 59 sem mensagem; sem cache de valores a planilha abre em branco no Modo Protegido —
  `grava_cache()` calcula com `formulas` e injeta `<v>` no XML. **Armadilhas do openpyxl** achadas
  aqui: `formula1` da validação vai **sem o «=»** e precisa de `showErrorMessage=True`; lista com
  «13,8» tem de ser intervalo (a vírgula separa itens); regravar a planilha base com openpyxl
  perde o gráfico da aba SLA — por isso a automática é arquivo à parte, com instrução de mover as
  abas. O que fica para o gestor decidir: a MO do RT completo fora de 400/34,5; 5841308190 (dois
  furtos sem orçamento); 7947203070 (controle no rol, completo na carteira).

- **O quadro da premissa set–dez em gráficos** (`painel_premissa_setdez.py` →
  `dist/PAINEL_PREMISSA_SETDEZ.xlsx`, 02/09). O gestor mandou o quadro **sem rótulo de
  coluna** — backlog 100 fixo · entrante 8·5·4·6 · resolvidos acumulados 6·35·57·77 ·
  pendentes 102·70·47·29 · orçado 5.206.065,02 → 6.062.323,84 · forecast 2.129.866,67 →
  6.058.299,31. **As colunas são setembro a dezembro de 2026**, provado no centavo pela
  planilha base: o primeiro forecast é o realizado de jan–ago (R$ 1.605.280,07, soma
  acumulada da aba **Apresentação**) + o desembolso de setembro da premissa da aba
  Orçamento (R$ 524.586,60); o último é a soma acumulada de tudo na Apresentação
  (R$ 6.058.299,32), **R$ 4.024,53 abaixo do orçado** — a mesma diferença que a
  Apresentação guarda em G8. **PENDENTES = BACKLOG + ENTRANTE − RESOLVIDOS**, coluna a
  coluna, reproduz os quatro números exato — mas resolvidos é acumulado e entrante é do
  mês, então os entrantes de meses anteriores somem da conta; acumulando-os a série vira
  **102 · 78 · 60 · 46** (dezembro 17 acima). Idem o desembolso de setembro, que carrega o
  ano inteiro. As duas ressalvas estão na aba «Como ler» e a segunda leitura tem aba
  própria. Oito abas de gráfico, todas lendo a aba **Dados** (mudou lá, mudou o gráfico),
  com `grava_cache()` de `planilha_automatica` para não abrir em branco.
  **Régua de gráfico** (skill dataviz): par **#1f7c50 verde / #b8480c laranja** aprovado no
  validador sobre `#fbfaf6` (deuteranopia ΔE 8,9 · visão normal 22,9 · contraste ≥ 3:1) —
  ocre `#996c15` **reprova** contra o laranja (ΔE 1,4 deutan) e grafite `#6d675a` não tem
  croma para ser categórico, só serve de neutro; **nunca dois eixos Y** (grandeza diferente
  = gráfico separado); legenda sempre que houver 2 séries. **Armadilhas do openpyxl em
  gráfico**: com `from_rows=True, titles_from_data=True` o título da série vem da **coluna
  A de cada linha**, então a linha de categorias **não pode entrar** no `Reference` (entra
  como série fantasma); combinar `BarChart += LineChart` **sem** mexer em `axId` mantém
  eixo único (mexer cria o segundo eixo); cascata se faz com série-base `noFill` + `dPt`
  por ponto; e o **código de formato é sempre em convenção US** — `0.0%` e `R$ #,##0.00`,
  nunca `0,0%` (a vírgula ali é separador de milhar). **`set_categories` com rótulo de
  TEXTO grava `numRef` e o Excel mostra 1·2·3·4 no lugar dos meses** — tem de ser
  `ser.cat = AxDataSource(strRef=StrRef("'Aba'!$B$4:$E$4"))`, aplicado em cada série de
  cada sub-gráfico de `ch._charts`; e o `axPos` sai `l` nos dois eixos, então acertar
  `x_axis.axPos = "b"` na mão. Gráfico só na segunda aba passa despercebido — repetir um
  na primeira. **Conferência de gráfico**: LibreOffice está instalado (`/usr/bin/soffice`,
  24.2.7.2) mas **não carrega xlsx nenhum** neste ambiente, nem um mínimo do openpyxl nem
  um gravado pelo Excel («source file could not be loaded», mesmo com
  `-env:UserInstallation` próprio) — não serve para renderizar. Matplotlib também não está
  instalado. O caminho que funciona é **SVG em HTML renderizado pelo Playwright/Chromium**
  (`scratchpad/previa.py` + screenshot), que serve de prévia visual para o gestor conferir
  sem abrir o Excel.

- **O backlog mês a mês** (`backlog_mensal.py` → `dist/BACKLOG_MENSAL_2026.xlsx` e
  `data/missao/backlog_mensal.json`, 02/09). Backlog é **estoque**: quantos RL/RT estavam com
  demanda aberta no fim de cada mês. **A régua é a da visão ETO** — ativo 58/79 com SS de
  INDISPONIBILIDADE PARA OPERAÇÃO em aberto —, e a série **fecha em 93 na posição da base**,
  o mesmo 93 que o gestor deu em 22/08: é âncora, não calibração. Série 2026: **início 70 ·
  jan 83 · fev 77 · mar 85 · abr 88 · mai 79 · jun 84 · jul 87 · ago 93**; no ano entraram
  269 e saíram 246 — quase empate, e é por isso que a fila não cede. **RL oscila 63–73; RT
  sobe de 14 para 22.** A fila **rejuvenesce**: herdados de 2025 ou antes caem de 60 para 21
  e a idade mediana de 150 para 72 dias (a mais velha, 905 dias). Pela régua larga
  (indisponibilidade + anomalia) vai de 120 a 104.
  **Como a demanda é montada**: abre na abertura da primeira SS, fecha na saída da última;
  a saída é a conclusão, senão a abertura da SS seguinte do mesmo ativo, senão segue aberta.
  **A exceção que decide o número**: SS REPASSADA **sem nenhuma SS seguinte no recorte** sai
  do registro na data em que foi aberta (145 casos) — tratá-las como abertas para sempre
  levaria o estoque de 93 para **217** e nada bateria com o gestor. **Fronteira do mês** que
  faz o saldo fechar nos oito meses (`assert` no script): estoque no fim = `abertura <= último
  dia < saída`; entradas e saídas = datas dentro do mês. Medir o estoque no dia 1º do mês
  seguinte quebra a conta (demanda que abre naquele dia entra sem ser entrada).
  **Horizonte**: `BASE_SS_OS_20082026.txt` tem aberturas até 20/08 e **fechamentos até 21/08**
  — a posição é 21/08/2026 e agosto é mês parcial. Para chegar a hoje: base nova em
  `data/raw` → `extrai_ssos_min.py` → `backlog_mensal.py`. O recorte `data/missao/ssos_min.json`
  tem 6.362 SS (2024–2026). **Não confundir** com a fila do posto do COEP (`curva_mensal` de
  `coep_2026.json`, 42–54), que é outro recorte e vai numa aba à parte para comparar.

- **O ano de 2026 na visão DCMD, de ponta a ponta** (`ano_dcmd.py` → `dist/ANO_DCMD_2026.xlsx`
  e `data/missao/ano_dcmd.json`, 02/09). Correção do gestor: **o quadro de set–dez é visão
  DCMD**, não a visão ETO, e nela «resolvemos 71 até agosto». **O backlog de 100 do quadro é
  número redondo de referência** (gestor, 02/09), não estoque apurado — o apurado no fim de
  agosto é **72** (54 na fila do posto + 18 em outra mesa, que a partição reparte em 15
  despachados + 3 em execução). **Reancorando a premissa dele no 72, dezembro fecha em 18, não
  em 29**; a diferença de 28 anda junto o ano todo (set 74×102 · out 50×70 · nov 32×47 ·
  dez 18×29). Série apurada: herdados 50 → jan 52 · fev 56 · mar 63 · abr 73 · mai 68 · jun 70
  · jul 77 · ago 72; entradas 6·5·11·12·6·31·21·1 (93) e **os 71 resolvidos mensalizados:
  4·1·4·2·11·29·14·6** (45 RL + 26 RT; junho sozinho faz 29). **O ritmo da premissa é o dobro
  do realizado**: jan–ago resolveu 8,9/mês e recebeu 11,6; set–dez promete resolver 19,2/mês
  e receber 5,8. Dezembro em quatro cenários, todos partindo de 72: premissa **18** · entrada
  no ritmo real **41** · resolução no ritmo real **59** · tudo no ritmo real **82**.
  **Armadilha**: 2 ativos (7921040031, 7955430075) têm `data_do_fechamento` **anterior** à
  `primeira_chegada` — travar a saída na data de entrada, senão o saldo não fecha e a série
  point-in-time discorda da corrente. Posição do apurado: **18/08/2026** (`coep_2026.json`),
  agosto parcial. **Não confundir com `BACKLOG_MENSAL_2026.xlsx`** (visão ETO, todo RL/RT com
  indisponibilidade aberta, 93 no fecho da base): recorte mais largo, outra pergunta.

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
