/* Aba Empresas · Análises. Duas análises transversais, lidas de /api/empresas (scripts/build_empresas_base.py), que a aba carrega uma vez
   e entrega aqui (empresas-atlas.js → EmpresasAnalises.iniciar):
   - Produção estimada (AMB × CFEM): o total do estado do Anuário Mineral dividido entre as empresas pela parcela de cada uma na CFEM
     (bloco "estimada", dividido e auditado na geração da base de produção). É estimativa, não produção observada.
   - Produção declarada e energia: o que 10 empresas declararam produzir, a carga do agente na CCEE e o coeficiente entre os dois.
   Cada análise trabalha em dois escopos, escolhidos na barra de escopo da aba: a empresa selecionada (pelo CNPJ raiz) ou todas as
   empresas. Empresa sem dado na análise mostra "Dados não disponíveis para esta empresa" — nunca o agregado de todas no lugar dela.
   Aqui só se filtra, soma e desenha: anualização, coeficiente e qualidade são decididos nos geradores, onde são auditáveis. */
(()=>{'use strict';
const el=id=>document.getElementById(id),escape=esc;
const QUALIDADES=['observado_completo','estimado_alto','estimado_medio','estimado_baixo'];
let dados=null,est=null;
// Escopo vindo da aba: empresa escolhida e se a análise está recortada nela ('empresa') ou mostra todas ('todas').
const ctx={cnpj:null,nome:'',escopo:'todas',resumo:null};
const daEmpresa=()=>ctx.escopo==='empresa'&&!!ctx.cnpj;

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
function preencher(select,valores,rotuloVazio){
 select.innerHTML=`<option value="">${escape(rotuloVazio)}</option>`
  +valores.map(v=>`<option value="${escape(v[0])}">${escape(v[1])}</option>`).join('');}
// Um número da faixa de síntese: rótulo, valor e o detalhe (período, unidade, ressalva) — sem cartão, para não pesar.
const faixa=([,rotulo,valor,detalhe])=>`<div><dt>${escape(rotulo)}</dt><dd><b>${escape(valor)}</b><small>${escape(detalhe)}</small></dd></div>`;
// Exportação dos recortes: o mesmo exportador tipado do resto da aba (public/empresas-exportar.js) — cabeçalho na 1ª linha, decimal
// vírgula, texto que parece fórmula neutralizado, vazio = sem dado — e o recorte (filtros e escopo) em colunas.
function baixarCsv(nome,tabela){
 const url=URL.createObjectURL(new Blob([window.EmpresasExportar.csv(tabela)],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download=nome;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
const tipadas=pares=>pares.map(([id,tipo])=>({id,tipo}));

// Nome de empresa que abre o dossiê (o clique vai para empresas-atlas.js, que seleciona a empresa sem mexer nesta análise): só quando o
// CNPJ raiz tem 8 dígitos e está no índice da aba. Pessoa física, linha do estado, ano, mineral e base continuam texto.
let ligacao=null;
const temDossie=cnpj=>!!ligacao&&/^\d{8}$/.test(String(cnpj||''))&&ligacao.existe(String(cnpj));
const nomeEmp=(rotulo,cnpj)=>temDossie(cnpj)
 ?`<button type="button" class="ea-emp-link" data-emp-cnpj="${escape(String(cnpj))}" title="${escape(t('ea.abrirDossieDe',{nome:ligacao.nome(String(cnpj))||rotulo}))}">${escape(rotulo)}</button>`
 :escape(rotulo);
// Rótulo de cada grupo de barra (a chave é o CNPJ raiz, nunca o nome): dois CNPJs com o mesmo nome viram duas barras, com o CNPJ.
const cnpjFmt=c=>/^\d{8}$/.test(String(c||''))?`${String(c).slice(0,2)}.${String(c).slice(2,5)}.${String(c).slice(5)}`:'';
function rotulosPorChave(linhas){
 const nome=new Map();linhas.forEach(l=>{if(!nome.has(chaveEmp(l)))nome.set(chaveEmp(l),l.empresa)});
 const vezes=new Map();[...nome.values()].forEach(n=>vezes.set(n,(vezes.get(n)||0)+1));
 return k=>{const n=nome.get(k)||k;return vezes.get(n)>1&&cnpjFmt(k)?n+' · '+cnpjFmt(k):n}}

// Bloco "Dados não disponíveis para esta empresa": diz por quê e mostra o que a base tem dela (vem da aba: CFEM, títulos, carga CCEE).
function indisponivel(box,porque,outra){
 box.hidden=false;
 box.innerHTML=`<div class="ea-indisp-msg"><b>${escape(t('ea.indisp.titulo'))}</b><span>${escape(ctx.nome)}</span></div>`
  +`<p>${escape(porque)}</p>`
  +(ctx.resumo?`<div class="ea-indisp-alt"><h4>${escape(t('ea.indisp.outras'))}</h4>${ctx.resumo(ctx.cnpj)}</div>`:'')
  +`<p class="ea-indisp-acoes"><button type="button" class="btn outline" data-todas="1">${escape(outra)}</button></p>`;
 box.querySelector('[data-todas]').onclick=()=>{if(window.EmpresasAtlas)window.EmpresasAtlas.escopo('todas')};}

// ======================================================================= Produção declarada e energia (10 empresas)
const linhasDeclaradas=()=>daEmpresa()?dados.linhas.filter(l=>l.cnpj_raiz===ctx.cnpj):dados.linhas;
const filtradas=()=>{
 const ano=el('ep-ano').value,min=el('ep-min').value,qual=el('ep-qual').value;
 return linhasDeclaradas().filter(l=>(!ano||String(l.ano)===ano)&&(!min||l.mineral===min)&&
   (!qual||(l.coeficiente?l.coeficiente.qualidade:l.energia&&l.energia.qualidade)===qual));};

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
 ].map(faixa).join('');}
// Síntese da declarada: o resultado principal numa frase (empresa: o último ano declarado; todas: a maior carga do ano mais recente).
function sinteseDeclarada(linhas){
 const comProd=linhas.filter(l=>l.producao).sort((a,b)=>b.ano-a.ano);if(!comProd.length)return t('ep.sint.vazio');
 if(daEmpresa()){const l=comProd[0],c=l.coeficiente;
  return t('ep.sint.empresa',{nome:ctx.nome,ano:String(l.ano),mineral:l.mineral||'—',prod:num(l.producao.valor)+' '+l.producao.unidade,
   energia:l.energia?num(l.energia.mwh_empresa_anualizado)+' MWh':'—',coef:c?num(c.valor,c.valor<100?1:0)+' '+c.unidade:'—'})}
 const ano=Math.max(...comProd.map(l=>l.ano)),doAno=porEmpresaAno(linhas.filter(l=>l.ano===ano)).sort((a,b)=>b.energia.mwh_empresa_anualizado-a.energia.mwh_empresa_anualizado);
 return t('ep.sint.todas',{n:num(new Set(comProd.map(l=>l.empresa)).size),ano:String(ano),
  maior:doAno.length?doAno[0].empresa:'—',mwh:doAno.length?num(doAno[0].energia.mwh_empresa_anualizado):'—'})}

/* Barra sobreposta: a clara é o total anualizado, a escura é o que a CCEE mediu de fato. Mostrar as duas
   deixa visível, no próprio gráfico, quanto do número é medição e quanto é extrapolação. */
function barrasEnergia(linhas){
 // Este gráfico é da CARGA INTEIRA da empresa no ano. O rateio entre minerais aparece no coeficiente e na tabela.
 const itens=porEmpresaAno(linhas).sort((a,b)=>b.energia.mwh_empresa_anualizado-a.energia.mwh_empresa_anualizado);
 if(!itens.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const max=Math.max(...itens.map(l=>l.energia.mwh_empresa_anualizado),1);
 return itens.map(l=>{
  const e=l.energia,rotuloSeguro=`${escape(nomeCurto(l))} · ${escape(String(l.ano))}`;
  return `<div class="bar-row"><span class="bar-label" title="${rotuloSeguro}">${nomeEmp(nomeCurto(l),l.cnpj_raiz)} · ${escape(String(l.ano))}</span>`
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
  const itens=comCoef.filter(l=>l.coeficiente.unidade===unidade).sort((a,b)=>b.coeficiente.valor-a.coeficiente.valor);
  const max=Math.max(...itens.map(l=>l.coeficiente.valor),1);
  return `<h3 class="mk-sub">${escape(t('ep.coefUnidade',{unidade}))}</h3>`
   +itens.map(l=>{
     const c=l.coeficiente,rotuloSeguro=`${escape(String(l.ano))} · ${escape(l.mineral)} · ${escape(nomeCurto(l))}`;
     return `<div class="bar-row"><span class="bar-label" title="${rotuloSeguro}">${escape(String(l.ano))} · ${escape(l.mineral)} · ${nomeEmp(nomeCurto(l),l.cnpj_raiz)}</span>`
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
    +(p.origem==='anualizada_de_parciais'?` · ${escape(t('ep.deParciais',{periodos:p.periodos.join(', '),observado:num(p.observado)}))}`:'')+'</div>'
    :`<span class="muted">${escape(t('ep.semProducao'))}</span>`;
  const energia=e?`<b>${escape(num(e.mwh_anualizado))} MWh</b>`
    +`<div class="mk-note">${escape(t('ep.mesesObservados',{meses:String(e.meses_observados),observado:num(e.mwh_observado)}))}</div>`
    +(notaRateio(e)?`<div class="mk-note">${escape(notaRateio(e))}</div>`:'')
    :`<span class="muted">${escape(t('ep.semEnergia'))}</span>`;
  const coef=c?`<b>${escape(num(c.valor,c.valor<100?1:0))}</b> <span class="muted">${escape(c.unidade)}</span>`
    +(c.energia_exclusiva?'':`<div class="mk-note">${escape(t('ep.naoExclusivaCurto'))}</div>`)
    :`<span class="muted">${escape(l.sem_coeficiente?t('ep.semCoefNota'):'—')}</span>`;
  const qualidade=c?c.qualidade:e?e.qualidade:null;
  return `<tr><td><b>${nomeEmp(nomeCurto(l),l.cnpj_raiz)}</b><div class="mk-note">${escape(l.empresa)}</div>`
   +`<div class="mk-note">${escape(l.municipios.join(', '))}</div></td>`
   +`<td>${escape(l.mineral||'—')}</td><td>${escape(String(l.ano))}</td>`
   +`<td>${producao}</td><td>${energia}</td><td>${coef}</td>`
   +`<td>${qualidade?`<span class="pill">${escape(rotuloQualidade(qualidade))}</span>`:'—'}</td></tr>`}).join('');
 return `<table><thead><tr>${cabecalho}</tr></thead><tbody>${corpo}</tbody></table>`;}

// Evolução: da empresa selecionada (se ela está entre as 10); sem empresa, a análise pede uma.
function serie(){
 const cnpj=ctx.cnpj,daEmp=cnpj?dados.linhas.filter(l=>l.cnpj_raiz===cnpj).sort((a,b)=>a.ano-b.ano||String(a.mineral).localeCompare(String(b.mineral))):[];
 if(!cnpj)return `<p class="mk-note">${escape(t('ea.ep.serieEscolha'))}</p>`;
 if(!daEmp.length)return `<p class="mk-note">${escape(t('ea.ep.serieFora',{nome:ctx.nome}))}</p>`;
 const maxEnergia=Math.max(...daEmp.filter(l=>l.energia).map(l=>l.energia.mwh_empresa_anualizado),1),vistos=new Set();
 return `<p class="mk-note"><b>${escape(nomeCurto(daEmp[0])||daEmp[0].empresa)}</b></p>`+daEmp.map(l=>{
  const linhas=[];
  if(l.energia&&!vistos.has(l.ano)){vistos.add(l.ano);
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
  +`<p class="mk-note">${escape(t('ep.cobProducao',{declaradas:String(b.declaradas),anualizadas:String(b.anualizadas),sem:String(b.semProducao)}))}</p>`).join('')+extras;}

const COLS_DECLARADA=tipadas([['empresa','texto'],['grupo','texto'],['cnpj_raiz','id'],['municipios','texto'],['mineral','texto'],['ano','inteiro'],
 ['producao_valor','numero'],['producao_unidade','texto'],['producao_produto','texto'],['producao_medida','texto'],['producao_origem','texto'],
 ['producao_periodos','texto'],['producao_meses_cobertos','inteiro'],['energia_mwh_anualizado','numero'],['energia_mwh_observado','numero'],
 ['energia_meses_observados','inteiro'],['energia_base_do_rateio','texto'],['energia_parcela_da_empresa','numero'],['coeficiente','numero'],
 ['coeficiente_unidade','texto'],['energia_exclusiva','bool'],['qualidade','texto'],
 ['escopo','texto'],['filtro_ano','texto'],['filtro_mineral','texto'],['filtro_qualidade','texto'],['fonte','texto'],['data_pacote','texto']]);
function exportar(linhas){
 const rec={escopo:daEmpresa()?ctx.cnpj:'todas',filtro_ano:el('ep-ano').value||null,filtro_mineral:el('ep-min').value||null,
  filtro_qualidade:el('ep-qual').value||null,fonte:t('ea.ep.fontes',{periodo:dados.meta.periodo_ccee.map(mesAno).join('–')}),data_pacote:dados.meta.built_on};
 baixarCsv(`minera-goias-empresas-producao-declarada${daEmpresa()?'-'+ctx.cnpj:''}.csv`,{colunas:COLS_DECLARADA,linhas:linhas.map(l=>{
  const p=l.producao,e=l.energia,c=l.coeficiente;
  return {empresa:l.empresa,grupo:nomeCurto(l)||null,cnpj_raiz:l.cnpj_raiz,municipios:l.municipios.join(' | ')||null,mineral:l.mineral||null,ano:l.ano,
   producao_valor:p?p.valor:null,producao_unidade:p?p.unidade:null,producao_produto:p?p.produto:null,producao_medida:p?p.medida:null,
   producao_origem:p?p.origem:null,producao_periodos:p&&p.periodos?p.periodos.join(' | '):null,producao_meses_cobertos:p?p.meses_cobertos:null,
   energia_mwh_anualizado:e?e.mwh_anualizado:null,energia_mwh_observado:e?e.mwh_observado:null,energia_meses_observados:e?e.meses_observados:null,
   energia_base_do_rateio:e?e.base_do_rateio:null,energia_parcela_da_empresa:e?e.parcela_da_empresa:null,coeficiente:c?c.valor:null,
   coeficiente_unidade:c?c.unidade:null,energia_exclusiva:c?c.energia_exclusiva:null,qualidade:c?c.qualidade:e?e.qualidade:null,...rec}})});}

function desenhar(){
 if(!dados)return;
 const box=el('ep-indisp');
 // Empresa fora das 10 com produção declarada: o painel não volta para todas as empresas; diz que não há dado e mostra o que há.
 if(daEmpresa()&&!dados.linhas.some(l=>l.cnpj_raiz===ctx.cnpj)){
  indisponivel(box,t('ea.indisp.declarada',{n:String(new Set(dados.linhas.map(l=>l.cnpj_raiz)).size)}),t('ea.indisp.verDeclaradas'));
  ['ep-sintese','ep-metrics','ep-energia','ep-coef','ep-tabela','ep-serie','ep-cobertura','ep-count','ep-context'].forEach(id=>{el(id).innerHTML='';el(id).textContent=''});
  el('empresas-content').hidden=true;return}
 box.hidden=true;box.innerHTML='';el('empresas-content').hidden=false;
 const linhas=filtradas();
 el('ep-sintese').textContent=sinteseDeclarada(linhas);
 el('ep-metrics').innerHTML=metricas(linhas);
 el('ep-energia').innerHTML=barrasEnergia(linhas);
 el('ep-coef').innerHTML=barrasCoeficiente(linhas);
 el('ep-tabela').innerHTML=tabela(linhas);
 el('ep-serie').innerHTML=serie();
 el('ep-cobertura').innerHTML=cobertura(linhas);
 el('ep-count').textContent=t('ep.contagem',{linhas:num(linhas.length),total:num(linhasDeclaradas().length)});
 el('ep-context').textContent=(daEmpresa()?t('ea.escopoEmpresaCtx',{nome:ctx.nome})+' · ':t('ea.escopoTodasCtx')+' · ')
  +t('ep.contexto',{inicio:mesAno(dados.meta.periodo_ccee[0]),fim:mesAno(dados.meta.periodo_ccee[1])});
 el('ep-export').onclick=()=>exportar(linhas);}

// ======================================================================= Produção estimada por empresa (AMB × CFEM)
/* O bloco "estimada" do mesmo pacote. O total do estado do Anuário Mineral dividido pela parcela de cada empresa na CFEM em R$ —
   divisão feita e auditada na geração da base de produção; aqui só se filtra e soma. */
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
const rotuloBase=b=>({beneficiada:t('es.base.beneficiada'),ROM:t('es.base.rom'),conteudo_mineral:t('es.base.contido')}[b]||b);
const chaveEmp=l=>l.cnpj_raiz||l.empresa;
const ORDEM_BASE=['beneficiada','conteudo_mineral','ROM'];
const linhasEstimadas=()=>daEmpresa()?est.linhas.filter(l=>l.cnpj_raiz===ctx.cnpj):est.linhas;
const estFiltradas=()=>{
 const ano=el('es-ano').value,base=el('es-base').value,min=el('es-min').value,busca=daEmpresa()?'':el('es-busca').value.trim().toUpperCase();
 return linhasEstimadas().filter(l=>(!ano||String(l.ano)===ano)&&(!base||l.base===base)&&(!min||l.mineral===min)
  &&(!busca||l.empresa.toUpperCase().includes(busca)||String(l.cnpj_raiz).includes(busca.replace(/\D/g,'')||'#')));};
const estEstado=()=>{
 const ano=el('es-ano').value,base=el('es-base').value,min=el('es-min').value;
 return est.estado.filter(e=>(!ano||String(e.ano)===ano)&&(!base||e.base===base)&&(!min||e.mineral===min));};

/* CFEM do recorte, uma vez por empresa, mineral e ano. A linha de ROM e a de beneficiada repetem a mesma CFEM; a versão anterior
   somava as duas com "Todas as bases" e dobrava o valor (R$ 1,45 bi em vez de R$ 0,73 bi em 2022–2025). Soma-se só a primeira base
   presente na ordem beneficiada → contido → ROM; as várias pessoas físicas sem nome de um grupo continuam somadas entre si. */
function cfemUnica(linhas,agrupar=chaveEmp){
 const baseDe=new Map();
 linhas.forEach(l=>{const k=l.ano+'|'+l.mineral+'|'+chaveEmp(l),b=baseDe.get(k);if(b===undefined||ORDEM_BASE.indexOf(l.base)<ORDEM_BASE.indexOf(b))baseDe.set(k,l.base)});
 const out=new Map();
 linhas.forEach(l=>{if(l.base!==baseDe.get(l.ano+'|'+l.mineral+'|'+chaveEmp(l)))return;const g=agrupar(l);out.set(g,(out.get(g)||0)+(l.cfem_brl||0))});
 return out;}
const somaMapa=m=>[...m.values()].reduce((s,v)=>s+v,0);
function naBasePreferida(linhas){
 const baseDe=new Map();
 linhas.forEach(l=>{const k=l.ano+'|'+l.mineral+'|'+chaveEmp(l),b=baseDe.get(k);if(b===undefined||ORDEM_BASE.indexOf(l.base)<ORDEM_BASE.indexOf(b))baseDe.set(k,l.base)});
 return linhas.filter(l=>l.base===baseDe.get(l.ano+'|'+l.mineral+'|'+chaveEmp(l)));}

// A energia é da empresa no mineral, a mesma nas linhas de ROM e de beneficiada: soma uma vez por empresa, mineral e ano.
function energiaRecorte(linhas){const vistos=new Map();
 linhas.filter(l=>l.energia_mwh!=null).forEach(l=>vistos.set(l.ano+'|'+l.mineral+'|'+l.empresa+'|'+l.cnpj_raiz,l));
 const xs=[...vistos.values()];if(!xs.length)return '—';
 const obs=xs.filter(l=>String(l.energia_origem).startsWith('observada')).reduce((s,l)=>s+l.energia_mwh,0),tot=xs.reduce((s,l)=>s+l.energia_mwh,0);
 return num(tot/1000,0)+' GWh'+(tot?' · '+num(obs/tot*100,0)+' % CCEE':'')}
function estMetricas(linhas,estado){
 const proprias=linhas.filter(l=>!l.minerio_de_outro_mineral),comPub=proprias.filter(l=>l.diferenca_vs_publicado!=null);
 const cf=somaMapa(cfemUnica(proprias));
 const tile=faixa;
 if(daEmpresa()){
  const minerais=new Set(proprias.map(l=>l.mineral)),anos=[...new Set(proprias.map(l=>l.ano))].sort();
  const unica=proprias.length&&new Set(proprias.map(l=>l.ano+'|'+l.mineral+'|'+l.base)).size===1?proprias:null;
  const parcela=unica?unica.reduce((s,l)=>s+(l.parcela_do_estado||0),0):null;
  return [['a',t('es.m.minerais'),num(minerais.size),anos.length?t('es.m.mineraisSub',{anos:anos[0]+(anos.length>1?'–'+anos[anos.length-1]:'')}):'—'],
   ['b',t('es.m.parcela'),parcela==null?'—':pct(parcela),parcela==null?t('es.m.parcelaEscolha'):t('es.m.parcelaSub',{t:toneladas(unica.reduce((s,l)=>s+l.producao_t,0))})],
   ['c',t('es.m.cfem'),dinheiro(cf),t('es.m.cfemSubUnica')],
   ['d',t('es.m.publicado'),num(comPub.length),t('es.m.publicadoSub')],
   ['a',t('es.m.energia'),energiaRecorte(proprias),t('es.m.energiaSub')]].map(tile).join('');}
 const empresas=new Set(proprias.map(chaveEmp));
 const tot=estado.reduce((s,e)=>s+e.producao_estado_t-e.minerio_de_outro_mineral_t,0),div=estado.reduce((s,e)=>s+e.dividida_por_empresa_t,0);
 return [
  ['a',t('es.m.empresas'),num(empresas.size),t('es.m.empresasSub')],
  ['b',t('es.m.cobertura'),tot?pct(div/tot):'—',t('es.m.coberturaSub')],
  ['c',t('es.m.cfem'),dinheiro(cf),t('es.m.cfemSubUnica')],
  ['d',t('es.m.publicado'),num(comPub.length),t('es.m.publicadoSub')],
  ['a',t('es.m.energia'),energiaRecorte(proprias),t('es.m.energiaSub')],
 ].map(tile).join('');}

// Síntese da estimada numa frase. Empresa: o mineral de maior CFEM no recorte (na base preferida), com a parcela do estado.
// Todas: quantas empresas, quem lidera pela CFEM e quanto as cinco maiores concentram.
function estSintese(linhas,estado){
 const proprias=linhas.filter(l=>!l.minerio_de_outro_mineral);if(!proprias.length)return t('es.sint.vazio');
 const ano=el('es-ano').value,base=el('es-base').value,rec=[ano||t('es.todosAnos'),base?rotuloBase(base):t('es.todasBases')].join(' · ');
 if(daEmpresa()){const l=naBasePreferida(proprias).sort((a,b)=>(b.cfem_brl||0)-(a.cfem_brl||0))[0],outros=new Set(proprias.map(x=>x.mineral)).size-1;
  return t('es.sint.empresa',{nome:ctx.nome,mineral:l.mineral,ano:String(l.ano),t:toneladas(l.producao_t),parcela:pct(l.parcela_do_estado),base:rotuloBase(l.base)})
   +(outros>0?' '+t('es.sint.outros',{n:String(outros)}):'')}
 const cf=[...cfemUnica(proprias).entries()].sort((a,b)=>b[1]-a[1]),tot=cf.reduce((s,x)=>s+x[1],0),top5=cf.slice(0,5).reduce((s,x)=>s+x[1],0);
 const nome=k=>{const l=proprias.find(x=>chaveEmp(x)===k);return l?l.empresa:k};
 void estado;
 return t('es.sint.todas',{rec,n:num(cf.length),lider:cf.length?nome(cf[0][0]):'—',cfem:cf.length?dinheiro(cf[0][1]):'—',p5:tot?pct(top5/tot):'—'})}

// Com um mineral escolhido, a barra é a produção (t) — comparável dentro do mineral. Sem mineral, toneladas de areia e de ouro não se
// comparam: a barra vira a CFEM paga, que está em R$ para todos. Com uma empresa só, as barras são os anos (ou os minerais).
function estBarras(linhas){
 const min=el('es-min').value,proprias=linhas.filter(l=>!l.minerio_de_outro_mineral),uma=daEmpresa();
 el('es-barrasT').textContent=min?(uma?t('es.barrasAnosT',{mineral:min}):t('es.barrasT',{mineral:min})):(uma?t('es.barrasMineraisT'):t('es.barrasCfemT'));
 el('es-barrasS').textContent=min?t('es.barrasS'):t('es.barrasCfemS');
 let itens;
 // Toda base aparece separada (empresa: "ano · base"); com "Todas as bases", cada empresa entra na base preferida — toneladas de ROM
 // e de beneficiada não se somam.
 if(min){const g=new Map();(uma?proprias:naBasePreferida(proprias)).forEach(l=>{const k=uma?l.ano+' · '+rotuloBase(l.base):chaveEmp(l);g.set(k,(g.get(k)||0)+l.producao_t)});
  itens=[...g.entries()].filter(([,v])=>v>0).sort((a,b)=>uma?String(a[0]).localeCompare(String(b[0])):b[1]-a[1]).slice(0,15)}
 else itens=[...cfemUnica(proprias,l=>uma?l.mineral:chaveEmp(l)).entries()].filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]).slice(0,15);
 if(!itens.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const max=Math.max(...itens.map(x=>x[1])),rot=uma?k=>k:rotulosPorChave(proprias);
 return itens.map(([e,v])=>`<div class="bar-row"><span class="bar-label" title="${escape(rot(e))}">${uma?escape(e):nomeEmp(rot(e),e)}</span>`
  +`<div class="bar-track"><div class="bar-fill completo" style="width:${v/max*100}%"></div></div>`
  +`<span class="bar-value">${escape(min?toneladas(v):dinheiro(v))}</span></div>`).join('');}

function estCobertura(estado){
 const itens=estado.filter(e=>e.producao_estado_t>0).sort((a,b)=>b.producao_estado_t-a.producao_estado_t).slice(0,20);
 if(!itens.length)return `<p class="mk-note">${escape(t('ep.vazio'))}</p>`;
 const ano=el('es-ano').value;
 return itens.map(e=>{const parte=e.producao_estado_t-e.minerio_de_outro_mineral_t,p=parte?e.dividida_por_empresa_t/parte:0;
  return `<div class="bar-row"><span class="bar-label">${escape(e.mineral)} · ${escape(rotuloBase(e.base))}${ano?'':' · '+e.ano}</span>`
   +`<div class="bar-track"><div class="bar-fill ${p>=0.99?'completo':'parcial'}" style="width:${p*100}%"></div></div>`
   +`<span class="bar-value">${escape(pct(p))} · ${escape(toneladas(e.producao_estado_t))}</span></div>`
   +(e.minerio_de_outro_mineral_t?`<p class="mk-note">${escape(t('es.outroMineral',{t:toneladas(e.minerio_de_outro_mineral_t)}))}</p>`:'')
   +(e.empresas===0?`<p class="mk-note">${escape(e.situacao)}</p>`:'')}).join('');}

// Tabela paginada (25 linhas): a versão anterior despejava 200 linhas e a página não acabava; a exportação leva o recorte inteiro.
const POR_PAG=25;let estPag=0;
function estTabela(linhas){
 const ordem=[...linhas].sort((a,b)=>b.ano-a.ano||a.mineral.localeCompare(b.mineral)||a.base.localeCompare(b.base)||b.producao_t-a.producao_t);
 const pags=Math.max(1,Math.ceil(ordem.length/POR_PAG));estPag=Math.min(estPag,pags-1);const ini=estPag*POR_PAG;
 const cab=[t('es.h.ano'),t('es.h.mineral'),t('es.h.base'),t('es.h.empresa'),t('es.h.cnpj'),t('es.h.producao'),t('es.h.parcela'),
  t('es.h.processos'),t('es.h.municipios'),t('es.h.cfem'),t('es.h.energia'),t('es.h.coef')];
 const corpo=ordem.slice(ini,ini+POR_PAG).map(l=>`<tr><td>${l.ano}</td><td>${escape(l.mineral)}</td><td>${escape(rotuloBase(l.base))}</td>`
  +`<td>${nomeEmp(l.empresa,l.cnpj_raiz)}${l.minerio_de_outro_mineral?` <span class="pill" title="${escape(t('es.outroMineralTip'))}">${escape(t('es.outroMineralPill'))}</span>`:''}</td>`
  +`<td>${escape(l.cnpj_raiz||'—')}</td><td class="num">${escape(toneladas(l.producao_t))} <span class="ea-est" title="${escape(t('ea.estimativaTip'))}">${escape(t('ea.estimativa'))}</span></td><td class="num">${escape(pct(l.parcela_do_estado))}</td>`
  +`<td class="num">${num(l.processos)}</td><td>${escape(l.municipios||'—')}</td><td class="num">${escape(dinheiro(l.cfem_brl))}</td>`
  +`<td class="num">${l.energia_mwh==null?'—':escape(num(l.energia_mwh))+' MWh'}${l.energia_origem?` <span class="pill" title="${escape(l.energia_nota||'')}">${escape(rotuloEnergia(l.energia_origem))}</span>`:''}</td>`
  +`<td class="num">${l.coeficiente_mwh_t==null||l.coeficiente_mwh_t===''?'—':escape(coef(l.coeficiente_mwh_t))}</td></tr>`).join('');
 el('es-count').textContent=t('ea.es.linhas',{de:num(ordem.length?ini+1:0),ate:num(Math.min(ini+POR_PAG,ordem.length)),n:num(ordem.length)});
 const pager=pags>1?`<div class="ea-pag"><button type="button" class="link-button" data-es-pag="-1" ${estPag?'':'disabled'}>← ${escape(t('ea.anterior'))}</button>`
  +`<span>${escape(t('ea.pagina',{p:String(estPag+1),n:String(pags)}))}</span><button type="button" class="link-button" data-es-pag="1" ${estPag<pags-1?'':'disabled'}>${escape(t('ea.proxima'))} →</button></div>`:'';
 return `<table><thead><tr>${cab.map(c=>`<th>${escape(c)}</th>`).join('')}</tr></thead><tbody>${corpo||`<tr><td colspan="12" class="muted">${escape(t('ep.vazio'))}</td></tr>`}</tbody></table>${pager}`;}

function estPublicado(linhas){
 const com=linhas.filter(l=>l.publicado_t!=null).sort((a,b)=>b.ano-a.ano||a.mineral.localeCompare(b.mineral));
 if(!com.length)return `<p class="mk-note">${escape(t('es.pubVazio'))}</p>`;
 return `<table><thead><tr>${[t('es.h.ano'),t('es.h.mineral'),t('es.h.empresa'),t('es.h.producao'),t('es.h.publicado'),t('es.h.diferenca'),t('es.h.fonte')]
   .map(c=>`<th>${escape(c)}</th>`).join('')}</tr></thead><tbody>`
  +com.map(l=>{const d=l.diferenca_vs_publicado,fora=Math.abs(d)>0.1;
   return `<tr><td>${l.ano}</td><td>${escape(l.mineral)}</td><td>${nomeEmp(l.empresa,l.cnpj_raiz)}</td><td class="num">${escape(toneladas(l.producao_t))}</td>`
    +`<td class="num">${escape(toneladas(l.publicado_t))}</td><td class="num"${fora?' style="font-weight:700"':''}>${d>0?'+':''}${escape(num(d*100,0))} %</td>`
    +`<td>${l.publicado_url?`<a href="${escape(l.publicado_url)}" target="_blank" rel="noopener noreferrer">${escape(l.publicado_fonte)}</a>`:escape(l.publicado_fonte)}</td></tr>`}).join('')
  +'</tbody></table>';}

const TIPOS_ESTIMADA={ano:'inteiro',cnpj_raiz:'id',producao_t:'numero',parcela_do_estado:'numero',processos:'inteiro',cfem_brl:'numero',
 minerio_de_outro_mineral:'bool',publicado_t:'numero',diferenca_vs_publicado:'numero',energia_mwh:'numero',coeficiente_mwh_t:'numero'};
function estExportar(linhas){
 const colunas=[...est.colunas.map(c=>({id:c,tipo:TIPOS_ESTIMADA[c]||'texto'})),
  ...tipadas([['natureza','texto'],['escopo','texto'],['filtro_ano','texto'],['filtro_base','texto'],['filtro_mineral','texto'],['filtro_busca','texto'],['fonte','texto'],['data_pacote','texto']])];
 const rec={natureza:t('ea.exp.naturezaEstimada'),escopo:daEmpresa()?ctx.cnpj:'todas',filtro_ano:el('es-ano').value||null,filtro_base:el('es-base').value||null,
  filtro_mineral:el('es-min').value||null,filtro_busca:daEmpresa()?null:el('es-busca').value.trim()||null,fonte:t('ea.exp.fonteEstimada'),data_pacote:dados.meta.built_on};
 baixarCsv(`minera-goias-producao-estimada-amb-cfem${daEmpresa()?'-'+ctx.cnpj:''}.csv`,{colunas,linhas:linhas.map(l=>({...l,...rec}))});}

/* Energia: uma por empresa, mineral e ano (a mesma nas linhas de ROM e de beneficiada). O coeficiente é lido na base em que a energia
   foi dividida — beneficiada, contido (nióbio) ou ROM, nessa ordem —, salvo quando o filtro de base escolhe outra. */
function baseDaEnergia(linhas){const m=new Map();
 linhas.filter(l=>l.energia_mwh!=null&&!l.minerio_de_outro_mineral).forEach(l=>{const k=l.ano+'|'+l.mineral,b=m.get(k);
  if(!b||ORDEM_BASE.indexOf(l.base)<ORDEM_BASE.indexOf(b))m.set(k,l.base)});return m}
const observada=l=>String(l.energia_origem).startsWith('observada');
const foraDaMedia=l=>/fora da média/.test(l.energia_nota||'');
// A média do mineral usa só a carga que é inteira do mineral (empresa de um mineral só) ou separada por ramo e município — como na geração.
const deReferencia=l=>(l.energia_origem==='observada_ccee'||l.energia_origem==='observada_ccee_separada')&&!foraDaMedia(l);
function linhasDeEnergia(linhas){const base=el('es-base').value,bm=baseDaEnergia(est.linhas);
 return linhas.filter(l=>l.energia_mwh!=null&&!l.minerio_de_outro_mineral&&l.base===(base||bm.get(l.ano+'|'+l.mineral)))}

function estEnergia(linhas){
 const g=new Map(),uma=daEmpresa();
 linhasDeEnergia(linhas).forEach(l=>{const k=uma?l.ano+' · '+l.mineral:chaveEmp(l),a=g.get(k)||{obs:0,est:0};a[observada(l)?'obs':'est']+=l.energia_mwh;g.set(k,a)});
 const itens=[...g.entries()].map(([e,a])=>[e,a,a.obs+a.est]).filter(x=>x[2]>0).sort((a,b)=>uma?String(b[0]).localeCompare(String(a[0])):b[2]-a[2]).slice(0,15);
 if(!itens.length)return `<p class="mk-note">${escape(t('ea.es.semEnergia'))}</p>`;
 const max=Math.max(...itens.map(x=>x[2])),rot=uma?k=>k:rotulosPorChave(linhas);
 return itens.map(([e,a,tot])=>`<div class="bar-row"><span class="bar-label" title="${escape(rot(e))}">${uma?escape(e):nomeEmp(rot(e),e)}</span>`
  +`<div class="bar-track"><div class="bar-fill parcial" style="width:${tot/max*100}%;position:relative">`
  +`<div class="bar-fill completo" style="width:${tot?a.obs/tot*100:0}%;position:absolute;left:0;top:0;height:100%"></div></div></div>`
  +`<span class="bar-value">${escape(num(tot))} MWh</span></div>`).join('');}

// Coeficiente por empresa no mineral escolhido; a média de referência é sempre a do mineral entre todas as empresas (mesmo ano e base),
// para a empresa selecionada ser lida contra o setor.
function estCoef(linhas){
 const min=el('es-min').value;
 el('es-coefT').textContent=min?t('es.coefT',{mineral:min}):t('es.coefTodosT');
 el('es-coefS').textContent=min?t('es.coefS'):t('es.coefTodosS');
 if(!min)return `<p class="mk-note">${escape(t('es.coefEscolha'))}</p>`;
 const xs=linhasDeEnergia(linhas).filter(l=>l.coeficiente_mwh_t!=null&&l.coeficiente_mwh_t!=='').sort((a,b)=>b.coeficiente_mwh_t-a.coeficiente_mwh_t);
 const ano=el('es-ano').value;
 const universo=linhasDeEnergia(est.linhas.filter(l=>l.mineral===min&&(!ano||String(l.ano)===ano))).filter(l=>l.coeficiente_mwh_t!=null&&l.coeficiente_mwh_t!=='');
 const ref=universo.filter(deReferencia),media=ref.length?ref.reduce((s,l)=>s+l.coeficiente_mwh_t,0)/ref.length:null;
 if(!xs.length)return (media!=null?`<p class="mk-note">${escape(t('es.coefMedia',{v:coef(media),n:String(ref.length)}))}</p>`:'')+`<p class="mk-note">${escape(t('ea.es.semEnergia'))}</p>`;
 const max=Math.max(xs[0].coeficiente_mwh_t,media||0);
 return (media!=null?`<p class="mk-note">${escape(t('es.coefMedia',{v:coef(media),n:String(ref.length)}))}</p>`:'')
  +xs.slice(0,20).map(l=>`<div class="bar-row"><span class="bar-label" title="${escape(l.empresa+' · '+(l.energia_nota||''))}">${nomeEmp(l.empresa,l.cnpj_raiz)}${l.ano?' · '+l.ano:''}</span>`
  +`<div class="bar-track"><div class="bar-fill ${observada(l)?'completo':'parcial'}" style="width:${l.coeficiente_mwh_t/max*100}%"></div></div>`
  +`<span class="bar-value">${escape(coef(l.coeficiente_mwh_t))}${foraDaMedia(l)?' *':''}</span></div>`).join('')
  +(xs.some(foraDaMedia)?`<p class="mk-note">${escape(t('es.coefFora'))}</p>`:'');}

function estReferencias(){
 const ano=el('es-ano').value,base=el('es-base').value,bm=baseDaEnergia(est.linhas);
 const xs=est.linhas.filter(l=>l.energia_mwh!=null&&!l.minerio_de_outro_mineral&&(!ano||String(l.ano)===ano)&&l.base===(base||bm.get(l.ano+'|'+l.mineral)));
 const g=new Map();
 xs.forEach(l=>{const k=l.ano+'|'+l.mineral+'|'+l.base;const a=g.get(k)||{ano:l.ano,mineral:l.mineral,base:l.base,obs:[],nEst:0,energia:0,prod:0};
  if(deReferencia(l))a.obs.push(l.coeficiente_mwh_t);if(!observada(l))a.nEst++;a.energia+=l.energia_mwh;a.prod+=l.producao_t;g.set(k,a)});
 const rows=[...g.values()].sort((a,b)=>b.ano-a.ano||b.energia-a.energia);
 if(!rows.length)return `<p class="mk-note">${escape(t('ea.es.semEnergia'))}</p>`;
 return `<table><thead><tr>${[t('es.h.ano'),t('es.h.mineral'),t('es.h.base'),t('es.h.media'),t('es.h.faixa'),t('es.h.nObs'),t('es.h.nEst'),t('es.h.energiaTot'),t('es.h.coefSetor')]
  .map(c=>`<th>${escape(c)}</th>`).join('')}</tr></thead><tbody>`
  +rows.map(r=>{const m=r.obs.length?r.obs.reduce((s,v)=>s+v,0)/r.obs.length:null;
   return `<tr><td>${r.ano}</td><td>${escape(r.mineral)}</td><td>${escape(rotuloBase(r.base))}</td><td class="num">${m==null?'—':escape(coef(m))}</td>`
    +`<td class="num">${r.obs.length?escape(coef(Math.min(...r.obs))+' – '+coef(Math.max(...r.obs))):'—'}</td><td class="num">${r.obs.length}</td><td class="num">${r.nEst}</td>`
    +`<td class="num">${escape(num(r.energia/1000,1))} GWh</td><td class="num">${r.prod?escape(coef(r.energia/r.prod)):'—'}</td></tr>`}).join('')
  +'</tbody></table>';}

// troca só a página da tabela (os filtros e os gráficos ficam)
function estDesenharPag(linhas){el('es-tabela').querySelectorAll('[data-es-pag]').forEach(b=>b.onclick=()=>{estPag+=+b.dataset.esPag;el('es-tabela').innerHTML=estTabela(linhas);estDesenharPag(linhas)})}
let estPadrao=null;   // ano mais recente + produção beneficiada: o recorte que se lê sem somar coisas diferentes
function estDesenhar(){
 if(!est)return;
 const box=el('es-indisp'),daEmp=daEmpresa()?est.linhas.filter(l=>l.cnpj_raiz===ctx.cnpj):null;
 if(daEmp&&!daEmp.length){
  indisponivel(box,t('ea.indisp.estimada',{n:num(new Set(est.linhas.filter(l=>l.cnpj_raiz).map(l=>l.cnpj_raiz)).size)}),t('ea.indisp.verTodas'));
  ['es-sintese','es-metrics','es-barras','es-cobertura','es-energia','es-coef','es-ref','es-tabela','es-publicado','es-count','es-context'].forEach(id=>{el(id).innerHTML='';el(id).textContent=''});
  el('es-content').hidden=true;return}
 box.hidden=true;box.innerHTML='';el('es-content').hidden=false;
 el('es-busca-box').hidden=daEmpresa();
 const linhas=estFiltradas(),estado=estEstado();
 el('es-sintese').textContent=estSintese(linhas,estado);
 el('es-metrics').innerHTML=estMetricas(linhas,estado);
 el('es-barras').innerHTML=estBarras(linhas);
 el('es-cobertura').innerHTML=estCobertura(estado);
 el('es-energia').innerHTML=estEnergia(linhas);
 el('es-coef').innerHTML=estCoef(linhas);
 el('es-ref').innerHTML=estReferencias();
 el('es-tabela').innerHTML=estTabela(linhas);
 el('es-tabela').querySelectorAll('[data-es-pag]').forEach(b=>b.onclick=()=>{estPag+=+b.dataset.esPag;el('es-tabela').innerHTML=estTabela(linhas);estDesenharPag(linhas)});
 el('es-publicado').innerHTML=estPublicado(linhas);
 const partes=[el('es-ano').value,el('es-base').value&&rotuloBase(el('es-base').value),el('es-min').value,daEmpresa()?'':el('es-busca').value.trim()].filter(Boolean);
 el('es-context').textContent=(daEmpresa()?t('ea.escopoEmpresaCtx',{nome:ctx.nome}):t('ea.escopoTodasCtx'))+(partes.length?' · '+t('pn.cut')+' '+partes.join(' · '):'');
 el('es-export').onclick=()=>estExportar(linhas);}

// Ao recortar numa empresa, o filtro de ano/base em vigor pode não ter linha dela (só ROM, ou outro ano): abre-se para todos os anos e bases,
// em vez de mostrar uma análise vazia. O filtro de mineral também se abre se a empresa não tem o mineral escolhido.
function ajustarFiltrosEmpresa(nova){
 if(!est||!daEmpresa())return;
 const ls=est.linhas.filter(l=>l.cnpj_raiz===ctx.cnpj);if(!ls.length)return;
 if(nova){el('es-ano').value=String(Math.max(...ls.map(l=>l.ano)));el('es-base').value=''}
 if(el('es-min').value&&!ls.some(l=>l.mineral===el('es-min').value))el('es-min').value='';
 if(!estFiltradas().length){el('es-ano').value='';el('es-base').value=''}}

function estMontar(){
 const bloco=dados.estimada;
 if(!bloco){el('es-error').textContent=t('es.semDados');el('es-loading').hidden=true;return}
 est={colunas:bloco.colunas,linhas:bloco.linhas.map(r=>linhaObj(bloco.colunas,r)),estado:bloco.estado.map(r=>linhaObj(bloco.estado_colunas,r))};
 const anos=[...new Set(est.linhas.map(l=>l.ano))].sort((a,b)=>b-a),minerais=[...new Set(est.linhas.map(l=>l.mineral))].sort((a,b)=>a.localeCompare(b,'pt'));
 preencher(el('es-ano'),anos.map(a=>[String(a),String(a)]),t('es.todosAnos'));
 preencher(el('es-base'),[['beneficiada',t('es.base.beneficiada')],['ROM',t('es.base.rom')],['conteudo_mineral',t('es.base.contido')]],t('es.todasBases'));
 preencher(el('es-min'),minerais.map(m=>[m,m]),t('es.todosMinerais'));
 estPadrao=()=>{el('es-ano').value=String(anos[0]);el('es-base').value='beneficiada'};estPadrao();
 ['es-ano','es-base','es-min'].forEach(id=>el(id).onchange=()=>{estPag=0;estDesenhar()});
 let timer;el('es-busca').oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>{estPag=0;estDesenhar()},300)};
 el('es-reset').onclick=()=>{estPadrao();el('es-min').value='';el('es-busca').value='';ajustarFiltrosEmpresa(true);estDesenhar()};
 el('es-nota').textContent=t('es.nota');
 el('es-fontes').textContent=t('ea.es.fontes')+' '+t('ea.es.correcaoCfem');
 el('es-loading').hidden=true;ajustarFiltrosEmpresa(true);estDesenhar();}

function montarDeclarada(){
 const anos=[...new Set(dados.linhas.map(l=>l.ano))].sort();
 const minerais=[...new Set(dados.linhas.map(l=>l.mineral).filter(Boolean))].sort();
 preencher(el('ep-ano'),anos.map(a=>[String(a),String(a)]),t('ep.todosAnos'));
 preencher(el('ep-min'),minerais.map(m=>[m,m]),t('ep.todosMinerais'));
 preencher(el('ep-qual'),QUALIDADES.map(q=>[q,rotuloQualidade(q)]),t('ep.todasQualidades'));
 ['ep-ano','ep-min','ep-qual'].forEach(id=>el(id).onchange=desenhar);
 el('ep-reset').onclick=()=>{['ep-ano','ep-min','ep-qual'].forEach(id=>el(id).value='');desenhar()};
 el('ep-nota').textContent=t('ep.nota');
 el('ep-fontes').textContent=t('ea.ep.fontes',{periodo:dados.meta.periodo_ccee.map(mesAno).join('–')});
 el('empresas-loading').hidden=true;desenhar();}

// ======================================================================= ganchos para a aba (empresas-atlas.js)
window.EmpresasAnalises={
 iniciar(d){dados=d;el('empresas-error').textContent='';el('es-error').textContent='';
  try{estMontar()}catch(e){el('es-error').textContent=e.message;console.error(e)}
  try{montarDeclarada()}catch(e){el('empresas-error').textContent=e.message;console.error(e)}},
 falhou(msg,tentar){for(const [id,ld] of [['empresas-error','empresas-loading'],['es-error','es-loading']]){
   el(ld).hidden=true;el(id).innerHTML=`${escape(msg)} <button type="button" class="btn outline">${escape(t('ea.tentarDeNovo'))}</button>`;
   el(id).querySelector('button').onclick=()=>{el(id).textContent='';el(ld).hidden=false;tentar()}}},
 // escopo da aba: {cnpj, nome, escopo:'empresa'|'todas'}; resumo(cnpj) devolve o HTML do que a base tem da empresa
 escopo(x){const antes=ctx.escopo+'|'+ctx.cnpj;Object.assign(ctx,x);const agora=ctx.escopo+'|'+ctx.cnpj;
  // outra empresa selecionada com "todas as empresas" no escopo não muda o universo da análise: filtros e página ficam
  const mudou=antes.split('|')[0]!==ctx.escopo||(ctx.escopo==='empresa'&&antes!==agora);if(mudou)estPag=0;
  if(!dados)return;
  // nova empresa no escopo: último ano dela, todas as bases; de volta a todas as empresas: o recorte padrão (último ano, beneficiada)
  if(mudou){if(daEmpresa())ajustarFiltrosEmpresa(true);else if(est&&ctx.escopo==='todas'&&antes.startsWith('empresa'))estPadrao()}
  estDesenhar();desenhar()},
 // a aba diz quais CNPJ raiz têm dossiê (empresas-atlas.js): {existe(cnpj), nome(cnpj)}
 definirLigacao(x){ligacao=x;if(dados){estDesenhar();desenhar()}},
 definirResumo(fn){ctx.resumo=fn},
 // para o dossiê e a comparação: as mesmas linhas desta análise (uma fonte só)
 estimadaDe:cnpj=>est?est.linhas.filter(l=>l.cnpj_raiz===cnpj&&!l.minerio_de_outro_mineral):[],
 declaradaDe:cnpj=>dados?dados.linhas.filter(l=>l.cnpj_raiz===cnpj):[],
 temDeclarada:cnpj=>!!dados&&dados.linhas.some(l=>l.cnpj_raiz===cnpj),
 temEstimada:cnpj=>!!est&&est.linhas.some(l=>l.cnpj_raiz===cnpj),
 pronto:()=>!!dados,
 periodoCcee:()=>dados?dados.meta.periodo_ccee.map(mesAno).join('–'):''};
})();
