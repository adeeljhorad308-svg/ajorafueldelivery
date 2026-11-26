import { initDialogs } from "./admin_dialogs.js";

function initShowAllDrivers() {
  document.querySelectorAll("[data-show-all-drivers]").forEach((trigger) => {
    trigger.addEventListener("click", () => {
      trigger
        .closest("[data-dialog]")
        ?.querySelectorAll("[data-driver-extra]")
        .forEach((row) => {
          row.hidden = false;
        });
      trigger.hidden = true;
    });
  });
}

function initDriverPick() {
  document.querySelectorAll("[data-driver-radio]").forEach((radio) => {
    radio.addEventListener("change", () => {
      const button = radio.closest("[data-dialog]")?.querySelector("[data-assign-submit] span");
      if (button) button.textContent = `Assign ${radio.dataset.driverName}`;
    });
  });
}

function initCancelOtherReason() {
  document.querySelectorAll("[data-cancel-reason]").forEach((radio) => {
    radio.addEventListener("change", () => {
      const otherField = radio.closest("[data-dialog]")?.querySelector("[data-cancel-other-field]");
      if (otherField) otherField.hidden = radio.value !== "Other";
    });
  });
}

function initCopyButtons() {
  document.querySelectorAll("[data-copy-value]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copyValue);
        button.classList.add("order-detail__copy-btn--copied");
        setTimeout(() => button.classList.remove("order-detail__copy-btn--copied"), 1500);
      } catch {
        // Clipboard access can be blocked by the browser; the value stays visible either way.
      }
    });
  });
}

function initAutoOpen(dialogs) {
  const target = document.querySelector("[data-open-dialog]");
  if (target) dialogs.open(target.dataset.openDialog);
}

const dialogs = initDialogs();
initAutoOpen(dialogs);
initShowAllDrivers();
initDriverPick();
initCancelOtherReason();
initCopyButtons();
