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
  { id: 'consolidado', nome: 'Carteira consolidada', desc: 'As duas listas fundidas: onde cada equipamento está de fato', termos: 'consolidado consolidada tudo junto fundido uniao das duas listas onde esta ponto atual situacao real resolvido pendente escada total geral 159 160' },
  { id: 'acompanhamento', nome: 'Acompanhamento atual', desc: 'Como está cada equipamento hoje, pelo parecer COEP mais recente', termos: 'acompanhamento atual hoje situacao em operacao cancelada errada dmsl pendente fluxo em analise desmobilizado check concluidas parecer atualizada novo primeiro ataque divergencia' },
  { id: 'entrada', nome: 'Carteira de entrada', desc: 'O que estava pendente quando assumi e quanto já reduzi', termos: 'entrada herdada assumi reduzi reducao pendente quando entrei foto inicial baixa canceladas tratativas ajustes comissionamento resolvi resolvidos quantos' },
  { id: 'mensal', nome: 'Entrada mês a mês', desc: 'A carteira herdada pela abertura da SS, todos os tipos, com o livro-caixa do posto', termos: 'mensal mes a mes mensalizado mensalizada 117 data de abertura abertura ss janeiro jan fev mar abr mai jun 2026 legado antigo quando abriu curva ritmo entrada por mes grafico barras entrantes resolvidos indisponibilidade recorte tiposs' },
  { id: 'reportes', nome: 'Reportes de campo', desc: 'As fotos que a equipe mandou, todas num lugar só', termos: 'reportes reporte campo foto fotos imagem imagens anexo anexos galeria prova equipe servico feito comprovacao ver as fotos' },
  { id: 'dcmd', nome: 'Missão DCMD', desc: 'Concluídas em 2026, o que vai entrar, SIGCO e o fluxo de repasse', termos: 'dcmd missao concluidas 2026 sigco 8481 8495 fluxo repasse cocm atrasado dmsl entrar' },
  { id: 'conclusao', nome: 'Conclusões', desc: 'Quantos já foram realizados, e com que certeza', termos: 'concluidas concluidos conclusao encerradas aic obras fechadas quantas quantos realizei realizadas realizados tratados tratadas provaveis resolvidos' },
  { id: 'coep', nome: 'Parecer COEP', desc: 'O que já deveria estar concluído e não está', termos: 'coep parecer pendencia atraso prazo vencido sla' },
  { id: 'emd', nome: 'Cruzamento EMD', desc: 'Divergências entre a requisição e a criticidade', termos: 'emd requisicao divergencia obra deposito material' },
  { id: 'compras', nome: 'Plano de compras', desc: 'Pedido de 17/07/2026, prazos e conferência', termos: 'compras compra pedido plano valor preco prazo 120 180 portilho' },
  { id: 'classificacoes', nome: 'Minhas classificações', desc: 'O que você marcou à mão e o arquivo para me mandar', termos: 'minhas classificacoes classificar marcar corrigir gestor decisao exportar download json' },
  { id: 'frota', nome: 'Mapa e frota', desc: 'Onde estão, marca, potência e especificação', termos: 'mapa frota coordenada localizacao marca modelo potencia tensao kvar especificacao ajustes' },
  { id: 'visao', nome: 'Visão geral', desc: 'Distribuição da carteira em números', termos: 'visao geral panorama distribuicao criticidade resumo grafico' },
  { id: 'metodo', nome: 'Metodologia', desc: 'De onde vem cada número e o que ele não prova', termos: 'metodologia metodo fonte limite como foi feito' },
];

function bucketParecer(p) {
  const t = puro(p || '');
  if (!t.trim()) return 'Sem parecer';
  if (t.includes('aquisi')) return 'Em aquisição';
  if (t.includes('logistic')) return 'Em logística';
  if (t.includes('comission')) return 'Aguardando comissionamento';
  if (t.includes('ajust')) return 'Em fase de ajustes';
  if (t.includes('entregue')) return 'Entregue ao COCM';
  if (t.includes('conclu') || t.includes('substitu')) return 'Concluído/substituído';
  if (t.includes('dmsl') || t.includes('laudo')) return 'Aguardando DMSL/laudo';
  return 'Outros pareceres';
}

const estado = {
  equipamentos: [], alertas: [], divergencias: [], compras: [], meta: null, imagens: {}, classificacoes: {},
  termo: '', facetas: {}, limite: 40, selecionado: -1, vista: 'busca',
};

/* ---------------- utilidades ---------------- */

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const moedaBR = (v) => Number(v || 0)
  .toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

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
  estado.classificacoes = lerClassificacoes();
  if (typeof DADOS_EMBUTIDOS !== 'undefined') {
    Object.assign(estado, DADOS_EMBUTIDOS);
  } else {
    try {
      const [equipamentos, alertas, divergencias, compras, meta, geo, imagens] = await Promise.all([
        fetch('data/equipamentos.json').then((r) => r.json()),
        fetch('data/alertas_coep.json').then((r) => r.json()),
        fetch('data/divergencias_emd.json').then((r) => r.json()),
        fetch('data/plano_compras.json').then((r) => r.json()),
        fetch('data/meta.json').then((r) => r.json()),
        fetch('data/geo_tocantins.json').then((r) => r.json()).catch(() => null),
        fetch('data/reportes_imagens.json').then((r) => r.json()).catch(() => ({})),
      ]);
      Object.assign(estado, { equipamentos, alertas, divergencias, compras, meta, geo, imagens });
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
    ['Realizadas', m.realizadas?.total ?? m.conclusao.confirmadas, ''],
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
  { id: 'parecer', rotulo: 'Parecer COEP', valores: null, de: (e) => bucketParecer(e.parecer_coep) },
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

  const ordemParecer = ['Em aquisição', 'Em logística', 'Entregue ao COCM',
    'Aguardando comissionamento', 'Em fase de ajustes', 'Aguardando DMSL/laudo',
    'Concluído/substituído', 'Outros pareceres', 'Sem parecer'];
  const chipsParecer = ordemParecer
    .map((bkt) => [bkt, estado.equipamentos.filter((e) => bucketParecer(e.parecer_coep) === bkt).length])
    .filter(([, n]) => n)
    .map(([bkt, n]) => `<button class="pastilha" data-faceta="parecer" data-valor="${esc(bkt)}" aria-pressed="false">${esc(bkt)} <b>${n}</b></button>`)
    .join('');

  const html = atalhos.map((a) => {
    const n = estado.equipamentos.filter(a.teste).length;
    return `<button class="pastilha" data-atalho="${a.id}" aria-pressed="false">${esc(a.rotulo)} <b>${n}</b></button>`;
  }).join('') +
  ORDEM_CRIT.filter((c) => estado.equipamentos.some((e) => e.criticidade === c))
    .map((c) => {
      const n = estado.equipamentos.filter((e) => e.criticidade === c).length;
      return `<button class="pastilha" data-faceta="criticidade" data-valor="${esc(c)}" aria-pressed="false">${esc(c)} <b>${n}</b></button>`;
    }).join('') + chipsParecer +
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
  // Casa por palavra, não pela frase inteira: "quantos já concluí" precisa achar
  // Conclusões. Tokens curtos (a, de, já) não contam; ranqueia por nº de acertos.
  const tokens = t.split(/\s+/).filter((x) => x.length >= 4);
  if (!tokens.length) return COLECOES.filter((c) => puro(`${c.nome} ${c.desc} ${c.termos}`).includes(t));
  return COLECOES
    .map((c) => {
      const alvo = puro(`${c.nome} ${c.desc} ${c.termos}`);
      const acertos = tokens.filter((tk) => alvo.includes(tk)).length;
      return { c, acertos };
    })
    .filter((x) => x.acertos > 0)
    .sort((a, b) => b.acertos - a.acertos)
    .map((x) => x.c);
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
  // Clipe na linha da busca: este ativo tem reporte de campo com foto anexa.
  const fotos = (e.reportes_campo || []).reduce((n, r) => n + (r.imagem ? 1 : (r.anexo?.fotos || 0)), 0);
  return `<button class="linha fila c-${chave(e.criticidade)}" data-ativo="${esc(e.ativo)}" data-idx="${idx}">
    <span class="ponto"></span>
    <span>
      <span class="principal">
        <span class="cod">${esc(e.ativo)}</span>
        <span class="nome">${esc(e.localidade || '—')} · ${esc(e.tipo_nome)}</span>
        ${fotos ? `<span class="clipe" title="reporte de campo com ${fotos} foto${fotos > 1 ? 's' : ''} anexa${fotos > 1 ? 's' : ''}">📎 ${fotos}</span>` : ''}
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

/* ---------------- classificação do gestor ----------------
   O painel é um arquivo só, sem servidor. O que o gestor classifica fica no
   navegador dele e sai daqui por download, para virar decisão no repositório. */

const ESCADA_GESTOR = [
  'Em operação',
  'Executado — falta ajuste ou comissionamento',
  'Em execução',
  'Pendente no COEP',
  'Pendente com outra equipe',
  'Cancelada errada pelo DMSL',
  'Em análise',
  'Sem ação do COEP',
  'Fora da análise',
];

const CHAVE_CLASSIF = 'coep.classificacoes.v1';

function lerClassificacoes() {
  try { return JSON.parse(localStorage.getItem(CHAVE_CLASSIF) || '{}'); } catch { return {}; }
}

function gravarClassificacao(ativo, dados) {
  const todas = lerClassificacoes();
  if (dados) todas[ativo] = dados; else delete todas[ativo];
  try { localStorage.setItem(CHAVE_CLASSIF, JSON.stringify(todas)); } catch { /* modo privado */ }
  estado.classificacoes = todas;
}

function painelClassificacao(e) {
  const minha = (estado.classificacoes || {})[e.ativo];
  const atual = e.consolidado?.situacao || '—';
  return `<section class="bloco" id="classificar"><h3>Sua classificação</h3>
    <p class="destaque-texto">O painel diz <b>${esc(atual)}</b>. Se você sabe que é outra coisa, marque aqui —
    fica guardado neste navegador e sai por download para virar decisão no repositório.</p>
    ${minha ? `<div class="nota" style="margin-bottom:12px"><strong>Já classificado por você</strong>
      ${esc(minha.situacao)}${minha.nota ? ` — ${esc(minha.nota)}` : ''} <i>(${esc(minha.data)})</i></div>` : ''}
    <div class="opcoes-classif">
      ${ESCADA_GESTOR.map((s) => `<button class="pastilha op-classif" data-situacao="${esc(s)}"
        aria-pressed="${minha?.situacao === s}">${esc(s)}</button>`).join('')}
    </div>
    <label class="rotulo" for="nota-classif" style="display:block;margin:16px 0 6px">Por quê</label>
    <textarea id="nota-classif" rows="3" placeholder="o que você sabe que o sistema não sabe"
      >${esc(minha?.nota || '')}</textarea>
    <div class="acoes-classif">
      <button class="pastilha" id="salvar-classif">Salvar</button>
      ${minha ? '<button class="pastilha limpar" id="apagar-classif">Apagar a minha</button>' : ''}
      <a class="pastilha" href="#" data-colecao="classificacoes">Ver todas as minhas</a>
    </div></section>`;
}

function ligarClassificacao(e) {
  const secao = $('#classificar');
  if (!secao) return;
  let escolhida = (estado.classificacoes || {})[e.ativo]?.situacao || '';
  secao.querySelectorAll('.op-classif').forEach((b) => b.addEventListener('click', () => {
    escolhida = b.dataset.situacao;
    secao.querySelectorAll('.op-classif').forEach((o) => o.setAttribute('aria-pressed', o === b));
  }));
  $('#salvar-classif')?.addEventListener('click', () => {
    if (!escolhida) { alert('Escolha uma situação primeiro.'); return; }
    gravarClassificacao(e.ativo, {
      ativo: e.ativo,
      localidade: e.localidade || '',
      situacao: escolhida,
      nota: $('#nota-classif').value.trim(),
      situacao_do_painel: e.consolidado?.situacao || '',
      data: new Date().toLocaleDateString('pt-BR'),
    });
    abrirAtivo(e.ativo);
  });
  $('#apagar-classif')?.addEventListener('click', () => {
    gravarClassificacao(e.ativo, null);
    abrirAtivo(e.ativo);
  });
}

async function baixarClassificacoes() {
  const todas = Object.values(estado.classificacoes || {});
  if (!todas.length) { alert('Você ainda não classificou nenhum ativo.'); return; }
  const conteudo = JSON.stringify(todas, null, 2);
  if (window.claude?.downloads?.save) {
    try {
      await window.claude.downloads.save({ filename: 'classificacoes-coep.json', data: conteudo });
      return;
    } catch (erro) { console.warn('download recusado', erro); }
  }
  // Sem o download disponível, mostra o JSON para copiar e cola na conversa.
  const area = $('#json-classif');
  if (!area) return;
  area.value = conteudo;
  area.style.display = 'block';
  area.focus();
  area.select();
  try { document.execCommand('copy'); } catch { /* o usuário copia à mão */ }
  const aviso = $('#aviso-classif');
  if (aviso) {
    aviso.textContent = 'Copiado. Cole na conversa que eu registro como decisão no repositório.';
    aviso.style.display = 'block';
  }
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
    e.realizada?.veredito ? '<span class="selo c-baixa">✓ Realizada</span>' : '',
    e.realizada?.origem_cancelamento === 'Sem reincidência' ? '<span class="selo neutro">sem reincidência</span>' : '',
    c ? `<span class="selo ${c.situacao === 'Confirmada no AIC' ? 'c-baixa' : c.situacao === 'Indício contestado' ? 'c-alta' : 'neutro'}">${esc(c.situacao)}</span>` : '',
    (estado.classificacoes || {})[e.ativo] ? `<span class="selo destaque">classificado por você</span>` : '',
  ].filter(Boolean).join('');

  const partes = [`<header class="cabeca">
    <div class="cod">${esc(e.ativo)}</div>
    <div class="nome">${esc(e.localidade || 'localidade não informada')} · ${esc(e.polo || '—')} / ${esc(e.regional || '—')}</div>
    <div class="selos">${selos}</div>
  </header>`];

  if (e.realizada) {
    const r = e.realizada;
    partes.push(bloco('Foi realizada?', `
      <p class="destaque-texto">${r.veredito
        ? 'Sim — pela régua do gestor: ' + esc(r.vias.join(' e ')) +
          (r.origem_cancelamento === 'Sem reincidência' ? ' (inferida: cancelada e nada reabriu no ativo)' : '') +
          ', sem demanda aberta.'
        : (r.vias.length
          ? 'Candidata (' + esc(r.vias.join(' e ')) + '), mas o ativo ainda tem demanda aberta.'
          : 'Não — nenhuma via se aplica: sem AIC encerrado, sem cancelamento em operação, e há demanda aberta ou nenhuma cancelada.')}</p>
      ${r.evidencias.map((ev) => `<div class="item-linha"><span>${esc(ev)}</span><b>evidência</b></div>`).join('')}
      ${r.demanda_bloqueando ? `<div class="nota branda" style="margin-top:10px">
        <strong>Demanda aberta bloqueando</strong>${esc(r.demanda_bloqueando.numero_ss || '—')} (${esc(r.demanda_bloqueando.equipe || '—')}) · ${esc((r.demanda_bloqueando.situacao || '').replace('SS ', ''))} · aberta em ${dataBr(r.demanda_bloqueando.abertura)}</div>` : ''}
      ${r.confianca_m5 ? `<div class="item-linha" style="margin-top:8px"><span>Confiança da leitura do cancelamento</span><b>${esc(r.confianca_m5)}</b></div>` : ''}`));
  }

  (e.agenda_campo || []).forEach((ag) => {
    partes.push(bloco('Programado para campo', `
      <p class="destaque-texto"><b>${dataBr(ag.data)}</b>${ag.condicional ? ` — ${esc(ag.condicional)}` : ''}.
      ${esc(ag.servico || '')}</p>
      <div class="campos">
        ${campo('Material', esc(ag.material || '—'))}
        ${campo('Quem executa', esc(ag.quem_executa || '—'))}
        ${ag.valor ? campo('Valor', 'R$ ' + moedaBR(ag.valor)) : ''}
      </div>
      ${ag.situacao_material ? `<div class="item-linha" style="margin-top:8px"><span>Situação do material</span><b>${esc(ag.situacao_material)}</b></div>` : ''}
      ${ag.nota ? `<div class="nota branda" style="margin-top:10px"><strong>Origem das peças</strong>${esc(ag.nota)}</div>` : ''}
      ${ag.divergencia ? `<div class="nota" style="margin-top:10px"><strong>Divergência de data</strong>${esc(ag.divergencia)}</div>` : ''}
      <div class="reporte-fonte">${esc(ag.fonte || '')}</div>`));
  });

  (e.reportes_campo || []).forEach((rc) => {
    // O anexo pode estar embutido (foto no repositório) ou só anunciado, quando o
    // gestor mandou as fotos pela conversa e o arquivo ainda não chegou.
    const temFoto = rc.imagem && estado.imagens?.[rc.imagem];
    const anexo = temFoto
      ? { texto: 'Foto anexa — clique para ampliar', tom: 'destaque' }
      : rc.anexo
        ? { texto: `${rc.anexo.fotos} foto${rc.anexo.fotos > 1 ? 's' : ''} anexa${rc.anexo.fotos > 1 ? 's' : ''} — ${esc(rc.anexo.estado)}`, tom: 'neutro' }
        : null;
    partes.push(bloco('Reporte de campo — serviço concluído', `
      <div class="reporte">
        <div class="reporte-topo">
          <span class="reporte-acao">${esc(rc.acao || 'Ação de manutenção')}</span>
          ${anexo ? `<span class="selo ${anexo.tom} reporte-anexo">${anexo.texto}</span>` : ''}
          <span class="reporte-data">${dataBr(rc.data)}</span>
        </div>
        <h4 class="reporte-titulo">${esc(rc.titulo)}</h4>
        <p class="reporte-sub">${esc(rc.subtitulo || '')}</p>
        ${rc.faixa ? `<div class="reporte-faixa">${esc(rc.faixa)}</div>` : ''}
        <div class="campos">
          ${campo('Local', esc(rc.local || '—'))}
          ${campo('Equipe', esc(rc.equipe || '—'))}
          ${rc.cocm ? campo('COCM', esc(rc.cocm)) : ''}
          ${rc.polo ? campo('Polo', esc(rc.polo)) : ''}
          ${rc.ordem_servico ? campo('Ordem de serviço', esc(rc.ordem_servico)) : ''}
          ${rc.servico_executado ? campo('Serviço executado', esc(rc.servico_executado)) : ''}
          ${rc.equipamento_instalado ? campo('Equipamento instalado', esc(rc.equipamento_instalado)) : ''}
        </div>
        ${rc.objetivo ? `<p class="destaque-texto" style="margin-top:12px">${esc(rc.objetivo)}</p>` : ''}
        ${temFoto
          ? `<a class="reporte-foto" href="${estado.imagens[rc.imagem]}" target="_blank" rel="noopener">
             <img src="${estado.imagens[rc.imagem]}" alt="Reporte de campo do ativo ${esc(rc.ativo)} em ${dataBr(rc.data)}" loading="lazy"></a>`
          : rc.anexo ? `<div class="nota" style="margin-top:12px"><strong>${rc.anexo.fotos} foto${rc.anexo.fotos > 1 ? 's' : ''} deste reporte — ${esc(rc.anexo.estado)}</strong>${esc(rc.anexo.descricao)}</div>` : ''}
        ${rc.vinculo ? `<div class="nota branda" style="margin-top:12px">
          <strong>Como esse reporte foi ligado ao ativo</strong>${esc(rc.vinculo)}</div>` : ''}
        <div class="reporte-fonte">${esc(rc.fonte || '')}</div>
      </div>`));
  });

  if (e.consolidado) {
    const c2 = e.consolidado;
    partes.push(bloco('Em que ponto está', `
      <p class="destaque-texto">${esc(c2.situacao)} — ${esc(c2.porque)}</p>
      <div class="campos">
        ${campo('Origem', esc(c2.origem))}
        ${campo('Posto atual', esc(c2.posto_atual || 'sem demanda aberta'))}
      </div>`));
  }

  if (e.acompanhamento) {
    const ac = e.acompanhamento;
    partes.push(bloco('Acompanhamento atual', `
      <p class="destaque-texto">${esc(ac.situacao)}${ac.sem_acao_coep ? ' — desmobilizado, caso sem ação do COEP' : ''}</p>
      <div class="campos">
        ${campo('Check de concluídas', esc(ac.check))}
        ${campo('SS mais recente na base', esc(ac.na_base.ss_mais_recente || '—'))}
        ${campo('Equipe', esc(ac.na_base.equipe || '—'))}
        ${campo('Situação dessa SS', esc((ac.na_base.situacao || '—').replace('SS ', '')))}
        ${campo('Demanda aberta hoje', ac.na_base.demanda_aberta ? esc(ac.na_base.posto_atual || 'sim') : 'nenhuma')}
      </div>
      ${(ac.alertas || []).length ? ac.alertas.map((x) => `<div class="nota" style="margin-top:10px">
        <strong>Planilha × base</strong>${esc(x)}</div>`).join('') : ''}`));
  }

  if ((e.entrada || []).length) {
    const rotulo = { resolvido: 'Saiu da carteira de entrada', verificar: 'Precisa de verificação', em_andamento: 'Ainda no fluxo' };
    partes.push(bloco('Estava na carteira de entrada', e.entrada.map((x) => `
      <p class="destaque-texto">${esc(rotulo[x.veredito] || x.veredito)} — ${esc(x.motivo)}</p>
      <div class="campos">
        ${campo('SS da foto de entrada', esc(x.numero_ss))}
        ${campo('Aberta em', x.abertura ? dataBr(x.abertura) : '—')}
        ${campo('Tipo de SS', esc(x.tiposs || '—'))}
        ${campo('Situação hoje', esc(x.situacao_hoje || '—'))}
        ${campo('Régua do gestor', x.regra ? `item ${x.regra}` : '—')}
        ${campo('Posto atual', esc(x.posto_atual || '—'))}
      </div>
      ${(x.tratativa || []).length ? `<div class="itens" style="margin-top:10px">${x.tratativa.map((t) =>
        `<div class="item-linha"><span>${esc(t)}</span><b>tratativa</b></div>`).join('')}</div>` : ''}
      ${(x.obras_encerradas || []).length ? `<div class="item-linha"><span>Obra encerrada no AIC</span><b>${x.obras_encerradas.map(esc).join(' · ')}</b></div>` : ''}
      ${x.decisao_gestor ? `<div class="nota calma" style="margin-top:10px">
        <strong>Confirmado pelo gestor em ${dataBr(x.decisao_gestor.data)}</strong>${esc(x.decisao_gestor.nota)}</div>` : ''}
      ${(x.cauda_mesma_demanda || []).length ? `<div class="nota ${x.alerta_cauda ? '' : 'calma'}" style="margin-top:10px">
        <strong>Mesma demanda, etapa seguinte${x.etapa_final ? ' — falta ' + (x.etapa_final === 'DEOP' ? 'o ajuste da Proteção' : 'o comissionamento do DMSL') : ''}</strong>
        ${x.cauda_mesma_demanda.map((i) => `${esc(i.numero)} · ${esc(i.equipe)} (${esc(i.departamento)}) · aberta em ${dataBr(i.abertura)}`).join('<br>')}
        ${x.alerta_cauda ? '<br>Atenção: o texto desta SS fala em espera de material ou defeito novo.' : ''}</div>` : ''}
      ${(x.indisponibilidades_abertas || []).length ? `<div class="nota" style="margin-top:10px">
        <strong>SS de indisponibilidade de outra demanda</strong>${x.indisponibilidades_abertas.map((i) =>
          `${esc(i.numero)} · ${esc(i.equipe)} (${esc(i.departamento)}) · aberta em ${dataBr(i.abertura)}`).join('<br>')}</div>` : ''}`).join('<div class="separador-bloco"></div>')));
  }

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

  if (e.demandas?.length) {
    const naoRotina = e.demandas.filter((d) => !d.rotina);
    if (naoRotina.length) {
      partes.push(bloco('Demandas encadeadas (a lógica do SGM)', naoRotina.slice(0, 6).map((d) => `
        <div class="nota ${d.situacao === 'aberta' ? (d.repasse_pendurado ? '' : 'branda') : 'calma'}" style="margin-bottom:10px">
          <strong>${esc(d.postos.join(' → '))} · ${esc(d.situacao)}${d.posto_atual ? ' no ' + esc(d.posto_atual) : ''}${d.repasse_pendurado ? ' · repasse pendurado' : ''}</strong>
          ${d.ss.map((x) => `${esc(x.numero)} (${esc(x.equipe)}, ${esc(x.situacao).replace('SS ', '')})`).join(' → ')}
          ${d.abertura ? `<br>aberta em ${dataBr(d.abertura)}${d.termino ? ' · concluída em ' + dataBr(d.termino) : ''}` : ''}
        </div>`).join('')));
    }
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

  const demAberta = (e.demandas || []).find((d) => d.situacao === 'aberta' && !d.rotina);
  const ssAtual = demAberta
    ? (demAberta.ss.filter((x) => x.situacao !== 'SS ATENDIDA' && x.situacao !== 'SS CANCELADA').slice(-1)[0] || demAberta.ss.slice(-1)[0])
    : null;
  partes.push(bloco('Registro na planilha de criticidade', `<div class="campos">
    ${campo('SS aberta atual (base SS/OS)', ssAtual ? esc(`${ssAtual.numero} · ${ssAtual.equipe}`) : 'nenhuma demanda aberta')}
    ${campo('SS na planilha', esc(e.ss || '—'))}
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

  partes.push(painelClassificacao(e));

  paginaLeitura(partes.join(''));
  ligarClassificacao(e);
}

/* ---------------- coleções ---------------- */

function num({ rotulo, valor, nota, tom = '' }) {
  const longo = String(valor).length > 11 ? ' longo' : '';
  return `<div class="numero ${tom}"><span>${esc(rotulo)}</span>
    <strong class="${longo.trim()}">${esc(valor)}</strong>
    ${nota ? `<small>${esc(nota)}</small>` : ''}</div>`;
}

/* Barras agrupadas — três séries por mês. As cores saem de --serie-1/2/3, que
   passaram pelo validador de paleta nos dois temas: azul-tinta, o laranja do
   sinal e o verde. Cada barra leva o valor escrito em cima, então a identidade
   nunca depende só da cor. */
function barrasTresColunas(curva, series) {
  const SERIES = series || [
    { chave: 'entrantes', nome: 'Entrantes', cor: 'var(--serie-1)',
      dica: 'a carteira herdada, pela abertura da SS — janeiro carrega o acervo' },
    { chave: 'resolvidos', nome: 'Resolvidos', cor: 'var(--serie-3)',
      dica: 'pelo mês da tratativa ou do repasse' },
  ];
  const teto = Math.max(...curva.flatMap((m) => SERIES.map((s) => m[s.chave])), 1);
  const L = 44, R = 12, T = 22, B = 44;      // margens
  const larguraGrupo = 96, alturaPlot = 210;
  const W = L + R + larguraGrupo * curva.length;
  const H = T + alturaPlot + B;
  const larguraBarra = 24, vao = 2;          // 2px de papel entre barras vizinhas
  const bloco = SERIES.length * larguraBarra + (SERIES.length - 1) * vao;

  const passo = teto <= 10 ? 2 : teto <= 30 ? 10 : 20;
  const riscos = [];
  for (let v = 0; v <= teto; v += passo) riscos.push(v);

  const y = (v) => T + alturaPlot - (v / teto) * alturaPlot;

  return `<figure class="grafico-barras">
    <div class="legenda-series">
      ${SERIES.map((s) => `<span class="serie"><i style="background:${s.cor}"></i>
        <b>${esc(s.nome)}</b> <em>${esc(s.dica)}</em></span>`).join('')}
    </div>
    <div class="tela-grafico">
    <svg viewBox="0 0 ${W} ${H}" role="img" preserveAspectRatio="xMinYMid meet"
         aria-label="Barras agrupadas por mês de 2026: ${curva.map((m) => `${m.rotulo}, ${SERIES.map((s) => `${s.nome} ${m[s.chave]}`).join(', ')}`).join('; ')}">
      ${riscos.map((v) => `<g>
        <line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="risco"/>
        <text x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" class="rot-eixo" text-anchor="end">${v}</text>
      </g>`).join('')}
      <line x1="${L}" x2="${W - R}" y1="${T + alturaPlot}" y2="${T + alturaPlot}" class="base-eixo"/>
      ${curva.map((m, i) => {
        const x0 = L + i * larguraGrupo + (larguraGrupo - bloco) / 2;
        return `<g class="grupo-mes">
          ${SERIES.map((s, j) => {
            const v = m[s.chave];
            const x = x0 + j * (larguraBarra + vao);
            const alt = Math.max((v / teto) * alturaPlot, v ? 2 : 0);
            return `<g class="barra-mes">
              <title>${esc(m.rotulo)} · ${esc(s.nome)}: ${v}</title>
              <rect x="${x}" y="${(T + alturaPlot - alt).toFixed(1)}" width="${larguraBarra}"
                    height="${alt.toFixed(1)}" rx="4" ry="4" fill="${s.cor}"
                    class="${v ? '' : 'vazia'}"/>
              ${v ? `<rect x="${x}" y="${(T + alturaPlot - Math.min(alt, 5)).toFixed(1)}"
                    width="${larguraBarra}" height="${Math.min(alt, 5).toFixed(1)}" fill="${s.cor}"/>` : ''}
              ${v ? `<text x="${x + larguraBarra / 2}" y="${(T + alturaPlot - alt - 5).toFixed(1)}"
                    class="rot-valor" text-anchor="middle">${v}</text>` : ''}
            </g>`;
          }).join('')}
          <text x="${(x0 + bloco / 2).toFixed(1)}" y="${T + alturaPlot + 18}"
                class="rot-mes" text-anchor="middle">${esc(m.rotulo)}</text>
        </g>`;
      }).join('')}
    </svg>
    </div>
    <figcaption>Cada barra traz o próprio número, então dá para ler a figura sem
    depender da cor. Os mesmos valores estão na tabela abaixo.</figcaption>
  </figure>`;
}

/* O saldo da carteira herdada, mês a mês. Série única — sem caixa de legenda;
   a coluna cinza da frente é o acervo com que o posto abriu o ano. */
function colunaSaldo(mm) {
  const cols = [
    { rotulo: 'Acervo', final: mm.abertura, tipo: 'acervo',
      conta: `Acervo: ${mm.abertura} SS de 2023–2025 pendentes na abertura de 2026` },
    ...mm.saldo.map((s) => ({ rotulo: s.rotulo, final: s.final, tipo: '',
      conta: `${s.rotulo}: começou com ${s.inicial}, abriram ${s.entram}, tratados ${s.saem}, sobrou ${s.final}` })),
  ];
  const picoV = Math.max(...mm.saldo.map((s) => s.final));
  const teto = Math.ceil(Math.max(picoV, mm.abertura, 1) / 20) * 20;
  const L = 44, R = 12, T = 22, B = 44;
  const largura = 88, alturaPlot = 190;
  const W = L + R + largura * cols.length;
  const H = T + alturaPlot + B;
  const barra = 34;
  const y = (v) => T + alturaPlot - (v / teto) * alturaPlot;
  const riscos = [];
  for (let v = 0; v <= teto; v += 20) riscos.push(v);

  return `<figure class="grafico-barras grafico-saldo">
    <div class="tela-grafico">
    <svg viewBox="0 0 ${W} ${H}" role="img" preserveAspectRatio="xMinYMid meet"
         aria-label="Saldo da carteira herdada no fim de cada mês: ${cols.map((c) => `${c.rotulo}, ${c.final}`).join('; ')}">
      ${riscos.map((v) => `<g>
        <line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="risco"/>
        <text x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" class="rot-eixo" text-anchor="end">${v}</text>
      </g>`).join('')}
      <line x1="${L}" x2="${W - R}" y1="${T + alturaPlot}" y2="${T + alturaPlot}" class="base-eixo"/>
      ${cols.map((c, i) => {
        const x = L + i * largura + (largura - barra) / 2;
        const alt = Math.max((c.final / teto) * alturaPlot, c.final ? 2 : 0);
        return `<g class="barra-mes ${c.tipo}${!c.tipo && c.final === picoV ? ' pico' : ''}">
          <title>${esc(c.conta)}</title>
          <rect x="${x}" y="${(T + alturaPlot - alt).toFixed(1)}" width="${barra}"
                height="${alt.toFixed(1)}" rx="4" ry="4"/>
          <rect x="${x}" y="${(T + alturaPlot - Math.min(alt, 5)).toFixed(1)}"
                width="${barra}" height="${Math.min(alt, 5).toFixed(1)}"/>
          <text x="${x + barra / 2}" y="${(T + alturaPlot - alt - 6).toFixed(1)}"
                class="rot-valor" text-anchor="middle">${c.final}</text>
          <text x="${x + barra / 2}" y="${T + alturaPlot + 18}" class="rot-mes"
                text-anchor="middle">${esc(c.rotulo)}</text>
        </g>`;
      }).join('')}
    </svg>
    </div>
    <figcaption>A coluna cinza é o acervo herdado; as azuis, o saldo no fim de cada mês;
    a laranja marca o topo da fila. Passe o mouse para ver a conta do mês inteiro.</figcaption>
  </figure>`;
}

/* O livro-caixa: saldo do mês anterior + SS abertas no mês − tratadas = sobra. */
function livroCaixa(mm) {
  const sal = mm.saldo;
  const totE = sal.reduce((n, s) => n + s.entram, 0);
  const totS = sal.reduce((n, s) => n + s.saem, 0);
  const fim = sal[sal.length - 1];
  return `${colunaSaldo(mm)}
  <div class="tabela-rol" style="margin-top:18px"><table class="matriz livro"><thead><tr>
    <th>Mês</th><th class="num">Começou com</th><th class="num">Entraram</th>
    <th class="num">Saíram</th><th class="num">Sobrou no fim</th>
    <th class="num">Variação</th></tr></thead><tbody>
    <tr><td>Acervo de 2023–2025 <i>(saldo de abertura)</i></td><td class="num">—</td>
      <td class="num">—</td><td class="num">—</td><td class="num"><b>${mm.abertura}</b></td>
      <td class="num">—</td></tr>
    ${sal.map((s) => {
      const d = s.final - s.inicial;
      return `<tr><td>${esc(s.rotulo)}</td><td class="num">${s.inicial}</td>
        <td class="num">${s.entram || '—'}</td><td class="num">${s.saem || '—'}</td>
        <td class="num"><b>${s.final}</b></td>
        <td class="num ${d > 0 ? 'sobe' : d < 0 ? 'desce' : ''}">${d > 0 ? '+' : ''}${d || '—'}</td></tr>`;
    }).join('')}
  </tbody><tfoot><tr><td>Total até 18/08</td><td class="num">—</td>
    <td class="num"><b>${totE}</b></td><td class="num"><b>${totS}</b></td>
    <td class="num"><b>${fim.final}</b></td>
    <td class="num">${fim.final - mm.abertura > 0 ? '+' : ''}${fim.final - mm.abertura}</td></tr></tfoot></table></div>
  <div class="nota" style="margin-top:14px"><strong>A conta fecha na carteira</strong>
  ${mm.abertura} do acervo + ${totE} abertas em 2026 = ${mm.abertura + totE} ativos da foto;
  ${totS} tratados na janela; sobram ${fim.final} em 18/08${mm.apos_janela?.resolvidos
    ? ` — e mais ${mm.apos_janela.resolvidos} já ${mm.apos_janela.resolvidos > 1 ? 'foram tratados' : 'foi tratado'} em agosto${(mm.apos_janela.lista || []).length ? ` (${mm.apos_janela.lista.map((x) => esc(x.localidade)).join(' e ')})` : ''}, fora da janela, deixando ${fim.final - mm.apos_janela.resolvidos} no fluxo hoje`
    : ' — exatamente os que a carteira mostra ainda no fluxo'}.
  ${mm.ss_resolvidas > totS + (mm.apos_janela?.resolvidos || 0) ? `Na conta por SS são ${mm.ss_resolvidas} resolvidas — ${(mm.resolvidos_duplicados || []).map((a) => `<b class="mono">${esc(a)}</b>`).join(' e ')} tinham duas SS cada na foto e contam uma vez no livro. Contando por SS, a janela fecharia em ${mm.abertura + totE - mm.ss_resolvidas}.` : ''}
  Os ${mm.fora_do_livro} ativos que passaram pelo COEP em 2026 por fora da foto não entram neste
  livro: sem SS na foto de entrada, não há data de tratativa rastreada para dar baixa. Eles
  seguem na coluna de entrantes e na lista própria.</div>`;
}

/* A mesma coisa somando: onde cada série chegou até o fim de cada mês. Linha em
   vez de barra porque o que importa aqui é a distância entre as curvas — o
   tamanho da fila contra o que já saiu — e barra empilhada esconde isso. */
function linhaAcumulada(curva, series) {
  const SERIES = series || [
    { chave: 'entrantes', nome: 'Entrantes', cor: 'var(--serie-1)' },
    { chave: 'resolvidos', nome: 'Resolvidos', cor: 'var(--serie-3)' },
  ];
  const soma = {};
  SERIES.forEach((s) => { soma[s.chave] = 0; });
  const ac = curva.map((m) => {
    SERIES.forEach((s) => { soma[s.chave] += m[s.chave] || 0; });
    return { ...soma, mes: m.mes, rotulo: m.rotulo };
  });
  const bruto = Math.max(...ac.flatMap((m) => SERIES.map((s) => m[s.chave])), 1);
  const passo = bruto <= 50 ? 10 : 20;
  const teto = Math.ceil(bruto / passo) * passo;
  const L = 44, R = 58, T = 20, B = 44;
  const largura = 108, alturaPlot = 210;
  const W = L + R + largura * (ac.length - 1);
  const H = T + alturaPlot + B;
  const x = (i) => L + i * largura;
  const y = (v) => T + alturaPlot - (v / teto) * alturaPlot;
  const riscos = [];
  for (let v = 0; v <= teto; v += passo) riscos.push(v);

  return `<figure class="grafico-barras grafico-linha">
    <div class="legenda-series">
      ${SERIES.map((s) => `<span class="serie"><i style="background:${s.cor}"></i>
        <b>${esc(s.nome)}</b> <em>somando mês a mês</em></span>`).join('')}
    </div>
    <div class="tela-grafico">
    <svg viewBox="0 0 ${W} ${H}" role="img" preserveAspectRatio="xMinYMid meet"
         aria-label="Acumulado de 2026 até cada mês: ${ac.map((m) => `${m.rotulo}, ${SERIES.map((s) => `${s.nome} ${m[s.chave]}`).join(', ')}`).join('; ')}">
      ${riscos.map((v) => `<g>
        <line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="risco"/>
        <text x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" class="rot-eixo" text-anchor="end">${v}</text>
      </g>`).join('')}
      <line x1="${L}" x2="${W - R}" y1="${T + alturaPlot}" y2="${T + alturaPlot}" class="base-eixo"/>
      ${ac.map((m, i) => `<text x="${x(i)}" y="${T + alturaPlot + 18}" class="rot-mes"
        text-anchor="middle">${esc(m.rotulo)}</text>`).join('')}
      ${SERIES.map((s) => `<polyline class="traco" stroke="${s.cor}"
        points="${ac.map((m, i) => `${x(i)},${y(m[s.chave]).toFixed(1)}`).join(' ')}"/>`).join('')}
      ${SERIES.map((s) => ac.map((m, i) => `<g class="ponto-linha">
        <title>${esc(m.rotulo)} · ${esc(s.nome)}, acumulado: ${m[s.chave]}</title>
        <circle cx="${x(i)}" cy="${y(m[s.chave]).toFixed(1)}" r="4.5" fill="${s.cor}"/>
        <circle cx="${x(i)}" cy="${y(m[s.chave]).toFixed(1)}" r="11" fill="transparent"/>
      </g>`).join('')).join('')}
      ${SERIES.map((s) => {
        const ultimo = ac[ac.length - 1];
        return `<text x="${x(ac.length - 1) + 12}" y="${(y(ultimo[s.chave]) + 4).toFixed(1)}"
          class="rot-fim" text-anchor="start">${ultimo[s.chave]}</text>`;
      }).join('')}
    </svg>
    </div>
    <figcaption>O número no fim de cada linha é onde ela chegou em 18/08 — agosto é mês
    parcial. Passe o
    mouse num ponto para ver o acumulado daquele mês.</figcaption>
  </figure>`;
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
  $$('.carta[data-ativo], .tabela tbody tr[data-ativo], .matriz tbody tr[data-ativo], .ponto-mapa[data-ativo]').forEach((el) => {
    el.addEventListener('click', () => abrirAtivo(el.dataset.ativo));
  });
}

function abrirColecao(id) {
  const m = estado.meta;
  let html = '';

  if (id === 'conclusao') {
    const c = m.conclusao;
    const r = m.realizadas || {};
    html = cabecaColecao('Conclusões', 'Quantos equipamentos já foram realizados — e o quanto disso é certeza.') +
      `<div class="numeros">
        ${num({ rotulo: 'REALIZADAS', valor: r.total ?? '—', nota: 'pela régua do gestor, abaixo', tom: 'bom' })}
        ${num({ rotulo: 'Via AIC', valor: r.por_via ? r.por_via.AIC + r.por_via.Ambas : '—', nota: 'obra encerrada no AIC' })}
        ${num({ rotulo: 'Cancelada em operação · COI', valor: r.por_origem_cancelamento?.['COI confirmou'] ?? '—', nota: 'confirmação no texto do cancelamento' })}
        ${num({ rotulo: 'Cancelada em operação · sem reincidência', valor: r.por_origem_cancelamento?.['Sem reincidência'] ?? '—', nota: 'cancelada e nada reabriu no ativo' })}
        ${num({ rotulo: 'Candidatas bloqueadas', valor: r.bloqueadas_por_demanda_aberta ?? '—', nota: 'o ativo ainda tem demanda aberta', tom: 'atento' })}
      </div>
      <div class="nota calma" style="margin-bottom:24px">
        <strong>A régua das realizadas</strong>
        Realizada = obra encerrada no AIC (07/08/2026) OU cancelada em operação — que tem duas
        origens, ambas valendo por decisão do gestor (12/08): o COI confirmou no texto do
        cancelamento, ou a inferência de não-reincidência (cancelada e nada reabriu no ativo).
        Bloqueio por demanda aberta usa a lógica das cadeias: pendente de qualquer idade
        bloqueia; repassada consumida e rotina de bateria não bloqueiam. Conclusão física sem
        encerramento contábil não conta até o AIC registrar.
      </div>
      ${(r.lista || []).length ? `<section class="bloco"><h3>As realizadas</h3><div class="cartas">
        ${r.lista.map((x) => `<button class="carta" data-ativo="${esc(x.ativo)}">
          <div class="topo-carta"><span class="cod">${esc(x.ativo)}</span>
            <span class="selo c-baixa">Realizada</span>
            <span class="selo neutro">${esc(x.vias.join(' + '))}</span>
            ${x.origem_cancelamento ? `<span class="selo ${x.origem_cancelamento === 'COI confirmou' ? 'destaque' : 'neutro'}">${esc(x.origem_cancelamento)}</span>` : ''}</div>
          <div class="onde">${esc(x.localidade)} · ${esc(x.tipo)}</div>
          <p>${esc(x.evidencia)}</p></button>`).join('')}</div></section>` : ''}
      ${(r.fora_carteira_lista || []).length ? `<section class="bloco"><h3>Canceladas em operação fora da carteira</h3>
        <p style="margin:0 0 14px;color:var(--tinta-2);font-size:13.5px;font-style:italic">
          A varredura das 585 canceladas de todos os postos achou mais ${r.fora_carteira_lista.length}
          ativos cancelados em operação que nem estão na relação dos 129 — resolvidos antes de
          entrar na carteira.</p>
        <div class="cartas">${r.fora_carteira_lista.map((x) => `<div class="carta" style="cursor:default">
          <div class="topo-carta"><span class="cod">${esc(x.ativo)}</span>
            <span class="selo neutro">fora da carteira</span>
            ${x.confianca ? `<span class="selo ${x.confianca === 'Alta' ? 'destaque' : 'neutro'}">${esc(x.confianca)}</span>` : ''}</div>
          <p>${esc(x.evidencia)}</p>
          ${x.quem_confirmou ? `<div class="rodape"><span>confirmou: ${esc(x.quem_confirmou)}</span></div>` : ''}
        </div>`).join('')}</div></section>` : ''}
      ${(r.bloqueadas || []).length ? `<section class="bloco"><h3>Candidatas bloqueadas por demanda aberta</h3>
        <div class="cartas">${r.bloqueadas.map((x) => `<button class="carta" data-ativo="${esc(x.ativo)}">
          <div class="topo-carta"><span class="cod">${esc(x.ativo)}</span>
            <span class="selo c-alta">Bloqueada</span>
            <span class="selo neutro">${esc(x.vias.join(' + '))}</span></div>
          <div class="onde">${esc(x.localidade)}</div>
          <p>${x.pendencia ? esc(`Demanda aberta: ${x.pendencia.numero_ss || '—'} (${x.pendencia.equipe || '—'}), aberta em ${dataBr(x.pendencia.abertura)}`) : ''}</p>
        </button>`).join('')}</div></section>` : ''}
      <div class="numeros">
        ${num({ rotulo: 'Confirmadas no AIC', valor: c.confirmadas, nota: c.aic_disponivel ? 'obras encerradas no AIC' : 'extrato do AIC ainda não carregado', tom: c.confirmadas ? 'bom' : '' })}
        ${num({ rotulo: 'Com algum indício', valor: c.com_algum_indicio, nota: 'sinal de conclusão em ao menos uma fonte' })}
        ${num({ rotulo: 'Indício contestado', valor: c.contestadas, nota: 'algo no registro desmente', tom: 'critico' })}
        ${num({ rotulo: 'Sem indício', valor: c.sem_indicio, nota: 'nenhuma fonte sinaliza conclusão' })}
      </div>
      ${c.aic_disponivel ? `<div class="nota calma" style="margin-bottom:32px">
        <strong>A régua é o AIC</strong>
        Confirmado = obra do ativo encerrada no AIC (extrato de 07/08/2026). ${c.confirmadas}
        equipamentos passam nessa régua${m.missao?.aic129 ? `; outros
        ${m.missao.aic129.resumo.fisica_sem_encerramento ?? 0} têm conclusão física sem
        encerramento contábil, ${m.missao.aic129.resumo.obra_em_andamento ?? 0} têm obra em
        andamento e ${m.missao.aic129.resumo.sem_obra ?? 0} não têm obra vinculada` : ''}.
        O resto é indício, ordenado pela força abaixo.
      </div>` : `<div class="nota calma" style="margin-bottom:32px">
        <strong>Por que ainda não há número confirmado</strong>
        A regra é sua: só há certeza depois que a obra aparece no AIC como encerrada. O extrato do
        AIC ainda não entrou no repositório, então nenhum equipamento está contado como concluído.
      </div>`}
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

  if (id === 'classificacoes') {
    const minhas = Object.values(estado.classificacoes || {})
      .sort((a, b) => (a.localidade || '').localeCompare(b.localidade || ''));
    html = cabecaColecao('Minhas classificações',
      'O que você marcou à mão, direto na ficha do ativo. Fica guardado neste navegador — ' +
      'gere o arquivo, cole na conversa e eu transformo em decisão registrada no repositório.') +
      (minhas.length ? `<div class="numeros">
        ${num({ rotulo: 'Ativos classificados por você', valor: minhas.length })}
        ${num({ rotulo: 'Onde você discorda do painel', valor: minhas.filter((x) => x.situacao !== x.situacao_do_painel).length, tom: 'atento' })}
      </div>
      <div class="acoes-classif" style="margin-bottom:22px">
        <button class="pastilha" id="baixar-classif">Gerar o arquivo para me mandar</button>
        <button class="pastilha limpar" id="limpar-classif">Apagar tudo</button>
      </div>
      <div class="nota" id="aviso-classif" style="display:none;margin-bottom:10px"></div>
      <textarea id="json-classif" rows="10" style="display:none;width:100%"></textarea>
      <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th>O painel diz</th><th>Você diz</th><th>Por quê</th><th>Quando</th></tr></thead><tbody>
      ${minhas.map((x) => `<tr data-ativo="${esc(x.ativo)}">
        <td><b class="mono">${esc(x.ativo)}</b></td><td>${esc(x.localidade || '—')}</td>
        <td>${esc(x.situacao_do_painel || '—')}</td>
        <td><b>${esc(x.situacao)}</b></td><td>${esc(x.nota || '—')}</td>
        <td class="mono">${esc(x.data)}</td></tr>`).join('')}
      </tbody></table></div>`
      : `<div class="nota calma"><strong>Ainda vazio</strong>
        Abra a ficha de um ativo e vá até o bloco «Sua classificação», no fim da página.
        Marque a situação que você sabe que é a certa e escreva o porquê. Aqui vai aparecer a lista,
        com o botão para baixar o arquivo.</div>`);
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
        <div class="fichas" id="modo-mapa" style="margin-bottom:12px">
          <button class="pastilha" data-modo="criticidade">Ver por criticidade</button>
          <button class="pastilha" data-modo="tipo">Ver por tipo (RL × RT)</button>
          <button class="pastilha" data-modo="situacao">Ver por situação</button>
          <button class="pastilha" id="alternar-estradas">Estradas</button>
        </div>
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
    estado._mapaItens = comGeo;
    desenharMapa(comGeo);
    $$('#modo-mapa .pastilha[data-modo]').forEach((b) => {
      b.addEventListener('click', () => {
        estado.mapaModo = b.dataset.modo;
        desenharMapa(estado._mapaItens);
      });
    });
    $('#alternar-estradas').addEventListener('click', () => {
      estado.mapaEstradas = !estado.mapaEstradas;
      desenharMapa(estado._mapaItens);
    });
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

  if (id === 'consolidado') {
    const co = m.consolidado;
    if (!co) {
      html = cabecaColecao('Carteira consolidada', 'Ainda não processada.');
    } else {
      const TOM = {
        'Em operação': 'bom', 'Executado — falta ajuste ou comissionamento': 'bom', 'Em execução': '',
        'Pendente no COEP': 'critico', 'Pendente com outra equipe': 'atento',
        'Cancelada errada pelo DMSL': 'critico', 'Em análise': '', 'Sem ação do COEP': '',
        'Fora da análise': '',
      };
      const ORDEM = Object.keys(co.por_situacao).filter((s) => co.por_situacao[s]);
      const grupo = (s) => co.lista.filter((i) => i.situacao === s);

      html = cabecaColecao('Carteira consolidada',
        `As duas listas do posto fundidas numa só, sem repetir ativo: a foto de entrada de junho e o ` +
        `acompanhamento de hoje. São ${co.total} equipamentos, e a pergunta é uma só — em que ponto cada ` +
        `um está de fato.`) +
        `${(() => {
          const R = co.resposta;
          if (!R) return '';
          const falta = R.manutencionados.por_falta || {};
          const pl = R.aquisicao_x_plano || {};
          const compra = R.nao_manutencionados.por_espera['Compra do material (aquisição)'] || 0;
          const noPlano = pl.no_plano ?? 0;
          const depois = pl.ano_que_vem ?? Math.max(compra - noPlano, 0);
          const linha = (r, v, nota) => `<div class="item-linha"><span>${esc(r)}${nota ? `<i class="linha-nota">${esc(nota)}</i>` : ''}</span><b>${v}</b></div>`;
          return `<div class="numeros">
          ${num({ rotulo: 'Total da carteira', valor: co.total, nota: `${co.por_origem['Nas duas listas'] || 0} nas duas listas · ${co.por_origem['Só na lista de hoje'] || 0} novos · ${co.por_origem['Saiu da lista de hoje'] || 0} já saíram` })}
          ${num({ rotulo: 'Resolvidos', valor: R.resolvidos_total, nota: `${co.percentual_resolvido}% da carteira`, tom: 'bom' })}
          ${num({ rotulo: 'Aguardando a compra', valor: compra, nota: 'na fila do posto', tom: 'critico' })}
        </div>

        <section class="bloco"><h3>Como os resolvidos se dividem</h3>
        <p class="destaque-texto">Saíram do problema. ${R.manutencionados.total} com intervenção física,
        ${R.por_cancelamento ? R.por_cancelamento.total : 0} por cancelamento.</p>
        <div class="itens">
          ${linha('Em operação, nada falta', falta['Nada — em operação'] || 0, 'serviço fechado')}
          ${linha('Canceladas', R.por_cancelamento ? R.por_cancelamento.total : 0, 'não precisaram de substituição')}
          ${linha('Ajuste da Proteção', falta['Ajuste da Proteção'] || 0, 'trocado, falta o ajuste')}
          ${linha('Comissionamento', falta['Comissionamento do DMSL'] || 0, 'trocado, falta comissionar')}
          ${falta['Baixa da SS no sistema'] ? linha('Baixa da SS', falta['Baixa da SS no sistema'], 'trocado, falta só encerrar') : ''}
        </div></section>
`; })()}

        ${m.visao_dcmd ? (() => {
          const vd = m.visao_dcmd;
          const rs2 = (v) => `R$ ${moedaBR(v)}`;
          const saldo = vd.orcamento_previsto - vd.ja_consumido.total;
          const crits = ['Muito Alta', 'Alta', 'Média', 'Baixa', 'Sem classificação'];
          const stats = [...new Set(vd.matriz.map((x) => x.status))];
          return `<section class="bloco"><h3>${esc(vd.titulo)}</h3>
        <p class="destaque-texto">${esc(vd.fonte)}. São ${vd.ativos} ativos —
        ${vd.por_tipo.map((t) => `${t.qtd} ${t.tipo}`).join(' e ')} — com valor previsto ativo a ativo.</p>
        <div class="numeros">
          ${num({ rotulo: 'Orçamento previsto', valor: rs2(vd.orcamento_previsto), nota: `${vd.ativos} ativos` })}
          ${num({ rotulo: 'Já consumido', valor: rs2(vd.ja_consumido.total), nota: `RL ${rs2(vd.ja_consumido.rl)} · RT ${rs2(vd.ja_consumido.rt)}`, tom: 'bom' })}
          ${num({ rotulo: 'Ainda por consumir', valor: rs2(saldo), nota: `${Math.round(100 * saldo / vd.orcamento_previsto)}% do previsto`, tom: 'atento' })}
        </div>

        <p class="destaque-texto">Onde cada um está <b>hoje</b>, pelo parecer COEP mais recente:</p>
        <div class="itens">${(vd.por_etapa_hoje || []).map((s) => `<div class="item-linha">
          <span>${esc(s.etapa)}<i class="linha-nota">${esc(s.ativos.slice(0, 10).join(' · '))}${s.ativos.length > 10 ? ' …' : ''}</i></span>
          <b>${s.qtd} · ${rs2(s.valor)}</b></div>`).join('')}</div>
        ${vd.servico_feito ? `<div class="nota calma" style="margin-top:12px"><strong>Serviço já feito</strong>
        ${vd.servico_feito.ativos} ativos somando ${rs2(vd.servico_feito.valor)}. ${esc(vd.servico_feito.nota)}</div>` : ''}
        ${vd.variantes ? `<div class="nota branda" style="margin-top:10px"><strong>Grafia do parecer</strong>${esc(vd.variantes)}</div>` : ''}

        <p class="destaque-texto" style="margin-top:20px">A foto que está na planilha do Allan, para comparar —
        ${vd.mudaram_de_etapa} dos ${vd.ativos} mudaram de etapa desde então:</p>
        <div class="itens">${vd.por_status.map((s) => `<div class="item-linha">
          <span>${esc(s.status)}</span><b>${s.qtd} · ${rs2(s.valor)}</b></div>`).join('')}</div>

        <p class="destaque-texto" style="margin-top:20px">Por tipo e criticidade:</p>
        <div class="tabela-rol"><table class="matriz"><thead><tr><th>Tipo</th><th>Criticidade</th>
        ${stats.map((s) => `<th class="num">${esc(s)}</th>`).join('')}
        <th class="num">Total</th></tr></thead><tbody>
        ${['RL', 'RT'].flatMap((t) => crits.map((c) => {
          const linhas = vd.matriz.filter((x) => x.tipo === t && x.criticidade === c);
          if (!linhas.length) return '';
          const tot = linhas.reduce((a, x) => a + x.valor, 0);
          const totq = linhas.reduce((a, x) => a + x.qtd, 0);
          return `<tr><td><b>${t}</b></td><td>${esc(c)}</td>
            ${stats.map((s) => { const x = linhas.find((y) => y.status === s);
              return `<td class="num">${x ? `${x.qtd}<br><span style="font-size:11px">${rs2(x.valor)}</span>` : '—'}</td>`; }).join('')}
            <td class="num"><b>${totq}</b><br><span style="font-size:11px">${rs2(tot)}</span></td></tr>`;
        })).join('')}
        </tbody></table></div>
        <div class="nota branda" style="margin-top:12px"><strong>Anotação à mão na planilha</strong>${esc(vd.anotacao_gerar_5)}</div>

        <div class="confronto-duplo" style="margin-top:18px">
          <div><h4 class="rotulo-coluna">Em execução</h4>
          <p class="destaque-texto">${vd.em_execucao.ativos} ativos · <b>${rs2(vd.em_execucao.valor)}</b>
          <i class="linha-nota">${esc(vd.em_execucao.fonte)}</i></p></div>
          <div><h4 class="rotulo-coluna">Em análise de compra</h4>
          <p class="destaque-texto">${vd.em_analise_compra.ativos} ativos · <b>${rs2(vd.em_analise_compra.valor)}</b>
          <i class="linha-nota">${esc(vd.em_analise_compra.fonte)}</i></p></div>
        </div>

        <div class="tabela-rol" style="margin-top:18px"><table class="matriz rol-entrada"><thead><tr>
        <th>Ativo</th><th>Regional</th><th>Modelo</th><th>Criticidade</th><th>Etapa hoje</th>
        <th>O que comprar</th><th class="num">Valor previsto</th></tr></thead><tbody>
        ${vd.lista.map((x) => `<tr data-ativo="${esc(x.ativo)}">
          <td><b class="mono">${esc(x.ativo)}</b></td><td>${esc(x.regional || '—')}</td>
          <td>${esc(x.modelo || '—')}</td><td>${esc(x.criticidade)}</td>
          <td>${esc(x.etapa_hoje || x.status)}
          ${x.status_allan && x.status_allan !== x.etapa_hoje ? `<i class="linha-nota">na planilha do Allan: ${esc(x.status_allan)}</i>` : ''}</td>
          <td>${esc(x.compra && x.compra !== '#N/A' ? x.compra : '—')}
          ${x.check ? `<i class="linha-nota">check: ${esc(x.check)}</i>` : ''}</td>
          <td class="num">${rs2(x.valor)}</td></tr>`).join('')}
        </tbody><tfoot><tr><td colspan="6">Total</td>
        <td class="num"><b>${rs2(vd.orcamento_previsto)}</b></td></tr></tfoot></table></div>
        </section>`; })() : ''}

        ${m.leitura_canceladas ? (() => {
          const lc = m.leitura_canceladas;
          const rec = new Set(lc.reclassificar || []);
          const perg = new Set(lc.perguntar_ao_gestor || []);
          return `<section class="bloco"><h3>As canceladas da ETO-COEP, lidas fio a fio</h3>
        <p class="destaque-texto">${esc(lc.criterio)}</p>
        <div class="itens">
          <div class="item-linha"><span>SS canceladas a partir de 01/05/2026<i class="linha-nota">em ${lc.universo.ativos} ativos</i></span><b>${lc.universo.ss_canceladas}</b></div>
          <div class="item-linha"><span>Sem nenhuma SS nova depois<i class="linha-nota">a condição (a) passa</i></span><b>${lc.universo.sem_ss_nova}</b></div>
          <div class="item-linha"><span>Resolvidos de verdade<i class="linha-nota">passam nas duas condições</i></span><b>${(lc.resolvidos || []).length}</b></div>
          <div class="item-linha"><span>Pendência que o cancelamento escondia<i class="linha-nota">o texto pede peça, laudo ou reabertura</i></span><b>${(lc.pendencias || []).length}</b></div>
          <div class="item-linha"><span>Sem evidência para os dois lados<i class="linha-nota">o texto não decide</i></span><b>${(lc.indefinidos || []).length}</b></div>
        </div>
        <p class="destaque-texto" style="margin-top:16px"><b>${rec.size} já foram reclassificados</b> no painel:
        eram contados como resolvidos por cancelamento e voltaram para pendentes.
        <b>${perg.size} dependem da sua palavra</b> — neles o painel não resolve pelo cancelamento, e sim
        pela sua régua de «aguardando comissionamento já foi manutencionado», que a leitura contesta.</p>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>Veredito</th><th>Por quê</th></tr></thead><tbody>
        ${(lc.pendencias || []).map((p) => `<tr data-ativo="${esc(p.ativo)}">
          <td><b class="mono">${esc(p.ativo)}</b></td><td>${esc(p.localidade || '—')}</td>
          <td>${rec.has(p.ativo) ? '<span class="selo c-alta">reclassificado</span>'
            : perg.has(p.ativo) ? '<span class="selo neutro">aguarda você</span>'
            : '<span class="selo neutro">já era pendente</span>'}</td>
          <td>${esc((p.porque || '').slice(0, 240))}</td></tr>`).join('')}
        </tbody></table></div>
        ${lc.caso_5852775092 ? `<div class="nota" style="margin-top:14px">
          <strong>O caso que você citou — 5852775092</strong>${esc(lc.caso_5852775092.slice(0, 1200))}</div>` : ''}
        </section>`; })() : ''}

        ${co.resposta ? `<section class="bloco"><h3>A pergunta em duas colunas</h3>
        <p class="destaque-texto">${co.resposta.manutencionados.total} manutencionados +
        ${co.resposta.por_cancelamento ? co.resposta.por_cancelamento.total : 0} resolvidos por cancelamento +
        ${co.resposta.nao_manutencionados.total} ainda no fluxo = ${co.total} ativos. Os cancelados saíram da
        carteira sem intervenção física — ficam no detalhamento logo abaixo.</p>
        <div class="confronto-duplo">
          <div>
            <h4 class="rotulo-coluna">Já manutencionados — ${co.resposta.manutencionados.total}</h4>
            <p class="destaque-texto">Alguém foi ao ativo e fez o serviço: o equipamento está no poste. Falta, no máximo, fechar o processo — o ajuste da Proteção, o comissionamento do DMSL ou a baixa da SS.</p>
            <div class="itens">${Object.entries(co.resposta.manutencionados.por_falta)
              .sort((a, b) => b[1] - a[1])
              .map(([k, v]) => `<div class="item-linha"><span>${esc(k)}</span><b>${v}</b></div>`).join('')}</div>
            ${co.resposta.manutencionados.por_como_resolveu ? `
            <p class="destaque-texto" style="margin-top:16px">Como cada um saiu:</p>
            <div class="itens">${Object.entries(co.resposta.manutencionados.por_como_resolveu)
              .map(([k, v]) => `<div class="item-linha"><span>${esc(k)}</span><b>${v}</b></div>`).join('')}</div>` : ''}
          </div>
          <div>
            <h4 class="rotulo-coluna">Ainda não manutencionados — ${co.resposta.nao_manutencionados.total}</h4>
            <p class="destaque-texto">Ninguém mexeu no equipamento ainda. O que cada um está esperando:</p>
            <div class="itens">${Object.entries(co.resposta.nao_manutencionados.por_espera)
              .map(([k, v]) => `<div class="item-linha"><span>${esc(k)}</span><b>${v}</b></div>`).join('')}</div>
          </div>
        </div></section>

        ${co.resposta.por_cancelamento ? `<section class="bloco"><h3>Detalhamento dos resolvidos — como cada um saiu da carteira</h3>
        <p class="destaque-texto">Resolvido não é sinônimo de manutencionado. Destes ${co.resposta.resolvidos_total}
        que saíram do problema, ${co.resposta.manutencionados.total} tiveram alguém subindo no poste e
        ${co.resposta.por_cancelamento.total} se resolveram por cancelamento — não precisaram de substituição
        nem de SS nova.</p>
        <div class="itens">
          <div class="item-linha"><span>Cancelados — não precisaram de substituição</span><b>${co.resposta.por_cancelamento.total}</b></div>
          <div class="item-linha"><span>Trocados e em operação, nada falta</span><b>${co.resposta.manutencionados.por_falta['Nada — em operação'] || 0}</b></div>
          <div class="item-linha"><span>Trocados — falta o ajuste da Proteção</span><b>${co.resposta.manutencionados.por_falta['Ajuste da Proteção'] || 0}</b></div>
          <div class="item-linha"><span>Trocados — falta o comissionamento do DMSL</span><b>${co.resposta.manutencionados.por_falta['Comissionamento do DMSL'] || 0}</b></div>
          <div class="item-linha"><span>Trocados — falta só baixar a SS</span><b>${co.resposta.manutencionados.por_falta['Baixa da SS no sistema'] || 0}</b></div>
          <div class="item-linha"><span>Em processo de logística — material comprado, a caminho</span><b>${co.resposta.nao_manutencionados.por_espera['Logística — material comprado, a caminho'] || 0}</b></div>
        </div></section>

        <section class="bloco"><h3>Cancelados sem precisar de substituição (${co.resposta.por_cancelamento.total})</h3>
        <p class="destaque-texto">A demanda foi cancelada e nenhuma SS de indisponibilidade voltou no mesmo ativo.
        O equipamento está operando — só não houve intervenção física.</p>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>Tipo</th><th>Criticidade</th><th>Parecer COEP</th><th>Como saiu</th></tr></thead><tbody>
        ${co.resposta.por_cancelamento.lista.map((i) => `<tr data-ativo="${esc(i.ativo)}"><td><b class="mono">${esc(i.ativo)}</b></td>
          <td>${esc(i.localidade || '—')}</td><td>${esc(i.tipo === 'Religador' ? 'RL' : 'RT')}</td>
          <td>${esc(i.criticidade || '—')}</td><td>${esc(i.parecer_coep || '—')}</td>
          <td>${esc(i.entrada_motivo || 'cancelada sem reincidência')}</td></tr>`).join('')}
        </tbody></table></div></section>` : ''}

        ${Object.entries(co.resposta.manutencionados.listas).filter(([k]) => k !== 'Nada — em operação').map(([k, lista]) => `
        <section class="bloco"><h3>Manutencionados — falta ${esc(k.toLowerCase())} (${lista.length})</h3>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>Tipo</th><th>Criticidade</th><th>Parecer COEP</th><th>Onde está a SS</th></tr></thead><tbody>
        ${lista.map((i) => `<tr data-ativo="${esc(i.ativo)}"><td><b class="mono">${esc(i.ativo)}</b></td>
          <td>${esc(i.localidade || '—')}</td><td>${esc(i.tipo === 'Religador' ? 'RL' : 'RT')}</td>
          <td>${esc(i.criticidade || '—')}</td><td>${esc(i.parecer_coep || '—')}</td>
          <td>${esc(i.posto_atual || '—')}</td></tr>`).join('')}
        </tbody></table></div></section>`).join('')}

        ${['Compra do material (aquisição)', 'Logística — material comprado, a caminho', 'Execução pelo COCM/DCMD — material já entregue', 'Reabrir a SS que foi cancelada errada']
          .filter((k) => co.resposta.nao_manutencionados.listas[k])
          .map((k) => { const lista = co.resposta.nao_manutencionados.listas[k]; return `
        <section class="bloco"><h3>Não manutencionados — ${esc(k)} (${lista.length})</h3>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>Tipo</th><th>Criticidade</th><th>Parecer COEP</th><th>Onde está a SS</th></tr></thead><tbody>
        ${lista.map((i) => `<tr data-ativo="${esc(i.ativo)}"><td><b class="mono">${esc(i.ativo)}</b></td>
          <td>${esc(i.localidade || '—')}</td><td>${esc(i.tipo === 'Religador' ? 'RL' : 'RT')}</td>
          <td>${esc(i.criticidade || '—')}</td><td>${esc(i.parecer_coep || '—')}</td>
          <td>${esc(i.posto_atual || '—')}</td></tr>`).join('')}
        </tbody></table></div></section>`; }).join('')}` : ''}

        <div class="nota calma" style="margin:-6px 0 26px"><strong>Como ler a escada</strong>
        Cada equipamento aparece uma vez só, na etapa mais avançada em que ele está.
        <b>Resolvido</b> = em operação + executado esperando ajuste/comissionamento + sem ação do COEP —
        porque, na sua régua, equipamento em ajuste ou comissionamento já foi manutencionado.
        <b>Pendente</b> = no COEP + com outra equipe + cancelada errada pelo DMSL.
        Em execução e em análise ficam à parte: não são nem uma coisa nem outra.</div>

        <section class="bloco"><h3>A escada, degrau por degrau</h3>
        <div class="itens">${ORDEM.map((s) => `<div class="item-linha">
          <span>${esc(s)}</span><b>${co.por_situacao[s]}</b></div>`).join('')}</div>
        <div class="grade" style="margin-top:18px">
          <div class="quadro"><header><h3>De onde vem cada um</h3><p>as duas fotos do posto</p></header>
          ${barras(Object.entries(co.por_origem).map(([k, v]) => ({ rotulo: k, total: v })))}</div>
        </div></section>

        ${ORDEM.map((s) => `<section class="bloco"><h3>${esc(s)} — ${co.por_situacao[s]}</h3>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr>
          <th>Ativo</th><th>Localidade</th><th>Tipo</th><th>Criticidade</th><th>Por quê</th>
          <th>Parecer COEP</th><th>De onde vem</th></tr></thead><tbody>
        ${grupo(s).map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td><b class="mono">${esc(i.ativo)}</b></td><td>${esc(i.localidade || '—')}</td>
          <td>${esc(i.tipo === 'Religador' ? 'RL' : i.tipo === 'Regulador de Tensão' ? 'RT' : '—')}</td>
          <td>${esc(i.criticidade || '—')}</td>
          <td>${esc(i.porque)}${i.decisao_gestor ? ' <b>(decisão sua)</b>' : ''}</td>
          <td>${esc(i.parecer_coep || '—')}</td>
          <td>${esc(i.origem)}</td></tr>`).join('')}
        </tbody></table></div></section>`).join('')}

        ${co.recorte_dcmd ? `<section class="bloco"><h3>Recorte do DCMD — tirando o primeiro ataque</h3>
        <p class="destaque-texto">Equipamento parado no DMSL que nunca passou pelo COEP, ou marcado «Novo»,
        está em primeiro ataque: é diagnóstico de campo, ainda não é demanda do posto. Fora esses
        ${co.recorte_dcmd.primeiro_ataque.total} (${co.recorte_dcmd.primeiro_ataque.novos} deles «Novo»),
        a carteira do DCMD é esta:</p>
        <div class="numeros">
          ${num({ rotulo: 'Carteira do DCMD', valor: co.recorte_dcmd.total, nota: 'sem o primeiro ataque' })}
          ${num({ rotulo: 'Já manutencionados', valor: co.recorte_dcmd.manutencionados, nota: `${co.recorte_dcmd.percentual_manutencionado}% do recorte`, tom: 'bom' })}
          ${num({ rotulo: 'Resolvidos no total', valor: co.recorte_dcmd.resolvidos ?? co.recorte_dcmd.manutencionados, nota: `${co.recorte_dcmd.percentual_resolvido ?? co.recorte_dcmd.percentual_manutencionado}% — inclui ${co.recorte_dcmd.por_cancelamento ?? 0} por cancelamento`, tom: 'bom' })}
          ${num({ rotulo: 'No posto do COEP', valor: co.recorte_dcmd.no_coep, nota: 'compra, logística ou reabertura', tom: 'critico' })}
          ${num({ rotulo: 'Com o DCMD / COCM', valor: co.recorte_dcmd.nos_cocm, nota: 'material entregue, falta executar', tom: 'atento' })}
        </div></section>` : ''}

        ${co.resposta?.aquisicao_x_plano ? `<section class="bloco"><h3>Os ${co.resposta.aquisicao_x_plano.em_aquisicao} em aquisição × o plano de compras</h3>
        <div class="numeros">
          ${num({ rotulo: 'Pedidos em 17/07', valor: co.resposta.aquisicao_x_plano.no_plano, nota: moeda(co.resposta.aquisicao_x_plano.valor_no_plano), tom: 'bom' })}
          ${num({ rotulo: 'Sem pedido no plano', valor: co.resposta.aquisicao_x_plano.fora_do_plano, nota: 'em aquisição, mas fora do pedido', tom: 'critico' })}
        </div>
        <div class="nota" style="margin:14px 0"><strong>O plano é só material</strong>
        Os 40 itens do pedido de 17/07 são tanque/parte ativa, controle, célula, chave faca e bateria+rádio.
        Não há nenhuma linha de mão de obra ou serviço — a execução corre por conta dos COCMs, fora deste valor.</div>
        <h3 style="margin-top:20px;border:0;padding:0;font-size:12px">No plano</h3>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>Criticidade</th><th>Itens</th><th>Valor</th><th>Material</th></tr></thead><tbody>
        ${co.resposta.aquisicao_x_plano.lista_no_plano.map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td><b class="mono">${esc(i.ativo)}</b></td><td>${esc(i.localidade || '—')}</td>
          <td>${esc(i.criticidade || '—')}</td><td>${i.itens}</td><td>${moeda(i.valor)}</td>
          <td>${esc(i.materiais.join(' · '))}</td></tr>`).join('')}
        </tbody></table></div>
        <h3 style="margin-top:22px;border:0;padding:0;font-size:12px">Em aquisição, mas sem pedido no plano</h3>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>Tipo</th><th>Criticidade</th><th>Parecer COEP</th></tr></thead><tbody>
        ${co.resposta.aquisicao_x_plano.lista_fora.map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td><b class="mono">${esc(i.ativo)}</b></td><td>${esc(i.localidade || '—')}</td>
          <td>${esc(i.tipo === 'Religador' ? 'RL' : 'RT')}</td><td>${esc(i.criticidade || '—')}</td>
          <td>${esc(i.parecer_coep || '—')}</td></tr>`).join('')}
        </tbody></table></div></section>` : ''}

        ${co.auditoria ? `<section class="bloco"><h3>De onde vêm os ${co.auditoria.uniao} — e por que não há repetido</h3>
        <div class="itens">
          <div class="item-linha"><span>Foto de entrada (as duas abas), ativos distintos</span><b>${co.auditoria.entrada_distintos}</b></div>
          <div class="item-linha"><span>Lista de hoje (ATUALIZADA6), ativos distintos</span><b>${co.auditoria.hoje_distintos}</b></div>
          <div class="item-linha"><span>Estão nas duas listas (contados uma vez só)</span><b>− ${co.auditoria.em_comum}</b></div>
          <div class="item-linha"><span><b>União</b></span><b>${co.auditoria.uniao}</b></div>
          <div class="item-linha"><span>Excluídos da análise por decisão sua</span><b>− ${co.auditoria.excluidos ?? 0}</b></div>
          <div class="item-linha"><span><b>Na análise</b></span><b>${co.auditoria.na_analise ?? co.auditoria.uniao}</b></div>
          <div class="item-linha"><span>Linhas na tabela × ativos distintos</span><b>${co.auditoria.linhas} × ${co.auditoria.distintos}</b></div>
          <div class="item-linha"><span>Códigos no padrão 79/58 + 8 dígitos</span><b>${co.auditoria.codigos_validos}</b></div>
          <div class="item-linha"><span>Ativos repetidos</span><b>${Object.keys(co.auditoria.repetidos).length ? Object.keys(co.auditoria.repetidos).join(', ') : 'nenhum'}</b></div>
        </div>
        ${co.auditoria.quase_iguais.length ? `<div class="nota" style="margin-top:12px">
          <strong>Pares que diferem em um dígito só — conferidos</strong>
          ${co.auditoria.quase_iguais.map((p2) => esc(p2.join(' e '))).join('<br>')}<br>
          Não são digitação errada: cada um tem SS, histórico e situação próprios na base.</div>` : ''}
        <div class="nota calma" style="margin-top:12px"><strong>O que os 160 não são</strong>
        Na base de SS/OS, ${co.auditoria.universo_2026} religadores e reguladores tiveram alguma SS em 2026 —
        e só ${co.auditoria.universo_2026_na_carteira} deles estão nesta carteira. Os outros correram por
        outras equipes sem passar pelo posto (troca de bateria, cadastro, comunicação). Esta base é o que
        passou pelo COEP, não tudo que aconteceu com equipamento especial no ano.</div></section>` : ''}

        ${(co.premissas || []).length ? `<div class="nota calma" style="margin-top:18px"><strong>Premissas desta consolidação</strong>${co.premissas.map(esc).join('<br>')}</div>` : ''}`;
    }
  }

  if (id === 'acompanhamento') {
    const ac = m.acompanhamento;
    if (!ac) {
      html = cabecaColecao('Acompanhamento atual', 'A planilha atualizada ainda não foi carregada.');
    } else {
      const TOM = {
        'Em operação': 'bom', 'Cancelada errada pelo DMSL': 'critico',
        'Pendente no fluxo': 'atento', 'Em andamento': '', 'Em análise': '',
      };
      const NOTA = {
        'Em operação': 'check Ok, Em operação ou Desmobilizado',
        'Cancelada errada pelo DMSL': 'SS dada como concluída, check pendente',
        'Pendente no fluxo': 'check pendente, SS ainda aberta',
        'Em andamento': 'execução em curso',
        'Em análise': 'check em branco — inclui os «Novo»',
      };
      const tabela = (lista) => `<div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr>
        <th>Ativo</th><th>Localidade</th><th>Tipo</th><th>Criticidade</th><th>SS na planilha</th>
        <th>Parecer COEP</th><th>Observação</th><th>Na base de SS/OS</th></tr></thead><tbody>
        ${lista.map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td><b class="mono">${esc(i.ativo)}</b></td><td>${esc(i.localidade || '—')}</td>
          <td>${esc(i.tipo === 'Religador' ? 'RL' : 'RT')}</td><td>${esc(i.criticidade || '—')}</td>
          <td>${esc(i.ss_planilha || '—')}</td><td>${esc(i.parecer_coep || '—')}</td>
          <td>${esc(i.observacao || '—')}${i.sem_acao_coep ? '<br><b>sem ação do COEP</b>' : ''}</td>
          <td>${i.na_base.demanda_aberta ? `aberta no ${esc(i.na_base.posto_atual || '—')}` : 'sem demanda aberta'}
            ${i.na_base.ss_mais_recente ? `<br><span class="mono">${esc(i.na_base.ss_mais_recente)} · ${esc((i.na_base.situacao || '').replace('SS ', ''))}</span>` : ''}</td>
        </tr>`).join('')}</tbody></table></div>`;

      html = cabecaColecao('Acompanhamento atual',
        'A situação de cada um dos ' + ac.total + ' equipamentos hoje, lida do parecer COEP mais recente ' +
        '(planilha ATUALIZADA6) e conferida contra a base de SS/OS pelo código operativo do ativo.') +
        `<div class="numeros">
          ${Object.entries(ac.por_situacao).map(([s, n]) => num({
            rotulo: s, valor: n, nota: NOTA[s], tom: TOM[s] })).join('')}
        </div>

        <div class="nota calma" style="margin:-6px 0 26px"><strong>Como cada um foi classificado</strong>
        A coluna «Check de concluídas» manda: <b>Ok</b>, <b>Em operação</b> ou <b>Desmobilizado</b> → em operação
        (${ac.sem_acao_coep} desmobilizado, caso em que não deveria ter havido ação do COEP);
        <b>Pendente</b> com a SS dada como CONCLUÍDA → cancelada errada pelo DMSL;
        <b>Pendente</b> com a SS aberta → pendência seguindo no fluxo; <b>Em andamento</b> → execução em curso;
        <b>em branco</b> → em análise. Soma: ${Object.values(ac.por_situacao).reduce((s, n) => s + n, 0)} = ${ac.total} ativos,
        sem repetição (${Object.keys(ac.ativos_repetidos || {}).length ? 'ATENÇÃO: ' + Object.keys(ac.ativos_repetidos).join(', ') : 'conferido: nenhum ativo duplicado'}).</div>

        ${ac.listas['Cancelada errada pelo DMSL'].length ? `<section class="bloco"><h3>Canceladas erradas pelo DMSL — ${ac.listas['Cancelada errada pelo DMSL'].length}</h3>
        <p class="destaque-texto">A SS foi dada como concluída no sistema, mas o check diz que a pendência continua.
        São as que precisam voltar a existir no SGM.</p>${tabela(ac.listas['Cancelada errada pelo DMSL'])}</section>` : ''}

        <section class="bloco"><h3>Em operação — ${ac.listas['Em operação'].length}</h3>
        ${tabela(ac.listas['Em operação'])}</section>

        <section class="bloco"><h3>Pendente no fluxo — ${ac.listas['Pendente no fluxo'].length}</h3>
        ${tabela(ac.listas['Pendente no fluxo'])}</section>

        <section class="bloco"><h3>Em andamento — ${ac.listas['Em andamento'].length}</h3>
        ${tabela(ac.listas['Em andamento'])}</section>

        <section class="bloco"><h3>Em análise — ${ac.listas['Em análise'].length}</h3>
        <p class="destaque-texto">Check em branco. Inclui os marcados «Novo» — SS de primeiro ataque abertas
        pela TELE que ainda não passaram pelo COEP, por isso sem parecer e sem criticidade calculada.</p>
        ${tabela(ac.listas['Em análise'])}</section>

        ${ac.divergencias.length ? `<section class="bloco"><h3>Planilha × base de SS/OS — ${ac.divergencias.length} divergências</h3>
        <p class="destaque-texto">O que a planilha diz e o que o SGM mostra não batem nestes ativos. São indícios
        para conferência, não conclusões.</p>
        <div class="itens">${ac.divergencias.map((d) => `<div class="item-linha" data-ativo="${esc(d.ativo)}" style="cursor:pointer">
          <span><b class="mono">${esc(d.ativo)}</b> · ${esc(d.localidade || '')} — ${esc(d.alertas[0])}</span>
          <b>${esc(d.situacao)}</b></div>`).join('')}</div></section>` : ''}

        ${ac.reconciliacao ? `<section class="bloco"><h3>Da foto de entrada até hoje</h3>
        <p class="destaque-texto">Duas listas diferentes, do mesmo posto, em momentos diferentes: a foto de
        entrada (junho) e o acompanhamento de hoje. Quem foi resolvido saiu da lista — por isso o número de
        «em operação» de hoje não é a conta do que você concluiu.</p>
        <div class="numeros">
          ${num({ rotulo: 'Vieram da foto de entrada', valor: ac.reconciliacao.continuam, nota: `de ${ac.reconciliacao.entrada_total} que estavam lá` })}
          ${num({ rotulo: 'Saíram da lista', valor: ac.reconciliacao.sairam, nota: `${ac.reconciliacao.sairam_resolvidos} deles eu já dava por resolvidos`, tom: 'bom' })}
          ${num({ rotulo: 'Entrantes novos', valor: ac.reconciliacao.novos, nota: 'não estavam na foto de entrada', tom: 'atento' })}
          ${num({ rotulo: 'Pendência total hoje', valor: ac.pendencia_total, nota: 'no fluxo + canceladas erradas pelo DMSL', tom: 'critico' })}
        </div>
        <div class="grade" style="margin:18px 0">
          <div class="quadro"><header><h3>Como estão os entrantes novos</h3></header>
          ${barras(Object.entries(ac.reconciliacao.novos_por_situacao).map(([k, v]) => ({ rotulo: k, total: v })))}</div>
        </div>
        <h3 style="margin-top:24px;border:0;padding:0;font-size:12px">Os ${ac.reconciliacao.sairam} que saíram da lista</h3>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>Como eu classifiquei na entrada</th></tr></thead><tbody>
        ${ac.reconciliacao.lista_sairam.map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td><b class="mono">${esc(i.ativo)}</b></td><td>${esc(i.localidade || '—')}</td>
          <td>${esc(i.motivo || (i.balde === 'em_andamento' ? 'ainda no fluxo' : i.balde))}</td></tr>`).join('')}
        </tbody></table></div></section>` : ''}

        ${(ac.confronto_entrada || []).length ? `<section class="bloco"><h3>Confronto com a carteira de entrada</h3>
        <p class="destaque-texto">Como os ativos que vieram da foto de entrada estão hoje. ${ac.fora_da_entrada}
        dos ${ac.total} não estavam na foto — entraram depois.</p>
        <div class="itens">${ac.confronto_entrada.map((c) => `<div class="item-linha">
          <span>Entrada: <b>${esc(c.entrada === 'em_andamento' ? 'ainda no fluxo' : c.entrada)}</b> → hoje: ${esc(c.acompanhamento)}</span>
          <b>${c.total}</b></div>`).join('')}</div></section>` : ''}

        ${(ac.premissas || []).length ? `<div class="nota calma" style="margin-top:18px"><strong>Premissas desta leitura</strong>${ac.premissas.map(esc).join('<br>')}</div>` : ''}`;
    }
  }

  if (id === 'reportes') {
    const rc = m.reportes_campo;
    if (!rc || !rc.lista?.length) {
      html = cabecaColecao('Reportes de campo', 'Nenhum reporte carregado ainda.');
    } else {
      // Quem tem foto embutida vem primeiro; quem só anunciou o anexo vem depois.
      const comFoto = rc.lista.filter((r) => r.imagem && estado.imagens?.[r.imagem]);
      const anunciados = rc.lista.filter((r) => !(r.imagem && estado.imagens?.[r.imagem]) && r.anexo);
      const semAnexo = rc.lista.filter((r) => !(r.imagem && estado.imagens?.[r.imagem]) && !r.anexo);
      const ficha = (a) => estado.equipamentos.find((x) => x.ativo === a);

      const cartao = (r) => {
        const e = ficha(r.ativo);
        const foto = r.imagem && estado.imagens?.[r.imagem];
        return `<figure class="reporte-galeria">
          ${foto ? `<a href="${estado.imagens[r.imagem]}" target="_blank" rel="noopener">
            <img src="${estado.imagens[r.imagem]}" loading="lazy"
              alt="Reporte de campo do ativo ${esc(r.ativo)} em ${dataBr(r.data)}"></a>`
            : r.anexo
              ? `<div class="sem-foto"><b>${r.anexo.fotos} foto${r.anexo.fotos > 1 ? 's' : ''}</b>
                <span>${esc(r.anexo.estado)}</span></div>`
              : `<div class="sem-foto"><b>Sem foto</b><span>reporte só em texto</span></div>`}
          <figcaption>
            <div class="topo-galeria">
              ${e ? `<button class="cod abre-ficha" data-ativo="${esc(r.ativo)}">${esc(r.ativo)}</button>`
                  : `<span class="cod">${esc(r.ativo)}</span>`}
              <span class="reporte-data">${dataBr(r.data)}</span>
            </div>
            <b>${esc(r.titulo)}</b>
            <span class="onde">${esc(r.local || r.subtitulo || '')}${r.equipe ? ` · ${esc(r.equipe)}` : ''}</span>
            ${r.servico_executado ? `<span class="feito">${esc(r.servico_executado)}</span>` : ''}
            ${r.equipamento_instalado ? `<span class="feito mono">${esc(r.equipamento_instalado)}</span>` : ''}
            ${!foto && r.anexo?.descricao ? `<span class="feito">${esc(r.anexo.descricao)}</span>` : ''}
          </figcaption>
        </figure>`;
      };

      html = cabecaColecao('Reportes de campo',
        `Todas as fotos que a equipe mandou, num lugar só. ${rc.fotos} foto${rc.fotos > 1 ? 's' : ''} em
         ${rc.total} reporte${rc.total > 1 ? 's' : ''}, cobrindo ${rc.ativos.length} equipamentos.
         Clique na foto para abrir em tamanho cheio, ou no código do ativo para ir à ficha.`) +
        `<div class="numeros">
          ${num({ rotulo: 'Reportes recebidos', valor: rc.total, nota: `${rc.ativos.length} equipamentos` })}
          ${num({ rotulo: 'Fotos', valor: rc.fotos, nota: `${comFoto.length} já embutidas na página`, tom: 'bom' })}
          ${anunciados.length ? num({ rotulo: 'Anexo anunciado', valor: anunciados.length, nota: 'esperando o arquivo da foto', tom: 'atento' }) : ''}
          ${semAnexo.length ? num({ rotulo: 'Sem foto', valor: semAnexo.length, nota: 'reporte só em texto' }) : ''}
        </div>

        <div class="nota calma" style="margin:-6px 0 26px"><strong>Por que isso é a prova mais forte</strong>
        O reporte é a equipe assinando que subiu no poste e trocou. Nenhuma inferência sobre o texto
        da SS ganha disso — por isso o reporte de campo entra como via de resolução na carteira, mesmo
        quando o SGM ainda não registrou nada.</div>

        <section class="bloco"><h3>Com foto (${comFoto.length})</h3>
        <div class="galeria">${comFoto.map(cartao).join('')}</div></section>

        ${anunciados.length ? `<section class="bloco"><h3>Anexo anunciado, arquivo pendente (${anunciados.length})</h3>
        <p class="destaque-texto">O reporte chegou pela conversa e as fotos ainda não viraram arquivo
        no repositório. O que dá para ler nelas já está descrito aqui.</p>
        <div class="galeria">${anunciados.map(cartao).join('')}</div></section>` : ''}

        ${semAnexo.length ? `<section class="bloco"><h3>Reportes só em texto (${semAnexo.length})</h3>
        <div class="galeria">${semAnexo.map(cartao).join('')}</div></section>` : ''}`;
    }
    paginaLeitura(html, 'colecao');
    $$('.abre-ficha').forEach((el) => el.addEventListener('click', () => abrirAtivo(el.dataset.ativo)));
    return;
  }

  if (id === 'mensal') {
    const mm = m.entrada_mensal;
    if (!mm) {
      html = cabecaColecao('Entrada mês a mês', 'A foto de entrada ainda não foi carregada.');
    } else {
      const pico = Math.max(...mm.meses.map((x) => x.qtd), 1);
      const jan = mm.meses.find((x) => x.mes === '2026-01');
      const anos = mm.legado.por_ano.map((x) => `${x.qtd} de ${x.ano}`).join(', ');
      const porMes = (mes) => mm.lista.filter((x) => x.mes === mes);

      html = cabecaColecao('Entrada mês a mês',
        `Os ${mm.total} ativos da foto de junho, pelo mês em que a SS foi
         aberta — recorte: ${esc(mm.recorte || '')}.`) +
        `<div class="numeros">
          ${num({ rotulo: 'Na foto de entrada', valor: mm.total, nota: `${mm.total_ss} SS — ativo com mais de uma entra pela mais antiga` })}
          ${num({ rotulo: 'Herdados de antes de 2026', valor: mm.legado.qtd, nota: `${Math.round(100 * mm.legado.qtd / mm.total)}% da carteira — ${anos}`, tom: 'critico' })}
          ${num({ rotulo: 'Abertos dentro de 2026', valor: mm.total - mm.legado.qtd, nota: 'de janeiro a junho' })}
          ${num({ rotulo: 'Já resolvidos', valor: mm.resolvidos, nota: `${mm.em_andamento} ainda no fluxo${mm.fora_da_carteira ? ` · ${mm.fora_da_carteira} saíram da lista de hoje` : ''}`, tom: 'bom' })}
        </div>

        <div class="nota calma" style="margin:-6px 0 26px"><strong>A regra do mês</strong>
        ${esc(mm.regra)} A data vem da coluna DATA_ABERTURA_SS da planilha de entrada;
        ${mm.fonte_data.find((f) => f.fonte.startsWith('cruzamento'))?.qtd || 0} ativos não tinham
        essa coluna preenchida e a data saiu do cruzamento pelo número da SS na base de SS/OS,
        como você mandou.</div>

        ${(mm.curva || []).length ? (() => {
          const c = mm.curva;
          const tot = (k) => c.reduce((n, x) => n + x[k], 0);
          const anos = mm.legado.por_ano;
          const janProprio = (c.find((x) => x.mes === '2026-01')?.ativos || 0) - mm.legado.qtd;
          const s26 = (mm.serie_coep || []).filter((x) => x.mes >= '2026-01' && x.mes <= '2026-07');
          const tot26 = (k) => s26.reduce((n, x) => n + x[k], 0);
          const tratadas = (mm.tratativas || []).filter((t) => t.mes_resolucao);
          const tj = tratadas.filter((x) => x.mes_resolucao <= '2026-07');
          const meses = [...new Set(tj.map((x) => x.mes_resolucao))].sort();
          const conta = (lista, f) => lista.filter(f).length;
          const cp = m.coep_2026 || {};
          const ccv = cp.curva || [];
          const SERIE_CP = [
            { chave: 'chegaram', nome: 'Chegaram ao posto', cor: 'var(--serie-1)',
              dica: 'equipamento que apareceu no COEP naquele mês, pela primeira vez em 2026' },
            { chave: 'resolvidos', nome: 'Resolvidos', cor: 'var(--serie-3)',
              dica: 'pelo mês em que a demanda fechou' },
          ];
          const usaCp = ccv.length > 0;
          return `<section class="bloco"><h3>Entrada e saída do posto em 2026</h3>
        <p class="destaque-texto">${usaCp ? `A linha azul é quem <b>chegou ao posto</b> no mês —
        equipamento apontado pela cadeia de repasse, pela primeira vez em 2026. A verde é quem o
        posto <b>resolveu</b>, pelo mês em que a demanda fechou. O ano abriu com
        <b>${cp.herdados || 0}</b> já na mesa, de anos anteriores. Agosto é mês parcial, até
        18/08.` : `Duas séries, uma entrada e uma saída, na janela ${esc(mm.janela || '')}.`}</p>
        ${barrasTresColunas(usaCp ? ccv : c, usaCp ? SERIE_CP : undefined)}
    <h4 class="sub-grafico">Visão COEP</h4>
    <p class="destaque-texto">Onde cada série chegou até o fim de cada mês. Aqui o que conta é a
    distância entre as curvas: enquanto a azul sobe e a verde fica no chão, a fila está
    crescendo; quando a verde encosta na azul, o posto passou a dar conta do que entra.</p>
    ${linhaAcumulada(usaCp ? ccv : c, usaCp ? SERIE_CP : undefined)}
    ${mm.saldo?.length ? `<h4 class="sub-grafico">A carteira em movimento</h4>
    <p class="destaque-texto">O livro-caixa da carteira herdada: começa com o acervo de
    ${mm.abertura} SS de anos anteriores, cada mês soma o que abriu no próprio mês e desconta o
    que foi tratado. Janeiro: ${mm.abertura} + ${mm.saldo[0].entram} − ${mm.saldo[0].saem} =
    ${mm.saldo[0].final}, e fevereiro já começa com ${mm.saldo[0].final}.</p>
    ${livroCaixa(mm)}` : ''}
        <div class="tabela-rol" style="margin-top:18px"><table class="matriz livro"><thead><tr><th>Mês</th>
        <th class="num">${usaCp ? 'Chegaram ao posto' : 'Entrantes'}</th><th class="num">Resolvidos</th></tr></thead><tbody>
        ${(usaCp ? ccv : c).map((x) => `<tr><td>${esc(x.rotulo)}</td>
          <td class="num">${(usaCp ? x.chegaram : x.entrantes) || '—'}</td>
          <td class="num">${x.resolvidos || '—'}</td></tr>`).join('')}
        </tbody><tfoot><tr><td>Total até 18/08</td>
        <td class="num"><b>${usaCp ? ccv.reduce((n, x) => n + x.chegaram, 0) : tot('entrantes')}</b></td>
        <td class="num"><b>${usaCp ? ccv.reduce((n, x) => n + x.resolvidos, 0) : tot('resolvidos')}</b></td>
        </tr></tfoot></table></div>
        ${usaCp ? `<div class="nota branda"><strong>O livro-caixa abaixo é outro recorte.</strong>
        Ele acompanha só a carteira herdada da foto de entrada — ${mm.total} SS. Os gráficos acima
        contam a base inteira pela cadeia da demanda.</div>` : ''}
        ${mm.fora_do_recorte?.qtd ? `<div class="nota branda" style="margin-top:12px"><strong>O que ficou fora do recorte</strong>
        Concluído conta de qualquer tipo; pendente, só se for indisponibilidade. Da foto de entrada
        fica fora ${mm.fora_do_recorte.qtd === 1 ? 'um ativo' : `${mm.fora_do_recorte.qtd} ativos`} de outro
        tipo ainda pendente: ${mm.fora_do_recorte.por_tipo.map(([t, q]) => `${q} ${esc(t.toLowerCase())}`).join(' · ')}.
        Segue na coleção «Carteira de entrada».</div>` : ''}
        </section>

        <section class="bloco"><h3>O que janeiro carrega</h3>
        <p class="destaque-texto">Janeiro é metade da carteira e é quase tudo acervo: dos
        ${c.find((x) => x.mes === '2026-01')?.ativos || 0} ativos, só ${janProprio} têm SS aberta no
        próprio mês. Sem a regra, esses ${mm.legado.qtd} ficariam espalhados por 2023, 2024 e 2025 e
        a curva de 2026 perderia o tamanho do que foi herdado.</p>
        <div class="tabela-rol"><table class="matriz"><thead><tr><th>Origem</th>
        <th class="num">Ativos</th><th class="num">% de janeiro</th></tr></thead><tbody>
        <tr><td>SS aberta em jan/2026</td><td class="num">${janProprio}</td>
          <td class="num">${(100 * janProprio / (c.find((x) => x.mes === '2026-01')?.ativos || 1)).toFixed(1).replace('.', ',')}%</td></tr>
        ${[...anos].reverse().map((a) => `<tr><td>Acervo — SS aberta em ${a.ano}</td>
          <td class="num">${a.qtd}</td>
          <td class="num">${(100 * a.qtd / (c.find((x) => x.mes === '2026-01')?.ativos || 1)).toFixed(1).replace('.', ',')}%</td></tr>`).join('')}
        </tbody><tfoot><tr><td>Total de janeiro</td>
        <td class="num"><b>${c.find((x) => x.mes === '2026-01')?.ativos || 0}</b></td>
        <td class="num"><b>100,0%</b></td></tr></tfoot></table></div>
        ${mm.legado.mais_antiga ? `<div class="nota branda" style="margin-top:12px">
        <strong>A mais velha da carteira</strong>${esc(mm.legado.mais_antiga.numero_ss)}, ativo
        ${esc(mm.legado.mais_antiga.ativo)} em ${esc(mm.legado.mais_antiga.localidade)}, aberta em
        ${esc(dataBr(mm.legado.mais_antiga.abertura))}.</div>` : ''}
        </section>

        

        ${meses.length ? `<section class="bloco"><h3>Quando cada um foi tratado de verdade</h3>
        <p class="destaque-texto">Mês da tratativa, não da abertura. A data é o término da SS de
        entrada; quando a SS foi repassada em vez de encerrada, vale a data do repasse. Faltando as
        duas, entram obra encerrada no AIC, reporte de campo, decisão do gestor e, por último, a SS
        mais recente atendida no ativo.</p>
        <div class="tabela-rol"><table class="matriz"><thead><tr><th>Mês da tratativa</th>
        <th class="num">Resolvidos</th><th class="num">Acumulado</th>
        <th class="num">Por cancelamento da SS</th><th class="num">Por repasse</th>
        <th class="num">Outras vias</th><th class="num">Com parecer COEP</th></tr></thead><tbody>
        ${(() => { let ac = 0; return meses.map((k) => {
          const g = tratadas.filter((t) => t.mes_resolucao === k);
          ac += g.length;
          const canc = conta(g, (t) => t.via === 'cancelamento da SS de entrada');
          const rep = conta(g, (t) => t.via === 'repasse para a etapa seguinte');
          const [a, mnum] = k.split('-');
          return `<tr><td>${['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'][+mnum - 1]}/${a}</td>
            <td class="num"><b>${g.length}</b></td><td class="num">${ac}</td>
            <td class="num">${canc || '—'}</td><td class="num">${rep || '—'}</td>
            <td class="num">${(g.length - canc - rep) || '—'}</td>
            <td class="num">${conta(g, (t) => t.parecer_coep) || '—'}</td></tr>`;
        }).join(''); })()}
        </tbody><tfoot><tr><td>Total até 18/08</td><td class="num"><b>${tj.length}</b></td><td class="num">—</td>
        <td class="num"><b>${conta(tj, (t) => t.via === 'cancelamento da SS de entrada')}</b></td>
        <td class="num"><b>${conta(tj, (t) => t.via === 'repasse para a etapa seguinte')}</b></td>
        <td class="num"><b>${conta(tj, (t) => !['cancelamento da SS de entrada', 'repasse para a etapa seguinte'].includes(t.via))}</b></td>
        <td class="num"><b>${conta(tj, (t) => t.parecer_coep)}</b></td></tr></tfoot></table></div>
        <div class="nota" style="margin-top:12px"><strong>O desenho da atuação</strong>
        ${conta(tj, (t) => t.mes_resolucao >= '2026-04')} dos ${tj.length} foram tratados de
        abril em diante na janela.${tratadas.length > tj.length ? ` Fora dela, em agosto, mais ${tratadas.length - tj.length}.` : ''} Maio e junho são limpeza de fila — a maioria saiu por cancelamento de SS.
        Julho vira o jogo: a maior parte sai por repasse, e é o mês em que quase todos os que tinham
        parecer COEP foram embora. Repasse quer dizer que a demanda saiu do posto, não que o serviço
        acabou em campo.</div>
        </section>` : ''}`;
        })() : ''}

        <section class="bloco"><h3>A curva de entrada</h3>
        <p class="destaque-texto">Cada barra é um mês; a parte verde é o que já saiu da carteira e a
        amarela é o que continua no fluxo. Janeiro é o mês do acervo: ${jan ? jan.legado : 0} das
        ${jan ? jan.qtd : 0} demandas de janeiro são SS abertas antes de 2026.</p>
        <div class="curva-mes">
          ${mm.meses.map((b) => `<div class="mes-linha">
            <span class="rot">${esc(b.rotulo)}</span>
            <i class="trilho"><b style="width:${(b.resolvidos / pico * 100).toFixed(1)}%"></b><em style="width:${(b.em_andamento / pico * 100).toFixed(1)}%"></em></i>
            <span class="lado"><b>${b.qtd}</b> ${b.resolvidos} resolvidos · ${b.em_andamento} no fluxo</span>
          </div>`).join('')}
        </div>
        <div class="legenda-mes"><span class="am-feito"></span> resolvido
          <span class="am-fluxo"></span> ainda no fluxo</div>
        </section>

        <section class="bloco"><h3>Como cada safra de entrada terminou</h3>
        <p class="destaque-texto">Aqui a linha é o mês em que a SS <b>abriu</b> e as duas últimas
        colunas dizem onde aquela safra está <b>hoje</b> — não em que mês foi tratada. É outra
        pergunta: a tabela lá em cima conta a saída pelo mês da tratativa, esta conta o destino de
        quem entrou em cada mês.</p>
        <div class="tabela-rol"><table class="matriz"><thead><tr><th>Mês de abertura</th>
        <th class="num">Ativos</th><th class="num">De antes de 2026</th><th class="num">Abertos no mês</th>
        <th class="num">Já resolvidos hoje</th><th class="num">Ainda no fluxo</th><th class="num">% resolvido</th></tr></thead><tbody>
        ${mm.meses.map((b) => `<tr><td>${esc(b.rotulo)}</td>
          <td class="num"><b>${b.qtd}</b></td>
          <td class="num">${b.legado || '—'}</td><td class="num">${b.no_mes || '—'}</td>
          <td class="num">${b.resolvidos}</td><td class="num">${b.em_andamento}</td>
          <td class="num">${b.percentual.toFixed(1).replace('.', ',')}%</td></tr>`).join('')}
        </tbody><tfoot><tr><td>Total</td><td class="num"><b>${mm.total}</b></td>
        <td class="num">${mm.legado.qtd}</td><td class="num">${mm.total - mm.legado.qtd}</td>
        <td class="num">${mm.resolvidos}</td><td class="num">${mm.em_andamento}</td>
        <td class="num">${(100 * mm.resolvidos / mm.total).toFixed(1).replace('.', ',')}%</td></tr></tfoot>
        </table></div></section>

        ${mm.meses.map((b) => `<section class="bloco"><h3>${esc(b.rotulo)} — ${b.qtd} ativos</h3>
        <div class="cartas">${porMes(b.mes).map((x) => {
          const abre = x.na_carteira;
          return `<${abre ? 'button' : 'div'} class="carta"${abre ? ` data-ativo="${esc(x.ativo)}"` : ' style="cursor:default"'}>
          <div class="topo-carta"><span class="cod">${esc(x.ativo)}</span>
            <span class="selo ${x.resolvido ? 'c-baixa' : 'neutro'}">${x.resolvido ? 'resolvido' : 'no fluxo'}</span>
            ${x.legado ? '<span class="selo destaque">acervo</span>' : ''}
            ${abre ? '' : '<span class="selo neutro">saiu da lista de hoje</span>'}</div>
          <div class="onde">${esc(x.localidade)} · ${esc(x.tipo)}</div>
          <p><b class="mono">${esc(x.numero_ss)}</b> aberta em ${esc(dataBr(x.abertura))}${x.outras_ss.length ? ` · mais ${x.outras_ss.length} SS na foto` : ''}
          ${x.motivo ? `<br>${esc(x.motivo)}` : ''}</p></${abre ? 'button' : 'div'}>`;
        }).join('')}</div></section>`).join('')}

        <section class="bloco"><h3>De onde veio cada data</h3>
        <div class="itens">
          ${mm.fonte_data.map((f) => `<div class="item-linha"><span>${esc(f.fonte)}</span><b>${f.qtd}</b></div>`).join('')}
          ${mm.legado.mais_antiga ? `<div class="item-linha"><span>SS mais antiga da foto — ${esc(mm.legado.mais_antiga.numero_ss)},
            ativo ${esc(mm.legado.mais_antiga.ativo)} em ${esc(mm.legado.mais_antiga.localidade)}</span>
            <b>${esc(dataBr(mm.legado.mais_antiga.abertura))}</b></div>` : ''}
          ${mm.multiplas_ss.length ? `<div class="item-linha"><span>Ativos com mais de uma SS na foto — entraram pela mais antiga</span>
            <b>${mm.multiplas_ss.length}</b></div>` : ''}
          ${mm.sem_data.length ? `<div class="item-linha"><span>SS sem data em nenhuma das duas bases</span><b>${mm.sem_data.length}</b></div>` : ''}
        </div>
        ${mm.multiplas_ss.length ? `<p class="destaque-texto" style="margin-top:14px">
        ${mm.multiplas_ss.map((x) => `<b class="mono">${esc(x.ativo)}</b>: ${x.ss.map(esc).join(', ')} — usei a ${esc(x.usada)}`).join('<br>')}</p>` : ''}
        </section>`;
    }
    paginaLeitura(html, 'colecao');
    ligarCartas();
    return;
  }

  if (id === 'entrada') {
    const en = m.entrada;
    if (!en) {
      html = cabecaColecao('Carteira de entrada', 'A foto de entrada ainda não foi carregada.');
    } else {
      const res = en.resolvidos, ver = en.verificar, and = en.em_andamento;
      const REGRAS = {
        1: 'Canceladas', 2: 'Tratativa com equipamento', 3: 'Em fase de ajustes',
        4: 'Concluída sem indisponibilidade aberta', 5: 'Aguardando comissionamento',
        6: 'Cancelada sem reincidência', 7: 'Obra encerrada no AIC',
      };
      const fichaLink = (a) => `<b class="mono">${esc(a)}</b>`;

      html = cabecaColecao('Carteira de entrada', '') +
        `<div class="numeros">
          ${num({ rotulo: 'Carteira de entrada', valor: en.total_ativos, nota: `${en.por_tipo['Religador'] || 0} religadores · ${en.por_tipo['Regulador de Tensão'] || 0} reguladores · ${en.total_ss} SS` })}
          ${num({ rotulo: 'Já resolvidos', valor: res.ativos, nota: `${en.reducao_percentual}% da carteira herdada`, tom: 'bom' })}
          ${num({ rotulo: 'Ainda no fluxo', valor: and.ativos, nota: `${and.por_posto['COEP'] || 0} SS ainda no COEP`, tom: 'atento' })}
          ${ver.ativos ? num({ rotulo: 'A verificar', valor: ver.ativos, nota: 'etapa seguinte com sinal de espera ou defeito novo', tom: 'critico' })
            : en.sem_rastro_ativos ? num({ rotulo: 'Sem rastro no SGM', valor: en.sem_rastro_ativos, nota: 'SS de 2023 que sumiram da base', tom: 'atento' })
            : num({ rotulo: 'Fora da análise', valor: en.excluidos_ativos ?? 0, nota: 'excluídos por decisão do gestor' })}
        </div>

        <div class="nota calma" style="margin:-6px 0 26px"><strong>A conta fecha assim</strong>
        ${res.ativos} resolvidos + ${and.ativos} ainda no fluxo${ver.ativos ? ` + ${ver.ativos} a verificar` : ''}${en.sem_rastro_ativos ? ` + ${en.sem_rastro_ativos} sem rastro no SGM` : ''}
        = ${en.total_ativos} ativos da carteira de entrada. Cada ativo entra num balde só.
        ${en.excluidos_ativos ? `Fora da conta, por decisão sua: ${en.excluidos_ativos} ${en.excluidos_ativos === 1 ? 'ativo excluído' : 'ativos excluídos'} da análise
        (${[...new Set(en.excluidos.map((x) => x.ativo + ' · ' + (x.localidade || '')))].map(esc).join('; ')}).` : ''}
        ${en.ss_sumida_com_ativo_vivo ? `Em ${en.ss_sumida_com_ativo_vivo} caso${en.ss_sumida_com_ativo_vivo > 1 ? 's' : ''} a SS de 2023 sumiu do SGM,
        mas o ativo tem histórico — aí a leitura passa a ser a cadeia mais recente dele.` : ''}</div>

        <section class="bloco"><h3>Detalhamento</h3>
        <div class="numeros" style="margin-bottom:0">
          ${num({ rotulo: 'Canceladas', valor: en.canceladas.ss, nota: 'SS da foto que hoje estão canceladas' })}
          ${num({ rotulo: 'Tratativa no equipamento', valor: en.tratativas.ss, nota: 'troca, instalação ou obra registrada' })}
        </div></section>

        <section class="bloco"><h3>As sete réguas, uma a uma</h3>
        <p class="destaque-texto">Cada ativo entra uma vez só: quando mais de uma régua se aplica, vale a mais forte
        (obra encerrada → concluída → comissionamento → cancelada → ajustes).</p>
        <div class="itens">
          ${[1, 2, 3, 4, 5, 6, 7].map((r) => {
            const valor = r === 1 ? en.canceladas.ss : r === 2 ? en.tratativas.ss : (res.por_regra[r] || 0);
            const extra = r === 1 ? ' — o que você cancelou'
              : r === 2 ? ` — ${res.por_regra[2] || 0} entraram na conta por confirmação sua`
              : '';
            return `<div class="item-linha"><span>Item ${r} · ${esc(REGRAS[r])}${extra}</span><b>${valor}</b></div>`;
          }).join('')}
        </div>
        <p class="destaque-texto" style="margin-top:12px">Os itens 1 e 2 medem o que foi feito e não somam
        no total: uma SS cancelada volta no item 6 quando não houve reincidência, e a tratativa entra pelo
        item que fechou o caso. A soma dos resolvidos são os itens 3 a 7.</p>
        <div class="nota calma" style="margin-top:14px"><strong>Leitura</strong>
        SS pendente da MESMA cadeia não bloqueia: é a etapa seguinte do próprio serviço (ajuste ou
        comissionamento depois da troca), e não reincidência — correção do gestor em 13/08.
        As 25 canceladas aparecem no item 1 e voltam no item 6 quando não houve reincidência —
        são o mesmo ativo, contado uma vez no total. O item 2 mede intervenção no equipamento
        (execução do DCMD, obra de substituição, parecer de troca/entrega); laudo do DMSL e ajuste
        do DEOP ficam em «atendimento técnico», à parte.</div></section>

        ${ver.lista.length ? `<section class="bloco"><h3>Para você verificar — ${ver.ativos} ativos</h3>
        <p class="destaque-texto">Ou têm SS de INDISPONIBILIDADE PARA OPERAÇÃO de OUTRA demanda ainda
        pendente, ou a etapa seguinte da própria demanda traz sinal de espera de material / defeito novo no texto.
        Pela sua régua não entram como resolvidos até você conferir.</p>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>SS de entrada</th><th>Situação</th><th>SS de indisponibilidade aberta</th><th>Parecer COEP</th></tr></thead><tbody>
        ${ver.lista.map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td>${fichaLink(i.ativo)}</td><td>${esc(i.localidade || '—')}</td>
          <td>${esc(i.numero_ss)}</td><td>${esc((i.situacao_hoje || '').replace('SS ', ''))}</td>
          <td>${[...(i.indisponibilidades_abertas || []), ...(i.cauda_mesma_demanda || [])]
            .map((x) => `${esc(x.numero)} · ${esc(x.equipe)} · ${dataBr(x.abertura)}`).join('<br>') || '—'}</td>
          <td>${esc(i.parecer_coep || '—')}</td></tr>`).join('')}
        </tbody></table></div></section>` : ''}

        ${(en.decisoes_gestor || []).length ? `<section class="bloco"><h3>Confirmado por você — ${en.decisoes_gestor.length} ativos</h3>
        <p class="destaque-texto">Casos em que o campo andou e o SGM não registrou. Sua confirmação vale como
        fonte; o que falta aqui é higiene de sistema, não serviço.</p>
        ${en.decisoes_gestor.map((d) => `<div class="nota calma" style="margin-bottom:12px">
          <strong>${esc(d.ativo)} · ${esc(d.localidade)} — ${esc(d.motivo)}</strong>${esc(d.nota)}</div>`).join('')}
        </section>` : ''}

        ${en.cauda && en.cauda.ss ? `<section class="bloco"><h3>Etapa seguinte do mesmo serviço — ${en.cauda.ss} ativos</h3>
        <p class="destaque-texto">Correção de 13/08: a SS que aparecia «bloqueando» estes ativos é da MESMA cadeia — 
        o DCMD executou e repassou no mesmo carimbo para a Proteção ajustar (${en.cauda.por_etapa.DEOP || 0})
        ou para o DMSL comissionar (${en.cauda.por_etapa.DMSL || 0}). É a etapa seguinte do mesmo serviço,
        não uma reincidência. Só conta quando o texto da cadeia registra a execução.</p>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>Etapa que falta</th><th>SS do fluxo</th><th>Situação</th></tr></thead><tbody>
        ${en.cauda.lista.map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td>${fichaLink(i.ativo)}</td><td>${esc(i.localidade || '—')}</td>
          <td>${i.etapa_final === 'DEOP' ? 'ajustes da Proteção' : 'comissionamento do DMSL'}</td>
          <td>${i.cauda_mesma_demanda.map((c) => `${esc(c.numero)} · ${esc(c.equipe)} · ${dataBr(c.abertura)}`).join('<br>')}</td>
          <td>${i.alerta_cauda ? '<b>a verificar</b> — o texto fala em espera de material ou defeito novo' : 'conta como resolvido'}</td></tr>`).join('')}
        </tbody></table></div></section>` : ''}

        <section class="bloco"><h3>Os ${res.ativos} que saíram${res.ss !== res.ativos ? ` — ${res.ss} SS, porque ${res.ss - res.ativos} ${res.ss - res.ativos === 1 ? 'ativo trouxe duas SS' : 'ativos trouxeram duas SS'} da foto de entrada` : ''}</h3>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Tipo</th><th>Localidade</th>
        <th>Régua</th><th>Por quê</th></tr></thead><tbody>
        ${res.lista.map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td>${fichaLink(i.ativo)}</td><td>${esc(i.tipo === 'Religador' ? 'RL' : 'RT')}</td>
          <td>${esc(i.localidade || '—')}</td><td>item ${esc(String(i.regra))}</td>
          <td>${esc(i.motivo)}${i.obras_encerradas?.length ? ` · obra ${i.obras_encerradas.map(esc).join(', ')}` : ''}${i.na_protecao && i.regra === 3 ? ' · ainda na Proteção' : ''}</td></tr>`).join('')}
        </tbody></table></div></section>

        <section class="bloco"><h3>Os ${and.ativos} que continuam no fluxo${and.ss !== and.ativos ? ` — ${and.ss} SS` : ''}</h3>
        <div class="grade" style="margin-bottom:18px">
          <div class="quadro"><header><h3>Posto atual</h3><p>onde a demanda parou</p></header>
          ${barras(Object.entries(and.por_posto).map(([k, v]) => ({ rotulo: k, total: v })))}</div>
        </div>
        <div class="tabela-rol"><table class="matriz rol-entrada"><thead><tr><th>Ativo</th><th>Localidade</th>
        <th>SS de entrada</th><th>Aberta em</th><th>Posto</th><th>Parecer COEP</th></tr></thead><tbody>
        ${and.lista.map((i) => `<tr data-ativo="${esc(i.ativo)}">
          <td>${fichaLink(i.ativo)}</td><td>${esc(i.localidade || '—')}</td><td>${esc(i.numero_ss)}</td>
          <td>${i.abertura ? dataBr(i.abertura) : '—'}</td><td>${esc(i.posto_atual || '—')}</td>
          <td>${esc(i.parecer_coep || (i.na_carteira ? '—' : 'fora da carteira dos 129'))}</td></tr>`).join('')}
        </tbody></table></div></section>

        ${en.ajustes.ss ? `<section class="bloco"><h3>Em fase de ajustes — item 3</h3>
        <p class="destaque-texto">Pelo parecer COEP contam como resolvidos por você; ${en.ajustes.ainda_na_protecao}
        dos ${en.ajustes.ss} ainda aparecem no posto da Proteção pela base de SS/OS, então seguem marcados
        como «em fase de ajuste».</p>
        <div class="itens">${en.ajustes.lista.map((i) =>
          `<div class="item-linha"><span>${fichaLink(i.ativo)} · ${esc(i.localidade || '')}</span><b>${i.na_protecao ? 'na Proteção' : 'fora da Proteção'}</b></div>`).join('')}</div></section>` : ''}

        ${(en.excluidos || []).length ? `<section class="bloco"><h3>Fora da análise por decisão sua</h3>
        ${en.excluidos.map((x) => `<div class="nota calma" style="margin-bottom:10px">
          <strong>${esc(x.ativo)} · ${esc(x.localidade || '')} — SS ${esc(x.numero_ss)}</strong>${esc(x.nota || '')}</div>`).join('')}
        </section>` : ''}

        ${en.sem_rastro.length ? `<section class="bloco"><h3>Sem rastro na base de hoje</h3>
        <p class="destaque-texto">${en.sem_rastro.length} SS de 2023 da foto de entrada não existem mais na base
        de SS/OS — sumiram do SGM entre as duas fotos. Ficam sem veredito.</p>
        <div class="itens">${en.sem_rastro.map((i) =>
          `<div class="item-linha"><span>${esc(i.numero_ss)} · ${fichaLink(i.ativo)} · ${esc(i.localidade || '')}</span><b>${esc(i.ano)}</b></div>`).join('')}</div></section>` : ''}

        ${(en.premissas || []).length ? `<div class="nota calma" style="margin-top:18px"><strong>Premissas desta contagem</strong>${en.premissas.map(esc).join('<br>')}</div>` : ''}`;
    }
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

    const dem = m.demandas;
    if (dem) {
      const c2 = dem.concluidas_dcmd_2026 || {}, ab = dem.abertas || {};
      partes.push(`<section class="bloco"><h3>Recorte do gestor — por demanda encadeada</h3>
        <div class="numeros">
          ${num({ rotulo: 'Concluídas pelo DCMD em 2026', valor: c2.total ?? '—', nota: 'demandas executadas por equipe RD/ENC/DOLP', tom: 'bom' })}
          ${num({ rotulo: 'Religador / Regulador', valor: `${c2.por_tipo?.['Religador'] ?? 0} / ${c2.por_tipo?.['Regulador de Tensão'] ?? 0}` })}
          ${num({ rotulo: 'Passaram pelo COEP', valor: c2.passaram_pelo_coep ?? '—', nota: 'com etapa de compra na cadeia' })}
          ${num({ rotulo: 'Demandas abertas', valor: ab.total ?? '—', nota: `${ab.na_carteira_129 ?? '—'} ativos da carteira`, tom: 'atento' })}
          ${num({ rotulo: 'Repasses pendurados', valor: ab.repasses_pendurados ?? '—', nota: 'repassada sem SS sucessora', tom: 'critico' })}
        </div>
        <div class="grade">
          ${c2.por_mes ? `<div class="quadro"><header><h3>Concluídas DCMD por mês</h3></header>${barras(Object.entries(c2.por_mes).map(([k, v]) => ({ rotulo: k, total: v })))}</div>` : ''}
          ${ab.por_posto_atual ? `<div class="quadro"><header><h3>Abertas por posto atual</h3></header>${barras(Object.entries(ab.por_posto_atual).map(([k, v]) => ({ rotulo: k, total: v })))}</div>` : ''}
          ${dem.caminhos_mais_comuns ? `<div class="quadro"><header><h3>Caminhos mais comuns</h3><p>postos percorridos pela demanda</p></header>${barras(dem.caminhos_mais_comuns.slice(0, 8).map((x) => ({ rotulo: x.caminho, total: x.demandas })))}</div>` : ''}
        </div>
        <div class="nota calma" style="margin-top:16px"><strong>A lógica das SS gêmeas</strong>
        ${esc(`${dem.total_ss} SS de RL/RT viram ${dem.total_demandas} demandas (média ${dem.ss_por_demanda_media} SS por demanda). `)}
        Cadeia: mesmo ativo + mesmo carimbo de abertura (padrão do repasse no SGM), ou SS aberta
        em até 7 dias após uma repassada; ciclos separados a 180 dias. Rotina de bateria/cadastro
        fora do recorte, como definido em 12/08.</div>
        ${(dem.premissas || []).length ? `<div class="nota calma" style="margin-top:10px"><strong>Premissas</strong>${dem.premissas.map(esc).join('<br>')}</div>` : ''}
      </section>`);
    }

    const c25 = m.missao?.coep2025;
    if (c25) {
      const rr = c25.resumo || {};
      const NOMES_V = {
        resolvido_confirmado: 'Resolvido (confirmado)', resolvido_aparente: 'Resolvido (aparente)',
        em_aberto: 'Em aberto', reincidiu: 'Reincidiu', virou_outro_defeito: 'Virou outro defeito',
        indefinido: 'Indefinido',
      };
      const reinc = (c25.ativos || []).filter((x) => x.veredito === 'reincidiu');
      const conflitos = (c25.ativos || []).filter((x) => x.conflito_com_site);
      partes.push(`<section class="bloco"><h3>A turma de 2025 do COEP — onde está hoje</h3>
        <p style="margin:0 0 14px;color:var(--tinta-2);font-size:13.5px;font-style:italic">
          Auditoria independente: os ${rr.total ?? '—'} ativos que passaram pelo posto do COEP em
          2025 (inclusive só como repassado), conferidos linha por linha contra a base de SS/OS
          de hoje. ${rr.na_carteira ?? '—'} estão na carteira dos 129.</p>
        <div class="numeros">
          ${Object.entries(rr.por_veredito || {}).map(([k, v]) =>
            num({ rotulo: NOMES_V[k] || k, valor: v,
                  tom: k === 'reincidiu' ? 'critico' : k === 'em_aberto' ? 'atento' : (k.startsWith('resolvido') ? 'bom' : '') })).join('')}
        </div>
        ${rr.por_posto_dos_em_aberto ? `<div class="grade" style="margin-bottom:22px">
          <div class="quadro"><header><h3>Os em aberto estão com</h3></header>${barras(Object.entries(rr.por_posto_dos_em_aberto).map(([k, v]) => ({ rotulo: k, total: v })))}</div>
        </div>` : ''}
        ${reinc.length ? `<h3 style="margin:22px 0 12px;border-bottom:1px solid var(--tinta);padding-bottom:5px;font-size:14.5px">Reincidências — resolvido que voltou</h3>
          <div class="cartas">${reinc.map((x) => `<button class="carta" ${x.na_carteira ? `data-ativo="${esc(x.ativo)}"` : 'style="cursor:default"'}>
            <div class="topo-carta"><span class="cod">${esc(x.ativo)}</span>
              <span class="selo c-muito-alta">Reincidiu</span>
              ${x.reincidencia ? `<span class="selo neutro">${esc(dataBr(x.reincidencia.resolvido_em))} → ${esc(dataBr(x.reincidencia.voltou_em))}</span>` : ''}</div>
            <p>${esc(x.historia || '')}</p></button>`).join('')}</div>` : ''}
        ${conflitos.length ? `<h3 style="margin:22px 0 12px;border-bottom:1px solid var(--tinta);padding-bottom:5px;font-size:14.5px">Conflitos e higiene do SGM — ${conflitos.length} apontamentos</h3>
          <p style="margin:0 0 12px;color:var(--tinta-2);font-size:13px;font-style:italic">A maioria é
          o mesmo padrão: execução concluída e as SS antigas seguem repassadas no sistema, sem baixa.
          Mostrando os ${Math.min(30, conflitos.length)} primeiros — os da carteira abrem a ficha.</p>
          <div class="cartas">${conflitos.slice(0, 30).map((x) => `<button class="carta" ${x.na_carteira ? `data-ativo="${esc(x.ativo)}"` : 'style="cursor:default"'}>
            <div class="topo-carta"><span class="cod">${esc(x.ativo)}</span><span class="selo c-alta">Conflito</span>${x.na_carteira ? '<span class="selo neutro">carteira</span>' : ''}</div>
            <p>${esc(x.conflito_com_site)}</p></button>`).join('')}</div>` : ''}
        ${(c25.premissas || []).length ? `<div class="nota calma" style="margin-top:14px"><strong>Premissas</strong>${c25.premissas.map(esc).join('<br>')}</div>` : ''}
      </section>`);
    }

    const oc = m.obra_cruzada;
    if (oc && (oc.achados || []).length) {
      const NOMES_OC = {
        obra_em_dois_ativos: 'Mesma obra em ativos diferentes',
        obra_ss_vs_emd: 'SS diz um ativo, EMD diz outro',
        emd_vs_descricao_aic: 'EMD diz um ativo, a descrição da obra cita outro',
        obra_fantasma: 'Obra declarada que não existe no AIC',
        m4_vs_ssos: 'Obra principal aparecendo em SS de outro ativo',
      };
      partes.push(`<section class="bloco"><h3>Obra × ativo — caminhos inversos</h3>
        <p style="margin:0 0 14px;color:var(--tinta-2);font-size:13.5px;font-style:italic">
          Partindo do número da obra e perguntando a quais ativos 58/79 ele está preso em cada
          fonte (SS/OS, EMD, descrição no AIC). Conferência contra o índice completo do AIC:
          124.084 obras — e as 202 obras declaradas nas SS existem todas, corrigindo a leitura
          anterior de que algumas seriam inexistentes (estavam só fora do recorte de RL/RT).</p>
        <div class="cartas">${oc.achados.map((a) => `<div class="carta" ${a.na_carteira.length ? `data-ativo="${esc(a.na_carteira[0])}"` : 'style="cursor:default"'}>
          <div class="topo-carta"><span class="cod">${esc(a.obra)}</span>
            <span class="selo ${a.tipo === 'obra_fantasma' ? 'c-muito-alta' : 'c-alta'}">${esc(NOMES_OC[a.tipo] || a.tipo)}</span>
            ${a.aic ? `<span class="selo neutro">${esc(a.aic.st.split(':')[0])}${a.aic.sig ? ' · SIGCO ' + esc(a.aic.sig) : ''}</span>` : ''}</div>
          <p>${esc(a.detalhe)}</p>
          ${a.na_carteira.length ? `<div class="rodape"><span>na carteira: ${esc(a.na_carteira.join(', '))}</span></div>` : ''}
        </div>`).join('')}</div>
        ${(oc.premissas || []).length ? `<div class="nota calma" style="margin-top:14px"><strong>Premissas</strong>${oc.premissas.map(esc).join('<br>')}</div>` : ''}
      </section>`);
    }

    if (d) {
      const e = d.recorte_estrito || {}, a = d.recorte_amplo || {};
      const ec = e.concluidas_2026 || {}, ee = e.a_entrar || {};
      const ac = a.concluidas_2026 || {}, ae = a.a_entrar || {};
      partes.push(`<section class="bloco"><h3>Contagem por SS (recorte por natureza — anterior à regra do gestor)</h3>
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
  $('#baixar-classif')?.addEventListener('click', baixarClassificacoes);
  $('#limpar-classif')?.addEventListener('click', () => {
    if (!confirm('Apagar todas as suas classificações deste navegador?')) return;
    try { localStorage.removeItem(CHAVE_CLASSIF); } catch { /* ignora */ }
    estado.classificacoes = {};
    abrirColecao('classificacoes');
  });
}

/* ---------------- mapa ---------------- */

// Modos de pintura do mapa. A cor é sinal: cada modo responde a uma pergunta —
// onde está o risco (criticidade), o que é cada ponto (tipo), como está em campo (situação).
const MODOS_MAPA = {
  criticidade: {
    rotulo: (e) => e.criticidade,
    ordem: ORDEM_CRIT,
    cor: {
      'Muito Alta': 'var(--muito-alta)', 'Alta': 'var(--alta)', 'Média': 'var(--media)',
      'Baixa': 'var(--baixa)', 'Sem classificação': 'var(--sem-classe)',
    },
  },
  tipo: {
    rotulo: (e) => (e.tipo === '79' ? 'Religador' : 'Regulador de Tensão'),
    ordem: ['Religador', 'Regulador de Tensão'],
    cor: { 'Religador': 'var(--sinal)', 'Regulador de Tensão': 'var(--baixa)' },
  },
  situacao: {
    rotulo: (e) => e.analise?.status_operacional || 'Não informado',
    ordem: ['By-passado em campo', 'Fora de operação', 'Operando com restrição',
            'Removido/Recolhido', 'Operando normal', 'Não informado'],
    cor: {
      'By-passado em campo': 'var(--muito-alta)', 'Fora de operação': 'var(--alta)',
      'Operando com restrição': 'var(--media)', 'Removido/Recolhido': 'var(--sem-classe)',
      'Operando normal': 'var(--baixa)', 'Não informado': 'var(--sem-classe)',
    },
  },
};

function desenharMapa(itens) {
  const caixa = $('#mapa');
  if (!caixa || !itens.length) return;

  const modo = MODOS_MAPA[estado.mapaModo || 'criticidade'];
  $$('#modo-mapa .pastilha').forEach((b) =>
    b.setAttribute('aria-pressed', String(b.dataset.modo === (estado.mapaModo || 'criticidade'))));

  const margem = 42;
  const geo = estado.geo;
  let lats = itens.map((e) => e.geo.lat), lons = itens.map((e) => e.geo.lon);
  if (geo?.fronteira?.length) {
    // O contorno do estado emoldura o mapa: a bbox passa a ser a do Tocantins.
    const anel = geo.fronteira.flat();
    lats = anel.map((p) => p[1]);
    lons = anel.map((p) => p[0]);
  }
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

  // Categorias mais graves por último, para ficarem por cima na sobreposição.
  const ordenados = [...itens].sort((a, b) =>
    modo.ordem.indexOf(modo.rotulo(b)) - modo.ordem.indexOf(modo.rotulo(a)));

  const pontos = ordenados.map((e) => {
    const cat = modo.rotulo(e);
    const destaque = modo.ordem.indexOf(cat);
    const r = destaque === 0 ? 6.5 : destaque === 1 ? 5.5 : 4.5;
    const d = e.ss_sgm?.dias_aberta;
    return `<circle class="ponto-mapa" data-ativo="${esc(e.ativo)}" cx="${px(e.geo.lon).toFixed(1)}"
      cy="${py(e.geo.lat).toFixed(1)}" r="${r}" fill="${modo.cor[cat] || 'var(--sem-classe)'}">
      <title>${esc(e.ativo)} · ${esc(e.localidade)} · ${esc(cat)} · ${esc(e.criticidade)}${d != null ? ` — ${d} dias em aberto` : ''}</title>
    </circle>`;
  }).join('');

  const caminho = (pts) => 'M' + pts.map((p) => `${px(p[0]).toFixed(1)},${py(p[1]).toFixed(1)}`).join('L');
  const fronteira = (geo?.fronteira || [])
    .map((anel) => `<path d="${caminho(anel)}Z" fill="none" stroke="var(--tinta-2)" stroke-width="1.4"/>`)
    .join('');
  const estradas = (estado.mapaEstradas && geo?.estradas)
    ? geo.estradas.map((t) => `<path d="${caminho(t.pts)}" fill="none" stroke="var(--filete-2)" stroke-width="1"/>`).join('')
    : '';
  $('#alternar-estradas')?.setAttribute('aria-pressed', String(!!estado.mapaEstradas));

  caixa.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="max-width:${W}px;margin:0 auto" role="img"
    aria-label="Distribuição geográfica dos equipamentos indisponíveis">${grade.join('')}${estradas}${fronteira}${pontos}</svg>`;

  $('#legenda-mapa').innerHTML = modo.ordem
    .filter((c) => itens.some((e) => modo.rotulo(e) === c))
    .map((c) => `<div><i style="background:${modo.cor[c]}"></i>${esc(c)}
      <b>${itens.filter((e) => modo.rotulo(e) === c).length}</b></div>`).join('');

  $$('#mapa .ponto-mapa').forEach((el) => {
    el.addEventListener('click', () => abrirAtivo(el.dataset.ativo));
  });
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

    <h3>Primeiro ataque e a ausência de parecer</h3>
    <p>Regra do gestor (13/08): demanda parada no <strong>DMSL</strong> pode ainda estar no
    <strong>primeiro ataque</strong> — o diagnóstico em campo, antes de qualquer compra. É por isso
    que esses ativos costumam não ter parecer COEP na planilha de criticidade: a demanda ainda não
    chegou ao posto de compra. Falta de parecer não é falta de tratamento.</p>

    <h3>Quando a palavra do gestor entra na conta</h3>
    <p>O SGM nem sempre registra o que já aconteceu em campo — SS de execução que ninguém baixa,
    repasse para a Proteção que não sai. Quando o gestor confirma o que houve, isso vale como fonte
    nos dois sentidos: <em>executado</em> conta o ativo como resolvido mesmo sem registro, e
    <em>pendente</em> tira o ativo da conta mesmo quando as réguas automáticas o dariam por
    resolvido. Cada decisão fica gravada em <code>data/raw/decisoes_gestor.json</code> com data e
    motivo, aparece na ficha do ativo e numa seção própria da coleção Carteira de entrada — o
    número não vira palpite, e dá para auditar depois.</p>

    <h3>Hierarquia de fontes</h3>
    <p>Definida pelo gestor em 12/08: o <strong>último Parecer COEP</strong> vale o que está na
    planilha de criticidade (a coluna é mantida atualizada); a <strong>SS aberta atual</strong> de
    cada ativo vale o que está na base de SS/OS do SGM — a coluna de SS da planilha pode estar
    defasada. A ficha de cada ativo mostra as duas lado a lado, e as cadeias de demanda usam
    sempre a base de SS/OS.</p>

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
      <li>A aba Planilha1 da Gestão de Equipamentos guarda, abaixo de uma linha em branco, um
      segundo bloco sem cabeçalho (pares de ativos e material de compra) cujas colunas não
      correspondem ao cabeçalho de cima. Esse bloco é <strong>ignorado na leitura</strong> —
      lido como se fosse a tabela principal, punha o número de outro ativo no campo
      «SS no SGM» de 65 fichas (defeito corrigido em 12/08).</li>
    </ul></div>`;
}

/* ---------------- tema e início ---------------- */

/* O padrão é o modo claro, por decisão do gestor — o papel é a cara do
   prontuário. O botão de tema segue funcionando e a escolha fica guardada. */
document.documentElement.dataset.tema = localStorage.getItem('tema-equip') || 'claro';

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
