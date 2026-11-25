// Shared poll timing: pauses while the tab is hidden, rechecks immediately
// when it becomes visible again, and backs off after repeated errors
// (app/docs/PERFORMANCE.md: paused when hidden, back-off after errors).
export function createPoller({ check, intervalMs, backoffMs, maxErrors = 3 }) {
  let timer = null;
  let errorCount = 0;
  let stopped = false;

  function clear() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function schedule(delay) {
    clear();
    timer = setTimeout(run, delay);
  }

  async function run() {
    if (stopped || document.hidden) return;
    let ok = false;
    try {
      ok = await check();
    } catch {
      ok = false;
    }
    if (stopped) return;
    errorCount = ok ? 0 : errorCount + 1;
    schedule(errorCount >= maxErrors ? backoffMs : intervalMs);
  }

  document.addEventListener("visibilitychange", () => {
    if (stopped) return;
    if (document.hidden) {
      clear();
    } else {
      run();
    }
  });

  return {
    start: run,
    stop() {
      stopped = true;
      clear();
    },
  };
}
