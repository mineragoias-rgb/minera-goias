// Roda public/empresas.js (Análises da aba Empresas) com um DOM mínimo e o pacote real data/empresas/empresas.json, e confere o escopo:
// empresa fora das 10 com produção declarada NÃO pode fazer o painel voltar a mostrar todas as empresas (defeito da versão anterior,
// em que a sincronização limpava o filtro e o painel inteiro reaparecia). Usado por tests/test_atlas_empresas.py; imprime um JSON.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const RAIZ = path.resolve(__dirname, '..', '..');

const els = new Map();
function elemento(id) {
  return {id, hidden: false, innerHTML: '', textContent: '', value: '', disabled: false,
    onclick: null, onchange: null, oninput: null, dataset: {},
    querySelector() { return elemento('?'); }, querySelectorAll() { return []; },
    addEventListener() {}, setAttribute() {}, removeAttribute() {}, closest() { return elemento('?'); }};
}
const documento = {getElementById(id) { if (!els.has(id)) els.set(id, elemento(id)); return els.get(id); },
  createElement() { return Object.assign(elemento('a'), {click() {}, remove() {}}); }, body: {appendChild() {}}};
const contexto = {
  document: documento, window: {}, console, setTimeout: f => f(), clearTimeout() {}, Blob: function () {}, URL: {createObjectURL() { return ''; }, revokeObjectURL() {}},
  esc: s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c])),
  t: (k, v) => k + (v ? JSON.stringify(v) : ''),
  I18N: {num: (v, o) => Number(v).toFixed(o && o.maximumFractionDigits || 0)},
};
contexto.window = contexto;
vm.createContext(contexto);
vm.runInContext(fs.readFileSync(path.join(RAIZ, 'public', 'empresas.js'), 'utf8'), contexto);
const A = contexto.window.EmpresasAnalises;
const dados = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', 'empresas', 'empresas.json'), 'utf8'));
const el = id => documento.getElementById(id);
A.definirResumo(cnpj => `<p>resumo ${cnpj}</p>`);
A.iniciar(dados);

const estado = () => ({
  declarada: {indisp: !el('ep-indisp').hidden, conteudo: !el('empresas-content').hidden, tabela: el('ep-tabela').innerHTML,
    indispHtml: el('ep-indisp').innerHTML, contagem: el('ep-count').textContent},
  estimada: {indisp: !el('es-indisp').hidden, conteudo: !el('es-content').hidden, tabela: el('es-tabela').innerHTML,
    indispHtml: el('es-indisp').innerHTML, contagem: el('es-count').textContent, buscaVisivel: !el('es-busca-box').hidden},
});
const linhasTabela = html => (html.match(/<tr>/g) || []).length - 1;   // menos o cabeçalho
const cnpjsNaTabela = html => [...new Set([...html.matchAll(/<td>(\d{8})<\/td>/g)].map(m => m[1]))];
const out = {};
out.todas = estado();
const dez = [...new Set(dados.linhas.map(l => l.cnpj_raiz))];
// empresa fora das 10 (Ciplan: tem CFEM e estimativa AMB × CFEM, mas não produção declarada)
A.escopo({cnpj: '00057240', nome: 'CIPLAN CIMENTO PLANALTO SA', escopo: 'empresa'});
out.fora = estado();
out.fora.cnpjsEstimada = cnpjsNaTabela(out.fora.estimada.tabela);
// empresa dentro das 10
A.escopo({cnpj: '26108898', nome: 'CMOC', escopo: 'empresa'});
out.dentro = estado();
out.dentro.linhasDeclaradas = linhasTabela(out.dentro.declarada.tabela);
out.dentro.linhasDeclaradasEsperadas = dados.linhas.filter(l => l.cnpj_raiz === '26108898').length;
out.dentro.cnpjsEstimada = cnpjsNaTabela(out.dentro.estimada.tabela);
// empresa sem nenhum dado nas duas análises (CNPJ raiz que não está em nenhuma)
A.escopo({cnpj: '99999999', nome: 'SEM DADO', escopo: 'empresa'});
out.semDado = estado();
// volta para todas: as 10 empresas reaparecem, agora porque o usuário pediu
A.escopo({cnpj: '99999999', nome: 'SEM DADO', escopo: 'todas'});
out.devolta = estado();
out.devolta.linhasDeclaradas = linhasTabela(out.devolta.declarada.tabela);
out.totalDeclaradas = dados.linhas.length;
out.dez = dez.length;
process.stdout.write(JSON.stringify(out));
