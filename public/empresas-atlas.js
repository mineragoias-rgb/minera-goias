/* Aba Empresas — inteligência empresarial da mineração e energia em Goiás, em quatro áreas com uma seleção só:
   Explorar (mapa em três modos, busca, filtros, indicadores, Top N), Dossiê (ficha da empresa), Análises (produção estimada AMB × CFEM,
   produção declarada e energia, arrecadação/títulos/consumo) e Comparar (2 a 3 empresas).
   Dados: /api/empresas/atlas (scripts/build_atlas_empresas.py) e /api/empresas (scripts/build_empresas_base.py), ambos autenticados.
   Aqui só se filtra, soma e desenha: identidade por CNPJ raiz, vínculos e classificações são decididos nos geradores, onde são auditáveis.
   O mapa desenha centroides de direitos minerários (indicativos) e referências de município (aproximadas); nenhum ponto é apresentado
   como localização exata de mina — nenhuma fonte traz essa coordenada. Polígonos ANM só carregam quando pedidos. */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc;
const num=(v,c=0)=>I18N.num(v,{minimumFractionDigits:c,maximumFractionDigits:c});
const brl=v=>'R$ '+(Math.abs(v)>=1e6?num(v/1e6,1)+' mi':num(v,0));
const norm=s=>String(s??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
const soDigitos=s=>String(s??'').replace(/\D/g,'');
const cnpjFmt=c=>c&&c.length===8?`${c.slice(0,2)}.${c.slice(2,5)}.${c.slice(5)}`:c||'—';
const toneladas=v=>v==null?'—':num(v,Math.abs(v)<10?3:Math.abs(v)<1000?1:0)+' t';
const r2=v=>v==null||!Number.isFinite(+v)?null:Math.round(v*100)/100;
// "(nome não informado no CFEM — CNPJ raiz …)": CNPJ raiz sem razão social na fonte; vai para o fim da ordem por nome
const semNome=e=>/^\(nome n/i.test(e.nome);
const XP=()=>window.EmpresasExportar;
const GRUPOS=['lavra_autorizada','requerimento_lavra','pesquisa','disponibilidade','outro'];
const COR={lavra_autorizada:'#0d9488',requerimento_lavra:'#0f6fb0',pesquisa:'#c2681b',disponibilidade:'#8250c4',outro:'#93a4b1'};
// Chaves por extenso para o teste de tradução enxergar cada uma.
const rotuloGrupo=g=>({lavra_autorizada:t('ea.g.lavra_autorizada'),requerimento_lavra:t('ea.g.requerimento_lavra'),pesquisa:t('ea.g.pesquisa'),
 disponibilidade:t('ea.g.disponibilidade'),outro:t('ea.g.outro')}[g]||g);
const rotuloMetrica=m=>({cfem:t('ea.met.cfem'),processos:t('ea.met.processos'),area:t('ea.met.area'),ccee:t('ea.met.ccee'),
 relevancia:t('ea.met.relevancia'),nome:t('ea.met.nome')}[m]||m);
// Relevância e nome só ordenam a lista; o tamanho do ponto e o valor ao lado do nome continuam sendo a CFEM.
const metricaDados=m=>m==='relevancia'||m==='nome'?'cfem':m;
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
const rotuloBase=b=>({beneficiada:t('es.base.beneficiada'),ROM:t('es.base.rom'),conteudo_mineral:t('es.base.contido')}[b]||b);
// Maturidade dos projetos em cinco classes (as sete do Radar de Projetos), da operação ao sinal.
const MAT=[['op',['OPERAÇÃO','EXPANSÃO'],'#0d9488'],['impl',['CONSTRUÇÃO','DEFINIDO'],'#0f6fb0'],['prov',['PROVÁVEL'],'#7a5cc4'],
 ['poss',['POSSÍVEL'],'#c2681b'],['sinal',['SINAL'],'#93a4b1']];
const matDe=p=>{const m=String(p.maturidade||'').toUpperCase();const k=MAT.findIndex(([,ms])=>ms.includes(m));return k<0?MAT.length-1:k};
const rotuloMat=k=>({op:t('ea.mat.op'),impl:t('ea.mat.impl'),prov:t('ea.mat.prov'),poss:t('ea.mat.poss'),sinal:t('ea.mat.sinal')}[MAT[k][0]]);
const AREAS=['explorar','dossie','analises','comparar'],ANALISES=['estimada','declarada','direitos'],MODOS=['empresas','processos','projetos'];
const rotuloArea=a=>({explorar:t('ea.nav.explorar'),dossie:t('ea.nav.dossie'),analises:t('ea.nav.analises'),comparar:t('ea.nav.comparar')}[a]);
const rotuloAnalise=a=>({estimada:t('ea.anal.estimada'),declarada:t('ea.anal.declarada'),direitos:t('ea.anal.direitos')}[a]);

let D=null,EP=null,loaded=false;
// Estado de domínio por identificador: empresa (S.sel → CNPJ raiz), processo (S.destaque → número ANM), município (filtro ea-mun → código
// IBGE). O município é RECORTE (persiste, como os outros filtros); empresa, processo e município disputam só o FOCO (S.foco), que decide
// o que o cartão único sobre o mapa mostra. Um não apaga o outro: sair do município não desmarca a empresa, e vice-versa.
const S={sel:null,aba:'perfil',nLista:50,ppag:0,nNews:40,nEv:25,nRk:50,volta:null,cmp:[],cmpTudo:new Set(),destaque:null,mapa:null,camadas:{},geo:null,munCentro:null,universo:[],ranking:[],puxadores:new Set(),
 area:'explorar',modo:'empresas',anal:'estimada',escopo:'todas',off:new Set(),matOff:new Set(),uni:new Set(),projVis:[],refCache:new Map(),
 foco:null,munOrigem:null,irProc:false,previa:new Map()};
// Largura de mesa: lista lateral fixa ao lado do mapa. Abaixo disso, a lista vira gaveta e a busca fica acima do mapa.
const largo=window.matchMedia?matchMedia('(min-width:1001px)'):{matches:true,addEventListener(){}};
let E=[],porI=new Map(),buscaPorI=new Map(),procsPorEmp=new Map(),cfemPorEmp=new Map(),projPorEmp=new Map(),newsPorEmp=new Map(),procPorId=new Map(),idxBusca=[],criticosPorMin=new Map();
const PC={};   // índice das colunas de processos

// ------------------------------------------------------------------ preparo
function preparar(){
 D.processos.cols.forEach((c,i)=>PC[c]=i);
 E=D.empresas;E.forEach(e=>porI.set(e.i,e));
 D.processos.rows.forEach((r,k)=>{procPorId.set(soDigitos(r[PC.processo]),k);
  if(r[PC.empresa]>=0){if(!procsPorEmp.has(r[PC.empresa]))procsPorEmp.set(r[PC.empresa],[]);procsPorEmp.get(r[PC.empresa]).push(k)}});
 D.cfem.rows.forEach(r=>{if(!cfemPorEmp.has(r[0]))cfemPorEmp.set(r[0],[]);cfemPorEmp.get(r[0]).push(r)});
 D.projetos.forEach((p,j)=>{p.j=j;p.mat=matDe(p);p.e.forEach(i=>{if(!projPorEmp.has(i))projPorEmp.set(i,[]);projPorEmp.get(i).push(p)})});
 D.noticias.forEach(n=>{if(!newsPorEmp.has(n.e))newsPorEmp.set(n.e,[]);newsPorEmp.get(n.e).push(n)});
 for(const esfera of ['federal','estadual'])for(const cat of D.criticos[esfera].categorias)for(const item of cat.itens)for(const m of item.min){
  if(!criticosPorMin.has(m))criticosPorMin.set(m,{federal:[],estadual:[]});
  const alvo=criticosPorMin.get(m)[esfera];if(!alvo.includes(cat.id))alvo.push(cat.id)}
 idxBusca=E.map(e=>({i:e.i,txt:norm([e.nome,e.cnpj,cnpjFmt(e.cnpj),e.grupo||'',...(e.alias||[])].join(' '))}));idxBusca.forEach(x=>buscaPorI.set(x.i,x.txt));
 if(window.L)prepararPontos();}

const anos=()=>{const a=+el('ea-ano-ini').value,b=+el('ea-ano-fim').value;return a<=b?[a,b]:[b,a]};
const filtros=()=>({mun:el('ea-mun').value,min:el('ea-min').value,grupo:el('ea-grupo').value,dado:el('ea-dado').value,
 ordem:el('ea-metrica').value,metrica:metricaDados(el('ea-metrica').value),q:norm(el('ea-busca').value.trim())});
// Relevância para a busca: nome que começa pelo texto (ou CNPJ), depois palavra do nome, depois o resto (grupo, alias).
function relevanciaBusca(e,q){
 const n=norm(e.nome),d=soDigitos(q);
 if(n.startsWith(q)||(d.length>=3&&e.cnpj.startsWith(d)))return 0;
 if(n.split(/[^a-z0-9]+/).some(w=>w.startsWith(q)))return 1;
 return n.includes(q)?2:3}
// Referência territorial da empresa: município e mineral do processo de referência (o do ponto no mapa);
// sem processo georreferenciado, o município e o mineral onde ela mais recolhe CFEM.
function referencia(e){
 let c=S.refCache.get(e.i);if(c)return c;
 const R=D.processos.rows;let mun=null,min=null;
 if(e.pt>=0){mun=R[e.pt][PC.municipios][0]??null;min=R[e.pt][PC.mineral]??null}
 if(mun===null||min===null){const g=new Map(),h=new Map();
  for(const r of cfemPorEmp.get(e.i)||[]){g.set(r[2],(g.get(r[2])||0)+r[4]);h.set(r[3],(h.get(r[3])||0)+r[4])}
  const topo=m=>{let k=null,v=-1;for(const[a,b]of m)if(b>v){k=a;v=b}return k};
  if(mun===null)mun=topo(g)??(e.mun[0]??null);if(min===null)min=topo(h)??(e.min[0]??null)}
 c={mun:mun!==null&&D.dims.mun[mun]?D.dims.mun[mun][1]:null,min:min!==null&&D.dims.min[min]?D.dims.min[min][0]:null,outros:Math.max(0,e.mun.length-1)};
 S.refCache.set(e.i,c);return c}
// Municípios e minerais da empresa na ordem que importa: CFEM recolhida (todos os anos), depois número de processos, depois nome.
function ordenarPorPeso(e,campoCfem,lista,doProcesso){
 const peso=new Map(),nproc=new Map();
 for(const r of cfemPorEmp.get(e.i)||[])peso.set(r[campoCfem],(peso.get(r[campoCfem])||0)+r[4]);
 for(const k of procsPorEmp.get(e.i)||[])for(const x of doProcesso(D.processos.rows[k]))nproc.set(x,(nproc.get(x)||0)+1);
 return [...lista].sort((a,b)=>(peso.get(b)||0)-(peso.get(a)||0)||(nproc.get(b)||0)-(nproc.get(a)||0)||a-b)}
const munsOrdenados=e=>ordenarPorPeso(e,2,e.mun,r=>r[PC.municipios]);
// Situação do processo (classificação do Panorama, que a aba só mostra). "Operação ativa" vem apenas de título de lavra + CFEM recente: é
// indício de atividade, não confirmação de operação — na aba, o rótulo diz isso. As outras classes seguem a fonte, traduzidas.
function rotuloStatus(s){const x=D.dims.status[s];if(x==null)return '—';
 if(/^Opera/.test(x))return t('ea.st.lavraCfem');if(/^Lavra autorizada/.test(x))return t('ea.st.lavraSem');if(/^Recolhe CFEM/.test(x))return t('ea.st.cfemSemTitulo');
 if(/^Pré-lavra/.test(x))return t('ea.st.prelavra');if(/^Pesquisa/.test(x))return t('ea.st.pesquisa');if(/^Requerimento de licenciamento/.test(x))return t('ea.st.licGarimpo');
 if(/^Disponibilidade/.test(x))return t('ea.st.disponibilidade');if(/^Outros/.test(x))return t('ea.st.outros');return x}
const emDisponibilidade=k=>D.dims.fase[D.processos.rows[k][PC.fase]].grupo==='disponibilidade';
// Municípios da empresa pela ORIGEM do vínculo, nunca misturados num rótulo só:
// - op: operação documentada (municípios das operações que a própria empresa divulga; só nas empresas com detalhes);
// - vig: direitos ANM vigentes (processos fora de disponibilidade: lavra, requerimento, pesquisa, outros);
// - disp: só processos em disponibilidade (área devolvida à ANM): vínculo histórico/cadastral, não direito vigente;
// - cfem: só CFEM recolhida com origem no município, sem processo da empresa ligado a ele na base.
// vig ∪ disp ∪ cfem = e.mun (a lista "municípios" do pacote). Ordem: CFEM recolhida, depois processos, depois nome.
function munsPorOrigem(e){
 S.munOrig=S.munOrig||new Map();let c=S.munOrig.get(e.i);if(c)return c;
 const R=D.processos.rows,vig=new Map(),disp=new Map(),cf=new Map();
 for(const k of procsPorEmp.get(e.i)||[]){const a=emDisponibilidade(k)?disp:vig;for(const m of R[k][PC.municipios])a.set(m,(a.get(m)||0)+1)}
 for(const r of cfemPorEmp.get(e.i)||[])if(r[2]!=null&&D.dims.mun[r[2]])cf.set(r[2],(cf.get(r[2])||0)+r[4]);
 const det=D.detalhes[String(e.i)],op=[];
 if(det)for(const nome of det.municipios_operacao||[]){const k=D.dims.mun.findIndex(m=>norm(m[1])===norm(nome));if(k>=0&&!op.includes(k))op.push(k)}
 const ord=xs=>xs.sort((a,b)=>(cf.get(b)||0)-(cf.get(a)||0)||(vig.get(b)||0)-(vig.get(a)||0)||(disp.get(b)||0)-(disp.get(a)||0)||D.dims.mun[a][1].localeCompare(D.dims.mun[b][1],'pt'));
 c={op,vig:ord([...vig.keys()]),disp:ord([...disp.keys()].filter(k=>!vig.has(k))),cfem:ord([...cf.keys()].filter(k=>!vig.has(k)&&!disp.has(k))),nVig:vig,nDisp:disp,cf};
 c.processos=c.vig.length+c.disp.length;c.total=c.processos+c.cfem.length;
 S.munOrig.set(e.i,c);return c}
// origem do vínculo de UM município, para a prévia e o cartão do território
function origemMun(e,k){const o=munsPorOrigem(e);return {op:o.op.includes(k),vig:o.nVig.get(k)||0,disp:o.nDisp.get(k)||0,cfem:o.cf.get(k)||0}}
const minsOrdenados=e=>ordenarPorPeso(e,3,e.min,r=>[r[PC.mineral]]);
const textoReferencia=e=>{const r=referencia(e);return [r.mun?r.mun+(r.outros?` +${r.outros}`:''):null,r.min].filter(Boolean).join(' · ')||t('ea.semReferencia')};

// Processos da empresa que passam pelos filtros de território (município, mineral, fase).
// Município do recorte (índice em dims.mun) e o código IBGE dele; null sem município.
const munSel=()=>{const v=el('ea-mun')?el('ea-mun').value:'';return v===''?null:+v};
const ibgeDe=k=>k==null||!D.dims.mun[k]?null:String(D.dims.mun[k][0]);
const kDoIbge=c=>{if(!S.munK)S.munK=new Map(D.dims.mun.map((m,k)=>[String(m[0]),k]));const k=S.munK.get(String(c));return k===undefined?null:k};
const nomeMunUf=k=>D.dims.mun[k][1]+' · GO';
// Número ANM → URL oficial do cadastro (SCM da ANM). Só com o formato número/ano válido; senão, nenhum link.
function urlAnm(p){const m=/^(\d{3,6})\/(\d{4})$/.exec(String(p||'').replace(/\./g,''));
 return m?`https://sistemas.anm.gov.br/SCM/Extra/site/admin/dadosProcesso.aspx?numero=${m[1]}&ano=${m[2]}`:null}
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
// Fase mais avançada entre os processos (lavra autorizada → requerimento → pesquisa → disponibilidade → outro).
const faseMaisAvancada=ks=>ks.reduce((g,k)=>Math.min(g,Math.max(0,GRUPOS.indexOf(D.dims.fase[D.processos.rows[k][PC.fase]].grupo))),GRUPOS.length-1);

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
  linhas.push({e,ps,cf,v:valorMetrica(e,f,per,ps),gi:faseMaisAvancada(ps.length?ps:(procsPorEmp.get(e.i)||[]))});}
 // Ordem da lista: pela métrica (maior primeiro), pelo nome ou por relevância — com busca, quem casa melhor com o texto;
 // depois a fase mais avançada (lavra antes de pesquisa), a CFEM e o número de processos.
 if(f.ordem==='nome')linhas.sort((a,b)=>semNome(a.e)-semNome(b.e)||(semNome(a.e)?a.e.cnpj.localeCompare(b.e.cnpj):a.e.nome.localeCompare(b.e.nome,'pt')));
 else if(f.ordem==='relevancia'){linhas.forEach(l=>{l.r=f.q?relevanciaBusca(l.e,f.q):0});
  linhas.sort((a,b)=>a.r-b.r||a.gi-b.gi||b.cf-a.cf||b.ps.length-a.ps.length||a.e.nome.localeCompare(b.e.nome))}
 else linhas.sort((a,b)=>b.v-a.v||a.e.nome.localeCompare(b.e.nome));
 // Puxadores: o menor grupo que soma 80% da CFEM do recorte no período (Pareto).
 const porCfem=[...linhas].sort((a,b)=>b.cf-a.cf),total=porCfem.reduce((s,l)=>s+l.cf,0);
 S.puxadores=new Set();let acc=0;
 if(total>0)for(const l of porCfem){if(acc>=0.8*total)break;S.puxadores.add(l.e.i);acc+=l.cf}
 S.cfemTotal=total;S.universo=linhas;S.f=f;S.per=per;S.temFiltroTerr=temFiltroTerr;
 S.uni=new Map(linhas.map(l=>[l.e.i,l]));
 S.ranking=linhas;   // a lista mostra o recorte inteiro, em lotes ("mostrar mais"); a posição é a da ordem escolhida
 calcularProjetos();}

// Projetos do recorte: os ligados a empresas do universo (com filtro de território, só os que caem nele); sem vínculo, só sem filtros.
function calcularProjetos(){
 const f=S.f,semFiltro=!S.temFiltroTerr&&!f.dado&&!f.q,minNome=f.min!==''?norm(D.dims.min[+f.min][0]):null;
 const noTerr=p=>{if(!S.temFiltroTerr)return true;const loc=p.loc;
  if(loc&&loc.t==='p'){const ks=new Set();for(const i of p.e){const l=S.uni.get(i);if(l)l.ps.forEach(k=>ks.add(k))}return loc.k.some(k=>ks.has(k))}
  return (f.mun===''||(loc&&loc.m.includes(+f.mun)))&&(minNome===null||norm(p.mineral).includes(minNome))&&!f.grupo};
 S.projetos=D.projetos.filter(p=>(p.e.length?p.e.some(i=>S.uni.has(i)):semFiltro)&&noTerr(p))
  .sort((a,b)=>a.mat-b.mat||(!!b.loc-!!a.loc)||a.nome.localeCompare(b.nome));}

// ------------------------------------------------------------------ cabeçalho do recorte
// Faixa do recorte: quatro números, cada um com o período; o resto vai para a síntese do Ranking e para as análises.
const PERIODO_PADRAO='2022–2025';
function metricas(){
 const u=S.universo,procs=u.reduce((s,l)=>s+l.ps.length,0),per=S.per.join('–');
 const parcial=S.per[1]>=2026?' · '+t('ea.parcial2026',{meses:String(D.meta.meses_cfem_2026.length)}):'';
 el('ea-metrics').innerHTML=[
  [t('ea.m.empresas'),num(u.length),t('ea.m.empresasSub',{total:num(E.length)})],
  [t('ea.m.processos'),num(procs),t('ea.m.processosSub')],
  [t('ea.m.cfem',{per}),brl(S.cfemTotal),t('ea.m.cfemSub')+parcial],
  [t('ea.m.puxadores'),num(S.puxadores.size),t('ea.m.puxadoresSub',{per})],
 ].map(([r,v,d])=>`<div title="${escape(d)}"><dt>${escape(r)}</dt><dd><b>${escape(v)}</b><small class="sr-only">${escape(d)}</small></dd></div>`).join('');
 // filtros ativos: cada um vira uma etiqueta que se remove com um clique
 const f=S.f,chips=[];
 if(f.mun!=='')chips.push(['ea-mun',nomeMunUf(+f.mun)]);
 if(f.min!=='')chips.push(['ea-min',D.dims.min[+f.min][0]]);
 if(f.grupo)chips.push(['ea-grupo',rotuloGrupo(f.grupo)]);
 if(f.dado)chips.push(['ea-dado',el('ea-dado').selectedOptions[0].textContent]);
 if(per!==PERIODO_PADRAO)chips.push(['ea-periodo',t('ea.periodoChip',{per})]);
 if(f.q)chips.push(['ea-busca','“'+el('ea-busca').value.trim()+'”']);
 el('ea-context').innerHTML=chips.map(([id,txt])=>`<button type="button" class="ea-chip-f" data-limpa="${id}" title="${escape(t('ea.removerFiltro'))}">`
  +`${escape(txt)}<span aria-hidden="true">×</span><span class="sr-only"> · ${escape(t('ea.removerFiltro'))}</span></button>`).join('');
 el('ea-context').hidden=!chips.length;
 const nf=chips.filter(c=>c[0]!=='ea-busca').length;
 el('ea-filtros-n').hidden=!nf;el('ea-filtros-n').textContent=nf?String(nf):'';
 el('ea-reset').hidden=!chips.length;
 el('ea-lista-btn-txt').textContent=t('ea.abrirListaN',{n:num(u.length)})+(nf?` · ${t('ea.filtrosN',{n:String(nf)})}`:'');}

// ------------------------------------------------------------------ lista lateral: o recorte inteiro, em lotes, na ordem escolhida
const LOTE=50;
function fmtMetrica(v,m){return m==='cfem'?brl(v):m==='area'?num(v,0)+' ha':m==='ccee'?num(v,0)+' MWh':num(v);}
// "Mostrar mais": devolve quantos itens desenhar agora.
function maisLista(total,desenhar){
 const n=Math.min(S.nLista,total),resto=total-n;
 el('ea-pag').innerHTML=resto>0?`<button type="button" class="ea-mais" data-mais>${escape(t('ea.maisLista',{n:num(Math.min(LOTE,resto))}))}</button>`
   +`<span>${escape(t('ea.listaConta',{v:num(n),n:num(total)}))}</span>`
  :total>LOTE?`<span>${escape(t('ea.listaTodas',{n:num(total)}))}</span>`:'';
 const b=el('ea-pag').querySelector('[data-mais]');
 if(b)b.onclick=()=>{S.nLista+=LOTE;desenhar();const it=el('ea-lista').querySelectorAll('.ea-item')[n];if(it)it.focus({preventScroll:true})};
 return n}
// Rola só a lista (não a página) até o item marcado.
function rolarLista(){
 const L_=el('ea-lista'),b=L_.querySelector('.ea-item.on');if(!b)return;
 const li=b.parentNode,top=li.offsetTop,h=li.offsetHeight;
 if(top<L_.scrollTop)L_.scrollTop=top-6;else if(top+h>L_.scrollTop+L_.clientHeight)L_.scrollTop=top+h-L_.clientHeight+6}
function lista(){
 const proj=S.modo==='projetos';
 el('ea-lista-ctl').hidden=proj;el('ea-exp-json').hidden=proj;el('ea-ranking-btn').hidden=proj;
 if(proj)return listaProjetos();
 const rk=S.ranking,m=S.f.metrica,n=maisLista(rk.length,lista);
 el('ea-lista-titulo').textContent=t('ea.listaN',{n:num(rk.length)});
 // CCEE é a carga do agente inteiro (CNPJ raiz em Goiás): com filtro de município, mineral ou fase, não vira "consumo do recorte"
 el('ea-lista-sub').textContent=m==='ccee'&&S.temFiltroTerr?t('ea.cceeAgenteNota'):'';el('ea-lista-titulo').title=t('ea.listaDica',{metrica:rotuloMetrica(m)});
 const semCcee=l=>m==='ccee'&&!cceePeriodo(l.e,S.per).meses;
 el('ea-lista').innerHTML=n?rk.slice(0,n).map((l,j)=>{
  const e=l.e,on=S.sel===e.i,pux=S.puxadores.has(e.i);
  const dica=t('ea.tip.faseMax',{fase:rotuloGrupo(GRUPOS[l.gi])})+(pux?' · '+t('ea.puxadorTip'):'');
  return `<li><button type="button" class="ea-item${on?' on':''}" data-i="${e.i}" aria-pressed="${on}">`
   +`<span class="ea-pos">${j+1}</span>`
   +`<span class="ea-nome"><b title="${escape(e.nome)}">${escape(e.nome)}</b><small><i class="ea-dot${pux?' ea-dot-pux':''}" style="background:${COR[GRUPOS[l.gi]]}" title="${escape(dica)}"></i>`
   +`<span class="ea-ref">${escape(textoReferencia(e))}</span>${pux?`<span class="sr-only"> · ${escape(t('ea.puxador'))}</span>`:''}`
   +(e.enr?`<em class="ea-tag-enr" title="${escape(t('ea.enrTip'))}">${escape(t('ea.enr'))}</em>`:'')
   +(S.locE&&!S.locE.has(e.i)?`<em class="ea-tag-sempt" title="${escape(t('ea.semPontoLocalDica'))}">${escape(t('ea.semPontoLocal'))}</em>`:'')+`</small></span>`
   +`<span class="ea-val">${semCcee(l)?`<span class="muted" title="${escape(t('ea.semCceeTip'))}">—</span>`:escape(fmtMetrica(l.v,m))}</span></button></li>`}).join('')
  :`<li class="empty">${escape(t('ea.vazio'))}</li>`;
 el('ea-lista').querySelectorAll('.ea-item').forEach(b=>b.onclick=()=>{selecionar(+b.dataset.i,{origem:'lista'});gaveta(false)});}

const rotuloLocal=p=>!p.loc?t('ea.loc.sem'):p.loc.t==='p'?t('ea.loc.processo'):t('ea.loc.municipio');
function listaProjetos(){
 const ps=S.projetos,n=maisLista(ps.length,listaProjetos);
 const c={p:0,m:0,sem:0};ps.forEach(p=>c[p.loc?p.loc.t:'sem']++);
 el('ea-lista-titulo').textContent=t('ea.projListaT',{n:num(ps.length)});
 el('ea-lista-sub').textContent=t('ea.projListaS',{p:num(c.p),m:num(c.m),s:num(c.sem)});
 el('ea-lista').innerHTML=n?ps.slice(0,n).map(p=>{const on=S.sel!==null&&p.e.includes(S.sel);
  const emp=p.e.length?porI.get(p.e[0]).nome+(p.e.length>1?' +'+(p.e.length-1):''):t('ea.semVinculo');
  return `<li><button type="button" class="ea-item ea-item-proj${on?' on':''}" data-j="${p.j}" aria-pressed="${on}">`
   +`<span class="ea-mat" style="background:${MAT[p.mat][2]}" title="${escape(rotuloMat(p.mat))}"></span>`
   +`<span class="ea-nome"><b>${escape(p.nome)}</b><small>${escape(emp)}${p.mineral?' · '+escape(p.mineral):''}</small></span>`
   +`<span class="ea-val"><em class="ea-tag-mat">${escape(p.maturidade||'—')}</em><small class="ea-loc ea-loc-${p.loc?p.loc.t:'sem'}">${escape(rotuloLocal(p))}</small></span></button></li>`}).join('')
  :`<li class="empty">${escape(t('ea.projVazio'))}</li>`;
 el('ea-lista').querySelectorAll('[data-j]').forEach(b=>b.onclick=()=>{abrirProjeto(D.projetos[+b.dataset.j],{origem:'lista'});gaveta(false)});}

// Gaveta da lista (tablet e celular): abre por cima do mapa; Esc, o × ou o fundo fecham.
function gaveta(abrir){
 const lat=el('ea-lateral'),on=!!abrir&&!largo.matches;
 if(lat.classList.contains('aberta')===on)return;
 lat.classList.toggle('aberta',on);el('ea-lat-fundo').hidden=!on;el('ea-lista-btn').setAttribute('aria-expanded',String(on));
 if(on)setTimeout(()=>el('ea-filtros-btn').focus(),30);
 else if(lat.contains(document.activeElement))el('ea-lista-btn').focus({preventScroll:true});}
// A busca é uma só: na lateral do Explorar (mesa) ou no alto da aba (outras áreas e telas estreitas).
function posicionarBusca(){
 const box=el('ea-busca-box'),lateral=S.area==='explorar'&&largo.matches,alvo=el(lateral?'ea-busca-lat':'ea-busca-topo');
 if(box.parentNode!==alvo){const foco=document.activeElement===el('ea-busca');alvo.appendChild(box);if(foco)el('ea-busca').focus()}
 el('ea-sel').hidden=S.area==='explorar';el('ea-topbar').hidden=lateral;
 if(largo.matches)gaveta(false);}

// ------------------------------------------------------------------ busca com autocomplete (combobox ARIA), sempre visível
function combobox(inp,box,{gerar,escolher}){
 const st={itens:[],ativa:-1,consulta:null};
 const fechar=()=>{box.hidden=true;inp.setAttribute('aria-expanded','false');inp.removeAttribute('aria-activedescendant')};
 const marcar=j=>{const lis=[...box.querySelectorAll('[data-j]')];lis.forEach((li,k)=>li.setAttribute('aria-selected',String(k===j)));
  st.ativa=j;if(lis[j]){inp.setAttribute('aria-activedescendant',lis[j].id);lis[j].scrollIntoView({block:'nearest'})}};
 const abrir=()=>{const q=norm(inp.value.trim());st.consulta=q;if(q.length<2){fechar();return}
  st.itens=gerar(q);st.ativa=-1;
  const rotTipo={empresa:t('ea.sug.empresa'),processo:t('ea.sug.processo'),mun:t('ea.sug.munT'),min:t('ea.sug.minT')};
  box.innerHTML=st.itens.length?st.itens.map((s,j)=>`<li role="option" id="${box.id}-${j}" data-j="${j}" aria-selected="false">`
    +`<span class="ea-sug-tipo">${escape(rotTipo[s.tipo])}</span><b>${escape(s.rot)}</b><small>${escape(s.sub)}</small></li>`).join('')
   :`<li class="ea-sug-vazia" role="option" aria-disabled="true">${escape(t('ea.semSugestao'))}</li>`;
  box.hidden=false;inp.setAttribute('aria-expanded','true');
  box.querySelectorAll('[data-j]').forEach(li=>li.onmousedown=ev=>{ev.preventDefault();const s=st.itens[+li.dataset.j];fechar();escolher(s)})};
 inp.addEventListener('keydown',ev=>{const n=st.itens.length;
  if(ev.key==='ArrowDown'){ev.preventDefault();if(box.hidden)abrir();marcar(Math.min(n-1,st.ativa+1))}
  else if(ev.key==='ArrowUp'){ev.preventDefault();marcar(Math.max(0,st.ativa-1))}
  else if(ev.key==='Enter'){ev.preventDefault();
   // Enter antes do fim da espera da digitação: as sugestões ainda são da consulta anterior, então refaz agora.
   if(st.consulta!==norm(inp.value.trim()))abrir();
   const s=st.itens[st.ativa>=0?st.ativa:0];if(s){fechar();escolher(s)}}
  else if(ev.key==='Escape'){if(!box.hidden){ev.stopPropagation();fechar()}}});
 inp.addEventListener('blur',()=>setTimeout(fechar,120));
 return {abrir,fechar};}
function sugestoesEmpresas(q,lim){const out=[];
 for(const x of idxBusca){if(x.txt.includes(q)){const e=porI.get(x.i);out.push({tipo:'empresa',i:e.i,rot:e.nome,sub:cnpjFmt(e.cnpj)+(e.grupo?' · '+e.grupo:'')});if(out.length>=lim)break}}
 return out;}
function sugestoesBusca(q){
 const out=[],dig=soDigitos(q);
 // processo ANM: '860.337/2020' = '860337/2020' = '8603372020'
 if(dig.length>=6){for(const[id,k]of procPorId){if(id.startsWith(dig)){const r=D.processos.rows[k];
   out.push({tipo:'processo',k,rot:r[PC.processo],sub:r[PC.empresa]>=0?porI.get(r[PC.empresa]).nome:t(r[PC.empresa]===-2?'ea.pf':'ea.semTitular')});if(out.length>=5)break}}}
 out.push(...sugestoesEmpresas(q,8));
 D.dims.mun.forEach((m,k)=>{if(norm(m[1]).includes(q)&&out.filter(o=>o.tipo==='mun').length<4)out.push({tipo:'mun',k,rot:nomeMunUf(k),sub:t('ea.sug.mun')})});
 D.dims.min.forEach((m,k)=>{if(norm(m[0]).includes(q)&&out.filter(o=>o.tipo==='min').length<4)out.push({tipo:'min',k,rot:m[0],sub:t('ea.sug.min')})});
 return out.slice(0,16);}
function escolherBusca(s){
 el('ea-busca').value='';redesenhar();
 if(s.tipo==='empresa'){selecionar(s.i,{origem:'busca'});return}
 // processo: o próprio processo (modo Processos, cartão do processo), não a empresa titular no lugar dele
 if(s.tipo==='processo'){const r=D.processos.rows[s.k];mostrarArea('explorar');if(S.modo!=='processos')definirModo('processos');
  selecionarProcesso(s.k,{ir:true});if(r[PC.empresa]<0)avisoMapa(t(r[PC.empresa]===-2?'ea.pfAviso':'ea.semTitularAviso'));return}
 mostrarArea('explorar');
 if(s.tipo==='mun')selecionarMunicipio(s.k,{origem:'busca'});
 else if(s.tipo==='min'){el('ea-min').value=String(s.k);redesenhar()}}

// ------------------------------------------------------------------ mapa: um só, em três modos
// Empresas: um ponto por empresa (centroide do processo de referência), tamanho pela métrica, cor pela fase mais avançada.
// Processos: cada direito minerário de empresa é um ponto fino no centroide do título, com polígonos ANM ao aproximar.
// Projetos: losango no centroide do processo citado pelo projeto (indicativo) ou, vazado, na referência do município (aproximado).
// Tudo é desenhado numa camada Canvas única, a partir de coordenadas projetadas uma vez só: mover ou aproximar só repinta.
const BOUNDS=[[-19.6,-53.4],[-12.3,-45.8]];
const ORDEM_DESENHO={pesquisa:0,disponibilidade:1,outro:1,requerimento_lavra:2,lavra_autorizada:3};
const MP={n:0};    // processos de titular PJ com centroide, na ordem de desenho (pesquisa por baixo, lavra por cima)
const MPE={n:0};   // empresas com ponto de referência
const MPJ={n:0};   // projetos com localização
const goBounds=()=>S.go||L.latLngBounds(BOUNDS);
const ZOOM_POLIGONOS=11.5;
const projetar=(lat,lon)=>L.CRS.EPSG3857.latLngToPoint(L.latLng(lat,lon),0);
function prepararPontos(){
 const R=D.processos.rows,ks=[];
 const gi=k=>{const g=GRUPOS.indexOf(D.dims.fase[R[k][PC.fase]].grupo);return g<0?GRUPOS.length-1:g};
 for(let k=0;k<R.length;k++)if(R[k][PC.lat]!=null&&R[k][PC.empresa]>=0)ks.push(k);
 ks.sort((a,b)=>ORDEM_DESENHO[GRUPOS[gi(a)]]-ORDEM_DESENHO[GRUPOS[gi(b)]]||a-b);
 const n=ks.length;Object.assign(MP,{n,k:Int32Array.from(ks),x:new Float64Array(n),y:new Float64Array(n),g:new Uint8Array(n),j:new Int32Array(R.length).fill(-1)});
 ks.forEach((k,j)=>{const p=projetar(R[k][PC.lat],R[k][PC.lon]);MP.x[j]=p.x;MP.y[j]=p.y;MP.g[j]=gi(k);MP.j[k]=j});
 S.vis=new Uint8Array(R.length);S.selMarca=new Uint8Array(R.length);S.selJ=[];
 const es=E.filter(e=>e.pt>=0&&R[e.pt][PC.lat]!=null);
 Object.assign(MPE,{n:es.length,i:Int32Array.from(es.map(e=>e.i)),x:new Float64Array(es.length),y:new Float64Array(es.length),pos:new Map()});
 es.forEach((e,j)=>{const p=projetar(R[e.pt][PC.lat],R[e.pt][PC.lon]);MPE.x[j]=p.x;MPE.y[j]=p.y;MPE.pos.set(e.i,j)});
 prepararProjetos();}
// Projetos: processo citado → centroide do maior deles; só município → referência do município (depois que os municípios chegam).
function prepararProjetos(){
 const R=D.processos.rows,itens=[];
 for(const p of D.projetos){const loc=p.loc;if(!loc)continue;
  if(loc.t==='p'){const k=loc.k[0];itens.push([p.j,projetar(R[k][PC.lat],R[k][PC.lon]),0])}
  else if(S.munCentro){const c=S.munCentro.get(D.dims.mun[loc.m[0]][0]);if(c)itens.push([p.j,projetar(c[0],c[1]),1])}}
 Object.assign(MPJ,{n:itens.length,j:Int32Array.from(itens.map(x=>x[0])),x:Float64Array.from(itens.map(x=>x[1].x)),y:Float64Array.from(itens.map(x=>x[1].y)),
  tipo:Uint8Array.from(itens.map(x=>x[2])),pos:new Map(itens.map((x,q)=>[x[0],q]))});}

const RAIOS=[[5,1.3],[6,1.5],[7,1.9],[8,2.4],[9,2.9],[10,3.4],[11,4],[12,4.6],[13,5.2],[16,6.2]];
function raioPonto(z){for(let i=1;i<RAIOS.length;i++)if(z<=RAIOS[i][0]){const [z0,r0]=RAIOS[i-1],[z1,r1]=RAIOS[i];return r0+(r1-r0)*Math.max(0,Math.min(1,(z-z0)/(z1-z0)))}return 6.2}
const raioSel=z=>Math.max(3.4,raioPonto(z)*1.3+1);
// Hierarquia de fase: lavra autorizada maior e mais forte, requerimento médio, pesquisa/disponibilidade menores e claras.
const HIER_RAIO={lavra_autorizada:1.45,requerimento_lavra:1.1,pesquisa:.75,disponibilidade:.75,outro:.75};
const HIER_ALFA={lavra_autorizada:.95,requerimento_lavra:.85,pesquisa:.42,disponibilidade:.42,outro:.42};
function estiloFase(gi,z){const g=GRUPOS[gi];return {r:raioPonto(z)*HIER_RAIO[g],a:HIER_ALFA[g],traco:g==='lavra_autorizada'?z>=8:z>=10}}
// Fases (e maturidades) desligadas pela legenda: só no mapa; lista e indicadores seguem os filtros. Não é lembrado entre visitas.
const faseVisivel=gi=>!S.off.has(gi);
// Raio do ponto da empresa: área proporcional à métrica escolhida no recorte (raiz quadrada), com um piso visível.
function raioEmpresa(v,vmax,z){const f=Math.max(.85,Math.min(1.6,.85+(z-6)*.09));return (vmax>0&&v>0?3+15*Math.sqrt(v/vmax):2.4)*f}
const raioProjeto=(z,mat)=>Math.max(4.2,raioPonto(z)*1.7)*(mat<=1?1.2:1);

// Anéis em coordenadas de zoom 0 (lista plana x,y), com a caixa para descartar rápido o que está fora da tela.
function projetarAneis(rings){
 let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
 const out=rings.filter(r=>r.length>2).map(r=>{const a=new Float64Array(r.length*2);
  for(let i=0;i<r.length;i++){const q=projetar(r[i][0],r[i][1]);a[2*i]=q.x;a[2*i+1]=q.y;
   if(q.x<x0)x0=q.x;if(q.x>x1)x1=q.x;if(q.y<y0)y0=q.y;if(q.y>y1)y1=q.y}return a});
 return out.length?{rings:out,bb:[x0,y0,x1,y1]}:null}
// Contornos de município simplificados (Douglas-Peucker do Leaflet, 0,7 px) para cada meio nível de zoom, calculados na primeira vez.
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
// Caixa (zoom 0) do polígono ANM de cada processo da camada, calculada uma vez depois que a geometria chega: [x0,y0,x1,y1] por posição em
// MP; sem polígono, a caixa é vazia (x0 > x1) e o processo não entra como polígono.
function caixasPoligonos(){
 if(S.bbPoli)return S.bbPoli;const R=D.processos.rows,bb=new Float64Array(MP.n*4);
 for(let j=0;j<MP.n;j++){const g=S.geo&&S.geo.get(R[MP.k[j]][PC.processo]);bb[4*j]=1;bb[4*j+2]=0;if(!g||!g.rings||!g.rings.length)continue;
  let la0=Infinity,la1=-Infinity,lo0=Infinity,lo1=-Infinity;for(const r of g.rings)for(const q of r){if(q[0]<la0)la0=q[0];if(q[0]>la1)la1=q[0];if(q[1]<lo0)lo0=q[1];if(q[1]>lo1)lo1=q[1]}
  const a=projetar(la1,lo0),b=projetar(la0,lo1);bb[4*j]=a.x;bb[4*j+1]=a.y;bb[4*j+2]=b.x;bb[4*j+3]=b.y}
 return S.bbPoli=bb}
function dentroPoligono(p,X,Y){
 const b=p.bb;if(X<b[0]||X>b[2]||Y<b[1]||Y>b[3])return false;let d=false;
 for(const a of p.rings)for(let i=0,j=a.length-2;i<a.length;j=i,i+=2){const xi=a[i],yi=a[i+1],xj=a[j],yj=a[j+1];
  if((yi>Y)!==(yj>Y)&&X<(xj-xi)*(Y-yi)/(yj-yi)+xi)d=!d}
 return d}

// Índice espacial em grade (pixels da camada) para tooltip e clique: cada entrada é [tipo, id, x, y, raio]
// (tipo 0 = processo, id = posição em MP; 1 = empresa, id = i; 2 = projeto, id = posição em D.projetos). Montado na primeira consulta.
const T_PROC=0,T_EMP=1,T_PROJ=2;
const GRADE={T:16,cel:new Map(),pend:[],
 limpar(){this.cel.clear();this.pend=[]},
 add(tp,id,x,y,r){const k=Math.floor(x/this.T)*1e6+Math.floor(y/this.T);let a=this.cel.get(k);if(!a)this.cel.set(k,a=[]);a.push(tp,id,x,y,r)},
 perto(x,y,minimo){if(this.pend.length){const fs=this.pend;this.pend=[];fs.forEach(f=>f())}
  const out=[],cx=Math.floor(x/this.T),cy=Math.floor(y/this.T),alc=2;
  for(let i=cx-alc;i<=cx+alc;i++)for(let k=cy-alc;k<=cy+alc;k++){const a=this.cel.get(i*1e6+k);if(!a)continue;
   for(let m=0;m<a.length;m+=5){const dx=a[m+2]-x,dy=a[m+3]-y,d=dx*dx+dy*dy,rr=Math.max(minimo,a[m+4]+3);if(d<=rr*rr)out.push([d,a[m],a[m+1]])}}
  out.sort((p,q)=>p[0]-q[0]);const vistos=new Set();
  return out.filter(o=>{const c=o[1]+':'+o[2];if(vistos.has(c))return false;vistos.add(c);return true}).map(o=>({t:o[1],id:o[2]}))}};

// Desenho, de baixo para cima: contornos de município, polígonos (área visível em zoom ≥ 11,5 no modo Processos; empresa escolhida;
// processo destacado) e os símbolos do modo. Os pontos vão um a um: com rasterização forçada, foi o mais rápido dos jeitos medidos.
const ORDEM_GRUPOS=['pesquisa','disponibilidade','outro','requerimento_lavra','lavra_autorizada'].map(g=>GRUPOS.indexOf(g));
function pintarMapa(ctx,b){
 GRADE.limpar();S.nPontos=0;S.poliDesenhados=[];if(!S.mapa)return;
 const m=S.mapa,z=m.getZoom(),o=m.getPixelOrigin(),s=Math.pow(2,z),pad=24;
 const V={ctx,z,o,s,x0:b.min.x-pad,x1:b.max.x+pad,y0:b.min.y-pad,y1:b.max.y+pad,
  X0:(b.min.x+o.x)/s,X1:(b.max.x+o.x)/s,Y0:(b.min.y+o.y)/s,Y1:(b.max.y+o.y)/s,TAU:Math.PI*2};
 const fora=bb=>bb[2]<V.X0||bb[0]>V.X1||bb[3]<V.Y0||bb[1]>V.Y1;
 const comSel=S.sel!==null,so=comSel&&S.soSel;
 const caminho=p=>{ctx.beginPath();for(const a of p.rings){for(let i=0;i<a.length;i+=2){const x=a[i]*s-o.x,y=a[i+1]*s-o.y;if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y)}ctx.closePath()}};
 if(S.munProj){ctx.beginPath();
  for(const p of munNoZoom(z)){if(fora(p.bb))continue;
   for(const a of p.rings){for(let i=0;i<a.length;i+=2){const x=a[i]*s-o.x,y=a[i+1]*s-o.y;if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y)}ctx.closePath()}}
  ctx.globalAlpha=.6;ctx.lineWidth=.5;ctx.strokeStyle='#9fb3c2';ctx.stroke();ctx.globalAlpha=1;
  // município do recorte: contorno real (multipartes e buracos pela regra par-ímpar), preenchimento translúcido e traço com halo
  const pm=S.munIdx&&munSel()!==null?S.munIdx.get(ibgeDe(munSel())):undefined,pz=pm!==undefined?munNoZoom(z)[pm]:null;
  S.munDesenhado=null;
  if(pz&&!fora(pz.bb)){caminho(pz);ctx.fillStyle='rgba(15,111,176,.07)';ctx.fill('evenodd');ctx.lineJoin='round';
   ctx.lineWidth=4.5;ctx.strokeStyle='rgba(255,255,255,.75)';ctx.stroke();ctx.lineWidth=2;ctx.strokeStyle='#0f6fb0';ctx.stroke();
   S.munDesenhado={ibge:ibgeDe(munSel()),aneis:pz.rings.length}}}
 // Polígonos só são alvo de clique no modo Processos; nos outros modos (realce da empresa escolhida) são desenho, sem clique nem dica.
 const alvo=S.modo==='processos';
 const poli=(k,alfaFundo,larg,cor)=>{const p=projetado(k);if(!p||fora(p.bb))return;const c=COR[D.dims.fase[D.processos.rows[k][PC.fase]].grupo]||COR.outro;
  caminho(p);ctx.globalAlpha=alfaFundo;ctx.fillStyle=c;ctx.fill('evenodd');ctx.globalAlpha=1;ctx.lineWidth=larg;ctx.strokeStyle=cor||c;ctx.stroke();if(alvo)S.poliDesenhados.push(k)};
 if(S.geo){
  if(S.modo==='processos'&&z>=ZOOM_POLIGONOS&&el('ea-poligonos').checked&&!so){
   // candidato = polígono cuja caixa cruza a tela (não o centroide): um título que atravessa o município aparece mesmo com o centroide longe
   const bb=caixasPoligonos();let n=0;
   for(let j=0;j<MP.n&&n<1500;j++){const k=MP.k[j];if(!S.vis[k]||(comSel&&S.selMarca[k])||k===S.destaque||!faseVisivel(MP.g[j]))continue;
    if(bb[4*j]>bb[4*j+2])continue;if(bb[4*j+2]<V.X0||bb[4*j]>V.X1||bb[4*j+3]<V.Y0||bb[4*j+1]>V.Y1)continue;poli(k,.12,.8);n++}}
  if(comSel&&S.modo!=='projetos')for(const j of S.selJ){const k=MP.k[j];if(k!==S.destaque&&faseVisivel(MP.g[j]))poli(k,.28,1.4)}
  if(S.destaque!==null&&alvo)poli(S.destaque,.45,3,'#062844')}
 if(S.modo==='empresas')pintarEmpresas(V);else if(S.modo==='projetos')pintarProjetos(V);else pintarProcessos(V);}

function circulo(V,x,y,r,traco){const c=V.ctx;c.beginPath();c.arc(x,y,r,0,V.TAU);c.fill();if(traco)c.stroke()}
const naTela=(V,x,y)=>x>=V.x0&&x<=V.x1&&y>=V.y0&&y<=V.y1;
// Processos da empresa escolhida, por cima de tudo: halo branco, cor da fase e contorno azul-marinho.
function pintarProcessosDaEmpresa(V){
 const selVis=S.selJ.filter(j=>faseVisivel(MP.g[j]));if(!selVis.length)return 0;
 // no modo Processos são alvos (halo e contorno escuro); nos outros modos, contexto: menores, translúcidos, sem contorno escuro
 const alvo=S.modo==='processos',c=V.ctx,rs=alvo?raioSel(V.z):Math.max(2.4,raioSel(V.z)*.72);let n=0;
 if(alvo){c.fillStyle='rgba(255,255,255,.95)';for(const j of selVis){const x=MP.x[j]*V.s-V.o.x,y=MP.y[j]*V.s-V.o.y;if(naTela(V,x,y))circulo(V,x,y,rs+1.6)}}
 c.lineWidth=alvo?1.4:.8;c.strokeStyle=alvo?'#062844':'rgba(255,255,255,.9)';c.globalAlpha=alvo?1:.6;
 for(const g of ORDEM_GRUPOS){c.fillStyle=COR[GRUPOS[g]];
  for(const j of selVis){if(MP.g[j]!==g)continue;const x=MP.x[j]*V.s-V.o.x,y=MP.y[j]*V.s-V.o.y;if(!naTela(V,x,y))continue;circulo(V,x,y,rs,true);n++}}
 c.globalAlpha=1;
 // no modo Empresas é realce de contexto: entra no índice de clique só no modo Processos
 if(S.modo==='processos')GRADE.pend.push(()=>{for(const j of selVis){const x=MP.x[j]*V.s-V.o.x,y=MP.y[j]*V.s-V.o.y;if(naTela(V,x,y))GRADE.add(T_PROC,j,x,y,rs)}});
 return n}
// Processo em foco (modo Processos): halo branco e anel azul-marinho no centroide, também quando o polígono não carregou
// (e para o processo de pessoa física ou sem titular achado pela busca, que não tem ponto próprio na camada).
function pintarDestaque(V){
 const k=S.destaque;if(k===null)return;const r=D.processos.rows[k];if(r[PC.lat]==null)return;
 const q=projetar(r[PC.lat],r[PC.lon]),x=q.x*V.s-V.o.x,y=q.y*V.s-V.o.y;if(!naTela(V,x,y))return;
 const c=V.ctx,rr=Math.max(5,raioSel(V.z)+1.5),g=D.dims.fase[r[PC.fase]].grupo;
 c.globalAlpha=1;c.fillStyle='rgba(255,255,255,.95)';circulo(V,x,y,rr+2.6);
 c.fillStyle=COR[g]||COR.outro;c.lineWidth=2.4;c.strokeStyle='#062844';circulo(V,x,y,rr,true)}

function pintarProcessos(V){
 const c=V.ctx,comSel=S.sel!==null,so=comSel&&S.soSel,r=raioPonto(V.z);
 const fundo=j=>!so&&S.vis[MP.k[j]]&&!(comSel&&S.selMarca[MP.k[j]])&&faseVisivel(MP.g[j]);
 const varrer=(teste,raio,traco)=>{let n=0;for(let j=0;j<MP.n;j++){if(!teste(j))continue;const x=MP.x[j]*V.s-V.o.x,y=MP.y[j]*V.s-V.o.y;
   if(!naTela(V,x,y))continue;circulo(V,x,y,raio,traco);n++}return n};
 let n=0;
 if(!so&&comSel){c.globalAlpha=.32;c.fillStyle='#8d9eab';n+=varrer(fundo,Math.max(1.2,r*.85),false);c.globalAlpha=1}
 else if(!so){c.lineWidth=.8;c.strokeStyle='rgba(255,255,255,.9)';
  for(const g of ORDEM_GRUPOS){const st=estiloFase(g,V.z);c.globalAlpha=st.a;c.fillStyle=COR[GRUPOS[g]];n+=varrer(j=>MP.g[j]===g&&fundo(j),st.r,st.traco)}
  c.globalAlpha=1}
 if(comSel)n+=pintarProcessosDaEmpresa(V);
 pintarDestaque(V);
 S.nPontos=n;
 GRADE.pend.push(()=>{for(let j=0;j<MP.n;j++){if(!fundo(j))continue;const x=MP.x[j]*V.s-V.o.x,y=MP.y[j]*V.s-V.o.y;
  if(naTela(V,x,y))GRADE.add(T_PROC,j,x,y,comSel?r*.85:estiloFase(MP.g[j],V.z).r)}});}

function pintarEmpresas(V){
 const c=V.ctx,comSel=S.sel!==null,so=comSel&&S.soSel,vmax=S.vmax||0,desenhadas=[];let n=0;
 // do maior para o menor: os pequenos ficam por cima e continuam clicáveis
 for(const q of S.ptsEmp||[]){const i=q.i;if(comSel&&i===S.sel)continue;if(so)continue;
  const l=S.uni.get(i);if(!l||!faseVisivel(l.gi))continue;
  const x=q.x*V.s-V.o.x,y=q.y*V.s-V.o.y;if(!naTela(V,x,y))continue;
  const r=raioEmpresa(l.v,vmax,V.z);
  if(comSel){c.globalAlpha=.3;c.fillStyle='#8d9eab';circulo(V,x,y,Math.max(1.6,r*.7))}
  else{c.globalAlpha=l.v>0?.78:.5;c.fillStyle=COR[GRUPOS[l.gi]];c.lineWidth=S.puxadores.has(i)?1.8:.8;
   c.strokeStyle=S.puxadores.has(i)?'#062844':'rgba(255,255,255,.95)';circulo(V,x,y,r,true)}
  desenhadas.push([i,x,y,comSel?Math.max(1.6,r*.7):r]);n++}
 c.globalAlpha=1;
 if(comSel){n+=pintarProcessosDaEmpresa(V);
  const q=posEmpresa(S.sel),l=S.uni.get(S.sel);
  if(q){const x=q.x*V.s-V.o.x,y=q.y*V.s-V.o.y,r=Math.max(7,raioEmpresa(l?l.v:0,vmax,V.z));
   if(naTela(V,x,y)){c.fillStyle='rgba(255,255,255,.95)';circulo(V,x,y,r+3);c.fillStyle=COR[GRUPOS[l?l.gi:faseMaisAvancada(procsPorEmp.get(S.sel)||[])]];
    c.lineWidth=2.4;c.strokeStyle='#062844';circulo(V,x,y,r,true);desenhadas.push([S.sel,x,y,r]);n++}}}
 S.nPontos=n;
 GRADE.pend.push(()=>desenhadas.forEach(([i,x,y,r])=>GRADE.add(T_EMP,i,x,y,r)));}

function losango(V,x,y,r,cheio){const c=V.ctx;c.beginPath();c.moveTo(x,y-r);c.lineTo(x+r,y);c.lineTo(x,y+r);c.lineTo(x-r,y);c.closePath();
 if(cheio){c.fill();c.stroke()}else{c.save();c.fillStyle='rgba(255,255,255,.88)';c.fill();c.restore();c.stroke()}}
function pintarProjetos(V){
 const c=V.ctx,comSel=S.sel!==null,so=comSel&&S.soSel,desenhadas=[];let n=0;
 const vis=S.projVis||[];
 const um=(q,dest)=>{const p=D.projetos[MPJ.j[q]],x=MPJ.x[q]*V.s-V.o.x,y=MPJ.y[q]*V.s-V.o.y;if(!naTela(V,x,y))return;
  const r=raioProjeto(V.z,p.mat)*(dest?1.15:1),cheio=MPJ.tipo[q]===0;
  if(comSel&&!dest){c.globalAlpha=.35;c.fillStyle='#a9b7c2';c.strokeStyle='#a9b7c2';c.lineWidth=1.2}
  else{c.globalAlpha=1;c.fillStyle=MAT[p.mat][2];c.strokeStyle=cheio?(dest?'#062844':'rgba(255,255,255,.95)'):MAT[p.mat][2];c.lineWidth=cheio?(dest?1.8:1):2.2}
  losango(V,x,y,r,cheio);desenhadas.push([p.j,x,y,r]);n++};
 // por baixo os de maturidade menor; com empresa escolhida, os dela por cima
 const ordem=[];for(let q=0;q<MPJ.n;q++){const p=D.projetos[MPJ.j[q]];if(vis[p.j]&&!S.matOff.has(p.mat))ordem.push(q)}
 ordem.sort((a,b)=>D.projetos[MPJ.j[b]].mat-D.projetos[MPJ.j[a]].mat);
 const daSel=q=>comSel&&D.projetos[MPJ.j[q]].e.includes(S.sel);
 if(!so)for(const q of ordem)if(!daSel(q))um(q,false);
 for(const q of ordem)if(daSel(q))um(q,true);
 c.globalAlpha=1;S.nPontos=n;
 // Agrupamento: projetos no mesmo lugar (a referência de um município, o mesmo processo) ganham a contagem; o clique lista todos.
 const grupos=new Map();for(const d of desenhadas){const k=Math.round(d[1]/3)+','+Math.round(d[2]/3),g=grupos.get(k);if(g)g.n++;else grupos.set(k,{x:d[1],y:d[2],r:d[3],n:1})}
 c.font='700 9px Manrope,sans-serif';c.textAlign='center';c.textBaseline='middle';
 for(const g of grupos.values())if(g.n>1){const bx=g.x+g.r*.85,by=g.y-g.r*.85,br=6.5;
  c.fillStyle='#062844';c.beginPath();c.arc(bx,by,br,0,V.TAU);c.fill();c.lineWidth=1.2;c.strokeStyle='#fff';c.stroke();
  c.fillStyle='#fff';c.fillText(g.n>9?'9+':String(g.n),bx,by+.5)}
 S.gruposProj=[...grupos.values()].filter(g=>g.n>1).length;
 GRADE.pend.push(()=>desenhadas.forEach(([j,x,y,r])=>GRADE.add(T_PROJ,j,x,y,r)));}

// Camada Canvas do mapa: o L.Canvas do Leaflet cuida do tamanho, da posição e da escala durante a animação de zoom;
// aqui só se troca o desenho (nenhuma camada vetorial usa este renderer).
let Tela=null;
function classeTela(){return Tela||(Tela=L.Canvas.extend({
 _draw(){if(!this._map)return;const t0=performance.now();this._ctx.save();pintarMapa(this._ctx,this._bounds);this._ctx.restore();this.ms=performance.now()-t0},
 repintar(){if(this._map&&this._ctx)this._redraw()}}))}

function htmlProcesso(k){
 const r=D.processos.rows[k],e=r[PC.empresa],gr=D.dims.fase[r[PC.fase]].grupo,mi=D.dims.min[r[PC.mineral]];
 return `<b>${escape(r[PC.processo])}</b> · <span style="color:${COR[gr]||COR.outro}">●</span> ${escape(D.dims.fase[r[PC.fase]].nome)}`
  +`<br>${escape(e>=0?porI.get(e).nome:t(e===-2?'ea.pf':'ea.semTitular'))}<small>${escape(mi?mi[0]:'—')} · ${escape(t('ea.tip.centroide'))}</small>`}
function htmlEmpresa(i){
 const e=porI.get(i),l=S.uni.get(i),gi=l?l.gi:faseMaisAvancada(procsPorEmp.get(i)||[]);
 return `<b>${escape(e.nome)}</b><br>${escape(rotuloMetrica(S.f.metrica))}: ${escape(fmtMetrica(l?l.v:0,S.f.metrica))}`
  +(S.puxadores.has(i)?` · <b>${escape(t('ea.puxador'))}</b>`:'')
  +`<small><span style="color:${COR[GRUPOS[gi]]}">●</span> ${escape(t('ea.tip.faseMax',{fase:rotuloGrupo(GRUPOS[gi])}))} · ${escape(t('ea.tip.nProc',{n:num(e.n)}))}</small>`
  +`<small>${escape(munSel()!==null?t('ea.tip.pontoEmpresaMun',{mun:D.dims.mun[munSel()][1]}):t('ea.tip.pontoEmpresa'))}</small>`}
function htmlProjeto(j){
 const p=D.projetos[j],emp=p.e.length?p.e.map(i=>porI.get(i).nome).join(', '):t('ea.semVinculo');
 return `<b>${escape(p.nome)}</b><br><span style="color:${MAT[p.mat][2]}">◆</span> ${escape(p.maturidade||'—')} · ${escape(emp)}`
  +`<small>${escape(p.mineral||'—')}${p.mun?' · '+escape(p.mun):''}</small><small>${escape(p.loc&&p.loc.t==='p'?t('ea.tip.projProc'):t('ea.tip.projMun'))}</small>`}
// O que está sob o pixel: primeiro os símbolos do modo ativo (índice em grade), depois os polígonos (só no modo Processos), de cima
// para baixo. Só a camada do modo responde: Empresas → pontos de empresa; Processos → pontos e polígonos ANM; Projetos → losangos.
// Polígonos sobrepostos voltam todos (quem chama oferece a escolha, sem pegar o primeiro em silêncio).
const TIPO_DO_MODO={empresas:T_EMP,processos:T_PROC,projetos:T_PROJ};
function acertar(lp){
 const m=S.mapa,z=m.getZoom(),tp=TIPO_DO_MODO[S.modo],hs=GRADE.perto(lp.x,lp.y,Math.max(7,raioPonto(z)*HIER_RAIO.lavra_autorizada+3)).filter(h=>h.t===tp);
 if(hs.length){const ids=hs.map(h=>h.id);
  if(tp===T_PROC)return {tipo:'ponto',ks:ids.map(j=>MP.k[j])};
  if(tp===T_EMP)return {tipo:'empresa',is:ids};
  return {tipo:'projeto',ps:ids}}
 if(S.modo!=='processos')return null;
 const o=m.getPixelOrigin(),s=Math.pow(2,z),X=(lp.x+o.x)/s,Y=(lp.y+o.y)/s,ps=S.poliDesenhados||[],ks=[];
 for(let i=ps.length-1;i>=0;i--){const p=PROJ.get(ps[i]);if(p&&dentroPoligono(p,X,Y)&&!ks.includes(ps[i]))ks.push(ps[i])}
 return ks.length?{tipo:'poligono',ks}:null}
// Município (índice em dims.mun) sob o pixel, pelos limites oficiais (anéis completos, multipartes e buracos); null fora de Goiás.
function munNoPixel(lp){
 if(!S.munProj||!S.munCod)return null;const m=S.mapa,o=m.getPixelOrigin(),s=Math.pow(2,m.getZoom()),X=(lp.x+o.x)/s,Y=(lp.y+o.y)/s;
 for(let i=0;i<S.munProj.length;i++)if(dentroPoligono(S.munProj[i],X,Y))return kDoIbge(S.munCod[i]);
 return null}
// O fundo livre do mapa é alvo de município desde a primeira visita (marcadores do modo ativo têm prioridade). Em Camadas, uma opção
// avançada suspende isso; suspensa, o fundo volta ao comportamento antigo (clique no vazio desmarca).
const alvoMunicipio=()=>!el('ea-sel-mun')||el('ea-sel-mun').checked;
function esconderHover(){
 if(!S.mapa)return;if(S.tip&&S.mapa.hasLayer(S.tip))S.tip.close();if(S.anel&&S.mapa.hasLayer(S.anel))S.anel.remove();S.mapa.getContainer().style.cursor=''}
function sondar(){
 S.rafMov=0;const ev=S.ultimoMov,m=S.mapa;if(!ev||!m)return;
 if(m.dragging.moving()||m._animatingZoom){esconderHover();return}
 const cp=m.mouseEventToContainerPoint(ev),lp=m.containerPointToLayerPoint(cp),h=acertar(lp);
 if(!h){
  // fundo: com a ferramenta de município (ou um município escolhido), o município sob o cursor é o alvo — o atual não é
  const k=alvoMunicipio()?munNoPixel(lp):null;
  if(k===null){esconderHover();return}
  if(S.anel&&m.hasLayer(S.anel))S.anel.remove();m.getContainer().style.cursor='pointer';
  if(!S.tip)S.tip=L.tooltip({direction:'top',className:'ea-tip',opacity:1});
  S.tip.options.offset=[0,-10];S.tip.setLatLng(m.containerPointToLatLng(cp)).setContent(`<b>${escape(nomeMunUf(k))}</b><small>${escape(k===munSel()?t('ea.tip.munTirar'):munSel()!==null?t('ea.tip.munTrocar'):t('ea.tip.munSel'))}</small>`);
  if(!m.hasLayer(S.tip))S.tip.addTo(m);else S.tip.update();return}
 m.getContainer().style.cursor='pointer';
 const R=D.processos.rows,z=m.getZoom();let ll=m.containerPointToLatLng(cp),dy=-8,w=0,html='',n=1;
 if(h.tipo==='ponto'||h.tipo==='poligono'){const k=h.ks[0];html=htmlProcesso(k)+(k===S.destaque&&h.ks.length===1?`<small>${escape(t('ea.cliqueDesmarca'))}</small>`:'');n=h.ks.length;
  if(h.tipo==='ponto'){ll=L.latLng(R[k][PC.lat],R[k][PC.lon]);w=Math.round((R[k][PC.empresa]===S.sel?raioSel(z):estiloFase(MP.g[MP.j[k]],z).r)*2+8)}}
 else if(h.tipo==='empresa'){const i=h.is[0],e=porI.get(i),l=S.uni.get(i);html=htmlEmpresa(i)+(i===S.sel?`<small>${escape(t('ea.cliqueDesmarca'))}</small>`:'');n=h.is.length;
  const q=posEmpresa(i);ll=q?llDe(q):L.latLng(R[e.pt][PC.lat],R[e.pt][PC.lon]);w=Math.round(raioEmpresa(l?l.v:0,S.vmax,z)*2+8)}
 else{const p=D.projetos[h.ps[0]],q=MPJ.pos.get(p.j);html=htmlProjeto(p.j);n=h.ps.length;
  ll=L.CRS.EPSG3857.pointToLatLng(L.point(MPJ.x[q],MPJ.y[q]),0);w=Math.round(raioProjeto(z,p.mat)*2+8)}
 if(w){dy=-w/2;
  if(!S.anel)S.anel=L.marker(ll,{interactive:false,keyboard:false,icon:L.divIcon({className:'ea-anel',html:'<i></i>',iconSize:[w,w]})});
  S.anel.setLatLng(ll);if(S.anel._eaW!==w){S.anel.setIcon(L.divIcon({className:'ea-anel',html:'<i></i>',iconSize:[w,w]}));S.anel._eaW=w}
  if(!m.hasLayer(S.anel))S.anel.addTo(m)}
 else if(S.anel&&m.hasLayer(S.anel))S.anel.remove();
 const mais=n>1?`<small>${escape(t(h.tipo==='ponto'||h.tipo==='poligono'?'ea.maisAqui':'ea.maisAquiItens',{n:num(n-1)}))}</small>`:'';
 if(!S.tip)S.tip=L.tooltip({direction:'top',className:'ea-tip',opacity:1});
 S.tip.options.offset=[0,dy];S.tip.setLatLng(ll).setContent(html+mais);if(!m.hasLayer(S.tip))S.tip.addTo(m);else S.tip.update()}

const ICONE={go:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>',
 emp:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>',
 cheia:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>'};
function botoesMapa(){
 const Ctl=L.Control.extend({options:{position:'bottomright'},onAdd(){
  const d=L.DomUtil.create('div','leaflet-bar ea-ctl');
  const b=(a,ic,txt)=>`<a href="#" role="button" data-a="${a}" title="${escape(txt)}" aria-label="${escape(txt)}">${ic}</a>`;
  d.innerHTML=b('go',ICONE.go,t('ea.voltarGo'))+b('emp',ICONE.emp,t('ea.enquadrarEmp'))+b('cheia',ICONE.cheia,t('ea.telaCheia'));
  L.DomEvent.disableClickPropagation(d);L.DomEvent.disableScrollPropagation(d);
  d.addEventListener('click',ev=>{const a=ev.target.closest('a');if(!a)return;L.DomEvent.stop(ev);
   if(a.dataset.a==='go')S.mapa.fitBounds(goBounds(),{padding:[10,10]});
   else if(a.dataset.a==='emp'){if(S.sel!==null){S.destaque=null;S.foco='empresa';desenharSelecao(true);estadoBotoesMapa()}}
   else telaCheia()});
  return d}});
 S.botoes=new Ctl().addTo(S.mapa);estadoBotoesMapa()}
// Botões do mapa e o cartão da seleção (que também mostra um processo destacado sem empresa: pessoa física ou sem titular).
function estadoBotoesMapa(){
 resumoSel();
 if(!S.botoes)return;const c=S.botoes.getContainer(),a=c.querySelector('[data-a="emp"]');
 a.classList.toggle('ea-desligado',S.sel===null);a.setAttribute('aria-disabled',String(S.sel===null));
 const cheia=c.querySelector('[data-a="cheia"]'),on=emTelaCheia(),txt=t(on?'ea.sairTelaCheia':'ea.telaCheia');cheia.title=txt;cheia.setAttribute('aria-label',txt)}
const painelMapa=()=>document.querySelector('#empresas-view .ea-map-panel');
const emTelaCheia=()=>{const p=painelMapa();return !!p&&(document.fullscreenElement===p||p.classList.contains('ea-cheia'))};
function telaCheia(){
 const p=painelMapa();if(!p)return;
 if(emTelaCheia()){p.classList.remove('ea-cheia');if(document.fullscreenElement)document.exitFullscreen().catch(()=>null)}
 else if(p.requestFullscreen&&document.fullscreenEnabled)p.requestFullscreen().catch(()=>p.classList.add('ea-cheia'));
 else p.classList.add('ea-cheia');   // sem a API (Safari do iPhone): uma camada fixa sobre a página faz o mesmo
 setTimeout(()=>{estadoBotoesMapa();S.mapa.invalidateSize()},120)}

// Desfaz o foco, um passo por vez: o processo em foco; depois a empresa (todas as áreas, a URL e as análises acompanham).
// O município é recorte: sai pelo × da etiqueta, pelo filtro, por Esc sem outro foco ou por um clique fora dos municípios.
function desmarcar(){
 if(S.destaque!==null&&(focoAtual()==='processo'||S.sel===null)){limparProcesso();return}
 if(S.sel!==null){limparSelecao();return}}
function limparProcesso(){
 S.destaque=null;if(S.foco==='processo')S.foco=null;anotarHistorico({proc:null});avisoMapa('');estadoBotoesMapa();if(S.tela)S.tela.repintar()}
// Foco do cartão: o pedido (S.foco) quando ainda vale; senão processo > empresa > município. 'fechado' = cartão do município fechado
// pelo × (o recorte continua, com a etiqueta no mapa).
function focoAtual(){
 const f=S.foco;
 if(f==='processo'&&S.destaque!==null)return 'processo';
 if(f==='municipio'&&munSel()!==null)return 'municipio';
 if(f==='empresa'&&S.sel!==null)return 'empresa';
 if(f==='fechado')return null;
 return S.destaque!==null?'processo':S.sel!==null?'empresa':munSel()!==null?'municipio':null}
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
 const m=L.map('ea-map',{preferCanvas:true,zoomControl:false,minZoom:6,maxZoom:16,zoomSnap:.5,zoomDelta:1,wheelPxPerZoomLevel:36/(window.devicePixelRatio||1),wheelDebounceTime:30,
  maxBounds:L.latLngBounds(BOUNDS).pad(.4)}).fitBounds(BOUNDS);
 S.mapa=m;
 // zoom e enquadramentos no canto inferior direito; modos (alto, à esquerda), cartão da seleção (alto, à direita) e legenda
 // (baixo, à esquerda) ficam fora do elemento do mapa, em HTML por cima dele
 L.control.scale({imperial:false,position:'bottomright'}).addTo(m);
 L.control.zoom({position:'bottomright',zoomInTitle:t('ea.aproximar'),zoomOutTitle:t('ea.afastar')}).addTo(m);
 botoesMapa();
 // OpenStreetMap em cinza claro (filtro CSS), para o fundo não competir com as cores
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,className:'ea-osm-suave',opacity:.62,
  attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(m);
 m.createPane('ea-mascara').style.zIndex=350;m.getPane('ea-mascara').style.pointerEvents='none';
 m.createPane('ea-pontos').style.zIndex=450;m.getPane('ea-pontos').style.pointerEvents='none';
 S.camadas.operacao=L.layerGroup().addTo(m);
 S.tela=new (classeTela())({pane:'ea-pontos',padding:.3}).addTo(m);
 focoGoias(L.canvas({pane:'ea-mascara',padding:.4}));
 m.on('moveend',poligonosVisiveis);
 m.on('movestart zoomstart',esconderHover);
 // clique: símbolo do modo ativo (ou polígono, em Processos) seleciona; de novo no mesmo desmarca; área vazia desmarca (se havia lista
 // aberta, só a fecha). Com a ferramenta de município (ou um município escolhido), o fundo escolhe ou troca o município; fora dos
 // municípios, tira o recorte. Dentro do município já escolhido, o vazio desfaz o foco como sempre e o cartão volta ao território.
 m.on('preclick',()=>{S.popupNoClique=temPopup()});
 m.on('click',ev=>{
  const h=acertar(ev.layerPoint);
  if(h){const mesmo=(h.tipo==='empresa'&&h.is.length===1&&h.is[0]===S.sel)||((h.tipo==='ponto'||h.tipo==='poligono')&&h.ks.length===1&&h.ks[0]===S.destaque);
   if(!S.popupNoClique&&mesmo){if(h.tipo==='empresa')limparSelecao();else limparProcesso();return}
   clicarMapa(h,ev.latlng);return}
  if(S.popupNoClique)return;
  if(alvoMunicipio()){const k=munNoPixel(ev.layerPoint);
   if(k===null){if(munSel()!==null)limparMunicipio();else desmarcar();return}
   // outro município: troca; o mesmo de novo: tira do recorte (a dica sob o cursor avisa antes)
   if(k!==munSel()){selecionarMunicipio(k,{origem:'mapa',enquadrar:false});return}
   limparMunicipio();return}
  desmarcar()});
 const c=m.getContainer();
 c.addEventListener('mousemove',ev=>{S.ultimoMov=ev;if(!S.rafMov)S.rafMov=requestAnimationFrame(sondar)});
 c.addEventListener('mouseleave',()=>{S.ultimoMov=null;esconderHover()});
 document.addEventListener('fullscreenchange',()=>setTimeout(()=>{estadoBotoesMapa();m.invalidateSize()},60));
 setTimeout(()=>{m.invalidateSize();m.fitBounds(goBounds(),{padding:[10,10]})},80);
 // Mapa escondido (outra área aberta) tem tamanho 0: esse tamanho não entra no Leaflet. Antes entrava, e a volta ao Explorar dependia
 // de quem rodava primeiro (este observador ou o invalidateSize de mostrarArea): às vezes o centro voltava deslocado em meio mapa.
 new ResizeObserver(()=>{const c=el('ea-map');if(!c.offsetWidth||!c.offsetHeight)return;m.invalidateSize({pan:false})}).observe(el('ea-map'));
 // municípios (referência) vêm do pacote do Atlas, compartilhado com as outras abas
 (window.loadAtlas?window.loadAtlas():api('/atlas')).then(a=>{
  S.munCentro=new Map();S.munProj=[];S.munBounds=new Map();
  S.munCod=[];S.munIdx=new Map();   // código IBGE de cada contorno e a posição dele (para o destaque e o clique no município)
  for(const mu of a.municipalities){
   const rings=mu.rings||[],p=projetarAneis(rings);if(p){S.munIdx.set(String(mu.code),S.munProj.length);S.munCod.push(String(mu.code));S.munProj.push(p)}
   // centro aproximado do município: média dos vértices do maior anel
   const r=rings.reduce((a,b)=>b.length>a.length?b:a,[]);
   if(r.length){S.munCentro.set(mu.code,[r.reduce((s,p)=>s+p[0],0)/r.length,r.reduce((s,p)=>s+p[1],0)/r.length]);S.munBounds.set(mu.code,L.latLngBounds(rings.flat()))}}
  S.atlasMun=a;prepararProjetos();desenharPontos();if(S.sel!==null)desenharOperacao();if(S.modo==='projetos')lista();
  if(S.enqMun!=null){const k=S.enqMun;S.enqMun=null;enquadrarMunicipio(k)}
 }).catch(()=>{S.atlasMun=false});}

// Enquadra o município inteiro (todas as partes), sem zoom excessivo, desviando do cartão (alto à direita na mesa, base no celular).
function enquadrarMunicipio(k){
 if(!S.mapa)return;if(!S.munBounds){S.enqMun=k;return}
 const b=S.munBounds.get(ibgeDe(k));if(!b)return;
 S.mapa.fitBounds(b,{maxZoom:11,paddingTopLeft:[24,56],paddingBottomRight:largo.matches?[350,24]:[24,150]})}

// Recalcula o que aparece (recorte, empresa selecionada, projetos) e pede um desenho novo da camada.
function desenharPontos(){
 if(!S.mapa||!MP.n)return;
 const so=S.sel!==null&&el('ea-so-sel').checked,R=D.processos.rows;
 S.vis.fill(0);for(const l of S.universo)for(const k of l.ps)S.vis[k]=1;
 S.soSel=so;S.selMarca.fill(0);S.selJ=[];
 if(S.sel!==null){
  // com município no recorte, o realce da empresa são os direitos dela ligados ao município; a atuação estadual só por pedido explícito
  const local=munSel()!==null&&!S.verEstadual;
  const ks=so?procsFiltrados(S.sel,S.f):procsFiltrados(S.sel,{mun:local?S.f.mun:'',min:'',grupo:''});
  for(const k of ks)if(MP.j[k]>=0){S.selMarca[k]=1;S.selJ.push(MP.j[k])}
  S.selJ.sort((a,b)=>a-b)}
 // empresas do recorte, do maior ponto para o menor
 S.vmax=Math.max(0,...S.universo.map(l=>l.v));
 pontosDasEmpresas();
 S.projVis=new Uint8Array(D.projetos.length);for(const p of S.projetos||[])S.projVis[p.j]=1;
 esconderHover();estadoBotoesMapa();S.tela.repintar();notaMapa();}

// Ponto de cada empresa no mapa. Sem município no recorte: o direito de referência estadual (empresas[].pt). Com município: um direito da
// empresa LIGADO ao município e com o centroide DENTRO do contorno (o que mais recolheu CFEM; depois lavra; depois o maior) — o ponto
// estadual não finge ser local. Empresa do recorte sem direito com centroide dentro (ou só com CFEM) fica sem ponto: só na lista, dito ali.
function pontosDasEmpresas(){
 const R=D.processos.rows,k=munSel(),idx=k!==null&&S.munIdx?S.munIdx.get(ibgeDe(k)):undefined,geo=idx!==undefined?S.munProj[idx]:null;
 S.ptsEmp=[];S.locE=null;
 if(k!==null&&geo){S.locE=new Map();
  for(const l of S.universo){let best=-1,bs=null;
   for(const p of l.ps){const j=MP.j[p];if(j<0||!dentroPoligono(geo,MP.x[j],MP.y[j]))continue;
    const r=R[p],sc=[r[PC.cfem_2022_2026]||0,D.dims.fase[r[PC.fase]].grupo==='lavra_autorizada'?1:0,r[PC.area_ha]||0];
    if(!bs||sc[0]>bs[0]||(sc[0]===bs[0]&&(sc[1]>bs[1]||(sc[1]===bs[1]&&sc[2]>bs[2])))){bs=sc;best=p}}
   if(best>=0){const j=MP.j[best];S.locE.set(l.e.i,{x:MP.x[j],y:MP.y[j],k:best})}}
  for(const l of S.universo){const q=S.locE.get(l.e.i);if(q)S.ptsEmp.push({i:l.e.i,x:q.x,y:q.y})}}
 else if(k===null)for(let q=0;q<MPE.n;q++){const i=MPE.i[q];if(S.uni.has(i))S.ptsEmp.push({i,x:MPE.x[q],y:MPE.y[q]})}
 S.ptsEmp.sort((a,b)=>S.uni.get(b.i).v-S.uni.get(a.i).v);
 S.posEmp=new Map(S.ptsEmp.map(q=>[q.i,q]))}
// Posição (zoom 0) do ponto de uma empresa agora: o local no recorte municipal; sem município, o estadual (também fora do recorte de filtros).
function posEmpresa(i){
 if(S.posEmp&&S.posEmp.has(i))return S.posEmp.get(i);
 if(S.locE)return null;const q=MPE.pos.get(i);return q===undefined?null:{x:MPE.x[q],y:MPE.y[q]}}
const llDe=q=>L.CRS.EPSG3857.pointToLatLng(L.point(q.x,q.y),0);

// Nota sob o mapa: o que o modo desenha e o que fica de fora (empresas sem processo georreferenciado, projetos sem localização).
function notaMapa(){
 const semPonto=S.universo.filter(l=>l.e.pt<0).length,semLocal=(S.projetos||[]).filter(p=>!p.loc).length;
 const txt={empresas:t('ea.nota.empresas',{n:num(semPonto)}),processos:t('ea.nota.processos'),projetos:t('ea.nota.projetos',{n:num(semLocal)})}[S.modo];
 // o que é clicável em cada modo, e a ferramenta de município
 // com município no recorte (modo Empresas), o ponto de cada empresa é um direito dela dentro do município; quem não tem fica só na lista
 const km=munSel(),loc=km!==null&&S.modo==='empresas'&&S.locE?' '+t('ea.nota.pontoLocal',{mun:D.dims.mun[km][1],n:num(S.universo.filter(l=>!S.locE.has(l.e.i)).length)}):'';
 el('ea-mapa-nota').textContent=txt+loc+' '+t(S.modo==='empresas'?'ea.nota.realce':'ea.nota.soModo')+' '+t('ea.nota.municipio');}

// Clique no mapa: um símbolo só → seleciona (empresa, o processo exato ou o projeto); vários sobrepostos → lista inteira para escolher,
// sem escolha silenciosa do primeiro nem corte da lista.
function clicarMapa(h,ll){
 if(h.tipo==='empresa'){if(h.is.length===1){selecionar(h.is[0],{origem:'mapa'});return}
  popupLista(ll,t('ea.sobrepostosEmp',{n:String(h.is.length)}),h.is.map(i=>`<li data-busca="${escape(norm(porI.get(i).nome))}"><button type="button" class="link-button" data-i="${i}">${escape(porI.get(i).nome)}</button>`
   +`<small>${escape(fmtMetrica(S.uni.get(i)?S.uni.get(i).v:0,S.f.metrica))}</small></li>`),h.is.length);return}
 if(h.tipo==='projeto'){if(h.ps.length===1){abrirProjeto(D.projetos[h.ps[0]],{origem:'mapa',ll});return}
  popupLista(ll,t('ea.sobrepostosProj',{n:String(h.ps.length)}),h.ps.map(j=>{const p=D.projetos[j];
   return `<li data-busca="${escape(norm(p.nome))}"><button type="button" class="link-button" data-j="${j}">${escape(p.nome)}</button><small>${escape(p.maturidade||'—')} · ${escape(p.e.length?porI.get(p.e[0]).nome:t('ea.semVinculo'))}</small></li>`}),h.ps.length);return}
 if(h.ks.length===1){selecionarProcesso(h.ks[0]);return}
 // processos sobrepostos (mesmo titular ou não): número ANM + mineral + fase, e o titular; fase mais avançada primeiro
 const R=D.processos.rows,gr=k=>GRUPOS.indexOf(D.dims.fase[R[k][PC.fase]].grupo);
 const ks=[...h.ks].sort((a,b)=>gr(a)-gr(b)||String(R[a][PC.processo]).localeCompare(String(R[b][PC.processo])));
 popupLista(ll,t('ea.sobrepostosProc',{n:String(ks.length)}),ks.map(k=>{const r=R[k],e=r[PC.empresa],mi=D.dims.min[r[PC.mineral]],g=D.dims.fase[r[PC.fase]].grupo;
  const tit=e>=0?porI.get(e).nome:t(e===-2?'ea.pf':'ea.semTitular');
  return `<li data-busca="${escape(norm([r[PC.processo],soDigitos(r[PC.processo]),mi?mi[0]:'',D.dims.fase[r[PC.fase]].nome,tit].join(' ')))}">`
   +`<button type="button" class="link-button" data-k="${k}"><span class="ea-pop-dot" style="background:${COR[g]||COR.outro}" aria-hidden="true"></span>${escape(r[PC.processo])}</button>`
   +`<small>${escape(mi?mi[0]:'—')} · ${escape(D.dims.fase[r[PC.fase]].nome)}</small><small class="ea-pop-tit">${escape(tit)}</small></li>`}),ks.length);}
// Lista de escolha num balão: inteira, com rolagem; com mais de 8 itens, um campo filtra. Setas ↑/↓ andam entre as opções, Esc fecha;
// o foco entra na lista (teclado) e o toque funciona como clique.
function popupLista(ll,titulo,itens,n){
 const filtro=n>8?`<input type="search" class="ea-pop-filtro" placeholder="${escape(t('ea.filtrarLista'))}" aria-label="${escape(t('ea.filtrarLista'))}">`:'';
 const pop=L.popup({maxWidth:330,autoPanPaddingTopLeft:[20,60],autoPanPaddingBottomRight:[20,20]}).setLatLng(ll)
  .setContent(`<div class="ea-pop" role="group" aria-label="${escape(titulo)}"><b>${escape(titulo)}</b>${filtro}<ul>${itens.join('')}</ul></div>`).openOn(S.mapa);
 const box=pop.getElement();
 box.querySelectorAll('[data-i]').forEach(b=>b.onclick=()=>{S.mapa.closePopup();selecionar(+b.dataset.i,{origem:'mapa'})});
 box.querySelectorAll('[data-j]').forEach(b=>b.onclick=()=>{S.mapa.closePopup();abrirProjeto(D.projetos[+b.dataset.j],{origem:'mapa',ll})});
 box.querySelectorAll('[data-k]').forEach(b=>b.onclick=()=>{S.mapa.closePopup();selecionarProcesso(+b.dataset.k)});
 L.DomEvent.disableScrollPropagation(box);
 box.addEventListener('keydown',ev=>{if(ev.key!=='ArrowDown'&&ev.key!=='ArrowUp')return;
  const bs=[...box.querySelectorAll('li:not([hidden]) button')],i=bs.indexOf(document.activeElement);ev.preventDefault();
  const x=bs[i<0?0:Math.max(0,Math.min(bs.length-1,i+(ev.key==='ArrowDown'?1:-1)))];if(x)x.focus()});
 const f=box.querySelector('.ea-pop-filtro');
 if(f)f.addEventListener('input',()=>{const q=norm(f.value.trim());box.querySelectorAll('li[data-busca]').forEach(li=>{li.hidden=!!q&&!li.dataset.busca.includes(q)})});
 setTimeout(()=>{const a=f||box.querySelector('li button');if(a)a.focus({preventScroll:true})},0);}
// Projeto: seleciona a empresa vinculada (se uma só) e mostra o projeto num balão, com a precisão da localização.
function abrirProjeto(p,{origem,ll}={}){
 if(p.e.length===1&&S.sel!==p.e[0])selecionar(p.e[0],{origem:'mapa'});
 const q=MPJ.pos.get(p.j);
 if(!S.mapa)return;
 if(!ll&&q!==undefined){const z=Math.max(S.mapa.getZoom(),p.loc.t==='p'?10:9),pt=L.CRS.EPSG3857.pointToLatLng(L.point(MPJ.x[q],MPJ.y[q]),0);
  S.mapa.setView(pt,z);ll=pt}
 if(!ll){avisoMapa(t('ea.projSemLocal',{nome:p.nome}));return}
 const fonte=p.link?`<a href="${escape(urlSegura(p.link))}" target="_blank" rel="noopener noreferrer">${escape(p.fonte_nome||t('ea.verFonte'))} ↗</a>`:escape(p.fonte_nome||'');
 const pop=L.popup({maxWidth:340}).setLatLng(ll).setContent(`<div class="ea-pop"><b>${escape(p.nome)}</b>`
  +`<small><span style="color:${MAT[p.mat][2]}">◆</span> ${escape(p.maturidade||'—')} · ${escape(p.fase||'')}</small>`
  +`<small>${escape(p.e.length?p.e.map(i=>porI.get(i).nome).join(', '):t('ea.semVinculo'))} · ${escape(rotuloMetodo(p.metodo))} · ${escape(t('ea.conf'))}: ${escape(rotuloConf(p.conf))}</small>`
  +`<small>${escape(p.mineral||'—')}${p.mun?' · '+escape(p.mun):''} · ${escape(p.loc&&p.loc.t==='p'?t('ea.tip.projProc'):t('ea.tip.projMun'))}</small>`
  +`<small>${fonte}</small>`+(p.e.length===1?`<button type="button" class="link-button" data-dossie="${p.e[0]}">${escape(t('ea.abrirDossieProj'))}</button>`:'')+`</div>`).openOn(S.mapa);
 const b=pop.getElement().querySelector('[data-dossie]');if(b)b.onclick=()=>{S.mapa.closePopup();S.aba='projetos';mostrarArea('dossie')};}

function avisoMapa(txt){el('ea-map-aviso').textContent=txt;el('ea-map-aviso').hidden=!txt}

// ------------------------------------------------------------------ processo e município em foco
// Processo exato (número ANM): vira o foco do cartão, sem trocar a empresa selecionada (que segue como empresa de interesse) nem o
// zoom — a não ser que se peça para ir até ele (busca, dossiê).
function selecionarProcesso(k,{ir=false}={}){
 if(k==null||!D.processos.rows[k])return;
 S.destaque=k;S.foco='processo';avisoMapa('');
 anotarHistorico({proc:D.processos.rows[k][PC.processo]});
 estadoBotoesMapa();if(S.tela)S.tela.repintar();
 // ir até ele depois que o mapa (talvez recém-mostrado) tiver tamanho
 geometria().catch(()=>null).then(()=>{if(S.destaque!==k)return;S.tela.repintar();if(ir)setTimeout(()=>{if(S.destaque!==k)return;S.mapa.invalidateSize();irParaProcesso(k)},30)});}

// Município pelo código IBGE: as três portas (ferramenta do mapa, busca, dossiê) chegam aqui. Vira recorte do Explorar (o mesmo filtro
// de município da lista: vínculo processo–município do cadastro ANM, nunca a posição do centroide), foco do cartão, contorno
// destacado e etiqueta removível no mapa. A empresa de interesse, os outros filtros e o período não mudam.
function selecionarMunicipio(k,{origem='',enquadrar=true}={}){
 if(k==null||!D.dims.mun[k]||!el('ea-mun').querySelector(`option[value="${k}"]`))return;
 if(origem!=='dossie')S.munOrigem=null;
 // o foco passa ao território; a empresa de interesse fica. (O município é filtro, como os outros: não entra no histórico.)
 if(S.destaque!==null&&focoAtual()==='processo'){S.destaque=null;anotarHistorico({proc:null})}
 S.foco='municipio';S.verEstadual=false;el('ea-mun').value=String(k);
 if(S.mapa&&temPopup())S.mapa.closePopup();
 redesenhar();etiquetaMunicipio();gravarHash(true);
 if(enquadrar)enquadrarMunicipio(k);}
function limparMunicipio(){
 if(munSel()===null)return;
 el('ea-mun').value='';S.munOrigem=null;S.verEstadual=false;if(S.foco==='municipio'||S.foco==='fechado')S.foco=null;
 redesenhar();etiquetaMunicipio();gravarHash(true);}
// Etiqueta do município no alto do mapa: "Catalão · GO ×". O nome reabre o cartão do território; o × tira só o município.
function etiquetaMunicipio(){
 const tools=document.querySelector('#empresas-view .ea-map-tools');if(!tools)return;
 let b=el('ea-mun-etq');
 if(!b){b=document.createElement('span');b.id='ea-mun-etq';b.className='ea-mun-etq';tools.appendChild(b)}
 const k=munSel();b.hidden=k===null;if(k===null){b.innerHTML='';return}
 const nome=nomeMunUf(k);
 b.innerHTML=`<button type="button" class="ea-mun-etq-nome" title="${escape(t('ea.munCartao',{mun:nome}))}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h9l5 6-4 10H6l-2-8z"/></svg>${escape(nome)}</button>`
  +`<button type="button" class="ea-x ea-mun-etq-x" aria-label="${escape(t('ea.munLimpar',{mun:nome}))}" title="${escape(t('ea.munLimpar',{mun:nome}))}">×</button>`;
 b.querySelector('.ea-mun-etq-nome').onclick=()=>{S.foco='municipio';estadoBotoesMapa()};
 b.querySelector('.ea-mun-etq-x').onclick=()=>{limparMunicipio();const a=el('ea-camadas');if(a)a.querySelector('summary').focus()};}

async function geometria(){
 if(S.geo)return S.geo;
 avisoMapa(t('ea.carregandoPoligonos'));
 try{const g=await window.loadProcesses();S.geo=new Map(g.records.map(r=>[r.id,r]));avisoMapa('');return S.geo}
 catch(e){avisoMapa(t('ea.falhaPoligonos'));throw e}}

// Zoom alto (modo Processos): os polígonos da área são desenhados pela camada; aqui só se garante que a geometria (2,6 MB) chegou.
function poligonosVisiveis(){
 if(!S.mapa||S.geo||S.modo!=='processos'||S.mapa.getZoom()<ZOOM_POLIGONOS||!el('ea-poligonos').checked)return;
 geometria().then(()=>S.tela.repintar()).catch(()=>{});}

// Empresa escolhida: enquadra (se pedido), carrega a geometria e repinta; irPara leva até o processo destacado.
async function desenharSelecao(enquadrar,irPara){
 S.camadas.operacao.clearLayers();
 if(!S.mapa)return;
 if(S.sel===null){S.tela.repintar();return}
 // com município no recorte, o recorte é o enquadramento: o município inteiro mais os direitos da empresa ligados a ele (inclusive os de
 // centroide fora do contorno); a atuação estadual inteira só com "Ver atuação em todo o estado"
 const km=munSel(),local=km!==null&&!S.verEstadual,R=D.processos.rows;
 const ks=procsFiltrados(S.sel,{mun:local?String(km):'',min:'',grupo:''});
 const pts=ks.filter(k=>R[k][PC.lat]!=null).map(k=>[R[k][PC.lat],R[k][PC.lon]]);
 // o cartão da seleção fica no alto, à direita (mesa), ou na base do mapa (celular): o enquadramento desvia dele
 const desvio={paddingTopLeft:[16,56],paddingBottomRight:largo.matches?[350,16]:[60,200]};
 if(enquadrar&&S.destaque===null){
  const bm=local&&S.munBounds?S.munBounds.get(ibgeDe(km)):null;
  if(bm){const b=L.latLngBounds(bm.getSouthWest(),bm.getNorthEast());pts.forEach(q=>b.extend(q));S.mapa.fitBounds(b,{maxZoom:11,...desvio})}
  else if(pts.length)S.mapa.fitBounds(L.latLngBounds(pts).pad(.2),{maxZoom:12,...desvio})}
 desenharOperacao();
 if(S.modo==='projetos')return;
 try{await geometria()}catch{return}
 if(S.sel===null)return;S.tela.repintar();
 if(irPara&&S.destaque!==null)irParaProcesso(S.destaque);}

// Município da operação declarada (só nas empresas com produção declarada): referência aproximada, quadrado vazado. É desenho de
// contexto (a legenda explica): não recebe clique, dica nem foco, para não roubar o clique do ponto da empresa embaixo dele.
function desenharOperacao(){
 const g=S.camadas.operacao;g.clearLayers();
 const det=S.sel!==null&&D.detalhes[String(S.sel)];if(!det||!S.munCentro)return;
 for(const nome of det.municipios_operacao){
  const k=D.dims.mun.findIndex(m=>norm(m[1])===norm(nome));if(k<0)continue;
  const c=S.munCentro.get(D.dims.mun[k][0]);if(!c)continue;
  L.marker(c,{icon:L.divIcon({className:'ea-op-icone',html:'<i></i>',iconSize:[18,18]}),keyboard:false,interactive:false}).addTo(g)}}

function irParaProcesso(k){
 const r=D.processos.rows[k];if(r[PC.lat]==null||!S.mapa)return;
 const geo=S.geo&&S.geo.get(r[PC.processo]);
 if(geo&&geo.rings.length)S.mapa.fitBounds(L.latLngBounds(geo.rings.flat()).pad(.6),{maxZoom:14});else S.mapa.setView([r[PC.lat],r[PC.lon]],12);
 el('ea-map').scrollIntoView({block:'nearest',behavior:'smooth'});}

// Legenda do modo, compacta e recolhível. Em Empresas e Processos as fases ligam e desligam; em Projetos, as maturidades.
// O que cada símbolo é (e o que não é: posição de mina) fica em "Como ler o mapa".
function legenda(){
 const box=el('ea-legenda'),mais=el('ea-legenda-mais'),emp=S.modo==='empresas';
 const fases=GRUPOS.slice(0,4).map((g,gi)=>{const d=emp?10:Math.round(9*HIER_RAIO[g]);
  return `<button type="button" class="ea-fase" data-g="${gi}" aria-pressed="${!S.off.has(gi)}" title="${escape(t('ea.leg.alternar',{fase:rotuloGrupo(g)}))}">`
   +`<i style="background:${COR[g]};width:${d}px;height:${d}px;opacity:${emp?.85:HIER_ALFA[g]}"></i>${escape(rotuloGrupo(g))}</button>`}).join('');
 // linha de cima: o que a cor quer dizer e as chaves que ligam e desligam; o resto dos símbolos fica em "Símbolos e como ler"
 const tit=x=>`<span class="ea-leg-t">${escape(x)} <span class="ea-leg-dica">· ${escape(t('ea.leg.dica'))}</span></span>`;
 if(emp){box.innerHTML=tit(t('ea.leg.corEmpresa'))+`<div class="ea-leg-chaves">${fases}</div>`;
  mais.innerHTML=`<span class="ea-leg-tam"><i></i><i></i><i></i>${escape(t('ea.leg.tamEmpresa',{metrica:rotuloMetrica(S.f?S.f.metrica:'cfem')}))}</span>`
   +`<span><i class="ea-leg-pux"></i>${escape(t('ea.leg.puxador'))}</span><span><i class="ea-leg-quad"></i>${escape(t('ea.leg.municipio'))}</span>`}
 else if(S.modo==='processos'){box.innerHTML=tit(t('ea.leg.faseTitulo'))+`<div class="ea-leg-chaves">${fases}</div>`;
  mais.innerHTML=`<span class="ea-leg-tam"><i></i><i></i><i></i>${escape(t('ea.leg.hierarquia'))}</span><span><i class="ea-leg-quad"></i>${escape(t('ea.leg.municipio'))}</span>`}
 else{box.innerHTML=tit(t('ea.leg.maturidadeT'))+`<div class="ea-leg-chaves">`
   +MAT.map(([id,,cor],k)=>`<button type="button" class="ea-fase" data-m="${k}" aria-pressed="${!S.matOff.has(k)}" title="${escape(t('ea.leg.alternar',{fase:rotuloMat(k)}))}"><i class="ea-leg-los" style="background:${cor}"></i>${escape(rotuloMat(k))}</button>`).join('')+`</div>`;
  mais.innerHTML=`<span><i class="ea-leg-los ea-cheio"></i>${escape(t('ea.leg.projProc'))}</span><span><i class="ea-leg-los ea-vazado"></i>${escape(t('ea.leg.projMun'))}</span>`
   +`<span><i class="ea-leg-cont">2</i>${escape(t('ea.leg.projGrupo'))}</span>`}}

// Trocar o modo adapta o foco: o processo em foco só existe no modo Processos (fora dele volta a empresa, ou o município); a empresa
// de interesse e o recorte municipal continuam.
function definirModo(m){
 if(!MODOS.includes(m))return;
 if(m!=='processos'&&S.destaque!==null){S.destaque=null;if(S.foco==='processo')S.foco=null;anotarHistorico({proc:null});avisoMapa('')}
 if(S.mapa&&temPopup())S.mapa.closePopup();
 S.modo=m;S.nLista=LOTE;
 el('ea-modos').querySelectorAll('[data-modo]').forEach(b=>{const on=b.dataset.modo===m;b.setAttribute('aria-checked',String(on));b.tabIndex=on?0:-1;b.classList.toggle('on',on)});
 el('ea-poligonos-box').hidden=m!=='processos';
 legenda();lista();desenharPontos();poligonosVisiveis();if(S.sel!==null)desenharSelecao(false);}

// ------------------------------------------------------------------ áreas, barra de seleção e escopo das análises
function mostrarArea(a,{foco=false,semHistorico=false}={}){
 if(!AREAS.includes(a))return;S.area=a;
 AREAS.forEach(x=>{el('ea-area-'+x).hidden=x!==a;const b=el('ea-nav-'+x),on=x===a;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});
 posicionarBusca();if(a!=='explorar')gaveta(false);
 if(foco)el('ea-nav-'+a).focus();
 if(a==='explorar'&&S.mapa)setTimeout(()=>{S.mapa.invalidateSize();if(S.enqPend&&S.sel!==null){S.enqPend=false;desenharSelecao(true,false)}},0);
 if(a==='dossie')dossie();
 if(a==='analises')mostrarAnalise(S.anal);
 if(a==='comparar')comparar();
 if(a!=='dossie')S.volta=null;   // o "Voltar à análise" só vale no dossiê aberto a partir de uma análise
 // cada área é uma entrada no histórico: do dossiê, Voltar leva de novo ao mapa com a mesma seleção
 if(!semHistorico)gravarHash(false);}
// URL = estado: #empresas[/área][/cnpj raiz]. Com empresa selecionada no Explorar a área vai escrita (#empresas/explorar/cnpj),
// porque o link curto #empresas/cnpj abre o dossiê. Voltar e Avançar leem a URL (não o history.state, que é nulo na entrada inicial).
// No Explorar, o município do recorte vai junto (/mun/<IBGE>): o link copiado abre o mesmo recorte. Trocar o município substitui a entrada
// atual (não cria outra); Voltar e Avançar trazem o município de cada entrada do Explorar.
const HASH=/^#empresas(?:\/(explorar|dossie|analises|comparar))?(?:\/(\d{8}))?(?:\/mun\/(\d{7}))?$/;
function gravarHash(substituir){
 const mun=S.area==='explorar'&&munSel()!==null?'/mun/'+ibgeDe(munSel()):'';
 const area=S.area!=='explorar'?S.area:S.sel!==null||mun?'explorar':null;
 const h='#empresas'+(area?'/'+area:'')+(S.sel!==null?'/'+porI.get(S.sel).cnpj:'')+mun;
 const st={ea:S.sel,area:S.area,escopo:S.escopo};
 try{if(location.hash!==h)history[substituir?'replaceState':'pushState'](substituir?{...(history.state||{}),...st}:st,'',h)}catch{}}
// Junta dados ao estado da entrada atual do histórico (escopo das análises, a análise aberta e a rolagem), sem mudar a URL.
function anotarHistorico(x){try{if(/^#empresas/.test(location.hash))history.replaceState({...(history.state||{}),...x},'',location.href)}catch{}}
// st: o history.state da entrada (pode ser nulo). O escopo gravado volta junto com a empresa: voltar a uma análise de "todas as
// empresas" não a recorta na empresa selecionada, e a análise e a rolagem voltam como estavam.
function aplicarHash(h,st){
 const m=String(h||'').match(HASH);if(!m)return false;
 const e=m[2]?E.find(x=>x.cnpj===m[2]):null,esc=st&&(st.escopo==='todas'||st.escopo==='empresa')?st.escopo:null;
 if(e){if(S.sel!==e.i)selecionar(e.i,{semHistorico:true,escopo:esc});else if(esc&&esc!==S.escopo)definirEscopo(esc)}
 else if(S.sel!==null||S.destaque!==null)limparSelecao(true);
 if(st&&ANALISES.includes(st.anal))S.anal=st.anal;
 const area=m[1]||(e?'dossie':'explorar');
 // município: no Explorar, o do endereço (sem /mun/, nenhum); nas outras áreas o recorte fica como está
 if(area==='explorar'){const km=m[3]?kDoIbge(m[3]):null;
  if(km!==munSel()&&(km===null||el('ea-mun').querySelector(`option[value="${km}"]`))){el('ea-mun').value=km===null?'':String(km);S.verEstadual=false;
   if(km===null&&(S.foco==='municipio'||S.foco==='fechado'))S.foco=null;if(km!==null&&!(st&&st.proc))S.foco='municipio';redesenhar();if(km!==null&&!(st&&st.vista))S.enqMunHash=km}}
 // no mapa, o processo em foco é o gravado na entrada (de volta do dossiê, o mesmo processo; sem registro, nenhum — nada obsoleto)
 if(area==='explorar'){const k=st&&st.proc?procPorId.get(soDigitos(st.proc)):undefined;
  if(k!=null){if(S.modo!=='processos')definirModo('processos');S.destaque=k;S.foco='processo'}
  else if(S.destaque!==null){S.destaque=null;if(S.foco==='processo')S.foco=null}}
 if(area==='dossie'&&e&&st&&st.deAnalise&&st.deAnalise.cnpj===e.cnpj)S.volta={...st.deAnalise};
 if(area==='dossie'&&e&&st&&st.deMapa&&st.deMapa.cnpj===e.cnpj)S.volta={...st.deMapa};
 mostrarArea(area,{semHistorico:true});
 if(area==='explorar'){estadoBotoesMapa();if(S.tela)S.tela.repintar();
  if(S.enqMunHash!=null){const km=S.enqMunHash;S.enqMunHash=null;setTimeout(()=>{if(S.mapa)S.mapa.invalidateSize();enquadrarMunicipio(km)},60)}
  if(st&&st.vista&&S.mapa)setTimeout(()=>{S.mapa.invalidateSize();S.mapa.setView([st.vista.lat,st.vista.lng],st.vista.z,{animate:false})},40)}
 if((area==='analises'||area==='dossie')&&st&&st.rolagem!=null)setTimeout(()=>window.scrollTo(0,st.rolagem),0);
 return true}

// Das análises para o dossiê: o nome de uma empresa identificada pelo CNPJ raiz abre a ficha dela, num clique e numa entrada só do
// histórico. A análise não muda — filtros, aba, escopo (todas/empresa), página da tabela —; o estado dela fica na entrada atual do
// histórico, e Voltar (ou "Voltar à análise", no dossiê) a devolve igual, na mesma rolagem. Sem CNPJ no índice da aba, não há atalho.
const porCnpj=c=>E.find(x=>x.cnpj===c)||null;
function abrirDaAnalise(cnpj){
 const e=porCnpj(cnpj);if(!e)return;
 const de=S.area==='analises'?S.anal:null;
 if(de){S.volta={anal:de,cnpj,rolagem:window.scrollY};anotarHistorico({escopo:S.escopo,anal:de,rolagem:window.scrollY})}
 selecionar(e.i,{origem:'analise',semHistorico:true});
 mostrarArea('dossie');
 if(de)anotarHistorico({deAnalise:{...S.volta}});   // Avançar de volta ao dossiê traz o atalho junto
 const ficha=el('ea-area-dossie');if(ficha)ficha.scrollIntoView({block:'start'});
 const titulo=el('ea-ficha-titulo');if(titulo){titulo.tabIndex=-1;titulo.focus({preventScroll:true})}}
function voltarAnalise(){
 const v=S.volta;if(!v)return;
 if(history.state&&history.state.deAnalise){history.back();return}   // a entrada anterior é a própria análise
 S.anal=v.anal;mostrarArea('analises');setTimeout(()=>window.scrollTo(0,v.rolagem),0)}
// o atalho fica no topo da ficha só enquanto ela foi aberta a partir de uma análise (ou do cartão de um processo no mapa), para a mesma empresa
function linkVolta(){
 let b=el('ea-volta-analise');const ficha=el('ea-ficha');if(!ficha)return;
 if(!b){b=document.createElement('p');b.id='ea-volta-analise';b.className='ea-volta';ficha.insertBefore(b,ficha.firstChild)}
 const v=S.volta,on=!!v&&S.sel!==null&&porI.get(S.sel).cnpj===v.cnpj;b.hidden=!on;
 b.innerHTML=!on?'':v.tipo==='mapa'?`<button type="button" class="link-button" data-volta-mapa>← ${escape(t('ea.volta.mapa',{proc:v.proc}))}</button>`
  :`<button type="button" class="link-button" data-volta-analise>← ${escape(t('ea.voltaAnalise',{anal:rotuloAnalise(v.anal)}))}</button>`;
 const x=b.querySelector('[data-volta-analise]');if(x)x.onclick=voltarAnalise;
 const y=b.querySelector('[data-volta-mapa]');if(y)y.onclick=voltarAoMapa}

// Do cartão do processo para o dossiê do titular: Território (na linha do processo, na página certa) ou Perfil. A entrada atual do
// histórico (o mapa) guarda o processo, o modo e o enquadramento; "Voltar ao mapa" (ou Voltar do navegador) devolve tudo como estava.
function abrirProcessoNoDossie(k,aba){
 const r=D.processos.rows[k],i=r[PC.empresa];if(i<0||!porI.has(i))return;
 const e=porI.get(i),c=S.mapa?S.mapa.getCenter():null;
 anotarHistorico({proc:r[PC.processo],modo:S.modo,vista:c?{lat:c.lat,lng:c.lng,z:S.mapa.getZoom()}:null});
 S.volta={tipo:'mapa',cnpj:e.cnpj,proc:r[PC.processo]};
 selecionar(i,{origem:'mapa',processo:k,semHistorico:true});
 S.aba=aba;S.irProc=aba==='territorio';S.enqPend=false;
 mostrarArea('dossie');
 anotarHistorico({deMapa:{...S.volta}});
 if(aba!=='territorio'){const f=el('ea-area-dossie');if(f)f.scrollIntoView({block:'start'})}}
function voltarAoMapa(){
 const v=S.volta;if(!v)return;
 if(history.state&&history.state.deMapa){history.back();return}   // a entrada anterior é o próprio mapa
 const k=procPorId.get(soDigitos(v.proc));S.enqPend=false;mostrarArea('explorar');
 if(k!=null){if(S.modo!=='processos')definirModo('processos');selecionarProcesso(k,{ir:true})}}
// Território do dossiê aberto pelo processo: rola até a linha dele (já na página certa), realça e põe o foco no número.
function rolarAteProcesso(){
 const tr=el('ea-corpo').querySelector('tr.ea-destaque');
 if(!tr){if(S.destaque!==null)aviso(t('ea.proc.naoNaTabela',{p:D.processos.rows[S.destaque][PC.processo]}));return}
 setTimeout(()=>{tr.scrollIntoView({block:'center',behavior:'smooth'});tr.classList.add('ea-pisca');
  const b=tr.querySelector('[data-proc]');if(b)b.focus({preventScroll:true});setTimeout(()=>tr.classList.remove('ea-pisca'),2400)},80)}

// Município do dossiê → Explorar: o município vira recorte e foco (contorno, etiqueta, cartão do território), a empresa do dossiê fica
// como empresa de interesse (não como filtro), o modo do mapa não muda. A entrada do dossiê guarda a rolagem; o cartão oferece a volta.
function irMunicipioDoDossie(k){
 fecharPrevia();
 if(k==null||!el('ea-mun').querySelector(`option[value="${k}"]`))return;
 const e=S.sel!==null?porI.get(S.sel):null;
 if(S.area==='dossie')anotarHistorico({rolagem:window.scrollY});
 S.munOrigem=e&&S.area==='dossie'?{cnpj:e.cnpj,nome:e.nome,aba:S.aba}:null;
 S.enqPend=false;mostrarArea('explorar');
 selecionarMunicipio(k,{origem:'dossie',enquadrar:false});
 if(S.munOrigem)anotarHistorico({deDossie:{...S.munOrigem}});
 setTimeout(()=>{if(S.mapa)S.mapa.invalidateSize();enquadrarMunicipio(k);el('ea-map').scrollIntoView({block:'nearest',behavior:'smooth'})},40)}
function voltarAoDossie(){
 const o=S.munOrigem;if(!o)return;
 if(history.state&&history.state.deDossie&&history.state.deDossie.cnpj===o.cnpj){history.back();return}
 const e=porCnpj(o.cnpj);if(!e)return;
 if(S.sel!==e.i)selecionar(e.i,{origem:'dossie',semHistorico:true});
 if(o.aba)S.aba=o.aba;mostrarArea('dossie')}

// Fora do Explorar, a seleção aparece no alto da aba (o Explorar mostra o cartão sobre o mapa): nome, CNPJ e o × para desmarcar.
function barraSelecao(){
 const box=el('ea-sel');
 if(S.sel===null){box.innerHTML=`<span class="ea-sel-vazia">${escape(t('ea.sel.nenhumaCurta'))}</span>`;return}
 const e=porI.get(S.sel);
 box.innerHTML=`<span class="ea-sel-rot">${escape(t('ea.selecionada'))}</span><span class="ea-sel-nome"><b title="${escape(e.nome)}">${escape(e.nome)}</b><small>${escape(cnpjFmt(e.cnpj))}</small></span>`
  +`<button type="button" class="ea-x ea-sel-x" aria-label="${escape(t('ea.limparSelecao'))}" title="${escape(t('ea.limparSelecaoDica'))}">×</button>`;
 box.querySelector('.ea-sel-x').onclick=()=>limparSelecao();}

// O que a base tem da empresa, em uma linha: CFEM, carga CCEE, produção estimada e declarada, projetos e notícias.
function dadosDisponiveis(e){
 const A=window.EmpresasAnalises,pronto=!!A&&A.pronto();
 const item=(on,rot)=>{const est=on===null?t('ea.dados.carregando'):on?t('ea.dados.sim'):t('ea.dados.nao');
  return `<span class="ea-dado ${on===null?'pend':on?'sim':'nao'}" title="${escape(rot+': '+est)}"><i aria-hidden="true">${on===null?'…':on?'✓':'–'}</i>${escape(rot)}<span class="sr-only">: ${escape(est)}</span></span>`};
 return item(Object.keys(e.cfem).length>0,t('ea.dados.cfem'))+item(Object.keys(e.ccee).length>0,t('ea.dados.ccee'))
  +item(pronto?A.temEstimada(e.cnpj):null,t('ea.dados.est'))+item(pronto?A.temDeclarada(e.cnpj):null,t('ea.dados.dec'))
  +`<span class="ea-dado-n">${escape(t('ea.dados.projNews',{p:num(e.np),n:num(e.nn)}))}</span>`}

// Cartão contextual, um só sobre o mapa: o conteúdo segue o foco — empresa, processo ANM ou município. Nunca dois cartões empilhados.
function resumoSel(){
 const box=el('ea-resumo');if(!box)return;
 const f=D?focoAtual():null;
 box.dataset.foco=f||'';
 if(!f){box.hidden=true;box.innerHTML='';return}
 box.setAttribute('aria-label',t({empresa:'ea.cardAria',processo:'ea.card.ariaProc',municipio:'ea.card.ariaMun'}[f]));
 if(f==='processo')return cartaoProcesso(box);
 if(f==='municipio')return cartaoMunicipio(box);
 cartaoEmpresa(box)}
function cartaoEmpresa(box){
 const x=`<button type="button" class="ea-x ea-card-x" aria-label="${escape(t('ea.limparSelecao'))}" title="${escape(t('ea.limparSelecaoDica'))}">×</button>`;
 const e=porI.get(S.sel),per=S.per||[2022,2025],cf=cfemPeriodo(e.i,{mun:'',min:''},per),gi=faseMaisAvancada(procsPorEmp.get(e.i)||[]),naCmp=S.cmp.includes(e.i);
 const resumir=(xs,n)=>xs.length?xs.slice(0,n).join(', ')+(xs.length>n?` +${xs.length-n}`:''):'—';
 const mins=minsOrdenados(e).map(m=>D.dims.min[m][0]),ref=referencia(e);
 if(!mins.length&&ref.min)mins.push(ref.min);
 // território: a operação documentada primeiro; sem ela, os direitos vigentes; só disponibilidade ou só CFEM dizem o que são
 const o=munsPorOrigem(e),nomes=ks=>ks.map(k=>D.dims.mun[k][1]);
 const onde=o.op.length?`${t('ea.card.opDoc')}: ${resumir(nomes(o.op),2)}`:o.vig.length?`${t('ea.card.direitosVig')}: ${resumir(nomes(o.vig),3)}`
  :o.disp.length?`${t('ea.card.soDisp')}: ${resumir(nomes(o.disp),2)}`:o.cfem.length?`${t('ea.card.soCfem')}: ${resumir(nomes(o.cfem),2)}`:(ref.mun||'—');
 box.hidden=false;
 box.innerHTML=`<div class="ea-card-cab"><span class="ea-card-rot"><i class="ea-dot" style="background:${COR[GRUPOS[gi]]}"></i>${escape(t('ea.selecionada'))}</span>${x}</div>`
  +`<b class="ea-card-nome" title="${escape(e.nome)}">${escape(e.nome)}</b>`
  +`<p class="ea-card-id">${escape(cnpjFmt(e.cnpj))}${e.grupo?' · '+escape(e.grupo):''}</p>`
  // o que é o ponto: sem município, o direito de referência estadual; com município, só se a empresa tem um direito com ponto dentro dele
  +(munSel()!==null?(S.locE&&S.locE.has(e.i)?`<p class="ea-card-micro">${escape(t('ea.card.pontoRefMun'))}</p>`:'')
   :e.pt>=0?`<p class="ea-card-micro">${escape(t('ea.card.pontoRef'))}</p>`:'')
  +`<dl class="ea-card-fatos"><div><dt>${escape(t('ea.card.onde'))}</dt><dd>${escape(onde)}</dd></div>`
  +`<div><dt>${escape(t('ea.card.minerais'))}</dt><dd>${escape(resumir(mins,3))}</dd></div>`
  +`<div><dt>${escape(t('ea.k.cfem',{per:per.join('–')}))}</dt><dd><b>${cf?escape(brl(cf)):'—'}</b></dd></div>`
  +`<div><dt>${escape(t('ea.k.processos'))}</dt><dd><b>${num(e.n)}</b> <small>${escape(rotuloGrupo(GRUPOS[gi]))}</small></dd></div></dl>`
  +recorteDoCartao(e)
  +`<p class="ea-card-dados">${dadosDisponiveis(e)}</p>`
  +`<div class="ea-card-acoes"><button type="button" class="btn" data-ir="dossie">${escape(t('ea.abrirDossie'))} →</button>`
  +`<button type="button" class="btn outline" data-cmp aria-pressed="${naCmp}"${!naCmp&&S.cmp.length>=CMP_MAX?` title="${escape(t('ea.cmpCheia',{n:String(CMP_MAX)}))}"`:''}>${escape(naCmp?t('ea.cmpRemoverCurto'):t('ea.sel.comparar'))}</button></div>`;
 box.querySelector('.ea-card-x').onclick=()=>limparSelecao();
 box.querySelector('[data-ir]').onclick=()=>mostrarArea('dossie');
 box.querySelector('[data-cmp]').onclick=()=>alternarComparacao(e.i);
 const est=box.querySelector('[data-estadual]');if(est)est.onclick=()=>{S.verEstadual=!S.verEstadual;desenharPontos();desenharSelecao(true,false)};}
// Linha compacta da empresa de interesse (quando o foco é outro): o nome reabre o cartão dela.
function linhaInteresse(extra,fora){
 if(S.sel===null)return '';const e=porI.get(S.sel);
 return `<p class="ea-card-interesse${fora?' fora':''}"><span>${escape(t('ea.card.interesse'))}</span> <button type="button" class="ea-emp-link" data-interesse title="${escape(t('ea.card.interesseDica'))}">${escape(e.nome)}</button>${extra?' · '+escape(extra):''}</p>`}
function ligarInteresse(box){const b=box.querySelector('[data-interesse]');if(b)b.onclick=()=>{if(S.modo==='processos'&&S.destaque!==null)S.destaque=null;S.foco='empresa';estadoBotoesMapa();if(S.tela)S.tela.repintar()}}
// Processo ANM: número, fase exata, situação, mineral, área do processo inteiro, municípios vinculados (IBGE), titular PJ quando há (pessoa
// física não é nomeada), CFEM do PRÓPRIO processo só quando a fonte traz o processo — nunca a CFEM do titular — e os caminhos: dossiê
// (Território, na linha do processo), titular (Perfil) e o cadastro oficial na ANM.
function cartaoProcesso(box){
 const k=S.destaque,r=D.processos.rows[k],e=r[PC.empresa],g=D.dims.fase[r[PC.fase]].grupo,mi=D.dims.min[r[PC.mineral]];
 const per=S.per||[2022,2025],cpa=D.cfem_processo_ano&&D.cfem_processo_ano[r[PC.processo]];
 let cfRot=t('ea.card.cfemProc',{per:per.join('–')}),cfVal=null;
 if(cpa){let s=0;for(const[a,v]of Object.entries(cpa))if(+a>=per[0]&&+a<=per[1])s+=v;cfVal=s?brl(s):'—'}
 else if(r[PC.cfem_2022_2026]){cfRot=t('ea.card.cfemProc',{per:'2022–2026'});cfVal=brl(r[PC.cfem_2022_2026])}
 const muns=r[PC.municipios].map(m=>D.dims.mun[m][1]),url=urlAnm(r[PC.processo]),pj=e>=0;
 const tit=pj?`${escape(porI.get(e).nome)} <small>${escape(cnpjFmt(porI.get(e).cnpj))}</small>`:`<span class="muted">${escape(t(e===-2?'ea.pf':'ea.semTitular'))}</span>`;
 box.hidden=false;
 box.innerHTML=`<div class="ea-card-cab"><span class="ea-card-rot"><i class="ea-dot" style="background:${COR[g]||COR.outro}"></i>${escape(t('ea.card.processo'))}</span>`
  +`<button type="button" class="ea-x ea-card-x" aria-label="${escape(t('ea.card.limparProc'))}" title="${escape(t('ea.card.limparProc'))}">×</button></div>`
  +`<b class="ea-card-nome">${escape(r[PC.processo])}</b>`
  +`<p class="ea-card-id">${escape(D.dims.fase[r[PC.fase]].nome)} · ${escape(rotuloGrupo(g))}</p>`
  +`<dl class="ea-card-fatos"><div class="ea-largo"><dt>${escape(t('ea.th.situacao'))}</dt><dd>${escape(rotuloStatus(r[PC.status]))}</dd></div>`
  +`<div><dt>${escape(t('ea.th.mineral'))}</dt><dd>${escape(mi?mi[0]:'—')}</dd></div>`
  +`<div><dt>${escape(t('ea.card.area'))}</dt><dd><b>${r[PC.area_ha]!=null?escape(num(r[PC.area_ha],2)):'—'}</b> <small>ha</small></dd></div>`
  +`<div class="ea-largo"><dt>${escape(t('ea.card.municipios',{n:String(muns.length)}))}</dt><dd>${escape(muns.join(', ')||'—')}</dd></div>`
  +`<div class="ea-largo"><dt>${escape(t('ea.card.titular'))}</dt><dd>${tit}</dd></div>`
  +`<div class="ea-largo"><dt>${escape(cfRot)}</dt><dd>${cfVal?`<b>${escape(cfVal)}</b> <small>${escape(t('ea.card.cfemProcFonte'))}</small>`:`<span class="muted">${escape(t('ea.card.cfemProcSem'))}</span>`}</dd></div></dl>`
  +`<p class="ea-card-micro">${escape(t('ea.card.procNota'))}${r[PC.minas_ativas_sgb]?' '+escape(t('ea.card.sgb')):''}</p>`
  +(g==='disponibilidade'?`<p class="ea-card-recorte fora">${escape(t('ea.card.dispNota'))}</p>`:'')
  +(pj&&S.sel!==e?linhaInteresse():'')
  +(pj?`<div class="ea-card-acoes"><button type="button" class="btn" data-proc-dossie>${escape(t('ea.card.verProcDossie'))} →</button>`
    +`<button type="button" class="btn outline" data-proc-titular>${escape(t('ea.card.verTitular'))}</button></div>`:'')
  +(url?`<p class="ea-card-anm"><a href="${escape(urlSegura(url))}" target="_blank" rel="noopener noreferrer">${escape(t('ea.card.consultarAnm'))} ↗</a></p>`:'');
 box.querySelector('.ea-card-x').onclick=limparProcesso;
 const d=box.querySelector('[data-proc-dossie]');if(d)d.onclick=()=>abrirProcessoNoDossie(k,'territorio');
 const ti=box.querySelector('[data-proc-titular]');if(ti)ti.onclick=()=>abrirProcessoNoDossie(k,'perfil');
 ligarInteresse(box)}
// Totais do município inteiro no período, sem os outros filtros (mineral, fase, dado, busca): a régua para quando o recorte é menor.
// Mesmas regras do recorte: empresa entra com processo PJ vinculado (código IBGE) ou CFEM recolhida ali no período; projeto entra pelo
// processo citado (vinculado ao município) ou pelo município informado, desde que de empresa do município.
function totaisMunicipio(k){
 const per=S.per,chave=k+'|'+per.join('-');if(S.totMun&&S.totMun.k===chave)return S.totMun;
 const R=D.processos.rows,porEmp=new Map(),procs=new Set(),cfe=new Map();let cf=0;
 R.forEach((r,j)=>{const e=r[PC.empresa];if(e>=0&&r[PC.municipios].includes(k)){procs.add(j);porEmp.set(e,(porEmp.get(e)||0)+1)}});
 for(const r of D.cfem.rows)if(r[2]===k&&r[1]>=per[0]&&r[1]<=per[1]){cf+=r[4];cfe.set(r[0],(cfe.get(r[0])||0)+r[4])}
 const emp=new Set([...porEmp.keys(),...[...cfe].filter(([,v])=>v>0).map(([i])=>i)]);
 const proj=D.projetos.filter(p=>p.e.some(i=>emp.has(i))&&p.loc&&(p.loc.t==='p'?p.loc.k.some(x=>procs.has(x)):p.loc.m.includes(k))).length;
 return S.totMun={k:chave,emp:emp.size,procs:procs.size,cfem:cf,proj}}
// Município: nome · UF, código IBGE e o recorte em números discretos. Sem outros filtros, os números SÃO do município (no período); com
// outros filtros, os rótulos dizem "no recorte" e uma linha dá o município inteiro. Também: quantos processos vinculados têm o centroide
// fora do contorno (aparecem no mapa onde estão), a empresa de interesse (dentro ou fora, e se só por disponibilidade) e a volta ao dossiê.
function cartaoMunicipio(box){
 const k=munSel(),f=S.f,per=S.per.join('–'),u=S.universo,procs=u.reduce((s,l)=>s+l.ps.length,0),R=D.processos.rows;
 const cnt=new Map();for(const l of u)for(const p of l.ps){const m=R[p][PC.mineral];cnt.set(m,(cnt.get(m)||0)+1)}
 const mins=[...cnt].sort((a,b)=>b[1]-a[1]).slice(0,4).map(([m])=>D.dims.min[m]&&D.dims.min[m][0]).filter(Boolean);
 // processos de pessoa física ou sem titular vinculados ao município (contagem, sem nomes), com os mesmos filtros de mineral e fase
 const chave=[k,f.min,f.grupo].join('|');if(!S.semPj||S.semPj.k!==chave){let n=0;const mn=f.min===''?null:+f.min;
  for(const r of R)if(r[PC.empresa]<0&&r[PC.municipios].includes(k)&&(mn===null||r[PC.mineral]===mn)&&(!f.grupo||D.dims.fase[r[PC.fase]].grupo===f.grupo))n++;S.semPj={k:chave,n}}
 // vinculados com o centroide fora do contorno (o vínculo é do cadastro ANM; o ponto fica onde está, nada é deslocado)
 const idx=S.munIdx?S.munIdx.get(ibgeDe(k)):undefined,geo=idx!==undefined?S.munProj[idx]:null;let fora=0;
 if(geo)for(const l of u)for(const p of l.ps){const j=MP.j[p];if(j>=0&&!dentroPoligono(geo,MP.x[j],MP.y[j]))fora++}
 const outros=[f.min!==''?D.dims.min[+f.min][0]:'',f.grupo?rotuloGrupo(f.grupo):'',f.dado?el('ea-dado').selectedOptions[0].textContent:'',f.q?'“'+el('ea-busca').value.trim()+'”':''].filter(Boolean);
 const rec=outros.length>0,tot=rec?totaisMunicipio(k):null,nome=D.dims.mun[k][1];
 let interesse='';
 if(S.sel!==null){const l=S.uni.get(S.sel),e=porI.get(S.sel),og=origemMun(e,k);
  interesse=!l?linhaInteresse(t('ea.card.interesseFora'),true)
   :l.ps.length&&l.ps.every(emDisponibilidade)?linhaInteresse(t('ea.card.interesseDisp',{p:num(l.ps.length)}),true)
   :!l.ps.length?linhaInteresse(t('ea.card.interesseSoCfem',{cfem:l.cf?brl(l.cf):'—'}))
   :linhaInteresse(t('ea.card.interesseAqui',{p:num(l.ps.length),cfem:l.cf?brl(l.cf):'—'})+(og.op?' · '+t('ea.card.opDoc').toLocaleLowerCase():''))}
 const o=S.munOrigem,volta=o?`<div class="ea-card-acoes"><button type="button" class="btn outline" data-volta-dossie>← ${escape(t('ea.card.voltarDossie',{nome:o.nome}))}</button></div>`:'';
 box.hidden=false;
 box.innerHTML=`<div class="ea-card-cab"><span class="ea-card-rot"><svg class="ea-card-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h9l5 6-4 10H6l-2-8z"/></svg>${escape(t('ea.card.municipio'))}</span>`
  +`<button type="button" class="ea-x ea-card-x" aria-label="${escape(t('ea.card.fecharMun'))}" title="${escape(t('ea.card.fecharMun'))}">×</button></div>`
  +`<b class="ea-card-nome">${escape(nomeMunUf(k))}</b><p class="ea-card-id">${escape(t('ea.card.ibge',{c:ibgeDe(k)}))}</p>`
  +`<dl class="ea-card-fatos"><div><dt>${escape(t(rec?'ea.card.empresasRec':'ea.card.empresasMun'))}</dt><dd><b>${num(u.length)}</b></dd></div>`
  +`<div><dt>${escape(t(rec?'ea.card.processosRec':'ea.card.processosMun'))}</dt><dd><b>${num(procs)}</b>${S.semPj.n?` <small>${escape(t('ea.card.semPj',{n:num(S.semPj.n)}))}</small>`:''}</dd></div>`
  +`<div><dt>${escape(rec?t('ea.card.cfemRec',{mun:nome,per}):t('ea.card.cfemMun',{per}))}</dt><dd>${S.cfemTotal?`<b>${escape(brl(S.cfemTotal))}</b>`:`<span class="muted">${escape(t('ea.card.cfemMunSem'))}</span>`}</dd></div>`
  +`<div><dt>${escape(t(rec?'ea.card.projetosRec':'ea.card.projetosMun'))}</dt><dd><b>${num((S.projetos||[]).length)}</b></dd></div>`
  +`<div class="ea-largo"><dt>${escape(t('ea.card.mineraisMun'))}</dt><dd>${escape(mins.join(', ')||'—')}</dd></div></dl>`
  +(rec?`<p class="ea-card-recorte">${escape(t('ea.card.munFiltros',{f:outros.join(' · ')}))} ${escape(t('ea.card.munTotal',{e:num(tot.emp),p:num(tot.procs),cfem:tot.cfem?brl(tot.cfem):'—',proj:num(tot.proj)}))}</p>`:'')
  +(fora?`<p class="ea-card-micro">${escape(t('ea.card.foraContorno',{n:num(fora),t:num(procs)}))}</p>`:'')
  +interesse+volta
  +`<details class="ea-card-mais"><summary>${escape(t('ea.card.munMicro'))}</summary><p>${escape(t('ea.card.munNota'))}</p></details>`;
 box.dataset.fora=String(fora);box.dataset.recorte=rec?'1':'';
 box.querySelector('.ea-card-x').onclick=()=>{S.foco='fechado';estadoBotoesMapa();const b=document.querySelector('#ea-mun-etq .ea-mun-etq-nome');if(b)b.focus({preventScroll:true})};
 const v=box.querySelector('[data-volta-dossie]');if(v)v.onclick=voltarAoDossie;
 ligarInteresse(box)}

// Com filtro ativo, o cartão diz como a selecionada fica no recorte (os números acima são da empresa inteira) — ou que ela está fora
// dele. A seleção e os filtros não mudam sozinhos.
function recorteDoCartao(e){
 const f=S.f;if(!f||!(S.temFiltroTerr||f.dado||f.q))return '';
 const l=S.uni.get(e.i),km=munSel(),mun=km!==null?D.dims.mun[km][1]:'';
 // com município: ver só a atuação ali (padrão) ou em todo o estado — pedido explícito, que volta ao padrão quando o município muda
 const estadual=km!==null&&(procsPorEmp.get(e.i)||[]).length?`<button type="button" class="link-button ea-card-estadual" data-estadual>${escape(S.verEstadual?t('ea.card.verLocal',{mun}):t('ea.card.verEstadual'))}</button>`:'';
 if(!l)return `<p class="ea-card-recorte fora">${escape(t('ea.card.foraRecorte'))}${estadual?' '+estadual:''}</p>`;
 if(!S.temFiltroTerr)return '';
 const semPonto=km!==null&&S.locE&&!S.locE.has(e.i)?' '+t('ea.card.semPontoLocal',{mun}):'';
 return `<p class="ea-card-recorte">${escape(t('ea.card.noRecorte',{p:num(l.ps.length),cfem:l.cf?brl(l.cf):'—'})+semPonto)}${estadual?' '+estadual:''}</p>`;}

// O que a base tem da empresa, para os blocos "Dados não disponíveis" das análises: CFEM, títulos, carga do agente CCEE.
function resumoAlternativo(cnpj){
 const e=E.find(x=>x.cnpj===cnpj);if(!e)return '';
 const cf=Object.entries(e.cfem),tot=cf.reduce((s,[,v])=>s+v,0),cc=Object.entries(e.ccee);
 return `<ul class="ea-alt">`
  +`<li><b>${escape(t('ea.alt.cfem'))}</b> ${tot?escape(brl(tot))+' <span class="muted">('+escape(cf.map(([a,v])=>a+': '+brl(v)).join(' · '))+')</span>':escape(t('ea.alt.semCfem'))}</li>`
  +`<li><b>${escape(t('ea.alt.titulos'))}</b> ${e.n?GRUPOS.filter(g=>e.grupos[g]).map(g=>escape(rotuloGrupo(g))+': '+num(e.grupos[g])).join(' · ')+' · '+escape(num(e.area,0))+' ha':escape(t('ea.semProcesso'))}</li>`
  +`<li><b>${escape(t('ea.alt.ccee'))}</b> ${cc.length?escape(cc.map(([a,v])=>a+': '+num(v.obs,0)+' MWh ('+t('ea.meses',{n:String(v.meses)})+')').join(' · ')):escape(t('ea.alt.semCcee'))}</li>`
  +`</ul><p class="mk-note">${escape(t('ea.alt.nota'))}</p>`
  +`<p><button type="button" class="link-button" data-alt-dossie>${escape(t('ea.abrirDossie'))} →</button> · <button type="button" class="link-button" data-alt-direitos>${escape(t('ea.alt.irDireitos'))} →</button></p>`;}
document.addEventListener('click',ev=>{const b=ev.target.closest('[data-alt-dossie],[data-alt-direitos]');if(!b||!el('empresas-view').contains(b))return;
 if(b.hasAttribute('data-alt-dossie'))mostrarArea('dossie');else{mostrarArea('analises');mostrarAnalise('direitos')}});

function barraEscopo(){
 const box=el('ea-escopo'),e=S.sel!==null?porI.get(S.sel):null;
 if(!e)S.escopo='todas';
 box.innerHTML=`<span class="ea-lbl">${escape(t('ea.escopo.rot'))}</span><div class="ea-seg" role="radiogroup" aria-label="${escape(t('ea.escopo.rot'))}">`
  +`<button type="button" role="radio" data-escopo="empresa" aria-checked="${S.escopo==='empresa'}" ${e?'':'disabled'}>${escape(e?t('ea.escopo.empresa',{nome:e.nome}):t('ea.escopo.nenhuma'))}</button>`
  +`<button type="button" role="radio" data-escopo="todas" aria-checked="${S.escopo==='todas'}">${escape(t('ea.escopo.todas'))}</button></div>`;
 box.querySelectorAll('[data-escopo]').forEach(b=>b.onclick=()=>definirEscopo(b.dataset.escopo));}
function definirEscopo(x){
 S.escopo=x==='empresa'&&S.sel!==null?'empresa':'todas';barraEscopo();
 const e=S.sel!==null?porI.get(S.sel):null;
 if(window.EmpresasAnalises)window.EmpresasAnalises.escopo({cnpj:e?e.cnpj:null,nome:e?e.nome:'',escopo:S.escopo});
 if(window.empresasPanoramaEscopo)window.empresasPanoramaEscopo(S.escopo==='empresa'&&e?e.cnpj:null,e?e.nome:'');
 anotarHistorico({escopo:S.escopo});}
function mostrarAnalise(a){
 if(!ANALISES.includes(a))return;S.anal=a;
 ANALISES.forEach(x=>{el('ea-anal-'+x).hidden=x!==a;const b=el('ea-anal-tab-'+x),on=x===a;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});
 // estimada e declarada já dizem o que são na síntese (ressalva); o parágrafo de abertura fica só para a análise sem síntese
 el('ea-anal-lead').textContent=a==='direitos'?t('ea.anal.direitosLead'):'';el('ea-anal-lead').hidden=a!=='direitos';
 barraEscopo();
 if(a==='direitos'&&window.showEmpresasPanorama)window.showEmpresasPanorama();}

// ------------------------------------------------------------------ seleção (uma para a aba inteira)
const ABAS=['perfil','territorio','economia','projetos','noticias','historico'];
const rotuloAba=a=>({perfil:t('ea.aba.perfil'),territorio:t('ea.aba.territorio'),economia:t('ea.aba.economia'),projetos:t('ea.aba.projetos'),
 noticias:t('ea.aba.noticias'),historico:t('ea.aba.historico')}[a]);

function selecionar(i,{origem='',processo=null,semHistorico=false,escopo=null}={}){
 if(!porI.has(i))return;
 const outra=S.sel!==i;
 // escolher uma empresa (mesmo a que já estava) volta as análises para ela; "Todas as empresas" é sempre um pedido explícito.
 // Duas exceções: vinda de uma análise, a análise fica no escopo em que estava (a pergunta do consultor não muda); vinda do histórico,
 // o escopo gravado na entrada.
 S.sel=i;S.destaque=processo;S.foco=processo!==null?'processo':'empresa';S.escopo=escopo||(origem==='analise'?S.escopo:'empresa');if(outra){S.ppag=0;S.nNews=40;S.nEv=25;S.tFiltro='';S.verEstadual=false}
 if(processo!==null&&origem!=='mapa')S.aba='territorio';
 if(!semHistorico)gravarHash(false);
 // a empresa escolhida fora do lote desenhado da lista: a lista cresce até ela (e rola só a lista até o item)
 const pos=S.ranking.findIndex(l=>l.e.i===i);if(pos>=S.nLista)S.nLista=Math.ceil((pos+1)/LOTE)*LOTE;
 barraSelecao();resumoSel();lista();desenharPontos();if(origem!=='lista')rolarLista();
 // o mapa só enquadra a empresa visível; com outra área aberta, enquadra quando o Explorar voltar (um mapa escondido não tem tamanho)
 const enquadrar=origem!=='mapa'&&origem!=='projeto';
 if(S.area==='explorar')desenharSelecao(enquadrar,origem!=='mapa');else{S.enqPend=enquadrar;desenharSelecao(false,false)}
 definirEscopo(S.escopo);
 if(S.area==='dossie')dossie();else esvaziarFicha();
 if(S.area==='comparar')comparar();
 if(S.area==='explorar'&&!largo.matches&&(origem==='busca'||origem==='lista'))el('ea-map').scrollIntoView({block:'nearest',behavior:'smooth'});
 if(!el('ea-ranking').hidden)ranking();}

function limparSelecao(semHistorico){
 S.sel=null;S.destaque=null;S.escopo='todas';if(S.foco!=='fechado')S.foco=null;
 if(!semHistorico)gravarHash(false);
 barraSelecao();resumoSel();lista();desenharPontos();desenharSelecao();definirEscopo('todas');
 if(S.area==='dossie')dossie();else esvaziarFicha();if(S.area==='comparar')comparar();
 if(!el('ea-ranking').hidden)ranking();}
// A ficha do dossiê só existe para a empresa selecionada: fora do Dossiê, trocar ou tirar a seleção a esvazia (é refeita ao abrir), para
// nenhum trecho escondido guardar a empresa anterior.
function esvaziarFicha(){fecharPrevia();const f=el('ea-ficha');if(!f||!f.dataset.cnpj)return;f.dataset.cnpj='';
 ['ea-ficha-titulo','ea-ficha-sub','ea-ficha-fatos','ea-kpis','ea-ficha-dados','ea-abas','ea-corpo'].forEach(id=>{const x=el(id);if(x)x.innerHTML=''})}

// Até três empresas. A quarta não entra (nem tira ninguém): o aviso explica e leva ao Comparar, onde se remove uma.
const CMP_MAX=3;
function alternarComparacao(i){
 if(S.cmp.includes(i))S.cmp=S.cmp.filter(x=>x!==i);
 else if(S.cmp.length>=CMP_MAX){aviso(t('ea.cmpCheia',{n:String(CMP_MAX)}),S.area==='comparar'?null:{rotulo:t('ea.cmpIrComparar'),acao:()=>mostrarArea('comparar')});return false}
 else S.cmp.push(i);
 el('ea-cmp-n').hidden=!S.cmp.length;el('ea-cmp-n').textContent=S.cmp.length?String(S.cmp.length):'';
 barraSelecao();resumoSel();if(S.area==='dossie'&&S.sel!==null)ficha();if(S.area==='comparar')comparar();return true}
// Aviso curto no rodapé da aba (role=status): some sozinho, ou com o ×.
function aviso(txt,acao){
 let b=el('ea-aviso');
 if(!b){b=document.createElement('div');b.id='ea-aviso';b.className='ea-aviso';b.setAttribute('role','status');b.setAttribute('aria-live','polite');el('empresas-view').appendChild(b)}
 b.innerHTML=`<span>${escape(txt)}</span>${acao?`<button type="button" class="link-button" data-aviso-acao>${escape(acao.rotulo)} →</button>`:''}`
  +`<button type="button" class="ea-x" data-aviso-x aria-label="${escape(t('ea.avisoFechar'))}" title="${escape(t('ea.avisoFechar'))}">×</button>`;
 b.hidden=false;clearTimeout(S.tAviso);
 const fechar=()=>{b.hidden=true;b.innerHTML=''};S.tAviso=setTimeout(fechar,7000);
 b.querySelector('[data-aviso-x]').onclick=fechar;
 const a=b.querySelector('[data-aviso-acao]');if(a)a.onclick=()=>{fechar();acao.acao()};}

// ------------------------------------------------------------------ ranking completo e Pareto (sob demanda, abaixo do mapa)
// Sempre pela CFEM do recorte, que é a régua dos puxadores: curva acumulada com a linha dos 80% e a tabela das 50 maiores.
function ranking(){
 const box=el('ea-ranking');if(box.hidden)return;
 const per=S.per.join('–'),tot=S.cfemTotal||0,com=S.universo.filter(l=>l.cf>0).sort((a,b)=>b.cf-a.cf);
 let acc=0;const ls=com.map((l,j)=>{acc+=l.cf;return {l,pos:j+1,parte:tot?l.cf/tot:0,acum:tot?acc/tot:0}});
 const n80=S.puxadores.size,TOPO=Math.min(S.nRk,ls.length);
 // curva: até 150 empresas (o resto da cauda soma pouco e achataria o desenho)
 const pts=ls.slice(0,150),W=720,H=210,P={l:40,r:12,t:12,b:28},w=W-P.l-P.r,h=H-P.t-P.b;
 const x=i=>P.l+(pts.length>1?i/(pts.length-1):0)*w,y=v=>P.t+(1-v)*h;
 const barW=Math.max(1,w/Math.max(pts.length,1)-1);
 const svg=pts.length?`<svg class="ea-pareto" viewBox="0 0 ${W} ${H}" role="img" aria-label="${escape(t('ea.rk.svgAria',{n:num(n80),u:num(com.length),per}))}">`
  +[0,.5,.8,1].map(v=>`<line x1="${P.l}" x2="${W-P.r}" y1="${y(v)}" y2="${y(v)}" class="${v===.8?'ea-p80':'ea-pgrade'}"/><text x="${P.l-6}" y="${y(v)+3.5}" text-anchor="end">${v*100}%</text>`).join('')
  +pts.map((p,i)=>`<rect x="${(x(i)-barW/2).toFixed(1)}" y="${y(p.parte).toFixed(1)}" width="${barW.toFixed(1)}" height="${(h*p.parte).toFixed(1)}" class="${i<n80?'ea-pbar on':'ea-pbar'}"/>`).join('')
  +`<path d="${pts.map((p,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(p.acum).toFixed(1)).join('')}" class="ea-pcurva"/>`
  +(n80&&n80<=pts.length?`<line x1="${x(n80-1)}" x2="${x(n80-1)}" y1="${P.t}" y2="${P.t+h}" class="ea-pcorte"/><text x="${x(n80-1)+5}" y="${P.t+11}" class="ea-pcorte-t">${escape(t('ea.rk.corte',{n:num(n80)}))}</text>`:'')
  +`<text x="${P.l}" y="${H-8}">1</text><text x="${W-P.r}" y="${H-8}" text-anchor="end">${num(pts.length)}</text><text x="${P.l+w/2}" y="${H-8}" text-anchor="middle">${escape(t('ea.rk.eixoX'))}</text></svg>`:'';
 box.innerHTML=`<div class="ea-rk-cab"><div><h2 id="ea-rk-titulo">${escape(t('ea.rk.titulo',{per}))}</h2>`
  +`<p class="subtitle">${escape(t('ea.rk.sub',{n:num(n80),u:num(com.length),total:brl(tot),per}))}</p></div>`
  +`<div class="ea-acoes"><button type="button" class="btn outline" data-rk-xlsx>${escape(t('ea.expXlsx'))}</button><button type="button" class="btn outline" data-rk-csv>${escape(t('ea.expCsv'))}</button><button type="button" class="ea-x" data-rk-fechar aria-label="${escape(t('ea.rk.fechar'))}" title="${escape(t('ea.rk.fechar'))}">×</button></div></div>`
  +(ls.length?`<div class="ea-rk-grade"><figure class="ea-rk-fig">${svg}<figcaption class="mk-note">${escape(t('ea.rk.leitura'))}</figcaption></figure>`
   +`<div class="table-wrap"><table class="pn-table ea-rk-tab"><thead><tr><th class="num">#</th><th>${escape(t('es.h.empresa'))}</th><th class="num">${escape(t('ea.k.cfem',{per}))}</th><th class="num">${escape(t('ea.rk.parte'))}</th><th class="num">${escape(t('ea.rk.acum'))}</th><th class="num">${escape(t('ea.k.processos'))}</th></tr></thead><tbody>`
   +ls.slice(0,TOPO).map(r=>`<tr class="${r.pos<=n80?'ea-rk-pux':''}${r.l.e.i===S.sel?' ea-destaque':''}"><td class="num">${r.pos}</td><td><button type="button" class="link-button ea-rk-nome" data-i="${r.l.e.i}">${escape(r.l.e.nome)}</button></td>`
    +`<td class="num">${escape(brl(r.l.cf))}</td><td class="num">${escape(num(r.parte*100,1))} %</td><td class="num">${escape(num(r.acum*100,1))} %</td><td class="num">${num(r.l.ps.length)}</td></tr>`).join('')
   +`</tbody></table></div></div>`
   +(ls.length>TOPO?`<div class="ea-pag ea-rk-pag"><button type="button" class="ea-mais" data-rk-mais>${escape(t('ea.maisLista',{n:num(Math.min(50,ls.length-TOPO))}))}</button><span>${escape(t('ea.rk.conta',{v:num(TOPO),n:num(ls.length)}))}</span></div>`:'')
  :`<p class="empty">${escape(t('ea.rk.vazio'))}</p>`);
 box.querySelector('[data-rk-fechar]').onclick=()=>alternarRanking(false);
 box.querySelector('[data-rk-csv]').onclick=()=>exportarRecorte('csv');
 box.querySelector('[data-rk-xlsx]').onclick=()=>exportarRecorte('xlsx');
 const mais=box.querySelector('[data-rk-mais]');if(mais)mais.onclick=()=>{S.nRk+=50;ranking();const b=box.querySelectorAll('.ea-rk-nome')[TOPO];if(b)b.focus({preventScroll:true})};
 box.querySelectorAll('[data-i]').forEach(b=>b.onclick=()=>{selecionar(+b.dataset.i,{origem:'ranking'});el('ea-map').scrollIntoView({block:'nearest',behavior:'smooth'})});}
function alternarRanking(abrir){
 const box=el('ea-ranking'),on=abrir===undefined?box.hidden:abrir;
 box.hidden=!on;el('ea-ranking-btn').setAttribute('aria-expanded',String(on));
 if(on){S.nRk=50;ranking();gaveta(false);box.scrollIntoView({behavior:'smooth',block:'start'})}else box.innerHTML='';}

function badgesCriticos(m){
 const c=criticosPorMin.get(m);if(!c)return '';
 return (c.federal.length?`<span class="ea-crit fed" title="${escape(D.criticos.federal.norma)}">${escape(t('ea.critFed'))}</span>`:'')
  +(c.estadual.length?`<span class="ea-crit est" title="${escape(D.criticos.estadual.norma)}">${escape(t('ea.critEst'))}</span>`:'');}

// ------------------------------------------------------------------ dossiê
function dossie(){
 const vazio=S.sel===null;el('ea-dossie-vazio').hidden=!vazio;el('ea-ficha').hidden=vazio;
 if(!vazio){ficha();return}
 // sugestões: os maiores do recorte atual
 el('ea-dossie-sug').innerHTML=`<span class="muted">${escape(t('ea.dossieSugestoes'))}</span>`+S.ranking.slice(0,6).map(l=>`<button type="button" class="ea-chip" data-i="${l.e.i}">${escape(l.e.nome)}</button>`).join('');
 el('ea-dossie-sug').querySelectorAll('[data-i]').forEach(b=>b.onclick=()=>selecionar(+b.dataset.i,{origem:'dossie'}));}

// Números de abertura do dossiê, cada um com período e fonte; os que dependem de análise levam ao aprofundamento.
function kpis(e){
 const per=S.per||[2022,2025],cf=cfemPeriodo(e.i,{mun:'',min:''},per),cc=Object.entries(e.ccee).sort().pop();
 const A=window.EmpresasAnalises,est=A?A.estimadaDe(e.cnpj):[],ult=est.length?Math.max(...est.map(l=>l.ano)):null;
 const estUlt=ult?principaisEstimadas(est.filter(l=>l.ano===ult)).slice(0,1):[];
 // o número de abertura é o último ANO publicado pela empresa; anualização de trimestres só entra se não houver ano publicado, e dita
 const dec=A?A.declaradaDe(e.cnpj).filter(l=>l.producao).sort((a,b)=>(a.producao.origem!=='declarada_anual')-(b.producao.origem!=='declarada_anual')||b.ano-a.ano):[];
 const decSub=l=>l.producao.origem==='declarada_anual'?t('ea.k.declaradaSub',{min:l.mineral||'',ano:String(l.ano)})
  :t('ea.k.declaradaSubParcial',{min:l.mineral||'',ano:String(l.ano),periodos:(l.producao.periodos||[]).join(', ')});
 const tile=(rot,val,sub,ir)=>`<div class="ea-kpi"><span>${escape(rot)}</span><b>${val}</b><small>${escape(sub)}</small>${ir?`<button type="button" class="link-button" data-anal="${ir}">${escape(t('ea.aprofundar'))} →</button>`:''}</div>`;
 // processos ficam na linha de fatos do cabeçalho (com as fases); aqui, os quatro números econômicos, cada um com período
 return tile(t('ea.k.cfem',{per:per.join('–')}),cf?escape(brl(cf)):'—',t('ea.k.cfemSub'),'direitos')
  +tile(t('ea.k.cceeUlt'),cc?escape(num(cc[1].obs,0))+' MWh':'—',cc?t('ea.k.cceeUltSub',{ano:cc[0],meses:String(cc[1].meses)}):t('ea.alt.semCcee'),cc?'direitos':null)
  +tile(t('ea.k.estimada'),estUlt.length?escape(toneladas(estUlt[0].producao_t)):'—',
   estUlt.length?t('ea.k.estimadaSub',{min:estUlt[0].mineral,base:rotuloBase(estUlt[0].base),ano:String(ult)}):t('ea.k.estimadaNao'),estUlt.length?'estimada':null)
  +tile(t('ea.k.declarada'),dec.length?escape(num(dec[0].producao.valor)+' '+dec[0].producao.unidade):'—',
   dec.length?decSub(dec[0]):t('ea.k.declaradaNao'),dec.length?'declarada':null);}
// Linhas estimadas mais representativas: base beneficiada (senão contido, senão ROM), ordenadas pela CFEM.
function principaisEstimadas(ls){
 const ordem=['beneficiada','conteudo_mineral','ROM'],porMin=new Map();
 ls.forEach(l=>{const b=porMin.get(l.mineral);if(!b||ordem.indexOf(l.base)<ordem.indexOf(b.base))porMin.set(l.mineral,l)});
 return [...porMin.values()].sort((a,b)=>(b.cfem_brl||0)-(a.cfem_brl||0));}

// Com filtro de município, mineral ou fase ativo no Explorar, uma frase curta acima dos números: o dossiê é da empresa inteira.
function notaRecorteFicha(){
 const k=el('ea-kpis');let n=el('ea-ficha-recorte');
 if(!n){n=document.createElement('p');n.id='ea-ficha-recorte';n.className='mk-note ea-ficha-recorte';k.parentNode.insertBefore(n,k)}
 const f=S.f||{},partes=[f.mun?D.dims.mun[+f.mun][1]:'',f.min?D.dims.min[+f.min][0]:'',f.grupo?rotuloGrupo(f.grupo):''].filter(Boolean);
 n.hidden=!partes.length;n.textContent=partes.length?t('ea.ficha.recorte',{filtros:partes.join(' · ')}):''}
function ficha(){
 const e=porI.get(S.sel);if(!e)return;
 const det=D.detalhes[String(e.i)];fecharPrevia();
 el('ea-ficha').dataset.cnpj=e.cnpj;
 el('ea-ficha-titulo').textContent=e.nome;
 el('ea-ficha-sub').innerHTML=[`<span>${escape(t('ea.cnpjRaiz'))} <b>${escape(cnpjFmt(e.cnpj))}</b></span>`,
  e.grupo?`<span>${escape(t('ea.grupo'))} <b>${escape(e.grupo)}</b></span>`:`<span class="muted">${escape(t('ea.grupoNao'))}</span>`,
  S.puxadores.has(e.i)?`<span class="pill ea-pill-pux">${escape(t('ea.puxadorLongo',{per:S.per.join('–')}))}</span>`:''].join('');
 // linha de fatos: onde atua, o que explora e os processos por fase (o território completo está na seção Território)
 const o=munsPorOrigem(e),mins=minsOrdenados(e);
 // território: a operação documentada (com os municípios dela) primeiro; os municípios vinculados, pela origem, num "ver" que abre ali mesmo
 const resumo=[t('ea.fatos.nVig',{n:num(o.vig.length)}),o.disp.length?t('ea.fatos.nDisp',{n:num(o.disp.length)}):'',o.cfem.length?t('ea.fatos.nCfem',{n:num(o.cfem.length)}):''].filter(Boolean).join(' · ');
 const terr=(o.op.length?`<p class="ea-terr-op"><span class="ea-terr-rot">${escape(t('ea.fatos.opDoc'))}</span> ${o.op.map(linkMunicipio).join(', ')}</p>`
   :`<p class="ea-terr-op"><span class="ea-terr-rot">${escape(t('ea.fatos.opDoc'))}</span> <span class="muted">${escape(t('ea.fatos.opNao'))}</span></p>`)
  +(o.total?`<details class="ea-terr-mais"><summary>${escape(t('ea.fatos.ver',{n:num(o.total)}))} <span class="muted">· ${escape(resumo)}</span></summary>${gruposMunicipios(o,true)}</details>`
   :`<p class="muted">${escape(t('ea.naoDisp'))}</p>`);
 const fases=GRUPOS.slice(0,4).filter(g=>e.grupos[g]).map(g=>`<span class="ea-fase-n"><i class="ea-dot" style="background:${COR[g]}"></i>${escape(rotuloGrupo(g))} ${num(e.grupos[g])}</span>`).join('');
 el('ea-ficha-fatos').innerHTML=`<div><dt>${escape(t('ea.fatos.terr'))}</dt><dd class="ea-terr">${terr}</dd></div>`
  +`<div><dt>${escape(t('ea.fatos.min'))}</dt><dd>${mins.length?mins.slice(0,6).map(m=>`<span class="ea-min-f">${escape(D.dims.min[m][0])}${badgesCriticos(m)}</span>`).join('')+(e.min.length>6?` <span class="muted">+${e.min.length-6}</span>`:''):`<span class="muted">${escape(t('ea.naoDisp'))}</span>`}</dd></div>`
  +`<div><dt>${escape(t('ea.fatos.proc'))}</dt><dd><b>${num(e.n)}</b> · ${escape(num(e.area,0))} ha${fases?`<span class="ea-fases-n">${fases}</span>`:''}</dd></div>`;
 el('ea-ficha-dados').innerHTML=`<span class="ea-dados-t">${escape(t('ea.situacaoDados'))}</span>${dadosDisponiveis(e)}`
  +`<span class="ea-dado-n">${escape(e.enr?t('ea.enrLongo'):t('ea.indiceGeral'))}</span>`
  +`<button type="button" class="link-button" data-ir-metodo>${escape(t('ea.verMetodo'))}</button>`;
 el('ea-ficha-dados').querySelector('[data-ir-metodo]').onclick=()=>{el('ea-metodo').open=true;el('ea-metodo').scrollIntoView({behavior:'smooth'})};
 const naCmp=S.cmp.includes(e.i);
 el('ea-cmp-add').textContent=naCmp?t('ea.cmpRemover'):t('ea.cmpAdicionar');
 el('ea-cmp-add').setAttribute('aria-pressed',String(naCmp));
 el('ea-cmp-add').title=!naCmp&&S.cmp.length>=CMP_MAX?t('ea.cmpCheia',{n:String(CMP_MAX)}):'';
 el('ea-kpis').innerHTML=kpis(e);
 el('ea-kpis').querySelectorAll('[data-anal]').forEach(b=>b.onclick=()=>{S.anal=b.dataset.anal;mostrarArea('analises')});
 notaRecorteFicha();linkVolta();
 el('ea-abas').innerHTML=ABAS.map(a=>`<button type="button" role="tab" class="pn-tab${a===S.aba?' active':''}" id="ea-tab-${a}" aria-controls="ea-corpo" aria-selected="${a===S.aba}" tabindex="${a===S.aba?0:-1}" data-aba="${a}">${escape(rotuloAba(a))}${a==='projetos'&&e.np?` <small>${e.np}</small>`:''}${a==='noticias'&&e.nn?` <small>${e.nn}</small>`:''}</button>`).join('');
 el('ea-abas').querySelectorAll('[data-aba]').forEach(b=>{b.onclick=()=>{S.aba=b.dataset.aba;ficha()};
  b.onkeydown=ev=>{const j=ABAS.indexOf(S.aba);if(ev.key==='ArrowRight'||ev.key==='ArrowLeft'){ev.preventDefault();S.aba=ABAS[(j+(ev.key==='ArrowRight'?1:ABAS.length-1))%ABAS.length];ficha();el('ea-tab-'+S.aba).focus()}}});
 // no celular as seis seções rolam de lado: a borda esmaecida avisa que há mais, e a seção aberta fica à vista
 const abas=el('ea-abas'),pista=()=>{abas.classList.toggle('ea-rola',abas.scrollWidth>abas.clientWidth+2);abas.classList.toggle('ea-fim',abas.scrollLeft+abas.clientWidth>=abas.scrollWidth-2)};
 abas.onscroll=pista;const ativa=el('ea-tab-'+S.aba);if(ativa&&abas.scrollWidth>abas.clientWidth+2)abas.scrollLeft=Math.max(0,abas.scrollLeft+ativa.getBoundingClientRect().left-abas.getBoundingClientRect().left-abas.clientWidth/2+ativa.offsetWidth/2);pista();
 el('ea-corpo').setAttribute('aria-labelledby','ea-tab-'+S.aba);
 el('ea-corpo').innerHTML=({perfil,territorio,economia,projetos,noticias,historico}[S.aba])(e,det);
 ligarCorpo(e);
 if(S.irProc){S.irProc=false;if(S.aba==='territorio')rolarAteProcesso()}}

function linhaFonte(txt,url){return `<p class="source-line">${escape(txt)}${url?` <a href="${escape(urlSegura(url))}" target="_blank" rel="noopener noreferrer">${escape(t('ea.verFonte'))} ↗</a>`:''}</p>`}

function perfil(e,det){
 const fases=Object.entries(e.fases).map(([f,n])=>[D.dims.fase[+f],n]).sort((a,b)=>b[1]-a[1]);
 const grupos=GRUPOS.filter(g=>e.grupos[g]).map(g=>`<div class="bar-row"><span class="bar-label">${escape(rotuloGrupo(g))}</span>`
   +`<div class="bar-track"><div class="bar-fill" style="width:${e.grupos[g]/e.n*100}%;background:${COR[g]}"></div></div><span class="bar-value">${num(e.grupos[g])}</span></div>`).join('');
 const minerais=e.min.map(m=>`<li><span>${escape(D.dims.min[m][0])}</span>${badgesCriticos(m)}</li>`).join('');
 const mins=minsOrdenados(e);
 return `<div class="ea-cols">
  <section><h4>${escape(t('ea.identidade'))}</h4><dl class="ea-dl">
   <dt>${escape(t('ea.razao'))}</dt><dd>${escape(e.nome)}</dd>
   <dt>${escape(t('ea.cnpjRaiz'))}</dt><dd>${escape(cnpjFmt(e.cnpj))} <span class="muted">· ${escape(t('ea.chave'))}</span></dd>
   <dt>${escape(t('ea.grupo'))}</dt><dd>${e.grupo?escape(e.grupo):`<span class="muted">${escape(t('ea.naoDisp'))}</span>`}</dd>
   <dt>${escape(t('ea.alias'))}</dt><dd>${e.alias&&e.alias.length?e.alias.map(a=>`<span class="pill">${escape(a)}</span>`).join(' '):`<span class="muted">${escape(t('ea.semAlias'))}</span>`}</dd>
   ${det?`<dt>${escape(t('ea.operacoes'))}</dt><dd>${escape(det.operacoes.join(' · '))}<div class="mk-note">${escape(t('ea.operacoesNota',{mun:det.municipios_operacao.join(', ')}))}</div></dd>`:''}
   <dt>${escape(t('ea.titularAnm'))}</dt><dd>${escape(t('ea.titularAnmTxt',{n:num(e.n),area:num(e.area,0)}))}</dd>
  </dl>
  <p class="mk-note">${escape(t('ea.identidadeNota'))}</p>
  ${det&&det.ri.length?`<h4>${escape(t('ea.ri'))}</h4><ul class="ea-links">${det.ri.map(r=>`<li><a href="${escape(urlSegura(r.u))}" target="_blank" rel="noopener noreferrer">${escape(r.t)} ↗</a></li>`).join('')}</ul>`:''}
  </section>
  <section><h4>${escape(t('ea.fasesT'))}</h4>${grupos||`<p class="mk-note">${escape(t('ea.semProcesso'))}</p>`}
   <p class="mk-note">${escape(t('ea.fasesNota'))}</p>
   <details><summary>${escape(t('ea.fasesDetalhe'))}</summary><table class="pn-table"><tbody>${fases.map(([f,n])=>`<tr><td>${escape(f.nome)}</td><td class="num">${num(n)}</td></tr>`).join('')}</tbody></table></details>
   <h4>${escape(t('ea.mineraisT'))}</h4><ul class="ea-minerais">${minerais||`<li class="muted">${escape(t('ea.naoDisp'))}</li>`}</ul>
   <p class="mk-note">${escape(t('ea.critNota'))} <button type="button" class="link-button" data-ir="metodo">${escape(t('ea.verBaseLegal'))}</button></p>
   <h4>${escape(t('ea.municipiosT',{n:String(munsPorOrigem(e).total)}))}</h4><div class="ea-muns-links">${gruposMunicipios(munsPorOrigem(e))||escape(t('ea.naoDisp'))}</div>
   <p class="mk-note">${escape(t('ea.mun.linkNota'))}</p>
  </section></div>
  ${linhaFonte(t('ea.fontePerfil'))}`;}

// Território do dossiê. Três blocos que não se confundem: operação DOCUMENTADA (o que a empresa divulga), INDÍCIOS de atividade (CFEM
// recente em título de lavra, camada do SGB, CFEM por município de origem — não confirmam operação) e DIREITOS (títulos e intenções, com
// os processos em disponibilidade à parte: área devolvida à ANM, vínculo histórico). Embaixo, a tabela de todos os processos, com filtro.
function territorio(e){
 const ks=procsPorEmp.get(e.i)||[],R=D.processos.rows,o=munsPorOrigem(e),grupo=k=>D.dims.fase[R[k][PC.fase]].grupo;
 const comCfemRecente=ks.filter(k=>/^Opera/.test(D.dims.status[R[k][PC.status]]));
 const lavraSem=ks.filter(k=>grupo(k)==='lavra_autorizada'&&!comCfemRecente.includes(k));
 const req=ks.filter(k=>grupo(k)==='requerimento_lavra'),pesq=ks.filter(k=>grupo(k)==='pesquisa'),disp=ks.filter(emDisponibilidade);
 const sgb=ks.filter(k=>R[k][PC.minas_ativas_sgb]);
 const det=D.detalhes[String(e.i)],realizado=det?det.producao.filter(p=>ehProducaoGO(p)&&p.nivel!=='operacao'):[];
 const projFuturos=(projPorEmp.get(e.i)||[]).filter(p=>p.maturidade&&!/OPERA/i.test(p.maturidade));
 const cfOrigem=[...o.cf.entries()].sort((a,b)=>b[1]-a[1]);
 const bloco=(tit,itens,nota,classe,vazio)=>`<div class="ea-ev ${classe}"><h5>${escape(tit)}</h5><ul>${itens.length?itens.join(''):`<li class="muted">${escape(vazio||t('ea.naoDisp'))}</li>`}</ul><p class="mk-note">${escape(nota)}</p></div>`;
 const n=x=>`<b>${num(x)}</b>`;
 return `<div class="ea-explora">
  ${bloco(t('ea.terr.opT'),[
    ...(det?det.operacoes.map(op=>`<li><b>${escape(op)}</b></li>`):[]),
    o.op.length?`<li>${escape(t('ea.terr.opMun'))} ${o.op.map(linkMunicipio).join(', ')}</li>`:'',
    ...(realizado.some(p=>p.periodo_tipo==='ano')?realizado.filter(p=>p.periodo_tipo==='ano').slice(-3):realizado.slice(-2)).map(p=>`<li><b>${escape(num(p.valor))} ${escape(p.unidade)}</b> ${escape(p.produto)} · ${escape(p.periodo)} <span class="muted">(${escape(t('ea.prodDeclarada'))})</span></li>`)
   ].filter(Boolean),t('ea.terr.opNota'),'explora',t('ea.terr.opNenhuma'))}
  ${bloco(t('ea.terr.indT'),[
    comCfemRecente.length?`<li>${n(comCfemRecente.length)} ${escape(t('ea.procCfemRecente'))}</li>`:'',
    sgb.length?`<li>${n(sgb.length)} ${escape(t('ea.procSgb'))}</li>`:'',
    cfOrigem.length?`<li>${escape(t('ea.terr.cfemOrigem'))} ${cfOrigem.slice(0,4).map(([k,v])=>`${linkMunicipio(k)} <span class="muted">${escape(brl(v))}</span>`).join(', ')}${cfOrigem.length>4?` <span class="muted">+${cfOrigem.length-4}</span>`:''}</li>`:''
   ].filter(Boolean),t('ea.terr.indNota'),'indicio',t('ea.terr.indNenhum'))}
  ${bloco(t('ea.terr.dirT'),[
    lavraSem.length?`<li>${n(lavraSem.length)} ${escape(t('ea.procLavraSem'))}</li>`:'',
    req.length?`<li>${n(req.length)} ${escape(t('ea.procReq'))}</li>`:'',
    pesq.length?`<li>${n(pesq.length)} ${escape(t('ea.procPesq'))}</li>`:'',
    projFuturos.length?`<li>${n(projFuturos.length)} ${escape(t('ea.projFuturos'))}</li>`:'',
    disp.length?`<li class="ea-hist">${n(disp.length)} ${escape(t('ea.terr.disp'))}${o.disp.length?` <span class="muted">· ${escape(t('ea.terr.dispMun',{n:num(o.disp.length)}))}</span>`:''}</li>`:''
   ].filter(Boolean),t('ea.podeExplorarNota'),'pode')}
 </div>
 <div class="atlas-data-head"><h4>${escape(t('ea.processosT',{n:num(ks.length)}))}</h4><div class="ea-acoes"><button type="button" class="btn outline" data-ver-mapa="processos">${escape(t('ea.verProcessosMapa'))}</button><button type="button" class="btn outline" data-exp="proc-csv">${escape(t('ea.expProcCsv'))}</button></div></div>
 ${ks.length>8?`<div class="ea-terr-filtro"><input type="search" id="ea-terr-q" value="${escape(S.tFiltro||'')}" placeholder="${escape(t('ea.terr.filtro'))}" aria-label="${escape(t('ea.terr.filtro'))}" aria-controls="ea-terr-tab" autocomplete="off"><span id="ea-terr-n" role="status" aria-live="polite"></span></div>`:''}
 <div id="ea-terr-tab">${tabelaTerritorio(e)}</div>
 <p class="mk-note">${escape(t('ea.terr.cfemNota'))}</p>
 ${linhaFonte(t('ea.fonteTerritorio'))}`;}
// Processos que passam pelo filtro do Território (número, município, mineral, fase, situação), na ordem natural (CFEM do processo, depois área).
function procsTerritorio(e){
 const ks=procsPorEmp.get(e.i)||[],R=D.processos.rows,q=norm((S.tFiltro||'').trim()),d=soDigitos(q);
 const ordem=[...ks].sort((a,b)=>R[b][PC.cfem_2022_2026]-R[a][PC.cfem_2022_2026]||(R[b][PC.area_ha]||0)-(R[a][PC.area_ha]||0)||a-b);
 if(!q)return ordem;
 return ordem.filter(k=>{const r=R[k],f=D.dims.fase[r[PC.fase]];
  if(d.length>=3&&soDigitos(r[PC.processo]).includes(d))return true;
  return norm([r[PC.processo],f.nome,rotuloGrupo(f.grupo),rotuloStatus(r[PC.status]),D.dims.min[r[PC.mineral]]?D.dims.min[r[PC.mineral]][0]:'',...r[PC.municipios].map(m=>D.dims.mun[m][1])].join(' ')).includes(q)})}
function tabelaTerritorio(e){
 const R=D.processos.rows,todos=(procsPorEmp.get(e.i)||[]).length;
 // vindo do mapa: o processo pedido tem de estar na lista (o filtro sai se o esconderia) e a tabela abre na página dele
 if(S.irProc&&S.destaque!==null&&S.tFiltro&&!procsTerritorio(e).includes(S.destaque)){S.tFiltro='';const q=el('ea-terr-q');if(q)q.value=''}
 const ordem=procsTerritorio(e),POR=15,pags=Math.max(1,Math.ceil(ordem.length/POR));
 if(S.irProc&&S.destaque!==null){const pos=ordem.indexOf(S.destaque);if(pos>=0)S.ppag=Math.floor(pos/POR)}
 S.ppag=Math.max(0,Math.min(S.ppag,pags-1));
 const nEl=el('ea-terr-n');if(nEl)nEl.textContent=S.tFiltro?t('ea.terr.n',{v:num(ordem.length),n:num(todos)}):'';
 const linhas=ordem.slice(S.ppag*POR,(S.ppag+1)*POR).map(k=>{const r=R[k],url=urlAnm(r[PC.processo]),cpa=D.cfem_processo_ano&&D.cfem_processo_ano[r[PC.processo]],g=D.dims.fase[r[PC.fase]].grupo;
  return `<tr class="${k===S.destaque?'ea-destaque':''}${g==='disponibilidade'?' ea-linha-disp':''}" data-linha-proc="${escape(r[PC.processo])}"><td><button type="button" class="link-button" data-proc="${k}" title="${escape(t('ea.verProcessoMapa'))}">${escape(r[PC.processo])}</button>`
   +(url?`<div class="mk-note"><a href="${escape(urlSegura(url))}" target="_blank" rel="noopener noreferrer">${escape(t('ea.cadastroAnm'))} ↗</a></div>`:'')+`</td>`
   +`<td>${escape(D.dims.fase[r[PC.fase]].nome)}<div class="mk-note"><i class="ea-dot" style="background:${COR[g]}"></i>${escape(rotuloGrupo(g))}</div></td>`
   +`<td>${escape(rotuloStatus(r[PC.status]))}${r[PC.minas_ativas_sgb]?`<div class="mk-note">${escape(t('ea.sgbFlag'))}</div>`:''}</td>`
   +`<td>${escape(D.dims.min[r[PC.mineral]]?D.dims.min[r[PC.mineral]][0]:'—')} ${badgesCriticos(r[PC.mineral])}</td>`
   +`<td>${r[PC.municipios].map(linkMunTabela).join(', ')||'—'}</td>`
   +`<td class="num">${r[PC.area_ha]!=null?num(r[PC.area_ha],2):'—'}</td>`
   // total 2022–2026 do Panorama na célula; a série anual (CFEM por processo, ANM) abre sob demanda, sem alargar a coluna
   +`<td class="num">${r[PC.cfem_2022_2026]?brl(r[PC.cfem_2022_2026]):'—'}${cpa?`<details class="ea-serie"><summary>${escape(t('ea.terr.serie'))}</summary>${Object.entries(cpa).map(([y,v])=>`<span>${escape(y)}: ${escape(brl(v))}</span>`).join('')}</details>`:''}</td></tr>`}).join('');
 return `<div class="table-wrap"><table class="pn-table ea-tabela"><thead><tr><th>${escape(t('ea.th.processo'))}</th><th>${escape(t('ea.th.fase'))}</th><th>${escape(t('ea.th.situacao'))}</th><th>${escape(t('ea.th.mineral'))}</th><th>${escape(t('ea.th.municipios'))}</th><th class="num">${escape(t('ea.th.area'))}</th><th class="num">${escape(t('ea.th.cfem'))}</th></tr></thead><tbody>${linhas||`<tr><td colspan="7" class="muted">${escape(S.tFiltro?t('ea.terr.nada'):t('ea.semProcesso'))}</td></tr>`}</tbody></table></div>`
  +(pags>1?`<div class="ea-pag"><button type="button" class="link-button" data-ppag="-1" ${S.ppag?'':'disabled'}>← ${escape(t('ea.anterior'))}</button><span>${escape(t('ea.pagina',{p:String(S.ppag+1),n:String(pags)}))}</span><button type="button" class="link-button" data-ppag="1" ${S.ppag<pags-1?'':'disabled'}>${escape(t('ea.proxima'))} →</button></div>`:'')}
// Município na tabela de Território: o mesmo link do cabeçalho e do Perfil, com prévia geográfica sob demanda.
// As linhas da tabela são paginadas; a prévia só é montada depois do hover (~650 ms), sem custo no desenho da tabela.
const linkMunTabela=k=>`<button type="button" class="ea-mun-link" data-mun-ibge="${escape(ibgeDe(k))}">${escape(D.dims.mun[k][1])}</button>`;
// liga os números de processo e a paginação da tabela (refeita sozinha quando o filtro muda, sem refazer a ficha nem tirar o foco do campo)
function ligarTabelaTerritorio(){
 const c=el('ea-terr-tab');if(!c)return;
 c.querySelectorAll('[data-proc]').forEach(b=>b.onclick=()=>{const k=+b.dataset.proc;S.enqPend=false;mostrarArea('explorar');if(S.modo!=='processos')definirModo('processos');selecionarProcesso(k,{ir:true})});
 c.querySelectorAll('[data-ppag]').forEach(b=>b.onclick=()=>{S.ppag+=+b.dataset.ppag;atualizarTabelaTerritorio();const t_=el('ea-terr-tab');if(t_)t_.scrollIntoView({block:'nearest'})});}
function tabelaTerritorioContagem(){const e=porI.get(S.sel),n=el('ea-terr-n');if(!e||!n)return;n.textContent=S.tFiltro?t('ea.terr.n',{v:num(procsTerritorio(e).length),n:num((procsPorEmp.get(e.i)||[]).length)}):''}
function atualizarTabelaTerritorio(){const e=porI.get(S.sel),c=el('ea-terr-tab');if(!e||!c)return;
 // a tabela é refeita (filtro, paginação): uma prévia aberta ou agendada para um link desta tabela fecharia órfã
 if(S.previaLink&&c.contains(S.previaLink)||S.tPrevia)fecharPrevia();
 c.innerHTML=tabelaTerritorio(e);ligarTabelaTerritorio()}

function barrasAno(serie,fmt,cor,nota){
 const ent=Object.entries(serie);if(!ent.length)return `<p class="mk-note">${escape(t('ea.naoDisp'))}</p>`;
 const max=Math.max(...ent.map(([,v])=>typeof v==='object'?v.anual:v),1);
 return ent.map(([a,v])=>{const val=typeof v==='object'?v:{x:v};
  return `<div class="bar-row ea-ano"><span class="bar-label">${escape(a)}</span><div class="bar-track ea-track">`
   +(typeof v==='object'?`<div class="bar-fill ea-anual" style="width:${v.anual/max*100}%"></div><div class="bar-fill ea-obs" style="width:${v.obs/max*100}%;background:${cor}"></div>`
     :`<div class="bar-fill" style="width:${v/max*100}%;background:${cor}"></div>`)
   +`</div><span class="bar-value">${escape(fmt(typeof v==='object'?v.obs:v))}</span></div>`
   +(nota?`<p class="mk-note">${escape(nota(a,val.x!==undefined?val.x:v))}</p>`:'')}).join('');}

// Economia e energia: resumo executivo. CFEM e carga CCEE ano a ano; produção estimada e declarada em poucas linhas, cada uma
// com o caminho para a análise completa (onde estão os filtros, os gráficos e as tabelas — sem repeti-los aqui).
function economia(e,det){
 const A=window.EmpresasAnalises,est=A?A.estimadaDe(e.cnpj):[],dec=A?A.declaradaDe(e.cnpj):[];
 const cfem=barrasAno(e.cfem,brl,'#0f6fb0',a=>a==='2026'?t('ea.parcial2026',{meses:String(D.meta.meses_cfem_2026.length)}):'');
 const ccee=barrasAno(e.ccee,v=>num(v,0)+' MWh','#0d9488',(a,v)=>t('ea.cceeNota',{meses:String(v.meses),anual:num(v.anual,0),q:rotuloQualidade(v.q)}));
 const ult=est.length?Math.max(...est.map(l=>l.ano)):null,estUlt=ult?principaisEstimadas(est.filter(l=>l.ano===ult)):[];
 const blocoEst=estUlt.length?`<div class="table-wrap"><table class="pn-table"><thead><tr><th>${escape(t('es.h.mineral'))}</th><th>${escape(t('es.h.base'))}</th><th class="num">${escape(t('es.h.producao'))}</th><th class="num">${escape(t('es.h.parcela'))}</th></tr></thead><tbody>`
   +estUlt.slice(0,6).map(l=>`<tr><td>${escape(l.mineral)}</td><td>${escape(rotuloBase(l.base))}</td><td class="num">${escape(toneladas(l.producao_t))} <span class="ea-est">${escape(t('ea.estimativa'))}</span></td><td class="num">${escape(num((l.parcela_do_estado||0)*100,1))} %</td></tr>`).join('')
   +`</tbody></table></div><p class="mk-note">${escape(t('ea.eco.estimadaNota',{ano:String(ult)}))}</p>`
  :`<div class="ea-indisp ea-indisp-mini"><b>${escape(t('ea.indisp.titulo'))}</b> ${escape(t('ea.eco.semEstimada'))}</div>`;
 const decAnual=dec.filter(l=>l.producao).sort((a,b)=>b.ano-a.ano||String(a.mineral).localeCompare(String(b.mineral)));
 const blocoDec=decAnual.length?`<ul class="ea-links">${decAnual.slice(0,5).map(l=>`<li><b>${escape(String(l.ano))} · ${escape(l.mineral||'—')}</b>: ${escape(num(l.producao.valor))} ${escape(l.producao.unidade)}`
   +(l.producao.origem==='anualizada_de_parciais'?` <span class="pill" title="${escape((l.producao.periodos||[]).join(', '))}">${escape(t('ep.origem.anualizada_de_parciais'))}</span>`:'')
   +(l.coeficiente?` · ${escape(t('ea.eco.coef'))} ${escape(num(l.coeficiente.valor,l.coeficiente.valor<100?1:0))} ${escape(l.coeficiente.unidade)} <span class="pill">${escape(rotuloQualidade(l.coeficiente.qualidade))}</span>`:'')+`</li>`).join('')}</ul>`
  :`<div class="ea-indisp ea-indisp-mini"><b>${escape(t('ea.indisp.titulo'))}</b> ${escape(t('ea.eco.semDeclarada'))}</div>`;
 const prod=det?det.producao:[];
 const registros=prod.length?`<details class="ea-registros"><summary>${escape(t('ea.eco.registros',{n:String(prod.length)}))}</summary><div class="table-wrap"><table class="pn-table"><thead><tr><th>${escape(t('ea.th.periodo'))}</th><th>${escape(t('ea.th.mineral'))}</th><th class="num">${escape(t('ea.th.valor'))}</th><th>${escape(t('ea.th.medida'))}</th><th>${escape(t('ea.th.tipo'))}</th><th>${escape(t('ea.th.fonte'))}</th></tr></thead><tbody>`
  +prod.map(p=>`<tr class="${ehProducaoGO(p)?'':'ea-nao-realizado'}"><td>${escape(p.periodo)}</td><td>${escape(p.mineral||'—')}<div class="mk-note">${escape(p.produto||'')}${p.nivel==='operacao'?' · '+escape(p.operacao):''}</div></td>`
   +`<td class="num"><b>${escape(num(p.valor))}${p.valor_max?'–'+escape(num(p.valor_max)):''}</b> ${escape(p.unidade)}</td><td>${escape(rotuloMedida(p.medida))}<div class="mk-note">${escape(rotuloEscopo(p.escopo))}</div></td>`
   +`<td><span class="pill">${escape(rotuloTipoValor(p.tipo_valor))}</span><div class="mk-note">${escape(t('ea.conf'))}: ${escape(rotuloConf(p.confianca))} · ${escape(p.status_validacao==='nao_validado'?t('ea.naoValidado'):p.status_validacao)}</div></td>`
   +`<td>${p.fonte_url?`<a href="${escape(urlSegura(p.fonte_url))}" target="_blank" rel="noopener noreferrer">${escape(p.fonte_nome)} ↗</a>`:escape(p.fonte_nome||'—')}</td></tr>`).join('')+'</tbody></table></div></details>':'';
 const notas=det&&det.notas_energia&&det.notas_energia.length?det.notas_energia.map(n=>`<p class="mk-note"><span class="pill">${escape(n.efeito)}</span> ${escape(n.texto)} ${n.fonte?`<a href="${escape(urlSegura(n.fonte))}" target="_blank" rel="noopener noreferrer">${escape(t('ea.verFonte'))} ↗</a>`:''}</p>`).join(''):'';
 const ir=(a,txt)=>`<button type="button" class="link-button ea-ir" data-anal="${a}">${escape(txt)} →</button>`;
 return `<div class="ea-cols">
  <section><h4>${escape(t('ea.cfemT'))}</h4><p class="mk-note">${escape(t('ea.cfemS'))}</p>${cfem}${ir('direitos',t('ea.eco.irDireitos'))}</section>
  <section><h4>${escape(t('ea.cceeT'))}</h4><p class="mk-note">${escape(t('ea.cceeS'))}</p>${ccee}${det&&det.rateio?`<p class="mk-note"><b>${escape(t('ea.rateio'))}</b> ${escape(det.rateio.nota)}</p>`:''}${notas}</section></div>
  <div class="ea-cols ea-eco-prod">
  <section><h4>${escape(t('ea.eco.estimadaT'))}</h4><p class="mk-note">${escape(t('ea.eco.estimadaS'))}</p>${blocoEst}${estUlt.length?ir('estimada',t('ea.eco.irEstimada')):''}</section>
  <section><h4>${escape(t('ea.eco.declaradaT'))}</h4><p class="mk-note">${escape(t('ea.eco.declaradaS'))}</p>${blocoDec}${decAnual.length?ir('declarada',t('ea.eco.irDeclarada')):''}${registros}</section></div>
  <p class="mk-note">${escape(t('ea.eco.naoSomar'))}</p>
  ${linhaFonte(t('ea.fonteEconomia'))}`;}

// Rótulo de um link pelo endereço de destino: a ANM pelo nome; os demais sites pelo domínio. Nunca o nome de quem fez o levantamento.
// tipo do registro de projeto (quem montou o registro, não a fonte primária)
const rotFonte=f=>({projetos:t('ea.pf.projetos'),mercado:t('ea.pf.mercado'),radar:t('ea.pf.radar')}[f]||f);
function destinoLink(url){const h=String(url||'').replace(/^https?:\/\//i,'').split('/')[0].toLowerCase().replace(/^www\./,'');
 return /(^|\.)anm\.gov\.br$/.test(h)?t('ea.link.anm'):t('ea.link.site',{host:h})}
function projetos(e){
 const ps=(projPorEmp.get(e.i)||[]).slice().sort((a,b)=>a.mat-b.mat||({projetos:0,mercado:1,radar:2}[a.fonte])-({projetos:0,mercado:1,radar:2}[b.fonte]));
 if(!ps.length)return `<p class="empty">${escape(t('ea.semProjetos'))}</p>${linhaFonte(t('ea.fonteProjetos'))}`;
 const capex=p=>p.capex?`${p.moeda||''} ${p.capex}${p.ano_capex?' ('+p.ano_capex+')':''}`:t('ea.naoDisp');
 return `<div class="table-wrap"><table class="pn-table"><thead><tr><th>${escape(t('ea.th.projeto'))}</th><th>${escape(t('ea.th.maturidade'))}</th><th>${escape(t('ea.th.mineral'))}</th><th>${escape(t('ea.th.capacidade'))}</th><th>${escape(t('ea.th.capex'))}</th><th>${escape(t('ea.th.vinculo'))}</th><th>${escape(t('ea.th.local'))}</th></tr></thead><tbody>`
  +ps.slice(0,60).map(p=>`<tr><td><b>${escape(p.nome)}</b><div class="mk-note">${escape(rotFonte(p.fonte))}${p.mun?' · '+escape(p.mun):''}${p.data?' · '+escape(p.data):''}</div>`
   // tipo do registro (linha acima) × quem publicou (fonte) × para onde o link leva (rótulo pelo endereço de destino)
   +(p.fonte_nome||p.link?`<div class="mk-note">${escape(t('ea.fonteRot'))}: ${p.fonte_nome?escape(p.fonte_nome):''}${p.link?`${p.fonte_nome?' · ':''}<a href="${escape(urlSegura(p.link))}" target="_blank" rel="noopener noreferrer">${escape(destinoLink(p.link))} ↗</a>`:''}</div>`:'')
   +(p.evidencias&&p.evidencias.length?`<details><summary>${escape(t('ea.evidencias',{n:String(p.evidencias.length)}))}</summary><ul class="ea-links">${p.evidencias.map(v=>`<li>${escape(v.d||'')} · ${v.u?`<a href="${escape(urlSegura(v.u))}" target="_blank" rel="noopener noreferrer">${escape(v.t)} ↗</a>`:escape(v.t)} <span class="muted">${escape(v.v||'')}</span></li>`).join('')}</ul></details>`:'')+`</td>`
   +`<td><span class="pill ea-pill-mat" style="border-color:${MAT[p.mat][2]}">${escape(p.maturidade||'—')}</span><div class="mk-note">${escape(p.fase||'')}</div></td><td>${escape(p.mineral||'—')}</td>`
   +`<td>${p.capacidade?escape(p.capacidade+' '+(p.cap_unidade||'')):`<span class="muted">${escape(t('ea.naoDisp'))}</span>`}</td><td>${escape(capex(p))}</td>`
   +`<td>${escape(rotuloMetodo(p.metodo))}<div class="mk-note">${escape(t('ea.conf'))}: ${escape(rotuloConf(p.conf))}${p.processos?' · '+escape(p.processos.slice(0,4).join(', '))+(p.processos.length>4?'…':''):''}</div></td>`
   +`<td>${p.loc&&MPJ.pos.has(p.j)?`<button type="button" class="link-button" data-proj="${p.j}">${escape(rotuloLocal(p))}</button>`:`<span class="muted">${escape(rotuloLocal(p))}</span>`}</td></tr>`).join('')
  +`</tbody></table></div>${ps.length>60?`<p class="mk-note">${escape(t('ea.maisProjetos',{n:String(ps.length-60)}))}</p>`:''}
  <p class="mk-note">${escape(t('ea.projetosNota'))}</p>${linhaFonte(t('ea.fonteProjetos'))}`;}

function noticias(e){
 const ns=newsPorEmp.get(e.i)||[];
 if(!ns.length)return `<p class="empty">${escape(t('ea.semNoticias'))}</p><p class="mk-note">${escape(t('ea.semNoticiasNota'))}</p>${linhaFonte(t('ea.fonteNoticias'))}`;
 const diretas=ns.filter(n=>n.tipo==='empresa'),indiretas=ns.filter(n=>n.tipo==='indireta'),nVer=Math.min(S.nNews,diretas.length);
 // notícia ligada pelo nome do GRUPO (não da empresa) leva a marca "via grupo": vale como contexto, não como fato da operação
 const li=n=>`<li${n.metodo==='alias_grupo'?' class="ea-news-grupo"':''}><a href="${escape(urlSegura(n.u))}" target="_blank" rel="noopener noreferrer">${escape(n.t)}</a><div class="rd-meta"><span class="rd-data">${escape(n.d)}</span><span class="rd-fonte">${escape(n.v)}</span>`
  +(n.go?`<span class="rd-tag-go">GO</span>`:'')+(n.metodo==='alias_grupo'?`<span class="ea-tag-grupo" title="${escape(t('ea.newsGrupoDica'))}">${escape(t('ea.newsGrupo'))}</span>`:'')
  +`<span class="rd-sub">${escape(rotuloMetodo(n.metodo))}: “${escape(n.alias)}”</span><span class="pill">${escape(t('ea.conf'))}: ${escape(rotuloConf(n.conf))}</span></div></li>`;
 const nGrupo=diretas.filter(n=>n.metodo==='alias_grupo').length;
 return `<p class="mk-note">${escape(t('ea.noticiasNota'))}${nGrupo?' '+escape(t('ea.newsGrupoConta',{n:num(nGrupo),total:num(diretas.length)})):''}</p><ul class="rd-news">${diretas.slice(0,nVer).map(li).join('')}</ul>
  ${diretas.length>40?`<div class="ea-pag">${nVer<diretas.length?`<button type="button" class="ea-mais" data-news-mais>${escape(t('ea.maisLista',{n:num(Math.min(40,diretas.length-nVer))}))}</button>`:''}<span>${escape(t('ea.newsConta',{v:num(nVer),n:num(diretas.length)}))}</span></div>`:''}
  ${indiretas.length?`<h4>${escape(t('ea.indiretasT'))}</h4><p class="mk-note">${escape(t('ea.indiretasS'))}</p><ul class="rd-news ea-indiretas">${indiretas.map(li).join('')}</ul>`:''}
  ${linhaFonte(t('ea.fonteNoticias'))}`;}

function historico(e,det){
 const evs=[...(newsPorEmp.get(e.i)||[]).filter(n=>n.tipo==='empresa').map(n=>({d:n.d,t:n.t,u:n.u,tipo:t('ea.evNoticia'),v:n.v})),
  ...(projPorEmp.get(e.i)||[]).filter(p=>p.fonte!=='radar').flatMap(p=>(p.evidencias||[]).map(v=>({d:v.d,t:v.t,u:v.u,tipo:t('ea.evProjeto'),v:v.v})))]
  .filter(x=>x.d).sort((a,b)=>b.d.localeCompare(a.d));
 const nEv=evs.length;evs.length=Math.min(evs.length,S.nEv);   // em lotes de 25 ("Mostrar mais"), do mais recente ao mais antigo
 const est=window.EmpresasAnalises?window.EmpresasAnalises.estimadaDe(e.cnpj):[];
 const anosC=[...new Set([...Object.keys(e.cfem),...Object.keys(e.ccee),...est.map(l=>String(l.ano))])].sort();
 const tab=`<table class="pn-table"><thead><tr><th>${escape(t('ea.th.ano'))}</th><th class="num">${escape(t('ea.th.cfemAno'))}</th><th class="num">${escape(t('ea.th.ccee'))}</th><th>${escape(t('ea.th.producao'))}</th><th>${escape(t('ea.th.estimada'))}</th></tr></thead><tbody>`
  +anosC.map(a=>{const pr=det?det.producao.filter(p=>String(p.periodo)===a&&ehProducaoGO(p)&&p.nivel!=='operacao'):[];
   const es=principaisEstimadas(est.filter(l=>String(l.ano)===a)).slice(0,2);
   return `<tr><td>${escape(a)}${a==='2026'?` <span class="muted">(${escape(t('ea.parcial'))})</span>`:''}</td><td class="num">${e.cfem[a]?brl(e.cfem[a]):'—'}</td>`
    +`<td class="num">${e.ccee[a]?escape(num(e.ccee[a].obs,0))+' MWh<div class="mk-note">'+escape(t('ea.meses',{n:String(e.ccee[a].meses)}))+'</div>':'—'}</td>`
    +`<td>${pr.length?pr.map(p=>escape(num(p.valor)+' '+p.unidade+' '+(p.mineral||''))).join('<br>'):'<span class="muted">—</span>'}</td>`
    +`<td>${es.length?es.map(l=>escape(toneladas(l.producao_t)+' '+l.mineral+' ('+rotuloBase(l.base)+')')).join('<br>'):'<span class="muted">—</span>'}</td></tr>`}).join('')+'</tbody></table>';
 return `<div class="ea-cols"><section><h4>${escape(t('ea.serieT'))}</h4><p class="mk-note">${escape(t('ea.serieS'))}</p><div class="table-wrap">${tab}</div></section>
  <section><h4>${escape(t('ea.eventosT'))}</h4>${evs.length?`<p class="mk-note">${escape(t('ea.eventosNota'))}</p>`:''}${evs.length?`<ol class="ea-timeline">${evs.map(x=>`<li><span class="rd-data">${escape(x.d)}</span><span class="pill">${escape(x.tipo)}</span> ${x.u?`<a href="${escape(urlSegura(x.u))}" target="_blank" rel="noopener noreferrer">${escape(x.t)}</a>`:escape(x.t)} <span class="muted">${escape(x.v||'')}</span></li>`).join('')}</ol>${nEv>25?`<div class="ea-pag">${evs.length<nEv?`<button type="button" class="ea-mais" data-ev-mais>${escape(t('ea.maisLista',{n:num(Math.min(25,nEv-evs.length))}))}</button>`:''}<span>${escape(t('ea.eventosConta',{v:num(evs.length),n:num(nEv)}))}</span></div>`:''}`:`<p class="mk-note">${escape(t('ea.semEventos'))}</p>`}</section></div>
  ${linhaFonte(t('ea.fonteHistorico'))}`;}

// ------------------------------------------------------------------ municípios do dossiê: link discreto + prévia geográfica
// Nome do município (cabeçalho e Perfil do dossiê) como link de texto, pelo código IBGE: clicar leva ao Explorar com o município como
// recorte; parar o mouse ~650 ms (ou o foco do teclado) abre a prévia, que não muda nada.
const linkMunicipio=k=>`<button type="button" class="ea-mun-link" data-mun-ibge="${escape(ibgeDe(k))}">${escape(D.dims.mun[k][1])}<span class="sr-only"> · ${escape(t('ea.mun.dica',{mun:D.dims.mun[k][1]}))}</span></button>`;
const PREVIA_MS=650;
// Links das bases (notícias coletadas na web, RI, fontes): só http(s); qualquer outro esquema vira '#', nunca javascript:.
const urlSegura=u=>/^https?:\/\//i.test(String(u??''))?String(u):'#';
// Grupos de municípios pela origem do vínculo (cabeçalho e Perfil do dossiê): operação documentada, direitos vigentes, só disponibilidade
// (vínculo histórico) e só CFEM. Cada nome é o mesmo link (código IBGE) com prévia; nada se repete entre os grupos de processo e CFEM.
function gruposMunicipios(o){
 const g=(rot,ks,cls)=>ks.length?`<p class="ea-mun-grupo${cls?' '+cls:''}"><span class="ea-mun-rot">${escape(rot)}</span> ${ks.map(linkMunicipio).join(', ')}</p>`:'';
 return g(t('ea.mun.gOp',{n:num(o.op.length)}),o.op)+g(t('ea.mun.gVig',{n:num(o.vig.length)}),o.vig)
  +g(t('ea.mun.gDisp',{n:num(o.disp.length)}),o.disp,'ea-mun-hist')+g(t('ea.mun.gCfem',{n:num(o.cfem.length)}),o.cfem,'ea-mun-cfem')}
// Prévia: contorno real do município (SVG, sem segundo mapa) e SÓ os direitos ANM da empresa do dossiê vinculados a ele pelo código IBGE.
// Ponto só onde o centroide cai dentro do município (nada é deslocado para dentro); o resto é contado e dito. Pontos no mesmo lugar viram
// um só com contador. Guardada em cache por empresa × município. Sem contorno no pacote, só o texto (nenhum desenho inventado).
function htmlPrevia(e,k){
 const ibge=ibgeDe(k),chave=e.cnpj+'|'+ibge;if(S.previa.has(chave))return S.previa.get(chave);
 const R=D.processos.rows,ks=(procsPorEmp.get(e.i)||[]).filter(p=>R[p][PC.municipios].includes(k));
 const idx=S.munIdx?S.munIdx.get(ibge):undefined,geo=idx!==undefined?S.munProj[idx]:null;
 let svg='',dentro=0,fora=0,sem=0,nGrupos=0;
 if(geo){
  const W=248,H=172,P=10,[x0,y0,x1,y1]=geo.bb,es=Math.min((W-2*P)/Math.max(x1-x0,1e-12),(H-2*P)/Math.max(y1-y0,1e-12));
  const ox=(W-(x1-x0)*es)/2,oy=(H-(y1-y0)*es)/2,px=x=>ox+(x-x0)*es,py=y=>oy+(y-y0)*es;
  const d=geo.rings.map(a=>{const pts=[];for(let i=0;i<a.length;i+=2)pts.push(L.point(px(a[i]),py(a[i+1])));
   return 'M'+L.LineUtil.simplify(pts,.4).map(q=>q.x.toFixed(1)+','+q.y.toFixed(1)).join('L')+'Z'}).join('');
  const grupos=new Map();
  for(const p of ks){const r=R[p];if(r[PC.lat]==null){sem++;continue}
   const q=projetar(r[PC.lat],r[PC.lon]);if(!dentroPoligono(geo,q.x,q.y)){fora++;continue}
   dentro++;const x=px(q.x),y=py(q.y),c=Math.round(x/8)+','+Math.round(y/8),gi=Math.max(0,GRUPOS.indexOf(D.dims.fase[r[PC.fase]].grupo)),g=grupos.get(c);
   if(g){g.n++;g.sx+=x;g.sy+=y;g.gi=Math.min(g.gi,gi)}else grupos.set(c,{n:1,sx:x,sy:y,gi})}
  const pts=[...grupos.values()].sort((a,b)=>b.gi-a.gi).map(g=>{const x=(g.sx/g.n).toFixed(1),y=(g.sy/g.n).toFixed(1),c=COR[GRUPOS[g.gi]];
   return g.n===1?`<circle cx="${x}" cy="${y}" r="3.6" fill="${c}" class="ea-pv-pt"/>`
    :`<circle cx="${x}" cy="${y}" r="6.6" fill="${c}" class="ea-pv-pt"/><text x="${x}" y="${(+y+3).toFixed(1)}" class="ea-pv-n">${g.n>99?'99+':g.n}</text>`}).join('');
  nGrupos=grupos.size;
  svg=`<svg class="ea-pv-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true"><path d="${d}" class="ea-pv-mun"/>${pts}</svg>`}
 else{for(const p of ks)if(R[p][PC.lat]==null)sem++}
 // origem do vínculo neste município: operação documentada, direitos vigentes, só disponibilidade (histórico) ou só CFEM
 const og=origemMun(e,k),linhas=[];
 if(og.op)linhas.push(t('ea.previa.op'));
 if(ks.length)linhas.push(t('ea.previa.n',{n:num(ks.length)}));
 else linhas.push(og.cfem?t('ea.previa.soCfem',{v:brl(og.cfem)}):t('ea.previa.nenhum'));
 if(ks.length&&!og.vig&&og.disp)linhas.push(t('ea.previa.soDisp'));
 else if(og.disp)linhas.push(t('ea.previa.algunsDisp',{n:num(og.disp)}));
 if(geo&&ks.length)linhas.push(t('ea.previa.leg'));
 if(fora)linhas.push(t('ea.previa.fora',{n:num(fora)}));
 if(sem)linhas.push(t('ea.previa.semCoord',{n:num(sem)}));
 if(!geo)linhas.push(t('ea.previa.semGeo'));
 const html=`<div class="ea-pv" data-ibge="${escape(ibge)}" data-n="${ks.length}" data-pontos="${dentro}" data-fora="${fora}" data-grupos="${nGrupos}" data-geo="${geo?1:0}" data-vig="${og.vig}" data-disp="${og.disp}" data-op="${og.op?1:0}" data-cfem="${og.cfem?1:0}">`
  +`<div class="ea-pv-cab"><b>${escape(nomeMunUf(k))}</b><small>${escape(t('ea.card.ibge',{c:ibge}))}</small></div>`
  +`<span class="ea-pv-t">${escape(t('ea.previa.titulo'))}</span>${svg}`
  +linhas.map(x=>`<small class="ea-pv-l">${escape(x)}</small>`).join('')+`<small class="ea-pv-acao">${escape(t('ea.previa.clique'))}</small></div>`;
 if(S.munProj)S.previa.set(chave,html);   // antes do contorno chegar, não guarda a versão sem desenho
 return html}
function mostrarPrevia(a){
 S.tPrevia=null;const k=kDoIbge(a.dataset.munIbge),e=S.sel!==null?porI.get(S.sel):null;
 if(k===null||!e||!document.body.contains(a)||S.area!=='dossie')return;
 let p=el('ea-previa');
 if(!p){p=document.createElement('div');p.id='ea-previa';p.className='ea-previa';p.setAttribute('role','tooltip');el('empresas-view').appendChild(p)}
 p.innerHTML=htmlPrevia(e,k);p.hidden=false;S.previaLink=a;a.setAttribute('aria-describedby','ea-previa');
 // abaixo do link (ou acima, se não couber), dentro da tela, sem cobrir o próprio link
 const r=a.getBoundingClientRect(),w=p.offsetWidth,h=p.offsetHeight,vw=document.documentElement.clientWidth,vh=window.innerHeight;
 let top=r.bottom+8;if(top+h>vh-8)top=r.top-8-h>=8?r.top-8-h:Math.max(8,vh-8-h);
 const sobre=top<r.bottom&&top+h>r.top;
 let left=Math.min(Math.max(8,r.left-12),vw-w-8);
 if(sobre)left=r.right+12+w<=vw-8?r.right+12:Math.max(8,r.left-12-w);
 p.style.top=Math.round(top)+'px';p.style.left=Math.round(left)+'px'}
function agendarPrevia(a){
 if(S.previaLink===a&&!el('ea-previa').hidden)return;
 clearTimeout(S.tPrevia);fecharPrevia();S.tPrevia=setTimeout(()=>mostrarPrevia(a),PREVIA_MS)}
function fecharPrevia(){
 clearTimeout(S.tPrevia);S.tPrevia=null;const p=el('ea-previa');
 if(S.previaLink){S.previaLink.removeAttribute('aria-describedby');S.previaLink=null}
 if(p&&!p.hidden){p.hidden=true;p.innerHTML=''}}
const previaAberta=()=>{const p=el('ea-previa');return !!p&&!p.hidden};

function verNoMapa(modo){mostrarArea('explorar');if(modo)definirModo(modo);desenharSelecao(true,false);el('ea-map').scrollIntoView({block:'center',behavior:'smooth'})}
function ligarCorpo(e){
 const c=el('ea-corpo');
 // tabela do Território: número do processo → o processo no mapa; paginação e filtro refazem só a tabela
 ligarTabelaTerritorio();
 const tq=el('ea-terr-q');if(tq){let tm=null;tabelaTerritorioContagem();tq.addEventListener('input',()=>{clearTimeout(tm);tm=setTimeout(()=>{S.tFiltro=tq.value;S.ppag=0;atualizarTabelaTerritorio()},120)})}
 c.querySelectorAll('[data-ver-mapa]').forEach(b=>b.onclick=()=>verNoMapa(b.dataset.verMapa));
 c.querySelectorAll('[data-proj]').forEach(b=>b.onclick=()=>{mostrarArea('explorar');definirModo('projetos');abrirProjeto(D.projetos[+b.dataset.proj],{origem:'dossie'})});
 c.querySelectorAll('[data-news-mais]').forEach(b=>b.onclick=()=>{const n=S.nNews;S.nNews+=40;ficha();const a=el('ea-corpo').querySelectorAll('.rd-news > li > a')[n];if(a)a.focus()});
 c.querySelectorAll('[data-ev-mais]').forEach(b=>b.onclick=()=>{const n=S.nEv;S.nEv+=25;ficha();const a=el('ea-corpo').querySelectorAll('.ea-timeline > li')[n];if(a){const l=a.querySelector('a');(l||a).focus&&(l||a).focus()}});
 c.querySelectorAll('[data-ir=metodo]').forEach(b=>b.onclick=()=>{el('ea-metodo').open=true;el('ea-metodo').scrollIntoView({behavior:'smooth'})});
 c.querySelectorAll('[data-anal]').forEach(b=>b.onclick=()=>{S.anal=b.dataset.anal;mostrarArea('analises')});
 c.querySelectorAll('[data-exp=proc-csv]').forEach(b=>b.onclick=()=>exportarProcessos(e));}

// ------------------------------------------------------------------ comparação (2 a 3 empresas)
// Empresa inteira (sem os filtros do Explorar), mesmas unidades: CFEM em R$ correntes por ano, carga do agente CCEE em MWh observados
// (com meses), produção estimada por mineral × base × ano (t) e produção declarada só entre registros com a MESMA chave (período,
// mineral, produto, medida, unidade, escopo, tipo de valor e nível; EmpresasExportar.gruposDeclarada). O maior da linha só se destaca
// quando os valores são comparáveis: um registro por empresa e, na CCEE, a mesma cobertura em meses.
// Linhas além do limite de cada grupo ficam a um clique ("Mostrar todas"); a exportação leva todas, inclusive as que não entram na tabela.
const LIM_CMP={est:12,dec:10,coef:6};
const naTabelaDeclarada=p=>ehProducaoGO(p)&&p.nivel!=='operacao'&&/^\d{4}$/.test(String(p.periodo));
// por que um registro declarado não entra na tabela de comparação (vazio = entra)
function motivoForaDaTabela(p){
 if(p.tipo_valor!=='realizado')return rotuloTipoValor(p.tipo_valor);
 if(!MEDIDAS_PRODUCAO.includes(p.medida))return rotuloMedida(p.medida);
 if(p.escopo!=='operacao_goias')return rotuloEscopo(p.escopo);
 if(p.nivel==='operacao')return t('ea.cmp.foraOperacao',{op:p.operacao||''});
 if(!/^\d{4}$/.test(String(p.periodo)))return t('ea.cmp.foraPeriodo');
 return '';}
const ordemBase=b=>['beneficiada','conteudo_mineral','ROM'].indexOf(b);
function linhasComparacao(es,{tudo=false}={}){
 // raw: os números por trás de cada célula (null = sem dado), para destacar o maior da linha; linhas sem raw não se destacam
 const L_=[],cortes={},linha=(grupo,rot,vals,raw,o)=>L_.push({grupo,rot,vals,raw:raw||null,...(o||{})});
 const A=window.EmpresasAnalises,per=S.per.join('–');
 const cortar=(g,xs)=>{const n=LIM_CMP[g];if(xs.length<=n)return xs;const aberto=tudo||S.cmpTudo.has(g);cortes[g]={n:aberto?xs.length:n,total:xs.length,aberto};return aberto?xs:xs.slice(0,n)};
 linha('id',t('ea.cnpjRaiz'),es.map(e=>cnpjFmt(e.cnpj)));
 linha('id',t('ea.grupo'),es.map(e=>e.grupo||'—'));
 const filtrado=S.temFiltroTerr||!!S.f.dado||!!S.f.q;
 linha('id',filtrado?t('ea.cmp.puxadorFiltro'):t('ea.puxador'),es.map(e=>S.puxadores.has(e.i)?t('ea.cmp.sim',{per}):t('ea.cmp.nao')));
 linha('terr',t('ea.m.processos'),es.map(e=>num(e.n)),es.map(e=>e.n));
 linha('terr',t('ea.met.area'),es.map(e=>num(e.area,0)+' ha'),es.map(e=>e.area));
 GRUPOS.slice(0,4).forEach(g=>linha('terr',rotuloGrupo(g),es.map(e=>num(e.grupos[g]||0)),es.map(e=>e.grupos[g]||0)));
 // municípios pela origem do vínculo (nunca um número só para direitos, histórico e CFEM)
 const mo=es.map(munsPorOrigem);
 linha('terr',t('ea.cmp.munOp'),mo.map(o=>o.op.length?num(o.op.length):'—'));
 linha('terr',t('ea.cmp.munVig'),mo.map(o=>num(o.vig.length)),mo.map(o=>o.vig.length));
 linha('terr',t('ea.cmp.munDisp'),mo.map(o=>num(o.disp.length)));   // histórico: sem destaque de maior
 linha('terr',t('ea.cmp.munCfem'),mo.map(o=>num(o.cfem.length)));
 const anosC=[...new Set(es.flatMap(e=>Object.keys(e.cfem)))].sort();
 anosC.forEach(a=>linha('cfem',`CFEM ${a}${a==='2026'?' ('+t('ea.parcial')+')':''}`,es.map(e=>e.cfem[a]?brl(e.cfem[a]):'—'),es.map(e=>e.cfem[a]||null)));
 const cfPer=es.map(e=>cfemPeriodo(e.i,{mun:'',min:''},S.per)||null);
 linha('cfem',t('ea.k.cfem',{per}),cfPer.map(v=>v?brl(v):'—'),cfPer,{periodo:true});
 // CCEE: com meses observados diferentes, o total maior não quer dizer carga maior — sem destaque, com a nota
 const anosE=[...new Set(es.flatMap(e=>Object.keys(e.ccee)))].sort();
 anosE.forEach(a=>{const ms=es.map(e=>e.ccee[a]?e.ccee[a].meses:null),dif=new Set(ms.filter(m=>m!=null)).size>1;
  linha('ccee',`${t('ea.th.ccee')} ${a}`,es.map(e=>e.ccee[a]?`${num(e.ccee[a].obs,0)} MWh · ${t('ea.meses',{n:String(e.ccee[a].meses)})}`:'—'),
   es.map(e=>e.ccee[a]?e.ccee[a].obs:null),{meses:ms,nota:dif?t('ea.cmp.coberturaDif'):''})});
 if(A){const est=es.map(e=>A.estimadaDe(e.cnpj));
  const ks=[...new Set(est.flat().map(l=>l.ano+'|'+l.mineral+'|'+l.base))].map(k=>k.split('|'))
   .sort((a,b)=>b[0]-a[0]||a[1].localeCompare(b[1])||ordemBase(a[2])-ordemBase(b[2]));
  cortar('est',ks).forEach(([ano,minr,base])=>{
   const ls_=est.map(ls=>ls.filter(x=>String(x.ano)===ano&&x.mineral===minr&&x.base===base)),dup=ls_.some(x=>x.length>1);
   linha('est',`${t('ea.cmp.estimada')} ${ano} · ${minr} · ${rotuloBase(base)} (t)`,ls_.map(x=>x.length?x.map(l=>toneladas(l.producao_t)).join(' · '):'—'),
    dup?null:ls_.map(x=>x.length?x[0].producao_t:null),{nota:dup?t('ea.cmp.duplicado'):''})});}
 // produção declarada: uma linha por chave de comparabilidade; produto ou medida diferentes no mesmo ano e mineral = outra linha, marcada
 const reg=es.map(e=>{const d=D.detalhes[String(e.i)];return d?d.producao:[]});
 const grupos=XP().gruposDeclarada(reg.map(rs=>rs.filter(naTabelaDeclarada)))
  .sort((a,b)=>String(b.ref.periodo).localeCompare(String(a.ref.periodo))||a.ref.mineral.localeCompare(b.ref.mineral)||a.ref.produto.localeCompare(b.ref.produto)||a.ref.unidade.localeCompare(b.ref.unidade));
 const vizinhos=new Map();grupos.forEach(g=>{const k=g.ref.periodo+'|'+g.ref.mineral;vizinhos.set(k,(vizinhos.get(k)||0)+1)});
 cortar('dec',grupos).forEach(g=>{const p=g.ref,faixa=g.por.some(rs=>rs.some(x=>x.valor_max!=null));
  const notas=[g.duplicado?t('ea.cmp.duplicado'):'',vizinhos.get(p.periodo+'|'+p.mineral)>1?t('ea.cmp.produtoDif'):''].filter(Boolean).join(' ');
  linha('dec',`${t('ea.cmp.declarada')} ${p.periodo} · ${p.mineral} · ${p.produto} · ${rotuloMedida(p.medida)} (${p.unidade})`,
   g.por.map(rs=>rs.length?rs.map(x=>num(x.valor)+(x.valor_max!=null?'–'+num(x.valor_max):'')).join(' · '):'—'),
   g.duplicado||faixa?null:g.por.map(rs=>rs.length?rs[0].valor:null),{nota:notas})});
 // coeficiente de energia: estimado (carga anualizada ÷ produção), por ano, mineral, produto e unidade; nunca em destaque
 if(A){const dec=es.map(e=>A.declaradaDe(e.cnpj).filter(l=>l.coeficiente));
  const chave=l=>[l.ano,l.mineral,(l.producao&&l.producao.produto)||'',l.coeficiente.unidade].join('|');
  const ks=[...new Set(dec.flat().map(chave))].map(k=>k.split('|')).sort((a,b)=>b[0]-a[0]||a[1].localeCompare(b[1])||a[2].localeCompare(b[2]));
  cortar('coef',ks).forEach(k=>{const ch=k.join('|'),[ano,minr,prod,un]=k;
   linha('coef',`${t('ea.cmp.coef')} ${ano} · ${minr}${prod?' · '+prod:''} (${un})`,dec.map(ls=>{const l=ls.find(x=>chave(x)===ch);
    return l?num(l.coeficiente.valor,l.coeficiente.valor<100?1:0)+' · '+rotuloQualidade(l.coeficiente.qualidade):'—'}),null)});}
 linha('mais',t('ea.aba.projetos'),es.map(e=>{const ps=projPorEmp.get(e.i)||[];return ps.length?num(ps.length)+' · '+MAT.map((m,k)=>[k,ps.filter(p=>p.mat===k).length]).filter(x=>x[1]).map(([k,n])=>rotuloMat(k)+': '+n).join(', '):'0'}));
 linha('mais',t('ea.aba.noticias'),es.map(e=>num(e.nn)),es.map(e=>e.nn));
 // registros declarados que não entram na tabela (guidance, capacidade, meta, embarque, venda, consolidado fora de Goiás, trimestre...)
 const fora=es.flatMap((e,k)=>reg[k].filter(p=>!naTabelaDeclarada(p)).map(p=>({e,p,motivo:motivoForaDaTabela(p)})));
 return {linhas:L_,cortes,fora};}
const rotuloGrupoCmp=g=>({id:t('ea.cmp.g.id'),terr:t('ea.cmp.g.terr'),cfem:t('ea.cmp.g.cfem'),ccee:t('ea.cmp.g.ccee'),est:t('ea.cmp.g.est'),dec:t('ea.cmp.g.dec'),coef:t('ea.cmp.g.coef'),mais:t('ea.cmp.g.mais')}[g]);
const maiorDaLinha=(l,n)=>!l.raw||n<2?-1:XP().indiceMaior(l.raw,{meses:l.meses||null});
function comparar(){
 el('ea-cmp-n').hidden=!S.cmp.length;el('ea-cmp-n').textContent=S.cmp.length?String(S.cmp.length):'';
 const corpo=el('ea-cmp-corpo'),es=S.cmp.map(i=>porI.get(i));
 // três vagas: quem está na comparação (com ×) e, nas vazias, o atalho para a empresa selecionada
 const addSel=S.sel!==null&&!S.cmp.includes(S.sel)?porI.get(S.sel):null;
 el('ea-cmp-slots').innerHTML=[0,1,2].map(k=>{const e=es[k];
  if(e)return `<div class="ea-slot"><span class="ea-slot-n">${k+1}</span><div class="ea-slot-nome"><button type="button" class="link-button ea-cmp-nome" data-cmp-sel="${e.i}" title="${escape(t('ea.cmpAbrirDossie'))}">${escape(e.nome)}</button><small>${escape(cnpjFmt(e.cnpj))}${e.grupo?' · '+escape(e.grupo):''}</small></div>`
   +`<button type="button" class="ea-x" data-cmp-rm="${e.i}" aria-label="${escape(t('ea.cmpRemoverNome',{nome:e.nome}))}" title="${escape(t('ea.cmpRemover'))}">×</button></div>`;
  return `<div class="ea-slot vazio"><span class="ea-slot-n">${k+1}</span>${k===es.length?(addSel?`<button type="button" class="link-button" data-add-sel>+ ${escape(t('ea.cmpAddSelCurto',{nome:addSel.nome}))}</button>`:`<span class="muted">${escape(t('ea.cmp.slotVazio'))}</span>`):''}</div>`}).join('')
  +(es.length>=CMP_MAX?`<p class="mk-note ea-cmp-cheia">${escape(t('ea.cmpCheia',{n:String(CMP_MAX)}))}</p>`:'');
 el('ea-cmp-add-box').hidden=es.length>=CMP_MAX;
 el('ea-cmp-slots').querySelectorAll('[data-cmp-rm]').forEach(b=>b.onclick=()=>alternarComparacao(+b.dataset.cmpRm));
 el('ea-cmp-slots').querySelectorAll('[data-cmp-sel]').forEach(b=>b.onclick=()=>{selecionar(+b.dataset.cmpSel,{origem:'comparar',semHistorico:true});mostrarArea('dossie')});
 const bs=el('ea-cmp-slots').querySelector('[data-add-sel]');if(bs)bs.onclick=()=>alternarComparacao(S.sel);
 const vazia=!S.cmp.length;el('ea-cmp-csv').disabled=vazia;el('ea-cmp-xlsx').disabled=vazia;
 if(vazia){corpo.innerHTML=`<div class="ea-vazio-cmp"><p>${escape(t('ea.cmpVazio'))}</p></div>`;return}
 const {linhas:ls,cortes,fora}=linhasComparacao(es),per=S.per.join('–'),nc=es.length+1;
 const porGrupo=[];ls.forEach(l=>{const g=porGrupo[porGrupo.length-1];if(g&&g.g===l.grupo)g.ls.push(l);else porGrupo.push({g:l.grupo,ls:[l]})});
 const celula=(v,k,mx)=>`<td class="num${k===mx?' ea-max':''}">${v==='—'?'<span class="muted">—</span>':escape(v)}</td>`;
 corpo.innerHTML=`<p class="mk-note ea-cmp-escopo">${escape(t('ea.cmp.escopoNota',{per}))}</p>`
  +`<div class="table-wrap"><table class="pn-table ea-cmp-tab"><thead><tr><th scope="col"><span class="sr-only">${escape(t('ea.cmp.indicador'))}</span></th>${es.map(e=>`<th scope="col">${escape(e.nome)}</th>`).join('')}</tr></thead>`
  +porGrupo.map(({g,ls:gl})=>{const c=cortes[g];
   return `<tbody><tr class="ea-cmp-grupo"><th colspan="${nc}" scope="colgroup">${escape(rotuloGrupoCmp(g))}</th></tr>`
    +gl.map(l=>{const mx=maiorDaLinha(l,es.length);
     return `<tr><th scope="row">${escape(l.rot)}${l.nota?`<span class="ea-cmp-nota">${escape(l.nota)}</span>`:''}</th>${l.vals.map((v,k)=>celula(v,k,mx)).join('')}</tr>`}).join('')
    +(c?`<tr class="ea-cmp-corte"><td colspan="${nc}"><span>${escape(t('ea.cmp.mostrando',{v:num(c.n),n:num(c.total)}))}</span> <button type="button" class="link-button" data-cmp-tudo="${g}" aria-expanded="${c.aberto}">${escape(c.aberto?t('ea.cmp.mostrarMenos'):t('ea.cmp.mostrarTodas'))}</button></td></tr>`:'')
    +`</tbody>`}).join('')
  +`</table></div>`
  +(fora.length?`<details class="ea-cmp-fora"><summary>${escape(t('ea.cmp.foraT',{n:num(fora.length)}))}</summary><p class="mk-note">${escape(t('ea.cmp.foraS'))}</p>`
   +`<div class="table-wrap"><table class="pn-table"><thead><tr><th>${escape(t('es.h.empresa'))}</th><th>${escape(t('ea.th.periodo'))}</th><th>${escape(t('ea.th.mineral'))}</th><th class="num">${escape(t('ea.th.valor'))}</th><th>${escape(t('ea.th.medida'))}</th><th>${escape(t('ea.cmp.foraMotivo'))}</th><th>${escape(t('ea.th.fonte'))}</th></tr></thead><tbody>`
   +fora.map(({e,p,motivo})=>`<tr><td>${escape(e.nome)}</td><td>${escape(p.periodo)}</td><td>${escape(p.mineral||'—')}<div class="mk-note">${escape(p.produto||'')}${p.nivel==='operacao'?' · '+escape(p.operacao):''}</div></td>`
    +`<td class="num"><b>${escape(num(p.valor))}${p.valor_max!=null?'–'+escape(num(p.valor_max)):''}</b> ${escape(p.unidade)}</td><td>${escape(rotuloMedida(p.medida))}<div class="mk-note">${escape(rotuloEscopo(p.escopo))}</div></td>`
    +`<td><span class="pill">${escape(motivo)}</span><div class="mk-note">${escape(rotuloTipoValor(p.tipo_valor))} · ${escape(t('ea.conf'))}: ${escape(rotuloConf(p.confianca))}</div></td>`
    +`<td>${p.fonte_url?`<a href="${escape(urlSegura(p.fonte_url))}" target="_blank" rel="noopener noreferrer">${escape(p.fonte_nome||t('ea.verFonte'))} ↗</a>`:escape(p.fonte_nome||'—')}</td></tr>`).join('')
   +`</tbody></table></div></details>`:'')
  +`<p class="mk-note">${escape(t('ea.cmpNotaMax'))} ${escape(t('ea.cmpNota'))}</p>`;
 corpo.querySelectorAll('[data-cmp-tudo]').forEach(b=>b.onclick=()=>{const g=b.dataset.cmpTudo;if(S.cmpTudo.has(g))S.cmpTudo.delete(g);else S.cmpTudo.add(g);comparar();
  const n=el('ea-cmp-corpo').querySelector(`[data-cmp-tudo="${g}"]`);if(n)n.focus({preventScroll:true})});
 el('ea-cmp-csv').onclick=()=>exportarComparacao('csv');el('ea-cmp-xlsx').onclick=()=>exportarComparacao('xlsx');}

// ------------------------------------------------------------------ exportação: o que está na tela, com tipos (EmpresasExportar)
// Mesmos filtros = mesmos números na tela e no arquivo. Cada linha leva o recorte (período, filtros) e a data do pacote; contagens
// "_no_recorte" seguem os filtros e "_empresa_total" são da empresa inteira. Lacuna sai vazia (CCEE de quem não é agente, por exemplo).
function baixar(nome,conteudo,tipo){const url=URL.createObjectURL(new Blob([conteudo],{type:tipo}));const a=document.createElement('a');a.href=url;a.download=nome;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
const TIPO_XLSX='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const cols=pares=>pares.map(([id,tipo,largura])=>({id,tipo,largura}));
const COLS_RECORTE=[['periodo_inicio','inteiro'],['periodo_fim','inteiro'],['filtro_municipio','texto'],['filtro_municipio_ibge','id',9],['filtro_mineral','texto'],['filtro_fase','texto'],
 ['filtro_dado','texto'],['filtro_busca','texto'],['ordem','texto'],['data_pacote','texto',12]];
function recorteAtual(){const f=S.f;return {periodo_inicio:S.per[0],periodo_fim:S.per[1],filtro_municipio:f.mun!==''?D.dims.mun[+f.mun][1]:null,filtro_municipio_ibge:f.mun!==''?ibgeDe(+f.mun):null,
 filtro_mineral:f.min!==''?D.dims.min[+f.min][0]:null,filtro_fase:f.grupo||null,filtro_dado:f.dado||null,filtro_busca:el('ea-busca').value.trim()||null,ordem:f.ordem,data_pacote:D.meta.built_on}}
// descrição de cada coluna (aba "Colunas" da planilha e "colunas" do JSON)
const descColunas=()=>({posicao:t('ea.col.posicao'),posicao_cfem:t('ea.col.posicao_cfem'),cnpj_raiz:t('ea.col.cnpj_raiz'),empresa:t('ea.col.empresa'),grupo:t('ea.col.grupo'),
 cfem_periodo_rs:t('ea.col.cfem_periodo_rs'),cfem_periodo_empresa_total_rs:t('ea.col.cfem_periodo_empresa_total_rs'),puxador_80pct_cfem:t('ea.col.puxador_80pct_cfem'),
 processos_no_recorte:t('ea.col.processos_no_recorte'),lavra_autorizada_no_recorte:t('ea.col.fase_no_recorte'),requerimento_lavra_no_recorte:t('ea.col.fase_no_recorte'),
 pesquisa_no_recorte:t('ea.col.fase_no_recorte'),disponibilidade_no_recorte:t('ea.col.fase_no_recorte'),area_ha_no_recorte:t('ea.col.area_ha_no_recorte'),
 fase_mais_avancada:t('ea.col.fase_mais_avancada'),processos_empresa_total:t('ea.col.empresa_total'),lavra_autorizada_empresa_total:t('ea.col.empresa_total'),
 area_ha_empresa_total:t('ea.col.empresa_total'),ccee_mwh_agente_periodo:t('ea.col.ccee_mwh_agente_periodo'),ccee_meses_observados_periodo:t('ea.col.ccee_meses'),
 metrica:t('ea.col.metrica'),valor_metrica:t('ea.col.valor_metrica'),unidade_metrica:t('ea.col.unidade_metrica'),producao_declarada:t('ea.col.producao_declarada'),
 projetos_vinculados:t('ea.col.projetos_vinculados'),noticias_vinculadas:t('ea.col.noticias_vinculadas'),ponto_processo_referencia:t('ea.col.ponto'),
 ponto_lat_indicativo:t('ea.col.ponto'),ponto_lon_indicativo:t('ea.col.ponto'),periodo_inicio:t('ea.col.periodo'),periodo_fim:t('ea.col.periodo'),
 filtro_municipio:t('ea.col.filtro'),filtro_municipio_ibge:t('ea.col.filtro_municipio_ibge'),municipios_ibge:t('ea.col.municipios_ibge'),filtro_mineral:t('ea.col.filtro'),filtro_fase:t('ea.col.filtro'),filtro_dado:t('ea.col.filtro'),filtro_busca:t('ea.col.filtro'),
 ordem:t('ea.col.ordem'),data_pacote:t('ea.col.data_pacote'),
 empresa_ordem:t('ea.col.empresa_ordem'),grupo_indicador:t('ea.col.grupo_indicador'),indicador:t('ea.col.indicador'),periodo:t('ea.col.periodo_registro'),
 mineral:t('ea.col.mineral'),produto:t('ea.col.produto'),medida:t('ea.col.medida'),base_calculo:t('ea.col.base_calculo'),escopo:t('ea.col.escopo'),
 tipo_valor:t('ea.col.tipo_valor'),nivel:t('ea.col.nivel'),operacao:t('ea.col.operacao'),valor:t('ea.col.valor'),valor_max:t('ea.col.valor_max'),unidade:t('ea.col.unidade'),
 meses_observados:t('ea.col.meses_observados'),valor_anualizado:t('ea.col.valor_anualizado'),qualidade:t('ea.col.qualidade'),confianca:t('ea.col.confianca'),
 status_validacao:t('ea.col.status_validacao'),na_tabela:t('ea.col.na_tabela'),observacao:t('ea.col.observacao'),fonte:t('ea.col.fonte'),fonte_url:t('ea.col.fonte_url'),
 periodo_escolhido:t('ea.col.periodo_escolhido'),tipo_registro:t('ea.col.tipo_registro')});
const metaComum=()=>[['gerado_em',new Date().toISOString()],['fonte',t('ea.exp.fontePublica')],['data_pacote',D.meta.built_on],['formato_csv',t('ea.exp.formatoCsv')],
 ['formato_xlsx',t('ea.exp.formatoXlsx')]];
const metaRecorte=()=>{const r=recorteAtual();return [['periodo',S.per.join('-')],['filtro_municipio',r.filtro_municipio],['filtro_municipio_ibge',r.filtro_municipio_ibge],
 ...(r.filtro_municipio?[['aviso_municipio',t('ea.exp.avisoMunicipio')]]:[]),['filtro_mineral',r.filtro_mineral],
 ['filtro_fase',r.filtro_fase],['filtro_dado',r.filtro_dado],['filtro_busca',r.filtro_busca],['ordem',r.ordem],['empresas_no_recorte',S.universo.length]]};
const regrasMeta=()=>[['regra_top_n',D.meta.regras.top_n],['regra_puxadores',D.meta.regras.puxadores],['regra_cfem',D.meta.regras.cfem],['regra_ponto_empresa',D.meta.regras.ponto_empresa],
 ['aviso_ccee',t('ea.col.ccee_mwh_agente_periodo')],['aviso_fase_cfem',t('ea.exp.avisoFaseCfem')]];
function emitir(nome,formato,tabela,{abaNome,extras=[],meta=[],json,chave='linhas'}={}){
 const X_=XP();
 if(formato==='csv')return baixar(nome+'.csv',X_.csv(tabela),'text/csv;charset=utf-8');
 if(formato==='xlsx')return baixar(nome+'.xlsx',X_.xlsx([{nome:abaNome||'Dados',...tabela},...extras,{nome:'Colunas',...X_.dicionario(tabela.colunas,descColunas())},
  {nome:'Metadados',...X_.metadados([...metaComum(),...meta])}]),TIPO_XLSX);
 const d=descColunas();
 baixar(nome+'.json',JSON.stringify({...json,colunas:Object.fromEntries(tabela.colunas.map(c=>[c.id,{tipo:c.tipo,descricao:d[c.id]||''}])),[chave]:tabela.linhas},null,1),'application/json');}

const COLS_EMPRESAS=[['posicao','inteiro',8],['posicao_cfem','inteiro',8],['cnpj_raiz','id',11],['empresa','texto',44],['grupo','texto',22],
 ['cfem_periodo_rs','numero',16],['cfem_periodo_empresa_total_rs','numero',16],['puxador_80pct_cfem','bool'],
 ['processos_no_recorte','inteiro'],['lavra_autorizada_no_recorte','inteiro'],['requerimento_lavra_no_recorte','inteiro'],['pesquisa_no_recorte','inteiro'],
 ['disponibilidade_no_recorte','inteiro'],['area_ha_no_recorte','numero'],['fase_mais_avancada','texto',18],
 ['processos_empresa_total','inteiro'],['lavra_autorizada_empresa_total','inteiro'],['area_ha_empresa_total','numero'],
 ['ccee_mwh_agente_periodo','numero'],['ccee_meses_observados_periodo','inteiro'],['metrica','texto',10],['valor_metrica','numero'],['unidade_metrica','texto',10],
 ['producao_declarada','bool'],['projetos_vinculados','inteiro'],['noticias_vinculadas','inteiro'],
 ['ponto_processo_referencia','id',14],['ponto_lat_indicativo','numero'],['ponto_lon_indicativo','numero'],...COLS_RECORTE];
function tabelaRecorte(){
 const R=D.processos.rows,rec=recorteAtual(),m=S.f.metrica,un={cfem:'R$',processos:'processos',area:'ha',ccee:'MWh'}[m];
 const posCfem=new Map(S.universo.filter(l=>l.cf>0).sort((a,b)=>b.cf-a.cf).map((l,j)=>[l.e.i,j+1]));
 const fase=(ks,g)=>ks.filter(k=>D.dims.fase[R[k][PC.fase]].grupo===g).length,area=ks=>r2(ks.reduce((s,k)=>s+(R[k][PC.area_ha]||0),0));
 return {colunas:cols(COLS_EMPRESAS),linhas:S.ranking.map((l,j)=>{const e=l.e,tod=procsPorEmp.get(e.i)||[],cc=cceePeriodo(e,S.per);
  return {posicao:j+1,posicao_cfem:posCfem.get(e.i)??null,cnpj_raiz:e.cnpj,empresa:e.nome,grupo:e.grupo||null,
   cfem_periodo_rs:r2(l.cf),cfem_periodo_empresa_total_rs:r2(cfemPeriodo(e.i,{mun:'',min:''},S.per)),puxador_80pct_cfem:S.puxadores.has(e.i),
   processos_no_recorte:l.ps.length,lavra_autorizada_no_recorte:fase(l.ps,'lavra_autorizada'),requerimento_lavra_no_recorte:fase(l.ps,'requerimento_lavra'),
   pesquisa_no_recorte:fase(l.ps,'pesquisa'),disponibilidade_no_recorte:fase(l.ps,'disponibilidade'),area_ha_no_recorte:area(l.ps),
   fase_mais_avancada:l.ps.length?GRUPOS[l.gi]:null,processos_empresa_total:tod.length,lavra_autorizada_empresa_total:fase(tod,'lavra_autorizada'),area_ha_empresa_total:area(tod),
   ccee_mwh_agente_periodo:cc.meses?r2(cc.mwh):null,ccee_meses_observados_periodo:cc.meses||null,
   metrica:m,valor_metrica:m==='ccee'&&!cc.meses?null:r2(l.v),unidade_metrica:un,
   producao_declarada:!!e.enr,projetos_vinculados:e.np,noticias_vinculadas:e.nn,
   ponto_processo_referencia:e.pt>=0?R[e.pt][PC.processo]:null,ponto_lat_indicativo:e.pt>=0?R[e.pt][PC.lat]:null,ponto_lon_indicativo:e.pt>=0?R[e.pt][PC.lon]:null,...rec}})};}
const COLS_PROJETOS=[['projeto','texto',36],['empresas','texto',36],['cnpj_raiz','id',20],['maturidade','texto',14],['fase','texto',18],['mineral','texto',16],['municipio','texto',18],
 ['vinculo','texto',16],['confianca','texto',10],['localizacao','texto',22],['lat_indicativa','numero'],['lon_indicativa','numero'],['tipo_registro','texto',20],['fonte','texto',24],['link','texto',40],...COLS_RECORTE];
function tabelaProjetos(){
 const rec=recorteAtual();
 return {colunas:cols(COLS_PROJETOS),linhas:S.projetos.map(p=>{const q=MPJ.pos.get(p.j),ll=q!==undefined?L.CRS.EPSG3857.pointToLatLng(L.point(MPJ.x[q],MPJ.y[q]),0):null;
  return {projeto:p.nome,empresas:p.e.map(i=>porI.get(i).nome).join(' | ')||null,cnpj_raiz:p.e.map(i=>porI.get(i).cnpj).join(' | ')||null,maturidade:p.maturidade||null,fase:p.fase||null,
   mineral:p.mineral||null,municipio:p.mun||null,vinculo:p.metodo||null,confianca:p.conf||null,
   localizacao:p.loc?p.loc.t==='p'?'centroide_processo_anm':'referencia_municipio':'sem_localizacao',lat_indicativa:ll?+ll.lat.toFixed(5):null,lon_indicativa:ll?+ll.lng.toFixed(5):null,
   tipo_registro:rotFonte(p.fonte),fonte:p.fonte_nome||null,link:p.link||null,...rec}})};}
function exportarRecorte(formato){
 const per=S.per.join('-');
 if(S.modo==='projetos')return emitir(`minera-goias-projetos-${per}`,formato==='json'?'csv':formato,tabelaProjetos(),{abaNome:'Projetos',meta:[...metaRecorte(),['aviso_localizacao',t('ea.csvProjCab')]]});
 const tab=tabelaRecorte();
 emitir(`minera-goias-empresas-${per}`,formato,tab,{abaNome:'Empresas',meta:[...metaRecorte(),...regrasMeta()],
  json:{gerado_em:new Date().toISOString(),fonte:t('ea.exp.fontePublica'),pacote:D.meta.built_on,recorte:recorteAtual(),universo:S.universo.length,
   regras:{top_n:D.meta.regras.top_n,puxadores:D.meta.regras.puxadores,cfem:D.meta.regras.cfem,ponto_empresa:D.meta.regras.ponto_empresa}},chave:'empresas'});}

// comparação: formato longo (uma linha por empresa × indicador × período), com TODAS as linhas elegíveis — inclusive as que a tabela
// encolhe ou deixa de fora (guidance, capacidade, consolidado...), cada uma dizendo se está na tabela e por quê
const COLS_CMP=[['empresa_ordem','inteiro',8],['cnpj_raiz','id',11],['empresa','texto',36],['grupo_indicador','texto',18],['indicador','texto',24],['periodo','texto',10],
 ['mineral','texto',16],['produto','texto',28],['medida','texto',18],['base_calculo','texto',14],['escopo','texto',18],['tipo_valor','texto',12],['nivel','texto',10],['operacao','texto',24],
 ['valor','numero',14],['valor_max','numero'],['unidade','texto',10],['meses_observados','inteiro'],['valor_anualizado','numero'],['qualidade','texto',16],['confianca','texto',10],
 ['status_validacao','texto',14],['na_tabela','bool'],['observacao','texto',40],['fonte','texto',30],['fonte_url','texto',40],['periodo_escolhido','texto',10],['data_pacote','texto',12]];
function tabelaComparacao(es){
 const A=window.EmpresasAnalises,linhas=[],per=S.per.join('-'),{linhas:vis}=linhasComparacao(es,{tudo:true});
 const add=(k,e,o)=>linhas.push({empresa_ordem:k+1,cnpj_raiz:e.cnpj,empresa:e.nome,na_tabela:true,...o,periodo_escolhido:per,data_pacote:D.meta.built_on});
 es.forEach((e,k)=>{
  const anm={fonte:t('ea.exp.fonteAnm'),unidade:'processos',grupo_indicador:'territorio'};
  add(k,e,{...anm,indicador:'processos',valor:e.n});
  add(k,e,{...anm,indicador:'area_titulos',valor:r2(e.area),unidade:'ha'});
  GRUPOS.slice(0,4).forEach(g=>add(k,e,{...anm,indicador:'processos_'+g,valor:e.grupos[g]||0}));
  const mo=munsPorOrigem(e),nm=ks=>ks.map(m=>D.dims.mun[m][1]).join(' | ')||null;
  add(k,e,{...anm,indicador:'municipios_operacao_documentada',valor:mo.op.length,unidade:'municipios',observacao:nm(mo.op),fonte:t('ea.exp.fonteOperacao')});
  add(k,e,{...anm,indicador:'municipios_direitos_vigentes',valor:mo.vig.length,unidade:'municipios',observacao:nm(mo.vig)});
  add(k,e,{...anm,indicador:'municipios_so_disponibilidade',valor:mo.disp.length,unidade:'municipios',observacao:nm(mo.disp)});
  add(k,e,{grupo_indicador:'cfem',indicador:'municipios_so_cfem',valor:mo.cfem.length,unidade:'municipios',observacao:nm(mo.cfem),fonte:t('ea.exp.fonteCfem')});
  add(k,e,{grupo_indicador:'cfem',indicador:'puxador_80pct_cfem',periodo:per,valor:S.puxadores.has(e.i)?1:0,unidade:'1 = sim',observacao:t('ea.exp.puxadorObs'),fonte:t('ea.exp.fonteCfem')});
  Object.entries(e.cfem).sort().forEach(([a,v])=>add(k,e,{grupo_indicador:'cfem',indicador:'cfem_ano',periodo:a,valor:r2(v),unidade:'R$ correntes',fonte:t('ea.exp.fonteCfem'),
   observacao:a==='2026'?t('ea.parcial2026',{meses:String(D.meta.meses_cfem_2026.length)}):null}));
  add(k,e,{grupo_indicador:'cfem',indicador:'cfem_periodo',periodo:per,valor:r2(cfemPeriodo(e.i,{mun:'',min:''},S.per)),unidade:'R$ correntes',fonte:t('ea.exp.fonteCfem')});
  Object.entries(e.ccee).sort().forEach(([a,v])=>{const l=vis.find(x=>x.grupo==='ccee'&&x.rot.endsWith(' '+a));
   add(k,e,{grupo_indicador:'ccee',indicador:'ccee_carga_agente',periodo:a,valor:r2(v.obs),unidade:'MWh',meses_observados:v.meses,valor_anualizado:r2(v.anual),
    qualidade:v.q||null,observacao:[t('ea.exp.cceeObs'),l&&l.nota?l.nota:''].filter(Boolean).join(' '),fonte:t('ea.exp.fonteCcee')})});
  if(A)A.estimadaDe(e.cnpj).forEach(l=>add(k,e,{grupo_indicador:'producao_estimada',indicador:'producao_estimada_amb_cfem',periodo:String(l.ano),mineral:l.mineral,base_calculo:l.base,
   valor:l.producao_t,unidade:'t',qualidade:'estimativa',observacao:t('ea.csvEstimada'),fonte:t('ea.exp.fonteEstimada'),fonte_url:l.publicado_url||null}));
  const det=D.detalhes[String(e.i)];
  (det?det.producao:[]).forEach(p=>{const mot=motivoForaDaTabela(p);
   add(k,e,{grupo_indicador:'producao_declarada',indicador:'producao_declarada',periodo:String(p.periodo),mineral:p.mineral||null,produto:p.produto||null,medida:p.medida||null,
    escopo:p.escopo||null,tipo_valor:p.tipo_valor||null,nivel:p.nivel||null,operacao:p.operacao||null,valor:p.valor,valor_max:p.valor_max??null,unidade:p.unidade,
    confianca:p.confianca||null,status_validacao:p.status_validacao||null,na_tabela:!mot,observacao:mot?t('ea.exp.foraTabela',{motivo:mot}):(p.observacao||null),
    fonte:p.fonte_nome||null,fonte_url:p.fonte_url||null})});
  if(A)A.declaradaDe(e.cnpj).filter(l=>l.coeficiente).forEach(l=>{const c=l.coeficiente,en=l.energia||{};
   add(k,e,{grupo_indicador:'coeficiente',indicador:'coeficiente_energia',periodo:String(l.ano),mineral:l.mineral||null,produto:l.producao&&l.producao.produto||null,
    medida:l.producao&&l.producao.medida||null,valor:c.valor,unidade:c.unidade,meses_observados:en.meses_observados??null,qualidade:c.qualidade||null,
    observacao:t('ea.exp.coefObs',{base:c.base_do_rateio||'—',exclusiva:c.energia_exclusiva?t('ea.exp.sim'):t('ea.exp.nao'),
     origem:l.producao?(l.producao.origem==='declarada_anual'?t('ep.origem.declarada_anual'):t('ep.origem.anualizada_de_parciais')+' ('+(l.producao.periodos||[]).join(', ')+')'):'—'}),fonte:t('ea.exp.fonteCoef')})});
  add(k,e,{grupo_indicador:'mais',indicador:'projetos_vinculados',valor:(projPorEmp.get(e.i)||[]).length,unidade:'projetos'});
  add(k,e,{grupo_indicador:'mais',indicador:'noticias_vinculadas',valor:e.nn,unidade:'noticias'});});
 return {colunas:cols(COLS_CMP),linhas};}
// a tabela da tela, larga, com os números brutos (para leitura na planilha)
function tabelaComparacaoLarga(es){
 const {linhas:ls}=linhasComparacao(es,{tudo:true}),nomes=es.map(e=>`${e.nome} (${cnpjFmt(e.cnpj)})`);
 return {colunas:[{id:'grupo',tipo:'texto',largura:28},{id:'indicador',tipo:'texto',largura:56},...nomes.map(n=>({id:n,tipo:'texto',largura:26})),
   ...nomes.map(n=>({id:n+' · valor',tipo:'numero',largura:18})),{id:'maior_valor',tipo:'texto',largura:30},{id:'observacao',tipo:'texto',largura:50}],
  linhas:ls.map(l=>{const mx=maiorDaLinha(l,es.length),o={grupo:rotuloGrupoCmp(l.grupo),indicador:l.rot,maior_valor:mx>=0?es[mx].nome:null,observacao:l.nota||null};
   nomes.forEach((n,k)=>{o[n]=l.vals[k]==='—'?null:l.vals[k];o[n+' · valor']=l.raw?l.raw[k]:null});return o})};}
function exportarComparacao(formato){
 const es=S.cmp.map(i=>porI.get(i));if(!es.length)return;
 const nome=`minera-goias-comparacao-${es.map(e=>e.cnpj).join('-')}`;
 emitir(nome,formato,tabelaComparacao(es),{abaNome:'Dados',extras:[{nome:'Tabela',...tabelaComparacaoLarga(es)}],
  meta:[['empresas',es.map(e=>`${e.cnpj} ${e.nome}`).join(' | ')],['periodo_escolhido',S.per.join('-')],['escopo',t('ea.cmp.escopoNota',{per:S.per.join('–')})],
   ['destaque',t('ea.cmpNotaMax')],['notas',t('ea.cmpNota')]]});}

const COLS_PROC=[['processo','id',14],['empresa','texto',36],['cnpj_raiz','id',11],['fase','texto',26],['grupo_fase','texto',18],['situacao_panorama','texto',24],['mineral','texto',16],
 ['municipios','texto',24],['municipios_ibge','texto',16],['area_ha','numero'],['cfem_2022_2026_rs','numero',16],['minas_ativas_sgb','bool'],['centroide_lat_indicativo','numero'],['centroide_lon_indicativo','numero'],['data_pacote','texto',12]];
function tabelaProcessos(e){
 const R=D.processos.rows;
 return {colunas:cols(COLS_PROC),linhas:(procsPorEmp.get(e.i)||[]).map(k=>{const r=R[k];return {processo:r[PC.processo],empresa:e.nome,cnpj_raiz:e.cnpj,
  fase:D.dims.fase[r[PC.fase]].nome,grupo_fase:D.dims.fase[r[PC.fase]].grupo,situacao_panorama:D.dims.status[r[PC.status]]!=null?rotuloStatus(r[PC.status]):null,mineral:D.dims.min[r[PC.mineral]]?D.dims.min[r[PC.mineral]][0]:null,
  municipios:r[PC.municipios].map(m=>D.dims.mun[m][1]).join(' | ')||null,municipios_ibge:r[PC.municipios].map(ibgeDe).join(' | ')||null,area_ha:r[PC.area_ha],cfem_2022_2026_rs:r[PC.cfem_2022_2026],minas_ativas_sgb:!!r[PC.minas_ativas_sgb],
  centroide_lat_indicativo:r[PC.lat],centroide_lon_indicativo:r[PC.lon],data_pacote:D.meta.built_on}})};}
function exportarProcessos(e,formato='csv'){emitir(`minera-goias-processos-${e.cnpj}`,formato,tabelaProcessos(e),{abaNome:'Processos',meta:[['empresa',`${e.cnpj} ${e.nome}`],['aviso',t('ea.exp.avisoCentroide')]]});}
function exportarFicha(){
 const e=porI.get(S.sel);if(!e)return;
 const R=D.processos.rows,A=window.EmpresasAnalises;
 baixar(`minera-goias-dossie-${e.cnpj}.json`,JSON.stringify({gerado_em:new Date().toISOString(),pacote:D.meta.built_on,regras:D.meta.regras,empresa:e,detalhes:D.detalhes[String(e.i)]||null,
  municipios_por_origem:(o=>Object.fromEntries([['operacao_documentada',o.op],['direitos_vigentes',o.vig],['so_disponibilidade',o.disp],['so_cfem',o.cfem]]
   .map(([c,ks])=>[c,ks.map(m=>({ibge:ibgeDe(m),municipio:D.dims.mun[m][1]}))])))(munsPorOrigem(e)),
  processos:(procsPorEmp.get(e.i)||[]).map(k=>Object.fromEntries(D.processos.cols.map((c,j)=>[c,c==='fase'?D.dims.fase[R[k][j]].nome:c==='mineral'?(D.dims.min[R[k][j]]||[''])[0]:c==='municipios'?R[k][j].map(m=>D.dims.mun[m][1]):c==='status'?rotuloStatus(R[k][j]):c==='uso'?D.dims.uso[R[k][j]]:R[k][j]]))),
  producao_estimada_amb_cfem:{aviso:t('ea.csvEstimada'),linhas:A?A.estimadaDe(e.cnpj):[]},
  producao_declarada_e_energia:A?A.declaradaDe(e.cnpj):[],
  projetos:projPorEmp.get(e.i)||[],noticias:newsPorEmp.get(e.i)||[]},null,1),'application/json');}
// Dossiê em planilha: uma aba por assunto, todas com fonte e unidade; para o consultor montar tabelas e gráficos sem redigitar
function exportarFichaXlsx(){
 const e=porI.get(S.sel);if(!e)return;
 const A=window.EmpresasAnalises,X_=XP(),det=D.detalhes[String(e.i)],dp=D.meta.built_on;
 const anos=[...new Set([...Object.keys(e.cfem),...Object.keys(e.ccee)])].sort();
 const abaAnos={colunas:cols([['ano','inteiro',8],['cfem_rs','numero',16],['cfem_parcial','bool'],['ccee_mwh_observado','numero',18],['ccee_meses_observados','inteiro'],
  ['ccee_mwh_anualizado','numero',18],['ccee_qualidade','texto',16],['data_pacote','texto',12]]),
  linhas:anos.map(a=>({ano:+a,cfem_rs:e.cfem[a]!=null?r2(e.cfem[a]):null,cfem_parcial:a==='2026',ccee_mwh_observado:e.ccee[a]?r2(e.ccee[a].obs):null,
   ccee_meses_observados:e.ccee[a]?e.ccee[a].meses:null,ccee_mwh_anualizado:e.ccee[a]?r2(e.ccee[a].anual):null,ccee_qualidade:e.ccee[a]?e.ccee[a].q||null:null,data_pacote:dp}))};
 const abaDec={colunas:cols([['periodo','texto',10],['periodo_tipo','texto',10],['mineral','texto',16],['produto','texto',28],['medida','texto',18],['escopo','texto',18],['tipo_valor','texto',12],
  ['nivel','texto',10],['operacao','texto',28],['valor','numero',14],['valor_max','numero'],['unidade','texto',8],['confianca','texto',10],['status_validacao','texto',14],
  ['compara_na_aba_comparar','bool'],['fonte','texto',36],['fonte_url','texto',40],['observacao','texto',30],['id_registro','id',10]]),
  linhas:(det?det.producao:[]).map(p=>({periodo:String(p.periodo),periodo_tipo:p.periodo_tipo||null,mineral:p.mineral||null,produto:p.produto||null,medida:p.medida||null,escopo:p.escopo||null,
   tipo_valor:p.tipo_valor||null,nivel:p.nivel||null,operacao:p.operacao||null,valor:p.valor,valor_max:p.valor_max??null,unidade:p.unidade,confianca:p.confianca||null,
   status_validacao:p.status_validacao||null,compara_na_aba_comparar:naTabelaDeclarada(p),fonte:p.fonte_nome||null,fonte_url:p.fonte_url||null,observacao:p.observacao||null,id_registro:p.id||null}))};
 const est=A?A.estimadaDe(e.cnpj):[];
 const abaEst={colunas:cols([['ano','inteiro',8],['mineral','texto',18],['base','texto',14],['producao_t','numero',16],['parcela_do_estado','numero'],['cfem_rs','numero',16],
  ['publicado_t','numero',14],['diferenca_vs_publicado','numero'],['publicado_fonte','texto',30],['publicado_url','texto',40],['energia_mwh','numero'],['coeficiente_mwh_t','numero'],['aviso','texto',60]]),
  linhas:est.map(l=>({ano:l.ano,mineral:l.mineral,base:l.base,producao_t:l.producao_t,parcela_do_estado:l.parcela_do_estado,cfem_rs:l.cfem_brl,publicado_t:l.publicado_t,
   diferenca_vs_publicado:l.diferenca_vs_publicado,publicado_fonte:l.publicado_fonte||null,publicado_url:l.publicado_url||null,energia_mwh:l.energia_mwh,
   coeficiente_mwh_t:l.coeficiente_mwh_t===''?null:l.coeficiente_mwh_t,aviso:t('ea.csvEstimada')}))};
 const dec=A?A.declaradaDe(e.cnpj):[];
 const abaEnergia={colunas:cols([['ano','inteiro',8],['mineral','texto',16],['producao','numero',14],['producao_unidade','texto',10],['producao_produto','texto',24],
  ['energia_mwh_observado','numero',16],['energia_meses_observados','inteiro'],['energia_mwh_anualizado','numero',16],['energia_qualidade','texto',14],['base_do_rateio','texto',16],
  ['parcela_da_empresa','numero'],['coeficiente','numero'],['coeficiente_unidade','texto',10],['coeficiente_qualidade','texto',14],['energia_exclusiva','bool']]),
  linhas:dec.map(l=>{const p=l.producao||{},en=l.energia||{},c=l.coeficiente||{};return {ano:l.ano,mineral:l.mineral||null,producao:p.valor??null,producao_unidade:p.unidade||null,
   producao_produto:p.produto||null,energia_mwh_observado:en.mwh_empresa_observado??en.mwh_observado??null,energia_meses_observados:en.meses_observados??null,
   energia_mwh_anualizado:en.mwh_empresa_anualizado??en.mwh_anualizado??null,energia_qualidade:en.qualidade||null,base_do_rateio:en.base_do_rateio||null,parcela_da_empresa:en.parcela_da_empresa??null,
   coeficiente:c.valor??null,coeficiente_unidade:c.unidade||null,coeficiente_qualidade:c.qualidade||null,energia_exclusiva:c.energia_exclusiva??null}})};
 const abaProj={colunas:cols([['projeto','texto',34],['maturidade','texto',14],['fase','texto',18],['mineral','texto',16],['municipio','texto',18],['capacidade','texto',14],['capacidade_unidade','texto',12],
  ['capex','texto',12],['moeda','texto',6],['ano_capex','texto',8],['vinculo','texto',16],['confianca','texto',10],['processos','texto',30],['tipo_registro','texto',20],['fonte','texto',24],['link','texto',40]]),
  linhas:(projPorEmp.get(e.i)||[]).map(p=>({projeto:p.nome,maturidade:p.maturidade||null,fase:p.fase||null,mineral:p.mineral||null,municipio:p.mun||null,capacidade:p.capacidade??null,
   capacidade_unidade:p.cap_unidade||null,capex:p.capex??null,moeda:p.moeda||null,ano_capex:p.ano_capex??null,vinculo:p.metodo||null,confianca:p.conf||null,
   processos:(p.processos||[]).join(' | ')||null,tipo_registro:rotFonte(p.fonte),fonte:p.fonte_nome||null,link:p.link||null}))};
 const abaNews={colunas:cols([['data','texto',11],['titulo','texto',70],['veiculo','texto',20],['link','texto',40],['ligacao','texto',22],['nome_usado','texto',20],['confianca','texto',10],
  ['tipo','texto',10],['menciona_goias','bool']]),
  linhas:(newsPorEmp.get(e.i)||[]).map(n=>({data:n.d,titulo:n.t,veiculo:n.v||null,link:n.u||null,ligacao:n.metodo||null,nome_usado:n.alias||null,confianca:n.conf||null,tipo:n.tipo||null,menciona_goias:!!n.go}))};
 baixar(`minera-goias-dossie-${e.cnpj}.xlsx`,X_.xlsx([
  {nome:'Empresa',...X_.metadados([['cnpj_raiz',e.cnpj],['empresa',e.nome],['grupo',e.grupo],['aliases',(e.alias||[]).join(' | ')],['processos',e.n],['area_ha',r2(e.area)],
   // as quatro origens sempre saem (vazio = "nenhum nesta base"): a ausência também é informação
   ...(o=>{const nm=ks=>ks.map(m=>D.dims.mun[m][1]).join(' | ')||t('ea.exp.nenhumMun');
    return [['municipios_operacao_documentada',nm(o.op)],['municipios_direitos_vigentes',nm(o.vig)],['municipios_so_disponibilidade',nm(o.disp)],['municipios_so_cfem',nm(o.cfem)]]})(munsPorOrigem(e)),['minerais',minsOrdenados(e).map(m=>D.dims.min[m][0]).join(' | ')],
   ['operacoes',det?det.operacoes.join(' | '):null],['rateio_ccee',det&&det.rateio?det.rateio.nota:null],...metaComum(),['aviso_estimada',t('ea.csvEstimada')],['aviso_ccee',t('ea.exp.cceeObs')]])},
  {nome:'CFEM e CCEE',...abaAnos},{nome:'Processos',...tabelaProcessos(e)},{nome:'Produção declarada',...abaDec},{nome:'Produção estimada',...abaEst},
  {nome:'Energia e coeficiente',...abaEnergia},{nome:'Projetos',...abaProj},{nome:'Notícias',...abaNews}]),TIPO_XLSX);}

// ------------------------------------------------------------------ metodologia e fontes
function metodologia(){
 const m=D.meta,c=m.cobertura,cr=D.criticos,est=EP&&EP.estimada;
 const crit=esf=>{const x=cr[esf];return `<h4>${escape(x.nome)}</h4><p class="mk-note"><b>${escape(x.norma)}</b> · ${escape(x.jurisdicao)} · ${escape(t('ea.consultado',{d:x.consultado_em}))} · <a href="${escape(urlSegura(x.link))}" target="_blank" rel="noopener noreferrer">${escape(t('ea.textoOficial'))} ↗</a></p>`
  +`<p class="mk-note">${escape(x.situacao)}</p>`+x.categorias.map(cat=>`<p class="mk-note"><span class="ea-crit ${esf==='federal'?'fed':'est'}">${escape(cat.id)}</span> <b>${escape(cat.nome)}:</b> ${cat.itens.map(i=>escape(i.texto)+(i.min.length?'':' <span class="muted">('+escape(t('ea.semCategoria'))+')</span>')).join('; ')}</p>`).join('')
  +(x.ressalvas||[]).map(r=>`<p class="mk-note">· ${escape(r)}</p>`).join('');};
 const lp=c.projetos_localizacao||{};
 el('ea-metodo-corpo').innerHTML=`<div class="ea-cols"><section><h4>${escape(t('ea.regrasT'))}</h4>${Object.values(m.regras).map(r=>`<p class="mk-note">· ${escape(r)}</p>`).join('')}
  <h4>${escape(t('ea.metodo.estimadaT'))}</h4><p class="mk-note">${escape(est?est.metodo:t('es.semDados'))}</p><p class="mk-note">· ${escape(t('ea.metodo.estimadaLim'))}</p><p class="mk-note">· ${escape(t('ea.es.correcaoCfem'))}</p>
  <h4>${escape(t('ea.metodo.declaradaT'))}</h4>${EP?[t('ea.metodo.decFonteProd'),t('ea.metodo.decFonteEnergia')].map(f=>`<p class="mk-note">· ${escape(f)}</p>`).join('')+`<p class="mk-note">· ${escape(EP.meta.chave_de_ligacao||'')}</p>`:''}
  <h4>${escape(t('ea.avisosT'))}</h4>${m.avisos.map(a=>`<p class="mk-note">· ${escape(a)}</p>`).join('')}
  <h4>${escape(t('ea.coberturaT'))}</h4><p class="mk-note">${escape(t('ea.cobertura',{proc:num(c.processos),pj:num(c.processos_pj),pf:num(c.processos_pf_nao_nomeados),sem:num(c.processos_sem_titular),emp:num(c.empresas_indice),cfem:num(c.empresas_com_cfem),ccee:num(c.empresas_com_ccee),enr:num(c.empresas_enriquecidas),sgb:num(c.processos_em_minas_ativas_sgb)}))}</p>
  <p class="mk-note">${escape(t('ea.coberturaMapa',{ponto:num(c.empresas_com_ponto||0),emp:num(c.empresas_indice),p:num(lp.p||0),m:num(lp.m||0),s:num(lp.sem||0)}))}</p>
  <p class="mk-note">${escape(t('ea.coberturaNoticias',{acervo:num(c.noticias.acervo_deduplicado),v:num(c.noticias.vinculadas),d:num(Object.values(c.noticias.descartadas).reduce((s,x)=>s+x,0))}))}</p>
  <p class="mk-note">${escape(t('ea.coberturaProjetos',{v:num(c.projetos_vinculados),s:num(c.projetos_sem_vinculo)}))}</p></section>
  <section>${crit('federal')}${crit('estadual')}<p class="mk-note">${escape(t('ea.critSeparadas'))}</p></section></div>
  <details><summary>${escape(t('ea.descartesT'))}</summary><ul class="ea-links">${D.noticias_descartadas_exemplos.map(d=>`<li>${escape(d.d)} · ${escape(d.t)} <span class="pill">${escape(d.motivo)}</span> <span class="muted">${escape(porI.get(d.e)?porI.get(d.e).nome:'')} · “${escape(d.alias)}”</span></li>`).join('')}</ul></details>
  <p class="source-line">${escape(t('ea.fontesGerais',{data:m.built_on}))}</p>`;}

// ------------------------------------------------------------------ montagem
function preencher(select,valores,vazio){select.innerHTML=(vazio!=null?`<option value="">${escape(vazio)}</option>`:'')+valores.map(([v,r])=>`<option value="${escape(v)}">${escape(r)}</option>`).join('')}
function redesenhar(){S.nLista=LOTE;calcular();if(MP.n&&S.mapa)pontosDasEmpresas();metricas();lista();   // pontos locais antes da lista (marca "sem ponto aqui")
 legenda();desenharPontos();poligonosVisiveis();resumoSel();etiquetaMunicipio();
 if(S.area==='dossie'&&S.sel!==null)ficha();if(S.area==='comparar')comparar();if(!el('ea-ranking').hidden)ranking();}

function tablist(box,sel,ativar){box.addEventListener('keydown',ev=>{if(ev.key!=='ArrowRight'&&ev.key!=='ArrowLeft')return;
 const bs=[...box.querySelectorAll(sel)].filter(b=>!b.disabled),i=bs.findIndex(b=>b.getAttribute('aria-selected')==='true'||b.getAttribute('aria-checked')==='true');
 const n=bs[(i+(ev.key==='ArrowRight'?1:bs.length-1))%bs.length];if(!n)return;ev.preventDefault();ativar(n);n.focus()})}
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
 preencher(el('ea-metrica'),['cfem','relevancia','processos','area','ccee','nome'].map(m=>[m,rotuloMetrica(m)]));
 ['ea-min','ea-grupo','ea-ano-ini','ea-ano-fim','ea-dado','ea-metrica'].forEach(id=>el(id).onchange=redesenhar);
 // o filtro de município da lista é a mesma seleção municipal das outras portas (contorno, etiqueta, cartão)
 el('ea-mun').onchange=()=>{const k=munSel();if(k===null){S.munOrigem=null;S.verEstadual=false;if(S.foco==='municipio'||S.foco==='fechado')S.foco=null;redesenhar();gravarHash(true)}
  else selecionarMunicipio(k,{origem:'filtro'})};
 el('ea-reset').onclick=()=>{['ea-mun','ea-min','ea-grupo','ea-dado'].forEach(id=>el(id).value='');el('ea-busca').value='';S.munOrigem=null;if(S.foco==='municipio'||S.foco==='fechado')S.foco=null;
  el('ea-ano-ini').value='2022';el('ea-ano-fim').value='2025';el('ea-metrica').value='cfem';S.verEstadual=false;redesenhar();gravarHash(true);
  if(S.mapa)S.mapa.fitBounds(goBounds(),{padding:[10,10]})};
 // filtros recolhidos por padrão; as etiquetas dos filtros ativos removem um de cada vez
 el('ea-filtros-btn').onclick=()=>{const f=el('ea-filtros'),on=f.hidden;f.hidden=!on;el('ea-filtros-btn').setAttribute('aria-expanded',String(on));if(on)el('ea-mun').focus()};
 el('ea-context').onclick=ev=>{const b=ev.target.closest('[data-limpa]');if(!b)return;const id=b.dataset.limpa;
  if(id==='ea-periodo'){el('ea-ano-ini').value='2022';el('ea-ano-fim').value='2025'}else el(id).value='';
  if(id==='ea-mun'){S.munOrigem=null;S.verEstadual=false;if(S.foco==='municipio'||S.foco==='fechado')S.foco=null}
  redesenhar();if(id==='ea-mun')gravarHash(true);const prox=el('ea-context').querySelector('[data-limpa]');(prox||el('ea-filtros-btn')).focus()};
 // gaveta da lista (tablet e celular) e a mudança de largura (a busca troca de lugar, a gaveta fecha)
 el('ea-lista-btn').onclick=()=>gaveta(!el('ea-lateral').classList.contains('aberta'));
 el('ea-lat-fechar').onclick=()=>gaveta(false);el('ea-lat-fundo').onclick=()=>gaveta(false);
 largo.addEventListener('change',()=>{posicionarBusca();if(S.mapa)setTimeout(()=>S.mapa.invalidateSize(),60)});
 el('ea-ranking-btn').onclick=()=>alternarRanking();
 // Análises: detalhamento em abas (tabela, cobertura, método...) e o par Consumo × Coeficiente da produção estimada
 document.querySelectorAll('#empresas-view .ea-detalhe').forEach(sec=>{
  const tabs=[...sec.querySelectorAll('[data-det]')],ps=[...sec.querySelectorAll('[data-det-painel]')];
  tabs.forEach(b=>{b.id=`${sec.id}-tab-${b.dataset.det}`;b.setAttribute('aria-controls',`${sec.id}-p-${b.dataset.det}`)});
  ps.forEach(p=>{p.id=`${sec.id}-p-${p.dataset.detPainel}`;p.setAttribute('aria-labelledby',`${sec.id}-tab-${p.dataset.detPainel}`)});
  const ativar=b=>{tabs.forEach(x=>{const on=x===b;x.setAttribute('aria-selected',String(on));x.tabIndex=on?0:-1;x.classList.toggle('active',on)});
   ps.forEach(p=>p.hidden=p.dataset.detPainel!==b.dataset.det)};
  tabs.forEach(b=>b.onclick=()=>ativar(b));tablist(sec.querySelector('.ea-det-tabs'),'[data-det]',ativar);ativar(tabs[0])});
 el('empresas-view').addEventListener('click',ev=>{const b=ev.target.closest('[data-det-ir]');if(!b)return;
  const [pfx,painel]=b.dataset.detIr.split(':'),sec=el(pfx+'-detalhe'),tab=sec&&sec.querySelector(`[data-det="${painel}"]`);if(!tab)return;
  tab.click();sec.scrollIntoView({behavior:'smooth',block:'start'});tab.focus({preventScroll:true})});
 const lado=el('es-lado'),ativarLado=b=>{lado.querySelectorAll('[data-lado]').forEach(x=>{const on=x===b;x.setAttribute('aria-checked',String(on));x.tabIndex=on?0:-1});
  el('es-lado-energia').hidden=b.dataset.lado!=='energia';el('es-lado-coef').hidden=b.dataset.lado!=='coef'};
 lado.querySelectorAll('[data-lado]').forEach(b=>b.onclick=()=>ativarLado(b));tablist(lado,'[data-lado]',ativarLado);

 // busca: sugestões (empresa, processo, município, mineral) e, enquanto digita, o recorte do Explorar
 const busca=el('ea-busca'),cb=combobox(busca,el('ea-sugestoes'),{gerar:sugestoesBusca,escolher:escolherBusca});let timer=null;
 busca.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>{cb.abrir();redesenhar()},160)});
 // comparação: busca só de empresas
 const cbusca=el('ea-cmp-busca'),cc=combobox(cbusca,el('ea-cmp-sug'),{gerar:q=>sugestoesEmpresas(q,10),escolher:s=>{cbusca.value='';if(!S.cmp.includes(s.i))alternarComparacao(s.i)}});
 cbusca.addEventListener('input',()=>cc.abrir());
 el('ea-exp-xlsx').onclick=()=>exportarRecorte('xlsx');el('ea-exp-csv').onclick=()=>exportarRecorte('csv');el('ea-exp-json').onclick=()=>exportarRecorte('json');
 el('ea-ficha-exp').onclick=exportarFicha;el('ea-ficha-xlsx').onclick=exportarFichaXlsx;el('ea-ver-mapa').onclick=()=>verNoMapa(null);
 el('ea-cmp-add').onclick=()=>{if(S.sel!==null)alternarComparacao(S.sel)};
 el('ea-cmp-limpar').onclick=()=>{S.cmp=[];el('ea-cmp-n').hidden=true;barraSelecao();resumoSel();comparar();if(S.area==='dossie'&&S.sel!==null)ficha()};
 el('ea-so-sel').onchange=desenharPontos;el('ea-poligonos').onchange=()=>{poligonosVisiveis();if(S.tela)S.tela.repintar()};
 // opção avançada (Camadas): ligada por padrão, o clique no fundo escolhe o município; desligada, o fundo volta ao normal (o recorte fica)
 el('ea-sel-mun').onchange=()=>{esconderHover();
  const txt=t('ea.selMunDesligado');clearTimeout(S.tAvisoMun);
  if(!el('ea-sel-mun').checked){avisoMapa(txt);S.tAvisoMun=setTimeout(()=>{if(el('ea-map-aviso').textContent===txt)avisoMapa('')},5000)}
  else if(el('ea-map-aviso').textContent===txt)avisoMapa('')};
 // municípios do dossiê (cabeçalho e Perfil): clique → Explorar com o município; mouse parado ~650 ms ou foco do teclado → prévia.
 // No toque não há prévia: o toque navega direto.
 const dz=el('ea-area-dossie');
 dz.addEventListener('click',ev=>{const a=ev.target.closest('[data-mun-ibge]');if(!a)return;ev.preventDefault();irMunicipioDoDossie(kDoIbge(a.dataset.munIbge))});
 dz.addEventListener('pointerover',ev=>{const a=ev.target.closest('.ea-mun-link:not(.ea-sem-previa)');if(a&&ev.pointerType==='mouse')agendarPrevia(a)});
 dz.addEventListener('pointerout',ev=>{const a=ev.target.closest('.ea-mun-link');if(!a||(ev.relatedTarget&&a.contains(ev.relatedTarget)))return;
  if(S.tPrevia||S.previaLink===a)fecharPrevia()});
 dz.addEventListener('focusin',ev=>{const a=ev.target.closest('.ea-mun-link:not(.ea-sem-previa)');if(a&&a.matches(':focus-visible'))agendarPrevia(a)});
 dz.addEventListener('focusout',ev=>{if(ev.target.closest('.ea-mun-link'))fecharPrevia()});
 // captura: rolar a página OU um contêiner interno (a tabela do Território rola dentro de .table-wrap) fecha a prévia,
 // que é posicionada pela tela e ficaria deslocada do nome
 addEventListener('scroll',()=>{if(S.tPrevia||previaAberta())fecharPrevia()},{passive:true,capture:true});
 // navegação das áreas, dos modos do mapa e das análises (setas trocam, como numa lista de abas)
 el('ea-nav').querySelectorAll('[data-area]').forEach(b=>b.onclick=()=>mostrarArea(b.dataset.area));
 tablist(el('ea-nav'),'[data-area]',b=>mostrarArea(b.dataset.area));
 el('ea-modos').querySelectorAll('[data-modo]').forEach(b=>b.onclick=()=>definirModo(b.dataset.modo));
 tablist(el('ea-modos'),'[data-modo]',b=>definirModo(b.dataset.modo));
 el('ea-anal-nav').querySelectorAll('[data-anal]').forEach(b=>b.onclick=()=>mostrarAnalise(b.dataset.anal));
 tablist(el('ea-anal-nav'),'[data-anal]',b=>mostrarAnalise(b.dataset.anal));
 // legenda: fases (Empresas e Processos) ou maturidades (Projetos) ligam e desligam no mapa
 el('ea-legenda').onclick=ev=>{const b=ev.target.closest('.ea-fase');if(!b)return;
  if(b.dataset.g!=null){const g=+b.dataset.g;if(S.off.has(g))S.off.delete(g);else S.off.add(g);b.setAttribute('aria-pressed',String(!S.off.has(g)))}
  else{const k=+b.dataset.m;if(S.matOff.has(k))S.matOff.delete(k);else S.matOff.add(k);b.setAttribute('aria-pressed',String(!S.matOff.has(k)))}
  esconderHover();if(S.tela)S.tela.repintar()};
 // Esc, um passo por vez: sai da tela cheia (camada fixa); fecha a prévia, a lista aberta, o balão de escolha e o menu Camadas; depois
 // desfaz o foco (processo → empresa) e, no Explorar, fecha o cartão do município e, por fim, tira o município. Não age com a aba
 // escondida nem dentro de campos.
 document.addEventListener('keydown',ev=>{
  if(ev.key!=='Escape')return;
  const p=painelMapa();if(p&&p.classList.contains('ea-cheia')){telaCheia();return}
  if(el('empresas-view').hidden)return;
  if(previaAberta()||S.tPrevia){fecharPrevia();return}
  if(el('ea-lateral').classList.contains('aberta')){gaveta(false);return}
  if(temPopup()){S.mapa.closePopup();return}
  const cam=el('ea-camadas');if(cam&&cam.open){cam.open=false;cam.querySelector('summary').focus();return}
  const a=document.activeElement;if(a&&/^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName))return;
  if(S.area!=='explorar'){desmarcar();return}
  const f=focoAtual();
  if(f==='processo'||f==='empresa'){desmarcar();return}
  if(f==='municipio'){S.foco='fechado';estadoBotoesMapa();return}
  if(munSel()!==null)limparMunicipio()});
 // Voltar/Avançar: a URL manda. Sem hash e com a aba aberta (entrada do painel antes da primeira seleção) = Explorar sem seleção.
 addEventListener('popstate',ev=>{const h=location.hash||(el('empresas-view').hidden?'':'#empresas');aplicarHash(h,ev.state)});
 // nome de empresa nas análises (e no quadro de titulares do Panorama da aba) → dossiê
 el('empresas-view').addEventListener('click',ev=>{const b=ev.target.closest('[data-emp-cnpj]');if(!b)return;ev.preventDefault();abrirDaAnalise(b.dataset.empCnpj)});}

async function carregar(){
 el('ea-error').innerHTML='';el('ea-loading').hidden=false;
 try{
  const ep=api('/empresas');
  D=await api('/empresas/atlas');preparar();controles();
  el('ea-content').hidden=false;el('ea-loading').hidden=true;
  criarMapa();redesenhar();definirModo('empresas');barraSelecao();barraEscopo();posicionarBusca();
  if(window.EmpresasAnalises){window.EmpresasAnalises.definirResumo(resumoAlternativo);
   window.EmpresasAnalises.definirLigacao({existe:c=>!!porCnpj(c),nome:c=>{const e=porCnpj(c);return e?e.nome:''}})}
  // /api/empresas: análises de produção estimada e declarada; se falhar, só elas mostram o erro (com tentar de novo)
  const analises=p=>p.then(d=>{EP=d;window.EmpresasAnalises.iniciar(d);metodologia();resumoSel();if(S.area==='dossie')dossie();if(S.area==='comparar')comparar()})
   .catch(e=>window.EmpresasAnalises.falhou(e.message||t('c.failed'),()=>analises(api('/empresas'))));
  analises(ep);metodologia();
  // link direto: #empresas[/área][/cnpj raiz]; só o CNPJ abre o dossiê
  aplicarHash(location.hash,history.state);
 }catch(e){
  loaded=false;el('ea-loading').hidden=true;
  el('ea-error').innerHTML=`${escape(e.message||t('c.failed'))} <button type="button" class="btn outline" id="ea-retry">${escape(t('ea.tentarDeNovo'))}</button>`;
  el('ea-retry').onclick=()=>{loaded=true;carregar()};}}

// Ganchos para o teste de navegador (tests/e2e_atlas_empresas.py) e para as análises (escopo, seleção por CNPJ).
window.EmpresasAtlas={mapa:()=>S.mapa,selecionada:()=>S.sel===null?null:porI.get(S.sel).cnpj,
 // redesenhoMs força a rasterização (getImageData) para medir o desenho de verdade, não só o registro dos comandos
 redesenhoMs:()=>{const t0=performance.now();S.tela.repintar();S.tela._ctx.getImageData(0,0,1,1);return performance.now()-t0},
 pontosNaTela:()=>S.nPontos,raioFase:g=>estiloFase(g,S.mapa.getZoom()).r,destaque:()=>S.destaque,modo:()=>S.modo,area:()=>S.area,
 escopo:x=>{if(x)definirEscopo(x);return S.escopo},analise:()=>S.anal,comparacao:()=>S.cmp.map(i=>porI.get(i).cnpj),
 selecionarCnpj:c=>{const e=E.find(x=>x.cnpj===c);if(e)selecionar(e.i,{origem:'teste'});return !!e},
 // o Panorama da aba liga o nome do titular ao dossiê só quando o CNPJ raiz está no índice (nunca por nome)
 temEmpresa:c=>!!porCnpj(c),voltaAnalise:()=>S.volta?{...S.volta}:null,
 // posição na tela (px do contêiner) do ponto da empresa e de um projeto, para os testes clicarem neles
 telaEmpresa:c=>{const e=E.find(x=>x.cnpj===c);if(!e)return null;const q=posEmpresa(e.i);if(!q)return null;const p=S.mapa.latLngToContainerPoint(llDe(q));return [p.x,p.y]},
 // pontos de empresa desenhados agora: [cnpj, processo do ponto, município IBGE sob ele] (para conferir o recorte municipal)
 pontosEmpresas:()=>(S.ptsEmp||[]).map(q=>{const ll=llDe(q),c=S.mapa.latLngToContainerPoint(ll),km=munNoPixel(S.mapa.containerPointToLayerPoint(c));
  return [porI.get(q.i).cnpj,S.locE&&S.locE.get(q.i)?D.processos.rows[S.locE.get(q.i).k][PC.processo]:null,km===null?null:ibgeDe(km),+ll.lat.toFixed(5),+ll.lng.toFixed(5)]}),
 semPontoLocal:()=>S.locE?S.universo.filter(l=>!S.locE.has(l.e.i)).map(l=>l.e.cnpj):null,
 realce:()=>S.selJ.map(j=>D.processos.rows[MP.k[j]][PC.processo]),
 telaProjeto:id=>{const p=D.projetos.find(x=>x.id===id),q=p&&MPJ.pos.get(p.j);if(q===undefined)return null;
  const ll=L.CRS.EPSG3857.pointToLatLng(L.point(MPJ.x[q],MPJ.y[q]),0),pt=S.mapa.latLngToContainerPoint(ll);return [pt.x,pt.y,ll.lat,ll.lng]},
 projetos:()=>({recorte:(S.projetos||[]).length,comLocal:MPJ.n}),
 totais:()=>({cfem:S.cfemTotal,empresas:S.universo.length,processos:S.universo.reduce((s,l)=>s+l.ps.length,0),puxadores:S.puxadores.size}),
 // um pixel do mapa sem símbolo nem polígono (meio da tela), para o teste de desmarcar clicando no vazio
 // (e fora do cartão, da legenda e dos botões que flutuam sobre o mapa)
 pontoVazio:()=>{const m=S.mapa,sz=m.getSize(),c=m.getContainer(),r=c.getBoundingClientRect();
  for(let y=Math.round(sz.y*.3);y<sz.y*.7;y+=9)for(let x=Math.round(sz.x*.3);x<sz.x*.7;x+=9){if(acertar(m.containerPointToLayerPoint([x,y])))continue;
   const e=document.elementFromPoint(r.left+x,r.top+y);if(e&&c.contains(e))return [x,y]}return null},
 limites:()=>{const b=S.mapa&&S.mapa.options.maxBounds;return b?[b.getSouth(),b.getWest(),b.getNorth(),b.getEast()]:null},processo:id=>{const k=procPorId.get(soDigitos(id));return k==null?null:{lat:D.processos.rows[k][PC.lat],lon:D.processos.rows[k][PC.lon]}},
 // cartografia: foco do cartão, processo em foco (número ANM), município do recorte (IBGE), prévia aberta e pixels para os cliques do teste
 foco:()=>focoAtual(),processoFoco:()=>S.destaque===null?null:D.processos.rows[S.destaque][PC.processo],
 municipio:()=>{const k=munSel();return k===null?null:{ibge:ibgeDe(k),nome:D.dims.mun[k][1]}},
 cartao:()=>{const b=el('ea-resumo');return b.hidden?null:{foco:b.dataset.foco,texto:b.innerText}},
 previa:()=>{const p=el('ea-previa'),d=p&&!p.hidden&&p.querySelector('.ea-pv');return d?{...d.dataset,texto:p.innerText}:null},
 munNoPixel:xy=>{const k=munNoPixel(S.mapa.containerPointToLayerPoint(xy));return k===null?null:ibgeDe(k)},
 contorno:()=>{S.tela.repintar();return S.munDesenhado?{...S.munDesenhado}:null},
 acerto:xy=>{const h=acertar(S.mapa.containerPointToLayerPoint(xy));return h?{tipo:h.tipo,n:(h.ks||h.is||h.ps).length,ids:h.ks?h.ks.map(k=>D.processos.rows[k][PC.processo]):null}:null},
 // pixel livre (sem símbolo do modo, dentro do mapa e fora do cartão/legenda/botões) dentro do município, ou fora de todos (c=null)
 // (parte = índice do anel: um pixel dentro daquela parte de um município multipartes)
 telaMunicipio:(c,parte)=>{const m=S.mapa,sz=m.getSize(),ct=m.getContainer(),rc=ct.getBoundingClientRect(),o=m.getPixelOrigin(),s=Math.pow(2,m.getZoom());
  // livre = sem símbolo do modo no pixel nem a 4 px dele (o mouse real tem coordenadas fracionárias)
  const livre=(x,y)=>{if(x<20||y<20||x>sz.x-20||y>sz.y-20)return false;
   for(const[dx,dy]of[[0,0],[4,0],[-4,0],[0,4],[0,-4],[3,3],[-3,-3],[3,-3],[-3,3]])if(acertar(m.containerPointToLayerPoint([x+dx,y+dy])))return false;
   const e=document.elementFromPoint(rc.left+x,rc.top+y);return !!e&&ct.contains(e)};
  if(c==null){for(let y=24;y<sz.y-24;y+=12)for(let x=24;x<sz.x-24;x+=12)if(livre(x,y)&&munNoPixel(m.containerPointToLayerPoint([x,y]))===null)return [x,y];return null}
  const i=S.munIdx&&S.munIdx.get(String(c));if(i===undefined)return null;const p=S.munProj[i];let best=null,[x0,y0,x1,y1]=p.bb;
  if(parte!=null&&p.rings[parte]){const a=p.rings[parte];x0=y0=Infinity;x1=y1=-Infinity;for(let j=0;j<a.length;j+=2){x0=Math.min(x0,a[j]);x1=Math.max(x1,a[j]);y0=Math.min(y0,a[j+1]);y1=Math.max(y1,a[j+1])}}
  for(let a=1;a<24;a++)for(let b=1;b<24;b++){const X=x0+(x1-x0)*a/24,Y=y0+(y1-y0)*b/24;if(!dentroPoligono(p,X,Y))continue;
   const x=X*s-o.x,y=Y*s-o.y,cp=m.layerPointToContainerPoint([x,y]);if(!livre(cp.x,cp.y))continue;const d=(a-12)**2+(b-12)**2;if(!best||d<best[2])best=[cp.x,cp.y,d]}
  return best?[Math.round(best[0]),Math.round(best[1])]:null}};
window.showEmpresas=()=>{if(loaded){if(S.mapa)setTimeout(()=>S.mapa.invalidateSize(),0);return}loaded=true;carregar()};
// Link direto (#empresas/...) abre a aba Empresas depois que o painel monta a sessão.
if(/^#empresas/.test(location.hash))addEventListener('load',()=>setTimeout(()=>{const b=document.querySelector('[data-view="empresas"]');
 const tentar=n=>{if(!document.getElementById('loading').hidden&&n<40)return setTimeout(()=>tentar(n+1),150);if(b)b.click()};tentar(0)},0));
})();
