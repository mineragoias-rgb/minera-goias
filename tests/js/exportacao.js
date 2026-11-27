// Roda public/empresas-exportar.js (exportações da aba Empresas) no Node, sem DOM: grava um CSV e um XLSX com casos difíceis
// (fórmula maliciosa, CNPJ com zero à esquerda, decimais, negativos, vazio, quebra de linha, aspas, ponto e vírgula, acentos) na pasta
// do argumento e confere a comparabilidade da produção declarada com o pacote real data/empresas/atlas_empresas.json.
// Usado por tests/test_atlas_empresas.py (ExportacaoTests), que lê os arquivos gravados; imprime um JSON.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const RAIZ = path.resolve(__dirname, '..', '..');
const SAIDA = process.argv[2];
const ctx = {TextEncoder, console};
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(RAIZ, 'public', 'empresas-exportar.js'), 'utf8'), ctx);
const X = ctx.window.EmpresasExportar;

const colunas = [{id: 'cnpj_raiz', tipo: 'id'}, {id: 'empresa', tipo: 'texto'}, {id: 'valor', tipo: 'numero'}, {id: 'lat', tipo: 'numero'},
  {id: 'n', tipo: 'inteiro'}, {id: 'ok', tipo: 'bool'}, {id: 'periodo', tipo: 'texto'}];
const MALICIOSOS = ['=1+1', '+SOMA(A1:A2)', '-2+3', '@cmd', '\t=1', '\r=1', '=HYPERLINK("http://exemplo.invalid","x")'];
const linhas = [
  {cnpj_raiz: '08842895', empresa: 'Mineração “Ação” — São Luís; linha\nnova', valor: 12.345, lat: -16.1234, n: 7, ok: true, periodo: '2025-Q3'},
  {cnpj_raiz: '00057240', empresa: 'Sem dado', valor: null, lat: '', n: NaN, ok: false, periodo: '2024'},
  {cnpj_raiz: '26108898', empresa: 'Grande', valor: 1234567.891234, lat: -0.000001, n: 0, ok: false, periodo: '2022-2025'},
  ...MALICIOSOS.map((m, k) => ({cnpj_raiz: String(10000000 + k), empresa: m, valor: -k - 0.5, lat: null, n: -k, ok: true, periodo: m})),
];
const tabela = {colunas, linhas};
fs.mkdirSync(SAIDA, {recursive: true});
fs.writeFileSync(path.join(SAIDA, 'teste.csv'), X.csv(tabela));
fs.writeFileSync(path.join(SAIDA, 'teste.xlsx'), X.xlsx([{nome: 'Dados', ...tabela}, {nome: 'Colunas', ...X.dicionario(colunas, {cnpj_raiz: 'CNPJ raiz'})},
  {nome: 'Metadados', ...X.metadados([['gerado_em', '2026-11-26'], ['filtro', {mineral: 'Fosfato'}], ['vazio', null]])}], new Date(2026, 10, 26, 12, 0, 0)));

// comparabilidade da produção declarada, com os registros reais
const A = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', 'empresas', 'atlas_empresas.json'), 'utf8'));
const porCnpj = c => { const e = A.empresas.find(x => x.cnpj === c); return (A.detalhes[String(e.i)] || {producao: []}).producao; };
const resumo = gs => gs.map(g => ({chave: g.chave, empresas: g.empresas, duplicado: g.duplicado, n: g.por.map(r => r.length)}));
const maracaAmarillo = X.gruposDeclarada([porCnpj('86902053'), porCnpj('42799486')]);
const cmocMosaic = X.gruposDeclarada([porCnpj('26108898'), porCnpj('33931486')]);
const todas = A.empresas.filter(e => A.detalhes[String(e.i)]).map(e => porCnpj(e.cnpj));
const tudo = X.gruposDeclarada(todas);
// nenhum registro some: a soma dos registros dos grupos é a soma dos registros de entrada
const contagem = gs => gs.reduce((s, g) => s + g.por.reduce((t, r) => t + r.length, 0), 0);
// grupos que juntam empresas: todos os campos da chave iguais em todos os registros
const camposIguais = gs => gs.every(g => g.por.flat().every(p => X.CAMPOS_DECLARADA.every(c => String(p[c] ?? '') === String(g.ref[c] ?? ''))));
console.log(JSON.stringify({
  celulas: {formula: X.celulaCsv('=1+1', 'texto'), negativo: X.celulaCsv(-16.1234, 'numero'), id: X.celulaCsv('08842895', 'id'), vazio: X.celulaCsv(null, 'numero'),
    zero: X.celulaCsv(0, 'inteiro'), nan: X.celulaCsv(NaN, 'numero'), textoNumero: X.celulaCsv('12.5', 'numero'), bool: X.celulaCsv(true, 'bool')},
  maiusculo: {mesmosMeses: X.indiceMaior([10, 20, 5], {meses: [12, 12, 12]}), mesesDiferentes: X.indiceMaior([10, 20, 5], {meses: [8, 9, 9]}),
    umValor: X.indiceMaior([10, null, null]), empate: X.indiceMaior([20, 20, 5]), semMeses: X.indiceMaior([10, 20, null])},
  maracaAmarillo: resumo(maracaAmarillo), cmocMosaic: resumo(cmocMosaic),
  todas: {entrada: todas.reduce((s, r) => s + r.length, 0), nosGrupos: contagem(tudo), camposIguais: camposIguais(tudo), grupos: tudo.length},
  crc: X.crc32(new TextEncoder().encode('123456789')),
}));
