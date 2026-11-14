(() => {
  "use strict";

  const SOURCE = "/data/previsao/production_benchmark_v1.json";
  const $ = (selector) => document.querySelector(selector);

  const escapeHtml = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (char) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[char]
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
    if (Math.abs(numeric) >= 1e6) return `${number(numeric / 1e6, 2)} Mt`;
    if (Math.abs(numeric) >= 1e3) return `${number(numeric / 1e3, 1)} mil t`;

    return `${number(numeric, 0)} t`;
  };

  const percent = (value, digits = 1) =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : `${number(value, digits)}%`;

  const methodName = (method) => {
    const names = {
      persistence: "Persistência",
      weighted_log_trend: "Tendência logarítmica",
      holt_damped: "Holt com tendência amortecida",
      not_forecastable_zero_2025: "Sem projeção",
    };

    return names[method] || method;
  };

  const style = `
    #production-benchmark-panel {
      margin-top: 24px;
    }

    .pb-topline {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 20px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }

    .pb-control {
      min-width: 280px;
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
      background: #fff;
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
      font-size: 20px;
      line-height: 1.1;
    }

    .pb-metric small {
      display: block;
      color: #6b7e8a;
      font-size: 11px;
      margin-top: 6px;
    }

    .pb-chart-wrap {
      overflow-x: auto;
      margin-top: 8px;
    }

    .pb-chart-wrap svg {
      display: block;
      min-width: 680px;
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
      width: 19px;
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
      width: 19px;
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
        grid-template-columns: repeat(2, minmax(130px, 1fr));
      }
    }
  `;

  function chart(observed, projected, mineralName) {
    const width = 940;
    const height = 330;
    const left = 76;
    const right = 22;
    const top = 20;
    const bottom = 44;

    const points = [
      ...observed.map((row) => ({
        year: Number(row.year),
        value: Number(row.production_t),
      })),
      ...projected.map((row) => ({
        year: Number(row.year),
        value: Number(row.production_reference_t),
      })),
    ];

    const bandValues = projected.flatMap((row) => [
      Number(row.production_lower_t),
      Number(row.production_upper_t),
    ]);

    const allValues = [
      ...points.map((point) => point.value),
      ...bandValues,
      0,
    ];

    const maxValue = Math.max(...allValues) * 1.08 || 1;
    const minYear = Math.min(...points.map((point) => point.year));
    const maxYear = Math.max(...points.map((point) => point.year));

    const x = (year) =>
      left +
      ((year - minYear) / Math.max(1, maxYear - minYear)) *
        (width - left - right);

    const y = (value) =>
      top + (1 - value / maxValue) * (height - top - bottom);

    const niceStep = (value) => {
      const power = Math.pow(10, Math.floor(Math.log10(value)));
      const scaled = value / power;

      if (scaled <= 1) return power;
      if (scaled <= 2) return 2 * power;
      if (scaled <= 5) return 5 * power;

      return 10 * power;
    };

    const step = niceStep(maxValue / 4);
    const ticks = [];

    for (let tick = 0; tick <= maxValue + step; tick += step) {
      ticks.push(tick);
    }

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
          >${escapeHtml(tonnes(tick))}</text>
        `
      )
      .join("");

    const years = Array.from(
      new Set(points.map((point) => point.year))
    ).sort((a, b) => a - b);

    const xLabels = years
      .filter(
        (year, index) =>
          index === 0 ||
          index === years.length - 1 ||
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

    const line = (rows, field) =>
      rows
        .map(
          (row) =>
            `${x(Number(row.year))},${y(Number(row[field]))}`
        )
        .join(" ");

    const band = projected.length
      ? `
        <path
          d="
            M ${projected
              .map(
                (row) =>
                  `${x(Number(row.year))},${y(
                    Number(row.production_upper_t)
                  )}`
              )
              .join(" L ")}
            L ${[...projected]
              .reverse()
              .map(
                (row) =>
                  `${x(Number(row.year))},${y(
                    Number(row.production_lower_t)
                  )}`
              )
              .join(" L ")}
            Z
          "
          fill="#168a7a"
          opacity=".16"
        />
      `
      : "";

    const projectionStart = projected.length
      ? `
        <line
          x1="${x(Number(projected[0].year))}"
          x2="${x(Number(projected[0].year))}"
          y1="${top}"
          y2="${height - bottom}"
          stroke="#9fb3c2"
          stroke-dasharray="4 4"
        />
        <text
          x="${x(Number(projected[0].year)) + 7}"
          y="${top + 14}"
          fill="#637787"
          font-size="11"
        >projeção</text>
      `
      : "";

    return `
      <div class="pb-chart-wrap">
        <svg
          viewBox="0 0 ${width} ${height}"
          role="img"
          aria-label="Produção histórica e projeção de ${escapeHtml(
            mineralName
          )}"
        >
          ${grid}
          ${xLabels}
          ${projectionStart}
          ${band}
          <polyline
            points="${line(observed, "production_t")}"
            fill="none"
            stroke="#123a5a"
            stroke-width="2.5"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
          ${observed
            .map(
              (row) => `
                <circle
                  cx="${x(Number(row.year))}"
                  cy="${y(Number(row.production_t))}"
                  r="2.8"
                  fill="#123a5a"
                />
              `
            )
            .join("")}
          ${
            projected.length
              ? `
                <polyline
                  points="${line(projected, "production_reference_t")}"
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

  function setup(data) {
    const dataTab = $("#pv-dados");

    if (!dataTab || $("#production-benchmark-panel")) return;

    const styleNode = document.createElement("style");
    styleNode.textContent = style;
    document.head.appendChild(styleNode);

    const panel = document.createElement("article");
    panel.className = "panel pv-panel";
    panel.id = "production-benchmark-panel";

    panel.innerHTML = `
      <div class="pb-topline">
        <div>
          <h3>Benchmark de produção mineral</h3>
          <p class="subtitle">
            Produção estadual observada e previsão 2027–2040.
            Este painel amplia a análise além dos cinco minerais elétricos,
            mas não os soma em TWh sem coeficiente energético compatível.
          </p>
        </div>

        <div class="pb-control">
          <label for="pb-mineral">Selecionar mineral</label>
          <select id="pb-mineral"></select>
        </div>
      </div>

      <div class="pb-metrics" id="pb-metrics"></div>

      <div id="pb-chart"></div>

      <div class="pb-note">
        A previsão compara persistência, tendência logarítmica e Holt
        amortecido em backtest. Uma tendência só é usada quando melhora
        claramente a previsão simples e tem erro aceitável; caso contrário,
        o modelo mantém o último nível observado.
      </div>

      <div class="table-wrap pb-table" id="pb-table"></div>
    `;

    dataTab.appendChild(panel);

    const select = $("#pb-mineral");
    const metrics = $("#pb-metrics");
    const chartTarget = $("#pb-chart");
    const tableTarget = $("#pb-table");

    const minerals = [...data.minerals_in_benchmark].sort((a, b) =>
      a.mineral_name.localeCompare(
        b.mineral_name,
        "pt-BR"
      )
    );

    select.innerHTML = minerals
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

    select.value = bauxite
      ? bauxite.mineral_id
      : minerals[0].mineral_id;

    function renderTable(selectedId) {
      tableTarget.innerHTML = `
        <table class="pn-table">
          <thead>
            <tr>
              <th>Mineral</th>
              <th class="num">Anos observados</th>
              <th>Método escolhido</th>
              <th class="num">Erro no backtest</th>
              <th class="num">Produção 2025</th>
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
                      >${escapeHtml(mineral.mineral_name)}</button>
                    </td>
                    <td class="num">${number(
                      mineral.observed_years
                    )}</td>
                    <td>${escapeHtml(
                      methodName(mineral.selected_method)
                    )}</td>
                    <td class="num">${percent(
                      mineral.backtest_smape_selected_pct
                    )}</td>
                    <td class="num">${tonnes(
                      mineral.production_latest_t
                    )}</td>
                  </tr>
                `
              )
              .join("")}
          </tbody>
        </table>
      `;

      tableTarget
        .querySelectorAll("[data-pb-mineral]")
        .forEach((button) => {
          button.addEventListener("click", () => {
            select.value = button.dataset.pbMineral;
            render();
            panel.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          });
        });
    }

    function render() {
      const id = select.value;

      const mineral = minerals.find(
        (item) => item.mineral_id === id
      );

      const observed = data.series
        .filter((row) => row.mineral_id === id)
        .sort((a, b) => Number(a.year) - Number(b.year));

      const projected = data.forecast
        .filter((row) => row.mineral_id === id)
        .sort((a, b) => Number(a.year) - Number(b.year));

      const forecast2040 = projected.find(
        (row) => Number(row.year) === 2040
      );

      metrics.innerHTML = `
        <div class="pb-metric">
          <span>Primeiro ano observado</span>
          <strong>${number(
            mineral.first_observed_year
          )}</strong>
          <small>Base do índice histórico = 100</small>
        </div>

        <div class="pb-metric">
          <span>Produção em 2025</span>
          <strong>${tonnes(
            mineral.production_latest_t
          )}</strong>
          <small>${number(
            mineral.observed_years
          )} anos observados</small>
        </div>

        <div class="pb-metric">
          <span>Método selecionado</span>
          <strong>${escapeHtml(
            methodName(mineral.selected_method)
          )}</strong>
          <small>Escolhido por backtest</small>
        </div>

        <div class="pb-metric">
          <span>Produção de referência em 2040</span>
          <strong>${
            forecast2040
              ? tonnes(forecast2040.production_reference_t)
              : "Não projetável"
          }</strong>
          <small>${
            forecast2040
              ? `Erro de backtest: ${percent(
                  mineral.backtest_smape_selected_pct
                )}`
              : "Produção de 2025 igual a zero"
          }</small>
        </div>
      `;

      chartTarget.innerHTML = chart(
        observed,
        projected,
        mineral.mineral_name
      );

      renderTable(id);
    }

    select.addEventListener("change", render);
    render();
  }

  async function init() {
    try {
      const response = await fetch(`${SOURCE}?v=20261115a`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Não foi possível carregar o benchmark.");
      }

      const data = await response.json();
      setup(data);
    } catch (error) {
      console.error(error);
    }
  }

  init();
})();
