#!/bin/bash
# Fecha o ciclo da revisão: consolida, aplica, refaz o painel e commita.
# O artifact é republicado à parte (só o Claude tem a ferramenta).
set -e
cd /home/user/vera-pc
S=.claude/skills/checkpoint/scripts/ckpt.py
python3 $S fecha .analise/revisao-2425 revisao --parcial -o .analise/revisao-2425/revisao.json | tail -1
python3 scripts/aplica_revisao.py | tail -12
python3 scripts/painel_falha_completa.py
cp scratchpad/painel_falha_completa.html \
   /tmp/claude-0/-home-user-vera-pc/c3d5c486-5de5-52ac-a54a-1691b373e364/scratchpad/painel_falha_dcmd.html
git add -A
git commit -q -m "Ciclo da revisao: consolida, aplica e refaz o painel

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KYbdJsSNgLt2EhkdschjHa" 2>/dev/null || echo "(nada novo a commitar)"
git push -q origin claude/analise-equipamentos-especiais-apu6vj 2>&1 | tail -1 || true
python3 $S status .analise/revisao-2425 | sed -n '3,4p'
