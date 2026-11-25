import { buildIcon } from "./svg_icon.js";

const VISIBLE_MS = 4000;
const TOAST_ICONS = { success: "circle-check", error: "circle-exclamation", info: "circle-info" };

export function initToasts() {
  document.querySelectorAll(".toast").forEach((toast) => {
    const dismiss = () => toast.remove();
    const close = toast.querySelector("[data-toast-close]");
    if (close) close.addEventListener("click", dismiss);
    setTimeout(dismiss, VISIBLE_MS);
  });
}

// Builds and shows a toast from JS (live status changes), matching the
// server-rendered markup in components/toast.html.
export function showToast(type, message) {
  const area = document.getElementById("toast-area");
  if (!area) return;
  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  toast.setAttribute("role", "status");
  toast.appendChild(buildIcon(TOAST_ICONS[type] || "circle-info"));
  const text = document.createElement("p");
  text.className = "toast__message";
  text.textContent = message;
  toast.appendChild(text);
  const close = document.createElement("button");
  close.type = "button";
  close.className = "toast__close";
  close.setAttribute("aria-label", "Dismiss");
  close.appendChild(buildIcon("xmark"));
  toast.appendChild(close);
  area.appendChild(toast);
  const dismiss = () => toast.remove();
  close.addEventListener("click", dismiss);
  setTimeout(dismiss, VISIBLE_MS);
}
