// Roda as funções puras da cartografia de public/empresas-atlas.js (URL oficial da ANM e ponto no contorno com multipartes e buracos)
// sobre os dados reais: contornos de data/atlas/atlas.json e processos de data/empresas/atlas_empresas.json, na mesma projeção do mapa
// (EPSG:3857 no zoom 0). Usado por tests/test_atlas_empresas.py (CartografiaTests); imprime um JSON.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const RAIZ = path.resolve(__dirname, '..', '..');
const src = fs.readFileSync(path.join(RAIZ, 'public', 'empresas-atlas.js'), 'utf8');
const trecho = (ini, fim) => { const a = src.indexOf(ini); if (a < 0) throw new Error('não achei ' + ini); return src.slice(a, src.indexOf(fim, a)); };
const ctx = {};
vm.createContext(ctx);
vm.runInContext(trecho('function urlAnm(', 'function procsFiltrados(') + trecho('function dentroPoligono(', '// Índice espacial'), ctx);

// mesma projeção do mapa (L.CRS.EPSG3857.latLngToPoint(…, 0))
const projetar = (lat, lon) => { const s = Math.sin(lat * Math.PI / 180); return {x: (lon + 180) / 360 * 256, y: (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * 256}; };
function projetarAneis(rings) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const out = rings.filter(r => r.length > 2).map(r => { const a = new Float64Array(r.length * 2);
    r.forEach((p, i) => { const q = projetar(p[0], p[1]); a[2 * i] = q.x; a[2 * i + 1] = q.y; x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x); y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y); });
    return a; });
  return {rings: out, bb: [x0, y0, x1, y1]};
}
const geo = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', 'atlas', 'atlas.json'), 'utf8'));
const atlas = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', 'empresas', 'atlas_empresas.json'), 'utf8'));
const porNome = n => geo.municipalities.find(m => m.name === n);
const dentro = (mun, lat, lon) => { const q = projetar(lat, lon); return ctx.dentroPoligono(projetarAneis(mun.rings), q.x, q.y); };
const centro = r => [r.reduce((s, p) => s + p[0], 0) / r.length, r.reduce((s, p) => s + p[1], 0) / r.length];

const mineiros = porNome('Mineiros'), portelandia = porNome('Portelândia');
const [sulLat, sulLon] = centro(mineiros.rings[0]), [furoLat, furoLon] = centro(mineiros.rings[2]);
// CMOC × Catalão: processos vinculados pelo código IBGE e os que têm o centroide dentro do contorno
const PC = Object.fromEntries(atlas.processos.cols.map((c, i) => [c, i]));
const cmoc = atlas.empresas.find(e => e.cnpj === '26108898').i;
const kCat = atlas.dims.mun.findIndex(m => String(m[0]) === '5205109'), catalao = geo.municipalities.find(m => String(m.code) === '5205109');
const ks = atlas.processos.rows.filter(r => r[PC.empresa] === cmoc && r[PC.municipios].includes(kCat));
// todos os municípios da aba têm contorno no pacote geográfico (prévia e destaque nunca inventam desenho)
const codigos = new Set(geo.municipalities.map(m => String(m.code)));
console.log(JSON.stringify({
  urls: Object.fromEntries(['803343/1973', '860.337/2020', '1138/1962', 'abc', '', null, '12/2020', '860337/20201'].map(p => [String(p), ctx.urlAnm(p)])),
  mineiros: {sul: dentro(mineiros, sulLat, sulLon), furo: dentro(mineiros, furoLat, furoLon), furoEmPortelandia: dentro(portelandia, furoLat, furoLon), aneis: mineiros.rings.length},
  cmocCatalao: {n: ks.length, dentro: ks.filter(r => r[PC.lat] != null && dentro(catalao, r[PC.lat], r[PC.lon])).map(r => r[PC.processo]).sort()},
  semContorno: atlas.dims.mun.filter(m => !codigos.has(String(m[0]))).map(m => m[1]),
}));
