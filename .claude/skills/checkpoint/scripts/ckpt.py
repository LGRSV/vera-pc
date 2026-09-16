#!/usr/bin/env python3
"""
ckpt — trabalho longo que não se perde quando o contexto acaba.

O problema: um agente processa 80 itens e só grava o resultado no fim. Se o contexto
estourar no item 79, perdem-se os 79. E quem retoma não sabe onde parou.

A ideia: **grave cada item assim que ele fica pronto**, numa linha de um arquivo JSONL,
com fsync. O pior caso passa a ser perder um item. Retomar vira uma pergunta —
«o que falta?» — que o próprio arquivo responde.

Não tem dependência, não tem servidor, não tem banco. É um diretório com arquivos de
texto, que versionam bem no git e se leem com `cat`.

    run/
      manifesto.json              o que precisa ser feito, e em quais etapas
      dados/<etapa>/<parte>.jsonl uma linha por item pronto (append-only, fsync)
      notas/<etapa>/<parte>.log   o diário de bordo de quem está trabalhando

GARANTIAS

- **Nada se perde no meio.** Cada `put` é um write() único com O_APPEND e fsync. Se o
  processo morrer no meio de uma linha, a linha quebrada é ignorada na leitura e o resto
  continua válido.
- **Refazer é seguro.** A chave manda: gravar a mesma chave de novo substitui a anterior.
  Um item refeito por engano não vira dois.
- **Paralelo é seguro.** Cada trabalhador escreve na sua própria PARTE. Duas partes nunca
  disputam o mesmo arquivo.
- **Retomar é barato.** `todo` compara o manifesto com o que já está gravado e devolve só
  o que falta.

COMANDOS

    ckpt.py init   <run> --itens a,b,c | --itens-de arquivo | --itens-json f.json
                         [--etapas leitura,revisao,conferencia] [--partes 8]
    ckpt.py put    <run> <etapa> --chave K [--parte P] --dados '{...}'   (ou --de-arquivo, ou stdin)
    ckpt.py todo   <run> <etapa> [--parte P]        o que ainda falta
    ckpt.py status <run>                            o painel de todas as etapas
    ckpt.py nota   <run> <etapa> --parte P "texto"  diário de bordo
    ckpt.py ler    <run> <etapa> --chave K          o que já foi gravado para um item
    ckpt.py fecha  <run> <etapa> [-o saida.json]    consolida a etapa num JSON só
    ckpt.py sweep  <run>                            procura linha corrompida e relata

Exemplo de uso por um agente:

    R=.analise/run-falhas
    python3 ckpt.py todo $R leitura --parte 3        # de onde retomo?
    ... trabalha o item ...
    python3 ckpt.py put $R leitura --parte 3 --chave 7926089013 --dados "$JSON"
    ... repete ...
    python3 ckpt.py fecha $R leitura -o leitura.json
"""

import argparse
import datetime as dt
import glob
import json
import os
import sys

ETAPAS_PADRAO = ["leitura", "revisao", "conferencia"]


# ------------------------------------------------------------------ caminhos
def _dir(run, *p):
    return os.path.join(run, *p)


def _jsonl(run, etapa, parte):
    return _dir(run, "dados", etapa, "%s.jsonl" % parte)


def _nome_seguro(rotulo, valor):
    """Nome de etapa ou parte vira caminho de arquivo. Sem isto, `--etapas ../../escapou`
    e `--parte ../../../pwn` gravavam fora do run."""
    v = str(valor).strip()
    if not v or "/" in v or "\\" in v or v in (".", ".."):
        raise SystemExit("erro: %s inválido: %r — sem barra, sem '..', não pode ser vazio"
                         % (rotulo, valor))
    return v


def _confere(man, etapa=None, parte=None):
    if etapa is not None and etapa not in man["etapas"]:
        raise SystemExit("erro: etapa '%s' não está no manifesto (%s)"
                         % (etapa, ", ".join(man["etapas"])))
    if parte is not None and str(parte) not in man["partes"]:
        raise SystemExit("erro: parte '%s' não existe neste run (partes: %s)"
                         % (parte, ", ".join(sorted(man["partes"], key=lambda x: int(x)))))


def _manifesto(run):
    cam = _dir(run, "manifesto.json")
    if not os.path.exists(cam):
        raise SystemExit("erro: %s não existe — rode `init` primeiro" % cam)
    with open(cam, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ escrita
def _append(cam, linha):
    """Grava um registro. Duas lições que custaram caro na auditoria adversarial:

    **Sempre escrever `\n` ANTES da linha**, em vez de checar se o arquivo termina em
    `\n` e emendar. A checagem parecia mais limpa, mas é um ler-depois-escrever: entre a
    leitura do último byte e o `write()`, outro processo na mesma parte pode gravar um
    fragmento, e aí a nossa linha cola nele — destruindo um registro que JÁ tinha sido
    confirmado ao chamador. O `\n` incondicional custa um byte e mata a corrida; o leitor
    já pula linha vazia.

    **`os.write` pode gravar só um pedaço e não levantar erro** — disco cheio, `ulimit -f`.
    Sem conferir o retorno, o `put` respondia «gravado» com rc 0 e o registro não estava
    lá. Justamente o cenário que um checkpoint existe para sobreviver.
    """
    os.makedirs(os.path.dirname(cam), exist_ok=True)
    buf = ("\n" + linha).encode("utf-8")
    fd = os.open(cam, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        n = os.write(fd, buf)          # O_APPEND: vai para o fim, sem corrida de offset
        os.fsync(fd)
    finally:
        os.close(fd)
    if n != len(buf):
        raise SystemExit("erro: gravação parcial em %s (%d de %d bytes) — disco cheio ou "
                         "limite de arquivo. O registro NÃO foi salvo." % (cam, n, len(buf)))


def _ler_jsonl(cam):
    """Devolve (registros_por_chave, n_linhas_ruins).

    Tolera linha truncada — que é exatamente o que sobra quando o processo morre no meio
    de uma gravação. A linha quebrada é descartada; o resto do arquivo continua bom."""
    fora, ruins = {}, 0
    if not os.path.exists(cam):
        return fora, ruins
    with open(cam, encoding="utf-8", errors="replace") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                o = json.loads(linha)
            except json.JSONDecodeError:
                ruins += 1
                continue
            # JSON válido que não é objeto (`null`, `[1,2]`, `42`) derrubava a leitura
            # inteira com traceback. Não nasce de queda — prefixo de `{…}` nunca é JSON
            # válido —, mas nasce de edição manual, e é o `sweep` que existe para isso.
            if not isinstance(o, dict) or not isinstance(o.get("_chave"), str):
                ruins += 1
                continue
            fora[o["_chave"]] = o          # último vence
    return fora, ruins


def _todos_registros(run, etapa):
    d = _dir(run, "dados", etapa)
    fora, ruins = {}, 0
    if not os.path.isdir(d):
        return fora, ruins
    for nome in sorted(os.listdir(d)):
        if not nome.endswith(".jsonl"):
            continue
        r, b = _ler_jsonl(os.path.join(d, nome))
        # «último vence» tem de ser o mais RECENTE, não o de nome alfabeticamente maior:
        # com 11 partes, "2.jsonl" > "10.jsonl", e um item regravado na parte 10 perdia
        # para a versão velha da parte 2. Desempata pelo carimbo.
        for k, o in r.items():
            antigo = fora.get(k)
            if antigo is None or (o.get("_em") or "") >= (antigo.get("_em") or ""):
                fora[k] = o
        ruins += b
    return fora, ruins


# ------------------------------------------------------------------ comandos
def cmd_init(a):
    itens = []
    if a.itens:
        itens = [x.strip() for x in a.itens.split(",") if x.strip()]
    elif a.itens_de:
        with open(a.itens_de, encoding="utf-8-sig") as f:
            itens = [x.strip() for x in f if x.strip()]
    elif a.itens_json:
        with open(a.itens_json, encoding="utf-8-sig") as f:
            d = json.load(f)
        itens = [str(x) for x in (d if isinstance(d, list) else d.get("itens", []))]
    if not itens:
        raise SystemExit("erro: nenhum item — use --itens, --itens-de ou --itens-json")
    if len(set(itens)) != len(itens):
        vistos, dup = set(), set()
        for i in itens:
            (dup if i in vistos else vistos).add(i)
        raise SystemExit("erro: itens repetidos no manifesto: %s" % ", ".join(sorted(dup)[:5]))

    etapas = [_nome_seguro("nome de etapa", x)
              for x in (a.etapas or ",".join(ETAPAS_PADRAO)).split(",") if x.strip()]
    if not etapas:
        raise SystemExit("erro: nenhuma etapa válida em --etapas")
    partes = max(1, a.partes)
    tam = -(-len(itens) // partes)
    reparte = {}
    for n in range(partes):
        fatia = itens[n * tam:(n + 1) * tam]
        if fatia:
            reparte[str(n + 1)] = fatia

    run_dir = a.run
    ja = glob.glob(os.path.join(run_dir, "dados", "*", "*.jsonl"))
    if ja and not a.forcar:
        raise SystemExit("erro: %s já tem %d arquivo(s) de dados. Um init novo reparte as "
                         "partes e o `todo` passa a comparar com a lista errada. Use "
                         "--forcar se é mesmo isso que você quer." % (run_dir, len(ja)))
    os.makedirs(run_dir, exist_ok=True)
    man = {"criado": dt.datetime.now().isoformat(timespec="seconds"),
           "itens": itens, "etapas": etapas, "partes": reparte,
           "descricao": a.descricao or ""}
    cam = _dir(run_dir, "manifesto.json")
    tmp = cam + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, cam)
    for e in etapas:
        os.makedirs(_dir(run_dir, "dados", e), exist_ok=True)
        os.makedirs(_dir(run_dir, "notas", e), exist_ok=True)
    print("run em %s · %d itens · %d partes · etapas: %s"
          % (run_dir, len(itens), len(reparte), ", ".join(etapas)))
    for p, fatia in reparte.items():
        print("   parte %-3s %d itens" % (p, len(fatia)))


def cmd_put(a):
    man = _manifesto(a.run)
    _confere(man, a.etapa)
    bruto = a.dados
    if a.de_arquivo:
        with open(a.de_arquivo, encoding="utf-8-sig") as f:
            bruto = f.read()
    if bruto is None:
        bruto = sys.stdin.read()
    try:
        o = json.loads(bruto)
    except json.JSONDecodeError as e:
        raise SystemExit("erro: os dados não são JSON válido — %s" % e)
    if not isinstance(o, dict):
        raise SystemExit("erro: os dados têm de ser um objeto JSON, não %s" % type(o).__name__)

    chave = a.chave or o.get("chave") or o.get("_chave")
    if not chave:
        raise SystemExit("erro: falta --chave")
    chave = str(chave)
    if chave not in man["itens"]:
        raise SystemExit("erro: '%s' não está no manifesto — chave errada ou item novo "
                         "(refaça o init se o escopo mudou)" % chave)

    parte = str(a.parte) if a.parte else next(
        (p for p, f in man["partes"].items() if chave in f), "1")
    _confere(man, parte=parte)
    o["_chave"] = chave
    o["_etapa"] = a.etapa
    o["_em"] = dt.datetime.now().isoformat(timespec="seconds")
    _append(_jsonl(a.run, a.etapa, parte), json.dumps(o, ensure_ascii=False) + "\n")

    feitos, _ = _ler_jsonl(_jsonl(a.run, a.etapa, parte))
    esperados = man["partes"].get(parte, [])
    print("gravado %s · parte %s: %d de %d" % (chave, parte, len(feitos), len(esperados)))


def cmd_todo(a):
    man = _manifesto(a.run)
    _confere(man, a.etapa)
    if a.parte:
        _confere(man, parte=a.parte)
    partes = [str(a.parte)] if a.parte else sorted(man["partes"], key=lambda x: int(x))
    total_falta = []
    for p in partes:
        esperados = man["partes"].get(p, [])
        feitos, ruins = _ler_jsonl(_jsonl(a.run, a.etapa, p))
        faltam = [i for i in esperados if i not in feitos]
        total_falta += faltam
        print("parte %-3s %s: %d de %d feitos%s"
              % (p, a.etapa, len(feitos), len(esperados),
                 " · %d linha(s) corrompida(s) ignorada(s)" % ruins if ruins else ""))
        if faltam and (a.parte or len(faltam) <= 40):
            print("   faltam: %s" % " ".join(faltam))
    if not total_falta:
        print("\nnada faltando em %s — pode fechar" % a.etapa)
    else:
        print("\n%d itens faltando em %s" % (len(total_falta), a.etapa))
    return total_falta


def cmd_status(a):
    man = _manifesto(a.run)
    n = len(man["itens"])
    print("%s · %d itens · criado em %s" % (a.run, n, man["criado"]))
    if man.get("descricao"):
        print("  %s" % man["descricao"])
    print()
    larg = max(len(e) for e in man["etapas"])
    for e in man["etapas"]:
        feitos, ruins = _todos_registros(a.run, e)
        pron = sum(1 for i in man["itens"] if i in feitos)
        pct = 100 * pron / n if n else 0
        barra = "█" * int(pct / 4) + "·" * (25 - int(pct / 4))
        print("  %-*s %s %4d/%d  %5.1f%%%s"
              % (larg, e, barra, pron, n, pct,
                 "  ⚠ %d linha(s) ruim(ns)" % ruins if ruins else ""))
    print()
    for e in man["etapas"]:
        feitos, _ = _todos_registros(a.run, e)
        faltam = [i for i in man["itens"] if i not in feitos]
        if faltam:
            print("  %s: faltam %d (%s%s)"
                  % (e, len(faltam), " ".join(faltam[:8]),
                     " …" if len(faltam) > 8 else ""))


def cmd_nota(a):
    man = _manifesto(a.run)
    _confere(man, a.etapa, a.parte)
    cam = _dir(a.run, "notas", a.etapa, "%s.log" % (a.parte or "geral"))
    _append(cam, "%s  %s\n" % (dt.datetime.now().isoformat(timespec="seconds"),
                               " ".join(a.texto)))
    print("anotado em %s" % cam)


def cmd_ler(a):
    _confere(_manifesto(a.run), a.etapa)
    feitos, _ = _todos_registros(a.run, a.etapa)
    o = feitos.get(str(a.chave))
    if not o:
        print("nada gravado para %s em %s" % (a.chave, a.etapa))
        return
    print(json.dumps(o, ensure_ascii=False, indent=1))


def cmd_fecha(a):
    man = _manifesto(a.run)
    _confere(man, a.etapa)
    feitos, ruins = _todos_registros(a.run, a.etapa)
    faltam = [i for i in man["itens"] if i not in feitos]
    if faltam and not a.parcial:
        raise SystemExit("erro: %d itens sem registro — rode `todo` para ver, ou use "
                         "--parcial para fechar assim mesmo" % len(faltam))
    saida = a.saida or _dir(a.run, "%s.json" % a.etapa)
    ordenado = [feitos[i] for i in man["itens"] if i in feitos]
    tmp = saida + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ordenado, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, saida)
    print("fechado: %d de %d itens em %s%s%s"
          % (len(ordenado), len(man["itens"]), saida,
             " · %d faltando" % len(faltam) if faltam else "",
             " · %d linhas ruins descartadas" % ruins if ruins else ""))


def cmd_sweep(a):
    man = _manifesto(a.run)
    achou = False
    for e in man["etapas"]:
        d = _dir(a.run, "dados", e)
        if not os.path.isdir(d):
            continue
        for nome in sorted(os.listdir(d)):
            if not nome.endswith(".jsonl"):
                continue
            cam = os.path.join(d, nome)
            _, ruins = _ler_jsonl(cam)
            if ruins:
                achou = True
                print("⚠ %s: %d linha(s) corrompida(s) — ignoradas na leitura." % (cam, ruins))
                print("   os itens delas aparecem como faltando em `todo`; refaça-os.")
    if not achou:
        print("nenhuma linha corrompida.")


# ------------------------------------------------------------------ cli
def main():
    ap = argparse.ArgumentParser(description="trabalho longo que não se perde")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="cria o run e o manifesto")
    p.add_argument("run")
    p.add_argument("--itens")
    p.add_argument("--itens-de")
    p.add_argument("--itens-json")
    p.add_argument("--etapas")
    p.add_argument("--partes", type=int, default=1)
    p.add_argument("--descricao")
    p.add_argument("--forcar", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("put", help="grava o resultado de um item")
    p.add_argument("run"); p.add_argument("etapa")
    p.add_argument("--chave"); p.add_argument("--parte")
    p.add_argument("--dados"); p.add_argument("--de-arquivo")
    p.set_defaults(fn=cmd_put)

    p = sub.add_parser("todo", help="o que ainda falta")
    p.add_argument("run"); p.add_argument("etapa"); p.add_argument("--parte")
    p.set_defaults(fn=cmd_todo)

    p = sub.add_parser("status", help="painel de todas as etapas")
    p.add_argument("run")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("nota", help="diário de bordo")
    p.add_argument("run"); p.add_argument("etapa")
    p.add_argument("--parte"); p.add_argument("texto", nargs="+")
    p.set_defaults(fn=cmd_nota)

    p = sub.add_parser("ler", help="o que já foi gravado para um item")
    p.add_argument("run"); p.add_argument("etapa"); p.add_argument("--chave", required=True)
    p.set_defaults(fn=cmd_ler)

    p = sub.add_parser("fecha", help="consolida a etapa num JSON")
    p.add_argument("run"); p.add_argument("etapa")
    p.add_argument("-o", "--saida"); p.add_argument("--parcial", action="store_true")
    p.set_defaults(fn=cmd_fecha)

    p = sub.add_parser("sweep", help="procura linha corrompida")
    p.add_argument("run")
    p.set_defaults(fn=cmd_sweep)

    a = ap.parse_args()
    fora = a.fn(a)
    # `todo` sai com rc 1 quando falta item, para o agente poder encadear com &&
    if a.cmd == "todo" and fora:
        sys.exit(1)


if __name__ == "__main__":
    main()
