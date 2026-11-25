import { createPoller } from "./polling.js";
import { fillDriverCard } from "./driver_card.js";
import { showToast } from "./toast.js";
import { buildIcon } from "./svg_icon.js";

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

function formatClock(date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Karachi",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).formatToParts(date);
  const value = (type) => parts.find((p) => p.type === type).value;
  return `${value("hour")}:${value("minute")} ${value("dayPeriod").toLowerCase()}`;
}

function announce(page, message) {
  const region = page.querySelector("[data-live-region]");
  if (region) region.textContent = message;
}

function updateStatusChip(page, status, statusLabel) {
  const chip = page.querySelector("[data-track-status-chip] .status-chip");
  if (!chip) return;
  chip.className = `status-chip status-chip--${statusSlug(status)}`;
  const use = chip.querySelector("use");
  if (use) use.setAttribute("href", use.getAttribute("href").split("#")[0] + `#icon-${STATUS_ICONS[status] || "clock"}`);
  const label = chip.querySelector("span");
  if (label) label.textContent = statusLabel;
}

function updateSteps(page, steps) {
  const card = page.querySelector("[data-steps-card]");
  if (!card || !steps || !steps.length) {
    if (card) card.hidden = true;
    return;
  }
  card.hidden = false;
  const rows = card.querySelectorAll("[data-step]");
  let justCurrent = null;
  steps.forEach((step, index) => {
    const row = rows[index];
    if (!row) return;
    const wasCurrent = row.classList.contains("status-steps__row--current");
    row.className = `status-steps__row status-steps__row--${step.state}`;
    row.querySelector("[data-step-time]").textContent = step.time_label;
    const dot = row.querySelector(".status-steps__dot");
    dot.textContent = "";
    if (step.state === "done") dot.appendChild(buildIcon("check"));
    if (step.state === "current" && !wasCurrent) justCurrent = row;
  });
  if (justCurrent) {
    justCurrent.classList.add("status-steps__row--just-updated");
    setTimeout(() => justCurrent.classList.remove("status-steps__row--just-updated"), 300);
  }
}

function updateEta(page, data) {
  const etaCard = page.querySelector("[data-eta-card]");
  const searching = page.querySelector("[data-searching-banner]");
  if (data.driver) {
    etaCard.hidden = false;
    if (searching) searching.hidden = true;
    page.querySelector("[data-eta-value]").textContent = data.eta_text;
    page.querySelector("[data-eta-updated]").textContent =
      `Updated ${formatClock(new Date())} · checks every 30 seconds`;
    page.dataset.etaTarget = data.eta_target || "";
  } else {
    etaCard.hidden = true;
    if (searching) searching.hidden = !!data.is_finished;
  }
}

function updateFinishedState(page, data) {
  if (data.status === "Delivered") {
    page.querySelector("[data-delivered-card]").hidden = false;
    page.querySelector("[data-delivered-label]").textContent = data.delivered_label;
    page.querySelector("[data-delivered-card] .finished-card__message").textContent =
      data.delivered_sub_label;
  }
  if (data.status === "Cancelled") {
    page.querySelector("[data-cancelled-banner]").hidden = false;
    page.querySelector("[data-cancelled-label]").textContent = data.cancelled_label;
    page.querySelector("[data-cancelled-reason]").textContent = data.reason_label;
  }
  if (data.is_finished) {
    page.querySelector("[data-finished-note]").hidden = false;
    page.querySelector("[data-order-again]").hidden = false;
  }
}

function setOffline(page, isOffline) {
  const banner = page.querySelector("[data-offline-banner]");
  if (banner) banner.hidden = !isOffline;
}

function recomputeEta(page) {
  if (page.dataset.finished === "true") return;
  const target = page.dataset.etaTarget;
  const valueEl = page.querySelector("[data-eta-value]");
  const etaCard = page.querySelector("[data-eta-card]");
  if (!target || !valueEl || etaCard.hidden) return;
  const remaining = Math.max(0, Math.round((new Date(target) - new Date()) / 60000));
  valueEl.textContent = remaining <= 0 ? "Arriving any moment" : `about ${remaining} min`;
}

function initSummaryFold(page) {
  const fold = page.querySelector("[data-summary-fold]");
  const toggle = page.querySelector("[data-summary-toggle]");
  if (!fold || !toggle) return;
  toggle.addEventListener("click", () => {
    const isOpen = fold.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
  });
}

export function initOrderTrack() {
  const page = document.querySelector("[data-track-page]");
  if (!page) return;

  initSummaryFold(page);

  const poller = createPoller({
    intervalMs: 30000,
    backoffMs: 60000,
    async check() {
      let response;
      try {
        response = await fetch(page.dataset.statusUrl, { headers: { Accept: "application/json" } });
      } catch {
        setOffline(page, true);
        return false;
      }
      if (!response.ok) {
        setOffline(page, true);
        return false;
      }
      setOffline(page, false);
      const data = await response.json();
      const previousStatus = page.dataset.status;

      updateStatusChip(page, data.status, data.status_label);
      updateSteps(page, data.steps);
      updateEta(page, data);
      updateFinishedState(page, data);
      const driverLabel = page.querySelector("[data-driver-label]");
      if (data.driver) {
        fillDriverCard(page.querySelector("[data-driver-card]"), data.driver);
        if (driverLabel) driverLabel.hidden = false;
      }

      if (data.status !== previousStatus) {
        announce(page, `${data.status_label}`);
        if (data.status === "On the Way") showToast("success", "Your driver is on the way");
      }
      page.dataset.status = data.status;

      if (data.is_finished) {
        page.dataset.finished = "true";
        poller.stop();
      }
      return true;
    },
  });

  document.querySelector("[data-retry-button]")?.addEventListener("click", () => poller.start());

  if (page.dataset.finished !== "true") {
    poller.start();
    setInterval(() => recomputeEta(page), 60000);
  }
}

initOrderTrack();
