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

export function initAdminFiltersSheet() {
  const trigger = document.querySelector("[data-filters-toggle]");
  const panel = document.querySelector("[data-filters-panel]");
  const backdrop = document.querySelector("[data-filters-backdrop]");
  if (!trigger || !panel || !backdrop) return;

  function onKeydown(event) {
    if (event.key === "Escape") close();
    trapFocus(panel, event);
  }

  function close() {
    panel.hidden = true;
    backdrop.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    document.removeEventListener("keydown", onKeydown);
    trigger.focus();
  }

  function open() {
    panel.hidden = false;
    backdrop.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    document.addEventListener("keydown", onKeydown);
    panel.querySelector(FOCUSABLE)?.focus();
  }

  trigger.addEventListener("click", open);
  backdrop.addEventListener("click", close);
  document.querySelector("[data-filters-close]")?.addEventListener("click", close);
}

initAdminFiltersSheet();
