const VISIBLE_MS = 4000;

export function initToasts() {
  document.querySelectorAll(".toast").forEach((toast) => {
    const dismiss = () => toast.remove();
    const close = toast.querySelector("[data-toast-close]");
    if (close) close.addEventListener("click", dismiss);
    setTimeout(dismiss, VISIBLE_MS);
  });
}
