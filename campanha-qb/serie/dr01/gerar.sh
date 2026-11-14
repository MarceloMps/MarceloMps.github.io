#!/usr/bin/env bash
# Gera as três variantes de gancho (dr01a, dr01b, dr01c) a partir de dr01/ep.html.
# Uso: bash dr01/gerar.sh   e depois   RATE=+18% bash build_ep.sh dr01a   (idem b, c)
set -euo pipefail
cd "$(dirname "$0")/.."
for v in a b c; do
  d=dr01$v; mkdir -p $d
  cp dr01/ep.html $d/ep.html
  echo "window.VAR='$v';" > $d/variante.js
  node -e "
const s=require('fs').readFileSync('dr01/ep.html','utf8');
const hook=s.match(new RegExp(\"  $v:\\\\{vo:'([^']+)'\"))[1];
const body=[...s.matchAll(/^  (p1|p2|s1|s2|o1|c1):'([^']+)'/gm)].map(m=>m[1]+'|'+m[2]);
require('fs').writeFileSync('$d/narracao.txt',['g1|'+hook,...body].join('\n')+'\n');
require('fs').writeFileSync('$d/takes.txt',['g1','p1','p2','s1','s2','o1','c1'].map(k=>k+'|'+k).join('\n')+'\n');"
done
echo ok
