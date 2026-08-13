/* Dinâmica do posto — onde cada equipamento está hoje.
   Uma página só: a escada de etapas, o corte por criticidade e a lista inteira. */

const D = DINAMICA;
const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const rs = (v) => `R$ ${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const TOM = {
  'Concluído': 'bom', 'Cancelada em operação': 'bom', 'Em ajustes': 'bom',
  'Aguardando comissionamento': 'bom', 'Entregue ao COCM': 'atento', 'Em logística': 'atento',
  'Em compra': 'critico', 'Travado': 'critico',
};

const EXPLICA = {
  'Concluído': 'serviço fechado no parecer',
  'Cancelada em operação': 'a SS caiu porque o equipamento já estava operando',
  'Em ajustes': 'trocado, a Proteção ainda vai ajustar',
  'Aguardando comissionamento': 'trocado, o DMSL ainda vai comissionar',
  'Entregue ao COCM': 'material na mão da equipe, falta subir no poste',
  'Em logística': 'comprado, a caminho',
  'Em compra': 'na fila do posto',
  'Com o DMSL': 'laudo pedido, esperando o DMSL responder',
  'Primeiro ataque do DMSL': 'entrou agora, o DMSL vai ao campo diagnosticar',
  'Em análise': 'o posto está lendo o caso',
  'Travado': 'parado por coisa que não é material',
  'Desmobilizado': 'não era caso do posto',
  'Sem parecer': 'ainda não foi olhado',
};

const num = ({ rotulo, valor, nota, tom = '' }) => `<div class="numero ${tom}">
  <span>${esc(rotulo)}</span><b>${esc(valor)}</b>${nota ? `<i>${esc(nota)}</i>` : ''}</div>`;

let filtro = null;

function escada() {
  const maior = Math.max(...D.por_etapa.map((e) => e.qtd));
  return `<div class="escada">${D.por_etapa.map((e) => `
    <button class="degrau ${TOM[e.etapa] || ''}" data-etapa="${esc(e.etapa)}">
      <span class="nome">${esc(e.etapa)}</span>
      <span class="barra"><i style="width:${(100 * e.qtd / maior).toFixed(1)}%"></i></span>
      <span class="lado"><b>${e.qtd}</b>${e.valor ? esc(rs(e.valor))
        : e.valor_evitado ? `<i class="evitado">${esc(rs(e.valor_evitado))} evitados</i>` : '—'}</span>
    </button>`).join('')}</div>
    <p class="destaque-texto" style="margin-top:10px">Clique numa etapa para filtrar a lista.
    O valor é o previsto na planilha de gestão — ${D.com_valor} dos ${D.total} têm valor lá.</p>`;
}

function matriz() {
  const crits = D.por_criticidade.map((c) => c.criticidade);
  const etapas = D.por_etapa.map((e) => e.etapa);
  const busca = (e, c) => D.matriz.find((x) => x.etapa === e && x.criticidade === c);
  return `<div class="tabela-rol"><table class="matriz matriz-etapa"><thead><tr><th>Etapa</th>
    ${crits.map((c) => `<th class="num">${esc(c)}</th>`).join('')}<th class="num">Total</th></tr></thead><tbody>
    ${etapas.map((e) => {
      const linha = D.por_etapa.find((x) => x.etapa === e);
      return `<tr><td><b>${esc(e)}</b></td>
        ${crits.map((c) => { const x = busca(e, c);
          return `<td class="num ${x ? '' : 'zero'}">${x ? x.qtd : '·'}</td>`; }).join('')}
        <td class="num"><b>${linha.qtd}</b></td></tr>`;
    }).join('')}
    <tr><td><b>Total</b></td>
      ${crits.map((c) => `<td class="num"><b>${D.por_criticidade.find((x) => x.criticidade === c).qtd}</b></td>`).join('')}
      <td class="num"><b>${D.total}</b></td></tr>
    </tbody></table></div>`;
}

function rol() {
  const lista = filtro ? D.lista.filter((x) => x.etapa === filtro) : D.lista;
  return `<div class="filtros">
      <button class="pastilha ${filtro ? '' : 'limpar'}" data-etapa="" aria-pressed="${!filtro}">Todos · ${D.total}</button>
      ${D.por_etapa.map((e) => `<button class="pastilha" data-etapa="${esc(e.etapa)}"
        aria-pressed="${filtro === e.etapa}">${esc(e.etapa)} <b>${e.qtd}</b></button>`).join('')}
    </div>
    <div class="tabela-rol"><table class="matriz rol"><thead><tr><th>Ativo</th><th>Localidade</th>
    <th>Tipo</th><th>Criticidade</th><th>Etapa</th><th>Parecer COEP</th><th>Check</th>
    <th class="num">Valor previsto<i class="linha-nota">em vermelho, o que teria sido gasto</i></th></tr></thead><tbody>
    ${lista.map((x) => `<tr>
      <td><b class="mono">${esc(x.ativo)}</b></td>
      <td>${esc(x.localidade || '—')}${x.polo ? `<span class="nota-campo">${esc(x.polo)}</span>` : ''}</td>
      <td>${esc(x.tipo)}</td>
      <td>${esc(x.criticidade)}</td>
      <td>${esc(x.etapa)}</td>
      <td>${esc(x.parecer || '—')}
        ${x.o_que_trocar ? `<span class="nota-campo">troca: ${esc(x.o_que_trocar)}</span>` : ''}
        ${x.nota_campo ? `<span class="nota-campo">${esc(x.nota_campo)}</span>` : ''}
        ${x.observacao && x.observacao !== x.nota_campo ? `<span class="nota-campo">${esc(x.observacao)}</span>` : ''}</td>
      <td>${esc(x.check || '—')}</td>
      <td class="num">${x.valor ? esc(rs(x.valor))
        : x.valor_evitado ? `<i class="evitado">${esc(rs(x.valor_evitado))}</i>` : '—'}</td></tr>`).join('')}
    </tbody></table></div>`;
}

function desenhar() {
  const feito = D.feito;
  $('#pagina').innerHTML = `<div class="folha">
    <header>
      <h1>Dinâmica do posto</h1>
      <p class="sub">Onde cada um dos ${D.total} religadores e reguladores da carteira do ETO-COEP está
      hoje, pelo parecer mais recente${D.sem_parecer === 0 ? ' — e agora todos têm parecer' : ''}.
      As quatro primeiras etapas já tiveram serviço: <b>${feito.qtd} equipamentos</b>,
      ${rs(feito.valor)} de valor previsto.</p>
      <div class="carimbo">
        <span>${esc(D.fonte)}</span>
        <span>posição de ${esc(D.gerado_em.split('-').reverse().join('/'))}</span>
      </div>
    </header>

    <div class="numeros">
      ${num({ rotulo: 'Na carteira', valor: D.total, nota: D.por_tipo.map((t) => `${t.qtd} ${t.tipo}`).join(' · ') })}
      ${num({ rotulo: 'Com serviço feito', valor: feito.qtd, nota: `${Math.round(100 * feito.qtd / D.total)}% da carteira`, tom: 'bom' })}
      ${num({ rotulo: 'Na fila de compra', valor: D.por_etapa.find((e) => e.etapa === 'Em compra')?.qtd ?? 0, nota: 'esperando material', tom: 'critico' })}
      ${num({ rotulo: 'Valor previsto', valor: rs(D.valor_total), nota: `${D.com_valor} ativos orçados — os cancelados não entram` })}
      ${D.economia ? num({ rotulo: 'O que teria sido gasto', valor: rs(D.economia.total), nota: `${D.economia.total_ativos} cancelados em operação`, tom: 'evitado' }) : ''}
    </div>

    <section class="bloco"><h3>A escada</h3>${escada()}</section>

    ${D.economia ? `<section class="bloco"><h3>O que teria sido gasto nos cancelados em operação</h3>
      <p class="destaque-texto">${esc(D.economia.criterio)}</p>
      <div class="numeros">
        ${num({ rotulo: 'Total evitado', valor: rs(D.economia.total), nota: `${D.economia.total_ativos} equipamentos`, tom: 'evitado' })}
        ${num({ rotulo: 'Só material de catálogo', valor: rs(D.economia.material_puro), nota: `sem o adicional de obra de ${rs(D.economia.adicional_obra)}` })}
        ${num({ rotulo: 'Com peça identificada', valor: D.economia.com_material, nota: `${D.economia.sem_material} não precisavam de peça · ${D.economia.indeterminados} sem laudo que decida` })}
      </div>
      <div class="tabela-rol"><table class="matriz"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th>Criticidade</th><th>Tensão</th><th>Peça que teria sido comprada</th><th>Confiança</th>
      <th class="num">Valor evitado</th></tr></thead><tbody>
      ${D.economia.lista.map((x) => `<tr>
        <td><b class="mono">${esc(x.ativo)}</b></td><td>${esc(x.localidade || '—')}</td>
        <td>${esc(x.criticidade || '—')}</td><td>${esc(x.classe_tensao || '—')}</td>
        <td>${x.materiais.length ? x.materiais.map((m) => esc(m.split('|')[1] ? m.split('|')[1].trim() : m)).join('<br>')
          : `<i>${x.veredito === 'sem_material' ? 'não precisava de peça' : 'o laudo não permite dizer'}</i>`}
          ${x.defeito ? `<span class="nota-campo">${esc(x.defeito)}</span>` : ''}</td>
        <td>${esc(x.confianca || '—')}</td>
        <td class="num">${x.valor ? `<i class="evitado">${esc(rs(x.valor))}</i>` : '—'}</td></tr>`).join('')}
      </tbody><tfoot><tr><td colspan="6">Total</td>
      <td class="num"><i class="evitado"><b>${esc(rs(D.economia.total))}</b></i></td></tr></tfoot></table></div>
      ${D.economia.conciliacao ? (() => { const c = D.economia.conciliacao; return `
      <div class="nota" style="margin-top:16px"><strong>${esc(c.pergunta)}</strong>${esc(c.resumo)}</div>
      <div class="tabela-rol" style="margin-top:10px"><table class="matriz"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th class="num">Planilha de gestão</th><th class="num">Leitura das SS</th><th class="num">Diferença</th>
      <th>Por quê</th></tr></thead><tbody>
      ${c.linhas.map((l) => `<tr><td><b class="mono">${esc(l.ativo)}</b></td><td>${esc(l.localidade)}</td>
        <td class="num">${esc(rs(l.planilha))}</td><td class="num">${esc(rs(l.leitura))}</td>
        <td class="num">${l.diferenca ? `<i class="evitado">${esc(rs(l.diferenca))}</i>` : '—'}</td>
        <td>${esc(l.explica)}</td></tr>`).join('')}
      <tr><td colspan="2"><b>Os outros ${c.fora_da_planilha}</b></td><td class="num">—</td>
        <td class="num">${esc(rs(c.vem_de_fora))}</td><td class="num">—</td>
        <td>Não estão na planilha de gestão, que cobre 65 dos 129 ativos. Para eles a planilha não mostra
        valor nenhum — o número vem inteiro da leitura das SS.</td></tr>
      </tbody></table></div>`; })() : ''}
      ${D.economia.comparacao ? `<div class="nota branda" style="margin-top:12px"><strong>Contra a estimativa por mediana que estava aqui antes</strong>${esc(D.economia.comparacao)}</div>` : ''}
      ${(D.economia.ressalvas || []).length ? `<p class="destaque-texto" style="margin-top:16px">Onde a leitura pede cuidado:</p>
      ${D.economia.ressalvas.map((x) => `<div class="nota branda" style="margin-bottom:8px">${esc(x)}</div>`).join('')}` : ''}
    </section>` : ''}

    <section class="bloco"><h3>Etapa × criticidade</h3>
      <p class="destaque-texto">Onde está o risco: quantos de cada criticidade em cada etapa.</p>
      ${matriz()}</section>

    ${D.notas_campo.length ? `<section class="bloco"><h3>O que o campo anotou (${D.notas_campo.length})</h3>
      <div class="itens">${D.notas_campo.map((x) => `<div class="item-linha">
        <span><b class="mono">${esc(x.ativo)}</b> · ${esc(x.localidade)}
        <i class="linha-nota">${esc(x.nota_campo)}</i></span>
        <b>${esc(x.etapa)}</b></div>`).join('')}</div></section>` : ''}

    ${(D.ajustes || []).length ? `<section class="bloco"><h3>Ajustes que você mandou fazer</h3>
      <div class="itens">${D.ajustes.map((a) => `<div class="item-linha">
        <span><b class="mono">${esc(a.ativo)}</b> · ${esc(a.localidade)} — ${esc(a.o_que_trocar)}
        <i class="linha-nota">${esc(a.motivo)}</i></span><b>${esc(rs(a.valor))}</b></div>`).join('')}</div>
      </section>` : ''}

    <section class="bloco"><h3>A carteira inteira</h3>${rol()}</section>
  </div>`;

  document.querySelectorAll('[data-etapa]').forEach((b) => b.addEventListener('click', () => {
    const e = b.dataset.etapa;
    filtro = (!e || filtro === e) ? null : e;
    desenhar();
    if (filtro) document.querySelector('.rol')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }));
}

desenhar();
