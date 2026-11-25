const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled])';

function trapFocus(panel, event) {
  if (event.key !== "Tab") return;
  const focusable = Array.from(panel.querySelectorAll(FOCUSABLE));
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function quantityText(summary, unitPrice, formatPkr) {
  if (summary.quantityTextForUnit) return summary.quantityTextForUnit(unitPrice, formatPkr);
  return `${summary.litres} L × ${formatPkr(unitPrice)}`;
}

function fillDialog(dialog, summary, formatPkr) {
  dialog.querySelector("[data-confirm-service]").textContent = summary.fuel_type;
  dialog.querySelector("[data-confirm-quantity]").textContent = quantityText(
    summary,
    summary.unitPrice,
    formatPkr,
  );
  dialog.querySelector("[data-confirm-deliver]").textContent = summary.deliverTo;
  dialog.querySelector("[data-confirm-total]").textContent = formatPkr(summary.total);
  dialog.querySelector("[data-price-banner]").hidden = true;
  dialog.querySelector("[data-confirm-form-error]").hidden = true;
}

function setPlacing(dialog, placing) {
  const confirmButton = dialog.querySelector('[data-action="confirm-order"]');
  const editButton = dialog.querySelector('[data-action="close-confirm"]:not(.dialog-panel__close)');
  confirmButton.disabled = placing;
  confirmButton.classList.toggle("btn--loading", placing);
  confirmButton.querySelector("span").textContent = placing
    ? confirmButton.dataset.loadingText
    : "Confirm order";
  if (editButton) editButton.disabled = placing;
}

function showPriceUpdate(dialog, data, summary, formatPkr) {
  const banner = dialog.querySelector("[data-price-banner]");
  banner.hidden = false;
  banner.querySelector(".alert-banner__message").textContent =
    `${summary.fuel_type} is now ${data.formatted_price}. Your new total is below.`;
  dialog.querySelector("[data-confirm-quantity]").textContent = quantityText(
    summary,
    parseFloat(data.unit_price),
    formatPkr,
  );
  dialog.querySelector("[data-confirm-total]").textContent = data.formatted_total;
}

function defaultRequestBody(summary) {
  return {
    fuel_type: summary.fuel_type,
    litres: summary.litres,
    address: summary.address,
    area: summary.area,
    note: summary.note,
    latitude: summary.latitude,
    longitude: summary.longitude,
    order_key: summary.orderKey,
    price_snapshot: summary.priceSnapshot,
  };
}

async function submitOrder(form, dialog, options) {
  const summary = options.summary(form);
  setPlacing(dialog, true);
  let response;
  try {
    response = await fetch(options.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": summary.csrfToken },
      body: JSON.stringify((options.buildRequestBody || defaultRequestBody)(summary)),
    });
  } catch {
    setPlacing(dialog, false);
    const errorEl = dialog.querySelector("[data-confirm-form-error]");
    errorEl.hidden = false;
    errorEl.textContent = "Check your internet and try again.";
    return;
  }

  const data = await response.json();
  if (response.ok && data.status === "ok") {
    window.location.href = data.redirect;
    return;
  }
  setPlacing(dialog, false);
  if (response.status === 409) {
    form.querySelector("[data-price-snapshot]").value = data.unit_price;
    showPriceUpdate(dialog, data, summary, options.formatPkr);
    return;
  }
  if (options.handleCustomError && options.handleCustomError(dialog, data, response)) return;
  const errorEl = dialog.querySelector("[data-confirm-form-error]");
  errorEl.hidden = false;
  errorEl.textContent = Object.values(data.errors || {})[0] || data.message || "Something went wrong. Try again.";
}

export function initConfirmOrderDialog(form, options) {
  const backdrop = form.closest(".order-page").querySelector("[data-confirm-backdrop]");
  const dialog = form.closest(".order-page").querySelector("[data-confirm-dialog]");
  let opener = null;

  function close() {
    dialog.hidden = true;
    backdrop.hidden = true;
    document.removeEventListener("keydown", onKeydown);
    if (opener) opener.focus();
  }

  function onKeydown(event) {
    if (event.key === "Escape") close();
    trapFocus(dialog, event);
  }

  function open(trigger) {
    if (!options.validate(form)) return;
    opener = trigger;
    fillDialog(dialog, options.summary(form), options.formatPkr);
    dialog.hidden = false;
    backdrop.hidden = false;
    document.addEventListener("keydown", onKeydown);
    dialog.querySelector('[data-action="confirm-order"]').focus();
  }

  document.querySelectorAll('[data-action="open-confirm"]').forEach((button) => {
    button.addEventListener("click", () => open(button));
  });
  dialog.querySelectorAll('[data-action="close-confirm"]').forEach((button) => {
    button.addEventListener("click", close);
  });
  backdrop.addEventListener("click", close);
  dialog
    .querySelector('[data-action="confirm-order"]')
    .addEventListener("click", () => submitOrder(form, dialog, options));
}
