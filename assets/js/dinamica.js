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

const MES_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const rotuloMes = (m) => `${MES_PT[+m.split('-')[1] - 1]}/${m.split('-')[0]}`;
const dataBr = (iso) => { const [a, m, d] = String(iso).split('-'); return d ? `${d}/${m}/${a}` : iso; };

/* Barras agrupadas — três séries por mês. As cores saem de --serie-1/2/3, que
   passaram pelo validador de paleta nos dois temas. Cada barra leva o valor
   escrito em cima, então a identidade nunca depende só da cor. */
function barrasTresColunas(curva, series) {
  const SERIES = series || [
    { chave: 'entrantes', nome: 'Entrantes', cor: 'var(--serie-1)',
      dica: 'a carteira herdada, pela abertura da SS — janeiro carrega o acervo' },
    { chave: 'resolvidos', nome: 'Resolvidos', cor: 'var(--serie-3)',
      dica: 'pelo mês da tratativa ou do repasse' },
  ];
  const teto = Math.max(...curva.flatMap((m) => SERIES.map((s) => m[s.chave])), 1);
  const L = 44, R = 12, T = 22, B = 44;
  const larguraGrupo = 96, alturaPlot = 210;
  const W = L + R + larguraGrupo * curva.length;
  const H = T + alturaPlot + B;
  const larguraBarra = 24, vao = 2;
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
                    height="${alt.toFixed(1)}" rx="4" ry="4" fill="${s.cor}"/>
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
function linhaAcumulada(curva, series, legenda) {
  const SERIES = series || [
    { chave: 'entrantes', nome: 'Entrantes', cor: 'var(--serie-1)' },
    { chave: 'resolvidos', nome: 'Resolvidos', cor: 'var(--serie-3)' },
  ];
  const soma = {};
  SERIES.forEach((s) => { soma[s.chave] = 0; });
  const ac = curva.map((m) => {
    SERIES.forEach((s) => {
      // série de estoque (a fila) já vem no nível do mês — não se acumula
      soma[s.chave] = s.estoque ? (m[s.chave] || 0) : soma[s.chave] + (m[s.chave] || 0);
    });
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
        <b>${esc(s.nome)}</b> <em>${esc(s.dica_acum || legenda || 'somando mês a mês')}</em></span>`).join('')}
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
    <figcaption>O número no fim de cada linha é onde ela chegou no último mês do gráfico —
    agosto vai só até o dia 18.
    Passe o mouse num ponto para ver o acumulado daquele mês.</figcaption>
  </figure>`;
}

/* O mês a mês do posto: a mesma sequência da planilha entregue ao gestor. */
function mesAMes() {
  const mm = D.mes_a_mes;
  if (!mm || !mm.curva?.length) return '';
  const c = mm.curva;
  const tot = (k) => c.reduce((n, x) => n + x[k], 0);
  const jan = c.find((x) => x.mes === '2026-01')?.ativos || 0;
  const janProprio = jan - mm.legado.qtd;
  const s26 = mm.serie_coep || [];
  const tot26 = (k) => s26.reduce((n, x) => n + x[k], 0);
  const t = mm.tratativas || [];
  const tj = t.filter((x) => x.mes_resolucao <= '2026-07');
  const meses = [...new Set(tj.map((x) => x.mes_resolucao))].sort();
  const conta = (lista, f) => lista.filter(f).length;
  const pct = (v, base) => `${(100 * v / (base || 1)).toFixed(1).replace('.', ',')}%`;

  const cp = D.coep_2026 || {};
  const cc = cp.curva || [];
  const totCp = (k) => cc.reduce((n, x) => n + x[k], 0);
  return `<section class="bloco"><h3>Entrada e saída do posto em 2026</h3>
    <p class="destaque-texto">A linha azul é quem <b>chegou ao posto</b> no mês — equipamento
    apontado pela cadeia de repasse, pela primeira vez em 2026. A verde é quem o posto
    <b>resolveu</b>, pelo mês em que a demanda fechou. O ano abriu com <b>${cp.herdados || 0}</b>
    já na mesa, vindos de anos anteriores — esses não aparecem na curva de chegada. Agosto é mês
    parcial: vai até 18/08 na base de ocorrência.</p>
    ${barrasTresColunas(cc, SERIE_COEP)}
    <h4 class="sub-grafico">Visão COEP</h4>
    <p class="destaque-texto">Onde cada série chegou até o fim de cada mês. Aqui o que conta é a
    distância entre as curvas: enquanto a azul sobe e a verde fica no chão, a fila está
    crescendo; quando a verde encosta na azul, o posto passou a dar conta do que entra.</p>
    ${linhaAcumulada(cc, [...SERIE_COEP,
      { chave: 'no_posto', nome: 'No posto', cor: 'var(--serie-2)', estoque: true,
        dica_acum: 'a fila no fim de cada mês — não é soma' }], 'somando mês a mês')}
    <div class="nota branda"><strong>Por que 101 − 71 não dá a fila.</strong> A curva azul só
    conta quem <b>chegou em 2026</b> — o ano abriu com <b>${cp.herdados || 0}</b> já na mesa,
    que não estão nela. E «resolvido» é a demanda fechando em qualquer posto — parte fechou
    depois de sair daqui. A conta que fecha, equipamento a equipamento: <b>143 passaram =
    71 resolvidos + 50 esperando no posto + 22 repassados e pendentes em outra mesa</b>
    (4 dos resolvidos têm outra nota antiga ainda aberta no posto — por isso a linha laranja
    termina em 54). O livro-caixa herdado fecha em 52 porque é outro recorte: só a foto de
    entrada.</div>
    ${mm.saldo?.length ? `<h4 class="sub-grafico">A carteira em movimento</h4>
    <p class="destaque-texto">O livro-caixa da carteira herdada: começa com o acervo de
    ${mm.abertura} SS de anos anteriores, cada mês soma o que abriu no próprio mês e desconta o
    que foi tratado. Janeiro: ${mm.abertura} + ${mm.saldo[0].entram} − ${mm.saldo[0].saem} =
    ${mm.saldo[0].final}, e fevereiro já começa com ${mm.saldo[0].final}.</p>
    ${livroCaixa(mm)}` : ''}
    <div class="tabela-rol" style="margin-top:18px"><table class="matriz livro"><thead><tr><th>Mês</th>
    <th class="num">Chegaram ao posto</th><th class="num">Resolvidos</th></tr></thead><tbody>
    ${cc.map((x) => `<tr><td>${esc(x.rotulo)}</td>
      <td class="num">${x.chegaram || '—'}</td>
      <td class="num">${x.resolvidos || '—'}</td></tr>`).join('')}
    </tbody><tfoot><tr><td>Total até 18/08</td>
    <td class="num"><b>${totCp('chegaram')}</b></td><td class="num"><b>${totCp('resolvidos')}</b></td>
    </tr></tfoot></table></div>
    <div class="nota branda"><strong>O livro-caixa abaixo é outro recorte.</strong> Ele acompanha
    só a carteira herdada da foto de entrada — ${mm.total} SS, ${mm.ss_resolvidas || 0} resolvidas
    na régua da tratativa. Os gráficos acima contam a base inteira pela cadeia da demanda; a
    ponte entre as duas contas, ativo a ativo, está no bloco do posto, mais abaixo.</div>
    ${mm.fora_do_recorte?.qtd ? `<div class="nota branda" style="margin-top:12px"><strong>O que ficou fora do recorte</strong>
    Concluído conta de qualquer tipo; pendente, só se for indisponibilidade. Da foto de entrada
    fica fora ${mm.fora_do_recorte.qtd === 1 ? 'um ativo' : `${mm.fora_do_recorte.qtd} ativos`} de outro
    tipo ainda pendente: ${mm.fora_do_recorte.por_tipo.map(([t, q]) => `${q} ${esc(t.toLowerCase())}`).join(' · ')}.
    Segue na carteira de entrada.</div>` : ''}
  </section>

  <section class="bloco"><h3>O que janeiro carrega</h3>
    <p class="destaque-texto">Janeiro é metade da carteira e é quase tudo acervo: dos ${jan} ativos,
    só ${janProprio} têm SS aberta no próprio mês. Sem a regra, esses ${mm.legado.qtd} ficariam
    espalhados por 2023, 2024 e 2025 e a curva de 2026 perderia o tamanho do que foi herdado.</p>
    <div class="tabela-rol"><table class="matriz"><thead><tr><th>Origem</th>
    <th class="num">Ativos</th><th class="num">% de janeiro</th></tr></thead><tbody>
    <tr><td>SS aberta em jan/2026</td><td class="num">${janProprio}</td>
      <td class="num">${pct(janProprio, jan)}</td></tr>
    ${[...mm.legado.por_ano].reverse().map((a) => `<tr><td>Acervo — SS aberta em ${a.ano}</td>
      <td class="num">${a.qtd}</td><td class="num">${pct(a.qtd, jan)}</td></tr>`).join('')}
    </tbody><tfoot><tr><td>Total de janeiro</td><td class="num"><b>${jan}</b></td>
    <td class="num"><b>100,0%</b></td></tr></tfoot></table></div>
    ${mm.legado.mais_antiga ? `<div class="nota branda" style="margin-top:12px">
    <strong>A mais velha da carteira</strong>${esc(mm.legado.mais_antiga.numero_ss)}, ativo
    ${esc(mm.legado.mais_antiga.ativo)} em ${esc(mm.legado.mais_antiga.localidade)}, aberta em
    ${esc(dataBr(mm.legado.mais_antiga.abertura))}.</div>` : ''}
  </section>

  

  ${meses.length ? `<section class="bloco"><h3>Quando cada um foi tratado de verdade</h3>
    <p class="destaque-texto">Mês da tratativa, não da abertura. A data é o término da SS de entrada;
    quando a SS foi repassada em vez de encerrada, vale a data do repasse. Faltando as duas, entram
    obra encerrada no AIC, reporte de campo, decisão do gestor e, por último, a SS mais recente
    atendida no ativo.</p>
    <div class="tabela-rol"><table class="matriz"><thead><tr><th>Mês da tratativa</th>
    <th class="num">Resolvidos</th><th class="num">Acumulado</th>
    <th class="num">Por cancelamento da SS</th><th class="num">Por repasse</th>
    <th class="num">Outras vias</th><th class="num">Com parecer COEP</th></tr></thead><tbody>
    ${(() => { let ac = 0; return meses.map((k) => {
      const g = t.filter((x) => x.mes_resolucao === k);
      ac += g.length;
      const canc = conta(g, (x) => x.via === 'cancelamento da SS de entrada');
      const rep = conta(g, (x) => x.via === 'repasse para a etapa seguinte');
      return `<tr><td>${rotuloMes(k)}</td><td class="num"><b>${g.length}</b></td>
        <td class="num">${ac}</td><td class="num">${canc || '—'}</td><td class="num">${rep || '—'}</td>
        <td class="num">${(g.length - canc - rep) || '—'}</td>
        <td class="num">${conta(g, (x) => x.parecer_coep) || '—'}</td></tr>`;
    }).join(''); })()}
    </tbody><tfoot><tr><td>Total até 18/08</td><td class="num"><b>${tj.length}</b></td><td class="num">—</td>
    <td class="num"><b>${conta(tj, (x) => x.via === 'cancelamento da SS de entrada')}</b></td>
    <td class="num"><b>${conta(tj, (x) => x.via === 'repasse para a etapa seguinte')}</b></td>
    <td class="num"><b>${conta(tj, (x) => !['cancelamento da SS de entrada', 'repasse para a etapa seguinte'].includes(x.via))}</b></td>
    <td class="num"><b>${conta(tj, (x) => x.parecer_coep)}</b></td></tr></tfoot></table></div>
    <div class="nota" style="margin-top:12px"><strong>O desenho da atuação</strong>
    ${conta(tj, (x) => x.mes_resolucao >= '2026-04')} dos ${tj.length} foram tratados de abril em diante.${t.length > tj.length ? ` Fora da janela, em agosto, mais ${t.length - tj.length}.` : ''}
    Maio e junho são limpeza de fila — a maioria saiu por cancelamento de SS. Julho vira o jogo: a
    maior parte sai por repasse, e é o mês em que quase todos os que tinham parecer COEP foram
    embora. Repasse quer dizer que a demanda saiu do posto, não que o serviço acabou em campo.</div>
  </section>` : ''}`;
}

/* As fotos que a equipe mandou, todas num lugar só. É a prova mais forte que
   existe: a equipe assinando que subiu no poste e trocou. */
function galeriaReportes() {
  const R = D.reportes;
  if (!R || !R.lista?.length) return '';
  const img = R.imagens || {};
  const comFoto = R.lista.filter((r) => r.imagem && img[r.imagem]);
  const anunciados = R.lista.filter((r) => !(r.imagem && img[r.imagem]) && r.anexo);
  const semAnexo = R.lista.filter((r) => !(r.imagem && img[r.imagem]) && !r.anexo);

  const cartao = (r) => {
    const foto = r.imagem && img[r.imagem];
    return `<figure class="reporte-galeria">
      ${foto ? `<a href="${foto}" target="_blank" rel="noopener">
        <img src="${foto}" loading="lazy"
          alt="Reporte de campo do ativo ${esc(r.ativo)} em ${esc(dataBr(r.data))}"></a>`
        : r.anexo
          ? `<div class="sem-foto"><b>${r.anexo.fotos} foto${r.anexo.fotos > 1 ? 's' : ''}</b>
            <span>${esc(r.anexo.estado)}</span></div>`
          : `<div class="sem-foto"><b>Sem foto</b><span>reporte só em texto</span></div>`}
      <figcaption>
        <div class="topo-galeria"><span class="cod">${esc(r.ativo)}</span>
          <span class="reporte-data">${esc(dataBr(r.data))}</span></div>
        <b>${esc(r.titulo)}</b>
        <span class="onde">${esc(r.local || r.subtitulo || '')}${r.equipe ? ` · ${esc(r.equipe)}` : ''}</span>
        ${r.etapa ? `<span class="feito">na carteira: ${esc(r.etapa)}</span>` : ''}
        ${r.servico_executado ? `<span class="feito">${esc(r.servico_executado)}</span>` : ''}
        ${r.equipamento_instalado ? `<span class="feito mono">${esc(r.equipamento_instalado)}</span>` : ''}
        ${!foto && r.anexo?.descricao ? `<span class="feito">${esc(r.anexo.descricao)}</span>` : ''}
      </figcaption>
    </figure>`;
  };

  return `<section class="bloco"><h3>As fotos de campo (${R.fotos})</h3>
    <p class="destaque-texto">Todas as fotos que a equipe mandou, num lugar só: ${R.fotos} em
    ${R.total} reportes, cobrindo ${R.ativos.length} equipamentos. Clique para abrir em tamanho
    cheio. O reporte é a equipe assinando que subiu no poste e trocou — nenhuma inferência sobre o
    texto da SS ganha disso, e é por isso que ele conta como resolução mesmo quando o SGM ainda não
    registrou nada.</p>
    <div class="galeria">${comFoto.map(cartao).join('')}</div>
    ${anunciados.length ? `<p class="destaque-texto" style="margin-top:24px">Anexo anunciado, arquivo
    ainda não veio — o que dá para ler nas fotos já está descrito aqui.</p>
    <div class="galeria">${anunciados.map(cartao).join('')}</div>` : ''}
    ${semAnexo.length ? `<p class="destaque-texto" style="margin-top:24px">Reportes só em texto.</p>
    <div class="galeria">${semAnexo.map(cartao).join('')}</div>` : ''}
  </section>`;
}

/* A escada mede os 129 de hoje pelo parecer; o livro mede os 117 herdados pelas
   réguas da entrada. A ponte cruza os dois, ativo a ativo, para a conta fechar
   dos dois lados. */
function ponte() {
  const p = D.ponte, mm = D.mes_a_mes;
  if (!p || !mm) return '';
  const concl = D.por_etapa.find((e) => e.etapa === 'Concluído')?.qtd ?? '—';
  return `<section class="bloco"><h3>Por que a escada não bate com o mês a mês — e como fecha</h3>
    <p class="destaque-texto">A escada conta os ${D.total} de HOJE pelo parecer mais recente; o mês
    a mês conta os ${mm.total} HERDADOS na foto de junho, pelas réguas da carteira de entrada. Nem
    o universo nem a régua são os mesmos — por isso «Concluído ${concl}» lá em cima não é o
    «${p.resolvidos} resolvidos» daqui de baixo. Ativo a ativo, a ponte fecha assim:</p>
    <div class="itens">
      <div class="item-linha"><span>Resolvidos do livro que já SAÍRAM da lista atual dos ${D.total}
        <i class="linha-nota">tratados e fora da relação de indisponíveis de hoje</i></span>
        <b>${p.fora_da_lista}</b></div>
      <div class="item-linha"><span>Resolvidos do livro que aparecem na escada com serviço feito
        <i class="linha-nota">${p.feito_por_etapa.map((x) => `${esc(x.etapa)} ${x.qtd}`).join(' · ')}</i></span>
        <b>${p.com_feito}</b></div>
      ${p.na_fila.length ? `<div class="item-linha"><span>Resolvidos pela régua da entrada, com a demanda atual ainda andando
        <i class="linha-nota">${p.na_fila.map((x) => `${esc(x.ativo)} — ${esc(x.etapa)}`).join(' · ')}. O repasse foi feito; a etapa seguinte corre.</i></span>
        <b>${p.na_fila.length}</b></div>` : ''}
      <div class="item-linha"><span><b>Soma — os resolvidos do livro</b></span><b>${p.resolvidos}</b></div>
    </div>
    <div class="itens" style="margin-top:16px">
      <div class="item-linha"><span>Serviço feito da escada que veio da foto de entrada</span><b>${p.feito_da_foto}</b></div>
      <div class="item-linha"><span>Serviço feito da escada em ativos que entraram DEPOIS da foto</span><b>${p.feito_novos}</b></div>
      <div class="item-linha"><span><b>Soma — o serviço feito da escada</b></span><b>${p.feito_escada}</b></div>
    </div>
    ${p.feito_foto_pendentes ? `<div class="nota branda" style="margin-top:12px"><strong>Os ${p.feito_foto_pendentes} que explicam o resto</strong>
    ${p.feito_da_foto} feitos da escada vieram da foto, mas só ${p.com_feito} estão nos ${p.resolvidos} resolvidos do livro.
    A diferença são ${p.feito_foto_pendentes} ativos em que o parecer atual dá o serviço como feito, mas ainda existe SS
    pendente da mesma demanda — e a régua da entrada, que é mais dura, não deixa baixar.</div>` : ''}
  </section>`;
}

// O posto em 2026 — quem passou pela mesa e o que o posto devolveu. A conta sai da
// cadeia da demanda, não da carteira: a carteira é a foto do que ainda está pendente
// e não guarda o que fechou e saiu, que é justamente o trabalho velho fechado agora.
const SERIE_COEP = [
  { chave: 'chegaram', nome: 'Chegaram ao posto', cor: 'var(--serie-1)',
    dica: 'equipamento que apareceu no COEP naquele mês, pela primeira vez em 2026' },
  { chave: 'resolvidos', nome: 'Resolvidos', cor: 'var(--serie-3)',
    dica: 'pelo mês em que a demanda fechou' },
];

function coepBloco() {
  const c = D.coep_2026;
  if (!c || !c.resolvidos) return '';
  const anos = Object.entries(c.por_ano || {}).sort((a, b) => a[0].localeCompare(b[0]));
  const antigos = anos.filter(([a]) => a < '2026').reduce((n, [, v]) => n + v, 0);
  const prova = Object.entries(c.por_prova || {}).sort((a, b) => b[1] - a[1]);
  const espera = (c.espera_dos_pendentes || []).filter((f) => f.qtd);
  const travando = (c.parecer_dos_pendentes || [])[0];
  const pt = c.ponte_com_o_livro;
  return `<section class="bloco"><h3>O posto do COEP em 2026 — o que entrou e o que saiu</h3>
    <p class="destaque-texto">As duas contas são de <b>equipamento</b>, não de SS: o mesmo
    religador com três SS no posto no mesmo ano é um equipamento. Quem passou pelo posto é quem
    esteve lá em algum momento do ano, não só quem chegou nele.</p>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr>
    <th>O que está sendo contado</th><th class="num">Equipamentos</th></tr></thead><tbody>
    <tr><td>Passaram pela mesa do posto</td><td class="num"><b>${c.passaram}</b></td></tr>
    <tr><td class="recuo">dos quais na carteira consolidada</td><td class="num">${c.na_carteira}</td></tr>
    <tr><td class="recuo">dos quais fora dela</td><td class="num">${c.fora_da_carteira}</td></tr>
    <tr><td>O posto resolveu</td><td class="num"><b>${c.resolvidos}</b></td></tr>
    <tr><td>Seguem no posto em 18/08</td><td class="num"><b>${c.pendentes}</b></td></tr>
    </tbody></table></div>
    <div class="nota branda"><strong>Resolvido é a demanda que fechou.</strong> Passou pelo posto
    dentro de 2026 e a cadeia dela terminou dentro de 2026, com SS atendida ou cancelada. Régua do
    gestor para o cancelamento: cancelado é resolvido, desde que não tenham aberto outra nota para
    aquele ativo no posto do COEP depois — quem voltou não conta, e foram
    <b>${c.tirados_por_volta}</b> assim. Quem fecha não precisa ser o COEP: o posto diagnostica e
    despacha, a ponta executa.</div>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr>
    <th>Ano em que a demanda nasceu</th><th class="num">Resolvidos em 2026</th>
    <th class="num">Do total</th></tr></thead><tbody>
    ${anos.map(([a, v]) => `<tr><td>${a}${a === '2026' ? ' <i>(até 18/08)</i>' : ''}</td>
      <td class="num"><b>${v}</b></td>
      <td class="num">${Math.round(100 * v / c.resolvidos)}%</td></tr>`).join('')}
    <tr class="total"><td><b>Total</b></td><td class="num"><b>${c.resolvidos}</b></td>
      <td class="num">100%</td></tr></tbody></table></div>
    <div class="nota"><strong>${antigos} dos ${c.resolvidos} são dívida velha.</strong> Nasceram
    antes de 2026 e só foram fechados agora. É por isso que «${c.resolvidos} resolvidos» e
    «43 falharam» não se contradizem: um mede a produção do posto, o outro mede a saúde do
    parque.</div>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Como foi resolvido</th>
    <th class="num">Equipamentos</th></tr></thead><tbody>
    ${prova.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num"><b>${v}</b></td></tr>`).join('')}
    </tbody></table></div>
    <div class="nota branda"><strong>O que fica para conferir.</strong>
    ${c.no_lote_de_junho} dos ${c.resolvidos} foram cancelados no lote de 29 e 30 de junho — pela
    régua contam, mas o lote está marcado na base. E ${c.com_pendencia_fora} seguem com nota
    pendente em outro posto: o COEP fechou a parte dele, o equipamento ainda tem pendência em
    outra mesa.</div>
    <h4 class="sub-grafico">Os ${c.pendentes} que seguem no posto</h4>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Há quanto tempo esperam</th>
    <th class="num">Equipamentos</th></tr></thead><tbody>
    ${espera.map((f) => `<tr><td>${esc(f.faixa)}</td>
      <td class="num"><b>${f.qtd}</b></td></tr>`).join('')}
    </tbody></table></div>
    ${travando ? `<div class="nota"><strong>Não é fila de diagnóstico, é fila de peça.</strong>
    ${travando.qtd} dos ${c.pendentes} estão com o parecer «${esc(travando.parecer)}». O mais
    antigo espera há ${c.mais_antigo} dias.</div>` : ''}
    ${pt ? `<h4 class="sub-grafico">Por que aqui dá ${pt.conta} e no livro-caixa dá ${pt.livro}</h4>
    <p class="destaque-texto">São universos diferentes, e os dois estão certos. O livro conta os
    ${D.mes_a_mes?.total ?? ''} da foto de entrada, mês a mês pela abertura da SS. Esta conta varre
    a base inteira pela cadeia da demanda. Ativo a ativo, fecha assim:</p>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Cruzamento</th>
    <th class="num">Equipamentos</th></tr></thead><tbody>
    <tr><td>Nos dois — o livro e esta conta concordam</td><td class="num"><b>${pt.nos_dois}</b></td></tr>
    <tr><td>Só no livro: a demanda não fechou na base de SS dentro de 2026</td>
      <td class="num">${pt.so_no_livro_sem_fechamento}</td></tr>
    <tr><td>Só no livro: fechou, mas o ativo voltou para o COEP depois</td>
      <td class="num">${pt.so_no_livro_voltou}</td></tr>
    <tr><td>Só nesta conta: nunca esteve na foto de entrada</td>
      <td class="num">${pt.so_na_conta_fora_da_foto}</td></tr>
    <tr><td>Só nesta conta: está na foto, mas o livro não o deu por resolvido</td>
      <td class="num">${pt.so_na_conta_na_foto}</td></tr>
    </tbody></table></div>` : ''}
  </section>`;
}

function taxaFalha() {
  const t = D.taxa_falha;
  if (!t || !t.linhas?.length) return '';
  const ANOS = ['2024', '2025', '2026'];
  const ROT = { religador: 'Religadores', regulador: 'Reguladores' };
  const res = t.resolvidos || {};
  const dem = res.demandas_de_falha_encerradas || {};
  const campo = res.obra_de_substituicao_concluida_em_campo || {};
  const contab = res.obra_de_substituicao_encerrada_no_contabil || {};
  const somaAno = (m, a) => Object.values(m[a] || {}).reduce((n, v) => n + v, 0);
  const proj26 = Math.round(somaAno(dem, '2026') / 0.6274);

  const pct = (v) => (v != null ? String(v).replace('.', ',') + '%' : '—');
  const tabelaFam = (l) => `<h4 class="sub-grafico">${ROT[l.familia]}</h4>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Ano</th>
    <th class="num">Parque</th><th class="num">Ocorrências</th>
    <th class="num">Total que falharam</th><th class="num">Taxa</th></tr></thead><tbody>
    ${ANOS.map((a) => { const x = l.anos[a]; return `<tr><td>${a}${a === '2026' ? ' <i>(até 18/08)</i>' : ''}</td>
      <td class="num">${x.parque ?? '—'}</td><td class="num">${x.ocorrencias || '—'}</td>
      <td class="num"><b>${x.falhas || '—'}</b></td>
      <td class="num"><b>${pct(x.taxa)}</b></td></tr>`; }).join('')}
    ${l.anos.trienio ? `<tr class="total"><td><b>Triênio</b></td>
      <td class="num">${l.anos.trienio.parque}</td><td class="num">—</td>
      <td class="num"><b>${l.anos.trienio.falhas}</b></td>
      <td class="num"><b>${pct(l.anos.trienio.taxa)}</b></td></tr>` : ''}
    </tbody></table></div>`;

  return `<section class="bloco"><h3>Taxa de falha do parque</h3>
    <p class="destaque-texto">Falha aqui é só o que exigiu <b>peça grande</b>. No religador:
    controle (a placa de alimentação CA e o relé de sincronismo são controle), tanque ou o
    equipamento completo. No regulador: célula, relé, o banco completo ou furto. Trafo auxiliar,
    chave faca, rádio, antena, bateria e aterramento ficam fora da taxa. O parque é o de cada
    ano, informado pelo gestor: 1.307 religadores e 207 reguladores. 2026 vai até 18/08,
    sem anualizar.</p>
    ${t.leitura_em_andamento ? `<div class="nota branda"><strong>Leitura em andamento</strong>
    Agentes estão lendo o texto completo das 1.087 SS e OS dos 129 ativos da carteira, com um
    time revisor conferindo cada falha apontada. A linha «Falhas» abaixo é a prévia pelo que já
    está documentado — troca executada em obra encerrada mais peça grande registrada na fila.
    Pode haver pequena sobreposição entre as duas parcelas; a leitura revisada substitui esta
    prévia.</div>` : ''}
    ${t.linhas.map(tabelaFam).join('')}

    <h4 class="sub-grafico">O contraponto: as três medidas da ETO inteira</h4>
    <p class="destaque-texto">Três medidas que contam coisas diferentes. <b>Demandas encerradas</b>
    é a SS de falha que terminou (atendida ou cancelada) — a única comparável entre anos.
    <b>Obra concluída em campo</b> é o serviço feito. <b>Obra encerrada no contábil</b> vem sempre
    atrasada: as obras de 2026 ainda não fecharam no sistema, por isso o número é baixo — é
    atraso de papel, não queda de produção.</p>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Ano</th>
    <th class="num">Demandas de falha encerradas</th><th class="num">Obra concluída em campo</th>
    <th class="num">Obra encerrada no contábil</th></tr></thead><tbody>
    ${ANOS.map((a) => `<tr><td>${a}${a === '2026' ? ' <i>(até 18/08)</i>' : ''}</td>
      <td class="num"><b>${somaAno(dem, a) || '—'}</b> <i>(${(dem[a] || {}).religador || 0} RL · ${(dem[a] || {}).regulador || 0} RT)</i></td>
      <td class="num">${somaAno(campo, a) || '—'}</td>
      <td class="num">${somaAno(contab, a) || '—'}</td></tr>`).join('')}
    </tbody></table></div>
    <div class="nota" style="margin-top:12px"><strong>2026 está no ritmo mais alto já registrado</strong>
    São ${somaAno(dem, '2026')} demandas de falha encerradas em 63% do ano. Mantido o ritmo, o ano
    fecha em torno de ${proj26} — empata com 2025 (${somaAno(dem, '2025')}) e fica bem acima de
    2024 (${somaAno(dem, '2024')}). A impressão do gestor de que 2026 é o ano que mais resolveu
    se confirma no ritmo, com 2025 ainda à frente no volume fechado.</div>

    ${t.premissas?.length ? `<h4 class="sub-grafico">Como foi feito — as premissas</h4>
    <div class="premissas-taxa">${t.premissas.map((p, i) => `<div class="nota branda">
      <strong>${i + 1}.</strong> ${esc(p)}</div>`).join('')}</div>` : ''}
  </section>`;
}

function escada() {
  const maior = Math.max(...D.por_etapa.map((e) => e.qtd));
  return `<div class="escada">${D.por_etapa.map((e) => `
    <button class="degrau ${TOM[e.etapa] || ''}" data-etapa="${esc(e.etapa)}">
      <span class="nome">${esc(e.etapa)}</span>
      <span class="barra"><i style="width:${(100 * e.qtd / maior).toFixed(1)}%"></i></span>
      <span class="lado"><b>${e.qtd}</b>${e.valor ? esc(rs(e.valor))
        : e.valor_evitado ? `<i class="evitado">${esc(rs(e.valor_evitado))} evitados</i>` : '—'}${
        e.realizado_aic ? `<i class="evitado">${esc(rs(e.realizado_aic))} realizados no AIC</i>` : ''}</span>
    </button>`).join('')}</div>
    <p class="destaque-texto" style="margin-top:10px">Clique numa etapa para filtrar a lista.
    O valor preto é o previsto na planilha de gestão — ${D.com_valor} dos ${D.total} têm valor
    lá. O verde é outra régua: o que a obra <b>já pagou</b>, pela conclusão no AIC.</p>
    ${D.realizado_aic ? `<div class="nota branda"><strong>Previsto não é realizado.</strong>
    No «Concluído» a planilha prevê ${rs(D.por_etapa.find((e) => e.etapa === 'Concluído')?.valor || 0)},
    mas o AIC já registra ${rs(D.realizado_aic.por_etapa['Concluído'] || 0)} de obra concluída
    nesses ativos — e mais ${rs(D.realizado_aic.expansao_fora)} numa obra de expansão ligada ao
    ${D.realizado_aic.expansao_ativo}, que é obra de cliente e fica fora da conta de manutenção.
    Somando o executado nos ativos de comissionamento e ajustes, o campo já pagou
    ${rs(Object.values(D.realizado_aic.por_etapa).reduce((a, b) => a + b, 0))}. O painel de Capex
    do gestor marca <b>R$ 1.573.958,37</b> realizados até agosto — mesma ordem de grandeza:
    manutenção mais a expansão dão R$ 1,51 mi no AIC, e o resto é defasagem de lançamento.</div>` : ''}`;
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
        ${x.reporte_campo ? `<span class="reporte-selo">reporte de campo entregue${x.reporte_campo.fotos ? ` · ${x.reporte_campo.fotos} foto${x.reporte_campo.fotos > 1 ? 's' : ''}` : ''}</span>` : ''}
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

    ${ponte()}

    ${mesAMes()}

    ${coepBloco()}

    ${D.economia ? `<section class="bloco"><h3>O que teria sido gasto nos cancelados em operação</h3>
      <p class="destaque-texto">${esc(D.economia.criterio)}</p>
      <div class="numeros">
        ${num({ rotulo: 'O que teria sido gasto', valor: rs(D.economia.total), nota: `${D.economia.total_ativos} equipamentos, material + mão de obra`, tom: 'evitado' })}
        ${num({ rotulo: 'Material de catálogo', valor: rs(D.economia.material), nota: `mão de obra de campo: ${rs(D.economia.mao_de_obra)}` })}
        ${num({ rotulo: 'Com peça identificada', valor: D.economia.com_material, nota: `${D.economia.sem_material} não precisavam de peça · ${D.economia.indeterminados} sem laudo que decida` })}
        ${D.economia.orcado ? num({ rotulo: 'Ainda dentro do orçamento', valor: rs(D.economia.orcado.liberavel), nota: `${D.economia.orcado.com_custo} cancelados com custo lançado — dinheiro a liberar`, tom: 'evitado' }) : ''}
      </div>
      ${(D.economia.decisoes || []).length ? `<div class="decisoes">
      ${D.economia.decisoes.map((x) => `<div class="nota branda"><strong>${esc(x.titulo)}</strong>${esc(x.texto)}</div>`).join('')}
      </div>` : ''}
      <div class="tabela-rol"><table class="matriz economia"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th>Criticidade</th><th>Tensão</th><th>Peça que teria sido comprada</th>
      <th class="num">Material</th><th class="num">Mão de obra</th><th class="num">Total</th>
      <th>Fonte do valor</th></tr></thead><tbody>
      ${D.economia.lista.map((x) => `<tr class="cabeca">
        <td><b class="mono">${esc(x.ativo)}</b></td><td>${esc(x.localidade || '—')}</td>
        <td>${esc(x.criticidade || '—')}</td>
        <td>${esc(x.classe_tensao || '—')}${x.kva ? `<br>${x.kva} kVA` : ''}</td>
        <td>${x.linhas.length ? x.linhas.map((l) => `${esc(l.descricao)}${l.qtd > 1 ? ` × ${l.qtd}` : ''} <span class="mono">${esc(l.codigo)}</span>`).join('<br>')
          : `<i>${x.veredito === 'sem_material' ? 'não precisava de peça' : 'o laudo não permite dizer'}</i>`}</td>
        <td class="num">${x.material ? esc(rs(x.material)) : '—'}</td>
        <td class="num">${x.mao_de_obra ? esc(rs(x.mao_de_obra)) : '—'}</td>
        <td class="num">${x.valor ? `<i class="evitado"><b>${esc(rs(x.valor))}</b></i>` : '—'}</td>
        <td>${esc(x.fonte)}${x.no_orcamento ? `<br><i>aba «${esc(x.no_orcamento)}»</i>` : ''}</td></tr>
        ${x.nota ? `<tr class="rodape-linha"><td colspan="9">${esc(x.nota)}</td></tr>` : ''}`).join('')}
      </tbody><tfoot><tr><td colspan="5">Total</td>
      <td class="num"><b>${esc(rs(D.economia.material))}</b></td>
      <td class="num"><b>${esc(rs(D.economia.mao_de_obra))}</b></td>
      <td class="num"><i class="evitado"><b>${esc(rs(D.economia.total))}</b></i></td>
      <td></td></tr></tfoot></table></div>

      ${D.economia.orcado ? `<div class="nota" style="margin-top:16px"><strong>Você tinha razão: parte dos cancelados ainda está orçada</strong>
      ${D.economia.orcado.citados} dos ${D.economia.total_ativos} aparecem no ORCAMENTO_EQ_ESPECIAIS revisado.
      ${D.economia.orcado.com_custo} deles estão nas abas que somam no orçamento, com
      ${esc(rs(D.economia.orcado.liberavel))} de custo lançado para equipamento que já está rodando.
      Esse é o valor que dá para liberar da fila de compra sem mexer em mais nada. Os outros
      ${D.economia.orcado.citados - D.economia.orcado.com_custo} estão em «Repassados» e «Em Análise», que já ficam fora da conta.</div>
      <div class="tabela-rol" style="margin-top:10px"><table class="matriz"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th>SS</th><th>Aba do orçamento</th><th class="num">Valor lançado</th></tr></thead><tbody>
      ${D.economia.orcado.ativos.map((l) => `<tr><td><b class="mono">${esc(l.ativo)}</b></td>
        <td>${esc(l.localidade)}</td><td class="mono">${esc(l.ss)}</td><td>${esc(l.aba)}</td>
        <td class="num">${l.soma ? `<i class="evitado">${esc(rs(l.valor))}</i>` : '<i>fora do total</i>'}</td></tr>`).join('')}
      </tbody><tfoot><tr><td colspan="4">A liberar da fila de compra</td>
      <td class="num"><i class="evitado"><b>${esc(rs(D.economia.orcado.liberavel))}</b></i></td></tr></tfoot></table></div>` : ''}

      ${D.economia.teto ? `<div class="nota" style="margin-top:16px"><strong>O teto, se os ${D.economia.teto.ativos} indeterminados se confirmarem</strong>
      Estes não têm laudo que nomeie a peça e ficam em R$ 0 no número oficial, por instrução de errar para baixo.
      Se os três laudos vierem como o texto sugere, entram mais ${esc(rs(D.economia.teto.extra))} e o total vai a
      ${esc(rs(D.economia.teto.valor))}.</div>
      <div class="tabela-rol" style="margin-top:10px"><table class="matriz"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th>Peça provável</th><th>O que falta para decidir</th><th class="num">Valor em aberto</th></tr></thead><tbody>
      ${D.economia.teto.linhas.map((l) => `<tr><td><b class="mono">${esc(l.ativo)}</b></td>
        <td>${esc(l.localidade)}</td><td>${esc(l.peca)}</td>
        <td>${esc(l.porque)}</td><td class="num"><i class="evitado">${esc(rs(l.valor))}</i></td></tr>`).join('')}
      </tbody><tfoot><tr><td colspan="4">Total em aberto</td>
      <td class="num"><i class="evitado"><b>${esc(rs(D.economia.teto.extra))}</b></i></td></tr></tfoot></table></div>` : ''}
    </section>` : ''}

    <section class="bloco"><h3>Etapa × criticidade</h3>
      <p class="destaque-texto">Onde está o risco: quantos de cada criticidade em cada etapa.</p>
      ${matriz()}</section>

    ${galeriaReportes()}

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
