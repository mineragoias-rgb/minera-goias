/* Mapa Mineral de Goiás — one layer as an ESRI shapefile in a .zip, built in the browser from the data the map already holds.
   Follows the ESRI Shapefile Technical Description (1998) and dBase III: .shp and .shx carry the geometry, .dbf one attribute row
   per shape (UTF-8, declared in .cpg) and .prj the CRS the catalogue states. The zip stores the files as they are (method 0), so it
   needs only CRC-32. Pure functions, exported for node (tests/mapa-shp.test.js). */
(function (raiz) {
 'use strict';
 const utf8 = new TextEncoder();
 const PRJ = {'EPSG:4674': 'GEOGCS["GCS_SIRGAS_2000",DATUM["D_SIRGAS_2000",SPHEROID["GRS_1980",6378137.0,298.257222101]],' +
  'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'};
 const prj = crs => { const m = /^EPSG:\d+/.exec(crs || ''); return (m && PRJ[m[0]]) || null };

 // One shape type per file: points that come as MultiPoint make the whole file MultiPoint (8).
 function tipoShape(geometria, geoms) {
  if (geometria === 'linha') return 3;
  if (geometria === 'poligono') return 5;
  return geoms.some(g => g.type === 'MultiPoint') ? 8 : 1;
 }
 const area = a => { let s = 0; for (let i = 0; i + 1 < a.length; i++) s += a[i][0] * a[i + 1][1] - a[i + 1][0] * a[i][1]; return s / 2 };
 const fechado = a => a.length && (a[0][0] !== a[a.length - 1][0] || a[0][1] !== a[a.length - 1][1]) ? [...a, a[0]] : a;
 // GeoJSON geometry -> shapefile parts in [x = longitude, y = latitude]. Rings: outer clockwise, holes counterclockwise.
 // Parts that draw nothing are left out: lines under 2 points and rings with no area (quantization can collapse a thin sliver
 // onto a line). A feature left with no part has no geometry for the file.
 function partes(g) {
  if (g.type === 'Point') return [[g.coordinates]];
  if (g.type === 'MultiPoint') return [g.coordinates];
  if (g.type === 'LineString' || g.type === 'MultiLineString') return (g.type === 'LineString' ? [g.coordinates] : g.coordinates).filter(l => l.length >= 2);
  const polis = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  return polis.flatMap(p => p.flatMap((anel, k) => {
   const a = fechado(anel), s = area(a);
   return Math.abs(s) < 1e-12 ? [] : [(s < 0) === (k === 0) ? a : [...a].reverse()];
  }));
 }
 function caixa(pts) {
  if (!pts.length) return [0, 0, 0, 0];
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of pts) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y }
  return [x0, y0, x1, y1];
 }
 function cabecalho(v, bytes, tipo, b) {
  v.setInt32(0, 9994); v.setInt32(24, bytes / 2); v.setInt32(28, 1000, true); v.setInt32(32, tipo, true);
  b.forEach((x, j) => v.setFloat64(36 + 8 * j, x, true));
 }
 // .shp and .shx. Record and file lengths count 16-bit words, as the format asks; headers are big-endian, the rest little-endian.
 // Every geometry must have at least one point: features without one stay out of the file.
 function shp(tipo, geoms) {
  const recs = geoms.map(g => {
   const ps = partes(g), pts = ps.flat();
   return {ps, pts, b: caixa(pts), tam: tipo === 1 ? 20 : tipo === 8 ? 40 + 16 * pts.length : 44 + 4 * ps.length + 16 * pts.length};
  });
  const bytes = 100 + recs.reduce((s, r) => s + 8 + r.tam, 0), bytesShx = 100 + 8 * recs.length;
  const v = new DataView(new ArrayBuffer(bytes)), x = new DataView(new ArrayBuffer(bytesShx));
  const b = caixa(recs.flatMap(r => [r.b.slice(0, 2), r.b.slice(2)]));
  cabecalho(v, bytes, tipo, b); cabecalho(x, bytesShx, tipo, b);
  let o = 100;
  recs.forEach((r, k) => {
   x.setInt32(100 + 8 * k, o / 2); x.setInt32(104 + 8 * k, r.tam / 2);
   v.setInt32(o, k + 1); v.setInt32(o + 4, r.tam / 2); o += 8;
   v.setInt32(o, tipo, true);
   if (tipo === 1) { v.setFloat64(o + 4, r.pts[0][0], true); v.setFloat64(o + 12, r.pts[0][1], true) }
   else {
    r.b.forEach((c, j) => v.setFloat64(o + 4 + 8 * j, c, true));
    let p = o + 36;
    if (tipo !== 8) { v.setInt32(p, r.ps.length, true); p += 4 }
    v.setInt32(p, r.pts.length, true); p += 4;
    if (tipo !== 8) { let ini = 0; for (const parte of r.ps) { v.setInt32(p, ini, true); p += 4; ini += parte.length } }
    for (const [px, py] of r.pts) { v.setFloat64(p, px, true); v.setFloat64(p + 8, py, true); p += 16 }
   }
   o += r.tam;
  });
  return {shp: new Uint8Array(v.buffer), shx: new Uint8Array(x.buffer)};
 }

 // dBase names: ASCII, at most 10 characters, unique without regard to case. The readme maps each one back to its label.
 function nomesCampos(ids) {
  const usados = new Set();
  return ids.map(id => {
   let base = String(id).normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/^@/, '').replace(/[^A-Za-z0-9_]/g, '_').toLowerCase();
   if (!/^[a-z]/.test(base)) base = 'c_' + base;
   let nome = base.slice(0, 10);
   for (let k = 2; usados.has(nome); k++) nome = base.slice(0, 10 - String(k).length) + k;
   usados.add(nome);
   return nome;
  });
 }
 // Cut UTF-8 at max bytes without splitting a character.
 const corta = (b, max) => { if (b.length <= max) return b; let n = max; while (n > 0 && (b[n] & 0xc0) === 0x80) n--; return b.subarray(0, n) };
 // campos: [{nome, tipo: 'N' | 'L' | 'C', casas}]; linhas: values in field order, null = empty (never zero). A number field whose
 // values are not all numbers, or that would need more than 19 characters, becomes text; so does a logical one with non-booleans.
 // Text longer than 254 bytes, the dBase limit, is cut and counted in the returned campos[k].cortados.
 function dbf(campos, linhas, data) {
  const largura = s => s.reduce((m, y) => Math.max(m, y ? y.length : 0), 1);
  const saida = campos.map((c, k) => {
   const vals = linhas.map(l => l[k] == null || l[k] === '' ? null : l[k]);
   if (c.tipo === 'N' && vals.every(y => y == null || (typeof y === 'number' && Number.isFinite(y)))) {
    const s = vals.map(y => y == null ? null : y.toFixed(c.casas));
    if (largura(s) <= 19) return {...c, s, tamanho: largura(s), cortados: 0};
   }
   if (c.tipo === 'L' && vals.every(y => y == null || typeof y === 'boolean')) return {...c, s: vals.map(y => y == null ? '?' : y ? 'T' : 'F'), tamanho: 1, cortados: 0};
   let cortados = 0;
   const s = vals.map(y => { if (y == null) return null; const b = utf8.encode(String(y)); if (b.length > 254) cortados++; return corta(b, 254) });
   return {...c, tipo: 'C', casas: 0, s, tamanho: largura(s), cortados};
  });
  const cab = 32 + 32 * saida.length + 1, reg = 1 + saida.reduce((s, c) => s + c.tamanho, 0);
  const buf = new Uint8Array(cab + reg * linhas.length + 1), v = new DataView(buf.buffer);
  buf[0] = 3; buf[1] = data.getFullYear() - 1900; buf[2] = data.getMonth() + 1; buf[3] = data.getDate();
  v.setUint32(4, linhas.length, true); v.setUint16(8, cab, true); v.setUint16(10, reg, true);
  saida.forEach((c, k) => { const o = 32 + 32 * k; buf.set(utf8.encode(c.nome), o); buf[o + 11] = c.tipo.charCodeAt(0); buf[o + 16] = c.tamanho; buf[o + 17] = c.casas });
  buf[cab - 1] = 0x0d;
  buf.fill(0x20, cab, buf.length - 1);
  let o = cab;
  for (let i = 0; i < linhas.length; i++) {
   o++;  // deletion flag: a space, record in use
   for (const c of saida) {
    const y = c.s[i];
    if (y != null) { const b = typeof y === 'string' ? utf8.encode(y) : y; buf.set(b, c.tipo === 'N' ? o + c.tamanho - b.length : o) }
    o += c.tamanho;
   }
  }
  buf[buf.length - 1] = 0x1a;
  return {dbf: buf, campos: saida.map(c => ({id: c.id, nome: c.nome, tipo: c.tipo, tamanho: c.tamanho, casas: c.casas, cortados: c.cortados}))};
 }

 // One layer. registros: [{geometria (GeoJSON), valores (in field order)}]; campos: [{id, tipo: 'numero' | 'logico' | 'texto', casas}].
 function camada({geometria, registros, campos, data}) {
  const tipo = tipoShape(geometria, registros.map(r => r.geometria));
  const {shp: s, shx} = shp(tipo, registros.map(r => r.geometria));
  const nomes = nomesCampos(campos.map(c => c.id));
  const {dbf: d, campos: info} = dbf(campos.map((c, k) => ({id: c.id, nome: nomes[k], tipo: c.tipo === 'numero' ? 'N' : c.tipo === 'logico' ? 'L' : 'C',
   casas: c.tipo === 'numero' ? c.casas || 0 : 0})), registros.map(r => r.valores), data);
  return {tipo, shp: s, shx, dbf: d, campos: info};
 }

 const CRC = new Uint32Array(256);
 for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; CRC[n] = c >>> 0 }
 function crc32(b) { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0 }
 // Zip (APPNOTE 6.3): local headers and data, central directory, end record. Stored, UTF-8 names (flag bit 11).
 function zip(arquivos, data) {
  const hora = (data.getHours() << 11) | (data.getMinutes() << 5) | (data.getSeconds() >> 1);
  const dia = ((data.getFullYear() - 1980) << 9) | ((data.getMonth() + 1) << 5) | data.getDate();
  const itens = arquivos.map(a => ({nome: utf8.encode(a.nome), dados: a.dados, crc: crc32(a.dados)}));
  const local = itens.reduce((s, a) => s + 30 + a.nome.length + a.dados.length, 0), central = itens.reduce((s, a) => s + 46 + a.nome.length, 0);
  const buf = new Uint8Array(local + central + 22), v = new DataView(buf.buffer);
  const comum = (o, a) => { v.setUint16(o, 0x0800, true); v.setUint16(o + 2, 0, true); v.setUint16(o + 4, hora, true); v.setUint16(o + 6, dia, true);
   v.setUint32(o + 8, a.crc, true); v.setUint32(o + 12, a.dados.length, true); v.setUint32(o + 16, a.dados.length, true); v.setUint16(o + 20, a.nome.length, true) };
  let o = 0;
  for (const a of itens) {
   a.inicio = o;
   v.setUint32(o, 0x04034b50, true); v.setUint16(o + 4, 20, true); comum(o + 6, a);
   buf.set(a.nome, o + 30); buf.set(a.dados, o + 30 + a.nome.length); o += 30 + a.nome.length + a.dados.length;
  }
  const dir = o;
  for (const a of itens) {
   v.setUint32(o, 0x02014b50, true); v.setUint16(o + 4, 20, true); v.setUint16(o + 6, 20, true); comum(o + 8, a);
   v.setUint32(o + 42, a.inicio, true); buf.set(a.nome, o + 46); o += 46 + a.nome.length;
  }
  v.setUint32(o, 0x06054b50, true); v.setUint16(o + 8, itens.length, true); v.setUint16(o + 10, itens.length, true);
  v.setUint32(o + 12, o - dir, true); v.setUint32(o + 16, dir, true);
  return buf;
 }

 const puro = {prj, tipoShape, partes, shp, nomesCampos, dbf, camada, crc32, zip};
 if (typeof module === 'object' && module.exports) module.exports = puro;
 if (raiz) raiz.MapaShp = puro;
})(typeof window !== 'undefined' ? window : null);
