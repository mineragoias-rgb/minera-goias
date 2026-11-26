(function () {
  'use strict';

  var CAMINHO_PARAMETROS = '/data/simulador/parametros_v1.json';
  var $ = function (id) { return document.getElementById(id); };
  var estado = { parametros: null, scenario: 'referencia', ganho: 0, ajustes: {} };

  var num = function (v, casas) {
    return v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
  };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  var data = function (iso) {
    var p = String(iso).split('-');
    return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : iso;
  };
  var sinal = function (v, casas) { return (v > 0 ? '+' : v < 0 ? '−' : '') + num(Math.abs(v), casas); };
  var base = function (b) { return b === 'conteudo_mineral' ? 'conteúdo mineral' : 'produção beneficiada'; };

  function escalaBonita(valor) {
    if (!(valor > 0)) return 1;
    var potencia = Math.pow(10, Math.floor(Math.log10(valor))), n = valor / potencia;
    return (n <= 1 ? 1 : n <= 1.5 ? 1.5 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 3 ? 3 : n <= 4 ? 4 : n <= 5 ? 5 : n <= 7.5 ? 7.5 : 10) * potencia;
  }
  var topoEscala = function (v) { return escalaBonita(v / 4) * 4; };

  function graficoAnos(resultados, selecionado) {
    var L = 60, R = 18, T = 18, B = 40, W = 900, H = 340;
    var anos = resultados[0].anos;
    var maximo = 0;
    resultados.forEach(function (r) {
      r.serie.forEach(function (p) { if (p.energia_twh > maximo) maximo = p.energia_twh; });
    });
    var topo = topoEscala(maximo) || 1;
    var x = function (i) { return L + (W - L - R) * (anos.length === 1 ? 0 : i / (anos.length - 1)); };
    var y = function (v) { return T + (H - T - B) * (1 - v / topo); };

    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Demanda de energia por ano em cada cenário">';
    for (var i = 0; i <= 4; i++) {
      var valor = topo * i / 4, yy = y(valor);
      svg += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + yy + '" y2="' + yy + '" stroke="#e8e2d6"/>';
      svg += '<text x="' + (L - 10) + '" y="' + (yy + 4) + '" text-anchor="end" font-size="11" fill="#6b7780">' + esc(num(valor, 0)) + '</text>';
    }
    svg += '<text x="' + L + '" y="' + (H - 8) + '" font-size="10" fill="#6b7780">TWh por ano</text>';
    anos.forEach(function (ano, i) {
      svg += '<text x="' + x(i) + '" y="' + (H - B + 20) + '" text-anchor="middle" font-size="10" fill="#6b7780">' + ano + '</text>';
    });

    resultados.forEach(function (r) {
      var atual = r.scenario === selecionado;
      var pontos = r.serie.map(function (p, i) { return x(i) + ',' + y(p.energia_twh); }).join(' ');
      svg += '<polyline points="' + pontos + '" fill="none" stroke="' + r.cor + '"'
        + ' stroke-width="' + (atual ? 3 : 1.6) + '" stroke-opacity="' + (atual ? 1 : 0.42) + '"'
        + ' stroke-linejoin="round" stroke-linecap="round"/>';
      if (atual) {
        r.serie.forEach(function (p, i) {
          svg += '<circle cx="' + x(i) + '" cy="' + y(p.energia_twh) + '" r="3.5" fill="' + r.cor + '">'
            + '<title>' + esc(r.rotulo + ' · ' + p.ano + ': ' + num(p.energia_twh, 2) + ' TWh') + '</title></circle>';
        });
        var ultimo = r.serie[r.serie.length - 1];
        svg += '<text x="' + (x(anos.length - 1) - 4) + '" y="' + (y(ultimo.energia_twh) - 12) + '"'
          + ' text-anchor="end" font-size="12" font-weight="700" fill="' + r.cor + '">'
          + esc(num(ultimo.energia_twh, 1)) + ' TWh</text>';
      }
    });
    return svg + '</svg>';
  }

  function graficoMinerais(minerais, cor) {
    if (!minerais.length) return '<p class="ajuda">Sem dados para o ano selecionado.</p>';
    var linha = 44, L = 178, R = 96, W = 900, H = minerais.length * linha + 16;
    var topo = topoEscala(minerais[0].energia_twh) || 1;
    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Demanda de energia por mineral">';
    minerais.forEach(function (m, i) {
      var yy = i * linha + 8, largura = (W - L - R) * (m.energia_twh / topo);
      var rotulo = m.mineral_name + (m.ajuste_intensidade_pct ? ' (' + sinal(m.ajuste_intensidade_pct, 0) + '%)' : '');
      svg += '<text x="' + (L - 12) + '" y="' + (yy + 16) + '" text-anchor="end" font-size="12" fill="#26313A">' + esc(rotulo) + '</text>';
      svg += '<text x="' + (L - 12) + '" y="' + (yy + 29) + '" text-anchor="end" font-size="9" fill="#6b7780">' + esc(base(m.production_basis)) + '</text>';
      svg += '<rect x="' + L + '" y="' + yy + '" width="' + (W - L - R) + '" height="24" fill="#f2efe7"/>';
      svg += '<rect x="' + L + '" y="' + yy + '" width="' + Math.max(largura, 1) + '" height="24" fill="' + cor + '">'
        + '<title>' + esc(m.mineral_name + ': ' + num(m.energia_twh, 3) + ' TWh · '
          + num(m.producao_t / 1e6, 3) + ' Mt · ' + num(m.intensidade_mwh_t, 2) + ' MWh/t') + '</title></rect>';
      svg += '<text x="' + (W - R + 10) + '" y="' + (yy + 16) + '" font-size="12" font-weight="700" fill="#26313A">' + esc(num(m.energia_twh, 2)) + '</text>';
      svg += '<text x="' + (W - R + 10) + '" y="' + (yy + 29) + '" font-size="9" fill="#6b7780">TWh</text>';
    });
    return svg + '</svg>';
  }

  function tabelaAnos(resultados) {
    var cab = '<tr><th>Ano</th>' + resultados.map(function (r) {
      return '<th>' + esc(r.rotulo) + ' · TWh</th>';
    }).join('') + '</tr>';
    var corpo = resultados[0].anos.map(function (ano, i) {
      return '<tr><td>' + ano + '</td>' + resultados.map(function (r) {
        return '<td class="num">' + esc(num(r.serie[i].energia_twh, 3)) + '</td>';
      }).join('') + '</tr>';
    }).join('');
    return '<table><thead>' + cab + '</thead><tbody>' + corpo + '</tbody></table>';
  }

  function tabelaMinerais(minerais) {
    var linhas = minerais.map(function (m) {
      return '<tr><td>' + esc(m.mineral_name) + '</td>'
        + '<td>' + esc(base(m.production_basis)) + '</td>'
        + '<td class="num">' + esc(num(m.producao_t / 1e6, 3)) + '</td>'
        + '<td class="num">' + esc(num(m.intensidade_mwh_t, 3)) + '</td>'
        + '<td class="num">' + esc(sinal(m.ajuste_intensidade_pct, 0)) + '%</td>'
        + '<td class="num">' + esc(num(m.energia_twh, 3)) + '</td></tr>';
    }).join('');
    return '<table><thead><tr><th>Mineral</th><th>Base de produção</th><th>Produção · Mt</th>'
      + '<th>Intensidade · MWh/t</th><th>Ajuste</th><th>Energia · TWh</th></tr></thead>'
      + '<tbody>' + linhas + '</tbody></table>'
      + '<p class="ajuda">As toneladas não são somadas entre minerais: as bases de produção são diferentes.</p>';
  }

  function kpis(resumo) {
    var p = estado.parametros;
    var itens = [
      ['Energia em ' + p.horizonte.fim, num(resumo.energiaFinalTwh, 2) + ' TWh',
        sinal(resumo.variacaoPercentual, 1) + '% em relação a ' + p.horizonte.inicio, true],
      ['Energia em ' + p.horizonte.inicio, num(resumo.energiaInicialTwh, 2) + ' TWh', 'início do horizonte', false],
      ['Energia acumulada', num(resumo.energiaAcumuladaTwh, 0) + ' TWh',
        p.horizonte.inicio + ' a ' + p.horizonte.fim, false],
      ['Minerais cobertos', String(p.cobertura.minerais), 'nióbio fora desta versão', false]
    ];
    return itens.map(function (it) {
      return '<div class="kpi' + (it[3] ? ' destaque' : '') + '"><span>' + esc(it[0]) + '</span>'
        + '<strong>' + esc(it[1]) + '</strong><small>' + esc(it[2]) + '</small></div>';
    }).join('');
  }

  function botoesCenario() {
    $('cenarios').innerHTML = estado.parametros.cenarios.map(function (c) {
      return '<button type="button" role="radio" data-cenario="' + esc(c.scenario) + '"'
        + ' aria-checked="' + (c.scenario === estado.scenario) + '">'
        + '<span class="ponto"></span>' + esc(c.rotulo) + '</button>';
    }).join('');
    Array.prototype.forEach.call($('cenarios').querySelectorAll('button'), function (b) {
      b.onclick = function () { estado.scenario = b.dataset.cenario; desenhar(); };
    });
  }

  function controlesSensibilidade() {
    var p = estado.parametros, faixa = window.SimuladorEngine.faixaSensibilidade(p);
    $('sensibilidade').innerHTML = p.minerais.map(function (m) {
      var id = 'sens-' + m.mineral_id;
      return '<div class="sens-linha">'
        + '<label for="' + id + '">' + esc(m.mineral_name) + '</label>'
        + '<input type="range" id="' + id + '" data-mineral="' + esc(m.mineral_id) + '"'
        + ' min="' + faixa.minimo + '" max="' + faixa.maximo + '" step="' + faixa.passo + '" value="0">'
        + '<output for="' + id + '" id="' + id + '-valor">0%</output></div>';
    }).join('');
    Array.prototype.forEach.call($('sensibilidade').querySelectorAll('input'), function (input) {
      input.oninput = function () {
        estado.ajustes[this.dataset.mineral] = Number(this.value);
        desenhar();
      };
    });
    $('ajuda-sens').innerHTML = 'Testa quanto o resultado depende dos coeficientes de intensidade, que são a maior '
      + 'incerteza desta versão. Faixa de ' + faixa.minimo + '% a +' + faixa.maximo + '%, definida na análise de '
      + 'sensibilidade do modelo. Não altera a produção projetada.';
  }

  function desenhar() {
    var engine = window.SimuladorEngine, p = estado.parametros;
    var resultados = engine.simularCenarios(p, estado.ganho, estado.ajustes);
    var atual = resultados.filter(function (r) { return r.scenario === estado.scenario; })[0];
    var anoFinal = p.horizonte.fim;
    var minerais = engine.energiaPorMineral(atual, anoFinal);
    var cenario = engine.cenarioPorId(p, estado.scenario);

    Array.prototype.forEach.call($('cenarios').querySelectorAll('button'), function (b) {
      b.setAttribute('aria-checked', String(b.dataset.cenario === estado.scenario));
    });
    $('ganho').value = (estado.ganho * 100).toFixed(1);
    $('ganho-valor').textContent = num(estado.ganho * 100, 1) + '%';
    p.minerais.forEach(function (m) {
      var v = estado.ajustes[m.mineral_id] || 0, saida = $('sens-' + m.mineral_id + '-valor');
      $('sens-' + m.mineral_id).value = v;
      saida.textContent = sinal(v, 0) + '%';
      saida.className = v ? 'ativo' : '';
    });

    $('ajuda-cenario').innerHTML = 'Ajuste sobre o crescimento histórico de cada mineral: <b>'
      + esc(sinal(cenario.growth_adjustment * 100, 1)) + ' ponto percentual ao ano</b>. '
      + 'Padrão de eficiência deste cenário: <b>' + esc(num(cenario.ganho_eficiencia_anual_padrao * 100, 1)) + '%</b> ao ano.';

    $('kpis').innerHTML = kpis(engine.resumo(atual));
    $('grafico-anos').innerHTML = graficoAnos(resultados, estado.scenario);
    $('legenda-anos').innerHTML = resultados.map(function (r) {
      return '<span class="' + (r.scenario === estado.scenario ? 'atual' : '') + '">'
        + '<i style="background:' + r.cor + '"></i>' + esc(r.rotulo)
        + (r.scenario === estado.scenario ? ' · selecionado' : '') + '</span>';
    }).join('');
    $('tabela-anos').innerHTML = tabelaAnos(resultados);
    $('grafico-minerais').innerHTML = graficoMinerais(minerais, atual.cor);
    $('tabela-minerais').innerHTML = tabelaMinerais(minerais);
    $('ano-final-1').textContent = anoFinal;
    $('sub-minerais').textContent = 'Cenário ' + cenario.rotulo.toLowerCase()
      + ', no último ano do horizonte. Só a energia é somada entre minerais.';
  }

  function selo(natureza) {
    return '<span class="selo ' + (natureza === 'observado' ? 'observado' : 'ilustrativo') + '">'
      + esc(natureza) + '</span>';
  }

  function indiceFontes() {
    var mapa = {};
    estado.parametros.fontes.forEach(function (f) { mapa[f.source_id] = f; });
    return mapa;
  }

  function blocoParametros() {
    var p = estado.parametros, fontes = indiceFontes();
    var cen = window.SimuladorEngine.cenarioPorId(p, estado.scenario);
    var padrao = estado.ganho === cen.ganho_eficiencia_anual_padrao;
    var f = fontes[cen.source_id];
    var linhas = [
      ['Ajuste de crescimento do cenário', sinal(cen.growth_adjustment * 100, 1) + ' p.p. ao ano', f, 'ilustrativo'],
      ['Ganho de eficiência em uso (g)', num(estado.ganho * 100, 1) + '% ao ano', f,
        padrao ? 'ilustrativo' : 'definido pelo usuário nesta simulação'],
      ['Ganho padrão deste cenário', num(cen.ganho_eficiencia_anual_padrao * 100, 1) + '% ao ano', f, 'ilustrativo']
    ].map(function (l) {
      return '<tr><td>' + esc(l[0]) + '</td><td class="num">' + esc(l[1]) + '</td>'
        + '<td>' + esc(l[2].source_name) + '</td><td>' + esc(data(l[2].data_acesso)) + '</td>'
        + '<td>' + selo(l[3]) + '</td></tr>';
    }).join('');
    return '<table><thead><tr><th>Parâmetro</th><th>Valor</th><th>Fonte</th>'
      + '<th>Data de acesso</th><th>Natureza</th></tr></thead><tbody>' + linhas + '</tbody></table>';
  }

  function blocoMinerais() {
    var fontes = indiceFontes();
    var linhas = estado.parametros.minerais.map(function (m) {
      var f = fontes[m.source_id];
      var mape = m.mape_backtest == null ? '—' : num(m.mape_backtest * 100, 1) + '%';
      var alerta = m.mape_backtest != null && m.mape_backtest > 0.2
        ? '<span class="aviso-mape">erro alto</span>' : '';
      return '<tr><td>' + esc(m.mineral_name) + '<br><span class="ajuda">' + esc(m.mineral_id) + '</span></td>'
        + '<td>' + esc(base(m.production_basis)) + '</td>'
        + '<td class="num">' + m.ano_base + '</td>'
        + '<td class="num">' + esc(num(m.producao_base_t / 1e6, 3)) + '</td>'
        + '<td class="num">' + esc(sinal(m.crescimento_historico * 100, 2)) + '%</td>'
        + '<td class="num">' + esc(num(m.energy_intensity_mwh_t, 3)) + '</td>'
        + '<td class="num">' + esc(mape) + alerta + '</td>'
        + '<td>' + selo(m.valor_observado_estimado) + '</td></tr>';
    }).join('');
    return '<table><thead><tr><th>Mineral</th><th>Base de produção</th><th>Ano base</th>'
      + '<th>Produção base · Mt</th><th>Crescimento histórico</th><th>Intensidade · MWh/t</th>'
      + '<th>Erro do backtest</th><th>Natureza</th></tr></thead><tbody>' + linhas + '</tbody></table>';
  }

  function blocoCatalogo() {
    return estado.parametros.fontes.map(function (f) {
      var campos = [
        ['Identificador', f.source_id],
        ['Origem', f.source_url || 'sem URL pública'],
        ['Período de referência', f.periodo_referencia],
        ['Tipo de fonte', f.tipo_fonte],
        ['Data de acesso', data(f.data_acesso)],
        ['Método de estimação', f.metodo_estimacao || 'não se aplica'],
        ['Status de validação', f.status_validacao],
        ['Responsável pela validação', f.responsavel_validacao]
      ].map(function (c) {
        return '<tr><td>' + esc(c[0]) + '</td><td>' + esc(c[1]) + '</td></tr>';
      }).join('');
      return '<h3>' + esc(f.source_name) + ' ' + selo(f.valor_observado_estimado) + '</h3>'
        + '<p>' + esc(f.notas) + '</p>'
        + '<div class="tabela-wrap"><table><tbody>' + campos + '</tbody></table></div>';
    }).join('');
  }

  function abrirModal() {
    var p = estado.parametros, cen = window.SimuladorEngine.cenarioPorId(p, estado.scenario);
    var conf = p.conferencia_modelo, origem = p.origem_modelo;
    $('modal-sub').textContent = 'Cenário ' + cen.rotulo.toLowerCase() + ' · arquivo de parâmetros v'
      + p.versao + ', de ' + data(p.data_versao) + '.';
    $('modal-corpo').innerHTML =
      '<h3>Como o resultado é calculado</h3>'
      + '<p>Os números vêm do modelo econômico-energético do projeto. A produção de cada mineral parte do último '
      + 'ano observado na ANM e '
      + 'cresce pelo próprio crescimento histórico, ajustado pelo cenário. A intensidade cai conforme a hipótese '
      + 'de eficiência e pode ser ajustada por mineral no controle de sensibilidade.</p>'
      + '<p>Produção: <b>' + esc(p.equacoes.producao) + '</b><br>'
      + 'Intensidade: <b>' + esc(p.equacoes.intensidade) + '</b><br>'
      + 'Energia: <b>' + esc(p.equacoes.energia) + '</b></p>'
      + '<p>O pacote de parâmetros é gerado a partir do modelo, e a geração confere que esta tela devolve '
      + 'os mesmos números. A maior diferença encontrada foi de '
      + esc(conf.maior_diferenca_mwh) + ' MWh, em todos os minerais, anos e cenários.</p>'

      + '<h3>Cobertura</h3>'
      + '<p>' + esc(p.cobertura.nota) + '</p>'
      + '<p>' + esc(p.cobertura.nota_toneladas) + '</p>'

      + '<h3>Parâmetros do cenário selecionado</h3>'
      + '<div class="tabela-wrap">' + blocoParametros() + '</div>'

      + '<h3>Parâmetros por mineral</h3>'
      + '<p>O erro do backtest é o erro percentual absoluto médio do modelo ao projetar os dois '
      + 'últimos anos conhecidos usando apenas os anteriores. A bauxita tem erro alto porque a produção caiu '
      + 'em 2024 depois de anos de crescimento: é o limite de uma projeção de tendência, que não antecipa '
      + 'interrupções operacionais nem decisões de mercado.</p>'
      + '<div class="tabela-wrap">' + blocoMinerais() + '</div>'

      + '<h3>Resultado do modelo</h3>'
      + '<p>No cenário de referência, com as hipóteses padrão, a demanda estimada vai de <b>'
      + esc(num(conf.referencia_2027_twh, 2)) + ' TWh</b> em ' + p.horizonte.inicio + ' a <b>'
      + esc(num(conf.referencia_2040_twh, 2)) + ' TWh</b> em ' + p.horizonte.fim + '. No conservador, '
      + esc(num(conf.conservador_2040_twh, 2)) + ' TWh; no de expansão, '
      + esc(num(conf.expansao_2040_twh, 2)) + ' TWh. ' + esc(p.aviso) + '</p>'

      + '<h3>Catálogo de fontes</h3>'
      + blocoCatalogo();
    $('modal').hidden = false;
    $('modal-fechar').focus();
  }

  function fecharModal() { $('modal').hidden = true; }

  function restaurarPadrao() {
    estado.ganho = window.SimuladorEngine.cenarioPorId(estado.parametros, estado.scenario).ganho_eficiencia_anual_padrao;
    estado.ajustes = {};
    desenhar();
  }

  function iniciar(parametros) {
    window.SimuladorEngine.validar(parametros);
    estado.parametros = parametros;
    estado.ganho = window.SimuladorEngine.cenarioPorId(parametros, estado.scenario).ganho_eficiencia_anual_padrao;

    $('version-tag').textContent = 'parâmetros v' + parametros.versao + ' · ' + data(parametros.data_versao);
    $('aviso-ilustrativo').innerHTML = '<b>Cenário condicional, não previsão.</b> ' + esc(parametros.aviso);
    $('nota-cobertura').innerHTML = 'Projeção do modelo econômico-energético do projeto sobre a produção '
      + 'histórica consolidada a partir da ANM. ' + esc(parametros.cobertura.nota);
    $('linha-fonte').textContent = 'Fontes: ' + parametros.fontes.map(function (f) { return f.source_name; }).join(' · ')
      + '. Parâmetros v' + parametros.versao + ', de ' + data(parametros.data_versao)
      + ', gerados por ' + parametros.origem_modelo.gerado_por + '.';

    botoesCenario();
    controlesSensibilidade();
    $('ganho').oninput = function () { estado.ganho = Number(this.value) / 100; desenhar(); };
    $('btn-padrao').onclick = restaurarPadrao;
    $('btn-fontes').hidden = false;
    $('btn-fontes').onclick = abrirModal;
    $('modal-fechar').onclick = fecharModal;
    $('modal').onclick = function (e) { if (e.target === $('modal')) fecharModal(); };
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fecharModal(); });

    desenhar();
    $('carregando').hidden = true;
    $('conteudo').hidden = false;
  }

  function falhar(mensagem) {
    $('carregando').hidden = true;
    $('erro').hidden = false;
    $('erro').textContent = 'Não foi possível carregar o simulador: ' + mensagem;
  }

  fetch(CAMINHO_PARAMETROS, { cache: 'no-store' })
    .then(function (r) {
      if (!r.ok) throw new Error('arquivo de parâmetros não encontrado (' + r.status + ').');
      return r.json();
    })
    .then(iniciar)
    .catch(function (e) { falhar(e.message); });
})();
