(() => {
  "use strict";

  const FORECAST_SOURCE = "/data/previsao/previsao_v1.json";
  const BENCHMARK_SOURCE =
    "/data/previsao/production_benchmark_v1.json";

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

  const style = `
    #additional-minerals-status {
      margin-top: 24px;
    }

    .am-metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(160px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }

    .am-metric {
      padding: 14px 15px;
      background: #f4f8fa;
      border-left: 3px solid #57768b;
    }

    .am-metric span {
      display: block;
      font-size: 12px;
      color: #5d7383;
      margin-bottom: 7px;
    }

    .am-metric strong {
      display: block;
      font-size: 20px;
      color: #123a5a;
      line-height: 1.15;
    }

    .am-metric small {
      display: block;
      color: #6b7e8a;
      font-size: 11px;
      line-height: 1.35;
      margin-top: 6px;
    }

    .am-note {
      border-left: 3px solid #57768b;
      background: #f1f6f8;
      padding: 11px 14px;
      color: #355c72;
      font-size: 13px;
      line-height: 1.5;
      margin: 18px 0;
    }

    .am-status {
      color: #6a4b23;
      font-weight: 600;
    }

    @media (max-width: 760px) {
      .am-metrics {
        grid-template-columns: 1fr;
      }
    }
  `;

  function render(forecastData, benchmarkData) {
    const target = $("#pv-dados");

    if (!target || $("#additional-minerals-status")) return;

    const styleNode = document.createElement("style");
    styleNode.textContent = style;
    document.head.appendChild(styleNode);

    const modelMineralIds = new Set(
      forecastData.minerais.map((mineral) => mineral.mineral_id)
    );

    const additionalMinerals =
      benchmarkData.minerals_in_benchmark
        .filter(
          (mineral) => !modelMineralIds.has(mineral.mineral_id)
        )
        .map((mineral) => {
          const in2040 = benchmarkData.forecast.find(
            (row) =>
              row.mineral_id === mineral.mineral_id &&
              Number(row.year) === 2040
          );

          const base = Number(mineral.production_latest_t);

          const pressureIndex =
            in2040 && base > 0
              ? (Number(in2040.production_reference_t) / base) * 100
              : null;

          return {
            ...mineral,
            pressureIndex,
            hasForecast: Boolean(in2040),
          };
        })
        .sort((a, b) =>
          a.mineral_name.localeCompare(
            b.mineral_name,
            "pt-BR"
          )
        );

    const projectable = additionalMinerals.filter(
      (mineral) => mineral.hasForecast
    ).length;

    const panel = document.createElement("article");
    panel.className = "panel pv-panel";
    panel.id = "additional-minerals-status";

    panel.innerHTML = `
      <h3>Minerais adicionais: cobertura energética</h3>
      <p class="subtitle">
        Minerais incluídos no benchmark de produção, mas ainda fora da
        soma quantitativa de eletricidade.
      </p>

      <div class="am-metrics">
        <div class="am-metric">
          <span>Minerais adicionais no benchmark</span>
          <strong>${additionalMinerals.length}</strong>
          <small>
            Têm série histórica suficiente além dos cinco minerais do
            modelo elétrico.
          </small>
        </div>

        <div class="am-metric">
          <span>Com previsão de produção até 2040</span>
          <strong>${projectable}</strong>
          <small>
            Um caso fica apenas no histórico porque a produção de 2025
            é igual a zero.
          </small>
        </div>

        <div class="am-metric">
          <span>Com coeficiente MWh/t compatível</span>
          <strong>0</strong>
          <small>
            Por isso nenhum é somado ao total de TWh nesta versão.
          </small>
        </div>
      </div>

      <div class="am-note">
        <strong>O que já sabemos:</strong> a produção e a pressão
        energética relativa de cada mineral podem ser acompanhadas.
        <strong>O que ainda não afirmamos:</strong> quantos TWh cada
        mineral adicional consumirá. Para isso seria necessário reconciliar
        consumo CCEE, operação produtiva e unidade física do mineral.
      </div>

      <div class="table-wrap">
        <table class="pn-table">
          <thead>
            <tr>
              <th>Mineral</th>
              <th class="num">Produção em 2025</th>
              <th class="num">Índice de pressão em 2040<br>2025 = 100</th>
              <th>Coeficiente energético</th>
              <th>Tratamento no modelo</th>
            </tr>
          </thead>
          <tbody>
            ${additionalMinerals
              .map(
                (mineral) => `
                  <tr>
                    <td>${escapeHtml(mineral.mineral_name)}</td>
                    <td class="num">${escapeHtml(
                      tonnes(mineral.production_latest_t)
                    )}</td>
                    <td class="num">${
                      mineral.pressureIndex == null
                        ? "—"
                        : number(mineral.pressureIndex, 0)
                    }</td>
                    <td class="am-status">
                      ${
                        mineral.mineral_name === "Nióbio" ||
                        mineral.mineral_name === "Ouro"
                          ? "A validar"
                          : "Não disponível"
                      }
                    </td>
                    <td>${
                      mineral.hasForecast
                        ? "Benchmark produtivo; fora do total TWh"
                        : "Histórico apenas; sem previsão"
                    }</td>
                  </tr>
                `
              )
              .join("")}
          </tbody>
        </table>
      </div>

      <p class="source-line">
        Nióbio e ouro permanecem como candidatos para uma versão futura:
        há evidência energética, mas a base de produção e o coeficiente
        ainda exigem reconciliação antes de entrar no cálculo em TWh.
      </p>
    `;

    target.appendChild(panel);
  }

  async function init() {
    try {
      const [forecastResponse, benchmarkResponse] =
        await Promise.all([
          fetch(`${FORECAST_SOURCE}?v=20261115a`, {
            cache: "no-store",
          }),
          fetch(`${BENCHMARK_SOURCE}?v=20261115b`, {
            cache: "no-store",
          }),
        ]);

      if (!forecastResponse.ok || !benchmarkResponse.ok) {
        throw new Error("Não foi possível carregar os dados.");
      }

      const [forecastData, benchmarkData] = await Promise.all([
        forecastResponse.json(),
        benchmarkResponse.json(),
      ]);

      render(forecastData, benchmarkData);
    } catch (error) {
      console.error(error);
    }
  }

  init();
})();
