import { COMMON_PASSWORD_SAMPLE } from "./common_passwords_sample.js";

const MIN_LENGTH = 8;

function setRuleState(rule, ok) {
  const use = rule.querySelector("use");
  rule.classList.toggle("auth-form__rule--ok", ok);
  if (use) {
    const spriteBase = use.getAttribute("href").split("#")[0];
    use.setAttribute("href", `${spriteBase}#icon-${ok ? "circle-check" : "circle-info"}`);
  }
}

export function initPasswordRules() {
  const form = document.querySelector("[data-password-rules]");
  if (!form) return;

  const passwordInput = form.querySelector("#field-password");
  const emailInput = form.querySelector("#field-email");
  const lengthRule = form.querySelector('[data-rule="length"]');
  const commonRule = form.querySelector('[data-rule="common"]');
  const emailRule = form.querySelector('[data-rule="email"]');
  if (!passwordInput) return;

  const update = () => {
    const password = passwordInput.value;
    const email = (emailInput ? emailInput.value : "").trim().toLowerCase();
    if (lengthRule) setRuleState(lengthRule, password.length >= MIN_LENGTH);
    if (commonRule) {
      setRuleState(commonRule, password.length > 0 && !COMMON_PASSWORD_SAMPLE.has(password.toLowerCase()));
    }
    if (emailRule) {
      setRuleState(emailRule, password.length > 0 && password.toLowerCase() !== email);
    }
  };

  passwordInput.addEventListener("input", update);
  if (emailInput) emailInput.addEventListener("input", update);
}
