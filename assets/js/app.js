/* Equipamentos Especiais — painel de acompanhamento.
   JavaScript sem dependências: os dados vêm dos JSONs em data/, ou de DADOS_EMBUTIDOS
   quando a página é servida como arquivo único. */

const CORES_CRITICIDADE = {
  'Muito Alta': 'var(--muito-alta)',
  'Alta': 'var(--alta)',
  'Média': 'var(--media)',
  'Baixa': 'var(--baixa)',
  'Sem classificação': 'var(--sem-classe)',
};

const ORDEM_CRITICIDADE = ['Muito Alta', 'Alta', 'Média', 'Baixa', 'Sem classificação'];
const ORDEM_GRAVIDADE = ['Crítica', 'Alta', 'Média', 'Baixa'];

const DESCRICAO_ALERTA = {
  'SS de 2025 ainda aberta':
    'SS abertas em 2025 que atravessaram o período chuvoso e chegaram ao seco de 2026 sem solução. São os casos mais envelhecidos da carteira. O tempo em aberto vem da data real de abertura registrada na planilha de gestão; onde ela falta, é contado pelo piso — a partir de 31/12 do ano da SS.',
  'Prazo-limite da SS estourado':
    'A SS tem prazo-limite registrado no próprio sistema (SGM), esse prazo já passou e a SS continua pendente. Diferente da previsão anotada à mão na coluna Observação, este é o prazo formal do sistema, definido pela criticidade com que a SS foi aberta.',
  'Prazo de previsão vencido':
    'A própria planilha registrou uma data de entrega ou substituição que já passou, e o Check não foi movido para “Ok”.',
  'SS fechada com pendência aberta':
    'A SS está marcada como CONCLUÍDA, mas o Parecer COEP e/ou o Check continuam indicando pendência. Ou a baixa foi indevida, ou os campos não foram atualizados.',
  'Concluído pelo COEP, não fechado':
    'O COEP já deu o parecer de concluído, mas a SS segue “Em andamento” — normalmente esperando laudo ou confirmação de campo.',
  'Substituído, pendente laudo':
    'O equipamento já foi trocado em campo. O que trava o encerramento é o laudo da empreiteira.',
};

const DESCRICAO_DIVERGENCIA = {
  'Aquisição sem requisição':
    'O Parecer COEP declara o equipamento “em processo de aquisição”, mas não existe linha correspondente na planilha de EMD. Sem linha de EMD não há requisição de material rastreável — o processo de compra pode não ter sido efetivamente aberto, ou está sendo controlado fora deste arquivo.',
  'SS atribuída a outro ativo':
    'O mesmo número de SS aparece nas duas planilhas apontando para equipamentos diferentes. Uma das duas está errada, e o material pode ser destinado ao ativo errado.',
  'Ativo divergente dentro do EMD':
    'A planilha de EMD tem duas colunas “Ativo” e nesta linha elas trazem códigos diferentes. Não dá para saber a qual equipamento a requisição pertence.',
  'Substituição feita, SS aberta':
    'O EMD dá a substituição como concluída, mas a SS de campo continua aberta. Se a troca realmente ocorreu, falta apenas a baixa — e o equipamento está inflando a lista de indisponíveis.',
  'SS concluída, EMD pendente':
    'A planilha de criticidade dá a SS como concluída, mas o EMD ainda marca a substituição ou a entrega como pendente.',
  'Número de SS divergente':
    'As duas planilhas usam números de SS diferentes para o mesmo ativo. Isso é esperado quando uma registra a SS de requisição e a outra a SS de campo — o problema é não haver campo comum ligando as duas, o que impede a conferência automática.',
  'Defeito divergente':
    'O defeito descrito no EMD não bate com o da planilha de criticidade. Como é o defeito que define o material a requisitar, a divergência pode gerar compra do item errado.',
  'Criticidade divergente':
    'A criticidade diverge entre as planilhas, ou está em branco no EMD. A fila de prioridade muda conforme a planilha consultada.',
  'Localidade ou polo divergente':
    'Localidade ou polo diferentes entre as planilhas — afeta o depósito de destino e a equipe acionada.',
  'Entrega atrasada':
    'O material chegou depois da data prevista registrada no próprio EMD.',
  'Cadastro incompleto no EMD':
    'Campos de controle em branco (número de EMD, obra, modelo, SS). Sem eles a requisição não é rastreável da abertura até a entrega.',
  'Incoerência interna do EMD':
    'A própria linha do EMD se contradiz — por exemplo, substituição concluída com equipamento não entregue.',
};

const DESCRICAO_COMPRA = {
  'Compra possivelmente desnecessária':
    'O Parecer COEP já registra o equipamento como substituído ou concluído. Se a troca ocorreu depois do pedido, o material comprado vira sobressalente — vale confirmar com o COCM antes de a compra avançar.',
  'Comprado sem requisição de EMD':
    'O ativo entrou no plano de compras mas não tem linha na planilha de EMD. A compra foi pedida sem a requisição formal correspondente no arquivo analisado.',
  'Status do plano desatualizado':
    'O status congelado no plano (foto de 17/07/2026) já não corresponde ao Parecer COEP atual. Não é erro do plano, é defasagem — mas muda a leitura de quem consulta só o plano.',
  'SS divergente no plano':
    'O plano cita uma SS diferente da registrada na planilha de criticidade para o mesmo ativo — mesma questão de rastreabilidade vista no cruzamento do EMD.',
};

const estado = {
  equipamentos: [],
  alertas: [],
  divergencias: [],
  compras: [],
  meta: null,
  filtros: { busca: '', criticidade: '', regional: '', polo: '', tipo: '', categoria: '', situacao: '' },
  filtrosEmd: { busca: '', tipo: '', gravidade: '', criticidade: '' },
  ordenacao: { campo: 'priorizacao', direcao: 'desc' },
};

/* ---------------- utilidades ---------------- */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function esc(texto) {
  return String(texto ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function chaveClasse(texto) {
  return String(texto ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

const categoriaDe = (e) => e.analise?.categoria_primaria || '';
const estaConcluida = (e) => /CONCLU/i.test(e.ss || '');

function dataBr(iso) {
  const [a, m, d] = String(iso).split('-');
  return d ? `${d}/${m}/${a}` : iso;
}

function moeda(valor) {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function numero(valor) {
  return valor.toLocaleString('pt-BR');
}

function textoBusca(e) {
  if (!e._busca) {
    const a = e.analise || {};
    e._busca = [
      e.ativo, e.localidade, e.polo, e.regional, e.ss, e.parecer_coep, e.observacao,
      e.defeito_planilha, e.descricao_ss, e.tipo_nome, a.categoria_primaria,
      a.componente_especifico, a.resumo_tecnico, a.acao_requerida, a.causa_raiz,
      a.pendencia_declarada, a.responsavel_atual,
    ].join(' ').toLowerCase();
  }
  return e._busca;
}

/* ---------------- carregamento ---------------- */

async function carregar() {
  if (typeof DADOS_EMBUTIDOS !== 'undefined') {
    Object.assign(estado, DADOS_EMBUTIDOS);
  } else {
    try {
      const [equipamentos, alertas, divergencias, compras, meta] = await Promise.all([
        fetch('data/equipamentos.json').then((r) => r.json()),
        fetch('data/alertas_coep.json').then((r) => r.json()),
        fetch('data/divergencias_emd.json').then((r) => r.json()),
        fetch('data/plano_compras.json').then((r) => r.json()),
        fetch('data/meta.json').then((r) => r.json()),
      ]);
      Object.assign(estado, { equipamentos, alertas, divergencias, compras, meta });
    } catch (erro) {
      $('.area').innerHTML =
        '<article class="metodologia"><h3>Não foi possível carregar os dados</h3>' +
        '<p>Os arquivos em <code>data/</code> precisam ser servidos por HTTP. Rode ' +
        '<code>python3 -m http.server 8000</code> na raiz do projeto e abra ' +
        '<code>http://localhost:8000</code>.</p></article>';
      console.error(erro);
      return;
    }
  }

  const m = estado.meta;
  $('#data-referencia').textContent = dataBr(m.gerado_em);
  $('#nota-lateral').textContent =
    `${m.total_equipamentos} equipamentos · ${m.total_com_descricao} descrições de SS lidas ` +
    `e categorizadas em ${m.lotes_analisados} lotes.`;

  $('#selo-equipamentos').textContent = m.total_equipamentos;
  $('#selo-coep').textContent = m.equipamentos_com_alerta;
  $('#selo-emd').textContent = m.equipamentos_com_divergencia;
  $('#selo-compras').textContent = m.compras.total_ativos;

  $('#meta-total').textContent = m.total_equipamentos;
  $('#meta-abertos').textContent = `${m.total_abertos} SS em aberto`;
  $('#meta-equip').textContent = m.total_equipamentos;
  $('#meta-equip-desc').textContent = `${m.total_com_descricao} com descrição`;
  $('#meta-coep').textContent = m.equipamentos_com_alerta;
  $('#meta-coep-alertas').textContent = `${m.total_alertas} alertas`;
  $('#meta-emd').textContent = m.total_divergencias;
  $('#meta-emd-equip').textContent = `${m.equipamentos_com_divergencia} equipamentos`;
  $('#meta-compras').textContent = moeda(m.compras.valor_total);
  $('#meta-compras-itens').textContent = `${m.compras.total_pecas} peças`;

  montarVisaoGeral();
  montarFiltros();
  renderTabela();
  montarCoep();
  montarEmd();
  montarCompras();
  montarFrota();
  montarMetodologia();
}

/* ---------------- componentes ---------------- */

function kpi({ rotulo, valor, nota, tom = '' }) {
  const longo = String(valor).length > 11 ? ' longo' : '';
  return `<article class="kpi ${tom}">
    <span>${esc(rotulo)}</span>
    <strong class="${longo.trim()}">${esc(valor)}</strong>
    ${nota ? `<small>${esc(nota)}</small>` : ''}
  </article>`;
}

function barras(seletor, itens) {
  const maximo = Math.max(...itens.map((i) => i.total), 1);
  $(seletor).innerHTML = itens.map((i) => `
    <div class="linha-barra">
      <div><span>${esc(i.rotulo)}</span><strong>${i.total}</strong></div>
      <i><b style="width:${(i.total / maximo * 100).toFixed(1)}%"></b></i>
    </div>`).join('');
}

function rosca(seletor, itens, corDe) {
  const total = itens.reduce((s, i) => s + i.total, 0) || 1;
  const raio = 60, espessura = 24, circ = 2 * Math.PI * raio;
  let acumulado = 0;

  const fatias = itens.map((item) => {
    const fracao = item.total / total;
    const traco = `${(fracao * circ).toFixed(2)} ${circ.toFixed(2)}`;
    const offset = -(acumulado * circ).toFixed(2);
    acumulado += fracao;
    return `<circle cx="78" cy="78" r="${raio}" fill="none" stroke="${corDe(item)}"
      stroke-width="${espessura}" stroke-dasharray="${traco}" stroke-dashoffset="${offset}"
      transform="rotate(-90 78 78)"><title>${esc(item.rotulo)}: ${item.total}</title></circle>`;
  }).join('');

  $(seletor).innerHTML = `
    <svg width="156" height="156" viewBox="0 0 156 156" role="img" aria-label="Distribuição por criticidade">
      ${fatias}
      <text x="78" y="76" text-anchor="middle" font-family="Georgia, serif" font-size="30" fill="#17222f">${total}</text>
      <text x="78" y="94" text-anchor="middle" font-size="9" letter-spacing="1" fill="#63727f">EQUIPAMENTOS</text>
    </svg>
    <div class="legenda-rosca">
      ${itens.map((i) => `<div class="item-legenda">
        <i style="background:${corDe(i)}"></i><span>${esc(i.rotulo)}</span><b>${i.total}</b>
      </div>`).join('')}
    </div>`;
}

/* ---------------- visão geral ---------------- */

function montarVisaoGeral() {
  const m = estado.meta;
  const pega = (r) => m.por_criticidade.find((i) => i.rotulo === r)?.total ?? 0;

  $('#faixa-escopo').innerHTML = [
    ['Fonte', 'Relação dos Equipamentos Indisponíveis — ETO'],
    ['Aba', 'Criticidade por Equipamento'],
    ['Posição', dataBr(m.gerado_em)],
    ['Descrições lidas', `${m.total_com_descricao} em ${m.lotes_analisados} lotes`],
    ['Planilhas cruzadas', 'Criticidade · EMD · Plano de compras'],
  ].map(([k, v]) => `<div><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');

  $('#kpis').innerHTML = [
    kpi({ rotulo: 'Equipamentos na relação', valor: m.total_equipamentos, nota: `${m.total_com_descricao} com descrição de SS`, tom: 'tom-tinta' }),
    kpi({ rotulo: 'SS em aberto', valor: m.total_abertos, nota: `${m.total_concluidos} já concluídas`, tom: 'tom-atencao' }),
    kpi({ rotulo: 'Criticidade muito alta', valor: pega('Muito Alta'), nota: `+ ${pega('Alta')} de criticidade alta`, tom: 'tom-critico' }),
    kpi({ rotulo: 'Com pendência no COEP', valor: m.equipamentos_com_alerta, nota: `${m.total_alertas} alertas levantados`, tom: 'tom-critico' }),
    kpi({ rotulo: 'Divergência entre planilhas', valor: m.equipamentos_com_divergencia, nota: `${m.total_divergencias} divergências`, tom: 'tom-critico' }),
    kpi({ rotulo: 'Sem classificação', valor: pega('Sem classificação'), nota: 'fora da matriz de priorização', tom: 'tom-atencao' }),
  ].join('');

  rosca('#rosca-criticidade', m.por_criticidade, (i) => CORES_CRITICIDADE[i.rotulo] || 'var(--petroleo)');
  barras('#barras-categoria', m.por_categoria);
  barras('#barras-regional', m.por_regional);
  barras('#barras-responsavel', m.por_responsavel);
  barras('#barras-status', m.por_status_operacional);
  barras('#barras-polo', m.por_polo.filter((i) => i.rotulo !== 'Não informado').slice(0, 10));

  const linhas = m.matriz_categoria_criticidade;
  const maximo = Math.max(...linhas.flatMap((l) => ORDEM_CRITICIDADE.map((c) => l[c] || 0)), 1);
  $('#matriz-categoria').innerHTML = `
    <thead><tr><th>Categoria</th>${ORDEM_CRITICIDADE.map((c) => `<th>${esc(c)}</th>`).join('')}<th>Total</th></tr></thead>
    <tbody>${linhas.map((l) => {
      const total = ORDEM_CRITICIDADE.reduce((s, c) => s + (l[c] || 0), 0);
      return `<tr><td>${esc(l.categoria)}</td>${ORDEM_CRITICIDADE.map((c) => {
        const n = l[c] || 0;
        if (!n) return '<td class="zero">·</td>';
        const pct = (12 + (n / maximo) * 55).toFixed(0);
        return `<td><span class="celula-calor" style="background:color-mix(in srgb, ${CORES_CRITICIDADE[c]} ${pct}%, transparent)">${n}</span></td>`;
      }).join('')}<td><strong>${total}</strong></td></tr>`;
    }).join('')}</tbody>`;
}

/* ---------------- filtros e tabela ---------------- */

function preencher(seletor, valores) {
  const select = $(seletor);
  valores.forEach((v) => {
    const opcao = document.createElement('option');
    opcao.value = v;
    opcao.textContent = v;
    select.appendChild(opcao);
  });
}

function montarFiltros() {
  const unicos = (fn) => [...new Set(estado.equipamentos.map(fn).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b, 'pt-BR'));

  preencher('#f-criticidade', ORDEM_CRITICIDADE.filter((c) => estado.equipamentos.some((e) => e.criticidade === c)));
  preencher('#f-regional', unicos((e) => e.regional));
  preencher('#f-polo', unicos((e) => e.polo));
  preencher('#f-tipo', unicos((e) => e.tipo_nome));
  preencher('#f-categoria', unicos(categoriaDe));

  const mapa = {
    '#f-busca': 'busca', '#f-criticidade': 'criticidade', '#f-regional': 'regional',
    '#f-polo': 'polo', '#f-tipo': 'tipo', '#f-categoria': 'categoria', '#f-situacao': 'situacao',
  };

  Object.entries(mapa).forEach(([sel, chave]) => {
    $(sel).addEventListener('input', (ev) => {
      estado.filtros[chave] = ev.target.value;
      renderTabela();
    });
  });

  $('#limpar-filtros').addEventListener('click', () => {
    Object.keys(estado.filtros).forEach((k) => { estado.filtros[k] = ''; });
    Object.keys(mapa).forEach((s) => { $(s).value = ''; });
    renderTabela();
  });

  $$('#tabela-equipamentos thead th').forEach((th) => {
    th.addEventListener('click', () => {
      const campo = th.dataset.ordenar;
      const o = estado.ordenacao;
      o.direcao = o.campo === campo && o.direcao === 'asc' ? 'desc' : 'asc';
      o.campo = campo;
      renderTabela();
    });
  });
}

function renderTabela() {
  const f = estado.filtros;
  const termo = f.busca.trim().toLowerCase();

  let lista = estado.equipamentos.filter((e) => {
    if (f.criticidade && e.criticidade !== f.criticidade) return false;
    if (f.regional && e.regional !== f.regional) return false;
    if (f.polo && e.polo !== f.polo) return false;
    if (f.tipo && e.tipo_nome !== f.tipo) return false;
    if (f.categoria && categoriaDe(e) !== f.categoria) return false;
    if (f.situacao === 'aberta' && estaConcluida(e)) return false;
    if (f.situacao === 'concluida' && !estaConcluida(e)) return false;
    if (f.situacao === 'alerta' && !e.tem_alerta) return false;
    if (f.situacao === 'divergencia' && !e.tem_divergencia) return false;
    if (f.situacao === 'compras' && !e.no_plano_compras) return false;
    if (termo && !textoBusca(e).includes(termo)) return false;
    return true;
  });

  const { campo, direcao } = estado.ordenacao;
  const sinal = direcao === 'asc' ? 1 : -1;
  const valorDe = (e) => {
    if (campo === 'categoria') return categoriaDe(e);
    if (campo === 'criticidade') return ORDEM_CRITICIDADE.indexOf(e.criticidade);
    return e[campo];
  };
  lista = [...lista].sort((a, b) => {
    const va = valorDe(a), vb = valorDe(b);
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * sinal;
    return String(va ?? '').localeCompare(String(vb ?? ''), 'pt-BR') * sinal;
  });

  $$('#tabela-equipamentos thead th').forEach((th) => {
    if (th.dataset.ordenar === campo) {
      th.setAttribute('aria-sort', direcao === 'asc' ? 'ascending' : 'descending');
      th.querySelector('.seta').textContent = direcao === 'asc' ? '↑' : '↓';
    } else {
      th.removeAttribute('aria-sort');
      th.querySelector('.seta').textContent = '↕';
    }
  });

  $('#contador-resultado').textContent = `${lista.length} / ${estado.equipamentos.length}`;
  $('#tabela-vazia').hidden = lista.length > 0;

  $('#corpo-tabela').innerHTML = lista.map((e) => `
    <tr data-ativo="${esc(e.ativo)}">
      <td class="mono">${esc(e.ativo)}${e.tem_alerta ? ' <span class="pilula crit-muito-alta">!</span>' : ''}</td>
      <td>${esc(e.tipo_nome)}</td>
      <td>${esc(e.localidade || '—')}</td>
      <td>${esc(e.regional || '—')}</td>
      <td class="mono">${estaConcluida(e) ? '<span class="pilula neutra">Concluída</span>' : esc(e.ss)}</td>
      <td class="truncar" title="${esc(categoriaDe(e))}">${esc(categoriaDe(e) || '—')}</td>
      <td class="num">${e.priorizacao || '—'}</td>
      <td><span class="pilula crit-${chaveClasse(e.criticidade)}">${esc(e.criticidade)}</span></td>
      <td class="truncar" title="${esc(e.parecer_coep)}">${esc(e.parecer_coep || '—')}</td>
    </tr>`).join('');

  $$('#corpo-tabela tr').forEach((tr) => {
    tr.addEventListener('click', () => abrirFicha(tr.dataset.ativo));
  });
}

/* ---------------- fichas em grupo ---------------- */

function fichaHtml(item, extras = '') {
  return `<article class="ficha g-${chaveClasse(item.gravidade)}" data-ativo="${esc(item.ativo)}">
    <div class="ficha-topo">
      <b>${esc(item.ativo)}</b>
      <span class="pilula crit-${chaveClasse(item.criticidade)}">${esc(item.criticidade)}</span>
      ${item.dias_atraso ? `<span class="atraso">${item.dias_atraso} dias de atraso</span>` : ''}
      ${item.valor_envolvido ? `<span class="valor-envolvido">${moeda(item.valor_envolvido)}</span>` : ''}
    </div>
    <div class="ficha-local">${esc(item.localidade || '—')} · ${esc(item.polo || '—')} / ${esc(item.regional || '—')}</div>
    <p>${esc(item.detalhe)}</p>
    ${extras}
  </article>`;
}

function renderGrupos(seletor, itens, chaveTipo, descricoes, extrasDe) {
  const grupos = {};
  itens.forEach((i) => { (grupos[i[chaveTipo]] ??= []).push(i); });

  const chaves = Object.keys(grupos).sort((x, y) =>
    ORDEM_GRAVIDADE.indexOf(grupos[x][0].gravidade) - ORDEM_GRAVIDADE.indexOf(grupos[y][0].gravidade)
    || grupos[y].length - grupos[x].length);

  if (!chaves.length) {
    $(seletor).innerHTML = '<div class="vazio"><strong>Nada aqui</strong><span>Nenhum registro corresponde aos filtros.</span></div>';
    return;
  }

  $(seletor).innerHTML = chaves.map((tipo) => {
    const itensGrupo = grupos[tipo];
    const g = itensGrupo[0].gravidade;
    return `<section class="grupo">
      <div class="cabecalho-grupo">
        <div>
          <h2>${esc(tipo)}</h2>
          <span class="pilula crit-${g === 'Crítica' ? 'muito-alta' : chaveClasse(g)}">${itensGrupo.length}</span>
        </div>
        <p>${esc(descricoes[tipo] || '')}</p>
      </div>
      <div class="lista-fichas">
        ${itensGrupo.map((i) => fichaHtml(i, extrasDe ? extrasDe(i) : '')).join('')}
      </div>
    </section>`;
  }).join('');

  $$(`${seletor} .ficha`).forEach((el) => {
    el.addEventListener('click', () => abrirFicha(el.dataset.ativo));
  });
}

/* ---------------- parecer COEP ---------------- */

function montarCoep() {
  const alertas = estado.alertas;
  const criticos = alertas.filter((a) => a.gravidade === 'Crítica').length;
  const vencidos = alertas.filter((a) => a.dias_atraso);
  const maior = Math.max(0, ...vencidos.map((a) => a.dias_atraso));
  const altaCrit = new Set(alertas.filter((a) => ['Muito Alta', 'Alta'].includes(a.criticidade)).map((a) => a.ativo)).size;

  $('#kpis-coep').innerHTML = [
    kpi({ rotulo: 'Equipamentos com pendência', valor: estado.meta.equipamentos_com_alerta, nota: `${alertas.length} alertas no total`, tom: 'tom-critico' }),
    kpi({ rotulo: 'SS de anos anteriores', valor: criticos, nota: 'atravessaram o ano sem solução', tom: 'tom-critico' }),
    kpi({ rotulo: 'Prazos vencidos', valor: vencidos.length, nota: `maior atraso: ${maior} dias`, tom: 'tom-atencao' }),
    kpi({ rotulo: 'Criticidade alta ou muito alta', valor: altaCrit, nota: 'prioridade de tratativa', tom: 'tom-atencao' }),
  ].join('');

  renderGrupos('#grupos-alertas', alertas, 'tipo_alerta', DESCRICAO_ALERTA,
    (a) => `<div class="ficha-rodape"><span>SS ${esc(a.ss || '—')}</span>${a.observacao ? `<span>${esc(a.observacao)}</span>` : ''}</div>`);
}

/* ---------------- cruzamento EMD ---------------- */

function montarEmd() {
  const m = estado.meta;
  const criticas = estado.divergencias.filter((d) => d.gravidade === 'Crítica').length;

  $('#kpis-emd').innerHTML = [
    kpi({ rotulo: 'Linhas na planilha de EMD', valor: m.total_emd, nota: `contra ${m.total_equipamentos} equipamentos`, tom: 'tom-tinta' }),
    kpi({ rotulo: 'Divergências encontradas', valor: m.total_divergencias, nota: `em ${m.equipamentos_com_divergencia} equipamentos`, tom: 'tom-critico' }),
    kpi({ rotulo: 'Divergências críticas', valor: criticas, nota: 'verificar antes de comprar', tom: 'tom-critico' }),
    kpi({ rotulo: 'Em aquisição sem EMD', valor: m.em_aquisicao_sem_emd, nota: `de ${m.em_aquisicao} declarados em aquisição`, tom: 'tom-critico' }),
    kpi({ rotulo: 'SS em aberto sem EMD', valor: m.abertos_sem_emd, nota: `de ${m.total_abertos} SS abertas`, tom: 'tom-atencao' }),
  ].join('');

  const tipos = [...new Set(estado.divergencias.map((d) => d.tipo))].sort((a, b) => {
    const ga = estado.divergencias.find((d) => d.tipo === a).gravidade;
    const gb = estado.divergencias.find((d) => d.tipo === b).gravidade;
    return ORDEM_GRAVIDADE.indexOf(ga) - ORDEM_GRAVIDADE.indexOf(gb);
  });

  preencher('#f-emd-tipo', tipos);
  preencher('#f-emd-gravidade', ORDEM_GRAVIDADE.filter((g) => estado.divergencias.some((d) => d.gravidade === g)));
  preencher('#f-emd-criticidade', ORDEM_CRITICIDADE.filter((c) => estado.divergencias.some((d) => d.criticidade === c)));

  const mapa = {
    '#f-emd-busca': 'busca', '#f-emd-tipo': 'tipo',
    '#f-emd-gravidade': 'gravidade', '#f-emd-criticidade': 'criticidade',
  };
  Object.entries(mapa).forEach(([sel, chave]) => {
    $(sel).addEventListener('input', (ev) => {
      estado.filtrosEmd[chave] = ev.target.value;
      renderDivergencias();
    });
  });

  renderDivergencias();
}

function renderDivergencias() {
  const f = estado.filtrosEmd;
  const termo = f.busca.trim().toLowerCase();

  const lista = estado.divergencias.filter((d) => {
    if (f.tipo && d.tipo !== f.tipo) return false;
    if (f.gravidade && d.gravidade !== f.gravidade) return false;
    if (f.criticidade && d.criticidade !== f.criticidade) return false;
    if (termo) {
      const alvo = `${d.ativo} ${d.localidade} ${d.polo} ${d.regional} ${d.detalhe} ${d.valor_emd} ${d.valor_criticidade} ${d.campo}`.toLowerCase();
      if (!alvo.includes(termo)) return false;
    }
    return true;
  });

  $('#contador-emd').textContent = `${lista.length} / ${estado.divergencias.length}`;

  renderGrupos('#grupos-divergencias', lista, 'tipo', DESCRICAO_DIVERGENCIA, (d) => `
    <div class="comparacao">
      <div><span>EMD</span><b>${esc(d.valor_emd || '—')}</b></div>
      <div><span>Criticidade</span><b>${esc(d.valor_criticidade || '—')}</b></div>
    </div>`);
}

/* ---------------- plano de compras ---------------- */

function montarCompras() {
  const c = estado.meta.compras;

  $('#kpis-compras').innerHTML = [
    kpi({ rotulo: 'Valor do pedido', valor: moeda(c.valor_total), nota: `${c.total_pecas} peças em ${c.total_itens} itens`, tom: 'tom-tinta' }),
    kpi({ rotulo: 'Equipamentos atendidos', valor: c.total_ativos, nota: 'todos de criticidade alta ou muito alta', tom: 'tom-marca' }),
    kpi({ rotulo: 'Dias desde o pedido', valor: c.dias_decorridos, nota: `pedido em ${dataBr(c.data_pedido)}` }),
    kpi({ rotulo: 'Pedidos sem EMD', valor: c.ativos_sem_emd, nota: 'sem requisição formal correspondente', tom: 'tom-atencao' }),
    kpi({ rotulo: 'Valor a reconferir', valor: moeda(c.valor_em_revisao), nota: 'equipamentos já dados como resolvidos', tom: 'tom-critico' }),
  ].join('');

  $('#prazos-compras').innerHTML = Object.entries(c.prazos).map(([tipo, p]) => {
    const pct = Math.min(100, (c.dias_decorridos / p.prazo_dias) * 100);
    return `<article class="prazo">
      <span>${p.prazo_dias} dias a partir do pedido</span>
      <h2>${esc(tipo)}</h2>
      <p>${p.pecas} peças · ${moeda(p.valor)}</p>
      <div class="prazo-datas"><span>${dataBr(c.data_pedido)}</span><span>${dataBr(p.data_limite)}</span></div>
      <div class="prazo-trilho" role="img" aria-label="${c.dias_decorridos} de ${p.prazo_dias} dias decorridos">
        <div class="prazo-decorrido" style="width:${pct.toFixed(1)}%"></div>
      </div>
      <div class="prazo-resumo">
        <div><span>Decorridos</span><strong>${c.dias_decorridos} dias</strong></div>
        <div><span>Restantes</span><strong>${p.dias_restantes} dias</strong></div>
        <div><span>Entrega limite</span><strong>${dataBr(p.data_limite)}</strong></div>
      </div>
    </article>`;
  }).join('');

  $('#tabela-materiais tbody').innerHTML = c.por_material.map((mat) => `
    <tr>
      <td class="mono">${esc(mat.codigo)}</td>
      <td>${esc(mat.descricao)}</td>
      <td>${esc(mat.tipo)}</td>
      <td class="num">${mat.qtd}</td>
      <td class="num">${moeda(mat.valor_unitario)}</td>
      <td class="num">${moeda(mat.valor_total)}</td>
    </tr>`).join('');

  $('#tabela-materiais tfoot').innerHTML =
    `<tr><td colspan="3">Total</td><td class="num">${c.total_pecas}</td><td></td><td class="num">${moeda(c.valor_total)}</td></tr>`;

  renderGrupos('#grupos-compras', estado.compras, 'tipo', DESCRICAO_COMPRA,
    (a) => `<div class="ficha-rodape"><span>${esc(a.materiais)}</span></div>`);
}

/* ---------------- mapa e frota ---------------- */

const CORES_HEX = {
  'Muito Alta': '#a3324a',
  'Alta': '#a85c1a',
  'Média': '#7d6a15',
  'Baixa': '#2f6b52',
  'Sem classificação': '#6b7683',
};

function montarFrota() {
  const g = estado.meta.gestao;
  const comGeo = estado.equipamentos.filter((e) => e.geo);
  const comSs = estado.equipamentos.filter((e) => e.ss_sgm?.dias_aberta != null);

  $('#selo-frota').textContent = g.com_especificacao;
  $('#meta-frota').textContent = g.com_especificacao;
  $('#meta-frota-geo').textContent = `${g.com_coordenada} com coordenada`;

  $('#kpis-frota').innerHTML = [
    kpi({ rotulo: 'Com especificação técnica', valor: g.com_especificacao, nota: `de ${estado.meta.total_equipamentos} equipamentos`, tom: 'tom-tinta' }),
    kpi({ rotulo: 'Com coordenada', valor: g.com_coordenada, nota: 'plotados no mapa', tom: 'tom-marca' }),
    kpi({ rotulo: 'Prazo-limite estourado', valor: g.sla_estourado, nota: `maior atraso: ${g.maior_atraso_sla} dias`, tom: 'tom-critico' }),
    kpi({ rotulo: 'SS mais antiga', valor: `${g.maior_dias_aberta} dias`, nota: `média de ${g.media_dias_pendente} dias pendente`, tom: 'tom-critico' }),
    kpi({ rotulo: 'Valor previsto', valor: moeda(g.valor_previsto_total), nota: `em ${g.com_valor_previsto} equipamentos`, tom: 'tom-atencao' }),
  ].join('');

  desenharMapa(comGeo);
  barras('#barras-modelo', g.por_modelo.slice(0, 10));

  const faixas = [
    { rotulo: 'até 90 dias', teste: (d) => d <= 90 },
    { rotulo: '91 a 180 dias', teste: (d) => d > 90 && d <= 180 },
    { rotulo: '181 a 365 dias', teste: (d) => d > 180 && d <= 365 },
    { rotulo: 'mais de 1 ano', teste: (d) => d > 365 },
  ].map((f) => ({ rotulo: f.rotulo, total: comSs.filter((e) => f.teste(e.ss_sgm.dias_aberta)).length }));
  barras('#barras-idade', faixas);

  const comEspec = estado.equipamentos
    .filter((e) => e.especificacao)
    .sort((a, b) => (b.ss_sgm?.dias_aberta ?? -1) - (a.ss_sgm?.dias_aberta ?? -1));

  $('#tabela-frota tbody').innerHTML = comEspec.map((e) => {
    const s = e.especificacao;
    const ss = e.ss_sgm || {};
    const tensao = s.tensao_kv || s.tensao_primaria || '';
    return `<tr data-ativo="${esc(e.ativo)}">
      <td class="mono">${esc(e.ativo)}</td>
      <td>${esc(s.familia || '—')}</td>
      <td>${esc(s.marca_modelo || '—')}</td>
      <td class="mono">${esc(s.alimentador || '—')}</td>
      <td class="num">${esc(tensao || '—')}</td>
      <td>${esc(e.localidade || '—')}</td>
      <td class="num">${ss.dias_aberta != null ? ss.dias_aberta : '—'}</td>
      <td class="num">${ss.sla_estourado ? `<span class="atraso">+${ss.dias_sla}d</span>` : (ss.data_limite ? dataBr(ss.data_limite) : '—')}</td>
      <td><span class="pilula crit-${chaveClasse(e.criticidade)}">${esc(e.criticidade)}</span></td>
    </tr>`;
  }).join('');

  $$('#tabela-frota tbody tr').forEach((tr) => {
    tr.addEventListener('click', () => abrirFicha(tr.dataset.ativo));
  });
}

function desenharMapa(itens) {
  if (!itens.length) {
    $('#mapa').innerHTML = '<div class="vazio"><strong>Sem coordenadas</strong></div>';
    return;
  }

  const margem = 42;
  const lats = itens.map((e) => e.geo.lat);
  const lons = itens.map((e) => e.geo.lon);
  const latMin = Math.min(...lats), latMax = Math.max(...lats);
  const lonMin = Math.min(...lons), lonMax = Math.max(...lons);

  // Uma folga de 4% evita que os pontos das bordas encostem no quadro.
  const folgaLat = (latMax - latMin) * 0.04 || 0.1;
  const folgaLon = (lonMax - lonMin) * 0.04 || 0.1;
  const l0 = lonMin - folgaLon, l1 = lonMax + folgaLon;
  const a0 = latMin - folgaLat, a1 = latMax + folgaLat;

  // Projeção equirretangular com o paralelo médio como padrão: um grau de longitude
  // encurta por cos(lat), então sem essa correção o mapa sai esticado na horizontal.
  const escalaLon = Math.cos(((a0 + a1) / 2) * Math.PI / 180);
  const extensaoX = (l1 - l0) * escalaLon;
  const extensaoY = a1 - a0;

  const areaAltura = 620;
  const areaLargura = Math.round((areaAltura * extensaoX) / extensaoY);
  const largura = areaLargura + 2 * margem;
  const altura = areaAltura + 2 * margem;

  const px = (lon) => margem + ((lon - l0) * escalaLon / extensaoX) * areaLargura;
  const py = (lat) => altura - margem - ((lat - a0) / extensaoY) * areaAltura;

  const grade = [];
  for (let i = 0; i <= 4; i++) {
    const lon = l0 + ((l1 - l0) * i) / 4;
    const lat = a0 + ((a1 - a0) * i) / 4;
    grade.push(`<line class="malha" x1="${px(lon).toFixed(1)}" y1="${margem}" x2="${px(lon).toFixed(1)}" y2="${altura - margem}"/>`);
    grade.push(`<line class="malha" x1="${margem}" y1="${py(lat).toFixed(1)}" x2="${(margem + areaLargura).toFixed(1)}" y2="${py(lat).toFixed(1)}"/>`);
    grade.push(`<text class="eixo" x="${px(lon).toFixed(1)}" y="${altura - margem + 15}" text-anchor="middle">${lon.toFixed(2)}°</text>`);
    grade.push(`<text class="eixo" x="${margem - 6}" y="${(py(lat) + 3).toFixed(1)}" text-anchor="end">${lat.toFixed(2)}°</text>`);
  }

  // Muito Alta por último, para ficar por cima na sobreposição.
  const ordenados = [...itens].sort((a, b) =>
    ORDEM_CRITICIDADE.indexOf(b.criticidade) - ORDEM_CRITICIDADE.indexOf(a.criticidade));

  const pontos = ordenados.map((e) => {
    const cor = CORES_HEX[e.criticidade] || CORES_HEX['Sem classificação'];
    const raio = e.criticidade === 'Muito Alta' ? 7 : e.criticidade === 'Alta' ? 6 : 5;
    const ss = e.ss_sgm || {};
    const detalhe = ss.dias_aberta != null ? ` — ${ss.dias_aberta} dias em aberto` : '';
    return `<circle class="ponto" data-ativo="${esc(e.ativo)}" cx="${px(e.geo.lon).toFixed(1)}"
      cy="${py(e.geo.lat).toFixed(1)}" r="${raio}" fill="${cor}" fill-opacity=".82">
      <title>${esc(e.ativo)} · ${esc(e.localidade)} · ${esc(e.criticidade)}${esc(detalhe)}</title>
    </circle>`;
  }).join('');

  $('#mapa').innerHTML = `<svg viewBox="0 0 ${largura} ${altura}" style="max-width:${largura}px;margin:0 auto"
    role="img" aria-label="Distribuição geográfica dos equipamentos indisponíveis">
    <rect x="${margem}" y="${margem}" width="${areaLargura}" height="${areaAltura}"
      fill="#fff" stroke="#ccd6e0"/>
    ${grade.join('')}
    ${pontos}
  </svg>`;

  $('#legenda-mapa').innerHTML = ORDEM_CRITICIDADE
    .filter((c) => itens.some((e) => e.criticidade === c))
    .map((c) => `<div><i style="background:${CORES_HEX[c]}"></i>${esc(c)}
      <b style="font-family:var(--mono);font-size:10px">${itens.filter((e) => e.criticidade === c).length}</b></div>`)
    .join('');

  $$('#mapa .ponto').forEach((el) => {
    el.addEventListener('click', () => abrirFicha(el.dataset.ativo));
  });
}

/* ---------------- ficha do equipamento ---------------- */

function bloco(eyebrow, titulo, conteudo) {
  return `<article class="bloco"><span>${esc(eyebrow)}</span><h3>${esc(titulo)}</h3>${conteudo}</article>`;
}

const par = (chave, valor) => `<div class="par"><span>${esc(chave)}</span><b>${valor ?? '—'}</b></div>`;

function realcarPareceres(texto) {
  return esc(texto).replace(/(PARECER COEP:|PARECER DMSL:|FEEDBACK EQUIP\. ESPECIAIS)/gi, '<mark>$1</mark>');
}

function abrirFicha(ativo) {
  const e = estado.equipamentos.find((x) => x.ativo === ativo);
  if (!e) return;
  const a = e.analise;
  const alertas = estado.alertas.filter((x) => x.ativo === ativo);
  const divergencias = estado.divergencias.filter((x) => x.ativo === ativo);
  const achadosCompra = estado.compras.filter((x) => x.ativo === ativo);

  $('#gaveta-titulo').textContent = e.ativo;
  $('#gaveta-eyebrow').textContent = `${e.tipo_nome} · ${e.criticidade}`;
  $('#gaveta-sub').textContent =
    `${e.localidade || 'localidade não informada'} · ${e.polo || '—'} / ${e.regional || '—'}`;

  const partes = [];

  if (alertas.length || achadosCompra.length) {
    partes.push(bloco('Atenção', 'Pendências identificadas',
      [...alertas, ...achadosCompra].map((x) => `
        <div class="aviso ${['Média', 'Baixa'].includes(x.gravidade) ? 'suave' : ''}">
          <strong>${esc(x.tipo_alerta || x.tipo)}${x.dias_atraso ? ` — ${x.dias_atraso} dias de atraso` : ''}</strong>
          ${esc(x.detalhe)}
        </div>`).join('')));
  }

  if (e.especificacao) {
    const s = e.especificacao;
    const campos = [
      ['Família', s.familia], ['Marca / modelo', s.marca_modelo],
      ['Parte ativa', s.parte_ativa], ['Controlador', s.controlador],
      ['Tipo de instalação', s.tipo_instalacao], ['Alimentador', s.alimentador],
      ['Tensão (kV)', s.tensao_kv || s.tensao_primaria], ['Potência (kvar)', s.potencia_kvar],
      ['Corrente (A)', s.corrente_a], ['Tensão de controle (V)', s.tensao_controle_v],
      ['Automatizado', s.automatizado], ['Descrição', s.descricao],
      ['Estudo', s.estudo], ['Autor do estudo', s.autor_estudo],
      ['Data do estudo', s.data_estudo ? dataBr(s.data_estudo) : ''],
    ].filter(([, v]) => v);

    partes.push(bloco('Ficha técnica', 'Especificação', `
      <div class="pares">${campos.map(([k, v]) => par(k, esc(v))).join('')}</div>
      ${s.ajustes ? `<h3 style="margin:18px 0 10px;font:500 15px var(--serif)">Ajustes de proteção</h3>
        <div class="pares">${Object.entries(s.ajustes).filter(([, v]) => v)
          .map(([k, v]) => par(k, esc(v))).join('')}</div>` : ''}`));
  }

  if (e.ss_sgm) {
    const s = e.ss_sgm;
    partes.push(bloco('Sistema', 'SS no SGM', `
      ${s.sla_estourado ? `<div class="aviso" style="margin-bottom:14px">
        <strong>Prazo-limite estourado</strong>
        A SS tinha prazo até ${dataBr(s.data_limite)} e está ${s.dias_sla} dias além do prazo.</div>` : ''}
      <div class="pares">
        ${par('Número da SS', esc(s.numero || '—'))}
        ${par('Criticidade no sistema', esc(s.criticidade_ss || '—'))}
        ${par('Situação', esc(s.situacao || '—'))}
        ${par('Órgão solicitante', esc(s.org_solicitante || '—'))}
        ${par('Abertura', s.data_abertura ? dataBr(s.data_abertura) : '—')}
        ${par('Prazo-limite', s.data_limite ? dataBr(s.data_limite) : '—')}
        ${par('Término', s.data_termino ? dataBr(s.data_termino) : '—')}
        ${par('Dias em aberto', s.dias_aberta != null ? `${s.dias_aberta} dias` : '—')}
      </div>`));
  }

  if (e.geo) {
    partes.push(bloco('Localização', 'Coordenadas', `<div class="pares">
      ${par('Latitude', e.geo.lat.toFixed(6))}
      ${par('Longitude', e.geo.lon.toFixed(6))}
      ${par('UTM 22S (E, N)', `${numero(e.geo.coord_x)}, ${numero(e.geo.coord_y)}`)}
      ${par('Código GIS', esc(e.geo.cod_gis || '—'))}
      ${par('Alimentador', esc(e.geo.alimentador || '—'))}
    </div>`));
  }

  if (e.gestao) {
    const g = e.gestao;
    const campos = [
      ['Modelo', g.modelo], ['Status', g.status], ['Status (apresentação)', g.status_apresentacao],
      ['Responsável', g.responsavel], ['Status do atendimento', g.status_atendimento],
      ['Dias pendente', g.dias_pendente != null ? `${g.dias_pendente} dias` : ''],
      ['SS no SGM', g.ss_sgm], ['Descrição da compra', g.descricao_compra],
      ['Valor previsto', g.valor_previsto ? moeda(g.valor_previsto) : ''],
    ].filter(([, v]) => v);
    partes.push(bloco('Acompanhamento', 'Gestão de equipamentos',
      `<div class="pares">${campos.map(([k, v]) => par(k, esc(v))).join('')}</div>`));
  }

  partes.push(bloco('Registro', 'Identificação', `<div class="pares">
    ${par('SS aberta', esc(e.ss || '—'))}
    ${par('Parecer COEP', esc(e.parecer_coep || '—'))}
    ${par('Check de conclusão', esc(e.check || '—'))}
    ${par('Observação', esc(e.observacao || '—'))}
    ${par('Defeito (planilha)', esc(e.defeito_planilha || '—'))}
    ${par('Pontuação de priorização', e.priorizacao || '—')}
    ${par('Linha na planilha', e.linha_planilha)}
  </div>`));

  if (a) {
    partes.push(bloco('Leitura da SS', 'Categorização do defeito', `
      <div class="marcadores">
        <span class="pilula marca">${esc(a.categoria_primaria)}</span>
        ${(a.categorias_secundarias || []).map((c) => `<span class="pilula neutra">${esc(c)}</span>`).join('')}
        ${a.risco_operacional ? `<span class="pilula crit-${chaveClasse(a.risco_operacional)}">Risco ${esc(a.risco_operacional)}</span>` : ''}
      </div>
      <p class="resumo-tecnico">${esc(a.resumo_tecnico || '')}</p>
      <div class="pares">
        ${par('Componente', esc(a.componente_especifico || '—'))}
        ${par('Fases afetadas', (a.fases_afetadas || []).join(', ') || '—')}
        ${par('Situação em campo', esc(a.status_operacional || '—'))}
        ${par('Responsável atual', esc(a.responsavel_atual || '—'))}
        ${par('Causa raiz', esc(a.causa_raiz || '—'))}
        ${par('Ação necessária', esc(a.acao_requerida || '—'))}
        ${par('Pendência declarada', esc(a.pendencia_declarada || '—'))}
        ${par('Confiança da leitura', esc(a.confianca || '—'))}
      </div>
      ${a.divergencia_planilha ? `<div class="aviso suave" style="margin-top:14px">
        <strong>Divergência com a planilha</strong>${esc(a.divergencia_planilha)}</div>` : ''}`));

    if (a.datas_citadas?.length) {
      partes.push(bloco('Cronologia', 'Datas citadas na SS', `<div class="linha-tempo">
        ${a.datas_citadas.map((d) => `<div class="evento">
          <i></i><time>${esc(dataBr(d.data))}</time><span>${esc(d.o_que)}</span>
        </div>`).join('')}</div>`));
    }
  }

  if (e.compras?.length) {
    const total = e.compras.reduce((s, i) => s + i.valor_total, 0);
    partes.push(bloco('Pedido de 17/07/2026', 'Plano de compras', `<div class="linhas">
      ${e.compras.map((i) => `<div class="linha-item">
        <span>${esc(i.material)}
          <small>${esc(i.codigo)} · ${i.qtd}x · prazo de ${i.prazo_dias} dias — entrega limite ${dataBr(i.data_limite)}, faltam ${i.dias_restantes} dias</small>
        </span>
        <b>${moeda(i.valor_total)}</b>
      </div>`).join('')}
      <div class="linha-item total"><span><strong>Total</strong></span><b>${moeda(total)}</b></div>
    </div>`));
  }

  if (e.emd) {
    partes.push(bloco('Requisição de material', 'Planilha de EMD', `<div class="pares">
      ${Object.entries(e.emd).filter(([k]) => k !== 'linha_emd').map(([k, v]) => par(k, esc(v))).join('')}
    </div>`));
  } else {
    partes.push(bloco('Requisição de material', 'Planilha de EMD',
      `<div class="aviso suave"><strong>Sem linha no EMD</strong>${
        e.parecer_coep.toLowerCase().includes('aquisi')
          ? `O Parecer COEP declara «${esc(e.parecer_coep)}», mas não há requisição de material correspondente no arquivo analisado.`
          : 'Nenhuma requisição de material foi encontrada para este ativo.'}</div>`));
  }

  if (divergencias.length) {
    partes.push(bloco('Conferência', 'Divergências entre planilhas', divergencias.map((d) => `
      <div class="aviso ${['Média', 'Baixa'].includes(d.gravidade) ? 'suave' : ''}">
        <strong>${esc(d.tipo)} — ${esc(d.campo)}</strong>${esc(d.detalhe)}
        <div class="comparacao">
          <div><span>EMD</span><b>${esc(d.valor_emd || '—')}</b></div>
          <div><span>Criticidade</span><b>${esc(d.valor_criticidade || '—')}</b></div>
        </div>
      </div>`).join('')));
  }

  if (e.descricao_ss) {
    partes.push(bloco('Texto original', 'Descrição integral da SS',
      `<div class="texto-ss">${realcarPareceres(e.descricao_ss)}</div>`));
  }

  const premissas = Object.entries(e.premissas).filter(([, v]) => v !== null);
  if (premissas.length) {
    partes.push(bloco('Pontuação', 'Premissas de priorização', `<div class="linhas">
      ${premissas.map(([k, v]) => `<div class="linha-item"><span>Premissa ${k.slice(1)}</span><b>${v}</b></div>`).join('')}
      <div class="linha-item total"><span><strong>Total</strong></span><b>${e.priorizacao}</b></div>
    </div>`));
  }

  if (e.obs_analise) {
    partes.push(bloco('Nota', 'Observação após análise',
      `<p style="margin:0;font-size:13px;line-height:1.65">${esc(e.obs_analise)}</p>`));
  }

  $('#gaveta-corpo').innerHTML = partes.join('');
  $('#gaveta-corpo').scrollTop = 0;
  $('#camada-gaveta').hidden = false;
  document.body.style.overflow = 'hidden';
  $('#fechar-gaveta').focus();
}

function fecharFicha() {
  $('#camada-gaveta').hidden = true;
  document.body.style.overflow = '';
}

/* ---------------- metodologia ---------------- */

function montarMetodologia() {
  const m = estado.meta;
  const semClasse = m.por_criticidade.find((i) => i.rotulo === 'Sem classificação')?.total ?? 0;

  $('#texto-metodologia').innerHTML = `
    <h3>De onde vêm os dados</h3>
    <p>Três planilhas alimentam este site, todas versionadas em <code>data/raw/</code>:
    a <strong>Relação dos Equipamentos Indisponíveis</strong> (aba Criticidade por Equipamento),
    a planilha de <strong>EMD</strong> (OBRAS_EQ_ESPECIAL, usada para gerar as requisições de
    material) e o <strong>Plano de Compras</strong> pedido em 17/07/2026. O script
    <code>scripts/build_data.py</code> reconstrói todos os JSONs a partir delas — nenhum número
    foi digitado à mão.</p>

    <h3>Como a criticidade é calculada</h3>
    <p>A criticidade não foi inventada aqui: ela já vinha da planilha, como soma de oito premissas
    de priorização. O site preserva a pontuação e a classificação originais. ${semClasse}
    equipamentos entraram na relação depois da rodada de classificação e ainda estão
    <strong>sem criticidade atribuída</strong>.</p>

    <h3>Como as descrições de SS foram categorizadas</h3>
    <p>O campo <em>Descrição SS</em> é texto livre e concentra três vozes coladas sem separador:
    o relato de abertura da SS, os blocos <code>PARECER COEP:</code> e os blocos
    <code>PARECER DMSL:</code> / <code>FEEDBACK EQUIP. ESPECIAIS</code>. São
    ${m.total_com_descricao} descrições, várias com mais de mil caracteres.</p>
    <p>Elas foram divididas em ${m.lotes_analisados} lotes e lidas integralmente, uma a uma, por
    ${m.lotes_analisados} analistas em paralelo, com a mesma especificação de saída. Cada descrição
    rendeu categoria do defeito, componente, fases afetadas, causa raiz, situação operacional, ação
    necessária, responsável, datas prometidas e a <strong>divergência entre o que o texto diz e o
    que os campos estruturados registram</strong>.</p>
    <ul>
      <li>A classificação vem da leitura do texto, não de busca por palavra-chave.</li>
      <li>Quando o texto não sustenta uma conclusão, o campo fica como não informado — não houve
      preenchimento por suposição.</li>
      <li>Cada registro carrega um nível de confiança da leitura, visível na ficha.</li>
    </ul>

    <h3>Como as pendências do COEP foram levantadas</h3>
    <p>O Parecer COEP foi cruzado com o Check de conclusão, o ano da SS e as previsões anotadas na
    coluna Observação. Cinco regras geram os alertas:</p>
    <ul>
      <li><strong>SS de anos anteriores ainda aberta</strong> — o ano na numeração da SS é anterior
      ao atual e não há conclusão.</li>
      <li><strong>Prazo de previsão vencido</strong> — a Observação traz uma data já passada e o
      Check não está “Ok”.</li>
      <li><strong>SS fechada com pendência aberta</strong> — a SS está CONCLUÍDA mas o Parecer COEP
      ou o Check continuam sinalizando pendência.</li>
      <li><strong>Concluído pelo COEP, não fechado</strong> — o parecer diz concluído e o Check não
      acompanhou.</li>
      <li><strong>Substituído, pendente laudo</strong> — a troca ocorreu em campo e falta o laudo da
      empreiteira.</li>
    </ul>

    <h3>Como as planilhas foram casadas</h3>
    <p>A ligação entre a planilha de EMD e a de criticidade é feita pelo <strong>código do
    ativo</strong>, não pela SS. As duas usam numerações de universos diferentes: o EMD registra a
    SS de requisição do COEP (<code>ETO-COEP …</code>) e a planilha de criticidade registra a SS de
    campo (<code>ETO-RD-…</code>, <code>ETO-PROT-…</code>, <code>ETO-TELE-…</code>). Casar por SS
    produziria falso negativo em quase toda a base. Pelo ativo, as ${m.total_emd} linhas do EMD
    encontraram par.</p>

    <h3>Prazos do plano de compras</h3>
    <p>O pedido de ${dataBr(m.compras.data_pedido)} segue prazo contratual de
    ${m.compras.prazos.Religador.prazo_dias} dias para religador (entrega limite
    ${dataBr(m.compras.prazos.Religador.data_limite)}) e
    ${m.compras.prazos.Regulador.prazo_dias} dias para regulador de tensão (entrega limite
    ${dataBr(m.compras.prazos.Regulador.data_limite)}), contados da data do pedido.</p>

    <h3>Limites desta análise</h3>
    <ul>
      <li>A posição é de <strong>${dataBr(m.gerado_em)}</strong>. Prazos são calculados contra essa
      data — reprocessar o script atualiza os atrasos.</li>
      <li>As previsões da coluna Observação não trazem ano. Datas de meses já passados foram lidas
      como do ano corrente, o que pode subestimar atrasos de itens mais antigos.</li>
      <li>A numeração da SS informa só o ano, então o tempo em aberto das SS de anos anteriores é
      contado pelo piso — a partir de 31/12 do ano da SS.</li>
      <li>Só a aba Criticidade por Equipamento foi recebida da planilha de indisponíveis; as abas de
      concluídas pelo DMSL não estavam no arquivo.</li>
      <li>${m.total_equipamentos - m.total_com_descricao} equipamentos não têm descrição de SS (em
      geral os já concluídos) e por isso não entram nos gráficos de categoria de defeito.</li>
      <li>Divergências apontadas são indícios para verificação com as áreas, não conclusões
      administrativas.</li>
    </ul>`;
}

/* ---------------- navegação ---------------- */

function montarNavegacao() {
  $$('.grupo-nav button').forEach((botao) => {
    botao.addEventListener('click', () => {
      $$('.grupo-nav button').forEach((x) => x.setAttribute('aria-selected', String(x === botao)));
      $$('.painel').forEach((p) => { p.hidden = p.id !== botao.dataset.painel; });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });

  $('#fechar-gaveta').addEventListener('click', fecharFicha);
  $('#fundo-gaveta').addEventListener('click', fecharFicha);
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && !$('#camada-gaveta').hidden) fecharFicha();
  });
}

montarNavegacao();
carregar();
