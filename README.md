# Equipamentos Especiais — prontuário industrial

Site estático que consolida a situação dos religadores e reguladores de tensão
indisponíveis da ETO, cruzando quatro planilhas que hoje vivem separadas:

| Planilha | O que registra | Arquivo |
| --- | --- | --- |
| Relação dos Equipamentos Indisponíveis (aba *Criticidade por Equipamento*) | SS de campo, criticidade, parecer COEP e a descrição livre da SS | `data/raw/equipamentos_especiais.csv` |
| OBRAS_EQ_ESPECIAL | requisição de material (EMD), obra, depósito e entrega | `data/raw/obras_eq_especial.csv` |
| Plano de Compras MA+Alta | pedido de compra de 17/07/2026, material e valores | `data/raw/plano_compras.csv` |
| GESTÃO DE EQUIPAMENTOS | coordenadas, marca e modelo, ajustes de proteção, datas reais da SS e valor previsto | `data/raw/GESTAO_DE_EQUIPAMENTOS.xlsx` |

Posição de **12/08/2026**.

## O que o site mostra

A página abre numa única pergunta — a busca. Digitar filtra os 129 equipamentos por
qualquer campo (ativo, cidade, SS, defeito, marca, alimentador) e também encontra as
**coleções**: Conclusões, Parecer COEP, Cruzamento EMD, Plano de compras, Mapa e frota,
Visão geral e Metodologia. As pastilhas abaixo da busca filtram por situação (em aberto,
com pendência, com divergência, by-passado…) e por criticidade. Navegação completa por
teclado: `/` foca a busca, setas percorrem, Enter abre, Esc volta.

Cada equipamento abre numa página de leitura com a resposta à pergunta central — **está
concluído?** — seguida do defeito, especificação, SS no sistema, requisição, compras,
coordenadas e a descrição integral da SS.

## Como rodar

O site é HTML, CSS e JavaScript sem dependências, mas lê os dados por `fetch`, então
precisa ser servido por HTTP (abrir o `index.html` direto do disco não funciona):

```bash
python3 -m http.server 8000
# abrir http://localhost:8000
```

Para uma cópia autocontida — CSS, JavaScript e dados embutidos num único HTML que abre
direto do disco, sem servidor e sem nenhuma requisição de rede:

```bash
python3 scripts/build_single_file.py
# gera dist/equipamentos-especiais.html
```

## Como regerar os dados

Os JSONs em `data/` são gerados a partir dos CSVs em `data/raw/`. Nenhum número é
digitado à mão:

```bash
python3 scripts/build_data.py
```

O script valida a base antes de escrever e falha se encontrar ativo duplicado, ativo fora
do padrão de 10 dígitos, prefixo do ativo incompatível com o tipo, SS fora do padrão ou
descrição de SS sem categorização correspondente.

| Script | Responsabilidade |
| --- | --- |
| `scripts/build_data.py` | lê a planilha de criticidade, junta a categorização, valida e escreve os JSONs |
| `scripts/cruzamento_emd.py` | compara a planilha de EMD com a de criticidade |
| `scripts/plano_compras.py` | calcula os prazos do pedido e confere o plano contra as demais planilhas |
| `scripts/gestao_equipamentos.py` | lê a planilha de gestão: coordenadas, especificação e datas reais da SS |
| `scripts/build_single_file.py` | empacota o site num HTML autocontido |
| `scripts/baixar_fontes.py` | baixa as fontes do tema e as embute como data URI |

## Tema

O visual segue o tema **Prontuário Industrial** (`assets/TEMA.md`), criado com a skill
theme-factory: papel e tinta de impresso técnico, Barlow Condensed nos títulos, Spectral
na leitura e IBM Plex Mono nos dados. As fontes são embutidas em `assets/css/fontes.css`
(subset latino, woff2 em data URI), então o site continua sem nenhuma requisição externa.

## O que conta como concluído

Nada é dado como concluído por conta própria. A prova é a obra aparecer no **AIC como
encerrada**; enquanto o extrato do AIC não estiver em `data/raw/aic_obras.csv` (colunas
`ativo;obra;situacao;data_encerramento`, separador `;`), o contador de confirmadas fica em
zero e o resto é indício, pesado por fonte: SGM vale 4, EMD 3, Check e SS 2 cada, Parecer
COEP 1. Quando algo no mesmo registro desmente o indício — Check pendente, SS ainda aberta,
prazo estourado — ele vira *contestado* em vez de somar. Hoje: 0 confirmadas, 19 com
indício forte, 14 contestadas, 8 isoladas, 88 sem indício. Nenhuma das SS tem data de
término no SGM.

## Faixa de potência e classe de tensão

A **faixa de potência** vale só para os reguladores de tensão, que são os que têm capacidade
em kvar na planilha de gestão — 12 até 200 kvar, 4 entre 201 e 300, 13 entre 301 e 400. O campo
aceita um valor único ou um por fase; bancos montados com células de capacidades diferentes
ficam marcados como *banco misto*, porque não cabem numa faixa só.

Os religadores não têm kvar registrado. Para eles a dimensão comparável é a **classe de
tensão** — 99 equipamentos em 34,5 kV e 28 em 13,8 kV —, que o console também mostra e filtra.

## Atualização automática

Uma Rotina semanal (segundas, 7h de Brasília) atualiza a data de referência, roda o build,
regera o arquivo único e faz push na mesma branch. Como todos os prazos são calculados contra
`DATA_REF`, os atrasos ficam corretos sem intervenção manual.

Para atualizar a posição da análise, altere `DATA_REF` em `scripts/build_data.py`
(e, se o pedido de compra mudar, `DATA_PEDIDO` em `scripts/plano_compras.py`) e rode o
build de novo.

## Como as descrições de SS foram categorizadas

O campo *Descrição SS* é texto livre e concentra três vozes coladas sem separador: o
relato de abertura, os blocos `PARECER COEP:` e os blocos `PARECER DMSL:` /
`FEEDBACK EQUIP. ESPECIAIS`. São 92 descrições, várias com mais de mil caracteres.

Elas foram divididas em 10 lotes e lidas integralmente, uma a uma, por 10 analistas em
paralelo, todos com a mesma especificação de saída — `data/analise_ia/SPEC_CATEGORIZACAO.md`.
Cada descrição rendeu categoria do defeito, componente, fases afetadas, causa raiz,
situação operacional, ação necessária, responsável, datas prometidas e a divergência entre
o texto e os campos estruturados da planilha. Os resultados brutos estão em
`data/analise_ia/result_*.json` e são reprocessados pelo build.

## Limites conhecidos

- As previsões da coluna *Observação* não trazem ano; datas de meses já passados foram
  lidas como do ano corrente, o que pode subestimar atrasos de itens mais antigos.
- O tempo em aberto das SS usa a data real de abertura quando a planilha de gestão a traz
  (70 dos 129 equipamentos). Nos demais, é contado pelo piso — a partir de 31/12 do ano da SS.
- As coordenadas vêm em SIRGAS 2000 / UTM 22S, inclusive os pontos a leste do limite da zona,
  que a distribuidora mantém na mesma projeção. A conversão para latitude e longitude é feita
  no build, em Python puro.
- Só a aba *Criticidade por Equipamento* foi recebida da planilha de indisponíveis. As
  abas de concluídas pelo DMSL não estavam no arquivo, então o casamento com o EMD foi
  feito pelo **código do ativo** — o que cobriu as 36 linhas do EMD.
- As divergências apontadas são indícios para verificação com as áreas, não conclusões
  administrativas.
