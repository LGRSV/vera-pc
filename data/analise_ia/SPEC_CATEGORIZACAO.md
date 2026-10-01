# Spec de categorização — Equipamentos Especiais (Religadores 79 / Reguladores de Tensão 58)

Contexto: base de equipamentos ESPECIAIS indisponíveis de uma distribuidora de energia no
Tocantins (ETO). Tipo `79` = religador automático. Tipo `58` = regulador de tensão (RT).
Cada linha tem uma SS (solicitação de serviço) aberta e um campo `descricao_ss` que
concatena, em texto livre e sem separadores confiáveis, três coisas:
  - o texto original de abertura da SS (relato do campo / COD / operação),
  - blocos que começam com `PARECER COEP:` (área de Engenharia de Operação/Proteção),
  - blocos que começam com `PARECER DMSL:` ou `FEEDBACK EQUIP. ESPECIAIS` (equipe de manutenção
    de subestações e equipamentos especiais, quem executa ensaios e laudos).

**DATA DE HOJE: 2026-08-12.** Use isso para julgar prazos vencidos.

## Sua tarefa
LEIA de verdade cada descrição, inteira. Não classifique por palavra-chave solta nem pelo
campo `defeito_planilha` (ele é resumido e às vezes diverge do texto — divergências são um
achado valioso, registre). Extraia o que realmente está escrito.

## Saída — um objeto JSON por registro, com estes campos

- `ativo` (string, copie exato)  — `ss` (string, copie exato)  — `linha` (int, copie exato)
- `categoria_primaria`: escolha UMA da lista fechada:
  `Tanque/Parte Ativa`, `Controle/Eletrônica`, `Célula de Potência`, `Comunicação/Telecom`,
  `Aterramento`, `Bateria/Fonte Auxiliar`, `Parametrização/Proteção`, `Transformador Auxiliar`,
  `Cabo/Conector/Umbilical`, `Estrutura/Instalação Civil`, `Vazamento de Óleo`,
  `Vandalismo/Furto`, `Descarga Atmosférica`, `Indefinido/Sem Diagnóstico`
- `categorias_secundarias`: lista (mesma lista fechada), vazia se não houver
- `componente_especifico`: string curta e concreta (ex.: "relé da fase C", "TP de medição",
  "placa de comunicação 3G", "malha de aterramento", "bucha polimérica"). "" se não disser.
- `fases_afetadas`: lista com "A","B","C" ou [] se não especificado
- `causa_raiz`: uma frase objetiva extraída do texto (não invente; se o texto não conclui, escreva
  "não conclusiva no texto")
- `status_operacional`: UM de `Fora de operação`, `By-passado em campo`, `Operando com restrição`,
  `Operando normal`, `Removido/Recolhido`, `Não informado`
- `acao_requerida`: uma frase — o que precisa acontecer para fechar (ex.: "substituir célula fase B",
  "retrofit para controle RUA", "aquisição de placa de comunicação")
- `responsavel_atual`: UM de `DMSL`, `COCM`, `COEP`, `Linha Viva`, `Empreiteira`, `Telecom`,
  `Suprimentos/Aquisição`, `Proteção`, `Não informado`
- `tem_parecer_dmsl` (bool), `tem_parecer_coep` (bool)
- `datas_citadas`: lista de objetos `{"data":"AAAA-MM-DD","o_que":"texto curto do compromisso"}`.
  Converta datas do formato brasileiro. Se o texto der só dia/mês, use o ano da SS.
- `prazo_vencido` (bool): TRUE se o texto promete/estipula uma entrega, prazo, previsão ou SLA
  cuja data já passou de 2026-08-12 e nada no registro indica conclusão. Seja rigoroso.
- `justificativa_prazo`: string curta explicando o `prazo_vencido` (ou "" se false)
- `pendencia_declarada`: string — a pendência explícita no texto (ex.: "pendente laudo da
  empreiteira", "aguardando chegada de cabos"). "" se não houver.
- `divergencia_planilha`: string — descreva se o texto contradiz `defeito_planilha`,
  `parecer_coep`, `check` ou `criticidade`. "" se coerente.
- `risco_operacional`: UM de `Crítico`, `Alto`, `Médio`, `Baixo` — seu julgamento técnico do
  risco de manter assim, considerando o que o texto diz sobre impacto (carga, clientes,
  período seco, proteção desabilitada, by-pass).
- `resumo_tecnico`: 1–2 frases, português claro, o que há de fato com o equipamento.
- `confianca`: `Alta`|`Média`|`Baixa` — quão bem o texto sustenta sua classificação.

## Regras
- Não invente fato que não esteja no texto. Se faltar, use "" / "Não informado" / [].
- Texto vem de planilha: pode ter acentuação quebrada, CAPS LOCK, repetição do mesmo parecer
  duas vezes, quebras coladas. Normalize ao interpretar.
- `by-passado`/`BAY PASSADO`/`bypass` ⇒ `By-passado em campo` (equipamento existe mas está
  curto-circuitado na rede — proteção/regulação perdida).
- "Em processo de aquisição" no parecer COEP ⇒ responsável `Suprimentos/Aquisição`, a menos que
  o texto diga outra coisa mais recente.
