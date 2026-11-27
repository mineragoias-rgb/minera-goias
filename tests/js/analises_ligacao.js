// Roda public/empresas.js (Análises da aba Empresas) com um DOM mínimo e o pacote real data/empresas/empresas.json, e confere o atalho
// nome da empresa → dossiê: só com CNPJ raiz do índice da aba, nunca por nome; dois CNPJs com o MESMO nome viram duas barras e dois
// atalhos; pessoa física e linhas sem CNPJ continuam texto; trocar a empresa selecionada com "todas as empresas" no escopo não mexe nos
// filtros da análise. Usado por tests/test_atlas_empresas.py (AjustesFinaisTests); imprime um JSON.
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
const el = id => documento.getElementById(id);

const dados = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', 'empresas', 'empresas.json'), 'utf8'));
const atlas = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', 'empresas', 'atlas_empresas.json'), 'utf8'));
const C = dados.estimada.colunas, ix = Object.fromEntries(C.map((c, i) => [c, i]));
// caso de teste: um segundo CNPJ com o MESMO nome de uma empresa real, no mesmo mineral, ano e base
const modelo = dados.estimada.linhas.find(r => r[ix.ano] === 2023 && r[ix.mineral] === 'Ouro' && r[ix.base] === 'beneficiada' && /^\d{8}$/.test(r[ix.cnpj_raiz]));
const gemeo = [...modelo];
gemeo[ix.cnpj_raiz] = '99999901'; gemeo[ix.producao_t] = modelo[ix.producao_t] / 2; gemeo[ix.cfem_brl] = (modelo[ix.cfem_brl] || 0) / 2;
dados.estimada.linhas.push(gemeo);
// um CNPJ válido que NÃO está no índice da aba
const fora = [...modelo];
fora[ix.cnpj_raiz] = '99999902'; fora[ix.empresa] = 'EMPRESA FORA DO INDICE'; fora[ix.producao_t] = modelo[ix.producao_t] / 3;
dados.estimada.linhas.push(fora);
const indice = new Set(atlas.empresas.map(e => e.cnpj));
indice.add('99999901');

A.definirResumo(() => '');
A.definirLigacao({existe: c => indice.has(c), nome: () => ''});
A.iniciar(dados);
el('es-ano').value = '2023'; el('es-base').value = 'beneficiada'; el('es-min').value = 'Ouro';
A.escopo({cnpj: null, nome: '', escopo: 'todas'});
const atalhos = html => [...html.matchAll(/data-emp-cnpj="(\d{8})"[^>]*>([^<]*)</g)].map(m => ({cnpj: m[1], rotulo: m[2]}));
const out = {};
out.modelo = {cnpj: modelo[ix.cnpj_raiz], nome: modelo[ix.empresa]};
out.barras = atalhos(el('es-barras').innerHTML);
out.tabela = atalhos(el('es-tabela').innerHTML);
out.textoTabela = el('es-tabela').innerHTML;
out.foraNaTabela = /EMPRESA FORA DO INDICE/.test(el('es-tabela').innerHTML);
out.coberturaSemAtalho = !/data-emp-cnpj/.test(el('es-cobertura').innerHTML);
out.pfComAtalho = /data-emp-cnpj="[^"]*"[^>]*>pessoa f/i.test(el('es-tabela').innerHTML + el('es-barras').innerHTML);
// sem mineral: barras de CFEM por empresa, também pela chave
el('es-min').value = '';
A.escopo({cnpj: null, nome: '', escopo: 'todas'});
out.barrasCfem = atalhos(el('es-barras').innerHTML);
out.pfNasBarrasCfem = /pessoa f/i.test(el('es-barras').innerHTML);
// trocar a empresa selecionada com "todas as empresas" no escopo: filtros ficam
el('es-ano').value = '2023'; el('es-base').value = ''; el('es-min').value = 'Ouro';
A.escopo({cnpj: '26108898', nome: 'CMOC', escopo: 'todas'});
out.filtrosAposTrocaTodas = {ano: el('es-ano').value, base: el('es-base').value, min: el('es-min').value};
// pedir explicitamente "empresa": a análise se ajusta à empresa (comportamento de antes, mantido)
A.escopo({cnpj: '26108898', nome: 'CMOC', escopo: 'empresa'});
out.filtrosAposEscopoEmpresa = {ano: el('es-ano').value, base: el('es-base').value, min: el('es-min').value};
// declarada: as 10 empresas têm atalho na tabela
A.escopo({cnpj: '26108898', nome: 'CMOC', escopo: 'todas'});
out.declaradaTabela = [...new Set(atalhos(el('ep-tabela').innerHTML).map(x => x.cnpj))];
out.declaradaEsperada = [...new Set(dados.linhas.map(l => l.cnpj_raiz))];
out.declaradaEnergia = atalhos(el('ep-energia').innerHTML).length;
// sem a ligação da aba (página sem o Atlas), nada vira atalho
A.definirLigacao(null);
out.semLigacao = !/data-emp-cnpj/.test(el('es-tabela').innerHTML + el('ep-tabela').innerHTML);
process.stdout.write(JSON.stringify(out));
