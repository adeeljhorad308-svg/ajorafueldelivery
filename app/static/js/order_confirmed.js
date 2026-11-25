const POLL_MS = 30000;

function fillDriverCard(card, driver) {
  card.hidden = false;
  card.querySelector("[data-driver-initials]").textContent = driver.initials;
  card.querySelector("[data-driver-name]").textContent = driver.name;
  card.querySelector("[data-driver-meta] span").textContent =
    `${driver.rating_label} · ${driver.vehicle_no}`;
  card.querySelector("[data-driver-call]").href = `tel:${driver.phone}`;
  card.querySelector("[data-driver-distance]").textContent = driver.distance_label;
  card.querySelector("[data-driver-eta]").textContent = `about ${driver.eta_minutes} min`;
}

export function initOrderConfirmedPolling() {
  const container = document.querySelector("[data-confirmed-card]");
  if (!container || container.dataset.assigned === "true") return;

  let timer = null;

  async function checkStatus() {
    let response;
    try {
      response = await fetch(container.dataset.statusUrl, {
        headers: { Accept: "application/json" },
      });
    } catch {
      return;
    }
    if (!response.ok) return;
    const data = await response.json();
    if (!data.driver) return;

    fillDriverCard(container.querySelector("[data-driver-card]"), data.driver);
    const searching = container.querySelector("[data-searching-banner]");
    if (searching) searching.hidden = true;
    container.dataset.assigned = "true";
    stop();
  }

  function stop() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function schedule() {
    stop();
    timer = setTimeout(async () => {
      await checkStatus();
      if (container.dataset.assigned !== "true") schedule();
    }, POLL_MS);
  }

  document.addEventListener("visibilitychange", () => {
    if (container.dataset.assigned === "true") return;
    if (document.hidden) {
      stop();
      return;
    }
    checkStatus().then(() => {
      if (container.dataset.assigned !== "true") schedule();
    });
  });

  schedule();
}

initOrderConfirmedPolling();
