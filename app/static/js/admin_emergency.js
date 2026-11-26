import { createPoller } from "./polling.js";
import { buildIcon } from "./svg_icon.js";

const OVERDUE_MINUTES = 5;

function waitingMinutes(card) {
  const createdAt = new Date(card.dataset.createdAt).getTime();
  return Math.max(0, Math.round((Date.now() - createdAt) / 60000));
}

/** Recomputes each card's waiting timer from its own data-created-at and
 * reorders the list (docs/SPEC.md screen 15's 5-minute rule): an unassigned
 * request waiting over 5 minutes gets the red border and moves to the top,
 * oldest-waiting first within each group. Runs locally, not from the server
 * poll, so the timer still ticks between polls. */
function retick(container) {
  const cards = Array.from(container.querySelectorAll("[data-emergency-card]"));
  for (const card of cards) {
    const minutes = waitingMinutes(card);
    const overdue = minutes > OVERDUE_MINUTES;
    card.querySelector("[data-emergency-timer]").textContent = `Waiting ${minutes} min`;
    card.querySelector("[data-emergency-overdue-label]").hidden = !overdue;
    card.classList.toggle("emergency-card--overdue", overdue);
  }
  cards
    .sort((a, b) => {
      const aMinutes = waitingMinutes(a);
      const bMinutes = waitingMinutes(b);
      const aOverdue = aMinutes > OVERDUE_MINUTES;
      const bOverdue = bMinutes > OVERDUE_MINUTES;
      if (aOverdue !== bOverdue) return aOverdue ? -1 : 1;
      if (aMinutes !== bMinutes) return bMinutes - aMinutes;
      return Number(a.dataset.orderId) - Number(b.dataset.orderId);
    })
    .forEach((card) => container.append(card));
}

function updateSummary(count, oldestMinutes) {
  const summary = document.querySelector("[data-emergency-summary]");
  if (!summary) return;
  let title = summary.querySelector("[data-emergency-title]");
  const caption = summary.querySelector("[data-emergency-caption]");
  if (count === 0) {
    title?.remove();
    if (caption) caption.textContent = "Updates every 15 seconds";
    return;
  }
  if (!title) {
    title = document.createElement("p");
    title.className = "h4";
    title.dataset.emergencyTitle = "";
    summary.prepend(title);
  }
  // "open" is an adjective ("N open [requests]"), never pluralised.
  title.textContent = `${count} open · oldest waiting ${oldestMinutes} min`;
  if (caption) caption.textContent = "Oldest first · unassigned over 5 min goes to the top";
}

function cell(className, text) {
  const span = document.createElement("span");
  if (className) span.className = className;
  if (text) span.textContent = text;
  return span;
}

function buildCard(item) {
  const card = document.createElement("div");
  card.className = "emergency-card";
  card.dataset.emergencyCard = "";
  card.dataset.orderId = String(item.order_id);
  card.dataset.createdAt = item.created_at_iso;

  const top = cell("emergency-card__top");
  const timerText = cell(null, "Waiting 0 min");
  timerText.dataset.emergencyTimer = "";
  const timer = cell("emergency-card__timer");
  timer.append(buildIcon("clock"), timerText);
  const statusChip = cell("status-chip status-chip--pending");
  statusChip.append(buildIcon("clock"), cell(null, "Pending"));
  top.append(timer, cell("emergency-card__spacer"), statusChip);

  const overdueLabel = cell(
    "emergency-card__overdue",
    "Waiting over 5 min · assign a driver now",
  );
  overdueLabel.dataset.emergencyOverdueLabel = "";
  overdueLabel.hidden = true;

  const orderBlock = cell("emergency-card__order");
  const orderTitle = cell("h4", item.title);
  const orderMeta = cell("caption", item.placed_meta);
  orderBlock.append(orderTitle, orderMeta);

  const customer = cell("emergency-card__customer");
  const avatar = cell("driver-card__avatar", item.customer_initials);
  const who = cell("emergency-card__who");
  who.append(cell("body-strong", item.customer_name), cell("caption mono-amount", item.customer_phone_label));
  const callLink = document.createElement("a");
  callLink.className = "btn btn--outline btn--small";
  callLink.href = `tel:${item.customer_phone}`;
  callLink.append(buildIcon("phone"), cell(null, "Call"));
  customer.append(avatar, who, callLink);

  const addressFact = cell("emergency-card__fact");
  addressFact.append(buildIcon("location-dot"), cell(null, item.address_line));

  const driverFact = cell("emergency-card__fact emergency-card__fact--muted");
  driverFact.append(buildIcon("user"), cell(null, "Driver: not assigned"));

  const actions = cell("emergency-card__actions");
  const assignLink = document.createElement("a");
  assignLink.className = "btn btn--brand";
  assignLink.href = `${item.detail_url}?open=assign`;
  assignLink.append(buildIcon("user-check"), cell(null, "Assign driver"));
  const openLink = document.createElement("a");
  openLink.className = "btn btn--outline";
  openLink.href = item.detail_url;
  openLink.append(cell(null, "Open"));
  actions.append(assignLink, openLink);

  card.append(top, overdueLabel, orderBlock, customer, addressFact);
  if (item.vehicle_note) {
    const noteFact = cell("emergency-card__fact");
    noteFact.append(buildIcon("circle-info"), cell(null, item.vehicle_note));
    card.append(noteFact);
  }
  card.append(driverFact, actions);
  return card;
}

export function initEmergencyList() {
  const container = document.querySelector("[data-emergency-cards]");
  if (!container) return;
  let maxId = Number(container.dataset.maxEmergencyId || 0);

  const poller = createPoller({
    intervalMs: 15000,
    backoffMs: 60000,
    async check() {
      retick(container);
      let response;
      try {
        response = await fetch(`${document.querySelector("[data-admin-live]").dataset.liveUrl}?after=${maxId}`, {
          headers: { Accept: "application/json" },
        });
      } catch {
        return false;
      }
      if (!response.ok) return false;
      const data = await response.json();
      for (const item of data.new_emergencies) {
        if (item.order_id <= maxId) continue;
        container.append(buildCard(item));
        maxId = Math.max(maxId, item.order_id);
      }
      container.dataset.maxEmergencyId = String(maxId);
      retick(container);
      const cards = container.querySelectorAll("[data-emergency-card]");
      const oldest = Math.max(0, ...Array.from(cards).map(waitingMinutes));
      updateSummary(cards.length, oldest);
      return true;
    },
  });

  poller.start();
}

initEmergencyList();
