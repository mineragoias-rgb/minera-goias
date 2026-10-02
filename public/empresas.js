/* Empresas tab: what each company declared producing, how much CCEE load it pulled in Goiás and the coefficient between the two.
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

/* Barra empilhada: a parte clara é o que a CCEE mediu, a escura é o que a anualizacao acrescentou. Mostrar as duas
   deixa visivel, no proprio grafico, quanto do numero e' medicao e quanto e' extrapolacao. */
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
   inicio:String(dados.meta.periodo_ccee[0]),fim:String(dados.meta.periodo_ccee[1])});
 el('ep-export').onclick=()=>exportar(linhas);}

async function load(){
 el('empresas-error').textContent='';
 try{
  dados=await api('/empresas');
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
  el('ep-fontes').textContent=t('ep.fontes',{periodo:dados.meta.periodo_ccee.join('–'),base:dados.meta.versao_base});
  desenhar();
  el('empresas-content').hidden=false;
 }catch(e){el('empresas-error').textContent=e.message}
 finally{el('empresas-loading').hidden=true}}

window.showEmpresas=()=>{if(loaded)return;loaded=true;load()};
})();
