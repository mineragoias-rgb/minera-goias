// Testes do shapefile por camada do Mapa Mineral (public/mapa-shp.js): formato .shp/.shx/.dbf e zip, lidos de volta aqui
// com leitores mínimos escritos a partir das especificações, e camadas reais de data/mapa decodificadas como no navegador.
// Execução: node tests/mapa-shp.test.js
'use strict';
const fs = require('fs'), path = require('path');
const RAIZ = path.join(__dirname, '..');
const S = require(path.join(RAIZ, 'public', 'mapa-shp.js'));
const M = require(path.join(RAIZ, 'public', 'mapa-dados.js'));
const lerJson = p => JSON.parse(fs.readFileSync(path.join(RAIZ, p), 'utf8'));

const falhas = [];
let total = 0;
function ok(nome, condicao, detalhe) {
 total++;
 if (!condicao) falhas.push(nome + (detalhe !== undefined ? ' — ' + detalhe : ''));
}
const DATA = new Date(2026, 9, 22, 10, 30, 0);
const dv = b => new DataView(b.buffer, b.byteOffset, b.byteLength);
const sinal = a => { let s = 0; for (let i = 0; i + 1 < a.length; i++) s += a[i][0] * a[i + 1][1] - a[i + 1][0] * a[i][1]; return s };

// Leitor de .shp/.shx (ESRI 1998): cabeçalho, registros e índice.
function lerShp(shp, shx) {
 const v = dv(shp), x = dv(shx), tipo = v.getInt32(32, true), recs = [];
 const cab = {codigo: v.getInt32(0), palavras: v.getInt32(24), versao: v.getInt32(28, true), tipo,
  caixa: [0, 1, 2, 3].map(j => v.getFloat64(36 + 8 * j, true)), codigoShx: x.getInt32(0), palavrasShx: x.getInt32(24)};
 let o = 100;
 while (o < shp.length) {
  const num = v.getInt32(o), palavras = v.getInt32(o + 4), c = o + 8, t = v.getInt32(c, true);
  let partes;
  if (t === 1) partes = [[[v.getFloat64(c + 4, true), v.getFloat64(c + 12, true)]]];
  else {
   const np = t === 8 ? 1 : v.getInt32(c + 36, true), n = v.getInt32(c + (t === 8 ? 36 : 40), true);
   const ini = t === 8 ? [0] : Array.from({length: np}, (_, k) => v.getInt32(c + 44 + 4 * k, true));
   const p0 = c + (t === 8 ? 40 : 44 + 4 * np), pts = Array.from({length: n}, (_, k) => [v.getFloat64(p0 + 16 * k, true), v.getFloat64(p0 + 16 * k + 8, true)]);
   partes = ini.map((s, k) => pts.slice(s, k + 1 < ini.length ? ini[k + 1] : n));
  }
  recs.push({num, palavras, inicio: o, tipo: t, partes});
  o = c + 2 * palavras;
 }
 const indice = recs.map((_, k) => [x.getInt32(100 + 8 * k), x.getInt32(104 + 8 * k)]);
 return {cab, recs, indice, fim: o};
}
// Leitor de .dbf (dBase III).
function lerDbf(b) {
 const v = dv(b), n = v.getUint32(4, true), cab = v.getUint16(8, true), reg = v.getUint16(10, true), dec = new TextDecoder();
 const campos = [];
 for (let o = 32; b[o] !== 0x0d; o += 32) campos.push({nome: dec.decode(b.subarray(o, o + 11)).replace(/\0+$/, ''), tipo: String.fromCharCode(b[o + 11]), tamanho: b[o + 16], casas: b[o + 17]});
 const linhas = [];
 for (let i = 0; i < n; i++) {
  let o = cab + i * reg + 1;
  linhas.push(campos.map(c => { const s = b.subarray(o, o + c.tamanho); o += c.tamanho; return s }));
 }
 return {versao: b[0], ano: b[1] + 1900, mes: b[2], dia: b[3], n, cab, reg, campos, linhas, tamanho: b.length, ultimo: b[b.length - 1], terminador: b[cab - 1]};
}
const textoCampo = s => new TextDecoder().decode(s).replace(/ +$/, '');
// Leitor de zip: registro final, diretório central e cabeçalhos locais.
function lerZip(b) {
 const v = dv(b);
 let fim = b.length - 22;
 while (fim >= 0 && v.getUint32(fim, true) !== 0x06054b50) fim--;
 const n = v.getUint16(fim + 10, true), tam = v.getUint32(fim + 12, true), dir = v.getUint32(fim + 16, true), itens = [];
 for (let o = dir, k = 0; k < n; k++) {
  const nl = v.getUint16(o + 28, true), local = v.getUint32(o + 42, true), nome = new TextDecoder().decode(b.subarray(o + 46, o + 46 + nl));
  const crc = v.getUint32(o + 16, true), comp = v.getUint32(o + 20, true), metodo = v.getUint16(o + 10, true), flags = v.getUint16(o + 8, true);
  const lnl = v.getUint16(local + 26, true), dados = b.subarray(local + 30 + lnl, local + 30 + lnl + comp);
  itens.push({nome, crc, metodo, flags, assinaturaLocal: v.getUint32(local, true), dados, nomeLocal: new TextDecoder().decode(b.subarray(local + 30, local + 30 + lnl))});
  o += 46 + nl;
 }
 return {itens, dir, tam, fim};
}

// CRC-32 (IEEE): valor de conferência da especificação.
ok('crc32 de "123456789" = CBF43926', S.crc32(new TextEncoder().encode('123456789')) === 0xcbf43926, S.crc32(new TextEncoder().encode('123456789')).toString(16));

// Nomes de campo do dBase.
const nomes = S.nomesCampos(['processo', '@titular', 'municipios_que_tocam', 'municipios_sem_dado', 'municipios', 'área_ha', '2025']);
ok('nomes: até 10 caracteres ASCII', nomes.every(n => n.length <= 10 && /^[a-z][a-z0-9_]*$/.test(n)), nomes.join(','));
ok('nomes: únicos', new Set(nomes).size === nomes.length, nomes.join(','));
ok('nomes: sem @ e sem acento', nomes[1] === 'titular' && nomes[5] === 'area_ha', nomes.join(','));
ok('nomes: começam por letra', nomes[6] === 'c_2025', nomes[6]);

// Partes: orientação dos anéis e partes que não desenham nada.
const quadrado = (x, y, l) => [[x, y], [x + l, y], [x + l, y + l], [x, y + l], [x, y]];
const furado = S.partes({type: 'Polygon', coordinates: [quadrado(-50, -17, 1), quadrado(-49.8, -16.8, 0.3).reverse()]});
ok('anel externo no sentido horário, furo no anti-horário', sinal(furado[0]) < 0 && sinal(furado[1]) > 0, furado.map(sinal).join(','));
ok('anel aberto é fechado', (a => a[0][0] === a[a.length - 1][0] && a[0][1] === a[a.length - 1][1])(S.partes({type: 'Polygon', coordinates: [[[-50, -17], [-49, -17], [-49, -16]]]})[0]));
ok('anel sem área fica de fora', S.partes({type: 'Polygon', coordinates: [[[-49.65, -14.25], [-49.66, -14.25], [-49.64, -14.25], [-49.65, -14.25]]]}).length === 0);
ok('linha de 1 ponto fica de fora', S.partes({type: 'MultiLineString', coordinates: [[[-49, -16]], [[-49, -16], [-48, -15]]]}).length === 1);
ok('tipo do arquivo', S.tipoShape('ponto', [{type: 'Point'}]) === 1 && S.tipoShape('ponto', [{type: 'Point'}, {type: 'MultiPoint'}]) === 8 &&
 S.tipoShape('linha', []) === 3 && S.tipoShape('poligono', []) === 5);

// Arquivo completo de cada tipo, lido de volta.
const campos = [{id: 'nome', tipo: 'texto'}, {id: 'potencia_mw', tipo: 'numero', casas: 2}, {id: 'em_operacao', tipo: 'logico'}, {id: 'municipios', tipo: 'texto'}, {id: 'codigo', tipo: 'numero'}];
const longo = 'Ação '.repeat(60);
const valores = [['Serra da Mesa', 1275, true, 'Minaçu (5213087)', 7], ['Cana Brava', null, false, longo, 'x'], ['', 0.5, null, null, null]];
const casos = {
 ponto: [{type: 'Point', coordinates: [-48.3, -13.8]}, {type: 'Point', coordinates: [-48.1, -13.4]}, {type: 'Point', coordinates: [-49, -16.7]}],
 multiponto: [{type: 'MultiPoint', coordinates: [[-48.3, -13.8], [-48.2, -13.7]]}, {type: 'Point', coordinates: [-48.1, -13.4]}, {type: 'Point', coordinates: [-49, -16.7]}],
 linha: [{type: 'LineString', coordinates: [[-49, -16], [-48.5, -15.5]]}, {type: 'MultiLineString', coordinates: [[[-50, -17], [-49.5, -17]], [[-50, -18], [-49, -18]]]}, {type: 'LineString', coordinates: [[-47, -14], [-46, -13]]}],
 poligono: [{type: 'Polygon', coordinates: [quadrado(-50, -17, 1), quadrado(-49.8, -16.8, 0.3)]}, {type: 'MultiPolygon', coordinates: [[quadrado(-48, -15, 0.5)], [quadrado(-47, -14, 0.2)]]}, {type: 'Polygon', coordinates: [quadrado(-46, -13, 0.1)]}]};
for (const [caso, geoms] of Object.entries(casos)) {
 const geometria = caso === 'multiponto' ? 'ponto' : caso;
 const c = S.camada({geometria, campos, data: DATA, registros: geoms.map((g, i) => ({geometria: g, valores: valores[i]}))});
 const s = lerShp(c.shp, c.shx);
 ok(caso + ': código 9994 e versão 1000', s.cab.codigo === 9994 && s.cab.versao === 1000 && s.cab.codigoShx === 9994);
 ok(caso + ': tamanho do .shp em palavras de 16 bits', s.cab.palavras * 2 === c.shp.length && s.fim === c.shp.length, s.cab.palavras * 2 + ' ≠ ' + c.shp.length);
 ok(caso + ': tamanho do .shx', s.cab.palavrasShx * 2 === c.shx.length && c.shx.length === 100 + 8 * geoms.length);
 ok(caso + ': tipo no cabeçalho e nos registros', s.recs.every(r => r.tipo === c.tipo) && s.cab.tipo === c.tipo, c.tipo);
 ok(caso + ': registros numerados a partir de 1', s.recs.map(r => r.num).join() === geoms.map((_, i) => i + 1).join());
 ok(caso + ': índice aponta para cada registro', s.indice.every(([o, p], k) => o * 2 === s.recs[k].inicio && p === s.recs[k].palavras));
 const todos = s.recs.flatMap(r => r.partes.flat());
 const b = [Math.min(...todos.map(p => p[0])), Math.min(...todos.map(p => p[1])), Math.max(...todos.map(p => p[0])), Math.max(...todos.map(p => p[1]))];
 ok(caso + ': caixa do arquivo', b.every((x, j) => x === s.cab.caixa[j]), s.cab.caixa.join(','));
 if (caso === 'poligono') ok('polígono: furo vira anti-horário mesmo vindo horário', sinal(s.recs[0].partes[1]) > 0 && sinal(s.recs[0].partes[0]) < 0);
 if (caso === 'multiponto') ok('multiponto: ponto simples vira multiponto de 1', s.recs[1].partes[0].length === 1);
 const d = lerDbf(c.dbf);
 ok(caso + ': dbf versão 3, data, registros', d.versao === 3 && d.ano === 2026 && d.mes === 10 && d.dia === 22 && d.n === geoms.length);
 ok(caso + ': dbf tamanhos e marcadores', d.tamanho === d.cab + d.reg * d.n + 1 && d.ultimo === 0x1a && d.terminador === 0x0d && d.cab === 32 + 32 * campos.length + 1);
 ok(caso + ': registro = 1 + soma das larguras', d.reg === 1 + d.campos.reduce((a, f) => a + f.tamanho, 0));
 if (caso !== 'ponto') continue;
 ok('dbf: tipos N, L e C', d.campos.map(f => f.tipo).join('') === 'CNLCC', d.campos.map(f => f.tipo).join(''));
 ok('dbf: número com as casas declaradas, alinhado à direita', textoCampo(d.linhas[0][1]).trim() === '1275.00' && d.campos[1].casas === 2 && new TextDecoder().decode(d.linhas[2][1]) === '   0.50');
 ok('dbf: vazio é vazio, nunca zero', textoCampo(d.linhas[1][1]) === '' && textoCampo(d.linhas[2][4]) === '' && textoCampo(d.linhas[2][3]) === '');
 ok('dbf: lógico T, F e ?', [0, 1, 2].map(i => textoCampo(d.linhas[i][2])).join('') === 'TF?');
 ok('dbf: texto UTF-8', textoCampo(d.linhas[0][3]) === 'Minaçu (5213087)');
 const cortado = d.linhas[1][3];
 ok('dbf: texto cortado em até 254 bytes sem partir caractere', d.campos[3].tamanho <= 254 && !textoCampo(cortado).includes('�') && longo.startsWith(textoCampo(cortado)), d.campos[3].tamanho);
 ok('dbf: corte contado', c.campos[3].cortados === 1 && c.campos[0].cortados === 0);
 ok('dbf: número com valor não numérico vira texto', d.campos[4].tipo === 'C' && textoCampo(d.linhas[1][4]) === 'x' && textoCampo(d.linhas[0][4]) === '7');
}

// Zip: lido de volta, CRC conferido e conteúdo igual.
const arquivos = [{nome: 'camada.shp', dados: new Uint8Array([1, 2, 3])}, {nome: 'LEIAME.txt', dados: new TextEncoder().encode('﻿Ação — UTF-8')}, {nome: 'vazio.cpg', dados: new Uint8Array(0)}];
const z = lerZip(S.zip(arquivos, DATA));
ok('zip: entradas do diretório central', z.itens.length === 3 && z.itens.map(i => i.nome).join() === 'camada.shp,LEIAME.txt,vazio.cpg');
ok('zip: cabeçalho local de cada entrada', z.itens.every((i, k) => i.assinaturaLocal === 0x04034b50 && i.nomeLocal === arquivos[k].nome));
ok('zip: armazenado (método 0) e nomes em UTF-8', z.itens.every(i => i.metodo === 0 && i.flags === 0x0800));
ok('zip: conteúdo e CRC', z.itens.every((i, k) => Buffer.compare(Buffer.from(i.dados), Buffer.from(arquivos[k].dados)) === 0 && i.crc === S.crc32(arquivos[k].dados)));
ok('zip: diretório termina no registro final', z.dir + z.tam === z.fim);
ok('prj: SIRGAS 2000 para EPSG:4674; nada para CRS desconhecido', /SIRGAS_2000/.test(S.prj('EPSG:4674 — SIRGAS 2000, longitude e latitude em graus')) && S.prj('EPSG:9999') === null && S.prj(undefined) === null);

// Paleta de PNG (ladrilhos da camada de imagem): só o PLTE e o CRC dele mudam; os pixels (IDAT) ficam intactos.
{
 const zlib = require('zlib');
 const bloco = (tipo, dados) => { const t = Buffer.from(tipo), b = Buffer.alloc(12 + dados.length); b.writeUInt32BE(dados.length, 0); t.copy(b, 4);
  Buffer.from(dados).copy(b, 8); b.writeUInt32BE(S.crc32(Buffer.concat([t, Buffer.from(dados)])), 8 + dados.length); return b };
 const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(2, 0); ihdr.writeUInt32BE(1, 4); ihdr[8] = 2; ihdr[9] = 3;
 const png = new Uint8Array(Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), bloco('IHDR', ihdr),
  bloco('PLTE', [255, 255, 255, 31, 141, 73, 214, 188, 116]), bloco('tRNS', [0, 255, 255]), bloco('IDAT', zlib.deflateSync(Buffer.from([0, 0x60]))), bloco('IEND', [])]));
 const novo = S.paletaPng(png, {1: [255, 0, 255]});
 const chunks = b => { const out = {}; for (let o = 8; o < b.length;) { const n = dv(b).getUint32(o), t = String.fromCharCode(...b.subarray(o + 4, o + 8));
  out[t] = {dados: [...b.subarray(o + 8, o + 8 + n)], crc: dv(b).getUint32(o + 8 + n), crcCerto: S.crc32(b.subarray(o + 4, o + 8 + n))}; o += 12 + n } return out };
 const a = chunks(png), c = chunks(novo);
 ok('paleta: a cor do índice 1 muda e as outras não', c.PLTE.dados.join() === [255, 255, 255, 255, 0, 255, 214, 188, 116].join(), c.PLTE.dados.join());
 ok('paleta: CRC do PLTE refeito', c.PLTE.crc === c.PLTE.crcCerto);
 ok('paleta: pixels e transparência intactos', c.IDAT.dados.join() === a.IDAT.dados.join() && c.tRNS.dados.join() === a.tRNS.dados.join());
 ok('paleta: o original não é alterado', a.PLTE.dados[3] === 31 && novo.length === png.length);
 ok('paleta: índice fora da paleta é ignorado', S.paletaPng(png, {7: [1, 2, 3]}).join() === png.join());
 let erro = null; try { S.paletaPng(png.slice(0, 8 + 25), {1: [0, 0, 0]}) } catch (e) { erro = e }
 ok('paleta: PNG sem PLTE dá erro', erro !== null);
 // ladrilho real da camada de vegetação: a troca mantém o PNG válido
 const veg = lerJson(lerJson('data/mapa/catalogo.json').camadas.find(e => e.id === 'vegetacao_nativa').dados.arquivo), bytes = M.binario(veg.ladrilhos[0].png, Uint8Array);
 const v = chunks(S.paletaPng(bytes, {1: [0, 0, 0], 2: [9, 9, 9]}));
 ok('paleta: ladrilho da vegetação continua com CRC certo em todos os blocos', Object.values(v).every(x => x.crc === x.crcCerto));
}

// Camadas reais, decodificadas como no navegador: um registro por feição desenhável, valores conferidos.
const catalogo = lerJson('data/mapa/catalogo.json');
const comoGeo = (geometria, partes) => {
 const ll = p => p.map(([la, lo]) => [lo, la]);
 if (geometria === 'ponto') return partes.length === 1 ? {type: 'Point', coordinates: [partes[0][0][1], partes[0][0][0]]} : {type: 'MultiPoint', coordinates: partes.map(p => [p[0][1], p[0][0]])};
 if (geometria === 'linha') return {type: 'MultiLineString', coordinates: partes.map(ll)};
 return {type: 'MultiPolygon', coordinates: partes.map(p => [ll(p)])};
};
for (const id of ['hidreletricas', 'estruturas', 'minas_ativas', 'litoestratigrafia']) {
 const e = catalogo.camadas.find(c => c.id === id), m = M.decodificar(lerJson(e.dados.arquivo), e);
 const registros = [];
 for (let i = 0; i < m.n; i++) {
  const g = comoGeo(e.geometria, m.partes[i]);
  if (S.partes(g).length) registros.push({geometria: g, valores: e.campos.map(c => m.valor(i, c.id))});
 }
 const c = S.camada({geometria: e.geometria, campos: e.campos.map(f => ({id: f.id, tipo: f.tipo === 'numero' || f.tipo === 'inteiro' ? 'numero' : f.tipo === 'booleano' ? 'logico' : 'texto', casas: f.casas ?? (f.tipo === 'numero' ? 2 : 0)})),
  registros: registros.map(r => ({...r, valores: r.valores.map(v => Array.isArray(v) ? v.join(' | ') : v)})), data: DATA});
 const s = lerShp(c.shp, c.shx), d = lerDbf(c.dbf);
 ok(id + ': um registro por feição desenhável', s.recs.length === registros.length && d.n === registros.length && registros.length >= e.n_feicoes - 2, `${s.recs.length} de ${e.n_feicoes}`);
 ok(id + ': .shp coerente', s.cab.palavras * 2 === c.shp.length && s.fim === c.shp.length);
 ok(id + ': caixa dentro de Goiás', s.cab.caixa[0] >= -53.7 && s.cab.caixa[2] <= -45.4 && s.cab.caixa[1] >= -20.1 && s.cab.caixa[3] <= -12, s.cab.caixa.join(','));
 if (e.geometria === 'poligono') ok(id + ': todo registro tem anel externo horário', s.recs.every(r => r.partes.some(p => sinal(p) < 0)));
 if (id === 'hidreletricas') {
  const k = e.campos.findIndex(f => f.id === 'nome'), j = e.campos.findIndex(f => f.id === 'potencia_mw');
  const linha = d.linhas.find(l => textoCampo(l[k]) === 'Serra da Mesa');
  ok('hidreletricas: Serra da Mesa 1275 MW no .dbf', linha && Number(textoCampo(linha[j])) === 1275, linha && textoCampo(linha[j]));
 }
}

if (falhas.length) {
 console.error(falhas.length + ' de ' + total + ' verificações falharam:\n' + falhas.join('\n'));
 process.exit(1);
}
console.log(total + ' verificações ok');
