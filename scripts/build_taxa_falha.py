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
ARQ_COEP = os.path.join(RAIZ, "data", "missao", "coep_2026.json")
DESTINO = os.path.join(RAIZ, "dist", "taxa-falha.html")

ANOS = ("2024", "2025", "2026")
ROT = {"religador": "Religadores", "regulador": "Reguladores"}
FATOR = {"2024": 1.0, "2025": 1.0, "2026": 1.0}  # divisão direta, sem anualizar


ESTILO_BASES = """
.bases-baixar { display: grid; gap: 8px; margin: 10px 0 4px; }
.base-linha { display: flex; align-items: center; justify-content: space-between; gap: 14px;
  padding: 10px 13px; border: 1px solid var(--filete); background: var(--papel-2);
  border-radius: 3px; }
.base-linha > div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.base-linha b { font-family: var(--cond); font-size: 1.02rem; letter-spacing: .01em; }
.base-conta { font-size: .82rem; color: var(--tinta-3); }
.base-baixar { flex: none; font-family: var(--cond); font-size: .92rem; letter-spacing: .04em;
  text-transform: uppercase; color: var(--papel); background: var(--sinal);
  padding: 7px 15px; border-radius: 3px; transition: opacity .15s; }
.base-baixar:hover { opacity: .85; }
.base-baixar[disabled] { opacity: .5; cursor: default; }
.base-baixar.pronto { background: var(--baixa); }
.base-aviso { font-size: .85rem; color: var(--tinta-3); margin: 4px 0 0; font-style: italic; }
@media (max-width: 560px) { .base-linha { flex-direction: column; align-items: stretch; }
  .base-baixar { width: 100%; } }
"""

SCRIPT_BASES = """
<script>
(function () {
  "use strict";
  const BASES = __BASES__;
  const caixa = document.getElementById("bases-baixar");
  const indisponivel = document.getElementById("base-indisponivel");
  const aviso = document.getElementById("base-aviso");
  const BOM = "\uFEFF";   // sem isto o Excel do Windows come os acentos

  function dizer(texto) {
    if (!aviso) return;
    aviso.textContent = texto || "";
    aviso.hidden = !texto;
  }

  async function salvar(api, nome, csv, extensao) {
    return api.save({ filename: nome + "." + extensao, data: BOM + csv });
  }

  async function iniciar() {
    let api = null;
    try { api = await (window.claude && window.claude.use ? window.claude.use("downloads") : null); }
    catch (e) { api = null; }
    if (!api) return;                       // fica só o aviso de indisponível
    if (indisponivel) indisponivel.hidden = true;
    if (caixa) caixa.hidden = false;

    caixa.addEventListener("click", async function (ev) {
      const botao = ev.target.closest(".base-baixar");
      if (!botao || botao.disabled) return;
      const chave = botao.dataset.base;
      const base = BASES[chave];
      if (!base) return;
      const rotulo = botao.textContent;
      botao.disabled = true;
      botao.textContent = "Salvando…";
      dizer("");
      try {
        try {
          await salvar(api, chave, base.csv, "csv");
        } catch (erro) {
          // csv está no conjunto estendido; onde não estiver ligado, vai como txt
          if (erro && erro.code === "extension_not_enabled") {
            await salvar(api, chave, base.csv, "txt");
            dizer("Salvo como .txt — esta janela não libera .csv. Renomeie para .csv e o "
                  + "Excel abre igual.");
          } else { throw erro; }
        }
        botao.textContent = "Salvo";
        botao.classList.add("pronto");
        setTimeout(function () {
          botao.textContent = rotulo;
          botao.classList.remove("pronto");
          botao.disabled = false;
        }, 2600);
        return;
      } catch (erro) {
        const codigo = erro && erro.code;
        if (codigo === "declined") dizer("");
        else if (codigo === "rate_limited") dizer("Tem outro download esperando resposta. "
          + "Responda aquele e tente de novo.");
        else if (codigo === "too_large") dizer("Arquivo grande demais para salvar por aqui.");
        else dizer("Não deu para salvar agora. Tente de novo em instantes.");
      }
      botao.textContent = rotulo;
      botao.disabled = false;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else { iniciar(); }
})();
</script>
"""


def _csv(linhas):
    """CSV com ponto e vírgula, do jeito que o Excel brasileiro abre sem pedir nada."""
    def cel(v):
        t = "" if v is None else str(v)
        return '"' + t.replace('"', '""') + '"' if any(c in t for c in ';"\n\r') else t
    return "\r\n".join(";".join(cel(c) for c in linha) for linha in linhas)


def bases_para_baixar(coep, taxa, leitura):
    ppa = taxa.get("parque_por_ano") or {}
    """As bases da página em CSV, prontas para o gestor abrir no Excel e mostrar."""
    sn = lambda v: "sim" if v else "não"
    ativos = coep.get("ativos") or []
    resolv = coep.get("resolvidos_do_coep") or []
    ss = coep.get("ss") or []

    passaram = [["Ativo", "Tipo", "Localidade", "SS no COEP em 2026", "Quantas SS",
                 "Primeira chegada", "Dias no posto", "Ainda no posto em 18/08",
                 "Está na carteira", "Parecer COEP", "Criticidade"]]
    passaram += [[a["ativo"], a["tipo"], a["localidade"], a["ss"], a["ss_no_coep_em_2026"],
                  a["primeira_chegada"], a["dias_no_posto"], sn(a["segue_no_posto"]),
                  sn(a["na_carteira"]), a["parecer_coep"], a["criticidade"]]
                 for a in ativos]

    pend = [passaram[0]] + [linha for a, linha in zip(ativos, passaram[1:])
                            if a["segue_no_posto"]]

    resolvidos = [["Ativo", "Tipo", "Ano da demanda", "Ocorrência", "Conta", "Prova",
                   "Por que não conta", "Nota nova no COEP", "Nota nova em outro posto",
                   "Tem nota pendente hoje", "Cancelada no lote de 29-30/06",
                   "SS que abriu a demanda", "Posto que abriu", "SS no COEP",
                   "SS que fechou", "Posto que fechou", "Como terminou", "Fechou em",
                   "Dias da demanda", "Está na carteira", "Parecer COEP", "Localidade"]]
    resolvidos += [[r["ativo"], r["tipo"], r["ano_da_demanda"], r["ocorrencia_da_demanda"],
                    sn(r["conta_como_resolvido_pelo_coep"]), r["prova"], r["porque_nao"],
                    r["nota_nova_no_coep"], r["nota_nova_em_outro_posto"],
                    sn(r["tem_nota_pendente_hoje"]), sn(r["cancelada_no_lote_de_junho"]),
                    r["ss_que_abriu_a_demanda"], r["posto_que_abriu"], r["ss_no_coep"],
                    r["ss_que_fechou"], r["posto_que_fechou"], r["como_terminou"],
                    r["data_do_fechamento"], r["dias_da_demanda"], sn(r["esta_na_carteira"]),
                    r["parecer_coep"], r["localidade"]]
                   for r in sorted(resolv, key=lambda x: (not x["conta_como_resolvido_pelo_coep"],
                                                          x["ano_da_demanda"] or 9999, x["ativo"]))]

    ss_csv = [["SS", "Ativo", "Tipo", "Status", "Chegou", "Saiu", "Como se apurou a saída",
               "Foi para", "Dias no posto", "Pendência"]]
    ss_csv += [[i["ss"], i["ativo"], i["tipo"], i["status"], i["chegou"], i["saiu"],
                i["como_apurou_a_saida"], i["foi_para"], i["dias_no_posto"], i["pendencia"]]
               for i in sorted(ss, key=lambda x: -x["dias_no_posto"])]

    # a mesma conta da tabela da página: equipamentos que falharam ÷ parque do ano
    ppa = taxa.get("parque_por_ano") or {}
    serie = taxa.get("serie_por_ano") or {}
    tx = [["Família", "Ano", "Parque", "Ocorrências", "Equipamentos que falharam", "Taxa (%)"]]
    for fam in ("religador", "regulador"):
        soma = 0
        for ano in ANOS:
            parque = ((ppa.get(fam) or {}).get(ano) or {}).get("medio") or 0
            n = (leitura.get("total_equipamentos_que_falharam") or {}).get(f"{fam}|{ano}", 0) \
                if leitura else 0
            obra = (leitura.get("complemento_obra_direta") or {}).get(f"{fam}|{ano}", 0) \
                if leitura else 0
            oc = ((leitura.get("ocorrencias") or {}).get(f"{fam}|{ano}", 0) + obra) \
                if leitura else 0
            soma += n
            taxa_ano = f"{100.0 * n / parque:.1f}".replace(".", ",") if parque and n else ""
            tx.append([fam, ano, parque, oc or "", n or "", taxa_ano])
        parque = ((ppa.get(fam) or {}).get("2026") or {}).get("medio") or 0
        tx.append([fam, "Triênio", parque, "", soma,
                   f"{100.0 * soma / parque:.1f}".replace(".", ",") if parque else ""])

    saida = {
        "coep-2026-passaram-pelo-posto": {
            "titulo": "Passaram pelo posto do COEP em 2026",
            "conta": "um equipamento por linha, com as SS que teve no posto",
            "linhas": len(passaram) - 1, "csv": _csv(passaram)},
        "coep-2026-pendentes-no-posto": {
            "titulo": "Pendentes no posto em 18/08/2026",
            "conta": "os que seguem no COEP, com o tempo parado e o parecer",
            "linhas": len(pend) - 1, "csv": _csv(pend)},
        "coep-2026-resolvidos": {
            "titulo": "Resolvidos pelo COEP em 2026",
            "conta": "todos os candidatos, com o veredito e o motivo de cada corte",
            "linhas": len(resolvidos) - 1, "csv": _csv(resolvidos)},
        "coep-2026-ss-no-posto": {
            "titulo": "As SS que estiveram no posto em 2026",
            "conta": "uma SS por linha, com chegada, saída e para onde foi",
            "linhas": len(ss_csv) - 1, "csv": _csv(ss_csv)},
    }
    serie_csv = taxa.get("serie_por_ano") or {}
    tt = [["Família", "Ano", "Parque", "Ocorrências", "Equipamentos que falharam", "Taxa (%)"]]
    for fam in ("religador", "regulador"):
        soma = 0
        for ano in ANOS:
            b = ((serie_csv.get(ano) or {}).get(fam)) or {}
            parque = ((ppa.get(fam) or {}).get(ano) or {}).get("medio") or 0
            n = b.get("ativos_distintos") or 0
            soma += n
            tt.append([fam, ano, parque, b.get("eventos") or "", n or "",
                       f"{100.0 * n / parque:.1f}".replace(".", ",") if parque and n else ""])
        parque = ((ppa.get(fam) or {}).get("2026") or {}).get("medio") or 0
        tt.append([fam, "Triênio", parque, "", soma,
                   f"{100.0 * soma / parque:.1f}".replace(".", ",") if parque else ""])
    saida["taxa-total-sem-expurgo"] = {
        "titulo": "A taxa total, sem a régua da peça grande",
        "conta": "todo equipamento com falha no ano, qualquer peça, ÷ parque",
        "linhas": len(tt) - 1, "csv": _csv(tt)}
    if len(tx) > 1:
        saida["taxa-de-falha-2024-2026"] = {
            "titulo": "A taxa de falha, ano a ano",
            "conta": "parque, quantos falharam e a taxa, por família e ano",
            "linhas": len(tx) - 1, "csv": _csv(tx)}
    return saida


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
        rot_ano = f'{ano}{" <i>(até 18/08)</i>" if ano == "2026" else ""}'
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
    ritmo26 = 100.0 * (n26 / 0.6274) / parque if parque and n26 else None
    rodape_total = (f'<tr><td><b>Total</b></td><td class="num">—</td>'
                    f'<td class="num"><b>{tot_oc}</b></td>'
                    f'<td class="num"><b>{tot_n}</b></td>'
                    f'<td class="num"><b>{_pct(taxa_total)}</b></td></tr>')
    if leitura:
        comp = " · ".join(
            f'{a}: {(leitura.get("contagem") or {}).get(f"{fam}|{a}", 0)} na carteira lida '
            f'+ {(leitura.get("complemento_obra_direta") or {}).get(f"{fam}|{a}", 0)} por obra direta'
            for a in ANOS)
        ritmo_txt = (f' 2026 vai até 18/08; mantido o ritmo, fecharia em torno de '
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


def tabela_total(fam, serie, ppa):
    """A visão sem expurgo: todo equipamento com falha no ano, qualquer peça."""
    linhas, soma = [], 0
    for ano in ANOS:
        b = ((serie.get(ano) or {}).get(fam)) or {}
        parque = ((ppa.get(fam) or {}).get(ano) or {}).get("medio") or b.get("parque") or 0
        n = b.get("ativos_distintos") or 0
        oc = b.get("eventos") or 0
        soma += n
        taxa = 100.0 * n / parque if parque else None
        rot = f'{ano}{" <i>(até 20/08)</i>" if ano == "2026" else ""}'
        linhas.append(f'<tr><td>{rot}</td><td class="num">{parque or "—"}</td>'
                      f'<td class="num">{oc or "—"}</td><td class="num"><b>{n or "—"}</b></td>'
                      f'<td class="num"><b>{_pct(taxa)}</b></td></tr>')
    parque = ((ppa.get(fam) or {}).get("2026") or {}).get("medio") or 0
    total = (f'<tr class="total"><td><b>Triênio</b></td><td class="num">{parque}</td>'
             f'<td class="num">—</td><td class="num"><b>{soma}</b></td>'
             f'<td class="num"><b>{_pct(100.0 * soma / parque if parque else None)}</b></td></tr>')
    rot_fam = "Religadores" if fam == "religador" else "Reguladores"
    return (f'<h4 class="sub-grafico">{rot_fam}</h4>'
            f'<div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Ano</th>'
            f'<th class="num">Parque</th><th class="num">Ocorrências</th>'
            f'<th class="num">Total que falharam</th><th class="num">Taxa</th></tr></thead>'
            f'<tbody>{"".join(linhas)}{total}</tbody></table></div>')


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
    coep = _ler(ARQ_COEP) or {}
    cc = coep.get("conta") or {}
    cano = cc.get("resolvidos_por_ano_da_demanda") or {}
    cprova = cc.get("resolvidos_por_prova") or {}
    antigos = sum(v for k, v in cano.items() if k < "2026")
    resolv = cc.get("resolvidos_pelo_coep", 0)
    passaram = cc.get("equipamentos_que_passaram", 0)
    linhas_coep = "".join(
        f'<tr><td>{k}{" <i>(até 18/08)</i>" if k == "2026" else ""}</td>'
        f'<td class="num"><b>{v}</b></td>'
        f'<td class="num">{round(100.0 * v / resolv)}%</td></tr>'
        for k, v in sorted(cano.items()))
    fechou_em = (coep.get("postos_que_fecharam") or
                 {"ETO-COEP": 40, "ETO-TELE": 15, "ETO-RD-PS": 5, "ETO-RD-AR": 5,
                  "ETO-PROT": 4, "ETO-RD-PA": 1, "ETO-RD-PO": 1})
    linhas_posto = "".join(
        f'<tr><td>{k}</td><td class="num"><b>{v}</b></td></tr>'
        for k, v in sorted(fechou_em.items(), key=lambda kv: -kv[1]))

    ppa = taxa.get("parque_por_ano") or {}
    serie = taxa.get("serie_por_ano") or {}
    regua = (taxa.get("regua_do_componente") or {}).get("por_familia_e_ano") or {}
    aic = (taxa.get("trocas_no_aic") or {}).get("por_ano_de_conclusao_fisica") or {}
    res = taxa.get("resolvidos_por_ano") or {}
    dem = res.get("demandas_de_falha_encerradas") or {}
    campo = res.get("obra_de_substituicao_concluida_em_campo") or {}
    contab = res.get("obra_de_substituicao_encerrada_no_contabil") or {}

    def soma(m, a):
        return sum((m.get(a) or {}).values())

    proj26 = round(soma(dem, "2026") / 0.6274)

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
        f'<tr><td>{a}{" <i>(até 18/08)</i>" if a == "2026" else ""}</td>'
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

    bases = bases_para_baixar(coep, taxa, leitura)
    cartoes_base = "".join(
        f'<div class="base-linha"><div><b>{esc(v["titulo"])}</b>'
        f'<span class="base-conta">{esc(v["conta"])} · {v["linhas"]} linhas</span></div>'
        f'<button class="base-baixar" data-base="{esc(k)}">Baixar CSV</button></div>'
        for k, v in bases.items())
    bases_json = json.dumps({k: {"csv": v["csv"], "titulo": v["titulo"]}
                             for k, v in bases.items()}, ensure_ascii=False)

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
    <span>posição de 20/08/2026 · leitura de falhas e repasse pela base de 11/08</span></div>
  </header>

  <section class="bloco"><h3>A taxa, ano a ano</h3>
    <p class="destaque-texto">Conta simples, na regra do gestor: o total que falharam dividido
    pelo tamanho do parque. O parque é o atual — <b>1.307 religadores</b> (1.297 + 10 instalados
    em 2026) e <b>207 reguladores</b> (197 + 10) — e vale para os três anos: instala-se pouco por
    ano, a variação não muda a taxa. 2026 vai até 18/08, sem anualizar.</p>
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
    São {soma(dem, "2026")} demandas de falha encerradas em 63% do ano. Mantido o ritmo, o ano fecha
    em torno de {proj26} — empata com 2025 ({soma(dem, "2025")}) e fica bem acima de 2024
    ({soma(dem, "2024")}). A impressão do gestor de que 2026 é o ano que mais resolve se confirma
    no ritmo, com 2025 ainda à frente no volume fechado.</div>
  </section>


  <section class="bloco"><h3>A linha que fecha — do parque ao caixa</h3>
    <p class="destaque-texto">Sete elos, cada número nascendo do anterior. É a mesma história
    contada de ponta a ponta, sem ponta solta.</p>
    <div class="nota branda"><strong>1 · O parque.</strong> A ETO opera 1.307 religadores e 207
    reguladores — 1.514 equipamentos especiais.</div>
    <div class="nota branda"><strong>2 · O que quebra.</strong> Em 2026, até 18/08, falharam com
    peça grande 31 religadores (2,4%) e 12 reguladores (5,8%). No triênio: 156 RL (11,9%) e 60 RT
    (29,0%). O religador quebra pouco e parelho; o regulador quebra duas vezes e meia mais — e é
    onde a peça custa de R$ 57 mil a R$ 127 mil.</div>
    <div class="nota branda"><strong>3 · Para onde a quebra vai.</strong> Dos 43 de 2026, 7 foram
    trocados na hora por obra direta (4 RL + 3 RT, corretivas emergenciais) e 36 entraram na
    carteira do COEP (27 RL + 9 RT) para diagnóstico, compra e programação. A carteira é
    exatamente o lugar onde a falha espera peça.</div>
    <div class="nota branda"><strong>4 · O que o posto devolve.</strong> O COEP não trata só a
    safra do ano: janeiro abriu com 59 SS de anos anteriores. Em 2026, até 18/08,
    <b>{resolv} equipamentos</b> tiveram a demanda fechada
    depois de passar pelo posto — e <b>{antigos} deles nasceram antes de 2026</b>. Por isso
    «{resolv} resolvidos» e «43 falharam» não se contradizem: um mede produção do posto, o outro
    mede saúde do parque.</div>
    <div class="nota branda"><strong>5 · O saldo.</strong> Entra 43, sai {resolv} — a fila encolhe. O
    livro-caixa da dinâmica do posto registra: pico de 99 em abril, 55 no fim de julho. Pela
    primeira vez o posto resolve mais do que quebra, no ano de maior produção da série (483
    demandas encerradas em 63% do ano, ritmo de ~790).</div>
    <div class="nota branda"><strong>6 · O que ainda trava.</strong> Da safra 2026, 21 dos 27 RL e
    5 dos 9 RT da carteira seguem pendentes — esperando peça. A fila material confirma: 69 peças
    grandes já levadas a campo em obras não concluídas (26 partes ativas + 24 controles de RL;
    15 células + 4 controles de RT), R$ 3,18 milhões entre o almoxarifado e a energização. O plano
    de compras de 17/07 (R$ 1,72 mi) só entrega religador em nov/2026 e regulador em jan/2027.</div>
    <div class="nota branda"><strong>7 · O dinheiro fecha o ciclo.</strong> A mesma leitura que
    conta as falhas evitou gasto: R$ 1,19 milhão que seria gasto nos 23 cancelados em operação,
    com R$ 420 mil ainda lançados no orçamento, prontos para liberar — dinheiro que volta para a
    fila do elo 6.</div>

    <h4 class="sub-grafico" id="taxa-total">A taxa total — sem a régua da peça grande</h4>
    <p class="destaque-texto">A visão pedida em 22/08: a mesma conta, <b>sem os expurgos</b>.
    Aqui entra todo equipamento com falha registrada no ano, qualquer que seja a peça — trafo
    auxiliar, bateria, telecom, peça miúda ou peça grande —, contado uma vez por ano e dividido
    pelo mesmo parque. A régua que sobra é uma só: o defeito é <b>do equipamento</b>. Continua de
    fora o que é da rede pendurado no código dele (poste, cruzeta, chave da rede, para-raios,
    aterramento) e o serviço programado (ajuste, comissionamento, cadastro) — isso não é falha do
    ativo em nenhuma das duas contas.</p>
    {tabela_total("religador", serie, ppa)}
    {tabela_total("regulador", serie, ppa)}
    <div class="nota branda"><strong>Como ler as duas contas juntas.</strong> A taxa da peça
    grande mede o que dói no orçamento: controle, tanque, célula, o equipamento inteiro. A taxa
    total mede quanto o parque chama manutenção por qualquer motivo próprio. A distância entre as
    duas é a peça miúda — muita chamada, pouco custo. As duas usam a mesma base de SS/OS
    (extração de 20/08) e o mesmo parque.</div>

    <h4 class="sub-grafico">Baixar as bases</h4>
    <p class="destaque-texto">Os números desta página, em CSV — abre direto no Excel, com
    acento e com ponto e vírgula separando as colunas. O navegador pede confirmação antes de
    salvar.</p>
    <div class="bases-baixar" id="bases-baixar" hidden>{cartoes_base}
      <p class="base-aviso" id="base-aviso" hidden></p>
    </div>
    <p class="base-aviso" id="base-indisponivel">Baixar arquivo não está disponível nesta
    janela. Abra a página no claude.ai para salvar as bases.</p>

    <h4 class="sub-grafico">O posto do COEP em 2026 — duas visões</h4>
    <p class="destaque-texto">Quem passou pela mesa do posto, e o que o posto devolveu. As duas
    contas são de <b>equipamento</b>, não de SS: o mesmo religador com três SS no posto no mesmo
    ano é um equipamento.</p>
    <div class="nota branda"><strong>Visão 1 — passaram pelo posto.</strong>
    <b>{passaram} equipamentos</b> estiveram no COEP em algum momento de 2026, em
    {cc.get("ss_no_posto", 0)} SS — {(cc.get("por_tipo") or {{}}).get("religador", 0)} religadores
    e {(cc.get("por_tipo") or {{}}).get("regulador", 0)} reguladores. Desses,
    {cc.get("seguem_no_posto_em_18_08", 0)} ainda estavam lá em 18/08.
    {cc.get("na_carteira_consolidada", 0)} estão na carteira consolidada e
    {cc.get("fora_da_carteira", 0)} não — passam pelo posto sem entrar na planilha de
    acompanhamento.</div>
    <div class="nota branda"><strong>A armadilha que quase estragou a conta.</strong> SS repassada
    não tem data de conclusão: sai vazia na base. Quem contar «sem conclusão» como «ainda no
    posto» arrasta SS de 2020 para dentro de 2026 — a primeira contagem deu 442 SS herdadas,
    número falso. A saída certa vem da cadeia de repasse: a SS saiu do posto no dia em que a SS
    seguinte foi aberta. Das 694 SS do COEP, 153 têm saída pela conclusão, <b>486 só têm saída
    pelo repasse</b> e 55 seguem no posto.</div>
    <div class="nota branda"><strong>Visão 2 — o posto resolveu {resolv}.</strong> A conta não sai
    da carteira: a carteira é a foto do que ainda está pendente, e o que fechou e saiu não fica
    registrado nela. Sai da cadeia da demanda — passou pelo posto dentro de 2026 e a cadeia fechou
    dentro de 2026, com SS atendida ou cancelada. O ano é o da <b>data de ocorrência</b> da
    primeira SS da cadeia.</div>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr>
    <th>Ano em que a demanda nasceu</th><th class="num">Resolvidos em 2026</th>
    <th class="num">Do total</th></tr></thead><tbody>{linhas_coep}
    <tr class="total"><td>Total</td><td class="num"><b>{resolv}</b></td>
    <td class="num">100%</td></tr></tbody></table></div>
    <div class="nota branda"><strong>Como cada um foi resolvido.</strong>
    {cprova.get("SS atendida", 0)} por SS atendida, com serviço executado;
    {cprova.get("cancelada, com leitura que confirma volta à operação", 0)} por cancelamento com
    leitura do texto confirmando volta à operação;
    {cprova.get("resolvido por cancelamento", 0)} por cancelamento sem nota nova no COEP depois,
    que é a régua do gestor: cancelado é resolvido, desde que não tenham aberto outra nota para
    aquele ativo no posto. Quem voltou não conta — <b>{cc.get("tirados_por_volta_ao_coep", 0)}
    equipamentos caíram</b> por isso, cada um com o número e a data da nota que os trouxe de
    volta.</div>
    <div class="nota branda"><strong>Quem fecha não precisa ser o COEP.</strong> O posto
    diagnostica e despacha; quem executa é a ponta. O ETO-TELE conta quando há parecer do COEP ou
    passagem pelo posto antes — e os 15 fechados lá têm SS no COEP, 11 com parecer na carteira.</div>
    <div class="tabela-rol"><table class="matriz livro"><thead><tr><th>Onde a demanda fechou</th>
    <th class="num">Equipamentos</th></tr></thead><tbody>{linhas_posto}</tbody></table></div>
    <div class="nota branda"><strong>O que fica para o gestor conferir.</strong>
    {cc.get("resolvidos_no_lote_de_junho", 0)} dos {resolv} foram cancelados no lote de 29 e 30 de
    junho — pela régua eles contam, mas o lote está marcado em coluna própria na planilha.
    E {cc.get("resolvidos_com_nota_pendente_em_outro_posto", 0)} seguem com nota pendente em outro
    posto: o COEP fechou a parte dele, o equipamento ainda tem pendência em outra mesa. Se essas
    também derrubarem, o número cai para
    {resolv - cc.get("resolvidos_com_nota_pendente_em_outro_posto", 0)}.</div>

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
        f"<style>{ESTILO_BASES}</style>\n"
        f"{corpo}\n"
        + SCRIPT_BASES.replace("__BASES__", bases_json)
    )
    with open(DESTINO, "w", encoding="utf-8") as fh:
        fh.write(pagina)
    print(f"OK — {DESTINO} ({os.path.getsize(DESTINO) / 1024:.0f} KB)"
          f" · falhas por {origem_falhas}")


if __name__ == "__main__":
    main()
