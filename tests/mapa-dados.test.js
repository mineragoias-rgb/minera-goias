// Testes do carregador do Mapa Mineral (public/mapa-dados.js) com os arquivos de data/mapa e data/atlas.
// Decodifica cada camada como o navegador fará e confere contagem, coordenadas dentro de Goiás e atributos.
// Execução: node tests/mapa-dados.test.js
'use strict';
const fs = require('fs'), path = require('path');
const RAIZ = path.join(__dirname, '..');
const lerJson = p => JSON.parse(fs.readFileSync(path.join(RAIZ, p), 'utf8'));
const M = require(path.join(RAIZ, 'public', 'mapa-dados.js'));

const falhas = [];
let total = 0;
function ok(nome, condicao, detalhe) {
 total++;
 if (!condicao) falhas.push(nome + (detalhe ? ' — ' + detalhe : ''));
}
// Caixa de Goiás com folga (processos e linhas que cruzam a divisa saem um pouco).
const dentro = ([lat, lon]) => lat >= -20.0 && lat <= -12.0 && lon >= -53.6 && lon <= -45.5;
const MINIMO = {ponto: 1, linha: 2, poligono: 3};

function conferir(nome, camada, esperado) {
 ok(nome + ': contagem', camada.n === esperado, camada.n + ' ≠ ' + esperado);
 let semParte = 0, fora = 0, curtas = 0;
 for (let i = 0; i < camada.n; i++) {
  if (!camada.partes[i].length) semParte++;
  for (const parte of camada.partes[i]) {
   if (parte.length < MINIMO[camada.geometria]) curtas++;
   for (const p of parte) if (!dentro(p)) fora++;
  }
 }
 ok(nome + ': toda feição tem geometria', semParte === 0, semParte + ' sem parte');
 ok(nome + ': coordenadas em Goiás, na ordem [lat, lon]', fora === 0, fora + ' vértices fora');
 ok(nome + ': partes com vértices suficientes', curtas === 0, curtas + ' partes curtas');
 for (const c of camada.campos) {
  const v = camada.valor(0, c);
  ok(nome + ': campo ' + c + ' definido', v !== undefined);
  if (Array.isArray(v)) ok(nome + ': lista ' + c + ' sem índice perdido', v.every(x => x !== undefined));
 }
}

const catalogo = lerJson('data/mapa/catalogo.json');
const atlas = lerJson('data/atlas/atlas.json');
for (const entrada of catalogo.camadas) {
 const f = entrada.dados.formato;
 if (f === 'mapa-v1') {
  conferir(entrada.id, M.decodificar(lerJson(entrada.dados.arquivo), entrada), entrada.n_feicoes);
 } else if (f === 'processos-atlas') {
  // mesmo caminho do navegador: processes.js decodifica, mapa-dados.js adapta
  global.window = global;
  global.t = k => k;
  global.api = async () => lerJson('data/atlas/processes.json');
  require(path.join(RAIZ, 'public', 'processes.js'));
  global.loadProcesses().then(r => {
   const camada = M.doAtlas(entrada, null, r.records);
   conferir(entrada.id, camada, entrada.n_feicoes);
   ok('processos: grupo legível', M.GRUPOS_ATLAS.includes(camada.valor(0, 'grupo')));
   ok('processos: campo que a camada não tem vale undefined, sem erro', camada.valor(0, 'na_divisa') === undefined);
   fim();
  });
 } else {
  conferir(entrada.id, M.doAtlas(entrada, atlas), entrada.n_feicoes);
 }
}

// Atributos com dicionário, unidade convertida e lista alinhada.
const usinas = M.decodificar(lerJson('data/mapa/camadas/hidreletricas.json'));
const serra = [...Array(usinas.n).keys()].find(i => usinas.valor(i, 'nome') === 'Serra da Mesa');
ok('Serra da Mesa existe', serra !== undefined);
if (serra !== undefined) {
 ok('Serra da Mesa: 1.275 MW (kW ÷ 1.000)', usinas.valor(serra, 'potencia_mw') === 1275, usinas.valor(serra, 'potencia_mw'));
 ok('Serra da Mesa: UHE', usinas.valor(serra, 'tipo') === 'UHE');
}
const guias = M.decodificar(lerJson('data/mapa/camadas/guias_utilizacao.json'));
let desalinhadas = 0;
for (let i = 0; i < guias.n; i++) {
 const n = guias.valor(i, 'guias').length;
 if (guias.valor(i, 'quantidades').length !== n || guias.valor(i, 'prazos').length !== n || guias.valor(i, 'n_registros_fonte') !== n) desalinhadas++;
}
ok('guias: listas alinhadas com os registros da fonte', desalinhadas === 0, desalinhadas + ' processos');

// Ligações das tabelas.
const radar = lerJson('data/mapa/tabelas/radar_projetos.json');
const porProcesso = M.radarPorProcesso(radar);
const citados = new Set(radar.linhas.flatMap(p => p.processos));
ok('radar: todo processo citado está no índice', citados.size === porProcesso.size);
const complemento = M.complementoPorProcesso(lerJson('data/mapa/tabelas/processos_complemento.json'));
ok('complemento: um por processo do Atlas', complemento.size === lerJson('data/atlas/processes.json').n);
const exemplo = complemento.get('10670/1967');
ok('complemento: titular, municípios IBGE e mineral', exemplo && exemplo.titular && exemplo.municipios.every(c => /^\d{7}$/.test(c)) && Array.isArray(exemplo.mineral));

// Busca por identificador: mesma chave com ou sem pontos e zeros; código com zeros não vira outro código.
const id = (chaves, q) => M.casaId(chaves.map(M.chaveId), q);
ok('id: processo com pontos', id(['860337/2020'], '860.337/2020'));
ok('id: processo com zeros à esquerda', id(['9291/1967'], '009.291/1967'));
ok('id: começo do número do processo', id(['860337/2020'], '860337'));
ok('id: GO-0001 não casa com GO-0010', !id(['GO-0010'], 'GO-0001') && id(['GO-0001'], 'go-0001'));
ok('id: processo 9291/1967 não casa com 19291/1967', !id(['19291/1967'], '9291/1967'));
ok('id: trecho de nome', id(['Parque Nacional da Chapada dos Veadeiros'], 'chapada'));

let pendentes = catalogo.camadas.filter(e => e.dados.formato === 'processos-atlas').length;
function fim() {
 if (--pendentes > 0) return;
 if (falhas.length) {
  console.error(falhas.length + ' de ' + total + ' verificações falharam:\n' + falhas.join('\n'));
  process.exit(1);
 }
 console.log(total + ' verificações ok');
}
if (!pendentes) { pendentes = 1; fim(); }
