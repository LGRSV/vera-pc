# A régua do gestor do ETO-COEP

Quem decide o que conta é o gestor do posto. Estas são as decisões dele, com data.

## O que é falha (21/08/2026)

Só conta como **falha** o que exigiu **peça grande**:

- **Religador** — controle, tanque/parte ativa, ou o equipamento completo.
- **Regulador** — célula, relé, o banco completo, ou furto.

**Sinônimos de controle, que contam**: placa de alimentação CA, relé de sincronismo,
armário de controle, retrofit.

**Não contam, é telecom**: placa de comunicação, placa 3G, rádio, antena.

> O que decide é a **peça**, não a palavra «placa» nem a palavra «relé».

Furto é decidido **pela peça, não pela causa**: furto de trafo auxiliar não conta; furto
que levou célula ou o equipamento, conta.

## Como se conta

- **Equipamento, não ocorrência.** Ativo que falhou duas vezes no mesmo ano conta uma vez
  naquele ano — e conta de novo se falhar em outro ano.
- **O ano é o da data de ocorrência**, nunca o da abertura da SS. A abertura vem em média
  39 dias depois do fato e em 9,8% dos casos cai em outro ano.
- **Repasse não é falha nova.** O SGM abre SS nova a cada passagem de posto; a cadeia
  inteira é uma falha só.
- **Regulador é banco de três células.** O parque conta banco, não célula; falha de uma
  célula é uma falha do banco.
- **Objeto do fato** — a SS pendura no código do religador porque ele é o marco do
  trecho, mas o fato pode ser do poste, da cruzeta, da vegetação. Sem separar, a taxa do
  ativo vira taxa do alimentador.

## A taxonomia completa — 22 rótulos em 5 classes

Um rótulo por demanda, o do motivo dela. Outros itens citados vão em `tambem`.

### PEÇA GRANDE — o equipamento em si, a régua que entra na taxa
| rótulo | quando |
| --- | --- |
| `tanque` | o texto nomeia tanque, parte ativa, câmara de interrupção ou bucha do RELIGADOR |
| `controle` | o texto nomeia controle, armário de controle, placa de alimentação CA, fonte, relé de sincronismo ou retrofit do RELIGADOR |
| `celula` | o texto nomeia a célula, ou o tanque de UMA FASE, do REGULADOR |
| `rele` | o texto nomeia o relé do REGULADOR |
| `completo` | o texto pede o equipamento inteiro, ou tanque E controle juntos, ou o banco de três células |
| `furto` | furto ou vandalismo de qualquer item — diga qual no campo `item` |

### APOIO — componentes que ficam junto do equipamento
`trafo auxiliar` · `chave faca` (chave, seccionadora, chave de saída, bypass) ·
`para-raio` · `fusivel` · `bateria` (inclui carregador) · `cabo` (cabo, conector, jumper,
emenda, ponto quente) · `aterramento` (malha, haste) · `telecom` (rádio, antena, placa de
comunicação, placa 3G, SCADA, automação, firmware, perda de comunicação, comando remoto)

### FATO DE TERCEIRO — o equipamento não tinha defeito
`poste` (poste, cruzeta, estrutura, base) · `poda` (vegetação, árvore)

### NÃO É MANUTENÇÃO CORRETIVA
`ajuste de protecao` · `comissionamento` · `obra nova` (instalação, energização,
remanejamento, recodificação) · `melhoria`

### NADA APURADO
`sem defeito` (primeiro ataque sem achado, equipamento normalizado, limpeza, ninho de
inseto, SS duplicada ou cancelada sem defeito descrito) · `nao identificado` (o texto não
permite dizer qual item era)

## Onde caem os casos que mais confundem

| o texto diz | o rótulo é | por quê |
| --- | --- | --- |
| «disjuntor», «disjuntor CA», «disjuntor de alimentação», «DJ» | `chave faca`, `cabo` ou `nao identificado` | disjuntor não é tanque nem controle |
| «não fecha», «não aceita comando», «bloqueado», «em bypass», «display apagado» | `nao identificado` | sintoma sem peça nomeada |
| «não comunica», «sem SCADA», «não responde remoto» | `telecom` | remoto é comunicação |
| «DPS queimado» | `para-raio` | DPS é para-raio |
| relé de proteção de RELIGADOR | `controle` | o rótulo `rele` é só de regulador |
| célula ou tanque de fase de REGULADOR | `celula` | o rótulo `tanque` é só de religador |
| ninho de abelha ou formiga no armário | `sem defeito` | limpeza, não troca |
