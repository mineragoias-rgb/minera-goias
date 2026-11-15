/* Panorama: extra analyses for the energy-demand work, added to the tabs they belong to — CFEM seasonality, drivers and concentration,
   municipal dependency on mining, operational stage of the claims, implicit prices, ore moved per tonne sold, Goiás share by mineral,
   research spending against royalties, the ANM project pipeline and deposits, holder concentration and idle titles, the mineral chain
   in the CCEE load units and the energy coefficients of the atlas snapshot. */
(()=>{'use strict';
const cards=window.PN_CARDS=window.PN_CARDS||[];
const sum=(rows,i)=>rows.reduce((s,r)=>s+(r[i]||0),0);
const lastYear=rows=>rows.reduce((m,r)=>Math.max(m,r[0]),0);
const monthName=m=>new Date(2020,m-1,1).toLocaleString(I18N.locale(),{month:'short'}).replace('.','');
const monthLabel=k=>Math.floor(k/100)+'-'+String(k%100).padStart(2,'0');
const hours=m=>new Date(Math.floor(m/100),m%100,0).getDate()*24;
const tableIn=(X,box,caption)=>{box.innerHTML=`<p class="small muted">${X.E(caption)}</p><div></div>`;return box.lastElementChild};
const notice=(X,key)=>`<p class="notice">${X.E(X.t(key))}</p>`;
const noAtlas=X=>`<p class="empty">${X.E(X.t('pn.noAtlas'))}</p>`;
const atlasRows=(X,key)=>{const p=X.A&&X.A[key];return p?p.rows.map(r=>Object.fromEntries(p.cols.map((c,i)=>[c,r[i]]))):[]};
// Years with all twelve months in the CFEM base (2026 is partial), so annual figures are comparable.
const fullYears=X=>X.memo('cfemFull',()=>{const m=new Map();X.P.cfem.rows.forEach(r=>{if(!m.has(r[0]))m.set(r[0],new Set());m.get(r[0]).add(r[1])});
 return new Set([...m].filter(([,s])=>s.size===12).map(([y])=>y))});
// Average annual CFEM per municipality over the full years of the cut, and the years used.
function annualCfemByMun(X){const full=fullYears(X),rows=X.cfem(['mun','mes']).filter(r=>full.has(r[0])),ys=[...new Set(rows.map(r=>r[0]))].sort((a,b)=>a-b);
 return {ys,by:ys.length?X.sumBy(rows,r=>r[2],r=>r[5]/ys.length):new Map()}}
cards.push(
{id:'cfem_sazonal',sec:'cfem',filters:['ano','mun','min','emp'],render(X){const C=X.C,full=fullYears(X),rows=X.cfem(['mes']).filter(r=>full.has(r[0])),n=new Set(rows.map(r=>r[0])).size;
 if(!n)return notice(X,'pn.needFullYear');
 const by=X.sumBy(rows,r=>r[1],r=>r[5]),months=[1,2,3,4,5,6,7,8,9,10,11,12];
 return C.vbar(months.map(monthName),[{name:'CFEM',values:months.map(m=>(by.get(m)||0)/n)}],{fmt:v=>C.money(v,0),aria:X.t('pn.c.cfem_sazonal')})}},
{id:'cfem_conc',sec:'cfem',filters:['ano','mes'],render(X){const C=X.C,years=X.years(2022,2026),rows=X.cfem(['mun','min','emp']);
 const share=(key,y)=>{const v=[...X.sumBy(rows.filter(r=>r[0]===y),key,r=>r[5]).values()].sort((a,b)=>b-a),t=v.reduce((s,x)=>s+x,0);
  return t?v.slice(0,5).reduce((s,x)=>s+x,0)/t*100:null};
 return C.line(years.map(String),[{name:X.t('pn.top5mun'),values:years.map(y=>share(r=>r[2],y))},{name:X.t('pn.top5min'),values:years.map(y=>share(r=>r[3],y))},
  {name:X.t('pn.top5emp'),values:years.map(y=>share(r=>r[4],y))}],{fmt:v=>C.fmt(v,1)+' %',axis:v=>C.fmt(v,0)+'%',aria:X.t('pn.c.cfem_conc')})}},
{id:'cfem_var',sec:'subs',wide:true,filters:['ano','mes','mun','emp'],render(X,box){const C=X.C,full=[...fullYears(X)].filter(y=>y>=X.F.y0&&y<=X.F.y1).sort((a,b)=>a-b);
 if(full.length<2)return notice(X,'pn.needTwoYears');
 const [a,b]=full.slice(-2),rows=X.cfem(['min']),va=X.sumBy(rows.filter(r=>r[0]===a),r=>r[3],r=>r[5]),vb=X.sumBy(rows.filter(r=>r[0]===b),r=>r[3],r=>r[5]);
 const delta=[...new Set([...va.keys(),...vb.keys()])].map(k=>({label:X.min(k),value:(vb.get(k)||0)-(va.get(k)||0)})).filter(d=>Math.abs(d.value)>=1).sort((p,q)=>q.value-p.value);
 const ta=[...va.values()].reduce((s,v)=>s+v,0),tb=[...vb.values()].reduce((s,v)=>s+v,0),rowsShown=delta.length>16?[...delta.slice(0,8),...delta.slice(-8)]:delta;
 const out=tableIn(X,box,X.t('pn.varCaption',{a,b,d:(tb>=ta?'+':'')+C.money(tb-ta,0),p:ta?C.fmt((tb-ta)/ta*100,1):'—'}));
 out.innerHTML=C.hdiv(rowsShown,{fmt:v=>(v>0?'+':'')+C.money(v,0),aria:X.t('pn.c.cfem_var')})}},

{id:'mun_dep',sec:'geo',filters:['ano','min','emp'],render(X,box){const C=X.C,{ys,by}=annualCfemByMun(X);
 if(!ys.length)return notice(X,'pn.needFullYear');
 const list=[...by.entries()].filter(([m,v])=>m>=0&&v>0&&X.P.dims.mun[m][3]>0).map(([m,v])=>({label:X.mun(m),value:v/X.P.dims.mun[m][3]*100})).sort((a,b)=>b.value-a.value).slice(0,15);
 tableIn(X,box,X.t('pn.depCaption',{a:ys[0],b:ys[ys.length-1],pib:X.P.meta.periods.pib})).innerHTML=C.hbar(list,{fmt:v=>C.fmt(v,2)+' %',aria:X.t('pn.c.mun_dep')})}},
{id:'mun_percap',sec:'geo',wide:true,filters:['ano','min','emp'],render(X,box){const C=X.C,{ys,by}=annualCfemByMun(X);
 if(!ys.length)return notice(X,'pn.needFullYear');
 const rows=[...by.entries()].filter(([m,v])=>m>=0&&v>0).map(([m,v])=>{const d=X.P.dims.mun[m];return {mun:d[1],pop:d[2],v,pc:d[2]?v/d[2]:null,dep:d[3]?v/d[3]*100:null}}).sort((a,b)=>(b.pc||0)-(a.pc||0));
 C.table(tableIn(X,box,X.t('pn.depCaption',{a:ys[0],b:ys[ys.length-1],pib:X.P.meta.periods.pib})),[{label:X.t('pn.h.mun'),key:'mun'},{label:X.t('pn.h.pop'),key:'pop',num:1,fmt:v=>C.fmt(v)},
  {label:X.t('pn.h.cfemAno'),key:'v',num:1,fmt:v=>C.money(v,0)},{label:X.t('pn.h.percap'),key:'pc',num:1,fmt:v=>v==null?'—':C.money(v,2)},{label:X.t('pn.h.dep'),key:'dep',num:1,fmt:v=>v==null?'—':C.fmt(v,2)+' %'}],rows,{limit:12})}},
{id:'status_funil',sec:'terr',wide:true,filters:['mun','min','emp'],render(X){const C=X.C,rows=X.proc(['fase']),n=X.sumBy(rows,r=>r[6],()=>1),a=X.sumBy(rows,r=>r[6],r=>r[4]);
 return C.hbar([...n.entries()].sort((p,q)=>q[1]-p[1]).map(([s,v])=>({label:X.P.dims.status[s]+' · '+C.short(a.get(s)||0)+' ha',value:v})),{fmt:v=>C.fmt(v),aria:X.t('pn.c.status_funil')})}},

{id:'preco_indice',sec:'prod',wide:true,filters:['ano','min'],render(X){const C=X.C,years=X.years(2010,2025),amb=X.amb();
 const price=(mi,y)=>{const r=amb.filter(x=>x[1]===mi&&x[0]===y),t=sum(r,4),v=sum(r,5);return t>0&&v>0?v/t:null};
 if(X.F.min>=0)return C.line(years.map(String),[{name:X.min(X.F.min),values:years.map(y=>price(X.F.min,y))}],{fmt:v=>C.money(v,2)+'/t',axis:v=>C.short(v),aria:X.t('pn.c.preco_indice')});
 const top=[...X.sumBy(amb,r=>r[1],r=>r[5]).entries()].filter(([m])=>m>=0).sort((p,q)=>q[1]-p[1]).slice(0,6).map(([m])=>m);
 const series=top.map((mi,j)=>{const ps=years.map(y=>price(mi,y)),base=ps.find(v=>v!=null);return {name:X.min(mi),color:C.PALETTE[j],values:ps.map(v=>v!=null&&base?v/base*100:null)}});
 return C.line(years.map(String),series,{fmt:v=>C.fmt(v,0),axis:v=>C.fmt(v,0),aria:X.t('pn.c.preco_indice')})}},
{id:'share_min',sec:'prod',filters:['ano'],render(X){const C=X.C,go=X.P.amb_go.rows.filter(r=>r[0]>=X.F.y0&&r[0]<=X.F.y1),last=lastYear(go);
 const g=X.sumBy(go.filter(r=>r[0]===last&&r[1]>=0),r=>r[1],r=>r[5]),b=X.sumBy(X.P.amb_br.rows.filter(r=>r[0]===last&&r[1]>=0),r=>r[1],r=>r[3]);
 const list=[...g.entries()].filter(([m,v])=>v>0&&b.get(m)>0).map(([m,v])=>({label:X.min(m),value:v/b.get(m)*100})).sort((p,q)=>q.value-p.value).slice(0,15);
 return `<p class="small muted">${X.E(X.t('pn.refYear',{y:last||'—'}))}</p>`+C.hbar(list,{fmt:v=>C.fmt(v,1)+' %',aria:X.t('pn.c.share_min')})}},
{id:'rom_benef',sec:'prod',filters:['ano','min'],render(X,box){const C=X.C,amb=X.amb(),last=lastYear(amb),rows=amb.filter(r=>r[0]===last&&r[2]>0&&r[4]>0).sort((a,b)=>b[2]-a[2]);
 C.table(tableIn(X,box,X.t('pn.refYear',{y:last||'—'})),[{label:X.t('pn.h.min'),get:r=>X.min(r[1])},{label:X.t('pn.h.rom'),get:r=>r[2],num:1,fmt:v=>C.fmt(v,0)},
  {label:X.t('pn.h.benefT'),get:r=>r[4],num:1,fmt:v=>C.fmt(v,2)},{label:X.t('pn.h.romPorT'),get:r=>r[2]/r[4],num:1,fmt:v=>C.fmt(v,v<10?2:0)}],rows,{limit:12})}},
// Physical beneficiated output by mineral, in tonnes and never summed across minerals. A break is a year more than 10 times above, or
// below a tenth of, the median of the other producing years (at least 3): a change in how the company reports, flagged and not corrected.
{id:'benef_t',sec:'prod',wide:true,filters:['ano','min'],render(X,box){const C=X.C,years=X.years(2010,2025),amb=X.amb();
 const serie=mi=>{const m=new Map();amb.forEach(r=>{if(r[1]===mi)m.set(r[0],(m.get(r[0])||0)+r[4])});return m};
 const quebras=s=>[...s].filter(([y,v])=>{if(!(v>0))return false;const o=[...s].filter(([z,w])=>z!==y&&w>0).map(x=>x[1]).sort((a,b)=>a-b);
  if(o.length<3)return false;const h=o.length>>1,med=o.length%2?o[h]:(o[h-1]+o[h])/2;return v>10*med||v<med/10}).map(([y])=>y).sort((a,b)=>a-b);
 const ton=v=>C.fmt(v,v<100?2:0);
 if(X.F.min>=0){const s=serie(X.F.min),q=quebras(s);
  return (q.length?`<p class="small muted">${X.E(X.t('pn.benefT.quebra',{y:q.join(', ')}))}</p>`:'')
   +C.vbar(years.map(String),[{name:X.min(X.F.min),values:years.map(y=>s.get(y)||0)}],{fmt:v=>ton(v)+' t',axis:v=>C.short(v),partial:new Set(q.map(String)),aria:X.t('pn.c.benef_t')})}
 const last=lastYear(amb),rows=[...new Set(amb.filter(r=>r[1]>=0).map(r=>r[1]))].map(mi=>{const s=serie(mi),ys=[...s.keys()].filter(y=>s.get(y)>0).sort((a,b)=>a-b);
  return {mi,s,first:ys[0],q:quebras(s)}}).filter(r=>r.s.get(last)>0).sort((a,b)=>b.s.get(last)-a.s.get(last));
 C.table(tableIn(X,box,X.t('pn.benefT.tabela',{y:last||'—'})),[{label:X.t('pn.h.min'),get:r=>X.min(r.mi)},{label:X.t('pn.h.desde'),get:r=>r.first,num:1,fmt:v=>String(v)},
  {label:X.t('pn.h.tPrimeiro'),get:r=>r.s.get(r.first)||0,num:1,fmt:ton},{label:X.t('pn.h.tUltimo'),get:r=>r.s.get(last),num:1,fmt:ton},
  {label:X.t('pn.h.quebras'),get:r=>r.q.join(', ')||'—'}],rows,{limit:15})}},

{id:'inv_cfem',sec:'pesq',wide:true,filters:['ano','min'],render(X,box){const C=X.C,P=X.P,F=X.F,y0=Math.max(F.y0,2022),y1=Math.min(F.y1,2025);
 if(y0>y1)return notice(X,'pn.invCfemYears');
 const minOf=i=>P.dims.subinv[i][1];
 const inv=X.sumBy(P.inv_go.rows.filter(r=>r[0]>=y0&&r[0]<=y1&&minOf(r[1])>=0&&(F.min<0||minOf(r[1])===F.min)),r=>minOf(r[1]),r=>r[3]);
 const cf=X.sumBy(P.cfem.rows.filter(r=>r[0]>=y0&&r[0]<=y1&&r[3]>=0&&(F.min<0||r[3]===F.min)),r=>r[3],r=>r[5]);
 const rows=[...inv.keys()].map(m=>({min:X.min(m),i:inv.get(m),c:cf.get(m)||0})).filter(r=>r.i>0).sort((a,b)=>b.i-a.i);
 C.table(tableIn(X,box,X.t('pn.invCfemCaption',{a:y0,b:y1})),[{label:X.t('pn.h.min'),key:'min'},{label:X.t('pn.h.invest'),key:'i',num:1,fmt:v=>C.money(v,0)},
  {label:X.t('pn.h.cfem'),key:'c',num:1,fmt:v=>v?C.money(v,0):'—'},{label:X.t('pn.h.invPorCfem'),get:r=>r.c?r.i/r.c:null,num:1,fmt:v=>v==null?X.t('pn.semCfem'):C.fmt(v,2)}],rows,{limit:12})}},
{id:'proj_min',sec:'proj',wide:true,filters:['mun','min'],render(X,box){if(!X.A)return noAtlas(X);const C=X.C,F=X.F,code=F.mun>=0?X.munCode(F.mun):'',name=F.min>=0?X.min(F.min):'',g=new Map();
 atlasRows(X,'projects').filter(p=>(!code||String(p.mun)===code)&&(!name||p.mineral===name)).forEach(p=>{let a=g.get(p.mineral);if(!a)g.set(p.mineral,a={p:0,o:0,s:0,b:0,ha:0});
  a[p.classe==='provável'?'p':p.classe==='possível'?'o':'s']++;if(p.brownfield)a.b++;a.ha+=p.area_ha||0});
 const tot=e=>e[1].p+e[1].o+e[1].s;
 C.table(box,[{label:X.t('pn.h.min'),get:e=>e[0]},{label:X.t('pn.h.provavel'),get:e=>e[1].p,num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.possivel'),get:e=>e[1].o,num:1,fmt:v=>C.fmt(v)},
  {label:X.t('pn.h.sinal'),get:e=>e[1].s,num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.total'),get:tot,num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.brownfield'),get:e=>e[1].b,num:1,fmt:v=>C.fmt(v)},
  {label:X.t('pn.h.area'),get:e=>e[1].ha,num:1,fmt:v=>C.fmt(v,0)}],[...g.entries()].sort((a,b)=>tot(b)-tot(a)),{limit:12})}},
{id:'proj_mun',sec:'proj',filters:['min'],render(X){if(!X.A)return noAtlas(X);const C=X.C,name=X.F.min>=0?X.min(X.F.min):'',nome=new Map(X.A.municipalities.map(m=>[m.code,m.name]));
 const by=X.sumBy(atlasRows(X,'projects').filter(p=>p.classe!=='sinal'&&(!name||p.mineral===name)),p=>String(p.mun),()=>1);
 return C.hbar(X.topRows(by,12,c=>nome.get(c)||X.t('pn.notInformed')),{fmt:v=>C.fmt(v),aria:X.t('pn.c.proj_mun')})}},
{id:'occ_sub',sec:'proj',filters:['mun'],render(X,box){if(!X.A)return noAtlas(X);
 const C=X.C,code=X.F.mun>=0?X.munCode(X.F.mun):'',IMP=['Depósito','Ocorrência','Indício','Indeterminado'],by=new Map();
 atlasRows(X,'occurrences').filter(o=>!code||String(o.mun)===code)
  .forEach(o=>String(o.substancias||'').split(';').map(x=>x.trim()).filter(Boolean).forEach(x=>{
   const r=by.get(x)||{sub:x,total:0};r[o.importancia]=(r[o.importancia]||0)+1;r.total++;by.set(x,r)}));
 const rows=[...by.values()].sort((a,b)=>b.total-a.total);
 C.table(box,[{label:X.t('pn.h.sub'),key:'sub'},...IMP.map(k=>({label:X.t(`pn.imp.${k}`),key:k,num:1,fmt:v=>C.fmt(v||0)})),
  {label:X.t('pn.h.total'),key:'total',num:1,fmt:v=>C.fmt(v)}],rows,{limit:12})}},
// A unica serie do bloco removido do Atlas sem equivalente aqui: diz quanto da producao bruta a base
// consegue atribuir a operacoes com coordenada, que e o quanto se pode confiar nos numeros de producao.
{id:'cobertura',sec:'prod',filters:[],render(X){if(!X.A)return noAtlas(X);
 const C=X.C,c=X.A.charts&&X.A.charts.operation_coverage;
 if(!c)return noAtlas(X);
 return C.vbar(c.labels.map(String),c.groups.map((g,i)=>({name:X.t(`pn.cov.${g}`),color:C.PALETTE[i%C.PALETTE.length],values:c.values[i]})),
  {stacked:true,fmt:v=>C.fmt(v,1)+' %',aria:X.t('pn.c.cobertura')})}},

{id:'emp_pareto',sec:'emp',filters:['ano','mes','mun','min'],render(X){const C=X.C,v=[...X.sumBy(X.cfem(['emp']),r=>r[4],r=>r[5]).values()].filter(x=>x>0).sort((a,b)=>b-a),t=v.reduce((s,x)=>s+x,0);
 if(!t)return C.empty();let acc=0;const vals=v.slice(0,Math.min(50,v.length)).map(x=>(acc+=x)/t*100);
 return C.line(vals.map((_,i)=>String(i+1)),[{name:X.t('pn.cumShare'),values:vals}],{fmt:v=>C.fmt(v,1)+' %',axis:v=>C.fmt(v,0)+'%',aria:X.t('pn.c.emp_pareto')})}},
{id:'emp_dormente',sec:'emp',wide:true,filters:['mun','min','emp'],render(X,box){const C=X.C,P=X.P,pagou=X.memo('empPagou',()=>new Set(P.cfem.rows.filter(r=>r[5]>0).map(r=>r[4]))),g=new Map();
 X.proc(['fase']).filter(r=>X.LAVRA.includes(P.dims.fase[r[0]])&&!pagou.has(r[3])).forEach(r=>{let a=g.get(r[3]);if(!a)g.set(r[3],a={n:0,ha:0,mins:new Map(),muns:new Set()});
  a.n++;a.ha+=r[4];a.mins.set(r[1],(a.mins.get(r[1])||0)+1);if(r[2]>=0)a.muns.add(r[2])});
 C.table(box,[{label:X.t('pn.h.holder'),get:e=>X.emp(e[0])},{label:X.t('pn.h.titles'),get:e=>e[1].n,num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.area'),get:e=>e[1].ha,num:1,fmt:v=>C.fmt(v,0)},
  {label:X.t('pn.h.mins'),get:e=>[...e[1].mins.entries()].sort((a,b)=>b[1]-a[1]).slice(0,3).map(([m])=>X.min(m)).join(', ')},{label:X.t('pn.h.muns'),get:e=>e[1].muns.size,num:1,fmt:v=>C.fmt(v)}],
  [...g.entries()].sort((a,b)=>b[1].ha-a[1].ha),{limit:12})}},

{id:'ee_cadeia_mes',sec:'energia',wide:true,filters:['ano','mes','mun','emp'],render(X){const C=X.C,P=X.P,idx=X.MINING_RAMOS.map(r=>P.dims.ramo.indexOf(r)).filter(i=>i>=0);
 const rows=X.ccee(['ramo']).filter(r=>idx.includes(r[2])),keys=[...new Set(rows.map(r=>r[0]))].sort((a,b)=>a-b);
 const series=idx.map((ri,j)=>{const by=X.sumBy(rows.filter(r=>r[2]===ri),r=>r[0],r=>r[6]/1000);return {name:P.dims.ramo[ri],color:C.PALETTE[j],values:keys.map(k=>by.get(k)||0)}});
 return C.vbar(keys.map(monthLabel),series,{stacked:true,fmt:v=>C.fmt(v,1)+' GWh',axis:v=>C.fmt(v,0),aria:X.t('pn.c.ee_cadeia_mes')})}},
{id:'ee_ramo_tab',sec:'energia',wide:true,filters:['ano','mes','mun','emp'],render(X,box){const C=X.C,P=X.P,g=new Map();let tot=0;
 X.ccee(['ramo']).filter(r=>!X.isDist(r[2])).forEach(r=>{let a=g.get(r[2]);if(!a)g.set(r[2],a={t:0,e:new Set(),ch:0});a.t+=r[6];a.e.add(r[3]);a.ch+=r[7]*hours(r[0]);tot+=r[6]});
 C.table(box,[{label:X.t('pn.h.ramo'),get:e=>P.dims.ramo[e[0]]},{label:X.t('pn.h.gwh'),get:e=>e[1].t/1000,num:1,fmt:v=>C.fmt(v,1)},{label:X.t('pn.h.shareLivre'),get:e=>tot?e[1].t/tot*100:0,num:1,fmt:v=>C.fmt(v,1)},
  {label:X.t('pn.h.emps'),get:e=>e[1].e.size,num:1,fmt:v=>C.fmt(v)},{label:X.t('pn.h.fc'),get:e=>e[1].ch?e[1].t/e[1].ch*100:0,num:1,fmt:v=>v?C.fmt(v,0)+' %':'—'}],
  [...g.entries()].sort((a,b)=>b[1].t-a[1].t),{limit:16})}},
{id:'ee_rs_mwh',sec:'energia',filters:['ano','mes','mun','ramo','emp'],render(X){const C=X.C,P=X.P,mwh=X.sumBy(X.ccee().filter(r=>P.dims.ce[r[3]][2]>=0),r=>r[3],r=>r[6]),cf=X.sumBy(X.cfem(['mun','min','emp']),r=>r[4],r=>r[5]);
 const list=[...mwh.entries()].filter(([,v])=>v>=1000).map(([ce,v])=>({label:X.ceName(ce),value:(cf.get(P.dims.ce[ce][2])||0)/v})).filter(r=>r.value>0).sort((a,b)=>b.value-a.value).slice(0,15);
 return C.hbar(list,{fmt:v=>C.money(v,2),aria:X.t('pn.c.ee_rs_mwh')})}},

// A unica medida de energia por unidade extraida que existe no acervo: producao vinda dos relatorios
// das proprias empresas, curada no artefato do Squad 1. Tudo mais em `energy` e razao municipal.
{id:'coef_emp',sec:'intens',wide:true,filters:[],render(X,box){if(!X.A)return noAtlas(X);
 const C=X.C,E=X.E,rows=X.A.coef||[];
 if(!rows.length)return `<p class="empty">${E(X.t('pn.empty'))}</p>`;
 const BASE={'metal contido':'metal','produto':'produto','capacidade':'capacidade','exportação':'exportacao'};
 const CONF={'alta':'alta','média':'media','baixa':'baixa'};
 const cols=[['pn.h.emp',0],['pn.h.operacao',0],['pn.h.ore',0],['pn.h.qtd',1],['pn.h.coef',1],['pn.h.base',0],['pn.h.conf',0],['pn.h.fonte',0]];
 box.innerHTML=`<p class="small muted">${E(X.t('pn.coefNote'))}</p><div class="table-wrap"><table class="pn-table"><thead><tr>`
  +cols.map(([k,n])=>`<th${n?' class="num"':''}>${E(X.t(k))}</th>`).join('')+'</tr></thead><tbody>'
  +rows.map(r=>{const cf=CONF[r.conf]||'baixa';
   return '<tr>'
    +`<td>${E(r.empresa)}</td>`
    +`<td>${E(r.operacao)}<br><span class="small muted">${E(r.detalhe||'')}</span></td>`
    +`<td>${E(r.produto)}</td>`
    +`<td class="num">${E(C.fmt(r.qtd,String(r.un).startsWith('kg')?2:0))} ${E(r.un)}</td>`
    +`<td class="num"><b>${E(C.fmt(r.coef,r.coef<1?4:2))}</b> ${E(r.coef_un)}</td>`
    +`<td>${E(X.t(`pn.base.${BASE[r.base]||'produto'}`))} · ${E(r.ano)}</td>`
    +`<td><span class="pill conf-${cf}">${E(X.t(`pn.conf.${cf}`))}</span></td>`
    +`<td><a href="${E(r.url)}" target="_blank" rel="noopener noreferrer">${E(r.fonte)}</a></td>`
    +'</tr>'}).join('')
  +'</tbody></table></div>'}},
{id:'ee_kwh_t',sec:'intens',filters:['mun'],render(X){if(!X.A)return noAtlas(X);const C=X.C,code=X.F.mun>=0?X.munCode(X.F.mun):'',nome=new Map(X.A.municipalities.map(m=>[m.code,m.name]));
 const list=X.A.energy.filter(e=>e.classe==='comparavel'&&e.kwh_t>0&&(!code||e.cod===code)).map(e=>({label:(nome.get(e.cod)||e.mun)+' · '+e.sub,value:e.kwh_t})).sort((a,b)=>b.value-a.value).slice(0,15);
 return C.hbar(list,{fmt:v=>C.fmt(v,1)+' kWh/t',aria:X.t('pn.c.ee_kwh_t')})}},
{id:'ee_sub',sec:'intens',filters:[],render(X){if(!X.A)return noAtlas(X);const C=X.C,by=X.sumBy(X.A.energy.filter(e=>e.mwh>0),e=>e.sub||X.t('pn.notInformed'),e=>e.mwh/1000);
 return C.hbar(X.topRows(by,12,k=>k),{fmt:v=>C.fmt(v,1)+' GWh',aria:X.t('pn.c.ee_sub')})}},
{id:'ee_mwh_cfem',sec:'intens',filters:['mun'],render(X){if(!X.A)return noAtlas(X);const C=X.C,code=X.F.mun>=0?X.munCode(X.F.mun):'',nome=new Map(X.A.municipalities.map(m=>[m.code,m.name]));
 const list=X.A.energy.filter(e=>['comparavel','ouro'].includes(e.classe)&&e.mwh>0&&e.cfem>0&&(!code||e.cod===code)).map(e=>({label:nome.get(e.cod)||e.mun,value:e.mwh/(e.cfem/1000)})).sort((a,b)=>b.value-a.value).slice(0,15);
 return C.hbar(list,{fmt:v=>C.fmt(v,2)+' MWh',aria:X.t('pn.c.ee_mwh_cfem')})}}
);
})();
