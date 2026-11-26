/* Atlas Empresarial — topo da aba Empresas. Mapa, busca, filtros, Top N, ficha da empresa, comparação e exportação.
   Dados de /api/empresas/atlas (autenticado), montado por scripts/build_atlas_empresas.py. Aqui só se filtra, soma e desenha:
   identidade por CNPJ raiz, vínculos e classificações são decididos no gerador, onde são auditáveis.
   O que o mapa desenha: centroide do direito minerário (indicativo) e referência do município da operação declarada (aproximada).
   Nenhum ponto é apresentado como localização exata de mina. Polígonos ANM só carregam quando pedidos (empresa ou zoom alto). */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc;
const num=(v,c=0)=>I18N.num(v,{minimumFractionDigits:c,maximumFractionDigits:c});
const brl=v=>'R$ '+(Math.abs(v)>=1e6?num(v/1e6,1)+' mi':num(v,0));
const norm=s=>String(s??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
const soDigitos=s=>String(s??'').replace(/\D/g,'');
const cnpjFmt=c=>c&&c.length===8?`${c.slice(0,2)}.${c.slice(2,5)}.${c.slice(5)}`:c||'—';
const GRUPOS=['lavra_autorizada','requerimento_lavra','pesquisa','disponibilidade','outro'];
const COR={lavra_autorizada:'#0d9488',requerimento_lavra:'#0f6fb0',pesquisa:'#c2681b',disponibilidade:'#8250c4',outro:'#93a4b1'};
// Chaves por extenso para o teste de tradução enxergar cada uma.
const rotuloGrupo=g=>({lavra_autorizada:t('ea.g.lavra_autorizada'),requerimento_lavra:t('ea.g.requerimento_lavra'),pesquisa:t('ea.g.pesquisa'),
 disponibilidade:t('ea.g.disponibilidade'),outro:t('ea.g.outro')}[g]||g);
const rotuloMetrica=m=>({cfem:t('ea.met.cfem'),processos:t('ea.met.processos'),area:t('ea.met.area'),ccee:t('ea.met.ccee')}[m]||m);
const rotuloTipoValor=v=>({realizado:t('ea.tv.realizado'),guidance:t('ea.tv.guidance'),capacidade:t('ea.tv.capacidade'),meta:t('ea.tv.meta'),
 estimativa:t('ea.tv.estimativa')}[v]||v);
// Só é produção o que a empresa declarou como realizado, medido como produção (não embarque nem venda), no recorte de Goiás.
const MEDIDAS_PRODUCAO=['minerio_rom','contido','metal_em_concentrado','produto_acabado'];
const ehProducaoGO=p=>p.tipo_valor==='realizado'&&MEDIDAS_PRODUCAO.includes(p.medida)&&p.escopo==='operacao_goias';
const rotuloMedida=m=>({minerio_rom:t('ea.md.minerio_rom'),contido:t('ea.md.contido'),metal_em_concentrado:t('ea.md.metal_em_concentrado'),
 produto_acabado:t('ea.md.produto_acabado'),embarque:t('ea.md.embarque'),venda:t('ea.md.venda'),capacidade:t('ea.md.capacidade'),meta:t('ea.md.meta')}[m]||m);
const rotuloEscopo=e=>({operacao_goias:t('ea.esc.operacao_goias'),consolidado_brasil:t('ea.esc.consolidado_brasil'),consolidado_global:t('ea.esc.consolidado_global')}[e]||e);
const rotuloQualidade=q=>({observado_completo:t('ep.q.observado_completo'),estimado_alto:t('ep.q.estimado_alto'),
 estimado_medio:t('ep.q.estimado_medio'),estimado_baixo:t('ep.q.estimado_baixo')}[q]||q);
const rotuloConf=c=>({alta:t('ea.conf.alta'),media:t('ea.conf.media')}[c]||c||'—');
const rotuloMetodo=m=>({processo_anm:t('ea.met.processo_anm'),curadoria_cnpj:t('ea.met.curadoria_cnpj'),alias_entidade:t('ea.met.alias_entidade'),
 alias_grupo:t('ea.met.alias_grupo'),sem_vinculo_verificado:t('ea.met.sem_vinculo')}[m]||m);

let D=null,EP=null,loaded=false,carregando=null;
const S={sel:null,aba:'perfil',pag:0,ppag:0,cmp:[],destaque:null,mapa:null,camadas:{},geo:null,munCentro:null,universo:[],ranking:[],puxadores:new Set()};
let E=[],porI=new Map(),buscaPorI=new Map(),procsPorEmp=new Map(),cfemPorEmp=new Map(),projPorEmp=new Map(),newsPorEmp=new Map(),procPorId=new Map(),idxBusca=[],criticosPorMin=new Map();
const PC={};   // índice das colunas de processos

// ------------------------------------------------------------------ preparo
function preparar(){
 D.processos.cols.forEach((c,i)=>PC[c]=i);
 E=D.empresas;E.forEach(e=>porI.set(e.i,e));
 D.processos.rows.forEach((r,k)=>{procPorId.set(soDigitos(r[PC.processo]),k);
  if(r[PC.empresa]>=0){if(!procsPorEmp.has(r[PC.empresa]))procsPorEmp.set(r[PC.empresa],[]);procsPorEmp.get(r[PC.empresa]).push(k)}});
 D.cfem.rows.forEach(r=>{if(!cfemPorEmp.has(r[0]))cfemPorEmp.set(r[0],[]);cfemPorEmp.get(r[0]).push(r)});
 D.projetos.forEach(p=>p.e.forEach(i=>{if(!projPorEmp.has(i))projPorEmp.set(i,[]);projPorEmp.get(i).push(p)}));
 D.noticias.forEach(n=>{if(!newsPorEmp.has(n.e))newsPorEmp.set(n.e,[]);newsPorEmp.get(n.e).push(n)});
 for(const esfera of ['federal','estadual'])for(const cat of D.criticos[esfera].categorias)for(const item of cat.itens)for(const m of item.min){
  if(!criticosPorMin.has(m))criticosPorMin.set(m,{federal:[],estadual:[]});
  const alvo=criticosPorMin.get(m)[esfera];if(!alvo.includes(cat.id))alvo.push(cat.id)}
 idxBusca=E.map(e=>({i:e.i,txt:norm([e.nome,e.cnpj,cnpjFmt(e.cnpj),e.grupo||'',...(e.alias||[])].join(' '))}));idxBusca.forEach(x=>buscaPorI.set(x.i,x.txt));
 if(window.L)prepararPontos();}

const anos=()=>{const a=+el('ea-ano-ini').value,b=+el('ea-ano-fim').value;return a<=b?[a,b]:[b,a]};
const filtros=()=>({mun:el('ea-mun').value,min:el('ea-min').value,grupo:el('ea-grupo').value,dado:el('ea-dado').value,
 metrica:el('ea-metrica').value,top:el('ea-top').value,q:norm(el('ea-busca').value.trim())});

// Processos da empresa que passam pelos filtros de território (município, mineral, fase).
function procsFiltrados(i,f){
 const ks=procsPorEmp.get(i)||[],mun=f.mun===''?null:+f.mun,min=f.min===''?null:+f.min;
 return ks.filter(k=>{const r=D.processos.rows[k];
  return (mun===null||r[PC.municipios].includes(mun))&&(min===null||r[PC.mineral]===min)&&(!f.grupo||D.dims.fase[r[PC.fase]].grupo===f.grupo)});}
function cfemPeriodo(i,f,[a,b]){
 const mun=f.mun===''?null:+f.mun,min=f.min===''?null:+f.min;let s=0;
 for(const r of cfemPorEmp.get(i)||[])if(r[1]>=a&&r[1]<=b&&(mun===null||r[2]===mun)&&(min===null||r[3]===min))s+=r[4];
 return s;}
function cceePeriodo(e,[a,b]){let s=0,m=0;for(const[ano,v]of Object.entries(e.ccee||{}))if(+ano>=a&&+ano<=b){s+=v.obs;m+=v.meses}return {mwh:s,meses:m};}
function temCritico(e,esfera){return e.min.some(m=>criticosPorMin.has(m)&&criticosPorMin.get(m)[esfera].length)}

function valorMetrica(e,f,per,ps){
 if(f.metrica==='cfem')return cfemPeriodo(e.i,f,per);
 if(f.metrica==='processos')return ps.length;
 if(f.metrica==='area')return ps.reduce((s,k)=>s+(D.processos.rows[k][PC.area_ha]||0),0);
 return cceePeriodo(e,per).mwh;}

function calcular(){
 const f=filtros(),per=anos();
 const temFiltroTerr=f.mun!==''||f.min!==''||!!f.grupo;
 const linhas=[];
 for(const e of E){
  const ps=procsFiltrados(e.i,f);
  const cf=cfemPeriodo(e.i,f,per);
  // Recorte territorial: a empresa entra se tem processo no recorte ou CFEM recolhida nele.
  if(temFiltroTerr&&!ps.length&&!(cf>0&&!f.grupo))continue;
  if(f.dado==='enr'&&!e.enr)continue;
  if(f.dado==='cfem'&&!(cf>0))continue;
  if(f.dado==='ccee'&&!cceePeriodo(e,per).mwh)continue;
  if(f.dado==='proj'&&!e.np)continue;
  if(f.dado==='news'&&!e.nn)continue;
  if(f.dado==='crit_fed'&&!temCritico(e,'federal'))continue;
  if(f.dado==='crit_est'&&!temCritico(e,'estadual'))continue;
  if(f.dado==='sgb'&&!e.sgb)continue;
  if(f.q&&!buscaPorI.get(e.i).includes(f.q))continue;
  linhas.push({e,ps,cf,v:valorMetrica(e,f,per,ps)});}
 linhas.sort((a,b)=>b.v-a.v||a.e.nome.localeCompare(b.e.nome));
 // Puxadores: o menor grupo que soma 80% da CFEM do recorte no período (Pareto).
 const porCfem=[...linhas].sort((a,b)=>b.cf-a.cf),total=porCfem.reduce((s,l)=>s+l.cf,0);
 S.puxadores=new Set();let acc=0;
 if(total>0)for(const l of porCfem){if(acc>=0.8*total)break;S.puxadores.add(l.e.i);acc+=l.cf}
 S.cfemTotal=total;S.universo=linhas;S.f=f;S.per=per;
 const n=f.top==='all'?linhas.length:+f.top;
 S.ranking=linhas.slice(0,n);}

// ------------------------------------------------------------------ cabeçalho do recorte
function metricas(){
 const u=S.universo,procs=u.reduce((s,l)=>s+l.ps.length,0),per=S.per.join('–');
 const parcial=S.per[1]>=2026?' · '+t('ea.parcial2026',{meses:String(D.meta.meses_cfem_2026.length)}):'';
 el('ea-metrics').innerHTML=[
  ['a',t('ea.m.empresas'),num(u.length),t('ea.m.empresasSub',{total:num(E.length)})],
  ['b',t('ea.m.processos'),num(procs),t('ea.m.processosSub')],
  ['c',t('ea.m.cfem',{per}),brl(S.cfemTotal),t('ea.m.cfemSub')+parcial],
  ['d',t('ea.m.puxadores'),num(S.puxadores.size),t('ea.m.puxadoresSub',{per})],
 ].map(([tom,r,v,d])=>`<div class="metric tone-${tom}"><span>${escape(r)}</span><strong>${escape(v)}</strong><small>${escape(d)}</small></div>`).join('');
 const f=S.f,chips=[];
 if(f.mun!=='')chips.push(D.dims.mun[+f.mun][1]);
 if(f.min!=='')chips.push(D.dims.min[+f.min][0]);
 if(f.grupo)chips.push(rotuloGrupo(f.grupo));
 if(f.dado)chips.push(el('ea-dado').selectedOptions[0].textContent);
 if(f.q)chips.push('“'+el('ea-busca').value.trim()+'”');
 el('ea-context').innerHTML=escape(t('ea.contexto',{n:num(S.ranking.length),u:num(u.length),metrica:rotuloMetrica(f.metrica),per}))
  +(chips.length?' · '+chips.map(c=>`<span class="pill">${escape(c)}</span>`).join(' '):'');}

// ------------------------------------------------------------------ lista lateral (Top N)
const POR_PAG=12;
function fmtMetrica(v,m){return m==='cfem'?brl(v):m==='area'?num(v,0)+' ha':m==='ccee'?num(v,0)+' MWh':num(v);}
function lista(){
 const rk=S.ranking,m=S.f.metrica,max=Math.max(...rk.map(l=>l.v),1),pags=Math.max(1,Math.ceil(rk.length/POR_PAG));
 S.pag=Math.min(S.pag,pags-1);
 const fatia=rk.slice(S.pag*POR_PAG,(S.pag+1)*POR_PAG);
 el('ea-lista-titulo').textContent=t('ea.listaT',{n:num(rk.length),metrica:rotuloMetrica(m)});
 el('ea-lista').innerHTML=fatia.length?fatia.map((l,j)=>{
  const e=l.e,pos=S.pag*POR_PAG+j+1,on=S.sel===e.i;
  return `<li><button type="button" class="ea-item${on?' on':''}" data-i="${e.i}" aria-pressed="${on}">`
   +`<span class="ea-pos">${pos}</span><span class="ea-nome"><b>${escape(e.nome)}</b>`
   +`<small>${escape(cnpjFmt(e.cnpj))}${e.grupo?' · '+escape(e.grupo):''}</small>`
   +`<span class="ea-barra"><i style="width:${(l.v/max*100).toFixed(1)}%"></i></span></span>`
   +`<span class="ea-val">${escape(fmtMetrica(l.v,m))}${S.puxadores.has(e.i)?`<em class="ea-tag-pux" title="${escape(t('ea.puxadorTip'))}">${escape(t('ea.puxador'))}</em>`:''}`
   +`${e.enr?`<em class="ea-tag-enr" title="${escape(t('ea.enrTip'))}">${escape(t('ea.enr'))}</em>`:''}</span></button></li>`}).join('')
  :`<li class="empty">${escape(t('ea.vazio'))}</li>`;
 el('ea-pag').innerHTML=pags>1?`<button type="button" class="link-button" data-pag="-1" ${S.pag?'':'disabled'}>← ${escape(t('ea.anterior'))}</button>`
  +`<span>${escape(t('ea.pagina',{p:String(S.pag+1),n:String(pags)}))}</span>`
  +`<button type="button" class="link-button" data-pag="1" ${S.pag<pags-1?'':'disabled'}>${escape(t('ea.proxima'))} →</button>`:'';
 el('ea-lista').querySelectorAll('.ea-item').forEach(b=>b.onclick=()=>selecionar(+b.dataset.i,{origem:'lista'}));
 el('ea-pag').querySelectorAll('[data-pag]').forEach(b=>b.onclick=()=>{S.pag+=+b.dataset.pag;lista()});}

// ------------------------------------------------------------------ busca com autocomplete (combobox ARIA)
let sugestoes=[],ativa=-1,consultaSugerida=null;
function sugerir(){
 const q=norm(el('ea-busca').value.trim()),box=el('ea-sugestoes');consultaSugerida=q;
 if(q.length<2){fecharSugestoes();return}
 const out=[],dig=soDigitos(q);
 // processo ANM: '860.337/2020' = '860337/2020' = '8603372020'
 if(dig.length>=6){for(const[id,k]of procPorId){if(id.startsWith(dig)){const r=D.processos.rows[k];
   out.push({tipo:'processo',k,rot:r[PC.processo],sub:r[PC.empresa]>=0?porI.get(r[PC.empresa]).nome:t(r[PC.empresa]===-2?'ea.pf':'ea.semTitular')});if(out.length>=5)break}}}
 for(const x of idxBusca){if(x.txt.includes(q)){const e=porI.get(x.i);out.push({tipo:'empresa',i:e.i,rot:e.nome,sub:cnpjFmt(e.cnpj)+(e.grupo?' · '+e.grupo:'')});if(out.filter(o=>o.tipo==='empresa').length>=8)break}}
 D.dims.mun.forEach((m,k)=>{if(norm(m[1]).includes(q)&&out.filter(o=>o.tipo==='mun').length<4)out.push({tipo:'mun',k,rot:m[1],sub:t('ea.sug.mun')})});
 D.dims.min.forEach((m,k)=>{if(norm(m[0]).includes(q)&&out.filter(o=>o.tipo==='min').length<4)out.push({tipo:'min',k,rot:m[0],sub:t('ea.sug.min')})});
 sugestoes=out.slice(0,16);ativa=-1;
 const rotTipo={empresa:t('ea.sug.empresa'),processo:t('ea.sug.processo'),mun:t('ea.sug.munT'),min:t('ea.sug.minT')};
 box.innerHTML=sugestoes.length?sugestoes.map((s,j)=>`<li role="option" id="ea-sug-${j}" data-j="${j}" aria-selected="false">`
   +`<span class="ea-sug-tipo">${escape(rotTipo[s.tipo])}</span><b>${escape(s.rot)}</b><small>${escape(s.sub)}</small></li>`).join('')
  :`<li class="ea-sug-vazia" role="option" aria-disabled="true">${escape(t('ea.semSugestao'))}</li>`;
 box.hidden=false;el('ea-busca').setAttribute('aria-expanded','true');
 box.querySelectorAll('[data-j]').forEach(li=>li.onmousedown=ev=>{ev.preventDefault();escolher(+li.dataset.j)});}
function fecharSugestoes(){el('ea-sugestoes').hidden=true;el('ea-busca').setAttribute('aria-expanded','false');el('ea-busca').removeAttribute('aria-activedescendant')}
function marcar(j){const lis=[...el('ea-sugestoes').querySelectorAll('[data-j]')];lis.forEach((li,k)=>li.setAttribute('aria-selected',String(k===j)));
 ativa=j;if(lis[j]){el('ea-busca').setAttribute('aria-activedescendant',lis[j].id);lis[j].scrollIntoView({block:'nearest'})}}
function escolher(j){
 const s=sugestoes[j];if(!s)return;fecharSugestoes();
 if(s.tipo==='empresa'){el('ea-busca').value='';redesenhar();selecionar(s.i,{origem:'busca'})}
 else if(s.tipo==='processo'){const r=D.processos.rows[s.k];el('ea-busca').value='';redesenhar();
  if(r[PC.empresa]>=0)selecionar(r[PC.empresa],{origem:'busca',processo:s.k});else{S.destaque=s.k;estadoBotoesMapa();const av=t(r[PC.empresa]===-2?'ea.pfAviso':'ea.semTitularAviso');
  geometria().catch(()=>null).then(()=>{S.tela.repintar();irParaProcesso(s.k);avisoMapa(av)})}}
 else if(s.tipo==='mun'){el('ea-busca').value='';el('ea-mun').value=String(s.k);redesenhar()}
 else if(s.tipo==='min'){el('ea-busca').value='';el('ea-min').value=String(s.k);redesenhar()}}

// ------------------------------------------------------------------ mapa
// Pontos finos: cada direito minerário de empresa é um ponto no centroide do título, na cor do grupo de fase. Pontos, polígonos ANM
// e contornos de município são desenhados numa camada Canvas única, a partir de coordenadas projetadas uma vez só: mover ou aproximar
// só repinta, sem criar objetos do Leaflet. O ponto cresce com o zoom; com empresa escolhida, os demais ficam cinza.
// Navegação: roda do mouse direto (1 nível por dente), limites em Goiás, botões Goiás inteiro / enquadrar empresa / tela cheia;
// desmarcar com segundo clique, clique numa área vazia, Esc ou a etiqueta da seleção.
const BOUNDS=[[-19.6,-53.4],[-12.3,-45.8]];
const ORDEM_DESENHO={pesquisa:0,disponibilidade:1,outro:1,requerimento_lavra:2,lavra_autorizada:3};
const MP={n:0};   // pontos do mapa: processos de titular PJ com centroide, na ordem de desenho (pesquisa por baixo, lavra por cima)
const goBounds=()=>S.go||L.latLngBounds(BOUNDS);
const ZOOM_POLIGONOS=11.5;
function prepararPontos(){
 const R=D.processos.rows,crs=L.CRS.EPSG3857,ks=[];
 const gi=k=>{const g=GRUPOS.indexOf(D.dims.fase[R[k][PC.fase]].grupo);return g<0?GRUPOS.length-1:g};
 for(let k=0;k<R.length;k++)if(R[k][PC.lat]!=null&&R[k][PC.empresa]>=0)ks.push(k);
 ks.sort((a,b)=>ORDEM_DESENHO[GRUPOS[gi(a)]]-ORDEM_DESENHO[GRUPOS[gi(b)]]||a-b);
 const n=ks.length;Object.assign(MP,{n,k:Int32Array.from(ks),x:new Float64Array(n),y:new Float64Array(n),g:new Uint8Array(n),j:new Int32Array(R.length).fill(-1)});
 ks.forEach((k,j)=>{const p=crs.latLngToPoint(L.latLng(R[k][PC.lat],R[k][PC.lon]),0);MP.x[j]=p.x;MP.y[j]=p.y;MP.g[j]=gi(k);MP.j[k]=j});
 S.vis=new Uint8Array(R.length);S.selMarca=new Uint8Array(R.length);S.selJ=[];}

const RAIOS=[[5,1.3],[6,1.5],[7,1.9],[8,2.4],[9,2.9],[10,3.4],[11,4],[12,4.6],[13,5.2],[16,6.2]];
function raioPonto(z){for(let i=1;i<RAIOS.length;i++)if(z<=RAIOS[i][0]){const [z0,r0]=RAIOS[i-1],[z1,r1]=RAIOS[i];return r0+(r1-r0)*Math.max(0,Math.min(1,(z-z0)/(z1-z0)))}return 6.2}
const raioSel=z=>Math.max(3.4,raioPonto(z)*1.3+1);
// Hierarquia de fase: lavra autorizada maior e mais forte, requerimento médio, pesquisa/disponibilidade menores e claras.
// O olho vai primeiro ao que está mais perto da produção, sem esconder nenhum título.
const HIER_RAIO={lavra_autorizada:1.45,requerimento_lavra:1.1,pesquisa:.75,disponibilidade:.75,outro:.75};
const HIER_ALFA={lavra_autorizada:.95,requerimento_lavra:.85,pesquisa:.42,disponibilidade:.42,outro:.42};
function estiloFase(gi,z){const g=GRUPOS[gi];return {r:raioPonto(z)*HIER_RAIO[g],a:HIER_ALFA[g],traco:g==='lavra_autorizada'?z>=8:z>=10}}
// Fases desligadas pela legenda (só no mapa; lista e indicadores seguem o filtro Fase da barra de filtros). Não é lembrado entre visitas.
S.off=new Set();
const faseVisivel=gi=>!S.off.has(gi);

// Anéis em coordenadas de zoom 0 (lista plana x,y), com a caixa para descartar rápido o que está fora da tela.
function projetarAneis(rings){
 const crs=L.CRS.EPSG3857;let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
 const out=rings.filter(r=>r.length>2).map(r=>{const a=new Float64Array(r.length*2);
  for(let i=0;i<r.length;i++){const q=crs.latLngToPoint(L.latLng(r[i][0],r[i][1]),0);a[2*i]=q.x;a[2*i+1]=q.y;
   if(q.x<x0)x0=q.x;if(q.x>x1)x1=q.x;if(q.y<y0)y0=q.y;if(q.y>y1)y1=q.y}return a});
 return out.length?{rings:out,bb:[x0,y0,x1,y1]}:null}
// Contornos de município simplificados (Douglas-Peucker do próprio Leaflet, tolerância de 0,7 px) para cada meio nível de zoom,
// calculados na primeira vez que o zoom aparece: no estado inteiro, dos ~49 mil vértices sobra uma fração.
function munNoZoom(z){
 const zk=Math.round(z*2)/2;S.munSimp=S.munSimp||new Map();let c=S.munSimp.get(zk);if(c)return c;
 const tol=.7/Math.pow(2,zk);
 c=S.munProj.map(p=>({bb:p.bb,rings:p.rings.map(a=>{const pts=[];for(let i=0;i<a.length;i+=2)pts.push(L.point(a[i],a[i+1]));
  const sm=L.LineUtil.simplify(pts,tol),out=new Float64Array(sm.length*2);sm.forEach((q,i)=>{out[2*i]=q.x;out[2*i+1]=q.y});return out})}));
 S.munSimp.set(zk,c);return c}
// Polígono ANM do processo k, projetado na primeira vez que é pedido (depois de loadProcesses).
const PROJ=new Map();
function projetado(k){
 if(PROJ.has(k))return PROJ.get(k);if(!S.geo)return null;
 const geo=S.geo.get(D.processos.rows[k][PC.processo]),p=geo&&geo.rings.length?projetarAneis(geo.rings):null;PROJ.set(k,p);return p}
function dentroPoligono(p,X,Y){
 const b=p.bb;if(X<b[0]||X>b[2]||Y<b[1]||Y>b[3])return false;let d=false;
 for(const a of p.rings)for(let i=0,j=a.length-2;i<a.length;j=i,i+=2){const xi=a[i],yi=a[i+1],xj=a[j],yj=a[j+1];
  if((yi>Y)!==(yj>Y)&&X<(xj-xi)*(Y-yi)/(yj-yi)+xi)d=!d}
 return d}

// Índice espacial em grade (pixels da camada) para tooltip e clique; montado só na primeira consulta depois de cada desenho.
const GRADE={T:14,cel:new Map(),pend:null,
 limpar(){this.cel.clear();this.pend=null},
 add(j,x,y){const k=Math.floor(x/this.T)*1e6+Math.floor(y/this.T);let a=this.cel.get(k);if(!a)this.cel.set(k,a=[]);a.push(j,x,y)},
 perto(x,y,rr){if(this.pend){const f=this.pend;this.pend=null;f()}
  const out=[],cx=Math.floor(x/this.T),cy=Math.floor(y/this.T),R2=rr*rr;
  for(let i=cx-1;i<=cx+1;i++)for(let k=cy-1;k<=cy+1;k++){const a=this.cel.get(i*1e6+k);if(!a)continue;
   for(let m=0;m<a.length;m+=3){const dx=a[m+1]-x,dy=a[m+2]-y,d=dx*dx+dy*dy;if(d<=R2)out.push([d,a[m]])}}
  out.sort((p,q)=>p[0]-q[0]);return [...new Set(out.map(p=>p[1]))]}};

// Desenho, de baixo para cima: contornos de município, polígonos da área (zoom ≥ 11,5), polígonos da empresa, processo destacado,
// pontos do recorte e pontos da empresa. Os pontos vão um a um (pontos sobrepostos se adensam), na ordem
// pesquisa → disponibilidade → requerimento → lavra: com rasterização forçada, foi o mais rápido dos jeitos medidos no Edge sem GPU.
const ORDEM_GRUPOS=['pesquisa','disponibilidade','outro','requerimento_lavra','lavra_autorizada'].map(g=>GRUPOS.indexOf(g));
function pintarMapa(ctx,b){
 GRADE.limpar();S.nPontos=0;S.poliDesenhados=[];if(!MP.n||!S.mapa)return;
 const m=S.mapa,z=m.getZoom(),o=m.getPixelOrigin(),s=Math.pow(2,z),r=raioPonto(z),pad=12,x0=b.min.x-pad,x1=b.max.x+pad,y0=b.min.y-pad,y1=b.max.y+pad;
 const X0=(b.min.x+o.x)/s,X1=(b.max.x+o.x)/s,Y0=(b.min.y+o.y)/s,Y1=(b.max.y+o.y)/s;   // caixa da tela em zoom 0
 const fora=bb=>bb[2]<X0||bb[0]>X1||bb[3]<Y0||bb[1]>Y1;
 const comSel=S.sel!==null,so=comSel&&S.soSel,TAU=Math.PI*2;
 const caminho=p=>{ctx.beginPath();for(const a of p.rings){for(let i=0;i<a.length;i+=2){const x=a[i]*s-o.x,y=a[i+1]*s-o.y;if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y)}ctx.closePath()}};
 // contornos de município (referência): um traço só, com os anéis simplificados para o zoom (como o Leaflet faria)
 if(S.munProj){ctx.beginPath();
  for(const p of munNoZoom(z)){if(fora(p.bb))continue;
   for(const a of p.rings){for(let i=0;i<a.length;i+=2){const x=a[i]*s-o.x,y=a[i+1]*s-o.y;if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y)}ctx.closePath()}}
  ctx.globalAlpha=.6;ctx.lineWidth=.5;ctx.strokeStyle='#9fb3c2';ctx.stroke();ctx.globalAlpha=1}
 // polígonos: os da área visível (zoom alto, opcional) e os da empresa escolhida
 const poli=(k,alfaFundo,larg,cor)=>{const p=projetado(k);if(!p||fora(p.bb))return;const c=COR[D.dims.fase[D.processos.rows[k][PC.fase]].grupo]||COR.outro;
  caminho(p);ctx.globalAlpha=alfaFundo;ctx.fillStyle=c;ctx.fill('evenodd');ctx.globalAlpha=1;ctx.lineWidth=larg;ctx.strokeStyle=cor||c;ctx.stroke();S.poliDesenhados.push(k)};
 if(S.geo){
  if(z>=ZOOM_POLIGONOS&&el('ea-poligonos').checked&&!so){
   const mx=(X1-X0)*.5,my=(Y1-Y0)*.5;let n=0;   // centroide até meia tela além da borda: cobre títulos grandes que entram pela lateral
   for(let j=0;j<MP.n&&n<1500;j++){const k=MP.k[j];if(!S.vis[k]||(comSel&&S.selMarca[k])||k===S.destaque||!faseVisivel(MP.g[j]))continue;
    if(MP.x[j]<X0-mx||MP.x[j]>X1+mx||MP.y[j]<Y0-my||MP.y[j]>Y1+my)continue;poli(k,.12,.8);n++}}
  if(comSel)for(const j of S.selJ){const k=MP.k[j];if(k!==S.destaque&&faseVisivel(MP.g[j]))poli(k,.28,1.4)}
  if(S.destaque!==null)poli(S.destaque,.45,3,'#062844')}
 // pontos
 const fundo=j=>!so&&S.vis[MP.k[j]]&&!(comSel&&S.selMarca[MP.k[j]])&&faseVisivel(MP.g[j]);
 const selVis=S.selJ.filter(j=>faseVisivel(MP.g[j]));
 const circulos=(teste,raio,traco,lista)=>{let c=0;const um=j=>{if(!teste(j))return;const x=MP.x[j]*s-o.x,y=MP.y[j]*s-o.y;
   if(x<x0||x>x1||y<y0||y>y1)return;ctx.beginPath();ctx.arc(x,y,raio,0,TAU);ctx.fill();if(traco)ctx.stroke();c++};
  if(lista)lista.forEach(um);else for(let j=0;j<MP.n;j++)um(j);return c};
 let n=0;
 if(!so&&comSel){   // com empresa escolhida, o resto do recorte fica cinza e menor
  ctx.globalAlpha=.32;ctx.fillStyle='#8d9eab';n+=circulos(fundo,Math.max(1.2,r*.85),false);ctx.globalAlpha=1}
 else if(!so){
  ctx.lineWidth=.8;ctx.strokeStyle='rgba(255,255,255,.9)';
  for(const g of ORDEM_GRUPOS){const st=estiloFase(g,z);ctx.globalAlpha=st.a;ctx.fillStyle=COR[GRUPOS[g]];n+=circulos(j=>MP.g[j]===g&&fundo(j),st.r,st.traco)}
  ctx.globalAlpha=1}
 if(comSel&&selVis.length){   // a empresa escolhida, por cima: halo branco, cor da fase e contorno azul-marinho
  const rs=raioSel(z);ctx.fillStyle='rgba(255,255,255,.95)';circulos(()=>true,rs+1.6,false,selVis);
  ctx.lineWidth=1.4;ctx.strokeStyle='#062844';
  for(const g of ORDEM_GRUPOS){ctx.fillStyle=COR[GRUPOS[g]];n+=circulos(j=>MP.g[j]===g,rs,true,selVis)}}
 S.nPontos=n;
 GRADE.pend=()=>{const vai=j=>{const x=MP.x[j]*s-o.x,y=MP.y[j]*s-o.y;if(x>=x0&&x<=x1&&y>=y0&&y<=y1)GRADE.add(j,x,y)};
  for(let j=0;j<MP.n;j++)if(fundo(j))vai(j);if(comSel)selVis.forEach(vai)};}

// Camada Canvas do mapa: o L.Canvas do Leaflet cuida do tamanho, da posição e da escala durante a animação de zoom;
// aqui só se troca o desenho (nenhuma camada vetorial usa este renderer).
let Tela=null;
function classeTela(){return Tela||(Tela=L.Canvas.extend({
 _draw(){if(!this._map)return;const t0=performance.now();this._ctx.save();pintarMapa(this._ctx,this._bounds);this._ctx.restore();this.ms=performance.now()-t0},
 repintar(){if(this._map&&this._ctx)this._redraw()}}))}

function htmlProcesso(k){
 const r=D.processos.rows[k],e=r[PC.empresa],gr=D.dims.fase[r[PC.fase]].grupo,mi=D.dims.min[r[PC.mineral]];
 return `<b>${escape(r[PC.processo])}</b> · <span style="color:${COR[gr]||COR.outro}">●</span> ${escape(D.dims.fase[r[PC.fase]].nome)}`
  +`<br>${escape(e>=0?porI.get(e).nome:t(e===-2?'ea.pf':'ea.semTitular'))}<small>${escape(mi?mi[0]:'—')}</small>`}
// O que está sob o pixel: primeiro os pontos (índice em grade), depois os polígonos desenhados, de cima para baixo.
function acertar(lp){
 const m=S.mapa,z=m.getZoom(),js=GRADE.perto(lp.x,lp.y,Math.max(7,raioPonto(z)*HIER_RAIO.lavra_autorizada+3));
 if(js.length)return {tipo:'ponto',ks:js.map(j=>MP.k[j])};
 const o=m.getPixelOrigin(),s=Math.pow(2,z),X=(lp.x+o.x)/s,Y=(lp.y+o.y)/s,ps=S.poliDesenhados||[];
 for(let i=ps.length-1;i>=0;i--){const p=PROJ.get(ps[i]);if(p&&dentroPoligono(p,X,Y))return {tipo:'poligono',ks:[ps[i]]}}
 return null}
function esconderHover(){
 if(!S.mapa)return;if(S.tip&&S.mapa.hasLayer(S.tip))S.tip.close();if(S.anel&&S.mapa.hasLayer(S.anel))S.anel.remove();S.mapa.getContainer().style.cursor=''}
function sondar(){
 S.rafMov=0;const ev=S.ultimoMov,m=S.mapa;if(!ev||!m)return;
 if(m.dragging.moving()||m._animatingZoom){esconderHover();return}
 const cp=m.mouseEventToContainerPoint(ev),h=acertar(m.containerPointToLayerPoint(cp));
 if(!h){esconderHover();return}
 m.getContainer().style.cursor='pointer';
 const k=h.ks[0],R=D.processos.rows;let ll=m.containerPointToLatLng(cp),dy=-8;
 if(h.tipo==='ponto'){
  ll=L.latLng(R[k][PC.lat],R[k][PC.lon]);const z=m.getZoom(),w=Math.round((R[k][PC.empresa]===S.sel?raioSel(z):estiloFase(MP.g[MP.j[k]],z).r)*2+8);dy=-w/2;
  if(!S.anel)S.anel=L.marker(ll,{interactive:false,keyboard:false,icon:L.divIcon({className:'ea-anel',html:'<i></i>',iconSize:[w,w]})});
  S.anel.setLatLng(ll);if(S.anel._eaW!==w){S.anel.setIcon(L.divIcon({className:'ea-anel',html:'<i></i>',iconSize:[w,w]}));S.anel._eaW=w}
  if(!m.hasLayer(S.anel))S.anel.addTo(m)}
 else if(S.anel&&m.hasLayer(S.anel))S.anel.remove();
 const mais=h.ks.length>1?`<small>${escape(t('ea.maisAqui',{n:num(h.ks.length-1)}))}</small>`:'';
 const dica=k===S.destaque?`<small>${escape(t('ea.cliqueDesmarca'))}</small>`:'';
 if(!S.tip)S.tip=L.tooltip({direction:'top',className:'ea-tip',opacity:1});
 S.tip.options.offset=[0,dy];S.tip.setLatLng(ll).setContent(htmlProcesso(k)+mais+dica);if(!m.hasLayer(S.tip))S.tip.addTo(m);else S.tip.update()}

const ICONE={go:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>',
 emp:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>',
 cheia:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>'};
function botoesMapa(){
 const Ctl=L.Control.extend({options:{position:'topleft'},onAdd(){
  const d=L.DomUtil.create('div','leaflet-bar ea-ctl');
  const b=(a,ic,txt)=>`<a href="#" role="button" data-a="${a}" title="${escape(txt)}" aria-label="${escape(txt)}">${ic}</a>`;
  d.innerHTML=b('go',ICONE.go,t('ea.voltarGo'))+b('emp',ICONE.emp,t('ea.enquadrarEmp'))+b('cheia',ICONE.cheia,t('ea.telaCheia'));
  L.DomEvent.disableClickPropagation(d);L.DomEvent.disableScrollPropagation(d);
  d.addEventListener('click',ev=>{const a=ev.target.closest('a');if(!a)return;L.DomEvent.stop(ev);
   if(a.dataset.a==='go')S.mapa.fitBounds(goBounds(),{padding:[10,10]});
   else if(a.dataset.a==='emp'){if(S.sel!==null){S.destaque=null;desenharSelecao(true)}}
   else telaCheia()});
  return d}});
 S.botoes=new Ctl().addTo(S.mapa);
 // etiqueta da seleção, no alto do mapa: mostra o que está marcado e desmarca com um clique
 const Etiqueta=L.Control.extend({options:{position:'topright'},onAdd(){
  const d=L.DomUtil.create('div','ea-chip-sel');d.hidden=true;
  L.DomEvent.disableClickPropagation(d);L.DomEvent.disableScrollPropagation(d);
  // o botão some no próprio clique; sem parar o evento aqui, o Leaflet o trataria como clique no mapa e selecionaria o ponto de baixo
  d.addEventListener('click',ev=>{L.DomEvent.stop(ev);if(ev.target.closest('button'))desmarcar()});return d}});
 S.etiqueta=new Etiqueta().addTo(S.mapa);estadoBotoesMapa()}
function estadoBotoesMapa(){
 if(!S.botoes)return;const c=S.botoes.getContainer(),a=c.querySelector('[data-a="emp"]');
 a.classList.toggle('ea-desligado',S.sel===null);a.setAttribute('aria-disabled',String(S.sel===null));
 const cheia=c.querySelector('[data-a="cheia"]'),on=emTelaCheia(),txt=t(on?'ea.sairTelaCheia':'ea.telaCheia');cheia.title=txt;cheia.setAttribute('aria-label',txt);
 const d=S.etiqueta&&S.etiqueta.getContainer();if(!d)return;
 const nome=S.sel!==null?porI.get(S.sel).nome:S.destaque!==null?`${t('ea.processo')} ${D.processos.rows[S.destaque][PC.processo]}`:null;
 if(!nome){d.hidden=true;d.innerHTML='';return}
 d.hidden=false;
 d.innerHTML=`<span class="ea-chip-rot">${escape(t('ea.selecionada'))}</span><b title="${escape(nome)}">${escape(nome)}</b>`
  +`<button type="button" aria-label="${escape(t('ea.limparSelecao'))}" title="${escape(t('ea.limparSelecaoDica'))}">×</button>`}
// Links das bases (notícias coletadas na web, RI, fontes): só http(s); qualquer outro esquema vira link vazio, nunca javascript:.
const urlSegura=u=>/^https?:\/\//i.test(String(u??''))?String(u):'#';
const painelMapa=()=>document.querySelector('#empresas-view .ea-map-panel');
// A aba Empresas tem sub-abas: o Atlas só reage ao teclado quando a aba e a sub-aba dele estão à vista.
const atlasVisivel=()=>!el('empresas-view').hidden&&!(el('ep-aba-atlas')&&el('ep-aba-atlas').hidden);
const emTelaCheia=()=>{const p=painelMapa();return !!p&&(document.fullscreenElement===p||p.classList.contains('ea-cheia'))};
function telaCheia(){
 const p=painelMapa();if(!p)return;
 if(emTelaCheia()){p.classList.remove('ea-cheia');if(document.fullscreenElement)document.exitFullscreen().catch(()=>null)}
 else if(p.requestFullscreen&&document.fullscreenEnabled)p.requestFullscreen().catch(()=>p.classList.add('ea-cheia'));
 else p.classList.add('ea-cheia');   // sem a API (Safari do iPhone): uma camada fixa sobre a página faz o mesmo
 setTimeout(()=>{estadoBotoesMapa();S.mapa.invalidateSize()},120)}

// Desmarca a empresa (ficha, URL e painel de produção acompanham) ou, sem empresa, o processo destacado pela busca.
function desmarcar(){
 if(S.sel!==null){limparSelecao();return}
 if(S.destaque!==null){S.destaque=null;avisoMapa('');estadoBotoesMapa();S.tela.repintar()}}
const temPopup=()=>!!(S.mapa&&S.mapa._popup&&S.mapa.hasLayer(S.mapa._popup));

// Contorno de Goiás e máscara do entorno, como no Atlas e no Mapa Mineral (camada limite_goias do IBGE). Sem ela, o mapa segue igual.
async function focoGoias(rm){
 if(!window.MapaDados)return;
 try{const go=await window.MapaDados.camada('limite_goias'),partes=go.partes.flat();
  S.go=L.latLngBounds(partes.flat());S.mapa.setMaxBounds(S.go.pad(.4));
  L.polygon([[[-89,-179.9],[-89,179.9],[89,179.9],[89,-179.9]],...partes],{pane:'ea-mascara',renderer:rm,stroke:false,fillRule:'evenodd',
   fillColor:'#eef3f7',fillOpacity:.62,interactive:false}).addTo(S.mapa);
  L.polygon(partes,{pane:'ea-mascara',renderer:rm,color:'#35566d',weight:1.4,opacity:.85,fill:false,interactive:false}).addTo(S.mapa)}
 catch{/* sem o contorno: sem máscara, limites pela caixa de Goiás */}}

function criarMapa(){
 if(S.mapa||!window.L)return;
 // um dente da roda ≈ 1 nível de zoom: o Leaflet divide o giro da roda pela escala da tela, então o passo também é dividido
 // (36 px a 100%, 24 px a 150%...); botões +/− andam 1 nível
 const m=L.map('ea-map',{preferCanvas:true,zoomControl:false,minZoom:6,maxZoom:16,zoomSnap:.5,zoomDelta:1,wheelPxPerZoomLevel:36/(window.devicePixelRatio||1),wheelDebounceTime:30,
  maxBounds:L.latLngBounds(BOUNDS).pad(.4)}).fitBounds(BOUNDS);
 S.mapa=m;
 L.control.zoom({zoomInTitle:t('ea.aproximar'),zoomOutTitle:t('ea.afastar')}).addTo(m);
 botoesMapa();
 L.control.scale({imperial:false}).addTo(m);
 // OpenStreetMap em cinza claro (filtro CSS), para o fundo não competir com as cores das fases
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,className:'ea-osm-suave',opacity:.62,
  attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(m);
 m.createPane('ea-mascara').style.zIndex=350;m.getPane('ea-mascara').style.pointerEvents='none';
 m.createPane('ea-pontos').style.zIndex=450;m.getPane('ea-pontos').style.pointerEvents='none';
 S.camadas.operacao=L.layerGroup().addTo(m);
 S.tela=new (classeTela())({pane:'ea-pontos',padding:.3}).addTo(m);
 focoGoias(L.canvas({pane:'ea-mascara',padding:.4}));
 m.on('moveend',poligonosVisiveis);
 m.on('movestart zoomstart',esconderHover);
 // clique: ponto ou polígono abre a empresa; de novo no destacado desmarca; área vazia desmarca (se havia lista aberta, só a fecha)
 m.on('preclick',()=>{S.popupNoClique=temPopup()});
 m.on('click',ev=>{
  const h=acertar(ev.layerPoint);
  if(h){if(S.destaque!==null&&h.ks[0]===S.destaque&&!S.popupNoClique){desmarcar();return}clicarPontos(h.ks,ev.latlng);return}
  if(!S.popupNoClique)desmarcar()});
 const c=m.getContainer();
 c.addEventListener('mousemove',ev=>{S.ultimoMov=ev;if(!S.rafMov)S.rafMov=requestAnimationFrame(sondar)});
 c.addEventListener('mouseleave',()=>{S.ultimoMov=null;esconderHover()});
 document.addEventListener('fullscreenchange',()=>setTimeout(()=>{estadoBotoesMapa();m.invalidateSize()},60));
 // Esc: sai da tela cheia (camada fixa), fecha a lista aberta ou desmarca; não age com a aba escondida nem dentro de campos
 document.addEventListener('keydown',ev=>{
  if(ev.key!=='Escape')return;
  const p=painelMapa();if(p&&p.classList.contains('ea-cheia')){telaCheia();return}
  if(!atlasVisivel())return;
  if(temPopup()){m.closePopup();return}
  const a=document.activeElement;if(a&&/^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName))return;
  desmarcar()});
 setTimeout(()=>{m.invalidateSize();m.fitBounds(goBounds(),{padding:[10,10]})},80);
 new ResizeObserver(()=>m.invalidateSize({pan:false})).observe(el('ea-map'));
 // municípios (referência) vêm do pacote do Atlas, compartilhado com as outras abas
 (window.loadAtlas?window.loadAtlas():api('/atlas')).then(a=>{
  S.munCentro=new Map();S.munProj=[];
  for(const mu of a.municipalities){
   const rings=mu.rings||[],p=projetarAneis(rings);if(p)S.munProj.push(p);
   // centro aproximado do município: média dos vértices do maior anel
   const r=rings.reduce((a,b)=>b.length>a.length?b:a,[]);
   if(r.length)S.munCentro.set(mu.code,[r.reduce((s,p)=>s+p[0],0)/r.length,r.reduce((s,p)=>s+p[1],0)/r.length]);}
  S.tela.repintar();if(S.sel!==null)desenharOperacao();
 }).catch(()=>{});}

function procsDoMapa(){
 // Pontos do recorte: processos das empresas do universo que passam pelo filtro territorial.
 const out=[];for(const l of S.universo)for(const k of l.ps)out.push(k);return out;}

// Recalcula o que aparece (recorte e empresa selecionada) e pede um desenho novo da camada.
function desenharPontos(){
 if(!S.mapa||!MP.n)return;
 const so=S.sel!==null&&el('ea-so-sel').checked,R=D.processos.rows;
 S.vis.fill(0);for(const k of procsDoMapa())S.vis[k]=1;
 S.soSel=so;S.selMarca=S.selMarca||new Uint8Array(R.length);S.selMarca.fill(0);S.selJ=[];
 if(S.sel!==null){
  const ks=so?procsFiltrados(S.sel,S.f):procsFiltrados(S.sel,{mun:'',min:'',grupo:''});
  for(const k of ks)if(MP.j[k]>=0){S.selMarca[k]=1;S.selJ.push(MP.j[k])}
  S.selJ.sort((a,b)=>a-b)}
 esconderHover();estadoBotoesMapa();S.tela.repintar();}

// Clique em ponto ou polígono: uma empresa só → abre a ficha; várias sobrepostas → lista para escolher.
function clicarPontos(ks,ll){
 const R=D.processos.rows,empresas=[...new Set(ks.map(k=>R[k][PC.empresa]))];
 if(empresas.length===1&&empresas[0]>=0){selecionar(empresas[0],{origem:'mapa',processo:ks[0]});return}
 const itens=ks.slice(0,12).map(k=>{const r=R[k],e=r[PC.empresa];
  return `<li>${e>=0?`<button type="button" class="link-button" data-i="${e}" data-k="${k}">${escape(porI.get(e).nome)}</button>`:`<span class="muted">${escape(t(e===-2?'ea.pf':'ea.semTitular'))}</span>`}`
   +`<small>${escape(r[PC.processo])} · ${escape(D.dims.fase[r[PC.fase]].nome)}</small></li>`}).join('');
 const pop=L.popup({maxWidth:320}).setLatLng(ll).setContent(`<div class="ea-pop"><b>${escape(t('ea.sobrepostos',{n:String(ks.length)}))}</b><ul>${itens}</ul></div>`).openOn(S.mapa);
 pop.getElement().querySelectorAll('[data-i]').forEach(b=>b.onclick=()=>{S.mapa.closePopup();selecionar(+b.dataset.i,{origem:'mapa',processo:+b.dataset.k})});}

function avisoMapa(txt){el('ea-map-aviso').textContent=txt;el('ea-map-aviso').hidden=!txt}

async function geometria(){
 if(S.geo)return S.geo;
 avisoMapa(t('ea.carregandoPoligonos'));
 try{const g=await window.loadProcesses();S.geo=new Map(g.records.map(r=>[r.id,r]));avisoMapa('');return S.geo}
 catch(e){avisoMapa(t('ea.falhaPoligonos'));throw e}}

// Zoom alto: os polígonos da área são desenhados pela própria camada; aqui só se garante que a geometria (2,6 MB) foi carregada.
function poligonosVisiveis(){
 if(!S.mapa||S.geo||S.mapa.getZoom()<ZOOM_POLIGONOS||!el('ea-poligonos').checked)return;
 geometria().then(()=>S.tela.repintar()).catch(()=>{});}

// Empresa escolhida: enquadra (se pedido), carrega a geometria e repinta; irPara leva até o processo destacado
// (busca e tabela da ficha; pelo mapa, não: o usuário já está olhando para ele).
async function desenharSelecao(enquadrar,irPara){
 S.camadas.operacao.clearLayers();
 if(!S.mapa)return;
 if(S.sel===null){S.tela.repintar();return}
 const ks=procsFiltrados(S.sel,{mun:'',min:'',grupo:''}),R=D.processos.rows;
 const pts=ks.filter(k=>R[k][PC.lat]!=null).map(k=>[R[k][PC.lat],R[k][PC.lon]]);
 if(enquadrar&&pts.length&&S.destaque===null)S.mapa.fitBounds(L.latLngBounds(pts).pad(.25),{maxZoom:12});
 desenharOperacao();
 try{await geometria()}catch{return}
 if(S.sel===null)return;S.tela.repintar();
 if(irPara&&S.destaque!==null)irParaProcesso(S.destaque);}

// Município da operação declarada (só nas empresas com produção declarada): referência aproximada, quadrado vazado.
function desenharOperacao(){
 const g=S.camadas.operacao;g.clearLayers();
 const det=S.sel!==null&&D.detalhes[String(S.sel)];if(!det||!S.munCentro)return;
 for(const nome of det.municipios_operacao){
  const k=D.dims.mun.findIndex(m=>norm(m[1])===norm(nome));if(k<0)continue;
  const c=S.munCentro.get(D.dims.mun[k][0]);if(!c)continue;
  L.marker(c,{icon:L.divIcon({className:'ea-op-icone',html:'<i></i>',iconSize:[18,18]}),keyboard:false,
   title:t('ea.operacaoAprox',{mun:nome})}).bindTooltip(t('ea.operacaoAprox',{mun:nome}),{direction:'top'}).addTo(g)}}

function irParaProcesso(k){
 const r=D.processos.rows[k];if(r[PC.lat]==null||!S.mapa)return;
 const geo=S.geo&&S.geo.get(r[PC.processo]);
 if(geo&&geo.rings.length)S.mapa.fitBounds(L.latLngBounds(geo.rings.flat()).pad(.6),{maxZoom:14});else S.mapa.setView([r[PC.lat],r[PC.lon]],12);
 el('ea-map').scrollIntoView({block:'nearest',behavior:'smooth'});}

// ------------------------------------------------------------------ ficha da empresa
const ABAS=['perfil','territorio','economia','projetos','noticias','historico'];
const rotuloAba=a=>({perfil:t('ea.aba.perfil'),territorio:t('ea.aba.territorio'),economia:t('ea.aba.economia'),projetos:t('ea.aba.projetos'),
 noticias:t('ea.aba.noticias'),historico:t('ea.aba.historico')}[a]);

function selecionar(i,{origem='',processo=null,semHistorico=false}={}){
 if(!porI.has(i))return;
 S.sel=i;S.destaque=processo;S.ppag=0;
 if(processo!==null&&origem!=='mapa')S.aba='territorio';
 if(!semHistorico)try{history.pushState({ea:i},'',`#empresas/${porI.get(i).cnpj}`)}catch{}
 lista();ficha();desenharPontos();desenharSelecao(origem!=='mapa',origem!=='mapa');
 if(window.empresasSelecionar)window.empresasSelecionar(porI.get(i).cnpj);
 if(origem!=='mapa')el('ea-ficha').scrollIntoView({block:'start',behavior:'smooth'});
 el('ea-ficha-titulo').focus({preventScroll:origem==='mapa'});}

function limparSelecao(semHistorico){
 S.sel=null;S.destaque=null;el('ea-ficha').hidden=true;
 if(!semHistorico)try{history.pushState({ea:null},'','#empresas')}catch{}
 lista();desenharPontos();desenharSelecao();if(window.empresasSelecionar)window.empresasSelecionar('');}

function badgesCriticos(m){
 const c=criticosPorMin.get(m);if(!c)return '';
 return (c.federal.length?`<span class="ea-crit fed" title="${escape(D.criticos.federal.norma)}">${escape(t('ea.critFed'))}</span>`:'')
  +(c.estadual.length?`<span class="ea-crit est" title="${escape(D.criticos.estadual.norma)}">${escape(t('ea.critEst'))}</span>`:'');}

function ficha(){
 const e=porI.get(S.sel);if(!e)return;
 const det=D.detalhes[String(e.i)];
 el('ea-ficha').hidden=false;
 el('ea-ficha-titulo').textContent=e.nome;
 el('ea-ficha-sub').innerHTML=[`<span>${escape(t('ea.cnpjRaiz'))} <b>${escape(cnpjFmt(e.cnpj))}</b></span>`,
  e.grupo?`<span>${escape(t('ea.grupo'))} <b>${escape(e.grupo)}</b></span>`:'',
  e.enr?`<span class="pill">${escape(t('ea.enrLongo'))}</span>`:`<span class="pill ea-pill-muted">${escape(t('ea.indiceGeral'))}</span>`,
  S.puxadores.has(e.i)?`<span class="pill ea-pill-pux">${escape(t('ea.puxadorLongo',{per:S.per.join('–')}))}</span>`:''].join('');
 const naCmp=S.cmp.includes(e.i);
 el('ea-cmp-add').textContent=naCmp?t('ea.cmpRemover'):t('ea.cmpAdicionar');
 el('ea-cmp-add').setAttribute('aria-pressed',String(naCmp));
 el('ea-abas').innerHTML=ABAS.map(a=>`<button type="button" role="tab" class="pn-tab${a===S.aba?' active':''}" id="ea-tab-${a}" aria-controls="ea-corpo" aria-selected="${a===S.aba}" tabindex="${a===S.aba?0:-1}" data-aba="${a}">${escape(rotuloAba(a))}${a==='projetos'&&e.np?` <small>${e.np}</small>`:''}${a==='noticias'&&e.nn?` <small>${e.nn}</small>`:''}</button>`).join('');
 el('ea-abas').querySelectorAll('[data-aba]').forEach(b=>{b.onclick=()=>{S.aba=b.dataset.aba;ficha()};
  b.onkeydown=ev=>{const j=ABAS.indexOf(S.aba);if(ev.key==='ArrowRight'||ev.key==='ArrowLeft'){ev.preventDefault();S.aba=ABAS[(j+(ev.key==='ArrowRight'?1:ABAS.length-1))%ABAS.length];ficha();el('ea-tab-'+S.aba).focus()}}});
 el('ea-corpo').setAttribute('aria-labelledby','ea-tab-'+S.aba);
 el('ea-corpo').innerHTML=({perfil,territorio,economia,projetos,noticias,historico}[S.aba])(e,det);
 ligarCorpo(e);}

function linhaFonte(txt,url){return `<p class="source-line">${escape(txt)}${url?` <a href="${escape(urlSegura(url))}" target="_blank" rel="noopener noreferrer">${escape(t('ea.verFonte'))} ↗</a>`:''}</p>`}

function perfil(e,det){
 const fases=Object.entries(e.fases).map(([f,n])=>[D.dims.fase[+f],n]).sort((a,b)=>b[1]-a[1]);
 const grupos=GRUPOS.filter(g=>e.grupos[g]).map(g=>`<div class="bar-row"><span class="bar-label">${escape(rotuloGrupo(g))}</span>`
   +`<div class="bar-track"><div class="bar-fill" style="width:${e.grupos[g]/e.n*100}%;background:${COR[g]}"></div></div><span class="bar-value">${num(e.grupos[g])}</span></div>`).join('');
 const minerais=e.min.map(m=>`<li><span>${escape(D.dims.min[m][0])}</span>${badgesCriticos(m)}</li>`).join('');
 const muns=e.mun.map(m=>D.dims.mun[m][1]);
 return `<div class="ea-cols">
  <section><h4>${escape(t('ea.identidade'))}</h4><dl class="ea-dl">
   <dt>${escape(t('ea.razao'))}</dt><dd>${escape(e.nome)}</dd>
   <dt>${escape(t('ea.cnpjRaiz'))}</dt><dd>${escape(cnpjFmt(e.cnpj))} <span class="muted">· ${escape(t('ea.chave'))}</span></dd>
   <dt>${escape(t('ea.grupo'))}</dt><dd>${e.grupo?escape(e.grupo):`<span class="muted">${escape(t('ea.naoDisp'))}</span>`}</dd>
   <dt>${escape(t('ea.alias'))}</dt><dd>${e.alias&&e.alias.length?e.alias.map(a=>`<span class="pill">${escape(a)}</span>`).join(' '):`<span class="muted">${escape(t('ea.semAlias'))}</span>`}</dd>
   ${det?`<dt>${escape(t('ea.operacoes'))}</dt><dd>${escape(det.operacoes.join(' · '))}<div class="mk-note">${escape(t('ea.operacoesNota',{mun:det.municipios_operacao.join(', ')}))}</div></dd>`:''}
   <dt>${escape(t('ea.titularAnm'))}</dt><dd>${escape(t('ea.titularAnmTxt',{n:num(e.n),area:num(e.area,0)}))}</dd>
  </dl>
  ${det&&det.ri.length?`<h4>${escape(t('ea.ri'))}</h4><ul class="ea-links">${det.ri.map(r=>`<li><a href="${escape(urlSegura(r.u))}" target="_blank" rel="noopener noreferrer">${escape(r.t)} ↗</a></li>`).join('')}</ul>`:''}
  </section>
  <section><h4>${escape(t('ea.fasesT'))}</h4>${grupos||`<p class="mk-note">${escape(t('ea.semProcesso'))}</p>`}
   <p class="mk-note">${escape(t('ea.fasesNota'))}</p>
   <details><summary>${escape(t('ea.fasesDetalhe'))}</summary><table class="pn-table"><tbody>${fases.map(([f,n])=>`<tr><td>${escape(f.nome)}</td><td class="num">${num(n)}</td></tr>`).join('')}</tbody></table></details>
   <h4>${escape(t('ea.mineraisT'))}</h4><ul class="ea-minerais">${minerais||`<li class="muted">${escape(t('ea.naoDisp'))}</li>`}</ul>
   <p class="mk-note">${escape(t('ea.critNota'))} <button type="button" class="link-button" data-ir="metodo">${escape(t('ea.verBaseLegal'))}</button></p>
   <h4>${escape(t('ea.municipiosT',{n:String(muns.length)}))}</h4><p class="ea-muns">${muns.map(m=>`<button type="button" class="ea-chip" data-mun="${escape(m)}">${escape(m)}</button>`).join('')||escape(t('ea.naoDisp'))}</p>
  </section></div>
  ${linhaFonte(t('ea.fontePerfil'))}`;}

function territorio(e){
 const ks=procsPorEmp.get(e.i)||[],R=D.processos.rows;
 const comCfemRecente=ks.filter(k=>/^Opera/.test(D.dims.status[R[k][PC.status]]));
 const lavraSem=ks.filter(k=>D.dims.fase[R[k][PC.fase]].grupo==='lavra_autorizada'&&!comCfemRecente.includes(k));
 const req=ks.filter(k=>D.dims.fase[R[k][PC.fase]].grupo==='requerimento_lavra'),pesq=ks.filter(k=>D.dims.fase[R[k][PC.fase]].grupo==='pesquisa');
 const sgb=ks.filter(k=>R[k][PC.minas_ativas_sgb]);
 const det=D.detalhes[String(e.i)],realizado=det?det.producao.filter(p=>ehProducaoGO(p)&&p.nivel!=='operacao'):[];
 const projFuturos=(projPorEmp.get(e.i)||[]).filter(p=>p.maturidade&&!/OPERA/i.test(p.maturidade));
 const ordem=[...ks].sort((a,b)=>(b===S.destaque)-(a===S.destaque)||R[b][PC.cfem_2022_2026]-R[a][PC.cfem_2022_2026]||(R[b][PC.area_ha]||0)-(R[a][PC.area_ha]||0));
 const POR=15,pags=Math.max(1,Math.ceil(ordem.length/POR));S.ppag=Math.min(S.ppag,pags-1);
 const linhas=ordem.slice(S.ppag*POR,(S.ppag+1)*POR).map(k=>{const r=R[k],[n,a]=r[PC.processo].split('/'),cpa=D.cfem_processo_ano&&D.cfem_processo_ano[r[PC.processo]];
  return `<tr class="${k===S.destaque?'ea-destaque':''}"><td><button type="button" class="link-button" data-proc="${k}">${escape(r[PC.processo])}</button>`
   +`<div class="mk-note"><a href="https://sistemas.anm.gov.br/SCM/Extra/site/admin/dadosProcesso.aspx?numero=${encodeURIComponent(n)}&ano=${encodeURIComponent(a)}" target="_blank" rel="noopener noreferrer">${escape(t('ea.cadastroAnm'))} ↗</a></div></td>`
   +`<td>${escape(D.dims.fase[r[PC.fase]].nome)}<div class="mk-note"><i class="ea-dot" style="background:${COR[D.dims.fase[r[PC.fase]].grupo]}"></i>${escape(rotuloGrupo(D.dims.fase[r[PC.fase]].grupo))}</div></td>`
   +`<td>${escape(D.dims.status[r[PC.status]]||'—')}${r[PC.minas_ativas_sgb]?`<div class="mk-note">${escape(t('ea.sgbFlag'))}</div>`:''}</td>`
   +`<td>${escape(D.dims.min[r[PC.mineral]]?D.dims.min[r[PC.mineral]][0]:'—')} ${badgesCriticos(r[PC.mineral])}</td>`
   +`<td>${escape(r[PC.municipios].map(m=>D.dims.mun[m][1]).join(', ')||'—')}</td>`
   +`<td class="num">${r[PC.area_ha]!=null?num(r[PC.area_ha],2):'—'}</td>`
   +`<td class="num">${r[PC.cfem_2022_2026]?brl(r[PC.cfem_2022_2026]):'—'}${cpa?`<div class="mk-note">${escape(Object.entries(cpa).map(([y,v])=>y+': '+brl(v)).join(' · '))}</div>`:''}</td></tr>`}).join('');
 const bloco=(tit,itens,nota,classe)=>`<div class="ea-ev ${classe}"><h5>${escape(tit)}</h5><ul>${itens.length?itens.join(''):`<li class="muted">${escape(t('ea.naoDisp'))}</li>`}</ul><p class="mk-note">${escape(nota)}</p></div>`;
 return `<div class="ea-explora">
  ${bloco(t('ea.jaExplora'),[
    ...(realizado.some(p=>p.periodo_tipo==='ano')?realizado.filter(p=>p.periodo_tipo==='ano').slice(-3):realizado.slice(-2)).map(p=>`<li><b>${escape(num(p.valor))} ${escape(p.unidade)}</b> ${escape(p.produto)} · ${escape(p.periodo)} <span class="muted">(${escape(t('ea.prodDeclarada'))})</span></li>`),
    comCfemRecente.length?`<li><b>${num(comCfemRecente.length)}</b> ${escape(t('ea.procCfemRecente'))}</li>`:'',
    sgb.length?`<li><b>${num(sgb.length)}</b> ${escape(t('ea.procSgb'))}</li>`:''].filter(Boolean),t('ea.jaExploraNota'),'explora')}
  ${bloco(t('ea.podeExplorar'),[
    lavraSem.length?`<li><b>${num(lavraSem.length)}</b> ${escape(t('ea.procLavraSem'))}</li>`:'',
    req.length?`<li><b>${num(req.length)}</b> ${escape(t('ea.procReq'))}</li>`:'',
    pesq.length?`<li><b>${num(pesq.length)}</b> ${escape(t('ea.procPesq'))}</li>`:'',
    projFuturos.length?`<li><b>${num(projFuturos.length)}</b> ${escape(t('ea.projFuturos'))}</li>`:''].filter(Boolean),t('ea.podeExplorarNota'),'pode')}
 </div>
 <div class="atlas-data-head"><h4>${escape(t('ea.processosT',{n:num(ks.length)}))}</h4><div class="ea-acoes"><button type="button" class="btn outline" data-exp="proc-csv">${escape(t('ea.expProcCsv'))}</button></div></div>
 <div class="table-wrap"><table class="pn-table ea-tabela"><thead><tr><th>${escape(t('ea.th.processo'))}</th><th>${escape(t('ea.th.fase'))}</th><th>${escape(t('ea.th.situacao'))}</th><th>${escape(t('ea.th.mineral'))}</th><th>${escape(t('ea.th.municipios'))}</th><th class="num">${escape(t('ea.th.area'))}</th><th class="num">${escape(t('ea.th.cfem'))}</th></tr></thead><tbody>${linhas||`<tr><td colspan="7" class="muted">${escape(t('ea.semProcesso'))}</td></tr>`}</tbody></table></div>
 ${pags>1?`<div class="ea-pag"><button type="button" class="link-button" data-ppag="-1" ${S.ppag?'':'disabled'}>← ${escape(t('ea.anterior'))}</button><span>${escape(t('ea.pagina',{p:String(S.ppag+1),n:String(pags)}))}</span><button type="button" class="link-button" data-ppag="1" ${S.ppag<pags-1?'':'disabled'}>${escape(t('ea.proxima'))} →</button></div>`:''}
 ${linhaFonte(t('ea.fonteTerritorio'))}`;}

function barrasAno(serie,fmt,cor,nota){
 const ent=Object.entries(serie);if(!ent.length)return `<p class="mk-note">${escape(t('ea.naoDisp'))}</p>`;
 const max=Math.max(...ent.map(([,v])=>typeof v==='object'?v.anual:v),1);
 return ent.map(([a,v])=>{const val=typeof v==='object'?v:{x:v};
  return `<div class="bar-row ea-ano"><span class="bar-label">${escape(a)}</span><div class="bar-track ea-track">`
   +(typeof v==='object'?`<div class="bar-fill ea-anual" style="width:${v.anual/max*100}%"></div><div class="bar-fill ea-obs" style="width:${v.obs/max*100}%;background:${cor}"></div>`
     :`<div class="bar-fill" style="width:${v/max*100}%;background:${cor}"></div>`)
   +`</div><span class="bar-value">${escape(fmt(typeof v==='object'?v.obs:v))}</span></div>`
   +(nota?`<p class="mk-note">${escape(nota(a,val.x!==undefined?val.x:v))}</p>`:'')}).join('');}

function economia(e,det){
 const linhasEp=EP?EP.linhas.filter(l=>l.cnpj_raiz===e.cnpj):[];
 const cfem=barrasAno(e.cfem,brl,'#0f6fb0',a=>a==='2026'?t('ea.parcial2026',{meses:String(D.meta.meses_cfem_2026.length)}):'');
 const ccee=barrasAno(e.ccee,v=>num(v,0)+' MWh','#0d9488',(a,v)=>t('ea.cceeNota',{meses:String(v.meses),anual:num(v.anual,0),q:rotuloQualidade(v.q)}));
 const prod=det?det.producao:[];
 const tabProd=prod.length?`<div class="table-wrap"><table class="pn-table"><thead><tr><th>${escape(t('ea.th.periodo'))}</th><th>${escape(t('ea.th.mineral'))}</th><th class="num">${escape(t('ea.th.valor'))}</th><th>${escape(t('ea.th.medida'))}</th><th>${escape(t('ea.th.tipo'))}</th><th>${escape(t('ea.th.fonte'))}</th></tr></thead><tbody>`
  +prod.map(p=>`<tr class="${ehProducaoGO(p)?'':'ea-nao-realizado'}"><td>${escape(p.periodo)}</td><td>${escape(p.mineral||'—')}<div class="mk-note">${escape(p.produto||'')}${p.nivel==='operacao'?' · '+escape(p.operacao):''}</div></td>`
   +`<td class="num"><b>${escape(num(p.valor))}${p.valor_max?'–'+escape(num(p.valor_max)):''}</b> ${escape(p.unidade)}</td><td>${escape(rotuloMedida(p.medida))}<div class="mk-note">${escape(rotuloEscopo(p.escopo))}</div></td>`
   +`<td><span class="pill">${escape(rotuloTipoValor(p.tipo_valor))}</span><div class="mk-note">${escape(t('ea.conf'))}: ${escape(rotuloConf(p.confianca))} · ${escape(p.status_validacao==='nao_validado'?t('ea.naoValidado'):p.status_validacao)}</div></td>`
   +`<td>${p.fonte_url?`<a href="${escape(urlSegura(p.fonte_url))}" target="_blank" rel="noopener noreferrer">${escape(p.fonte_nome)} ↗</a>`:escape(p.fonte_nome||'—')}</td></tr>`).join('')+'</tbody></table></div>'
  :`<p class="mk-note">${escape(t('ea.semProducao'))}</p>`;
 const coef=linhasEp.filter(l=>l.coeficiente).map(l=>`<li><b>${escape(String(l.ano))} · ${escape(l.mineral)}</b>: ${escape(num(l.coeficiente.valor,l.coeficiente.valor<100?1:0))} ${escape(l.coeficiente.unidade)} <span class="pill">${escape(rotuloQualidade(l.coeficiente.qualidade))}</span>${l.coeficiente.energia_exclusiva?'':` <span class="muted">· ${escape(t('ep.naoExclusivaCurto'))}</span>`}</li>`).join('');
 const notas=det&&det.notas_energia&&det.notas_energia.length?det.notas_energia.map(n=>`<p class="mk-note"><span class="pill">${escape(n.efeito)}</span> ${escape(n.texto)} ${n.fonte?`<a href="${escape(urlSegura(n.fonte))}" target="_blank" rel="noopener noreferrer">${escape(t('ea.verFonte'))} ↗</a>`:''}</p>`).join(''):'';
 return `<div class="ea-cols">
  <section><h4>${escape(t('ea.cfemT'))}</h4><p class="mk-note">${escape(t('ea.cfemS'))}</p>${cfem}</section>
  <section><h4>${escape(t('ea.cceeT'))}</h4><p class="mk-note">${escape(t('ea.cceeS'))}</p>${ccee}${det&&det.rateio?`<p class="mk-note"><b>${escape(t('ea.rateio'))}</b> ${escape(det.rateio.nota)}</p>`:''}${notas}</section></div>
  <h4>${escape(t('ea.producaoT'))}</h4><p class="mk-note">${escape(t('ea.producaoS'))}</p>${tabProd}
  ${coef?`<h4>${escape(t('ea.coefT'))}</h4><ul class="ea-links">${coef}</ul><p class="mk-note">${escape(t('ea.coefS'))} <button type="button" class="link-button" data-ir="painel-energia">${escape(t('ea.irPainelEnergia'))}</button></p>`:''}
  ${linhaFonte(t('ea.fonteEconomia'))}`;}

function projetos(e){
 const ps=(projPorEmp.get(e.i)||[]).slice().sort((a,b)=>({projetos:0,mercado:1,radar:2}[a.fonte])-({projetos:0,mercado:1,radar:2}[b.fonte]));
 if(!ps.length)return `<p class="empty">${escape(t('ea.semProjetos'))}</p>${linhaFonte(t('ea.fonteProjetos'))}`;
 const rotFonte=f=>({projetos:t('ea.pf.projetos'),mercado:t('ea.pf.mercado'),radar:t('ea.pf.radar')}[f]);
 const capex=p=>p.capex?`${p.moeda||''} ${p.capex}${p.ano_capex?' ('+p.ano_capex+')':''}`:t('ea.naoDisp');
 return `<div class="table-wrap"><table class="pn-table"><thead><tr><th>${escape(t('ea.th.projeto'))}</th><th>${escape(t('ea.th.maturidade'))}</th><th>${escape(t('ea.th.mineral'))}</th><th>${escape(t('ea.th.capacidade'))}</th><th>${escape(t('ea.th.capex'))}</th><th>${escape(t('ea.th.vinculo'))}</th></tr></thead><tbody>`
  +ps.slice(0,60).map(p=>`<tr><td><b>${escape(p.nome)}</b><div class="mk-note">${escape(rotFonte(p.fonte))}${p.mun?' · '+escape(p.mun):''}${p.data?' · '+escape(p.data):''}</div>`
   +(p.link?`<div class="mk-note"><a href="${escape(urlSegura(p.link))}" target="_blank" rel="noopener noreferrer">${escape(p.fonte_nome||t('ea.verFonte'))} ↗</a></div>`:'')
   +(p.evidencias&&p.evidencias.length?`<details><summary>${escape(t('ea.evidencias',{n:String(p.evidencias.length)}))}</summary><ul class="ea-links">${p.evidencias.map(v=>`<li>${escape(v.d||'')} · ${v.u?`<a href="${escape(urlSegura(v.u))}" target="_blank" rel="noopener noreferrer">${escape(v.t)} ↗</a>`:escape(v.t)} <span class="muted">${escape(v.v||'')}</span></li>`).join('')}</ul></details>`:'')+`</td>`
   +`<td><span class="pill">${escape(p.maturidade||'—')}</span><div class="mk-note">${escape(p.fase||'')}</div></td><td>${escape(p.mineral||'—')}</td>`
   +`<td>${p.capacidade?escape(p.capacidade+' '+(p.cap_unidade||'')):`<span class="muted">${escape(t('ea.naoDisp'))}</span>`}</td><td>${escape(capex(p))}</td>`
   +`<td>${escape(rotuloMetodo(p.metodo))}<div class="mk-note">${escape(t('ea.conf'))}: ${escape(rotuloConf(p.conf))}${p.processos?' · '+escape(p.processos.slice(0,4).join(', '))+(p.processos.length>4?'…':''):''}</div></td></tr>`).join('')
  +`</tbody></table></div>${ps.length>60?`<p class="mk-note">${escape(t('ea.maisProjetos',{n:String(ps.length-60)}))}</p>`:''}
  <p class="mk-note">${escape(t('ea.projetosNota'))}</p>${linhaFonte(t('ea.fonteProjetos'))}`;}

function noticias(e){
 const ns=newsPorEmp.get(e.i)||[];
 if(!ns.length)return `<p class="empty">${escape(t('ea.semNoticias'))}</p><p class="mk-note">${escape(t('ea.semNoticiasNota'))}</p>${linhaFonte(t('ea.fonteNoticias'))}`;
 const diretas=ns.filter(n=>n.tipo==='empresa'),indiretas=ns.filter(n=>n.tipo==='indireta');
 const li=n=>`<li><a href="${escape(urlSegura(n.u))}" target="_blank" rel="noopener noreferrer">${escape(n.t)}</a><div class="rd-meta"><span class="rd-data">${escape(n.d)}</span><span class="rd-fonte">${escape(n.v)}</span>`
  +(n.go?`<span class="rd-tag-go">GO</span>`:'')+`<span class="rd-sub">${escape(rotuloMetodo(n.metodo))}: “${escape(n.alias)}”</span><span class="pill">${escape(t('ea.conf'))}: ${escape(rotuloConf(n.conf))}</span></div></li>`;
 return `<p class="mk-note">${escape(t('ea.noticiasNota'))}</p><ul class="rd-news">${diretas.slice(0,40).map(li).join('')}</ul>
  ${diretas.length>40?`<p class="mk-note">${escape(t('ea.maisNoticias',{n:String(diretas.length-40)}))}</p>`:''}
  ${indiretas.length?`<h4>${escape(t('ea.indiretasT'))}</h4><p class="mk-note">${escape(t('ea.indiretasS'))}</p><ul class="rd-news ea-indiretas">${indiretas.map(li).join('')}</ul>`:''}
  ${linhaFonte(t('ea.fonteNoticias'))}`;}

function historico(e,det){
 const evs=[...(newsPorEmp.get(e.i)||[]).filter(n=>n.tipo==='empresa').map(n=>({d:n.d,t:n.t,u:n.u,tipo:t('ea.evNoticia'),v:n.v})),
  ...(projPorEmp.get(e.i)||[]).filter(p=>p.fonte!=='radar').flatMap(p=>(p.evidencias||[]).map(v=>({d:v.d,t:v.t,u:v.u,tipo:t('ea.evProjeto'),v:v.v})))]
  .filter(x=>x.d).sort((a,b)=>b.d.localeCompare(a.d)).slice(0,25);
 const anosC=[...new Set([...Object.keys(e.cfem),...Object.keys(e.ccee)])].sort();
 const tab=`<table class="pn-table"><thead><tr><th>${escape(t('ea.th.ano'))}</th><th class="num">${escape(t('ea.th.cfemAno'))}</th><th class="num">${escape(t('ea.th.ccee'))}</th><th>${escape(t('ea.th.producao'))}</th></tr></thead><tbody>`
  +anosC.map(a=>{const pr=det?det.producao.filter(p=>String(p.periodo)===a&&ehProducaoGO(p)&&p.nivel!=='operacao'):[];
   return `<tr><td>${escape(a)}${a==='2026'?` <span class="muted">(${escape(t('ea.parcial'))})</span>`:''}</td><td class="num">${e.cfem[a]?brl(e.cfem[a]):'—'}</td>`
    +`<td class="num">${e.ccee[a]?escape(num(e.ccee[a].obs,0))+' MWh<div class="mk-note">'+escape(t('ea.meses',{n:String(e.ccee[a].meses)}))+'</div>':'—'}</td>`
    +`<td>${pr.length?pr.map(p=>escape(num(p.valor)+' '+p.unidade+' '+(p.mineral||''))).join('<br>'):'<span class="muted">—</span>'}</td></tr>`}).join('')+'</tbody></table>';
 return `<div class="ea-cols"><section><h4>${escape(t('ea.serieT'))}</h4><p class="mk-note">${escape(t('ea.serieS'))}</p><div class="table-wrap">${tab}</div></section>
  <section><h4>${escape(t('ea.eventosT'))}</h4>${evs.length?`<ol class="ea-timeline">${evs.map(x=>`<li><span class="rd-data">${escape(x.d)}</span><span class="pill">${escape(x.tipo)}</span> ${x.u?`<a href="${escape(urlSegura(x.u))}" target="_blank" rel="noopener noreferrer">${escape(x.t)}</a>`:escape(x.t)} <span class="muted">${escape(x.v||'')}</span></li>`).join('')}</ol>`:`<p class="mk-note">${escape(t('ea.semEventos'))}</p>`}</section></div>
  ${linhaFonte(t('ea.fonteHistorico'))}`;}

function ligarCorpo(e){
 const c=el('ea-corpo');
 c.querySelectorAll('[data-proc]').forEach(b=>b.onclick=()=>{S.destaque=+b.dataset.proc;desenharSelecao(false).then(()=>irParaProcesso(S.destaque));ficha()});
 c.querySelectorAll('[data-ppag]').forEach(b=>b.onclick=()=>{S.ppag+=+b.dataset.ppag;ficha()});
 c.querySelectorAll('[data-mun]').forEach(b=>b.onclick=()=>{const k=D.dims.mun.findIndex(m=>m[1]===b.dataset.mun);if(k>=0){el('ea-mun').value=String(k);redesenhar()}});
 c.querySelectorAll('[data-ir=metodo]').forEach(b=>b.onclick=()=>{el('ea-metodo').open=true;el('ea-metodo').scrollIntoView({behavior:'smooth'})});
 c.querySelectorAll('[data-ir=painel-energia]').forEach(b=>b.onclick=()=>{if(window.empresasAba)window.empresasAba('declarada');
  el('ep-tabs').scrollIntoView({behavior:'smooth',block:'start'})});
 c.querySelectorAll('[data-exp=proc-csv]').forEach(b=>b.onclick=()=>exportarProcessos(e));}

// ------------------------------------------------------------------ comparação (2 a 3 empresas)
function comparar(){
 const box=el('ea-cmp');
 if(!S.cmp.length){box.hidden=true;return}
 box.hidden=false;
 const es=S.cmp.map(i=>porI.get(i)),anosC=[...new Set(es.flatMap(e=>[...Object.keys(e.cfem),...Object.keys(e.ccee)]))].sort();
 const linha=(rot,f)=>`<tr><th scope="row">${escape(rot)}</th>${es.map(e=>`<td class="num">${f(e)}</td>`).join('')}</tr>`;
 // Produção só se compara na mesma unidade; t e oz ficam em linhas separadas e coprodutos não se somam.
 const prodLinhas=[];
 const reg=es.map(e=>{const d=D.detalhes[String(e.i)];return d?d.producao.filter(p=>ehProducaoGO(p)&&p.nivel!=='operacao'&&/^\d{4}$/.test(String(p.periodo))):[]});
 const chaves=[...new Set(reg.flat().map(p=>p.periodo+'|'+p.mineral+'|'+p.unidade))].sort().reverse().slice(0,8);
 for(const ch of chaves){const[per,minr,un]=ch.split('|');
  prodLinhas.push(linha(`${t('ea.th.producao')} ${per} · ${minr} (${un})`,e=>{const p=reg[es.indexOf(e)].find(x=>x.periodo+'|'+x.mineral+'|'+x.unidade===ch);return p?escape(num(p.valor)):'<span class="muted">—</span>'}))}
 el('ea-cmp-corpo').innerHTML=`<div class="table-wrap"><table class="pn-table ea-cmp-tab"><thead><tr><th></th>${es.map(e=>`<th>${escape(e.nome)}<div><button type="button" class="link-button" data-cmp-rm="${e.i}">${escape(t('ea.cmpRemover'))}</button></div></th>`).join('')}</tr></thead><tbody>`
  +linha(t('ea.cnpjRaiz'),e=>escape(cnpjFmt(e.cnpj)))
  +linha(t('ea.m.processos'),e=>num(e.n))
  +linha(t('ea.met.area'),e=>num(e.area,0)+' ha')
  +GRUPOS.slice(0,3).map(g=>linha(rotuloGrupo(g),e=>num(e.grupos[g]||0))).join('')
  +anosC.map(a=>linha(`CFEM ${a}${a==='2026'?' ('+t('ea.parcial')+')':''}`,e=>e.cfem[a]?brl(e.cfem[a]):'<span class="muted">—</span>')).join('')
  +anosC.filter(a=>es.some(e=>e.ccee[a])).map(a=>linha(`${t('ea.th.ccee')} ${a}`,e=>e.ccee[a]?`${num(e.ccee[a].obs,0)} MWh<div class="mk-note">${escape(t('ea.meses',{n:String(e.ccee[a].meses)}))}</div>`:'<span class="muted">—</span>')).join('')
  +prodLinhas.join('')
  +linha(t('ea.aba.projetos'),e=>num(e.np))+linha(t('ea.aba.noticias'),e=>num(e.nn))
  +`</tbody></table></div><p class="mk-note">${escape(t('ea.cmpNota'))}</p>`;
 el('ea-cmp-corpo').querySelectorAll('[data-cmp-rm]').forEach(b=>b.onclick=()=>{S.cmp=S.cmp.filter(i=>i!==+b.dataset.cmpRm);comparar();if(S.sel!==null)ficha()});}

// ------------------------------------------------------------------ exportação (o recorte visível)
function baixar(nome,conteudo,tipo){const url=URL.createObjectURL(new Blob([conteudo],{type:tipo}));const a=document.createElement('a');a.href=url;a.download=nome;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
const celula=v=>`"${String(v??'').replace(/"/g,'""')}"`;
function exportarRecorte(formato){
 const per=S.per.join('-'),f=S.f,base={periodo:S.per,metrica:f.metrica,top:f.top,municipio:f.mun!==''?D.dims.mun[+f.mun][1]:null,
  mineral:f.min!==''?D.dims.min[+f.min][0]:null,grupo_fase:f.grupo||null,dado:f.dado||null,busca:el('ea-busca').value.trim()||null};
 const linhas=S.ranking.map((l,j)=>({posicao:j+1,empresa:l.e.nome,cnpj_raiz:l.e.cnpj,grupo:l.e.grupo||'',metrica:f.metrica,valor_metrica:Math.round(l.v*100)/100,
  cfem_periodo_rs:Math.round(l.cf*100)/100,processos_no_recorte:l.ps.length,area_ha_no_recorte:Math.round(l.ps.reduce((s,k)=>s+(D.processos.rows[k][PC.area_ha]||0),0)*100)/100,
  lavra_autorizada:l.e.grupos.lavra_autorizada||0,puxador_80pct_cfem:S.puxadores.has(l.e.i),producao_declarada:!!l.e.enr,projetos_vinculados:l.e.np,noticias_vinculadas:l.e.nn}));
 if(formato==='json')baixar(`minera-goias-atlas-empresas-${per}.json`,JSON.stringify({gerado_em:new Date().toISOString(),fonte:D.meta.gerado_por,pacote:D.meta.built_on,
  recorte:base,universo:S.universo.length,regras:{top_n:D.meta.regras.top_n,puxadores:D.meta.regras.puxadores,cfem:D.meta.regras.cfem},empresas:linhas},null,1),'application/json');
 else{const cab=Object.keys(linhas[0]||{posicao:0});
  baixar(`minera-goias-atlas-empresas-${per}.csv`,'﻿'+[`# ${t('ea.csvCab',{per,metrica:rotuloMetrica(f.metrica),u:String(S.universo.length)})}`,cab.join(';'),...linhas.map(l=>cab.map(c=>celula(l[c])).join(';'))].join('\r\n'),'text/csv;charset=utf-8')}}
function exportarProcessos(e){
 const R=D.processos.rows,ks=procsPorEmp.get(e.i)||[];
 const cab=['processo','empresa','cnpj_raiz','fase','grupo_fase','situacao_panorama','mineral','municipios','area_ha','cfem_2022_2026_rs','minas_ativas_sgb','centroide_lat_indicativo','centroide_lon_indicativo'];
 baixar(`minera-goias-processos-${e.cnpj}.csv`,'﻿'+[cab.join(';'),...ks.map(k=>{const r=R[k];return [r[PC.processo],e.nome,e.cnpj,D.dims.fase[r[PC.fase]].nome,D.dims.fase[r[PC.fase]].grupo,
  D.dims.status[r[PC.status]],D.dims.min[r[PC.mineral]]?D.dims.min[r[PC.mineral]][0]:'',r[PC.municipios].map(m=>D.dims.mun[m][1]).join(' | '),r[PC.area_ha],r[PC.cfem_2022_2026],r[PC.minas_ativas_sgb]?'sim':'nao',r[PC.lat],r[PC.lon]].map(celula).join(';')})].join('\r\n'),'text/csv;charset=utf-8');}
function exportarFicha(){
 const e=porI.get(S.sel);if(!e)return;
 const R=D.processos.rows;
 baixar(`minera-goias-ficha-${e.cnpj}.json`,JSON.stringify({gerado_em:new Date().toISOString(),pacote:D.meta.built_on,regras:D.meta.regras,empresa:e,detalhes:D.detalhes[String(e.i)]||null,
  processos:(procsPorEmp.get(e.i)||[]).map(k=>Object.fromEntries(D.processos.cols.map((c,j)=>[c,c==='fase'?D.dims.fase[R[k][j]].nome:c==='mineral'?(D.dims.min[R[k][j]]||[''])[0]:c==='municipios'?R[k][j].map(m=>D.dims.mun[m][1]):c==='status'?D.dims.status[R[k][j]]:c==='uso'?D.dims.uso[R[k][j]]:R[k][j]]))),
  projetos:projPorEmp.get(e.i)||[],noticias:newsPorEmp.get(e.i)||[]},null,1),'application/json');}

// ------------------------------------------------------------------ metodologia e fontes
function metodologia(){
 const m=D.meta,c=m.cobertura,cr=D.criticos;
 const crit=esf=>{const x=cr[esf];return `<h4>${escape(x.nome)}</h4><p class="mk-note"><b>${escape(x.norma)}</b> · ${escape(x.jurisdicao)} · ${escape(t('ea.consultado',{d:x.consultado_em}))} · <a href="${escape(urlSegura(x.link))}" target="_blank" rel="noopener noreferrer">${escape(t('ea.textoOficial'))} ↗</a></p>`
  +`<p class="mk-note">${escape(x.situacao)}</p>`+x.categorias.map(cat=>`<p class="mk-note"><span class="ea-crit ${esf==='federal'?'fed':'est'}">${escape(cat.id)}</span> <b>${escape(cat.nome)}:</b> ${cat.itens.map(i=>escape(i.texto)+(i.min.length?'':' <span class="muted">('+escape(t('ea.semCategoria'))+')</span>')).join('; ')}</p>`).join('')
  +(x.ressalvas||[]).map(r=>`<p class="mk-note">· ${escape(r)}</p>`).join('');};
 el('ea-metodo-corpo').innerHTML=`<div class="ea-cols"><section><h4>${escape(t('ea.regrasT'))}</h4>${Object.values(m.regras).map(r=>`<p class="mk-note">· ${escape(r)}</p>`).join('')}
  <h4>${escape(t('ea.avisosT'))}</h4>${m.avisos.map(a=>`<p class="mk-note">· ${escape(a)}</p>`).join('')}
  <h4>${escape(t('ea.coberturaT'))}</h4><p class="mk-note">${escape(t('ea.cobertura',{proc:num(c.processos),pj:num(c.processos_pj),pf:num(c.processos_pf_nao_nomeados),sem:num(c.processos_sem_titular),emp:num(c.empresas_indice),cfem:num(c.empresas_com_cfem),ccee:num(c.empresas_com_ccee),enr:num(c.empresas_enriquecidas),sgb:num(c.processos_em_minas_ativas_sgb)}))}</p>
  <p class="mk-note">${escape(t('ea.coberturaNoticias',{acervo:num(c.noticias.acervo_deduplicado),v:num(c.noticias.vinculadas),d:num(Object.values(c.noticias.descartadas).reduce((s,x)=>s+x,0))}))}</p>
  <p class="mk-note">${escape(t('ea.coberturaProjetos',{v:num(c.projetos_vinculados),s:num(c.projetos_sem_vinculo)}))}</p></section>
  <section>${crit('federal')}${crit('estadual')}<p class="mk-note">${escape(t('ea.critSeparadas'))}</p></section></div>
  <details><summary>${escape(t('ea.descartesT'))}</summary><ul class="ea-links">${D.noticias_descartadas_exemplos.map(d=>`<li>${escape(d.d)} · ${escape(d.t)} <span class="pill">${escape(d.motivo)}</span> <span class="muted">${escape(porI.get(d.e)?porI.get(d.e).nome:'')} · “${escape(d.alias)}”</span></li>`).join('')}</ul></details>
  <p class="source-line">${escape(t('ea.fontesGerais',{data:m.built_on}))} ${Object.values(m.entradas).map(x=>escape(x.arquivo)).join(' · ')}</p>`;}

// ------------------------------------------------------------------ montagem
function preencher(select,valores,vazio){select.innerHTML=(vazio!=null?`<option value="">${escape(vazio)}</option>`:'')+valores.map(([v,r])=>`<option value="${escape(v)}">${escape(r)}</option>`).join('')}
function redesenhar(){S.pag=0;calcular();metricas();lista();desenharPontos();poligonosVisiveis();if(S.sel!==null)ficha();}

function controles(){
 const munsUsados=new Set(D.processos.rows.flatMap(r=>r[PC.municipios]));
 preencher(el('ea-mun'),D.dims.mun.map((m,k)=>[k,m[1]]).filter(([k])=>munsUsados.has(k)),t('ea.todosMun'));
 const minsUsados=new Set([...D.processos.rows.map(r=>r[PC.mineral]),...D.cfem.rows.map(r=>r[3])]);
 preencher(el('ea-min'),D.dims.min.map((m,k)=>[k,m[0]]).filter(([k])=>minsUsados.has(k)).sort((a,b)=>a[1].localeCompare(b[1])),t('ea.todosMin'));
 preencher(el('ea-grupo'),GRUPOS.slice(0,4).map(g=>[g,rotuloGrupo(g)]),t('ea.todasFases'));
 const ys=['2022','2023','2024','2025','2026'];
 preencher(el('ea-ano-ini'),ys.map(y=>[y,y]));preencher(el('ea-ano-fim'),ys.map(y=>[y,y==='2026'?y+' ('+t('ea.parcial')+')':y]));
 el('ea-ano-ini').value='2022';el('ea-ano-fim').value='2025';
 preencher(el('ea-dado'),[['enr',t('ea.d.enr')],['cfem',t('ea.d.cfem')],['ccee',t('ea.d.ccee')],['proj',t('ea.d.proj')],['news',t('ea.d.news')],
  ['sgb',t('ea.d.sgb')],['crit_fed',t('ea.d.critFed')],['crit_est',t('ea.d.critEst')]],t('ea.d.todos'));
 preencher(el('ea-metrica'),['cfem','processos','area','ccee'].map(m=>[m,rotuloMetrica(m)]));
 preencher(el('ea-top'),[['10','Top 10'],['20','Top 20'],['50','Top 50'],['all',t('ea.todas')]]);
 ['ea-mun','ea-min','ea-grupo','ea-ano-ini','ea-ano-fim','ea-dado','ea-metrica','ea-top'].forEach(id=>el(id).onchange=redesenhar);
 el('ea-reset').onclick=()=>{['ea-mun','ea-min','ea-grupo','ea-dado'].forEach(id=>el(id).value='');el('ea-busca').value='';
  el('ea-ano-ini').value='2022';el('ea-ano-fim').value='2025';el('ea-metrica').value='cfem';el('ea-top').value='10';redesenhar();
  if(S.mapa)S.mapa.fitBounds(goBounds(),{padding:[10,10]})};
 const busca=el('ea-busca');let timer=null;
 busca.oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>{sugerir();redesenhar()},160)};
 busca.onkeydown=ev=>{const n=sugestoes.length;
  if(ev.key==='ArrowDown'){ev.preventDefault();if(el('ea-sugestoes').hidden)sugerir();marcar(Math.min(n-1,ativa+1))}
  else if(ev.key==='ArrowUp'){ev.preventDefault();marcar(Math.max(0,ativa-1))}
  else if(ev.key==='Enter'){ev.preventDefault();
   // Enter antes do fim da espera da digitação: as sugestões ainda são da consulta anterior, então refaz agora.
   if(consultaSugerida!==norm(busca.value.trim())){clearTimeout(timer);sugerir();redesenhar()}
   if(ativa>=0)escolher(ativa);else if(sugestoes.length)escolher(0)}
  else if(ev.key==='Escape'){fecharSugestoes()}};
 busca.onblur=()=>setTimeout(fecharSugestoes,120);
 el('ea-exp-csv').onclick=()=>exportarRecorte('csv');el('ea-exp-json').onclick=()=>exportarRecorte('json');
 el('ea-ficha-fechar').onclick=()=>limparSelecao();el('ea-ficha-exp').onclick=exportarFicha;
 el('ea-cmp-add').onclick=()=>{const i=S.sel;if(i===null)return;
  if(S.cmp.includes(i))S.cmp=S.cmp.filter(x=>x!==i);else{if(S.cmp.length>=3)S.cmp.shift();S.cmp.push(i)}
  comparar();ficha();if(S.cmp.length)el('ea-cmp').scrollIntoView({behavior:'smooth',block:'nearest'})};
 el('ea-cmp-limpar').onclick=()=>{S.cmp=[];comparar();if(S.sel!==null)ficha()};
 el('ea-so-sel').onchange=desenharPontos;el('ea-poligonos').onchange=()=>{poligonosVisiveis();if(S.tela)S.tela.repintar()};
 // legenda: cada fase é um botão que mostra ou esconde a fase no mapa; o tamanho do ponto na legenda segue a hierarquia
 el('ea-legenda').innerHTML=`<span class="ea-leg-dica">${escape(t('ea.leg.clique'))}</span>`
  +GRUPOS.slice(0,4).map((g,gi)=>{const d=Math.round(9*HIER_RAIO[g]);
   return `<button type="button" class="ea-fase" data-g="${gi}" aria-pressed="true" title="${escape(t('ea.leg.alternar',{fase:rotuloGrupo(g)}))}">`
    +`<i style="background:${COR[g]};width:${d}px;height:${d}px;opacity:${HIER_ALFA[g]}"></i>${escape(rotuloGrupo(g))}</button>`}).join('')
  +`<span class="muted">${escape(t('ea.leg.hierarquia'))}</span>`
  +`<span class="ea-leg-tam"><i></i><i></i><i></i>${escape(t('ea.leg.centroide'))} · ${escape(t('ea.leg.cresce'))}</span><span><i class="ea-leg-quad"></i>${escape(t('ea.leg.municipio'))}</span>`
  +`<span class="muted">${escape(t('ea.leg.operacao'))}</span>`;
 el('ea-legenda').onclick=ev=>{const b=ev.target.closest('.ea-fase');if(!b)return;const g=+b.dataset.g;
  if(S.off.has(g))S.off.delete(g);else S.off.add(g);b.setAttribute('aria-pressed',String(!S.off.has(g)));esconderHover();if(S.tela)S.tela.repintar()};
 addEventListener('popstate',ev=>{const st=ev.state;if(!st||!('ea' in st))return;if(window.empresasAba)window.empresasAba('atlas');if(st.ea===null)limparSelecao(true);else selecionar(st.ea,{semHistorico:true})});}

async function carregar(){
 el('ea-error').innerHTML='';el('ea-loading').hidden=false;
 try{
  const [atlas,ep]=await Promise.all([api('/empresas/atlas'),api('/empresas').catch(()=>null)]);
  D=atlas;EP=ep;preparar();controles();metodologia();
  el('ea-content').hidden=false;el('ea-loading').hidden=true;
  criarMapa();redesenhar();
  const m=location.hash.match(/^#empresas\/(\d{8})$/);
  if(m){const e=E.find(x=>x.cnpj===m[1]);if(e)selecionar(e.i,{semHistorico:true})}
 }catch(e){
  loaded=false;el('ea-loading').hidden=true;
  el('ea-error').innerHTML=`${escape(e.message||t('c.failed'))} <button type="button" class="btn outline" id="ea-retry">${escape(t('ea.tentarDeNovo'))}</button>`;
  el('ea-retry').onclick=()=>{loaded=true;carregar()};}}

// Ganchos só de leitura para o teste de navegador (tests/e2e_atlas_empresas.py): o mapa e a empresa selecionada.
window.EmpresasAtlas={mapa:()=>S.mapa,selecionada:()=>S.sel===null?null:porI.get(S.sel).cnpj,

 // redesenhoMs força a rasterização (getImageData) para medir o desenho de verdade, não só o registro dos comandos
 redesenhoMs:()=>{const t0=performance.now();S.tela.repintar();S.tela._ctx.getImageData(0,0,1,1);return performance.now()-t0},
pontosNaTela:()=>S.nPontos,raioFase:g=>estiloFase(g,S.mapa.getZoom()).r,destaque:()=>S.destaque,
 // um pixel do mapa sem ponto nem polígono (meio da tela), para o teste de desmarcar clicando no vazio
 pontoVazio:()=>{const m=S.mapa,sz=m.getSize();for(let y=Math.round(sz.y*.3);y<sz.y*.7;y+=9)for(let x=Math.round(sz.x*.3);x<sz.x*.7;x+=9)
  if(!acertar(m.containerPointToLayerPoint([x,y])))return [x,y];return null},
 limites:()=>{const b=S.mapa&&S.mapa.options.maxBounds;return b?[b.getSouth(),b.getWest(),b.getNorth(),b.getEast()]:null},processo:id=>{const k=procPorId.get(soDigitos(id));return k==null?null:{lat:D.processos.rows[k][PC.lat],lon:D.processos.rows[k][PC.lon]}}};
const anterior=window.showEmpresas;
window.showEmpresas=()=>{if(anterior)anterior();if(loaded){if(S.mapa)setTimeout(()=>S.mapa.invalidateSize(),0);return}loaded=true;carregar()};
// Link direto (#empresas/<cnpj>) abre a aba Empresas depois que o painel monta a sessão.
if(/^#empresas/.test(location.hash))addEventListener('load',()=>setTimeout(()=>{const b=document.querySelector('[data-view="empresas"]');
 const tentar=n=>{if(!document.getElementById('loading').hidden&&n<40)return setTimeout(()=>tentar(n+1),150);if(b)b.click()};tentar(0)},0));
})();
