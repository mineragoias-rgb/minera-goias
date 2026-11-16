/* Território e emissões: the Squad 2 report "Mineração e Cerrado em Goiás" as a panel tab, drawn like the other tabs.
   It reads the two files the Squad 2 delivered in Squad 2/mineracao_cerrado/, through the routes behind the session
   (Squad 3/backend/territorio.py): the report, whose tables sit in an embedded `const D={...}` object, and the project risk
   layer (GeoJSON), loaded only when the risk sub-tab opens. Nothing is recomputed here except counts and filters.
   Four sub-tabs: 1985–2025, scenarios, risk by project and method. */
(()=>{'use strict';
const el=id=>document.getElementById(id);
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Colour follows the entity: the scenarios keep the Previsão tab colours, risk is an ordered ramp from slate to crimson.
const COR_CEN={conservador:'#d7a43a',referencia:'#0f6fb0',expansao:'#b03a55',sinais:'#57768b'};
const CEN=['conservador','referencia','expansao','sinais'];
const RISCO=['baixo','medio','alto','muito_alto'];
const COR_RISCO={baixo:'#9fb3c2',medio:'#d7a43a',alto:'#c2681b',muito_alto:'#b03a55'};
const MAT=['operacao','provavel','possivel','sinal'];
const COR={area:'#0f6fb0',biomassa:'#0d9488',solo:'#c2681b',nativa:'#0d9488',evento:'#0f6fb0',lavra:'#8250c4',mina:'#14354e'};
const FONT=12,CHAR=FONT*.58,LISTA=25;
let d=null,P=null,carregandoP=null,loaded=false,aba='historico',mapa=null,camada=null,limite=LISTA;

/* ---------- reading the Squad 2 files ---------- */
// Labels in the files → codes the dictionaries translate.
const COD={
 via:{'direta':'direta','indireta<= 3 anos':'indireta','antrópica→mina':'antropica','camada B (proxy 30+25 em título ANM)':'titulo_anm'},
 cen:{'conservador':'conservador','referência':'referencia','expansão':'expansao','sinais (sensib.)':'sinais'},
 mat:{'OPERAÇÃO':'operacao','PROVÁVEL':'provavel','POSSÍVEL':'possivel','SINAL':'sinal'},
 risco:{'Baixo':'baixo','Médio':'medio','Alto':'alto','Muito alto':'muito_alto'},
 qual:{'Baixa':'baixa','Média':'media','Alta':'alta'},
 conf:{'BAIXO':'baixa','MÉDIO':'media','ALTO':'alta'}};
const ANEL={1:'0-1',2:'1-3',3:'3-5',soma:'0-5'};

async function buscar(caminho){
 const r=await fetch('/api/territorio/'+caminho,{credentials:'same-origin'});
 if(r.status===401){location.replace('/login.html');throw Error(t('c.sessionEnded'))}
 if(!r.ok)throw Error(t('te.fail'));return r}

// The report draws its charts from `const D={...}`, plain JSON inside the page: take that object, nothing else.
function dadosDoRelatorio(html){
 const m=/\bconst\s+D\s*=\s*\{/.exec(html);if(!m)throw Error(t('te.fail'));
 let i=m.index+m[0].length-1,nivel=0,str=false,esc=false;
 for(let j=i;j<html.length;j++){const c=html[j];
  if(str){if(esc)esc=false;else if(c==='\\')esc=true;else if(c==='"')str=false;continue}
  // Python wrote the object, so missing values come as bare NaN, which JSON does not accept.
  if(c==='"')str=true;else if(c==='{')nivel++;else if(c==='}'&&--nivel===0)
   return JSON.parse(html.slice(i,j+1).replace(/([\[,:]\s*)-?(?:NaN|Infinity)(?=\s*[,\]}])/g,'$1null'))}
 throw Error(t('te.fail'))}

function montar(D){
 return{
  historico:{
   area_minerada:D.serie.map(([a,ha])=>({ano:a,ha})),
   origem_da_area:D.vias.map(([n,ha,b])=>({via:COD.via[n]||n,ha,biomassa_tco2:b})),
   nativa_por_classe:D.origem.map(([classe,ha])=>({classe,ha})),
   emissao_por_mineral:D.e_mineral.map(([mineral,ha,b,s])=>({mineral,ha,biomassa_tco2:b,solo_tco2:s})),
   emissao_biomassa_por_ano:D.e_ano.map(([a,v])=>({ano:a,biomassa_tco2:v})),
   emissao_biomassa:D.E0.map(([,ha,v,lo,hi,th,k])=>({janela_anos:k,ha,tco2:v,tco2_p05:lo,tco2_p95:hi,tco2_ha:th})),
   emissao_solo:D.solo.map(([n,ha,v,lo,hi,th])=>({metodo:n.startsWith('modelo')?'modelo':'decapeamento',ha,tco2:v,tco2_p05:lo===''?null:lo,tco2_p95:hi===''?null:hi,tco2_ha:th}))},
  entorno:{
   estudo_de_evento:D.ev.map(([a,e,v,lo,hi])=>({anel:ANEL[a],ano_relativo:e,dif_pp:v,ic_baixo:lo,ic_alto:hi})),
   permutacao:D.perm.map(([a,h,v,p,lo,hi])=>({anel:ANEL[a],ano_relativo:h.includes('e=-1')?-1:10,unidade:a==='soma'?'ha_por_mina':'pp',efeito:v,p_valor:p,placebo_p05:lo,placebo_p95:hi}))},
  titulos:{
   defasagem:D.lag.map(([mineral,n,p25,med,p75])=>({mineral,todos:mineral==='TODOS',aberturas:n,p25,mediana:med,p75})),
   sem_lavra_visivel:D.km.map(([anos,s])=>({anos,sem_lavra:s})),
   area_por_tonelada:D.dose.map(([grupo,a9,a25,rom,hm])=>({grupo,area_2009_ha:a9,area_2025_ha:a25,rom_mt:rom,ha_por_mt:hm})),
   painel_area_producao:D.dose_reg.map(([n,c,ep,obs])=>({especificacao:n.includes('tendência')?'tendencia':'grupo',coef_ha_mt:c,erro_padrao:ep,n:obs}))},
  cenarios:{
   acumulado:D.cen.map(([c,a,n,ar,alo,ahi,e,elo,ehi,nat,ent])=>({cenario:COD.cen[c]||c,ano:a,projetos:n,area_ha:ar,area_p05:alo,area_p95:ahi,mtco2:e,mtco2_p05:elo,mtco2_p95:ehi,nativa_ha:nat,entorno_mtco2:ent})),
   grupo_maturidade:D.grupo_mat.map(([grupo,m,n,ar,nat,e])=>({grupo,maturidade:COD.mat[m]||m,projetos:n,area_ha:ar,nativa_ha:nat,mtco2:e}))},
  minas:D.minas.map(([lon,lat,ha])=>({lon,lat,ha}))}}

// Area centroid of the title polygon: the layer's own lat/lon are rounded to 0.1° (about 11 km).
function centro(g){
 const partes=g.type==='MultiPolygon'?g.coordinates:[g.coordinates];let A=0,X=0,Y=0;
 for(const pol of partes){const r=pol[0];for(let i=0;i<r.length-1;i++){const[x0,y0]=r[i],[x1,y1]=r[i+1],c=x0*y1-x1*y0;A+=c;X+=(x0+x1)*c;Y+=(y0+y1)*c}}
 return Math.abs(A)<1e-12?null:[Y/(3*A),X/(3*A)]}

function projeto(f){const p=f.properties,c=f.geometry?centro(f.geometry):null;
 return{id:p.id,projeto:p.projeto,empresa:p.empresa,mineral:p.mineral,categoria:p.categoria,grupo:p.grupo,municipio:p.municipio,
  maturidade:COD.mat[p.maturidade]||p.maturidade,confianca:COD.conf[p.confianca]||p.confianca,qualidade:COD.qual[p.qualidade_dado]||p.qualidade_dado,
  nativa_share:p.nativa_share_2025,area_p05:p.pot_area_ha_p05,area_p50:p.pot_area_ha_p50,area_p95:p.pot_area_ha_p95,nativa_p50:p.pot_desmat_nativa_ha_p50,
  tco2_p05:p.pot_tCO2_p05,tco2_p50:p.pot_tCO2_p50,tco2_p95:p.pot_tCO2_p95,entorno_tco2:p.pot_entorno_tCO2_indicativo,indice_tco2:p.indice_impacto_tCO2,
  risco:COD.risco[p.risco]||p.risco,risco_score:p.risco_score,lat:c?c[0]:p.lat,lon:c?c[1]:p.lon}}

function carregarProjetos(){
 if(!carregandoP)carregandoP=buscar('risco.geojson').then(r=>r.json()).then(g=>{P=g.features.map(projeto)});
 return carregandoP}

const fmt=(v,c=0)=>v==null||!Number.isFinite(v)?'—':I18N.num(v,{maximumFractionDigits:c,minimumFractionDigits:c});
const ano=v=>I18N.num(v,{useGrouping:false});
const pct=(v,c=0)=>v==null?'—':fmt(v*100,c)+'%';
const mt=v=>fmt(v/1e6,2);
// Keys built from data values go through tk(), so the i18n test does not read the bare prefix as a key.
const tk=(prefixo,valor)=>t(prefixo+String(valor));
const nomeCen=c=>tk('te.cen.',c),nomeMat=m=>tk('te.mat.',m),nomeRisco=r=>tk('te.risco.',r);
const tip=(...p)=>p.filter(x=>x!=null&&x!=='').map(E).join('&#10;');
const largura=id=>Math.max(260,Math.round(el(id).clientWidth||860));
const niceStep=v=>{if(!(v>0))return 1;const p=Math.pow(10,Math.floor(Math.log10(v))),n=v/p;return(n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10)*p};
const legenda=items=>`<div class="pn-legend">${items.map(([n,c,linha])=>`<span><i style="background:${c}${linha?';height:3px;vertical-align:3px':''}"></i>${E(n)}</span>`).join('')}</div>`;
const pill=s=>`<span class="pill">${E(s)}</span>`;
const selo=r=>`<span class="te-risco" style="--c:${COR_RISCO[r]}">${E(nomeRisco(r))}</span>`;

/* ---------- tooltip, scoped to this tab ---------- */
function tooltip(){
 const box=document.createElement('div');box.className='pn-tip';box.setAttribute('role','tooltip');box.hidden=true;document.body.append(box);
 const alvo=e=>e.target&&e.target.closest?e.target.closest('#territorio-view [data-tip]'):null;
 const show=(n,x,y)=>{box.innerHTML=n.getAttribute('data-tip');box.hidden=false;const r=box.getBoundingClientRect();
  let l=x+14,tp=y+16;if(l+r.width>innerWidth-8)l=x-r.width-14;if(tp+r.height>innerHeight-8)tp=y-r.height-12;
  box.style.left=Math.max(8,l)+'px';box.style.top=Math.max(8,tp)+'px'};
 document.addEventListener('mousemove',e=>{const n=alvo(e);if(n)show(n,e.clientX,e.clientY);else if(!box.hidden)box.hidden=true});
 document.addEventListener('click',e=>{const n=alvo(e);if(n)show(n,e.clientX,e.clientY)},true);
 addEventListener('scroll',()=>{box.hidden=true},true)}

/* ---------- charts (inline SVG, one y axis each) ---------- */
function eixo(min,max){const passo=niceStep((max-min)/4),base=Math.floor(min/passo)*passo,topo=Math.ceil(max/passo)*passo,ticks=[];
 for(let v=base;v<=topo+passo*1e-6;v+=passo)ticks.push(Math.abs(v)<passo*1e-6?0:v);return{base,topo,ticks}}
function grade(s,ey,Y,L,R,w,fy){for(const v of ey.ticks)s.push(`<line x1="${L}" x2="${w-R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${v===0&&ey.base<0?'#9fb3c2':'#e8eef2'}"/><text x="${L-8}" y="${Y(v)+4}" text-anchor="end" fill="#637787">${E(fy(v))}</text>`)}
function rotulosX(s,xs,X,H,w,L,R,f){const passo=Math.max(1,Math.ceil(xs.length/Math.max(2,Math.floor((w-L-R)/(4*CHAR+16)))));
 xs.forEach((v,i)=>{const fim=xs.length-1;if(i===fim||(i%passo===0&&fim-i>=passo))s.push(`<text x="${X(v)}" y="${H-10}" text-anchor="middle" fill="#637787">${E(f(v))}</text>`)})}

// Lines over x. series: [{cor,pontos:[{x,y}],area,degrau}], o.banda: {cor,pontos:[{x,lo,hi}]}, o.tipX(x) -> lines, o.divisa: x.
function linhas(w,series,o){
 const H=o.altura||290,L=o.margem||58,R=16,T=14,B=30,xs=[...new Set(series.flatMap(s=>s.pontos.map(p=>p.x)))].sort((a,b)=>a-b);
 const ys=series.flatMap(s=>s.pontos.map(p=>p.y)).concat(o.banda?o.banda.pontos.flatMap(p=>[p.lo,p.hi]):[]);
 const lo=o.min!=null?o.min:Math.min(0,...ys),hi=o.max!=null?o.max:Math.max(...ys)*1.06;
 const ey=eixo(lo,hi),x0=o.x0!=null?o.x0:xs[0],x1=o.x1!=null?o.x1:xs[xs.length-1];
 const X=v=>L+(w-L-R)*(x1===x0?.5:(v-x0)/(x1-x0)),Y=v=>T+(H-T-B)*(ey.topo-v)/(ey.topo-ey.base);
 const s=[`<svg width="${w}" height="${H}" viewBox="0 0 ${w} ${H}" font-size="${FONT}" role="img" aria-label="${E(o.aria)}">`];
 grade(s,ey,Y,L,R,w,o.fy);rotulosX(s,o.ticksX||xs,X,H,w,L,R,o.fx||ano);
 if(o.divisa!=null)s.push(`<line x1="${X(o.divisa)}" x2="${X(o.divisa)}" y1="${T}" y2="${H-B}" stroke="#9fb3c2" stroke-dasharray="3 3"/><text x="${X(o.divisa)+5}" y="${T+10}" fill="#637787">${E(o.divisaRotulo||'')}</text>`);
 if(o.banda){const p=o.banda.pontos;s.push(`<path d="M${p.map(q=>X(q.x)+','+Y(q.hi)).join('L')}L${p.slice().reverse().map(q=>X(q.x)+','+Y(q.lo)).join('L')}Z" fill="${o.banda.cor}" opacity=".16"/>`)}
 for(const se of series){if(!se.pontos.length)continue;const p=se.pontos;
  const caminho=se.degrau?p.map((q,i)=>(i?`H${X(q.x)}V${Y(q.y)}`:`M${X(q.x)},${Y(q.y)}`)).join(''):'M'+p.map(q=>X(q.x)+','+Y(q.y)).join('L');
  if(se.area)s.push(`<path d="${caminho}L${X(p[p.length-1].x)},${Y(Math.max(0,ey.base))}L${X(p[0].x)},${Y(Math.max(0,ey.base))}Z" fill="${se.cor}" opacity=".12"/>`);
  s.push(`<path d="${caminho}" fill="none" stroke="${se.cor}" stroke-width="${se.largura||2}" stroke-linejoin="round"/>`);
  if(se.pontosVisiveis)for(const q of p)s.push(`<circle cx="${X(q.x)}" cy="${Y(q.y)}" r="2.6" fill="${se.cor}"/>`);
  if(se.rotuloFim){const u=p[p.length-1];s.push(`<circle cx="${X(u.x)}" cy="${Y(u.y)}" r="4" fill="${se.cor}" stroke="#fff" stroke-width="2"/><text x="${X(u.x)-8}" y="${Y(u.y)-9}" text-anchor="end" fill="#14354e" font-weight="600">${E(se.rotuloFim)}</text>`)}}
 const meia=(w-L-R)/Math.max(1,xs.length-1)/2;
 for(const v of xs){const l=o.tipX&&o.tipX(v);if(!l)continue;
  s.push(`<rect x="${X(v)-meia}" y="${T}" width="${meia*2}" height="${H-T-B}" fill="transparent" data-tip="${tip(...l)}" class="te-hit"/>`)}
 return s.join('')+'</svg>'}

// Vertical columns, one per x.
function colunas(w,pontos,o){
 const H=260,L=58,R=12,T=14,B=30,ey=eixo(0,Math.max(...pontos.map(p=>p.y))*1.06),Y=v=>T+(H-T-B)*(1-v/ey.topo);
 const passoX=(w-L-R)/pontos.length,bw=Math.max(3,passoX*.72),X=i=>L+passoX*(i+.5);
 const s=[`<svg width="${w}" height="${H}" viewBox="0 0 ${w} ${H}" font-size="${FONT}" role="img" aria-label="${E(o.aria)}">`];
 grade(s,ey,Y,L,R,w,o.fy);
 pontos.forEach((p,i)=>s.push(`<rect x="${X(i)-bw/2}" y="${Y(p.y)}" width="${bw}" height="${Math.max(0,Y(0)-Y(p.y))}" fill="${o.cor}" data-tip="${tip(...o.tip(p))}"/>`));
 const passo=Math.max(1,Math.ceil((4*CHAR+12)/passoX));
 pontos.forEach((p,i)=>{if(i===pontos.length-1||(i%passo===0&&pontos.length-1-i>=passo))s.push(`<text x="${X(i)}" y="${H-10}" text-anchor="middle" fill="#637787">${E(ano(p.x))}</text>`)});
 return s.join('')+'</svg>'}

// Horizontal bars, optionally stacked. linhas: [{nome,partes:[v...],tip:[...]}], cores per part.
function barras(w,dados,o){
 const rh=30,rot=Math.min(Math.round(w*.42),Math.max(90,Math.max(...dados.map(r=>r.nome.length))*CHAR+18)),R=78,T=4,H=T*2+dados.length*rh;
 const max=Math.max(...dados.map(r=>r.partes.reduce((a,b)=>a+b,0)))||1,esc=v=>v/max*(w-rot-R);
 const s=[`<svg width="${w}" height="${H}" viewBox="0 0 ${w} ${H}" font-size="${FONT}" role="img" aria-label="${E(o.aria)}">`];
 dados.forEach((r,i)=>{const y=T+i*rh;let x=rot;
  s.push(`<text x="${rot-10}" y="${y+rh/2+4}" text-anchor="end" fill="#14354e">${E(r.nome)}</text>`);
  r.partes.forEach((v,j)=>{const lw=Math.max(0,esc(v));s.push(`<rect x="${x}" y="${y+6}" width="${lw}" height="${rh-12}" fill="${o.cores[j]}" rx="2" data-tip="${tip(...r.tip)}"/>`);x+=lw});
  s.push(`<text x="${x+8}" y="${y+rh/2+4}" fill="#637787">${E(o.fv(r.partes.reduce((a,b)=>a+b,0)))}</text>`)});
 return s.join('')+'</svg>'}

// Grouped columns with a p5–p95 whisker: one group per year, one column per scenario.
function grupos(w,anosG,series,o){
 const H=300,L=58,R=12,T=18,B=30,ey=eixo(0,Math.max(...series.flatMap(s=>anosG.map(a=>s.valores[a].hi)))*1.08),Y=v=>T+(H-T-B)*(1-v/ey.topo);
 const gw=(w-L-R)/anosG.length,bw=Math.min(46,gw*.8/series.length);
 const s=[`<svg width="${w}" height="${H}" viewBox="0 0 ${w} ${H}" font-size="${FONT}" role="img" aria-label="${E(o.aria)}">`];
 grade(s,ey,Y,L,R,w,o.fy);
 anosG.forEach((a,i)=>{const x0=L+gw*i+(gw-bw*series.length)/2;
  series.forEach((se,j)=>{const v=se.valores[a],x=x0+j*bw;
   s.push(`<rect x="${x+2}" y="${Y(v.y)}" width="${bw-4}" height="${Math.max(0,Y(0)-Y(v.y))}" fill="${se.cor}" rx="2" data-tip="${tip(se.nome+' · '+ano(a),...o.tip(v))}"/>`
    +`<line x1="${x+bw/2}" x2="${x+bw/2}" y1="${Y(v.lo)}" y2="${Y(v.hi)}" stroke="#14354e" stroke-width="1.2"/>`
    +`<line x1="${x+bw/2-4}" x2="${x+bw/2+4}" y1="${Y(v.hi)}" y2="${Y(v.hi)}" stroke="#14354e" stroke-width="1.2"/>`
    +`<line x1="${x+bw/2-4}" x2="${x+bw/2+4}" y1="${Y(v.lo)}" y2="${Y(v.lo)}" stroke="#14354e" stroke-width="1.2"/>`)});
  s.push(`<text x="${L+gw*(i+.5)}" y="${H-10}" text-anchor="middle" fill="#637787">${E(ano(a))}</text>`)});
 return s.join('')+'</svg>'}

/* ---------- tables ---------- */
function tabela(cab,linhasT,num){
 return `<table class="pn-table"><thead><tr>${cab.map((h,i)=>`<th${num&&num.includes(i)?' class="num"':''}>${E(h)}</th>`).join('')}</tr></thead><tbody>`
  +linhasT.map(l=>`<tr>${l.map((c,i)=>`<td${num&&num.includes(i)?' class="num"':''}>${c}</td>`).join('')}</tr>`).join('')+'</tbody></table>'}
const faixa=(c,lo,hi,dec=0)=>`${fmt(c,dec)} <span class="mk-note te-faixa">${E(fmt(lo,dec)+'–'+fmt(hi,dec))}</span>`;

/* ---------- sub-tab 1: 1985–2025 ---------- */
const h=()=>d.historico;
const biomassa=()=>h().emissao_biomassa.find(b=>b.janela_anos===3);
const solo=m=>h().emissao_solo.find(s=>s.metodo===m);
const cen=(c,a)=>d.cenarios.acumulado.find(r=>r.cenario===c&&r.ano===a);

function metricas(){
 const A=h().area_minerada,ini=A[0],fim=A[A.length-1],b=biomassa(),dec=solo('decapeamento');
 const perm=d.entorno.permutacao.find(p=>p.anel==='0-5'),ref=cen('referencia',2035);
 const m=(rot,val,det)=>`<div class="metric"><span>${E(rot)}</span><strong>${E(val)}</strong><small>${E(det)}</small></div>`;
 el('te-metrics').innerHTML=
  m(t('te.k.area',{a:ano(fim.ano)}),fmt(fim.ha)+' ha',t('te.k.areaSub',{v:fmt(ini.ha),a:ano(ini.ano)}))
  +m(t('te.k.emissao',{a:ano(A[1].ano),b:ano(fim.ano)}),fmt((b.tco2+dec.tco2_p05)/1e6,1)+'–'+fmt((b.tco2+dec.tco2_p95)/1e6,1)+' MtCO₂',
     t('te.k.emissaoSub',{b:mt(b.tco2),lo:fmt(dec.tco2_p05/1e6,1),hi:fmt(dec.tco2_p95/1e6,1)}))
  +m(t('te.k.entorno'),'+'+fmt(perm.efeito)+' ha',t('te.k.entornoSub',{p:fmt(perm.p_valor,3)}))
  +m(t('te.k.futuro'),fmt(ref.mtco2,2)+' MtCO₂',t('te.k.futuroSub',{lo:fmt(ref.mtco2_p05,2),hi:fmt(ref.mtco2_p95,2)}))}

function graficoArea(){
 const A=h().area_minerada,w=largura('te-area'),u=A[A.length-1];
 el('te-area').innerHTML=linhas(w,[{cor:COR.area,area:true,largura:2.5,rotuloFim:fmt(u.ha)+' ha',pontos:A.map(r=>({x:r.ano,y:r.ha}))}],
  {aria:t('te.h.areaT'),fy:v=>fmt(v),tipX:x=>{const r=A.find(q=>q.ano===x);return[ano(x),fmt(r.ha)+' ha']}})}

function graficoClasses(){
 const C=h().nativa_por_classe,tot=C.reduce((s,c)=>s+c.ha,0);
 el('te-classes').innerHTML=barras(largura('te-classes'),C.map(c=>({nome:c.classe,partes:[c.ha],tip:[c.classe,fmt(c.ha)+' ha',t('te.tip.share',{v:fmt(c.ha/tot*100,0)})]})),
  {aria:t('te.h.classesT'),cores:[COR.nativa],fv:v=>fmt(v)+' ha'});
 el('te-classes-sub').textContent=t('te.h.classesSub',{v:fmt(tot)})}

function tabelaVias(){
 const V=h().origem_da_area,tot=V.reduce((s,v)=>s+v.ha,0);
 el('te-vias').innerHTML=tabela([t('te.h.cVia'),t('te.h.cArea'),t('te.h.cShare'),t('te.h.cBio'),t('te.h.cTha')],
  V.map(v=>[E(tk('te.via.',v.via)),fmt(v.ha),pct(v.ha/tot),fmt(v.biomassa_tco2/1e3),fmt(v.biomassa_tco2/v.ha)])
   .concat([[`<b>${E(t('te.t.total'))}</b>`,`<b>${fmt(tot)}</b>`,'<b>100%</b>',`<b>${fmt(V.reduce((s,v)=>s+v.biomassa_tco2,0)/1e3)}</b>`,'']]),[1,2,3,4])}

function graficoMinerais(){
 const M=h().emissao_por_mineral;
 el('te-minerais').innerHTML=barras(largura('te-minerais'),M.map(m=>({nome:m.mineral==='outros'?t('te.h.outros'):m.mineral,partes:[m.biomassa_tco2/1e6,m.solo_tco2/1e6],
   tip:[m.mineral==='outros'?t('te.h.outros'):m.mineral,t('te.tip.bio',{v:mt(m.biomassa_tco2)}),t('te.tip.solo',{v:mt(m.solo_tco2)}),t('te.tip.areaMin',{v:fmt(m.ha)})]})),
  {aria:t('te.h.mineraisT'),cores:[COR.biomassa,COR.solo],fv:v=>fmt(v,2)})
  +legenda([[t('te.h.legBio'),COR.biomassa],[t('te.h.legSolo'),COR.solo]])}

function graficoAno(){
 const A=h().emissao_biomassa_por_ano.filter(r=>r.ano>=1986);
 el('te-ano').innerHTML=colunas(largura('te-ano'),A.map(r=>({x:r.ano,y:r.biomassa_tco2/1e3})),
  {aria:t('te.h.anoT'),cor:COR.biomassa,fy:v=>fmt(v),tip:p=>[ano(p.x),fmt(p.y,1)+' ktCO₂']})}

function tabelaComponentes(){
 const b=biomassa(),m=solo('modelo'),dc=solo('decapeamento');
 el('te-componentes').innerHTML=tabela([t('te.h.cComp'),'MtCO₂',t('te.h.cFaixa'),t('te.h.cTha')],[
  [E(t('te.h.compBio')),fmt(b.tco2/1e6,2),E(fmt(b.tco2_p05/1e6,2)+'–'+fmt(b.tco2_p95/1e6,2)),fmt(b.tco2_ha)],
  [E(t('te.h.compSolo')),fmt(m.tco2/1e6,2),'—',fmt(m.tco2_ha)],
  [E(t('te.h.compDecap')),fmt(dc.tco2/1e6,2),E(fmt(dc.tco2_p05/1e6,2)+'–'+fmt(dc.tco2_p95/1e6,2)),fmt(dc.tco2_ha)]],[1,2,3]);
 el('te-janelas').textContent=t('te.h.janelas',{a:fmt(h().emissao_biomassa[0].tco2/1e6,2),b:fmt(h().emissao_biomassa[2].tco2/1e6,2)})}

function graficosEvento(){
 const ev=d.entorno.estudo_de_evento,aneis=[...new Set(ev.map(r=>r.anel))];
 const lo=Math.min(...ev.map(r=>r.ic_baixo)),hi=Math.max(...ev.map(r=>r.ic_alto));
 el('te-evento').innerHTML=aneis.map(a=>`<div class="te-mini"><h4>${E(t('te.e.anel',{a:a.replace('-','–')}))}</h4><div id="te-ev-${a}"></div></div>`).join('');
 for(const a of aneis){const r=ev.filter(x=>x.anel===a),id='te-ev-'+a,w=largura(id);
  el(id).innerHTML=linhas(w,[{cor:COR.evento,pontosVisiveis:true,pontos:r.map(q=>({x:q.ano_relativo,y:q.dif_pp}))}],
   {aria:t('te.e.anel',{a}),altura:230,margem:40,min:Math.floor(lo),max:Math.ceil(hi),fy:v=>fmt(v),fx:v=>(v>0?'+':'')+v,
    ticksX:[-10,-5,0,5,10],divisa:-.5,divisaRotulo:t('te.e.abertura'),
    banda:{cor:COR.evento,pontos:r.map(q=>({x:q.ano_relativo,lo:q.ic_baixo,hi:q.ic_alto}))},
    tipX:x=>{const q=r.find(z=>z.ano_relativo===x);return q?[t('te.e.tipAno',{e:(x>0?'+':'')+x}),t('te.e.tipDif',{v:fmt(q.dif_pp,2)}),t('te.e.tipIc',{lo:fmt(q.ic_baixo,2),hi:fmt(q.ic_alto,2)})]:null}})}
 el('te-evento-leg').innerHTML=legenda([[t('te.e.legDif'),COR.evento,true],[t('te.e.legIc'),COR.evento+'40']])}

function tabelaPermutacao(){
 el('te-perm').innerHTML=tabela([t('te.e.cAnel'),t('te.e.cHorizonte'),t('te.e.cEfeito'),t('te.e.cP'),t('te.e.cPlacebo')],
  d.entorno.permutacao.map(p=>{const ha=p.unidade==='ha_por_mina',f=v=>ha?fmt(v):fmt(v,1);
   return[E(p.anel.replace('-','–')+' km'),E(t(p.ano_relativo<0?'te.e.hAntes':'te.e.hDepois')),
    (p.p_valor<.05?'<b>':'')+E(f(p.efeito)+' '+t(ha?'te.e.uHa':'te.e.uPp'))+(p.p_valor<.05?'</b>':''),fmt(p.p_valor,3),E(f(p.placebo_p05)+' a '+f(p.placebo_p95))]}),[2,3])}

function graficoLavra(){
 const S=d.titulos.sem_lavra_visivel,w=largura('te-lavra'),dez=S.find(s=>s.anos===10);
 el('te-lavra').innerHTML=linhas(w,[{cor:COR.lavra,degrau:true,largura:2.5,pontos:S.map(s=>({x:s.anos,y:(1-s.sem_lavra)*100}))}],
  {aria:t('te.l.kmT'),min:0,max:100,x0:0,fy:v=>fmt(v)+'%',fx:v=>v,ticksX:[0,5,10,15,20,25,30,35].filter(v=>v<=S[S.length-1].anos),
   divisa:10,divisaRotulo:t('te.l.dez',{v:pct(1-dez.sem_lavra)}),
   tipX:x=>{const s=S.find(q=>q.anos===x);return[t('te.l.tipAnos',{n:x}),t('te.l.tipCom',{v:pct(1-s.sem_lavra,1)})]}});
 const todos=d.titulos.defasagem.find(r=>r.todos);
 el('te-lavra-sub').textContent=t('te.l.kmSub',{n:todos.aberturas,m:fmt(todos.mediana,1)})}

function tabelaDefasagem(){
 const L=d.titulos.defasagem.slice().sort((a,b)=>(a.todos-b.todos)||b.aberturas-a.aberturas);
 el('te-lag').innerHTML=tabela([t('te.l.cMineral'),t('te.l.cAberturas'),'p25',t('te.l.cMediana'),'p75'],
  L.map(r=>{const b=r.todos?'<b>':'',bf=r.todos?'</b>':'';return[b+E(r.todos?t('te.l.todos'):r.mineral)+bf,b+fmt(r.aberturas)+bf,fmt(r.p25,1),b+fmt(r.mediana,1)+bf,fmt(r.p75,1)]}),[1,2,3,4])}

function tabelaDose(){
 el('te-dose').innerHTML=tabela([t('te.l.cGrupo'),t('te.l.cA09'),t('te.l.cA25'),t('te.l.cRom'),t('te.l.cHaMt')],
  d.titulos.area_por_tonelada.slice().sort((a,b)=>b.ha_por_mt-a.ha_por_mt).map(r=>[E(r.grupo),fmt(r.area_2009_ha),fmt(r.area_2025_ha),fmt(r.rom_mt,1),`<b>${fmt(r.ha_por_mt,1)}</b>`]),[1,2,3,4]);
 const p=d.titulos.painel_area_producao.find(x=>x.especificacao==='grupo');
 el('te-dose-nota').textContent=t('te.l.painel',{c:fmt(p.coef_ha_mt,2),ep:fmt(p.erro_padrao,2),n:p.n})}

function desenharHistorico(){metricas();graficoArea();graficoClasses();tabelaVias();graficoMinerais();graficoAno();tabelaComponentes();
 graficosEvento();tabelaPermutacao();graficoLavra();tabelaDefasagem();tabelaDose()}

/* ---------- sub-tab 2: scenarios ---------- */
function desenharCenarios(){
 const A=[...new Set(d.cenarios.acumulado.map(r=>r.ano))].sort((a,b)=>a-b);
 const series=CEN.map(c=>({nome:nomeCen(c),cor:COR_CEN[c],valores:Object.fromEntries(A.map(a=>{const r=cen(c,a);return[a,{y:r.mtco2,lo:r.mtco2_p05,hi:r.mtco2_p95,r}]}))}));
 el('te-cen').innerHTML=grupos(largura('te-cen'),A,series,{aria:t('te.c.graficoT'),fy:v=>fmt(v,1),
  tip:v=>[t('te.c.tipMt',{v:fmt(v.y,2),lo:fmt(v.lo,2),hi:fmt(v.hi,2)}),t('te.c.tipArea',{v:fmt(v.r.area_ha)}),t('te.c.tipNativa',{v:fmt(v.r.nativa_ha)}),t('te.c.tipProj',{n:fmt(v.r.projetos)})]})
  +legenda(CEN.map(c=>[nomeCen(c),COR_CEN[c]]));
 el('te-cen-tab').innerHTML=tabela([t('te.c.cCen'),t('te.c.cAno'),t('te.c.cProj'),t('te.c.cArea'),t('te.c.cNativa'),t('te.c.cMt'),t('te.c.cEntorno')],
  CEN.flatMap(c=>A.map(a=>{const r=cen(c,a);return[`<i class="te-dot" style="background:${COR_CEN[c]}"></i><b>${E(nomeCen(c))}</b>`,E(ano(a)),fmt(r.projetos),
   faixa(r.area_ha,r.area_p05,r.area_p95),fmt(r.nativa_ha),faixa(r.mtco2,r.mtco2_p05,r.mtco2_p95,2),a===2035?fmt(r.entorno_mtco2,1):'—']})),[2,3,4,5,6]);
 const G=d.cenarios.grupo_maturidade,grs=[...new Set(G.map(g=>g.grupo))];
 el('te-gm').innerHTML=tabela([t('te.c.cGrupo'),...MAT.map(nomeMat),t('te.t.total')],
  grs.map(g=>{const linha=MAT.map(m=>G.find(x=>x.grupo===g&&x.maturidade===m));const tot=linha.reduce((s,x)=>s+(x?x.area_ha:0),0);
   return[`<b>${E(g)}</b>`,...linha.map(x=>x?`${fmt(x.area_ha)}<div class="mk-note">${E(t('te.c.gmNota',{n:x.projetos,v:fmt(x.mtco2,2)}))}</div>`:'—'),`<b>${fmt(tot)}</b>`]}),[1,2,3,4,5])}

/* ---------- sub-tab 3: risk by project ---------- */
function filtrados(){
 const r=el('te-f-risco').value,m=el('te-f-mat').value,g=el('te-f-grupo').value,b=el('te-f-busca').value.trim().toLowerCase();
 return P.filter(p=>(!r||p.risco===r)&&(!m||p.maturidade===m)&&(!g||p.grupo===g)
  &&(!b||[p.id,p.projeto,p.empresa,p.municipio,p.mineral,p.categoria].join(' ').toLowerCase().includes(b)))}

function matriz(){
 el('te-matriz').innerHTML=tabela([t('te.r.cMat'),...RISCO.map(nomeRisco),t('te.t.total')],
  MAT.map(m=>{const q=P.filter(p=>p.maturidade===m);return[pill(nomeMat(m)),...RISCO.map(r=>{const n=q.filter(p=>p.risco===r).length;return n?fmt(n):'<span class="muted">0</span>'}),`<b>${fmt(q.length)}</b>`]})
   .concat([[`<b>${E(t('te.t.total'))}</b>`,...RISCO.map(r=>`<b>${fmt(P.filter(p=>p.risco===r).length)}</b>`),`<b>${fmt(P.length)}</b>`]]),[1,2,3,4,5]);
 const alta=P.filter(p=>p.confianca==='alta').length;
 el('te-matriz-nota').textContent=t('te.r.confianca',{n:fmt(alta),t:fmt(P.length)})}

function desenharMapa(F){
 if(!window.L){el('te-mapa').textContent=t('te.r.semMapa');return}
 const novo=!mapa;
 if(!mapa){mapa=L.map('te-mapa',{preferCanvas:true,scrollWheelZoom:true,minZoom:5,maxZoom:14,zoomSnap:.25});
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap'}).addTo(mapa);
  const minas=L.layerGroup().addTo(mapa);
  for(const m of d.minas)L.circleMarker([m.lat,m.lon],{radius:2.5,color:COR.mina,weight:1,fillColor:COR.mina,fillOpacity:1,interactive:false}).addTo(minas);
  mapa.fitBounds(L.latLngBounds(P.map(p=>[p.lat,p.lon])).pad(.04))}
 if(camada)camada.remove();camada=L.layerGroup().addTo(mapa);
 const max=Math.max(...P.map(p=>p.indice_tco2))||1;
 F.slice().sort((a,b)=>RISCO.indexOf(a.risco)-RISCO.indexOf(b.risco)||a.indice_tco2-b.indice_tco2).forEach(p=>{
  L.circleMarker([p.lat,p.lon],{radius:3+9*Math.sqrt(p.indice_tco2/max),color:'#ffffff',weight:1,fillColor:COR_RISCO[p.risco],fillOpacity:.88})
   .bindTooltip(`<b>${E(p.projeto)}</b><br>${E([p.id,p.mineral,p.municipio].filter(Boolean).join(' · '))}<br>${E(nomeMat(p.maturidade))} · ${E(t('te.r.tipRisco',{r:nomeRisco(p.risco)}))}<br>${E(t('te.r.tipTco2',{v:fmt(p.tco2_p50/1e3,1)}))}`,{direction:'top'})
   .addTo(camada)});
 // The panel may have just been shown: measure again, and frame Goiás once the map has its real size.
 requestAnimationFrame(()=>{mapa.invalidateSize();if(novo)mapa.fitBounds(L.latLngBounds(P.map(p=>[p.lat,p.lon])).pad(.04))})}

function tabelaProjetos(F){
 const ord=F.slice().sort((a,b)=>b.risco_score-a.risco_score||b.indice_tco2-a.indice_tco2),vis=ord.slice(0,limite);
 el('te-proj').innerHTML=tabela([t('te.r.cProj'),t('te.r.cMineral'),t('te.r.cMun'),t('te.r.cMat'),t('te.r.cRisco'),t('te.r.cArea'),t('te.r.cNativa'),t('te.r.cKt'),t('te.r.cEntorno'),t('te.r.cRedor'),t('te.r.cDado')],
  vis.map(p=>[`<span class="mk-code">${E(p.id)}</span> <b>${E(p.projeto)}</b><div class="mk-note">${E(p.empresa)}</div>`,
   `${E(p.mineral||p.categoria||'—')}<div class="mk-note">${E(p.grupo)}</div>`,E(p.municipio),pill(nomeMat(p.maturidade)),selo(p.risco),
   faixa(p.area_p50,p.area_p05,p.area_p95),fmt(p.nativa_p50),faixa(p.tco2_p50/1e3,p.tco2_p05/1e3,p.tco2_p95/1e3,1),fmt(p.entorno_tco2/1e3,1),pct(p.nativa_share),
   E(tk('te.q.',p.qualidade))]),[5,6,7,8,9]);
 el('te-proj-sub').textContent=t('te.r.mostrando',{n:fmt(vis.length),t:fmt(F.length)});
 el('te-mais').hidden=ord.length<=limite;
 el('te-mais').textContent=t('te.r.mais',{n:fmt(ord.length)})}

function desenharRisco(){const F=filtrados();el('te-r-context').textContent=t('te.r.contexto',{n:fmt(F.length),t:fmt(P.length)});
 desenharMapa(F);tabelaProjetos(F)}

/* ---------- wiring ---------- */
function mostrarAba(nova){aba=nova;
 document.querySelectorAll('#te-tabs [data-te]').forEach(b=>{const on=b.dataset.te===aba;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on))});
 for(const k of['historico','cenarios','risco'])el('te-'+k).hidden=k!==aba;
 el('te-metodo').hidden=aba!=='metodo';
 desenhar()}

async function abrirRisco(){
 if(P){matriz();desenharRisco();return}
 el('te-risco-loading').hidden=false;el('te-risco-corpo').hidden=true;
 try{await carregarProjetos();
  preencher('te-f-grupo',[...new Set(P.map(p=>p.grupo))].sort().map(g=>[g,g]),t('te.r.fTodos'));
  el('te-risco-corpo').hidden=false;if(aba==='risco'){matriz();desenharRisco()}}
 catch(e){carregandoP=null;el('territorio-error').textContent=e.message||t('te.fail')}
 finally{el('te-risco-loading').hidden=true}}

function desenhar(){if(!d)return;
 if(aba==='historico')desenharHistorico();
 if(aba==='cenarios')desenharCenarios();
 if(aba==='risco')abrirRisco()}

function preencher(id,valores,vazio){el(id).innerHTML=`<option value="">${E(vazio)}</option>`+valores.map(([v,n])=>`<option value="${E(v)}">${E(n)}</option>`).join('')}

async function load(){
 el('territorio-error').textContent='';
 try{
  d=montar(dadosDoRelatorio(await (await buscar('relatorio')).text()));
  preencher('te-f-risco',RISCO.map(r=>[r,nomeRisco(r)]),t('te.r.fTodos'));
  preencher('te-f-mat',MAT.map(m=>[m,nomeMat(m)]),t('te.r.fTodas'));
  const refazer=()=>{limite=LISTA;desenharRisco()};
  for(const id of['te-f-risco','te-f-mat','te-f-grupo'])el(id).onchange=refazer;
  let tb;el('te-f-busca').oninput=()=>{clearTimeout(tb);tb=setTimeout(refazer,200)};
  el('te-f-limpar').onclick=()=>{for(const id of['te-f-risco','te-f-mat','te-f-grupo','te-f-busca'])el(id).value='';refazer()};
  el('te-mais').onclick=()=>{limite=Infinity;tabelaProjetos(filtrados())};
  el('te-leg-risco').innerHTML=legenda([...RISCO.map(r=>[nomeRisco(r),COR_RISCO[r]]),[t('te.r.legMina'),COR.mina]]);
  document.querySelectorAll('#te-tabs [data-te]').forEach(b=>b.onclick=()=>mostrarAba(b.dataset.te));
  let timer;addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(()=>{if(!el('territorio-view').hidden&&aba!=='risco')desenhar()},150)});
  tooltip();
  el('territorio-content').hidden=false;
  mostrarAba(aba);
 }catch(e){el('territorio-error').textContent=e.message||t('te.fail')}
 finally{el('territorio-loading').hidden=true}}

window.showTerritorio=()=>{if(loaded){desenhar();return}loaded=true;load()};
})();
