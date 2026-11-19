(() => {
  "use strict";

  const SOURCE = "/data/previsao/production_benchmark_v1.json";

  const $ = (selector) => document.querySelector(selector);

  const escapeHtml = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (character) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[character]
    );

  const number = (value, digits = 0) =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : new Intl.NumberFormat("pt-BR", {
          maximumFractionDigits: digits,
          minimumFractionDigits: digits,
        }).format(Number(value));

  const tonnes = (value) => {
    const numeric = Number(value);

    if (!Number.isFinite(numeric)) return "—";
    if (Math.abs(numeric) >= 1000000) {
      return `${number(numeric / 1000000, 2)} Mt`;
    }

    if (Math.abs(numeric) >= 1000) {
      return `${number(numeric / 1000, 1)} mil t`;
    }

    return `${number(numeric, 0)} t`;
  };

  const percentage = (value, digits = 1) =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : `${number(value, digits)}%`;

  const methodName = (method) => {
    const names = {
      persistence: "Persistência",
      weighted_log_trend: "Tendência logarítmica",
      holt_damped: "Holt amortecido",
      not_forecastable_zero_2025: "Sem projeção",
    };

    return names[method] || method;
  };

  const style = `
    #production-benchmark-panel {
      margin-top: 24px;
    }

    .pb-head {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 20px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }

    .pb-controls {
      display: flex;
      align-items: flex-end;
      gap: 12px;
      flex-wrap: wrap;
    }

    .pb-control {
      min-width: 235px;
    }

    .pb-control label {
      display: block;
      margin-bottom: 7px;
      font-size: 12px;
      font-weight: 700;
      color: #36566d;
    }

    .pb-control select {
      width: 100%;
      min-height: 40px;
      border: 1px solid #c9d8e3;
      border-radius: 4px;
      background: #ffffff;
      padding: 8px 10px;
      color: #173d59;
      font-weight: 600;
    }

    .pb-metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(150px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }

    .pb-metric {
      border-left: 3px solid #0f6fb0;
      background: #f4f8fa;
      padding: 14px 15px;
    }

    .pb-metric span {
      display: block;
      color: #5d7383;
      font-size: 12px;
      margin-bottom: 7px;
    }

    .pb-metric strong {
      display: block;
      color: #123a5a;
      font-size: 19px;
      line-height: 1.15;
    }

    .pb-metric small {
      display: block;
      color: #6b7e8a;
      font-size: 11px;
      margin-top: 6px;
      line-height: 1.35;
    }

    .pb-chart-wrap {
      overflow-x: auto;
      margin-top: 10px;
    }

    .pb-chart-wrap svg {
      display: block;
      min-width: 700px;
      max-width: 100%;
    }

    .pb-legend {
      display: flex;
      gap: 17px;
      flex-wrap: wrap;
      margin-top: 10px;
      color: #526a7a;
      font-size: 12px;
    }

    .pb-legend span {
      display: inline-flex;
      align-items: center;
      gap: 7px;
    }

    .pb-dot {
      width: 20px;
      height: 3px;
      display: inline-block;
      border-radius: 3px;
    }

    .pb-dot.dashed {
      background: repeating-linear-gradient(
        90deg,
        #168a7a 0 7px,
        transparent 7px 11px
      );
    }

    .pb-band {
      width: 20px;
      height: 11px;
      display: inline-block;
      background: rgba(22, 138, 122, .17);
    }

    .pb-note {
      border-left: 3px solid #0f6fb0;
      padding: 11px 14px;
      background: #eef6fa;
      color: #355c72;
      font-size: 13px;
      line-height: 1.5;
      margin: 18px 0;
    }

    .pb-table button {
      appearance: none;
      border: 0;
      background: transparent;
      color: #0b5d93;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      padding: 0;
      text-align: left;
    }

    .pb-table tr.pb-selected td {
      background: #e9f4fa;
    }

    @media (max-width: 760px) {
      .pb-metrics {
        grid-template-columns: repeat(2, minmax(135px, 1fr));
      }
    }
  `;

  function niceStep(value) {
    const power = Math.pow(10, Math.floor(Math.log10(value)));
    const scaled = value / power;

    if (scaled <= 1) return power;
    if (scaled <= 2) return 2 * power;
    if (scaled <= 5) return 5 * power;

    return 10 * power;
  }

  function buildChart(observed, forecast, mode, mineralName) {
    const width = 940;
    const height = 330;
    const left = 76;
    const right = 22;
    const top = 20;
    const bottom = 44;

    const baseline = Number(observed[observed.length - 1]?.production_t);

    const value = (row, field) => {
      const numeric = Number(row[field]);

      if (mode === "index") {
        return baseline > 0 ? (numeric / baseline) * 100 : null;
      }

      return numeric;
    };

    const observedPoints = observed.map((row) => ({
      year: Number(row.year),
      value: value(row, "production_t"),
    }));

    const forecastPoints = forecast.map((row) => ({
      year: Number(row.year),
      reference: value(row, "production_reference_t"),
      low: value(row, "production_lower_t"),
      high: value(row, "production_upper_t"),
    }));

    const allValues = [
      0,
      ...observedPoints.map((row) => row.value),
      ...forecastPoints.flatMap((row) => [
        row.reference,
        row.low,
        row.high,
      ]),
    ].filter(Number.isFinite);

    const maxValue = Math.max(...allValues) * 1.08 || 1;

    const years = [
      ...observedPoints.map((row) => row.year),
      ...forecastPoints.map((row) => row.year),
    ];

    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);

    const x = (year) =>
      left +
      ((year - minYear) / Math.max(1, maxYear - minYear)) *
        (width - left - right);

    const y = (chartValue) =>
      top + (1 - chartValue / maxValue) * (height - top - bottom);

    const step = niceStep(maxValue / 4);
    const ticks = [];

    for (let tick = 0; tick <= maxValue + step; tick += step) {
      ticks.push(tick);
    }

    const formatAxis = (chartValue) => {
      if (mode === "index") return number(chartValue, 0);
      return tonnes(chartValue);
    };

    const grid = ticks
      .map(
        (tick) => `
          <line
            x1="${left}"
            x2="${width - right}"
            y1="${y(tick)}"
            y2="${y(tick)}"
            stroke="#e4edf2"
          />
          <text
            x="${left - 10}"
            y="${y(tick) + 4}"
            text-anchor="end"
            fill="#637787"
            font-size="11"
          >${escapeHtml(formatAxis(tick))}</text>
        `
      )
      .join("");

    const labels = [...new Set(years)]
      .sort((a, b) => a - b)
      .filter(
        (year, index, array) =>
          index === 0 ||
          index === array.length - 1 ||
          year % 2 === 0
      )
      .map(
        (year) => `
          <text
            x="${x(year)}"
            y="${height - 15}"
            text-anchor="middle"
            fill="#637787"
            font-size="11"
          >${year}</text>
        `
      )
      .join("");

    const observedLine = observedPoints
      .map((row) => `${x(row.year)},${y(row.value)}`)
      .join(" ");

    const forecastLine = forecastPoints
      .map((row) => `${x(row.year)},${y(row.reference)}`)
      .join(" ");

    const band =
      forecastPoints.length > 0
        ? `
          <path
            d="
              M ${forecastPoints
                .map((row) => `${x(row.year)},${y(row.high)}`)
                .join(" L ")}
              L ${[...forecastPoints]
                .reverse()
                .map((row) => `${x(row.year)},${y(row.low)}`)
                .join(" L ")}
              Z
            "
            fill="#168a7a"
            opacity=".16"
          />
        `
        : "";

    const projectionLine =
      forecastPoints.length > 0
        ? `
          <line
            x1="${x(forecastPoints[0].year)}"
            x2="${x(forecastPoints[0].year)}"
            y1="${top}"
            y2="${height - bottom}"
            stroke="#9fb3c2"
            stroke-dasharray="4 4"
          />
          <text
            x="${x(forecastPoints[0].year) + 7}"
            y="${top + 14}"
            fill="#637787"
            font-size="11"
          >projeção</text>
        `
        : "";

    const indexBase =
      mode === "index"
        ? `
          <line
            x1="${left}"
            x2="${width - right}"
            y1="${y(100)}"
            y2="${y(100)}"
            stroke="#9fb3c2"
            stroke-dasharray="3 4"
          />
          <text
            x="${width - right}"
            y="${y(100) - 7}"
            text-anchor="end"
            fill="#637787"
            font-size="11"
          >2025 = 100</text>
        `
        : "";

    const subtitle =
      mode === "index"
        ? "Índice de pressão energética relativa"
        : "Produção física (toneladas)";

    return `
      <div class="pb-chart-wrap">
        <svg
          viewBox="0 0 ${width} ${height}"
          role="img"
          aria-label="${escapeHtml(subtitle)} de ${escapeHtml(
            mineralName
          )}"
        >
          ${grid}
          ${labels}
          ${projectionLine}
          ${indexBase}
          ${band}

          <polyline
            points="${observedLine}"
            fill="none"
            stroke="#123a5a"
            stroke-width="2.5"
            stroke-linejoin="round"
            stroke-linecap="round"
          />

          ${observedPoints
            .map(
              (row) => `
                <circle
                  cx="${x(row.year)}"
                  cy="${y(row.value)}"
                  r="2.8"
                  fill="#123a5a"
                />
              `
            )
            .join("")}

          ${
            forecastPoints.length
              ? `
                <polyline
                  points="${forecastLine}"
                  fill="none"
                  stroke="#168a7a"
                  stroke-width="2.5"
                  stroke-dasharray="7 5"
                  stroke-linejoin="round"
                  stroke-linecap="round"
                />
              `
              : ""
          }
        </svg>
      </div>

      <div class="pb-legend">
        <span><i class="pb-dot" style="background:#123a5a"></i>Produção observada</span>
        <span><i class="pb-dot dashed"></i>Previsão de referência</span>
        <span><i class="pb-band"></i>Faixa calibrada pelo erro histórico</span>
      </div>
    `;
  }

  function createPanel(data) {
    const target = $("#pv-dados");

    if (!target || $("#production-benchmark-panel")) return;

    const styleNode = document.createElement("style");
    styleNode.textContent = style;
    document.head.appendChild(styleNode);

    const panel = document.createElement("article");
    panel.className = "panel pv-panel";
    panel.id = "production-benchmark-panel";

    panel.innerHTML = `
      <div class="pb-head">
        <div>
          <h3>Benchmark de produção e pressão energética relativa</h3>
          <p class="subtitle">
            Produção estadual observada e previsão 2027–2040 para além
            dos cinco minerais do modelo elétrico.
          </p>
        </div>

        <div class="pb-controls">
          <div class="pb-control">
            <label for="pb-mineral">Mineral</label>
            <select id="pb-mineral"></select>
          </div>

          <div class="pb-control">
            <label for="pb-view">Visualização</label>
            <select id="pb-view">
              <option value="tonnes">Produção física (t)</option>
              <option value="index">Pressão energética relativa · 2025 = 100</option>
            </select>
          </div>
        </div>
      </div>

      <div class="pb-metrics" id="pb-metrics"></div>

      <div id="pb-chart"></div>

      <div class="pb-note" id="pb-note"></div>

      <div class="table-wrap pb-table" id="pb-table"></div>
    `;

    target.appendChild(panel);

    const minerals = [...data.minerals_in_benchmark].sort((a, b) =>
      a.mineral_name.localeCompare(b.mineral_name, "pt-BR")
    );

    const selectMineral = $("#pb-mineral");
    const selectView = $("#pb-view");
    const metrics = $("#pb-metrics");
    const chart = $("#pb-chart");
    const note = $("#pb-note");
    const table = $("#pb-table");

    selectMineral.innerHTML = minerals
      .map(
        (mineral) => `
          <option value="${escapeHtml(mineral.mineral_id)}">
            ${escapeHtml(mineral.mineral_name)}
          </option>
        `
      )
      .join("");

    const bauxite = minerals.find(
      (mineral) => mineral.mineral_id === "MIN_005"
    );

    selectMineral.value = bauxite
      ? bauxite.mineral_id
      : minerals[0].mineral_id;

    function index2040(mineral) {
      const projected = data.forecast.find(
        (row) =>
          row.mineral_id === mineral.mineral_id &&
          Number(row.year) === 2040
      );

      const base = Number(mineral.production_latest_t);

      if (!projected || base <= 0) return null;

      return (
        (Number(projected.production_reference_t) / base) * 100
      );
    }

    function renderTable(selectedId) {
      table.innerHTML = `
        <table class="pn-table">
          <thead>
            <tr>
              <th>Mineral</th>
              <th class="num">Anos observados</th>
              <th>Método escolhido</th>
              <th class="num">Erro no backtest</th>
              <th class="num">Índice 2040<br>2025 = 100</th>
            </tr>
          </thead>
          <tbody>
            ${minerals
              .map(
                (mineral) => `
                  <tr class="${
                    mineral.mineral_id === selectedId
                      ? "pb-selected"
                      : ""
                  }">
                    <td>
                      <button
                        type="button"
                        data-pb-mineral="${escapeHtml(
                          mineral.mineral_id
                        )}"
                      >
                        ${escapeHtml(mineral.mineral_name)}
                      </button>
                    </td>
                    <td class="num">${number(
                      mineral.observed_years
                    )}</td>
                    <td>${escapeHtml(
                      methodName(mineral.selected_method)
                    )}</td>
                    <td class="num">${percentage(
                      mineral.backtest_smape_selected_pct
                    )}</td>
                    <td class="num">${
                      index2040(mineral) == null
                        ? "—"
                        : number(index2040(mineral), 0)
                    }</td>
                  </tr>
                `
              )
              .join("")}
          </tbody>
        </table>
      `;

      table
        .querySelectorAll("[data-pb-mineral]")
        .forEach((button) => {
          button.addEventListener("click", () => {
            selectMineral.value = button.dataset.pbMineral;
            render();
            panel.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          });
        });
    }

    function render() {
      const mineralId = selectMineral.value;
      const mode = selectView.value;

      const mineral = minerals.find(
        (item) => item.mineral_id === mineralId
      );

      const observed = data.series
        .filter((row) => row.mineral_id === mineralId)
        .sort((a, b) => Number(a.year) - Number(b.year));

      const forecast = data.forecast
        .filter((row) => row.mineral_id === mineralId)
        .sort((a, b) => Number(a.year) - Number(b.year));

      const in2040 = forecast.find(
        (row) => Number(row.year) === 2040
      );

      const pressure2040 = index2040(mineral);

      metrics.innerHTML = `
        <div class="pb-metric">
          <span>Primeiro ano observado</span>
          <strong>${number(
            mineral.first_observed_year
          )}</strong>
          <small>${number(
            mineral.observed_years
          )} anos históricos disponíveis</small>
        </div>

        <div class="pb-metric">
          <span>Produção em 2025</span>
          <strong>${tonnes(
            mineral.production_latest_t
          )}</strong>
          <small>Base para o índice relativo</small>
        </div>

        <div class="pb-metric">
          <span>Método selecionado</span>
          <strong>${escapeHtml(
            methodName(mineral.selected_method)
          )}</strong>
          <small>Escolhido pelo menor erro no backtest</small>
        </div>

        <div class="pb-metric">
          <span>Pressão energética relativa em 2040</span>
          <strong>${
            pressure2040 == null
              ? "Não calculável"
              : `${number(pressure2040, 0)}`
          }</strong>
          <small>${
            pressure2040 == null
              ? "Sem previsão: produção de 2025 igual a zero"
              : "Índice: 2025 = 100, intensidade constante"
          }</small>
        </div>
      `;

      chart.innerHTML = buildChart(
        observed,
        forecast,
        mode,
        mineral.mineral_name
      );

      note.innerHTML =
        mode === "index"
          ? `
            <strong>Como ler este índice:</strong> 100 representa a
            produção de 2025. Se o processo do mineral mantiver a mesma
            intensidade energética, um índice de 120 em 2040 significa
            20% mais demanda elétrica relativa que em 2025. Não é TWh:
            minerais sem coeficiente MWh/t compatível continuam fora do
            total elétrico.
          `
          : `
            A previsão compara persistência, tendência logarítmica e Holt
            amortecido em backtest. Uma tendência só é usada quando melhora
            claramente a previsão simples e tem erro aceitável; caso contrário,
            o modelo mantém o último nível observado.
          `;

      renderTable(mineralId);
    }

    selectMineral.addEventListener("change", render);
    selectView.addEventListener("change", render);

    render();
  }

  async function init() {
    try {
      const response = await fetch(`${SOURCE}?v=20261115b`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Não foi possível carregar o benchmark.");
      }

      createPanel(await response.json());
    } catch (error) {
      console.error(error);
    }
  }

  init();
})();
