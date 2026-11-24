export function initPasswordToggles() {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    const use = button.querySelector("use");
    const spriteBase = use ? use.getAttribute("href").split("#")[0] : null;

    button.addEventListener("click", () => {
      const fieldId = button.getAttribute("data-password-toggle");
      const input = document.getElementById(fieldId);
      if (!input) return;

      const willShow = input.type === "password";
      input.type = willShow ? "text" : "password";
      button.setAttribute("aria-pressed", String(willShow));
      button.setAttribute("aria-label", willShow ? "Hide password" : "Show password");
      if (use && spriteBase) {
        use.setAttribute("href", `${spriteBase}#icon-${willShow ? "eye-slash" : "eye"}`);
      }
    });
  });
}
