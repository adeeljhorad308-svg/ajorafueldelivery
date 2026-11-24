export function initFormLoadingState() {
  document.querySelectorAll("form[data-loading-text]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("button[type=submit]");
      if (!button) return;
      button.disabled = true;
      button.classList.add("btn--loading");
      const label = button.querySelector("span");
      if (label) label.textContent = form.getAttribute("data-loading-text");
    });
  });
}
