/* Previsão de demanda: the Squad 2 energy-demand model (Squad 2/modello_reale) as a panel tab.
   Everything comes from public/data/previsao/previsao_v1.json, built by scripts/build_previsao_base.py from the
   model outputs; nothing is recomputed here. Three sub-tabs: forecast, data used and methodology. */
(()=>{'use strict';
const el=id=>document.getElementById(id);
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const SOURCE='/data/previsao/previsao_v1.json';
const CEN=['conservador','referencia','expansao'];
// Validated categorical sets (light surface): scenarios and minerals; colour follows the entity, never its rank.
const COR_CEN={conservador:'#d7a43a',referencia:'#0f6fb0',expansao:'#b03a55'};
const COR_MIN=['#0f6fb0','#c2681b','#0d9488','#b03a55','#8250c4'];
const COR_PROJ='#57768b'; // new projects: a neutral slate, apart from the five mineral hues
const FONT=12,CHAR=FONT*.58;
let d=null,loaded=false,aba='previsao',cenario='referencia',mineralSel=null;

const fmt=(v,c=0)=>v==null||!Number.isFinite(v)?'—':I18N.num(v,{maximumFractionDigits:c,minimumFractionDigits:c});
const twh=v=>fmt(v/1e6,2);
const pct=(v,c=1)=>v==null?'—':fmt(v*100,c)+'%';
const ano=v=>I18N.num(v,{useGrouping:false});
// Keys built from data values go through tk(), so the i18n test does not read the bare prefix as a key.
const tk=(prefixo,valor)=>t(prefixo+String(valor).normalize('NFD').replace(/[\u0300-\u036f]/g,''));
const nomeCen=c=>tk('pv.cen.',c);
const nomeMin=m=>tk('pv.min.',m.mineral_id);
const corMin=m=>COR_MIN[d.minerais.indexOf(m)%COR_MIN.length];
const base=b=>tk('pv.base.',b);
const metodo=m=>tk('pv.met.',m);
const tip=(...p)=>p.filter(x=>x!=null&&x!=='').map(E).join('&#10;');
const largura=id=>Math.max(280,Math.round((el(id).clientWidth||860)));
const totalDe=(a,c)=>d.total.find(r=>r.ano===a&&r.cenario===c);
const anos=()=>{const r=[];for(let a=d.horizonte.inicio;a<=d.horizonte.fim;a++)r.push(a);return r};
const niceStep=v=>{const p=Math.pow(10,Math.floor(Math.log10(v))),n=v/p;return(n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10)*p};
const legenda=items=>`<div class="pn-legend">${items.map(([n,c,dash])=>`<span><i style="background:${c}${dash?';height:3px;vertical-align:3px':''}"></i>${E(n)}</span>`).join('')}</div>`;

/* ---------- tooltip, scoped to this tab ---------- */
function tooltip(){
 const box=document.createElement('div');box.className='pn-tip';box.setAttribute('role','tooltip');box.hidden=true;document.body.append(box);
 const alvo=e=>e.target&&e.target.closest?e.target.closest('#previsao-view [data-tip]'):null;
 const show=(n,x,y)=>{box.innerHTML=n.getAttribute('data-tip');box.hidden=false;const r=box.getBoundingClientRect();
  let l=x+14,tp=y+16;if(l+r.width>innerWidth-8)l=x-r.width-14;if(tp+r.height>innerHeight-8)tp=y-r.height-12;
  box.style.left=Math.max(8,l)+'px';box.style.top=Math.max(8,tp)+'px'};
 document.addEventListener('mousemove',e=>{const n=alvo(e);if(n)show(n,e.clientX,e.clientY);else if(!box.hidden)box.hidden=true});
 document.addEventListener('click',e=>{const n=alvo(e);if(n)show(n,e.clientX,e.clientY)},true);
 addEventListener('scroll',()=>{box.hidden=true},true)}

/* ---------- charts (inline SVG, one y axis each) ---------- */
function eixoY(max,unidade){const passo=niceStep(max/4),topo=Math.ceil(max/passo)*passo,ticks=[];for(let v=0;v<=topo+1e-9;v+=passo)ticks.push(v);return{topo,ticks,unidade}}

// Lines over years. series: [{nome,cor,pontos:[{x,y}],tracejado,largura}], banda: {cor,pontos:[{x,lo,hi}]}
function linhas(w,series,o){
 const H=300,L=58,R=16,T=14,B=30,xs=[...new Set(series.flatMap(s=>s.pontos.map(p=>p.x)))].sort((a,b)=>a-b);
 const maxY=Math.max(...series.flatMap(s=>s.pontos.map(p=>p.y)),...(o.banda?o.banda.pontos.map(p=>p.hi):[0]))*1.04;
 const ey=eixoY(maxY),x0=xs[0],x1=xs[xs.length-1];
 const X=v=>L+(w-L-R)*(x1===x0?0.5:(v-x0)/(x1-x0)),Y=v=>T+(H-T-B)*(1-v/ey.topo);
 let s=`<svg width="${w}" height="${H}" viewBox="0 0 ${w} ${H}" font-size="${FONT}" role="img" aria-label="${E(o.aria)}">`;
 for(const v of ey.ticks)s+=`<line x1="${L}" x2="${w-R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e8eef2"/><text x="${L-8}" y="${Y(v)+4}" text-anchor="end" fill="#637787">${E(o.fy(v))}</text>`;
 const passo=Math.max(1,Math.ceil(xs.length/Math.max(2,Math.floor((w-L-R)/(4*CHAR+14)))));
 xs.forEach((v,i)=>{const fim=xs.length-1;if(i===fim||(i%passo===0&&fim-i>=passo))s+=`<text x="${X(v)}" y="${H-10}" text-anchor="middle" fill="#637787">${E(ano(v))}</text>`});
 if(o.divisa!=null)s+=`<line x1="${X(o.divisa)}" x2="${X(o.divisa)}" y1="${T}" y2="${H-B}" stroke="#9fb3c2" stroke-dasharray="3 3"/><text x="${X(o.divisa)+5}" y="${T+10}" fill="#637787">${E(o.divisaRotulo||'')}</text>`;
 if(o.banda){const p=o.banda.pontos;s+=`<path d="M${p.map(q=>X(q.x)+','+Y(q.hi)).join('L')}L${p.slice().reverse().map(q=>X(q.x)+','+Y(q.lo)).join('L')}Z" fill="${o.banda.cor}" opacity=".14"/>`}
 for(const se of series){if(!se.pontos.length)continue;
  s+=`<path d="M${se.pontos.map(p=>X(p.x)+','+Y(p.y)).join('L')}" fill="none" stroke="${se.cor}" stroke-width="${se.largura||2}" stroke-linejoin="round"${se.tracejado?' stroke-dasharray="6 4"':''}/>`;
  const ult=se.pontos[se.pontos.length-1];if(se.rotulo)s+=`<circle cx="${X(ult.x)}" cy="${Y(ult.y)}" r="4" fill="${se.cor}" stroke="#fff" stroke-width="2"/>`}
 // Hover columns: one invisible band per x, with every series' value at that year.
 const meia=(w-L-R)/Math.max(1,xs.length-1)/2;
 for(const v of xs){const linhasTip=o.tipAno(v);if(!linhasTip)continue;
  s+=`<rect x="${X(v)-meia}" y="${T}" width="${meia*2}" height="${H-T-B}" fill="transparent" data-tip="${tip(...linhasTip)}" class="pv-hit"/>`}
 return s+'</svg>'}

// Stacked columns: one column per year, one segment per mineral.
function colunas(w,anosL,segs,o){
 const H=300,L=58,R=12,T=14,B=30,tot=anosL.map(a=>segs.reduce((s,g)=>s+(g.valores[a]||0),0));
 const ey=eixoY(Math.max(...tot)*1.04),Y=v=>T+(H-T-B)*(1-v/ey.topo),passoX=(w-L-R)/anosL.length,bw=Math.max(6,Math.min(34,passoX*.62));
 let s=`<svg width="${w}" height="${H}" viewBox="0 0 ${w} ${H}" font-size="${FONT}" role="img" aria-label="${E(o.aria)}">`;
 for(const v of ey.ticks)s+=`<line x1="${L}" x2="${w-R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e8eef2"/><text x="${L-8}" y="${Y(v)+4}" text-anchor="end" fill="#637787">${E(o.fy(v))}</text>`;
 const passo=Math.max(1,Math.ceil((4*CHAR+10)/passoX));
 anosL.forEach((a,i)=>{const cx=L+passoX*(i+.5);let acc=0;
  segs.forEach((g,j)=>{const v=g.valores[a]||0;if(v<=0)return;const y0=Y(acc),y1=Y(acc+v);acc+=v;const h=Math.max(0,y0-y1-(j?2:0));
   s+=`<rect x="${cx-bw/2}" y="${y1}" width="${bw}" height="${h}" fill="${g.cor}" rx="${j===segs.length-1?2:0}" data-tip="${tip(g.nome+' · '+ano(a),o.fv(v),t('pv.tip.share',{v:fmt(v/tot[i]*100,0)}),t('pv.tip.total',{v:o.fv(tot[i])}))}"/>`});
  if(i===anosL.length-1||(i%passo===0&&anosL.length-1-i>=passo))s+=`<text x="${cx}" y="${H-10}" text-anchor="middle" fill="#637787">${E(ano(a))}</text>`});
 return s+'</svg>'}

/* ---------- tables ---------- */
function tabela(cab,linhas,num){
 return `<table class="pn-table"><thead><tr>${cab.map((h,i)=>`<th${num&&num.includes(i)?' class="num"':''}>${E(h)}</th>`).join('')}</tr></thead><tbody>`
  +linhas.map(l=>`<tr>${l.map((c,i)=>`<td${num&&num.includes(i)?' class="num"':''}>${c}</td>`).join('')}</tr>`).join('')+'</tbody></table>'}

function csv(nome,cab,linhas){
 const q=v=>{v=String(v??'');return /[",;\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v};
 const blob=new Blob(['﻿'+[cab,...linhas].map(l=>l.map(q).join(',')).join('\n')],{type:'text/csv;charset=utf-8'});
 const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=nome;document.body.append(a);a.click();
 setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},0)}

/* ---------- sub-tab 1: forecast ---------- */
function metricas(){
 const r27=totalDe(d.horizonte.inicio,'referencia'),r40=totalDe(d.horizonte.fim,'referencia');
 const c40=totalDe(d.horizonte.fim,'conservador'),e40=totalDe(d.horizonte.fim,'expansao');
 const cagr=Math.pow(r40.energia_mwh/r27.energia_mwh,1/(d.horizonte.fim-d.horizonte.inicio))-1;
 const m=(rot,val,det)=>`<div class="metric"><span>${E(rot)}</span><strong>${E(val)}</strong><small>${E(det)}</small></div>`;
 el('pv-metrics').innerHTML=
  m(t('pv.k.ini',{a:ano(d.horizonte.inicio)}),twh(r27.energia_mwh)+' TWh',t('pv.k.iniSub',{lo:twh(r27.baixa_mwh),hi:twh(r27.alta_mwh)}))
  +m(t('pv.k.fim',{a:ano(d.horizonte.fim)}),twh(r40.energia_mwh)+' TWh',t('pv.k.iniSub',{lo:twh(r40.baixa_mwh),hi:twh(r40.alta_mwh)}))
  +m(t('pv.k.amp',{a:ano(d.horizonte.fim)}),twh(c40.energia_mwh)+' – '+twh(e40.energia_mwh)+' TWh',t('pv.k.ampSub'))
  +m(t('pv.k.cagr'),(cagr>=0?'+':'')+fmt(cagr*100,2)+'% '+t('pv.k.aa'),t('pv.k.cagrSub',{a:ano(d.horizonte.inicio),b:ano(d.horizonte.fim)}))}

function graficoTotal(){
 const A=anos(),w=largura('pv-total');
 const series=CEN.map(c=>({nome:nomeCen(c),cor:COR_CEN[c],largura:c===cenario?3:2,rotulo:true,
  pontos:A.map(a=>({x:a,y:totalDe(a,c).energia_mwh/1e6}))}));
 const banda={cor:COR_CEN[cenario],pontos:A.map(a=>{const r=totalDe(a,cenario);return{x:a,lo:r.baixa_mwh/1e6,hi:r.alta_mwh/1e6}})};
 el('pv-total').innerHTML=linhas(w,series,{aria:t('pv.c.totalAria'),banda,fy:v=>fmt(v,1),
  tipAno:a=>[ano(a),...CEN.map(c=>`${nomeCen(c)}: ${twh(totalDe(a,c).energia_mwh)} TWh`),
   t('pv.tip.band',{c:nomeCen(cenario),lo:twh(totalDe(a,cenario).baixa_mwh),hi:twh(totalDe(a,cenario).alta_mwh)})]})
  +legenda([...CEN.map(c=>[nomeCen(c),COR_CEN[c]]),[t('pv.c.bandLeg',{c:nomeCen(cenario)}),COR_CEN[cenario]+'40']])}

// Energy of each mineral's existing operations (trend) plus one segment for the weighted project portfolio.
const energiaProjetos=(m,c,a)=>{const p=m.cenarios[c].serie.find(x=>x.ano===a);return p?p.producao_projetos_t*p.intensidade_mwh_t:0};
const energiaProjetosTotal=(c,a)=>d.minerais.reduce((s,m)=>s+energiaProjetos(m,c,a),0);
function graficoComposicao(){
 const A=anos(),w=largura('pv-comp');
 const segs=d.minerais.map(m=>({nome:nomeMin(m),cor:corMin(m),
  valores:Object.fromEntries(m.cenarios[cenario].serie.map(p=>[p.ano,p.producao_tendencia_t*p.intensidade_mwh_t/1e6]))}));
 const temProjetos=A.some(a=>energiaProjetosTotal(cenario,a)>0);
 if(temProjetos)segs.push({nome:t('pv.c.projSeg'),cor:COR_PROJ,valores:Object.fromEntries(A.map(a=>[a,energiaProjetosTotal(cenario,a)/1e6]))});
 el('pv-comp').innerHTML=colunas(w,A,segs,{aria:t('pv.c.compAria'),fy:v=>fmt(v,1),fv:v=>fmt(v,2)+' TWh'})
  +legenda([...d.minerais.map(m=>[nomeMin(m),corMin(m)]),...(temProjetos?[[t('pv.c.projSeg'),COR_PROJ]]:[])])}

function tabelaCarteiraEfeito(){
 const c=d.carteira,quant=c.projetos.filter(p=>p.no_modelo),A=anos().filter(a=>CEN.some(x=>energiaProjetosTotal(x,a)>0));
 el('pv-proj-sub').textContent=t('pv.p.efeitoSub',{q:quant.length,n:c.projetos.length});
 if(!A.length){el('pv-proj-efeito').innerHTML=`<p class="muted small">${E(t('pv.p.nenhum'))}</p>`;return}
 const linhasT=A.map(a=>[E(ano(a)),...CEN.map(x=>{const v=energiaProjetosTotal(x,a),tot=totalDe(a,x).energia_mwh;
  return `${fmt(v/1e3,0)}<div class="mk-note">${E(t('pv.p.doTotal',{v:fmt(v/tot*100,1)}))}</div>`})]);
 el('pv-proj-efeito').innerHTML=tabela([t('pv.t.ano'),...CEN.map(nomeCen)],linhasT,[1,2,3])
  +`<p class="mk-note">${E(t('pv.p.quais',{l:quant.map(p=>p.projeto).join('; ')}))}</p>`}

function tabelaMinerais(){
 const sel=[d.horizonte.inicio,2030,2035,d.horizonte.fim].filter((a,i,arr)=>a>=d.horizonte.inicio&&a<=d.horizonte.fim&&arr.indexOf(a)===i);
 const linhasT=d.minerais.map(m=>{const s=m.cenarios[cenario].serie;
  return[`<i class="pv-dot" style="background:${corMin(m)}"></i><b>${E(nomeMin(m))}</b>`,...sel.map(a=>{const p=s.find(x=>x.ano===a);return fmt(p.energia_mwh/1e3,0)}),
   E(fmt(s[s.length-1].baixa_mwh/1e3,0)+' – '+fmt(s[s.length-1].alta_mwh/1e3,0))]});
 linhasT.push([`<b>${E(t('pv.t.total'))}</b>`,...sel.map(a=>`<b>${fmt(totalDe(a,cenario).energia_mwh/1e3,0)}</b>`),
  `<b>${E(fmt(totalDe(d.horizonte.fim,cenario).baixa_mwh/1e3,0)+' – '+fmt(totalDe(d.horizonte.fim,cenario).alta_mwh/1e3,0))}</b>`]);
 el('pv-tab-min').innerHTML=tabela([t('pv.t.mineral'),...sel.map(a=>ano(a)),t('pv.t.faixa',{a:ano(d.horizonte.fim)})],linhasT,[1,2,3,4,5]);
 el('pv-tab-min-sub').textContent=t('pv.t.minSub',{c:nomeCen(cenario)})}

function tabelaAnos(){
 const linhasT=anos().map(a=>[E(ano(a)),...CEN.flatMap(c=>{const r=totalDe(a,c);return[c===cenario?`<b>${twh(r.energia_mwh)}</b>`:twh(r.energia_mwh),E(twh(r.baixa_mwh)+' – '+twh(r.alta_mwh))]})]);
 el('pv-tab-anos').innerHTML=tabela([t('pv.t.ano'),...CEN.flatMap(c=>[nomeCen(c),t('pv.t.faixaCurta')])],linhasT,[1,2,3,4,5,6])}

function exportar(){
 const cab=['ano','cenario','mineral_id','mineral','base_producao','producao_projetada_t','producao_tendencia_t','producao_projetos_t','intensidade_mwh_t','energia_mwh','faixa_baixa_mwh','faixa_alta_mwh'];
 const linhasC=[];for(const m of d.minerais)for(const c of CEN)for(const p of m.cenarios[c].serie)
  linhasC.push([p.ano,c,m.mineral_id,m.nome,m.base_producao,p.producao_t,p.producao_tendencia_t,p.producao_projetos_t,p.intensidade_mwh_t,p.energia_mwh,p.baixa_mwh,p.alta_mwh]);
 linhasC.sort((a,b)=>a[0]-b[0]||CEN.indexOf(a[1])-CEN.indexOf(b[1])||String(a[2]).localeCompare(b[2]));
 csv('previsao_demanda_energia_goias.csv',cab,linhasC)}

function desenharPrevisao(){metricas();graficoTotal();graficoComposicao();tabelaCarteiraEfeito();tabelaMinerais();tabelaAnos();
 el('pv-total-sub').textContent=t('pv.c.totalSub',{c:nomeCen(cenario)});el('pv-comp-sub').textContent=t('pv.c.compSub',{c:nomeCen(cenario)})}

/* ---------- sub-tab 2: data used ---------- */
function graficoProducao(){
 const m=d.minerais.find(x=>x.mineral_id===mineralSel),w=largura('pv-prod');
 const hist=m.historico.serie.map(p=>({x:p.ano,y:p.producao_t}));
 const series=[{nome:t('pv.d.obs'),cor:'#14354e',pontos:hist,largura:2.5},
  ...CEN.map(c=>({nome:nomeCen(c),cor:COR_CEN[c],tracejado:true,rotulo:true,
   pontos:[hist[hist.length-1],...m.cenarios[c].serie.map(p=>({x:p.ano,y:p.producao_t}))]}))];
 const porAno=a=>{const o=m.historico.serie.find(p=>p.ano===a);if(o)return[ano(a),t('pv.d.tipObs',{v:fmt(o.producao_t,0)})];
  const linhasP=CEN.map(c=>{const p=m.cenarios[c].serie.find(q=>q.ano===a);return p?`${nomeCen(c)}: ${fmt(p.producao_t,0)} t`:null}).filter(Boolean);
  return linhasP.length?[ano(a),...linhasP]:null};
 el('pv-prod').innerHTML=linhas(w,series,{aria:t('pv.d.prodAria',{m:nomeMin(m)}),fy:v=>v>=1e6?fmt(v/1e6,1)+' '+t('pv.u.mi'):v>=1e3?fmt(v/1e3,0)+' '+t('pv.u.mil'):fmt(v,0),
  tipAno:porAno,divisa:m.ano_base,divisaRotulo:t('pv.d.anoBase',{a:ano(m.ano_base)})})
  +legenda([[t('pv.d.obs'),'#14354e'],...CEN.map(c=>[t('pv.d.proj',{c:nomeCen(c)}),COR_CEN[c],true])]);
 el('pv-prod-sub').textContent=t('pv.d.prodSub',{b:base(m.base_producao),a:ano(m.historico.serie[0].ano),z:ano(m.historico.serie[m.historico.serie.length-1].ano)})}

function tabelaCoeficientes(){
 const linhasT=d.minerais.map(m=>{const c=m.coeficiente;
  return[`<i class="pv-dot" style="background:${corMin(m)}"></i><b>${E(nomeMin(m))}</b><div class="mk-note">${E(base(m.base_producao))}</div>`,
   `<b>${fmt(c.mwh_t,3)}</b>`,`<span class="pill">${E(tk('pv.nat.',c.natureza))}</span>`,
   c.energia_ccee_mwh==null?'—':fmt(c.energia_ccee_mwh,0),c.producao_coberta_t==null?'—':fmt(c.producao_coberta_t,0),
   pct(c.cobertura,0),E(c.confianca||'—'),`<span class="mk-note">${E(c.metodo_agregacao||'')}</span><div class="mk-note">${E(c.observacao||'')}</div>`]});
 el('pv-coef').innerHTML=tabela([t('pv.t.mineral'),t('pv.d.cMwh'),t('pv.d.cNat'),t('pv.d.cEnergia'),t('pv.d.cProd'),t('pv.d.cCob'),t('pv.d.cConf'),t('pv.d.cObs')],linhasT,[1,3,4,5])}

function tabelaHistorico(){
 const todos=[...new Set(d.minerais.flatMap(m=>m.historico.serie.map(p=>p.ano)))].sort((a,b)=>a-b);
 const linhasT=todos.map(a=>[E(ano(a)),...d.minerais.map(m=>{const p=m.historico.serie.find(x=>x.ano===a);return p?fmt(p.producao_t,0):'—'})]);
 el('pv-hist').innerHTML=tabela([t('pv.t.ano'),...d.minerais.map(m=>nomeMin(m)+' (t)')],linhasT,d.minerais.map((_,i)=>i+1))}

function fontes(){
 const link=u=>!u?'':/^https?:/.test(u)?`<a href="${E(u)}" target="_blank" rel="noopener noreferrer">${E(u)}</a>`:`<code>${E(u)}</code>`;
 el('pv-fontes').innerHTML=d.fontes.map(f=>`<li><div><b>${E(f.source_name)}</b> <span class="pill">${E(tk('pv.nat.',f.valor_observado_estimado))}</span></div>`
  +`<div class="mk-note"><span class="mk-code">${E(f.source_id)}</span> · ${E(t('pv.d.fPer'))} ${E(f.periodo_referencia)} · ${E(t('pv.d.fStatus'))} ${E(f.status_validacao)}</div>`
  +(f.metodo_estimacao?`<div class="mk-note">${E(f.metodo_estimacao)}</div>`:'')+(f.notas?`<div class="mk-note">${E(f.notas)}</div>`:'')
  +(f.source_url?`<div class="mk-note">${link(f.source_url)}</div>`:'')+'</li>').join('')}

/* ---------- sub-tab 3: methodology ---------- */
function tabelaCarteira(){
 const mins=Object.fromEntries(d.minerais.map(m=>[m.mineral_id,m]));
 const link=p=>p.link&&/^https?:/.test(p.link)?`<a href="${E(p.link)}" target="_blank" rel="noopener noreferrer">${E(p.fonte||p.link)}</a>`:E(p.fonte||'');
 const linhasT=d.carteira.projetos.map(p=>[
  `<b>${E(p.projeto)}</b><div class="mk-note">${E([p.empresa,p.municipio].filter(Boolean).join(' · '))}</div>`,
  `<i class="pv-dot" style="background:${corMin(mins[p.mineral_id])}"></i>${E(nomeMin(mins[p.mineral_id]))}`,
  `<span class="pill">${E(tk('pv.mat.',p.maturidade))}</span>`,
  p.no_modelo?`<b>${E(t('pv.p.sim'))}</b>`:E(t('pv.p.nao')),
  p.no_modelo?`${fmt(p.incremento_t_ano,0)} t/${E(t('pv.p.ano'))}<div class="mk-note">${E(ano(p.inicio)+'–'+ano(p.fim))}</div>`:'—',
  `<span class="pv-nowrap">${E(CEN.map(c=>fmt(p.pesos[c],2)).join(' / '))}</span>`,
  `<span class="mk-note">${E(tk('pv.mot.',p.motivo))}</span>`+(p.nota_quantidade?`<div class="mk-note">${E(p.nota_quantidade)}</div>`:''),
  `<span class="mk-note">${link(p)}</span>`]);
 el('pv-carteira').innerHTML=tabela([t('pv.p.cProj'),t('pv.t.mineral'),t('pv.p.cMat'),t('pv.p.cEntra'),t('pv.p.cInc'),t('pv.p.cPesos'),t('pv.p.cMotivo'),t('pv.p.cFonte')],linhasT,[4])}

function metodologia(){
 el('pv-pesos').innerHTML=tabela([t('pv.p.cMat'),...CEN.map(nomeCen)],
  d.carteira.pesos.map(r=>[`<span class="pill">${E(tk('pv.mat.',r.maturidade))}</span>`,...CEN.map(c=>fmt(r[c],2))]),[1,2,3]);
 el('pv-cenarios').innerHTML=tabela([t('pv.m.cCen'),t('pv.m.cAjuste'),t('pv.m.cEf'),t('pv.m.cNat')],
  d.cenarios.map(c=>[`<i class="pv-dot" style="background:${COR_CEN[c.cenario]}"></i><b>${E(nomeCen(c.cenario))}</b>`,
   (c.ajuste_crescimento>0?'+':'')+fmt(c.ajuste_crescimento*100,1)+' p.p.',fmt(c.ganho_eficiencia_anual*100,1)+'% '+E(t('pv.k.aa')),E(tk('pv.nat.',c.natureza))]),[1,2]);
 el('pv-regras').innerHTML=tabela([t('pv.t.mineral'),t('pv.m.rBase'),t('pv.m.rJanela'),t('pv.m.rHist'),...CEN.map(nomeCen)],
  d.minerais.map(m=>[`<b>${E(nomeMin(m))}</b>`,E(base(m.base_producao)),E(ano(m.janela_tendencia[0])+'–'+ano(m.janela_tendencia[1])),
   pct(m.crescimento_historico,2),...CEN.map(c=>{const r=m.cenarios[c];return`<b>${pct(r.crescimento_aplicado,2)}</b><div class="mk-note">${E(metodo(r.metodo))}</div>`})]),[3]);
 el('pv-backtest').innerHTML=tabela([t('pv.t.mineral'),t('pv.m.bTreino'),t('pv.m.bTend'),t('pv.m.bPers'),t('pv.m.bRegra')],
  d.minerais.slice().sort((a,b)=>a.backtest.mape_selecionada-b.backtest.mape_selecionada).map(m=>{const b=m.backtest;
   const melhor=b.mape_tendencia<=b.mape_persistencia?'t':'p';
   return[`<b>${E(nomeMin(m))}</b>`,E(t('pv.m.bAte',{a:ano(b.treino_ate),n:b.anos_testados})),
    (melhor==='t'?'<b>':'')+pct(b.mape_tendencia)+(melhor==='t'?'</b>':''),(melhor==='p'?'<b>':'')+pct(b.mape_persistencia)+(melhor==='p'?'</b>':''),
    E(metodo(b.regra_selecionada))]}),[2,3]);
 el('pv-backtest-det').innerHTML=tabela([t('pv.t.mineral'),t('pv.t.ano'),t('pv.m.dObs'),t('pv.m.dTend'),t('pv.m.dPers')],
  d.minerais.flatMap(m=>m.backtest.detalhe.map(p=>[E(nomeMin(m)),E(ano(p.ano)),fmt(p.observado_t,0),fmt(p.tendencia_t,0),fmt(p.persistencia_t,0)])),[2,3,4]);
 el('pv-arquivos').innerHTML=[d.modelo.diretorio,...d.modelo.scripts,'Squad 2/modello_reale/src/projects.py',d.modelo.coeficientes,d.modelo.hipoteses,d.carteira.pipeline,d.carteira.pesos_arquivo,d.carteira.curadoria,...d.modelo.producao_historica,d.gerado_por,SOURCE.slice(1).replace(/^/,'public/')]
  .map(f=>`<li><code>${E(f)}</code></li>`).join('');
 el('pv-versao').textContent=t('pv.versao',{v:d.versao,d:d.data_versao,g:d.gerado_por})}

/* ---------- wiring ---------- */
function mostrarAba(nova){aba=nova;
 document.querySelectorAll('#pv-tabs [data-pv]').forEach(b=>{const on=b.dataset.pv===aba;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on))});
 for(const k of['previsao','dados','metodo'])el('pv-'+k).hidden=k!==aba;
 desenhar()}

function desenhar(){if(!d)return;
 if(aba==='previsao')desenharPrevisao();
 if(aba==='dados'){graficoProducao();tabelaCoeficientes();tabelaCarteira();tabelaHistorico();fontes()}
 if(aba==='metodo')metodologia()}

async function load(){
 el('previsao-error').textContent='';
 try{
  const r=await fetch(SOURCE,{cache:'no-store'});if(!r.ok)throw Error(t('pv.fail'));
  d=await r.json();
  el('pv-cenario').innerHTML=CEN.map(c=>`<option value="${c}"${c===cenario?' selected':''}>${E(nomeCen(c))}</option>`).join('');
  el('pv-cenario').onchange=e=>{cenario=e.target.value;desenhar()};
  mineralSel=d.minerais[0].mineral_id;
  el('pv-mineral').innerHTML=d.minerais.map(m=>`<option value="${m.mineral_id}">${E(nomeMin(m))}</option>`).join('');
  el('pv-mineral').onchange=e=>{mineralSel=e.target.value;graficoProducao()};
  el('pv-export').onclick=exportar;
  document.querySelectorAll('#pv-tabs [data-pv]').forEach(b=>b.onclick=()=>mostrarAba(b.dataset.pv));
  let timer;addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(()=>{if(!el('previsao-view').hidden)desenhar()},150)});
  tooltip();
  el('previsao-content').hidden=false;
  mostrarAba(aba);
 }catch(e){el('previsao-error').textContent=e.message}
 finally{el('previsao-loading').hidden=true}}

window.showPrevisao=()=>{if(loaded){desenhar();return}loaded=true;load()};
})();
