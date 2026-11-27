/* Reports charts (docs/SPEC.md FR-16): Chart.js, self-hosted, loaded only on
 * this page. Data comes from a <script type="application/json"> block, never
 * an inline script, and is read with JSON.parse. Each chart has a visible
 * canvas plus a sr-only data table in the template for screen readers. */

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function readData() {
  const block = document.querySelector("[data-report-data]");
  return block ? JSON.parse(block.textContent) : null;
}

function baseOptions(animate) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: animate ? {} : false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false } },
      y: { beginAtZero: true, grid: { color: cssVar("--color-border-default") } },
    },
  };
}

function renderOrdersPerDay(data, animate, brand) {
  const canvas = document.querySelector('[data-report-chart="orders_per_day"]');
  if (!canvas) return;
  new window.Chart(canvas, {
    type: "bar",
    data: {
      labels: data.orders_per_day.labels,
      datasets: [{ data: data.orders_per_day.values, backgroundColor: brand, borderRadius: 4 }],
    },
    options: baseOptions(animate),
  });
}

function renderOrdersByService(data, animate, brand) {
  const canvas = document.querySelector('[data-report-chart="orders_by_service"]');
  if (!canvas) return;
  new window.Chart(canvas, {
    type: "bar",
    data: {
      labels: data.orders_by_service.labels,
      datasets: [{ data: data.orders_by_service.values, backgroundColor: brand, borderRadius: 4 }],
    },
    options: {
      ...baseOptions(animate),
      indexAxis: "y",
      scales: {
        x: { beginAtZero: true, grid: { color: cssVar("--color-border-default") } },
        y: { grid: { display: false } },
      },
    },
  });
}

function renderPredictedVsActual(data, animate, brand, strong) {
  const canvas = document.querySelector('[data-report-chart="predicted_vs_actual"]');
  if (!canvas) return;
  new window.Chart(canvas, {
    type: "bar",
    data: {
      labels: data.predicted_vs_actual.labels,
      datasets: [
        {
          label: "Predicted",
          data: data.predicted_vs_actual.predicted,
          backgroundColor: strong,
          borderRadius: 3,
        },
        {
          label: "Actual",
          data: data.predicted_vs_actual.actual,
          backgroundColor: brand,
          borderRadius: 3,
        },
      ],
    },
    options: baseOptions(animate),
  });
}

export function initReportsCharts() {
  const data = readData();
  if (!data || typeof window.Chart === "undefined") return;

  window.Chart.defaults.font.family = cssVar("--font-sans");
  window.Chart.defaults.color = cssVar("--color-text-secondary");

  const animate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const brand = cssVar("--color-icon-brand");
  const strong = cssVar("--color-border-strong");

  renderOrdersPerDay(data, animate, brand);
  renderOrdersByService(data, animate, brand);
  renderPredictedVsActual(data, animate, brand, strong);
}

initReportsCharts();
