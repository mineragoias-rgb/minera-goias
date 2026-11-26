/* Panorama cards: companies, energy (CCEE and the atlas coefficients), dams and what the repository cannot rebuild. */
(()=>{'use strict';
const cards=window.PN_CARDS=window.PN_CARDS||[];
const cnpj=s=>String(s||'').replace(/^(\d{2})(\d{3})(\d{3})$/,'$1.$2.$3');
const topNames=(X,m,n)=>[...m.entries()].sort((a,b)=>b[1]-a[1]).slice(0,n).map(([k])=>X.min(k)).join(', ');
const hours=m=>new Date(Math.floor(m/100),m%100,0).getDate()*24;
// Titles grouped by holder for a set of phases: count, area, count per phase, main minerals and municipalities.
function holders(X,phases){const P=X.P,g=new Map();
 X.proc(['fase']).filter(r=>phases.includes(P.dims.fase[r[0]])&&(X.F.fase<0||r[0]===X.F.fase)).forEach(r=>{let a=g.get(r[3]);
  if(!a)g.set(r[3],a={n:0,ha:0,m:phases.map(()=>0),mins:new Map(),muns:new Set()});
  a.n++;a.ha+=r[4];a.m[phases.indexOf(P.dims.fase[r[0]])]++;a.mins.set(r[1],(a.mins.get(r[1])||0)+1);if(r[2]>=0)a.muns.add(r[2])});
 return [...g.entries()].sort((a,b)=>b[1].n-a[1].n||b[1].ha-a[1].ha).map(([e,a],i)=>({pos:i+1,e,emp:X.emp(e),n:a.n,ha:a.ha,m:a.m,mins:topNames(X,a.mins,3),muns:a.muns.size}))}
cards.push(
{id:'emp_tiles',sec:'emp',wide:true,filters:['ano','mes','mun','min','emp','fase'],render(X){const C=X.C,P=X.P,by=X.sumBy(X.cfem(),r=>r[4],r=>r[5]),vals=[...by.values()].filter(v=>v>0).sort((a,b)=>b-a),
  tot=vals.reduce((s,v)=>s+v,0),share=n=>tot?vals.slice(0,n).reduce((s,v)=>s+v,0)/tot*100:0,pr=X.proc(),lav=pr.filter(r=>X.LAVRA.includes(P.dims.fase[r[0]])),pes=pr.filter(r=>P.dims.fase[r[0]]===X.PESQUISA);
 return '<div class="metrics pn-tiles">'+C.tiles([
  ['tone-a',X.t('pn.k.producers'),C.fmt(vals.length),X.t('pn.k.producersSub',{p:X.period(2022,2026)})],
  ['tone-b',X.t('pn.k.top5'),C.fmt(share(5),1)+' %',X.t('pn.k.top10',{v:C.fmt(share(10),1)})],
  ['tone-c',X.t('pn.k.lavra'),C.fmt(new Set(lav.map(r=>r[3])).size),X.t('pn.k.lavraSub',{n:C.fmt(lav.length)})],
  ['tone-d',X.t('pn.k.pesq'),C.fmt(new Set(pes.map(r=>r[3])).size),X.t('pn.k.pesqSub',{n:C.fmt(pes.length)})]])+'</div>'}},
{id:'emp_cfem',sec:'emp',wide:true,filters:['ano','mes','mun','min','emp'],render(X,box){const C=X.C,P=X.P,g=new Map();
 X.cfem().forEach(r=>{let a=g.get(r[4]);if(!a)g.set(r[4],a={v:0,mins:new Map(),muns:new Set()});a.v+=r[5];a.mins.set(r[3],(a.mins.get(r[3])||0)+r[5]);if(r[2]>=0)a.muns.add(r[2])});
 const nproc=X.memo('procByEmp',()=>X.sumBy(P.proc.rows,r=>r[3],()=>1)),tot=[...g.values()].reduce((s,a)=>s+a.v,0);let acc=0;
 const rows=[...g.entries()].filter(([,a])=>a.v>0).sort((a,b)=>b[1].v-a[1].v).map(([e,a],i)=>{acc+=a.v;
  return {pos:i+1,emp:X.emp(e),cnpj:cnpj(P.dims.emp[e]?.[2]),v:a.v,p:tot?a.v/tot*100:0,ac:tot?acc/tot*100:0,proc:nproc.get(e)||0,mins:topNames(X,a.mins,3),muns:a.muns.size}});
 C.table(box,[{label:'#',key:'pos',num:1},{label:X.t('pn.h.emp'),key:'emp'},{label:X.t('pn.h.cnpj'),key:'cnpj'},{label:X.t('pn.h.cfem'),key:'v',num:1,fmt:v=>C.money(v,0)},
  {label:'%',key:'p',num:1,fmt:v=>C.fmt(v,1)},{label:X.t('pn.h.acum'),key:'ac',num:1,fmt:v=>C.fmt(v,1)},{label:X.t('pn.h.proc'),key:'proc',num:1,fmt:v=>C.fmt(v)},
  {label:X.t('pn.h.mins'),key:'mins'},{label:X.t('pn.h.muns'),key:'muns',num:1,fmt:v=>C.fmt(v)}],rows,{limit:12})}},
{id:'emp_lider',sec:'emp',filters:['ano','mes','mun','min'],render(X,box){const C=X.C,g=new Map();
 X.cfem(['emp']).forEach(r=>{let m=g.get(r[3]);if(!m)g.set(r[3],m=new Map());m.set(r[4],(m.get(r[4])||0)+r[5])});
 const rows=[...g.entries()].map(([mi,m])=>{const e=[...m.entries()].sort((a,b)=>b[1]-a[1]),tot=e.reduce((s,[,v])=>s+v,0);return {min:X.min(mi),tot,emp:X.emp(e[0][0]),share:tot?e[0][1]/tot*100:0}})
  .filter(r=>r.tot>0).sort((a,b)=>b.tot-a.tot);
 C.table(box,[{label:X.t('pn.h.min'),key:'min'},{label:X.t('pn.h.cfem'),key:'tot',num:1,fmt:v=>C.money(v,0)},{label:X.t('pn.h.leader'),key:'emp'},{label:X.t('pn.h.leaderShare'),key:'share',num:1,fmt:v=>C.fmt(v,1)+' %'}],rows,{limit:12})}},
{id:'lavra_mod',sec:'emp',filters:['mun','min','emp'],render(X,box){const C=X.C,rows=holders(X,X.LAVRA);
 C.table(box,[{label:X.t('pn.h.mod'),key:'m'},{label:X.t('pn.h.titles'),key:'n',num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.area'),key:'ha',num:1,fmt:v=>C.fmt(v,0)},{label:X.t('pn.h.holders'),key:'h',num:1,fmt:v=>C.fmt(v)}],
  X.LAVRA.map((m,i)=>{const h=rows.filter(r=>r.m[i]>0);return {m,n:h.reduce((s,r)=>s+r.m[i],0),h:h.length,ha:X.proc(['fase']).filter(r=>X.P.dims.fase[r[0]]===m).reduce((s,r)=>s+r[4],0)}}).filter(r=>r.n>0))}},
{id:'lavra_parado',sec:'emp',filters:['mun','min','emp'],render(X,box){const C=X.C,P=X.P,pagou=X.memo('empPagou',()=>new Set(P.cfem.rows.filter(r=>r[5]>0).map(r=>r[4]))),g={sim:[],nao:[]};
 holders(X,X.LAVRA).forEach(r=>g[pagou.has(r.e)?'sim':'nao'].push(r));
 C.table(box,[{label:X.t('pn.h.sit'),key:'s'},{label:X.t('pn.h.holders'),key:'h',num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.titles'),key:'n',num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.area'),key:'ha',num:1,fmt:v=>C.fmt(v,0)}],
  ['sim','nao'].map(k=>({s:X.t(`pn.lavraPagou.${k}`),h:g[k].length,n:g[k].reduce((s,r)=>s+r.n,0),ha:g[k].reduce((s,r)=>s+r.ha,0)})))}},
{id:'lavra_emp',sec:'emp',wide:true,filters:['mun','min','emp'],render(X,box){const C=X.C;
 C.table(box,[{label:'#',key:'pos',num:1},{label:X.t('pn.h.holder'),key:'emp'},{label:X.t('pn.h.titles'),key:'n',num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.area'),key:'ha',num:1,fmt:v=>C.fmt(v,0)},
  ...X.LAVRA.map((_,i)=>({label:X.t(`pn.h.mod${i}`),get:r=>r.m[i],num:1,fmt:v=>C.fmt(v)})),{label:X.t('pn.h.mins'),key:'mins'},{label:X.t('pn.h.muns'),key:'muns',num:1,fmt:v=>C.fmt(v)}],holders(X,X.LAVRA),{limit:12})}},
{id:'pesq_emp',sec:'emp',wide:true,filters:['mun','min','emp'],render(X,box){const C=X.C;
 C.table(box,[{label:'#',key:'pos',num:1},{label:X.t('pn.h.holder'),key:'emp'},{label:X.t('pn.h.alvaras'),key:'n',num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.area'),key:'ha',num:1,fmt:v=>C.fmt(v,0)},
  {label:X.t('pn.h.mins'),key:'mins'},{label:X.t('pn.h.muns'),key:'muns',num:1,fmt:v=>C.fmt(v)}],holders(X,[X.PESQUISA]),{limit:12})}},

{id:'ee_tiles',sec:'energia',wide:true,filters:['ano','mes','mun','ramo','emp'],render(X){const C=X.C,P=X.P,rows=X.ccee(),free=rows.filter(r=>!X.isDist(r[2])),tot=rows.reduce((a,r)=>a+r[6],0),acl=free.reduce((a,r)=>a+r[6],0),
  min=free.filter(r=>X.MINING_RAMOS.includes(P.dims.ramo[r[2]])).reduce((a,r)=>a+r[6],0),emps=new Set(free.map(r=>r[3]));
 return '<div class="metrics pn-tiles">'+C.tiles([
  ['tone-a',X.t('pn.k.eeTotal'),C.fmt(tot/1000,1)+' GWh',X.t('pn.k.eeTotalSub',{p:X.period(2024,2026)})],
  ['tone-b',X.t('pn.k.eeAcl'),C.fmt(acl/1000,1)+' GWh',X.t('pn.k.eeAclSub',{v:C.fmt(tot?acl/tot*100:0,1),c:C.fmt((tot-acl)/1000,1)})],
  ['tone-c',X.t('pn.k.eeMin'),C.fmt(min/1000,1)+' GWh',X.t('pn.k.eeMinSub',{v:C.fmt(acl?min/acl*100:0,1)})],
  ['tone-d',X.t('pn.k.eeEmp'),C.fmt(emps.size),X.t('pn.k.eeEmpSub',{n:C.fmt([...emps].filter(i=>P.dims.ce[i][2]>=0).length)})]])+'</div>'}},
{id:'ee_ramo',sec:'energia',filters:['ano','mes','mun','emp'],render(X){const C=X.C,by=X.sumBy(X.ccee(['ramo']).filter(r=>!X.isDist(r[2])),r=>r[2],r=>r[6]/1000);
 return C.hbar(X.topRows(by,16,i=>X.P.dims.ramo[i]),{fmt:v=>C.fmt(v,1)+' GWh',aria:X.t('pn.c.ee_ramo')})}},
{id:'ee_mun',sec:'energia',filters:['ano','mes','ramo','emp'],render(X){const C=X.C,by=X.sumBy(X.ccee(['mun']).filter(r=>!X.isDist(r[2])),r=>r[1],r=>r[6]/1000);
 return C.hbar(X.topRows(by,12,i=>X.mun(i)),{fmt:v=>C.fmt(v,1)+' GWh',aria:X.t('pn.c.ee_mun')})}},
{id:'ee_mes',sec:'energia',wide:true,filters:['ano','mes','mun','ramo','emp'],render(X){const C=X.C,rows=X.ccee(),keys=[...new Set(rows.map(r=>r[0]))].sort((a,b)=>a-b),
  l=X.sumBy(rows.filter(r=>!X.isDist(r[2])),r=>r[0],r=>r[6]/1000),c=X.sumBy(rows.filter(r=>X.isDist(r[2])),r=>r[0],r=>r[6]/1000);
 return C.vbar(keys.map(k=>Math.floor(k/100)+'-'+String(k%100).padStart(2,'0')),[{name:X.t('pn.aclShort'),values:keys.map(k=>l.get(k)||0)},{name:X.t('pn.cativoShort'),values:keys.map(k=>c.get(k)||0)}],
  {stacked:true,fmt:v=>C.fmt(v,1)+' GWh',axis:v=>C.fmt(v,0),aria:X.t('pn.c.ee_mes')})}},
{id:'ee_ano',sec:'energia',filters:['ano','mun','ramo','emp'],render(X,box){const C=X.C,g=new Map();
 X.ccee(['mes']).forEach(r=>{const y=Math.floor(r[0]/100);let a=g.get(y);if(!a)g.set(y,a={t:0,l:0,c:0,m:new Set(),e:new Set()});a.t+=r[6];if(X.isDist(r[2]))a.c+=r[6];else{a.l+=r[6];a.e.add(r[3])}a.m.add(r[0])});
 C.table(box,[{label:X.t('pn.h.year'),get:e=>e[0]},{label:X.t('pn.h.mwh'),get:e=>e[1].t,num:1,fmt:v=>C.fmt(v,0)},{label:X.t('pn.h.acl'),get:e=>e[1].l,num:1,fmt:v=>C.fmt(v,0)},
  {label:X.t('pn.h.cativo'),get:e=>e[1].c,num:1,fmt:v=>C.fmt(v,0)},{label:X.t('pn.h.livrePct'),get:e=>e[1].t?e[1].l/e[1].t*100:0,num:1,fmt:v=>C.fmt(v,1)},
  {label:X.t('pn.h.months'),get:e=>e[1].m.size,num:1},{label:X.t('pn.h.emps'),get:e=>e[1].e.size,num:1,fmt:v=>C.fmt(v)}],[...g.entries()].sort((a,b)=>a[0]-b[0]))}},
{id:'ee_emp',sec:'energia',wide:true,filters:['ano','mes','mun','ramo','emp'],render(X,box){const C=X.C,P=X.P,g=new Map();
 X.ccee().filter(r=>P.dims.ce[r[3]][2]>=0).forEach(r=>{let a=g.get(r[3]);if(!a)g.set(r[3],a={mwh:0,capH:0,h:new Map(),ramos:new Map()});
  a.mwh+=r[6];a.capH+=r[7]*hours(r[0]);a.h.set(r[0],hours(r[0]));a.ramos.set(r[2],(a.ramos.get(r[2])||0)+r[6])});
 const cf=X.sumBy(X.cfem(['mun','min','emp']),r=>r[4],r=>r[5]);
 const rows=[...g.entries()].map(([ce,a])=>{const cfem=cf.get(P.dims.ce[ce][2])||0,h=[...a.h.values()].reduce((s,v)=>s+v,0);
  return {emp:X.ceName(ce),ramo:P.dims.ramo[[...a.ramos.entries()].sort((x,y)=>y[1]-x[1])[0][0]],mwh:a.mwh,mw:h?a.capH/h:0,fc:a.capH?a.mwh/a.capH*100:0,cfem,rs:a.mwh?cfem/a.mwh:0}}).sort((a,b)=>b.mwh-a.mwh);
 C.table(box,[{label:X.t('pn.h.emp'),key:'emp'},{label:X.t('pn.h.ramo'),key:'ramo'},{label:X.t('pn.h.mwh'),key:'mwh',num:1,fmt:v=>C.fmt(v,0)},{label:X.t('pn.h.mw'),key:'mw',num:1,fmt:v=>C.fmt(v,1)},
  {label:X.t('pn.h.fc'),key:'fc',num:1,fmt:v=>v?C.fmt(v,0)+' %':'—'},{label:X.t('pn.h.cfem'),key:'cfem',num:1,fmt:v=>v?C.money(v,0):'—'},{label:X.t('pn.h.rsMwh'),key:'rs',num:1,fmt:v=>v?C.money(v,2):'—'}],rows,{limit:12})}},
{id:'ee_coef',sec:'energia',wide:true,filters:['mun'],render(X,box){const C=X.C;if(!X.A)return `<p class="empty">${X.E(X.t('pn.noAtlas'))}</p>`;
 const code=X.F.mun>=0?X.munCode(X.F.mun):'',name=new Map(X.A.municipalities.map(m=>[m.code,m.name]));
 C.table(box,[{label:X.t('pn.h.mun'),get:e=>name.get(e.cod)||e.mun},{label:X.t('pn.h.class'),key:'classe'},{label:X.t('pn.h.gwh'),get:e=>e.mwh/1000,num:1,fmt:v=>C.fmt(v,2)},
  {label:X.t('pn.h.massa'),key:'ton',num:1,fmt:v=>v?C.fmt(v,0):'—'},
  {label:X.t('pn.h.coef'),get:e=>e,num:1,fmt:e=>e.classe==='ouro'&&e.mwh_kg!=null?C.fmt(e.mwh_kg,2)+' MWh/kg':e.classe==='comparavel'&&e.kwh_t?C.fmt(e.kwh_t,1)+' kWh/t':'—'},
  {label:X.t('pn.h.mainSub'),key:'sub'},{label:X.t('pn.h.rsMwh'),get:e=>e.cfem&&e.mwh?e.cfem/e.mwh:0,num:1,fmt:v=>v?C.money(v,2):'—'}],
  X.A.energy.filter(e=>e.mwh>0&&(!code||e.cod===code)).sort((a,b)=>b.mwh-a.mwh),{limit:12})}},

{id:'barr',sec:'barr',wide:true,filters:['mun'],render(X,box){const C=X.C;if(!X.A)return `<p class="empty">${X.E(X.t('pn.noAtlas'))}</p>`;const name=X.F.mun>=0?X.norm(X.mun(X.F.mun)):'';
 C.table(box,[{label:X.t('pn.h.dam'),key:'Nome'},{label:X.t('pn.h.mun'),key:'Município'},{label:X.t('pn.h.ore'),key:'Minério principal presente no reservatório'},
  {label:X.t('pn.h.risk'),key:'Categoria de Risco - CRI'},{label:X.t('pn.h.damage'),key:'Dano Potencial Associado - DPA'},{label:X.t('pn.h.operation'),key:'Situação Operacional'},
  {label:X.t('pn.h.emergency'),key:'Nível de Emergência'},{label:X.t('pn.h.coords'),get:d=>C.fmt(d.lat,4)+', '+C.fmt(d.lon,4)}],X.A.dams.filter(d=>!name||X.norm(d['Município'])===name),{limit:25})}},
{id:'barr_matriz',sec:'barr',filters:['mun'],render(X,box){const C=X.C;if(!X.A)return `<p class="empty">${X.E(X.t('pn.noAtlas'))}</p>`;const name=X.F.mun>=0?X.norm(X.mun(X.F.mun)):'',lv=['ALTA','MEDIA','BAIXA'];
 const dams=X.A.dams.filter(d=>!name||X.norm(d['Município'])===name),n=(r,d)=>dams.filter(x=>X.norm(x['Categoria de Risco - CRI'])===r&&(d==null||X.norm(x['Dano Potencial Associado - DPA'])===d)).length;
 C.table(box,[{label:X.t('pn.h.riskDamage'),key:'r'},...lv.map((d,i)=>({label:X.t(`pn.lv.${i}`),get:x=>x.c[i],num:1})),{label:X.t('pn.h.total'),key:'tot',num:1}],
  lv.map((r,i)=>({r:X.t(`pn.lv.${i}`),c:lv.map(d=>n(r,d)),tot:n(r)})))}}
);
})();
