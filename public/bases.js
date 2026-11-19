/* Base de dados: catalogue of every data base the system uses. Each card carries the three fields the catalogue exists for —
   name, origin and last update — and the data comes from /api/catalogo (authenticated), rebuilt by scripts/build_catalogo_painel.py.
   Nothing is computed here: the generator counts rows and reads dates from the packets and from git, so the page cannot drift
   from the bases it describes. */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc;
let dados=null,loaded=false;

const num=v=>I18N.num(v,{maximumFractionDigits:0});
// Chaves escritas por extenso: montá-las por concatenação esconderia do teste de tradução quais existem.
const rotuloNatureza=n=>({bruta:t('bd.nat.bruta'),derivada:t('bd.nat.derivada'),curada:t('bd.nat.curada'),
 coletada:t('bd.nat.coletada')}[n]||n);
const tomNatureza=n=>({bruta:'a',derivada:'b',curada:'c',coletada:'d'}[n]||'a');

const filtradas=()=>{
 const familia=el('bd-familia').value,natureza=el('bd-natureza').value,
       busca=el('bd-busca').value.trim().toLowerCase();
 return dados.bases.filter(b=>
   (!familia||b.familia===familia)&&(!natureza||b.natureza===natureza)&&
   (!busca||[b.nome,b.origem,b.mede,b.onde].join(' ').toLowerCase().includes(busca)));};

function preencher(select,valores,rotuloVazio){
 select.innerHTML=`<option value="">${escape(rotuloVazio)}</option>`
  +valores.map(v=>`<option value="${escape(v[0])}">${escape(v[1])}</option>`).join('');}

function metricas(bases){
 const familias=new Set(bases.map(b=>b.familia));
 const datas=bases.map(b=>b.atualizado_em).filter(d=>d&&d!=='NA').sort();
 return [
  ['a',t('bd.m.bases'),num(bases.length),t('bd.m.basesSub')],
  ['b',t('bd.m.familias'),num(familias.size),t('bd.m.familiasSub')],
  ['c',t('bd.m.recente'),datas.length?datas[datas.length-1]:'—',t('bd.m.recenteSub')],
  ['d',t('bd.m.antiga'),datas.length?datas[0]:'—',t('bd.m.antigaSub')],
 ].map(([tom,rotulo,valor,detalhe])=>`<div class="metric tone-${tom}"><span>${escape(rotulo)}</span>`
   +`<strong>${escape(valor)}</strong><small>${escape(detalhe)}</small></div>`).join('');}

/* O cartão abre pelo cabeçalho de três campos — nome, origem e última atualização —, que é o que o catálogo existe para responder.
   Só depois vêm período, volume, onde vive e o que mede. */
function cartao(b){
 const readme=b.readme?`<a class="bd-readme" href="https://github.com/mineragoias-rgb/minera-goias/blob/main/${escape(b.readme)}"`
   +` target="_blank" rel="noopener noreferrer">${escape(t('bd.readme'))}</a>`:'';
 const campo=(rotulo,valor)=>valor&&valor!=='NA'
   ?`<div class="bd-campo"><span>${escape(rotulo)}</span><p>${escape(valor)}</p></div>`:'';
 return `<article class="panel bd-card">`
  +`<header class="bd-head">`
   +`<div class="bd-head-nome"><span>${escape(t('bd.hNome'))}</span><h3>${escape(b.nome)}</h3>`
    // As etiquetas ficam numa linha flex própria: como inline depois do h3, elas transbordavam o cabeçalho
    // quando o nome quebrava em três linhas, e invadiam o primeiro rótulo do corpo.
    +`<div class="bd-tags"><small class="pill tone-${escape(tomNatureza(b.natureza))}">${escape(rotuloNatureza(b.natureza))}</small>`
    +`<small class="pill">${escape(b.familia)}</small></div></div>`
   +`<div class="bd-head-origem"><span>${escape(t('bd.hOrigem'))}</span><p>${escape(b.origem)}</p></div>`
   +`<div class="bd-head-data"><span>${escape(t('bd.hAtualizado'))}</span><strong>${escape(b.atualizado_em||'—')}</strong></div>`
  +`</header>`
  +`<div class="bd-grid">`
   +campo(t('bd.periodo'),b.periodo)+campo(t('bd.volume'),b.volume)+campo(t('bd.onde'),b.onde)
   +campo(t('bd.mede'),b.mede)+campo(t('bd.naoMede'),b.nao_mede)
  +`</div>${readme}</article>`;}

function lista(bases){
 if(!bases.length)return `<p class="mk-note">${escape(t('bd.vazio'))}</p>`;
 const ordem=[...new Set(dados.bases.map(b=>b.familia))];
 return ordem.map(familia=>{
  const doGrupo=bases.filter(b=>b.familia===familia);
  if(!doGrupo.length)return '';
  return `<h3 class="mk-sub">${escape(familia)} · ${escape(num(doGrupo.length))}</h3>`
   +`<div class="bd-lista">${doGrupo.map(cartao).join('')}</div>`}).join('');}

function desenhar(){
 const bases=filtradas();
 el('bd-metrics').innerHTML=metricas(bases);
 el('bd-lista').innerHTML=lista(bases);
 el('bd-context').textContent=t('bd.contexto',{bases:num(bases.length),total:num(dados.bases.length)});}

async function load(){
 el('bases-error').textContent='';
 try{
  dados=await api('/catalogo');
  const familias=[...new Set(dados.bases.map(b=>b.familia))];
  const naturezas=[...new Set(dados.bases.map(b=>b.natureza))];
  preencher(el('bd-familia'),familias.map(f=>[f,f]),t('bd.todasFamilias'));
  preencher(el('bd-natureza'),naturezas.map(n=>[n,rotuloNatureza(n)]),t('bd.todasNaturezas'));
  ['bd-familia','bd-natureza'].forEach(id=>el(id).onchange=desenhar);
  el('bd-busca').oninput=desenhar;
  el('bd-reset').onclick=()=>{['bd-familia','bd-natureza','bd-busca'].forEach(id=>el(id).value='');desenhar()};
  el('bd-nota').textContent=t('bd.nota');
  el('bd-fonte').textContent=t('bd.fonte',{data:dados.meta.built_on});
  desenhar();
  el('bases-content').hidden=false;
 }catch(e){el('bases-error').textContent=e.message}
 finally{el('bases-loading').hidden=true}}

window.showBases=()=>{if(loaded)return;loaded=true;load()};
})();
