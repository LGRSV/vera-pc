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
import json
import os
import sys

ETAPAS_PADRAO = ["leitura", "revisao", "conferencia"]


# ------------------------------------------------------------------ caminhos
def _dir(run, *p):
    return os.path.join(run, *p)


def _jsonl(run, etapa, parte):
    return _dir(run, "dados", etapa, "%s.jsonl" % parte)


def _manifesto(run):
    cam = _dir(run, "manifesto.json")
    if not os.path.exists(cam):
        raise SystemExit("erro: %s não existe — rode `init` primeiro" % cam)
    with open(cam) as f:
        return json.load(f)


# ------------------------------------------------------------------ escrita
def _append(cam, linha):
    """Um write(), O_APPEND, fsync. É aqui que mora a garantia.

    E um detalhe que já custou um registro no teste: se o processo anterior morreu no meio
    de uma gravação, o arquivo termina **sem `\n`** — a última linha ficou pela metade. Sem
    fechar essa linha primeiro, o registro novo cola nela e os DOIS viram lixo: perde-se o
    fragmento *e* o dado bom que acabou de chegar. Então, antes de escrever, se o arquivo
    não termina em `\n`, põe-se um."""
    os.makedirs(os.path.dirname(cam), exist_ok=True)
    fd = os.open(cam, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        tam = os.lseek(fd, 0, os.SEEK_END)
        if tam:
            os.lseek(fd, tam - 1, os.SEEK_SET)
            if os.read(fd, 1) != b"\n":
                linha = "\n" + linha      # fecha a linha quebrada de quem morreu antes
        os.write(fd, linha.encode("utf-8"))   # O_APPEND: vai para o fim, sem corrida
        os.fsync(fd)
    finally:
        os.close(fd)


def _ler_jsonl(cam):
    """Devolve (registros_por_chave, n_linhas_ruins).

    Tolera linha truncada — que é exatamente o que sobra quando o processo morre no meio
    de uma gravação. A linha quebrada é descartada; o resto do arquivo continua bom."""
    fora, ruins = {}, 0
    if not os.path.exists(cam):
        return fora, ruins
    with open(cam, errors="replace") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                o = json.loads(linha)
            except json.JSONDecodeError:
                ruins += 1
                continue
            k = o.get("_chave")
            if k is not None:
                fora[k] = o          # último vence
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
        fora.update(r)
        ruins += b
    return fora, ruins


# ------------------------------------------------------------------ comandos
def cmd_init(a):
    itens = []
    if a.itens:
        itens = [x.strip() for x in a.itens.split(",") if x.strip()]
    elif a.itens_de:
        with open(a.itens_de) as f:
            itens = [x.strip() for x in f if x.strip()]
    elif a.itens_json:
        with open(a.itens_json) as f:
            d = json.load(f)
        itens = [str(x) for x in (d if isinstance(d, list) else d.get("itens", []))]
    if not itens:
        raise SystemExit("erro: nenhum item — use --itens, --itens-de ou --itens-json")
    if len(set(itens)) != len(itens):
        vistos, dup = set(), set()
        for i in itens:
            (dup if i in vistos else vistos).add(i)
        raise SystemExit("erro: itens repetidos no manifesto: %s" % ", ".join(sorted(dup)[:5]))

    etapas = [x.strip() for x in (a.etapas or ",".join(ETAPAS_PADRAO)).split(",") if x.strip()]
    partes = max(1, a.partes)
    tam = -(-len(itens) // partes)
    reparte = {}
    for n in range(partes):
        fatia = itens[n * tam:(n + 1) * tam]
        if fatia:
            reparte[str(n + 1)] = fatia

    os.makedirs(run_dir := a.run, exist_ok=True)
    man = {"criado": dt.datetime.now().isoformat(timespec="seconds"),
           "itens": itens, "etapas": etapas, "partes": reparte,
           "descricao": a.descricao or ""}
    cam = _dir(run_dir, "manifesto.json")
    tmp = cam + ".tmp"
    with open(tmp, "w") as f:
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
    if a.etapa not in man["etapas"]:
        raise SystemExit("erro: etapa '%s' não está no manifesto (%s)"
                         % (a.etapa, ", ".join(man["etapas"])))
    bruto = a.dados
    if a.de_arquivo:
        with open(a.de_arquivo) as f:
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
    o["_chave"] = chave
    o["_etapa"] = a.etapa
    o["_em"] = dt.datetime.now().isoformat(timespec="seconds")
    _append(_jsonl(a.run, a.etapa, parte), json.dumps(o, ensure_ascii=False) + "\n")

    feitos, _ = _ler_jsonl(_jsonl(a.run, a.etapa, parte))
    esperados = man["partes"].get(parte, [])
    print("gravado %s · parte %s: %d de %d" % (chave, parte, len(feitos), len(esperados)))


def cmd_todo(a):
    man = _manifesto(a.run)
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
    cam = _dir(a.run, "notas", a.etapa, "%s.log" % (a.parte or "geral"))
    _append(cam, "%s  %s\n" % (dt.datetime.now().isoformat(timespec="seconds"),
                               " ".join(a.texto)))
    print("anotado em %s" % cam)


def cmd_ler(a):
    feitos, _ = _todos_registros(a.run, a.etapa)
    o = feitos.get(str(a.chave))
    if not o:
        print("nada gravado para %s em %s" % (a.chave, a.etapa))
        return
    print(json.dumps(o, ensure_ascii=False, indent=1))


def cmd_fecha(a):
    man = _manifesto(a.run)
    feitos, ruins = _todos_registros(a.run, a.etapa)
    faltam = [i for i in man["itens"] if i not in feitos]
    if faltam and not a.parcial:
        raise SystemExit("erro: %d itens sem registro — rode `todo` para ver, ou use "
                         "--parcial para fechar assim mesmo" % len(faltam))
    saida = a.saida or _dir(a.run, "%s.json" % a.etapa)
    ordenado = [feitos[i] for i in man["itens"] if i in feitos]
    tmp = saida + ".tmp"
    with open(tmp, "w") as f:
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
    a.fn(a)


if __name__ == "__main__":
    main()
