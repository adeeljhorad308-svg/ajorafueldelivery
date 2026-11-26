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

function initDialogs() {
  const backdrop = document.querySelector("[data-dialog-backdrop]");
  if (!backdrop) return;
  let openPanel = null;
  let opener = null;

  function onKeydown(event) {
    if (event.key === "Escape") close();
    if (openPanel) trapFocus(openPanel, event);
  }

  function close() {
    if (openPanel) openPanel.hidden = true;
    backdrop.hidden = true;
    openPanel = null;
    document.removeEventListener("keydown", onKeydown);
    if (opener) opener.focus();
  }

  function open(id, trigger) {
    const panel = document.getElementById(id);
    if (!panel) return;
    opener = trigger;
    openPanel = panel;
    panel.hidden = false;
    backdrop.hidden = false;
    document.addEventListener("keydown", onKeydown);
    panel.querySelector(FOCUSABLE)?.focus();
  }

  document.querySelectorAll("[data-dialog-open]").forEach((trigger) => {
    trigger.addEventListener("click", () => open(trigger.dataset.dialogOpen, trigger));
  });
  document.querySelectorAll("[data-dialog-close]").forEach((button) => {
    button.addEventListener("click", close);
  });
  backdrop.addEventListener("click", close);
}

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

initDialogs();
initShowAllDrivers();
initDriverPick();
initCancelOtherReason();
initCopyButtons();
