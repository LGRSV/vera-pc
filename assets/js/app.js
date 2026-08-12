/* Equipamentos Especiais — interface de pesquisa.
   Uma busca no centro; tudo mais é consequência dela. Os dados vêm dos JSONs em data/,
   ou de DADOS_EMBUTIDOS quando a página é servida como arquivo único. */

const CORES = {
  'Muito Alta': 'var(--muito-alta)', 'Alta': 'var(--alta)', 'Média': 'var(--media)',
  'Baixa': 'var(--baixa)', 'Sem classificação': 'var(--sem-classe)',
};

const ORDEM_CRIT = ['Muito Alta', 'Alta', 'Média', 'Baixa', 'Sem classificação'];
const ORDEM_GRAV = ['Crítica', 'Alta', 'Média', 'Baixa'];

const DESC_ALERTA = {
  'SS de 2025 ainda aberta': 'SS abertas em 2025 que atravessaram o período chuvoso e chegaram ao seco de 2026 sem solução. O tempo em aberto vem da data real registrada na planilha de gestão; onde ela falta, é contado pelo piso — a partir de 31/12 do ano da SS.',
  'Prazo-limite da SS estourado': 'A SS tem prazo-limite registrado no próprio sistema (SGM), esse prazo já passou e a SS continua pendente. Este é o prazo formal, definido pela criticidade com que a SS foi aberta.',
  'Prazo de previsão vencido': 'A planilha registrou uma data de entrega ou substituição que já passou, e o Check não foi movido para “Ok”.',
  'SS fechada com pendência aberta': 'A SS está marcada como CONCLUÍDA, mas o Parecer COEP e/ou o Check continuam indicando pendência. Ou a baixa foi indevida, ou os campos não foram atualizados.',
  'Concluído pelo COEP, não fechado': 'O COEP já deu o parecer de concluído, mas a SS segue “Em andamento” — normalmente esperando laudo ou confirmação de campo.',
  'Substituído, pendente laudo': 'O equipamento já foi trocado em campo. O que trava o encerramento é o laudo da empreiteira.',
};

const DESC_DIVERGENCIA = {
  'Em aquisição, ainda sem EMD': 'O Parecer COEP diz “em processo de aquisição” e ainda não há linha de EMD. Premissa registrada em 12/08: isso é o curso normal — a EMD nasce quando a compra vira requisição de material. Acompanhar a conversão, não tratar como erro.',
  'SS atribuída a outro ativo': 'O mesmo número de SS aparece nas duas planilhas apontando para equipamentos diferentes. Uma das duas está errada.',
  'Ativo divergente dentro do EMD': 'A planilha de EMD tem duas colunas “Ativo” e nesta linha elas trazem códigos diferentes.',
  'Substituição feita, SS aberta': 'O EMD dá a substituição como concluída, mas a SS de campo continua aberta — o equipamento pode estar inflando a lista de indisponíveis.',
  'SS concluída, EMD pendente': 'A planilha de criticidade dá a SS como concluída, mas o EMD ainda marca a substituição ou a entrega como pendente.',
  'Número de SS divergente': 'As duas planilhas usam números de SS diferentes para o mesmo ativo. O problema é não haver campo comum ligando as duas.',
  'Defeito divergente': 'O defeito descrito no EMD não bate com o da planilha de criticidade. Como é o defeito que define o material, a divergência pode gerar compra do item errado.',
  'Criticidade divergente': 'A criticidade diverge entre as planilhas, ou está em branco no EMD.',
  'Localidade ou polo divergente': 'Localidade ou polo diferentes entre as planilhas — afeta o depósito de destino e a equipe acionada.',
  'Entrega atrasada': 'O material chegou depois da data prevista registrada no próprio EMD.',
  'Cadastro incompleto no EMD': 'Campos de controle em branco. Sem eles a requisição não é rastreável da abertura até a entrega.',
  'Incoerência interna do EMD': 'A própria linha do EMD se contradiz — por exemplo, substituição concluída com equipamento não entregue.',
};

const DESC_COMPRA = {
  'Compra possivelmente desnecessária': 'O Parecer COEP já registra o equipamento como substituído ou concluído. Se a troca ocorreu depois do pedido, o material vira sobressalente.',
  'Pedido ainda sem EMD': 'O ativo entrou no plano de compras e ainda não tem linha de EMD — esperado enquanto a compra corre.',
  'Status do plano desatualizado': 'O status congelado no plano (foto de 17/07/2026) já não corresponde ao Parecer COEP atual.',
  'SS divergente no plano': 'O plano cita uma SS diferente da registrada na planilha de criticidade para o mesmo ativo.',
};

const DESC_CONCLUSAO = {
  'Confirmada no AIC': 'A obra aparece no AIC como encerrada. É a única prova que conta — as demais são indício.',
  'Indício forte': 'Duas ou mais fontes concordam que o equipamento foi concluído e nenhuma delas contradiz. Ainda assim, sem o AIC não é confirmação.',
  'Indício contestado': 'Há sinal de conclusão, mas algo no mesmo registro o desmente — o Check, o Parecer COEP, a SS ainda aberta ou o prazo estourado.',
  'Indício isolado': 'Uma única fonte, e das mais fracas, indica conclusão. Não sustenta a contagem sozinha.',
  'Sem indício de conclusão': 'Nenhuma das fontes sinaliza conclusão.',
};

const COLECOES = [
  { id: 'dcmd', nome: 'Missão DCMD', desc: 'Concluídas em 2026, o que vai entrar, SIGCO e o fluxo de repasse', termos: 'dcmd missao concluidas 2026 sigco 8481 8495 fluxo repasse cocm atrasado dmsl entrar' },
  { id: 'conclusao', nome: 'Conclusões', desc: 'Quantos já foram concluídos, e com que certeza', termos: 'concluidas concluidos conclusao encerradas aic obras fechadas quantas' },
  { id: 'coep', nome: 'Parecer COEP', desc: 'O que já deveria estar concluído e não está', termos: 'coep parecer pendencia atraso prazo vencido sla' },
  { id: 'emd', nome: 'Cruzamento EMD', desc: 'Divergências entre a requisição e a criticidade', termos: 'emd requisicao divergencia obra deposito material' },
  { id: 'compras', nome: 'Plano de compras', desc: 'Pedido de 17/07/2026, prazos e conferência', termos: 'compras compra pedido plano valor preco prazo 120 180 portilho' },
  { id: 'frota', nome: 'Mapa e frota', desc: 'Onde estão, marca, potência e especificação', termos: 'mapa frota coordenada localizacao marca modelo potencia tensao kvar especificacao ajustes' },
  { id: 'visao', nome: 'Visão geral', desc: 'Distribuição da carteira em números', termos: 'visao geral panorama distribuicao criticidade resumo grafico' },
  { id: 'metodo', nome: 'Metodologia', desc: 'De onde vem cada número e o que ele não prova', termos: 'metodologia metodo fonte limite como foi feito' },
];

const estado = {
  equipamentos: [], alertas: [], divergencias: [], compras: [], meta: null,
  termo: '', facetas: {}, limite: 40, selecionado: -1, vista: 'busca',
};

/* ---------------- utilidades ---------------- */

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const chave = (t) => String(t ?? '').toLowerCase().normalize('NFD')
  .replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

const puro = (t) => String(t ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

const categoriaDe = (e) => e.analise?.categoria_primaria || '';
const concluidaSS = (e) => /CONCLU/i.test(e.ss || '');

function dataBr(iso) {
  const [a, m, d] = String(iso).split('-');
  return d ? `${d}/${m}/${a}` : iso;
}

const moeda = (v) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const numero = (v) => v.toLocaleString('pt-BR');

function indice(e) {
  if (!e._i) {
    const a = e.analise || {}, s = e.especificacao || {}, g = e.gestao || {};
    e._i = puro([e.ativo, e.localidade, e.polo, e.regional, e.ss, e.parecer_coep, e.observacao,
      e.defeito_planilha, e.descricao_ss, e.tipo_nome, e.criticidade, a.categoria_primaria,
      a.componente_especifico, a.resumo_tecnico, a.acao_requerida, a.causa_raiz,
      a.pendencia_declarada, a.responsavel_atual, a.status_operacional, s.marca_modelo,
      s.alimentador, s.classe_tensao, s.faixa_potencia, s.familia, g.status, g.descricao_compra,
      e.conclusao?.situacao,
    ].join(' '));
  }
  return e._i;
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
      $('#palco').innerHTML = '<div class="prosa"><h3>Não foi possível carregar os dados</h3>' +
        '<p>Os arquivos em <code>data/</code> precisam ser servidos por HTTP. Rode ' +
        '<code>python3 -m http.server 8000</code> na raiz do projeto.</p></div>';
      console.error(erro);
      return;
    }
  }

  const m = estado.meta;
  $('#posicao').textContent = dataBr(m.gerado_em);
  $('#subchamada').textContent =
    `${m.total_equipamentos} religadores e reguladores de tensão indisponíveis na ETO, ` +
    `${m.total_com_descricao} com a descrição de SS lida por inteiro. ` +
    `Busque por ativo, cidade, defeito ou marca — ou abra uma coleção.`;

  const chipDcmd = m.missao?.dcmd?.recorte_estrito?.concluidas_2026?.total;
  $('#resumo-topo').innerHTML = [
    ['Em aberto', m.total_abertos, ''],
    ['Muito alta', m.por_criticidade.find((i) => i.rotulo === 'Muito Alta')?.total ?? 0, 'crit'],
    ['Confirmadas no AIC', m.conclusao.confirmadas, ''],
    ...(chipDcmd != null ? [['DCMD 2026', chipDcmd, '']] : []),
  ].map(([k, v, c]) => `<div class="${c}"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('');

  montarFacetas();
  render();
}

/* ---------------- facetas ---------------- */

const FACETAS = [
  { id: 'criticidade', rotulo: 'Criticidade', valores: () => ORDEM_CRIT, de: (e) => e.criticidade },
  { id: 'tipo', rotulo: 'Tipo', valores: null, de: (e) => e.tipo_nome },
  { id: 'regional', rotulo: 'Regional', valores: null, de: (e) => e.regional },
  { id: 'potencia', rotulo: 'Potência', valores: null, de: (e) => e.especificacao?.faixa_potencia },
  { id: 'tensao', rotulo: 'Tensão', valores: null, de: (e) => e.especificacao?.classe_tensao },
  { id: 'conclusao', rotulo: 'Conclusão', valores: null, de: (e) => e.conclusao?.situacao },
];

function montarFacetas() {
  const atalhos = [
    { id: 'aberta', rotulo: 'Em aberto', teste: (e) => !concluidaSS(e) },
    { id: 'alerta', rotulo: 'Com pendência COEP', teste: (e) => e.tem_alerta },
    { id: 'divergencia', rotulo: 'Com divergência', teste: (e) => e.tem_divergencia },
    { id: 'compras', rotulo: 'No plano de compras', teste: (e) => e.no_plano_compras },
    { id: 'bypass', rotulo: 'By-passado', teste: (e) => e.analise?.status_operacional === 'By-passado em campo' },
  ];
  estado.atalhos = atalhos;

  const html = atalhos.map((a) => {
    const n = estado.equipamentos.filter(a.teste).length;
    return `<button class="pastilha" data-atalho="${a.id}" aria-pressed="false">${esc(a.rotulo)} <b>${n}</b></button>`;
  }).join('') +
  ORDEM_CRIT.filter((c) => estado.equipamentos.some((e) => e.criticidade === c))
    .map((c) => {
      const n = estado.equipamentos.filter((e) => e.criticidade === c).length;
      return `<button class="pastilha" data-faceta="criticidade" data-valor="${esc(c)}" aria-pressed="false">${esc(c)} <b>${n}</b></button>`;
    }).join('') +
  `<button class="pastilha limpar" id="limpar-facetas" hidden>limpar</button>`;

  $('#fichas').innerHTML = html;

  $$('#fichas .pastilha[data-atalho], #fichas .pastilha[data-faceta]').forEach((b) => {
    b.addEventListener('click', () => {
      const ligado = b.getAttribute('aria-pressed') === 'true';
      b.setAttribute('aria-pressed', String(!ligado));
      if (b.dataset.atalho) {
        estado.facetas[b.dataset.atalho] = !ligado;
      } else {
        estado.facetas[`${b.dataset.faceta}:${b.dataset.valor}`] = !ligado;
      }
      estado.limite = 40;
      render();
    });
  });

  $('#limpar-facetas').addEventListener('click', () => {
    estado.facetas = {};
    $$('#fichas .pastilha').forEach((b) => b.setAttribute('aria-pressed', 'false'));
    render();
  });
}

function filtrar() {
  const t = puro(estado.termo.trim());
  const ligadas = Object.entries(estado.facetas).filter(([, v]) => v).map(([k]) => k);

  return estado.equipamentos.filter((e) => {
    for (const f of ligadas) {
      if (f.includes(':')) {
        const [campo, valor] = f.split(':');
        const def = FACETAS.find((x) => x.id === campo);
        if (def && def.de(e) !== valor) return false;
      } else {
        const at = estado.atalhos.find((a) => a.id === f);
        if (at && !at.teste(e)) return false;
      }
    }
    return !t || indice(e).includes(t);
  });
}

/* ---------------- busca ---------------- */

function trecho(e, termo) {
  if (!termo) {
    const a = e.analise;
    return a?.resumo_tecnico || e.parecer_coep || e.defeito_planilha || e.ss;
  }
  const alvo = indice(e);
  const pos = alvo.indexOf(termo);
  if (pos < 0) return e.parecer_coep || e.ss;

  // O índice é uma versão sem acento do texto, e tem o mesmo comprimento do original
  // concatenado — então o deslocamento encontrado serve para recortar o texto legível.
  const bruto = [e.ativo, e.localidade, e.polo, e.regional, e.ss, e.parecer_coep, e.observacao,
    e.defeito_planilha, e.descricao_ss, e.tipo_nome, e.criticidade].join(' ');
  const ini = Math.max(0, pos - 42);
  const fim = Math.min(bruto.length, pos + termo.length + 78);
  const corte = (ini > 0 ? '…' : '') + bruto.slice(ini, fim).trim() + (fim < bruto.length ? '…' : '');
  const inicioRel = pos - ini + (ini > 0 ? 1 : 0);
  return esc(corte.slice(0, inicioRel)) +
    '<mark>' + esc(corte.slice(inicioRel, inicioRel + termo.length)) + '</mark>' +
    esc(corte.slice(inicioRel + termo.length));
}

function colecoesQueCasam(t) {
  if (!t) return [];
  return COLECOES.filter((c) => puro(`${c.nome} ${c.desc} ${c.termos}`).includes(t));
}

function render() {
  if (estado.vista !== 'busca') return;
  const t = puro(estado.termo.trim());
  const lista = filtrar();
  const colecoes = colecoesQueCasam(t);
  estado.lista = lista;
  estado.colecoesVisiveis = colecoes;

  const temFaceta = Object.values(estado.facetas).some(Boolean);
  $('#limpar-facetas').hidden = !temFaceta;

  const partes = [];

  if (!t && !temFaceta) {
    partes.push(`<div class="marcador"><h2>Coleções</h2></div>`);
    partes.push(COLECOES.map((c, i) => `
      <button class="linha comando fila" data-colecao="${c.id}" data-idx="${i}">
        <span class="icone">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 6h16M4 12h16M4 18h10"/></svg>
        </span>
        <span><span class="cod">${esc(c.nome)}</span><span class="sob">${esc(c.desc)}</span></span>
        <span class="lado">↵</span>
      </button>`).join(''));
  } else if (colecoes.length) {
    partes.push(`<div class="marcador"><h2>Coleções</h2></div>`);
    partes.push(colecoes.map((c, i) => `
      <button class="linha comando fila" data-colecao="${c.id}" data-idx="${i}">
        <span class="icone">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 6h16M4 12h16M4 18h10"/></svg>
        </span>
        <span><span class="cod">${esc(c.nome)}</span><span class="sob">${esc(c.desc)}</span></span>
        <span class="lado">↵</span>
      </button>`).join(''));
  }

  const desloc = colecoes.length || (!t && !temFaceta ? COLECOES.length : 0);

  if (t || temFaceta) {
    partes.push(`<div class="marcador"><h2>Equipamentos</h2>
      <span>${lista.length} de ${estado.equipamentos.length}</span></div>`);

    if (!lista.length) {
      partes.push(`<div class="nada"><strong>Nada encontrado</strong>
        <span>Tente outro termo, ou desligue algum filtro.</span></div>`);
    } else {
      const mostrar = lista.slice(0, estado.limite);
      partes.push(mostrar.map((e, i) => linhaEquipamento(e, t, desloc + i)).join(''));
      if (lista.length > estado.limite) {
        partes.push(`<button class="mais" id="mais">mostrar mais ${Math.min(40, lista.length - estado.limite)} de ${lista.length - estado.limite} restantes</button>`);
      }
    }
  }

  $('#saida').innerHTML = partes.join('');
  ligarLinhas();
  if ($('#mais')) $('#mais').addEventListener('click', () => { estado.limite += 40; render(); });
}

function linhaEquipamento(e, t, idx) {
  const dias = e.ss_sgm?.dias_aberta;
  const conc = e.conclusao?.situacao || '';
  return `<button class="linha fila c-${chave(e.criticidade)}" data-ativo="${esc(e.ativo)}" data-idx="${idx}">
    <span class="ponto"></span>
    <span>
      <span class="principal">
        <span class="cod">${esc(e.ativo)}</span>
        <span class="nome">${esc(e.localidade || '—')} · ${esc(e.tipo_nome)}</span>
      </span>
      <span class="sob">${trecho(e, t)}</span>
    </span>
    <span class="lado">
      <b>${e.priorizacao || '—'}</b>
      ${dias != null ? `${dias}d` : (conc === 'Indício forte' ? 'indício' : '—')}
    </span>
  </button>`;
}

function ligarLinhas() {
  $$('#saida .linha').forEach((el) => {
    el.addEventListener('click', () => {
      if (el.dataset.colecao) abrirColecao(el.dataset.colecao);
      else abrirAtivo(el.dataset.ativo);
    });
  });
}

/* ---------------- teclado ---------------- */

function alvos() {
  return $$('#saida .linha');
}

function mover(passo) {
  const els = alvos();
  if (!els.length) return;
  estado.selecionado = Math.max(0, Math.min(els.length - 1, estado.selecionado + passo));
  els.forEach((el, i) => el.setAttribute('aria-selected', String(i === estado.selecionado)));
  els[estado.selecionado].scrollIntoView({ block: 'nearest' });
}

document.addEventListener('keydown', (ev) => {
  const campo = $('#busca');
  const digitando = document.activeElement === campo;

  if (ev.key === '/' && !digitando) { ev.preventDefault(); campo?.focus(); return; }
  if ((ev.key === 'k' || ev.key === 'K') && (ev.metaKey || ev.ctrlKey)) {
    ev.preventDefault(); voltarBusca(); campo?.focus(); campo?.select(); return;
  }
  if (ev.key === 'Escape') {
    if (estado.vista !== 'busca') { voltarBusca(); return; }
    if (campo && campo.value) { campo.value = ''; estado.termo = ''; estado.limite = 40; render(); }
    return;
  }
  if (estado.vista !== 'busca') return;
  if (ev.key === 'ArrowDown') { ev.preventDefault(); mover(1); }
  if (ev.key === 'ArrowUp') { ev.preventDefault(); mover(-1); }
  if (ev.key === 'Enter') {
    const el = alvos()[estado.selecionado];
    if (el) { ev.preventDefault(); el.click(); }
  }
});

/* ---------------- navegação de vistas ---------------- */

function voltarBusca() {
  estado.vista = 'busca';
  $('#palco').className = 'palco';
  $('#palco').innerHTML = `
    <h1 class="chamada">O que você quer saber?</h1>
    <p class="subchamada">${esc($('#subchamada')?.textContent || '')}</p>
    <div class="campo-busca">
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input type="search" id="busca" autocomplete="off" spellcheck="false"
        value="${esc(estado.termo)}" placeholder="Ativo, localidade, SS, defeito, marca — ou uma coleção">
      <kbd class="atalho">/</kbd>
    </div>
    <div class="fichas" id="fichas"></div>
    <div id="saida"></div>`;
  montarFacetas();
  restaurarFacetas();
  ligarBusca();
  render();
  window.scrollTo({ top: 0 });
}

function restaurarFacetas() {
  Object.entries(estado.facetas).forEach(([k, v]) => {
    if (!v) return;
    const sel = k.includes(':')
      ? `#fichas .pastilha[data-faceta="${k.split(':')[0]}"][data-valor="${k.split(':')[1]}"]`
      : `#fichas .pastilha[data-atalho="${k}"]`;
    $(sel)?.setAttribute('aria-pressed', 'true');
  });
}

function ligarBusca() {
  const campo = $('#busca');
  if (!campo) return;
  campo.addEventListener('input', (ev) => {
    estado.termo = ev.target.value;
    estado.limite = 40;
    estado.selecionado = -1;
    render();
  });
}

function paginaLeitura(conteudo, classe = 'leitura') {
  estado.vista = 'leitura';
  const palco = $('#palco');
  palco.className = classe;
  palco.innerHTML = `<button class="voltar" id="voltar">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M15 6l-6 6 6 6"/></svg> voltar à busca <kbd class="atalho">esc</kbd>
    </button>${conteudo}`;
  $('#voltar').addEventListener('click', voltarBusca);
  window.scrollTo({ top: 0 });
}

/* ---------------- ficha do equipamento ---------------- */

const bloco = (titulo, corpo) => `<section class="bloco"><h3>${esc(titulo)}</h3>${corpo}</section>`;
const campo = (k, v) => `<div class="campo"><span>${esc(k)}</span><b>${v ?? '—'}</b></div>`;
const realcar = (t) => esc(t).replace(/(PARECER COEP:|PARECER DMSL:|FEEDBACK EQUIP\. ESPECIAIS)/gi, '<mark>$1</mark>');

function abrirAtivo(ativo) {
  const e = estado.equipamentos.find((x) => x.ativo === ativo);
  if (!e) return;
  const a = e.analise, s = e.especificacao, c = e.conclusao;
  const alertas = estado.alertas.filter((x) => x.ativo === ativo);
  const divergencias = estado.divergencias.filter((x) => x.ativo === ativo);
  const achados = estado.compras.filter((x) => x.ativo === ativo);

  const selos = [
    `<span class="selo c-${chave(e.criticidade)}">${esc(e.criticidade)}</span>`,
    `<span class="selo neutro">${esc(e.tipo_nome)}</span>`,
    categoriaDe(e) ? `<span class="selo destaque">${esc(categoriaDe(e))}</span>` : '',
    a?.risco_operacional ? `<span class="selo c-${chave(a.risco_operacional)}">Risco ${esc(a.risco_operacional)}</span>` : '',
    s?.faixa_potencia && s.faixa_potencia !== 'Não se aplica' ? `<span class="selo neutro">${esc(s.faixa_potencia)}</span>` : '',
    s?.classe_tensao ? `<span class="selo neutro">${esc(s.classe_tensao)}</span>` : '',
    c ? `<span class="selo ${c.situacao === 'Confirmada no AIC' ? 'c-baixa' : c.situacao === 'Indício contestado' ? 'c-alta' : 'neutro'}">${esc(c.situacao)}</span>` : '',
  ].filter(Boolean).join('');

  const partes = [`<header class="cabeca">
    <div class="cod">${esc(e.ativo)}</div>
    <div class="nome">${esc(e.localidade || 'localidade não informada')} · ${esc(e.polo || '—')} / ${esc(e.regional || '—')}</div>
    <div class="selos">${selos}</div>
  </header>`];

  if (c) {
    partes.push(bloco('Está concluído?', `
      <p class="destaque-texto">${esc(DESC_CONCLUSAO[c.situacao] || '')}</p>
      ${c.indicios.length ? `<div class="itens">${c.indicios.map((i) =>
        `<div class="item-linha"><span>${esc(i.texto)}</span><b>${esc(i.fonte)}</b></div>`).join('')}</div>` : ''}
      ${c.contradicoes.length ? c.contradicoes.map((x) =>
        `<div class="nota" style="margin-top:12px"><strong>Contradiz</strong>${esc(x)}</div>`).join('') : ''}
      ${!c.aic_disponivel ? `<div class="nota calma" style="margin-top:12px">
        <strong>AIC não carregado</strong>O extrato do AIC ainda não foi enviado, então nenhuma
        conclusão está confirmada. Assim que <code>data/raw/aic_obras.csv</code> existir, as obras
        encerradas passam a contar como confirmadas.</div>` : ''}`));
  }

  if (alertas.length || achados.length) {
    partes.push(bloco('Pendências', [...alertas, ...achados].map((x) => `
      <div class="nota ${['Média', 'Baixa'].includes(x.gravidade) ? 'branda' : ''}">
        <strong>${esc(x.tipo_alerta || x.tipo)}${x.dias_atraso ? ` · ${x.dias_atraso} dias de atraso` : ''}</strong>
        ${esc(x.detalhe)}</div>`).join('')));
  }

  if (e.fluxo) {
    const f = e.fluxo;
    partes.push(bloco('Fluxo da SS (COI → DEOP → DMSL → COEP → COCM)', `
      ${f.atrasado_cocm ? `<div class="nota" style="margin-bottom:14px"><strong>Atrasado no COCM</strong>
        Material entregue ao COCM sem previsão de execução registrada. ${esc(f.evidencia || '')}</div>` : ''}
      <div class="campos" style="margin-bottom:16px">
        ${campo('Onde está agora', esc(f.onde_esta || '—'))}
      </div>
      ${(f.etapas || []).length ? `<div class="cronologia">${f.etapas.map((et) => `
        <div><time>${esc(et.inicio ? dataBr(et.inicio) : '—')}</time>
        <span><strong style="font-family:var(--cond);text-transform:uppercase;letter-spacing:.06em;font-size:12px">${esc(et.etapa)}</strong>
        · ${esc(et.numero_ss || '')} ${esc(et.equipe ? '· ' + et.equipe : '')} ${esc(et.situacao ? '· ' + et.situacao : '')}${et.fim ? ' · concluída ' + dataBr(et.fim) : ''}</span></div>`).join('')}</div>` : ''}
      ${(f.quebras || []).length ? f.quebras.map((q) => `<div class="nota branda" style="margin-top:12px">
        <strong>Quebra de fluxo</strong>${esc(typeof q === 'string' ? q : (q.descricao || JSON.stringify(q)))}</div>`).join('') : ''}`));
  }

  if (e.aic) {
    const x = e.aic;
    partes.push(bloco('Obra no AIC', `
      <div class="campos">
        ${campo('Veredito', esc(x.veredito || '—'))}
        ${campo('Obra principal', esc(x.obra_principal || '—'))}
        ${campo('Como foi ligada', esc(x.via || '—'))}
        ${campo('SIGCO', esc(x.sigco || '—'))}
        ${campo('Status no AIC', esc(x.status_aic || '—'))}
        ${campo('Encerramento', x.data_encerramento ? dataBr(x.data_encerramento) : '—')}
        ${campo('Confiança do vínculo', esc(x.confianca || '—'))}
      </div>
      ${(x.outras_obras || []).length ? `<div class="nota calma" style="margin-top:12px">
        <strong>Outras obras do ativo</strong>${x.outras_obras.map((o) => esc(typeof o === 'string' ? o : (o.num_obra || '') + ' ' + (o.status || ''))).join('<br>')}</div>` : ''}`));
  }

  if (e.sigco && (e.sigco.veredito || e.sigco.sigco_aic || e.sigco.sigco_emd)) {
    partes.push(bloco('SIGCO da obra', `
      ${e.sigco.veredito === 'sigco_errado' ? `<div class="nota" style="margin-bottom:12px">
        <strong>SIGCO errado</strong>Obra no projeto ${esc(e.sigco.sigco_aic || e.sigco.sigco_emd || '?')} — o correto para ${esc(e.tipo_nome.toLowerCase())} é ${e.tipo === '58' ? '8481' : '8495'}.</div>` : ''}
      <div class="campos">
        ${campo('SIGCO no EMD', esc(e.sigco.sigco_emd || '—'))}
        ${campo('SIGCO no AIC', esc(e.sigco.sigco_aic || '—'))}
        ${campo('Veredito', esc(e.sigco.veredito || '—'))}
        ${campo('Conflito EMD × AIC', e.sigco.conflito_emd_aic ? 'sim' : 'não')}
      </div>`));
  }

  if (a) {
    partes.push(bloco('O defeito', `
      <p class="destaque-texto">${esc(a.resumo_tecnico || '')}</p>
      <div class="campos">
        ${campo('Componente', esc(a.componente_especifico || '—'))}
        ${campo('Fases afetadas', (a.fases_afetadas || []).join(', ') || '—')}
        ${campo('Situação em campo', esc(a.status_operacional || '—'))}
        ${campo('Responsável atual', esc(a.responsavel_atual || '—'))}
        ${campo('Causa raiz', esc(a.causa_raiz || '—'))}
        ${campo('Ação necessária', esc(a.acao_requerida || '—'))}
        ${campo('Pendência declarada', esc(a.pendencia_declarada || '—'))}
        ${campo('Confiança da leitura', esc(a.confianca || '—'))}
      </div>
      ${a.divergencia_planilha ? `<div class="nota branda" style="margin-top:16px">
        <strong>Divergência com a planilha</strong>${esc(a.divergencia_planilha)}</div>` : ''}`));

    if (a.datas_citadas?.length) {
      partes.push(bloco('Cronologia da SS', `<div class="cronologia">${a.datas_citadas.map((d) =>
        `<div><time>${esc(dataBr(d.data))}</time><span>${esc(d.o_que)}</span></div>`).join('')}</div>`));
    }
  }

  if (s) {
    const campos = [
      ['Família', s.familia], ['Marca / modelo', s.marca_modelo], ['Parte ativa', s.parte_ativa],
      ['Controlador', s.controlador], ['Tipo de instalação', s.tipo_instalacao],
      ['Alimentador', s.alimentador], ['Classe de tensão', s.classe_tensao],
      ['Tensão', s.tensao_kv || s.tensao_primaria], ['Potência (kvar)', s.potencia_kvar],
      ['Faixa de potência', s.faixa_potencia], ['Corrente (A)', s.corrente_a],
      ['Tensão de controle (V)', s.tensao_controle_v], ['Automatizado', s.automatizado],
      ['Descrição', s.descricao], ['Estudo', s.estudo], ['Autor do estudo', s.autor_estudo],
      ['Data do estudo', s.data_estudo ? dataBr(s.data_estudo) : ''],
    ].filter(([, v]) => v && v !== 'Não se aplica');

    partes.push(bloco('Especificação', `
      <div class="campos">${campos.map(([k, v]) => campo(k, esc(v))).join('')}</div>
      ${s.ajustes ? `<h3 style="margin:24px 0 12px;border:0;padding:0;font-size:11.5px">Ajustes de proteção</h3>
        <div class="campos">${Object.entries(s.ajustes).filter(([, v]) => v)
          .map(([k, v]) => campo(k, esc(v))).join('')}</div>` : ''}`));
  }

  if (e.ss_sgm) {
    const x = e.ss_sgm;
    partes.push(bloco('SS no sistema', `
      ${x.sla_estourado ? `<div class="nota" style="margin-bottom:16px"><strong>Prazo-limite estourado</strong>
        A SS tinha prazo até ${dataBr(x.data_limite)} e está ${x.dias_sla} dias além do prazo.</div>` : ''}
      <div class="campos">
        ${campo('Número da SS', esc(x.numero || '—'))}
        ${campo('Criticidade no sistema', esc(x.criticidade_ss || '—'))}
        ${campo('Situação', esc(x.situacao || '—'))}
        ${campo('Órgão solicitante', esc(x.org_solicitante || '—'))}
        ${campo('Abertura', x.data_abertura ? dataBr(x.data_abertura) : '—')}
        ${campo('Prazo-limite', x.data_limite ? dataBr(x.data_limite) : '—')}
        ${campo('Término', x.data_termino ? dataBr(x.data_termino) : '—')}
        ${campo('Dias em aberto', x.dias_aberta != null ? `${x.dias_aberta} dias` : '—')}
      </div>`));
  }

  partes.push(bloco('Registro na planilha de criticidade', `<div class="campos">
    ${campo('SS aberta', esc(e.ss || '—'))}
    ${campo('Parecer COEP', esc(e.parecer_coep || '—'))}
    ${campo('Check de conclusão', esc(e.check || '—'))}
    ${campo('Observação', esc(e.observacao || '—'))}
    ${campo('Defeito (planilha)', esc(e.defeito_planilha || '—'))}
    ${campo('Pontuação de priorização', e.priorizacao || '—')}
    ${campo('Linha na planilha', e.linha_planilha)}
  </div>`));

  if (e.compras?.length) {
    const total = e.compras.reduce((sm, i) => sm + i.valor_total, 0);
    partes.push(bloco('Plano de compras de 17/07/2026', `<div class="itens">
      ${e.compras.map((i) => `<div class="item-linha">
        <span>${esc(i.material)}<small>${esc(i.codigo)} · ${i.qtd}x · prazo de ${i.prazo_dias} dias, limite ${dataBr(i.data_limite)} (faltam ${i.dias_restantes})</small></span>
        <b>${moeda(i.valor_total)}</b></div>`).join('')}
      <div class="item-linha somatorio"><span><strong>Total</strong></span><b>${moeda(total)}</b></div>
    </div>`));
  }

  if (e.geo) {
    partes.push(bloco('Coordenadas', `<div class="campos">
      ${campo('Latitude', e.geo.lat.toFixed(6))}
      ${campo('Longitude', e.geo.lon.toFixed(6))}
      ${campo('UTM 22S (E, N)', `${numero(e.geo.coord_x)}, ${numero(e.geo.coord_y)}`)}
      ${campo('Código GIS', esc(e.geo.cod_gis || '—'))}
      ${campo('Alimentador', esc(e.geo.alimentador || '—'))}</div>`));
  }

  if (e.emd) {
    partes.push(bloco('Requisição de material (EMD)', `<div class="campos">
      ${Object.entries(e.emd).filter(([k]) => k !== 'linha_emd').map(([k, v]) => campo(k, esc(v))).join('')}
    </div>`));
  } else {
    partes.push(bloco('Requisição de material (EMD)', `<div class="nota branda">
      <strong>Sem linha no EMD</strong>${e.parecer_coep.toLowerCase().includes('aquisi')
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
    partes.push(bloco('Gestão de equipamentos',
      `<div class="campos">${campos.map(([k, v]) => campo(k, esc(v))).join('')}</div>`));
  }

  if (divergencias.length) {
    partes.push(bloco('Divergências entre planilhas', divergencias.map((d) => `
      <div class="nota ${['Média', 'Baixa'].includes(d.gravidade) ? 'branda' : ''}">
        <strong>${esc(d.tipo)} · ${esc(d.campo)}</strong>${esc(d.detalhe)}
        <div class="confronto">
          <div><span>EMD</span><b>${esc(d.valor_emd || '—')}</b></div>
          <div><span>Criticidade</span><b>${esc(d.valor_criticidade || '—')}</b></div>
        </div></div>`).join('')));
  }

  if (e.descricao_ss) {
    partes.push(bloco('Descrição integral da SS', `<div class="transcricao">${realcar(e.descricao_ss)}</div>`));
  }

  const premissas = Object.entries(e.premissas).filter(([, v]) => v !== null);
  if (premissas.length) {
    partes.push(bloco('Premissas de priorização', `<div class="itens">
      ${premissas.map(([k, v]) => `<div class="item-linha"><span>Premissa ${k.slice(1)}</span><b>${v}</b></div>`).join('')}
      <div class="item-linha somatorio"><span><strong>Total</strong></span><b>${e.priorizacao}</b></div></div>`));
  }

  paginaLeitura(partes.join(''));
}

/* ---------------- coleções ---------------- */

function num({ rotulo, valor, nota, tom = '' }) {
  const longo = String(valor).length > 11 ? ' longo' : '';
  return `<div class="numero ${tom}"><span>${esc(rotulo)}</span>
    <strong class="${longo.trim()}">${esc(valor)}</strong>
    ${nota ? `<small>${esc(nota)}</small>` : ''}</div>`;
}

function barras(itens) {
  const max = Math.max(...itens.map((i) => i.total), 1);
  return `<div class="barras">${itens.map((i) => `<div class="barra">
    <div><span>${esc(i.rotulo)}</span><strong>${i.total}</strong></div>
    <i><b style="width:${(i.total / max * 100).toFixed(1)}%"></b></i></div>`).join('')}</div>`;
}

function cabecaColecao(titulo, texto) {
  return `<header class="cabeca"><div class="cod">${esc(titulo)}</div>
    <div class="nome">${texto}</div></header>`;
}

function turmas(itens, campoTipo, descricoes, extras) {
  const grupos = {};
  itens.forEach((i) => { (grupos[i[campoTipo]] ??= []).push(i); });
  const chaves = Object.keys(grupos).sort((x, y) =>
    ORDEM_GRAV.indexOf(grupos[x][0].gravidade) - ORDEM_GRAV.indexOf(grupos[y][0].gravidade)
    || grupos[y].length - grupos[x].length);

  return `<div class="turmas">${chaves.map((tipo) => {
    const lista = grupos[tipo];
    return `<section class="turma"><header>
        <div><h3>${esc(tipo)}</h3><span class="selo neutro">${lista.length}</span></div>
        <p>${esc(descricoes[tipo] || '')}</p></header>
      <div class="cartas">${lista.map((i) => `
        <button class="carta" data-ativo="${esc(i.ativo)}">
          <div class="topo-carta">
            <span class="cod">${esc(i.ativo)}</span>
            <span class="selo c-${chave(i.criticidade)}">${esc(i.criticidade)}</span>
            ${i.dias_atraso ? `<span class="atraso">${i.dias_atraso}d</span>` : ''}
            ${i.valor_envolvido ? `<span class="valor">${moeda(i.valor_envolvido)}</span>` : ''}
          </div>
          <div class="onde">${esc(i.localidade || '—')} · ${esc(i.regional || '—')}</div>
          <p>${esc(i.detalhe)}</p>
          ${extras ? extras(i) : ''}
        </button>`).join('')}</div></section>`;
  }).join('')}</div>`;
}

function ligarCartas() {
  $$('.carta[data-ativo], .tabela tbody tr[data-ativo], .ponto-mapa[data-ativo]').forEach((el) => {
    el.addEventListener('click', () => abrirAtivo(el.dataset.ativo));
  });
}

function abrirColecao(id) {
  const m = estado.meta;
  let html = '';

  if (id === 'conclusao') {
    const c = m.conclusao;
    html = cabecaColecao('Conclusões', 'Quantos equipamentos já foram concluídos — e o quanto disso é certeza.') +
      `<div class="numeros">
        ${num({ rotulo: 'Confirmadas no AIC', valor: c.confirmadas, nota: c.aic_disponivel ? 'obras encerradas no AIC' : 'extrato do AIC ainda não carregado', tom: c.confirmadas ? 'bom' : '' })}
        ${num({ rotulo: 'Com algum indício', valor: c.com_algum_indicio, nota: 'sinal de conclusão em ao menos uma fonte' })}
        ${num({ rotulo: 'Indício contestado', valor: c.contestadas, nota: 'algo no registro desmente', tom: 'critico' })}
        ${num({ rotulo: 'Sem indício', valor: c.sem_indicio, nota: 'nenhuma fonte sinaliza conclusão' })}
      </div>
      <div class="nota calma" style="margin-bottom:32px">
        <strong>Por que ainda não há número confirmado</strong>
        A regra é sua: só há certeza depois que a obra aparece no AIC como encerrada. O extrato do
        AIC ainda não entrou no repositório, então <strong>nenhum equipamento está contado como
        concluído</strong> — o que existe abaixo é indício, ordenado pela força.
        Nenhuma das ${m.total_equipamentos} SS tem data de término registrada no SGM, o que reforça
        que a baixa formal não aconteceu.
        Assim que <code>data/raw/aic_obras.csv</code> existir (colunas
        <code>ativo;obra;situacao;data_encerramento</code>), o build passa a contar as encerradas.
      </div>
      <div class="grade" style="margin-bottom:34px">
        <div class="quadro"><header><h3>Força do indício</h3>
          <p>Como cada equipamento se classifica hoje</p></header>${barras(c.por_situacao)}</div>
        <div class="quadro"><header><h3>Origem do indício</h3>
          <p>Qual fonte sinalizou conclusão</p></header>${barras(c.por_fonte)}</div>
      </div>` +
      turmas(
        estado.equipamentos
          .filter((e) => e.conclusao.fontes.length)
          .map((e) => ({
            ativo: e.ativo, localidade: e.localidade, regional: e.regional,
            criticidade: e.criticidade, tipo: e.conclusao.situacao,
            gravidade: e.conclusao.situacao === 'Indício contestado' ? 'Alta'
              : e.conclusao.situacao === 'Confirmada no AIC' ? 'Crítica' : 'Média',
            detalhe: e.conclusao.indicios.map((i) => i.texto).join('. ') + '.',
            contradicoes: e.conclusao.contradicoes,
          })),
        'tipo', DESC_CONCLUSAO,
        (i) => i.contradicoes.length
          ? `<div class="rodape"><span>contradiz: ${esc(i.contradicoes[0])}</span></div>` : '');
  }

  if (id === 'coep') {
    const a = estado.alertas;
    const vencidos = a.filter((x) => x.dias_atraso);
    html = cabecaColecao('Parecer COEP', 'O que já deveria estar concluído e não está.') +
      `<div class="numeros">
        ${num({ rotulo: 'Equipamentos com pendência', valor: m.equipamentos_com_alerta, nota: `${a.length} alertas no total`, tom: 'critico' })}
        ${num({ rotulo: 'SS de anos anteriores', valor: a.filter((x) => x.gravidade === 'Crítica').length, nota: 'atravessaram o ano sem solução', tom: 'critico' })}
        ${num({ rotulo: 'Prazos vencidos', valor: vencidos.length, nota: `maior atraso: ${Math.max(0, ...vencidos.map((x) => x.dias_atraso))} dias`, tom: 'atento' })}
        ${num({ rotulo: 'Alta ou muito alta', valor: new Set(a.filter((x) => ['Muito Alta', 'Alta'].includes(x.criticidade)).map((x) => x.ativo)).size, nota: 'prioridade de tratativa', tom: 'atento' })}
      </div>` +
      turmas(a, 'tipo_alerta', DESC_ALERTA,
        (x) => `<div class="rodape"><span>SS ${esc(x.ss || '—')}</span>${x.observacao ? `<span>${esc(x.observacao)}</span>` : ''}</div>`);
  }

  if (id === 'emd') {
    html = cabecaColecao('Cruzamento EMD',
      'A ligação é feita pelo <strong>código do ativo</strong>, não pela SS: o EMD registra a SS de requisição do COEP e a planilha de criticidade registra a SS de campo.') +
      `<div class="numeros">
        ${num({ rotulo: 'Linhas no EMD', valor: m.total_emd, nota: `contra ${m.total_equipamentos} equipamentos` })}
        ${num({ rotulo: 'Divergências', valor: m.total_divergencias, nota: `em ${m.equipamentos_com_divergencia} equipamentos`, tom: 'critico' })}
        ${num({ rotulo: 'Em aquisição sem EMD', valor: m.em_aquisicao_sem_emd, nota: `de ${m.em_aquisicao} declarados em aquisição`, tom: 'critico' })}
        ${num({ rotulo: 'SS aberta sem EMD', valor: m.abertos_sem_emd, nota: `de ${m.total_abertos} SS abertas`, tom: 'atento' })}
      </div>` +
      turmas(estado.divergencias, 'tipo', DESC_DIVERGENCIA, (d) => `<div class="confronto">
        <div><span>EMD</span><b>${esc(d.valor_emd || '—')}</b></div>
        <div><span>Criticidade</span><b>${esc(d.valor_criticidade || '—')}</b></div></div>`);
  }

  if (id === 'compras') {
    const c = m.compras;
    html = cabecaColecao('Plano de compras',
      `Pedido de ${dataBr(c.data_pedido)}. Prazo de 120 dias para religador e 180 para regulador de tensão, contados da data do pedido.`) +
      `<div class="numeros">
        ${num({ rotulo: 'Valor do pedido', valor: moeda(c.valor_total), nota: `${c.total_pecas} peças em ${c.total_itens} itens` })}
        ${num({ rotulo: 'Equipamentos', valor: c.total_ativos, nota: 'todos de criticidade alta ou muito alta' })}
        ${num({ rotulo: 'Dias desde o pedido', valor: c.dias_decorridos, nota: `pedido em ${dataBr(c.data_pedido)}` })}
        ${num({ rotulo: 'Pedidos sem EMD', valor: c.ativos_sem_emd, nota: 'sem requisição formal', tom: 'atento' })}
        ${num({ rotulo: 'Valor a reconferir', valor: moeda(c.valor_em_revisao), nota: 'já dados como resolvidos', tom: 'critico' })}
      </div>
      <div class="prazos" style="margin-bottom:36px">${Object.entries(c.prazos).map(([tipo, p]) => {
        const pct = Math.min(100, (c.dias_decorridos / p.prazo_dias) * 100);
        return `<div class="prazo"><span>${p.prazo_dias} dias a partir do pedido</span>
          <h3>${esc(tipo)}</h3><p>${p.pecas} peças · ${moeda(p.valor)}</p>
          <div class="prazo-datas"><span>${dataBr(c.data_pedido)}</span><span>${dataBr(p.data_limite)}</span></div>
          <div class="trilho"><div style="width:${pct.toFixed(1)}%"></div></div>
          <div class="prazo-pes">
            <div><span>Decorridos</span><strong>${c.dias_decorridos}d</strong></div>
            <div><span>Restantes</span><strong>${p.dias_restantes}d</strong></div>
            <div><span>Limite</span><strong>${dataBr(p.data_limite)}</strong></div>
          </div></div>`;
      }).join('')}</div>
      <section class="bloco"><h3>Material pedido</h3><div class="tabela-rol">
        <table class="tabela"><thead><tr><th>Código</th><th>Descrição</th><th>Tipo</th>
          <th class="num">Qtd</th><th class="num">Unitário</th><th class="num">Total</th></tr></thead>
        <tbody>${c.por_material.map((x) => `<tr><td class="mono">${esc(x.codigo)}</td>
          <td>${esc(x.descricao)}</td><td>${esc(x.tipo)}</td><td class="num">${x.qtd}</td>
          <td class="num">${moeda(x.valor_unitario)}</td><td class="num">${moeda(x.valor_total)}</td></tr>`).join('')}</tbody>
        <tfoot><tr><td colspan="3">Total</td><td class="num">${c.total_pecas}</td><td></td>
          <td class="num">${moeda(c.valor_total)}</td></tr></tfoot></table></div></section>` +
      turmas(estado.compras, 'tipo', DESC_COMPRA, (x) => `<div class="rodape"><span>${esc(x.materiais)}</span></div>`);
  }

  if (id === 'frota') {
    const g = m.gestao;
    const comGeo = estado.equipamentos.filter((e) => e.geo);
    const comSs = estado.equipamentos.filter((e) => e.ss_sgm?.dias_aberta != null);
    const lista = estado.equipamentos.filter((e) => e.especificacao)
      .sort((a, b) => (b.ss_sgm?.dias_aberta ?? -1) - (a.ss_sgm?.dias_aberta ?? -1));

    html = cabecaColecao('Mapa e frota',
      'Onde estão, de que marca são, que potência têm. Coordenadas em SIRGAS 2000 / UTM 22S, convertidas para latitude e longitude no build.') +
      `<div class="numeros">
        ${num({ rotulo: 'Com especificação', valor: g.com_especificacao, nota: `de ${m.total_equipamentos} equipamentos` })}
        ${num({ rotulo: 'Com coordenada', valor: g.com_coordenada, nota: 'plotados no mapa' })}
        ${num({ rotulo: 'Prazo-limite estourado', valor: g.sla_estourado, nota: `maior atraso: ${g.maior_atraso_sla} dias`, tom: 'critico' })}
        ${num({ rotulo: 'SS mais antiga', valor: `${g.maior_dias_aberta} dias`, nota: `média de ${g.media_dias_pendente} dias pendente`, tom: 'critico' })}
        ${num({ rotulo: 'Valor previsto', valor: moeda(g.valor_previsto_total), nota: `em ${g.com_valor_previsto} equipamentos`, tom: 'atento' })}
      </div>
      <section class="bloco"><h3>Distribuição geográfica</h3>
        <div class="mapa" id="mapa"></div><div class="legenda-mapa" id="legenda-mapa"></div></section>
      <div class="grade" style="margin-bottom:34px">
        <div class="quadro"><header><h3>Marca e modelo</h3><p>Parque entre os indisponíveis</p></header>${barras(g.por_modelo.slice(0, 10))}</div>
        <div class="quadro"><header><h3>Faixa de potência</h3><p>Reguladores, por capacidade da célula</p></header>${barras(g.por_faixa_potencia)}</div>
        <div class="quadro"><header><h3>Classe de tensão</h3><p>Frota indisponível</p></header>${barras(g.por_classe_tensao)}</div>
        <div class="quadro"><header><h3>Idade da SS</h3><p>Dias desde a abertura registrada</p></header>${barras([
          { rotulo: 'até 90 dias', t: (d) => d <= 90 }, { rotulo: '91 a 180 dias', t: (d) => d > 90 && d <= 180 },
          { rotulo: '181 a 365 dias', t: (d) => d > 180 && d <= 365 }, { rotulo: 'mais de 1 ano', t: (d) => d > 365 },
        ].map((f) => ({ rotulo: f.rotulo, total: comSs.filter((e) => f.t(e.ss_sgm.dias_aberta)).length })))}</div>
      </div>
      <section class="bloco"><h3>Especificação por equipamento</h3><div class="tabela-rol">
        <table class="tabela"><thead><tr><th>Ativo</th><th>Família</th><th>Marca / modelo</th>
          <th>Alimentador</th><th class="num">Tensão</th><th class="num">Potência</th>
          <th>Localidade</th><th class="num">Dias</th></tr></thead>
        <tbody>${lista.map((e) => {
          const s = e.especificacao, ss = e.ss_sgm || {};
          return `<tr data-ativo="${esc(e.ativo)}"><td class="mono">${esc(e.ativo)}</td>
            <td>${esc(s.familia || '—')}</td><td>${esc(s.marca_modelo || '—')}</td>
            <td class="mono">${esc(s.alimentador || '—')}</td>
            <td class="num">${esc(s.classe_tensao || '—')}</td>
            <td class="num">${esc(s.potencia_kvar ? `${s.potencia_kvar} kvar` : '—')}</td>
            <td>${esc(e.localidade || '—')}</td>
            <td class="num">${ss.sla_estourado ? `<span class="atraso">${ss.dias_aberta}</span>` : (ss.dias_aberta ?? '—')}</td></tr>`;
        }).join('')}</tbody></table></div></section>`;

    paginaLeitura(html, 'colecao');
    desenharMapa(comGeo);
    ligarCartas();
    return;
  }

  if (id === 'visao') {
    const pega = (r) => m.por_criticidade.find((i) => i.rotulo === r)?.total ?? 0;
    const linhas = m.matriz_categoria_criticidade;
    const max = Math.max(...linhas.flatMap((l) => ORDEM_CRIT.map((c) => l[c] || 0)), 1);

    html = cabecaColecao('Visão geral', 'A carteira em números, como ela está em ' + dataBr(m.gerado_em) + '.') +
      `<div class="numeros">
        ${num({ rotulo: 'Equipamentos', valor: m.total_equipamentos, nota: `${m.total_com_descricao} com descrição de SS` })}
        ${num({ rotulo: 'SS em aberto', valor: m.total_abertos, nota: `${m.total_concluidos} marcadas como concluídas`, tom: 'atento' })}
        ${num({ rotulo: 'Muito alta', valor: pega('Muito Alta'), nota: `+ ${pega('Alta')} de criticidade alta`, tom: 'critico' })}
        ${num({ rotulo: 'Pendências COEP', valor: m.equipamentos_com_alerta, nota: `${m.total_alertas} alertas`, tom: 'critico' })}
        ${num({ rotulo: 'Divergências', valor: m.equipamentos_com_divergencia, nota: `${m.total_divergencias} no total`, tom: 'critico' })}
        ${num({ rotulo: 'Sem classificação', valor: pega('Sem classificação'), nota: 'fora da matriz de priorização', tom: 'atento' })}
      </div>
      <div class="grade" style="margin-bottom:34px">
        <div class="quadro"><header><h3>Criticidade</h3><p>Soma das oito premissas</p></header>${barras(m.por_criticidade)}</div>
        <div class="quadro"><header><h3>Categoria do defeito</h3><p>Da leitura integral das descrições</p></header>${barras(m.por_categoria)}</div>
        <div class="quadro"><header><h3>Regional</h3><p>Equipamentos por regional</p></header>${barras(m.por_regional)}</div>
        <div class="quadro"><header><h3>Próxima ação</h3><p>Quem está com a bola</p></header>${barras(m.por_responsavel)}</div>
        <div class="quadro"><header><h3>Situação em campo</h3><p>Como está hoje na rede</p></header>${barras(m.por_status_operacional)}</div>
        <div class="quadro"><header><h3>Polos afetados</h3><p>Dez maiores concentrações</p></header>${barras(m.por_polo.filter((i) => i.rotulo !== 'Não informado').slice(0, 10))}</div>
      </div>
      <section class="bloco"><h3>Categoria do defeito × criticidade</h3><div class="tabela-rol">
        <table class="matriz"><thead><tr><th>Categoria</th>${ORDEM_CRIT.map((c) => `<th>${esc(c)}</th>`).join('')}<th>Total</th></tr></thead>
        <tbody>${linhas.map((l) => {
          const t = ORDEM_CRIT.reduce((s, c) => s + (l[c] || 0), 0);
          return `<tr><td>${esc(l.categoria)}</td>${ORDEM_CRIT.map((c) => {
            const n = l[c] || 0;
            if (!n) return '<td class="zero">·</td>';
            return `<td><span class="calor" style="background:${CORES[c]};opacity:${(0.18 + (n / max) * 0.62).toFixed(2)};color:var(--fundo)">${n}</span></td>`;
          }).join('')}<td><strong>${t}</strong></td></tr>`;
        }).join('')}</tbody></table></div></section>`;
  }

  if (id === 'dcmd') {
    const mi = m.missao || {};
    const d = mi.dcmd, sg = mi.sigco, fl = mi.fluxo;
    const partes = [cabecaColecao('Missão DCMD',
      'Quantas SS de religador e regulador o fluxo DCMD concluiu em 2026, o que ainda vai entrar, ' +
      'se as obras estão no SIGCO correto (8481 = regulador, 8495 = religador) e onde cada um dos ' +
      '129 da carteira está no fluxo COI → DEOP → DMSL → COEP → COCM.')];

    const pendente = (nome) => `<div class="nota calma" style="margin-bottom:16px">
      <strong>${nome} em processamento</strong>Os agentes ainda estão lendo a base — recarregue em alguns minutos.</div>`;

    if (d) {
      const e = d.recorte_estrito || {}, a = d.recorte_amplo || {};
      const ec = e.concluidas_2026 || {}, ee = e.a_entrar || {};
      const ac = a.concluidas_2026 || {}, ae = a.a_entrar || {};
      partes.push(`<section class="bloco"><h3>Concluídas em 2026 e o que vai entrar</h3>
        <div class="numeros">
          ${num({ rotulo: 'Concluídas 2026 · recorte estrito', valor: ec.total ?? '—', nota: 'só o fluxo claro de eq. especiais', tom: 'bom' })}
          ${num({ rotulo: 'Concluídas 2026 · recorte amplo', valor: ac.total ?? '—', nota: 'toda SS de RL/RT atendida' })}
          ${num({ rotulo: 'Vão entrar · estrito', valor: ee.total ?? '—', nota: 'pendentes e repassadas', tom: 'atento' })}
          ${num({ rotulo: 'Vão entrar · amplo', valor: ae.total ?? '—', nota: `${ee.na_carteira_129 ?? '—'} já estão na carteira dos 129`, tom: 'critico' })}
        </div>
        <div class="grade">
          ${ec.por_tipo ? `<div class="quadro"><header><h3>Concluídas por tipo (estrito)</h3></header>${barras(Object.entries(ec.por_tipo).map(([k, v]) => ({ rotulo: k, total: v })))}</div>` : ''}
          ${ec.por_mes ? `<div class="quadro"><header><h3>Concluídas por mês (estrito)</h3></header>${barras(Object.entries(ec.por_mes).sort().map(([k, v]) => ({ rotulo: k, total: v })))}</div>` : ''}
          ${ec.por_equipe ? `<div class="quadro"><header><h3>Por equipe (estrito)</h3></header>${barras(Object.entries(ec.por_equipe).sort((x, y) => y[1] - x[1]).slice(0, 10).map(([k, v]) => ({ rotulo: k, total: v })))}</div>` : ''}
          ${ee.por_tipo ? `<div class="quadro"><header><h3>Vão entrar por tipo (estrito)</h3></header>${barras(Object.entries(ee.por_tipo).map(([k, v]) => ({ rotulo: k, total: v })))}</div>` : ''}
        </div>
        ${(d.premissas || []).length ? `<div class="nota calma" style="margin-top:18px"><strong>Premissas desta contagem</strong>${(d.premissas || []).map(esc).join('<br>')}</div>` : ''}
      </section>`);
    } else partes.push(pendente('Contagem DCMD'));

    if (sg) {
      const r = sg.resumo || {};
      partes.push(`<section class="bloco"><h3>Auditoria de SIGCO</h3>
        <div class="numeros">
          ${num({ rotulo: 'Obras no SIGCO correto', valor: r.corretas ?? '—', tom: 'bom' })}
          ${num({ rotulo: 'SIGCO errado', valor: r.sigco_errado ?? '—', nota: 'RL/RT em outro projeto', tom: 'critico' })}
          ${num({ rotulo: 'Valor nas erradas', valor: r.valor_nas_erradas != null ? moeda(r.valor_nas_erradas) : '—', tom: 'atento' })}
          ${num({ rotulo: 'Erradas já encerradas', valor: r.erradas_encerradas ?? '—', nota: `${r.erradas_em_andamento ?? '—'} ainda corrigíveis`, tom: 'atento' })}
        </div>
        ${r.por_sigco ? `<div class="grade"><div class="quadro"><header><h3>Obras de RL/RT por SIGCO</h3></header>${barras(Object.entries(r.por_sigco).sort((x, y) => y[1] - x[1]).slice(0, 10).map(([k, v]) => ({ rotulo: k || '(vazio)', total: v })))}</div></div>` : ''}
        ${(sg.obras || []).filter((o) => o.veredito === 'sigco_errado').length ? `
          <h3 style="margin:26px 0 14px;border-bottom:1px solid var(--tinta);padding-bottom:5px;font-size:14.5px">Obras no projeto errado</h3>
          <div class="cartas">${(sg.obras || []).filter((o) => o.veredito === 'sigco_errado').slice(0, 60).map((o) => `
            <button class="carta" ${o.ativo_ligado ? `data-ativo="${esc(o.ativo_ligado)}"` : ''}>
              <div class="topo-carta"><span class="cod">${esc(o.num_obra)}</span>
                <span class="selo ${o.tipo === 'regulador' ? 'destaque' : 'neutro'}">${esc(o.tipo || '?')}</span>
                <span class="atraso">SIGCO ${esc(o.sigco || '—')} → devia ${esc(o.sigco_certo || '—')}</span></div>
              <div class="onde">${esc(o.status || '')}</div>
              <p>${esc((o.descricao_curta || '').slice(0, 160))}</p>
            </button>`).join('')}</div>` : ''}
        ${(sg.premissas || []).length ? `<div class="nota calma" style="margin-top:18px"><strong>Premissas</strong>${(sg.premissas || []).map(esc).join('<br>')}</div>` : ''}
      </section>`);
    } else partes.push(pendente('Auditoria de SIGCO'));

    if (fl) {
      const ag = fl.agregado || {};
      partes.push(`<section class="bloco"><h3>Fluxo de repasse dos 129</h3>
        <div class="numeros">
          ${num({ rotulo: 'Atrasados no COCM', valor: ag.atrasados_cocm ?? '—', nota: 'material entregue, sem previsão dada', tom: 'critico' })}
          ${num({ rotulo: 'Quebras de fluxo', valor: ag.quebras ? Object.values(ag.quebras).reduce((s, v) => s + v, 0) : '—', nota: 'repasse sem rastro ou buraco >60 dias', tom: 'atento' })}
        </div>
        <div class="grade">
          ${ag.por_estagio ? `<div class="quadro"><header><h3>Onde cada ativo está</h3></header>${barras(Object.entries(ag.por_estagio).sort((x, y) => y[1] - x[1]).map(([k, v]) => ({ rotulo: k, total: v })))}</div>` : ''}
          ${ag.tempos_medianos_dias ? `<div class="quadro"><header><h3>Tempo mediano entre etapas (dias)</h3></header>${barras(Object.entries(ag.tempos_medianos_dias).map(([k, v]) => ({ rotulo: k, total: v })))}</div>` : ''}
        </div>
        ${(fl.premissas || []).length ? `<div class="nota calma" style="margin-top:18px"><strong>Premissas</strong>${(fl.premissas || []).map(esc).join('<br>')}</div>` : ''}
        <p style="margin-top:16px;font-size:13.5px;color:var(--tinta-2)">O fluxo completo de cada ativo — etapas, datas e quebras — está na ficha do equipamento. Busque o ativo e abra.</p>
      </section>`);
    } else partes.push(pendente('Fluxo de repasse'));

    html = partes.join('');
  }

  if (id === 'metodo') html = cabecaColecao('Metodologia', 'De onde vem cada número e o que ele não prova.') + prosaMetodo();

  paginaLeitura(html, 'colecao');
  ligarCartas();
}

/* ---------------- mapa ---------------- */

function desenharMapa(itens) {
  const caixa = $('#mapa');
  if (!caixa || !itens.length) return;

  const margem = 42;
  const lats = itens.map((e) => e.geo.lat), lons = itens.map((e) => e.geo.lon);
  const latMin = Math.min(...lats), latMax = Math.max(...lats);
  const lonMin = Math.min(...lons), lonMax = Math.max(...lons);
  const fLat = (latMax - latMin) * 0.04 || 0.1, fLon = (lonMax - lonMin) * 0.04 || 0.1;
  const l0 = lonMin - fLon, l1 = lonMax + fLon, a0 = latMin - fLat, a1 = latMax + fLat;

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
    const r = e.criticidade === 'Muito Alta' ? 6.5 : e.criticidade === 'Alta' ? 5.5 : 4.5;
    const d = e.ss_sgm?.dias_aberta;
    return `<circle class="ponto-mapa" data-ativo="${esc(e.ativo)}" cx="${px(e.geo.lon).toFixed(1)}"
      cy="${py(e.geo.lat).toFixed(1)}" r="${r}" fill="${CORES[e.criticidade] || CORES['Sem classificação']}">
      <title>${esc(e.ativo)} · ${esc(e.localidade)} · ${esc(e.criticidade)}${d != null ? ` — ${d} dias em aberto` : ''}</title>
    </circle>`;
  }).join('');

  caixa.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="max-width:${W}px;margin:0 auto" role="img"
    aria-label="Distribuição geográfica dos equipamentos indisponíveis">${grade.join('')}${pontos}</svg>`;

  $('#legenda-mapa').innerHTML = ORDEM_CRIT.filter((c) => itens.some((e) => e.criticidade === c))
    .map((c) => `<div><i style="background:${CORES[c]}"></i>${esc(c)}
      <b>${itens.filter((e) => e.criticidade === c).length}</b></div>`).join('');
}

/* ---------------- metodologia ---------------- */

function prosaMetodo() {
  const m = estado.meta;
  const semClasse = m.por_criticidade.find((i) => i.rotulo === 'Sem classificação')?.total ?? 0;
  return `<div class="prosa">
    <h3>De onde vêm os dados</h3>
    <p>Quatro planilhas alimentam esta página, todas versionadas em <code>data/raw/</code>: a
    <strong>Relação dos Equipamentos Indisponíveis</strong> (aba Criticidade por Equipamento), a
    planilha de <strong>EMD</strong> (OBRAS_EQ_ESPECIAL), o <strong>Plano de Compras</strong> de
    17/07/2026 e a <strong>Gestão de Equipamentos</strong>, com coordenadas, especificação e as
    datas reais da SS. O script <code>scripts/build_data.py</code> reconstrói todos os JSONs a
    partir delas — nenhum número foi digitado à mão.</p>

    <h3>O que conta como concluído</h3>
    <p>Nada é dado como concluído por conta própria. A prova é a obra aparecer no <strong>AIC como
    encerrada</strong>; enquanto o extrato do AIC não estiver em
    <code>data/raw/aic_obras.csv</code>, o contador de confirmadas fica em zero e o resto é
    indício, pesado por fonte: SGM vale 4, EMD 3, Check e SS 2 cada, Parecer COEP 1. Quando algo
    no mesmo registro desmente o indício — o Check pendente, a SS ainda aberta, o prazo estourado —
    ele vira <em>contestado</em> em vez de somar.</p>

    <h3>Criticidade, potência e tensão</h3>
    <p>A criticidade já vinha da planilha, como soma de oito premissas; a pontuação original foi
    preservada. ${semClasse} equipamentos entraram depois da rodada de classificação e seguem sem
    criticidade. A <strong>faixa de potência</strong> vale só para os reguladores, os únicos com
    kvar registrado — bancos com células de capacidades diferentes ficam como <em>banco misto</em>
    em vez de serem forçados numa faixa. Para os religadores a dimensão comparável é a
    <strong>classe de tensão</strong>.</p>

    <h3>Como as descrições de SS foram categorizadas</h3>
    <p>O campo <em>Descrição SS</em> é texto livre e concentra três vozes coladas sem separador: o
    relato de abertura, os blocos <code>PARECER COEP:</code> e os <code>PARECER DMSL:</code> /
    <code>FEEDBACK EQUIP. ESPECIAIS</code>. São ${m.total_com_descricao} descrições, divididas em
    ${m.lotes_analisados} lotes e lidas integralmente por ${m.lotes_analisados} analistas em
    paralelo, com a mesma especificação de saída.</p>
    <ul>
      <li>A classificação vem da leitura do texto, não de busca por palavra-chave.</li>
      <li>Quando o texto não sustenta uma conclusão, o campo fica como não informado.</li>
      <li>Cada registro carrega um nível de confiança da leitura, visível na ficha.</li>
    </ul>

    <h3>A missão DCMD e suas premissas</h3>
    <p>As contagens de concluídas em 2026, a auditoria de SIGCO e o fluxo de repasse foram
    produzidas sobre a base completa de SS/OS (352 mil linhas, das quais 6.305 de religador e
    regulador) e o extrato do AIC de 07/08/2026 (124 mil obras, 2.386 ligadas a RL/RT), por
    quatro análises independentes. <strong>Cada uma registra as próprias premissas</strong>,
    exibidas junto dos números na coleção Missão DCMD. Duas premissas do próprio usuário:
    parecer «em processo de aquisição» não implica EMD emitida — a EMD nasce quando a compra
    vira requisição; e material entregue ao COCM sem previsão de execução dada conta como
    atrasado.</p>

    <h3>Como as planilhas foram casadas</h3>
    <p>Pelo <strong>código do ativo</strong>, não pela SS. As planilhas usam numerações de
    universos diferentes: o EMD registra a SS de requisição do COEP e a de criticidade registra a
    SS de campo. Casar por SS produziria falso negativo em quase toda a base. Pelo ativo, as
    ${m.total_emd} linhas do EMD encontraram par.</p>

    <h3>Limites conhecidos</h3>
    <ul>
      <li>A posição é de <strong>${dataBr(m.gerado_em)}</strong>. Reprocessar o build atualiza os atrasos.</li>
      <li>As previsões da coluna Observação não trazem ano; datas de meses passados foram lidas
      como do ano corrente, o que pode subestimar atrasos antigos.</li>
      <li>Só a aba Criticidade por Equipamento foi recebida da planilha de indisponíveis; as abas
      de concluídas pelo DMSL não estavam no arquivo.</li>
      <li>${m.total_equipamentos - m.total_com_descricao} equipamentos não têm descrição de SS e
      não entram nos gráficos de categoria de defeito.</li>
      <li>As divergências apontadas são indícios para verificação com as áreas, não conclusões
      administrativas.</li>
    </ul></div>`;
}

/* ---------------- tema e início ---------------- */

const temaSalvo = localStorage.getItem('tema-equip');
if (temaSalvo) document.documentElement.dataset.tema = temaSalvo;

document.addEventListener('click', (ev) => {
  if (ev.target.closest('#tema')) {
    const atual = document.documentElement.dataset.tema
      || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'escuro' : 'claro');
    const novo = atual === 'escuro' ? 'claro' : 'escuro';
    document.documentElement.dataset.tema = novo;
    localStorage.setItem('tema-equip', novo);
  }
  if (ev.target.closest('#ir-inicio')) voltarBusca();
});

ligarBusca();
carregar();
