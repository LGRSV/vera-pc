/* Equipamentos Especiais — painel de acompanhamento.
   JavaScript sem dependências: os dados vêm dos JSONs em data/. */

const CORES_CRITICIDADE = {
  'Muito Alta': 'var(--muito-alta)',
  'Alta': 'var(--alta)',
  'Média': 'var(--media)',
  'Baixa': 'var(--baixa)',
  'Sem classificação': 'var(--sem-classe)',
};

const ORDEM_CRITICIDADE = ['Muito Alta', 'Alta', 'Média', 'Baixa', 'Sem classificação'];

const DESCRICAO_ALERTA = {
  'SS de 2025 ainda aberta':
    'SS abertas em 2025 que atravessaram o período chuvoso e chegaram ao seco de 2026 sem solução. São os casos mais envelhecidos da carteira. Como a numeração da SS só informa o ano, o tempo em aberto é contado pelo piso — a partir de 31/12 do ano da SS.',
  'Prazo de previsão vencido':
    'A própria planilha registrou uma data de entrega ou substituição que já passou, e o Check não foi movido para "Ok".',
  'SS fechada com pendência aberta':
    'A SS está marcada como CONCLUÍDA, mas o Parecer COEP e/ou o Check continuam indicando pendência. Ou a baixa foi indevida, ou os campos não foram atualizados.',
  'Concluído pelo COEP, não fechado':
    'O COEP já deu o parecer de concluído, mas a SS segue "Em andamento" — normalmente esperando laudo ou confirmação de campo.',
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

const estado = {
  equipamentos: [],
  alertas: [],
  divergencias: [],
  compras: [],
  filtrosEmd: { busca: '', tipo: '', gravidade: '', criticidade: '' },
  meta: null,
  filtros: { busca: '', criticidade: '', regional: '', polo: '', tipo: '', categoria: '', situacao: '' },
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

function categoriaDe(equipamento) {
  return equipamento.analise?.categoria_primaria || '';
}

function estaConcluida(equipamento) {
  return /CONCLU/i.test(equipamento.ss || '');
}

function dataBr(iso) {
  const [a, m, d] = String(iso).split('-');
  return d ? `${d}/${m}/${a}` : iso;
}

function textoBusca(equipamento) {
  if (!equipamento._busca) {
    const a = equipamento.analise || {};
    equipamento._busca = [
      equipamento.ativo, equipamento.localidade, equipamento.polo, equipamento.regional,
      equipamento.ss, equipamento.parecer_coep, equipamento.observacao,
      equipamento.defeito_planilha, equipamento.descricao_ss, equipamento.tipo_nome,
      a.categoria_primaria, a.componente_especifico, a.resumo_tecnico, a.acao_requerida,
      a.causa_raiz, a.pendencia_declarada, a.responsavel_atual,
    ].join(' ').toLowerCase();
  }
  return equipamento._busca;
}

/* ---------------- carregamento ---------------- */

async function carregar() {
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
    $('.conteudo').innerHTML =
      '<article class="cartao bloco"><h4>Não foi possível carregar os dados</h4>' +
      '<p>Os arquivos em <code>data/</code> precisam ser servidos por HTTP. ' +
      'Rode <code>python3 -m http.server</code> na raiz do projeto e abra ' +
      '<code>http://localhost:8000</code>.</p></article>';
    console.error(erro);
    return;
  }

  $('#data-referencia').textContent = dataBr(estado.meta.gerado_em);
  $('#pilula-equipamentos').textContent = estado.meta.total_equipamentos;
  $('#pilula-coep').textContent = estado.meta.equipamentos_com_alerta;
  $('#pilula-emd').textContent = estado.meta.equipamentos_com_divergencia;
  $('#rodape-texto').innerHTML =
    `${estado.meta.total_equipamentos} equipamentos &middot; ` +
    `${estado.meta.total_com_descricao} descrições de SS lidas e categorizadas em ` +
    `${estado.meta.lotes_analisados} lotes &middot; posição de ${dataBr(estado.meta.gerado_em)}. ` +
    `Fonte: planilha “Relação dos Equipamentos Indisponíveis — ETO atualizada”, aba Criticidade por Equipamento.`;

  montarPainel();
  montarFiltros();
  renderTabela();
  montarCoep();
  montarEmd();
  montarCompras();
  montarMetodologia();
}

/* ---------------- painel ---------------- */

function cartaoKpi({ rotulo, valor, nota, classe = '' }) {
  // Valores monetários longos não cabem no corpo padrão do cartão.
  const tamanho = String(valor).length > 11 ? ' longo' : '';
  return `<article class="cartao kpi ${classe}">
    <span class="rotulo">${esc(rotulo)}</span>
    <div class="valor${tamanho}">${esc(valor)}</div>
    ${nota ? `<div class="nota">${esc(nota)}</div>` : ''}
  </article>`;
}

function montarPainel() {
  const m = estado.meta;
  const muitoAlta = m.por_criticidade.find((i) => i.rotulo === 'Muito Alta')?.total ?? 0;
  const alta = m.por_criticidade.find((i) => i.rotulo === 'Alta')?.total ?? 0;
  const semClasse = m.por_criticidade.find((i) => i.rotulo === 'Sem classificação')?.total ?? 0;

  $('#kpis').innerHTML = [
    cartaoKpi({ rotulo: 'Equipamentos na relação', valor: m.total_equipamentos, nota: `${m.total_com_descricao} com descrição de SS` }),
    cartaoKpi({ rotulo: 'SS em aberto', valor: m.total_abertos, nota: `${m.total_concluidos} já concluídas`, classe: 'atencao' }),
    cartaoKpi({ rotulo: 'Criticidade muito alta', valor: muitoAlta, nota: `+ ${alta} de criticidade alta`, classe: 'destaque' }),
    cartaoKpi({ rotulo: 'Com pendência no COEP', valor: m.equipamentos_com_alerta, nota: `${m.total_alertas} alertas levantados`, classe: 'destaque' }),
    cartaoKpi({ rotulo: 'Sem classificação', valor: semClasse, nota: 'ainda fora da matriz de priorização', classe: 'atencao' }),
  ].join('');

  montarRosca('#rosca-criticidade', m.por_criticidade, (i) => CORES_CRITICIDADE[i.rotulo] || 'var(--marca)');
  montarBarras('#barras-categoria', m.por_categoria);
  montarBarras('#barras-regional', m.por_regional);
  montarBarras('#barras-responsavel', m.por_responsavel);
  montarBarras('#barras-status', m.por_status_operacional);
  montarBarras('#barras-polo', m.por_polo.filter((i) => i.rotulo !== 'Não informado').slice(0, 10));
  montarMatriz();
}

function montarRosca(seletor, itens, corDe) {
  const total = itens.reduce((s, i) => s + i.total, 0) || 1;
  const raio = 62, espessura = 22, circunferencia = 2 * Math.PI * raio;
  let acumulado = 0;

  const fatias = itens.map((item) => {
    const fracao = item.total / total;
    const traco = `${(fracao * circunferencia).toFixed(2)} ${circunferencia.toFixed(2)}`;
    const deslocamento = -(acumulado * circunferencia).toFixed(2);
    acumulado += fracao;
    return `<circle cx="80" cy="80" r="${raio}" fill="none" stroke="${corDe(item)}"
      stroke-width="${espessura}" stroke-dasharray="${traco}" stroke-dashoffset="${deslocamento}"
      transform="rotate(-90 80 80)"><title>${esc(item.rotulo)}: ${item.total}</title></circle>`;
  }).join('');

  $(seletor).innerHTML = `
    <svg width="160" height="160" viewBox="0 0 160 160" role="img" aria-label="Distribuição por criticidade">
      ${fatias}
      <text x="80" y="76" text-anchor="middle" font-size="27" font-weight="700" fill="var(--texto)">${total}</text>
      <text x="80" y="95" text-anchor="middle" font-size="11" fill="var(--texto-suave)">equipamentos</text>
    </svg>
    <div class="rosca-legenda">
      ${itens.map((item) => `<div class="rosca-item">
        <span class="rosca-cor" style="background:${corDe(item)}"></span>
        <span>${esc(item.rotulo)}</span>
        <span class="n">${item.total}</span>
      </div>`).join('')}
    </div>`;
}

function montarBarras(seletor, itens) {
  const maximo = Math.max(...itens.map((i) => i.total), 1);
  $(seletor).innerHTML = itens.map((item) => `
    <div class="barra-linha">
      <span class="barra-rotulo" title="${esc(item.rotulo)}">${esc(item.rotulo)}</span>
      <div class="barra-trilho">
        <div class="barra-preenchida" style="width:${(item.total / maximo * 100).toFixed(1)}%"></div>
      </div>
      <span class="barra-valor">${item.total}</span>
    </div>`).join('');
}

function montarMatriz() {
  const linhas = estado.meta.matriz_categoria_criticidade;
  const maximo = Math.max(...linhas.flatMap((l) => ORDEM_CRITICIDADE.map((c) => l[c] || 0)), 1);

  $('#matriz-categoria').innerHTML = `
    <thead><tr><th>Categoria</th>${ORDEM_CRITICIDADE.map((c) => `<th>${esc(c)}</th>`).join('')}<th>Total</th></tr></thead>
    <tbody>${linhas.map((linha) => {
      const total = ORDEM_CRITICIDADE.reduce((s, c) => s + (linha[c] || 0), 0);
      return `<tr><td>${esc(linha.categoria)}</td>${ORDEM_CRITICIDADE.map((c) => {
        const n = linha[c] || 0;
        if (!n) return '<td class="zero">·</td>';
        const intensidade = 0.12 + (n / maximo) * 0.55;
        return `<td><span class="celula-calor" style="background:color-mix(in srgb, ${CORES_CRITICIDADE[c]} ${(intensidade * 100).toFixed(0)}%, transparent)">${n}</span></td>`;
      }).join('')}<td><strong>${total}</strong></td></tr>`;
    }).join('')}</tbody>`;
}

/* ---------------- filtros e tabela ---------------- */

function montarFiltros() {
  const opcoes = (seletor, valores) => {
    const select = $(seletor);
    valores.forEach((v) => {
      const opcao = document.createElement('option');
      opcao.value = v;
      opcao.textContent = v;
      select.appendChild(opcao);
    });
  };

  const unicos = (fn) => [...new Set(estado.equipamentos.map(fn).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR'));

  opcoes('#f-criticidade', ORDEM_CRITICIDADE.filter((c) => estado.equipamentos.some((e) => e.criticidade === c)));
  opcoes('#f-regional', unicos((e) => e.regional));
  opcoes('#f-polo', unicos((e) => e.polo));
  opcoes('#f-tipo', unicos((e) => e.tipo_nome));
  opcoes('#f-categoria', unicos(categoriaDe));

  const mapa = {
    '#f-busca': 'busca', '#f-criticidade': 'criticidade', '#f-regional': 'regional',
    '#f-polo': 'polo', '#f-tipo': 'tipo', '#f-categoria': 'categoria', '#f-situacao': 'situacao',
  };

  Object.entries(mapa).forEach(([seletor, chave]) => {
    $(seletor).addEventListener('input', (ev) => {
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

function filtrar() {
  const f = estado.filtros;
  const termo = f.busca.trim().toLowerCase();

  return estado.equipamentos.filter((e) => {
    if (f.criticidade && e.criticidade !== f.criticidade) return false;
    if (f.regional && e.regional !== f.regional) return false;
    if (f.polo && e.polo !== f.polo) return false;
    if (f.tipo && e.tipo_nome !== f.tipo) return false;
    if (f.categoria && categoriaDe(e) !== f.categoria) return false;
    if (f.situacao === 'aberta' && estaConcluida(e)) return false;
    if (f.situacao === 'concluida' && !estaConcluida(e)) return false;
    if (f.situacao === 'alerta' && !e.tem_alerta) return false;
    if (termo && !textoBusca(e).includes(termo)) return false;
    return true;
  });
}

function ordenar(lista) {
  const { campo, direcao } = estado.ordenacao;
  const sinal = direcao === 'asc' ? 1 : -1;

  const valorDe = (e) => {
    if (campo === 'categoria') return categoriaDe(e);
    if (campo === 'criticidade') return ORDEM_CRITICIDADE.indexOf(e.criticidade);
    return e[campo];
  };

  return [...lista].sort((a, b) => {
    const va = valorDe(a), vb = valorDe(b);
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * sinal;
    return String(va ?? '').localeCompare(String(vb ?? ''), 'pt-BR') * sinal;
  });
}

function renderTabela() {
  const lista = ordenar(filtrar());

  $$('#tabela-equipamentos thead th').forEach((th) => {
    if (th.dataset.ordenar === estado.ordenacao.campo) {
      th.setAttribute('aria-sort', estado.ordenacao.direcao === 'asc' ? 'ascending' : 'descending');
      th.querySelector('.seta').textContent = estado.ordenacao.direcao === 'asc' ? '↑' : '↓';
    } else {
      th.removeAttribute('aria-sort');
      th.querySelector('.seta').textContent = '↕';
    }
  });

  $('#contador-resultado').textContent =
    `${lista.length} de ${estado.equipamentos.length} equipamentos`;
  $('#tabela-vazia').hidden = lista.length > 0;

  $('#corpo-tabela').innerHTML = lista.map((e) => {
    const concluida = estaConcluida(e);
    return `<tr data-ativo="${esc(e.ativo)}">
      <td class="mono">${esc(e.ativo)}${e.tem_alerta ? ' <span class="etiqueta alerta">!</span>' : ''}</td>
      <td>${esc(e.tipo_nome)}</td>
      <td>${esc(e.localidade || '—')}</td>
      <td>${esc(e.regional || '—')}</td>
      <td class="mono">${concluida ? '<span class="etiqueta neutra">Concluída</span>' : esc(e.ss)}</td>
      <td class="truncar" title="${esc(categoriaDe(e))}">${esc(categoriaDe(e) || '—')}</td>
      <td><strong>${e.priorizacao || '—'}</strong></td>
      <td><span class="etiqueta crit-${chaveClasse(e.criticidade)}">${esc(e.criticidade)}</span></td>
      <td class="truncar" title="${esc(e.parecer_coep)}">${esc(e.parecer_coep || '—')}</td>
    </tr>`;
  }).join('');

  $$('#corpo-tabela tr').forEach((tr) => {
    tr.addEventListener('click', () => abrirDetalhe(tr.dataset.ativo));
  });
}

/* ---------------- gaveta de detalhe ---------------- */

const NOMES_PREMISSAS = {
  P1: 'Premissa 1', P2: 'Premissa 2', P3: 'Premissa 3', P4: 'Premissa 4',
  P5: 'Premissa 5', P6: 'Premissa 6', P7: 'Premissa 7', P8: 'Premissa 8',
};

function realcarPareceres(texto) {
  return esc(texto)
    .replace(/(PARECER COEP:|PARECER DMSL:|FEEDBACK EQUIP\. ESPECIAIS)/gi, '<mark>$1</mark>');
}

function bloco(titulo, conteudo) {
  return `<article class="cartao bloco"><h4>${esc(titulo)}</h4>${conteudo}</article>`;
}

function par(chave, valor) {
  return `<div class="par"><span class="chave">${esc(chave)}</span>
    <span class="valor">${valor ?? '—'}</span></div>`;
}

function abrirDetalhe(ativo) {
  const e = estado.equipamentos.find((x) => x.ativo === ativo);
  if (!e) return;
  const a = e.analise;
  const alertas = estado.alertas.filter((x) => x.ativo === ativo);
  const divergencias = estado.divergencias.filter((x) => x.ativo === ativo);

  $('#gaveta-titulo').textContent = e.ativo;
  $('#gaveta-sub').innerHTML =
    `${esc(e.tipo_nome)} &middot; ${esc(e.localidade || 'localidade não informada')} &middot; ` +
    `${esc(e.polo || '—')} / ${esc(e.regional || '—')} &middot; ` +
    `<span class="etiqueta crit-${chaveClasse(e.criticidade)}">${esc(e.criticidade)}</span>`;

  const partes = [];

  if (alertas.length) {
    partes.push(bloco('Pendências identificadas', alertas.map((al) => `
      <div class="aviso ${al.gravidade === 'Média' ? 'suave' : ''}" style="margin-bottom:8px">
        <div><strong>${esc(al.tipo_alerta)}</strong>
        ${al.dias_atraso ? `<span class="atraso"> — ${al.dias_atraso} dias de atraso</span>` : ''}
        <br>${esc(al.detalhe)}</div>
      </div>`).join('')));
  }

  partes.push(bloco('Identificação', `<div class="pares">
    ${par('SS aberta', `<span class="mono">${esc(e.ss || '—')}</span>`)}
    ${par('Parecer COEP', esc(e.parecer_coep || '—'))}
    ${par('Check de conclusão', esc(e.check || '—'))}
    ${par('Observação', esc(e.observacao || '—'))}
    ${par('Defeito (planilha)', esc(e.defeito_planilha || '—'))}
    ${par('Pontuação de priorização', `<strong>${e.priorizacao || '—'}</strong>`)}
    ${par('Linha na planilha', e.linha_planilha)}
  </div>`));

  if (a) {
    partes.push(bloco('Categorização da descrição da SS', `
      <div class="marcadores" style="margin-bottom:14px">
        <span class="etiqueta neutra">${esc(a.categoria_primaria)}</span>
        ${(a.categorias_secundarias || []).map((c) => `<span class="etiqueta neutra">${esc(c)}</span>`).join('')}
        ${a.risco_operacional ? `<span class="etiqueta crit-${chaveClasse(a.risco_operacional === 'Crítico' ? 'Muito Alta' : a.risco_operacional)}">Risco ${esc(a.risco_operacional)}</span>` : ''}
      </div>
      <p style="margin:0 0 14px;font-size:14px">${esc(a.resumo_tecnico || '')}</p>
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
        <div><strong>Divergência com a planilha:</strong> ${esc(a.divergencia_planilha)}</div></div>` : ''}`));

    if (a.datas_citadas?.length) {
      partes.push(bloco('Datas e compromissos citados na SS', `<div class="linha-tempo">
        ${a.datas_citadas.map((d) => `<div class="evento">
          <span class="data">${esc(dataBr(d.data))}</span>
          <span class="o-que">${esc(d.o_que)}</span>
        </div>`).join('')}</div>`));
    }
  }

  if (e.compras?.length) {
    const total = e.compras.reduce((s, i) => s + i.valor_total, 0);
    partes.push(bloco('Plano de compras de 17/07/2026', `
      <div class="premissas">
        ${e.compras.map((i) => `<div class="premissa">
          <span class="nome">${esc(i.material)} <span style="color:var(--texto-fraco)">· ${esc(i.codigo)} · ${i.qtd}x</span><br>
          <span style="font-size:11.5px;color:var(--texto-fraco)">prazo de ${i.prazo_dias} dias — entrega limite ${dataBr(i.data_limite)}, faltam ${i.dias_restantes} dias</span></span>
          <span class="pontos">${moeda(i.valor_total)}</span>
        </div>`).join('')}
        <div class="premissa" style="border-top:1px solid var(--borda);padding-top:7px">
          <span class="nome"><strong>Total</strong></span>
          <span class="pontos">${moeda(total)}</span>
        </div>
      </div>`));
  }

  if (e.emd) {
    partes.push(bloco('Requisição de material (planilha de EMD)', `<div class="pares">
      ${Object.entries(e.emd)
        .filter(([k]) => k !== 'linha_emd')
        .map(([k, v]) => par(k, esc(v)))
        .join('')}
    </div>`));
  } else {
    partes.push(bloco('Requisição de material (planilha de EMD)',
      `<div class="aviso suave"><div>Este ativo <strong>não aparece na planilha de EMD</strong>.
      ${e.parecer_coep.toLowerCase().includes('aquisi')
        ? 'O Parecer COEP declara «' + esc(e.parecer_coep) + '», mas não há requisição correspondente no arquivo analisado.'
        : 'Nenhuma requisição de material foi encontrada para ele.'}</div></div>`));
  }

  if (divergencias.length) {
    partes.push(bloco('Divergências entre planilhas', divergencias.map((d) => `
      <div class="aviso ${['Média', 'Baixa'].includes(d.gravidade) ? 'suave' : ''}" style="margin-bottom:8px">
        <div><strong>${esc(d.tipo)}</strong> — ${esc(d.campo)}<br>${esc(d.detalhe)}
        <div class="comparacao">
          <div><span class="fonte">EMD</span><span class="v">${esc(d.valor_emd || '—')}</span></div>
          <div><span class="fonte">Criticidade</span><span class="v">${esc(d.valor_criticidade || '—')}</span></div>
        </div></div>
      </div>`).join('')));
  }

  if (e.descricao_ss) {
    partes.push(bloco('Descrição integral da SS', `<div class="texto-ss">${realcarPareceres(e.descricao_ss)}</div>`));
  }

  const premissas = Object.entries(e.premissas).filter(([, v]) => v !== null);
  if (premissas.length) {
    partes.push(bloco('Premissas de priorização', `<div class="premissas">
      ${premissas.map(([k, v]) => `<div class="premissa">
        <span class="nome">${esc(NOMES_PREMISSAS[k] || k)}</span>
        <span class="pontos">${v}</span>
      </div>`).join('')}
      <div class="premissa" style="border-top:1px solid var(--borda);padding-top:7px">
        <span class="nome"><strong>Total</strong></span>
        <span class="pontos">${e.priorizacao}</span>
      </div>
    </div>`));
  }

  if (e.obs_analise) {
    partes.push(bloco('Observação após análise', `<p style="margin:0;font-size:13.5px">${esc(e.obs_analise)}</p>`));
  }

  $('#gaveta-corpo').innerHTML = partes.join('');
  $('#fundo-modal').hidden = false;
  document.body.style.overflow = 'hidden';
  $('#fechar-gaveta').focus();
}

function fecharDetalhe() {
  $('#fundo-modal').hidden = true;
  document.body.style.overflow = '';
}

/* ---------------- parecer COEP ---------------- */

function montarCoep() {
  const alertas = estado.alertas;
  const criticos = alertas.filter((a) => a.gravidade === 'Crítica').length;
  const vencidos = alertas.filter((a) => a.dias_atraso);
  const maiorAtraso = Math.max(0, ...vencidos.map((a) => a.dias_atraso));
  const altaCrit = new Set(
    alertas.filter((a) => ['Muito Alta', 'Alta'].includes(a.criticidade)).map((a) => a.ativo)
  ).size;

  $('#kpis-coep').innerHTML = [
    cartaoKpi({ rotulo: 'Equipamentos com pendência', valor: estado.meta.equipamentos_com_alerta, nota: `${alertas.length} alertas no total`, classe: 'destaque' }),
    cartaoKpi({ rotulo: 'SS de anos anteriores', valor: criticos, nota: 'atravessaram o ano sem solução', classe: 'destaque' }),
    cartaoKpi({ rotulo: 'Prazos vencidos', valor: vencidos.length, nota: `maior atraso: ${maiorAtraso} dias`, classe: 'atencao' }),
    cartaoKpi({ rotulo: 'Em criticidade alta ou muito alta', valor: altaCrit, nota: 'prioridade de tratativa', classe: 'atencao' }),
  ].join('');

  const grupos = {};
  alertas.forEach((a) => { (grupos[a.tipo_alerta] ??= []).push(a); });

  const ordemGravidade = ['Crítica', 'Alta', 'Média', 'Baixa'];
  const chaves = Object.keys(grupos).sort((x, y) =>
    ordemGravidade.indexOf(grupos[x][0].gravidade) - ordemGravidade.indexOf(grupos[y][0].gravidade));

  $('#grupos-alertas').innerHTML = chaves.map((tipo) => {
    const itens = grupos[tipo];
    const gravidade = itens[0].gravidade;
    return `<section class="grupo-alerta">
      <div class="grupo-alerta-cabecalho">
        <h3>${esc(tipo)}</h3>
        <span class="etiqueta crit-${gravidade === 'Crítica' ? 'muito-alta' : chaveClasse(gravidade)}">${itens.length}</span>
        <p class="desc">${esc(DESCRICAO_ALERTA[tipo] || '')}</p>
      </div>
      <div class="lista-alertas">
        ${itens.map((a) => `<article class="cartao cartao-alerta" data-ativo="${esc(a.ativo)}">
          <span class="faixa g-${chaveClasse(a.gravidade)}"></span>
          <div class="corpo">
            <div class="topo">
              <span class="ativo">${esc(a.ativo)}</span>
              <span class="etiqueta crit-${chaveClasse(a.criticidade)}">${esc(a.criticidade)}</span>
              ${a.dias_atraso ? `<span class="atraso">${a.dias_atraso} dias de atraso</span>` : ''}
            </div>
            <div class="local">${esc(a.localidade || '—')} &middot; ${esc(a.polo || '—')} / ${esc(a.regional || '—')}</div>
            <p class="detalhe">${esc(a.detalhe)}</p>
            <div class="rodape">
              <span>SS ${esc(a.ss || '—')}</span>
              ${a.observacao ? `<span>${esc(a.observacao)}</span>` : ''}
            </div>
          </div>
        </article>`).join('')}
      </div>
    </section>`;
  }).join('');

  $$('#grupos-alertas .cartao-alerta').forEach((el) => {
    el.addEventListener('click', () => abrirDetalhe(el.dataset.ativo));
  });
}

/* ---------------- cruzamento EMD ---------------- */

const ORDEM_GRAVIDADE = ['Crítica', 'Alta', 'Média', 'Baixa'];

function montarEmd() {
  const m = estado.meta;
  const criticas = estado.divergencias.filter((d) => d.gravidade === 'Crítica').length;

  $('#kpis-emd').innerHTML = [
    cartaoKpi({ rotulo: 'Linhas na planilha de EMD', valor: m.total_emd, nota: `contra ${m.total_equipamentos} equipamentos na relação` }),
    cartaoKpi({ rotulo: 'Divergências encontradas', valor: m.total_divergencias, nota: `em ${m.equipamentos_com_divergencia} equipamentos`, classe: 'destaque' }),
    cartaoKpi({ rotulo: 'Divergências críticas', valor: criticas, nota: 'exigem verificação antes de comprar', classe: 'destaque' }),
    cartaoKpi({ rotulo: 'Em aquisição sem EMD', valor: m.em_aquisicao_sem_emd, nota: `de ${m.em_aquisicao} declarados “em processo de aquisição”`, classe: 'destaque' }),
    cartaoKpi({ rotulo: 'SS em aberto sem EMD', valor: m.abertos_sem_emd, nota: `de ${m.total_abertos} SS abertas`, classe: 'atencao' }),
  ].join('');

  const tipos = [...new Set(estado.divergencias.map((d) => d.tipo))]
    .sort((a, b) => ORDEM_GRAVIDADE.indexOf(gravidadeDoTipo(a)) - ORDEM_GRAVIDADE.indexOf(gravidadeDoTipo(b)));

  const preencher = (seletor, valores) => {
    const select = $(seletor);
    valores.forEach((v) => {
      const opcao = document.createElement('option');
      opcao.value = v;
      opcao.textContent = v;
      select.appendChild(opcao);
    });
  };

  preencher('#f-emd-tipo', tipos);
  preencher('#f-emd-gravidade', ORDEM_GRAVIDADE.filter((g) => estado.divergencias.some((d) => d.gravidade === g)));
  preencher('#f-emd-criticidade', ORDEM_CRITICIDADE.filter((c) => estado.divergencias.some((d) => d.criticidade === c)));

  const mapa = {
    '#f-emd-busca': 'busca', '#f-emd-tipo': 'tipo',
    '#f-emd-gravidade': 'gravidade', '#f-emd-criticidade': 'criticidade',
  };
  Object.entries(mapa).forEach(([seletor, chave]) => {
    $(seletor).addEventListener('input', (ev) => {
      estado.filtrosEmd[chave] = ev.target.value;
      renderDivergencias();
    });
  });

  renderDivergencias();
}

function gravidadeDoTipo(tipo) {
  return estado.divergencias.find((d) => d.tipo === tipo)?.gravidade || 'Baixa';
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

  $('#contador-emd').textContent =
    `${lista.length} de ${estado.divergencias.length} divergências`;

  const grupos = {};
  lista.forEach((d) => { (grupos[d.tipo] ??= []).push(d); });

  const chaves = Object.keys(grupos).sort((x, y) =>
    ORDEM_GRAVIDADE.indexOf(grupos[x][0].gravidade) - ORDEM_GRAVIDADE.indexOf(grupos[y][0].gravidade)
    || grupos[y].length - grupos[x].length);

  if (!chaves.length) {
    $('#grupos-divergencias').innerHTML =
      '<p class="vazio">Nenhuma divergência corresponde aos filtros.</p>';
    return;
  }

  $('#grupos-divergencias').innerHTML = chaves.map((tipo) => {
    const itens = grupos[tipo];
    const gravidade = itens[0].gravidade;
    return `<section class="grupo-alerta">
      <div class="grupo-alerta-cabecalho">
        <h3>${esc(tipo)}</h3>
        <span class="etiqueta crit-${gravidade === 'Crítica' ? 'muito-alta' : chaveClasse(gravidade)}">${itens.length}</span>
        <p class="desc">${esc(DESCRICAO_DIVERGENCIA[tipo] || '')}</p>
      </div>
      <div class="lista-alertas">
        ${itens.map((d) => `<article class="cartao cartao-alerta" data-ativo="${esc(d.ativo)}">
          <span class="faixa g-${chaveClasse(d.gravidade)}"></span>
          <div class="corpo">
            <div class="topo">
              <span class="ativo">${esc(d.ativo)}</span>
              <span class="etiqueta crit-${chaveClasse(d.criticidade)}">${esc(d.criticidade)}</span>
              ${d.dias_atraso ? `<span class="atraso">${d.dias_atraso} dias</span>` : ''}
            </div>
            <div class="local">${esc(d.localidade || '—')} &middot; ${esc(d.polo || '—')} / ${esc(d.regional || '—')}</div>
            <p class="detalhe">${esc(d.detalhe)}</p>
            <div class="comparacao">
              <div><span class="fonte">EMD</span><span class="v">${esc(d.valor_emd || '—')}</span></div>
              <div><span class="fonte">Criticidade</span><span class="v">${esc(d.valor_criticidade || '—')}</span></div>
            </div>
          </div>
        </article>`).join('')}
      </div>
    </section>`;
  }).join('');

  $$('#grupos-divergencias .cartao-alerta').forEach((el) => {
    el.addEventListener('click', () => abrirDetalhe(el.dataset.ativo));
  });
}

/* ---------------- plano de compras ---------------- */

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

function moeda(valor) {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function montarCompras() {
  const c = estado.meta.compras;
  $('#pilula-compras').textContent = c.total_ativos;

  $('#kpis-compras').innerHTML = [
    cartaoKpi({ rotulo: 'Valor do pedido', valor: moeda(c.valor_total), nota: `${c.total_pecas} peças em ${c.total_itens} itens` }),
    cartaoKpi({ rotulo: 'Equipamentos atendidos', valor: c.total_ativos, nota: 'todos de criticidade alta ou muito alta' }),
    cartaoKpi({ rotulo: 'Dias desde o pedido', valor: c.dias_decorridos, nota: `pedido em ${dataBr(c.data_pedido)}` }),
    cartaoKpi({ rotulo: 'Pedidos sem EMD', valor: c.ativos_sem_emd, nota: 'sem requisição formal correspondente', classe: 'atencao' }),
    cartaoKpi({ rotulo: 'Valor a reconferir', valor: moeda(c.valor_em_revisao), nota: 'equipamentos já dados como resolvidos', classe: 'destaque' }),
  ].join('');

  $('#prazos-compras').innerHTML = Object.entries(c.prazos).map(([tipo, p]) => {
    const decorrido = Math.min(100, (c.dias_decorridos / p.prazo_dias) * 100);
    return `<article class="cartao prazo">
      <h3>${esc(tipo)}</h3>
      <p class="contrato">${p.prazo_dias} dias a partir do pedido &middot; ${p.pecas} peças &middot; ${moeda(p.valor)}</p>
      <div class="prazo-datas">
        <span>${dataBr(c.data_pedido)}</span>
        <span>${dataBr(p.data_limite)}</span>
      </div>
      <div class="prazo-trilho" role="img" aria-label="${c.dias_decorridos} de ${p.prazo_dias} dias decorridos">
        <div class="prazo-decorrido" style="width:${decorrido.toFixed(1)}%"></div>
      </div>
      <div class="prazo-resumo">
        <div><span class="k">Decorridos</span><span class="v">${c.dias_decorridos} dias</span></div>
        <div><span class="k">Restantes</span><span class="v">${p.dias_restantes} dias</span></div>
        <div><span class="k">Entrega limite</span><span class="v">${dataBr(p.data_limite)}</span></div>
      </div>
    </article>`;
  }).join('');

  $('#tabela-materiais tbody').innerHTML = c.por_material.map((m) => `
    <tr>
      <td class="mono">${esc(m.codigo)}</td>
      <td>${esc(m.descricao)}</td>
      <td>${esc(m.tipo)}</td>
      <td class="num">${m.qtd}</td>
      <td class="num">${moeda(m.valor_unitario)}</td>
      <td class="num">${moeda(m.valor_total)}</td>
    </tr>`).join('');

  $('#tabela-materiais tfoot').innerHTML = `<tr>
    <td colspan="3">Total</td>
    <td class="num">${c.total_pecas}</td>
    <td></td>
    <td class="num">${moeda(c.valor_total)}</td>
  </tr>`;

  const grupos = {};
  estado.compras.forEach((a) => { (grupos[a.tipo] ??= []).push(a); });
  const chaves = Object.keys(grupos).sort((x, y) =>
    ORDEM_GRAVIDADE.indexOf(grupos[x][0].gravidade) - ORDEM_GRAVIDADE.indexOf(grupos[y][0].gravidade));

  $('#grupos-compras').innerHTML = chaves.map((tipo) => {
    const itens = grupos[tipo];
    const gravidade = itens[0].gravidade;
    return `<section class="grupo-alerta">
      <div class="grupo-alerta-cabecalho">
        <h3>${esc(tipo)}</h3>
        <span class="etiqueta crit-${gravidade === 'Crítica' ? 'muito-alta' : chaveClasse(gravidade)}">${itens.length}</span>
        <p class="desc">${esc(DESCRICAO_COMPRA[tipo] || '')}</p>
      </div>
      <div class="lista-alertas">
        ${itens.map((a) => `<article class="cartao cartao-alerta" data-ativo="${esc(a.ativo)}">
          <span class="faixa g-${chaveClasse(a.gravidade)}"></span>
          <div class="corpo">
            <div class="topo">
              <span class="ativo">${esc(a.ativo)}</span>
              <span class="etiqueta crit-${chaveClasse(a.criticidade)}">${esc(a.criticidade)}</span>
              <span class="valor-envolvido">${moeda(a.valor_envolvido)}</span>
            </div>
            <div class="local">${esc(a.localidade || '—')} &middot; ${esc(a.polo || '—')} / ${esc(a.regional || '—')}</div>
            <p class="detalhe">${esc(a.detalhe)}</p>
            <div class="rodape"><span>${esc(a.materiais)}</span></div>
          </div>
        </article>`).join('')}
      </div>
    </section>`;
  }).join('');

  $$('#grupos-compras .cartao-alerta').forEach((el) => {
    el.addEventListener('click', () => abrirDetalhe(el.dataset.ativo));
  });
}

/* ---------------- metodologia ---------------- */

function montarMetodologia() {
  const m = estado.meta;
  $('#texto-metodologia').innerHTML = `
    <h3>De onde vêm os dados</h3>
    <p>Tudo neste site sai de um único arquivo: a planilha
    <strong>“Relação dos Equipamentos Indisponíveis — ETO atualizada”</strong>, aba
    <strong>Criticidade por Equipamento</strong>. O CSV original está versionado em
    <code>data/raw/</code> e o script <code>scripts/build_data.py</code> reconstrói todos os
    JSONs a partir dele — nenhum número foi digitado à mão.</p>

    <h3>Como a criticidade é calculada</h3>
    <p>A criticidade não foi inventada aqui: ela já vinha da planilha, como soma de oito
    premissas de priorização. O site apenas preserva a pontuação e a classificação originais.
    ${m.por_criticidade.find((i) => i.rotulo === 'Sem classificação')?.total ?? 0} equipamentos
    entraram na relação depois da rodada de classificação e ainda estão
    <strong>sem criticidade atribuída</strong> — eles aparecem como “Sem classificação”.</p>

    <h3>Como as descrições de SS foram categorizadas</h3>
    <p>O campo <em>Descrição SS</em> é texto livre e concentra três vozes coladas sem separador:
    o relato de abertura da SS, os blocos <code>PARECER COEP:</code> e os blocos
    <code>PARECER DMSL:</code> / <code>FEEDBACK EQUIP. ESPECIAIS</code>. São
    ${m.total_com_descricao} descrições, algumas com mais de mil caracteres.</p>
    <p>Elas foram divididas em ${m.lotes_analisados} lotes e lidas integralmente, uma a uma,
    por ${m.lotes_analisados} analistas em paralelo, com a mesma especificação de saída. Cada
    descrição rendeu categoria do defeito, componente, fases afetadas, causa raiz, situação
    operacional, ação necessária, responsável, datas prometidas e — importante — a
    <strong>divergência entre o que o texto diz e o que os campos estruturados da planilha
    registram</strong>.</p>
    <ul>
      <li>A classificação vem da leitura do texto, não de busca por palavra-chave.</li>
      <li>Quando o texto não sustenta uma conclusão, o campo fica marcado como não informado —
      não houve preenchimento por suposição.</li>
      <li>Cada registro carrega um nível de confiança da leitura, visível no detalhe.</li>
    </ul>

    <h3>Como as pendências do COEP foram levantadas</h3>
    <p>A aba Parecer COEP foi cruzada com o Check de conclusão, a data da SS e as previsões
    anotadas na coluna Observação. Cinco regras geram os alertas, todas verificáveis no código:</p>
    <ul>
      <li><strong>SS de 2025 ainda aberta</strong> — o ano na numeração da SS é anterior ao atual
      e não há conclusão.</li>
      <li><strong>Prazo de previsão vencido</strong> — a Observação traz uma data já passada e o
      Check não está “Ok”. As previsões vêm só como dia/mês; assumiu-se o ano corrente.</li>
      <li><strong>SS fechada com pendência aberta</strong> — a SS está CONCLUÍDA mas o Parecer
      COEP ou o Check continuam sinalizando pendência.</li>
      <li><strong>Concluído pelo COEP, não fechado</strong> — o parecer diz concluído e o Check
      não acompanhou.</li>
      <li><strong>Substituído, pendente laudo</strong> — a troca ocorreu em campo e falta o laudo
      da empreiteira.</li>
    </ul>

    <h3>Limites desta análise</h3>
    <ul>
      <li>A posição é de <strong>${dataBr(m.gerado_em)}</strong>. Prazos são calculados contra
      essa data — reprocessar o script atualiza os atrasos.</li>
      <li>As previsões da coluna Observação não trazem ano. Datas de meses já passados foram
      lidas como do ano corrente, o que pode subestimar atrasos de itens mais antigos.</li>
      <li>${m.total_equipamentos - m.total_com_descricao} equipamentos não têm descrição de SS
      (em geral os já concluídos) e por isso não entram nos gráficos de categoria de defeito.</li>
      <li>Divergências apontadas são indícios para verificação com as áreas, não conclusões
      administrativas.</li>
    </ul>`;
}

/* ---------------- navegação e tema ---------------- */

function montarNavegacao() {
  $$('.aba').forEach((aba) => {
    aba.addEventListener('click', () => {
      $$('.aba').forEach((x) => x.setAttribute('aria-selected', String(x === aba)));
      $$('.painel').forEach((p) => { p.hidden = p.id !== aba.dataset.painel; });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });

  $('#fechar-gaveta').addEventListener('click', fecharDetalhe);
  $('#fundo-modal').addEventListener('click', (ev) => {
    if (ev.target === $('#fundo-modal')) fecharDetalhe();
  });
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && !$('#fundo-modal').hidden) fecharDetalhe();
  });
}

function montarTema() {
  const salvo = localStorage.getItem('tema-equipamentos');
  const preferido = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'escuro' : 'claro';
  document.documentElement.dataset.tema = salvo || preferido;

  $('#alternar-tema').addEventListener('click', () => {
    const novo = document.documentElement.dataset.tema === 'escuro' ? 'claro' : 'escuro';
    document.documentElement.dataset.tema = novo;
    localStorage.setItem('tema-equipamentos', novo);
  });
}

montarTema();
montarNavegacao();
carregar();
