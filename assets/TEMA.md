# Prontuário Industrial

Tema criado com a skill theme-factory para o site de Equipamentos Especiais.
A referência não é interface de software: é o impresso técnico de campo — a folha de
inspeção, o prontuário de subestação, o relatório datilografado com carimbo. Papel, tinta,
filete duplo e leader pontilhado ligando rótulo a valor, como em formulário impresso.

## Palette

- **Papel** `#f2efe6` — fundo, um creme de papel técnico envelhecido
- **Papel sombreado** `#e9e5d8` — campos de formulário e faixas
- **Tinta** `#211d15` — texto, um preto quente de fita de máquina
- **Tinta média** `#57513f` — texto secundário
- **Tinta apagada** `#8d8672` — anotações e rótulos
- **Laranja-sinal** `#bc4b0e` — o laranja de placa de segurança elétrica; ação e destaque
- **Vermelho de carimbo** `#a33327` — criticidade muito alta, pendência
- **Ocre** `#996c15` — criticidade alta / atenção
- **Oliva** `#75681a` — criticidade média
- **Verde-campo** `#3e6b4c` — criticidade baixa, concluído
- **Grafite** `#6d675a` — sem classificação, neutro

Modo escuro: quadro-negro de sala de operação — fundo `#191713`, papel invertido em giz
`#e8e3d4`, mesmos acentos clareados um ponto.

## Typography

- **Títulos e rótulos**: *Barlow Condensed* (600/700), sempre em caixa alta com
  tracking largo — a letra condensada de placa industrial e desenho DIN, nada de
  grotesca genérica de interface.
- **Leitura**: *Spectral* (400/600, com itálico) — serifa de texto desenhada para tela,
  voz de relatório impresso.
- **Dados**: *IBM Plex Mono* (400/600) — códigos de ativo, números de SS, valores e
  datas, como saída de terminal ou máquina de escrever.

As três famílias são embutidas na página como data URI (subset latino), então o site
continua autocontido: nenhuma requisição externa, nem para fontes.

## Visual identity

Formulário impresso, não dashboard: filete duplo sob o cabeçalho, leaders pontilhados
entre rótulo e valor, etiquetas com borda dura como carimbo, cantos retos em tudo.
A cor é sinal — aparece na criticidade, no atraso e no laranja de destaque; o resto da
página é papel e tinta.
