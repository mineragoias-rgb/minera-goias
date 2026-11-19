/* Indicadores municipais (2025) no Atlas · Território · Visão do mapa.
   Três partes: o seletor de indicador do mapa (cores por tamanho), a explicação e o ranking sob o mapa, e a composição de
   indicadores (cada um normalizado de 0 a 1, com pesos livres ou combinações fixas). Os dados vêm de /api/indicadores, atrás do
   login. As funções puras (minmax, compor, faixas, ranking, formato) são exportadas para o node (tests/indicadores.test.js). */
(function (raiz) {
 'use strict';

 // ---------- funções puras ----------
 const RAMPA = ['#d7e9f6', '#a8cde9', '#6fa9d4', '#3684b9', '#07588b'];
 const FORMATOS = {money0: [0, 'R$ '], money2: [2, 'R$ '], pct: [1, '', '%'], pct2: [2, '', '%'], int: [0], dec2: [2], dec3: [3], auto: [null]};
 const valido = v => typeof v === 'number' && Number.isFinite(v);

 // Normaliza de 0 a 1 pelo mínimo e máximo dos municípios com valor; com `log`, aplica ln(1 + x) antes.
 function minmax(valores, log) {
  const f = v => log ? Math.log1p(Math.max(v, -0.999999)) : v;
  const xs = valores.filter(valido).map(f);
  if (!xs.length) return {min: null, max: null, norm: () => null};
  const min = Math.min(...xs), max = Math.max(...xs);
  return {min, max, norm: v => !valido(v) ? null : (max === min ? 0 : (f(v) - min) / (max - min))};
 }

 // colunas: {id: [valor por município]}; pesos: {id: peso >= 0}. A nota é a média ponderada dos indicadores normalizados
 // que o município tem; o peso que falta (indicador sem valor) sai do denominador. Abaixo de 50% do peso, fica sem nota.
 function compor(colunas, pesos, log, exigirTodos) {
  const ids = Object.keys(pesos).filter(id => colunas[id] && pesos[id] > 0);
  const n = ids.length ? colunas[ids[0]].length : 0;
  const total = ids.reduce((s, id) => s + pesos[id], 0);
  const norm = Object.fromEntries(ids.map(id => [id, minmax(colunas[id], log)]));
  const nota = new Array(n).fill(null), cobertura = new Array(n).fill(0);
  for (let k = 0; k < n; k++) {
   let soma = 0, usado = 0;
   for (const id of ids) {
    const x = norm[id].norm(colunas[id][k]);
    if (x !== null) { soma += pesos[id] * x; usado += pesos[id]; }
   }
   cobertura[k] = total > 0 ? usado / total : 0;
   nota[k] = usado > 0 && (exigirTodos ? cobertura[k] >= 0.999999 : cobertura[k] >= 0.5) ? soma / usado : null;
  }
  return {nota, cobertura, total};
 }

 // Cortes das faixas de cor: 'q' = quantis dos municípios com valor; 'l' = faixas iguais entre o menor e o maior valor.
 function faixas(valores, modo) {
  const xs = valores.filter(valido).sort((a, b) => a - b);
  if (xs.length < 2) return [];
  const cortes = [1, 2, 3, 4].map(i => modo === 'l' ? xs[0] + (xs[xs.length - 1] - xs[0]) * i / 5 : xs[Math.floor(xs.length * i / 5)]);
  return [...new Set(cortes)].filter(c => c > xs[0] && c <= xs[xs.length - 1]);
 }
 function corDe(v, cortes) {
  if (!valido(v)) return null;
  const classe = cortes.filter(c => v >= c).length, total = cortes.length + 1;
  return RAMPA[total === 1 ? 2 : Math.round(classe * (RAMPA.length - 1) / (total - 1))];
 }

 // Posições (1 = maior valor); empate recebe a mesma posição.
 function posicoes(valores) {
  const ord = valores.map((v, k) => [v, k]).filter(x => valido(x[0])).sort((a, b) => b[0] - a[0]);
  const pos = new Array(valores.length).fill(null);
  ord.forEach((x, i) => { pos[x[1]] = i > 0 && x[0] === ord[i - 1][0] ? pos[ord[i - 1][1]] : i + 1; });
  return pos;
 }
 // crescimento = valor do ano final ÷ valor do ano base − 1; sem valor quando a base é zero ou ausente
 function crescimento(base, fim) { return valido(base) && base > 0 && valido(fim) ? fim / base - 1 : null; }
 function ranking(valores, n, ordem) {
  const lista = valores.map((v, k) => [v, k]).filter(x => valido(x[0]));
  lista.sort((a, b) => ordem === 'asc' ? a[0] - b[0] : b[0] - a[0]);
  return lista.slice(0, n).map(x => ({k: x[1], v: x[0]}));
 }
 function formatar(v, fmt, num) {
  if (!valido(v)) return null;
  const f = FORMATOS[fmt] || [2], x = f[2] === '%' ? v * 100 : v;
  // 'auto' (indicador personalizado): casas conforme a grandeza do valor
  const casas = f[0] === null ? (Math.abs(x) >= 1000 ? 0 : Math.abs(x) >= 1 ? 2 : Math.abs(x) === 0 ? 0 : 4) : f[0];
  return (f[1] || '') + num(x, casas) + (f[2] || '');
 }
 function mediana(valores) {
  const xs = valores.filter(valido).sort((a, b) => a - b);
  return xs.length ? (xs.length % 2 ? xs[(xs.length - 1) / 2] : (xs[xs.length / 2 - 1] + xs[xs.length / 2]) / 2) : null;
 }

 // Fórmula do indicador personalizado: códigos de indicador (R1, S2…), números e + − * / com parênteses.
 // Analisador próprio (descida recursiva), sem eval. Erros voltam como {erro: tipo, dado}.
 function compilar(texto, ids) {
  const src = String(texto || '').trim();
  if (!src) return {erro: 'vazio'};
  const toks = [];
  const re = /\s*(?:(\d+(?:[.,]\d+)?)|([A-Za-z]\d+)|([+\-*\/×÷()]))/y;
  let pos = 0;
  while (pos < src.length) {
   re.lastIndex = pos;
   const m = re.exec(src);
   if (!m) { const c = src.slice(pos).trim()[0]; if (c === undefined) break; return {erro: 'caractere', dado: c}; }
   pos = re.lastIndex;
   if (m[1] !== undefined) toks.push({t: 'n', v: parseFloat(m[1].replace(',', '.'))});
   else if (m[2] !== undefined) { const id = m[2].toUpperCase(); if (!ids.includes(id)) return {erro: 'id', dado: id}; toks.push({t: 'i', v: id}); }
   else toks.push({t: 'o', v: m[3] === '×' ? '*' : m[3] === '÷' ? '/' : m[3]});
  }
  let i = 0;
  const usados = new Set();
  const rot = () => i < toks.length ? String(toks[i].v) : '';
  function primario() {
   const k = toks[i];
   if (!k) throw {erro: 'sintaxe', dado: rot()};
   if (k.t === 'n') { i++; return () => k.v; }
   if (k.t === 'i') { i++; usados.add(k.v); return get => get(k.v); }
   if (k.t === 'o' && k.v === '(') {
    i++; const e = expr();
    if (!toks[i] || toks[i].v !== ')') throw {erro: 'parenteses'};
    i++; return e;
   }
   if (k.t === 'o' && k.v === ')') throw {erro: 'parenteses'};
   throw {erro: 'sintaxe', dado: rot()};
  }
  function unario() {
   const k = toks[i];
   if (k && k.t === 'o' && (k.v === '-' || k.v === '+')) { i++; const e = unario(); return k.v === '-' ? g => { const x = e(g); return valido(x) ? -x : null; } : e; }
   return primario();
  }
  function termo() {
   let e = unario();
   while (toks[i] && toks[i].t === 'o' && (toks[i].v === '*' || toks[i].v === '/')) {
    const op = toks[i++].v, a = e, b = unario();
    e = op === '*' ? g => { const x = a(g), y = b(g); return valido(x) && valido(y) ? x * y : null; }
                   : g => { const x = a(g), y = b(g); return valido(x) && valido(y) && y !== 0 ? x / y : null; };
   }
   return e;
  }
  function expr() {
   let e = termo();
   while (toks[i] && toks[i].t === 'o' && (toks[i].v === '+' || toks[i].v === '-')) {
    const op = toks[i++].v, a = e, b = termo();
    e = op === '+' ? g => { const x = a(g), y = b(g); return valido(x) && valido(y) ? x + y : null; }
                   : g => { const x = a(g), y = b(g); return valido(x) && valido(y) ? x - y : null; };
   }
   return e;
  }
  try {
   const e = expr();
   if (i < toks.length) throw toks[i].v === ')' ? {erro: 'parenteses'} : {erro: 'sintaxe', dado: rot()};
   // avalia por município: `col` = {id: [valores]}, `n` = número de municípios
   return {ok: true, ids: [...usados], valores: (col, n) => Array.from({length: n}, (_, k) => { const x = e(id => col[id][k]); return valido(x) ? x : null; })};
  } catch (err) { if (err && err.erro) return err; throw err; }
 }
 const puras = {compilar, crescimento, minmax, compor, faixas, corDe, posicoes, ranking, formatar, mediana, RAMPA};
 if (typeof module !== 'undefined' && module.exports) { module.exports = puras; return; }

 // ---------- interface ----------
 const el = id => document.getElementById(id), escape = esc, lang = () => (window.I18N && I18N.lang === 'en') ? 'en' : 'pt';
 const num = (v, d = 0) => I18N.num(v, {minimumFractionDigits: d, maximumFractionDigits: d});
 const E = {sel: 'R1', escala: 'q', log: false, todos: false, preset: 'arrecadacao', a0: 2024, a1: 2025, custom: null, pesos: {}, topo: 15, ordem: 'desc', dados: null, carga: null};
 const COMP = '__comp', CUST = '__custom';

 function campo(o, nome) { return lang() === 'en' && o[nome + '_en'] ? o[nome + '_en'] : o[nome]; }
 function carregar() {
  if (!E.carga) {
   E.carga = api('/indicadores').then(p => {
    const ids = p.indicadores.map(i => i.id), col = {};
    p.cols.forEach((c, j) => { if (c !== 'cod') col[c] = p.rows.map(r => r[j]); });
    const cods = p.rows.map(r => r[0]);
    E.dados = {meta: p.meta, ind: p.indicadores, porId: Object.fromEntries(p.indicadores.map(i => [i.id, i])), ids, col, cods,
               idx: new Map(cods.map((c, k) => [c, k])), presets: p.presets, anos: p.cfem_anual.anos, cfem: p.cfem_anual.rows};
    recalcularR2();
    aplicarPreset(E.preset);
    montar();
    return E.dados;
   }).catch(e => { E.carga = null; throw e; });
  }
  return E.carga;
 }
 // R2 recalculado com o ano base e o ano final escolhidos (padrão 2024 e 2025: o mesmo valor do banco)
 function recalcularR2() {
  const D = E.dados, ia = D.anos.indexOf(E.a0), ib = D.anos.indexOf(E.a1);
  D.col.R2 = D.cfem.map(r => crescimento(r[ia], r[ib]));
 }
 function nomeInd(i) { return i.id === 'R2' ? t('in.growth', {a: E.a0, b: E.a1}) : campo(i, 'nome'); }
 function opcoesAnos() {
  const D = E.dados, rot = a => a + (a === D.anos[D.anos.length - 1] ? ' ' + t('in.partial') : '');
  el('in-ano0').innerHTML = D.anos.slice(0, -1).map(a => `<option value="${a}">${escape(rot(a))}</option>`).join('');
  if (!D.anos.slice(0, -1).includes(E.a0)) E.a0 = D.anos[0];
  if (E.a1 <= E.a0) E.a1 = D.anos.find(a => a > E.a0);
  el('in-ano0').value = E.a0;
  el('in-ano1').innerHTML = D.anos.filter(a => a > E.a0).map(a => `<option value="${a}">${escape(rot(a))}</option>`).join('');
  el('in-ano1').value = E.a1;
 }
 function aplicarPreset(id) {
  const p = E.dados.presets.find(x => x.id === id);
  E.preset = id;
  if (p) E.pesos = {...p.pesos};
 }

 // Valores e metadados do que o mapa e o ranking mostram agora (um indicador ou a composição).
 function atual() {
  const D = E.dados;
  if (E.sel === COMP) {
   const c = compor(D.col, E.pesos, E.log, E.todos);
   return {id: COMP, comp: true, nome: t('in.comp'), unidade: '', fmt: 'dec3', valores: c.nota, cobertura: c.cobertura, total: c.total};
  }
  if (E.sel === CUST && E.custom) {
   const c = compilar(E.custom, D.ids);
   return {id: CUST, comp: false, nome: t('in.custom') + ': ' + E.custom, unidade: '', fmt: 'auto', valores: c.ok ? c.valores(D.col, D.cods.length) : D.cods.map(() => null)};
  }
  const i = D.porId[E.sel];
  return {id: i.id, comp: false, nome: nomeInd(i), unidade: i.unidade, fmt: i.fmt, valores: D.col[i.id], ind: i};
 }
 function texto(a, v) { return a.comp ? (valido(v) ? num(v, 3) : null) : formatar(v, a.fmt, num); }

 function selecao() {
  const D = E.dados, a = atual(), cortes = faixas(a.valores, E.escala), pos = posicoes(a.valores);
  const valor = new Map(), posMap = new Map(), cor = new Map();
  D.cods.forEach((c, k) => { valor.set(c, a.valores[k]); posMap.set(c, pos[k]); cor.set(c, corDe(a.valores[k], cortes)); });
  const min = Math.min(...a.valores.filter(valido));
  const itens = [[t('in.noValue'), '#edf1f4']], sufixo = a.ind && a.ind.unidade === 'ha' ? ' ha' : '';
  const limites = [min, ...cortes];
  limites.forEach((c, i) => itens.push([t('at.from') + ' ' + texto(a, c) + sufixo, RAMPA[Math.round(i * (RAMPA.length - 1) / Math.max(1, limites.length - 1))]]));
  return {a, valor, pos: posMap, cor, legenda: itens, texto: v => texto(a, v), nome: a.nome, unidade: a.unidade, comp: a.comp, n: pos.filter(p => p !== null).length};
 }
 // Linhas do painel de detalhe de um município: o valor mostrado, a posição e todos os indicadores.
 function detalhe(cod) {
  const D = E.dados, k = D.idx.get(cod), s = selecao();
  if (k === undefined) return [];
  const linhas = [[s.nome, s.texto(s.valor.get(cod)) || t('in.noValue')], [t('in.rank'), s.pos.get(cod) ? s.pos.get(cod) + ' / ' + s.n : t('in.noValue')]];
  D.ind.forEach(i => linhas.push([i.id + ' · ' + nomeInd(i), formatar(D.col[i.id][k], i.fmt, num) || t('in.noValue')]));
  return linhas;
 }

 // ---------- seções sob o mapa ----------
 function nomeMun(k) { return (M.nomes && M.nomes.get(E.dados.cods[k])) || E.dados.cods[k]; }
 function opcoesIndicador() {
  const D = E.dados, grupos = [];
  D.ind.forEach(i => { const f = campo(i, 'familia'); let g = grupos.find(x => x.f === f); if (!g) { g = {f, l: []}; grupos.push(g); } g.l.push(i); });
  el('in-sel').innerHTML = grupos.map(g => `<optgroup label="${escape(g.f)}">${g.l.map(i => `<option value="${i.id}">${escape(i.id + ' · ' + nomeInd(i))}</option>`).join('')}</optgroup>`).join('')
   + `<optgroup label="${escape(t('in.compGroup'))}"><option value="${COMP}">${escape(t('in.comp'))}</option>${E.custom ? `<option value="${CUST}">${escape(t('in.custom') + ': ' + E.custom)}</option>` : ''}</optgroup>`;
  el('in-sel').value = E.sel;
  el('in-scale').value = E.escala;
 }
 function explicacao() {
  const D = E.dados, linhas = [];
  let fam = '';
  D.ind.forEach(i => {
   if (campo(i, 'familia') !== fam) { fam = campo(i, 'familia'); linhas.push(`<tr class="in-fam"><th colspan="4" scope="colgroup">${escape(fam)}</th></tr>`); }
   linhas.push(`<tr><td><b>${i.id}</b></td><td>${escape(nomeInd(i))}<br><span class="small muted">${escape(i.unidade)}</span></td><td>${escape(campo(i, 'formula'))}</td><td>${escape(campo(i, 'leitura'))}</td></tr>`);
  });
  const rs = lang() === 'en' ? D.meta.ressalvas_en : D.meta.ressalvas;
  el('in-explain').innerHTML = `<div class="table-wrap"><table class="in-table"><thead><tr><th>${escape(t('in.col.code'))}</th><th>${escape(t('in.col.name'))}</th><th>${escape(t('in.col.formula'))}</th><th>${escape(t('in.col.reading'))}</th></tr></thead><tbody>${linhas.join('')}</tbody></table></div>`
   + `<h4>${escape(t('in.caveats'))}</h4><ul class="in-caveats">${rs.map(r => `<li>${escape(r)}</li>`).join('')}</ul>`;
 }
 function ranking_() {
  const s = selecao(), a = s.a, top = ranking(a.valores, E.topo, E.ordem);
  const maxAbs = Math.max(0, ...top.map(x => Math.abs(x.v)));
  const validos = a.valores.filter(valido);
  el('in-rank-title').textContent = t('in.rankOf', {name: s.nome});
  el('in-rank-stats').textContent = t('in.stats', {n: num(validos.length), total: num(a.valores.length), med: texto(a, mediana(validos)) || '—', max: texto(a, Math.max(...validos)) || '—'});
  el('in-rank-bars').innerHTML = top.map((x, i) => {
   const cod = E.dados.cods[x.k], larg = maxAbs ? Math.max(1.5, Math.abs(x.v) / maxAbs * 100) : 1.5;
   return `<button type="button" class="in-bar" data-cod="${escape(cod)}" aria-label="${escape(t('in.locate', {name: nomeMun(x.k)}))}"><span class="in-bar-name">${i + 1}. ${escape(nomeMun(x.k))}</span><span class="in-bar-track"><i style="width:${larg.toFixed(1)}%;background:${s.cor.get(cod) || RAMPA[4]}"></i></span><span class="in-bar-val">${escape(texto(a, x.v))}</span></button>`;
  }).join('') || `<p class="muted">${escape(t('in.noValue'))}</p>`;
  el('in-rank-bars').querySelectorAll('.in-bar').forEach(b => b.onclick = () => escolher(b.dataset.cod, true));
  el('in-rank-note').textContent = a.comp ? t('in.rankCompNote') : t('in.rankNote');
 }
 function avisoSoma(total) {
  el('in-comp-sum').textContent = total > 0 ? t('in.sumW', {n: num(total, 2)}) : t('in.noWeight');
  const soma = Math.round(total * 1e4) / 1e4, aviso = el('in-comp-warn');
  aviso.hidden = soma === 1;
  aviso.textContent = soma > 1 ? t('in.sumOver', {n: num(soma, 2)}) : soma < 1 ? t('in.sumUnder', {n: num(soma, 2)}) : '';
 }
 function composicao() {
  const D = E.dados, linhas = [];
  let fam = '';
  const total = Object.values(E.pesos).reduce((s, w) => s + (w > 0 ? w : 0), 0);
  D.ind.forEach(i => {
   if (campo(i, 'familia') !== fam) { fam = campo(i, 'familia'); linhas.push(`<div class="in-comp-fam">${escape(fam)}</div>`); }
   const w = E.pesos[i.id] || 0, parte = total ? w / total * 100 : 0;
   linhas.push(`<div class="in-comp-row"><label class="in-comp-name"><input type="checkbox" data-on="${i.id}"${w > 0 ? ' checked' : ''}> <b>${i.id}</b> ${escape(nomeInd(i))}</label><input type="number" class="in-num" min="0" max="1" step="0.05" value="${w}" data-n="${i.id}" aria-label="${escape(t('in.weight') + ' ' + i.id)}"><span class="in-share" aria-label="${escape(t('in.share'))}">${num(parte, 0)}%</span></div>`);
  });
  el('in-comp-rows').innerHTML = linhas.join('');
  el('in-preset').innerHTML = `<option value="">${escape(t('in.presetFree'))}</option>` + D.presets.map(p => `<option value="${p.id}">${escape(campo(p, 'nome'))}</option>`).join('');
  el('in-preset').value = E.preset || '';
  el('in-log').checked = E.log;
  el('in-all').checked = E.todos;
  avisoSoma(total);
  const c = compor(D.col, E.pesos, E.log, E.todos), top = ranking(c.nota, 10, 'desc');
  el('in-comp-prev').innerHTML = total > 0 ? top.map((x, i) => `<li><span>${i + 1}. ${escape(nomeMun(x.k))}</span><b>${escape(num(x.v, 3))}</b></li>`).join('') : '';
  el('in-comp-rows').querySelectorAll('[data-n]').forEach(r => r.oninput = () => {
   const v = parseFloat(String(r.value).replace(',', '.'));
   if (!isFinite(v)) return;
   E.pesos[r.dataset.n] = Math.min(1, Math.max(0, v)); E.preset = ''; mudou(false, r.dataset.n);
  });
  el('in-comp-rows').querySelectorAll('[data-on]').forEach(c2 => c2.onchange = () => {
   E.pesos[c2.dataset.on] = c2.checked ? (E.pesos[c2.dataset.on] > 0 ? E.pesos[c2.dataset.on] : 0.25) : 0; E.preset = ''; mudou(true);
  });
 }
 // Reconstrói o que depende do estado; `completo` refaz as linhas da composição (senão só atualiza o que mudou ao arrastar).
 function mudou(completo, editando) {
  if (!E.dados) return;
  if (completo || !el('in-comp-rows').children.length) composicao();
  else {
   const total = Object.values(E.pesos).reduce((s, w) => s + (w > 0 ? w : 0), 0);
   el('in-comp-rows').querySelectorAll('.in-comp-row').forEach(r => {
    const nn = r.querySelector('[data-n]'), id = nn.dataset.n, w = E.pesos[id] || 0; if (nn.dataset.n !== editando) nn.value = w; r.querySelector('.in-share').textContent = num(total ? w / total * 100 : 0, 0) + '%';
    r.querySelector('[data-on]').checked = w > 0;
   });
   el('in-preset').value = E.preset || '';
   avisoSoma(total);
   const c = compor(E.dados.col, E.pesos, E.log, E.todos), top = ranking(c.nota, 10, 'desc');
   el('in-comp-prev').innerHTML = total > 0 ? top.map((x, i) => `<li><span>${i + 1}. ${escape(nomeMun(x.k))}</span><b>${escape(num(x.v, 3))}</b></li>`).join('') : '';
  }
  if (E.sel === COMP) { ranking_(); }
  desenhar();
 }
 function montar() {
  montarPersonalizado(); opcoesAnos(); opcoesIndicador(); explicacao(); ranking_(); composicao();
  const trocouAnos = () => { recalcularR2(); opcoesIndicador(); explicacao(); ranking_(); composicao(); desenhar(); };
  el('in-ano0').onchange = () => { E.a0 = +el('in-ano0').value; opcoesAnos(); trocouAnos(); };
  el('in-ano1').onchange = () => { E.a1 = +el('in-ano1').value; trocouAnos(); };
  el('in-sel').onchange = () => { E.sel = el('in-sel').value; ranking_(); composicao(); desenhar(); };
  el('in-scale').onchange = () => { E.escala = el('in-scale').value; desenhar(); };
  el('in-top').onchange = () => { E.topo = +el('in-top').value; ranking_(); };
  el('in-order').onchange = () => { E.ordem = el('in-order').value; ranking_(); };
  el('in-preset').onchange = () => { const v = el('in-preset').value; if (v) { aplicarPreset(v); mudou(true); } else E.preset = ''; };
  el('in-log').onchange = () => { E.log = el('in-log').checked; mudou(false); };
  el('in-all').onchange = () => { E.todos = el('in-all').checked; mudou(false); };
  el('in-comp-clear').onclick = () => { E.pesos = {}; E.preset = ''; mudou(true); };
 }



 // ---------- indicador personalizado (fórmula) ----------
 function mensagemErro(e) {
  switch (e.erro) {
   case 'vazio': return t('in.err.empty');
   case 'caractere': return t('in.err.char', {c: e.dado});
   case 'id': return t('in.err.id', {c: e.dado});
   case 'parenteses': return t('in.err.paren');
   default: return t('in.err.syntax', {c: e.dado || t('in.err.end')});
  }
 }
 function montarPersonalizado() {
  const D = E.dados, campoF = el('in-formula'), msg = el('in-formula-msg');
  el('in-codes').innerHTML = D.ind.map(i => `<button type="button" class="in-code" data-code="${i.id}" title="${escape(nomeInd(i))}">${i.id}</button>`).join('');
  el('in-codes').querySelectorAll('[data-code]').forEach(b => b.onclick = () => {
   const a = campoF.selectionStart ?? campoF.value.length, z = campoF.selectionEnd ?? a;
   const antes = campoF.value.slice(0, a), depois = campoF.value.slice(z);
   const ins = (antes && !/[\s(+\-*\/]$/.test(antes) ? ' ' : '') + b.dataset.code + (depois && !/^[\s)+\-*\/]/.test(depois) ? ' ' : '');
   campoF.value = antes + ins + depois;
   campoF.focus(); const p = a + ins.length; campoF.setSelectionRange(p, p);
  });
  const calcular = () => {
   const c = compilar(campoF.value, D.ids);
   msg.classList.toggle('in-warn', !c.ok);
   if (!c.ok) { msg.textContent = mensagemErro(c); return; }
   const n = c.valores(D.col, D.cods.length).filter(valido).length;
   if (!n) { msg.classList.add('in-warn'); msg.textContent = t('in.err.noValue'); return; }
   E.custom = campoF.value.trim(); E.sel = CUST;
   msg.textContent = t('in.customOk', {n: num(n)});
   opcoesIndicador(); ranking_(); composicao(); desenhar();
   el('in-map').scrollIntoView({behavior: 'smooth', block: 'center'});
  };
  el('in-formula-go').onclick = calcular;
  campoF.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); calcular(); } };
 }

 // ---------- mapa próprio da seção ----------
 const M = {map: null, camada: null, pol: new Map(), pacote: null, nomes: null, sel: null, destaque: null, carga: null};
 function desenhar() {
  if (E.dados) { el('in-comp-box').hidden = E.sel !== COMP; el('in-ano-wrap').hidden = !(E.sel === 'R2' || (E.sel === COMP && E.pesos.R2 > 0)); }
  if (!M.map || !E.dados) return;
  const s = selecao(), D = E.dados;
  M.camada.clearLayers(); M.pol.clear();
  M.pacote.municipalities.forEach(m => {
   const v = s.valor.get(m.code), shape = L.polygon(m.rings, {weight: .7, color: '#57768b', fillColor: s.cor.get(m.code) || '#edf1f4', fillOpacity: .8, fillRule: 'evenodd'}).addTo(M.camada);
   shape.bindTooltip(escape(m.name + ' · ' + (s.texto(v) || t('in.noValue'))));
   shape.on('click', () => escolher(m.code, false));
   M.pol.set(m.code, shape);
  });
  el('in-legend').innerHTML = s.legenda.map(([rot, cor]) => `<div class="legend-item"><span class="legend-swatch" style="background:${cor}"></span><span>${escape(rot)}</span></div>`).join('');
  el('in-map-note').textContent = t(E.escala === 'l' ? 'in.mapNoteL' : 'in.mapNoteQ');
  el('in-context').textContent = t('in.context', {name: s.nome});
  if (M.sel) escolher(M.sel, false, true);
 }
 function escolher(cod, aproximar, manter) {
  if (!E.dados || !M.pol.has(cod)) return;
  M.sel = cod;
  const k = E.dados.idx.get(cod), nome = (M.nomes && M.nomes.get(cod)) || cod;
  el('in-detail-title').textContent = nome;
  el('in-detail-body').innerHTML = '<dl>' + [[t('at.ibge'), cod], ...detalhe(cod)].map(([a, b]) => `<dt>${escape(a)}</dt><dd>${escape(b)}</dd>`).join('') + '</dl>';
  if (M.destaque) { M.destaque.remove(); M.destaque = null; }
  const shape = M.pol.get(cod);
  M.destaque = L.polygon(shape.getLatLngs(), {color: '#07345c', weight: 2, fill: false, dashArray: '5 4', interactive: false}).addTo(M.map);
  if (aproximar && !manter) { M.map.fitBounds(shape.getBounds(), {maxZoom: 10, padding: [30, 30]}); shape.openTooltip(); el('in-map').scrollIntoView({behavior: 'smooth', block: 'center'}); }
 }
 async function mostrar() {
  el('in-error').textContent = '';
  try {
   if (!M.carga) M.carga = (async () => {
    if (!window.L) throw Error(t('at.leafletFail'));
    const [, pacote] = await Promise.all([carregar(), window.loadAtlas ? window.loadAtlas() : api('/atlas')]);
    M.pacote = pacote; M.nomes = new Map(pacote.municipalities.map(m => [m.code, m.name]));
    el('in-content').hidden = false;
    M.map = L.map('in-map', {preferCanvas: true, scrollWheelZoom: true, minZoom: 5, maxZoom: 14, zoomSnap: .25});
    L.control.scale({imperial: false}).addTo(M.map);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'})
     .on('tileerror', () => { el('in-error').textContent = t('at.tileFail'); }).addTo(M.map);
    M.camada = L.layerGroup().addTo(M.map);
    const pts = pacote.municipalities.flatMap(m => m.rings.flat());
    M.map.fitBounds(L.latLngBounds(pts));
    ranking_(); desenhar();
   })().catch(e => { M.carga = null; if (M.map) { M.map.remove(); M.map = null; } throw e; });
   await M.carga;
   el('in-loading').hidden = true; el('in-content').hidden = false;
   setTimeout(() => M.map && M.map.invalidateSize(), 50);
  } catch (e) { el('in-loading').hidden = true; el('in-error').textContent = e.message; }
 }

 window.showIndicadores = mostrar;
 window.AtInd = {pronto: carregar, selecao, detalhe};
})(typeof window !== 'undefined' ? window : globalThis);
