/* Radar panel: register phases, availability rounds and the news collector's output.
   Every number here is a count of records in a source, never a forecast. */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc,n=v=>I18N.num(v);
// Chave de tradução montada em tempo de execução. O teste de i18n colhe as chaves usadas
// por expressão regular sobre a chamada de tradução seguida de um literal, então passar o
// prefixo concatenado seria colhido como uma chave que não existe, e a verificação cairia.
// O nome tk não casa com aquele padrão - é o mesmo recurso que territorio.js usa. (Nem este
// comentário pode trazer um exemplo literal: ele também seria colhido.)
const tk=(prefixo,valor)=>t(prefixo+String(valor));
const VIZ={confirmado:'#0f6fb0',analise:'#0d9488',abrindo:'#c2681b'};
const norm=s=>String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase();
const area=v=>Number.isFinite(v)&&v>0?I18N.num(v,{maximumFractionDigits:2})+' ha':t('rd.semArea');
const PAGE=30;
let loaded=false,packet=null,records=null,phase='',shown=PAGE,selected=null;

// O formatador é opcional porque a aba de cruzamento mostra percentuais. E a linha com
// valor zero continua desenhada, de propósito: nos três painéis do cruzamento a ausência
// é o achado - areia é 20,7% do cadastro e 0% das manchetes - e os três precisam ter
// exatamente as mesmas linhas, na mesma ordem, para a leitura ser posicional.
function bars(rows,color,fmt){
 if(!rows.length)return `<div class="empty">${escape(t('ov.empty'))}</div>`;
 const texto=fmt||n,max=Math.max(...rows.map(r=>r.value),1);
 return rows.map(r=>`<div class="bar-row"><span class="bar-label" title="${escape(r.label)}">${escape(r.label)}</span>`
  +`<div class="bar-track"><div class="bar-fill" style="width:${r.value/max*100}%;background:${color}"></div></div>`
  +`<span class="bar-value">${escape(texto(r.value))}</span></div>`).join('')}

function phaseTable(fases){
 const rows=[...fases.confirmado.fases.map(f=>({...f,grupo:'confirmado'})),
             ...fases.analise.fases.map(f=>({...f,grupo:'analise'})),
             ...fases.abrindo.fases.map(f=>({...f,grupo:'abrindo'}))]
   .sort((a,b)=>b.processos-a.processos);
 return `<table><thead><tr><th>${escape(t('rd.thFase'))}</th><th>${escape(t('rd.thProcessos'))}</th></tr></thead><tbody>`
  +rows.map(r=>`<tr class="rd-row" tabindex="0" role="button" data-fase="${escape(r.fase)}"`
   +` aria-label="${escape(t('rd.abrirFase',{fase:r.fase}))}">`
   +`<td><span class="rd-dot" style="background:${VIZ[r.grupo]}"></span>${escape(r.fase)}</td>`
   +`<td>${escape(n(r.processos))}</td></tr>`).join('')+'</tbody></table>'}

// The claims snapshot is ~2.6 MB, so it is only fetched once someone opens a phase.
async function openPhase(wanted){
 phase=wanted;shown=PAGE;selected=null;
 el('rd-explorer').hidden=false;
 el('rd-explorer-title').textContent=wanted;
 el('rd-search').value='';
 clearDetail();
 markPhase();
 el('rd-explorer').scrollIntoView({behavior:'smooth',block:'start'});
 if(!records){
  el('rd-explorer-sub').textContent=t('rd.carregandoProcessos');
  el('rd-list').innerHTML='';el('rd-count').textContent='';el('rd-more').hidden=true;
  try{const decoded=await window.loadProcesses();packet=decoded.packet;records=decoded.records}
  catch(e){el('rd-explorer-sub').textContent=e.message;return}
  if(phase!==wanted)return}
 renderList()}

function markPhase(){
 el('rd-fases').querySelectorAll('[data-fase]').forEach(row=>
  row.classList.toggle('active',row.dataset.fase===phase))}

function matching(){
 const q=norm(el('rd-search').value);
 return records.filter(r=>r.phase===phase&&(!q||norm(r.id+' '+r.mineral).includes(q)))}

function renderList(){
 const found=matching();
 el('rd-explorer-sub').textContent=t('rd.exploreSub',{n:n(found.length)});
 el('rd-count').textContent=found.length>shown?t('rd.mostrando',{n:n(shown),total:n(found.length)}):'';
 el('rd-list').innerHTML=found.length
  ?found.slice(0,shown).map(r=>`<button type="button" class="rd-item" data-id="${escape(r.id)}">`
    +`<b>${escape(r.id)}</b><span>${escape(r.mineral)}</span><span class="muted">${escape(area(r.area))}</span></button>`).join('')
  :`<div class="empty">${escape(t('rd.nenhumProcesso'))}</div>`;
 el('rd-more').hidden=found.length<=shown;
 el('rd-list').querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>selectProcess(b.dataset.id));
 if(selected)markSelected()}

function markSelected(){
 el('rd-list').querySelectorAll('[data-id]').forEach(b=>
  b.classList.toggle('active',selected!=null&&b.dataset.id===selected.id))}

function clearDetail(){
 selected=null;
 el('rd-detail-title').textContent=t('rd.pickProcess');
 el('rd-detail-hint').hidden=false;
 el('rd-detail-body').innerHTML='';
 el('rd-detail-map').hidden=true}

function selectProcess(id){
 const found=records.find(r=>r.id===id&&r.phase===phase)||records.find(r=>r.id===id);
 if(!found)return;
 selected=found;
 el('rd-detail-title').textContent=t('rd.processo',{id:found.id});
 el('rd-detail-hint').hidden=true;
 el('rd-detail-body').innerHTML='<dl>'+[
  [t('rd.dFase'),found.phase],
  [t('rd.dGrupo'),packet.grupos[found.group]||t('rd.naoInformado')],
  [t('rd.dSubstancia'),found.mineral],
  [t('rd.dArea'),area(found.area)],
  [t('rd.dPoligonos'),n(found.rings.length)],
 ].map(([k,v])=>`<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`).join('')+'</dl>';
 el('rd-detail-map').hidden=false;
 markSelected()}

function wireExplorer(){
 el('rd-fases').querySelectorAll('[data-fase]').forEach(row=>{
  const open=()=>openPhase(row.dataset.fase);
  row.onclick=open;
  row.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}}});
 el('rd-search').oninput=()=>{shown=PAGE;renderList()};
 el('rd-more').onclick=()=>{shown+=PAGE;renderList()};
 el('rd-explorer-close').onclick=()=>{el('rd-explorer').hidden=true;phase='';markPhase()};
 el('rd-detail-map').onclick=()=>{
  if(!selected)return;
  const tab=document.querySelector('[data-view="atlas"]');
  if(tab)tab.click();
  if(window.atlasShowProcess)window.atlasShowProcess(selected.id)}}

/* Notícias. A lista abre no Brasil, nos últimos 7 dias e em ordem de data. O acervo
   passa de duas mil matérias e um terço é mineração de outros países: útil para
   contexto, mas não é por onde o painel de Goiás deve começar - está a um clique.
   Os arquivos de mês em /data/noticias/meses/ são buscados conforme o período pede
   e ficam na memória para os filtros seguintes. */
let NEWS=new Map(),CARREGADOS=new Set(),MUNICIPIOS={},MESES=[],MESES_NOVAS=[],JANELA='',REF='',MOSTRAR=0,COLETA='',AVISO='';
const F={escopo:'brasil',periodo:'7',mes:'',sub:'',mun:'',busca:'',tema:''};
const ANTERIORES='anteriores',PASSO=40,PERIODOS=['novas','7','30','90','mes'],ESCOPOS=['goias','brasil','todos'];

const dia=i=>(i.published_at||i.first_seen||'').slice(0,10);
const mesDe=i=>{const s=dia(i).slice(0,7);
 return /^\d{4}-\d{2}$/.test(s)&&s>=JANELA?s:ANTERIORES};

// "Outubro de 2026", com inicial maiúscula: em português o navegador escreve o mês em minúscula.
const mesNome=m=>m===ANTERIORES?t('rd.anteriores')
 :(s=>s.charAt(0).toUpperCase()+s.slice(1))(new Date(m+'-02T00:00:00Z').toLocaleDateString(I18N.locale(),
   {month:'long',year:'numeric',timeZone:'UTC'}));

// O período conta a partir da última coleta, não do relógio de quem abre a página:
// se o robô atrasar um dia, "7 dias" continua mostrando sete dias de matéria.
function inicio(dias){
 const d=new Date(REF+'T00:00:00Z');d.setUTCDate(d.getUTCDate()-(dias-1));
 return d.toISOString().slice(0,10)}

// "Novas" é o que chegou na última coleta, publicado quando for: a busca devolve
// matéria de meses atrás, então os arquivos a buscar são os que o índice diz ter novas.
const chegouAgora=i=>(i.first_seen||'').slice(0,10)===REF;

function mesesDoPeriodo(){
 if(F.periodo==='mes')return F.mes?[F.mes]:[];
 if(F.periodo==='novas')return MESES_NOVAS;
 const de=inicio(+F.periodo).slice(0,7),ate=REF.slice(0,7);
 return MESES.filter(m=>m!==ANTERIORES&&m>=de&&m<=ate)}

const noPeriodo=i=>F.periodo==='mes'?mesDe(i)===F.mes:F.periodo==='novas'?chegouAgora(i)
 :(d=>d>=inicio(+F.periodo)&&d<=REF)(dia(i));

// 'brasil' vem marcado pelo coletor. Um pacote antigo, sem a marca, cai na regra
// mais simples: fonte brasileira ou matéria de Goiás.
const doBrasil=i=>i.brasil!=null?!!i.brasil:!!i.regional||i.escopo!=='internacional';
const noEscopo=i=>F.escopo==='goias'?!!i.regional:F.escopo==='brasil'?doBrasil(i):true;

function guardar(itens){for(const i of itens||[])if(i.link&&!NEWS.has(i.link))NEWS.set(i.link,i)}

// Devolve os meses que não vieram. Um mês que falha não pode apagar a lista inteira:
// o que carregou é desenhado, e quem chamou decide se a falta importa.
async function carregarMeses(meses){
 const faltam=meses.filter(m=>!CARREGADOS.has(m));
 const resultado=await Promise.allSettled(faltam.map(async mes=>{
  // no-cache revalida com o servidor: o arquivo do mês corrente muda todo dia.
  const r=await fetch(`/data/noticias/meses/${encodeURIComponent(mes)}.json`,{cache:'no-cache'});
  if(!r.ok)throw Error(mes);
  guardar((await r.json()).itens);CARREGADOS.add(mes)}));
 return faltam.filter((m,k)=>resultado[k].status==='rejected')}

const subName=s=>tk('rd.s.',s);
const viaBusca=link=>/news\.google\.com|bing\.com/.test(link||'');
const chave=s=>String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase()
 .replace(/[^a-z0-9]+/g,' ').trim();

// Regulação e governo: o que muda regra, cobrança ou licença no setor. Lido no título
// sem acento; as notícias do próprio site da ANM entram sempre.
const REGULACAO=new RegExp('\\b(anm|cfem|mme|dnpm|outorgas?|licen\\w*|resoluc\\w*|portarias?|decretos?|leis?|pl|'
 +'tcu|mpf|ministerio\\w*|ministr[oa]s?|governo|politica|marco legal|regula\\w*|royalt\\w*|tribut\\w*|impostos?|'
 +'leiloes|leilao|rodadas?|fiscaliza\\w*|stf|justica|tribunal|judicial|senado|camara|congresso|deputad\\w*|'
 +'court|regulator\\w*|government|policy|permits?|licen[cs]e\\w*|law|taxe?s?)\\b');
const regulatoria=({titulo,veiculo})=>veiculo==='Agência Nacional de Mineração'||REGULACAO.test(chave(titulo));

// O Google News devolve "Manchete - Veículo". O veículo vai para a linha de fonte,
// e a manchete fica limpa; é também o que permite reconhecer a mesma matéria
// chegando por mais de uma busca.
function partes(i){
 let titulo=i.title||'',veiculo=i.fonte||'';
 const busca=viaBusca(i.link);
 if(/news\.google\.com/.test(i.link||'')){
  const k=titulo.lastIndexOf(' - ');
  if(k>15){veiculo=titulo.slice(k+3).trim();titulo=titulo.slice(0,k).trim()}}
 else if(/bing\.com/.test(i.link||''))veiculo='Bing';
 // Páginas da ANM trazem o órgão colado: "Título — Agência Nacional de Mineração".
 const orgao=titulo.match(/\s+[—–-]\s+(Agência Nacional de Mineração|Ministério de Minas e Energia)$/);
 if(orgao){titulo=titulo.slice(0,orgao.index);veiculo=orgao[1]}
 return {titulo,veiculo,busca}}

function quando(i){
 const d=dia(i);if(!/^\d{4}-\d{2}-\d{2}$/.test(d))return d;
 const mes=new Date(d+'T12:00:00Z').toLocaleDateString(I18N.locale(),{month:'short',timeZone:'UTC'})
  .replace('.','');
 return `${d.slice(8)} ${mes}`+(d.slice(0,4)===REF.slice(0,4)?'':` ${d.slice(0,4)}`)}

function newsItem({i,titulo,veiculo,busca,repetidas}){
 const lugar=MUNICIPIOS[i.regiao_termo];
 const marca=i.regional?`<span class="rd-tag-go">${escape(lugar||t('rd.regional'))}</span>`
  // No modo com o mundo, a matéria de fora é marcada para não ser lida como do Brasil.
  :F.escopo==='todos'&&!doBrasil(i)?`<span class="rd-tag-intl">${escape(t('rd.intl'))}</span>`:'';
 const subs=(i.substancias||[]).map(s=>`<span class="rd-sub">${escape(subName(s))}</span>`).join('');
 const via=busca?` <span class="rd-indireto">${escape(t('rd.viaBusca'))}</span>`:'';
 const mais=repetidas?`<span class="rd-repetidas">${escape(t(repetidas===1?'rd.maisUmaFonte':'rd.maisFontes',{n:n(repetidas)}))}</span>`:'';
 return `<li><a href="${escape(i.link)}" target="_blank" rel="noopener noreferrer">${escape(titulo)}</a>`
  +`<div class="rd-meta"><span class="rd-data">${escape(quando(i))}</span>`
  +`<span class="rd-fonte">${escape(veiculo)}${via}</span>${marca}${subs}${mais}</div></li>`}

/* Matérias que passam num filtro, sem repetidas: a mesma manchete vinda de várias
   buscas vira uma linha só, e 'repetidas' guarda quantos OUTROS veículos a publicaram.
   Conta veículo, não cópia: o Bing devolve a mesma matéria do mesmo site várias vezes. */
function linhas(filtro){
 const base=[...NEWS.values()].filter(filtro);
 // Data primeiro; no mesmo dia, Goiás e Brasil antes; e o link direto do veículo
 // antes do de busca, para a cópia que sobra na deduplicação ser a melhor.
 base.sort((a,b)=>dia(b).localeCompare(dia(a))||(b.regional?1:0)-(a.regional?1:0)
  ||(doBrasil(b)?1:0)-(doBrasil(a)?1:0)||(viaBusca(a.link)?1:0)-(viaBusca(b.link)?1:0));
 const vistos=new Map(),unicas=[];
 for(const i of base){
  const p=partes(i),k=chave(p.titulo);
  // "Mining.com · cobre" e "Mining.com" são o mesmo site em feeds diferentes, e
  // "Bing" é buscador, não veículo.
  const veiculo=chave(p.veiculo.split(' · ')[0]);
  if(vistos.has(k)){vistos.get(k).veiculos.add(veiculo);continue}
  const linha={i,...p,veiculos:new Set([veiculo])};vistos.set(k,linha);unicas.push(linha)}
 for(const l of unicas)l.repetidas=Math.max(0,[...l.veiculos].filter(v=>v&&v!=='bing').length-1);
 return unicas}

const periodoTexto=()=>F.periodo==='mes'?mesNome(F.mes):tk('rd.d',F.periodo);

/* Os cartões respondem ao que se pergunta ao abrir o radar - o que chegou, o que é
   de Goiás, o que mexe com regra e cobrança, qual foi a matéria da vez - e cada um é
   um atalho: o clique aplica o filtro correspondente na lista logo abaixo. */
function drawCartoes(rec){
 const novas=linhas(i=>chegouAgora(i)&&noEscopo(i)).length;
 const goias=rec.filter(({i})=>i.regional);
 const porMun={};
 for(const {i} of goias)if(MUNICIPIOS[i.regiao_termo])porMun[i.regiao_termo]=(porMun[i.regiao_termo]||0)+1;
 const munTopo=Object.entries(porMun).sort((a,b)=>b[1]-a[1])[0];
 const regulacao=rec.filter(regulatoria).length;
 // A mais repercutida: a manchete que mais veículos trouxeram; no empate, a mais recente.
 const topo=rec.reduce((m,l)=>!m||l.repetidas>m.repetidas?l:m,null);
 const cartao=(id,ativo,rotulo,valor,nota)=>`<button type="button" class="metric rd-card${ativo?' on':''}"`
  +` data-card="${id}" aria-pressed="${ativo}"><span>${escape(rotulo)}</span>`
  +`<strong>${escape(valor)}</strong><small>${escape(nota)}</small></button>`;
 el('rd-cartoes').innerHTML=
   cartao('novas',F.periodo==='novas',t('rd.cNovas'),n(novas),
    F.periodo==='novas'?t('rd.cAtivo'):t('rd.cNovasNota',{quando:COLETA}))
  +cartao('goias',F.escopo==='goias',t('rd.cGoias'),n(goias.length),
    F.escopo==='goias'?t('rd.cAtivo')
    // Um município citado uma vez não é "o mais citado": só nomeia com dois ou mais.
    :munTopo&&munTopo[1]>1?t('rd.cGoiasMun',{m:MUNICIPIOS[munTopo[0]],n:n(munTopo[1])})
    :t('rd.cGoiasNota',{periodo:periodoTexto()}))
  +cartao('regulacao',!!F.tema,t('rd.cRegulacao'),n(regulacao),
    F.tema?t('rd.cAtivo'):t('rd.cRegulacaoNota'))
  +(topo&&topo.repetidas
    ?`<a class="metric rd-card rd-card-destaque" href="${escape(topo.i.link)}" target="_blank" rel="noopener noreferrer">`
     +`<span>${escape(t('rd.cDestaque'))}</span><strong title="${escape(topo.titulo)}">${escape(topo.titulo)}</strong>`
     +`<small>${escape(t('rd.cDestaqueNota',{n:n(topo.repetidas+1),quando:quando(topo.i)}))}</small></a>`
    :`<div class="metric rd-card rd-card-destaque"><span>${escape(t('rd.cDestaque'))}</span>`
     +`<strong>—</strong><small>${escape(t('rd.cDestaqueNenhum'))}</small></div>`);
 el('rd-cartoes').querySelectorAll('[data-card]').forEach(b=>b.onclick=()=>{
  const card=b.dataset.card;
  if(card==='novas'){F.periodo=F.periodo==='novas'?'7':'novas';trocarPeriodo();return}
  if(card==='goias'){F.escopo=F.escopo==='goias'?'brasil':'goias';marcar('rd-escopos','data-escopo',F.escopo)}
  if(card==='regulacao')F.tema=F.tema?'':'regulacao';
  MOSTRAR=PASSO;drawNews()})}

function drawChips(base){
 const conta={};
 for(const {i} of base)for(const s of i.substancias||[])conta[s]=(conta[s]||0)+1;
 const subs=Object.keys(conta).sort((a,b)=>conta[b]-conta[a]);
 if(F.sub&&!conta[F.sub])subs.push(F.sub);
 const chip=(attr,ativo,rotulo,qtd)=>`<button type="button" class="rd-chip${ativo?' on':''}" ${attr}`
  +` aria-pressed="${ativo}">${escape(rotulo)}${qtd!=null?` <small>${escape(n(qtd))}</small>`:''}</button>`;
 el('rd-subs').innerHTML=chip('data-sub=""',!F.sub,t('rd.todas'),base.length)
  +subs.map(s=>chip(`data-sub="${escape(s)}"`,F.sub===s,subName(s),conta[s]||0)).join('');
 el('rd-subs').querySelectorAll('[data-sub]').forEach(b=>b.onclick=()=>{
  F.sub=b.dataset.sub;MOSTRAR=PASSO;drawNews()})}

function drawMunicipios(rec){
 const sel=el('rd-municipio');
 // O município só faz sentido dentro de Goiás; fora disso o seletor some.
 sel.hidden=F.escopo!=='goias';
 if(sel.hidden){F.mun='';return}
 const conta={};
 for(const {i} of rec)if(MUNICIPIOS[i.regiao_termo])conta[i.regiao_termo]=(conta[i.regiao_termo]||0)+1;
 const ms=Object.keys(conta).sort((a,b)=>MUNICIPIOS[a].localeCompare(MUNICIPIOS[b]));
 if(F.mun&&!conta[F.mun])F.mun='';
 sel.innerHTML=`<option value="">${escape(t('rd.todosMunicipios'))}</option>`
  +ms.map(m=>`<option value="${escape(m)}"${F.mun===m?' selected':''}>`
   +`${escape(MUNICIPIOS[m])} (${escape(n(conta[m]))})</option>`).join('');
 sel.disabled=!ms.length}

function drawNews(){
 if(!el('rd-lista'))return;
 const rec=linhas(i=>noPeriodo(i)&&noEscopo(i));
 drawCartoes(rec);drawMunicipios(rec);
 const q=chave(F.busca);
 const base=rec.filter(l=>(!q||chave(l.titulo).includes(q))&&(!F.mun||l.i.regiao_termo===F.mun)
  &&(!F.tema||regulatoria(l)));
 drawChips(base);
 const vis=F.sub?base.filter(({i})=>(i.substancias||[]).includes(F.sub)):base;
 el('rd-conta').textContent=(AVISO?AVISO+' ':'')+(!vis.length?''
  :vis.length>MOSTRAR?t('rd.newsParcial',{mostradas:n(MOSTRAR),filtradas:n(vis.length)})
  :t(vis.length===1?'rd.newsUma':'rd.newsMostrando',{mostradas:n(vis.length)}));
 el('rd-lista').innerHTML=vis.length?vis.slice(0,MOSTRAR).map(newsItem).join('')
  :`<li class="empty">${escape(t('rd.semFiltroPeriodo'))}</li>`;
 el('rd-mais').hidden=vis.length<=MOSTRAR;
 el('rd-mais').textContent=t('rd.mostrarMais',{n:n(Math.min(PASSO,vis.length-MOSTRAR))})}

function marcar(grupo,atributo,valor){
 el(grupo).querySelectorAll(`[${atributo}]`).forEach(b=>{
  const on=b.getAttribute(atributo)===valor;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)})}

async function trocarPeriodo(){
 marcar('rd-periodos','data-periodo',F.periodo);
 el('rd-mes').hidden=F.periodo!=='mes';
 if(F.periodo==='mes'&&!F.mes){F.mes=el('rd-mes').value=MESES[0]||''}
 MOSTRAR=PASSO;
 // O cartão de novas conta o que chegou na última coleta em qualquer período,
 // então os meses que têm novas são buscados sempre.
 const precisa=mesesDoPeriodo(),extras=MESES_NOVAS.filter(m=>!precisa.includes(m));
 AVISO='';
 if(precisa.some(m=>!CARREGADOS.has(m))){
  el('rd-conta').textContent=t('rd.carregandoMes');
  el('rd-lista').innerHTML='';el('rd-mais').hidden=true;
  const falhou=await carregarMeses(precisa);
  if(falhou.length)AVISO=t('rd.mesFalhou',{mes:falhou.map(mesNome).join(', ')})}
 drawNews();
 // Os meses que só o cartão de novas usa vêm depois, sem segurar a lista.
 if(extras.some(m=>!CARREGADOS.has(m))){await carregarMeses(extras);drawNews()}}

function newsBlock(noticias){
 if(!noticias.disponivel){
  const motivo=noticias.motivo==='banco_ilegivel'?'rd.bancoIlegivel':'rd.semColetor';
  return `<div class="notice">${escape(t(motivo))}</div>`}
 NEWS=new Map();CARREGADOS=new Set();guardar(noticias.itens);
 JANELA=noticias.janela||'';MUNICIPIOS=noticias.municipios||{};
 // Do mais recente para o mais antigo, com "antes disso" sempre no fim.
 const todos=(noticias.meses||[]).map(m=>m.mes);
 MESES=todos.filter(m=>m!==ANTERIORES).sort().reverse()
  .concat(todos.includes(ANTERIORES)?[ANTERIORES]:[]);
 MESES_NOVAS=(noticias.meses||[]).filter(m=>m.novas).map(m=>m.mes);
 // Sem data de coleta, a referência é a matéria mais recente que chegou.
 REF=(noticias.atualizado_em||'').slice(0,10)
  ||[...NEWS.values()].map(dia).filter(Boolean).sort().pop()||new Date().toISOString().slice(0,10);
 if(!NEWS.size)return `<div class="empty">${escape(t('ov.empty'))}</div>`;
 // A hora da última coleta, no horário de quem usa o painel em Goiás.
 const coletada=new Date(noticias.atualizado_em||''),fuso={timeZone:'America/Sao_Paulo'};
 COLETA=noticias.atualizado_em
  ?coletada.toLocaleDateString(I18N.locale(),{day:'2-digit',month:'short',...fuso}).replace(' de ',' ').replace('.','')
   +', '+coletada.toLocaleTimeString(I18N.locale(),{hour:'2-digit',minute:'2-digit',...fuso}):'—';
 const rotulo={novas:t('rd.pNovas'),'7':t('rd.p7'),'30':t('rd.p30'),'90':t('rd.p90'),mes:t('rd.pMes')};
 const escopo={goias:t('rd.eGoias'),brasil:t('rd.eBrasil'),todos:t('rd.eTodos')};
 const meses=MESES.map(m=>`<option value="${escape(m)}">${escape(mesNome(m))}</option>`).join('');
 const grupo=(id,rotuloGrupo,attr,lista,nomes)=>`<div class="rd-seg" id="${id}" role="group" aria-label="${escape(rotuloGrupo)}">`
  +lista.map(v=>`<button type="button" ${attr}="${v}">${escape(nomes[v])}</button>`).join('')+'</div>';
 return '<div class="rd-cards" id="rd-cartoes"></div>'
  +'<div class="rd-filtros">'
  +grupo('rd-escopos',t('rd.escopo'),'data-escopo',ESCOPOS,escopo)
  +grupo('rd-periodos',t('rd.periodo'),'data-periodo',PERIODOS,rotulo)
  +`<select id="rd-mes" aria-label="${escape(t('rd.pMes'))}" hidden>${meses}</select>`
  +`<input type="search" id="rd-busca" placeholder="${escape(t('rd.buscaPh'))}" aria-label="${escape(t('rd.buscaPh'))}">`
  +'</div><div class="rd-filtros rd-filtros-2">'
  +`<div class="rd-chips" id="rd-subs" role="group" aria-label="${escape(t('rd.thSubstancia'))}"></div>`
  +`<select id="rd-municipio" aria-label="${escape(t('rd.todosMunicipios'))}" hidden></select>`
  +'</div><p class="rd-conta" id="rd-conta"></p><ul class="rd-news" id="rd-lista"></ul>'
  +'<button type="button" class="btn outline rd-mais" id="rd-mais" hidden></button>'}

function wireNews(){
 if(!el('rd-lista'))return;
 el('rd-escopos').querySelectorAll('[data-escopo]').forEach(b=>b.onclick=()=>{
  F.escopo=b.dataset.escopo;marcar('rd-escopos','data-escopo',F.escopo);MOSTRAR=PASSO;drawNews()});
 marcar('rd-escopos','data-escopo',F.escopo);
 el('rd-periodos').querySelectorAll('[data-periodo]').forEach(b=>b.onclick=()=>{
  F.periodo=b.dataset.periodo;trocarPeriodo()});
 el('rd-mes').onchange=()=>{F.mes=el('rd-mes').value;trocarPeriodo()};
 el('rd-busca').oninput=()=>{F.busca=el('rd-busca').value;MOSTRAR=PASSO;drawNews()};
 el('rd-municipio').onchange=()=>{F.mun=el('rd-municipio').value;MOSTRAR=PASSO;drawNews()};
 el('rd-mais').onclick=()=>{MOSTRAR+=PASSO;drawNews()};
 trocarPeriodo()}

function trendBlock(noticias){
 if(!noticias.disponivel)return '';
 // Only signals the collector was willing to call are worth a row here.
 const rows=(noticias.tendencias||[]).filter(x=>x.verdict==='pressao_de_alta'||x.verdict==='pressao_de_baixa');
 // A leitura de alta/baixa está desligada no coletor, e uma seção permanentemente
 // vazia só confunde. Sem tendência, não desenha o bloco.
 if(!rows.length)return '';
 const body=rows.length
  ? `<table><thead><tr><th>${escape(t('rd.thSemana'))}</th><th>${escape(t('rd.thSubstancia'))}</th>`
    +`<th>${escape(t('rd.thMaterias'))}</th><th>${escape(t('rd.thVeredito'))}</th></tr></thead><tbody>`
    +rows.map(r=>`<tr><td>${escape(r.period)}</td><td>${escape(r.commodity)}</td><td>${escape(n(r.items))}</td>`
     +`<td>${escape(tk('rd.v.',r.verdict))}</td></tr>`).join('')+'</tbody></table>'
  : `<div class="empty">${escape(t('rd.semTendencia'))}</div>`;
 return `<h3>${escape(t('rd.tendencias'))}</h3>${body}<p class="small muted">${escape(t('rd.aviso'))}</p>`}

/* ---------------------------------------------------------------------------
   As três abas. Nada é recarregado na troca: showRadar é idempotente e pinta tudo
   numa passada, então mostrarAba() só revela o painel que já está no DOM. A exceção
   é o cruzamento, que busca o próprio recorte na primeira abertura - como o
   explorador de fases faz com o pacote de processos. */
const ABAS=['anm','noticias','cruzamento'];
let aba='anm';
try{const guardada=localStorage.getItem('minera-rd-aba');if(ABAS.includes(guardada))aba=guardada}catch{}

function mostrarAba(nova){
 aba=nova;
 try{localStorage.setItem('minera-rd-aba',nova)}catch{}
 el('rd-tabs').querySelectorAll('[data-rd]').forEach(b=>{
  const on=b.dataset.rd===aba;
  b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});
 for(const k of ABAS)el('rd-aba-'+k).hidden=k!==aba;
 if(aba==='cruzamento')abrirCruzamento()}

function wireAbas(){
 el('rd-tabs').querySelectorAll('[data-rd]').forEach(b=>b.onclick=()=>mostrarAba(b.dataset.rd));
 el('rd-tabs').onkeydown=e=>{
  if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;
  e.preventDefault();
  const i=ABAS.indexOf(aba),k=ABAS[(i+(e.key==='ArrowRight'?1:-1)+ABAS.length)%ABAS.length];
  mostrarAba(k);el('rd-tabs').querySelector(`[data-rd="${k}"]`).focus()}}

/* ---------------------------------------------------------------------------
   ANM × Notícias. Três contagens da mesma substância - manchetes, processos e CFEM -
   e a distância entre a primeira e a última. Não é série temporal e não mede
   antecipação: o cadastro da ANM não guarda a data em que um processo apareceu, e a
   nota que vem do backend diz isso na página. */
let CX=null,buscandoCX=null,escopoCX='goias';
const CX_COR={atencao:'#0f6fb0',cadastro:'#0d9488',caixa:'#c2681b'};
const pct=v=>v==null?'—':I18N.num(v,{minimumFractionDigits:1,maximumFractionDigits:1})+'%';

async function abrirCruzamento(){
 if(CX){desenharCruzamento();return}
 if(buscandoCX)return;
 el('rd-cx-erro').textContent='';
 el('rd-cx-loading').hidden=false;
 el('rd-cx-corpo').hidden=true;
 try{
  buscandoCX=api('/radar/cruzamento');
  CX=await buscandoCX;
  el('rd-cx-corpo').hidden=false;
  desenharCruzamento();
 }catch(e){el('rd-cx-erro').textContent=e.message;buscandoCX=null}
 finally{el('rd-cx-loading').hidden=true}}

// Os botões são construídos uma vez e só o estado ativo muda depois. Reconstruir o
// seletor a cada redesenho trocaria os botões sob o ponteiro no meio do clique, e o foco
// do teclado se perderia a cada troca de recorte.
function cxEscopos(){
 const caixa=el('rd-cx-escopos');
 if(!caixa.querySelector('[data-cx]')){
  const nomes={goias:t('rd.cx.eGoias'),brasil:t('rd.cx.eBrasil'),tudo:t('rd.cx.eTudo')};
  caixa.innerHTML=CX.escopos.map(v=>
   `<button type="button" data-cx="${escape(v)}">${escape(nomes[v]||v)}</button>`).join('');
  caixa.querySelectorAll('[data-cx]').forEach(b=>b.onclick=()=>{
   escopoCX=b.dataset.cx;desenharCruzamento()})}
 marcar('rd-cx-escopos','data-cx',escopoCX)}

function desenharCruzamento(){
 // window.PNC é lido aqui e não no topo do arquivo: painel.html carrega radar.js antes
 // de panorama-charts.js, então no topo da IIFE ele ainda seria undefined para sempre.
 const C=window.PNC;
 if(!C||el('rd-aba-cruzamento').hidden)return;
 const d=CX.dados[escopoCX]||CX.dados[CX.escopos[0]];
 cxEscopos();
 el('rd-cx-note').textContent=CX.nota;
 const nome=r=>tk('rd.s.',r.chave);
 // Uma linha só entra nos gráficos se alguma das três medidas tiver valor: substância
 // sem processo, sem CFEM e sem manchete não é achado, é ruído do mapeamento.
 const linhas=d.linhas.filter(r=>(r.processos||0)||(r.cfem||0)||(r.unicas||0));

 const box=el('rd-cx-div');
 C.setWidth(box.clientWidth||860);
 if(CX.imprensa_disponivel){
  const dist=linhas.filter(r=>r.distancia!=null&&r.distancia!==0)
   .map(r=>({label:nome(r),value:r.distancia}))
   .sort((a,b)=>Math.abs(b.value)-Math.abs(a.value));
  el('rd-cx-legenda').innerHTML=
   `<span><i style="background:${CX_COR.atencao}"></i>${escape(t('rd.cx.legAtencao'))}</span>`
   +`<span><i style="background:${CX_COR.caixa}"></i>${escape(t('rd.cx.legCaixa'))}</span>`;
  box.innerHTML=C.hdiv(dist,{pos:CX_COR.atencao,neg:CX_COR.caixa,aria:t('rd.cx.distanciaAria'),
   fmt:v=>(v>0?'+':'')+I18N.num(v,{minimumFractionDigits:1,maximumFractionDigits:1})+' p.p.'});
 }else{
  el('rd-cx-legenda').innerHTML='';
  box.innerHTML=`<div class="notice">${escape(t('rd.cx.semImprensa'))}</div>`}

 // A mesma ordem de linhas nos três painéis, e barras HTML em vez do SVG do Panorama:
 // o hbar de lá descarta a linha de valor zero, e aqui o zero é o que se quer ver.
 const ordem=[...linhas].sort((a,b)=>(b.processos||0)-(a.processos||0));
 const painel=(id,campo,cor)=>{el(id).innerHTML=
  bars(ordem.map(r=>({label:nome(r),value:r[campo]||0})),cor,pct)};
 if(CX.imprensa_disponivel)painel('rd-cx-imprensa','unicas_pct',CX_COR.atencao);
 else el('rd-cx-imprensa').innerHTML=`<div class="empty">${escape(t('ov.empty'))}</div>`;
 painel('rd-cx-proc','processos_pct',CX_COR.cadastro);
 painel('rd-cx-cfem','cfem_pct',CX_COR.caixa);

 C.table(el('rd-cx-tabela'),[
  {label:t('rd.cx.thSubs'),get:nome},
  {label:t('rd.cx.thMat'),num:true,get:r=>r.materias==null?'—':n(r.materias)},
  {label:t('rd.cx.thUnicas'),num:true,get:r=>r.unicas==null?'—':n(r.unicas)},
  {label:t('rd.cx.thPctMat'),num:true,get:r=>pct(r.unicas_pct)},
  {label:t('rd.cx.thProc'),num:true,get:r=>n(r.processos)},
  {label:t('rd.cx.thPctProc'),num:true,get:r=>pct(r.processos_pct)},
  {label:t('rd.cx.thCfem'),num:true,get:r=>C.money(r.cfem,0)},
  {label:t('rd.cx.thPctCfem'),num:true,get:r=>pct(r.cfem_pct)},
  {label:t('rd.cx.thDist'),num:true,get:r=>r.distancia==null?'—':(r.distancia>0?'+':'')+pct(r.distancia)},
 ],ordem,{limit:12});

 cxCartoes(C,linhas,d);
 const cob=CX.cobertura;
 el('rd-cx-cobertura').textContent=t('rd.cx.cobertura',
  {cfem:pct((cob.cfem||0)*100),proc:pct((cob.processos||0)*100)});
 el('rd-cx-duplicadas').textContent=d.tags&&d.manchetes
  ?t('rd.cx.duplicadas',{mat:n(d.tags),unicas:n(d.manchetes)}):'';
 const per=CX.periodos;
 el('rd-fonte-cruzamento').textContent=t('rd.fonteCruzamento',{fonte:CX.fonte})
  +(per.cfem?' · '+t('rd.cx.periodo',{a0:per.cfem[0],a1:per.cfem[1],
    acervo:n(per.imprensa_acervo||0),desde:per.imprensa_coleta_desde||'—'}):'')}

function cxCartoes(C,linhas,d){
 // Todos derivados dos dados: nenhuma substância é nomeada no código.
 const comDist=linhas.filter(r=>r.distancia!=null);
 const maisCitada=comDist.reduce((a,b)=>!a||b.distancia>a.distancia?b:a,null);
 const maisCaixa=comDist.reduce((a,b)=>!a||b.distancia<a.distancia?b:a,null);
 const maiorCad=linhas.reduce((a,b)=>!a||(b.processos||0)>(a.processos||0)?b:a,null);
 const sinal=v=>(v>0?'+':'')+I18N.num(v,{minimumFractionDigits:1,maximumFractionDigits:1});
 const cartoes=[];
 if(maisCitada&&maisCitada.distancia>0)cartoes.push(['tone-a',t('rd.cx.cMaisCitada'),
  tk('rd.s.',maisCitada.chave),t('rd.cx.cDist',{v:sinal(maisCitada.distancia)})]);
 if(maisCaixa&&maisCaixa.distancia<0)cartoes.push(['tone-c',t('rd.cx.cMaisCaixa'),
  tk('rd.s.',maisCaixa.chave),t('rd.cx.cDist',{v:sinal(maisCaixa.distancia)})]);
 if(maiorCad)cartoes.push(['tone-b',t('rd.cx.cMaiorCadastro'),tk('rd.s.',maiorCad.chave),
  t('rd.cx.cCadastroNota',{proc:pct(maiorCad.processos_pct),
   mat:maiorCad.unicas_pct==null?'—':pct(maiorCad.unicas_pct)})]);
 cartoes.push(['tone-d',t('rd.cx.cCobertura'),pct((CX.cobertura.cfem||0)*100),
  t('rd.cx.cCoberturaNota',{cfem:pct((CX.cobertura.cfem||0)*100),
   proc:pct((CX.cobertura.processos||0)*100)})]);
 el('rd-cx-cartoes').innerHTML=C.tiles(cartoes)}

// Os gráficos são redesenhados na largura real do cartão, nunca escalados.
let cxTimer;
addEventListener('resize',()=>{clearTimeout(cxTimer);
 cxTimer=setTimeout(()=>{if(!el('radar-view').hidden&&aba==='cruzamento'&&CX)desenharCruzamento()},150)});

async function load(){
 el('radar-error').textContent='';
 try{
  const d=await api('/radar');
  el('rd-confirmado').textContent=n(d.fases.confirmado.total);
  el('rd-analise').textContent=n(d.fases.analise.total);
  el('rd-abrindo').textContent=n(d.fases.abrindo.total);
  el('rd-futuras').textContent=n(d.rodadas.futuras);
  el('radar-note').textContent=d.nota;
  el('rd-fases').innerHTML=phaseTable(d.fases);
  el('rd-situacoes').innerHTML=bars(d.rodadas.situacoes,VIZ.analise);
  el('rd-municipios').innerHTML=bars(d.rodadas.top_municipios,VIZ.abrindo);
  el('rd-noticias').innerHTML=newsBlock(d.noticias);
  wireNews();
  el('rd-tendencias').innerHTML=trendBlock(d.noticias);
  el('rd-fonte').textContent=t('ov.sourcePrefix')+d.rodadas.fonte;
  el('rd-fonte-noticias').textContent=d.noticias.gerado_por
   ?t('rd.fonteNoticias',{gerado:d.noticias.gerado_por,desde:d.noticias.coleta_desde||'—'}):'';
  wireExplorer();
  wireAbas();
  mostrarAba(aba);
  el('radar-content').hidden=false;
 }catch(e){el('radar-error').textContent=e.message}
 finally{el('radar-loading').hidden=true}}

window.showRadar=()=>{if(loaded)return;loaded=true;load()};
})();
