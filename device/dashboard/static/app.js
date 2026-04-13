const fields = document.querySelectorAll("[data-field]");
const imageGrid = document.querySelector("[data-image-grid]");

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

async function refreshImages() {
  if (!imageGrid) {
    return;
  }

  try {
    const response = await fetch("/api/images", { cache: "no-store" });
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    const images = payload.images || [];
    if (!images.length) {
      return;
    }

    const nextSignature = images.map((image) => image.src).join("|");
    if (imageGrid.dataset.signature === nextSignature) {
      return;
    }
    imageGrid.dataset.signature = nextSignature;
    imageGrid.classList.remove("mock-growth");
    imageGrid.innerHTML = "";

    images.forEach((image) => {
      const img = document.createElement("img");
      img.src = `${image.src}?v=${Date.now()}`;
      img.alt = image.alt || "Plant capture";
      imageGrid.appendChild(img);
    });
  } catch (error) {
    console.debug("Image refresh skipped", error);
  }
}

window.setInterval(refreshImages, 5000);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/service-worker.js").catch(() => {});
  });
}
