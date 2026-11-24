export function initErrorActions() {
  document.querySelectorAll("[data-action='reload']").forEach((el) => {
    el.addEventListener("click", () => window.location.reload());
  });
  document.querySelectorAll("[data-action='back']").forEach((el) => {
    el.addEventListener("click", () => window.history.back());
  });
}
