// Testes do motor de cálculo do simulador (public/simulador-engine.js).
// Os valores de referência foram extraídos de
// Squad 2/modello_reale/outputs/future/future_projection_by_mineral.csv, com as intensidades do coeficiente estadual
// do Squad 2 (Squad 2/intensidade_energetica/coeficiente_estadual_para_modelo_v1.csv), que o modelo usa desde 23/09/2026.
// Execução: node tests/simulador.test.js

// Energia total em MWh, por cenário, nos extremos do horizonte.
var MODELO_SQUAD2 = {
  conservador: { 2027: 4955895.571979, 2040: 9438041.460239 },
  referencia: { 2027: 5096572.178565, 2040: 11568669.759542 },
  expansao: { 2027: 5237259.737403, 2040: 14104142.171063 }
};

// Referência em 2040, por mineral.
var POR_MINERAL_2040 = {
  MIN_005: { producao: 6931318.960980, intensidade: 1.2224549, energia: 8473224.969393 },
  MIN_022: { producao: 256772.509133, intensidade: 10.1935643, energia: 2617427.094239 },
  MIN_049: { producao: 2385690.562801, intensidade: 0.1058698, energia: 252572.666740 },
  MIN_011: { producao: 27770.415338, intensidade: 7.0796276, energia: 196604.199726 },
  MIN_033: { producao: 106224.217691, intensidade: 0.2715090, energia: 28840.829443 }
};

function executarTestes(engine, parametros) {
  var falhas = [], total = 0;

  function ok(nome, condicao, detalhe) {
    total++;
    if (!condicao) falhas.push(nome + (detalhe ? ' — ' + detalhe : ''));
  }
  function perto(nome, obtido, esperado, tolerancia) {
    total++;
    var t = tolerancia === undefined ? 1e-9 : tolerancia;
    if (!(Math.abs(obtido - esperado) <= t)) {
      falhas.push(nome + ' — esperado ' + esperado + ', obtido ' + obtido);
    }
  }
  function lanca(nome, fn) {
    total++;
    try { fn(); falhas.push(nome + ' — deveria ter lançado erro'); } catch (e) { /* esperado */ }
  }

  // O simulador tem de devolver exatamente os números do modelo do Squad 2 quando
  // roda com as hipóteses padrão de cada cenário e sem ajuste de intensidade.
  Object.keys(MODELO_SQUAD2).forEach(function (scenario) {
    var r = engine.simular(parametros, { scenario: scenario });
    perto('reproduz o Squad 2 · ' + scenario + ' · 2027',
      r.serie[0].energia_mwh, MODELO_SQUAD2[scenario][2027], 1e-5);
    perto('reproduz o Squad 2 · ' + scenario + ' · 2040',
      r.serie[r.serie.length - 1].energia_mwh, MODELO_SQUAD2[scenario][2040], 1e-5);
  });

  var referencia = engine.simular(parametros, { scenario: 'referencia' });
  ok('horizonte cobre 2027 a 2040',
    referencia.anos.length === 14 && referencia.anos[0] === 2027 && referencia.anos[13] === 2040);
  perto('referência começa em 5,097 TWh', referencia.serie[0].energia_twh, 5.096572, 1e-6);
  perto('referência termina em 11,569 TWh', referencia.serie[13].energia_twh, 11.568670, 1e-6);

  var minerais2040 = engine.energiaPorMineral(referencia, 2040);
  ok('cobre os cinco minerais do modelo', minerais2040.length === 5, 'obtido ' + minerais2040.length);
  ok('a bauxita é a maior consumidora em 2040', minerais2040[0].mineral_id === 'MIN_005');
  ok('o níquel vem logo depois', minerais2040[1].mineral_id === 'MIN_022');
  minerais2040.forEach(function (m) {
    var esperado = POR_MINERAL_2040[m.mineral_id];
    perto('produção do Squad 2 · ' + m.mineral_id, m.producao_t, esperado.producao, 1e-5);
    perto('intensidade do Squad 2 · ' + m.mineral_id, m.intensidade_mwh_t, esperado.intensidade, 1e-6);
    perto('energia do Squad 2 · ' + m.mineral_id, m.energia_mwh, esperado.energia, 1e-5);
  });
  perto('a soma dos minerais reproduz o total do ano',
    minerais2040.reduce(function (s, m) { return s + m.energia_mwh; }, 0),
    referencia.serie[13].energia_mwh, 1e-6);

  // Amostra fora dos extremos, para pegar erro no expoente do crescimento.
  var expansao = engine.simular(parametros, { scenario: 'expansao' });
  var niquel2033 = engine.energiaPorMineral(expansao, 2033).filter(function (m) {
    return m.mineral_id === 'MIN_022';
  })[0];
  perto('níquel · expansão · 2033 · produção', niquel2033.producao_t, 237846.903280691, 1e-6);
  perto('níquel · expansão · 2033 · intensidade', niquel2033.intensidade_mwh_t, 10.428853602, 1e-7);
  perto('níquel · expansão · 2033 · energia', niquel2033.energia_mwh, 2480470.534064465, 1e-5);

  // Controle 1: cenário. O ajuste de crescimento é em pontos percentuais.
  var conservador = engine.simular(parametros, { scenario: 'conservador' });
  ok('conservador fica abaixo de referência em 2040',
    conservador.serie[13].energia_mwh < referencia.serie[13].energia_mwh);
  ok('expansão fica acima de referência em 2040',
    expansao.serie[13].energia_mwh > referencia.serie[13].energia_mwh);
  perto('o ajuste de crescimento do conservador é -2 pontos', conservador.crescimentoAjuste, -0.02);

  // Controle 2: eficiência.
  var semGanho = engine.simular(parametros, { scenario: 'referencia', ganhoEficiencia: 0 });
  ok('sem ganho de eficiência a energia sobe mais',
    semGanho.serie[13].energia_mwh > referencia.serie[13].energia_mwh);
  ok('a eficiência não altera a produção física',
    Math.abs(engine.energiaPorMineral(semGanho, 2040)[0].producao_t
      - engine.energiaPorMineral(referencia, 2040)[0].producao_t) < 1e-6);
  perto('sem ganho a intensidade fica na base',
    engine.energiaPorMineral(semGanho, 2040).filter(function (m) { return m.mineral_id === 'MIN_049'; })[0].intensidade_mwh_t,
    0.121246, 1e-12);

  // Controle 3: sensibilidade da intensidade, um mineral por vez.
  var ajustado = engine.simular(parametros, {
    scenario: 'referencia',
    ajustesIntensidade: { MIN_022: 10 }
  });
  var niquelAjustado = engine.energiaPorMineral(ajustado, 2040).filter(function (m) {
    return m.mineral_id === 'MIN_022';
  })[0];
  perto('+10% na intensidade do níquel aplica a fórmula do contrato',
    niquelAjustado.energia_mwh, POR_MINERAL_2040.MIN_022.energia * 1.10, 1e-5);
  var fosfatoIntacto = engine.energiaPorMineral(ajustado, 2040).filter(function (m) {
    return m.mineral_id === 'MIN_049';
  })[0];
  perto('ajustar um mineral não mexe nos outros',
    fosfatoIntacto.energia_mwh, POR_MINERAL_2040.MIN_049.energia, 1e-6);
  perto('o total sobe só o efeito do mineral ajustado',
    ajustado.serie[13].energia_mwh,
    referencia.serie[13].energia_mwh + POR_MINERAL_2040.MIN_022.energia * 0.10, 1e-5);

  var faixa = engine.faixaSensibilidade(parametros);
  ok('a faixa de sensibilidade vem do contrato do Squad 2',
    faixa.minimo === -10 && faixa.maximo === 10 && faixa.passo === 1);

  var r = engine.resumo(referencia);
  perto('resumo usa o último ano', r.energiaFinalTwh, referencia.serie[13].energia_twh, 1e-12);
  perto('energia acumulada soma os catorze anos', r.energiaAcumuladaTwh,
    referencia.serie.reduce(function (s, x) { return s + x.energia_twh; }, 0), 1e-9);
  ok('a variação até 2040 é positiva no cenário de referência', r.variacaoPercentual > 0);

  var todos = engine.simularCenarios(parametros, 0.005, { MIN_005: -3 });
  ok('simularCenarios devolve os três cenários', todos.length === 3);
  ok('os três usam a mesma hipótese de eficiência',
    todos.every(function (x) { return x.ganhoEficiencia === 0.005; }));
  ok('os três usam o mesmo ajuste de intensidade',
    todos.every(function (x) { return x.ajustesIntensidade.MIN_005 === -3; }));

  // A energia agrega; as toneladas não, porque as bases de produção são diferentes.
  ok('a série anual não expõe soma de toneladas', !('producao_t' in referencia.serie[0]));
  ok('cada mineral declara a própria base de produção',
    minerais2040.every(function (m) { return !!m.production_basis; }));
  ok('o cobre usa conteúdo mineral',
    minerais2040.filter(function (m) { return m.mineral_id === 'MIN_011'; })[0].production_basis === 'conteudo_mineral');

  perto('a conferência gravada nos parâmetros confere com o cálculo',
    parametros.conferencia_modelo.referencia_2040_twh, referencia.serie[13].energia_twh, 1e-6);

  lanca('cenário inexistente é rejeitado', function () {
    engine.simular(parametros, { scenario: 'otimista' });
  });
  lanca('ganho fora da faixa é rejeitado', function () {
    engine.simular(parametros, { scenario: 'referencia', ganhoEficiencia: 1.5 });
  });
  lanca('ajuste de intensidade acima do contrato é rejeitado', function () {
    engine.simular(parametros, { scenario: 'referencia', ajustesIntensidade: { MIN_022: 25 } });
  });
  lanca('parâmetros sem minerais são rejeitados', function () {
    engine.validar({ versao: '0', horizonte: {}, cenarios: [], minerais: [], fontes: [], sensibilidade_intensidade: {} });
  });

  return { total: total, falhas: falhas };
}

if (typeof module === 'object' && module.exports) {
  module.exports = executarTestes;
  if (require.main === module) {
    var fs = require('fs'), path = require('path');
    var engine = require(path.join(__dirname, '..', 'public', 'simulador-engine.js'));
    var parametros = JSON.parse(fs.readFileSync(
      path.join(__dirname, '..', 'public', 'data', 'simulador', 'parametros_v1.json'), 'utf8'));
    var r = executarTestes(engine, parametros);
    r.falhas.forEach(function (f) { console.error('FALHOU: ' + f); });
    console.log((r.total - r.falhas.length) + '/' + r.total + ' verificações passaram.');
    process.exit(r.falhas.length ? 1 : 0);
  }
}
