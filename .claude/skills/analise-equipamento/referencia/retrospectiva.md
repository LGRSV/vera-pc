# Retrospectiva — o que foi feito com o equipamento, quando, e se foi atendido de verdade

Variante da análise para a pergunta do gestor (01/10/2026): **«o que melhorou a partir de abril
de 2026, mês a mês»** — lendo a cadeia real de cada demanda, não só os pareceres do COEP, e
verificando se o equipamento foi **atendido mesmo**. Muitas demandas são **backlog de 2025** que
só tiveram tratativa em 2026: isso tem de aparecer.

A régua de peça (`regua.md`) e as armadilhas (`armadilhas.md`) continuam valendo. Este arquivo
diz o que muda.

## Como ler as datas do dossiê

- **«chegou»** é quando a SS chegou ao posto (o repasse da SS anterior). **«saiu»** é o repasse
  (data e hora exatas), o cancelamento ou o atendimento (data de conclusão).
- **O export do SGM sobrescreve a abertura da SS repassada com o instante do repasse.** O dossiê
  já corrige isso. Não use o número da SS para datar nada: «ETO-COEP 149/2025» pode ter saído do
  COEP em 2026 — o número diz quando ela nasceu, a saída diz quando foi mexida.
- **«TEXTO NOVO DESTA SS»** é o que a SS acrescentou à anterior: foi escrito entre a chegada e a
  saída dela. O parecer de repasse é escrito **na saída** — então um texto novo numa SS
  REPASSADA tem, no mais tardar, a data do repasse.
- **«export»**: o texto que a SS ganhou entre 19/08 e 23/09/2026 foi escrito nesse intervalo; o
  que não estava no export de 11/07/2025 foi escrito depois dele.
- **Cancelamento** tem data e hora exatas, e o dossiê diz quantas SS de RL/RT foram canceladas no
  mesmo dia — muitas no mesmo dia, em vários postos, é limpeza em bloco, não conserto.
- **Data escrita no texto** («10/07 PARECER COEP», «DMSL 16/07») manda sobre as outras quando
  cabe na janela da SS. Sem ano, o ano é o que cabe na janela.

**Toda tratativa leva a data e COMO foi datada**: `escrita no texto` · `repasse (SGM)` ·
`cancelamento (SGM)` · `conclusão (SGM)` · `entre exports` · `janela da SS`.

## ANALISTA — o que devolver, por ativo (um `put` por ativo, na hora)

```json
{
 "ativo": "7908686014", "familia": "RL",
 "demandas": [{
   "cadeia": "ETO-TELE 867/2024",
   "aberta_em": "15/10/2024",
   "o_que_era": "tanque",                 // rótulo da régua (22), pelo texto mais recente
   "backlog_2025": true,                  // aberta antes de 2026 e ainda aberta em 01/01/2026
   "tratada_em_2025": false,              // houve tratativa REAL em 2025 (parecer, despacho, material, campo)?
   "o_que_houve_em_2025": "ficou 484 dias no COEP sem parecer",
   "tratativas": [                        // de 01/04/2026 a 23/09/2026, em ordem; mais a última antes de abril, com "antes": true
     {"data": "23/04/2026", "como_datou": "repasse (SGM)", "quem": "COEP",
      "acao": "despacho ao campo", "resumo": "COEP manda a SS para o COCM de Paraíso",
      "evidencia": "SGM: ETO-COEP 174/2024 repassada em 23/04/2026 17:00 para ETO-RD-PS"},
     {"data": "24/07/2026", "como_datou": "escrita no texto", "quem": "COCM",
      "acao": "execução em campo", "resumo": "COCM troca o religador",
      "evidencia": "24/07 PARECER COCM: EQUIPAMENTO FOI SUBSTITUIDO OBRA 0212600425"}
   ],
   "executada": true,                     // serviço que resolve a demanda foi FEITO — só com prova literal
   "data_execucao": "24/07/2026", "como_datou_execucao": "escrita no texto",
   "prova_execucao": "24/07 PARECER COCM: EQUIPAMENTO FOI SUBSTITUIDO OBRA 0212600425",
   "voltou_a_operar": null,               // true / false / null (o texto não diz)
   "prova_operacao": "",
   "desfecho": "executado, falta comissionar ou ajustar",
   "data_desfecho": "24/07/2026",
   "pendencia_restante": "ajuste da PROT (SS pendente desde 28/07)",
   "confianca": "alta", "motivo": "uma frase"
 }]
}
```

**`tratada_em_2025`** é `true` só se, **depois do diagnóstico que abriu a demanda**, houve em 2025
alguma ação para resolvê-la: parecer do COEP com decisão (compra, despacho com material,
remanejamento), compra ou entrega de material, despacho ao campo pedindo a execução, nova ida a
campo, ou a execução. **O diagnóstico da DMSL que gerou a demanda não conta, e repasse sem texto
não conta.** É isso que separa o backlog que andou em 2025 do que só foi tratado em 2026.

**Cadeia ainda aberta em 23/09**: se o serviço foi feito e a operação depois dele está provada,
é `atendido` mesmo com SS administrativa aberta — escreva a SS aberta em `pendencia_restante`. Sem
prova de operação e com SS aberta na PROT/TELE/SE, é `executado, falta comissionar ou ajustar`.

**`acao`** — uma destas: `despacho ao campo` · `material: compra ou aquisição` ·
`material: entrega ou logística` · `material: remanejamento` · `pergunta ao campo` ·
`cobrança de prazo ou de registro` · `triagem: repasse ao posto certo` · `cancelamento` ·
`execução em campo` · `diagnóstico ou visita sem troca` · `comissionamento ou ajuste` ·
`confirmação de operação` · `devolução ao COEP` · `outro`.

**`quem`** — `COEP` · `COCM` (equipes RD) · `DMSL/TELE` · `PROT` · `SE` · `COI/operação` · `outro`.
«PARECER DCMD» é usado pelos COCMs para relatar serviço: julgue pelo conteúdo.

**`desfecho`** na posição de 23/09/2026 — um destes:

| desfecho | quando |
| --- | --- |
| `atendido` | serviço feito **e** prova de que o equipamento opera (laudo, «ficou em operação? sim», comissionado, COI/SCADA confirmando depois do serviço) |
| `executado, falta comissionar ou ajustar` | serviço feito com prova, e a cadeia segue na PROT/TELE/SE ou o texto diz que falta ajuste/comissionamento |
| `executado, sem prova de operação` | serviço feito com prova, cadeia encerrada, mas nada diz que voltou a operar |
| `executado, mas não voltou a operar` | o texto diz que, depois do serviço, segue com defeito ou não ficou em operação |
| `estava operando, sem troca` | encerrada porque o equipamento estava em operação — com prova literal |
| `cancelado sem prova` | cancelada sem texto que prove execução ou operação (inclui limpeza em bloco) |
| `pendente: compra ou material` | aberta, esperando compra, logística ou peça |
| `pendente: no campo` | aberta com COCM/DMSL/PROT, sem execução registrada |
| `pendente: parada no COEP` | aberta no COEP sem tratativa a partir de abril |
| `repassada a outra área` | triagem: saiu para o posto certo (chave faca, aterramento, trafo, telecom) |
| `duplicada ou aberta por engano` | outra cadeia descreve o mesmo fato, ou a SS não descreve defeito |
| `nao identificado` | o texto não permite dizer |

## VERIFICADOR — adversarial

Recebe o dossiê **e** o JSON do analista do mesmo lote. O trabalho é **derrubar** o que a prova
não sustenta, demanda a demanda:

- **Execução**: tem frase que diga que o serviço foi FEITO («substituído», «realizado», «trocado»,
  laudo, OS com fabricante instalado)? Pedido de troca, «favor substituir», «material entregue»
  ou «previsão de troca» **não** é execução. Status ATENDIDA sem texto de serviço não é execução.
- **Operação**: «FICOU EM OPERAÇÃO? NÃO» é **não**. Operação antes do serviço não prova nada.
- **Datas**: a data da tratativa cabe na janela da SS? «como_datou» está certo? Repasse e
  cancelamento têm data exata do SGM — confira.
- **Backlog de 2025** e **tratada em 2025**: confira pela chegada e pelos textos de 2025.
- **Tratativa que o analista não viu** a partir de abril: aponte.
- **Texto de terceiro**: laudo de outro código colado na SS não prova nada deste ativo.

Devolve, por ativo:

```json
{"ativo": "...", "demandas": [{
   "cadeia": "...", "mantem": false,
   "desfecho_final": "...", "executada_final": true, "data_execucao_final": "dd/mm/aaaa",
   "voltou_a_operar_final": null, "prova_final": "trecho literal",
   "backlog_2025_final": true, "tratada_em_2025_final": false,
   "tratativas_faltando": [ {mesmo formato do analista} ],
   "tratativas_erradas": [ {"data": "...", "acao": "...", "porque": "..."} ],
   "porque": "o que mudou e por quê", "confianca": "alta"
}]}
```

## Regras que não se negociam

1. `todo` antes de começar. **Um `put` por ativo, na hora.**
2. **Nenhum agente lê a saída de outro da mesma etapa.**
3. **Evidência é literal e contígua**, copiada do dossiê, até 250 caracteres. Sem texto, cite o
   evento do SGM: «SGM: <SS> cancelada em 30/06/2026 16:41».
4. **Na dúvida, `null` ou `nao identificado`.** Um vazio honesto mede a lacuna do SGM.
5. **Texto mais recente vale** (a descrição é cumulativa), e **texto vale mais que status**.
