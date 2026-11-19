/* Comércio exterior tab: what Goiás shipped out and brought in, mineral by mineral, as declared to customs.
   Data comes from /api/comex (authenticated), rebuilt by scripts/build_comex_base.py from the Comex Stat API.
   Nothing is recomputed here beyond filtering and totals: the NCM↔mineral link, the annual aggregation and the
   partial-year flag are decided in the generator, where they are auditable. */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc;
const CLASSES=['marco_estadual','produzido_em_goias','insumo_importado'];
const FLUXOS=['export','import'];
let dados=null,porMineral=null,loaded=false;

const num=(v,casas=0)=>I18N.num(v,{minimumFractionDigits:casas,maximumFractionDigits:casas});
// Chaves escritas por extenso de propósito: montá-las por concatenação esconderia do teste de tradução quais existem.
const rotuloClasse=c=>({marco_estadual:t('cx.crit.marco_estadual'),produzido_em_goias:t('cx.crit.produzido_em_goias'),
 insumo_importado:t('cx.crit.insumo_importado')}[c]||c);
const rotuloFluxo=f=>f==='export'?t('cx.fluxo.export'):t('cx.fluxo.import');

/* Dólares em escala legível. Um embarque de nióbio e um de bauxita diferem por três ordens de grandeza; mostrar os dois
   com todos os dígitos esconde a diferença em vez de mostrá-la. */
function usd(v){
 const n=Math.abs(v);
 if(n>=1e9)return t('cx.bi',{valor:num(v/1e9,2)});
 if(n>=1e6)return t('cx.mi',{valor:num(v/1e6,1)});
 if(n>=1e3)return t('cx.mil',{valor:num(v/1e3,0)});
 return t('cx.usd',{valor:num(v)});}
/* Peso na unidade que cabe: quilo para ouro, tonelada para minério, mil toneladas para concentrado. */
function peso(kg){
 if(kg>=1e8)return t('cx.kt',{valor:num(kg/1e6,0)});
 if(kg>=1e6)return t('cx.kt',{valor:num(kg/1e6,1)});
 if(kg>=1e3)return t('cx.t',{valor:num(kg/1e3,1)});
 return t('cx.kg',{valor:num(kg)});}

const anoEscolhido=()=>el('cx-ano').value;
const fluxoEscolhido=()=>el('cx-fluxo').value||'export';

const filtradas=()=>{
 const ano=anoEscolhido(),mineral=el('cx-mineral').value,crit=el('cx-crit').value,fluxo=fluxoEscolhido();
 return dados.anual.filter(l=>l.fluxo===fluxo
   &&(!ano||String(l.ano)===ano)&&(!mineral||l.mineral===mineral)
   &&(!crit||porMineral.get(l.mineral).criticidade===crit));};

function preencher(select,valores,rotuloVazio){
 select.innerHTML=(rotuloVazio?`<option value="">${escape(rotuloVazio)}</option>`:'')
  +valores.map(v=>`<option value="${escape(v[0])}">${escape(v[1])}</option>`).join('');}

const somaPor=(linhas,chave)=>{
 const mapa=new Map();
 linhas.forEach(l=>{const k=chave(l),b=mapa.get(k)||{usd:0,kg:0};b.usd+=l.usd_fob;b.kg+=l.kg;mapa.set(k,b)});
 return [...mapa.entries()].sort((a,b)=>b[1].usd-a[1].usd);};

/* Uma barra por item, na escala do maior do recorte. As barras só comparam valor em dólares — peso e preço implícito
   ficam na nota, porque um quilo de ouro e um quilo de minério não cabem na mesma régua. */
function barras(itens,classe){
 if(!itens.length)return `<p class="mk-note">${escape(t('cx.vazio'))}</p>`;
 const max=Math.max(...itens.map(i=>i.valor),1);
 return itens.map(i=>`<div class="bar-row"><span class="bar-label" title="${escape(i.rotulo)}">${escape(i.rotulo)}</span>`
  +`<div class="bar-track"><div class="bar-fill ${classe||''}" style="width:${i.valor/max*100}%"></div></div>`
  +`<span class="bar-value">${escape(i.texto)}</span></div>`
  +(i.nota?`<p class="mk-note">${escape(i.nota)}</p>`:'')).join('');}

function metricas(linhas){
 const fluxo=fluxoEscolhido(),ano=anoEscolhido();
 const total=linhas.reduce((s,l)=>s+l.usd_fob,0);
 const criticos=linhas.filter(l=>porMineral.get(l.mineral).criticidade==='marco_estadual');
 const valorCritico=criticos.reduce((s,l)=>s+l.usd_fob,0);
 // Destino só existe na exportação: a base não publica a origem das importações.
 const anos=new Set(linhas.map(l=>l.ano)),minerais=new Set(linhas.map(l=>l.mineral));
 const dest=somaPor(dados.destinos.filter(d=>anos.has(d.ano)&&minerais.has(d.mineral)),d=>d.pais);
 const totalDest=dest.reduce((s,[,b])=>s+b.usd,0);
 const parcial=linhas.filter(l=>!l.ano_completo).length;
 const quantosCriticos=new Set(criticos.map(l=>l.mineral)).size;
 return [
  ['a',fluxo==='export'?t('cx.m.exportado'):t('cx.m.importado'),usd(total),
     ano?t('cx.m.doAno',{ano}):t('cx.m.doPeriodo',{inicio:String(dados.meta.periodo[0]),fim:String(dados.meta.periodo[1])})],
  ['b',t('cx.m.criticos'),num(quantosCriticos),
     total?t('cx.m.criticosSub',{parcela:num(valorCritico/total*100,0)}):t('cx.m.criticosVazio')],
  ['c',t('cx.m.destino'),dest.length&&fluxo==='export'?dest[0][0]:'—',
     dest.length&&fluxo==='export'?t('cx.m.destinoSub',{parcela:num(dest[0][1].usd/totalDest*100,0)}):t('cx.m.destinoVazio')],
  ['d',t('cx.m.parcial'),num(parcial),t('cx.m.parcialSub',{ano:String(dados.meta.publicado_ate.ano),
     mes:String(dados.meta.publicado_ate.mes)})],
 ].map(([tom,rotulo,valor,detalhe])=>`<div class="metric tone-${tom}"><span>${escape(rotulo)}</span>`
   +`<strong>${escape(valor)}</strong><small>${escape(detalhe)}</small></div>`).join('');}

function porMineralGrafico(linhas){
 return barras(somaPor(linhas,l=>l.mineral).map(([mineral,b])=>{
  const m=porMineral.get(mineral);
  return {rotulo:mineral,valor:b.usd,texto:usd(b.usd),
   nota:t('cx.notaMineral',{peso:peso(b.kg),classe:rotuloClasse(m.criticidade),
     preco:b.kg?t('cx.precoImplicito',{valor:num(b.usd/b.kg,b.usd/b.kg<100?2:0)}):t('cx.semPeso')})};}),
  'cx-mineral');}

function destinosGrafico(linhas){
 if(fluxoEscolhido()!=='export')return `<p class="mk-note">${escape(t('cx.destinoSoExport'))}</p>`;
 const anos=new Set(linhas.map(l=>l.ano)),minerais=new Set(linhas.map(l=>l.mineral));
 const rel=dados.destinos.filter(d=>anos.has(d.ano)&&minerais.has(d.mineral));
 const total=rel.reduce((s,d)=>s+d.usd_fob,0);
 return barras(somaPor(rel,d=>d.pais).slice(0,12).map(([pais,b])=>({
   rotulo:pais,valor:b.usd,texto:usd(b.usd),
   nota:t('cx.notaDestino',{parcela:num(total?b.usd/total*100:0,1),peso:peso(b.kg)})})),'cx-destino');}

/* Com um ano escolhido o eixo vira mês; sem ano, vira ano. É o mesmo gráfico lendo a mesma série em duas lentes. */
function serieGrafico(linhas){
 const ano=anoEscolhido(),fluxo=fluxoEscolhido(),minerais=new Set(linhas.map(l=>l.mineral));
 const rel=dados.serie.filter(s=>s.fluxo===fluxo&&minerais.has(s.mineral)&&(!ano||String(s.ano)===ano));
 if(!rel.length)return `<p class="mk-note">${escape(t('cx.vazio'))}</p>`;
 if(ano)return barras(somaPor(rel,s=>s.mes).sort((a,b)=>a[0]-b[0]).map(([mes,b])=>({
   rotulo:t('cx.mes',{mes:String(mes).padStart(2,'0'),ano}),valor:b.usd,texto:usd(b.usd)})),'cx-serie');
 const porAno=somaPor(rel,s=>s.ano).sort((a,b)=>a[0]-b[0]);
 const completo=new Map(dados.anual.filter(l=>l.fluxo===fluxo).map(l=>[l.ano,l.ano_completo]));
 return barras(porAno.map(([a,b])=>({rotulo:String(a),valor:b.usd,texto:usd(b.usd),
   nota:completo.get(a)===false?t('cx.anoParcial',{meses:String(dados.meta.publicado_ate.mes)}):''})),'cx-serie');}

/* Município só existe por capítulo da NCM — a API recusa detalhar município por produto. O rótulo diz o capítulo
   justamente para que ninguém leia "Barro Alto · capítulo 72" como se fosse níquel medido no município. */
function municipiosGrafico(){
 const ano=anoEscolhido();
 const rel=dados.municipios.filter(m=>!ano||String(m.ano)===ano);
 return barras(somaPor(rel,m=>m.municipio+' · '+m.capitulo).slice(0,14).map(([chave,b])=>{
   const [municipio,capitulo]=chave.split(' · ');
   const nome=(dados.municipios.find(m=>m.capitulo===capitulo)||{}).capitulo_nome||capitulo;
   return {rotulo:`${municipio} · ${t('cx.capitulo',{capitulo})}`,valor:b.usd,texto:usd(b.usd),
     nota:t('cx.notaMunicipio',{nome,peso:peso(b.kg)})};}),'cx-municipio');}

function tabela(linhas){
 const cabecalho=['cx.thMineral','cx.thClasse','cx.thAno','cx.thValor','cx.thPeso','cx.thPreco','cx.thCobertura']
   .map(k=>`<th>${escape(t(k))}</th>`).join('');
 const corpo=linhas.slice().sort((a,b)=>b.ano-a.ano||b.usd_fob-a.usd_fob).map(l=>{
  const m=porMineral.get(l.mineral);
  const ncms=m.ncms.map(n=>n.codigo).join(', ');
  return `<tr><td><b>${escape(l.mineral)}</b><div class="mk-note">${escape(ncms)}</div>`
   +(m.operacoes_em_goias.length?`<div class="mk-note">${escape(m.operacoes_em_goias.join(' · '))}</div>`:'')
   +`</td><td><span class="pill">${escape(rotuloClasse(m.criticidade))}</span></td>`
   +`<td>${escape(String(l.ano))}</td><td><b>${escape(usd(l.usd_fob))}</b></td>`
   +`<td>${escape(peso(l.kg))}</td>`
   +`<td>${l.usd_por_kg!==null?`<b>${escape(num(l.usd_por_kg,l.usd_por_kg<100?2:0))}</b> <span class="muted">${escape(t('cx.usdKg'))}</span>`
       :`<span class="muted">—</span>`}</td>`
   +`<td>${l.ano_completo?escape(t('cx.cobCompleto')):`<span class="pill">${escape(t('cx.cobParcial',{meses:String(l.meses_publicados)}))}</span>`}`
   +`<div class="mk-note">${escape(t('cx.cobMeses',{meses:String(l.meses_com_embarque)}))}</div></td></tr>`}).join('');
 return `<table><thead><tr>${cabecalho}</tr></thead><tbody>${corpo}</tbody></table>`;}

/* O que a base não mede fica na própria tela, não só no README: é a parte que impede de ler despacho como produção. */
function limites(){
 const meta=dados.meta;
 return `<h3 class="mk-sub">${escape(t('cx.naoMedeT'))}</h3>`
  +'<ul class="mk-bullets">'+meta.o_que_a_base_nao_mede.map(x=>`<li>${escape(x)}</li>`).join('')+'</ul>'
  +`<h3 class="mk-sub">${escape(t('cx.avisosT'))}</h3>`
  +'<ul class="mk-bullets">'+meta.avisos.map(x=>`<li>${escape(x)}</li>`).join('')+'</ul>'
  +`<h3 class="mk-sub">${escape(t('cx.recorteT'))}</h3>`
  +`<p class="mk-note">${escape(meta.criticidade.recorte_do_projeto)}</p>`
  +`<p class="mk-note"><b>${escape(t('cx.federal'))}</b> ${escape(meta.criticidade.por_que_na)}</p>`
  +`<h3 class="mk-sub">${escape(t('cx.foraT'))}</h3>`
  +'<ul class="mk-bullets">'+meta.regras.o_que_fica_de_fora.map(x=>`<li>${escape(x)}</li>`).join('')+'</ul>';}

function exportar(linhas){
 const cabecalho=['mineral','criticidade','fluxo','ano','usd_fob','kg','usd_por_kg','meses_com_embarque',
  'ano_completo','ncms','operacoes_em_goias'];
 const csv=[cabecalho.join(';'),...linhas.map(l=>{
  const m=porMineral.get(l.mineral);
  return [l.mineral,m.criticidade,l.fluxo,l.ano,l.usd_fob,l.kg,l.usd_por_kg??'',l.meses_com_embarque,
   l.ano_completo,m.ncms.map(n=>n.codigo).join(' | '),m.operacoes_em_goias.join(' | ')
  ].map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(';')})].join('\r\n');
 const url=URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download='minera-goias-comex.csv';a.click();
 URL.revokeObjectURL(url);}

function desenhar(){
 const linhas=filtradas();
 el('cx-metrics').innerHTML=metricas(linhas);
 el('cx-minerais').innerHTML=porMineralGrafico(linhas);
 el('cx-destinos').innerHTML=destinosGrafico(linhas);
 el('cx-serie').innerHTML=serieGrafico(linhas);
 el('cx-municipios').innerHTML=municipiosGrafico();
 el('cx-tabela').innerHTML=tabela(linhas);
 el('cx-limites').innerHTML=limites();
 el('cx-count').textContent=t('cx.contagem',{linhas:num(linhas.length),total:num(dados.anual.length)});
 el('cx-context').textContent=t('cx.contexto',{fluxo:rotuloFluxo(fluxoEscolhido()),
   inicio:String(dados.meta.periodo[0]),fim:String(dados.meta.periodo[1]),
   ano:String(dados.meta.publicado_ate.ano),mes:String(dados.meta.publicado_ate.mes)});
 el('cx-export').onclick=()=>exportar(linhas);}

async function load(){
 el('comex-error').textContent='';
 try{
  dados=await api('/comex');
  porMineral=new Map(dados.minerais.map(m=>[m.mineral,m]));
  const anos=[...new Set(dados.anual.map(l=>l.ano))].sort((a,b)=>b-a);
  const minerais=[...new Set(dados.anual.map(l=>l.mineral))].sort();
  preencher(el('cx-fluxo'),FLUXOS.map(f=>[f,rotuloFluxo(f)]),null);
  preencher(el('cx-ano'),anos.map(a=>[String(a),String(a)]),t('cx.todosAnos'));
  preencher(el('cx-mineral'),minerais.map(m=>[m,m]),t('cx.todosMinerais'));
  preencher(el('cx-crit'),CLASSES.map(c=>[c,rotuloClasse(c)]),t('cx.todasClasses'));
  ['cx-fluxo','cx-ano','cx-mineral','cx-crit'].forEach(id=>el(id).onchange=desenhar);
  el('cx-reset').onclick=()=>{el('cx-fluxo').value='export';
    ['cx-ano','cx-mineral','cx-crit'].forEach(id=>el(id).value='');desenhar()};
  el('cx-nota').textContent=dados.meta.fonte.natureza;
  el('cx-fontes').textContent=t('cx.fontes',{fonte:dados.meta.fonte.nome,portal:dados.meta.fonte.portal,
    baixado:dados.meta.coleta.baixado_em,atualizado:dados.meta.coleta.atualizacao_declarada_pela_api,
    base:dados.meta.versao_base});
  desenhar();
  el('comex-content').hidden=false;
 }catch(e){el('comex-error').textContent=e.message}
 finally{el('comex-loading').hidden=true}}

window.showComex=()=>{if(loaded)return;loaded=true;load()};
})();
