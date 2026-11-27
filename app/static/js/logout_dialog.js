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

/** Pop-up 7 Log out (docs/FIGMA.md P7, components/logout_dialog.html): one
 * dialog shared by every page's log out button (customer top bar, admin
 * sidebar - never both on the same page). The real #logout-form stays a
 * plain POST so logging out still works with no JS; this only intercepts
 * its submit button to ask "Log out of AJORA?" first. The dialog's own Log
 * out button submits that same form via its `form` attribute, so no JS is
 * needed to send it once confirmed. */
export function initLogoutDialog() {
  const trigger = document.querySelector('[data-action="open-logout"]');
  const backdrop = document.querySelector("[data-logout-backdrop]");
  const panel = document.querySelector("[data-logout-panel]");
  if (!trigger || !backdrop || !panel) return;

  function onKeydown(event) {
    if (event.key === "Escape") close();
    trapFocus(panel, event);
  }

  function close() {
    panel.hidden = true;
    backdrop.hidden = true;
    document.removeEventListener("keydown", onKeydown);
    trigger.focus();
  }

  function open(event) {
    event.preventDefault();
    panel.hidden = false;
    backdrop.hidden = false;
    document.addEventListener("keydown", onKeydown);
    panel.querySelector('[data-action="confirm-logout"]').focus();
  }

  trigger.addEventListener("click", open);
  panel.querySelectorAll('[data-action="close-logout"]').forEach((button) => {
    button.addEventListener("click", close);
  });
  backdrop.addEventListener("click", close);
}
