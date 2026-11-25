import { createPoller } from "./polling.js";

const STATUS_ICONS = {
  Pending: "clock",
  Assigned: "user-check",
  "On the Way": "truck-fast",
  Delivered: "circle-check",
  Cancelled: "circle-xmark",
};

function statusSlug(status) {
  return status.toLowerCase().replace(/ /g, "-");
}

function updateStatusChip(card, status, statusLabel) {
  const chip = card.querySelector(".status-chip");
  if (!chip) return;
  chip.className = `status-chip status-chip--${statusSlug(status)}`;
  const use = chip.querySelector("use");
  if (use) {
    const base = use.getAttribute("href").split("#")[0];
    use.setAttribute("href", `${base}#icon-${STATUS_ICONS[status] || "clock"}`);
  }
  const label = chip.querySelector("span");
  if (label) label.textContent = statusLabel;
}

function updateDriver(card, driver) {
  const etaBlock = card.querySelector("[data-active-order-eta]");
  if (!etaBlock) return;
  if (!driver) {
    etaBlock.hidden = true;
    return;
  }
  etaBlock.hidden = false;
  card.querySelector("[data-active-order-eta-value]").textContent = `about ${driver.eta_minutes} min`;
  card.querySelector("[data-active-order-driver-line]").textContent =
    `${driver.name} · ${driver.vehicle_no} · ${driver.distance_label}`;
}

export function initActiveOrderCard() {
  const card = document.querySelector("[data-active-order-card]");
  if (!card) return;

  const poller = createPoller({
    intervalMs: 30000,
    backoffMs: 60000,
    async check() {
      let response;
      try {
        response = await fetch(card.dataset.statusUrl, { headers: { Accept: "application/json" } });
      } catch {
        return false;
      }
      if (!response.ok) return false;
      const data = await response.json();
      updateStatusChip(card, data.status, data.status_label);
      updateDriver(card, data.driver);
      if (data.is_finished) {
        card.dataset.finished = "true";
        poller.stop();
      }
      return true;
    },
  });
  poller.start();
}

initActiveOrderCard();
