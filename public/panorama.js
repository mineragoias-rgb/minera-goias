/* Panorama: the charts and tables of the "Panorama da Mineração de Goiás", rebuilt from the Squad 1 base and filtered in the browser.
   The same engine runs twice: the Panorama under the atlas (every theme but companies) and, in the Empresas tab, the cards about
   holders and companies (CFEM by holder, mining and research titles, CCEE load by consumer), with the holder filter that only they read. */
(()=>{'use strict';
const C=window.PNC,E=C.E;
const FILTERS=['ano','mes','mun','min','emp','fase','rub','ramo'];
const norm=s=>String(s??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase();
// One panorama packet for both instances.
let carga=null;
const carregar=()=>carga||(carga=Promise.all([api('/panorama'),(window.loadAtlas?window.loadAtlas():api('/atlas')).catch(()=>null)]).catch(e=>{carga=null;throw e}));
// Cards about companies outside the 'emp' section: the CCEE load and R$/MWh by consumer.
const EMP_ENERGIA=['ee_emp','ee_rs_mwh'];
function engine(cfg){
const el=id=>document.getElementById(id.startsWith('pn-')?cfg.pfx+id.slice(3):id);
const SECTIONS=cfg.sections,TABS=cfg.tabs,secOf=cfg.secOf;
// Only the filters this instance offers: a card's chip for another filter would promise a cut that is not there.
const fl=d=>d.filters.filter(k=>cfg.filters.includes(k));
const FILTER_IDS={ano:['pn-y0','pn-y1'],mes:['pn-mes'],mun:['pn-mun'],min:['pn-min'],emp:['pn-emp'],fase:['pn-fase'],rub:['pn-rub'],ramo:['pn-ramo']};
const val=(id,d)=>{const x=el(id);return x?x.value:d};
let tab=TABS[0][0];if(cfg.main)try{const saved=localStorage.getItem('minera-pn-tab');if(TABS.some(([id])=>id===saved))tab=saved}catch{}
const F={y0:2010,y1:2026,mes:0,mun:-1,min:-1,emp:'',fase:-1,rub:-1,ramo:-1};
let P=null,loading=null,cards=[];
const X={F,C,E,t:(k,v)=>t(k,v),norm,cache:{},mapMetric:'cfem',
 get P(){return P},A:null,
 LAVRA:['CONCESSÃO DE LAVRA','LICENCIAMENTO','LAVRA GARIMPEIRA','REGISTRO DE EXTRAÇÃO'],PESQUISA:'AUTORIZAÇÃO DE PESQUISA',
 MINING_RAMOS:['EXTRAÇÃO DE MINERAIS METÁLICOS','MINERAIS NÃO-METÁLICOS','METALURGIA E PRODUTOS DE METAL'],
 mun:i=>i>=0?P.dims.mun[i][1]:t('pn.notInformed'),munCode:i=>i>=0?P.dims.mun[i][0]:'',
 min:i=>i>=0?P.dims.min[i][1]:t('pn.noMineral'),
 emp:i=>{const e=P.dims.emp[i];return !e?t('pn.notInformed'):e[1]||(e[3]==='ni'?t('pn.empNi'):t('pn.empHidden'))},
 empOk:i=>F.emp===''||(i>=0&&!!P.dims.emp[i][1]&&norm(P.dims.emp[i][1]).includes(F.emp)),
 years:(a,b)=>{const out=[];for(let y=Math.max(a,F.y0);y<=Math.min(b,F.y1);y++)out.push(y);return out},
 period:(a,b)=>{const y=X.years(a,b);return y.length?(y[0]===y[y.length-1]?String(y[0]):y[0]+'–'+y[y.length-1]):'—'},
 memo(key,fn){return key in X.cache?X.cache[key]:(X.cache[key]=fn())},
 sumBy(rows,key,val){const m=new Map();for(const r of rows){const k=key(r);m.set(k,(m.get(k)||0)+val(r))}return m},
 // Top n groups by total, the rest summed as "others"; label(i) names a group.
 topRows(map,n,label){const e=[...map.entries()].filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]),rest=e.slice(n).reduce((s,[,v])=>s+v,0);
  return [...e.slice(0,n).map(([k,v])=>({label:label(k),value:v})),...(rest>0?[{label:t('pn.others'),value:rest,color:C.OTHER}]:[])]},
 stackSeries(rows,group,x,val,xs,n,label){const tot=X.sumBy(rows,group,val),top=[...tot.entries()].sort((a,b)=>b[1]-a[1]).slice(0,n).map(([k])=>k),keep=new Set(top);
  const cell=new Map();for(const r of rows){const g=keep.has(group(r))?group(r):'__o',k=g+'|'+x(r);cell.set(k,(cell.get(k)||0)+val(r))}
  const out=top.map((g,j)=>({name:label(g),color:C.PALETTE[j%C.PALETTE.length],values:xs.map(v=>cell.get(g+'|'+v)||0)}));
  const other=xs.map(v=>cell.get('__o|'+v)||0);if(other.some(v=>v>0))out.push({name:t('pn.others'),color:C.OTHER,values:other});return out},
 // Filtered fact tables; skip lists the filters a card deliberately ignores (a ranking of municipalities ignores the municipality filter).
 cfem(skip=[]){return X.memo('cfem'+skip,()=>P.cfem.rows.filter(r=>r[0]>=F.y0&&r[0]<=F.y1&&(skip.includes('mes')||!F.mes||r[1]===F.mes)
  &&(skip.includes('mun')||F.mun<0||r[2]===F.mun)&&(skip.includes('min')||F.min<0||r[3]===F.min)&&(skip.includes('emp')||X.empOk(r[4]))))},
 amb(){return X.memo('amb',()=>P.amb_go.rows.filter(r=>r[0]>=F.y0&&r[0]<=F.y1&&(F.min<0||r[1]===F.min)))},
 ambBr(){return X.memo('ambBr',()=>P.amb_br.rows.filter(r=>r[0]>=F.y0&&r[0]<=F.y1&&(F.min<0||r[1]===F.min)))},
 proc(skip=[]){return X.memo('proc'+skip,()=>P.proc.rows.filter(r=>(skip.includes('fase')||F.fase<0||r[0]===F.fase)&&(skip.includes('min')||F.min<0||r[1]===F.min)
  &&(skip.includes('mun')||F.mun<0||r[2]===F.mun)&&(skip.includes('emp')||X.empOk(r[3]))))},
 inv(skip=[]){return X.memo('inv'+skip,()=>P.inv_go.rows.filter(r=>r[0]>=F.y0&&r[0]<=F.y1&&(skip.includes('min')||F.min<0||P.dims.subinv[r[1]][1]===F.min)
  &&(skip.includes('rub')||F.rub<0||r[2]===F.rub)))},
 invBr(){return X.memo('invBr',()=>P.inv_br.rows.filter(r=>r[0]>=F.y0&&r[0]<=F.y1&&(F.rub<0||r[1]===F.rub)))},
 rod(skip=[]){return X.memo('rod'+skip,()=>P.rod.rows.filter(r=>(skip.includes('mun')||F.mun<0||r[4]===F.mun)&&(F.min<0||r[9]===F.min)))},
 ceName:i=>P.dims.ce[i][1],distRamo:-1,isDist:i=>i===X.distRamo,
 ccee(skip=[]){return X.memo('ccee'+skip,()=>P.ccee.rows.filter(r=>{const y=Math.floor(r[0]/100);return y>=F.y0&&y<=F.y1&&(skip.includes('mes')||!F.mes||r[0]%100===F.mes)
  &&(skip.includes('mun')||F.mun<0||r[1]===F.mun)&&(skip.includes('ramo')||F.ramo<0||r[2]===F.ramo)&&(F.emp===''||norm(P.dims.ce[r[3]][1]).includes(F.emp))}))},
 renderCard(id){const d=cards.find(c=>c.id===id);if(d)draw(d)}
};
function draw(d){const box=el('pn-c-'+d.id).querySelector('.pn-out');C.setWidth(box.clientWidth);
 try{const out=d.render(X,box);if(typeof out==='string')box.innerHTML=out}
 catch(e){box.innerHTML=`<p class="error">${E(e.message)}</p>`;console.error(e)}}
function readFilters(){let a=+val('pn-y0',2010),b=+val('pn-y1',2026);if(a>b)[a,b]=[b,a];
 Object.assign(F,{y0:a,y1:b,mes:+val('pn-mes',0),mun:+val('pn-mun',-1),min:+val('pn-min',-1),emp:norm(val('pn-emp','').trim()),
  fase:+val('pn-fase',-1),rub:+val('pn-rub',-1),ramo:+val('pn-ramo',-1)})}
// The cut line only names the filters shown in the active tab.
function describe(){const u=X.used||new Set(FILTERS),parts=[];if(u.has('ano'))parts.push(X.period(1900,2100));
 if(u.has('mes')&&F.mes)parts.push(new Date(2020,F.mes-1,1).toLocaleString(I18N.locale(),{month:'long'}));
 if(u.has('mun')&&F.mun>=0)parts.push(X.mun(F.mun));if(u.has('min')&&F.min>=0)parts.push(X.min(F.min));if(u.has('emp')&&F.emp)parts.push('“'+el('pn-emp').value.trim()+'”');
 if(u.has('fase')&&F.fase>=0)parts.push(P.dims.fase[F.fase]);if(u.has('rub')&&F.rub>=0)parts.push(t(`pn.rub.${P.dims.rubrica[F.rub]}`));if(u.has('ramo')&&F.ramo>=0)parts.push(P.dims.ramo[F.ramo]);
 return parts.length?t('pn.cut')+' '+parts.join(' · '):''}
const visible=()=>{const secs=TABS.find(([id])=>id===tab)[1];return cards.filter(d=>secs.includes(secOf(d)))};
function scopeTitle(){const i=+val('pn-mun',-1),h=el('pn-title');if(!h)return;
 h.textContent=i>=0?t('pn.titleMun',{mun:X.mun(i)}):t('pn.title')}
// A card that cannot read the municipality filter keeps showing the state: say so on the card
// itself, otherwise a municipal cut and a state number sit side by side looking alike.
function markScope(){const on=+val('pn-mun',-1)>=0;
 el('pn-body').querySelectorAll('.pn-chips').forEach(box=>{const seal=box.querySelector('.pill.scope');
  if(seal)seal.hidden=!on;
  box.hidden=!box.querySelector('span:not([hidden])')})}
function render(){X.cache={};readFilters();visible().forEach(draw);markScope();const cut=describe();el('pn-context').textContent=cut;el('pn-context').hidden=!cut}
function showTab(id){tab=id;if(cfg.main)try{localStorage.setItem('minera-pn-tab',id)}catch{}
 const secs=TABS.find(([k])=>k===id)[1];
 if(el('pn-tabs'))el('pn-tabs').querySelectorAll('[data-tab]').forEach(b=>{const on=b.dataset.tab===id;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});
 SECTIONS.forEach(s=>{el('pn-s-'+s).hidden=!secs.includes(s)});
 // Only the filters read by some card of this tab are shown; the others keep their value for the tabs that use them.
 const used=X.used=new Set(visible().flatMap(fl));
 for(const [k,ids] of Object.entries(FILTER_IDS))ids.forEach(i=>{if(el(i))el(i).closest('div').hidden=!used.has(k)});
 document.querySelector('#'+cfg.view+' .pn-filters').hidden=!used.size;el('pn-context').hidden=!used.size;
 if(cfg.main&&window.atlasSetLayer)window.atlasSetLayer(TABS.find(([k])=>k===id)[2]);
 render()}
function options(select,items,all){if(!select)return;select.innerHTML=(all?`<option value="-1">${E(all)}</option>`:'')+items.map(([v,l])=>`<option value="${E(v)}">${E(l)}</option>`).join('')}
function fillFilters(){const years=[];for(let y=2001;y<=2026;y++)years.push([y,y]);
 options(el('pn-y0'),years);options(el('pn-y1'),years);if(el('pn-y0')){el('pn-y0').value=F.y0;el('pn-y1').value=F.y1}
 const months=[[0,t('pn.allMonths')]];for(let m=1;m<=12;m++)months.push([m,new Date(2020,m-1,1).toLocaleString(I18N.locale(),{month:'long'})]);options(el('pn-mes'),months);
 const byName=(list,label)=>list.map((x,i)=>[i,label(x)]).sort((a,b)=>String(a[1]).localeCompare(String(b[1]),'pt'));
 options(el('pn-mun'),byName(P.dims.mun,m=>m[1]),t('pn.allMun'));options(el('pn-min'),byName(P.dims.min,m=>m[1]),t('pn.allMin'));
 options(el('pn-fase'),byName(P.dims.fase,f=>f),t('pn.allFase'));options(el('pn-rub'),byName(P.dims.rubrica,r=>t(`pn.rub.${r}`)),t('pn.allRub'));
 options(el('pn-ramo'),byName(P.dims.ramo,r=>r),t('pn.allRamo'))}
function build(){cards=(window.PN_CARDS||[]).filter(d=>SECTIONS.includes(secOf(d)));const bar=el('pn-tabs');
 if(bar)bar.innerHTML=TABS.map(([id])=>`<button type="button" role="tab" class="pn-tab" data-tab="${id}" aria-controls="pn-body">${E(t(`pn.tab.${id}`))}</button>`).join('');
 el('pn-body').innerHTML=SECTIONS.map(s=>`<section class="pn-section" id="${cfg.pfx}s-${s}"><div class="pn-section-head"><h2>${E(t(`pn.s.${s}`))}</h2><p class="subtitle">${E(t(`pn.s.${s}.lead`))}</p></div><div class="pn-grid">`
  +cards.filter(d=>secOf(d)===s).map(d=>`<article class="panel pn-card${d.wide?' wide':''}" id="${cfg.pfx}c-${d.id}"><h3>${E(t(`pn.c.${d.id}`))}</h3><p class="subtitle">${E(t(`pn.c.${d.id}.n`))}</p>`
   +`<div class="pn-chips">${fl(d).length?`<span>${E(t('pn.appliedFilters'))}</span>`+fl(d).map(k=>`<span class="pill">${E(t(`pn.f.${k}`))}</span>`).join(''):''}`
   +(fl(d).includes('mun')?'':`<span class="pill scope" hidden>${E(t('pn.scopeState'))}</span>`)+'</div>'
   +'<div class="pn-out"></div></article>').join('')+'</div></section>').join('');
 if(!bar)return;
 bar.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>showTab(b.dataset.tab));
 bar.onkeydown=e=>{if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;const i=TABS.findIndex(([id])=>id===tab),
  n=TABS[(i+(e.key==='ArrowRight'?1:-1)+TABS.length)%TABS.length][0];showTab(n);el('pn-tabs').querySelector(`[data-tab="${n}"]`).focus()}}
function bind(){for(const id of ['pn-y0','pn-y1','pn-mes','pn-min','pn-fase','pn-rub','pn-ramo'])if(el(id))el(id).onchange=render;
 el('pn-mun').onchange=()=>{const i=+el('pn-mun').value;scopeTitle();
  if(cfg.main&&window.atlasSelectMun)window.atlasSelectMun(i>=0?X.munCode(i):'');
  render()};
 let timer;if(el('pn-emp'))el('pn-emp').oninput=()=>{clearTimeout(timer);timer=setTimeout(render,350)};
 // Charts follow the card width at a fixed font size, so they are redrawn when the window changes size.
 let resize,lastWidth=innerWidth;addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(()=>{
  // Panorama sits inside the atlas page, so visibility is decided by its ancestors too.
  if(innerWidth===lastWidth||document.getElementById(cfg.view).offsetParent===null)return;lastWidth=innerWidth;visible().forEach(draw)},250)});
 el('pn-reset').onclick=()=>{el('pn-y0').value=2010;el('pn-y1').value=2026;for(const id of ['pn-mes'])if(el(id))el(id).value=0;
  for(const id of ['pn-mun','pn-min','pn-fase','pn-rub','pn-ramo'])if(el(id))el(id).value=-1;if(el('pn-emp'))el('pn-emp').value='';render()}}
async function init(){const [p,a]=await carregar();P=p;X.A=a;X.distRamo=P.dims.ramo.indexOf(P.meta.ccee_distribuidora);
 fillFilters();build();bind();el('pn-content').hidden=false;showTab(tab);
 el('pn-source').textContent=t('pn.source',{v:P.meta.versao_base,d:P.meta.built_on})}
const show=async()=>{el('pn-error').textContent='';try{if(!loading)loading=init().catch(e=>{loading=null;throw e});await loading}
 catch(e){el('pn-error').textContent=e.message}finally{el('pn-loading').hidden=true}};
if(!cfg.main){window[cfg.show]=show;return}
window.showPanorama=show;
window.panoramaPickMun=code=>{
 if(!P)return;
 const wanted=String(code??'');
 if(!wanted){el('pn-mun').value='-1';scopeTitle();render();return}
 const i=P.dims.mun.findIndex(m=>m[0]===wanted);
 // findIndex gives -1 for an unknown code, and -1 is the "every municipality" value: clearing the
 // cut on a lookup miss would silently widen it instead of leaving the current scope alone.
 if(i<0)return;
 el('pn-mun').value=String(i);
 scopeTitle();
 render()};
// The radar opens a claim on the map, which means switching the page to the theme that owns it.
window.showPanoramaTab=async id=>{await window.showPanorama();if(P)showTab(id)};
}
// [id, seções do Panorama, camadas do mapa]. The tab bar is the whole page's navigation, so a theme
// picks at once what the atlas map draws and which panels appear below it; [] means the theme has no map.
// Companies left the Panorama for the Empresas tab (21/11/2026): the holder filter and the company cards live there now.
// The Notas tab (what the original Panorama had and was not rebuilt) left on 26/11/2026: it was a note for the team.
engine({main:true,pfx:'pn-',view:'panorama-view',filters:FILTERS.filter(k=>k!=='emp'),
 sections:['cfem','geo','subs','prod','usos','terr','pesq','proj','rod','energia','intens','barr'],
 secOf:d=>d.sec==='emp'||EMP_ENERGIA.includes(d.id)?null:d.sec,
 tabs:[['arrecadacao',['cfem','subs'],['cfem']],['territorio',['geo','usos','terr'],['cfem','occurrences']],
  ['producao',['prod'],['production']],['pesquisa',['pesq','proj','rod'],['projects','processes']],
  ['energia',['energia','intens'],['energy','coefficient']],['barragens',['barr'],['dams']]]});
engine({main:false,pfx:'epn-',view:'empresas-view',show:'showEmpresasPanorama',filters:FILTERS,
 sections:['emp','emp_energia'],secOf:d=>d.sec==='emp'?'emp':EMP_ENERGIA.includes(d.id)?'emp_energia':null,
 tabs:[['empresas',['emp','emp_energia'],[]]]});
window.PN_FILTER_KEYS=FILTERS;
})();
