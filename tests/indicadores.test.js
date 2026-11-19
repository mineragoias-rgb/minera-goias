// Funções puras dos indicadores municipais (public/indicadores.js): normalização, composição, faixas de cor, ranking e formato.
const assert = require('assert');
const I = require('../public/indicadores.js');
const num = (v, d) => v.toFixed(d);

// minmax: menor valor = 0, maior = 1; sem valor continua sem valor; constante vira 0
{
 const m = I.minmax([10, 20, 30, null]);
 assert.strictEqual(m.norm(10), 0); assert.strictEqual(m.norm(30), 1); assert.strictEqual(m.norm(20), 0.5); assert.strictEqual(m.norm(null), null);
 assert.strictEqual(I.minmax([5, 5]).norm(5), 0);
 const l = I.minmax([0, 9], true); assert.ok(Math.abs(l.norm(9) - 1) < 1e-12); assert.ok(l.norm(3) > 0.5, 'log aproxima os valores altos do meio');
 assert.doesNotThrow(() => I.minmax([-1, 2], true), 'crescimento de -100% não quebra o log');
}
// compor: média ponderada dos normalizados
{
 const col = {A: [0, 50, 100], B: [100, 50, 0]};
 let c = I.compor(col, {A: 1, B: 0});
 assert.deepStrictEqual(c.nota, [0, 0.5, 1]);
 c = I.compor(col, {A: 1, B: 1}); assert.deepStrictEqual(c.nota, [0.5, 0.5, 0.5]);
 c = I.compor(col, {A: 3, B: 1}); assert.ok(Math.abs(c.nota[2] - 0.75) < 1e-12 && Math.abs(c.nota[0] - 0.25) < 1e-12);
 // pesos proporcionais dão a mesma nota
 assert.deepStrictEqual(I.compor(col, {A: 30, B: 10}).nota, I.compor(col, {A: 3, B: 1}).nota);
 // sem peso: ninguém tem nota
 assert.ok(I.compor(col, {A: 0, B: 0}).nota.every(x => x === null));
 // indicador ausente: o peso sai do denominador; abaixo de 50% do peso fica sem nota
 const fal = {A: [0, 100, 100], B: [null, 0, 100]};
 c = I.compor(fal, {A: 1, B: 1});
 assert.strictEqual(c.cobertura[0], 0.5); assert.strictEqual(c.nota[0], 0, 'metade do peso basta');
 c = I.compor(fal, {A: 1, B: 3}); assert.strictEqual(c.nota[0], null, 'só 25% do peso: sem nota');
 // todas as notas ficam entre 0 e 1
 const r = I.compor({A: [3, 9, 1, 7], B: [0.2, 0.1, 0.9, 0.5]}, {A: 2, B: 7}, true);
 assert.ok(r.nota.every(x => x >= 0 && x <= 1));
}
// exigir todos os indicadores: sem redistribuição de pesos
{
 const fal = {A: [0, 100, 100], B: [null, 0, 100]};
 const c = I.compor(fal, {A: 1, B: 1}, false, true);
 assert.strictEqual(c.nota[0], null); assert.notStrictEqual(c.nota[1], null);
}
// faixas e cores
{
 const v = Array.from({length: 100}, (_, i) => i + 1);
 assert.strictEqual(I.faixas(v, 'q').length, 4);
 const q = I.faixas(v, 'q'); assert.deepStrictEqual(q, [21, 41, 61, 81]);
 assert.deepStrictEqual(I.faixas(v, 'l').map(x => Math.round(x)), [21, 41, 60, 80]);
 assert.strictEqual(I.corDe(null, q), null); assert.strictEqual(I.corDe(1, q), I.RAMPA[0]); assert.strictEqual(I.corDe(100, q), I.RAMPA[4]);
 // muitos zeros: cortes repetidos são unificados e todos têm cor
 const z = [0, 0, 0, 0, 0, 0, 0, 5, 9, 12]; const cz = I.faixas(z, 'q');
 assert.deepStrictEqual(cz, [...new Set(cz)]); assert.ok(z.every(x => I.corDe(x, cz)));
 assert.deepStrictEqual(I.faixas([1], 'q'), []);
 // valor negativo (crescimento) também recebe cor
 assert.ok(I.corDe(-0.4, I.faixas([-0.5, -0.4, 0, 0.3, 2, 9], 'q')));
}
// posições e ranking
{
 assert.deepStrictEqual(I.posicoes([5, 9, 9, null, 1]), [3, 1, 1, null, 4]);
 assert.deepStrictEqual(I.ranking([5, 9, null, 1, 7], 3, 'desc').map(x => x.k), [1, 4, 0]);
 assert.deepStrictEqual(I.ranking([5, 9, null, 1, 7], 2, 'asc').map(x => x.k), [3, 0]);
 assert.strictEqual(I.mediana([1, 3, null, 2]), 2); assert.strictEqual(I.mediana([1, 2, 3, 4]), 2.5); assert.strictEqual(I.mediana([]), null);
}
// formato
{
 assert.strictEqual(I.formatar(0.256, 'pct', num), '25.6%'); assert.strictEqual(I.formatar(0.00140, 'pct2', num), '0.14%');
 assert.strictEqual(I.formatar(1234.5, 'money0', num), 'R$ 1235'); assert.strictEqual(I.formatar(94.536, 'money2', num), 'R$ 94.54');
 assert.strictEqual(I.formatar(7, 'int', num), '7'); assert.strictEqual(I.formatar(null, 'int', num), null); assert.strictEqual(I.formatar(NaN, 'dec2', num), null);
}
console.log('indicadores.test.js: ok');
