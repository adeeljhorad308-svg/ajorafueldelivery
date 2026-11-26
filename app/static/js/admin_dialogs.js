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

/** Shared pop-up open/close (bottom sheet / centred dialog, dialog.css):
 * backdrop click or Esc closes, focus stays inside, focus returns to the
 * opener. Reused by every admin screen with pop-ups 2-6, not just Order
 * details, so it also exposes open()/close() for a dialog triggered from
 * code (e.g. a switch flipped to "off") instead of a [data-dialog-open]
 * button click. */
export function initDialogs() {
  const backdrop = document.querySelector("[data-dialog-backdrop]");
  if (!backdrop) return { open() {}, close() {} };
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
    opener = trigger || null;
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

  return { open, close };
}
