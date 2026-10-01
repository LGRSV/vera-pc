#!/usr/bin/env python3
"""Valida e grava, um put por ativo, a partir de um JSON com lista de vereditos."""
import json, sys, os, subprocess
SP=os.path.dirname(os.path.abspath(__file__)); import os as _o; SP=SP if _o.path.exists(SP+'/estado_2425.json') else '/home/user/vera-pc/.analise/revisao-2425/ferramentas'
RUN='/home/user/vera-pc/.analise/revisao-2425'
S='/home/user/vera-pc/.claude/skills/checkpoint/scripts/ckpt.py'
ROT={'tanque','controle','celula','rele','completo','furto','trafo auxiliar','chave faca','para-raio','fusivel','bateria','cabo','aterramento','telecom','poste','poda','ajuste de protecao','comissionamento','obra nova','melhoria','sem defeito','nao identificado'}
E=json.load(open(SP+'/estado_2425.json'))['cadeias']
T=json.load(open(SP+'/tiers_2425.json'))
L=json.load(open(sys.argv[1]))
erros=[]
for o in L:
    a=o['ativo']; esperadas=set(T[a]['cadeias'])
    vistas={d['cadeia'] for d in o['demandas']}
    if vistas!=esperadas: erros.append('%s: cadeias %s ≠ esperadas %s' % (a, sorted(vistas), sorted(esperadas)))
    for d in o['demandas']:
        if d.get('categoria_final') not in ROT: erros.append('%s %s: rótulo inválido %r' % (a, d['cadeia'], d.get('categoria_final')))
        for k in ('mantem','porque','confianca'):
            if k not in d: erros.append('%s %s: falta %s' % (a, d['cadeia'], k))
        if d.get('duplicata_de') and d['duplicata_de'] not in {c for c in T[a]['cadeias']} and d['duplicata_de'] not in E and not d.get('duplicata_fora_do_escopo'):
            # permite apontar cadeia de outro ano do mesmo ativo (fora do estado): exige marcação explícita
            erros.append('%s %s: duplicata_de %r não é cadeia conhecida (marque duplicata_fora_do_escopo=true se for de outro ano)' % (a, d['cadeia'], d['duplicata_de']))
        ant=E.get(d['cadeia'])
        if ant:
            d.setdefault('categoria_anterior', ant['categoria_vigente']); d.setdefault('fonte_anterior', ant['fonte'])
            if d['mantem'] and d['categoria_final']!=ant['categoria_vigente']: erros.append('%s %s: mantem=true mas rótulo mudou %s→%s' % (a, d['cadeia'], ant['categoria_vigente'], d['categoria_final']))
            if not d['mantem'] and d['categoria_final']==ant['categoria_vigente'] and not d.get('duplicata_de') and not d.get('aberta_por_engano'): erros.append('%s %s: mantem=false mas rótulo igual e sem duplicata/engano' % (a, d['cadeia']))
        else:
            d.setdefault('categoria_anterior', None); d.setdefault('fonte_anterior', None)
    o.setdefault('tier', T[a]['tier'])
if erros:
    print('ERROS — nada gravado:'); print('\n'.join(erros)); sys.exit(1)
for o in L:
    tmp=SP+'/_put.json'; json.dump(o, open(tmp,'w'), ensure_ascii=False)
    r=subprocess.run(['python3',S,'put',RUN,'revisao','--chave',o['ativo'],'--de-arquivo',tmp],capture_output=True,text=True)
    print(r.stdout.strip() or r.stderr.strip())
