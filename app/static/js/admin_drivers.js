import { initDialogs } from "./admin_dialogs.js";

initDialogs();

/** Quick on/off switch (docs/SPEC.md screen 18): either direction submits at
 * once, unlike the Services on/off switch - there is no confirm step. */
function initQuickToggle() {
  document.querySelectorAll("[data-driver-toggle]").forEach((input) => {
    input.addEventListener("change", () => input.closest("form")?.requestSubmit());
  });
}

initQuickToggle();
