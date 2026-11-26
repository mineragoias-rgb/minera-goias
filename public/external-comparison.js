(() => {
  "use strict";

  const SOURCE = "/data/previsao/previsao_v1.json";
  const EPE_GROWTH_RATE = 0.018;
  const FIRST_YEAR = 2027;
  const LAST_YEAR = 2035;

  const $ = (selector) => document.querySelector(selector);

  const number = (value, digits = 0) =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : new Intl.NumberFormat("pt-BR", {
          maximumFractionDigits: digits,
          minimumFractionDigits: digits,
        }).format(Number(value));

  const percentage = (value, digits = 1) =>
    `${number(value * 100, digits)}%`;

  const style = `
    #external-comparison-panel {
      margin-top: 24px;
    }

    .ec-metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(180px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }

    .ec-metric {
      padding: 14px 15px;
      background: #f4f8fa;
      border-left: 3px solid #0f6fb0;
    }

    .ec-metric.epe {
      border-left-color: #c2681b;
    }

    .ec-metric span {
      display: block;
      color: #5d7383;
      font-size: 12px;
      margin-bottom: 7px;
    }

    .ec-metric strong {
      display: block;
      color: #123a5a;
      font-size: 20px;
      line-height: 1.15;
    }

    .ec-metric small {
      display: block;
      color: #6b7e8a;
      font-size: 11px;
      margin-top: 6px;
      line-height: 1.35;
    }

    .ec-chart {
      overflow-x: auto;
      margin-top: 10px;
    }

    .ec-chart svg {
      display: block;
      min-width: 700px;
      max-width: 100%;
    }

    .ec-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      margin-top: 10px;
      color: #526a7a;
      font-size: 12px;
    }

    .ec-legend span {
      display: inline-flex;
      align-items: center;
      gap: 7px;
    }

    .ec-line {
      width: 20px;
      height: 3px;
      display: inline-block;
      border-radius: 3px;
    }

    .ec-note {
      border-left: 3px solid #c2681b;
      background: #fff8ef;
      color: #694d2f;
      padding: 11px 14px;
      font-size: 13px;
      line-height: 1.5;
      margin: 18px 0;
    }

    .ec-source {
      color: #607889;
      font-size: 12px;
      line-height: 1.5;
      margin-top: 16px;
    }

    .ec-source a {
      color: #0b5d93;
    }

    @media (max-width: 760px) {
      .ec-metrics {
        grid-template-columns: 1fr;
      }
    }
  `;

  function chart(model, epe) {
    const width = 920;
    const height = 330;
    const left = 58;
    const right = 24;
    const top = 20;
    const bottom = 42;

    const years = model.map((row) => row.year);
    const allValues = [
      ...model.map((row) => row.index),
      ...epe.map((row) => row.index),
    ];

    const minValue =
      Math.floor(Math.min(...allValues) / 5) * 5 - 5;
    const maxValue =
      Math.ceil(Math.max(...allValues) / 5) * 5 + 5;

    const x = (year) =>
      left +
      ((year - FIRST_YEAR) / (LAST_YEAR - FIRST_YEAR)) *
        (width - left - right);

    const y = (value) =>
      top +
      (1 - (value - minValue) / (maxValue - minValue)) *
        (height - top - bottom);

    const ticks = [];

    for (let value = minValue; value <= maxValue; value += 5) {
      ticks.push(value);
    }

    const grid = ticks
      .map(
        (value) => `
          <line
            x1="${left}"
            x2="${width - right}"
            y1="${y(value)}"
            y2="${y(value)}"
            stroke="#e4edf2"
          />
          <text
            x="${left - 9}"
            y="${y(value) + 4}"
            text-anchor="end"
            font-size="11"
            fill="#637787"
          >${number(value)}</text>
        `
      )
      .join("");

    const labels = years
      .map(
        (year) => `
          <text
            x="${x(year)}"
            y="${height - 16}"
            text-anchor="middle"
            font-size="11"
            fill="#637787"
          >${year}</text>
        `
      )
      .join("");

    const line = (data) =>
      data
        .map((row) => `${x(row.year)},${y(row.index)}`)
        .join(" ");

    return `
      <div class="ec-chart">
        <svg
          viewBox="0 0 ${width} ${height}"
          role="img"
          aria-label="Comparação de trajetórias de crescimento normalizadas"
        >
          ${grid}
          ${labels}

          <line
            x1="${left}"
            x2="${width - right}"
            y1="${y(100)}"
            y2="${y(100)}"
            stroke="#9fb3c2"
            stroke-dasharray="4 4"
          />

          <text
            x="${width - right}"
            y="${y(100) - 7}"
            text-anchor="end"
            font-size="11"
            fill="#637787"
          >2027 = 100</text>

          <polyline
            points="${line(model)}"
            fill="none"
            stroke="#0f6fb0"
            stroke-width="2.7"
            stroke-linejoin="round"
            stroke-linecap="round"
          />

          <polyline
            points="${line(epe)}"
            fill="none"
            stroke="#c2681b"
            stroke-width="2.7"
            stroke-linejoin="round"
            stroke-linecap="round"
          />

          ${model
            .map(
              (row) => `
                <circle
                  cx="${x(row.year)}"
                  cy="${y(row.index)}"
                  r="3.2"
                  fill="#0f6fb0"
                />
              `
            )
            .join("")}

          ${epe
            .map(
              (row) => `
                <circle
                  cx="${x(row.year)}"
                  cy="${y(row.index)}"
                  r="3.2"
                  fill="#c2681b"
                />
              `
            )
            .join("")}
        </svg>
      </div>

      <div class="ec-legend">
        <span>
          <i class="ec-line" style="background:#0f6fb0"></i>
          Modelo do projeto · Goiás · cinco minerais · eletricidade
        </span>
        <span>
          <i class="ec-line" style="background:#c2681b"></i>
          EPE PDE 2035 · Brasil · mineração e pelotização · energia final
        </span>
      </div>
    `;
  }

  function render(data) {
    const target = $("#pv-dados");

    if (!target || $("#external-comparison-panel")) return;

    const reference = data.total
      .filter(
        (row) =>
          row.cenario === "referencia" &&
          Number(row.ano) >= FIRST_YEAR &&
          Number(row.ano) <= LAST_YEAR
      )
      .sort((a, b) => Number(a.ano) - Number(b.ano));

    if (reference.length !== LAST_YEAR - FIRST_YEAR + 1) {
      return;
    }

    const baseEnergy = Number(reference[0].energia_mwh);

    const model = reference.map((row) => ({
      year: Number(row.ano),
      index: (Number(row.energia_mwh) / baseEnergy) * 100,
      energyMwh: Number(row.energia_mwh),
    }));

    const epe = model.map((row) => ({
      year: row.year,
      index:
        100 *
        Math.pow(EPE_GROWTH_RATE + 1, row.year - FIRST_YEAR),
    }));

    const modelCagr =
      Math.pow(
        model[model.length - 1].energyMwh / model[0].energyMwh,
        1 / (LAST_YEAR - FIRST_YEAR)
      ) - 1;

    const difference = EPE_GROWTH_RATE - modelCagr;

    const panel = document.createElement("article");
    panel.className = "panel pv-panel";
    panel.id = "external-comparison-panel";

    panel.innerHTML = `
      <h3>Comparação com projeção externa</h3>
      <p class="subtitle">
        Trajetórias de crescimento normalizadas, com 2027 = 100.
        A comparação testa a coerência do cenário, não os TWh absolutos.
      </p>

      <div class="ec-metrics">
        <div class="ec-metric">
          <span>Modelo · cenário referência</span>
          <strong>${percentage(modelCagr)}</strong>
          <small>
            Crescimento médio anual da eletricidade dos cinco minerais
            em Goiás, entre 2027 e 2035.
          </small>
        </div>

        <div class="ec-metric epe">
          <span>EPE PDE 2035</span>
          <strong>${percentage(EPE_GROWTH_RATE)}</strong>
          <small>
            Crescimento anual projetado para mineração e pelotização
            no Brasil, entre 2025 e 2035.
          </small>
        </div>

        <div class="ec-metric">
          <span>Diferença de ritmo</span>
          <strong>${number(difference * 100, 1)} p.p.</strong>
          <small>
            O nosso cenário cresce mais lentamente que o benchmark
            nacional da EPE.
          </small>
        </div>
      </div>

      ${chart(model, epe)}

      <div class="ec-note">
        <strong>Comparação de trajetória, não de nível:</strong>
        o modelo do projeto mede somente eletricidade de cinco minerais
        em Goiás. O PDE 2035 da EPE mede energia final de todo o setor
        nacional de mineração e pelotização, incluindo outras fontes
        energéticas e minerais. Por isso ambos são normalizados em
        2027 = 100 e não são comparados em TWh absolutos.
      </div>

      <div class="table-wrap">
        <table class="pn-table">
          <thead>
            <tr>
              <th>Ano</th>
              <th class="num">Modelo · índice</th>
              <th class="num">EPE · índice</th>
            </tr>
          </thead>
          <tbody>
            ${model
              .map(
                (row, index) => `
                  <tr>
                    <td>${row.year}</td>
                    <td class="num">${number(row.index, 1)}</td>
                    <td class="num">${number(
                      epe[index].index,
                      1
                    )}</td>
                  </tr>
                `
              )
              .join("")}
          </tbody>
        </table>
      </div>

      <p class="ec-source">
        Fonte externa:
        <a
          href="https://www.epe.gov.br/sites-pt/publicacoes-dados-abertos/publicacoes/Documents/PDE%202035_Relat%C3%B3rio%20Final_Envio%20MME_2026-11-05_rev4.pdf"
          target="_blank"
          rel="noopener"
        >EPE/MME, Plano Decenal de Expansão de Energia 2035</a>.
        O PDE projeta crescimento médio de 1,8% ao ano para o consumo
        final de energia do segmento “Mineração e Pelotização” entre
        2025 e 2035.
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
        throw new Error("Não foi possível carregar a previsão.");
      }

      render(await response.json());
    } catch (error) {
      console.error(error);
    }
  }

  init();
})();
