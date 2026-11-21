/* Mapa das empresas (aba Empresas): onde cada empresa minera em Goiás e, ao clicar, tudo o que a base tem sobre ela — CFEM, produção
   estimada e coeficiente energético, carga na CCEE, títulos de lavra e pesquisa e notícias. Desenho e comportamento seguem o Mapa
   Mineral (painel lateral, mapa, detalhe à direita, tabela embaixo). Dados: /api/empresas/mapa (scripts/build_mapa_empresas.py) e o
   bloco "estimada" de /api/empresas, que empresas.js já carregou. */
(()=>{'use strict';
const el=id=>document.getElementById(id),E=s=>esc(s);
const num=(v,c=0)=>I18N.num(v,{minimumFractionDigits:c,maximumFractionDigits:c});
const rs=v=>'R$ '+num(v,0);
const curto=v=>v>=1e9?num(v/1e9,1)+' bi':v>=1e6?num(v/1e6,1)+' mi':v>=1e3?num(v/1e3,0)+' mil':num(v,0);
const COR=['#1b7f4b','#0f6fb0','#c2681b','#8395a3'];  // lavra, pesquisa, requerimento, outros
const LIMITE_LISTA=200;
let D=null,map=null,camEmp=null,camProc=null,sel=null,loaded=false;
const F={busca:'',min:-1,mun:-1,grupos:new Set([0,1,2,3]),cfem:false};

const grupoLabel=g=>[t('em.g.lavra'),t('em.g.pesquisa'),t('em.g.requerimento'),t('em.g.outros')][g];
const norm=s=>String(s??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase();
// Processos de cada empresa, montados uma vez; a empresa entra no recorte se tem processo que passa nos filtros ou CFEM no mineral.
let procDe=null;
function preparar(){procDe=new Map();
 D.processos.rows.forEach(r=>{const p={e:r[0],lat:r[1],lon:r[2],fase:r[3],g:r[4],min:r[5],mun:r[6],ha:r[7],proc:r[8],cfem:r[9]};
  if(!procDe.has(p.e))procDe.set(p.e,[]);procDe.get(p.e).push(p)})}
const procOk=p=>F.grupos.has(p.g)&&(F.min<0||p.min===F.min)&&(F.mun<0||p.mun===F.mun);
function noRecorte(x){
 if(F.cfem&&!(x.cfem_total>0))return false;
 if(F.busca&&!(norm(x.nome).includes(F.busca)||String(x.cnpj_raiz).includes(F.busca.replace(/\D/g,'')||'#')))return false;
 const ps=procDe.get(x.i)||[];
 if(F.min<0&&F.mun<0&&F.grupos.size===4)return true;
 return ps.some(procOk);}
const recorte=()=>D.empresas.filter(noRecorte);

// ---------------------------------------------------------------------------------------------------------------- mapa
function iniciarMapa(){
 const b=[[-19.6,-53.3],[-12.3,-45.8]];
 map=L.map('emp-map',{preferCanvas:true,scrollWheelZoom:true,minZoom:5,maxZoom:16,zoomSnap:.25}).fitBounds(b);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
 camEmp=L.layerGroup().addTo(map);camProc=L.layerGroup().addTo(map);
 const leg=L.control({position:'bottomleft'});
 leg.onAdd=()=>{const d=L.DomUtil.create('div','mp-legend');
  d.innerHTML=`<div class="mp-legend-body"><div class="mp-legend-layer"><b>${E(t('em.legT'))}</b>`
   +[0,1,2,3].map(g=>`<div><span class="em-dot" style="background:${COR[g]}"></span> ${E(grupoLabel(g))}</div>`).join('')
   +`<small>${E(t('em.legS'))}</small></div></div>`;return d};
 leg.addTo(map);}
const raio=v=>Math.max(4,Math.min(22,3+Math.sqrt((v||0)/1e5)));
function corEmpresa(x){return x.titulos.lavra?COR[0]:x.titulos.pesquisa?COR[1]:x.titulos.requerimento?COR[2]:COR[3]}
function desenharEmpresas(lista){camEmp.clearLayers();camProc.clearLayers();
 lista.filter(x=>x.lat!=null).sort((a,b)=>b.cfem_total-a.cfem_total).forEach(x=>{
  const m=L.circleMarker([x.lat,x.lon],{radius:raio(x.cfem_total),color:'#fff',weight:1,fillColor:corEmpresa(x),fillOpacity:.8});
  m.bindTooltip(E(x.nome)+(x.cfem_total?' · '+E(rs(x.cfem_total)):''));m.on('click',()=>abrir(x));m.addTo(camEmp)})}
function desenharProcessos(x){camEmp.clearLayers();camProc.clearLayers();
 const ps=(procDe.get(x.i)||[]).filter(procOk),pts=[];
 ps.forEach(p=>{const m=L.circleMarker([p.lat,p.lon],{radius:p.g===0?7:5,color:'#fff',weight:1,fillColor:COR[p.g],fillOpacity:.85});
  m.bindTooltip(`${E(p.proc)} · ${E(D.dims.fase[p.fase])} · ${E(D.dims.min[p.min]||'')}`);m.addTo(camProc);pts.push([p.lat,p.lon])});
 if(pts.length)map.fitBounds(L.latLngBounds(pts).pad(.3),{maxZoom:12});}

// ---------------------------------------------------------------------------------------------------------- ficha da empresa
function barrasAno(obj,fmt,nota){const xs=Object.entries(obj||{}).filter(([,v])=>v>0);if(!xs.length)return '';
 const max=Math.max(...xs.map(([,v])=>v));
 return `<div class="em-bars">`+xs.map(([a,v])=>`<div class="bar-row"><span class="bar-label">${E(a)}${nota&&nota(a)?' *':''}</span>`
  +`<div class="bar-track"><div class="bar-fill completo" style="width:${v/max*100}%"></div></div><span class="bar-value">${E(fmt(v))}</span></div>`).join('')+'</div>';}
function producaoDe(x){const est=window.EMPRESAS_ESTIMADA;if(!est||!x.cnpj_raiz)return [];
 return est.linhas.filter(l=>l.cnpj_raiz===x.cnpj_raiz&&!l.minerio_de_outro_mineral).sort((a,b)=>b.ano-a.ano||a.mineral.localeCompare(b.mineral)||a.base.localeCompare(b.base));}
const coef=v=>v>=1?num(v,v>=100?0:2)+' MWh/t':num(v*1000,v*1000>=10?1:2)+' kWh/t';
function ficha(x){
 const ps=procDe.get(x.i)||[],prod=producaoDe(x),ano=prod.length?prod[0].ano:null,meses=D.meta.ccee_meses||{};
 const muns=[...new Set(ps.map(p=>D.dims.mun[p.mun]).filter(Boolean))];
 let h=`<dl class="mp-dl"><dt>${E(t('em.cnpj'))}</dt><dd>${E(x.cnpj_raiz||'—')}</dd>`
  +`<dt>${E(t('em.municipios'))}</dt><dd>${E((x.cfem_municipios.length?x.cfem_municipios:muns.slice(0,8)).join(', ')||'—')}</dd></dl>`;
 h+=`<div class="em-tiles"><div><b>${E(x.cfem_total?rs(x.cfem_total):'—')}</b><span>${E(t('em.k.cfem'))}</span></div>`
  +`<div><b>${E(num(x.titulos.lavra))}</b><span>${E(t('em.k.lavra',{ha:num(x.area_lavra_ha)}))}</span></div>`
  +`<div><b>${E(num(x.titulos.pesquisa))}</b><span>${E(t('em.k.pesquisa',{ha:num(x.area_pesquisa_ha)}))}</span></div>`
  +`<div><b>${E(num(x.titulos.requerimento))}</b><span>${E(t('em.k.requerimento'))}</span></div></div>`;
 // arrecadação
 h+=`<h4>${E(t('em.h.cfem'))}</h4>`+(x.cfem_total?barrasAno(x.cfem_ano,v=>'R$ '+curto(v),a=>a==='2026')
  +`<p class="mp-note">${E(t('em.cfemMinerais'))}: ${E(x.cfem_mineral.map(([m,v])=>m+' ('+curto(v)+')').join(', '))}</p>`
  +(x.cfem_ano['2026']?`<p class="mp-note">${E(t('em.parcial2026'))}</p>`:''):`<p class="mp-note">${E(t('em.semCfem'))}</p>`);
 // produção e coeficiente
 h+=`<h4>${E(t('em.h.producao'))}</h4>`;
 if(prod.length){const ult=prod.filter(l=>l.ano===ano);
  h+=`<table class="mp-mini"><tbody>`+ult.map(l=>`<tr><td>${E(l.mineral)} · ${E(l.base)}</td><td class="num">${E(num(l.producao_t,l.producao_t<10?3:0))} t</td>`
   +`<td class="num">${E(num((l.parcela_do_estado||0)*100,1))} %</td></tr>`).join('')+`</tbody></table>`
   +`<p class="mp-note">${E(t('em.producaoNota',{ano:String(ano)}))}</p>`;
  const en=prod.filter(l=>l.energia_mwh!=null&&(l.ano===2025||l.ano===2024));
  h+=`<h4>${E(t('em.h.coef'))}</h4>`+(en.length?`<table class="mp-mini"><tbody>`+en.map(l=>`<tr><td>${l.ano} · ${E(l.mineral)} · ${E(l.base)}</td>`
   +`<td class="num">${E(num(l.energia_mwh))} MWh</td><td class="num">${l.coeficiente_mwh_t!=null&&l.coeficiente_mwh_t!==''?E(coef(l.coeficiente_mwh_t)):'—'}</td></tr>`).join('')+`</tbody></table>`
   +`<p class="mp-note">${E(en[0].energia_nota||'')}</p>`:`<p class="mp-note">${E(t('em.semCoef'))}</p>`);
 }else h+=`<p class="mp-note">${E(t('em.semProducao'))}</p>`;
 // energia
 h+=`<h4>${E(t('em.h.energia'))}</h4>`+(Object.keys(x.ccee_mwh).length?barrasAno(x.ccee_mwh,v=>num(v)+' MWh',a=>(meses[a]||12)<12)
  +`<p class="mp-note">${E(t('em.energiaNota'))}</p>`:`<p class="mp-note">${E(t('em.semCcee'))}</p>`);
 // títulos
 h+=`<h4>${E(t('em.h.titulos'))}</h4>`;
 const top=[...ps].sort((a,b)=>a.g-b.g||b.cfem-a.cfem||b.ha-a.ha).slice(0,12);
 h+=top.length?`<table class="mp-mini"><tbody>`+top.map(p=>`<tr><td><button type="button" class="link-button" data-proc="${E(p.proc)}">${E(p.proc)}</button></td>`
  +`<td><span class="em-dot" style="background:${COR[p.g]}"></span> ${E(D.dims.fase[p.fase])}</td><td>${E(D.dims.min[p.min]||'')}</td><td>${E(D.dims.mun[p.mun]||'')}</td>`
  +`<td class="num">${E(num(p.ha,0))} ha</td></tr>`).join('')+`</tbody></table>`+(ps.length>top.length?`<p class="mp-note">${E(t('em.maisProcessos',{n:num(ps.length-top.length)}))}</p>`:'')
  :`<p class="mp-note">${E(t('em.semTitulos'))}</p>`;
 // notícias
 h+=`<h4>${E(t('em.h.noticias'))}</h4>`+(x.noticias.length?`<ul class="em-news">`+x.noticias.map(n=>`<li><a href="${E(n.link)}" target="_blank" rel="noopener noreferrer">${E(n.titulo)}</a>`
  +`<br><small>${E(n.data)} · ${E(n.fonte)}</small></li>`).join('')+'</ul>':`<p class="mp-note">${E(t('em.semNoticias'))}</p>`);
 h+=`<div class="mp-source"><p>${E(t('em.fonteFicha'))}</p></div>`;
 return h;}
function abrir(x){sel=x;
 el('em-detail-eyebrow').textContent=t('em.fichaEyebrow');el('em-detail-title').textContent=x.nome;
 el('em-detail-body').innerHTML=ficha(x);el('em-detail').hidden=false;el('em-work').classList.add('mp-com-detalhe');el('em-todas').hidden=false;
 el('em-detail-body').querySelectorAll('[data-proc]').forEach(b=>b.onclick=()=>{const p=(procDe.get(x.i)||[]).find(q=>q.proc===b.dataset.proc);if(p)map.setView([p.lat,p.lon],13)});
 desenharProcessos(x);
 el('em-lista').querySelectorAll('button').forEach(b=>b.classList.toggle('on',+b.dataset.i===x.i));}
function fechar(){sel=null;el('em-detail').hidden=true;el('em-work').classList.remove('mp-com-detalhe');el('em-todas').hidden=true;desenhar()}

// --------------------------------------------------------------------------------------------------- lista, tabela, recorte
function chips(){const c=[];
 if(F.busca)c.push(['busca','“'+el('em-busca').value.trim()+'”']);if(F.min>=0)c.push(['min',D.dims.min[F.min]]);if(F.mun>=0)c.push(['mun',D.dims.mun[F.mun]]);
 if(F.grupos.size<4)c.push(['grupos',[...F.grupos].map(grupoLabel).join(', ')]);if(F.cfem)c.push(['cfem',t('em.soCfem')]);
 el('em-chips').innerHTML=c.length?c.map(([k,v])=>`<button type="button" class="rd-chip" data-k="${k}">${E(v)} ×</button>`).join(''):`<span class="mp-note">${E(t('em.semFiltro'))}</span>`;
 el('em-clear').hidden=!c.length;
 el('em-chips').querySelectorAll('[data-k]').forEach(b=>b.onclick=()=>{const k=b.dataset.k;
  if(k==='busca')el('em-busca').value='';if(k==='min')el('em-min').value=-1;if(k==='mun')el('em-mun').value=-1;
  if(k==='grupos')el('em-grupos').querySelectorAll('input').forEach(i=>i.checked=true);if(k==='cfem')el('em-cfem').checked=false;ler();desenhar()})}
function ler(){F.busca=norm(el('em-busca').value.trim());F.min=+el('em-min').value;F.mun=+el('em-mun').value;F.cfem=el('em-cfem').checked;
 F.grupos=new Set([...el('em-grupos').querySelectorAll('input:checked')].map(i=>+i.value))}
function desenhar(){const lista=recorte();chips();
 const ordem=[...lista].sort((a,b)=>b.cfem_total-a.cfem_total||b.titulos.lavra-a.titulos.lavra||a.nome.localeCompare(b.nome));
 el('em-lista-nota').textContent=t('em.listaNota',{n:num(lista.length),m:num(Math.min(LIMITE_LISTA,lista.length))});
 el('em-lista').innerHTML=ordem.slice(0,LIMITE_LISTA).map(x=>`<li><button type="button" data-i="${x.i}">${E(x.nome)}`
  +`<small>${E(x.cfem_total?rs(x.cfem_total):t('em.semCfemCurto'))} · ${E(t('em.listaTitulos',{l:num(x.titulos.lavra),p:num(x.titulos.pesquisa)}))}</small></button></li>`).join('');
 el('em-lista').querySelectorAll('button').forEach(b=>b.onclick=()=>abrir(D.empresas.find(x=>x.i===+b.dataset.i)));
 // indicadores e tabela
 const cf=lista.reduce((s,x)=>s+x.cfem_total,0),lav=lista.reduce((s,x)=>s+x.titulos.lavra,0),pes=lista.reduce((s,x)=>s+x.titulos.pesquisa,0);
 el('em-metrics').innerHTML=[['a',t('em.m.empresas'),num(lista.length),t('em.m.empresasSub')],['b',t('em.m.cfem'),'R$ '+curto(cf),t('em.m.cfemSub')],
  ['c',t('em.m.lavra'),num(lav),t('em.m.lavraSub')],['d',t('em.m.pesquisa'),num(pes),t('em.m.pesquisaSub')]]
  .map(([tom,r,v,d])=>`<div class="metric tone-${tom}"><span>${E(r)}</span><strong>${E(v)}</strong><small>${E(d)}</small></div>`).join('');
 const est=window.EMPRESAS_ESTIMADA,en=new Map();
 if(est)est.linhas.forEach(l=>{if(l.ano===2025&&l.energia_mwh!=null&&!l.minerio_de_outro_mineral){const k=l.cnpj_raiz+'|'+l.mineral;if(!en.has(k))en.set(k,l.energia_mwh)}});
 const energia=x=>{let s=0,ok=false;en.forEach((v,k)=>{if(k.startsWith(x.cnpj_raiz+'|')){s+=v;ok=true}});return ok?s:null};
 el('em-thead').innerHTML=`<tr>${[t('em.h.empresa'),t('em.cnpj'),t('em.h.cfemTot'),t('em.g.lavra'),t('em.g.pesquisa'),t('em.h.energia25'),t('em.h.noticias')].map(c=>`<th>${E(c)}</th>`).join('')}</tr>`;
 const linhas=ordem.slice(0,300);
 el('em-tbody').innerHTML=linhas.map(x=>{const e=x.cnpj_raiz?energia(x):null;
  return `<tr data-i="${x.i}"><td>${E(x.nome)}</td><td>${E(x.cnpj_raiz)}</td><td class="num">${x.cfem_total?E(rs(x.cfem_total)):'—'}</td><td class="num">${num(x.titulos.lavra)}</td>`
   +`<td class="num">${num(x.titulos.pesquisa)}</td><td class="num">${e==null?'—':E(num(e))+' MWh'}</td><td class="num">${num(x.noticias.length)}</td></tr>`}).join('');
 el('em-tbody').querySelectorAll('tr').forEach(r=>r.onclick=()=>{abrir(D.empresas.find(x=>x.i===+r.dataset.i));el('emp-map').scrollIntoView({behavior:'smooth',block:'center'})});
 el('em-count').textContent=t('em.contagem',{m:num(linhas.length),n:num(lista.length)});
 el('em-csv').onclick=()=>exportar(ordem,energia);
 if(sel&&noRecorte(sel))desenharProcessos(sel);else{if(sel){sel=null;el('em-detail').hidden=true;el('em-todas').hidden=true;el('em-work').classList.remove('mp-com-detalhe')}desenharEmpresas(lista)}}
function exportar(lista,energia){
 const cab=['empresa','cnpj_raiz','cfem_2022_2026','titulos_lavra','area_lavra_ha','titulos_pesquisa','area_pesquisa_ha','requerimentos','energia_2025_mwh','municipios_cfem','lat','lon'];
 const csv=[cab.join(';'),...lista.map(x=>[x.nome,x.cnpj_raiz,x.cfem_total,x.titulos.lavra,x.area_lavra_ha,x.titulos.pesquisa,x.area_pesquisa_ha,x.titulos.requerimento,
  x.cnpj_raiz?energia(x)??'':'',x.cfem_municipios.join(' | '),x.lat??'',x.lon??''].map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(';'))].join('\r\n');
 const url=URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download='minera-goias-mapa-empresas.csv';a.click();URL.revokeObjectURL(url);}

function opcoes(sel_,itens,todos){sel_.innerHTML=`<option value="-1">${E(todos)}</option>`+itens.map(([v,l])=>`<option value="${v}">${E(l)}</option>`).join('')}
async function carregar(){
 el('em-error').textContent='';
 try{
  D=await api('/empresas/mapa');preparar();
  const usados=k=>[...new Set(D.processos.rows.map(r=>r[k]))].filter(i=>i>=0);
  opcoes(el('em-min'),usados(5).map(i=>[i,D.dims.min[i]]).sort((a,b)=>a[1].localeCompare(b[1],'pt')),t('em.todosMinerais'));
  const muns=usados(6).map(i=>[i,D.dims.mun[i]]).sort((a,b)=>a[1].localeCompare(b[1],'pt'));
  opcoes(el('em-mun'),muns,t('em.todosMunicipios'));opcoes(el('em-goto'),muns,t('em.irPara'));
  el('em-grupos').innerHTML=[0,1,2,3].map(g=>`<label><input type="checkbox" value="${g}" checked> <span class="em-dot" style="background:${COR[g]}"></span> ${E(grupoLabel(g))}</label>`).join('');
  el('em-content').hidden=false;iniciarMapa();
  let timer;el('em-busca').oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>{ler();desenhar()},300)};
  ['em-min','em-mun','em-cfem'].forEach(id=>el(id).onchange=()=>{ler();desenhar()});
  el('em-grupos').onchange=()=>{ler();desenhar()};
  el('em-clear').onclick=()=>{el('em-busca').value='';el('em-min').value=-1;el('em-mun').value=-1;el('em-cfem').checked=false;
   el('em-grupos').querySelectorAll('input').forEach(i=>i.checked=true);ler();desenhar()};
  el('em-goto').onchange=()=>{const i=+el('em-goto').value;if(i<0)return;const pts=D.processos.rows.filter(r=>r[6]===i).map(r=>[r[1],r[2]]);
   if(pts.length)map.fitBounds(L.latLngBounds(pts).pad(.2),{maxZoom:12})};
  el('em-detail-close').onclick=fechar;el('em-todas').onclick=()=>{fechar();map.fitBounds([[-19.6,-53.3],[-12.3,-45.8]])};
  el('em-side-toggle').onclick=()=>{const w=el('em-work'),off=!w.classList.contains('mp-side-off');
   if(matchMedia('(max-width:900px)').matches){w.classList.toggle('mp-side-open');el('em-backdrop').hidden=!w.classList.contains('mp-side-open')}
   else w.classList.toggle('mp-side-off',off);el('em-side-toggle').setAttribute('aria-expanded',String(!off));setTimeout(()=>map.invalidateSize(),220)};
  el('em-backdrop').onclick=()=>{el('em-work').classList.remove('mp-side-open');el('em-backdrop').hidden=true};
  for(const [tab,painel] of [['em-tab-lista','em-panel-lista'],['em-tab-filtros','em-panel-filtros']])el(tab).onclick=()=>{
   ['em-tab-lista','em-tab-filtros'].forEach(x=>el(x).setAttribute('aria-selected',String(x===tab)));
   ['em-panel-lista','em-panel-filtros'].forEach(x=>el(x).hidden=x!==painel)};
  el('em-fontes').textContent=t('em.fontes',{d:D.meta.built_on});
  ler();desenhar();
 }catch(e){el('em-error').textContent=e.message;console.error(e)}
 finally{el('em-loading').hidden=true}}
// A aba pode abrir escondida: o Leaflet precisa medir o mapa de novo quando ela aparece.
document.addEventListener('empresas-estimada',()=>{if(D)desenhar()});
window.showEmpresasMapa=()=>{if(!loaded){loaded=true;carregar()}else if(map)setTimeout(()=>map.invalidateSize(),50)};
})();
