(() => {
  "use strict";

  const SOURCE = "/data/previsao/previsao_v1.json";
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

  const mwh = (value) =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : `${number(value, 0)} MWh`;

  const coefficient = (value) =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : `${number(value, 3)} MWh/t`;

  const percentage = (value) =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : `${number(Number(value) * 100, 0)}%`;

  const natureName = (nature) => {
    const names = {
      calculated: "Calculado",
      estimated: "Estimado",
      benchmark_proxy: "Benchmark externo (proxy)",
    };

    return names[nature] || nature || "—";
  };

  const style = `
    #energy-intensity-panel {
      margin-top: 24px;
    }

    .ei-metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(170px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }

    .ei-metric {
      padding: 14px 15px;
      background: #f4f8fa;
      border-left: 3px solid #0f6fb0;
    }

    .ei-metric span {
      display: block;
      font-size: 12px;
      color: #5d7383;
      margin-bottom: 7px;
    }

    .ei-metric strong {
      display: block;
      font-size: 20px;
      color: #123a5a;
      line-height: 1.15;
    }

    .ei-metric small {
      display: block;
      font-size: 11px;
      color: #6b7e8a;
      margin-top: 6px;
      line-height: 1.35;
    }

    .ei-chart {
      overflow-x: auto;
      margin-top: 10px;
    }

    .ei-chart svg {
      min-width: 700px;
      max-width: 100%;
      display: block;
    }

    .ei-note {
      border-left: 3px solid #c2681b;
      background: #fff8ef;
      color: #694d2f;
      padding: 11px 14px;
      margin: 18px 0;
      line-height: 1.5;
      font-size: 13px;
    }

    .ei-source {
      color: #607889;
      font-size: 12px;
      margin-top: 16px;
    }

    @media (max-width: 760px) {
      .ei-metrics {
        grid-template-columns: 1fr;
      }
    }
  `;

  const colors = {
    "Alumínio (Bauxita)": "#0f6fb0",
    Cobre: "#c2681b",
    Níquel: "#0d9488",
    Fosfato: "#8250c4",
    Amianto: "#b03a55",
  };

  function chart(minerals) {
    const width = 900;
    const height = 330;
    const left = 185;
    const right = 110;
    const top = 24;
    const bottom = 42;

    const sorted = [...minerals].sort(
      (a, b) => a.coefficient - b.coefficient
    );

    const maxValue =
      Math.max(...sorted.map((mineral) => mineral.coefficient)) *
      1.12;

    const rowHeight =
      (height - top - bottom) / Math.max(1, sorted.length);

    const x = (value) =>
      left + (value / maxValue) * (width - left - right);

    const ticks = [0, 2, 4, 6, 8, 10, 12].filter(
      (tick) => tick <= maxValue * 1.05
    );

    const grid = ticks
      .map(
        (tick) => `
          <line
            x1="${x(tick)}"
            x2="${x(tick)}"
            y1="${top}"
            y2="${height - bottom}"
            stroke="#e4edf2"
          />
          <text
            x="${x(tick)}"
            y="${height - 16}"
            text-anchor="middle"
            font-size="11"
            fill="#637787"
          >${number(tick, 0)}</text>
        `
      )
      .join("");

    const bars = sorted
      .map((mineral, index) => {
        const center = top + rowHeight * (index + 0.5);
        const barHeight = Math.min(30, rowHeight * 0.52);
        const color = colors[mineral.name] || "#57768b";

        return `
          <text
            x="${left - 12}"
            y="${center + 4}"
            text-anchor="end"
            font-size="12"
            fill="#294e67"
            font-weight="600"
          >${escapeHtml(mineral.name)}</text>

          <rect
            x="${left}"
            y="${center - barHeight / 2}"
            width="${Math.max(1, x(mineral.coefficient) - left)}"
            height="${barHeight}"
            rx="3"
            fill="${color}"
          />

          <text
            x="${x(mineral.coefficient) + 8}"
            y="${center + 4}"
            font-size="12"
            fill="#294e67"
            font-weight="600"
          >${escapeHtml(coefficient(mineral.coefficient))}</text>
        `;
      })
      .join("");

    return `
      <div class="ei-chart">
        <svg
          viewBox="0 0 ${width} ${height}"
          role="img"
          aria-label="Intensidade energética aplicada pelo modelo por mineral"
        >
          ${grid}
          ${bars}
          <text
            x="${(left + width - right) / 2}"
            y="${height - 2}"
            text-anchor="middle"
            font-size="11"
            fill="#637787"
          >MWh por tonelada na base produtiva do modelo</text>
        </svg>
      </div>
    `;
  }

  function render(data) {
    const target = $("#pv-dados");

    if (!target || $("#energy-intensity-panel")) return;

    const styleNode = document.createElement("style");
    styleNode.textContent = style;
    document.head.appendChild(styleNode);

    const minerals = data.minerais.map((mineral) => ({
      id: mineral.mineral_id,
      name: mineral.nome,
      basis: mineral.base_producao,
      coefficient: Number(mineral.coeficiente?.mwh_t),
      nature: mineral.coeficiente?.natureza,
      energyCcee: mineral.coeficiente?.energia_ccee_mwh,
      coveredProduction: mineral.coeficiente?.producao_coberta_t,
      coverage: mineral.coeficiente?.cobertura,
      confidence: mineral.coeficiente?.confianca,
      observation: mineral.coeficiente?.observacao,
    }));

    const highest = [...minerals].sort(
      (a, b) => b.coefficient - a.coefficient
    )[0];

    const panel = document.createElement("article");
    panel.className = "panel pv-panel";
    panel.id = "energy-intensity-panel";

    panel.innerHTML = `
      <h3>Diferenças no uso de energia por mineral</h3>
      <p class="subtitle">
        Intensidade energética aplicada no modelo: energia elétrica de 2025
        dividida pela produção na mesma base física.
      </p>

      <div class="ei-metrics">
        <div class="ei-metric">
          <span>Minerais com coeficiente utilizável</span>
          <strong>${minerals.length}</strong>
          <small>Os únicos que entram no total em TWh.</small>
        </div>

        <div class="ei-metric">
          <span>Maior intensidade no modelo</span>
          <strong>${escapeHtml(highest.name)}</strong>
          <small>${escapeHtml(
            coefficient(highest.coefficient)
          )} na base produtiva correspondente.</small>
        </div>

        <div class="ei-metric">
          <span>Fonte direta de energia</span>
          <strong>CCEE 2025</strong>
          <small>
            Bauxita é a exceção: usa benchmark externo por falta de
            consumo CCEE observável.
          </small>
        </div>
      </div>

      ${chart(minerals)}

      <div class="ei-note">
        <strong>Leitura correta:</strong> esta não é uma classificação
        universal de eficiência das minas. O cobre usa produção de
        <em>metal contido</em>; os demais usam principalmente produção
        <em>beneficiada</em>. O gráfico compara os coeficientes que o
        modelo aplica, sempre junto da base produtiva indicada abaixo.
      </div>

      <div class="table-wrap">
        <table class="pn-table">
          <thead>
            <tr>
              <th>Mineral</th>
              <th class="num">Coeficiente</th>
              <th>Base de produção</th>
              <th>Natureza</th>
              <th class="num">Cobertura</th>
              <th class="num">Energia CCEE 2025</th>
              <th>Confiança</th>
            </tr>
          </thead>
          <tbody>
            ${minerals
              .sort((a, b) => b.coefficient - a.coefficient)
              .map(
                (mineral) => `
                  <tr>
                    <td>${escapeHtml(mineral.name)}</td>
                    <td class="num">${escapeHtml(
                      coefficient(mineral.coefficient)
                    )}</td>
                    <td>${escapeHtml(mineral.basis)}</td>
                    <td>${escapeHtml(
                      natureName(mineral.nature)
                    )}</td>
                    <td class="num">${escapeHtml(
                      percentage(mineral.coverage)
                    )}</td>
                    <td class="num">${escapeHtml(
                      mwh(mineral.energyCcee)
                    )}</td>
                    <td>${escapeHtml(
                      mineral.confidence || "—"
                    )}</td>
                  </tr>
                `
              )
              .join("")}
          </tbody>
        </table>
      </div>

      <p class="ei-source">
        Fonte: base de intensidade energética do projeto, CCEE 2025 e
        produção física das operações cobertas. O simulador permite testar
        variações desses coeficientes sem alterar a produção projetada.
      </p>
    `;

    target.appendChild(panel);
  }

  async function init() {
    try {
      const response = await fetch(`${SOURCE}?v=20261115a`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Não foi possível carregar os coeficientes.");
      }

      render(await response.json());
    } catch (error) {
      console.error(error);
    }
  }

  init();
})();
