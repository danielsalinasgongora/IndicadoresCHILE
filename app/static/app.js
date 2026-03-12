let mainChart;
let riskChart;

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Error HTTP ${res.status}`);
  return res.json();
}

function groupSeries(rows) {
  const grouped = {};
  for (const r of rows) {
    if (!grouped[r.country]) grouped[r.country] = [];
    grouped[r.country].push(r);
  }
  return grouped;
}

function renderMainChart(rows, indicator) {
  const grouped = groupSeries(rows);
  const years = [...new Set(rows.map((r) => r.year))].sort((a, b) => a - b);
  const palette = ["#60a5fa", "#f59e0b", "#34d399"];
  const datasets = Object.entries(grouped).map(([country, values], idx) => ({
    label: `${indicator} - ${country}`,
    data: years.map((y) => values.find((v) => v.year === y)?.value ?? null),
    borderWidth: 2,
    tension: 0.25,
    borderColor: palette[idx % palette.length],
  }));

  if (mainChart) mainChart.destroy();
  mainChart = new Chart(document.getElementById("mainChart"), {
    type: "line",
    data: { labels: years, datasets },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e5e7eb" } } },
      scales: {
        x: { ticks: { color: "#d1d5db" } },
        y: { ticks: { color: "#d1d5db" } },
      },
    },
  });
}

function renderRiskChart(riskRows) {
  const years = riskRows.map((r) => r.year);
  const values = riskRows.map((r) => r.spread_bps);
  if (riskChart) riskChart.destroy();
  riskChart = new Chart(document.getElementById("riskChart"), {
    type: "bar",
    data: {
      labels: years,
      datasets: [{
        label: "Riesgo país (bps)",
        data: values,
        backgroundColor: "#a78bfa",
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e5e7eb" } } },
      scales: {
        x: { ticks: { color: "#d1d5db" } },
        y: { ticks: { color: "#d1d5db" } },
      },
    },
  });
}

function renderStats(insights) {
  const node = document.getElementById("statsCards");
  node.innerHTML = `
    <div class="stat-card">
      Brecha inflación CHL - Mundo
      <strong>${insights.inflation_gap_chile_world ?? "N/D"}%</strong>
    </div>
    <div class="stat-card">
      Brecha PIB CHL - OCDE
      <strong>${insights.gdp_gap_chile_oecd ?? "N/D"}%</strong>
    </div>
    <div class="stat-card">
      Eventos en periodo
      <strong>${insights.events_count}</strong>
    </div>
  `;
}

async function loadMainData() {
  const indicator = document.getElementById("indicatorSelect").value;
  const start = document.getElementById("startYear").value;
  const end = document.getElementById("endYear").value;

  const data = await fetchJson(`/api/series?indicator=${indicator}&countries=CHL,OED,WLD&start_year=${start}&end_year=${end}`);
  renderMainChart(data.data, indicator);

  const events = await fetchJson(`/api/context/events?start_year=${start}&end_year=${end}`);
  document.getElementById("eventsList").innerHTML = events
    .map((e) => `<li><b>${e.year}</b> - ${e.title}: ${e.description}</li>`)
    .join("");

  const risk = await fetchJson(`/api/risk/governments?start_year=${start}&end_year=${end}`);
  document.getElementById("riskList").innerHTML = risk
    .map((r) => `<li><b>${r.year}</b>: ${r.spread_bps} bps (${r.president})</li>`)
    .join("");
  renderRiskChart(risk);

  const insights = await fetchJson(`/api/insights/overview?start_year=${start}&end_year=${end}`);
  renderStats(insights);
}

async function sumCurves() {
  const left = document.getElementById("leftCurve").value;
  const right = document.getElementById("rightCurve").value;
  const start = document.getElementById("startYear").value;
  const end = document.getElementById("endYear").value;

  const result = await fetchJson(`/api/curve/sum?left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}&start_year=${start}&end_year=${end}`);
  document.getElementById("sumResult").textContent = JSON.stringify(result.data.slice(-8), null, 2);
}

document.getElementById("loadBtn").addEventListener("click", loadMainData);
document.getElementById("sumBtn").addEventListener("click", sumCurves);

loadMainData();
