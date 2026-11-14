/* Benchmark de produção mineral.
   Mostra uma visão geral das séries, uma tabela-resumo e o detalhe
   de cada mineral. Nenhum mineral adicional é convertido em TWh. */

(() => {
  "use strict";

  const SOURCE = "/data/previsao/production_benchmark_v1.json";

  const COPY = {
    pt: {
      title: "Benchmark de produção mineral",
      subtitle:
        "Produção beneficiada estadual observada para ampliar a análise além dos cinco minerais do modelo elétrico.",
      overviewTitle: "Evolução de todos os minerais do benchmark",
      overviewSub:
        "Índice base no primeiro ano com produção positiva = 100. A escala vertical é logarítmica para tornar visíveis séries com trajetórias muito diferentes.",
      summaryTitle: "Resumo das séries históricas",
      detailTitle: "Detalhe do mineral selecionado",
      mineral: "Mineral",
      view: "Visualização",
      index: "Índice desde o primeiro ano = 100",
      tonnes: "Produção observada (t)",
      series: "Séries históricas",
      indexed: "Índices calculados",
      coverage: "Cobertura mínima",
      firstYear: "Primeiro ano positivo",
      initialOutput: "Produção inicial (t)",
      latestOutput: "Produção em 2025 (t)",
      totalChange: "Variação até 2025",
      note:
        "Toneladas não são somadas entre minerais. O índice compara a evolução de cada mineral desde o primeiro ano com produção positiva. O benchmark não atribui demanda elétrica aos minerais adicionais.",
      source:
        "Fonte: interface consolidada do Squad 1 — produção beneficiada, observada e válida.",
      logScale: "Escala logarítmica",
      years: "anos observados",
    },
    en: {
      title: "Mineral production benchmark",
      subtitle:
        "Observed state-level beneficiated output used to broaden the analysis beyond the five minerals in the electricity model.",
      overviewTitle: "Evolution of all benchmark minerals",
      overviewSub:
        "Index base in the first year with positive output = 100. The vertical axis is logarithmic so that series with very different trajectories remain visible.",
      summaryTitle: "Historical-series summary",
      detailTitle: "Selected mineral detail",
      mineral: "Mineral",
      view: "View",
      index: "Index since first year = 100",
      tonnes: "Observed output (t)",
      series: "Historical series",
      indexed: "Calculated indices",
      coverage: "Minimum coverage",
      firstYear: "First positive year",
      initialOutput: "Initial output (t)",
      latestOutput: "Output in 2025 (t)",
      totalChange: "Change to 2025",
      note:
        "Tonnes are not added across minerals. The index compares each mineral with its own first year with positive output. This benchmark does not assign electricity demand to additional minerals.",
      source:
        "Source: Squad 1 consolidated interface — observed, valid beneficiated output.",
      logScale: "Logarithmic scale",
      years: "observed years",
    },
  };

  const COLORS = [
    "#0f6fb0",
    "#c2681b",
    "#0d9488",
    "#b03a55",
    "#8250c4",
    "#4e7d36",
    "#855d42",
    "#277a9a",
    "#9b4b76",
    "#8c6c13",
    "#3e6ea8",
    "#bd4c42",
    "#536d7a",
    "#4c8b70",
    "#9a5c2d",
    "#6c62a6",
    "#48766d",
    "#9c4775",
  ];

  const esc = (value) =>
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

  const language = () => (window.I18N?.lang === "en" ? "en" : "pt");
  const text = () => COPY[language()];
  const locale = () => (language() === "en" ? "en-US" : "pt-BR");

  const number = (value, decimals = 0) =>
    Number(value).toLocaleString(locale(), {
      maximumFractionDigits: decimals,
      minimumFractionDigits: decimals,
    });

  const percent = (value) => {
    const sign = value > 0 ? "+" : "";
    return `${sign}${number(value, 1)}%`;
  };

  let data = null;
  let selectedMineral = null;
  let selectedView = "index";
  let started = false;

  function createPanel() {
    const target = document.getElementById("pv-dados");

    if (!target || document.getElementById("pv-production-benchmark")) {
      return;
    }

    const panel = document.createElement("article");
    panel.id = "pv-production-benchmark";
    panel.className = "panel pv-panel";

    panel.innerHTML = `
      <style>
        #pv-production-benchmark .pb-toolbar {
          display: flex;
          align-items: end;
          flex-wrap: wrap;
          gap: 16px;
          margin: 16px 0;
        }

        #pv-production-benchmark .pb-toolbar label {
          color: #486170;
          display: block;
          font-size: 12px;
          font-weight: 700;
          margin-bottom: 6px;
        }

        #pv-production-benchmark .pb-toolbar select {
          min-width: 260px;
        }

        #pv-production-benchmark .pb-metrics {
          display: grid;
          gap: 12px;
          grid-template-columns: repeat(3, minmax(150px, 1fr));
          margin: 14px 0 20px;
        }

        #pv-production-benchmark .pb-metric {
          background: #f5f9fb;
          border-left: 3px solid #0f6fb0;
          padding: 12px 14px;
        }

        #pv-production-benchmark .pb-metric span,
        #pv-production-benchmark .pb-metric small {
          color: #637787;
          display: block;
          font-size: 12px;
        }

        #pv-production-benchmark .pb-metric strong {
          color: #14354e;
          display: block;
          font-size: 24px;
          margin: 3px 0;
        }

        #pv-production-benchmark .pb-chart {
          min-height: 330px;
          overflow-x: auto;
        }

        #pv-production-benchmark .pb-chart svg {
          display: block;
        }

        #pv-production-benchmark .pb-legend {
          display: flex;
          flex-wrap: wrap;
          gap: 7px 14px;
          margin: 10px 0 18px;
        }

        #pv-production-benchmark .pb-legend span {
          align-items: center;
          color: #4e6471;
          display: inline-flex;
          font-size: 11px;
          gap: 5px;
        }

        #pv-production-benchmark .pb-legend i {
          border-radius: 50%;
          display: inline-block;
          height: 8px;
          width: 8px;
        }

        #pv-production-benchmark .pb-note {
          background: #eef7fb;
          border-left: 3px solid #0f6fb0;
          color: #365363;
          line-height: 1.55;
          margin-top: 16px;
          padding: 12px 14px;
        }

        #pv-production-benchmark .pb-source {
          color: #637787;
          font-size: 12px;
          margin: 14px 0 0;
        }

        #pv-production-benchmark .pb-subtitle {
          color: #637787;
          font-size: 13px;
          margin: -4px 0 12px;
        }

        #pv-production-benchmark .pb-table-positive {
          color: #19715d;
          font-weight: 700;
        }

        #pv-production-benchmark .pb-table-negative {
          color: #9a3a4d;
          font-weight: 700;
        }

        @media (max-width: 650px) {
          #pv-production-benchmark .pb-metrics {
            grid-template-columns: 1fr;
          }

          #pv-production-benchmark .pb-toolbar select {
            min-width: 220px;
          }
        }
      </style>

      <div class="pv-head">
        <div>
          <h3 id="pb-title"></h3>
          <p class="subtitle" id="pb-subtitle"></p>
        </div>
      </div>

      <div class="pb-metrics" id="pb-metrics"></div>

      <h3 class="mk-sub" id="pb-overview-title"></h3>
      <p class="pb-subtitle" id="pb-overview-subtitle"></p>
      <div class="pb-chart" id="pb-overview-chart"></div>
      <div class="pb-legend" id="pb-overview-legend"></div>

      <h3 class="mk-sub" id="pb-summary-title"></h3>
      <div class="table-wrap" id="pb-summary-table"></div>

      <div class="pb-toolbar">
        <div>
          <label for="pb-mineral" id="pb-mineral-label"></label>
          <select id="pb-mineral"></select>
        </div>

        <div>
          <label for="pb-view" id="pb-view-label"></label>
          <select id="pb-view"></select>
        </div>
      </div>

      <h3 class="mk-sub" id="pb-detail-title"></h3>
      <div class="pb-chart" id="pb-detail-chart"></div>

      <div class="pb-note" id="pb-note"></div>
      <p class="pb-source" id="pb-source"></p>
    `;

    target.insertBefore(panel, target.firstChild);
  }

  function summaryTable(copy) {
    const rows = data.minerals_in_benchmark.map((mineral) => {
      const changeClass =
        mineral.change_from_base_pct >= 0
          ? "pb-table-positive"
          : "pb-table-negative";

      return `
        <tr>
          <td><b>${esc(mineral.mineral_name)}</b></td>
          <td class="num">${number(mineral.index_base_year)}</td>
          <td class="num">${number(mineral.index_base_production_t)}</td>
          <td class="num">${number(mineral.production_latest_t)}</td>
          <td class="num ${changeClass}">${esc(
            percent(mineral.change_from_base_pct)
          )}</td>
        </tr>
      `;
    });

    return `
      <table class="pn-table">
        <thead>
          <tr>
            <th>${esc(copy.mineral)}</th>
            <th class="num">${esc(copy.firstYear)}</th>
            <th class="num">${esc(copy.initialOutput)}</th>
            <th class="num">${esc(copy.latestOutput)}</th>
            <th class="num">${esc(copy.totalChange)}</th>
          </tr>
        </thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    `;
  }

  function overviewSvg() {
    const container = document.getElementById("pb-overview-chart");
    const width = Math.max(700, container.clientWidth || 940);
    const height = 390;
    const left = 62;
    const right = 18;
    const top = 18;
    const bottom = 42;

    const all = data.series.filter(
      (point) => Number(point.index_first_year_100) > 0
    );

    const years = all.map((point) => Number(point.year));
    const values = all.map((point) => Number(point.index_first_year_100));

    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);

    const minPositive = Math.min(...values);
    const maxPositive = Math.max(...values);

    const minExponent = Math.floor(Math.log10(minPositive));
    const maxExponent = Math.ceil(Math.log10(maxPositive));

    const minValue = 10 ** minExponent;
    const maxValue = 10 ** maxExponent;

    const x = (year) =>
      left +
      ((year - minYear) / Math.max(1, maxYear - minYear)) *
        (width - left - right);

    const y = (value) => {
      const fraction =
        (Math.log10(value) - Math.log10(minValue)) /
        Math.max(1, Math.log10(maxValue) - Math.log10(minValue));

      return top + (1 - fraction) * (height - top - bottom);
    };

    let svg = `
      <svg
        width="${width}"
        height="${height}"
        viewBox="0 0 ${width} ${height}"
        role="img"
        aria-label="${esc(text().overviewTitle)}"
      >
    `;

    for (let exponent = minExponent; exponent <= maxExponent; exponent += 1) {
      const value = 10 ** exponent;
      const lineY = y(value);

      svg += `
        <line
          x1="${left}"
          x2="${width - right}"
          y1="${lineY}"
          y2="${lineY}"
          stroke="#e4edf2"
        />
        <text
          x="${left - 8}"
          y="${lineY + 4}"
          text-anchor="end"
          fill="#637787"
          font-size="11"
        >${esc(number(value))}</text>
      `;
    }

    const baseline = y(100);

    svg += `
      <line
        x1="${left}"
        x2="${width - right}"
        y1="${baseline}"
        y2="${baseline}"
        stroke="#607d8b"
        stroke-width="1.3"
        stroke-dasharray="5 4"
      />
      <text
        x="${width - right}"
        y="${baseline - 7}"
        text-anchor="end"
        fill="#637787"
        font-size="11"
      >100</text>
    `;

    const yearStep = Math.max(1, Math.ceil((maxYear - minYear) / 6));

    for (let year = minYear; year <= maxYear; year += 1) {
      if ((year - minYear) % yearStep !== 0 && year !== maxYear) {
        continue;
      }

      svg += `
        <text
          x="${x(year)}"
          y="${height - 14}"
          text-anchor="middle"
          fill="#637787"
          font-size="11"
        >${year}</text>
      `;
    }

    data.minerals_in_benchmark.forEach((mineral, index) => {
      const color = COLORS[index % COLORS.length];

      const series = data.series
        .filter(
          (point) =>
            point.mineral_id === mineral.mineral_id &&
            Number(point.index_first_year_100) > 0
        )
        .sort((a, b) => a.year - b.year);

      if (!series.length) {
        return;
      }

      const path = series
        .map(
          (point, pointIndex) =>
            `${pointIndex === 0 ? "M" : "L"}${x(
              Number(point.year)
            )},${y(Number(point.index_first_year_100))}`
        )
        .join(" ");

      svg += `
        <path
          d="${path}"
          fill="none"
          stroke="${color}"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          opacity="0.9"
        >
          <title>${esc(mineral.mineral_name)}</title>
        </path>
      `;
    });

    svg += "</svg>";
    return svg;
  }

  function detailSvg(points, mode) {
    const container = document.getElementById("pb-detail-chart");
    const width = Math.max(620, container.clientWidth || 900);
    const height = 330;
    const left = 64;
    const right = 20;
    const top = 18;
    const bottom = 42;

    const years = points.map((point) => Number(point.year));
    const values = points.map((point) => Number(point.value));

    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    const maxValue = Math.max(...values, mode === "index" ? 100 : 0);
    const topValue = maxValue === 0 ? 1 : maxValue * 1.12;

    const x = (year) =>
      left +
      ((year - minYear) / Math.max(1, maxYear - minYear)) *
        (width - left - right);

    const y = (value) =>
      top + (1 - value / topValue) * (height - top - bottom);

    const ticks = 5;
    let svg = `
      <svg
        width="${width}"
        height="${height}"
        viewBox="0 0 ${width} ${height}"
        role="img"
        aria-label="${esc(text().detailTitle)}"
      >
    `;

    for (let step = 0; step <= ticks; step += 1) {
      const value = (topValue / ticks) * step;
      const lineY = y(value);

      svg += `
        <line
          x1="${left}"
          x2="${width - right}"
          y1="${lineY}"
          y2="${lineY}"
          stroke="#e4edf2"
        />
        <text
          x="${left - 9}"
          y="${lineY + 4}"
          text-anchor="end"
          fill="#637787"
          font-size="11"
        >${esc(number(value))}</text>
      `;
    }

    if (mode === "index") {
      const baseline = y(100);

      svg += `
        <line
          x1="${left}"
          x2="${width - right}"
          y1="${baseline}"
          y2="${baseline}"
          stroke="#607d8b"
          stroke-width="1.3"
          stroke-dasharray="5 4"
        />
        <text
          x="${width - right}"
          y="${baseline - 7}"
          text-anchor="end"
          fill="#637787"
          font-size="11"
        >100</text>
      `;
    }

    const yearStep = Math.max(1, Math.ceil((maxYear - minYear) / 6));

    for (let year = minYear; year <= maxYear; year += 1) {
      if ((year - minYear) % yearStep !== 0 && year !== maxYear) {
        continue;
      }

      svg += `
        <text
          x="${x(year)}"
          y="${height - 14}"
          text-anchor="middle"
          fill="#637787"
          font-size="11"
        >${year}</text>
      `;
    }

    const path = points
      .map(
        (point, index) =>
          `${index === 0 ? "M" : "L"}${x(Number(point.year))},${y(
            Number(point.value)
          )}`
      )
      .join(" ");

    svg += `
      <path
        d="${path}"
        fill="none"
        stroke="#0f6fb0"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    `;

    for (const point of points) {
      const label =
        mode === "index"
          ? number(point.value, 1)
          : number(point.value);

      svg += `
        <circle
          cx="${x(Number(point.year))}"
          cy="${y(Number(point.value))}"
          r="4"
          fill="#0f6fb0"
          stroke="#ffffff"
          stroke-width="2"
        >
          <title>${esc(`${point.year}: ${label}`)}</title>
        </circle>
      `;
    }

    svg += "</svg>";
    return svg;
  }

  function render() {
    if (!data || !selectedMineral) {
      return;
    }

    const copy = text();
    const mineral = data.minerals_in_benchmark.find(
      (item) => item.mineral_id === selectedMineral
    );

    const selectedSeries = data.series
      .filter((point) => point.mineral_id === selectedMineral)
      .sort((a, b) => a.year - b.year)
      .map((point) => ({
        year: point.year,
        value:
          selectedView === "index"
            ? Number(point.index_first_year_100)
            : Number(point.production_t),
      }));

    document.getElementById("pb-title").textContent = copy.title;
    document.getElementById("pb-subtitle").textContent = copy.subtitle;
    document.getElementById("pb-overview-title").textContent =
      copy.overviewTitle;
    document.getElementById("pb-overview-subtitle").textContent =
      copy.overviewSub;
    document.getElementById("pb-summary-title").textContent =
      copy.summaryTitle;
    document.getElementById("pb-detail-title").textContent =
      `${copy.detailTitle}: ${mineral.mineral_name}`;
    document.getElementById("pb-mineral-label").textContent = copy.mineral;
    document.getElementById("pb-view-label").textContent = copy.view;
    document.getElementById("pb-note").textContent = copy.note;
    document.getElementById("pb-source").textContent = copy.source;

    document.getElementById("pb-metrics").innerHTML = `
      <div class="pb-metric">
        <span>${esc(copy.series)}</span>
        <strong>${number(data.minerals_in_benchmark.length)}</strong>
        <small>${data.minimum_observed_years}+ ${esc(copy.years)}</small>
      </div>
      <div class="pb-metric">
        <span>${esc(copy.indexed)}</span>
        <strong>${number(data.minerals_in_benchmark.length)}</strong>
        <small>${esc(copy.firstYear)} = 100</small>
      </div>
      <div class="pb-metric">
        <span>${esc(copy.coverage)}</span>
        <strong>${number(data.minimum_observed_years)}+</strong>
        <small>${esc(data.production_basis)}</small>
      </div>
    `;

    document.getElementById("pb-overview-chart").innerHTML = overviewSvg();

    document.getElementById("pb-overview-legend").innerHTML =
      data.minerals_in_benchmark
        .map(
          (item, index) => `
            <span>
              <i style="background:${COLORS[index % COLORS.length]}"></i>
              ${esc(item.mineral_name)}
            </span>
          `
        )
        .join("");

    document.getElementById("pb-summary-table").innerHTML =
      summaryTable(copy);

    document.getElementById("pb-detail-chart").innerHTML = detailSvg(
      selectedSeries,
      selectedView
    );
  }

  function populate() {
    const copy = text();
    const mineralSelect = document.getElementById("pb-mineral");
    const viewSelect = document.getElementById("pb-view");

    mineralSelect.innerHTML = "";
    data.minerals_in_benchmark.forEach((mineral) => {
      const option = document.createElement("option");
      option.value = mineral.mineral_id;
      option.textContent = mineral.mineral_name;
      mineralSelect.appendChild(option);
    });

    viewSelect.innerHTML = `
      <option value="index">${esc(copy.index)}</option>
      <option value="tonnes">${esc(copy.tonnes)}</option>
    `;

    selectedMineral = data.minerals_in_benchmark[0].mineral_id;

    mineralSelect.onchange = (event) => {
      selectedMineral = event.target.value;
      render();
    };

    viewSelect.onchange = (event) => {
      selectedView = event.target.value;
      render();
    };

    render();
  }

  async function start() {
    if (started) {
      render();
      return;
    }

    createPanel();

    if (!document.getElementById("pv-production-benchmark")) {
      return;
    }

    try {
      const response = await fetch(SOURCE, { cache: "no-store" });

      if (!response.ok) {
        throw new Error("Benchmark data unavailable");
      }

      data = await response.json();
      started = true;
      populate();
    } catch (error) {
      document.getElementById("pb-overview-chart").innerHTML =
        '<p class="muted small">Benchmark data is not available yet.</p>';
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    start();

    document.addEventListener("click", (event) => {
      if (event.target.closest('#pv-tabs [data-pv="dados"]')) {
        setTimeout(render, 50);
      }
    });

    let resizeTimer;

    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(render, 160);
    });
  });
})();
