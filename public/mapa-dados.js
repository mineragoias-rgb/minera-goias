/* Mapa Mineral de Goiás — data loader (no interface yet).
   Reads the catalogue (/api/mapa/catalogo) and fetches each layer only when asked; layers that already exist in the atlas
   come from /api/atlas and /api/atlas/processes (shared with the Atlas tab through loadProcesses), never from a copy.
   Every layer decodes to the same shape: {entrada, n, geometria, partes[i] = list of points, lines or rings in [lat, lon],
   valor(i, campo), atributos(i)}. Rings of one feature are drawn together with fillRule 'evenodd', as processes.js does.
   Raster layers (imagem-v1) decode to the same shape with one feature per class, no rings (partes[i] = []), the extent of each
   class in caixas[i] and the PNG tiles in imagem.
   The pure functions are exported for node (tests/mapa-dados.test.js). */
(function (raiz) {
 'use strict';
 const GRUPOS_ATLAS = ['Lavra / extração autorizada', 'Pesquisa autorizada', 'Requerimento em análise', 'Disponibilidade', 'Outros'];

 function binario(s, Tipo) {
  const texto = typeof atob === 'function' ? atob(s) : Buffer.from(s, 'base64').toString('binary');
  const bytes = new Uint8Array(texto.length);
  for (let i = 0; i < texto.length; i++) bytes[i] = texto.charCodeAt(i);
  return new Tipo(bytes.buffer);
 }

 // Format mapa-v1, written by scripts/build_mapa_base.py: lat = lat1 − y/65535·(lat1 − lat0), lon = lon0 + x/65535·(lon1 − lon0).
 function decodificar(pacote, entrada) {
  const xy = binario(pacote.xy, Uint16Array), inicio = binario(pacote.partStart, Uint32Array), dono = binario(pacote.partFeat, Uint32Array);
  const b = pacote.bounds, dLat = (b.lat1 - b.lat0) / 65535, dLon = (b.lon1 - b.lon0) / 65535;
  const partes = Array.from({length: pacote.n}, () => []);
  for (let k = 0; k < dono.length; k++) {
   const seq = [];
   for (let i = inicio[k]; i < inicio[k + 1]; i++) seq.push([b.lat1 - xy[2 * i + 1] * dLat, b.lon0 + xy[2 * i] * dLon]);
   partes[dono[k]].push(seq);
  }
  const valor = (i, campo) => {
   if (!pacote.valores[campo]) return undefined;  // a field the layer does not have (na_divisa exists only in the P3M layers)
   const v = pacote.valores[campo][i], d = pacote.dic[campo];
   if (v == null || !d) return v;
   return Array.isArray(v) ? v.map(x => x == null ? null : d[x]) : d[v];
  };
  return montar(entrada, pacote.geometria, pacote.n, partes, pacote.campos, valor);
 }

 // Format imagem-v1: palette PNG tiles on the Web Mercator pixel grid of one zoom; palette index k is feature k − 1.
 function decodificarImagem(pacote, entrada) {
  const valor = (i, campo) => {
   if (!pacote.valores[campo]) return undefined;
   const v = pacote.valores[campo][i], d = pacote.dic[campo];
   return v == null || !d ? v : d[v];
  };
  const m = montar(entrada, 'raster', pacote.n, Array.from({length: pacote.n}, () => []), pacote.campos, valor);
  return Object.assign(m, {caixas: pacote.caixas, imagem: {zoom: pacote.zoom, origem: pacote.origem_px, ladrilho: pacote.ladrilho,
   largura: pacote.largura, altura: pacote.altura, paleta: pacote.paleta, ladrilhos: pacote.ladrilhos}});
 }
 // Pixel of a point on that grid (256·2^zoom pixels around the world), as scripts/build_mapa_base.py computes it.
 function pixelMercator(lat, lon, zoom) {
  const n = 256 * 2 ** zoom, la = lat * Math.PI / 180;
  return [(lon + 180) / 360 * n, (1 - Math.log(Math.tan(la) + 1 / Math.cos(la)) / Math.PI) / 2 * n];
 }
 // Feature (class) of a decoded pixel: the nearest colour of the palette the tile was written with, since a browser may shift a
 // colour by a unit or two; a transparent pixel has no class.
 function classeDaCor(rgba, paleta) {
  if (rgba[3] < 128) return null;
  let melhor = null, menor = Infinity;
  for (let k = 1; k < paleta.length; k++) {
   const d = (paleta[k][0] - rgba[0]) ** 2 + (paleta[k][1] - rgba[1]) ** 2 + (paleta[k][2] - rgba[2]) ** 2;
   if (d < menor) { menor = d; melhor = k - 1 }
  }
  return melhor;
 }

 function montar(entrada, geometria, n, partes, campos, valor) {
  const atributos = i => Object.fromEntries(campos.map(c => [c, valor(i, c)]));
  return {entrada, geometria, n, partes, campos, valor, atributos};
 }

 // Layers whose catalogue entry points to the atlas. registros = records of loadProcesses() for the claims layer.
 function doAtlas(entrada, atlas, registros) {
  const formato = entrada.dados.formato, campos = entrada.campos.map(c => c.id);
  if (formato === 'processos-atlas') {
   const pega = {processo: r => r.id, fase: r => r.phase, grupo: r => GRUPOS_ATLAS[r.group], substancia: r => r.mineral, area: r => r.area};
   return montar(entrada, 'poligono', registros.length, registros.map(r => r.rings), campos, (i, c) => pega[c] ? pega[c](registros[i]) : undefined);
  }
  if (formato === 'municipios-atlas') {
   const lista = atlas.municipalities;
   return montar(entrada, 'poligono', lista.length, lista.map(m => m.rings), campos, (i, c) => lista[i][c]);
  }
  const bloco = atlas[entrada.dados.chave_json];
  const linhas = formato === 'colunas-lat-lon' ? bloco.rows.map(r => Object.fromEntries(bloco.cols.map((c, k) => [c, r[k]]))) : bloco;
  return montar(entrada, 'ponto', linhas.length, linhas.map(x => [[[x.lat, x.lon]]]), campos, (i, c) => linhas[i][c]);
 }

 // Radar projects drawn through their ANM claims: claim -> ids of the projects that cite it.
 function radarPorProcesso(tabela) {
  const mapa = new Map();
  for (const p of tabela.linhas) for (const k of p.processos) (mapa.get(k) || mapa.set(k, []).get(k)).push(p.id);
  return mapa;
 }

 // Holder (legal entities only; individuals come without a name), IBGE municipalities and ANM minerals of each atlas claim.
 function complementoPorProcesso(tabela) {
  const d = tabela.dic;
  return new Map(tabela.processos.map((k, i) => [k, {
   titular: tabela.titular[i] == null ? null : d.titular[tabela.titular[i]],
   municipios: tabela.municipios[i] ? tabela.municipios[i].map(j => d.municipios[j]) : [],
   mineral: tabela.mineral[i] ? tabela.mineral[i].map(j => d.mineral[j]) : []}]));
 }

 // Identifier search. Claims compare by number and year ('860.337/2020' = '860337/2020', '009291/1967' = '9291/1967');
 // other codes keep their zeros, so 'GO-0001' never matches 'GO-0010'. Digits alone are the start of a claim number;
 // text with letters may also match inside a name ('chapada' finds 'Parque Nacional da Chapada dos Veadeiros').
 function chaveId(s) {
  const t = String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[\s.\-]/g, '');
  const m = /^0*(\d{1,6})\/(\d{4})$/.exec(t);
  return m ? m[1] + '/' + m[2] : t;
 }
 function casaId(chaves, consulta) {
  const q = chaveId(consulta);
  if (!q) return true;
  const numero = /^\d+$/.test(q) ? q.replace(/^0+(?=\d)/, '') : null;
  return chaves.some(k => k === q || (numero !== null && k.includes('/') ? k.startsWith(numero) : k.startsWith(q)) ||
   (/[A-Z]/.test(q) && q.length >= 3 && k.includes(q)));
 }

 const puro = {GRUPOS_ATLAS, binario, decodificar, decodificarImagem, pixelMercator, classeDaCor, doAtlas, radarPorProcesso,
  complementoPorProcesso, chaveId, casaId};
 if (typeof module === 'object' && module.exports) module.exports = puro;
 if (!raiz) return;

 const cache = {};
 const uma = (chave, f) => cache[chave] || (cache[chave] = f().catch(e => { delete cache[chave]; throw e }));
 const catalogo = () => uma('catalogo', () => api('/mapa/catalogo'));
 const atlas = () => uma('atlas', () => api('/atlas'));
 function camada(id) {
  return uma('camada:' + id, async () => {
   const entrada = (await catalogo()).camadas.find(c => c.id === id);
   if (!entrada) throw Error('camada desconhecida: ' + id);
   const formato = entrada.dados.formato;
   if (formato === 'mapa-v1') return decodificar(await api('/mapa/camadas/' + id), entrada);
   if (formato === 'imagem-v1') return decodificarImagem(await api('/mapa/camadas/' + id), entrada);
   if (formato === 'processos-atlas') return doAtlas(entrada, null, (await raiz.loadProcesses()).records);
   return doAtlas(entrada, await atlas());
  });
 }
 const tabela = id => uma('tabela:' + id, () => api('/mapa/tabelas/' + id));
 raiz.MapaDados = Object.assign({catalogo, camada, tabela, atlas}, puro);
 // The 2 MB atlas packet is fetched once per page and shared with the Atlas and Panorama tabs, which only read it.
 raiz.loadAtlas = atlas;
})(typeof window !== 'undefined' ? window : null);
