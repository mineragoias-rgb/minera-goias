/* Mapa Mineral de Goiás: the P3M-style map tab, fed by /api/mapa (scripts/build_mapa_base.py) and the atlas layers it reuses.
   Rules kept here, so the interface never contradicts the data contract:
   - Goiás is a fixed cut: the data is already clipped; the basemap shows the surroundings only for orientation.
   - Analytic filters (municipality, mineral, holder, identifier; status, period and table search of the layer under analysis) apply to the map,
     the table and the indicators of the layers that carry the field. Values of one filter are joined with OR, different filters with AND.
   - Switching a layer on or off only changes the drawing. Moving the map changes totals only when "only the visible area" is ticked.
   - Every layer is a snapshot on its own date; only the municipal CFEM is a yearly series, and its last year is partial. */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc;
const EN=()=>I18N.lang==='en';
const rot=(o,k='nome')=>(EN()&&o[k+'_en'])||o[k];
const rotulo=c=>(EN()&&c.rotulo_en)||c.rotulo;
const minusculo=s=>s?s.charAt(0).toLowerCase()+s.slice(1):s;
// stored claim keys ('10670/1967') are shown the ANM way ('010.670/1967'); search accepts both
const fmtProc=k=>{const m=/^(\d{1,6})\/(\d{4})$/.exec(String(k));if(!m)return String(k);const n=m[1].padStart(6,'0');return n.slice(0,3)+'.'+n.slice(3)+'/'+m[2]};
const norm=s=>String(s??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase().replace(/\s+/g,' ').trim();
const num=(v,d=2)=>I18N.num(v,{maximumFractionDigits:d});
const dataBR=s=>{if(s==null||s==='')return '';const p=String(s).split('-');return EN()?String(s):p.reverse().join('/')};
const anoDe=v=>{if(v==null||v==='')return null;const y=typeof v==='number'?v:parseInt(String(v).slice(0,4),10);return Number.isFinite(y)?y:null};
const MATURIDADE={'OPERAÇÃO':'#0d9488','EXPANSÃO':'#2e7d32','CONSTRUÇÃO':'#07345c','DEFINIDO':'#0f6fb0','PROVÁVEL':'#8250c4','POSSÍVEL':'#c2681b','SINAL':'#b03a55'};
const PANES=[['mp-mascara',350],['mp-fundo',380],['mp-areas',410],['mp-limites',430],['mp-linhas',450],['mp-pontos',500],['mp-destaque',620]];
const ORDEM_TOQUE=['mp-pontos','mp-linhas','mp-areas','mp-fundo','mp-limites'];
const BASE=new Set(['limite_goias','municipios']);   // context layers: drawn whole, never thinned by filters
const POR_PAGINA=50,RAIO=5;

let cat=null,map=null,carregando=null,mascara=null,tiles=null,destaque=null,legendaCtrl=null,munDestaque=null;
let COMP=null,compProm=null,MUNTAB=null,RADAR=null,ATLAS_MUN=null,MUN_POR_NOME=null,MIN_CANON=null,GO_BOUNDS=null;
const estados=new Map();
const filtros={municipios:new Set(),minerais:new Set(),titular:'',id:'',situacao:new Set(),periodo:null,busca:'',area:false};
let analise='minas_ativas',selecao=null,outros=[],pagina=0,ordem={col:null,dir:1},cfemPeriodo=null,ocupados=0;

/* ---------- layer state and models ---------- */
function paneDe(e){
 if(BASE.has(e.id))return 'mp-limites';
 if(e.geometria==='ponto')return 'mp-pontos';
 if(e.geometria==='linha')return 'mp-linhas';
 return e.grupo==='mineracao'||e.grupo==='empreendimentos'?'mp-areas':'mp-fundo';
}
function estadoInicial(entrada,tipo){
 return {id:entrada.id,entrada,tipo,visivel:!!entrada.visivel_padrao,opacidade:1,status:'ocioso',erro:'',modelo:null,prom:null,
  grupo:L.layerGroup(),ix:null,exibidos:[],modoPonto:false,aberto:false};
}
function caixa(partes){
 let s=90,w=180,n=-90,e=-180,k=0;
 for(const p of partes)for(const [la,lo] of p){if(la<s)s=la;if(la>n)n=la;if(lo<w)w=lo;if(lo>e)e=lo;k++}
 return k?[s,w,n,e]:null;
}
function prepararModelo(c){
 const bb=new Array(c.n),centro=new Array(c.n),semGeo=new Array(c.n);
 for(let i=0;i<c.n;i++){const b=caixa(c.partes[i]);bb[i]=b;semGeo[i]=!b;centro[i]=b?[(b[0]+b[2])/2,(b[1]+b[3])/2]:null}
 return Object.assign(c,{bb,centro,semGeo});
}
// Radar projects have no coordinates: each project is drawn through the polygons of its ANM claims, never at a centroid.
function modeloRadar(tab,processos,entrada){
 const porChave=new Map();for(let i=0;i<processos.n;i++)porChave.set(processos.valor(i,'processo'),i);
 const linhas=tab.linhas,campos=entrada.campos.map(c=>c.id);
 const fontes=linhas.map(p=>p.processos.map(k=>porChave.get(k)).filter(j=>j!=null));
 const partes=fontes.map(js=>js.flatMap(j=>processos.partes[j]));
 const m={entrada,geometria:'poligono',n:linhas.length,partes,campos,valor:(i,c)=>linhas[i][c],grupos:fontes.map(js=>js.map(j=>processos.partes[j]))};
 m.atributos=i=>Object.fromEntries(campos.map(c=>[c,linhas[i][c]]));
 return prepararModelo(m);
}
function precisaComplemento(e){return Object.values(e.papeis||{}).includes('@processo')}
function complemento(){
 return compProm||(compProm=MapaDados.tabela('processos_complemento').then(t=>{COMP=MapaDados.complementoPorProcesso(t);return COMP}).catch(e=>{compProm=null;throw e}));
}
function carregar(st){
 if(st.modelo)return Promise.resolve(st.modelo);
 if(st.prom)return st.prom;
 st.status='carregando';st.erro='';linhaCamada(st);ocupado(1);
 st.prom=(async()=>{
  let m;
  if(st.tipo==='radar'){const [tab,proc]=await Promise.all([MapaDados.tabela('radar_projetos'),carregar(estados.get('processos'))]);RADAR=tab;m=modeloRadar(tab,proc,st.entrada)}
  else m=prepararModelo(await MapaDados.camada(st.id));
  if(precisaComplemento(st.entrada))await complemento();
  if(st.id==='municipios')anexarIndicadores(m);
  st.modelo=m;st.ix=indexar(st);st.status='pronto';
  return m;
 })().catch(e=>{st.status='erro';st.erro=e.message;st.prom=null;throw e}).finally(()=>{ocupado(-1);linhaCamada(st)});
 return st.prom;
}
function anexarIndicadores(m){
 const porCod=new Map(MUNTAB.linhas.map(l=>[l.code,l])),base=m.valor;
 m.valor=(i,c)=>{if(c==='code'||c==='name')return base(i,c);const l=porCod.get(base(i,'code'));if(!l)return null;
  if(c==='radar_total')return Object.values(l.radar_projetos).reduce((a,b)=>a+b,0);
  if(c.startsWith('cfem_'))return l.cfem_recolhida[c.slice(5)];return l[c]};
}
function ocupado(d){ocupados+=d;const b=el('mp-busy');if(b)b.hidden=ocupados<=0}

/* ---------- roles: which field answers each filter ---------- */
function lista(v){return v==null||v===''?[]:Array.isArray(v)?v.filter(x=>x!=null&&x!==''):[v]}
function indexar(st){
 const m=st.modelo,p=st.entrada.papeis||{},n=m.n,ix={};
 const comp=i=>COMP&&COMP.get(m.valor(i,'processo'));
 if(p.municipio){ix.municipio=new Array(n);for(let i=0;i<n;i++){let v=p.municipio==='@processo'?((comp(i)||{}).municipios||[]):lista(m.valor(i,p.municipio)).map(String);
  if(p.municipio_por_nome)v=v.map(x=>MUN_POR_NOME.get(norm(x))).filter(Boolean);ix.municipio[i]=v}}
 if(p.mineral){ix.mineral=new Array(n);for(let i=0;i<n;i++){const v=p.mineral==='@processo'?((comp(i)||{}).mineral||[]):lista(m.valor(i,p.mineral));
  ix.mineral[i]=[...new Set(v.flatMap(x=>String(x).split(';')).map(x=>MIN_CANON.get(norm(x))).filter(Boolean))]}}
 if(p.titular){ix.titular=new Array(n);ix.titularN=new Array(n);for(let i=0;i<n;i++){const v=p.titular==='@processo'?(comp(i)||{}).titular:m.valor(i,p.titular);ix.titular[i]=v||null;ix.titularN[i]=norm(v)}}
 if(p.id){ix.id=new Array(n);for(let i=0;i<n;i++)ix.id[i]=p.id.flatMap(f=>lista(m.valor(i,f))).map(MapaDados.chaveId)}
 if(p.situacao){ix.situacao=new Array(n);for(let i=0;i<n;i++){const v=lista(m.valor(i,p.situacao));ix.situacao[i]=v.length?String(v[0]):null}}
 if(p.data){ix.data=new Array(n);for(let i=0;i<n;i++)ix.data[i]=anoDe(m.valor(i,p.data))}
 return ix;
}
function textoBusca(st){
 if(st.ix.busca)return st.ix.busca;
 const cols=colunas(st),n=st.modelo.n,out=new Array(n);
 for(let i=0;i<n;i++)out[i]=norm(cols.map(c=>celula(c,c.get(i),true)).join(' '))+' '+(st.ix.id?st.ix.id[i].join(' '):'');
 return st.ix.busca=out;
}
const aplica=(st,papel)=>!!(st.entrada.papeis||{})[papel];
function passa(st,i,local){
 const ix=st.ix,f=filtros;
 if(f.municipios.size&&ix.municipio&&!ix.municipio[i].some(c=>f.municipios.has(c)))return false;
 if(f.minerais.size&&ix.mineral&&!ix.mineral[i].some(c=>f.minerais.has(c)))return false;
 if(f.titular&&ix.titularN&&!ix.titularN[i].includes(norm(f.titular)))return false;
 if(f.id&&ix.id&&!MapaDados.casaId(ix.id[i],f.id))return false;
 if(!local)return true;
 if(f.situacao.size&&ix.situacao&&!f.situacao.has(ix.situacao[i]))return false;
 if(f.periodo&&ix.data&&st.id!=='municipios'){const y=ix.data[i];if(y==null||y<f.periodo[0]||y>f.periodo[1])return false}
 if(f.busca&&!textoBusca(st)[i].includes(norm(f.busca)))return false;
 return true;
}
function globaisAtivos(){const f=filtros;return {municipio:f.municipios.size>0,mineral:f.minerais.size>0,titular:!!f.titular,id:!!f.id}}
function filtrada(st){const a=globaisAtivos();return Object.keys(a).some(k=>a[k]&&aplica(st,k))||(st.id===analise&&(filtros.situacao.size||filtros.periodo||filtros.busca))}

/* ---------- drawing ---------- */
const RENDER={};
function corDe(st,i){
 const lg=st.entrada.legenda||{tipo:'simples',cor:'#57768b'};
 if(lg.tipo==='simples')return lg.cor;
 let v=st.modelo.valor(i,lg.campo);if(Array.isArray(v))v=v[0];
 if(Array.isArray(lg.cores))return lg.cores[MapaDados.GRUPOS_ATLAS.indexOf(v)]||lg.outros||'#8a9aa8';
 return lg.cores[v]||lg.outros||'#8a9aa8';
}
function itensLegenda(st){
 const lg=st.entrada.legenda||{};
 if(lg.tipo==='categorias'){
  const pares=Array.isArray(lg.cores)?MapaDados.GRUPOS_ATLAS.map((g,k)=>[g,lg.cores[k]]):Object.entries(lg.cores);
  return lg.outros?[...pares,[t('mp.legendOther'),lg.outros]]:pares;
 }
 return [[rot(st.entrada),lg.cor||'#57768b']];
}
function estiloLinha(id){return {linhas_transmissao:{weight:2.2},ferrovias:{weight:2.4,dashArray:'7 4'},rodovias_federais:{weight:1.8},rodovias_estaduais:{weight:1.1},estruturas:{weight:.9}}[id]||{weight:1.6}}
async function desenhar(st){
 st.grupo.clearLayers();
 if(st.id==='limite_goias')desenharMascara(st);
 if(!st.visivel||!st.modelo){st.exibidos=[];linhaCamada(st);return}
 const m=st.modelo,e=st.entrada,op=st.opacidade,pane=paneDe(e),r=RENDER[pane],z=map.getZoom(),v=st.versao=(st.versao||0)+1;
 st.modoPonto=!!e.ponto_ate_zoom&&z<e.ponto_ate_zoom;
 const local=st.id===analise||st.tipo==='radar'&&analise==='radar_projetos';
 const idx=[];for(let i=0;i<m.n;i++)if(!m.semGeo[i]&&(BASE.has(st.id)||passa(st,i,local)))idx.push(i);
 st.exibidos=idx;linhaCamada(st);
 const sel=st.id==='municipios'?filtros.municipios:null;
 for(let k=0;k<idx.length;k++){
  const i=idx[k],cor=corDe(st,i);
  if(st.id==='limite_goias')L.polygon(m.partes[i],{renderer:r,color:'#07345c',weight:2.2,opacity:op,fill:false,interactive:false}).addTo(st.grupo);
  else if(st.id==='municipios'){const on=sel.has(m.valor(i,'code'));L.polygon(m.partes[i],{renderer:r,color:on?'#07345c':'#57768b',weight:on?1.8:.6,opacity:.9*op,fill:on,fillColor:'#07345c',fillOpacity:.1*op,interactive:false}).addTo(st.grupo)}
  else if(e.geometria==='ponto'||st.modoPonto){const pts=st.modoPonto?[m.centro[i]]:m.partes[i].map(p=>p[0]);for(const p of pts)L.circleMarker(p,{renderer:r,radius:RAIO,color:'#ffffff',weight:1,opacity:op,fillColor:cor,fillOpacity:.92*op,interactive:false}).addTo(st.grupo)}
  else if(e.geometria==='linha')L.polyline(m.partes[i],{renderer:r,color:cor,opacity:.9*op,interactive:false,...estiloLinha(st.id)}).addTo(st.grupo);
  else{const fundo=pane==='mp-fundo';L.polygon(m.partes[i],{renderer:r,color:cor,weight:fundo?.5:.9,opacity:.85*op,fillColor:cor,fillOpacity:(fundo?.26:.42)*op,fillRule:'evenodd',interactive:false}).addTo(st.grupo)}
  if(k%1500===1499){await new Promise(res=>requestAnimationFrame(res));if(v!==st.versao)return}  // a newer drawing of this layer took over
 }
}
function desenharMascara(st){
 if(mascara){mascara.remove();mascara=null}
 if(!st.visivel||!st.modelo)return;
 const mundo=[[-89,-179.9],[-89,179.9],[89,179.9],[89,-179.9]];
 mascara=L.polygon([mundo,...st.modelo.partes.flat()],{renderer:RENDER['mp-mascara'],stroke:false,fillColor:'#eef3f7',fillOpacity:.62,fillRule:'evenodd',interactive:false}).addTo(map);
}
function redesenharTudo(){for(const st of estados.values())if(st.visivel&&st.modelo)desenhar(st);desenharDestaque();legenda()}

/* ---------- hit test: every feature under the click, topmost first ---------- */
function dentro(lat,lon,aneis){
 let c=false;
 for(const a of aneis)for(let i=0,j=a.length-1;i<a.length;j=i++){const [yi,xi]=a[i],[yj,xj]=a[j];if((yi>lat)!==(yj>lat)&&lon<(xj-xi)*(lat-yi)/(yj-yi)+xi)c=!c}
 return c;
}
function distSeg(p,a,b){const dx=b.x-a.x,dy=b.y-a.y,l=dx*dx+dy*dy;let t=l?((p.x-a.x)*dx+(p.y-a.y)*dy)/l:0;t=Math.max(0,Math.min(1,t));return Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy)}
function tocar(latlng){
 const pt=map.latLngToContainerPoint(latlng),c2=map.containerPointToLatLng([pt.x+8,pt.y+8]),dLa=Math.abs(c2.lat-latlng.lat),dLo=Math.abs(c2.lng-latlng.lng);
 const res=[];
 const ests=[...estados.values()].filter(s=>s.visivel&&s.modelo&&s.id!=='limite_goias').sort((a,b)=>ORDEM_TOQUE.indexOf(paneDe(a.entrada))-ORDEM_TOQUE.indexOf(paneDe(b.entrada)));
 for(const st of ests){
  const m=st.modelo,g=st.entrada.geometria;
  for(const i of st.exibidos){
   const b=m.bb[i];if(latlng.lat<b[0]-dLa||latlng.lat>b[2]+dLa||latlng.lng<b[1]-dLo||latlng.lng>b[3]+dLo)continue;
   let hit=false;
   if(g==='ponto'||st.modoPonto)hit=(st.modoPonto?[m.centro[i]]:m.partes[i].map(p=>p[0])).some(p=>map.latLngToContainerPoint(p).distanceTo(pt)<=RAIO+4);
   else if(g==='linha')hit=m.partes[i].some(l=>{for(let k=1;k<l.length;k++)if(distSeg(pt,map.latLngToContainerPoint(l[k-1]),map.latLngToContainerPoint(l[k]))<6)return true;return false});
   else hit=dentro(latlng.lat,latlng.lng,m.partes[i]);
   if(hit){res.push({st,i});if(res.length>=40)return res}
  }
 }
 return res;
}

/* ---------- selection: highlight + details; never a filter ---------- */
function desenharDestaque(){
 destaque.clearLayers();
 if(!selecao)return;
 const {st,i}=selecao,m=st.modelo;if(!m||m.semGeo[i])return;
 const r=RENDER['mp-destaque'],g=st.entrada.geometria;
 if(g==='ponto')m.partes[i].forEach(p=>L.circleMarker(p[0],{renderer:r,radius:RAIO+5,color:'#ffb000',weight:3,fill:false,interactive:false}).addTo(destaque));
 else if(g==='linha')L.polyline(m.partes[i],{renderer:r,color:'#ffb000',weight:6,opacity:.85,interactive:false}).addTo(destaque);
 else{L.polygon(m.partes[i],{renderer:r,color:'#ffb000',weight:3,fillColor:'#ffd66b',fillOpacity:.25,fillRule:'evenodd',interactive:false}).addTo(destaque);
  if(st.modoPonto||map.getZoom()<9)L.circleMarker(m.centro[i],{renderer:r,radius:RAIO+5,color:'#ffb000',weight:3,fill:false,interactive:false}).addTo(destaque)}
}
// leave room for the details panel: it floats over the right edge (desktop) or the bottom half (phone)
function margens(){const movel=window.matchMedia('(max-width:900px)').matches,det=!el('mp-detail').hidden;
 return {paddingTopLeft:[40,40],paddingBottomRight:[det&&!movel?el('mp-detail').offsetWidth+40:40,det&&movel?Math.round(window.innerHeight*.5):40]}}
function aproximar(st,i){const b=st.modelo.bb[i];if(b)map.fitBounds([[b[0],b[1]],[b[2],b[3]]],{maxZoom:13,...margens()})}
function selecionar(st,i,opcoes={}){
 selecao={st,i};if(opcoes.outros)outros=opcoes.outros;else outros=[];
 desenharDestaque();detalhe();marcarLinha();
 if(opcoes.zoom&&!st.modelo.semGeo[i])aproximar(st,i);
}
function limparSelecao(){selecao=null;outros=[];desenharDestaque();el('mp-detail').hidden=true;el('mp-work').classList.remove('mp-com-detalhe');marcarLinha();requestAnimationFrame(()=>map.invalidateSize())}

/* ---------- columns, values and formatting ---------- */
function nomeMun(c){const n=ATLAS_MUN.get(String(c));return n?n:String(c)}
function colunas(st){
 const m=st.modelo,e=st.entrada,cols=e.campos.filter(c=>c.id!=='na_divisa').map(c=>({...c,get:i=>m.valor(i,c.id)}));
 const p=e.papeis||{};
 if(st.id==='municipios'){
  const med=MUNTAB.medidas;
  cols.push({id:'processos_que_tocam',rotulo:med.processos_que_tocam.rotulo,rotulo_en:med.processos_que_tocam.rotulo_en,tipo:'inteiro',get:i=>m.valor(i,'processos_que_tocam')},
   {id:'minas_ativas_que_tocam',rotulo:med.minas_ativas_que_tocam.rotulo,rotulo_en:med.minas_ativas_que_tocam.rotulo_en,tipo:'inteiro',get:i=>m.valor(i,'minas_ativas_que_tocam')},
   {id:'projetos_anm',rotulo:med.projetos_anm.rotulo,rotulo_en:med.projetos_anm.rotulo_en,tipo:'inteiro',get:i=>m.valor(i,'projetos_anm')},
   {id:'ocorrencias',rotulo:med.ocorrencias.rotulo,rotulo_en:med.ocorrencias.rotulo_en,tipo:'inteiro',get:i=>m.valor(i,'ocorrencias')},
   {id:'radar_total',rotulo:t('mp.radarProjects'),rotulo_en:t('mp.radarProjects'),tipo:'inteiro',get:i=>m.valor(i,'radar_total')});
  for(const a of med.cfem_recolhida.periodos){const parcial=med.cfem_recolhida.periodo_incompleto[a];
   cols.push({id:'cfem_'+a,rotulo:t('mp.cfemYear',{ano:a})+(parcial?' *':''),rotulo_en:t('mp.cfemYear',{ano:a})+(parcial?' *':''),tipo:'numero',unidade:'R$',get:i=>m.valor(i,'cfem_'+a)})}
 }
 if(precisaComplemento(e)){
  const c=i=>COMP.get(m.valor(i,'processo'))||{};
  if(p.titular==='@processo')cols.push({id:'@titular',rotulo:'Titular',rotulo_en:'Holder',tipo:'texto',get:i=>c(i).titular});
  if(p.municipio==='@processo')cols.push({id:'@municipios',rotulo:'Municípios (código IBGE)',rotulo_en:'Municipalities (IBGE code)',tipo:'municipios',get:i=>c(i).municipios});
  if(p.mineral==='@processo')cols.push({id:'@mineral',rotulo:'Mineral (categoria ANM)',rotulo_en:'Mineral (ANM category)',tipo:'mineral',get:i=>c(i).mineral});
 }
 return cols;
}
function celula(c,v,texto){
 if(v==null||v===''||(Array.isArray(v)&&!v.length))return '';
 const tipo=c.tipo;
 if(tipo==='processo')return fmtProc(v);
 if(c.id==='processos'&&Array.isArray(v))return v.map(fmtProc).join(texto?' | ':' · ');
 if(tipo==='municipios'||tipo==='municipios_nome'||tipo==='municipio')return lista(v).map(x=>texto?nomeMun(x)+' '+x:nomeMun(x)).join(', ');
 if(Array.isArray(v))return v.map(x=>x==null?t('mp.notInformed'):String(x)).join(texto?' | ':' · ');
 if(tipo==='numero')return c.unidade==='R$'?'R$ '+num(v,2):num(v,c.casas??2)+(c.unidade?' '+c.unidade:'');
 if(tipo==='inteiro')return num(v,0);
 if(tipo==='data')return dataBR(v);
 if(tipo==='booleano')return v?t('mp.yes'):t('mp.no');
 return String(v);
}
function valorDetalhe(c,v){
 const s=celula(c,v,false);
 if(!s)return `<span class="mp-ni">${escape(t('mp.notInformed'))}</span>`;
 if(c.tipo==='url'&&/^https?:\/\//.test(String(v)))return `<a href="${escape(v)}" target="_blank" rel="noopener noreferrer">${escape(t('mp.openLink'))} ↗</a>`;
 return escape(s);
}
function tituloDe(st,i){
 const p=st.entrada.papeis||{};
 for(const f of lista(p.titulo)){const v=st.modelo.valor(i,f);if(v!=null&&v!==''){const c=st.entrada.campos.find(x=>x.id===f);return c&&c.tipo==='processo'?fmtProc(v):String(v)}}
 return rot(st.entrada)+' #'+(i+1);
}

/* ---------- detail panel ---------- */
function detalhe(){
 const {st,i}=selecao,m=st.modelo,e=st.entrada,cols=colunas(st);
 el('mp-detail').hidden=false;el('mp-work').classList.add('mp-com-detalhe');
 el('mp-detail-layer').textContent=rot(e);
 el('mp-detail-title').textContent=tituloDe(st,i);
 let h='<dl class="mp-dl">';
 for(const c of cols){if(c.tipo==='lista'&&c.id==='processos'&&st.tipo==='radar')continue;
  h+=`<dt>${escape(rotulo(c))}${c.unidade&&c.unidade!=='R$'?` <small>(${escape(c.unidade)})</small>`:''}</dt><dd>${valorDetalhe(c,c.get(i))}${c.nota?`<small class="mp-note">${escape(c.nota)}</small>`:''}</dd>`}
 if(m.valor(i,'na_divisa'))h+=`<dt>${escape(t('mp.border'))}</dt><dd>${escape(t('mp.borderNote'))}</dd>`;
 h+='</dl>';
 if(st.tipo==='radar'){const ps=m.valor(i,'processos');h+=`<h4>${escape(t('mp.radarClaims',{n:ps.length,m:m.valor(i,'processos_no_mapa')}))}</h4><p class="mp-chiplist">${ps.slice(0,40).map(k=>`<button type="button" class="rd-chip" data-processo="${escape(k)}">${escape(fmtProc(k))}</button>`).join('')}${ps.length>40?' …':''}</p>`}
 if(e.campos.some(c=>c.id==='processo')&&st.tipo!=='radar'){
  if(!RADAR)MapaDados.tabela('radar_projetos').then(tab=>{RADAR=RADAR||tab;if(selecao&&selecao.st===st&&selecao.i===i)detalhe()}).catch(()=>null);
  const k=m.valor(i,'processo'),ps=RADAR?RADAR.linhas.filter(p=>p.processos.includes(k)):[];
  if(ps.length)h+=`<h4>${escape(t('mp.citedBy'))}</h4><ul class="mp-list">${ps.slice(0,12).map(p=>`<li><button type="button" class="link-button" data-radar="${escape(p.id)}">${escape(p.id)} · ${escape(p.projeto)}</button> <span class="pill">${escape(p.maturidade)}</span></li>`).join('')}</ul>`}
 if(st.id==='municipios')h+=perfilMunicipio(m.valor(i,'code'));
 h+=`<div class="mp-detail-actions">${m.semGeo[i]?`<span class="mp-note">${escape(t('mp.noGeometry'))}</span>`:`<button type="button" class="btn outline" data-acao="zoom">${escape(t('mp.zoomTo'))}</button>`}`+
  (st.id==='municipios'?`<button type="button" class="btn outline" data-acao="filtrar-mun">${escape(filtros.municipios.has(m.valor(i,'code'))?t('mp.unfilterMun'):t('mp.filterMun'))}</button>`:'')+
  (analise!==st.id?`<button type="button" class="btn outline" data-acao="analisar">${escape(t('mp.analyzeLayer'))}</button>`:'')+`</div>`;
 h+=fonteHtml(e,st.tipo==='radar');
 if(outros.length>1)h=`<div class="mp-overlap"><b>${escape(t('mp.overlapping',{n:outros.length}))}</b><ol>${outros.map((o,k)=>`<li><button type="button" class="link-button${o.st===st&&o.i===i?' on':''}" data-outro="${k}">${escape(rot(o.st.entrada))}: ${escape(tituloDe(o.st,o.i))}</button></li>`).join('')}</ol></div>`+h;
 el('mp-detail-body').innerHTML=h;
 requestAnimationFrame(()=>map.invalidateSize());
}
function perfilMunicipio(code){
 const l=MUNTAB.linhas.find(x=>x.code===code);if(!l)return '';
 const med=MUNTAB.medidas,c=med.cfem_recolhida;
 let h=`<h4>${escape(rot({nome:c.rotulo,nome_en:c.rotulo_en}))} <small>(${escape(c.unidade)})</small></h4><table class="mp-mini"><tbody>`;
 for(const a of c.periodos){const v=l.cfem_recolhida[a];h+=`<tr><td>${escape(a)}${c.periodo_incompleto[a]?` <span class="pill">${escape(t('mp.partial'))}</span>`:''}</td><td>${v==null?escape(t('mp.notInformed')):'R$ '+escape(num(v,2))}</td></tr>`}
 h+=`</tbody></table><p class="mp-note">${escape(c.nota)}</p>`;
 const radar=Object.entries(l.radar_projetos);
 h+=`<p class="mp-note">${escape(t('mp.radarByMaturity'))}: ${radar.length?radar.map(([k,v])=>escape(k)+' '+escape(num(v,0))).join(' · '):escape(t('mp.none'))}</p>`;
 return h;
}
function fonteHtml(e,radar){
 const f=e.fonte||{};
 const ref=e.periodo_referencia?escape(e.periodo_referencia):escape(t('mp.refNotInformed'));
 const dataR=Array.isArray(e.data_retrato)?e.data_retrato.map(dataBR).join(', '):e.data_retrato?dataBR(e.data_retrato):t('mp.notRecorded');
 return `<div class="mp-source"><p><b>${escape(t('mp.source'))}:</b> ${escape(radar?(e.fonte||''):f.nome||'')}${f.url?` · <a href="${escape(f.url)}" target="_blank" rel="noopener noreferrer">${escape(t('mp.openLink'))} ↗</a>`:''}</p>`+
  (radar?'':`<p><b>${escape(t('mp.snapshot'))}:</b> ${escape(dataR)} · <b>${escape(t('mp.refPeriod'))}:</b> ${ref}</p>`)+`</div>`;
}

/* ---------- universe under analysis: table + indicators ---------- */
function estadoAnalise(){return estados.get(analise)}
function linhasAnalise(){
 const st=estadoAnalise();if(!st.modelo)return null;
 const m=st.modelo,idx=[];
 for(let i=0;i<m.n;i++)if(passa(st,i,true))idx.push(i);
 if(filtros.area){const b=map.getBounds(),s=b.getSouth(),w=b.getWest(),n=b.getNorth(),e=b.getEast();
  return idx.filter(i=>{const q=m.bb[i];return q&&q[0]<=n&&q[2]>=s&&q[1]<=e&&q[3]>=w})}
 return idx;
}
function ordenar(st,idx){
 if(!ordem.col)return idx;
 const c=colunas(st).find(x=>x.id===ordem.col);if(!c)return idx;
 const chave=i=>{let v=c.get(i);if(Array.isArray(v))v=v[0];if(c.tipo==='municipios'||c.tipo==='municipios_nome'||c.tipo==='municipio')v=v==null?null:nomeMun(v);return v};
 return [...idx].sort((a,b)=>{const x=chave(a),y=chave(b);if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;
  return (typeof x==='number'&&typeof y==='number'?x-y:String(x).localeCompare(String(y),'pt',{numeric:true}))*ordem.dir});
}
function tabela(){
 const st=estadoAnalise();
 const head=el('mp-thead'),body=el('mp-tbody');
 if(!st.modelo){
  head.innerHTML='';body.innerHTML=`<tr><td class="mp-empty">${escape(st.status==='erro'?t('mp.layerFailed',{erro:st.erro}):t('mp.loadingLayer'))}</td></tr>`;
  el('mp-count').textContent='';el('mp-pager').innerHTML='';el('mp-table-notes').textContent='';indicadores(null);
  if(st.status!=='erro')carregar(st).then(()=>{atualizarFiltrosLocais();tabela();redesenharTudo()}).catch(()=>tabela());
  return;
 }
 const cols=colunas(st),todos=linhasAnalise(),idx=ordenar(st,todos);
 const com=idx.reduce((a,i)=>a+(st.modelo.semGeo[i]?0:1),0);
 const paginas=Math.max(1,Math.ceil(idx.length/POR_PAGINA));if(pagina>=paginas)pagina=paginas-1;
 head.innerHTML='<tr>'+cols.map(c=>`<th scope="col"><button type="button" class="mp-sort" data-col="${escape(c.id)}" aria-sort="${ordem.col===c.id?(ordem.dir>0?'ascending':'descending'):'none'}">${escape(rotulo(c))}${c.unidade&&c.unidade!=='R$'?` (${escape(c.unidade)})`:''}${ordem.col===c.id?(ordem.dir>0?' ▲':' ▼'):''}</button></th>`).join('')+'</tr>';
 const pag=idx.slice(pagina*POR_PAGINA,(pagina+1)*POR_PAGINA);
 body.innerHTML=pag.length?pag.map(i=>`<tr class="mp-row${selecao&&selecao.st===st&&selecao.i===i?' on':''}" data-i="${i}" tabindex="0">`+cols.map(c=>{const s=celula(c,c.get(i),false);return `<td title="${escape(s.length>60?s:'')}">${s?escape(s.length>90?s.slice(0,88)+'…':s):'<span class="mp-ni">—</span>'}</td>`}).join('')+'</tr>').join('')
  :`<tr><td class="mp-empty" colspan="${cols.length}">${escape(t('mp.noResults'))}</td></tr>`;
 el('mp-count').textContent=t('mp.count',{n:num(idx.length,0),total:num(st.modelo.n,0),geo:num(com,0)});
 el('mp-pager').innerHTML=paginas>1?`<button type="button" class="link-button" data-pag="0" ${pagina===0?'disabled':''}>«</button><button type="button" class="link-button" data-pag="${pagina-1}" ${pagina===0?'disabled':''}>‹ ${escape(t('mp.prev'))}</button><span>${escape(t('mp.page',{p:pagina+1,n:paginas}))}</span><button type="button" class="link-button" data-pag="${pagina+1}" ${pagina>=paginas-1?'disabled':''}>${escape(t('mp.next'))} ›</button><button type="button" class="link-button" data-pag="${paginas-1}" ${pagina>=paginas-1?'disabled':''}>»</button>`:'';
 notasTabela(st);
 indicadores(st,todos);
 referencia();
}
function notasTabela(st){
 const a=globaisAtivos(),n=[],nomes={municipio:t('mp.fMun'),mineral:t('mp.fMineral'),titular:t('mp.fHolder'),id:t('mp.fId')};
 const nao=Object.keys(a).filter(k=>a[k]&&!aplica(st,k)).map(k=>nomes[k]);
 if(nao.length)n.push(t('mp.notApplied',{filtros:nao.join(', ')}));
 if(a.municipio&&st.ix.municipio){const sem=st.ix.municipio.filter(v=>!v.length).length;if(sem)n.push(t('mp.withoutMun',{n:num(sem,0)}))}
 if(a.mineral&&st.ix.mineral){const sem=st.ix.mineral.filter(v=>!v.length).length;if(sem)n.push(t('mp.withoutMineral',{n:num(sem,0)}))}
 if(filtros.periodo&&st.ix.data&&st.id!=='municipios'){const sem=st.ix.data.filter(v=>v==null).length;if(sem)n.push(t('mp.withoutDate',{n:num(sem,0)}))}
 if(filtros.area)n.push(t('mp.areaOn'));
 if(st.entrada.temporalidade==='retrato'||st.tipo==='radar')n.push(t('mp.snapshotNote'));
 el('mp-table-notes').textContent=n.join(' ');
}
function marcarLinha(){document.querySelectorAll('#mp-tbody .mp-row').forEach(r=>r.classList.toggle('on',!!selecao&&selecao.st===estadoAnalise()&&selecao.i===+r.dataset.i))}

/* ---------- indicators and charts ---------- */
function barras(titulo,medida,pares,fmt=v=>num(v,0)){
 if(!pares.length)return '';
 const max=Math.max(...pares.map(p=>p[1]))||1;
 return `<article class="panel"><h3>${escape(titulo)}</h3><p class="subtitle">${escape(medida)}</p>`+pares.map(([k,v,extra])=>`<div class="bar-row"><span class="bar-label" title="${escape(k)}">${escape(k)}${extra?` <span class="pill">${escape(extra)}</span>`:''}</span><span class="bar-track"><span class="bar-fill" style="width:${(v/max*100).toFixed(1)}%"></span></span><b>${escape(fmt(v))}</b></div>`).join('')+'</article>';
}
function contar(idx,f){const c=new Map();for(const i of idx)for(const k of f(i))c.set(k,(c.get(k)||0)+1);return [...c.entries()].sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0]),'pt'))}
function indicadores(st,idx){
 const met=el('mp-metrics'),gr=el('mp-charts');
 if(!st){met.innerHTML='';gr.innerHTML='';el('mp-ind-sub').textContent='';return}
 const m=st.modelo,ix=st.ix,e=st.entrada,cards=[],graf=[];
 // what is being counted comes from the catalogue: a claim count is never shown as a mine or operation count
 const entidade=rot(e,'entidade')||t('mp.entFeatures');
 cards.push([entidade,num(idx.length,0),e.campos.some(c=>c.tipo==='processo')&&st.tipo!=='radar'?t('mp.claimsNotOperation'):t('mp.ofTotal',{n:num(m.n,0)})]);
 if(e.registros_fonte_rotulo){let s=0;for(const i of idx)s+=m.valor(i,'n_registros_fonte')||0;cards.push([rot(e,'registros_fonte_rotulo'),num(s,0),t('mp.sourceRecords')])}
 const temProc=e.campos.some(c=>c.id==='processo')||st.tipo==='radar';
 if(temProc&&e.chave!=='processo'){const s=new Set();for(const i of idx)for(const k of lista(m.valor(i,st.tipo==='radar'?'processos':'processo')))s.add(k);cards.push([t('mp.distinctClaims'),num(s.size,0),t('mp.distinctClaimsSub')])}
 if(ix.titular){const s=new Set();let pf=0;for(const i of idx){const v=ix.titular[i];if(!v)continue;if(/nome não publicado|nomes não publicados/.test(v))pf++;else s.add(norm(v))}
  cards.push([t('mp.distinctHolders'),num(s.size,0),t('mp.individuals',{n:num(pf,0)})])}
 if(ix.municipio&&st.id!=='municipios'){const s=new Set();for(const i of idx)for(const c of ix.municipio[i])if(ATLAS_MUN.has(c))s.add(c);cards.push([t('mp.munsWith'),num(s.size,0),t('mp.munsWithSub')])}
 if(st.id==='municipios'){const c=MUNTAB.medidas.cfem_recolhida,[a,b]=cfemPeriodo,anos=c.periodos.filter(y=>+y>=a&&+y<=b),parc=anos.filter(y=>c.periodo_incompleto[y]);
  let soma=0;for(const i of idx)for(const y of anos)soma+=m.valor(i,'cfem_'+y)||0;
  cards.push([t('mp.cfemPeriod',{p:a===b?String(a):a+'–'+b}),'R$ '+num(soma,0),parc.length?t('mp.cfemPartial',{anos:parc.map(y=>y+' ('+c.periodo_incompleto[y]+')').join(', ')}):t('mp.cfemCollected')]);
  graf.push(barras(t('mp.chartCfem'),t('mp.chartCfemSub'),c.periodos.map(y=>{let s=0;for(const i of idx)s+=m.valor(i,'cfem_'+y)||0;return [y,s,c.periodo_incompleto[y]?t('mp.partial'):'']}),v=>'R$ '+num(v/1e6,1)+' mi'))}
 if(st.tipo==='radar'){const lig=idx.filter(i=>m.valor(i,'ligacao')==='processos').length;cards.push([t('mp.radarLinked'),num(lig,0),t('mp.radarLinkedSub')])}
 if(ix.mineral)graf.push(barras(t('mp.chartMineral'),t('mp.chartMineralSub',{ent:entidade.toLowerCase()}),contar(idx,i=>ix.mineral[i].length?ix.mineral[i]:[t('mp.notInformed')]).slice(0,12)));
 if(ix.situacao){const camp=e.campos.find(c=>c.id===(e.papeis||{}).situacao);graf.push(barras(t('mp.chartStatus',{campo:minusculo(camp?rotulo(camp):t('mp.status'))}),t('mp.chartCountSub',{ent:entidade.toLowerCase()}),contar(idx,i=>[ix.situacao[i]??t('mp.notInformed')]).slice(0,12)))}
 if(ix.municipio&&st.id!=='municipios')graf.push(barras(t('mp.chartMun'),t('mp.chartMunSub',{ent:entidade.toLowerCase()}),contar(idx,i=>ix.municipio[i].filter(c=>ATLAS_MUN.has(c)).map(nomeMun)).slice(0,10)));
 if(ix.data&&st.id!=='municipios'){const camp=e.campos.find(c=>c.id===(e.papeis||{}).data);const pares=contar(idx,i=>ix.data[i]==null?[]:[ix.data[i]]).sort((a,b)=>a[0]-b[0]).slice(-15).map(([y,v])=>[String(y),v]);
  graf.push(barras(t('mp.chartYear',{campo:minusculo(camp?rotulo(camp):'')}),t('mp.chartCountSub',{ent:entidade.toLowerCase()}),pares))}
 met.innerHTML=cards.slice(0,4).map(([a,b,c],k)=>`<div class="metric tone-${'abcd'[k]}"><span>${escape(a)}</span><strong>${escape(b)}</strong><small>${escape(c)}</small></div>`).join('');
 gr.innerHTML=idx.length?graf.filter(Boolean).slice(0,4).join('')||`<p class="small muted">${escape(t('mp.noCharts'))}</p>`:`<p class="small muted">${escape(t('mp.noChartsEmpty'))}</p>`;
 el('mp-ind-sub').textContent=t('mp.indSub',{camada:rot(e)});
}

/* ---------- exports: the whole filtered set, every page ---------- */
function baixar(nome,tipo,texto){const url=URL.createObjectURL(new Blob([texto],{type:tipo}));const a=document.createElement('a');a.href=url;a.download=nome;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function descricaoFiltros(){return [...el('mp-chips').querySelectorAll('.rd-chip')].map(c=>c.dataset.texto).join(' | ')||t('mp.noFilters')}
function exportarCsv(){
 const st=estadoAnalise();if(!st.modelo)return;
 const cols=colunas(st),idx=ordenar(st,linhasAnalise());
 const safe=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replaceAll('"','""')+'"';
 const val=(c,v)=>{if(v==null||v===''||(Array.isArray(v)&&!v.length))return '';
  if(c.tipo==='municipios'||c.tipo==='municipios_nome'||c.tipo==='municipio')return lista(v).map(x=>nomeMun(x)+' ('+x+')').join(' | ');
  if(c.tipo==='processo')return fmtProc(v);
  if(Array.isArray(v))return v.map(x=>c.id==='processos'?fmtProc(x):x??'').join(' | ');
  if(c.tipo==='numero')return Number(v).toLocaleString('pt-BR',{useGrouping:false,maximumFractionDigits:c.casas??2});  // declared decimals; atlas areas are float32
  return String(v)};
 const e=st.entrada,f=e.fonte||{};
 const meta=[[t('mp.csvLayer'),rot(e)],[t('mp.source'),typeof f==='string'?f:f.nome||''],[t('mp.snapshot'),String(e.data_retrato??t('mp.notRecorded'))],[t('mp.refPeriod'),e.periodo_referencia||t('mp.refNotInformed')],
  [t('mp.csvFilters'),descricaoFiltros()],[t('mp.csvRows'),String(idx.length)],[t('mp.csvUse'),t('mp.csvUseText')]];
 const linhas=[...meta,[],cols.map(c=>rotulo(c)+(c.unidade?' ('+c.unidade+')':'')),...idx.map(i=>cols.map(c=>val(c,c.get(i))))];
 baixar(`mapa-mineral-goias-${st.id}.csv`,'text/csv;charset=utf-8','﻿'+linhas.map(r=>r.map(safe).join(';')).join('\r\n'));
 el('mp-export-msg').textContent=t('mp.csvDone',{n:num(idx.length,0)});
}
function aneisGeo(aneis){
 // rings of one source shape, nested by containment (even depth = outer ring, odd = hole of the ring that contains it)
 const fecha=a=>{const r=a.map(([la,lo])=>[+lo.toFixed(6),+la.toFixed(6)]);if(r.length&&(r[0][0]!==r[r.length-1][0]||r[0][1]!==r[r.length-1][1]))r.push(r[0]);return r};
 const prof=aneis.map((a,k)=>aneis.reduce((d,b,j)=>d+(j!==k&&a.length&&dentro(a[0][0],a[0][1],[b])?1:0),0));
 const polis=[];const de=new Map();
 aneis.forEach((a,k)=>{if(prof[k]%2===0){de.set(k,polis.length);polis.push([fecha(a)])}});
 aneis.forEach((a,k)=>{if(prof[k]%2===1){let pai=null,pd=-1;aneis.forEach((b,j)=>{if(prof[j]===prof[k]-1&&dentro(a[0][0],a[0][1],[b])&&prof[j]>pd){pai=j;pd=prof[j]}});if(pai!=null&&de.has(pai))polis[de.get(pai)].push(fecha(a))}});
 return polis;
}
function geometriaGeo(st,i){
 const m=st.modelo,g=st.entrada.geometria;if(m.semGeo[i])return null;
 if(g==='ponto'){const pts=m.partes[i].map(p=>[+p[0][1].toFixed(6),+p[0][0].toFixed(6)]);return pts.length===1?{type:'Point',coordinates:pts[0]}:{type:'MultiPoint',coordinates:pts}}
 if(g==='linha'){const ls=m.partes[i].map(l=>l.map(([la,lo])=>[+lo.toFixed(6),+la.toFixed(6)]));return ls.length===1?{type:'LineString',coordinates:ls[0]}:{type:'MultiLineString',coordinates:ls}}
 const polis=(st.tipo==='radar'?m.grupos[i]:[m.partes[i]]).flatMap(aneisGeo);
 return polis.length===1?{type:'Polygon',coordinates:polis[0]}:{type:'MultiPolygon',coordinates:polis};
}
function exportarGeojson(){
 const st=estadoAnalise();if(!st.modelo)return;
 const cols=colunas(st),idx=ordenar(st,linhasAnalise()),feats=[];let sem=0;
 for(const i of idx){const g=geometriaGeo(st,i);if(!g){sem++;continue}
  feats.push({type:'Feature',geometry:g,properties:Object.fromEntries(cols.map(c=>{const v=c.get(i)??null;return [c.id.replace('@',''),c.tipo==='numero'&&v!=null?+Number(v).toFixed(c.casas??2):v]}))})}
 const e=st.entrada,f=e.fonte||{};
 const fc={type:'FeatureCollection',name:`mapa-mineral-goias-${st.id}`,
  metadados:{camada:rot(e),fonte:typeof f==='string'?f:f.nome||'',data_retrato:e.data_retrato??null,periodo_referencia:e.periodo_referencia??null,filtros:descricaoFiltros(),
   registros_no_recorte:idx.length,registros_sem_geometria:sem,crs:'WGS 84 / SIRGAS 2000 (graus, longitude e latitude)',aviso:t('mp.geoWarning')},features:feats};
 baixar(`mapa-mineral-goias-${st.id}.geojson`,'application/geo+json',JSON.stringify(fc));
 el('mp-export-msg').textContent=t('mp.geoDone',{n:num(feats.length,0),sem:num(sem,0)});
}

/* ---------- side panel: groups, layer rows, info ---------- */
function linhaCamada(st){
 const row=document.querySelector(`#mapa-view .mp-layer[data-id="${st.id}"]`);if(!row)return;
 const s=row.querySelector('.mp-layer-status');let txt='',cls='';
 if(st.status==='carregando'){txt=t('mp.loadingShort');cls='load'}
 else if(st.status==='erro'){txt=t('mp.failedShort');cls='err'}
 else if(st.modelo){const n=st.modelo.n-st.modelo.semGeo.filter(Boolean).length;txt=st.visivel&&filtrada(st)&&!BASE.has(st.id)?t('mp.nOfM',{n:num(st.exibidos.length,0),m:num(n,0)}):num(n,0)}
 else if(st.entrada.bytes>600000&&(st.entrada.dados||{}).arquivo!=='data/atlas/atlas.json')txt=t('mp.sizeHint',{mb:num(st.entrada.bytes/1048576,1)});  // atlas.json is already in memory
 s.textContent=txt;s.className='mp-layer-status '+cls;
 row.querySelector('input[type=checkbox]').checked=st.visivel;
 const retry=row.querySelector('.mp-retry');retry.hidden=st.status!=='erro';
 if(st.status==='erro')retry.title=st.erro;
}
function painelCamadas(){
 const porGrupo=new Map(cat.grupos.map(g=>[g.id,[]]));
 for(const st of estados.values())porGrupo.get(st.entrada.grupo).push(st);
 const aberto=new Set(['territorio','mineracao','empreendimentos']);
 el('mp-groups').innerHTML=cat.grupos.filter(g=>porGrupo.get(g.id).length).map(g=>`<details class="mp-group" ${aberto.has(g.id)?'open':''}><summary>${escape(rot(g))} <small>${porGrupo.get(g.id).length}</small></summary>`+
  porGrupo.get(g.id).map(st=>{const e=st.entrada,cor=(itensLegenda(st)[0]||[])[1]||'#57768b';
   return `<div class="mp-layer" data-id="${escape(st.id)}"><div class="mp-layer-line"><label><input type="checkbox" ${st.visivel?'checked':''}><span class="mp-sw mp-sw-${e.geometria}" style="--c:${escape(cor)}"></span><span class="mp-layer-name">${escape(rot(e))}</span></label>`+
    `<span class="mp-layer-status"></span><button type="button" class="mp-ico mp-retry" hidden data-acao="retry" aria-label="${escape(t('mp.retry'))}">↻</button>`+
    `<button type="button" class="mp-ico" data-acao="extensao" title="${escape(t('mp.zoomLayer'))}" aria-label="${escape(t('mp.zoomLayer'))}: ${escape(rot(e))}">⤢</button>`+
    `<button type="button" class="mp-ico" data-acao="info" aria-expanded="false" title="${escape(t('mp.layerInfo'))}" aria-label="${escape(t('mp.layerInfo'))}: ${escape(rot(e))}">i</button></div><div class="mp-layer-info" hidden></div></div>`}).join('')+'</details>').join('');
 for(const st of estados.values())linhaCamada(st);
}
function infoCamada(st){
 const e=st.entrada,box=document.querySelector(`#mapa-view .mp-layer[data-id="${st.id}"] .mp-layer-info`);
 const omit=e.omitidos?Object.entries(e.omitidos):[];
 const feicoes=st.tipo==='radar'?t('mp.radarRows',{n:num(e.linhas,0)}):t('mp.features',{n:num(e.n_feicoes,0)})+(e.n_registros_fonte?' '+t('mp.fromRecords',{n:num(e.n_registros_fonte,0)}):'');
 box.innerHTML=`<label class="mp-op">${escape(t('mp.opacity'))} <input type="range" min="10" max="100" step="5" value="${Math.round(st.opacidade*100)}" data-acao="opacidade" aria-label="${escape(t('mp.opacity'))}: ${escape(rot(e))}"><output>${Math.round(st.opacidade*100)}%</output></label>`+
  `<div class="mp-leg">${itensLegenda(st).map(([k,c])=>`<span class="mp-leg-item"><span class="mp-sw mp-sw-${e.geometria}" style="--c:${escape(c)}"></span>${escape(k)}</span>`).join('')}</div>`+
  (e.ponto_ate_zoom?`<p class="mp-note">${escape(t('mp.pointMode',{z:e.ponto_ate_zoom}))}</p>`:'')+
  fonteHtml(e,st.tipo==='radar')+`<p class="mp-note">${escape(feicoes)}${e.bytes?' · '+escape(num(e.bytes/1024,0))+' KB':''}${e.carga==='sob_demanda'?' · '+escape(t('mp.onDemand')):''}</p>`+
  (e.notas&&e.notas.length?`<ul class="mp-notes-list">${e.notas.map(n=>`<li>${escape(n)}</li>`).join('')}</ul>`:'')+
  (e.recorte?`<p class="mp-note">${escape(e.recorte)}</p>`:'')+
  (omit.length?`<details class="mp-omit"><summary>${escape(t('mp.omitted'))}</summary><ul>${omit.map(([k,v])=>`<li><code>${escape(k)}</code>: ${escape(v)}</li>`).join('')}</ul></details>`:'')+
  `<p class="mp-note">${escape(escopoCamada(st))}</p>`+
  (analise!==st.id?`<button type="button" class="link-button" data-acao="analisar">${escape(t('mp.analyzeLayer'))} →</button>`:`<span class="pill">${escape(t('mp.underAnalysis'))}</span>`);
}
function escopoCamada(st){
 const p=st.entrada.papeis||{},nomes={municipio:t('mp.fMun'),mineral:t('mp.fMineral'),titular:t('mp.fHolder'),id:t('mp.fId')};
 const sim=Object.keys(nomes).filter(k=>p[k]).map(k=>nomes[k]);
 return sim.length?t('mp.scopeYes',{filtros:sim.join(', ')}):t('mp.scopeNone');
}
async function alternar(st,ligar){
 st.visivel=ligar;linhaCamada(st);
 if(ligar){try{await carregar(st)}catch{linhaCamada(st);return}}
 desenhar(st);legenda();fontes();escopos();
}
async function extensao(st){
 try{await carregar(st)}catch{return}
 const m=st.modelo,idx=st.exibidos.length?st.exibidos:[...m.bb.keys()];let s=90,w=180,n=-90,e=-180;
 for(const i of idx){const b=m.bb[i];if(!b)continue;s=Math.min(s,b[0]);w=Math.min(w,b[1]);n=Math.max(n,b[2]);e=Math.max(e,b[3])}
 if(n>=s)map.fitBounds([[s,w],[n,e]],{padding:[30,30],maxZoom:13});
 if(!st.visivel){st.visivel=true;alternar(st,true)}
}

/* ---------- filters ---------- */
function multiSelect(raiz,opcoes,selecionados,aoMudar,placeholder){
 raiz.innerHTML=`<input type="search" class="mp-ms-q" placeholder="${escape(placeholder)}" aria-label="${escape(placeholder)}"><div class="mp-ms-list" role="group"></div>`;
 const q=raiz.querySelector('.mp-ms-q'),box=raiz.querySelector('.mp-ms-list');
 const render=()=>{const k=norm(q.value);const ord=[...opcoes].sort((a,b)=>(selecionados.has(b.v)-selecionados.has(a.v))||a.r.localeCompare(b.r,'pt'));
  box.innerHTML=ord.filter(o=>!k||norm(o.r).includes(k)).slice(0,300).map(o=>`<label class="mp-ms-item"><input type="checkbox" value="${escape(o.v)}" ${selecionados.has(o.v)?'checked':''}> <span>${escape(o.r)}</span>${o.n!=null?`<small>${escape(num(o.n,0))}</small>`:''}</label>`).join('')||`<p class="mp-note">${escape(t('mp.noOptions'))}</p>`};
 q.oninput=render;
 box.onchange=ev=>{const v=ev.target.value;if(ev.target.checked)selecionados.add(v);else selecionados.delete(v);aoMudar()};
 raiz.render=render;render();
}
function atualizarFiltrosLocais(){
 const st=estadoAnalise(),e=st.entrada,p=e.papeis||{};
 el('mp-f-layer-title').textContent=t('mp.localFilters',{camada:rot(e)});
 const sitWrap=el('mp-f-sit-wrap'),perWrap=el('mp-f-per-wrap');
 sitWrap.hidden=!p.situacao||!st.ix;perWrap.hidden=!(p.data||st.id==='municipios')||!st.ix;
 if(st.ix&&p.situacao){const camp=e.campos.find(c=>c.id===p.situacao);el('mp-f-sit-label').textContent=camp?rotulo(camp):t('mp.status');
  const cont=contar([...Array(st.modelo.n).keys()],i=>[st.ix.situacao[i]]).filter(([k])=>k!=null);
  multiSelect(el('mp-f-sit'),cont.map(([k,n])=>({v:k,r:k,n})),filtros.situacao,mudouFiltro,t('mp.searchOptions'))}
 if(st.ix&&(p.data||st.id==='municipios')){
  let anos;
  if(st.id==='municipios'){anos=MUNTAB.medidas.cfem_recolhida.periodos.map(Number);el('mp-f-per-label').textContent=t('mp.cfemPeriodLabel');el('mp-scope-per').textContent=t('mp.cfemPeriodScope')}
  else{const ys=st.ix.data.filter(y=>y!=null);anos=ys.length?[...new Set(ys)].sort((a,b)=>a-b):[];const camp=e.campos.find(c=>c.id===p.data);
   el('mp-f-per-label').textContent=t('mp.periodOf',{campo:camp?rotulo(camp):''});el('mp-scope-per').textContent=t('mp.periodScope')}
  const a=el('mp-f-per-a'),b=el('mp-f-per-b'),opt=anos.map(y=>`<option value="${y}">${y}</option>`).join('');
  if(st.id==='municipios'){a.innerHTML=opt;b.innerHTML=opt;a.value=String(cfemPeriodo[0]);b.value=String(cfemPeriodo[1])}
  else{a.innerHTML=`<option value="">—</option>`+opt;b.innerHTML=`<option value="">—</option>`+opt;a.value=filtros.periodo?String(filtros.periodo[0]):'';b.value=filtros.periodo?String(filtros.periodo[1]):''}
 }
}
function escopos(){
 const vis=[...estados.values()].filter(s=>(s.visivel||s.id===analise)&&s.id!=='limite_goias');
 for(const [papel,id] of [['municipio','mp-scope-mun'],['mineral','mp-scope-min'],['titular','mp-scope-titular'],['id','mp-scope-id']]){
  const sim=vis.filter(s=>aplica(s,papel)).map(s=>rot(s.entrada)),nao=vis.filter(s=>!aplica(s,papel)&&!BASE.has(s.id)).map(s=>rot(s.entrada));
  el(id).textContent=(sim.length?t('mp.appliesTo',{camadas:sim.join(', ')}):t('mp.appliesToNone'))+(nao.length?' '+t('mp.notAppliesTo',{camadas:nao.join(', ')}):'');
 }
}
function chips(){
 const out=[],f=filtros,st=estadoAnalise();
 const add=(rotulo,texto,remover)=>out.push({rotulo,texto,remover});
 for(const c of f.municipios)add(t('mp.fMun'),nomeMun(c),()=>f.municipios.delete(c));
 for(const c of f.minerais)add(t('mp.fMineral'),c,()=>f.minerais.delete(c));
 if(f.titular)add(t('mp.fHolder'),f.titular,()=>{f.titular='';el('mp-f-titular').value=''});
 if(f.id)add(t('mp.fId'),f.id,()=>{f.id='';el('mp-f-id').value=''});
 for(const v of f.situacao)add(t('mp.status')+' ('+rot(st.entrada)+')',v,()=>f.situacao.delete(v));
 if(f.periodo)add(t('mp.period')+' ('+rot(st.entrada)+')',f.periodo.join('–'),()=>{f.periodo=null});
 if(f.busca)add(t('mp.tableSearch'),f.busca,()=>{f.busca='';el('mp-search').value=''});
 if(f.area)add(t('mp.visibleArea'),t('mp.on'),()=>{f.area=false;el('mp-area').checked=false});
 chips.atual=out;
 el('mp-chips').innerHTML=out.length?out.map((c,k)=>`<button type="button" class="rd-chip on" data-chip="${k}" data-texto="${escape(c.rotulo+': '+c.texto)}" aria-label="${escape(t('mp.removeFilter',{f:c.rotulo+': '+c.texto}))}">${escape(c.rotulo)}: ${escape(c.texto)} ×</button>`).join(''):`<span class="mp-note">${escape(t('mp.noFilters'))}</span>`;
 el('mp-clear').hidden=!out.length;
}
let espera=null;
function mudouFiltro(){
 clearTimeout(espera);
 el('mp-export-msg').textContent='';  // an export message describes the previous result
 espera=setTimeout(()=>{pagina=0;chips();redesenharTudo();tabela();escopos();
  const ms=[el('mp-f-mun'),el('mp-f-min'),el('mp-f-sit')];ms.forEach(r=>r&&r.render&&r.render())},120);
}
function limparFiltros(){
 const f=filtros;f.municipios.clear();f.minerais.clear();f.situacao.clear();f.titular='';f.id='';f.periodo=null;f.busca='';f.area=false;
 el('mp-f-titular').value='';el('mp-f-id').value='';el('mp-search').value='';el('mp-area').checked=false;
 atualizarFiltrosLocais();mudouFiltro();
}
async function trocarAnalise(id){
 analise=id;el('mp-universe').value=id;el('mp-export-msg').textContent='';
 filtros.situacao.clear();filtros.periodo=null;filtros.busca='';el('mp-search').value='';pagina=0;ordem={col:null,dir:1};
 const st=estadoAnalise();
 try{await carregar(st)}catch{}
 atualizarFiltrosLocais();chips();tabela();redesenharTudo();escopos();
 document.querySelectorAll('#mapa-view .mp-layer-info:not([hidden])').forEach(b=>infoCamada(estados.get(b.closest('.mp-layer').dataset.id)));
}

/* ---------- header, legend, sources ---------- */
function referencia(){
 const st=estadoAnalise(),e=st.entrada;
 let txt;
 if(st.id==='municipios'){const c=MUNTAB.medidas.cfem_recolhida;txt=t('mp.refCfem',{a:c.periodos[0],b:c.periodos[c.periodos.length-1],parcial:Object.values(c.periodo_incompleto).join(', ')})}
 else if(st.tipo==='radar')txt=t('mp.refRadar');
 else{const d=Array.isArray(e.data_retrato)?e.data_retrato.map(dataBR).join(', '):e.data_retrato?dataBR(e.data_retrato):t('mp.notRecorded');txt=t('mp.refLayer',{camada:rot(e),data:d})}
 el('mp-ref').textContent=txt;
}
function legenda(){
 if(!legendaCtrl)return;
 const box=legendaCtrl.getContainer().querySelector('.mp-legend-body');
 const vis=[...estados.values()].filter(s=>s.visivel&&s.id!=='limite_goias');
 box.innerHTML=vis.length?vis.map(st=>`<div class="mp-legend-layer"><b>${escape(rot(st.entrada))}</b>${itensLegenda(st).map(([k,c])=>`<span class="mp-leg-item"><span class="mp-sw mp-sw-${st.entrada.geometria}" style="--c:${escape(c)}"></span>${escape(k)}</span>`).join('')}${st.modoPonto?`<small>${escape(t('mp.pointModeShort'))}</small>`:''}</div>`).join(''):`<p class="mp-note">${escape(t('mp.noVisible'))}</p>`;
}
function fontes(){
 const vis=[...estados.values()].filter(s=>s.visivel||s.id===analise),vistos=new Set();
 const itens=[];for(const st of vis){const e=st.entrada,nome=st.tipo==='radar'?e.fonte:(e.fonte||{}).nome;if(!nome||vistos.has(nome))continue;vistos.add(nome);
  const d=st.tipo==='radar'?'':Array.isArray(e.data_retrato)?e.data_retrato.map(dataBR).join(', '):e.data_retrato?dataBR(e.data_retrato):t('mp.notRecorded');itens.push(nome+(d?' ('+d+')':''))}
 el('mp-sources').textContent=t('mp.sourcesLine',{fontes:itens.join('; ')});
}

/* ---------- init ---------- */
function controles(){
 L.control.scale({imperial:false,position:'bottomleft'}).addTo(map);
 const Voltar=L.Control.extend({onAdd(){const b=L.DomUtil.create('button','mp-home leaflet-bar');b.type='button';b.textContent=t('mp.backToGoias');b.title=t('mp.backToGoias');
  L.DomEvent.disableClickPropagation(b);b.onclick=()=>map.fitBounds(GO_BOUNDS,{padding:[12,12]});return b}});
 new Voltar({position:'topleft'}).addTo(map);
 const Leg=L.Control.extend({onAdd(){const d=L.DomUtil.create('div','mp-legend leaflet-bar');d.innerHTML=`<button type="button" class="mp-legend-toggle" aria-expanded="true">${escape(t('mp.legend'))}</button><div class="mp-legend-body"></div>`;
  L.DomEvent.disableClickPropagation(d);L.DomEvent.disableScrollPropagation(d);
  d.querySelector('.mp-legend-toggle').onclick=ev=>{const on=d.classList.toggle('fechada');ev.currentTarget.setAttribute('aria-expanded',String(!on))};return d}});
 legendaCtrl=new Leg({position:'topright'}).addTo(map);
 if(window.matchMedia('(max-width:1400px)').matches){const c=legendaCtrl.getContainer();c.classList.add('fechada');c.querySelector('.mp-legend-toggle').setAttribute('aria-expanded','false')}
}
function basemap(v){
 if(tiles){tiles.remove();tiles=null}
 if(v==='osm'){tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'});
  tiles.on('tileerror',()=>{el('mp-mapnote').textContent=t('mp.tileFail')});tiles.addTo(map)}
}
function eventos(){
 el('mp-groups').addEventListener('change',ev=>{const row=ev.target.closest('.mp-layer');if(row&&ev.target.type==='checkbox')alternar(estados.get(row.dataset.id),ev.target.checked)});
 el('mp-groups').addEventListener('input',ev=>{if(ev.target.dataset.acao!=='opacidade')return;const st=estados.get(ev.target.closest('.mp-layer').dataset.id);
  st.opacidade=+ev.target.value/100;ev.target.nextElementSibling.textContent=ev.target.value+'%';clearTimeout(st.op);st.op=setTimeout(()=>desenhar(st),80)});
 el('mp-groups').addEventListener('click',ev=>{const b=ev.target.closest('[data-acao]');if(!b||b.dataset.acao==='opacidade')return;const row=b.closest('.mp-layer'),st=estados.get(row.dataset.id);
  if(b.dataset.acao==='info'){const box=row.querySelector('.mp-layer-info'),abrir=box.hidden;box.hidden=!abrir;b.setAttribute('aria-expanded',String(abrir));if(abrir)infoCamada(st)}
  else if(b.dataset.acao==='extensao')extensao(st);
  else if(b.dataset.acao==='retry'){st.status='ocioso';alternar(st,true)}
  else if(b.dataset.acao==='analisar')trocarAnalise(st.id)});
 el('mp-basemap').onchange=ev=>basemap(ev.target.value);
 for(const [tab,painel] of [['mp-tab-layers','mp-panel-layers'],['mp-tab-filters','mp-panel-filters']])el(tab).onclick=()=>{
  for(const [t2,p2] of [['mp-tab-layers','mp-panel-layers'],['mp-tab-filters','mp-panel-filters']]){el(t2).setAttribute('aria-selected',String(t2===tab));el(p2).hidden=p2!==painel}};
 const lado=abrir=>{const work=el('mp-work'),movel=window.matchMedia('(max-width:900px)').matches;
  if(movel){work.classList.toggle('mp-side-open',abrir);el('mp-backdrop').hidden=!abrir}else work.classList.toggle('mp-side-off',!abrir);
  el('mp-side-toggle').setAttribute('aria-expanded',String(abrir));if(abrir&&movel)el('mp-side-close').focus()};
 el('mp-side-toggle').onclick=()=>{const work=el('mp-work'),movel=window.matchMedia('(max-width:900px)').matches;lado(movel?!work.classList.contains('mp-side-open'):work.classList.contains('mp-side-off'))};
 el('mp-side-close').onclick=()=>lado(false);el('mp-backdrop').onclick=()=>lado(false);
 document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&el('mp-work').classList.contains('mp-side-open'))lado(false)});
 el('mp-f-titular').oninput=ev=>{filtros.titular=ev.target.value.trim();mudouFiltroTexto()};
 el('mp-f-id').oninput=ev=>{filtros.id=ev.target.value.trim();mudouFiltroTexto()};
 el('mp-search').oninput=ev=>{filtros.busca=ev.target.value.trim();mudouFiltroTexto()};
 el('mp-area').onchange=ev=>{filtros.area=ev.target.checked;mudouFiltro()};
 const periodo=()=>{const a=el('mp-f-per-a').value,b=el('mp-f-per-b').value;
  if(analise==='municipios'){let x=+a,y=+b;if(x>y)[x,y]=[y,x];cfemPeriodo=[x,y];tabela();return}
  if(a===''&&b===''){filtros.periodo=null}else{let x=a===''?+b:+a,y=b===''?+a:+b;if(x>y)[x,y]=[y,x];filtros.periodo=[x,y]}mudouFiltro()};
 el('mp-f-per-a').onchange=periodo;el('mp-f-per-b').onchange=periodo;
 el('mp-clear').onclick=limparFiltros;
 el('mp-chips').onclick=ev=>{const b=ev.target.closest('[data-chip]');if(!b)return;chips.atual[+b.dataset.chip].remover();atualizarFiltrosLocais();mudouFiltro()};
 el('mp-universe').onchange=ev=>trocarAnalise(ev.target.value);
 el('mp-thead').onclick=ev=>{const b=ev.target.closest('[data-col]');if(!b)return;ordem=ordem.col===b.dataset.col?{col:b.dataset.col,dir:-ordem.dir}:{col:b.dataset.col,dir:1};pagina=0;tabela()};
 el('mp-pager').onclick=ev=>{const b=ev.target.closest('[data-pag]');if(!b||b.disabled)return;pagina=+b.dataset.pag;tabela();el('mp-table').scrollIntoView({block:'nearest'})};
 const escolherLinha=row=>{const st=estadoAnalise();selecionar(st,+row.dataset.i,{zoom:true})};
 el('mp-tbody').onclick=ev=>{const r=ev.target.closest('.mp-row');if(r)escolherLinha(r)};
 el('mp-tbody').onkeydown=ev=>{const r=ev.target.closest('.mp-row');if(r&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();escolherLinha(r)}};
 el('mp-csv').onclick=exportarCsv;el('mp-geojson').onclick=exportarGeojson;
 el('mp-detail-close').onclick=limparSelecao;
 el('mp-detail-body').onclick=async ev=>{const b=ev.target.closest('button');if(!b||!selecao)return;const {st,i}=selecao;
  if(b.dataset.acao==='zoom'){aproximar(st,i);el('mapa-map').scrollIntoView({block:'nearest',behavior:'smooth'})}
  else if(b.dataset.acao==='filtrar-mun'){const c=st.modelo.valor(i,'code');if(filtros.municipios.has(c))filtros.municipios.delete(c);else filtros.municipios.add(c);mudouFiltro();setTimeout(detalhe,150)}
  else if(b.dataset.acao==='analisar')await trocarAnalise(st.id);
  else if(b.dataset.outro!=null){const o=outros[+b.dataset.outro];selecionar(o.st,o.i,{outros})}
  else if(b.dataset.radar){const rs=estados.get('radar_projetos');try{await carregar(rs)}catch{return}const k=rs.modelo.n;for(let j=0;j<k;j++)if(rs.modelo.valor(j,'id')===b.dataset.radar){selecionar(rs,j,{zoom:true});break}}
  else if(b.dataset.processo){const ps=estados.get('processos');try{await carregar(ps)}catch{return}for(let j=0;j<ps.modelo.n;j++)if(ps.modelo.valor(j,'processo')===b.dataset.processo){selecionar(ps,j,{zoom:true});break}}};
 el('mp-goto').onchange=ev=>{const code=ev.target.value;if(!code)return;const m=estados.get('municipios').modelo;if(!m)return;
  for(let i=0;i<m.n;i++)if(m.valor(i,'code')===code){aproximar({modelo:m},i);if(munDestaque)munDestaque.remove();
   munDestaque=L.polygon(m.partes[i],{renderer:RENDER['mp-destaque'],color:'#07345c',weight:2.4,dashArray:'6 4',fill:false,interactive:false}).addTo(map);break}};
 map.on('click',ev=>{const hits=tocar(ev.latlng);if(!hits.length){limparSelecao();return}selecionar(hits[0].st,hits[0].i,{outros:hits})});
 map.on('zoomend',()=>{for(const st of estados.values())if(st.visivel&&st.modelo&&st.entrada.ponto_ate_zoom&&(map.getZoom()<st.entrada.ponto_ate_zoom)!==st.modoPonto)desenhar(st);desenharDestaque();legenda()});
 map.on('moveend',()=>{if(filtros.area){pagina=0;tabela()}});
 new ResizeObserver(()=>map.invalidateSize({pan:false})).observe(el('mapa-map'));
}
let espTexto=null;function mudouFiltroTexto(){clearTimeout(espTexto);espTexto=setTimeout(mudouFiltro,250)}

async function init(){
 if(!window.L)throw Error(t('mp.leafletFail'));
 if(!window.MapaDados)throw Error(t('mp.loaderFail'));
 const [c,atlas,mun]=await Promise.all([MapaDados.catalogo(),MapaDados.atlas(),MapaDados.tabela('municipios')]);
 cat=c;MUNTAB=mun;
 ATLAS_MUN=new Map(atlas.municipalities.map(m=>[m.code,m.name]));
 MUN_POR_NOME=new Map(atlas.municipalities.map(m=>[norm(m.name),m.code]));
 MIN_CANON=new Map(cat.minerais.map(m=>[norm(m),m]));
 cfemPeriodo=[+MUNTAB.medidas.cfem_recolhida.periodo_padrao,+MUNTAB.medidas.cfem_recolhida.periodo_padrao];
 for(const e of cat.camadas)estados.set(e.id,estadoInicial(e,'catalogo'));
 const r=cat.tabelas.find(x=>x.id==='radar_projetos');
 const radarEntrada={...r,id:'radar_projetos',nome:t('mp.radarLayer'),nome_en:t('mp.radarLayer'),grupo:'empreendimentos',geometria:'poligono',visivel_padrao:false,chave:'id',
  legenda:{tipo:'categorias',campo:'maturidade',cores:MATURIDADE},bytes:r.bytes,linhas:r.linhas};
 estados.set('radar_projetos',estadoInicial(radarEntrada,'radar'));
 el('mp-content').hidden=false;
 map=L.map('mapa-map',{preferCanvas:true,scrollWheelZoom:true,minZoom:5,maxZoom:16,zoomSnap:.25,zoomControl:false});
 L.control.zoom({zoomInTitle:t('mp.zoomIn'),zoomOutTitle:t('mp.zoomOut')}).addTo(map);
 for(const [nome,z] of PANES){map.createPane(nome).style.zIndex=z;RENDER[nome]=L.canvas({pane:nome,padding:.4})}
 map.getPane('mp-mascara').style.pointerEvents='none';
 destaque=L.layerGroup().addTo(map);
 for(const st of estados.values())st.grupo.addTo(map);
 const limite=estados.get('limite_goias');await carregar(limite);
 const b=caixa(limite.modelo.partes.flat());
 GO_BOUNDS=L.latLngBounds([b[0],b[1]],[b[2],b[3]]);
 map.fitBounds(GO_BOUNDS,{padding:[12,12]});map.setMaxBounds(GO_BOUNDS.pad(.8));
 basemap('osm');controles();
 el('mp-goto').innerHTML=`<option value="">${escape(t('mp.gotoMun'))}</option>`+[...ATLAS_MUN].sort((x,y)=>x[1].localeCompare(y[1],'pt')).map(([code,name])=>`<option value="${escape(code)}">${escape(name)}</option>`).join('');
 const opts=g=>[...estados.values()].filter(s=>s.entrada.grupo===g.id&&s.id!=='limite_goias').map(s=>`<option value="${escape(s.id)}">${escape(rot(s.entrada))}</option>`).join('');
 el('mp-universe').innerHTML=cat.grupos.map(g=>`<optgroup label="${escape(rot(g))}">${opts(g)}</optgroup>`).join('');
 el('mp-universe').value=analise;
 multiSelect(el('mp-f-mun'),[...ATLAS_MUN].map(([v,r])=>({v,r})),filtros.municipios,mudouFiltro,t('mp.searchMun'));
 multiSelect(el('mp-f-min'),cat.minerais.map(v=>({v,r:v})),filtros.minerais,mudouFiltro,t('mp.searchMineral'));
 painelCamadas();eventos();chips();escopos();
 await Promise.all([...estados.values()].filter(s=>s.visivel).map(s=>carregar(s).catch(()=>null)));
 redesenharTudo();atualizarFiltrosLocais();tabela();fontes();referencia();
 if(window.matchMedia('(max-width:900px)').matches)el('mp-side-toggle').setAttribute('aria-expanded','false');
}
window.showMapa=async()=>{
 el('mp-error').textContent='';
 try{
  if(!carregando)carregando=init().catch(e=>{if(map){map.remove();map=null}estados.clear();carregando=null;throw e});
  await carregando;
  requestAnimationFrame(()=>map&&map.invalidateSize());
 }catch(e){el('mp-error').textContent=t('mp.loadFail',{erro:e.message})}
 finally{el('mp-loading').hidden=true}
};
})();
