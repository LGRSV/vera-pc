# Equipamentos Especiais — painel de indisponibilidade

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

- **Visão geral** — 129 equipamentos, distribuição por criticidade, categoria de defeito,
  regional, polo, responsável pela próxima ação e situação operacional em campo.
- **Equipamentos** — tabela filtrável com a ficha completa de cada ativo: a descrição
  integral da SS, a categorização do defeito, a especificação técnica, as coordenadas, a
  requisição de EMD e os itens de compra.
- **Parecer COEP** — o que já deveria estar concluído: SS de anos anteriores ainda abertas,
  prazo-limite do sistema estourado, previsões vencidas e SS fechadas com pendência aberta.
- **Cruzamento EMD** — divergências entre a planilha de requisição e a de criticidade.
- **Plano de Compras** — o pedido de 17/07/2026, os prazos contratuais (120 dias para
  religador, 180 para regulador) e a conferência contra as demais planilhas.
- **Mapa e frota** — localização geográfica dos equipamentos, marca e modelo do parque,
  idade das SS e a especificação técnica de cada ativo.
- **Metodologia** — de onde vem cada número e quais são os limites da análise.

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
