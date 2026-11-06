(function (raiz) {
  'use strict';

  var MWH_POR_TWH = 1e6;

  function anosDoHorizonte(parametros) {
    var anos = [], a;
    for (a = parametros.horizonte.inicio; a <= parametros.horizonte.fim; a++) anos.push(a);
    return anos;
  }

  function cenarioPorId(parametros, scenario) {
    for (var i = 0; i < parametros.cenarios.length; i++) {
      if (parametros.cenarios[i].scenario === scenario) return parametros.cenarios[i];
    }
    throw new Error('Cenário desconhecido nos parâmetros: ' + scenario);
  }

  // Produção do Squad 2: último ano observado composto pelo crescimento histórico
  // do mineral, ajustado em pontos percentuais pelo cenário.
  function producao(mineral, crescimentoAjustado, ano) {
    return mineral.producao_base_t * Math.pow(1 + crescimentoAjustado, ano - mineral.ano_base);
  }

  // IE(t) = IE_base x (1 + ajuste_pct/100) x (1 - g)^(t - ano_base)
  function intensidade(mineral, ganho, ajustePct, ano) {
    return mineral.energy_intensity_mwh_t
      * (1 + (ajustePct || 0) / 100)
      * Math.pow(1 - ganho, ano - mineral.ano_base);
  }

  function validar(parametros) {
    if (!parametros || typeof parametros !== 'object') throw new Error('Parâmetros ausentes.');
    ['versao', 'horizonte', 'cenarios', 'minerais', 'fontes', 'sensibilidade_intensidade'].forEach(function (campo) {
      if (!(campo in parametros)) throw new Error('Parâmetros sem o campo obrigatório: ' + campo);
    });
    if (!parametros.minerais.length) throw new Error('Parâmetros sem nenhum mineral.');
    parametros.minerais.forEach(function (m) {
      if (!(m.producao_base_t >= 0)) throw new Error('Produção base inválida em ' + m.mineral_id);
      if (!(m.energy_intensity_mwh_t >= 0)) throw new Error('Intensidade inválida em ' + m.mineral_id);
      if (typeof m.crescimento_historico !== 'number') throw new Error('Crescimento ausente em ' + m.mineral_id);
      if (typeof m.ano_base !== 'number') throw new Error('Ano base ausente em ' + m.mineral_id);
    });
    return parametros;
  }

  function faixaSensibilidade(parametros) {
    var s = parametros.sensibilidade_intensidade;
    return { minimo: s.minimo_pct, maximo: s.maximo_pct, passo: s.passo_pct };
  }

  function simular(parametros, opcoes) {
    validar(parametros);
    opcoes = opcoes || {};
    var cenario = cenarioPorId(parametros, opcoes.scenario || 'referencia');
    var ganho = typeof opcoes.ganhoEficiencia === 'number'
      ? opcoes.ganhoEficiencia
      : cenario.ganho_eficiencia_anual_padrao;
    if (!(ganho >= 0 && ganho < 1)) throw new Error('Ganho de eficiência fora da faixa 0–1: ' + ganho);

    var ajustes = opcoes.ajustesIntensidade || {};
    var faixa = faixaSensibilidade(parametros);
    Object.keys(ajustes).forEach(function (id) {
      var v = ajustes[id];
      if (!(v >= faixa.minimo && v <= faixa.maximo)) {
        throw new Error('Ajuste de intensidade fora da faixa permitida em ' + id + ': ' + v);
      }
    });

    var anos = anosDoHorizonte(parametros);
    var detalhe = [];

    parametros.minerais.forEach(function (mineral) {
      // Taxa aplicada pelo modelo do Squad 2 no cenário (a bauxita tem regra própria); sem ela, tendência + ajuste.
      var porCenario = mineral.crescimento_por_cenario;
      var crescimento = (porCenario && typeof porCenario[cenario.scenario] === 'number')
        ? porCenario[cenario.scenario]
        : mineral.crescimento_historico + cenario.growth_adjustment;
      var ajuste = ajustes[mineral.mineral_id] || 0;
      anos.forEach(function (ano) {
        var q = producao(mineral, crescimento, ano);
        var ie = intensidade(mineral, ganho, ajuste, ano);
        detalhe.push({
          mineral_id: mineral.mineral_id,
          mineral_name: mineral.mineral_name,
          production_basis: mineral.production_basis,
          ano: ano,
          producao_t: q,
          intensidade_mwh_t: ie,
          ajuste_intensidade_pct: ajuste,
          crescimento_aplicado: crescimento,
          energia_mwh: q * ie
        });
      });
    });

    return {
      scenario: cenario.scenario,
      rotulo: cenario.rotulo,
      cor: cenario.cor,
      crescimentoAjuste: cenario.growth_adjustment,
      ganhoEficiencia: ganho,
      ajustesIntensidade: ajustes,
      anos: anos,
      detalhe: detalhe,
      serie: agregarPorAno(detalhe, anos),
      versaoParametros: parametros.versao
    };
  }

  // Só a energia é agregada. As toneladas não somam entre minerais porque o cobre
  // usa conteúdo mineral e os demais usam produção beneficiada.
  function agregarPorAno(detalhe, anos) {
    var mapa = {};
    anos.forEach(function (ano) { mapa[ano] = { ano: ano, energia_mwh: 0 }; });
    detalhe.forEach(function (linha) { mapa[linha.ano].energia_mwh += linha.energia_mwh; });
    return anos.map(function (ano) {
      var r = mapa[ano];
      r.energia_twh = r.energia_mwh / MWH_POR_TWH;
      return r;
    });
  }

  function energiaPorMineral(resultado, ano) {
    return resultado.detalhe.filter(function (linha) {
      return linha.ano === ano;
    }).map(function (linha) {
      return {
        mineral_id: linha.mineral_id,
        mineral_name: linha.mineral_name,
        production_basis: linha.production_basis,
        producao_t: linha.producao_t,
        intensidade_mwh_t: linha.intensidade_mwh_t,
        ajuste_intensidade_pct: linha.ajuste_intensidade_pct,
        energia_mwh: linha.energia_mwh,
        energia_twh: linha.energia_mwh / MWH_POR_TWH
      };
    }).sort(function (a, b) { return b.energia_mwh - a.energia_mwh; });
  }

  function resumo(resultado) {
    var primeiro = resultado.serie[0];
    var ultimo = resultado.serie[resultado.serie.length - 1];
    var acumulado = resultado.serie.reduce(function (s, r) { return s + r.energia_mwh; }, 0);
    return {
      energiaInicialTwh: primeiro.energia_twh,
      energiaFinalTwh: ultimo.energia_twh,
      energiaAcumuladaTwh: acumulado / MWH_POR_TWH,
      variacaoPercentual: primeiro.energia_mwh
        ? (ultimo.energia_mwh - primeiro.energia_mwh) / primeiro.energia_mwh * 100
        : 0
    };
  }

  // As três curvas usam as mesmas hipóteses de eficiência e sensibilidade, para que a
  // comparação isole o efeito do cenário de crescimento.
  function simularCenarios(parametros, ganhoEficiencia, ajustesIntensidade) {
    return parametros.cenarios.map(function (c) {
      return simular(parametros, {
        scenario: c.scenario,
        ganhoEficiencia: ganhoEficiencia,
        ajustesIntensidade: ajustesIntensidade
      });
    });
  }

  var api = {
    MWH_POR_TWH: MWH_POR_TWH,
    validar: validar,
    producao: producao,
    intensidade: intensidade,
    simular: simular,
    simularCenarios: simularCenarios,
    energiaPorMineral: energiaPorMineral,
    resumo: resumo,
    anosDoHorizonte: anosDoHorizonte,
    cenarioPorId: cenarioPorId,
    faixaSensibilidade: faixaSensibilidade
  };

  if (typeof module === 'object' && module.exports) module.exports = api;
  if (raiz) raiz.SimuladorEngine = api;
})(typeof window !== 'undefined' ? window : null);
