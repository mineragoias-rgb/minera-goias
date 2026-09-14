/* Panorama cards: energy price and cost of energy for mining in Goiás. The consumption is observed (CCEE); every price is an
   assumption of Squad 2 (there is no observed price series in the repository yet), so each card says which of the two it shows. */
(()=>{'use strict';
const cards=window.PN_CARDS=window.PN_CARDS||[];
const CEN=['conservador','referencia','expansao'];
const cen=(X,i)=>X.t(`pn.pr.cen.${CEN[i]}`);
// Missing package: the tab still renders, saying what would fill it.
const sem=X=>`<p class="empty">${X.E(X.t('pn.pr.noData'))}</p>`;
// A premissa badge above the content of every card that shows a projected price or cost.
const aviso=(X,box,html)=>{box.innerHTML=`<p class="pn-warn">${X.E(X.t('pn.pr.premissa'))}</p><div></div>`;
 const alvo=box.lastElementChild;if(typeof html==='string')alvo.innerHTML=html;return alvo};
const anos=R=>[...new Set(R.precos.rows.map(r=>r[0]))].sort((a,b)=>a-b);
const preco=(R,ano,i)=>R.precos.rows.find(r=>r[0]===ano&&r[1]===i);
const custo=(R,ano,ip,id)=>R.custo.rows.find(r=>r[0]===ano&&r[1]===ip&&r[2]===id);
const mi=(X,v)=>X.C.money(v/1e6,1)+' '+X.t('pn.u.mi');

cards.push(
{id:'pr_tiles',sec:'precos',wide:true,filters:[],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 const b=R.meta.baseline,f=R.meta.faixa_premissa_ano_base,a0=R.meta.horizonte[0],a1=R.meta.horizonte[1],ref=CEN.indexOf('referencia');
 const p0=preco(R,a0,ref),p1=preco(R,a1,ref),c1=custo(R,a1,ref,ref);
 // Três dos quatro números são projeção: o aviso vale para o quadro inteiro.
 aviso(X,box,'<div class="metrics pn-tiles">'+C.tiles([
  ['tone-a',X.t('pn.pr.k.base'),C.fmt(b.mwh_ano/1000,0)+' GWh',X.t('pn.pr.k.baseSub',{y:b.ano,m:b.meses,n:b.empresas})],
  ['tone-b',X.t('pn.pr.k.price'),C.money(p1[5],0)+'/MWh',X.t('pn.pr.k.priceSub',{a:C.money(p0[5],0),y0:a0,y1:a1})],
  ['tone-c',X.t('pn.pr.k.cost'),mi(X,c1[4]),X.t('pn.pr.k.costSub',{y:a1,g:C.fmt(c1[3]/1000,0)})],
  ['tone-d',X.t('pn.pr.k.range'),C.money(f.min,0)+' – '+C.money(f.max,0),X.t('pn.pr.k.rangeSub',{v:C.money(f.base,0),y:R.meta.ano_base})]])+'</div>')}},

{id:'pr_curvas',sec:'precos',wide:true,filters:[],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 const ys=anos(R),series=CEN.map((_,i)=>({name:cen(X,i),values:ys.map(y=>preco(R,y,i)[5])}));
 aviso(X,box,C.line(ys.map(String),series,{fmt:v=>C.money(v,2)+'/MWh',axis:v=>C.fmt(v,0),aria:X.t('pn.c.pr_curvas')}))}},

{id:'pr_comp',sec:'precos',filters:[],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 const a1=R.meta.horizonte[1],comps=R.meta.componentes;
 const series=comps.map((c,j)=>({name:X.t(`pn.pr.comp.${c}`),values:CEN.map((_,i)=>preco(R,a1,i)[2+j])}));
 aviso(X,box,C.vbar(CEN.map((_,i)=>cen(X,i)),series,{stacked:true,fmt:v=>C.money(v,2),axis:v=>C.fmt(v,0),aria:X.t('pn.c.pr_comp')}))}},

{id:'pr_custo',sec:'precos',wide:true,filters:[],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 // The diagonal of the matrix: price and demand of the same scenario. The crossings are in pr_matriz.
 const ys=anos(R),series=CEN.map((_,i)=>({name:cen(X,i),values:ys.map(y=>custo(R,y,i,i)[4]/1e6)}));
 aviso(X,box,C.line(ys.map(String),series,{fmt:v=>C.money(v,1)+' '+X.t('pn.u.mi'),axis:v=>C.fmt(v,0)+' '+X.t('pn.u.mi'),aria:X.t('pn.c.pr_custo')}))}},

{id:'pr_matriz',sec:'precos',filters:[],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 const a1=R.meta.horizonte[1],alvo=aviso(X,box);
 C.table(alvo,[{label:X.t('pn.pr.h.priceScenario'),key:'p'},...CEN.map((_,id)=>({label:cen(X,id),get:r=>r.v[id],num:1,fmt:v=>mi(X,v)}))],
  CEN.map((_,ip)=>({p:cen(X,ip),v:CEN.map((__,id)=>custo(R,a1,ip,id)[4])})))}},

{id:'pr_sens',sec:'precos',filters:[],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 const alvo=aviso(X,box);
 C.table(alvo,[{label:X.t('pn.pr.h.param'),get:r=>X.t(`pn.pr.sens.${r.parametro}`)},{label:X.t('pn.pr.h.cost2040'),key:'custo_brl',num:1,fmt:v=>mi(X,v)},
  {label:X.t('pn.pr.h.var'),key:'variacao_pct',num:1,fmt:v=>(v>0?'+':'')+C.fmt(v,1)+' %'}],R.sensibilidade,{limit:8})}},

{id:'pr_obs',sec:'precos',wide:true,filters:['ano'],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 const rows=R.observado.por_ano.filter(r=>r.ano>=X.F.y0&&r.ano<=X.F.y1);
 C.table(box,[{label:X.t('pn.h.year'),key:'ano'},{label:X.t('pn.h.months'),key:'meses',num:1},
  {label:X.t('pn.pr.h.gwhTit'),get:r=>r.mwh_titular/1000,num:1,fmt:v=>C.fmt(v,1)},
  {label:X.t('pn.pr.h.gwhRamo'),get:r=>r.mwh_ramo/1000,num:1,fmt:v=>C.fmt(v,1)},
  {label:X.t('pn.pr.h.gwhBase'),get:r=>r.mwh_base/1000,num:1,fmt:v=>C.fmt(v,1)},
  {label:X.t('pn.pr.h.annualised'),get:r=>r.mwh_titular_anualizado/1000,num:1,fmt:v=>v?C.fmt(v,1):'—'},
  {label:X.t('pn.h.livrePct'),key:'acl_pct_titular',num:1,fmt:v=>v==null?'—':C.fmt(v,1)},
  {label:X.t('pn.h.emps'),key:'empresas',num:1},{label:X.t('pn.h.muns'),key:'municipios',num:1}],rows)}},

{id:'pr_emp',sec:'precos',wide:true,filters:['emp'],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 const ref=CEN.indexOf('referencia'),p=preco(R,R.meta.horizonte[0],ref)[5];
 // Annual cost of each load at the reference price: the observed MWh over every month covered, scaled to twelve months.
 const meses=R.observado.por_ano.reduce((s,r)=>s+r.meses,0),fator=12/meses;
 const rows=R.observado.por_empresa.filter(e=>X.F.emp===''||X.norm(e.nome).includes(X.F.emp));
 const alvo=aviso(X,box);
 C.table(alvo,[{label:X.t('pn.h.emp'),key:'nome'},{label:X.t('pn.h.mun'),key:'municipio'},{label:X.t('pn.h.ramo'),key:'ramo'},
  {label:X.t('pn.h.mwh'),key:'mwh',num:1,fmt:v=>C.fmt(v,0)},{label:X.t('pn.h.mw'),key:'mw_media',num:1,fmt:v=>v?C.fmt(v,1):'—'},
  {label:X.t('pn.h.fc'),key:'fator_carga',num:1,fmt:v=>v?C.fmt(v,0)+' %':'—'},
  {label:X.t('pn.pr.h.costYear'),get:e=>e.mwh*fator*p,num:1,fmt:v=>mi(X,v)}],rows,{limit:12})}},

{id:'pr_premissas',sec:'precos',wide:true,filters:[],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 const alvo=aviso(X,box),num=v=>v===''||v==null?'—':C.fmt(+v,2);
 C.table(alvo,[{label:X.t('pn.pr.h.component'),get:r=>X.t(`pn.pr.comp.${r.componente}`)},{label:X.t('pn.pr.h.priceScenario'),get:r=>X.t(`pn.pr.cen.${r.cenario}`)},
  {label:X.t('pn.pr.h.p0'),get:r=>+r.preco_base_brl_mwh,num:1,fmt:v=>C.money(v,2)},
  {label:X.t('pn.pr.h.band'),get:r=>r.faixa_min_brl_mwh?C.fmt(+r.faixa_min_brl_mwh,0)+' – '+C.fmt(+r.faixa_max_brl_mwh,0):'—'},
  {label:X.t('pn.pr.h.longRun'),get:r=>r.nivel_longo_prazo_brl_mwh,num:1,fmt:num},
  {label:X.t('pn.pr.h.halfLife'),get:r=>r.meia_vida_anos,num:1,fmt:v=>v?C.fmt(+v,0):'—'},
  {label:X.t('pn.pr.h.trend'),get:r=>100*+r.tendencia_real_aa,num:1,fmt:v=>(v>0?'+':'')+C.fmt(v,1)+' %'},
  {label:X.t('pn.pr.h.method'),get:r=>X.t(`pn.pr.metodo.${r.metodo}`)},{label:X.t('pn.pr.h.nature'),key:'data_nature'}],R.premissas.preco,{limit:9})}},

{id:'pr_fontes',sec:'precos',wide:true,filters:[],render(X,box){const C=X.C,R=X.PR;if(!R)return sem(X);
 C.table(box,[{label:X.t('pn.pr.h.source'),key:'source_name'},{label:X.t('pn.pr.h.institution'),key:'instituicao'},
  {label:X.t('pn.pr.h.series'),key:'serie_necessaria'},{label:X.t('pn.pr.h.unit'),key:'unidade'},
  {label:X.t('pn.pr.h.status'),get:r=>X.t(`pn.pr.status.${r.status}`)}],R.premissas.fontes,{limit:8})}}
);
})();
