const DEBOUNCE_MS = 300;

/** Search updates 300 ms after typing stops (docs/SPEC.md screen 16); also
 * works without JS, since the field sits in a plain GET form. */
function initSearchDebounce() {
  const form = document.getElementById("customers-search-form");
  const input = form?.querySelector("input[name='q']");
  if (!form || !input) return;
  let timer = null;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => form.requestSubmit(), DEBOUNCE_MS);
  });
}

/** The customer panel (pop-up 4) is a real page (GET /admin/customers/<id>),
 * not a client-side toggle, so Esc and a backdrop click just navigate to the
 * clean list URL instead of hiding an element. */
function initPanelClose() {
  const backdrop = document.querySelector("[data-customer-panel-backdrop]");
  if (!backdrop) return;
  const closeHref = backdrop.dataset.closeHref;
  backdrop.addEventListener("click", () => {
    window.location.href = closeHref;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") window.location.href = closeHref;
  });
  document.querySelector("[data-customer-panel-close]")?.focus();
}

/** Cancelling must also undo form_loading.js's button mutation, since that
 * listener runs in the same "submit" event regardless of which one of the
 * two was registered first. */
function initBlockConfirm() {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    const button = form.querySelector("button[type=submit]");
    const label = button?.querySelector("span");
    const originalText = label?.textContent;
    form.addEventListener("submit", (event) => {
      if (window.confirm(form.dataset.confirm)) return;
      event.preventDefault();
      if (button) {
        button.disabled = false;
        button.classList.remove("btn--loading");
      }
      if (label && originalText) label.textContent = originalText;
    });
  });
}

initSearchDebounce();
initPanelClose();
initBlockConfirm();
