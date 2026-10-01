import json, glob, subprocess, sys
SP='/home/user/vera-pc/.analise/revisao-2425/ferramentas'
RUN='/home/user/vera-pc/.analise/revisao-2425'
kb=int(sys.argv[1]) if len(sys.argv)>1 else 40
ordem=json.load(open(SP+'/ordem_A.json'))
feitos=set()
for f in glob.glob(RUN+'/dados/revisao/*.jsonl'):
    for ln in open(f):
        try: feitos.add(json.loads(ln)['_chave'])
        except: pass
cand=[a for a in ordem if a not in feitos][:12]
txt=subprocess.run(['python3',SP+'/pack.py']+cand,capture_output=True,text=True).stdout
sep='\n\n################################################################################\n'
blocos=txt.split(sep); acc=''; n=0
for i,b in enumerate(blocos):
    piece=(b if i==0 else sep+b)
    if acc and len((acc+piece).encode())>kb*1024: break
    acc+=piece; n+=1
open(SP+'/pk.txt','w').write(acc)
print(n,"ativos ·",len(acc.encode())//1024,"KB · restam na ordem A:",len([a for a in ordem if a not in feitos]))
