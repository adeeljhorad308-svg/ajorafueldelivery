import { initDialogs } from "./admin_dialogs.js";

const dialogs = initDialogs();

/** Turning a service on submits at once; turning it off reverts the switch
 * and opens the turn-off confirm dialog instead (docs/SPEC.md pop-up 5: the
 * dialog's own "Turn off" button is what actually submits). */
function initQuickToggle() {
  document.querySelectorAll("[data-service-toggle]").forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) {
        input.closest("form")?.requestSubmit();
        return;
      }
      input.checked = true;
      dialogs.open(input.dataset.turnoffDialog, input);
    });
  });
}

initQuickToggle();
