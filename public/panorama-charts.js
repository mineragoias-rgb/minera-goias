/* Panorama: small SVG charts, tables and a municipality map shared by the Panorama cards, with a hover tooltip.
   Charts are drawn at the real pixel width of their card (setWidth), so every text keeps the same FONT size on every chart. */
(()=>{'use strict';
const PALETTE=['#0f6fb0','#c2681b','#0d9488','#b03a55','#8250c4','#d7a43a','#57768b','#5aa9d6'],OTHER='#c3ccd3',RAMP=['#d7e9f6','#a8cde9','#6fa9d4','#3684b9','#07588b'];
const FONT=12,CHAR=FONT*.58,H=290;
let WIDTH=860;
const setWidth=w=>{WIDTH=Math.max(200,Math.round(w||860))};
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=0)=>v==null||!Number.isFinite(v)?'—':I18N.num(v,{maximumFractionDigits:d});
const money=(v,d=2)=>v==null||!Number.isFinite(v)?'—':'R$ '+fmt(v,d);
const clip=(s,n)=>{s=String(s??'');return s.length>n?s.slice(0,Math.max(1,n-1))+'…':s};
function short(v){if(v==null||!Number.isFinite(v))return '—';const a=Math.abs(v);
 if(a>=1e9)return fmt(v/1e9,2)+' '+t('pn.u.bi');if(a>=1e6)return fmt(v/1e6,1)+' '+t('pn.u.mi');if(a>=1e4)return fmt(v/1e3,1)+' '+t('pn.u.k');return fmt(v,a<10?2:0)}
const niceStep=v=>{if(!(v>0))return 1;const p=Math.pow(10,Math.floor(Math.log10(v))),n=v/p;return (n<=1?1:n<=1.5?1.5:n<=2?2:n<=2.5?2.5:n<=3?3:n<=4?4:n<=5?5:n<=7.5?7.5:10)*p};
const niceTop=v=>niceStep(Math.max(v,1e-9)/4)*4;
const empty=()=>`<p class="empty">${E(t('pn.empty'))}</p>`;
const color=(s,j)=>s.color||PALETTE[j%PALETTE.length];
const svg=(w,h,aria)=>`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" font-size="${FONT}" role="img" aria-label="${E(aria||'')}">`;
// Tooltip text for data-tip: one line per part, the first one in bold.
const tip=(...parts)=>parts.filter(p=>p!=null&&p!=='').map(E).join('&#10;');
// Show every k-th x label so labels never overlap at FONT size.
const every=(labels,step)=>Math.max(1,Math.ceil((Math.max(...labels.map(l=>String(l).length))*CHAR+12)/step));
function legend(series){return `<div class="pn-legend">${series.map((s,j)=>`<span><i style="background:${color(s,j)}"></i>${E(s.name)}</span>`).join('')}</div>`}

// Horizontal bars: rows [{label,value,color}]; the whole row answers the hover.
function hbar(rows,o={}){
 rows=rows.filter(r=>r.value>0);if(!rows.length)return empty();
 const f=o.fmt||(v=>fmt(v,1)),W=WIDTH,rowH=26,vals=rows.map(r=>f(r.value));
 const right=Math.min(170,Math.max(...vals.map(v=>v.length))*CHAR+14),left=Math.round(Math.min(280,Math.max(120,W*.3))),w=Math.max(30,W-left-right);
 const h=rows.length*rowH+8,max=niceTop(Math.max(...rows.map(r=>r.value))),chars=Math.floor((left-14)/CHAR);
 let s=svg(W,h,o.aria);
 rows.forEach((r,i)=>{const y=4+i*rowH,bw=r.value/max*w;
  s+=`<g class="pn-row" data-tip="${tip(r.label,vals[i])}"><rect x="0" y="${y}" width="${W}" height="${rowH}" fill="transparent"/>`
   +`<text x="${left-10}" y="${y+17}" text-anchor="end" fill="#34495a">${E(clip(r.label,chars))}</text>`
   +`<rect class="pn-mark" x="${left}" y="${y+5}" width="${bw}" height="${rowH-10}" rx="3" fill="${r.color||o.color||PALETTE[0]}"/>`
   +`<text x="${left+bw+6}" y="${y+17}" fill="#4a6070" font-weight="600">${E(vals[i])}</text></g>`});
 return s+'</svg>'}

function axes(left,right,top,bottom,W,max,axisFmt){let s='';
 for(let k=0;k<=4;k++){const y=bottom-(bottom-top)*k/4;s+=`<line x1="${left}" x2="${W-right}" y1="${y}" y2="${y}" stroke="#e8eef3"/><text x="${left-8}" y="${y+4}" text-anchor="end" fill="#8395a3">${E(axisFmt(max*k/4))}</text>`}
 return s}

// Vertical bars. Stacked: each segment answers the hover with its own value only. Grouped: each bar with its series and value.
function vbar(labels,series,o={}){
 if(!labels.length||!series.length||!series.some(x=>x.values.some(v=>v>0)))return empty();
 const f=o.fmt||(v=>fmt(v,1)),axis=o.axis||short,W=WIDTH,top=16,bottom=H-32,n=labels.length,stacked=!!o.stacked;
 const tot=i=>stacked?series.reduce((a,x)=>a+(x.values[i]||0),0):Math.max(...series.map(x=>x.values[i]||0));
 const max=niceTop(Math.max(...labels.map((_,i)=>tot(i)))),left=Math.max(...[0,1,2,3,4].map(k=>axis(max*k/4).length))*CHAR+16,right=10,step=(W-left-right)/n;
 let s=svg(W,H,o.aria)+axes(left,right,top,bottom,W,max,axis);
 const k=every(labels,step),single=series.length===1;
 labels.forEach((lab,i)=>{const x0=left+i*step,op=o.partial&&o.partial.has(lab)?.55:1;
  if(stacked){let base=bottom;series.forEach((se,j)=>{const v=se.values[i]||0,hh=v/max*(bottom-top);
   if(hh>0){s+=`<rect class="pn-mark" x="${x0+step*.18}" y="${base-hh}" width="${step*.64}" height="${hh}" fill="${color(se,j)}" opacity="${op}" data-tip="${tip(lab,se.name+': '+f(v))}"/>`;base-=hh}})}
  else if(single){const v=series[0].values[i]||0,hh=Math.max(v,0)/max*(bottom-top),txt=short(v);
   s+=`<g class="pn-col" data-tip="${tip(lab,f(v))}"><rect x="${x0}" y="${top}" width="${step}" height="${bottom-top}" fill="transparent"/>`
    +`<rect class="pn-mark" x="${x0+step*.15}" y="${bottom-hh}" width="${step*.7}" height="${hh}" rx="2" fill="${color(series[0],0)}" opacity="${op}"/></g>`;
   if(v>0&&step>=txt.length*CHAR+4)s+=`<text x="${x0+step/2}" y="${bottom-hh-6}" text-anchor="middle" fill="#4a6070" font-weight="600">${E(txt)}</text>`}
  else{const bw=step*.7/series.length;series.forEach((se,j)=>{const v=se.values[i]||0,hh=Math.max(v,0)/max*(bottom-top);
   s+=`<rect class="pn-mark" x="${x0+step*.15+j*bw}" y="${bottom-hh}" width="${bw*.9}" height="${hh}" rx="2" fill="${color(se,j)}" opacity="${op}" data-tip="${tip(lab,se.name+': '+f(v))}"/>`})}
  if(i%k===0)s+=`<text x="${x0+step/2}" y="${bottom+19}" text-anchor="middle" fill="#8395a3">${E(lab)}</text>`});
 return s+'</svg>'+(series.length>1?legend(series):'')}

// Lines: null values break the line; hovering a column shows every series at that point.
function line(labels,series,o={}){
 const all=series.flatMap(x=>x.values).filter(v=>v!=null&&Number.isFinite(v));if(!labels.length||!all.length)return empty();
 const f=o.fmt||(v=>fmt(v,1)),axis=o.axis||short,W=WIDTH,top=16,bottom=H-32,n=labels.length,max=niceTop(Math.max(...all,0));
 const left=Math.max(...[0,1,2,3,4].map(k=>axis(max*k/4).length))*CHAR+16,right=14,step=n>1?(W-left-right-20)/(n-1):40;
 let s=svg(W,H,o.aria)+axes(left,right,top,bottom,W,max,axis);
 const X=i=>left+10+i*step,Y=v=>bottom-v/max*(bottom-top),ok=v=>v!=null&&Number.isFinite(v),k=every(labels,step);
 series.forEach((se,j)=>{let d='',pen=false;se.values.forEach((v,i)=>{if(!ok(v)){pen=false;return}d+=(pen?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1);pen=true});
  s+=`<path d="${d}" fill="none" stroke="${color(se,j)}" stroke-width="2.2"/>`;
  se.values.forEach((v,i)=>{if(ok(v))s+=`<circle cx="${X(i)}" cy="${Y(v)}" r="${n>30?2:3}" fill="${color(se,j)}"/>`})});
 labels.forEach((lab,i)=>{
  s+=`<g class="pn-col" data-tip="${tip(lab,...series.map(se=>(series.length>1?se.name+': ':'')+(ok(se.values[i])?f(se.values[i]):'—')))}">`
   +`<rect x="${X(i)-step/2}" y="${top}" width="${step}" height="${bottom-top}" fill="transparent"/><line class="pn-guide" x1="${X(i)}" x2="${X(i)}" y1="${top}" y2="${bottom}"/></g>`;
  if(i%k===0)s+=`<text x="${X(i)}" y="${bottom+19}" text-anchor="middle" fill="#8395a3">${E(lab)}</text>`});
 return s+'</svg>'+(series.length>1?legend(series):'')}

// Table with "show all": cols [{label,key|get,fmt,num}], rows of objects.
function table(box,cols,rows,o={}){const base=o.limit||10;let limit=base;
 const draw=()=>{const head=cols.map(c=>`<th${c.num?' class="num"':''}>${E(c.label)}</th>`).join('');
  const body=rows.slice(0,limit).map(r=>'<tr>'+cols.map(c=>{const v=c.get?c.get(r):r[c.key];return `<td${c.num?' class="num"':''}>${E(c.fmt?c.fmt(v,r):v)}</td>`}).join('')+'</tr>').join('');
  box.innerHTML=`<div class="table-wrap"><table class="pn-table"><thead><tr>${head}</tr></thead><tbody>${body||`<tr><td colspan="${cols.length}" class="empty">${E(t('pn.empty'))}</td></tr>`}</tbody></table></div>`
   +(rows.length>limit?`<button type="button" class="link-button pn-more">${E(t('pn.showAll',{n:fmt(rows.length)}))}</button>`:limit>base?`<button type="button" class="link-button pn-more">${E(t('pn.showLess'))}</button>`:'');
  const b=box.querySelector('.pn-more');if(b)b.onclick=()=>{limit=limit>base?base:rows.length;draw()}};
 draw()}

// Municipality choropleth drawn from the atlas rings ([lat,lon]); quantile colours of the positive values. No text inside: the legend is HTML.
function map(box,muns,values,o={}){
 let lon0=Infinity,lon1=-Infinity,lat0=Infinity,lat1=-Infinity;
 muns.forEach(m=>m.rings.forEach(r=>r.forEach(([la,lo])=>{if(lo<lon0)lon0=lo;if(lo>lon1)lon1=lo;if(la<lat0)lat0=la;if(la>lat1)lat1=la})));
 const W=560,MH=500,k=Math.cos((lat0+lat1)/2*Math.PI/180),sc=Math.min((W-20)/((lon1-lon0)*k),(MH-20)/(lat1-lat0)),X=lo=>10+(lo-lon0)*k*sc,Y=la=>10+(lat1-la)*sc;
 const f=o.fmt||(v=>fmt(v,1)),vals=[...values.values()].filter(v=>v>0).sort((a,b)=>a-b);
 const cuts=[...new Set([1,2,3,4].map(i=>vals[Math.floor(vals.length*i/5)]).filter(v=>v!=null&&v>vals[0]))];
 const paint=v=>!(v>0)?'#edf1f4':RAMP[cuts.filter(c=>v>=c).length];
 let s=`<svg viewBox="0 0 ${W} ${MH}" class="pn-map" role="img" aria-label="${E(o.aria||'')}">`,sel='';
 muns.forEach(m=>{const v=values.get(m.code),d=m.rings.map(r=>'M'+r.map(([la,lo])=>X(lo).toFixed(1)+' '+Y(la).toFixed(1)).join('L')+'Z').join('');
  const p=`<path class="pn-mark" d="${d}" fill="${paint(v)}" stroke="${m.code===o.selected?'#07345c':'#ffffff'}" stroke-width="${m.code===o.selected?2:.5}" fill-rule="evenodd" data-code="${E(m.code)}" data-tip="${tip(m.name,v>0?f(v):t('pn.noRecord'))}"/>`;
  if(m.code===o.selected)sel=p;else s+=p});
 s+=sel+'</svg>';
 const steps=vals.length?[vals[0],...cuts]:[];
 box.innerHTML=s+`<div class="pn-legend">`+[['#edf1f4',t('pn.noRecord')],...steps.map((c,i)=>[RAMP[i],t('pn.from')+' '+f(c)])].map(([c,l])=>`<span><i style="background:${c}"></i>${E(l)}</span>`).join('')+'</div>';
 if(o.onPick)box.querySelectorAll('path[data-code]').forEach(p=>{p.style.cursor='pointer';p.onclick=()=>o.onPick(p.dataset.code)})}

const tiles=items=>items.map(([tone,label,value,note])=>`<div class="metric ${tone}"><span>${E(label)}</span><strong>${E(value)}</strong><small>${E(note)}</small></div>`).join('');

// One tooltip for the whole Panorama: follows the pointer over any [data-tip] mark; a tap shows it on touch screens.
function tooltip(){const box=document.createElement('div');box.className='pn-tip';box.setAttribute('role','tooltip');box.hidden=true;document.body.append(box);
 const target=e=>e.target&&e.target.closest?e.target.closest('#panorama-view [data-tip],#overview-view [data-tip]'):null;
 const show=(node,x,y)=>{const text=node.getAttribute('data-tip');if(box.textContent!==text)box.textContent=text;box.hidden=false;
  const r=box.getBoundingClientRect();let left=x+14,top=y+16;if(left+r.width>innerWidth-8)left=x-r.width-14;if(top+r.height>innerHeight-8)top=y-r.height-12;
  box.style.left=Math.max(8,left)+'px';box.style.top=Math.max(8,top)+'px'};
 document.addEventListener('mousemove',e=>{const n=target(e);if(n)show(n,e.clientX,e.clientY);else if(!box.hidden)box.hidden=true});
 document.addEventListener('click',e=>{const n=target(e);if(n)show(n,e.clientX,e.clientY);else box.hidden=true},true);
 addEventListener('scroll',()=>{box.hidden=true},true)}
tooltip();

window.PNC={E,fmt,money,short,clip,hbar,vbar,line,table,map,tiles,empty,setWidth,FONT,PALETTE,OTHER};
})();
