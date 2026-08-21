"""
Página própria da taxa de falha — dist/taxa-falha.html.

A pedido do gestor (21/08): a visão da taxa de falha sai da dinâmica do posto e
vira uma página separada, como uma aba própria, no mesmo tema Prontuário
Industrial. Página estática: os números vêm prontos de data/missao/taxa_falha.json
e, quando existir, de data/missao/leitura_ss_os.json (a leitura das SS e OS pelos
agentes, revisada) — que substitui a prévia por evidência direta.

Rodar: python3 scripts/build_taxa_falha.py
"""

import html
import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ_TAXA = os.path.join(RAIZ, "data", "missao", "taxa_falha.json")
ARQ_LEITURA = os.path.join(RAIZ, "data", "missao", "leitura_ss_os.json")
DESTINO = os.path.join(RAIZ, "dist", "taxa-falha.html")

ANOS = ("2024", "2025", "2026")
ROT = {"religador": "Religadores", "regulador": "Reguladores"}
FATOR = {"2024": 1.0, "2025": 1.0, "2026": 1.0}  # divisão direta, sem anualizar


def esc(t):
    return html.escape(str(t if t is not None else ""))


def _ler(caminho):
    if not os.path.exists(caminho):
        return None
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def _pct(v):
    return f"{v:.1f}".replace(".", ",") + "%" if v is not None else "—"


def tabela_familia(fam, ppa, leitura, regua, aic):
    """Tabela da família: parque do ano, quem falhou e a taxa.

    Com a leitura pronta, o numerador é EQUIPAMENTO que falhou no ano (fórmula do
    gestor): os achados na carteira lida mais as trocas por obra direta que nunca
    passaram pela carteira. Sem leitura, vale a prévia por evidência direta.
    """
    linhas = []
    tot_n = tot_oc = tot_eq = 0
    for ano in ANOS:
        p = (ppa.get(fam) or {}).get(ano, {})
        medio = p.get("medio") or 0
        eq = medio * FATOR[ano]
        if leitura:
            carteira = (leitura.get("contagem") or {}).get(f"{fam}|{ano}", 0)
            obra = (leitura.get("complemento_obra_direta") or {}).get(f"{fam}|{ano}", 0)
            n = (leitura.get("total_equipamentos_que_falharam") or {}).get(f"{fam}|{ano}",
                                                                          carteira + obra)
            # cada troca por obra direta é uma ocorrência; as da carteira vêm da leitura
            oc = ((leitura.get("ocorrencias") or {}).get(f"{fam}|{ano}", 0)) + obra
        else:
            evid = (regua.get(fam) or {}).get(ano, {}).get("com_peca_grande") or 0
            troca = (aic.get(ano) or {}).get(fam, 0)
            n = evid + troca
            oc = n
        tot_n += n
        tot_oc += oc
        tot_eq += eq
        taxa = 100.0 * n / eq if eq else None
        rot_ano = f'{ano}{" <i>(até 12/08)</i>" if ano == "2026" else ""}'
        linhas.append(
            f'<tr><td>{rot_ano}</td>'
            f'<td class="num">{medio or "—"}</td>'
            f'<td class="num">{oc or "—"}</td>'
            f'<td class="num"><b>{n or "—"}</b></td>'
            f'<td class="num"><b>{_pct(taxa)}</b></td></tr>'
        )
    # Total pela regra do gestor: o total que falharam dividido pelo tamanho do parque
    parque = ((ppa.get(fam) or {}).get("2026") or {}).get("medio") or 0
    taxa_total = 100.0 * tot_n / parque if parque else None
    n26 = 0
    if leitura:
        n26 = (leitura.get("total_equipamentos_que_falharam") or {}).get(f"{fam}|2026", 0)
    ritmo26 = 100.0 * (n26 / 0.611) / parque if parque and n26 else None
    rodape_total = (f'<tr><td><b>Total</b></td><td class="num">—</td>'
                    f'<td class="num"><b>{tot_oc}</b></td>'
                    f'<td class="num"><b>{tot_n}</b></td>'
                    f'<td class="num"><b>{_pct(taxa_total)}</b></td></tr>')
    if leitura:
        comp = " · ".join(
            f'{a}: {(leitura.get("contagem") or {}).get(f"{fam}|{a}", 0)} na carteira lida '
            f'+ {(leitura.get("complemento_obra_direta") or {}).get(f"{fam}|{a}", 0)} por obra direta'
            for a in ANOS)
        ritmo_txt = (f' 2026 vai até 12/08; mantido o ritmo, fecharia em torno de '
                     f'{_pct(ritmo26)}.' if ritmo26 else '')
        rodape = (f'<p class="destaque-texto" style="margin-top:6px"><i>De onde vêm: '
                  f'{comp}. O total divide os que falharam nos três anos pelo parque.'
                  f'{ritmo_txt}</i></p>')
    else:
        rodape = ""
    return (f'<h4 class="sub-grafico">{ROT[fam]}</h4>'
            f'<div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Ano</th>'
            f'<th class="num">Parque do ano</th><th class="num">Ocorrências</th>'
            f'<th class="num">Total que falharam</th><th class="num">Taxa</th></tr></thead>'
            f'<tbody>{"".join(linhas)}{rodape_total}</tbody></table></div>{rodape}')


def tabela_pecas(fam, leitura):
    """De que a família falhou, pela leitura — controle, tanque, célula, furto."""
    if not leitura:
        return ""
    pp = leitura.get("por_peca") or {}
    pecas = sorted({ch.split("|")[2] for ch in pp if ch.startswith(fam + "|")})
    if not pecas:
        return ""
    cab = "".join(f'<th class="num">{esc(p.title())}</th>' for p in pecas)
    corpo = "".join(
        f'<tr><td>{ano}</td>' + "".join(
            f'<td class="num">{pp.get(f"{fam}|{ano}|{p}", 0) or "—"}</td>' for p in pecas
        ) + "</tr>"
        for ano in ANOS
    )
    return (f'<div class="tabela-rol" style="margin-top:10px"><table class="matriz livro">'
            f'<thead><tr><th>{ROT[fam]} — o que falhou</th>{cab}</tr></thead>'
            f'<tbody>{corpo}</tbody></table></div>')


def bloco_leitura(leitura):
    """O carimbo de auditoria: quantos apontamentos ficaram e quantos caíram."""
    if not leitura:
        return ""
    ex = ""
    descartes = leitura.get("descartes") or []
    if descartes:
        tres = descartes[:3]
        ex = " Exemplos do que caiu: " + " · ".join(
            f'{d.get("ativo")} ({(d.get("motivo") or "")[:110].strip()}…)' for d in tres)
    return (f'<div class="nota" style="margin-top:14px"><strong>Como estes números foram '
            f'conferidos</strong> Os leitores apontaram {leitura.get("falhas_apontadas")} '
            f'falhas nos {leitura.get("ativos_lidos")} ativos da carteira. Revisores '
            f'independentes conferiram cada uma contra o texto original e derrubaram '
            f'{leitura.get("derrubadas_pela_revisao")} — só {leitura.get("confirmadas_pela_revisao")} '
            f'resistiram, e é com elas que a taxa é calculada. Um episódio relatado em duas '
            f'SS foi contado uma vez só.{ex}</div>')


def main():
    taxa = _ler(ARQ_TAXA) or {}
    leitura = _ler(ARQ_LEITURA)

    ppa = taxa.get("parque_por_ano") or {}
    regua = (taxa.get("regua_do_componente") or {}).get("por_familia_e_ano") or {}
    aic = (taxa.get("trocas_no_aic") or {}).get("por_ano_de_conclusao_fisica") or {}
    res = taxa.get("resolvidos_por_ano") or {}
    dem = res.get("demandas_de_falha_encerradas") or {}
    campo = res.get("obra_de_substituicao_concluida_em_campo") or {}
    contab = res.get("obra_de_substituicao_encerrada_no_contabil") or {}

    def soma(m, a):
        return sum((m.get(a) or {}).values())

    proj26 = round(soma(dem, "2026") / 0.611)

    aviso = "" if leitura else (
        '<div class="nota branda"><strong>Leitura em andamento</strong> '
        "Agentes estão lendo o texto completo das 1.087 SS e OS dos 129 ativos da "
        "carteira, com revisores conferindo cada falha apontada. A coluna «Falhas» é a "
        "prévia pelo que já está documentado — troca executada em obra encerrada mais "
        "peça grande registrada na fila; pode haver pequena sobreposição entre as duas "
        "parcelas. A leitura revisada substitui esta prévia.</div>"
    )
    origem_falhas = (
        "a leitura integral das SS e OS pelos agentes, revisada"
        if leitura else "a prévia por evidência direta"
    )

    contraponto = "".join(
        f'<tr><td>{a}{" <i>(até 12/08)</i>" if a == "2026" else ""}</td>'
        f'<td class="num"><b>{soma(dem, a) or "—"}</b> <i>({(dem.get(a) or {}).get("religador", 0)} RL · '
        f'{(dem.get(a) or {}).get("regulador", 0)} RT)</i></td>'
        f'<td class="num">{soma(campo, a) or "—"}</td>'
        f'<td class="num">{soma(contab, a) or "—"}</td></tr>'
        for a in ANOS
    )

    premissas = "".join(
        f'<div class="nota branda"><strong>{i}.</strong> {esc(p)}</div>'
        for i, p in enumerate(taxa.get("premissas") or [], start=1)
    )

    passos = [
        "Separar o que é falha do que é serviço: das 6.305 SS de religador e regulador, "
        "saem ajustes, comissionamentos, obras novas, cadastro e preventivas.",
        "Juntar as SS gêmeas: o mesmo defeito repassado de equipe em equipe gera SS nova "
        "a cada passagem — todas viram uma falha só.",
        "Ler o texto: agentes leem a SS e a OS de cada ativo da carteira e decidem se a "
        "falha exigiu peça grande (controle, tanque, célula, completo, furto). Outro "
        "time revisa cada apontamento e derruba o que não se sustenta.",
        "Datar pela ocorrência: o ano da falha é quando ela aconteceu, não quando a SS "
        "foi aberta — a abertura vem em média 65 dias depois.",
        "Dividir pelo parque do ano: o parque de hoje menos o que foi instalado depois, "
        "na média entre o início e o fim de cada ano.",
    ]
    passo_a_passo = "".join(
        f'<div class="nota branda"><strong>Passo {i}.</strong> {esc(p)}</div>'
        for i, p in enumerate(passos, start=1)
    )

    def css(*p):
        with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
            return fh.read()

    corpo = f"""<main id="pagina"><div class="folha">
  <header>
    <h1>Taxa de falha</h1>
    <p class="sub">Religadores e reguladores de tensão da ETO, 2024 a 2026. Falha aqui é só o que
    exigiu <b>peça grande</b>: no religador, controle (a placa de alimentação CA e o relé de
    sincronismo são controle), tanque ou o equipamento completo; no regulador, célula, relé,
    o banco completo ou furto. O que a régua deixa de fora — trafo auxiliar, chave faca, rádio,
    antena, bateria, aterramento — não some: fica registrado em separado.</p>
    <div class="carimbo"><span>Base SS/OS · AIC · carteira do ETO-COEP</span>
    <span>posição de 12/08/2026 · falhas por {esc(origem_falhas)}</span></div>
  </header>

  <section class="bloco"><h3>A taxa, ano a ano</h3>
    <p class="destaque-texto">Conta simples, na regra do gestor: o total que falharam dividido
    pelo tamanho do parque. O parque é o atual — <b>1.307 religadores</b> (1.297 + 10 instalados
    em 2026) e <b>207 reguladores</b> (197 + 10) — e vale para os três anos: instala-se pouco por
    ano, a variação não muda a taxa. 2026 vai até 12/08, sem anualizar.</p>
    {aviso}
    {tabela_familia("religador", ppa, leitura, regua, aic)}
    {tabela_pecas("religador", leitura)}
    {tabela_familia("regulador", ppa, leitura, regua, aic)}
    {tabela_pecas("regulador", leitura)}
    {bloco_leitura(leitura)}
  </section>

  <section class="bloco"><h3>O contraponto: o que o posto resolveu</h3>
    <p class="destaque-texto">Três medidas que contam coisas diferentes. <b>Demandas de falha
    encerradas</b> é a SS que terminou (atendida ou cancelada) — a única comparável entre anos.
    <b>Obra concluída em campo</b> é o serviço feito. <b>Obra encerrada no contábil</b> vem
    sempre atrasada: as obras de 2026 ainda não fecharam no sistema — é atraso de papel, não
    queda de produção.</p>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Ano</th>
    <th class="num">Demandas de falha encerradas</th><th class="num">Obra concluída em campo</th>
    <th class="num">Obra encerrada no contábil</th></tr></thead><tbody>{contraponto}</tbody>
    </table></div>
    <div class="nota" style="margin-top:12px"><strong>2026 está no ritmo mais alto já registrado</strong>
    São {soma(dem, "2026")} demandas de falha encerradas em 61% do ano. Mantido o ritmo, o ano fecha
    em torno de {proj26} — empata com 2025 ({soma(dem, "2025")}) e fica bem acima de 2024
    ({soma(dem, "2024")}). A impressão do gestor de que 2026 é o ano que mais resolve se confirma
    no ritmo, com 2025 ainda à frente no volume fechado.</div>
  </section>


  <section class="bloco"><h3>A linha que fecha — do parque ao caixa</h3>
    <p class="destaque-texto">Sete elos, cada número nascendo do anterior. É a mesma história
    contada de ponta a ponta, sem ponta solta.</p>
    <div class="nota branda"><strong>1 · O parque.</strong> A ETO opera 1.307 religadores e 207
    reguladores — 1.514 equipamentos especiais.</div>
    <div class="nota branda"><strong>2 · O que quebra.</strong> Em 2026, até 12/08, falharam com
    peça grande 31 religadores (2,4%) e 12 reguladores (5,8%). No triênio: 156 RL (11,9%) e 60 RT
    (29,0%). O religador quebra pouco e parelho; o regulador quebra duas vezes e meia mais — e é
    onde a peça custa de R$ 57 mil a R$ 127 mil.</div>
    <div class="nota branda"><strong>3 · Para onde a quebra vai.</strong> Dos 43 de 2026, 7 foram
    trocados na hora por obra direta (4 RL + 3 RT, corretivas emergenciais) e 36 entraram na
    carteira do COEP (27 RL + 9 RT) para diagnóstico, compra e programação. A carteira é
    exatamente o lugar onde a falha espera peça.</div>
    <div class="nota branda"><strong>4 · O que a carteira devolve.</strong> A carteira não trata só
    a safra do ano: janeiro abriu com 59 SS de anos anteriores. Em 2026 o posto resolveu 62
    (39 RL + 23 RT) — dos 39 religadores, 14 eram falhas velhas de 2024/25 finalmente fechadas,
    4 eram do próprio ano e 21 eram limpeza de carteira (cancelados em operação, repasses):
    trabalho real que não é falha. Por isso «62 resolvidos» e «31 falharam» não se contradizem —
    um mede produção do posto, o outro mede saúde do parque.</div>
    <div class="nota branda"><strong>5 · O saldo.</strong> Entra 43, sai 62 — a fila encolhe. O
    livro-caixa da dinâmica do posto registra: pico de 99 em abril, 55 no fim de julho. Pela
    primeira vez o posto resolve mais do que quebra, no ano de maior produção da série (483
    demandas encerradas em 61% do ano, ritmo de ~790).</div>
    <div class="nota branda"><strong>6 · O que ainda trava.</strong> Da safra 2026, 21 dos 27 RL e
    5 dos 9 RT da carteira seguem pendentes — esperando peça. A fila material confirma: 69 peças
    grandes já levadas a campo em obras não concluídas (26 partes ativas + 24 controles de RL;
    15 células + 4 controles de RT), R$ 3,18 milhões entre o almoxarifado e a energização. O plano
    de compras de 17/07 (R$ 1,72 mi) só entrega religador em nov/2026 e regulador em jan/2027.</div>
    <div class="nota branda"><strong>7 · O dinheiro fecha o ciclo.</strong> A mesma leitura que
    conta as falhas evitou gasto: R$ 1,19 milhão que seria gasto nos 23 cancelados em operação,
    com R$ 420 mil ainda lançados no orçamento, prontos para liberar — dinheiro que volta para a
    fila do elo 6.</div>

    <h4 class="sub-grafico">A prova de que o COEP agiu — caso a caso, nos 36 da safra 2026</h4>
    <p class="destaque-texto">Conferido no texto das SS e OS de cada um dos 36 ativos que entraram
    na carteira em 2026: o rastro documental da ação do posto.</p>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Rastro documental</th>
    <th class="num">Casos</th><th class="num">Em 36</th></tr></thead><tbody>
    <tr><td>SS aberta no ETO-COEP</td><td class="num"><b>34</b></td><td class="num">94%</td></tr>
    <tr><td>Parecer COEP escrito no texto da SS</td><td class="num"><b>29</b></td><td class="num">81%</td></tr>
    <tr><td>Repasse COEP → execução registrado no SGM</td><td class="num"><b>20</b></td><td class="num">56%</td></tr>
    <tr><td>Ação de material documentada (compra, EMD, rota de entrega)</td><td class="num"><b>14</b></td><td class="num">39%</td></tr>
    <tr><td>Troca já executada, com OS que confirma</td><td class="num"><b>10</b></td><td class="num">28%</td></tr>
    </tbody></table></div>
    <p class="destaque-texto" style="margin-top:6px"><i>As duas exceções, ditas com clareza: o
    regulador 5848305116 e o religador 7957021094 (Peixe) foram resolvidos direto pela TELE/DMSL,
    com troca de controle confirmada em OS, sem passar pelo posto — a rede também resolve sem o
    COEP quando a peça está à mão, e a conta registra isso em vez de esconder.</i></p>
  </section>

  <section class="bloco"><h3>Como foi feito — passo a passo</h3>{passo_a_passo}</section>

  <section class="bloco"><h3>As premissas</h3>
    <p class="destaque-texto">Cada número desta página depende do que está escrito aqui.
    Premissa que muda, número que muda.</p>{premissas}</section>
</div></main>"""

    pagina = (
        '<meta charset="utf-8">\n'
        "<title>Taxa de Falha</title>\n"
        '<script>document.documentElement.dataset.tema = "claro";</script>\n'
        f"<style>\n{css('assets', 'css', 'fontes.css')}\n</style>\n"
        f"<style>\n{css('assets', 'css', 'styles.css')}\n</style>\n"
        f"<style>\n{css('assets', 'css', 'dinamica.css')}\n</style>\n"
        f"{corpo}\n"
    )
    with open(DESTINO, "w", encoding="utf-8") as fh:
        fh.write(pagina)
    print(f"OK — {DESTINO} ({os.path.getsize(DESTINO) / 1024:.0f} KB)"
          f" · falhas por {origem_falhas}")


if __name__ == "__main__":
    main()
