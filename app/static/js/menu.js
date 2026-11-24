export function initMenuToggle() {
  const toggle = document.querySelector("[data-menu-toggle]");
  const sheet = document.querySelector("[data-menu-sheet]");
  if (!toggle || !sheet) return;

  toggle.addEventListener("click", () => {
    const willOpen = sheet.hidden;
    sheet.hidden = !willOpen;
    toggle.setAttribute("aria-expanded", String(willOpen));
    toggle.setAttribute("aria-label", willOpen ? "Close menu" : "Open menu");
  });
}
