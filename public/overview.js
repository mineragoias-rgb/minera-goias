/* Overview tab, rebuilt in the same model as the Panorama: cards drawn from the versioned packages, with filters that change
   every number as soon as they change. What it measures is energy in MWh for the mineral chain — the cut is the load whose CNPJ
   root holds a mining title in the Squad 1 base, the same criterion of the Panorama and of the price tab — and not a count of
   rows. Counts that remain counts are named as such. Price and cost come from /precos and carry the assumption warning. */
(()=>{'use strict';
const el=id=>document.getElementById(id),C=window.PNC,E=C.E;
const FILTER_IDS=['ov-y0','ov-y1','ov-mes','ov-mun','ov-ramo'];
const F={y0:2024,y1:2026,mes:0,mun:-1,ramo:-1};
let P=null,R=null,A=null,loading=null;
const norm=s=>String(s??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase();
const cenRef=meta=>meta.cenarios.indexOf('referencia');   // o índice do cenário de referência vem do pacote
const gwh=v=>C.fmt(v/1000,1)+' GWh';
const mi=v=>C.money(v/1e6,1)+' '+t('pn.u.mi');
// Aviso de premissa acima do conteúdo, igual ao da aba de preços.
const aviso=(box,html)=>{box.innerHTML=`<p class="pn-warn">${E(t('pn.pr.premissa'))}</p><div></div>`;
 const alvo=box.lastElementChild;if(typeof html==='string')alvo.innerHTML=html;return alvo};

const mineral=r=>P.dims.ce[r[3]][2]>=0;                 // carga de titular de processo minerário
const ano=r=>Math.floor(r[0]/100);
// Parcelas de carga no recorte; skip lista os filtros que um quadro ignora de propósito (um ranking de ramos ignora o ramo).
const cargas=(skip=[])=>P.ccee.rows.filter(r=>ano(r)>=F.y0&&ano(r)<=F.y1&&(skip.includes('mes')||!F.mes||r[0]%100===F.mes)
 &&(skip.includes('mun')||F.mun<0||r[1]===F.mun)&&(skip.includes('ramo')||F.ramo<0||r[2]===F.ramo));
const cfem=()=>P.cfem.rows.filter(r=>r[0]>=F.y0&&r[0]<=F.y1&&(!F.mes||r[1]===F.mes)&&(F.mun<0||r[2]===F.mun));
const soma=(rows,f)=>rows.reduce((s,r)=>s+f(r),0);
const horas=m=>new Date(Math.floor(m/100),m%100,0).getDate()*24;
const mesRotulo=m=>Math.floor(m/100)+'-'+String(m%100).padStart(2,'0');

const CARDS=[
{id:'tiles',render(box){const rows=cargas(),min=rows.filter(mineral);
 const total=soma(rows,r=>r[6]),energia=soma(min,r=>r[6]),meses=new Set(rows.map(r=>r[0])).size;
 const emp=new Set(min.map(r=>r[3])),todas=new Set(rows.map(r=>r[3])),muns=new Set(min.map(r=>r[1]).filter(i=>i>=0));
 const cf=cfem(),valor=soma(cf,r=>r[5]),n=soma(cf,r=>r[6]);
 const arquivos=A&&A.summary?A.summary.files:null,linhas=A&&A.summary?A.summary.records:null;
 box.innerHTML='<div class="metrics pn-tiles">'+C.tiles([
  ['tone-a',t('ov.k.energia'),gwh(energia),t('ov.k.energiaSub',{v:C.fmt(total?energia/total*100:0,1),m:C.fmt(meses)})],
  ['tone-b',t('ov.k.emp'),C.fmt(emp.size),t('ov.k.empSub',{n:C.fmt(todas.size),m:C.fmt(muns.size)})],
  ['tone-c',t('ov.k.cfem'),mi(valor),t('ov.k.cfemSub',{n:C.fmt(n)})],
  ['tone-d',t('ov.k.acervo'),arquivos==null?'—':C.fmt(arquivos),
   linhas==null?t('ov.k.acervoOff'):t('ov.k.acervoSub',{n:C.fmt(linhas),d:A.summary.updated_at?String(A.summary.updated_at).slice(0,10):'—'})]])+'</div>'}},

{id:'mes',render(box){const rows=cargas(),keys=[...new Set(rows.map(r=>r[0]))].sort((a,b)=>a-b);
 const min=X0(rows.filter(mineral),keys),out=X0(rows.filter(r=>!mineral(r)),keys);
 box.innerHTML=C.vbar(keys.map(mesRotulo),[{name:t('ov.serieMineral'),values:min},{name:t('ov.serieOutras'),values:out}],
  {stacked:true,fmt:v=>C.fmt(v,1)+' GWh',axis:v=>C.fmt(v,0),aria:t('ov.c.mes')})}},

{id:'ramo',render(box){const by=new Map();
 cargas(['ramo']).filter(mineral).forEach(r=>by.set(r[2],(by.get(r[2])||0)+r[6]/1000));
 box.innerHTML=C.hbar(topRows(by,12,i=>P.dims.ramo[i]),{fmt:v=>C.fmt(v,1)+' GWh',aria:t('ov.c.ramo')})}},

{id:'mun',render(box){const by=new Map();
 cargas(['mun']).filter(mineral).forEach(r=>by.set(r[1],(by.get(r[1])||0)+r[6]/1000));
 box.innerHTML=C.hbar(topRows(by,12,i=>i>=0?P.dims.mun[i][1]:t('pn.notInformed')),{fmt:v=>C.fmt(v,1)+' GWh',aria:t('ov.c.mun')})}},

{id:'emp',render(box){const g=new Map();
 cargas().filter(mineral).forEach(r=>{let a=g.get(r[3]);if(!a)g.set(r[3],a={mwh:0,acl:0,capH:0,h:new Map(),ramos:new Map(),muns:new Map()});
  a.mwh+=r[6];a.acl+=r[4];a.capH+=r[7]*horas(r[0]);a.h.set(r[0],horas(r[0]));
  a.ramos.set(r[2],(a.ramos.get(r[2])||0)+r[6]);if(r[1]>=0)a.muns.set(r[1],(a.muns.get(r[1])||0)+r[6])});
 const maior=m=>[...m.entries()].sort((a,b)=>b[1]-a[1])[0];
 const rows=[...g.entries()].map(([ce,a])=>{const h=[...a.h.values()].reduce((s,v)=>s+v,0),mun=maior(a.muns);
  return {emp:P.dims.ce[ce][1],mun:mun?P.dims.mun[mun[0]][1]:t('pn.notInformed'),ramo:P.dims.ramo[maior(a.ramos)[0]],
   mwh:a.mwh,mw:h?a.capH/h:0,fc:a.capH?a.mwh/a.capH*100:0,acl:a.mwh?a.acl/a.mwh*100:0}}).sort((a,b)=>b.mwh-a.mwh);
 C.table(box,[{label:t('pn.h.emp'),key:'emp'},{label:t('pn.h.mun'),key:'mun'},{label:t('pn.h.ramo'),key:'ramo'},
  {label:t('pn.h.mwh'),key:'mwh',num:1,fmt:v=>C.fmt(v,0)},{label:t('pn.h.mw'),key:'mw',num:1,fmt:v=>v?C.fmt(v,1):'—'},
  {label:t('pn.h.fc'),key:'fc',num:1,fmt:v=>v?C.fmt(v,0)+' %':'—'},
  {label:t('pn.h.livrePct'),key:'acl',num:1,fmt:v=>C.fmt(v,0)}],rows,{limit:10})}},

{id:'custo',render(box){if(!R)return box.innerHTML=`<p class="empty">${E(t('pn.pr.noData'))}</p>`;
 const ref=cenRef(R.meta),a0=R.meta.horizonte[0],a1=R.meta.horizonte[1];
 const preco=R.precos.rows.find(r=>r[0]===a0&&r[1]===ref),fim=R.precos.rows.find(r=>r[0]===a1&&r[1]===ref);
 const custoFim=R.custo.rows.find(r=>r[0]===a1&&r[1]===ref&&r[2]===ref);
 const rows=cargas().filter(mineral),mwh=soma(rows,r=>r[6]),meses=new Set(rows.map(r=>r[0])).size;
 aviso(box,'<div class="metrics pn-tiles">'+C.tiles([
  ['tone-a',t('ov.k.custoRecorte'),mi(mwh*preco[5]),t('ov.k.custoRecorteSub',{p:C.money(preco[5],0),c:t(`pn.pr.cen.${R.meta.cenarios[ref]}`),m:C.fmt(meses)})],
  ['tone-b',t('ov.k.custoBase'),mi(R.meta.baseline.mwh_ano*preco[5]),t('ov.k.custoBaseSub',{g:C.fmt(R.meta.baseline.mwh_ano/1000,0),y:R.meta.baseline.ano})],
  ['tone-c',t('ov.k.custoFim',{y:a1}),mi(custoFim[4]),t('ov.k.custoFimSub',{y:a1,p:C.money(fim[5],0)})]])+'</div>')}},

{id:'cobertura',render(box){const g=new Map();
 cargas(['mes']).forEach(r=>{const y=ano(r);let a=g.get(y);if(!a)g.set(y,a={meses:new Set(),n:0,mwh:0,min:0,emp:new Set(),mun:new Set()});
  a.meses.add(r[0]);a.n++;a.mwh+=r[6];if(mineral(r)){a.min+=r[6];a.emp.add(r[3]);if(r[1]>=0)a.mun.add(r[1])}});
 C.table(box,[{label:t('pn.h.year'),get:e=>e[0]},{label:t('pn.h.months'),get:e=>e[1].meses.size,num:1},
  {label:t('ov.h.combos'),get:e=>e[1].n,num:1,fmt:v=>C.fmt(v)},
  {label:t('ov.h.gwhMineral'),get:e=>e[1].min/1000,num:1,fmt:v=>C.fmt(v,1)},
  {label:t('ov.h.gwhBase'),get:e=>e[1].mwh/1000,num:1,fmt:v=>C.fmt(v,1)},
  {label:t('pn.h.emps'),get:e=>e[1].emp.size,num:1},{label:t('pn.h.muns'),get:e=>e[1].mun.size,num:1}],
  [...g.entries()].sort((a,b)=>a[0]-b[0]))}}
];

// GWh por mês de um conjunto de linhas, na ordem de keys.
function X0(rows,keys){const m=new Map();for(const r of rows)m.set(r[0],(m.get(r[0])||0)+r[6]/1000);return keys.map(k=>m.get(k)||0)}
function topRows(map,n,label){const e=[...map.entries()].filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]),rest=e.slice(n).reduce((s,[,v])=>s+v,0);
 return [...e.slice(0,n).map(([k,v])=>({label:label(k),value:v})),...(rest>0?[{label:t('pn.others'),value:rest,color:C.OTHER}]:[])]}

function readFilters(){let a=+el('ov-y0').value,b=+el('ov-y1').value;if(a>b)[a,b]=[b,a];
 Object.assign(F,{y0:a,y1:b,mes:+el('ov-mes').value,mun:+el('ov-mun').value,ramo:+el('ov-ramo').value})}
function describe(){const parts=[F.y0===F.y1?String(F.y0):F.y0+'–'+F.y1];
 if(F.mes)parts.push(new Date(2020,F.mes-1,1).toLocaleString(I18N.locale(),{month:'long'}));
 if(F.mun>=0)parts.push(P.dims.mun[F.mun][1]);if(F.ramo>=0)parts.push(P.dims.ramo[F.ramo]);
 return t('pn.cut')+' '+parts.join(' · ')}
function render(){readFilters();
 for(const d of CARDS){const box=el('ov-c-'+d.id).querySelector('.pn-out');C.setWidth(box.clientWidth);
  try{d.render(box)}catch(e){box.innerHTML=`<p class="error">${E(e.message)}</p>`;console.error(e)}}
 el('ov-context').textContent=describe()}

function options(select,items,all){select.innerHTML=(all?`<option value="-1">${E(all)}</option>`:'')+items.map(([v,l])=>`<option value="${E(v)}">${E(l)}</option>`).join('')}
function fillFilters(){const anos=[...new Set(P.ccee.rows.map(ano))].sort((a,b)=>a-b);
 F.y0=anos[0];F.y1=anos[anos.length-1];
 options(el('ov-y0'),anos.map(y=>[y,y]));options(el('ov-y1'),anos.map(y=>[y,y]));
 el('ov-y0').value=F.y0;el('ov-y1').value=F.y1;
 const meses=[[0,t('pn.allMonths')]];for(let m=1;m<=12;m++)meses.push([m,new Date(2020,m-1,1).toLocaleString(I18N.locale(),{month:'long'})]);
 options(el('ov-mes'),meses);
 // Só os municípios e ramos que aparecem nas parcelas de carga, para não oferecer filtro que deixa tudo vazio.
 const comCarga=new Set(P.ccee.rows.map(r=>r[1])),ramos=new Set(P.ccee.rows.map(r=>r[2]));
 options(el('ov-mun'),[...comCarga].filter(i=>i>=0).map(i=>[i,P.dims.mun[i][1]]).sort((a,b)=>a[1].localeCompare(b[1],'pt')),t('pn.allMun'));
 options(el('ov-ramo'),[...ramos].map(i=>[i,P.dims.ramo[i]]).sort((a,b)=>String(a[1]).localeCompare(String(b[1]),'pt')),t('pn.allRamo'))}

function bind(){FILTER_IDS.forEach(id=>el(id).onchange=render);
 el('ov-reset').onclick=()=>{fillFilters();render()};
 el('ov-export').onclick=()=>exportar();
 let resize,largura=innerWidth;addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(()=>{
  if(innerWidth===largura||el('overview-view').hidden)return;largura=innerWidth;render()},250)})}

// Exporta a série mensal do recorte: o que a aba mostra, não o que a fonte tem.
function exportar(){const rows=cargas(),keys=[...new Set(rows.map(r=>r[0]))].sort((a,b)=>a-b);
 const min=X0(rows.filter(mineral),keys),tot=X0(rows,keys);
 const safe=v=>'"'+String(v).replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';
 const linhas=[[t('ov.csvMonth'),t('ov.csvGwhMineral'),t('ov.csvGwhBase'),t('ov.csvCut')],
  ...keys.map((k,i)=>[mesRotulo(k),min[i].toFixed(3),tot[i].toFixed(3),describe()])];
 const url=URL.createObjectURL(new Blob(['﻿'+linhas.map(r=>r.map(safe).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download=t('ov.csvName',{year:F.y1});a.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000)}

async function init(){const [p,r,d]=await Promise.all([PKG.get('/panorama'),PKG.tryGet('/precos'),PKG.tryGet('/dashboard')]);
 P=p;R=r;A=d;
 fillFilters();bind();el('ov-content').hidden=false;render();
 el('ov-source').textContent=t('ov.source',{v:P.meta.versao_base,d:P.meta.built_on})}
window.showOverview=async()=>{el('ov-error').textContent='';
 try{if(!loading)loading=init().catch(e=>{loading=null;throw e});await loading}
 catch(e){el('ov-error').textContent=e.message}finally{el('ov-loading').hidden=true}};
})();
