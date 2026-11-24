import { initErrorActions } from "./error_actions.js";
import { initFormLoadingState } from "./form_loading.js";
import { initMenuToggle } from "./menu.js";
import { initPasswordRules } from "./password_rules.js";
import { initPasswordToggles } from "./password_toggle.js";
import { initToasts } from "./toast.js";

initMenuToggle();
initPasswordToggles();
initToasts();
initFormLoadingState();
initErrorActions();
initPasswordRules();
