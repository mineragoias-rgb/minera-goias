/* Empresas tab, in three parts: production by company (the state total of the yearbook split by CFEM), what each company declared producing, how much CCEE load it pulled in Goiás and the coefficient between the two, and — from the panorama engine (panorama.js) — CFEM, titles and CCEE load by holder.
   Data comes from /api/empresas (authenticated), rebuilt by scripts/build_empresas_base.py. Nothing is recomputed here beyond
   filtering and totals: annualisation, the coefficient and its quality are decided in the generator, where they are auditable. */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc;
const QUALIDADES=['observado_completo','estimado_alto','estimado_medio','estimado_baixo'];
let dados=null,loaded=false;

const num=(v,casas=0)=>I18N.num(v,{minimumFractionDigits:casas,maximumFractionDigits:casas});
// Chaves escritas por extenso de propósito: montá-las por concatenação esconderia do teste de tradução quais existem.
const rotuloQualidade=q=>({observado_completo:t('ep.q.observado_completo'),estimado_alto:t('ep.q.estimado_alto'),
 estimado_medio:t('ep.q.estimado_medio'),estimado_baixo:t('ep.q.estimado_baixo')}[q]||q);
const rotuloOrigem=o=>o==='declarada_anual'?t('ep.origem.declarada_anual'):t('ep.origem.anualizada_de_parciais');
const rotuloRateio=b=>({carga_total:t('ep.rateio.carga_total'),ramo:t('ep.rateio.ramo'),municipio:t('ep.rateio.municipio'),
 ramo_municipio:t('ep.rateio.ramo_municipio')}[b]||b);
const rotuloEfeito=e=>({subestima:t('ep.efeito.subestima'),superestima:t('ep.efeito.superestima'),
 contexto:t('ep.efeito.contexto'),nao_encontrado:t('ep.efeito.nao_encontrado')}[e]||e);
// A carga separada por ramo ou município é uma parcela da carga da empresa; dizer qual parcela evita ler o número como se fosse o total.
const notaRateio=e=>e.base_do_rateio&&e.base_do_rateio!=='carga_total'
 ? t('ep.rateado',{base:rotuloRateio(e.base_do_rateio),parcela:num(e.parcela_da_empresa*100,0),
     total:num(e.mwh_empresa_anualizado)}) : '';
const nomeCurto=l=>String(l.grupo||'').split(' (')[0].split(' · ')[0];
// O período da CCEE chega como AAAAMM; na tela vira MM/AAAA.
const mesAno=v=>String(v).slice(4)+'/'+String(v).slice(0,4);

// A linha só entra numa comparação de coeficiente quando tem coeficiente; nas de energia, quando tem energia.
const filtradas=()=>{
 const ano=el('ep-ano').value,emp=el('ep-emp').value,min=el('ep-min').value,qual=el('ep-qual').value;
 return dados.linhas.filter(l=>
   (!ano||String(l.ano)===ano)&&(!emp||l.empresa===emp)&&(!min||l.mineral===min)&&
   (!qual||(l.coeficiente?l.coeficiente.qualidade:l.energia&&l.energia.qualidade)===qual));};

function preencher(select,valores,rotuloVazio){
 select.innerHTML=`<option value="">${escape(rotuloVazio)}</option>`
  +valores.map(v=>`<option value="${escape(v[0])}">${escape(v[1])}</option>`).join('');}

// A carga é da empresa no ano, não do mineral: somar por linha contaria duas vezes quem produz dois minerais.
const porEmpresaAno=linhas=>[...new Map(linhas.filter(l=>l.energia).map(l=>[l.empresa+'|'+l.ano,l])).values()];

function metricas(linhas){
 const comEnergia=porEmpresaAno(linhas),comCoef=linhas.filter(l=>l.coeficiente);
 const totalMwh=comEnergia.reduce((s,l)=>s+l.energia.mwh_empresa_anualizado,0);
 const exclusivos=comCoef.filter(l=>l.coeficiente.energia_exclusiva).length;
 const anualizadas=linhas.filter(l=>l.producao&&l.producao.origem==='anualizada_de_parciais').length;
 return [
  ['a',t('ep.m.empresas'),num(new Set(comEnergia.map(l=>l.empresa)).size),t('ep.m.empresasSub')],
  ['b',t('ep.m.energia'),num(totalMwh)+' MWh',t('ep.m.energiaSub')],
  ['c',t('ep.m.coef'),`${num(comCoef.length)}`,t('ep.m.coefSub',{exclusivos:num(exclusivos)})],
  ['d',t('ep.m.estimado'),num(anualizadas),t('ep.m.estimadoSub')],
 ].map(([tom,rotulo,valor,detalhe])=>`<div class="metric tone-${tom}"><span>${escape(rotulo)}</span>`
   +`<strong>${escape(valor)}</strong><small>${escape(detalhe)}</small></div>`).join('');}

/* Barra sobreposta: a clara é o total anualizado, a escura é o que a CCEE mediu de fato. Mostrar as duas
   deixa visível, no próprio gráfico, quanto do número é medição e quanto é extrapolação. */
function barrasEnergia(linhas){
 // Este gráfico é da CARGA INTEIRA da empresa no ano. O rateio entre minerais aparece no coeficiente e na tabela:
 // misturar parcela e total na mesma escala compararia parte com todo.
 const itens=porEmpresaAno(linhas).sort((a,b)=>b.energia.mwh_empresa_anualizado-a.energia.mwh_empresa_anualizado);
 if(!itens.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const max=Math.max(...itens.map(l=>l.energia.mwh_empresa_anualizado),1);
 return itens.map(l=>{
  // Rótulo já escapado na composição: entra cru nos dois lugares, sem risco de escapar duas vezes nem de esquecer um.
  const e=l.energia,rotuloSeguro=`${escape(nomeCurto(l))} · ${escape(String(l.ano))}`;
  return `<div class="bar-row"><span class="bar-label" title="${rotuloSeguro}">${rotuloSeguro}</span>`
   +`<div class="bar-track"><div class="bar-fill anualizado" style="width:${e.mwh_empresa_anualizado/max*100}%"></div>`
   +`<div class="bar-fill medido" style="width:${e.mwh_empresa_observado/max*100}%"></div></div>`
   +`<span class="bar-value">${escape(num(e.mwh_empresa_anualizado))} MWh</span></div>`
   +`<p class="mk-note">${escape(t('ep.energiaNota',{observado:num(e.mwh_empresa_observado),meses:String(e.meses_observados),
       municipios:e.municipios_ccee.join(', ')||'—'}))}</p>`}).join('');}

/* Um bloco por unidade: kWh/t e kWh/oz não se comparam, e juntá-los numa escala só seria um gráfico errado. */
function barrasCoeficiente(linhas){
 const comCoef=linhas.filter(l=>l.coeficiente);
 if(!comCoef.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const unidades=[...new Set(comCoef.map(l=>l.coeficiente.unidade))].sort();
 return unidades.map(unidade=>{
  const itens=comCoef.filter(l=>l.coeficiente.unidade===unidade)
    .sort((a,b)=>b.coeficiente.valor-a.coeficiente.valor);
  const max=Math.max(...itens.map(l=>l.coeficiente.valor),1);
  return `<h3 class="mk-sub">${escape(t('ep.coefUnidade',{unidade}))}</h3>`
   +itens.map(l=>{
     const c=l.coeficiente;
     const rotuloSeguro=`${escape(String(l.ano))} · ${escape(l.mineral)} · ${escape(nomeCurto(l))}`;
     return `<div class="bar-row"><span class="bar-label" title="${rotuloSeguro}">${rotuloSeguro}</span>`
      +`<div class="bar-track"><div class="bar-fill ${c.energia_exclusiva?'exclusiva':'compartilhada'}" style="width:${c.valor/max*100}%"></div></div>`
      +`<span class="bar-value">${escape(num(c.valor,c.valor<100?1:0))}</span></div>`
      +(c.energia_exclusiva
        ?(c.base_do_rateio!=='carga_total'?`<p class="mk-note">${escape(t('ep.rateadoCurto',{base:rotuloRateio(c.base_do_rateio)}))}</p>`:'')
        :`<p class="mk-note">${escape(t('ep.naoExclusiva',{minerais:c.minerais_na_carga.join(' + ')}))}</p>`)}).join('')}).join('');}

function tabela(linhas){
 const cabecalho=['ep.thEmpresa','ep.thMineral','ep.thAno','ep.thProducao','ep.thEnergia','ep.thCoef','ep.thQualidade']
   .map(k=>`<th>${escape(t(k))}</th>`).join('');
 const corpo=linhas.map(l=>{
  const p=l.producao,e=l.energia,c=l.coeficiente;
  const producao=p?`<b>${escape(num(p.valor))} ${escape(p.unidade)}</b>`
    +`<div class="mk-note">${escape(p.produto)} · ${escape(rotuloOrigem(p.origem))}`
    +(p.origem==='anualizada_de_parciais'?` · ${escape(t('ep.deParciais',{periodos:p.periodos.join(', '),
        observado:num(p.observado)}))}`:'')+'</div>':`<span class="muted">${escape(t('ep.semProducao'))}</span>`;
  const energia=e?`<b>${escape(num(e.mwh_anualizado))} MWh</b>`
    +`<div class="mk-note">${escape(t('ep.mesesObservados',{meses:String(e.meses_observados),observado:num(e.mwh_observado)}))}</div>`
    +(notaRateio(e)?`<div class="mk-note">${escape(notaRateio(e))}</div>`:'')
    :`<span class="muted">${escape(t('ep.semEnergia'))}</span>`;
  const coef=c?`<b>${escape(num(c.valor,c.valor<100?1:0))}</b> <span class="muted">${escape(c.unidade)}</span>`
    +(c.energia_exclusiva?'':`<div class="mk-note">${escape(t('ep.naoExclusivaCurto'))}</div>`)
    :`<span class="muted">${escape(l.sem_coeficiente?t('ep.semCoefNota'):'—')}</span>`;
  const qualidade=c?c.qualidade:e?e.qualidade:null;
  return `<tr><td><b>${escape(nomeCurto(l))}</b><div class="mk-note">${escape(l.empresa)}</div>`
   +`<div class="mk-note">${escape(l.municipios.join(', '))}</div></td>`
   +`<td>${escape(l.mineral||'—')}</td><td>${escape(String(l.ano))}</td>`
   +`<td>${producao}</td><td>${energia}</td><td>${coef}</td>`
   +`<td>${qualidade?`<span class="pill">${escape(rotuloQualidade(qualidade))}</span>`:'—'}</td></tr>`}).join('');
 return `<table><thead><tr>${cabecalho}</tr></thead><tbody>${corpo}</tbody></table>`;}

function serie(linhas){
 const empresa=el('ep-emp').value;
 if(!empresa)return `<p class="mk-note">${escape(t('ep.serieEscolha'))}</p>`;
 const daEmpresa=dados.linhas.filter(l=>l.empresa===empresa).sort((a,b)=>a.ano-b.ano||String(a.mineral).localeCompare(String(b.mineral)));
 if(!daEmpresa.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const maxEnergia=Math.max(...daEmpresa.filter(l=>l.energia).map(l=>l.energia.mwh_empresa_anualizado),1);
 const vistos=new Set();
 return daEmpresa.map(l=>{
  const linhas=[];
  if(l.energia&&!vistos.has(l.ano)){
   vistos.add(l.ano);
   linhas.push(`<div class="bar-row"><span class="bar-label">${escape(String(l.ano))} · ${escape(t('ep.serieEnergia'))}</span>`
    +`<div class="bar-track"><div class="bar-fill anualizado" style="width:${l.energia.mwh_empresa_anualizado/maxEnergia*100}%"></div></div>`
    +`<span class="bar-value">${escape(num(l.energia.mwh_empresa_anualizado))} MWh</span></div>`);}
  if(l.producao)linhas.push(`<p class="mk-note">${escape(t('ep.serieLinha',{ano:String(l.ano),mineral:l.mineral,
    producao:num(l.producao.valor)+' '+l.producao.unidade,
    coeficiente:l.coeficiente?num(l.coeficiente.valor,l.coeficiente.valor<100?1:0)+' '+l.coeficiente.unidade:t('ep.semCoefCurto')}))}</p>`);
  return linhas.join('')}).join('');}

function cobertura(linhas){
 const porAno=new Map();
 linhas.forEach(l=>{
  const b=porAno.get(l.ano)||{meses:new Set(),declaradas:0,anualizadas:0,semProducao:0};
  if(l.energia)l.energia.meses.forEach(m=>b.meses.add(m));
  if(l.producao)l.producao.origem==='declarada_anual'?b.declaradas++:b.anualizadas++;else b.semProducao++;
  porAno.set(l.ano,b)});
 const ordenados=[...porAno.entries()].sort((a,b)=>a[0]-b[0]);
 if(!ordenados.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const notas=[...new Map(linhas.flatMap(l=>(l.notas_energia||[]).map(n=>[n.texto,{...n,empresa:nomeCurto(l)}]))).values()];
 const rateios=[...new Map(linhas.filter(l=>l.rateio_ccee&&l.rateio_ccee.criterio!=='unico')
   .map(l=>[l.rateio_ccee.nota,{nota:l.rateio_ccee.nota,empresa:nomeCurto(l)}])).values()];
 const extras=(rateios.length?`<h3 class="mk-sub">${escape(t('ep.rateioT'))}</h3>`
   +rateios.map(r=>`<p class="mk-note"><b>${escape(r.empresa)}</b> · ${escape(r.nota)}</p>`).join(''):'')
  +(notas.length?`<h3 class="mk-sub">${escape(t('ep.notasT'))}</h3>`
   +notas.map(n=>`<p class="mk-note"><b>${escape(n.empresa)}</b> <span class="pill">${escape(rotuloEfeito(n.efeito))}</span> `
     +`${escape(n.texto)} <a href="${escape(n.fonte)}" target="_blank" rel="noopener noreferrer">${escape(t('ep.verFonte'))}</a></p>`).join(''):'');
 return ordenados.map(([ano,b])=>
  `<div class="bar-row"><span class="bar-label">${escape(String(ano))} · ${escape(t('ep.cobEnergia'))}</span>`
  +`<div class="bar-track"><div class="bar-fill ${b.meses.size>=12?'completo':'parcial'}" style="width:${b.meses.size/12*100}%"></div></div>`
  +`<span class="bar-value">${escape(b.meses.size?t('ep.cobMeses',{meses:String(b.meses.size)}):t('ep.cobSemBase'))}</span></div>`
  +`<p class="mk-note">${escape(t('ep.cobProducao',{declaradas:String(b.declaradas),anualizadas:String(b.anualizadas),
      sem:String(b.semProducao)}))}</p>`).join('')+extras;}

function exportar(linhas){
 const cabecalho=['empresa','grupo','cnpj_raiz','municipios','mineral','ano','producao_valor','producao_unidade',
  'producao_medida','producao_origem','producao_meses_cobertos','energia_mwh_anualizado','energia_mwh_observado',
  'energia_meses_observados','energia_base_do_rateio','energia_parcela_da_empresa','coeficiente',
  'coeficiente_unidade','energia_exclusiva','qualidade'];
 const csv=[cabecalho.join(';'),...linhas.map(l=>{
  const p=l.producao,e=l.energia,c=l.coeficiente;
  return [l.empresa,nomeCurto(l),l.cnpj_raiz,l.municipios.join(' | '),l.mineral||'',l.ano,
   p?p.valor:'',p?p.unidade:'',p?p.medida:'',p?p.origem:'',p?p.meses_cobertos:'',
   e?e.mwh_anualizado:'',e?e.mwh_observado:'',e?e.meses_observados:'',e?e.base_do_rateio:'',e?e.parcela_da_empresa:'',
   c?c.valor:'',c?c.unidade:'',c?c.energia_exclusiva:'',c?c.qualidade:e?e.qualidade:''
  ].map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(';')})].join('\r\n');
 const url=URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download='minera-goias-empresas.csv';a.click();
 URL.revokeObjectURL(url);}

function desenhar(){
 const linhas=filtradas();
 el('ep-metrics').innerHTML=metricas(linhas);
 el('ep-energia').innerHTML=barrasEnergia(linhas);
 el('ep-coef').innerHTML=barrasCoeficiente(linhas);
 el('ep-tabela').innerHTML=tabela(linhas);
 el('ep-serie').innerHTML=serie(linhas);
 el('ep-cobertura').innerHTML=cobertura(linhas);
 el('ep-count').textContent=t('ep.contagem',{linhas:num(linhas.length),total:num(dados.linhas.length)});
 el('ep-context').textContent=t('ep.contexto',{
   inicio:mesAno(dados.meta.periodo_ccee[0]),fim:mesAno(dados.meta.periodo_ccee[1])});
 el('ep-export').onclick=()=>exportar(linhas);}


/* Produção por empresa (AMB × CFEM): o bloco "estimada" do mesmo pacote. O total do estado do Anuário Mineral dividido pela parcela
   de cada empresa na CFEM em R$ — divisão feita e auditada no pipeline do Squad 1 (gerar_base_producao.py); aqui só se filtra e soma. */
let est=null;
const linhaObj=(cols,r)=>Object.fromEntries(cols.map((c,i)=>[c,r[i]]));
// Toneladas com casas que dependem do tamanho: ouro sai em poucas toneladas, areia em milhões.
const toneladas=v=>v==null?'—':num(v,Math.abs(v)<10?3:Math.abs(v)<1000?1:0)+' t';
const dinheiro=v=>v==null?'—':'R$ '+num(v,0);
const pct=v=>v==null?'—':num(v*100,1)+' %';
// Coeficiente em MWh por tonelada; abaixo de 1, em kWh/t, para não virar uma fila de zeros.
const coef=v=>v>=1?num(v,v>=100?0:2)+' MWh/t':num(v*1000,v*1000>=10?1:2)+' kWh/t';
// Chaves por extenso: o teste de tradução procura cada uma.
const rotuloEnergia=o=>({observada_ccee:t('es.en.observada_ccee'),observada_ccee_separada:t('es.en.observada_ccee_separada'),
 observada_ccee_rateada:t('es.en.observada_ccee_rateada'),estimada_media_mineral:t('es.en.estimada_media_mineral')}[o]||o);
const estFiltradas=()=>{
 const ano=el('es-ano').value,base=el('es-base').value,min=el('es-min').value,busca=el('es-busca').value.trim().toUpperCase();
 return est.linhas.filter(l=>(!ano||String(l.ano)===ano)&&(!base||l.base===base)&&(!min||l.mineral===min)
  &&(!busca||l.empresa.toUpperCase().includes(busca)||String(l.cnpj_raiz).includes(busca.replace(/\D/g,'')||'#')));};
const estEstado=()=>{
 const ano=el('es-ano').value,base=el('es-base').value,min=el('es-min').value;
 return est.estado.filter(e=>(!ano||String(e.ano)===ano)&&(!base||e.base===base)&&(!min||e.mineral===min));};

// A energia é da empresa no mineral, a mesma nas linhas de ROM e de beneficiada: soma uma vez por empresa, mineral e ano.
function energiaRecorte(linhas){const vistos=new Map();
 linhas.filter(l=>l.energia_mwh!=null).forEach(l=>vistos.set(l.ano+'|'+l.mineral+'|'+l.empresa+'|'+l.cnpj_raiz,l));
 const xs=[...vistos.values()];if(!xs.length)return '—';
 const obs=xs.filter(l=>String(l.energia_origem).startsWith('observada')).reduce((s,l)=>s+l.energia_mwh,0),tot=xs.reduce((s,l)=>s+l.energia_mwh,0);
 return num(tot/1000,0)+' GWh'+(tot?' · '+num(obs/tot*100,0)+' % CCEE':'')}
function estMetricas(linhas,estado){
 const proprias=linhas.filter(l=>!l.minerio_de_outro_mineral),empresas=new Set(proprias.map(l=>l.cnpj_raiz||l.empresa));
 const tot=estado.reduce((s,e)=>s+e.producao_estado_t-e.minerio_de_outro_mineral_t,0),div=estado.reduce((s,e)=>s+e.dividida_por_empresa_t,0);
 const comPub=proprias.filter(l=>l.diferenca_vs_publicado!=null);
 return [
  ['a',t('es.m.empresas'),num(empresas.size),t('es.m.empresasSub')],
  ['b',t('es.m.cobertura'),tot?pct(div/tot):'—',t('es.m.coberturaSub')],
  ['c',t('es.m.cfem'),dinheiro(proprias.reduce((s,l)=>s+(l.cfem_brl||0),0)),t('es.m.cfemSub')],
  ['d',t('es.m.publicado'),num(comPub.length),t('es.m.publicadoSub')],
  ['a',t('es.m.energia'),energiaRecorte(proprias),t('es.m.energiaSub')],
 ].map(([tom,rotulo,valor,detalhe])=>`<div class="metric tone-${tom}"><span>${escape(rotulo)}</span>`
   +`<strong>${escape(valor)}</strong><small>${escape(detalhe)}</small></div>`).join('');}

// Com um mineral escolhido, a barra é a produção (t) — comparável dentro do mineral. Sem mineral, toneladas de areia e de ouro não se
// comparam: a barra vira a CFEM paga, que está em R$ para todos.
function estBarras(linhas){
 const min=el('es-min').value,proprias=linhas.filter(l=>!l.minerio_de_outro_mineral);
 el('es-barrasT').textContent=min?t('es.barrasT',{mineral:min}):t('es.barrasCfemT');
 el('es-barrasS').textContent=min?t('es.barrasS'):t('es.barrasCfemS');
 const g=new Map();
 proprias.forEach(l=>{const k=l.empresa;g.set(k,(g.get(k)||0)+(min?l.producao_t:(l.cfem_brl||0)))});
 const itens=[...g.entries()].filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]).slice(0,15);
 if(!itens.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const max=itens[0][1];
 return itens.map(([e,v])=>`<div class="bar-row"><span class="bar-label" title="${escape(e)}">${escape(e)}</span>`
  +`<div class="bar-track"><div class="bar-fill completo" style="width:${v/max*100}%"></div></div>`
  +`<span class="bar-value">${escape(min?toneladas(v):dinheiro(v))}</span></div>`).join('');}

function estCobertura(estado){
 const itens=estado.filter(e=>e.producao_estado_t>0).sort((a,b)=>b.producao_estado_t-a.producao_estado_t).slice(0,20);
 if(!itens.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const ano=el('es-ano').value;
 return itens.map(e=>{const parte=e.producao_estado_t-e.minerio_de_outro_mineral_t,p=parte?e.dividida_por_empresa_t/parte:0;
  return `<div class="bar-row"><span class="bar-label">${escape(e.mineral)} · ${escape(e.base)}${ano?'':' · '+e.ano}</span>`
   +`<div class="bar-track"><div class="bar-fill ${p>=0.99?'completo':'parcial'}" style="width:${p*100}%"></div></div>`
   +`<span class="bar-value">${escape(pct(p))} · ${escape(toneladas(e.producao_estado_t))}</span></div>`
   +(e.minerio_de_outro_mineral_t?`<p class="mk-note">${escape(t('es.outroMineral',{t:toneladas(e.minerio_de_outro_mineral_t)}))}</p>`:'')
   +(e.empresas===0?`<p class="mk-note">${escape(e.situacao)}</p>`:'')}).join('');}

const LIMITE=200;
function estTabela(linhas){
 const ordem=[...linhas].sort((a,b)=>b.ano-a.ano||a.mineral.localeCompare(b.mineral)||a.base.localeCompare(b.base)||b.producao_t-a.producao_t);
 const cab=[t('es.h.ano'),t('es.h.mineral'),t('es.h.base'),t('es.h.empresa'),t('es.h.cnpj'),t('es.h.producao'),t('es.h.parcela'),
  t('es.h.processos'),t('es.h.municipios'),t('es.h.cfem'),t('es.h.energia'),t('es.h.coef')];
 const corpo=ordem.slice(0,LIMITE).map(l=>`<tr><td>${l.ano}</td><td>${escape(l.mineral)}</td><td>${escape(l.base)}</td>`
  +`<td>${escape(l.empresa)}${l.minerio_de_outro_mineral?` <span class="pill" title="${escape(t('es.outroMineralTip'))}">${escape(t('es.outroMineralPill'))}</span>`:''}</td>`
  +`<td>${escape(l.cnpj_raiz||'—')}</td><td class="num">${escape(toneladas(l.producao_t))}</td><td class="num">${escape(pct(l.parcela_do_estado))}</td>`
  +`<td class="num">${num(l.processos)}</td><td>${escape(l.municipios||'—')}</td><td class="num">${escape(dinheiro(l.cfem_brl))}</td>`
  +`<td class="num">${l.energia_mwh==null?'—':escape(num(l.energia_mwh))+' MWh'}${l.energia_origem?` <span class="pill" title="${escape(l.energia_nota||'')}">${escape(rotuloEnergia(l.energia_origem))}</span>`:''}</td>`
  +`<td class="num">${l.coeficiente_mwh_t==null||l.coeficiente_mwh_t===''?'—':escape(coef(l.coeficiente_mwh_t))}</td></tr>`).join('');
 el('es-count').textContent=t('es.contagem',{mostradas:num(Math.min(LIMITE,ordem.length)),linhas:num(ordem.length)});
 return `<table><thead><tr>${cab.map(c=>`<th>${escape(c)}</th>`).join('')}</tr></thead><tbody>${corpo}</tbody></table>`;}

function estPublicado(linhas){
 const com=linhas.filter(l=>l.publicado_t!=null).sort((a,b)=>b.ano-a.ano||a.mineral.localeCompare(b.mineral));
 if(!com.length)return `<p class="mk-note">${escape(t('es.pubVazio'))}</p>`;
 return `<table><thead><tr>${[t('es.h.ano'),t('es.h.mineral'),t('es.h.empresa'),t('es.h.producao'),t('es.h.publicado'),t('es.h.diferenca'),t('es.h.fonte')]
   .map(c=>`<th>${escape(c)}</th>`).join('')}</tr></thead><tbody>`
  +com.map(l=>{const d=l.diferenca_vs_publicado,fora=Math.abs(d)>0.1;
   return `<tr><td>${l.ano}</td><td>${escape(l.mineral)}</td><td>${escape(l.empresa)}</td><td class="num">${escape(toneladas(l.producao_t))}</td>`
    +`<td class="num">${escape(toneladas(l.publicado_t))}</td><td class="num"${fora?' style="font-weight:700"':''}>${d>0?'+':''}${escape(num(d*100,0))} %</td>`
    +`<td>${l.publicado_url?`<a href="${escape(l.publicado_url)}" target="_blank" rel="noopener noreferrer">${escape(l.publicado_fonte)}</a>`:escape(l.publicado_fonte)}</td></tr>`}).join('')
  +'</tbody></table>';}

function estExportar(linhas){
 const cols=est.colunas,csv=[cols.join(';'),...linhas.map(l=>cols.map(c=>`"${String(l[c]??'').replace(/"/g,'""')}"`).join(';'))].join('\r\n');
 const url=URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download='minera-goias-producao-por-empresa.csv';a.click();URL.revokeObjectURL(url);}

function estDesenhar(){
 const linhas=estFiltradas(),estado=estEstado();
 el('es-metrics').innerHTML=estMetricas(linhas,estado);
 el('es-barras').innerHTML=estBarras(linhas);
 el('es-cobertura').innerHTML=estCobertura(estado);
 el('es-tabela').innerHTML=estTabela(linhas);
 el('es-publicado').innerHTML=estPublicado(linhas);
 const partes=[el('es-ano').value,el('es-base').value,el('es-min').value,el('es-busca').value.trim()].filter(Boolean);
 el('es-context').textContent=partes.length?t('pn.cut')+' '+partes.join(' · '):'';
 el('es-export').onclick=()=>estExportar(linhas);}

function estMontar(){
 const bloco=dados.estimada;
 if(!bloco){el('es-error').textContent=t('es.semDados');return}
 est={colunas:bloco.colunas,linhas:bloco.linhas.map(r=>linhaObj(bloco.colunas,r)),estado:bloco.estado.map(r=>linhaObj(bloco.estado_colunas,r))};
 const anos=[...new Set(est.linhas.map(l=>l.ano))].sort((a,b)=>b-a),minerais=[...new Set(est.linhas.map(l=>l.mineral))].sort((a,b)=>a.localeCompare(b,'pt'));
 preencher(el('es-ano'),anos.map(a=>[String(a),String(a)]),t('es.todosAnos'));
 preencher(el('es-base'),[['beneficiada',t('es.base.beneficiada')],['ROM',t('es.base.rom')],['conteudo_mineral',t('es.base.contido')]],t('es.todasBases'));
 preencher(el('es-min'),minerais.map(m=>[m,m]),t('es.todosMinerais'));
 // Começa no ano mais recente e na produção beneficiada: é o recorte que se lê sem somar coisas diferentes.
 el('es-ano').value=String(anos[0]);el('es-base').value='beneficiada';
 ['es-ano','es-base','es-min'].forEach(id=>el(id).onchange=estDesenhar);
 let timer;el('es-busca').oninput=()=>{clearTimeout(timer);timer=setTimeout(estDesenhar,300)};
 el('es-reset').onclick=()=>{el('es-ano').value=String(anos[0]);el('es-base').value='beneficiada';el('es-min').value='';el('es-busca').value='';estDesenhar()};
 el('es-nota').textContent=t('es.nota');
 el('es-fontes').textContent=t('es.fontes',{fonte:bloco.fonte});
 estDesenhar();
 el('es-content').hidden=false;}

function mostrarAba(aba){
 document.querySelectorAll('#ep-tabs [data-ep]').forEach(b=>{const on=b.dataset.ep===aba;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});
 ['estimada','declarada','direitos'].forEach(k=>{el('ep-aba-'+k).hidden=k!==aba});
 if(aba==='direitos'&&window.showEmpresasPanorama)window.showEmpresasPanorama();}

async function load(){
 el('empresas-error').textContent='';
 document.querySelectorAll('#ep-tabs [data-ep]').forEach(b=>b.onclick=()=>mostrarAba(b.dataset.ep));
 try{
  dados=await api('/empresas');
  try{estMontar()}catch(e){el('es-error').textContent=e.message;console.error(e)}
  const anos=[...new Set(dados.linhas.map(l=>l.ano))].sort();
  const empresas=[...new Map(dados.linhas.map(l=>[l.empresa,nomeCurto(l)])).entries()]
    .sort((a,b)=>a[1].localeCompare(b[1]));
  const minerais=[...new Set(dados.linhas.map(l=>l.mineral).filter(Boolean))].sort();
  preencher(el('ep-ano'),anos.map(a=>[String(a),String(a)]),t('ep.todosAnos'));
  preencher(el('ep-emp'),empresas,t('ep.todasEmpresas'));
  preencher(el('ep-min'),minerais.map(m=>[m,m]),t('ep.todosMinerais'));
  preencher(el('ep-qual'),QUALIDADES.map(q=>[q,rotuloQualidade(q)]),t('ep.todasQualidades'));
  ['ep-ano','ep-emp','ep-min','ep-qual'].forEach(id=>el(id).onchange=desenhar);
  el('ep-reset').onclick=()=>{['ep-ano','ep-emp','ep-min','ep-qual'].forEach(id=>el(id).value='');desenhar()};
  el('ep-nota').textContent=t('ep.nota');
  el('ep-fontes').textContent=t('ep.fontes',{periodo:dados.meta.periodo_ccee.map(mesAno).join('–'),base:dados.meta.versao_base});
  desenhar();
  el('empresas-content').hidden=false;
 }catch(e){el('empresas-error').textContent=e.message;el('es-error').textContent=e.message}
 finally{el('empresas-loading').hidden=true;el('es-loading').hidden=true}}

window.showEmpresas=()=>{if(loaded)return;loaded=true;load()};
})();
