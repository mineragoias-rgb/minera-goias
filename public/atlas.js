/* Leaflet atlas: artifact snapshot, never blended with the live MySQL dashboard. */
(()=>{'use strict';
const el=id=>document.getElementById(id),fmt=(v,d=0)=>v==null?t('at.noRecord'):I18N.num(v,{maximumFractionDigits:d}),money=v=>'R$ '+fmt(v,2),escape=esc;
const withUnit=(v,unit)=>v==null?t('at.noRecord'):unit==='R$'?money(v):fmt(v,2)+' '+unit;
const normalize=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase();
const ramp=['#d7e9f6','#a8cde9','#6fa9d4','#3684b9','#07588b'],phaseColors=['#0f6fb0','#c2681b','#0d9488','#b03a55','#8250c4'];
const YEARS=['2022','2023','2024','2025','2026'];
// The consolidated base carries every year for all 246 municipalities, so any
// span can be summed; the full span is what used to be called the accumulated.
function yearRange(){let a=+el('atlas-year-from').value,b=+el('atlas-year-to').value;
 if(a>b)[a,b]=[b,a];return [a,b]}
function rangeYears(){const [a,b]=yearRange();return YEARS.slice(a,b+1)}
function rangeLabel(){const [a,b]=yearRange();
 if(a===0&&b===YEARS.length-1)return t('at.accum');
 return a===b?YEARS[a]:YEARS[a]+t('at.rangeJoin')+YEARS[b]}
let selectedCode='',highlight=null;
let packet,map,layers,municipalLayers=[],processPacket,processRecords,processLayers=[],loadingPromise,rows=[],visibleRows=[],limit=50,renderVersion=0,layer='cfem',catLayer='',minLayer='';
const bounds=[[-19.4981,-53.2485],[-12.3954,-45.9072]];
const CLASS_COLORS={'provável':'#0f6fb0','possível':'#0d9488','sinal':'#9aa9b4'},IMP_COLORS={'Depósito':'#c2681b','Ocorrência':'#8250c4','Indício':'#b03a55','Indeterminado':'#d3b88f'};
function classLabel(c){return ({'provável':t('at.class.probable'),'possível':t('at.class.possible'),'sinal':t('at.class.signal')})[c]||c}
function stageLabel(s){return ({lavra_autorizada_sem_producao:t('at.stage.mining'),requerimento_de_lavra:t('at.stage.miningRequest'),direito_de_requerer_lavra:t('at.stage.rightToRequest'),requerimento_de_licenciamento_ou_lavra_garimpeira:t('at.stage.licensing')})[s]||s}
function importanceLabel(v){return ({'Depósito':t('at.imp.deposit'),'Ocorrência':t('at.imp.occurrence'),'Indício':t('at.imp.showing'),'Indeterminado':t('at.imp.undetermined')})[v]||v}
function pointRows(key){const p=packet[key]||{cols:[],rows:[]};return p.rows.map(r=>Object.fromEntries(p.cols.map((c,i)=>[c,r[i]])))}
// Energy, intensity, projects and occurrences are cut by mineral instead of by municipality.
const MINERAL_LAYERS=['energy','coefficient','projects','occurrences'];
function mineralsOf(key,x){if(key==='projects')return [x.mineral];if(key==='occurrences')return String(x.substancias||'').split(';').map(s=>s.trim()).filter(Boolean);return x&&x.sub?[x.sub]:[]}
function mineralOptions(){if(minLayer===layer)return;minLayer=layer;const select=el('atlas-minfilter'),current=select.value,counts=new Map(),items=layer==='projects'||layer==='occurrences'?pointRows(layer):packet.energy;
 items.forEach(x=>new Set(mineralsOf(layer,x)).forEach(m=>counts.set(m,(counts.get(m)||0)+1)));
 select.innerHTML=`<option value="">${escape(t('at.allMinerals'))}</option>`+[...counts.keys()].sort((a,b)=>a.localeCompare(b,'pt')).map(m=>`<option value="${escape(m)}">${escape(m)} (${escape(fmt(counts.get(m)))})</option>`).join('');
 select.value=counts.has(current)?current:''}
function countBy(key,code){const p=packet[key];if(!p)return 0;const i=p.cols.indexOf('mun');return p.rows.reduce((s,r)=>s+(String(r[i])===code?1:0),0)}
function detail(title,entries){el('atlas-detail-title').textContent=title;el('atlas-detail-body').innerHTML='<dl>'+entries.map(([k,v])=>`<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`).join('')+'</dl>'}
function rampScale(vals){const values=vals.filter(v=>Number.isFinite(v)&&v>0).sort((a,b)=>a-b);const cuts=[...new Set([1,2,3,4].map(i=>values[Math.floor(values.length*i/5)]).filter(v=>v>values[0]))];return {cuts,min:values[0],color:v=>v==null||v<=0?'#edf1f4':ramp[cuts.filter(x=>v>=x).length]}}
function legend(items){el('atlas-legend').innerHTML=items.map(([label,color])=>`<div class="legend-item"><span class="legend-swatch" style="background:${color}"></span><span>${escape(label)}</span></div>`).join('')}
function selectedMunicipality(m,record){const target=municipalLayers.find(x=>x.code===m.code);if(target){target.shape.openTooltip();map.fitBounds(target.shape.getBounds(),{maxZoom:10,padding:[30,30]})}detail(m.name,[[t('at.ibge'),m.code],...record.detail]);}
async function init(){packet=await api('/atlas');if(!window.L)throw Error(t('at.leafletFail'));el('atlas-content').hidden=false;map=L.map('atlas-map',{preferCanvas:true,scrollWheelZoom:true,minZoom:5,maxZoom:14,zoomSnap:.25}).fitBounds(bounds);L.control.scale({imperial:false}).addTo(map);const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'});tiles.on('tileerror',()=>{el('atlas-error').textContent=t('at.tileFail')});tiles.addTo(map);layers=L.layerGroup().addTo(map);
el('atlas-mineral').innerHTML=packet.production.subs.map(s=>`<option>${escape(s.sub)}</option>`).join('');
el('atlas-mun').innerHTML=`<option value="">${escape(t('at.selectMunicipality'))}</option>`+[...packet.municipalities].sort((a,b)=>a.name.localeCompare(b.name,'pt')).map(m=>`<option value="${escape(m.code)}">${escape(m.name)}</option>`).join('');
yearLabel();
el('atlas-layer').onchange=render;for(const id of ['atlas-year-from','atlas-year-to']){
 el(id).oninput=yearLabel;el(id).onchange=()=>{yearLabel();render()}}el('atlas-mun').onchange=()=>{selectMun(el('atlas-mun').value);if(['projects','occurrences'].includes(layer))render()};el('mun-clear').onclick=()=>{selectMun('');if(['projects','occurrences'].includes(layer))render()};el('atlas-mineral').onchange=render;el('atlas-group').onchange=render;el('atlas-cat').onchange=render;el('atlas-minfilter').onchange=render;el('atlas-search').oninput=()=>{limit=50;filterRows()};el('atlas-more').onclick=()=>{limit+=50;table()};el('atlas-reset').onclick=()=>map.fitBounds(bounds);el('atlas-export').onclick=exportRows;
el('atlas-content').hidden=false;map.invalidateSize();map.fitBounds(bounds,{padding:[15,15]});await render();}
window.showAtlas=async()=>{el('atlas-error').textContent='';try{if(!loadingPromise){loadingPromise=init().catch(e=>{if(map){map.remove();map=null}loadingPromise=null;throw e})}await loadingPromise;requestAnimationFrame(()=>map.invalidateSize())}catch(e){el('atlas-error').textContent=e.message}finally{el('atlas-loading').hidden=true}};
async function getProcesses(){if(processRecords)return;const decoded=await window.loadProcesses();processPacket=decoded.packet;processRecords=decoded.records;
el('atlas-group').innerHTML=`<option value="">${escape(t('at.allGroups'))}</option>`+processPacket.grupos.map((g,i)=>`<option value="${i}">${escape(g)}</option>`).join('');}
async function render(){const version=++renderVersion;layer=el('atlas-layer').value;limit=50;el('atlas-search').value='';el('atlas-error').textContent='';el('atlas-detail-title').textContent=t('at.selectRecord');el('atlas-detail-body').innerHTML='';layers.clearLayers();if(highlight)highlight.bringToFront();municipalLayers=[];processLayers=[];rows=[];visibleRows=[];table();el('atlas-year-wrap').hidden=layer!=='cfem';el('atlas-mineral-wrap').hidden=layer!=='production';el('atlas-group-wrap').hidden=layer!=='processes';el('atlas-cat-wrap').hidden=!['projects','occurrences'].includes(layer);const byMineral=MINERAL_LAYERS.includes(layer);el('atlas-minfilter-wrap').hidden=!byMineral;if(byMineral)mineralOptions();const minSel=byMineral?el('atlas-minfilter').value:'';el('atlas-scale-note').textContent=t('at.quantileNote');
try{if(layer==='processes'){el('atlas-context').textContent=t('at.loadingPolys');await getProcesses();if(version!==renderVersion)return;const group=el('atlas-group').value;const selected=processRecords.filter(p=>group===''||String(p.group)===group);legend(processPacket.grupos.map((g,i)=>[g,phaseColors[i]]));el('atlas-scale-note').textContent=t('at.processNote');
for(let i=0;i<selected.length;i++){const p=selected[i];const shape=L.polygon(p.rings,{color:phaseColors[p.group],weight:.7,fillColor:phaseColors[p.group],fillOpacity:.32,fillRule:'evenodd'}).addTo(layers);const record={name:p.id,cells:[p.id,p.phase,p.mineral,fmt(p.area,2)+' ha'],detail:[[t('at.process'),p.id],[t('at.phase'),p.phase],[t('at.substance'),p.mineral],[t('at.areaDeclared'),fmt(p.area,2)+' ha'],[t('at.extractDate'),packet.meta.periods.processes||t('at.notInArtefact')]],shape};shape.on('click',()=>detail(t('at.processLabel',{id:p.id}),record.detail));rows.push(record);processLayers.push(shape);if(i%400===0){await new Promise(r=>requestAnimationFrame(r));if(version!==renderVersion)return}}
el('atlas-context').textContent=t('at.polyContext',{n:fmt(rows.length)});el('atlas-table-title').textContent=t('at.radarTitle');el('atlas-table-head').innerHTML=`<tr><th>${escape(t('at.process'))}</th><th>${escape(t('at.phase'))}</th><th>${escape(t('at.thSubstance'))}</th><th>${escape(t('at.thArea'))}</th></tr>`;
}else if(layer==='projects'||layer==='occurrences'){const projects=layer==='projects',colors=projects?CLASS_COLORS:IMP_COLORS,field=projects?'classe':'importancia',label=projects?classLabel:importanceLabel,items=pointRows(layer).filter(x=>(minSel===''||mineralsOf(layer,x).includes(minSel))&&(selectedCode===''||String(x.mun)===selectedCode)),munName=new Map(packet.municipalities.map(m=>[m.code,m.name])),count=k=>items.filter(x=>x[field]===k).length;
{const keep=catLayer===layer?el('atlas-cat').value:'';catLayer=layer;el('atlas-cat-label').textContent=projects?t('at.filterClass'):t('at.filterImportance');el('atlas-cat').innerHTML=`<option value="">${escape(t('at.allCategories'))}</option>`+Object.keys(colors).map(k=>`<option value="${escape(k)}">${escape(label(k))} (${escape(fmt(count(k)))})</option>`).join('');el('atlas-cat').value=keep}
const cat=el('atlas-cat').value;legend(Object.keys(colors).map(k=>[label(k)+' · '+fmt(count(k)),colors[k]]));el('atlas-scale-note').textContent=projects?t('at.projectNote'):t('at.occurrenceNote');
items.filter(x=>cat===''||x[field]===cat).forEach(x=>{const color=colors[x[field]]||'#8395a3',mun=munName.get(String(x.mun))||t('at.notInformed'),name=projects?x.mineral+' · '+x.processo:(x.local||x.id);
const shape=projects?L.circleMarker([x.lat,x.lon],{radius:5,color:x.brownfield?'#07345c':'#ffffff',weight:x.brownfield?2:1,fillColor:color,fillOpacity:.9}):L.marker([x.lat,x.lon],{icon:L.divIcon({className:'occ-icon',html:`<span style="background:${color}"></span>`,iconSize:[12,12]}),keyboard:false});shape.addTo(layers);shape.bindTooltip(escape(name));
const record={name,shape,cells:projects?[name,mun,classLabel(x.classe),stageLabel(x.estagio)]:[name,x.substancias||t('at.notInformed'),mun,importanceLabel(x.importancia)],
detail:projects?[[t('at.project'),x.id],[t('at.holder'),x.titular||t('at.holderHidden')],[t('at.substance'),x.mineral],[t('at.thMun'),mun],[t('at.maturity'),classLabel(x.classe)],[t('at.stage'),stageLabel(x.estagio)],[t('at.brownfield'),x.brownfield?t('at.yes'):t('at.no')],[t('at.claims'),fmt(x.processos)+' · '+x.processo],[t('at.areaHa'),fmt(x.area_ha,2)+' ha'],[t('at.evidence'),x.evidencia||t('at.noRecord')]]
:[[t('at.occurrence'),x.id],[t('at.substances'),x.substancias||t('at.notInformed')],[t('at.thMun'),mun],[t('at.importance'),importanceLabel(x.importancia)],[t('at.economicStatus'),x.status||t('at.notInformed')],[t('at.utilityClass'),x.classe_util||t('at.notInformed')],[t('at.positioning'),x.posicionamento||t('at.notInformed')],[t('at.anmOverlap'),x.categoria_anm||t('at.none')],[t('at.registered'),x.cadastro||t('at.noRecord')]]};
shape.on('click',()=>detail(name,record.detail));rows.push(record)});
el('atlas-context').textContent=(projects?t('at.projectsContext',{n:fmt(rows.length)}):t('at.occurrencesContext',{n:fmt(rows.length)}))+(minSel?' · '+minSel:'')+(selectedCode?' · '+(munName.get(selectedCode)||selectedCode):'');el('atlas-table-title').textContent=projects?t('at.projectsTitle'):t('at.occurrencesTitle');
el('atlas-table-head').innerHTML=projects?`<tr><th>${escape(t('at.project'))}</th><th>${escape(t('at.thMun'))}</th><th>${escape(t('at.maturity'))}</th><th>${escape(t('at.stage'))}</th></tr>`:`<tr><th>${escape(t('at.occurrence'))}</th><th>${escape(t('at.substances'))}</th><th>${escape(t('at.thMun'))}</th><th>${escape(t('at.importance'))}</th></tr>`;
}else if(layer==='dams'){legend([[t('at.riskHigh'),'#b03a55'],[t('at.riskMed'),'#c2681b'],[t('at.riskLow'),'#0f6fb0']]);el('atlas-scale-note').textContent=t('at.damNote');packet.dams.forEach(d=>{const risk=d['Categoria de Risco - CRI'],color=/alta/i.test(risk)?'#b03a55':/média/i.test(risk)?'#c2681b':'#0f6fb0';const shape=L.circleMarker([d.lat,d.lon],{radius:8,color:'#fff',weight:2,fillColor:color,fillOpacity:1}).addTo(layers);shape.bindTooltip(escape(d.Nome));const record={name:d.Nome,cells:[d.Nome,d['Município'],risk,d['Dano Potencial Associado - DPA']],shape,detail:[[t('at.thMun'),d['Município']],[t('at.thRisk'),risk],[t('at.thDamage'),d['Dano Potencial Associado - DPA']],[t('at.emergency'),d['Nível de Emergência']],[t('at.operation'),d['Situação Operacional']],[t('at.refDate'),t('at.notInArtefact')]]};shape.on('click',()=>detail(d.Nome,record.detail));rows.push(record)});el('atlas-context').textContent=t('at.damsContext');el('atlas-table-title').textContent=t('at.damsTitle');el('atlas-table-head').innerHTML=`<tr><th>${escape(t('at.thDam'))}</th><th>${escape(t('at.thMun'))}</th><th>${escape(t('at.thRisk'))}</th><th>${escape(t('at.thDamage'))}</th></tr>`;
}else{const years=rangeYears(),whole=years.length===YEARS.length,sub=el('atlas-mineral').value,gold=['OURO','MINÉRIO DE OURO'].includes(sub),unit=layer==='cfem'?'R$':layer==='production'?(gold?t('at.unitGold'):t('at.unitTons')):layer==='energy'?'GWh':'kWh/t';const cfem=new Map(packet.cfem.linhas.map(x=>[normalize(x['Município']),x])),energy=new Map(packet.energy.map(x=>[x.cod,x]));
rows=packet.municipalities.filter(m=>minSel===''||energy.get(m.code)?.sub===minSel).map(m=>{const e=energy.get(m.code),p=packet.production.dados[sub]?.[m.code];let value=null,note='',details=[];
if(layer==='cfem'){const source=cfem.get(normalize(m.name));
  if(whole)value=m.cfem_total;
  else if(source){const present=years.filter(y=>Object.hasOwn(source,y));
   value=present.length?present.reduce((sum,y)=>sum+source[y],0):null}
  else value=null;
  note=rangeLabel()+(years.includes('2026')?' · '+t('at.partial2026'):'');details=[[t('at.cfemCollected'),value==null?t('at.noRecord'):money(value)],[t('at.periodField'),note]]}
if(layer==='production'){value=p?p[0]*(gold?1000:1):null;note=sub;details=[[t('at.substance'),sub],[t('at.qtySold'),withUnit(value,unit)],[t('at.cfem'),p?money(p[1]):t('at.noRecord')],[t('at.companies'),p?fmt(p[2]):t('at.noRecord')],[t('at.periodField'),'2025']]}
if(layer==='energy'){value=e&&e.mwh>0?e.mwh/1000:null;note=e?.classe||t('at.noRecord');details=[[t('at.energyChain'),value==null?t('at.noRecord'):fmt(value,2)+' GWh'],[t('at.artefactClass'),note],[t('mun.mainSub'),e?.sub||t('at.noRecord')],[t('at.periodField'),'2025']]}
if(layer==='coefficient'){value=e?.classe==='comparavel'&&e.kwh_t>0?e.kwh_t:null;note=e?.classe||t('at.noRecord');details=[[t('at.artefactClass'),note],[t('mun.mainSub'),e?.sub||t('at.noRecord')],[t('at.coefficient'),e?.classe==='ouro'&&e.mwh_kg!=null?fmt(e.mwh_kg,2)+' MWh/'+t('at.unitGold'):value!=null?fmt(value,2)+' kWh/t':t('at.notComparable')],[t('at.periodField'),'2025'],[t('at.limitLabel'),t('at.limitNote')]]}
return {name:m.name,cells:[m.name,withUnit(value,unit),note],value,detail:details,municipality:m}});
const scale=rampScale(rows.map(r=>r.value)),special={'ouro':'#d7a43a','planta sem lavra local':'#ad80b2','quantidade declarada inconsistente':'#cf6870'};
rows.forEach(r=>{const shape=L.polygon(r.municipality.rings,{weight:.7,color:'#57768b',fillColor:layer==='coefficient'&&special[r.cells[2]]?special[r.cells[2]]:scale.color(r.value),fillOpacity:.8,fillRule:'evenodd'}).addTo(layers);shape.bindTooltip(escape(r.name));shape.on('click',()=>{detail(r.name,[[t('at.ibge'),r.municipality.code],...r.detail]);selectMun(r.municipality.code)});r.shape=shape;municipalLayers.push({code:r.municipality.code,shape})});
if(layer==='cfem'&&!whole)el('atlas-scale-note').textContent=t('at.cfemYearNote');if(minSel)el('atlas-scale-note').textContent=t('at.quantileNote')+' '+t('at.energyMineralNote');legend([[t('at.noneZero'),'#edf1f4'],...[scale.min,...scale.cuts].filter(v=>v!=null).map((v,i)=>[t('at.from')+' '+withUnit(v,unit),ramp[i]]),...(layer==='coefficient'?Object.entries(special):[])]);
el('atlas-context').textContent=layer==='cfem'?t('at.cfemPrefix')+rangeLabel()+t('at.allMunicipalities'):t('at.ref2025')+(layer==='production'?sub:unit)+(minSel?' · '+minSel:'');el('atlas-table-title').textContent=t('at.munIndicators');el('atlas-table-head').innerHTML=`<tr><th>${escape(t('at.thMun'))}</th><th>${escape(t('at.thValue'))} · ${escape(unit)}</th><th>${escape(t('at.thRefClass'))}</th></tr>`;rows.sort((a,b)=>(b.value??-1)-(a.value??-1));}
if(version===renderVersion)filterRows();}catch(e){if(version===renderVersion)el('atlas-error').textContent=e.message}}
function filterRows(){const q=normalize(el('atlas-search').value);visibleRows=rows.filter(r=>normalize(r.cells.join(' ')).includes(q));const selected=new Set(visibleRows);rows.forEach(r=>{if(selected.has(r)){if(!layers.hasLayer(r.shape))layers.addLayer(r.shape)}else layers.removeLayer(r.shape)});table()}
function table(){el('atlas-count').textContent=t('at.recordsHint',{n:fmt(visibleRows.length)});el('atlas-table-body').innerHTML=visibleRows.slice(0,limit).map((r,i)=>`<tr class="atlas-row" tabindex="0" data-record="${i}" aria-label="${escape(t('at.locate',{name:r.name}))}">${r.cells.map(c=>'<td>'+escape(c)+'</td>').join('')}</tr>`).join('')||`<tr><td colspan="4">${escape(t('at.noneInCut'))}</td></tr>`;el('atlas-more').hidden=visibleRows.length<=limit;el('atlas-table-body').querySelectorAll('[data-record]').forEach(row=>{const activate=()=>{const r=visibleRows[+row.dataset.record];detail(r.name,r.detail);if(r.municipality)selectMun(r.municipality.code);if(r.shape.getBounds)map.fitBounds(r.shape.getBounds(),{maxZoom:11,padding:[30,30]});else map.setView(r.shape.getLatLng(),11);r.shape.openTooltip();el('atlas-map').scrollIntoView({behavior:'smooth',block:'center'})};row.onclick=activate;row.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate()}}})}
// The page is driven by one theme picker (the panorama tab bar), which hands the map the layers
// its theme covers: the map view select only appears when a theme offers more than one.
window.atlasSetLayer=async layers=>{
 await window.showAtlas();
 if(!map)return;
 const choices=layers||[];
 el('atlas-content').hidden=!choices.length;
 if(!choices.length)return;
 el('atlas-layer-wrap').hidden=choices.length<2;
 const select=el('atlas-layer');
 [...select.options].forEach(o=>{o.hidden=!choices.includes(o.value)});
 if(!choices.includes(select.value))select.value=choices[0];
 await render();
 map.invalidateSize()};

// The radar links straight to a claim: open the claims layer and leave that polygon alone on the map.
window.atlasShowProcess=async id=>{
 if(window.showPanoramaTab)await window.showPanoramaTab('pesquisa');
 await window.showAtlas();
 if(!map)return;
 el('atlas-layer').value='processes';
 await render();
 el('atlas-search').value=id;
 filterRows();
 const record=visibleRows.find(r=>r.name===id);
 if(!record)return;
 detail(t('at.processLabel',{id:record.name}),record.detail);
 map.fitBounds(record.shape.getBounds(),{maxZoom:12,padding:[30,30]});
 el('atlas-map').scrollIntoView({behavior:'smooth',block:'center'})};
function exportRows(){const heads=[...el('atlas-table-head').querySelectorAll('th')].map(t=>t.textContent),safe=x=>'"'+String(x??'').replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';const text=[[t('at.csvSource'),t('at.csvArtefact')],['SHA256',packet.meta.sha256],[t('at.csvLayer'),layer],[t('at.csvRef'),el('atlas-context').textContent],heads,...visibleRows.map(r=>r.cells)].map(r=>r.map(safe).join(';')).join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff'+text],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='minera-goias-atlas-'+layer+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
// The two points share one track and may cross: yearRange orders them, so either point can move either way.
function yearLabel(){
 el('atlas-year-label').textContent=rangeLabel();
 const [a,b]=yearRange(),ticks=el('atlas-year-ticks'),last=YEARS.length-1,fill=el('atlas-year-fill');
 fill.style.left=a/last*100+'%';fill.style.right=(last-b)/last*100+'%';
 if(!ticks.children.length){ticks.innerHTML=YEARS.map((y,i)=>`<button type="button" data-year-index="${i}">${escape(y)}</button>`).join('');
  ticks.style.gridTemplateColumns=`1fr repeat(${last-1},2fr) 1fr`}
 [...ticks.children].forEach((button,i)=>{const inside=i>=a&&i<=b;
  button.classList.toggle('active',inside);
  button.classList.toggle('edge',i===a||i===b);
  button.setAttribute('aria-pressed',String(inside));
  // Clicking a year narrows the span to that single year.
  button.onclick=()=>{el('atlas-year-from').value=i;el('atlas-year-to').value=i;yearLabel();render()}})}
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
       energy?.sub?t('mun.mainSub')+': '+energy.sub:t('mun.energySub'))+
  tile('tone-a',t('mun.projects'),fmt(countBy('projects',m.code)),t('mun.projectsSub'))+
  tile('tone-c',t('mun.occurrences'),fmt(countBy('occurrences',m.code)),t('mun.occurrencesSub'));
 el('mun-subs').innerHTML=subs.length
  ?`<table><thead><tr><th>${escape(t('mun.thSub'))}</th><th>${escape(t('mun.thQty'))}</th><th>${escape(t('mun.thCfem'))}</th><th>${escape(t('mun.thCompanies'))}</th></tr></thead><tbody>`
   +subs.map(x=>`<tr><td>${escape(x.sub)}</td><td>${escape(fmt(x.ton,2))}</td><td>${escape(money(x.cfem))}</td><td>${escape(fmt(x.firms))}</td></tr>`).join('')
   +`</tbody><tfoot><tr><td>${escape(t('mun.production'))}</td><td>${escape(fmt(tons,2))}</td><td></td><td></td></tr></tfoot></table>`
  :`<p class="empty">${escape(t('mun.noSubs'))}</p>`;
 el('mun-dams').innerHTML=dams.length
  ?dams.map(d=>{const risk=d['Categoria de Risco - CRI'],color=/alta/i.test(risk)?'#b03a55':/média/i.test(risk)?'#c2681b':'#0f6fb0';
    return `<div class="mun-dam" style="border-left-color:${color}"><b>${escape(d.Nome)}</b><span>${escape(t('mun.damRisk',{risk,damage:d['Dano Potencial Associado - DPA']}))}</span></div>`}).join('')
  :`<p class="empty">${escape(t('mun.noDams'))}</p>`;
 }
function selectMun(code,scroll=true){
 if(highlight){map.removeLayer(highlight);highlight=null}
 const m=code?packet.municipalities.find(x=>x.code===code):null;
 if(!m){selectedCode='';el('atlas-mun').value='';el('mun-profile').hidden=true;syncPanorama('');return}
 profile(m);
 // The outline stays visible on every layer, including claims and dams.
 highlight=L.polygon(m.rings,{color:'#07345c',weight:2,fill:false,dashArray:'5 4',interactive:false}).addTo(map);
 map.fitBounds(highlight.getBounds(),{maxZoom:10,padding:[30,30]});
 syncPanorama(m.code);
 if(scroll)el('mun-profile').scrollIntoView({behavior:'smooth',block:'start'})}
// The map selection is the page's geographic scope: the panorama below follows it, and the
// panorama's own municipality select comes back this way. The flag keeps the two from bouncing.
let syncing=false;
function syncPanorama(code){if(syncing||!window.panoramaPickMun)return;
 syncing=true;try{window.panoramaPickMun(code)}finally{syncing=false}}
window.atlasSelectMun=code=>{if(syncing)return;syncing=true;try{selectMun(code,false)}finally{syncing=false}};
})();
