/* Leaflet atlas: artifact snapshot, never blended with the live MySQL dashboard. */
(()=>{'use strict';
const el=id=>document.getElementById(id),fmt=(v,d=0)=>v==null?t('at.noRecord'):I18N.num(v,{maximumFractionDigits:d}),money=v=>'R$ '+fmt(v,2),escape=esc;
const withUnit=(v,unit)=>v==null?t('at.noRecord'):unit==='R$'?money(v):fmt(v,2)+' '+unit;
const VIZ={blue:'#0f6fb0',blueSoft:'#93b7cd'};
const niceStep=v=>{if(!(v>0))return 1;const p=Math.pow(10,Math.floor(Math.log10(v))),n=v/p;return (n<=1?1:n<=1.5?1.5:n<=2?2:n<=2.5?2.5:n<=3?3:n<=4?4:n<=5?5:n<=7.5?7.5:10)*p};const niceTop=v=>niceStep(Math.max(v,Number.MIN_VALUE)/4)*4;
const barPath=(x,y,w,h,r)=>{if(h<=0)return '';const rr=Math.min(r,w/2,h);return `M${x} ${y+h}V${y+rr}a${rr} ${rr} 0 0 1 ${rr} ${-rr}h${w-2*rr}a${rr} ${rr} 0 0 1 ${rr} ${rr}V${y+h}Z`};
const normalize=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase();
const ramp=['#d7e9f6','#a8cde9','#6fa9d4','#3684b9','#07588b'],phaseColors=['#0f6fb0','#c2681b','#0d9488','#b03a55','#8250c4'];
const YEARS=['total','2022','2023','2024','2025','2026'];const yearValue=()=>YEARS[+el('atlas-year').value]||'total';
let selectedCode='',highlight=null;
let packet,map,layers,municipalLayers=[],processPacket,processRecords,processLayers=[],loadingPromise,rows=[],visibleRows=[],limit=50,renderVersion=0,layer='cfem';
const bounds=[[-19.4981,-53.2485],[-12.3954,-45.9072]];
function detail(title,entries){el('atlas-detail-title').textContent=title;el('atlas-detail-body').innerHTML='<dl>'+entries.map(([k,v])=>`<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`).join('')+'</dl>'}
function rampScale(vals){const values=vals.filter(v=>Number.isFinite(v)&&v>0).sort((a,b)=>a-b);const cuts=[...new Set([1,2,3,4].map(i=>values[Math.floor(values.length*i/5)]).filter(v=>v>values[0]))];return {cuts,min:values[0],color:v=>v==null||v<=0?'#edf1f4':ramp[cuts.filter(x=>v>=x).length]}}
function legend(items){el('atlas-legend').innerHTML=items.map(([label,color])=>`<div class="legend-item"><span class="legend-swatch" style="background:${color}"></span><span>${escape(label)}</span></div>`).join('')}
function selectedMunicipality(m,record){const target=municipalLayers.find(x=>x.code===m.code);if(target){target.shape.openTooltip();map.fitBounds(target.shape.getBounds(),{maxZoom:10,padding:[30,30]})}detail(m.name,[[t('at.ibge'),m.code],...record.detail]);}
async function init(){packet=await api('/atlas');if(!window.L)throw Error(t('at.leafletFail'));el('atlas-content').hidden=false;map=L.map('atlas-map',{preferCanvas:true,scrollWheelZoom:false,minZoom:5,maxZoom:14,zoomSnap:.25}).fitBounds(bounds);L.control.scale({imperial:false}).addTo(map);const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'});tiles.on('tileerror',()=>{el('atlas-error').textContent=t('at.tileFail')});tiles.addTo(map);layers=L.layerGroup().addTo(map);
el('atlas-mineral').innerHTML=packet.production.subs.map(s=>`<option>${escape(s.sub)}</option>`).join('');
el('atlas-mun').innerHTML=`<option value="">${escape(t('at.selectMunicipality'))}</option>`+[...packet.municipalities].sort((a,b)=>a.name.localeCompare(b.name,'pt')).map(m=>`<option value="${escape(m.code)}">${escape(m.name)}</option>`).join('');
yearLabel();
el('atlas-layer').onchange=render;el('atlas-year').oninput=yearLabel;el('atlas-year').onchange=()=>{yearLabel();render()};el('atlas-mun').onchange=()=>selectMun(el('atlas-mun').value);el('mun-clear').onclick=()=>selectMun('');el('atlas-mineral').onchange=render;el('atlas-group').onchange=render;el('atlas-search').oninput=()=>{limit=50;filterRows()};el('atlas-more').onclick=()=>{limit+=50;table()};el('atlas-reset').onclick=()=>map.fitBounds(bounds);el('atlas-export').onclick=exportRows;el('atlas-series').onchange=series;
el('atlas-content').hidden=false;map.invalidateSize();map.fitBounds(bounds,{padding:[15,15]});await render();series();}
window.showAtlas=async()=>{el('atlas-error').textContent='';try{if(!loadingPromise){loadingPromise=init().catch(e=>{if(map){map.remove();map=null}loadingPromise=null;throw e})}await loadingPromise;requestAnimationFrame(()=>map.invalidateSize())}catch(e){el('atlas-error').textContent=e.message}finally{el('atlas-loading').hidden=true}};
async function getProcesses(){if(processRecords)return;processPacket=await api('/atlas/processes');const p=processPacket,decode=(s,T)=>{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new T(b.buffer)},xy=decode(p.xy,Uint16Array),rs=decode(p.ringStart,Uint32Array),rp=decode(p.ringPoly,Uint16Array),gr=decode(p.g,Uint8Array),fa=decode(p.fase,Uint8Array),su=decode(p.subs,Uint16Array),ar=decode(p.area,Float32Array),ids=p.processo.split('\x01'),b=p.bounds;
processRecords=Array.from({length:p.n},(_,i)=>({id:ids[i],group:gr[i],phase:p.dFase[fa[i]]||t('at.notInformed'),mineral:p.dSubs[su[i]]||t('at.notInformed'),area:ar[i],rings:[]}));
for(let r=0;r<rp.length;r++){const ring=[];for(let i=rs[r];i<rs[r+1];i++)ring.push([b.lat1-xy[2*i+1]/65535*(b.lat1-b.lat0),b.lon0+xy[2*i]/65535*(b.lon1-b.lon0)]);processRecords[rp[r]].rings.push(ring)}
el('atlas-group').innerHTML=`<option value="">${escape(t('at.allGroups'))}</option>`+p.grupos.map((g,i)=>`<option value="${i}">${escape(g)}</option>`).join('');}
async function render(){const version=++renderVersion;layer=el('atlas-layer').value;limit=50;el('atlas-search').value='';el('atlas-error').textContent='';el('atlas-detail-title').textContent=t('at.selectRecord');el('atlas-detail-body').innerHTML='';layers.clearLayers();if(highlight)highlight.bringToFront();municipalLayers=[];processLayers=[];rows=[];visibleRows=[];table();el('atlas-year-wrap').hidden=layer!=='cfem';el('atlas-mineral-wrap').hidden=layer!=='production';el('atlas-group-wrap').hidden=layer!=='processes';el('atlas-scale-note').textContent=t('at.quantileNote');
try{if(layer==='processes'){el('atlas-context').textContent=t('at.loadingPolys');await getProcesses();if(version!==renderVersion)return;const group=el('atlas-group').value;const selected=processRecords.filter(p=>group===''||String(p.group)===group);legend(processPacket.grupos.map((g,i)=>[g,phaseColors[i]]));el('atlas-scale-note').textContent=t('at.processNote');
for(let i=0;i<selected.length;i++){const p=selected[i];const shape=L.polygon(p.rings,{color:phaseColors[p.group],weight:.7,fillColor:phaseColors[p.group],fillOpacity:.32,fillRule:'evenodd'}).addTo(layers);const record={name:p.id,cells:[p.id,p.phase,p.mineral,fmt(p.area,2)+' ha'],detail:[[t('at.process'),p.id],[t('at.phase'),p.phase],[t('at.substance'),p.mineral],[t('at.areaDeclared'),fmt(p.area,2)+' ha'],[t('at.extractDate'),t('at.notInArtefact')]],shape};shape.on('click',()=>detail(t('at.processLabel',{id:p.id}),record.detail));rows.push(record);processLayers.push(shape);if(i%400===0){await new Promise(r=>requestAnimationFrame(r));if(version!==renderVersion)return}}
el('atlas-context').textContent=t('at.polyContext',{n:fmt(rows.length)});el('atlas-table-title').textContent=t('at.radarTitle');el('atlas-table-head').innerHTML=`<tr><th>${escape(t('at.process'))}</th><th>${escape(t('at.phase'))}</th><th>${escape(t('at.thSubstance'))}</th><th>${escape(t('at.thArea'))}</th></tr>`;
}else if(layer==='dams'){legend([[t('at.riskHigh'),'#b03a55'],[t('at.riskMed'),'#c2681b'],[t('at.riskLow'),'#0f6fb0']]);el('atlas-scale-note').textContent=t('at.damNote');packet.dams.forEach(d=>{const risk=d['Categoria de Risco - CRI'],color=/alta/i.test(risk)?'#b03a55':/média/i.test(risk)?'#c2681b':'#0f6fb0';const shape=L.circleMarker([d.lat,d.lon],{radius:8,color:'#fff',weight:2,fillColor:color,fillOpacity:1}).addTo(layers);shape.bindTooltip(escape(d.Nome));const record={name:d.Nome,cells:[d.Nome,d['Município'],risk,d['Dano Potencial Associado - DPA']],shape,detail:[[t('at.thMun'),d['Município']],[t('at.thRisk'),risk],[t('at.thDamage'),d['Dano Potencial Associado - DPA']],[t('at.emergency'),d['Nível de Emergência']],[t('at.operation'),d['Situação Operacional']],[t('at.refDate'),t('at.notInArtefact')]]};shape.on('click',()=>detail(d.Nome,record.detail));rows.push(record)});el('atlas-context').textContent=t('at.damsContext');el('atlas-table-title').textContent=t('at.damsTitle');el('atlas-table-head').innerHTML=`<tr><th>${escape(t('at.thDam'))}</th><th>${escape(t('at.thMun'))}</th><th>${escape(t('at.thRisk'))}</th><th>${escape(t('at.thDamage'))}</th></tr>`;
}else{const year=yearValue(),sub=el('atlas-mineral').value,gold=['OURO','MINÉRIO DE OURO'].includes(sub),unit=layer==='cfem'?'R$':layer==='production'?(gold?t('at.unitGold'):t('at.unitTons')):layer==='energy'?'GWh':'kWh/t';const cfem=new Map(packet.cfem.linhas.map(x=>[normalize(x['Município']),x])),energy=new Map(packet.energy.map(x=>[x.cod,x]));
rows=packet.municipalities.map(m=>{const e=energy.get(m.code),p=packet.production.dados[sub]?.[m.code];let value=null,note='',details=[];
if(layer==='cfem'){const source=cfem.get(normalize(m.name));value=year==='total'?m.cfem_total:source&&Object.hasOwn(source,year)?source[year]:null;note=year==='total'?t('at.accumShort'):source?(year==='2026'?t('at.janJul2026'):year):t('at.noYearDetail');details=[[t('at.cfemCollected'),value==null?t('at.noRecord'):money(value)],[t('at.periodField'),note]]}
if(layer==='production'){value=p?p[0]*(gold?1000:1):null;note=sub;details=[[t('at.substance'),sub],[t('at.qtySold'),withUnit(value,unit)],[t('at.cfem'),p?money(p[1]):t('at.noRecord')],[t('at.companies'),p?fmt(p[2]):t('at.noRecord')],[t('at.periodField'),'2025']]}
if(layer==='energy'){value=e&&e.mwh>0?e.mwh/1000:null;note=e?.classe||t('at.noRecord');details=[[t('at.energyChain'),value==null?t('at.noRecord'):fmt(value,2)+' GWh'],[t('at.artefactClass'),note],[t('at.periodField'),'2025']]}
if(layer==='coefficient'){value=e?.classe==='comparavel'&&e.kwh_t>0?e.kwh_t:null;note=e?.classe||t('at.noRecord');details=[[t('at.artefactClass'),note],[t('at.coefficient'),e?.classe==='ouro'&&e.mwh_kg!=null?fmt(e.mwh_kg,2)+' MWh/'+t('at.unitGold'):value!=null?fmt(value,2)+' kWh/t':t('at.notComparable')],[t('at.periodField'),'2025'],[t('at.limitLabel'),t('at.limitNote')]]}
return {name:m.name,cells:[m.name,withUnit(value,unit),note],value,detail:details,municipality:m}});
const scale=rampScale(rows.map(r=>r.value)),special={'ouro':'#d7a43a','planta sem lavra local':'#ad80b2','quantidade declarada inconsistente':'#cf6870'};
rows.forEach(r=>{const shape=L.polygon(r.municipality.rings,{weight:.7,color:'#57768b',fillColor:layer==='coefficient'&&special[r.cells[2]]?special[r.cells[2]]:scale.color(r.value),fillOpacity:.8,fillRule:'evenodd'}).addTo(layers);shape.bindTooltip(escape(r.name));shape.on('click',()=>{detail(r.name,[[t('at.ibge'),r.municipality.code],...r.detail]);selectMun(r.municipality.code)});r.shape=shape;municipalLayers.push({code:r.municipality.code,shape})});
if(layer==='cfem'&&year!=='total')el('atlas-scale-note').textContent=t('at.cfemYearNote');legend([[t('at.noneZero'),'#edf1f4'],...[scale.min,...scale.cuts].filter(v=>v!=null).map((v,i)=>[t('at.from')+' '+withUnit(v,unit),ramp[i]]),...(layer==='coefficient'?Object.entries(special):[])]);
el('atlas-context').textContent=layer==='cfem'?t('at.cfemPrefix')+(year==='total'?t('at.accumShort'):(year==='2026'?t('at.janJul2026'):year)+t('at.onlyEight')):t('at.ref2025')+(layer==='production'?sub:unit);el('atlas-table-title').textContent=t('at.munIndicators');el('atlas-table-head').innerHTML=`<tr><th>${escape(t('at.thMun'))}</th><th>${escape(t('at.thValue'))} · ${escape(unit)}</th><th>${escape(t('at.thRefClass'))}</th></tr>`;rows.sort((a,b)=>(b.value??-1)-(a.value??-1));}
if(version===renderVersion)filterRows();}catch(e){if(version===renderVersion)el('atlas-error').textContent=e.message}}
function filterRows(){const q=normalize(el('atlas-search').value);visibleRows=rows.filter(r=>normalize(r.cells.join(' ')).includes(q));const selected=new Set(visibleRows);rows.forEach(r=>{if(selected.has(r)){if(!layers.hasLayer(r.shape))layers.addLayer(r.shape)}else layers.removeLayer(r.shape)});table()}
function table(){el('atlas-count').textContent=t('at.recordsHint',{n:fmt(visibleRows.length)});el('atlas-table-body').innerHTML=visibleRows.slice(0,limit).map((r,i)=>`<tr class="atlas-row" tabindex="0" data-record="${i}" aria-label="${escape(t('at.locate',{name:r.name}))}">${r.cells.map(c=>'<td>'+escape(c)+'</td>').join('')}</tr>`).join('')||`<tr><td colspan="4">${escape(t('at.noneInCut'))}</td></tr>`;el('atlas-more').hidden=visibleRows.length<=limit;el('atlas-table-body').querySelectorAll('[data-record]').forEach(row=>{const activate=()=>{const r=visibleRows[+row.dataset.record];detail(r.name,r.detail);if(r.municipality)selectMun(r.municipality.code);if(r.shape.getBounds)map.fitBounds(r.shape.getBounds(),{maxZoom:11,padding:[30,30]});else map.setView(r.shape.getLatLng(),11);r.shape.openTooltip();el('atlas-map').scrollIntoView({behavior:'smooth',block:'center'})};row.onclick=activate;row.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate()}}})}
function exportRows(){const heads=[...el('atlas-table-head').querySelectorAll('th')].map(t=>t.textContent),safe=x=>'"'+String(x??'').replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';const text=[[t('at.csvSource'),t('at.csvArtefact')],['SHA256',packet.meta.sha256],[t('at.csvLayer'),layer],[t('at.csvRef'),el('atlas-context').textContent],heads,...visibleRows.map(r=>r.cells)].map(r=>r.map(safe).join(';')).join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff'+text],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='minera-goias-atlas-'+layer+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function yearLabel(){const v=yearValue();el('atlas-year-label').textContent=v==='total'?t('at.accum'):v}
function chartBars(rows,unit,aria){
 if(!rows.length)return '';
 const max=niceTop(Math.max(...rows.map(r=>r.value),1)),step=760/rows.length;
 let svg='<svg viewBox="0 0 820 280" role="img" aria-label="'+escape(aria)+'">';
 for(let i=0;i<5;i++){const y=228-i*48;svg+=`<line x1="62" x2="800" y1="${y}" y2="${y}" stroke="#e8eef3"/><text x="52" y="${y+4}" text-anchor="end" font-size="11" fill="#8395a3">${fmt(max*i/4,1)}</text>`}
 rows.forEach((r,i)=>{const h=r.value/max*192,x=66+i*step,w=step*.62;
  svg+=`<path d="${barPath(x,228-h,w,h,4)}" fill="${r.partial?VIZ.blueSoft:VIZ.blue}"><title>${escape(r.label)}: ${fmt(r.value,2)} ${escape(unit)}</title></path>`;
  svg+=`<text x="${x+w/2}" y="${228-h-7}" text-anchor="middle" font-size="10" fill="#4a6070" font-weight="600">${escape(fmt(r.value,1))}</text>`;
  svg+=`<text x="${x+w/2}" y="252" text-anchor="middle" font-size="11" fill="#8395a3">${escape(r.label)}</text>`});
 return svg+'</svg>'}
function municipalitySubstances(code){
 const out=[];
 for(const sub of Object.keys(packet.production.dados)){const row=packet.production.dados[sub]?.[code];if(row)out.push({sub,ton:row[0],cfem:row[1],firms:row[2]})}
 return out.sort((a,b)=>b.cfem-a.cfem)}
function municipalityDams(name){const key=normalize(name);return packet.dams.filter(d=>normalize(d['Município'])===key)}
function tile(tone,label,value,note){return `<div class="metric ${tone}"><span>${escape(label)}</span><strong>${escape(value)}</strong><small>${escape(note)}</small></div>`}
function profile(m){
 selectedCode=m.code;
 el('atlas-mun').value=m.code;
 el('mun-profile').hidden=false;
 el('mun-name').textContent=m.name;
 el('mun-sub').textContent=t('mun.tag',{code:m.code});
 const energy=packet.energy.find(e=>e.cod===m.code),subs=municipalitySubstances(m.code),dams=municipalityDams(m.name);
 const stateTotal=packet.municipalities.reduce((sum,x)=>sum+(x.cfem_total||0),0);
 const share=stateTotal>0?m.cfem_total/stateTotal*100:0;
 const tons=subs.reduce((sum,x)=>sum+x.ton,0);
 el('mun-metrics').innerHTML=
  tile('tone-a',t('mun.processes'),fmt(m.processes),t('mun.processesSub'))+
  tile('tone-b',t('mun.cfemTotal'),money(m.cfem_total),t('mun.cfemTotalSub'))+
  tile('tone-c',t('mun.share'),fmt(share,2)+' %',t('mun.shareSub'))+
  tile('tone-d',t('mun.energy'),energy&&energy.mwh>0?fmt(energy.mwh/1000,2)+' GWh':t('at.noRecord'),
       energy?.sub?t('mun.mainSub')+': '+energy.sub:t('mun.energySub'));
 el('mun-subs').innerHTML=subs.length
  ?`<table><thead><tr><th>${escape(t('mun.thSub'))}</th><th>${escape(t('mun.thQty'))}</th><th>${escape(t('mun.thCfem'))}</th><th>${escape(t('mun.thCompanies'))}</th></tr></thead><tbody>`
   +subs.map(x=>`<tr><td>${escape(x.sub)}</td><td>${escape(fmt(x.ton,2))}</td><td>${escape(money(x.cfem))}</td><td>${escape(fmt(x.firms))}</td></tr>`).join('')
   +`</tbody><tfoot><tr><td>${escape(t('mun.production'))}</td><td>${escape(fmt(tons,2))}</td><td></td><td></td></tr></tfoot></table>`
  :`<p class="empty">${escape(t('mun.noSubs'))}</p>`;
 el('mun-dams').innerHTML=dams.length
  ?dams.map(d=>{const risk=d['Categoria de Risco - CRI'],color=/alta/i.test(risk)?'#b03a55':/média/i.test(risk)?'#c2681b':'#0f6fb0';
    return `<div class="mun-dam" style="border-left-color:${color}"><b>${escape(d.Nome)}</b><span>${escape(t('mun.damRisk',{risk,damage:d['Dano Potencial Associado - DPA']}))}</span></div>`}).join('')
  :`<p class="empty">${escape(t('mun.noDams'))}</p>`;
 const detailed=packet.cfem.linhas.find(x=>normalize(x['Município'])===normalize(m.name));
 if(detailed){
  const rows=YEARS.slice(1).filter(y=>Object.hasOwn(detailed,y)).map(y=>({label:y,value:detailed[y]/1e6,partial:y==='2026'}));
  el('mun-evo-note').textContent=t('mun.evoAvailable');
  el('mun-evo').innerHTML=chartBars(rows,t('mun.evoUnit'),t('at.chartAria',{title:m.name}));
  el('mun-evo-table').innerHTML=`<table><thead><tr><th>${escape(t('at.thPeriod'))}</th><th>${escape(t('mun.evoUnit'))}</th></tr></thead><tbody>`
   +rows.map(r=>`<tr><td>${escape(r.label)}</td><td>${escape(fmt(r.value,3))}</td></tr>`).join('')+'</tbody></table>';
  el('mun-evo-details').hidden=false;
 }else{
  el('mun-evo-note').textContent=t('mun.evoMissing',{name:m.name});
  el('mun-evo').innerHTML='';
  el('mun-evo-table').innerHTML='';
  el('mun-evo-details').hidden=true;
 }}
function selectMun(code){
 if(highlight){map.removeLayer(highlight);highlight=null}
 const m=code?packet.municipalities.find(x=>x.code===code):null;
 if(!m){selectedCode='';el('atlas-mun').value='';el('mun-profile').hidden=true;return}
 profile(m);
 // The outline stays visible on every layer, including claims and dams.
 highlight=L.polygon(m.rings,{color:'#07345c',weight:2,fill:false,dashArray:'5 4',interactive:false}).addTo(map);
 map.fitBounds(highlight.getBounds(),{maxZoom:10,padding:[30,30]});
 el('mun-profile').scrollIntoView({behavior:'smooth',block:'start'})}
function series(){const key=el('atlas-series').value;
const [label,value,divisor]={cfem_years:['Ano','valor',1e6],cfem_comparable:['Ano','v',1e6],energy_months:['rotulo','consumo_mwh',1000],beneficiated:['ano','venda_rs',1e9],investment:['Ano','TOTAL',1e6]}[key];
const title=t('at.s.'+key+'.title'),note=t('at.s.'+key+'.note'),unit=t('at.s.'+key+'.unit'),seriesRows=packet[key];
el('atlas-chart-title').textContent=title;el('atlas-chart-note').textContent=note;
const max=niceTop(Math.max(...seriesRows.map(r=>r[value]/divisor),1)),step=800/seriesRows.length,dense=seriesRows.length>14;
let svg='<svg viewBox="0 0 900 300" role="img" aria-label="'+escape(t('at.chartAria',{title}))+'">';
for(let i=0;i<5;i++){const y=245-i*52;svg+=`<line x1="65" x2="875" y1="${y}" y2="${y}" stroke="#e8eef3"/><text x="55" y="${y+4}" text-anchor="end" font-size="11" fill="#8395a3">${fmt(max*i/4,1)}</text>`}
seriesRows.forEach((r,i)=>{const h=r[value]/divisor/max*208,x=70+i*step,w=step*.68,partial=String(r[label]).startsWith('2026'),show=!dense||i%3===0;
svg+=`<path d="${barPath(x,245-h,w,h,4)}" fill="${partial?VIZ.blueSoft:VIZ.blue}"><title>${escape(r[label])}: ${fmt(r[value]/divisor,2)} ${escape(unit)}</title></path>`;
if(show)svg+=`<text x="${x+w/2}" y="${245-h-6}" text-anchor="middle" font-size="9.5" fill="#4a6070" font-weight="600">${escape(fmt(r[value]/divisor,1))}</text>`;
if(show)svg+=`<text x="${x+w/2}" y="270" text-anchor="middle" font-size="10" fill="#8395a3">${escape(r[label])}</text>`});
el('atlas-chart').innerHTML=svg+'</svg>';
el('atlas-series-table').innerHTML=`<table><thead><tr><th>${escape(t('at.thPeriod'))}</th><th>${escape(unit)}</th></tr></thead><tbody>`+seriesRows.map(r=>`<tr><td>${escape(r[label])}</td><td>${fmt(r[value]/divisor,3)}</td></tr>`).join('')+'</tbody></table>'}
})();
