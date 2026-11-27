/* Exportações da aba Empresas, sem DOM e sem traduções (testáveis no Node: tests/js/exportacao.js).
   Uma tabela é {colunas:[{id,tipo,largura?}], linhas:[{<id>:valor}]}; tipos: 'texto', 'id' (identificador: sempre texto, nunca número),
   'numero', 'inteiro' e 'bool'. Vazio (null, '', NaN) é "sem dado" e sai vazio — nunca zero.
   - CSV para o Excel brasileiro: UTF-8 com BOM, separador ";", decimal "," e sem separador de milhar, cabeçalho na PRIMEIRA linha
     (sem linha de comentário), textos entre aspas. Texto que começa por = + - @ (ou tabulação/quebra de linha) ganha um apóstrofo na frente,
     para a planilha não o executar como fórmula; números nunca são alterados. No pandas: read_csv(f, sep=';', decimal=',',
     dtype={'cnpj_raiz': str}).
   - XLSX (Office Open XML, sem biblioteca): números como números, identificadores e textos como texto (nunca fórmula), primeira linha
     congelada e com filtro; várias abas (dados, dicionário de colunas, metadados).
   - Comparabilidade da produção declarada: só se comparam registros com a mesma chave (período, mineral, produto, medida, unidade,
     escopo, tipo de valor e nível); registros diferentes ficam em linhas diferentes, e nenhum é descartado. */
(()=>{'use strict';
const PERIGO=/^[=+\-@\t\r\n]/;
const textoSeguro=s=>PERIGO.test(s)?"'"+s:s;
const vazio=v=>v==null||v===''||(typeof v==='number'&&!Number.isFinite(v));
const ehNumero=tipo=>tipo==='numero'||tipo==='inteiro';
function numero(v){if(typeof v==='boolean')return null;const n=typeof v==='number'?v:typeof v==='string'&&v.trim()!==''?+v:NaN;return Number.isFinite(n)?n:null}
// até 6 casas, sem notação científica nem zeros à direita
function numeroTexto(n){let s=String(+n.toFixed(6));if(/e/i.test(s))s=n.toFixed(6).replace(/\.?0+$/,'');return s}

// ------------------------------------------------------------------ CSV
function celulaCsv(v,tipo){
 if(vazio(v))return '';
 if(ehNumero(tipo)){const n=numero(v);return n===null?'':numeroTexto(n).replace('.',',')}
 if(tipo==='bool')return v?'true':'false';
 let s=String(v);
 if(tipo!=='id')s=textoSeguro(s);
 s=s.replace(/\r\n?/g,'\n');
 return '"'+s.replace(/"/g,'""')+'"';}
function csv({colunas,linhas}){
 return '﻿'+[colunas.map(c=>c.id).join(';'),...linhas.map(l=>colunas.map(c=>celulaCsv(l[c.id],c.tipo)).join(';'))].join('\r\n')+'\r\n';}

// ------------------------------------------------------------------ ZIP (sem compressão) e XLSX
const CRC=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c>>>0}return t})();
function crc32(b){let c=0xFFFFFFFF;for(let i=0;i<b.length;i++)c=CRC[(c^b[i])&255]^(c>>>8);return (c^0xFFFFFFFF)>>>0}
function zip(arquivos,data=new Date()){
 const enc=new TextEncoder(),partes=[],central=[];let pos=0;
 const dt=((data.getFullYear()-1980)<<9)|((data.getMonth()+1)<<5)|data.getDate(),tm=(data.getHours()<<11)|(data.getMinutes()<<5)|(data.getSeconds()>>1);
 for(const a of arquivos){
  const nome=enc.encode(a.nome),dados=typeof a.dados==='string'?enc.encode(a.dados):a.dados,crc=crc32(dados);
  const lh=new DataView(new ArrayBuffer(30));
  lh.setUint32(0,0x04034b50,true);lh.setUint16(4,20,true);lh.setUint16(6,0x0800,true);lh.setUint16(8,0,true);lh.setUint16(10,tm,true);lh.setUint16(12,dt,true);
  lh.setUint32(14,crc,true);lh.setUint32(18,dados.length,true);lh.setUint32(22,dados.length,true);lh.setUint16(26,nome.length,true);lh.setUint16(28,0,true);
  partes.push(new Uint8Array(lh.buffer),nome,dados);
  const ch=new DataView(new ArrayBuffer(46));
  ch.setUint32(0,0x02014b50,true);ch.setUint16(4,20,true);ch.setUint16(6,20,true);ch.setUint16(8,0x0800,true);ch.setUint16(10,0,true);ch.setUint16(12,tm,true);ch.setUint16(14,dt,true);
  ch.setUint32(16,crc,true);ch.setUint32(20,dados.length,true);ch.setUint32(24,dados.length,true);ch.setUint16(28,nome.length,true);ch.setUint32(42,pos,true);
  central.push(new Uint8Array(ch.buffer),nome);pos+=30+nome.length+dados.length;}
 const tam=central.reduce((s,b)=>s+b.length,0),fim=new DataView(new ArrayBuffer(22));
 fim.setUint32(0,0x06054b50,true);fim.setUint16(8,arquivos.length,true);fim.setUint16(10,arquivos.length,true);fim.setUint32(12,tam,true);fim.setUint32(16,pos,true);
 const tudo=[...partes,...central,new Uint8Array(fim.buffer)],out=new Uint8Array(tudo.reduce((s,b)=>s+b.length,0));
 let o=0;for(const b of tudo){out.set(b,o);o+=b.length}
 return out;}

const NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main',NSR='http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const XML='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';
const xmlEsc=s=>String(s).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F￾￿]/g,'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])).replace(/\r/g,'&#13;');
const letra=j=>{let s='';j++;while(j){const m=(j-1)%26;s=String.fromCharCode(65+m)+s;j=Math.floor((j-1)/26)}return s};
// estilos: 0 normal, 1 cabeçalho em negrito, 2 texto (formato @, para o Excel não transformar o identificador em número ao editar)
const ESTILOS=XML+`<styleSheet xmlns="${NS}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>`
 +`<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>`
 +`<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>`
 +`<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>`
 +`<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
function celulaXlsx(v,tipo,ref){
 if(vazio(v))return '';
 if(ehNumero(tipo)){const n=numero(v);return n===null?'':`<c r="${ref}"><v>${n}</v></c>`}
 if(tipo==='bool')return `<c r="${ref}" t="b"><v>${v?1:0}</v></c>`;
 return `<c r="${ref}" t="inlineStr"${tipo==='id'?' s="2"':''}><is><t xml:space="preserve">${xmlEsc(v)}</t></is></c>`;}
const nomeAba=(n,i)=>(String(n||'Aba'+(i+1)).replace(/[\\/?*[\]:]/g,' ').trim().slice(0,31))||'Aba'+(i+1);
const intervalo=({colunas,linhas})=>`$A$1:$${letra(Math.max(0,colunas.length-1))}$${linhas.length+1}`;
function planilha(tab){
 const {colunas,linhas}=tab;
 const cols=`<cols>${colunas.map((c,j)=>`<col min="${j+1}" max="${j+1}" width="${c.largura||Math.min(48,Math.max(10,c.id.length+3))}" customWidth="1"/>`).join('')}</cols>`;
 const cab=`<row r="1">${colunas.map((c,j)=>`<c r="${letra(j)}1" t="inlineStr" s="1"><is><t>${xmlEsc(c.id)}</t></is></c>`).join('')}</row>`;
 const corpo=linhas.map((l,i)=>`<row r="${i+2}">${colunas.map((c,j)=>celulaXlsx(l[c.id],c.tipo,letra(j)+(i+2))).join('')}</row>`).join('');
 return XML+`<worksheet xmlns="${NS}" xmlns:r="${NSR}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>`
  +`${cols}<sheetData>${cab}${corpo}</sheetData>${linhas.length?`<autoFilter ref="${intervalo(tab).replace(/\$/g,'')}"/>`:''}</worksheet>`;}
// abas: [{nome, colunas, linhas}]
function xlsx(abas,data){
 const nomes=[];abas.forEach((a,i)=>{let n=nomeAba(a.nome,i),k=2;while(nomes.includes(n))n=nomeAba(a.nome,i).slice(0,28)+' '+k++;nomes.push(n)});
 const filtros=abas.map((a,i)=>a.linhas.length?`<definedName name="_xlnm._FilterDatabase" localSheetId="${i}" hidden="1">'${xmlEsc(nomes[i].replace(/'/g,"''"))}'!${intervalo(a)}</definedName>`:'').join('');
 return zip([
  {nome:'[Content_Types].xml',dados:XML+`<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>`
   +`<Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>`
   +`<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>`
   +abas.map((a,i)=>`<Override PartName="/xl/worksheets/sheet${i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')+`</Types>`},
  {nome:'_rels/.rels',dados:XML+`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${NSR}/officeDocument" Target="xl/workbook.xml"/></Relationships>`},
  {nome:'xl/workbook.xml',dados:XML+`<workbook xmlns="${NS}" xmlns:r="${NSR}"><sheets>${nomes.map((n,i)=>`<sheet name="${xmlEsc(n)}" sheetId="${i+1}" r:id="rId${i+1}"/>`).join('')}</sheets>`
   +(filtros?`<definedNames>${filtros}</definedNames>`:'')+`</workbook>`},
  {nome:'xl/_rels/workbook.xml.rels',dados:XML+`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">`
   +abas.map((a,i)=>`<Relationship Id="rId${i+1}" Type="${NSR}/worksheet" Target="worksheets/sheet${i+1}.xml"/>`).join('')
   +`<Relationship Id="rId${abas.length+1}" Type="${NSR}/styles" Target="styles.xml"/></Relationships>`},
  {nome:'xl/styles.xml',dados:ESTILOS},
  ...abas.map((a,i)=>({nome:`xl/worksheets/sheet${i+1}.xml`,dados:planilha(a)}))],data);}

// tabelas auxiliares: dicionário de colunas e metadados (item, valor)
const dicionario=(colunas,descricoes)=>({colunas:[{id:'coluna',tipo:'texto',largura:34},{id:'tipo',tipo:'texto',largura:10},{id:'descricao',tipo:'texto',largura:110}],
 linhas:colunas.map(c=>({coluna:c.id,tipo:c.tipo,descricao:(descricoes&&descricoes[c.id])||''}))});
const metadados=pares=>({colunas:[{id:'item',tipo:'texto',largura:30},{id:'valor',tipo:'texto',largura:120}],
 linhas:pares.filter(([,v])=>!vazio(v)).map(([item,valor])=>({item,valor:typeof valor==='object'?JSON.stringify(valor):String(valor)}))});

// ------------------------------------------------------------------ comparabilidade da produção declarada
const CAMPOS_DECLARADA=['periodo','mineral','produto','medida','unidade','escopo','tipo_valor','nivel'];
const chaveDeclarada=p=>CAMPOS_DECLARADA.map(c=>String(p[c]??'')).join('|');
// porEmpresa: [[registro,...], ...] na ordem das empresas. Devolve uma linha por chave, com TODOS os registros de cada empresa nela.
function gruposDeclarada(porEmpresa){
 const g=new Map();
 porEmpresa.forEach((rs,k)=>rs.forEach(p=>{const ch=chaveDeclarada(p);if(!g.has(ch))g.set(ch,{chave:ch,ref:p,por:porEmpresa.map(()=>[])});g.get(ch).por[k].push(p)}));
 return [...g.values()].map(x=>({...x,empresas:x.por.filter(r=>r.length).length,duplicado:x.por.some(r=>r.length>1)}));}
// Destaque do maior só quando ao menos dois valores são comparáveis: um registro por empresa e a mesma cobertura (meses), se houver.
function indiceMaior(valores,{meses=null}={}){
 const vs=valores.map(v=>vazio(v)?null:+v);
 if(vs.filter(v=>v!=null&&v>0).length<2)return -1;
 if(meses){const ms=new Set(meses.filter((m,k)=>vs[k]!=null));if(ms.size>1)return -1}
 const m=Math.max(...vs.filter(v=>v!=null));return vs.filter(v=>v===m).length===1?vs.indexOf(m):-1;}

window.EmpresasExportar={csv,xlsx,zip,crc32,celulaCsv,textoSeguro,dicionario,metadados,chaveDeclarada,gruposDeclarada,indiceMaior,CAMPOS_DECLARADA};
})();
