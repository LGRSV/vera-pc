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
FATOR = {"2024": 1.0, "2025": 1.0, "2026": 0.611}


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
    """Tabela da família: parque do ano, falhas e taxa. Leitura revisada quando há."""
    linhas = []
    for ano in ANOS:
        p = (ppa.get(fam) or {}).get(ano, {})
        medio = p.get("medio") or 0
        eq = medio * FATOR[ano]
        if leitura:
            n = (leitura.get("contagem") or {}).get(f"{fam}|{ano}", 0)
            partes = ""
        else:
            evid = (regua.get(fam) or {}).get(ano, {}).get("com_peca_grande") or 0
            troca = (aic.get(ano) or {}).get(fam, 0)
            n = evid + troca
            partes = (f'<td class="num">{troca or "—"}</td>'
                      f'<td class="num">{evid or "—"}</td>')
        taxa = 100.0 * n / eq if eq else None
        rot_ano = f'{ano}{" <i>(até 12/08)</i>" if ano == "2026" else ""}'
        linhas.append(
            f'<tr><td>{rot_ano}</td>'
            f'<td class="num">{medio or "—"}</td>'
            f'<td class="num">{("+" + str(p.get("instalados_no_ano"))) if p.get("instalados_no_ano") else "—"}</td>'
            f"{partes}"
            f'<td class="num"><b>{n or "—"}</b></td>'
            f'<td class="num"><b>{_pct(taxa)}</b></td></tr>'
        )
    extra = ("" if leitura else
             "<th class=\"num\">Troca executada</th><th class=\"num\">Peça grande na fila</th>")
    return (f'<h4 class="sub-grafico">{ROT[fam]}</h4>'
            f'<div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Ano</th>'
            f'<th class="num">Parque do ano</th><th class="num">Novos no ano</th>{extra}'
            f'<th class="num">Falhas</th><th class="num">Taxa</th></tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


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
    <p class="destaque-texto">O parque é o de cada ano — o de hoje (1.297 religadores e 197
    reguladores) menos o que foi instalado depois, na média do ano. 2026 vai até 12/08 e a
    conta usa a fração decorrida do ano (61%), senão o ano em curso pareceria melhor do que é.</p>
    {aviso}
    {tabela_familia("religador", ppa, leitura, regua, aic)}
    {tabela_pecas("religador", leitura)}
    {tabela_familia("regulador", ppa, leitura, regua, aic)}
    {tabela_pecas("regulador", leitura)}
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
