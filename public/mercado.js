/* Market tab: public-source reading of the critical-minerals market around Goiás.
   Everything rendered here comes from public/data/mercado/mercado_v1.json — press,
   published company results and sector studies — never from the consolidated base. */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc;
const SOURCE='/data/mercado/mercado_v1.json';
const VIZ={a:'#0f6fb0',b:'#0d9488',c:'#c2681b',d:'#8250c4'};
let loaded=false;

// Every prose field in the file carries both languages; plain strings pass through.
const L=v=>v&&typeof v==='object'&&!Array.isArray(v)?(v[I18N.lang]??v.pt):v;

function metrics(rows){
 return rows.map(r=>`<div class="metric tone-${escape(r.tom)}"><span>${escape(L(r.rotulo))}</span>`
  +`<strong>${escape(L(r.valor))}</strong><small>${escape(L(r.detalhe))}</small></div>`).join('')}

function operationsTable(rows){
 return `<table><thead><tr><th>${escape(t('mk.thMineral'))}</th><th>${escape(t('mk.thLocal'))}</th>`
  +`<th>${escape(t('mk.thSituacao'))}</th></tr></thead><tbody>`
  +rows.map(r=>`<tr><td><b>${escape(L(r.mineral))}</b><div class="mk-note">${escape(L(r.nota))}</div></td>`
   +`<td>${escape(L(r.local))}</td><td><span class="pill">${escape(L(r.situacao))}</span></td></tr>`).join('')
  +'</tbody></table>'}

function dealBars(rows){
 const max=Math.max(...rows.map(r=>r.valor_usd_milhoes),1);
 return rows.map(r=>`<div class="bar-row"><span class="bar-label" title="${escape(L(r.ativo))}">${escape(L(r.ativo))}</span>`
  +`<div class="bar-track"><div class="bar-fill" style="width:${r.valor_usd_milhoes/max*100}%;background:${VIZ.a}"></div></div>`
  +`<span class="bar-value">${escape(L(r.rotulo))}</span></div>`
  +`<p class="mk-note">${escape(r.comprador)} · ${escape(I18N.num(r.ano,{useGrouping:false}))}</p>`).join('')}

function priceBlock(block){
 const max=Math.max(...block.pontos.map(p=>p.valor),1);
 return `<h3 class="mk-sub">${escape(L(block.rotulo))}</h3>`
  +block.pontos.map(p=>`<div class="bar-row"><span class="bar-label">${escape(L(p.quando))}</span>`
   +`<div class="bar-track"><div class="bar-fill" style="width:${p.valor/max*100}%;background:${VIZ.c}"></div></div>`
   +`<span class="bar-value">${escape(L(p.rotulo))}</span></div>`).join('')
  +`<p class="mk-note">${escape(L(block.nota))}</p>`}

function referenceTable(rows){
 return `<table><thead><tr><th>${escape(t('mk.thEmpresa'))}</th><th>${escape(t('mk.thMineral'))}</th>`
  +`<th>${escape(t('mk.thReceita'))}</th><th>${escape(t('mk.thResultado'))}</th></tr></thead><tbody>`
  +rows.map(r=>`<tr><td><b>${escape(r.empresa)}</b><div class="mk-note">${escape(L(r.onde))} · ${escape(L(r.praca))}</div>`
   +`<div class="mk-note">${escape(L(r.nota))}</div></td><td>${escape(L(r.mineral))}</td>`
   +`<td>${escape(L(r.receita))}</td><td>${escape(L(r.resultado))}</td></tr>`).join('')+'</tbody></table>'}

function ruleList(rows){
 return '<ul class="mk-list">'+rows.map(r=>`<li><b class="mk-code">${escape(r.sigla)}</b>`
  +`<b>${escape(L(r.nome))}</b><span class="muted">${escape(L(r.descricao))}</span></li>`).join('')+'</ul>'}

function newsList(rows){
 return '<ul class="rd-news">'+rows.map(r=>{
   const quando=String(r.data||'');
   return `<li><a href="${escape(r.link)}" target="_blank" rel="noopener noreferrer">${escape(L(r.titulo))}</a>`
    +`<span class="muted">${escape(r.fonte)}${quando?' · '+escape(quando):''}</span>`
    +`<span class="mk-note">${escape(L(r.resumo))}</span></li>`}).join('')+'</ul>'}

function plainList(rows){
 return '<ul class="mk-bullets">'+rows.map(r=>`<li>${escape(L(r))}</li>`).join('')+'</ul>'}

function sourceList(rows){
 return rows.map(r=>`<a href="${escape(r.link)}" target="_blank" rel="noopener noreferrer">${escape(r.nome)}</a>`).join(' · ')}

/* Carteira de projetos: the Squad 1 survey by Lucas Maia, published as-is by scripts/build_projetos_go.py.
   Texts stay in Portuguese, as surveyed; only labels are translated. Nothing is summed here: capacities come in
   different units and CAPEX in different years. */
const PROJETOS='/data/mercado/projetos_go_v1.json';
let carteira=null;
// Keys written out in full on purpose: building them by concatenation would hide from the translation test which ones exist.
const rotuloMaturidade=m=>({'OPERAÇÃO':t('mk.pj.m.operacao'),'EXPANSÃO':t('mk.pj.m.expansao'),'CONSTRUÇÃO':t('mk.pj.m.construcao'),
 'DEFINIDO':t('mk.pj.m.definido'),'PROVÁVEL':t('mk.pj.m.provavel'),'POSSÍVEL':t('mk.pj.m.possivel'),'SINAL':t('mk.pj.m.sinal')}[m]||m);
const rotuloConfianca=c=>({'ALTO':t('mk.pj.c.alto'),'MÉDIO':t('mk.pj.c.medio'),'BAIXO':t('mk.pj.c.baixo')}[c]||c);
// Firm, in progress, early: the same three tones the Radar uses for authorised, under review and may reopen.
const tomMaturidade=m=>['OPERAÇÃO','EXPANSÃO'].includes(m)?VIZ.b:['CONSTRUÇÃO','DEFINIDO'].includes(m)?VIZ.a
 :['PROVÁVEL','POSSÍVEL'].includes(m)?VIZ.c:VIZ.d;
const dataCurta=d=>d?(I18N.lang==='en'?d:d.split('-').reverse().join('/')):'—';
const capex=c=>c.moeda==='US$ milhões'?t('mk.pj.capexUsdMi',{valor:I18N.num(c.valor)}):`${I18N.num(c.valor)} ${c.moeda}`;

const projetosFiltrados=()=>{
 const mat=el('mk-pj-mat').value,min=el('mk-pj-min').value,busca=el('mk-pj-busca').value.trim().toLowerCase();
 return carteira.projetos.filter(p=>(!mat||p.maturidade===mat)&&(!min||p.mineral===min)&&
  (!busca||[p.projeto,p.empresa,p.controladora,p.municipio].some(v=>String(v||'').toLowerCase().includes(busca))))};

function barrasProjetos(itens,max,attr){
 return itens.map(([chave,rotulo,n,cor])=>`<button type="button" class="bar-row mk-pj-bar" data-${attr}="${escape(chave)}">`
  +`<span class="bar-label" title="${escape(rotulo)}">${escape(rotulo)}</span>`
  +`<span class="bar-track"><span class="bar-fill" style="width:${n/max*100}%;background:${cor}"></span></span>`
  +`<span class="bar-value">${escape(I18N.num(n))}</span></button>`).join('')}

function funil(lista){
 // All seven tags, empty ones included: an empty rung (no construction underway) is information too.
 const itens=carteira.meta.hierarquia.map(m=>[m,rotuloMaturidade(m),lista.filter(p=>p.maturidade===m).length,tomMaturidade(m)]);
 return barrasProjetos(itens,Math.max(...itens.map(i=>i[2]),1),'mat')}

function porMineral(lista){
 const contagem=new Map();lista.forEach(p=>contagem.set(p.mineral,(contagem.get(p.mineral)||0)+1));
 const itens=[...contagem.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([m,n])=>[m,m,n,VIZ.a]);
 return itens.length?barrasProjetos(itens,Math.max(...itens.map(i=>i[2]),1),'min'):`<p class="mk-note">${escape(t('mk.pj.vazio'))}</p>`}

function tabelaProjetos(lista){
 if(!lista.length)return `<p class="mk-note">${escape(t('mk.pj.vazio'))}</p>`;
 const ordem=carteira.meta.hierarquia;
 const linhas=[...lista].sort((a,b)=>ordem.indexOf(a.maturidade)-ordem.indexOf(b.maturidade)||a.id.localeCompare(b.id));
 const cab=['mk.pj.thProjeto','mk.pj.thMineral','mk.pj.thMunicipio','mk.pj.thMaturidade','mk.pj.thPorte','mk.pj.thCapex','mk.pj.thEntrada','mk.pj.thFonte']
  .map(k=>`<th>${escape(t(k))}</th>`).join('');
 return `<table><thead><tr>${cab}</tr></thead><tbody>`+linhas.map(p=>{
  const empresa=p.controladora&&p.controladora!==p.empresa?`${escape(p.empresa)} · ${escape(p.controladora)}`:escape(p.empresa);
  const porte=[p.capacidade?`${escape(t('mk.pj.capacidade'))}: ${escape(p.capacidade.valor)} ${escape(p.capacidade.unidade||'')}`:'',
   p.producao?`${escape(t('mk.pj.producao'))}: ${escape(p.producao.valor)} ${escape(p.producao.unidade||'')}`:''].filter(Boolean);
  const fonte=p.link?`<a href="${escape(p.link)}" target="_blank" rel="noopener noreferrer">${escape(p.fonte)}</a>`:escape(p.fonte);
  return `<tr><td><b>${escape(p.projeto)}</b> <span class="mk-code">${escape(p.id)}</span><div class="mk-note">${empresa}</div>`
   +(p.parceiros?`<div class="mk-note">${escape(t('mk.pj.parceiros',{parceiros:p.parceiros}))}</div>`:'')
   +`<div class="mk-note">${escape(p.evidencia)}</div>`
   +(p.observacoes?`<details><summary>${escape(t('mk.pj.obs'))}</summary>${escape(p.observacoes)}</details>`:'')+'</td>'
   +`<td><b>${escape(p.mineral)}</b>${p.outros_minerais?`<div class="mk-note">${escape(p.outros_minerais)}</div>`:''}</td>`
   +`<td>${escape(p.municipio)}</td>`
   +`<td><span class="pill" style="border-left:3px solid ${tomMaturidade(p.maturidade)}">${escape(rotuloMaturidade(p.maturidade))}</span>`
   +`<div class="mk-note">${escape(p.fase)}${p.status?' · '+escape(p.status):''}</div>`
   +(p.estagio?`<div class="mk-note">${escape(p.estagio)}</div>`:'')+'</td>'
   +`<td>${porte.length?porte.map(x=>`<div>${x}</div>`).join(''):'—'}</td>`
   +`<td>${p.capex?`<b>${escape(capex(p.capex))}</b><div class="mk-note">${escape(t('mk.pj.capexAno',{ano:String(p.capex.ano)}))}</div>`:'—'}</td>`
   +`<td>${p.ano_previsto?escape(String(p.ano_previsto)):'—'}</td>`
   +`<td>${fonte}<div class="mk-note">${escape(t('mk.pj.infoDe',{data:dataCurta(p.data_informacao)}))}</div>`
   +`<span class="pill">${escape(t('mk.pj.confianca',{nivel:rotuloConfianca(p.confianca)}))}</span>`
   +(p.outras_evidencias?`<div class="mk-note">${escape(p.outras_evidencias)}</div>`:'')+'</td></tr>'}).join('')+'</tbody></table>'}

function noticiasProjetos(lista){
 const ids=new Set(lista.map(p=>p.id)),nomes=new Map(carteira.projetos.map(p=>[p.id,p.projeto]));
 const itens=carteira.noticias.filter(n=>ids.has(n.projeto_id)).sort((a,b)=>String(b.data).localeCompare(String(a.data)));
 if(!itens.length)return `<p class="mk-note">${escape(t('mk.pj.semNoticias'))}</p>`;
 return '<ul class="rd-news">'+itens.map(n=>`<li>`
  +(n.link?`<a href="${escape(n.link)}" target="_blank" rel="noopener noreferrer">${escape(n.titulo)}</a>`:escape(n.titulo))
  +`<span class="muted">${escape(n.veiculo)} · ${escape(dataCurta(n.data))}${n.relevancia?' · '+escape(t('mk.pj.relevancia',{nivel:n.relevancia})):''}</span>`
  +`<span class="mk-note">${escape(nomes.get(n.projeto_id)||n.projeto_id)} — ${escape(n.evidencia||'')}</span></li>`).join('')+'</ul>'}

function desenharProjetos(){
 const lista=projetosFiltrados();
 el('mk-pj-funil').innerHTML=funil(lista);
 el('mk-pj-minerais').innerHTML=porMineral(lista);
 el('mk-pj-tabela').innerHTML=tabelaProjetos(lista);
 el('mk-pj-noticias').innerHTML=noticiasProjetos(lista);
 el('mk-pj-count').textContent=t('mk.pj.contagem',{n:I18N.num(lista.length),total:I18N.num(carteira.projetos.length),
  operacao:I18N.num(lista.filter(p=>p.maturidade==='OPERAÇÃO').length),capex:I18N.num(lista.filter(p=>p.capex).length)});
 // A bar is a shortcut for the select above it; clicking the active one clears it.
 el('mk-projetos').querySelectorAll('[data-mat]').forEach(b=>b.onclick=()=>{
  el('mk-pj-mat').value=el('mk-pj-mat').value===b.dataset.mat?'':b.dataset.mat;desenharProjetos()});
 el('mk-projetos').querySelectorAll('[data-min]').forEach(b=>b.onclick=()=>{
  el('mk-pj-min').value=el('mk-pj-min').value===b.dataset.min?'':b.dataset.min;desenharProjetos()});}

async function loadProjetos(){
 // Separate from the main market file: if the survey fails to load, the rest of the tab still renders.
 try{
  const r=await fetch(PROJETOS,{cache:'no-store'});
  if(!r.ok)throw Error(t('mk.pj.fail'));
  carteira=await r.json();
  const opcoes=(itens,vazio)=>`<option value="">${escape(vazio)}</option>`
   +itens.map(([v,rotulo])=>`<option value="${escape(v)}">${escape(rotulo)}</option>`).join('');
  el('mk-pj-mat').innerHTML=opcoes(carteira.meta.hierarquia.map(m=>[m,rotuloMaturidade(m)]),t('mk.pj.todasMaturidades'));
  el('mk-pj-min').innerHTML=opcoes([...new Set(carteira.projetos.map(p=>p.mineral))].sort().map(m=>[m,m]),t('mk.pj.todosMinerais'));
  ['mk-pj-mat','mk-pj-min'].forEach(id=>el(id).onchange=desenharProjetos);
  el('mk-pj-busca').oninput=desenharProjetos;
  el('mk-pj-reset').onclick=()=>{['mk-pj-mat','mk-pj-min','mk-pj-busca'].forEach(id=>el(id).value='');desenharProjetos()};
  el('mk-pj-nota').textContent=t('mk.pj.nota');
  el('mk-pj-metodo').innerHTML=carteira.metodologia.map(m=>`<li><b>${escape(m.parametro)}</b><span class="muted">${escape(m.descricao)}</span></li>`).join('');
  el('mk-pj-fonte').textContent=t('mk.pj.fonte',{autoria:L(carteira.meta.autoria),origem:carteira.meta.origem,
   data:dataCurta(carteira.meta.consultado_ate)});
  desenharProjetos();
 }catch(e){el('mk-pj-error').textContent=e.message}}

async function load(){
 el('mercado-error').textContent='';
 try{
  const r=await fetch(SOURCE,{cache:'no-store'});
  if(!r.ok)throw Error(t('mk.fail'));
  const d=await r.json();
  el('mk-metrics').innerHTML=metrics(d.indicadores);
  el('mk-nota').textContent=L(d.nota);
  el('mk-operacoes').innerHTML=operationsTable(d.operacoes);
  el('mk-transacoes').innerHTML=dealBars(d.transacoes);
  el('mk-preco').innerHTML=priceBlock(d.preco_referencia);
  el('mk-referencias').innerHTML=referenceTable(d.referencias);
  el('mk-regulacao').innerHTML=ruleList(d.regulacao);
  el('mk-noticias').innerHTML=newsList(d.noticias);
  el('mk-oportunidades').innerHTML=plainList(d.oportunidades);
  el('mk-riscos').innerHTML=plainList(d.riscos);
  el('mk-fontes').innerHTML=escape(t('mk.sourcePrefix'))+' '+sourceList(d.fontes);
  el('mk-updated').textContent=t('mk.updated',{data:d.atualizado_em,autoria:L(d.autoria)});
  el('mercado-content').hidden=false;
 }catch(e){el('mercado-error').textContent=e.message}
 finally{el('mercado-loading').hidden=true}}

window.showMercado=()=>{if(loaded)return;loaded=true;load();loadProjetos()};
})();
