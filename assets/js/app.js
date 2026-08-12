/* Equipamentos Especiais — console de operação.
   JavaScript sem dependências: os dados vêm dos JSONs em data/, ou de DADOS_EMBUTIDOS
   quando a página é servida como arquivo único. */

const CORES = {
  'Muito Alta': '#ff5f78',
  'Alta': '#ff9d45',
  'Média': '#ffd45e',
  'Baixa': '#57d69c',
  'Sem classificação': '#6d8296',
};

const ORDEM_CRIT = ['Muito Alta', 'Alta', 'Média', 'Baixa', 'Sem classificação'];
const ORDEM_GRAV = ['Crítica', 'Alta', 'Média', 'Baixa'];

const DESC_ALERTA = {
  'SS de 2025 ainda aberta':
    'SS abertas em 2025 que atravessaram o período chuvoso e chegaram ao seco de 2026 sem solução. O tempo em aberto vem da data real registrada na planilha de gestão; onde ela falta, é contado pelo piso — a partir de 31/12 do ano da SS.',
  'Prazo-limite da SS estourado':
    'A SS tem prazo-limite registrado no próprio sistema (SGM), esse prazo já passou e a SS continua pendente. Diferente da previsão anotada à mão na coluna Observação, este é o prazo formal, definido pela criticidade com que a SS foi aberta.',
  'Prazo de previsão vencido':
    'A própria planilha registrou uma data de entrega ou substituição que já passou, e o Check não foi movido para “Ok”.',
  'SS fechada com pendência aberta':
    'A SS está marcada como CONCLUÍDA, mas o Parecer COEP e/ou o Check continuam indicando pendência. Ou a baixa foi indevida, ou os campos não foram atualizados.',
  'Concluído pelo COEP, não fechado':
    'O COEP já deu o parecer de concluído, mas a SS segue “Em andamento” — normalmente esperando laudo ou confirmação de campo.',
  'Substituído, pendente laudo':
    'O equipamento já foi trocado em campo. O que trava o encerramento é o laudo da empreiteira.',
};

const DESC_DIVERGENCIA = {
  'Aquisição sem requisição':
    'O Parecer COEP declara o equipamento “em processo de aquisição”, mas não existe linha correspondente na planilha de EMD. Sem linha de EMD não há requisição rastreável — o processo de compra pode não ter sido efetivamente aberto, ou está sendo controlado fora deste arquivo.',
  'SS atribuída a outro ativo':
    'O mesmo número de SS aparece nas duas planilhas apontando para equipamentos diferentes. Uma das duas está errada, e o material pode ser destinado ao ativo errado.',
  'Ativo divergente dentro do EMD':
    'A planilha de EMD tem duas colunas “Ativo” e nesta linha elas trazem códigos diferentes. Não dá para saber a qual equipamento a requisição pertence.',
  'Substituição feita, SS aberta':
    'O EMD dá a substituição como concluída, mas a SS de campo continua aberta. Se a troca realmente ocorreu, falta apenas a baixa — e o equipamento está inflando a lista de indisponíveis.',
  'SS concluída, EMD pendente':
    'A planilha de criticidade dá a SS como concluída, mas o EMD ainda marca a substituição ou a entrega como pendente.',
  'Número de SS divergente':
    'As duas planilhas usam números de SS diferentes para o mesmo ativo. Isso é esperado quando uma registra a SS de requisição e a outra a de campo — o problema é não haver campo comum ligando as duas.',
  'Defeito divergente':
    'O defeito descrito no EMD não bate com o da planilha de criticidade. Como é o defeito que define o material a requisitar, a divergência pode gerar compra do item errado.',
  'Criticidade divergente':
    'A criticidade diverge entre as planilhas, ou está em branco no EMD. A fila de prioridade muda conforme a planilha consultada.',
  'Localidade ou polo divergente':
    'Localidade ou polo diferentes entre as planilhas — afeta o depósito de destino e a equipe acionada.',
  'Entrega atrasada': 'O material chegou depois da data prevista registrada no próprio EMD.',
  'Cadastro incompleto no EMD':
    'Campos de controle em branco (número de EMD, obra, modelo, SS). Sem eles a requisição não é rastreável da abertura até a entrega.',
  'Incoerência interna do EMD':
    'A própria linha do EMD se contradiz — por exemplo, substituição concluída com equipamento não entregue.',
};

const DESC_COMPRA = {
  'Compra possivelmente desnecessária':
    'O Parecer COEP já registra o equipamento como substituído ou concluído. Se a troca ocorreu depois do pedido, o material vira sobressalente — vale confirmar com o COCM antes de a compra avançar.',
  'Comprado sem requisição de EMD':
    'O ativo entrou no plano de compras mas não tem linha na planilha de EMD. A compra foi pedida sem a requisição formal correspondente.',
  'Status do plano desatualizado':
    'O status congelado no plano (foto de 17/07/2026) já não corresponde ao Parecer COEP atual. Não é erro do plano, é defasagem.',
  'SS divergente no plano':
    'O plano cita uma SS diferente da registrada na planilha de criticidade para o mesmo ativo.',
};

const estado = {
  equipamentos: [], alertas: [], divergencias: [], compras: [], meta: null,
  filtros: { busca: '', criticidade: '', regional: '', polo: '', tipo: '', categoria: '', potencia: '', tensao: '', situacao: '' },
  filtrosEmd: { busca: '', tipo: '', gravidade: '', criticidade: '' },
  ordemDesc: true,
  selecionado: null,
};

/* ---------------- utilidades ---------------- */

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const chave = (t) => String(t ?? '').toLowerCase().normalize('NFD')
  .replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

const categoriaDe = (e) => e.analise?.categoria_primaria || '';
const concluida = (e) => /CONCLU/i.test(e.ss || '');
const potenciaDe = (e) => e.especificacao?.faixa_potencia || '';
const tensaoDe = (e) => e.especificacao?.classe_tensao || '';

function dataBr(iso) {
  const [a, m, d] = String(iso).split('-');
  return d ? `${d}/${m}/${a}` : iso;
}

const moeda = (v) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const numero = (v) => v.toLocaleString('pt-BR');

function textoBusca(e) {
  if (!e._b) {
    const a = e.analise || {}, s = e.especificacao || {};
    e._b = [e.ativo, e.localidade, e.polo, e.regional, e.ss, e.parecer_coep, e.observacao,
      e.defeito_planilha, e.descricao_ss, e.tipo_nome, a.categoria_primaria,
      a.componente_especifico, a.resumo_tecnico, a.acao_requerida, a.causa_raiz,
      a.pendencia_declarada, a.responsavel_atual, s.marca_modelo, s.alimentador,
    ].join(' ').toLowerCase();
  }
  return e._b;
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
      $('.area').innerHTML = '<article class="prosa"><h3>Não foi possível carregar os dados</h3>' +
        '<p>Os arquivos em <code>data/</code> precisam ser servidos por HTTP. Rode ' +
        '<code>python3 -m http.server 8000</code> na raiz do projeto.</p></article>';
      console.error(erro);
      return;
    }
  }

  const m = estado.meta;
  $('#posicao').textContent = `POSIÇÃO ${dataBr(m.gerado_em)}`;
  $('#s-equip').textContent = m.total_equipamentos;
  $('#s-coep').textContent = m.equipamentos_com_alerta;
  $('#s-emd').textContent = m.equipamentos_com_divergencia;
  $('#s-compras').textContent = m.compras.total_ativos;
  $('#s-frota').textContent = m.gestao.com_especificacao;

  const vencidos = estado.alertas.filter((a) => a.dias_atraso).length;
  $('#tira').innerHTML = [
    ['Equipamentos', m.total_equipamentos, ''],
    ['SS em aberto', m.total_abertos, 't-atencao'],
    ['Muito alta', m.por_criticidade.find((i) => i.rotulo === 'Muito Alta')?.total ?? 0, 't-critico'],
    ['Pendências COEP', m.equipamentos_com_alerta, 't-critico'],
    ['Prazos vencidos', vencidos, 't-critico'],
    ['Divergências', m.total_divergencias, 't-atencao'],
    ['Plano de compras', moeda(m.compras.valor_total), 't-marca'],
  ].map(([k, v, t]) => `<div class="${t}"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');

  montarVisao();
  montarFiltros();
  renderLista();
  montarCoep();
  montarEmd();
  montarCompras();
  montarFrota();
  montarMetodo();
}

/* ---------------- componentes ---------------- */

function ind({ rotulo, valor, nota, tom = '' }) {
  const longo = String(valor).length > 11 ? ' longo' : '';
  return `<article class="ind ${tom}"><span>${esc(rotulo)}</span>
    <strong class="${longo.trim()}">${esc(valor)}</strong>
    ${nota ? `<small>${esc(nota)}</small>` : ''}</article>`;
}

function barras(sel, itens) {
  const max = Math.max(...itens.map((i) => i.total), 1);
  $(sel).innerHTML = itens.map((i) => `<div class="barra">
    <div><span>${esc(i.rotulo)}</span><strong>${i.total}</strong></div>
    <i><b style="width:${(i.total / max * 100).toFixed(1)}%"></b></i></div>`).join('');
}

function rosca(sel, itens) {
  const total = itens.reduce((s, i) => s + i.total, 0) || 1;
  const r = 58, esp = 22, circ = 2 * Math.PI * r;
  let acc = 0;
  const fatias = itens.map((i) => {
    const f = i.total / total;
    const t = `${(f * circ).toFixed(2)} ${circ.toFixed(2)}`;
    const o = -(acc * circ).toFixed(2);
    acc += f;
    return `<circle cx="76" cy="76" r="${r}" fill="none" stroke="${CORES[i.rotulo] || '#37d3d9'}"
      stroke-width="${esp}" stroke-dasharray="${t}" stroke-dashoffset="${o}"
      transform="rotate(-90 76 76)"><title>${esc(i.rotulo)}: ${i.total}</title></circle>`;
  }).join('');

  $(sel).innerHTML = `<svg width="152" height="152" viewBox="0 0 152 152" role="img"
    aria-label="Distribuição por criticidade">${fatias}
    <text x="76" y="76" text-anchor="middle" font-family="ui-monospace,monospace" font-size="27"
      font-weight="600" fill="#e3edf7">${total}</text>
    <text x="76" y="93" text-anchor="middle" font-family="ui-monospace,monospace" font-size="8"
      letter-spacing="1.4" fill="#63788c">EQUIPAMENTOS</text></svg>
    <div class="legenda">${itens.map((i) => `<div>
      <i style="background:${CORES[i.rotulo] || '#37d3d9'}"></i><span>${esc(i.rotulo)}</span><b>${i.total}</b>
    </div>`).join('')}</div>`;
}

/* ---------------- visão geral ---------------- */

function montarVisao() {
  const m = estado.meta;
  const pega = (r) => m.por_criticidade.find((i) => i.rotulo === r)?.total ?? 0;

  $('#ind-visao').innerHTML = [
    ind({ rotulo: 'Equipamentos na relação', valor: m.total_equipamentos, nota: `${m.total_com_descricao} com descrição de SS` }),
    ind({ rotulo: 'SS em aberto', valor: m.total_abertos, nota: `${m.total_concluidos} já concluídas`, tom: 't-atencao' }),
    ind({ rotulo: 'Criticidade muito alta', valor: pega('Muito Alta'), nota: `+ ${pega('Alta')} de criticidade alta`, tom: 't-critico' }),
    ind({ rotulo: 'Pendências no COEP', valor: m.equipamentos_com_alerta, nota: `${m.total_alertas} alertas levantados`, tom: 't-critico' }),
    ind({ rotulo: 'Divergência entre planilhas', valor: m.equipamentos_com_divergencia, nota: `${m.total_divergencias} divergências`, tom: 't-critico' }),
    ind({ rotulo: 'Sem classificação', valor: pega('Sem classificação'), nota: 'fora da matriz de priorização', tom: 't-atencao' }),
  ].join('');

  rosca('#g-criticidade', m.por_criticidade);
  barras('#g-categoria', m.por_categoria);
  barras('#g-potencia', m.gestao.por_faixa_potencia);
  barras('#g-tensao', m.gestao.por_classe_tensao);
  barras('#g-regional', m.por_regional);
  barras('#g-responsavel', m.por_responsavel);
  barras('#g-status', m.por_status_operacional);
  barras('#g-polo', m.por_polo.filter((i) => i.rotulo !== 'Não informado').slice(0, 10));

  const linhas = m.matriz_categoria_criticidade;
  const max = Math.max(...linhas.flatMap((l) => ORDEM_CRIT.map((c) => l[c] || 0)), 1);
  $('#g-matriz').innerHTML = `
    <thead><tr><th>Categoria</th>${ORDEM_CRIT.map((c) => `<th>${esc(c)}</th>`).join('')}<th>Total</th></tr></thead>
    <tbody>${linhas.map((l) => {
      const t = ORDEM_CRIT.reduce((s, c) => s + (l[c] || 0), 0);
      return `<tr><td>${esc(l.categoria)}</td>${ORDEM_CRIT.map((c) => {
        const n = l[c] || 0;
        if (!n) return '<td class="zero">·</td>';
        const op = (0.3 + (n / max) * 0.7).toFixed(2);
        return `<td><span class="calor" style="background:${CORES[c]};opacity:${op}">${n}</span></td>`;
      }).join('')}<td><strong>${t}</strong></td></tr>`;
    }).join('')}</tbody>`;
}

/* ---------------- lista e ficha ---------------- */

function preencher(sel, valores) {
  const el = $(sel);
  valores.forEach((v) => {
    const o = document.createElement('option');
    o.value = v; o.textContent = v;
    el.appendChild(o);
  });
}

function montarFiltros() {
  const unicos = (fn) => [...new Set(estado.equipamentos.map(fn).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b, 'pt-BR'));

  preencher('#f-criticidade', ORDEM_CRIT.filter((c) => estado.equipamentos.some((e) => e.criticidade === c)));
  preencher('#f-regional', unicos((e) => e.regional));
  preencher('#f-polo', unicos((e) => e.polo));
  preencher('#f-tipo', unicos((e) => e.tipo_nome));
  preencher('#f-categoria', unicos(categoriaDe));
  preencher('#f-potencia', estado.meta.gestao.por_faixa_potencia.map((i) => i.rotulo));
  preencher('#f-tensao', estado.meta.gestao.por_classe_tensao.map((i) => i.rotulo));

  const mapa = {
    '#f-busca': 'busca', '#f-criticidade': 'criticidade', '#f-regional': 'regional',
    '#f-polo': 'polo', '#f-tipo': 'tipo', '#f-categoria': 'categoria',
    '#f-potencia': 'potencia', '#f-tensao': 'tensao', '#f-situacao': 'situacao',
  };
  Object.entries(mapa).forEach(([sel, k]) => {
    $(sel).addEventListener('input', (ev) => { estado.filtros[k] = ev.target.value; renderLista(); });
  });

  $('#limpar').addEventListener('click', () => {
    Object.keys(estado.filtros).forEach((k) => { estado.filtros[k] = ''; });
    Object.keys(mapa).forEach((s) => { $(s).value = ''; });
    renderLista();
  });

  $('#ordenar').addEventListener('click', () => {
    estado.ordemDesc = !estado.ordemDesc;
    $('#ordenar').textContent = estado.ordemDesc ? 'Prioridade ↓' : 'Prioridade ↑';
    renderLista();
  });
}

function filtrar() {
  const f = estado.filtros;
  const termo = f.busca.trim().toLowerCase();
  return estado.equipamentos.filter((e) => {
    if (f.criticidade && e.criticidade !== f.criticidade) return false;
    if (f.regional && e.regional !== f.regional) return false;
    if (f.polo && e.polo !== f.polo) return false;
    if (f.tipo && e.tipo_nome !== f.tipo) return false;
    if (f.categoria && categoriaDe(e) !== f.categoria) return false;
    if (f.potencia && potenciaDe(e) !== f.potencia) return false;
    if (f.tensao && tensaoDe(e) !== f.tensao) return false;
    if (f.situacao === 'aberta' && concluida(e)) return false;
    if (f.situacao === 'concluida' && !concluida(e)) return false;
    if (f.situacao === 'alerta' && !e.tem_alerta) return false;
    if (f.situacao === 'divergencia' && !e.tem_divergencia) return false;
    if (f.situacao === 'compras' && !e.no_plano_compras) return false;
    if (termo && !textoBusca(e).includes(termo)) return false;
    return true;
  });
}

function renderLista() {
  const sinal = estado.ordemDesc ? -1 : 1;
  const lista = filtrar().sort((a, b) =>
    (a.priorizacao - b.priorizacao) * sinal || a.ativo.localeCompare(b.ativo));

  $('#contador').textContent = `${lista.length} / ${estado.equipamentos.length}`;

  if (!lista.length) {
    $('#lista').innerHTML = '<div class="vazio"><strong>Nenhum equipamento</strong><span>Nenhum registro corresponde aos filtros.</span></div>';
    $('#ficha').innerHTML = '<div class="vazio"><strong>Sem seleção</strong><span>Ajuste os filtros para ver um equipamento.</span></div>';
    return;
  }

  $('#lista').innerHTML = lista.map((e) => {
    const dias = e.ss_sgm?.dias_aberta;
    return `<div class="item c-${chave(e.criticidade)}" data-ativo="${esc(e.ativo)}"
      ${e.ativo === estado.selecionado ? 'aria-current="true"' : ''}>
      <i></i>
      <div>
        <div class="cod">${esc(e.ativo)}${e.tem_alerta ? ' <span class="alerta-ponto">●</span>' : ''}</div>
        <div class="onde">${esc(e.localidade || '—')} · ${esc(e.regional || '—')}</div>
      </div>
      <div class="dir">
        <b>${e.priorizacao || '—'}</b>
        <small>${dias != null ? `${dias}d` : (concluida(e) ? 'OK' : '—')}</small>
      </div>
    </div>`;
  }).join('');

  $$('#lista .item').forEach((el) => {
    el.addEventListener('click', () => selecionar(el.dataset.ativo));
  });

  if (!lista.some((e) => e.ativo === estado.selecionado)) selecionar(lista[0].ativo);
  else renderFicha();
}

function selecionar(ativo) {
  estado.selecionado = ativo;
  $$('#lista .item').forEach((el) => {
    if (el.dataset.ativo === ativo) el.setAttribute('aria-current', 'true');
    else el.removeAttribute('aria-current');
  });
  renderFicha();
}

function irParaAtivo(ativo) {
  Object.keys(estado.filtros).forEach((k) => { estado.filtros[k] = ''; });
  ['#f-busca', '#f-criticidade', '#f-regional', '#f-polo', '#f-tipo',
   '#f-categoria', '#f-potencia', '#f-tensao', '#f-situacao'].forEach((s) => { $(s).value = ''; });
  estado.selecionado = ativo;
  abrirPainel('p-equipamentos');
  renderLista();
  const alvo = $(`#lista .item[data-ativo="${ativo}"]`);
  if (alvo) alvo.scrollIntoView({ block: 'center' });
}

const secao = (titulo, corpo) => `<section class="secao"><h3>${esc(titulo)}</h3><div>${corpo}</div></section>`;
const par = (k, v) => `<div class="par"><span>${esc(k)}</span><b>${v ?? '—'}</b></div>`;

const realcar = (t) => esc(t)
  .replace(/(PARECER COEP:|PARECER DMSL:|FEEDBACK EQUIP\. ESPECIAIS)/gi, '<mark>$1</mark>');

function renderFicha() {
  const e = estado.equipamentos.find((x) => x.ativo === estado.selecionado);
  if (!e) return;
  const a = e.analise, s = e.especificacao;
  const alertas = estado.alertas.filter((x) => x.ativo === e.ativo);
  const divergencias = estado.divergencias.filter((x) => x.ativo === e.ativo);
  const achados = estado.compras.filter((x) => x.ativo === e.ativo);

  const partes = [];

  if (alertas.length || achados.length) {
    partes.push(secao('Pendências identificadas', [...alertas, ...achados].map((x) => `
      <div class="aviso ${['Média', 'Baixa'].includes(x.gravidade) ? 'suave' : ''}">
        <strong>${esc(x.tipo_alerta || x.tipo)}${x.dias_atraso ? ` · ${x.dias_atraso} dias de atraso` : ''}</strong>
        ${esc(x.detalhe)}</div>`).join('')));
  }

  if (a) {
    partes.push(secao('Categorização do defeito', `
      <p style="margin:0 0 14px;font-size:13px;line-height:1.7;color:var(--texto-fraco)">${esc(a.resumo_tecnico || '')}</p>
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
      partes.push(secao('Datas citadas na SS', `<div class="tempo">${a.datas_citadas.map((d) =>
        `<div><i></i><time>${esc(dataBr(d.data))}</time><span>${esc(d.o_que)}</span></div>`).join('')}</div>`));
    }
  }

  if (s) {
    const campos = [
      ['Família', s.familia], ['Marca / modelo', s.marca_modelo], ['Parte ativa', s.parte_ativa],
      ['Controlador', s.controlador], ['Tipo de instalação', s.tipo_instalacao],
      ['Alimentador', s.alimentador], ['Classe de tensão', s.classe_tensao],
      ['Tensão', s.tensao_kv || s.tensao_primaria],
      ['Potência (kvar)', s.potencia_kvar], ['Faixa de potência', s.faixa_potencia],
      ['Corrente (A)', s.corrente_a], ['Tensão de controle (V)', s.tensao_controle_v],
      ['Automatizado', s.automatizado], ['Descrição', s.descricao], ['Estudo', s.estudo],
      ['Autor do estudo', s.autor_estudo],
      ['Data do estudo', s.data_estudo ? dataBr(s.data_estudo) : ''],
    ].filter(([, v]) => v && v !== 'Não se aplica');

    partes.push(secao('Especificação técnica', `
      <div class="pares">${campos.map(([k, v]) => par(k, esc(v))).join('')}</div>
      ${s.ajustes ? `<div style="margin-top:16px"><span style="display:block;margin-bottom:10px;color:var(--texto-tenue);font:600 8.5px var(--mono);letter-spacing:.1em;text-transform:uppercase">Ajustes de proteção</span>
        <div class="pares">${Object.entries(s.ajustes).filter(([, v]) => v)
          .map(([k, v]) => par(k, esc(v))).join('')}</div></div>` : ''}`));
  }

  if (e.ss_sgm) {
    const x = e.ss_sgm;
    partes.push(secao('SS no sistema (SGM)', `
      ${x.sla_estourado ? `<div class="aviso" style="margin-bottom:14px"><strong>Prazo-limite estourado</strong>
        A SS tinha prazo até ${dataBr(x.data_limite)} e está ${x.dias_sla} dias além do prazo.</div>` : ''}
      <div class="pares">
        ${par('Número da SS', esc(x.numero || '—'))}
        ${par('Criticidade no sistema', esc(x.criticidade_ss || '—'))}
        ${par('Situação', esc(x.situacao || '—'))}
        ${par('Órgão solicitante', esc(x.org_solicitante || '—'))}
        ${par('Abertura', x.data_abertura ? dataBr(x.data_abertura) : '—')}
        ${par('Prazo-limite', x.data_limite ? dataBr(x.data_limite) : '—')}
        ${par('Dias em aberto', x.dias_aberta != null ? `${x.dias_aberta} dias` : '—')}
      </div>`));
  }

  partes.push(secao('Registro na planilha de criticidade', `<div class="pares">
    ${par('SS aberta', esc(e.ss || '—'))}
    ${par('Parecer COEP', esc(e.parecer_coep || '—'))}
    ${par('Check de conclusão', esc(e.check || '—'))}
    ${par('Observação', esc(e.observacao || '—'))}
    ${par('Defeito (planilha)', esc(e.defeito_planilha || '—'))}
    ${par('Pontuação de priorização', e.priorizacao || '—')}
    ${par('Linha na planilha', e.linha_planilha)}
  </div>`));

  if (e.compras?.length) {
    const total = e.compras.reduce((sm, i) => sm + i.valor_total, 0);
    partes.push(secao('Plano de compras de 17/07/2026', `<div class="linhas">
      ${e.compras.map((i) => `<div class="linha">
        <span>${esc(i.material)}<small>${esc(i.codigo)} · ${i.qtd}x · prazo de ${i.prazo_dias} dias — limite ${dataBr(i.data_limite)}, faltam ${i.dias_restantes} dias</small></span>
        <b>${moeda(i.valor_total)}</b></div>`).join('')}
      <div class="linha total"><span><strong>Total</strong></span><b>${moeda(total)}</b></div>
    </div>`));
  }

  if (e.geo) {
    partes.push(secao('Coordenadas', `<div class="pares">
      ${par('Latitude', e.geo.lat.toFixed(6))}
      ${par('Longitude', e.geo.lon.toFixed(6))}
      ${par('UTM 22S (E, N)', `${numero(e.geo.coord_x)}, ${numero(e.geo.coord_y)}`)}
      ${par('Código GIS', esc(e.geo.cod_gis || '—'))}
      ${par('Alimentador', esc(e.geo.alimentador || '—'))}
    </div>`));
  }

  if (e.emd) {
    partes.push(secao('Requisição de material (EMD)', `<div class="pares">
      ${Object.entries(e.emd).filter(([k]) => k !== 'linha_emd').map(([k, v]) => par(k, esc(v))).join('')}
    </div>`));
  } else {
    partes.push(secao('Requisição de material (EMD)',
      `<div class="aviso suave"><strong>Sem linha no EMD</strong>${
        e.parecer_coep.toLowerCase().includes('aquisi')
          ? `O Parecer COEP declara «${esc(e.parecer_coep)}», mas não há requisição correspondente no arquivo analisado.`
          : 'Nenhuma requisição de material foi encontrada para este ativo.'}</div>`));
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
    partes.push(secao('Gestão de equipamentos',
      `<div class="pares">${campos.map(([k, v]) => par(k, esc(v))).join('')}</div>`));
  }

  if (divergencias.length) {
    partes.push(secao('Divergências entre planilhas', divergencias.map((d) => `
      <div class="aviso ${['Média', 'Baixa'].includes(d.gravidade) ? 'suave' : ''}">
        <strong>${esc(d.tipo)} · ${esc(d.campo)}</strong>${esc(d.detalhe)}
        <div class="confronto">
          <div><span>EMD</span><b>${esc(d.valor_emd || '—')}</b></div>
          <div><span>Criticidade</span><b>${esc(d.valor_criticidade || '—')}</b></div>
        </div></div>`).join('')));
  }

  if (e.descricao_ss) {
    partes.push(secao('Descrição integral da SS', `<div class="texto-ss">${realcar(e.descricao_ss)}</div>`));
  }

  const premissas = Object.entries(e.premissas).filter(([, v]) => v !== null);
  if (premissas.length) {
    partes.push(secao('Premissas de priorização', `<div class="linhas">
      ${premissas.map(([k, v]) => `<div class="linha"><span>Premissa ${k.slice(1)}</span><b>${v}</b></div>`).join('')}
      <div class="linha total"><span><strong>Total</strong></span><b>${e.priorizacao}</b></div></div>`));
  }

  const marcas = [
    `<span class="tag c-${chave(e.criticidade)}">${esc(e.criticidade)}</span>`,
    `<span class="tag neutra">${esc(e.tipo_nome)}</span>`,
    categoriaDe(e) ? `<span class="tag marca">${esc(categoriaDe(e))}</span>` : '',
    a?.risco_operacional ? `<span class="tag c-${chave(a.risco_operacional)}">Risco ${esc(a.risco_operacional)}</span>` : '',
    s?.faixa_potencia && s.faixa_potencia !== 'Não se aplica' ? `<span class="tag neutra">${esc(s.faixa_potencia)}</span>` : '',
    s?.classe_tensao ? `<span class="tag neutra">${esc(s.classe_tensao)}</span>` : '',
  ].filter(Boolean).join('');

  $('#ficha').innerHTML = `
    <div class="ficha-topo">
      <div style="min-width:0">
        <div class="cod">${esc(e.ativo)}</div>
        <div class="onde">${esc(e.localidade || 'localidade não informada')} · ${esc(e.polo || '—')} / ${esc(e.regional || '—')}</div>
        <div class="marcas">${marcas}</div>
      </div>
    </div>
    <div class="ficha-corpo">${partes.join('')}</div>`;
}

/* ---------------- grupos de achados ---------------- */

function renderGrupos(sel, itens, campoTipo, descricoes, extras) {
  const grupos = {};
  itens.forEach((i) => { (grupos[i[campoTipo]] ??= []).push(i); });

  const chaves = Object.keys(grupos).sort((x, y) =>
    ORDEM_GRAV.indexOf(grupos[x][0].gravidade) - ORDEM_GRAV.indexOf(grupos[y][0].gravidade)
    || grupos[y].length - grupos[x].length);

  if (!chaves.length) {
    $(sel).innerHTML = '<div class="cartao vazio"><strong>Nada aqui</strong><span>Nenhum registro corresponde aos filtros.</span></div>';
    return;
  }

  $(sel).innerHTML = chaves.map((tipo) => {
    const lista = grupos[tipo];
    const g = lista[0].gravidade;
    return `<section class="grupo"><header>
        <div><h2>${esc(tipo)}</h2>
        <span class="tag c-${g === 'Crítica' ? 'muito-alta' : chave(g)}">${lista.length}</span></div>
        <p>${esc(descricoes[tipo] || '')}</p>
      </header>
      <div class="achados">${lista.map((i) => `
        <article class="achado g-${chave(i.gravidade)}" data-ativo="${esc(i.ativo)}">
          <div>
            <span class="cod">${esc(i.ativo)}</span>
            <span class="tag c-${chave(i.criticidade)}">${esc(i.criticidade)}</span>
            ${i.dias_atraso ? `<span class="atraso">${i.dias_atraso}d de atraso</span>` : ''}
            ${i.valor_envolvido ? `<span class="valor">${moeda(i.valor_envolvido)}</span>` : ''}
          </div>
          <div class="onde">${esc(i.localidade || '—')} · ${esc(i.polo || '—')} / ${esc(i.regional || '—')}</div>
          <p>${esc(i.detalhe)}</p>
          ${extras ? extras(i) : ''}
        </article>`).join('')}</div></section>`;
  }).join('');

  $$(`${sel} .achado`).forEach((el) => {
    el.addEventListener('click', () => irParaAtivo(el.dataset.ativo));
  });
}

/* ---------------- COEP ---------------- */

function montarCoep() {
  const alertas = estado.alertas;
  const criticos = alertas.filter((a) => a.gravidade === 'Crítica').length;
  const vencidos = alertas.filter((a) => a.dias_atraso);
  const maior = Math.max(0, ...vencidos.map((a) => a.dias_atraso));
  const altaCrit = new Set(alertas.filter((a) => ['Muito Alta', 'Alta'].includes(a.criticidade)).map((a) => a.ativo)).size;

  $('#ind-coep').innerHTML = [
    ind({ rotulo: 'Equipamentos com pendência', valor: estado.meta.equipamentos_com_alerta, nota: `${alertas.length} alertas no total`, tom: 't-critico' }),
    ind({ rotulo: 'SS de anos anteriores', valor: criticos, nota: 'atravessaram o ano sem solução', tom: 't-critico' }),
    ind({ rotulo: 'Prazos vencidos', valor: vencidos.length, nota: `maior atraso: ${maior} dias`, tom: 't-atencao' }),
    ind({ rotulo: 'Criticidade alta ou muito alta', valor: altaCrit, nota: 'prioridade de tratativa', tom: 't-atencao' }),
  ].join('');

  renderGrupos('#grupos-coep', alertas, 'tipo_alerta', DESC_ALERTA, (a) =>
    `<div class="rodape"><span>SS ${esc(a.ss || '—')}</span>${a.observacao ? `<span>${esc(a.observacao)}</span>` : ''}</div>`);
}

/* ---------------- EMD ---------------- */

function montarEmd() {
  const m = estado.meta;
  const criticas = estado.divergencias.filter((d) => d.gravidade === 'Crítica').length;

  $('#ind-emd').innerHTML = [
    ind({ rotulo: 'Linhas na planilha de EMD', valor: m.total_emd, nota: `contra ${m.total_equipamentos} equipamentos` }),
    ind({ rotulo: 'Divergências encontradas', valor: m.total_divergencias, nota: `em ${m.equipamentos_com_divergencia} equipamentos`, tom: 't-critico' }),
    ind({ rotulo: 'Divergências críticas', valor: criticas, nota: 'verificar antes de comprar', tom: 't-critico' }),
    ind({ rotulo: 'Em aquisição sem EMD', valor: m.em_aquisicao_sem_emd, nota: `de ${m.em_aquisicao} declarados em aquisição`, tom: 't-critico' }),
    ind({ rotulo: 'SS em aberto sem EMD', valor: m.abertos_sem_emd, nota: `de ${m.total_abertos} SS abertas`, tom: 't-atencao' }),
  ].join('');

  const tipos = [...new Set(estado.divergencias.map((d) => d.tipo))].sort((a, b) =>
    ORDEM_GRAV.indexOf(estado.divergencias.find((d) => d.tipo === a).gravidade)
    - ORDEM_GRAV.indexOf(estado.divergencias.find((d) => d.tipo === b).gravidade));

  preencher('#f-emd-tipo', tipos);
  preencher('#f-emd-gravidade', ORDEM_GRAV.filter((g) => estado.divergencias.some((d) => d.gravidade === g)));
  preencher('#f-emd-criticidade', ORDEM_CRIT.filter((c) => estado.divergencias.some((d) => d.criticidade === c)));

  Object.entries({
    '#f-emd-busca': 'busca', '#f-emd-tipo': 'tipo',
    '#f-emd-gravidade': 'gravidade', '#f-emd-criticidade': 'criticidade',
  }).forEach(([sel, k]) => {
    $(sel).addEventListener('input', (ev) => { estado.filtrosEmd[k] = ev.target.value; renderEmd(); });
  });

  renderEmd();
}

function renderEmd() {
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
  renderGrupos('#grupos-emd', lista, 'tipo', DESC_DIVERGENCIA, (d) => `<div class="confronto">
    <div><span>EMD</span><b>${esc(d.valor_emd || '—')}</b></div>
    <div><span>Criticidade</span><b>${esc(d.valor_criticidade || '—')}</b></div></div>`);
}

/* ---------------- compras ---------------- */

function montarCompras() {
  const c = estado.meta.compras;

  $('#ind-compras').innerHTML = [
    ind({ rotulo: 'Valor do pedido', valor: moeda(c.valor_total), nota: `${c.total_pecas} peças em ${c.total_itens} itens`, tom: 't-marca' }),
    ind({ rotulo: 'Equipamentos atendidos', valor: c.total_ativos, nota: 'todos de criticidade alta ou muito alta' }),
    ind({ rotulo: 'Dias desde o pedido', valor: c.dias_decorridos, nota: `pedido em ${dataBr(c.data_pedido)}` }),
    ind({ rotulo: 'Pedidos sem EMD', valor: c.ativos_sem_emd, nota: 'sem requisição formal correspondente', tom: 't-atencao' }),
    ind({ rotulo: 'Valor a reconferir', valor: moeda(c.valor_em_revisao), nota: 'equipamentos já dados como resolvidos', tom: 't-critico' }),
  ].join('');

  $('#prazos').innerHTML = Object.entries(c.prazos).map(([tipo, p]) => {
    const pct = Math.min(100, (c.dias_decorridos / p.prazo_dias) * 100);
    return `<article class="prazo">
      <span>${p.prazo_dias} dias a partir do pedido</span>
      <h2>${esc(tipo)}</h2>
      <p>${p.pecas} peças · ${moeda(p.valor)}</p>
      <div class="prazo-datas"><span>${dataBr(c.data_pedido)}</span><span>${dataBr(p.data_limite)}</span></div>
      <div class="trilho" role="img" aria-label="${c.dias_decorridos} de ${p.prazo_dias} dias decorridos">
        <div style="width:${pct.toFixed(1)}%"></div></div>
      <div class="prazo-resumo">
        <div><span>Decorridos</span><strong>${c.dias_decorridos}d</strong></div>
        <div><span>Restantes</span><strong>${p.dias_restantes}d</strong></div>
        <div><span>Entrega limite</span><strong>${dataBr(p.data_limite)}</strong></div>
      </div></article>`;
  }).join('');

  $('#t-materiais tbody').innerHTML = c.por_material.map((m) => `<tr>
    <td class="mono">${esc(m.codigo)}</td><td>${esc(m.descricao)}</td><td>${esc(m.tipo)}</td>
    <td class="num">${m.qtd}</td><td class="num">${moeda(m.valor_unitario)}</td>
    <td class="num">${moeda(m.valor_total)}</td></tr>`).join('');

  $('#t-materiais tfoot').innerHTML =
    `<tr><td colspan="3">Total</td><td class="num">${c.total_pecas}</td><td></td><td class="num">${moeda(c.valor_total)}</td></tr>`;

  renderGrupos('#grupos-compras', estado.compras, 'tipo', DESC_COMPRA, (a) =>
    `<div class="rodape"><span>${esc(a.materiais)}</span></div>`);
}

/* ---------------- mapa e frota ---------------- */

function montarFrota() {
  const g = estado.meta.gestao;
  const comGeo = estado.equipamentos.filter((e) => e.geo);
  const comSs = estado.equipamentos.filter((e) => e.ss_sgm?.dias_aberta != null);

  $('#ind-frota').innerHTML = [
    ind({ rotulo: 'Com especificação técnica', valor: g.com_especificacao, nota: `de ${estado.meta.total_equipamentos} equipamentos` }),
    ind({ rotulo: 'Com coordenada', valor: g.com_coordenada, nota: 'plotados no mapa', tom: 't-marca' }),
    ind({ rotulo: 'Prazo-limite estourado', valor: g.sla_estourado, nota: `maior atraso: ${g.maior_atraso_sla} dias`, tom: 't-critico' }),
    ind({ rotulo: 'SS mais antiga', valor: `${g.maior_dias_aberta} dias`, nota: `média de ${g.media_dias_pendente} dias pendente`, tom: 't-critico' }),
    ind({ rotulo: 'Valor previsto', valor: moeda(g.valor_previsto_total), nota: `em ${g.com_valor_previsto} equipamentos`, tom: 't-atencao' }),
  ].join('');

  desenharMapa(comGeo);
  barras('#g-modelo', g.por_modelo.slice(0, 10));
  barras('#g-idade', [
    { rotulo: 'até 90 dias', t: (d) => d <= 90 },
    { rotulo: '91 a 180 dias', t: (d) => d > 90 && d <= 180 },
    { rotulo: '181 a 365 dias', t: (d) => d > 180 && d <= 365 },
    { rotulo: 'mais de 1 ano', t: (d) => d > 365 },
  ].map((f) => ({ rotulo: f.rotulo, total: comSs.filter((e) => f.t(e.ss_sgm.dias_aberta)).length })));

  const lista = estado.equipamentos.filter((e) => e.especificacao)
    .sort((a, b) => (b.ss_sgm?.dias_aberta ?? -1) - (a.ss_sgm?.dias_aberta ?? -1));

  $('#t-frota tbody').innerHTML = lista.map((e) => {
    const s = e.especificacao, ss = e.ss_sgm || {};
    return `<tr data-ativo="${esc(e.ativo)}">
      <td class="mono">${esc(e.ativo)}</td>
      <td>${esc(s.familia || '—')}</td>
      <td>${esc(s.marca_modelo || '—')}</td>
      <td class="mono">${esc(s.alimentador || '—')}</td>
      <td class="num">${esc(s.classe_tensao || '—')}</td>
      <td class="num">${esc(s.potencia_kvar ? `${s.potencia_kvar} kvar` : '—')}</td>
      <td>${esc(e.localidade || '—')}</td>
      <td class="num">${ss.sla_estourado ? `<span class="atraso">${ss.dias_aberta}</span>` : (ss.dias_aberta ?? '—')}</td>
      <td><span class="tag c-${chave(e.criticidade)}">${esc(e.criticidade)}</span></td>
    </tr>`;
  }).join('');

  $$('#t-frota tbody tr').forEach((tr) => {
    tr.addEventListener('click', () => irParaAtivo(tr.dataset.ativo));
  });
}

function desenharMapa(itens) {
  if (!itens.length) { $('#mapa').innerHTML = '<div class="vazio"><strong>Sem coordenadas</strong></div>'; return; }

  const margem = 42;
  const lats = itens.map((e) => e.geo.lat), lons = itens.map((e) => e.geo.lon);
  const latMin = Math.min(...lats), latMax = Math.max(...lats);
  const lonMin = Math.min(...lons), lonMax = Math.max(...lons);
  const folgaLat = (latMax - latMin) * 0.04 || 0.1;
  const folgaLon = (lonMax - lonMin) * 0.04 || 0.1;
  const l0 = lonMin - folgaLon, l1 = lonMax + folgaLon;
  const a0 = latMin - folgaLat, a1 = latMax + folgaLat;

  // Projeção equirretangular com o paralelo médio como padrão: um grau de longitude
  // encurta por cos(lat), então sem essa correção o mapa sai esticado na horizontal.
  const escala = Math.cos(((a0 + a1) / 2) * Math.PI / 180);
  const extX = (l1 - l0) * escala, extY = a1 - a0;
  const areaH = 600, areaW = Math.round((areaH * extX) / extY);
  const W = areaW + 2 * margem, H = areaH + 2 * margem;

  const px = (lon) => margem + ((lon - l0) * escala / extX) * areaW;
  const py = (lat) => H - margem - ((lat - a0) / extY) * areaH;

  const grade = [];
  for (let i = 0; i <= 4; i++) {
    const lon = l0 + ((l1 - l0) * i) / 4, lat = a0 + ((a1 - a0) * i) / 4;
    grade.push(`<line class="malha" x1="${px(lon).toFixed(1)}" y1="${margem}" x2="${px(lon).toFixed(1)}" y2="${H - margem}"/>`);
    grade.push(`<line class="malha" x1="${margem}" y1="${py(lat).toFixed(1)}" x2="${(margem + areaW).toFixed(1)}" y2="${py(lat).toFixed(1)}"/>`);
    grade.push(`<text class="eixo" x="${px(lon).toFixed(1)}" y="${H - margem + 15}" text-anchor="middle">${lon.toFixed(2)}°</text>`);
    grade.push(`<text class="eixo" x="${margem - 6}" y="${(py(lat) + 3).toFixed(1)}" text-anchor="end">${lat.toFixed(2)}°</text>`);
  }

  // Muito Alta por último, para ficar por cima na sobreposição.
  const ordenados = [...itens].sort((a, b) =>
    ORDEM_CRIT.indexOf(b.criticidade) - ORDEM_CRIT.indexOf(a.criticidade));

  const pontos = ordenados.map((e) => {
    const cor = CORES[e.criticidade] || CORES['Sem classificação'];
    const r = e.criticidade === 'Muito Alta' ? 7 : e.criticidade === 'Alta' ? 6 : 5;
    const d = e.ss_sgm?.dias_aberta;
    return `<circle class="ponto" data-ativo="${esc(e.ativo)}" cx="${px(e.geo.lon).toFixed(1)}"
      cy="${py(e.geo.lat).toFixed(1)}" r="${r}" fill="${cor}" fill-opacity=".85">
      <title>${esc(e.ativo)} · ${esc(e.localidade)} · ${esc(e.criticidade)}${d != null ? ` — ${d} dias em aberto` : ''}</title>
    </circle>`;
  }).join('');

  $('#mapa').innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="max-width:${W}px;margin:0 auto" role="img"
    aria-label="Distribuição geográfica dos equipamentos indisponíveis">
    <rect x="${margem}" y="${margem}" width="${areaW}" height="${areaH}" fill="#0d1620" stroke="#223140"/>
    ${grade.join('')}${pontos}</svg>`;

  $('#legenda-mapa').innerHTML = ORDEM_CRIT.filter((c) => itens.some((e) => e.criticidade === c))
    .map((c) => `<div><i style="background:${CORES[c]}"></i>${esc(c)}
      <b>${itens.filter((e) => e.criticidade === c).length}</b></div>`).join('');

  $$('#mapa .ponto').forEach((el) => {
    el.addEventListener('click', () => irParaAtivo(el.dataset.ativo));
  });
}

/* ---------------- metodologia ---------------- */

function montarMetodo() {
  const m = estado.meta;
  const semClasse = m.por_criticidade.find((i) => i.rotulo === 'Sem classificação')?.total ?? 0;

  $('#metodo').innerHTML = `
    <h3>De onde vêm os dados</h3>
    <p>Quatro planilhas alimentam este console, todas versionadas em <code>data/raw/</code>: a
    <strong>Relação dos Equipamentos Indisponíveis</strong> (aba Criticidade por Equipamento), a
    planilha de <strong>EMD</strong> (OBRAS_EQ_ESPECIAL), o <strong>Plano de Compras</strong>
    pedido em 17/07/2026 e a <strong>Gestão de Equipamentos</strong>, que traz coordenadas,
    especificação técnica e as datas reais da SS. O script <code>scripts/build_data.py</code>
    reconstrói todos os JSONs a partir delas — nenhum número foi digitado à mão.</p>

    <h3>Criticidade e faixa de potência</h3>
    <p>A criticidade já vinha da planilha, como soma de oito premissas de priorização; o console
    preserva a pontuação original. ${semClasse} equipamentos entraram na relação depois da rodada
    de classificação e seguem <strong>sem criticidade atribuída</strong>.</p>
    <p>A <strong>faixa de potência</strong> vale só para os reguladores de tensão, que são os que
    têm capacidade em kvar na planilha de gestão. O campo aceita um valor único ou um por fase —
    bancos montados com células de capacidades diferentes ficam marcados como
    <em>banco misto</em>, porque não cabem numa faixa só. Os religadores não têm kvar; para eles a
    dimensão comparável é a <strong>classe de tensão</strong>, 13,8 ou 34,5 kV, que o console
    também mostra e filtra.</p>

    <h3>Como as descrições de SS foram categorizadas</h3>
    <p>O campo <em>Descrição SS</em> é texto livre e concentra três vozes coladas sem separador: o
    relato de abertura, os blocos <code>PARECER COEP:</code> e os blocos <code>PARECER DMSL:</code>
    / <code>FEEDBACK EQUIP. ESPECIAIS</code>. São ${m.total_com_descricao} descrições, várias com
    mais de mil caracteres.</p>
    <p>Elas foram divididas em ${m.lotes_analisados} lotes e lidas integralmente, uma a uma, por
    ${m.lotes_analisados} analistas em paralelo, com a mesma especificação de saída. Cada descrição
    rendeu categoria do defeito, componente, fases afetadas, causa raiz, situação operacional, ação
    necessária, responsável, datas prometidas e a <strong>divergência entre o que o texto diz e o
    que os campos estruturados registram</strong>.</p>
    <ul>
      <li>A classificação vem da leitura do texto, não de busca por palavra-chave.</li>
      <li>Quando o texto não sustenta uma conclusão, o campo fica como não informado.</li>
      <li>Cada registro carrega um nível de confiança da leitura, visível na ficha.</li>
    </ul>

    <h3>Pendências do COEP</h3>
    <p>O Parecer COEP foi cruzado com o Check de conclusão, o prazo-limite da SS no sistema, o ano
    da SS e as previsões da coluna Observação. Seis regras geram os alertas, todas verificáveis no
    código do build.</p>

    <h3>Como as planilhas foram casadas</h3>
    <p>A ligação é feita pelo <strong>código do ativo</strong>, não pela SS. As planilhas usam
    numerações de universos diferentes: o EMD registra a SS de requisição do COEP
    (<code>ETO-COEP …</code>) e a de criticidade registra a SS de campo (<code>ETO-RD-…</code>,
    <code>ETO-PROT-…</code>, <code>ETO-TELE-…</code>). Casar por SS produziria falso negativo em
    quase toda a base. Pelo ativo, as ${m.total_emd} linhas do EMD encontraram par.</p>

    <h3>Coordenadas</h3>
    <p>Vêm projetadas em SIRGAS 2000 / UTM 22S, inclusive os pontos a leste do limite da zona, que
    a distribuidora mantém na mesma projeção. A conversão inversa para latitude e longitude é feita
    no build, em Python puro. O mapa usa projeção equirretangular com o paralelo médio como padrão,
    então as distâncias horizontais não saem esticadas.</p>

    <h3>Prazos do plano de compras</h3>
    <p>O pedido de ${dataBr(m.compras.data_pedido)} segue prazo de
    ${m.compras.prazos.Religador.prazo_dias} dias para religador (limite
    ${dataBr(m.compras.prazos.Religador.data_limite)}) e ${m.compras.prazos.Regulador.prazo_dias}
    dias para regulador (limite ${dataBr(m.compras.prazos.Regulador.data_limite)}), contados da
    data do pedido.</p>

    <h3>Limites conhecidos</h3>
    <ul>
      <li>A posição é de <strong>${dataBr(m.gerado_em)}</strong>. Reprocessar o build atualiza os atrasos.</li>
      <li>As previsões da coluna Observação não trazem ano; datas de meses passados foram lidas como
      do ano corrente, o que pode subestimar atrasos antigos.</li>
      <li>O tempo em aberto usa a data real de abertura quando a planilha de gestão a traz; nos
      demais, é contado pelo piso — a partir de 31/12 do ano da SS.</li>
      <li>Só a aba Criticidade por Equipamento foi recebida da planilha de indisponíveis; as abas de
      concluídas pelo DMSL não estavam no arquivo.</li>
      <li>${m.total_equipamentos - m.total_com_descricao} equipamentos não têm descrição de SS (em
      geral os já concluídos) e não entram nos gráficos de categoria de defeito.</li>
      <li>As divergências apontadas são indícios para verificação com as áreas, não conclusões
      administrativas.</li>
    </ul>`;
}

/* ---------------- navegação ---------------- */

function abrirPainel(id) {
  $$('.nav button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.painel === id)));
  $$('.painel').forEach((p) => { p.hidden = p.id !== id; });
}

$$('.nav button').forEach((b) => {
  b.addEventListener('click', () => {
    abrirPainel(b.dataset.painel);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});

carregar();
