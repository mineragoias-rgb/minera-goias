/* Benchmark de produção mineral.
   Lê public/data/previsao/production_benchmark_v1.json e adiciona,
   na aba “Dados utilizados”, um gráfico interativo independente do
   modelo de demanda elétrica. */

(() => {
  "use strict";

  const SOURCE = "/data/previsao/production_benchmark_v1.json";

  const COPY = {
    pt: {
      title: "Benchmark de produção mineral",
      subtitle:
        "Séries estaduais observadas de produção beneficiada. O benchmark amplia a análise para minerais que não entram no modelo elétrico por falta de coeficiente energético compatível.",
      mineral: "Mineral",
      view: "Visualização",
      index: "Índice 2025 = 100",
      tonnes: "Produção observada (t)",
      series: "Séries históricas",
      normalized: "Com índice normalizado",
      basis: "Base do benchmark",
      note:
        "As toneladas não são somadas entre minerais. O índice permite comparar a evolução de cada mineral com seu próprio nível de 2025. Este painel não atribui demanda elétrica aos minerais adicionais.",
      unavailable:
        "Este mineral teve produção igual a zero em 2025; por isso, não recebe índice base 2025 = 100. Veja a série em toneladas.",
      source: "Fonte: interface consolidada do Squad 1 · produção beneficiada, observada e válida.",
      axisIndex: "Índice",
      axisTonnes: "t",
    },
    en: {
      title: "Mineral production benchmark",
      subtitle:
        "Observed state-level beneficiated-output series. This benchmark broadens the analysis to minerals that are not included in the electricity model because they lack a compatible energy coefficient.",
      mineral: "Mineral",
      view: "View",
      index: "Index 2025 = 100",
      tonnes: "Observed output (t)",
      series: "Historical series",
      normalized: "With normalised index",
      basis: "Benchmark basis",
      note:
        "Tonnes are not added across minerals. The index compares each mineral with its own 2025 level. This panel does not assign electricity demand to additional minerals.",
      unavailable:
        "This mineral had zero output in 2025, so it cannot receive a 2025 = 100 index. View the series in tonnes instead.",
      source: "Source: Squad 1 consolidated interface · observed, valid beneficiated output.",
      axisIndex: "Index",
      axisTonnes: "t",
    },
  };

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

  const locale = () => (window.I18N?.lang === "en" ? "en-US" : "pt-BR");

  const number = (value, decimals = 0) =>
    Number(value).toLocaleString(locale(), {
      maximumFractionDigits: decimals,
      minimumFractionDigits: decimals,
    });

  const text = () => COPY[window.I18N?.lang === "en" ? "en" : "pt"];

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
          gap: 18px;
          align-items: end;
          flex-wrap: wrap;
          margin: 18px 0 14px;
        }

        #pv-production-benchmark .pb-toolbar label {
          display: block;
          margin-bottom: 6px;
          color: #486170;
          font-size: 12px;
          font-weight: 700;
        }

        #pv-production-benchmark .pb-toolbar select {
          min-width: 220px;
        }

        #pv-production-benchmark .pb-metrics {
          display: grid;
          grid-template-columns: repeat(3, minmax(150px, 1fr));
          gap: 12px;
          margin: 14px 0 18px;
        }

        #pv-production-benchmark .pb-metric {
          border-left: 3px solid #0f6fb0;
          background: #f5f9fb;
          padding: 12px 14px;
        }

        #pv-production-benchmark .pb-metric span,
        #pv-production-benchmark .pb-metric small {
          display: block;
          color: #637787;
          font-size: 12px;
        }

        #pv-production-benchmark .pb-metric strong {
          display: block;
          color: #14354e;
          font-size: 24px;
          margin: 3px 0;
        }

        #pv-production-benchmark .pb-note {
          border-left: 3px solid #0f6fb0;
          background: #eef7fb;
          color: #365363;
          line-height: 1.55;
          margin-top: 16px;
          padding: 12px 14px;
        }

        #pv-production-benchmark .pb-warning {
          color: #805b12;
          font-size: 13px;
          margin: 4px 0 12px;
        }

        #pv-production-benchmark .pb-source {
          color: #637787;
          font-size: 12px;
          margin: 14px 0 0;
        }

        #pv-production-benchmark .pb-chart {
          min-height: 320px;
          overflow-x: auto;
        }

        @media (max-width: 650px) {
          #pv-production-benchmark .pb-metrics {
            grid-template-columns: 1fr;
          }
        }
      </style>

      <div class="pv-head">
        <div>
          <h3 id="pb-title"></h3>
          <p class="subtitle" id="pb-subtitle"></p>
        </div>
      </div>

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

      <div class="pb-metrics" id="pb-metrics"></div>
      <p class="pb-warning" id="pb-warning" hidden></p>
      <div class="pb-chart" id="pb-chart"></div>
      <div class="pb-note" id="pb-note"></div>
      <p class="pb-source" id="pb-source"></p>
    `;

    target.insertBefore(panel, target.firstChild);
  }

  function chartSvg(points, mode) {
    const container = document.getElementById("pb-chart");
    const width = Math.max(620, container.clientWidth || 860);
    const height = 330;
    const left = 64;
    const right = 20;
    const top = 18;
    const bottom = 42;

    const clean = points.filter((point) => Number.isFinite(point.value));

    if (!clean.length) {
      return "";
    }

    const years = clean.map((point) => point.year);
    const values = clean.map((point) => point.value);

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
        aria-label="${esc(
          mode === "index"
            ? "Índice de produção mineral"
            : "Produção mineral observada"
        )}"
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
        >${esc(number(value, mode === "index" ? 0 : 0))}</text>
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
          stroke="#667f90"
          stroke-width="1.2"
          stroke-dasharray="5 4"
        />
        <text
          x="${width - right}"
          y="${baseline - 7}"
          text-anchor="end"
          fill="#637787"
          font-size="11"
        >2025 = 100</text>
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

    const path = clean
      .map(
        (point, index) =>
          `${index === 0 ? "M" : "L"}${x(point.year)},${y(point.value)}`
      )
      .join(" ");

    svg += `
      <path
        d="${path}"
        fill="none"
        stroke="#0f6fb0"
        stroke-width="3"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
    `;

    for (const point of clean) {
      const valueLabel =
        mode === "index"
          ? number(point.value, 1)
          : number(point.value, 0);

      svg += `
        <circle
          cx="${x(point.year)}"
          cy="${y(point.value)}"
          r="4"
          fill="#0f6fb0"
          stroke="#ffffff"
          stroke-width="2"
        >
          <title>${esc(`${point.year}: ${valueLabel}`)}</title>
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

    if (!mineral) {
      return;
    }

    if (selectedView === "index" && !mineral.can_normalize_2025) {
      selectedView = "tonnes";
      document.getElementById("pb-view").value = "tonnes";
    }

    const series = data.series
      .filter((item) => item.mineral_id === selectedMineral)
      .sort((a, b) => a.year - b.year)
      .map((item) => ({
        year: item.year,
        value:
          selectedView === "index"
            ? Number(item.index_2025_100)
            : Number(item.production_t),
      }));

    const normalised = data.minerals_in_benchmark.filter(
      (item) => item.can_normalize_2025
    ).length;

    document.getElementById("pb-title").textContent = copy.title;
    document.getElementById("pb-subtitle").textContent = copy.subtitle;
    document.getElementById("pb-mineral-label").textContent = copy.mineral;
    document.getElementById("pb-view-label").textContent = copy.view;
    document.getElementById("pb-note").textContent = copy.note;
    document.getElementById("pb-source").textContent = copy.source;

    document.getElementById("pb-metrics").innerHTML = `
      <div class="pb-metric">
        <span>${esc(copy.series)}</span>
        <strong>${number(data.minerals_in_benchmark.length)}</strong>
        <small>${mineral.first_year}–${mineral.last_year}</small>
      </div>
      <div class="pb-metric">
        <span>${esc(copy.normalized)}</span>
        <strong>${number(normalised)}</strong>
        <small>${esc(copy.index)}</small>
      </div>
      <div class="pb-metric">
        <span>${esc(copy.basis)}</span>
        <strong>${esc(data.production_basis)}</strong>
        <small>${mineral.observed_years} anos observados</small>
      </div>
    `;

    const warning = document.getElementById("pb-warning");
    warning.textContent = copy.unavailable;
    warning.hidden = mineral.can_normalize_2025;

    document.getElementById("pb-chart").innerHTML = chartSvg(
      series,
      selectedView
    );
  }

  function populate() {
    const copy = text();
    const mineralSelect = document.getElementById("pb-mineral");
    const viewSelect = document.getElementById("pb-view");

    mineralSelect.innerHTML = "";
    for (const mineral of data.minerals_in_benchmark) {
      const option = document.createElement("option");
      option.value = mineral.mineral_id;
      option.textContent = mineral.mineral_name;
      mineralSelect.appendChild(option);
    }

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
      const chart = document.getElementById("pb-chart");

      if (chart) {
        chart.innerHTML =
          '<p class="muted small">Benchmark data is not available yet.</p>';
      }
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
