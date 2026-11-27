// Roda as funções reais de public/empresas-atlas.js que classificam os municípios de uma empresa pela origem do vínculo (munsPorOrigem,
// emDisponibilidade) e o rótulo da situação dos processos (rotuloStatus), sobre o pacote real data/empresas/atlas_empresas.json, para TODAS as
// empresas. Imprime um JSON com os códigos IBGE por origem; tests/test_atlas_empresas.py (AuditoriaCriticaTests) compara com o oráculo das
// fontes (tests/oraculo_empresas.py), que é outro caminho de código.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const RAIZ = path.resolve(__dirname, '..', '..');
const src = fs.readFileSync(path.join(RAIZ, 'public', 'empresas-atlas.js'), 'utf8');
const trecho = (ini, fim) => { const a = src.indexOf(ini); if (a < 0) throw new Error('não achei ' + ini); return src.slice(a, src.indexOf(fim, a)); };
const D = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', 'empresas', 'atlas_empresas.json'), 'utf8'));
const PC = {}; D.processos.cols.forEach((c, i) => { PC[c] = i; });
const procsPorEmp = new Map(), cfemPorEmp = new Map();
D.processos.rows.forEach((r, k) => { if (r[PC.empresa] >= 0) { if (!procsPorEmp.has(r[PC.empresa])) procsPorEmp.set(r[PC.empresa], []); procsPorEmp.get(r[PC.empresa]).push(k); } });
D.cfem.rows.forEach(r => { if (!cfemPorEmp.has(r[0])) cfemPorEmp.set(r[0], []); cfemPorEmp.get(r[0]).push(r); });
const ctx = {D, PC, procsPorEmp, cfemPorEmp, S: {}, t: k => k, norm: s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()};
vm.createContext(ctx);
vm.runInContext(trecho('function rotuloStatus(', 'function munsPorOrigem(') + trecho('function munsPorOrigem(', '// origem do vínculo de UM município')
  + 'this.munsPorOrigem=munsPorOrigem;this.rotuloStatus=rotuloStatus;', ctx);
const ibge = k => String(D.dims.mun[k][0]);
const out = {};
for (const e of D.empresas) {
  const o = ctx.munsPorOrigem(e);
  out[e.cnpj] = {op: o.op.map(ibge).sort(), vig: o.vig.map(ibge).sort(), disp: o.disp.map(ibge).sort(), cfem: o.cfem.map(ibge).sort(), total: o.total};
}
console.log(JSON.stringify({empresas: out, status: D.dims.status.map((_, s) => ctx.rotuloStatus(s))}));
