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
   (!busca||[b.nome,b.origem,b.mede].join(' ').toLowerCase().includes(busca)));};

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

/* Cartão curto: nome, etiquetas, uma linha do que mede, período e data. O resto (origem, volume, o que não mede e a documentação)
   fica no quadro que abre em "Documentação", para a aba caber na tela sem rolar páginas de cartões. */
function cartao(b){
 const periodo=b.periodo&&b.periodo!=='NA'?b.periodo:'';
 const meta=[periodo,b.atualizado_em?t('bd.atualizada',{data:b.atualizado_em}):''].filter(Boolean).join(' · ');
 return `<article class="panel bd-card">`
  +`<header class="bd-head"><h3>${escape(b.nome)}</h3>`
   +`<div class="bd-tags"><small class="pill tone-${escape(tomNatureza(b.natureza))}">${escape(rotuloNatureza(b.natureza))}</small>`
   +`<small class="pill">${escape(b.familia)}</small></div></header>`
  +(b.mede&&b.mede!=='NA'?`<p class="bd-mede">${escape(b.mede)}</p>`:'')
  +`<p class="bd-meta">${escape(meta)}</p>`
  +`<div class="bd-acoes">${botaoBaixar(b)}<button type="button" class="btn outline bd-btn" data-bd-doc="${escape(b.id)}">${escape(t('bd.abrir'))}</button></div>`
  +`</article>`;}

/* A documentação vem do README da base, como está no repositório. O texto é escapado antes de qualquer marcação; só depois
   viram tag os títulos (##), listas (-, 1.), tabelas (| … |), `código` e **negrito**. Links viram só o texto: o site não manda
   o usuário para o repositório. */
function inline(txt){
 return escape(txt).replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').replace(/`([^`]+)`/g,'<code>$1</code>')
  .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');}
function markdown(md){
 const linhas=md.split('\n'),html=[];let i=0;
 const celulas=l=>l.trim().replace(/^\||\|$/g,'').split('|').map(c=>c.trim());
 while(i<linhas.length){
  const l=linhas[i];
  if(!l.trim()){i++;continue}
  const h=l.match(/^(#{2,4})\s+(.*)$/);
  if(h){html.push(`<h${h[1].length+1}>${inline(h[2])}</h${h[1].length+1}>`);i++;continue}
  if(l.trim().startsWith('|')){
   const bloco=[];while(i<linhas.length&&linhas[i].trim().startsWith('|'))bloco.push(linhas[i++]);
   const corpo=bloco.filter((x,k)=>!(k===1&&/^\|?[\s:|-]+\|?$/.test(x.trim())));
   html.push('<div class="bd-doc-tabela"><table>'+corpo.map((x,k)=>'<tr>'+celulas(x).map(c=>k===0?`<th>${inline(c)}</th>`:`<td>${inline(c)}</td>`).join('')+'</tr>').join('')+'</table></div>');
   continue}
  if(/^\s*([-*]|\d+\.)\s+/.test(l)){
   const ordenada=/^\s*\d+\./.test(l),itens=[];
   while(i<linhas.length&&linhas[i].trim()&&!/^#{2,4}\s/.test(linhas[i])&&!linhas[i].trim().startsWith('|')){
    if(/^\s*([-*]|\d+\.)\s+/.test(linhas[i]))itens.push(linhas[i].replace(/^\s*([-*]|\d+\.)\s+/,''));
    else itens[itens.length-1]+=' '+linhas[i].trim();
    i++}
   html.push(`<${ordenada?'ol':'ul'}>`+itens.map(x=>`<li>${inline(x)}</li>`).join('')+`</${ordenada?'ol':'ul'}>`);continue}
  const par=[];
  while(i<linhas.length&&linhas[i].trim()&&!/^#{2,4}\s/.test(linhas[i])&&!linhas[i].trim().startsWith('|')&&!/^\s*([-*]|\d+\.)\s+/.test(linhas[i]))
   par.push(linhas[i++].trim());
  html.push(`<p>${inline(par.join(' '))}</p>`)}
 return html.join('');}

/* Baixar: link para a rota com login; a sessão vai no próprio pedido. Base sem arquivo no repositório (o agente semanal, que vive
   no servidor) fica sem o botão. */
const botaoBaixar=b=>b.download?`<a class="btn outline bd-btn" href="/api/catalogo/baixar/${encodeURIComponent(b.id)}" download>${escape(t('bd.baixar'))}</a>`:'';
const resumoArquivos=d=>t('bd.arquivos',{n:num(d.arquivos.length),mb:d.tamanho_mb<0.1?'< 0,1':I18N.num(d.tamanho_mb,{maximumFractionDigits:1}),
 formatos:d.formatos.join(', ')});

/* O quadro de detalhes: os campos do catálogo e, quando houver, a documentação da base. */
function quadro(b){
 const campo=(rotulo,valor)=>valor&&valor!=='NA'
   ?`<div class="bd-campo"><span>${escape(rotulo)}</span><p>${escape(valor)}</p></div>`:'';
 return `<div class="bd-modal-topo"><div><h2 id="bd-modal-titulo">${escape(b.nome)}</h2>`
   +`<div class="bd-tags"><small class="pill tone-${escape(tomNatureza(b.natureza))}">${escape(rotuloNatureza(b.natureza))}</small>`
   +`<small class="pill">${escape(b.familia)}</small></div></div>`
   +`<button type="button" class="bd-fechar" data-bd-fechar aria-label="${escape(t('bd.fechar'))}">×</button></div>`
  +`<div class="bd-modal-grid">`
   +campo(t('bd.hOrigem'),b.origem)+campo(t('bd.periodo'),b.periodo)+campo(t('bd.volume'),b.volume)
   +campo(t('bd.hAtualizado'),b.atualizado_em)+`</div>`
  +`<div class="bd-modal-texto">`+campo(t('bd.mede'),b.mede)+campo(t('bd.naoMede'),b.nao_mede)+`</div>`
  +(b.download?`<div class="bd-modal-baixar"><p>${escape(resumoArquivos(b.download))}</p>${botaoBaixar(b)}</div>`:'')
  +(b.doc?`<div class="bd-doc"><span class="bd-doc-rotulo">${escape(t('bd.docT'))}</span>${markdown(b.doc)}</div>`:'');}

function abrir(id){
 const b=dados.bases.find(x=>x.id===id);
 if(!b)return;
 el('bd-modal-corpo').innerHTML=quadro(b);
 el('bd-modal').hidden=false;
 el('bd-modal-corpo').querySelector('[data-bd-fechar]').focus();}
function fechar(){el('bd-modal').hidden=true}

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
  el('bd-lista').onclick=e=>{const b=e.target.closest('[data-bd-doc]');if(b)abrir(b.dataset.bdDoc)};
  el('bd-modal').onclick=e=>{if(e.target===el('bd-modal')||e.target.closest('[data-bd-fechar]'))fechar()};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!el('bd-modal').hidden)fechar()});
  el('bd-nota').textContent=t('bd.nota');
  el('bd-fonte').textContent=t('bd.fonte',{data:dados.meta.built_on});
  desenhar();
  el('bases-content').hidden=false;
 }catch(e){el('bases-error').textContent=e.message}
 finally{el('bases-loading').hidden=true}}

window.showBases=()=>{if(loaded)return;loaded=true;load()};
})();
