import { createPoller } from "./polling.js";
import { buildIcon } from "./svg_icon.js";

function updateTabTitle(openEmergencies) {
  document.title = openEmergencies > 0 ? `(${openEmergencies}) AJORA Admin` : "AJORA Admin";
}

function updateSidebarBadge(openEmergencies) {
  document.querySelectorAll("[data-sidebar-emergency-badge]").forEach((badge) => {
    badge.textContent = String(openEmergencies);
    badge.hidden = openEmergencies === 0;
  });
}

function updateCount(selector, value) {
  const el = document.querySelector(selector);
  if (el) el.textContent = String(value);
}

function cell(className, text) {
  const span = document.createElement("span");
  span.className = className;
  span.textContent = text;
  return span;
}

function insertNewEmergencyRow(table, item) {
  const row = document.createElement("a");
  row.className = "latest-orders__row latest-orders__row--pinned latest-orders__row--new";
  row.href = item.detail_url;
  row.dataset.orderId = String(item.order_id);

  const orderCell = cell("latest-orders__order latest-orders__cell", item.order_number);
  orderCell.prepend(buildIcon("triangle-exclamation"));
  row.append(
    orderCell,
    cell("latest-orders__customer latest-orders__cell", item.customer_name),
    cell("latest-orders__service latest-orders__cell", "Emergency fuel"),
    cell("latest-orders__amount latest-orders__cell mono-amount", item.amount_label),
  );

  const statusCell = document.createElement("span");
  statusCell.className = "latest-orders__status";
  const chip = document.createElement("span");
  chip.className = "status-chip status-chip--emergency";
  chip.append(buildIcon("triangle-exclamation"), cell("", "Emergency"));
  statusCell.append(chip);
  row.append(statusCell, cell("latest-orders__time latest-orders__cell", "now"));

  table.prepend(row);
  setTimeout(() => row.classList.remove("latest-orders__row--new"), 2500);
}

export function initAdminLive() {
  const root = document.querySelector("[data-admin-live]");
  if (!root) return;

  const table = document.querySelector("[data-latest-orders]");
  let maxEmergencyId = table ? Number(table.dataset.maxEmergencyId || 0) : 0;

  const poller = createPoller({
    intervalMs: 15000,
    backoffMs: 60000,
    async check() {
      let response;
      try {
        response = await fetch(`${root.dataset.liveUrl}?after=${maxEmergencyId}`, {
          headers: { Accept: "application/json" },
        });
      } catch {
        return false;
      }
      if (!response.ok) return false;
      const data = await response.json();

      updateTabTitle(data.open_emergencies);
      updateSidebarBadge(data.open_emergencies);
      updateCount("[data-due-soon-count]", data.due_soon);
      updateCount("[data-call-needed-count]", data.call_needed);

      const body = document.querySelector("[data-latest-orders-body]");
      if (body && data.new_emergencies.length) {
        for (const item of data.new_emergencies) {
          insertNewEmergencyRow(body, item);
          maxEmergencyId = Math.max(maxEmergencyId, item.order_id);
        }
        if (table) table.dataset.maxEmergencyId = String(maxEmergencyId);
      }
      return true;
    },
  });

  poller.start();
}

initAdminLive();
