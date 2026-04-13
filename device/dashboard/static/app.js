const fields = document.querySelectorAll("[data-field]");

async function refreshStatus() {
  if (!fields.length) {
    return;
  }

  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) {
      return;
    }
    const status = await response.json();
    fields.forEach((node) => {
      const key = node.dataset.field;
      if (Object.prototype.hasOwnProperty.call(status, key)) {
        node.textContent = status[key] || "None";
      }
    });
  } catch (error) {
    console.debug("Status refresh skipped", error);
  }
}

window.setInterval(refreshStatus, 5000);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/service-worker.js").catch(() => {});
  });
}
