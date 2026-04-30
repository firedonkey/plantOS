import logging
import threading
from urllib.parse import unquote
from dataclasses import dataclass

from flask import Flask, jsonify, render_template_string, request
from werkzeug.serving import make_server

from .network import NetworkManager


logger = logging.getLogger(__name__)


SETUP_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PlantLab Setup</title>
    <style>
      :root {
        color-scheme: light;
        --green: #2f7d4b;
        --text: #17201a;
        --muted: #566259;
        --line: #d9e1d8;
        --soft: #f6f8f4;
        --error: #9b332b;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        background: var(--soft);
        color: var(--text);
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      main {
        width: min(520px, calc(100% - 32px));
        margin: 0 auto;
        padding: 42px 0;
      }

      .card {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 24px;
        background: #fff;
        box-shadow: 0 16px 40px rgba(23, 32, 26, 0.07);
      }

      .eyebrow {
        margin: 0 0 8px;
        color: var(--green);
        font-size: 0.78rem;
        font-weight: 850;
        letter-spacing: 0;
        text-transform: uppercase;
      }

      h1 {
        margin: 0 0 10px;
        font-size: 2rem;
        letter-spacing: 0;
      }

      p {
        color: var(--muted);
        line-height: 1.55;
      }

      label {
        display: grid;
        gap: 8px;
        margin-top: 16px;
        font-weight: 700;
      }

      input {
        width: 100%;
        min-height: 42px;
        border: 1px solid #cfd8cf;
        border-radius: 8px;
        padding: 8px 10px;
        font: inherit;
      }

      select {
        width: 100%;
        min-height: 42px;
        border: 1px solid #cfd8cf;
        border-radius: 8px;
        padding: 8px 10px;
        background: #fff;
        font: inherit;
      }

      input:focus {
        outline: 2px solid rgba(47, 125, 75, 0.22);
        border-color: var(--green);
      }

      select:focus {
        outline: 2px solid rgba(47, 125, 75, 0.22);
        border-color: var(--green);
      }

      .password-row {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 8px;
      }

      .manual-ssid {
        display: none;
      }

      .manual-ssid.visible {
        display: block;
      }

      .hidden {
        display: none;
      }

      .secondary-button {
        min-height: 42px;
        border: 1px solid #cfd8cf;
        border-radius: 8px;
        padding: 8px 10px;
        background: #fff;
        color: var(--text);
        font: inherit;
        font-weight: 750;
      }

      button {
        cursor: pointer;
      }

      .submit-button {
        width: 100%;
        min-height: 44px;
        margin-top: 20px;
        border: 1px solid var(--green);
        border-radius: 8px;
        background: var(--green);
        color: #fff;
        font: inherit;
        font-weight: 800;
      }

      .submit-button:disabled {
        cursor: wait;
        opacity: 0.65;
      }

      .hint {
        margin-top: 18px;
        font-size: 0.92rem;
      }

      .status {
        display: none;
        margin-top: 16px;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 12px;
        background: #f7faf6;
        color: var(--muted);
        font-weight: 700;
      }

      .status.visible {
        display: block;
      }

      .status.success {
        border-color: #b8d8c0;
        background: #eff9f1;
        color: var(--green);
      }

      .status.error {
        border-color: #e0b0aa;
        background: #fff2f1;
        color: var(--error);
      }

      .connecting-view {
        display: none;
        gap: 18px;
      }

      .connecting-view.visible {
        display: grid;
      }

      .connecting-hero {
        display: grid;
        gap: 18px;
        margin-top: 12px;
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: linear-gradient(180deg, #f9fbf8 0%, #f3f8f3 100%);
      }

      .connecting-hero-topline {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .connecting-spinner {
        width: 18px;
        height: 18px;
        border-radius: 999px;
        border: 2px solid rgba(47, 125, 75, 0.18);
        border-top-color: var(--green);
        animation: spin 0.95s linear infinite;
      }

      .connecting-hero strong {
        font-size: 1rem;
      }

      .connecting-hero p {
        margin: 0;
      }

      .connecting-signal {
        display: grid;
        grid-template-columns: 72px 1fr 72px;
        align-items: center;
        gap: 14px;
      }

      .connecting-node {
        display: grid;
        justify-items: center;
        gap: 8px;
      }

      .connecting-node-badge {
        display: grid;
        place-items: center;
        width: 52px;
        height: 52px;
        border: 1px solid #cfe0d2;
        border-radius: 8px;
        background: #ffffff;
        color: var(--green);
        font-size: 1.35rem;
      }

      .connecting-node-label {
        color: var(--muted);
        font-size: 0.9rem;
        font-weight: 700;
      }

      .connecting-wave {
        position: relative;
        height: 12px;
        border-radius: 999px;
        background: #e3ebe3;
        overflow: hidden;
      }

      .connecting-wave::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 -32%;
        width: 32%;
        border-radius: inherit;
        background: linear-gradient(90deg, rgba(47, 125, 75, 0.08), rgba(47, 125, 75, 0.8), rgba(47, 125, 75, 0.08));
        animation: wave 1.8s ease-in-out infinite;
      }

      .connecting-checklist {
        display: grid;
        gap: 12px;
        margin: 0;
        padding: 0;
        list-style: none;
      }

      .connecting-check {
        display: flex;
        align-items: center;
        gap: 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 12px 14px;
        background: #f9fbf8;
      }

      .connecting-check-dot {
        width: 12px;
        height: 12px;
        border-radius: 999px;
        background: #c8d2c8;
      }

      .connecting-check strong {
        display: block;
      }

      .connecting-check span {
        color: var(--muted);
        font-size: 0.95rem;
      }

      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }

      @keyframes wave {
        0% {
          transform: translateX(0);
        }
        100% {
          transform: translateX(430%);
        }
      }

      @media (max-width: 480px) {
        main {
          width: min(100% - 24px, 520px);
          padding: 24px 0;
        }

        .card {
          padding: 18px;
        }

        h1 {
          font-size: 1.8rem;
        }

        .connecting-signal {
          grid-template-columns: 1fr;
          gap: 12px;
        }

        .connecting-wave {
          order: 3;
          height: 10px;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <div class="card">
        <div id="setup-form-view">
          <p class="eyebrow">PlantLab Local Setup</p>
          <h1>PlantLab Setup</h1>
          <p>Connect this device to your home Wi-Fi and add it to your PlantLab account.</p>
          <p>Enter your Wi-Fi details to finish setup.</p>

          <form id="provision-form" novalidate>
            <label>
              Wi-Fi SSID
              <select id="ssid-select" name="ssid_select">
                <option value="">Scanning nearby Wi-Fi...</option>
              </select>
              <input class="manual-ssid" id="ssid" name="ssid" autocomplete="off" placeholder="Type Wi-Fi name">
            </label>

            <label>
              Wi-Fi password
              <div class="password-row">
                <input id="password" name="password" type="password" autocomplete="current-password" placeholder="Leave empty for open Wi-Fi">
                <button class="secondary-button" id="toggle-password" type="button">Show</button>
              </div>
            </label>

            <label id="serial-number-field">
              SN
              <input id="serial-number" name="serial_number" required autocomplete="off" placeholder="123">
            </label>

            <label class="hidden" id="setup-code-field">
              Setup code
              <input id="claim-token" name="claim_token" required autocomplete="one-time-code" placeholder="PL-ABC123XYZ">
            </label>

            <input id="backend-url" name="backend_url" type="hidden" value="{{ backend_url }}">
            <input id="return-url" name="return_url" type="hidden">
            <input id="device-name" name="device_name" type="hidden">
            <input id="location" name="location" type="hidden">

            <button class="submit-button" id="submit-button" type="submit">Save and connect</button>
          </form>

          <div class="status" id="status" role="status" aria-live="polite"></div>
          <p class="hint">After submitting, the device will leave setup mode and try to join your Wi-Fi.</p>
        </div>

        <div class="connecting-view" id="connecting-view" aria-live="polite">
          <p class="eyebrow">Setup</p>
          <h1>Connecting your PlantLab</h1>
          <p>Your device is leaving setup mode, joining your Wi‑Fi, and reopening PlantLab as soon as it is ready.</p>

          <div class="connecting-hero" aria-hidden="true">
            <div class="connecting-hero-topline">
              <span class="connecting-spinner"></span>
              <strong>Reconnecting and syncing</strong>
            </div>
            <div class="connecting-signal">
              <div class="connecting-node">
                <div class="connecting-node-badge">Pi</div>
                <div class="connecting-node-label">Device</div>
              </div>
              <div class="connecting-wave"></div>
              <div class="connecting-node">
                <div class="connecting-node-badge">☁</div>
                <div class="connecting-node-label">PlantLab</div>
              </div>
            </div>
          </div>

          <ul class="connecting-checklist">
            <li class="connecting-check">
              <span class="connecting-check-dot" aria-hidden="true"></span>
              <div>
                <strong>Joining your Wi‑Fi</strong>
                <span>PlantLab is switching from setup mode back to your home network.</span>
              </div>
            </li>
            <li class="connecting-check">
              <span class="connecting-check-dot" aria-hidden="true"></span>
              <div>
                <strong>Reopening your dashboard</strong>
                <span>The next page will open automatically when your browser can reach PlantLab again.</span>
              </div>
            </li>
          </ul>

          <div class="status visible success" id="connecting-status">Setup saved. PlantLab is reconnecting to your Wi‑Fi and will reopen the dashboard when it is ready.</div>
        </div>
      </div>
    </main>

    <script>
      const form = document.querySelector("#provision-form");
      const ssidInput = document.querySelector("#ssid");
      const ssidSelect = document.querySelector("#ssid-select");
      const passwordInput = document.querySelector("#password");
      const serialNumberInput = document.querySelector("#serial-number");
      const serialNumberField = document.querySelector("#serial-number-field");
      const claimTokenInput = document.querySelector("#claim-token");
      const backendUrlInput = document.querySelector("#backend-url");
      const setupCodeField = document.querySelector("#setup-code-field");
      const returnUrlInput = document.querySelector("#return-url");
      const deviceNameInput = document.querySelector("#device-name");
      const locationInput = document.querySelector("#location");
      const togglePasswordButton = document.querySelector("#toggle-password");
      const submitButton = document.querySelector("#submit-button");
      const statusBox = document.querySelector("#status");
      const setupFormView = document.querySelector("#setup-form-view");
      const connectingView = document.querySelector("#connecting-view");
      const connectingStatus = document.querySelector("#connecting-status");

      function setStatus(message, type = "info") {
        statusBox.textContent = message;
        statusBox.className = `status visible ${type}`;
      }

      function clearStatus() {
        statusBox.textContent = "";
        statusBox.className = "status";
      }

      function showConnectingView(message) {
        setupFormView.hidden = true;
        connectingView.classList.add("visible");
        connectingStatus.textContent = message;
      }

      function validateForm() {
        const ssid = selectedSsid();
        const serialNumber = serialNumberInput.value.trim();
        const claimToken = claimTokenInput.value.trim();
        const backendUrl = backendUrlInput.value.trim();

        if (!ssid) {
          return "Enter your home Wi-Fi name.";
        }
        if (!serialNumber && !claimToken) {
          return "Enter the device SN.";
        }
        if (!backendUrl) {
          return "Setup service is not configured. Restart setup and try again.";
        }
        try {
          new URL(backendUrl);
        } catch (_error) {
          return "Setup service is not configured correctly.";
        }
        return "";
      }

      function selectedSsid() {
        return ssidSelect.value === "__manual__" ? ssidInput.value.trim() : ssidSelect.value.trim();
      }

      function applySetupCodeFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const setupCode = params.get("setup_code");
        const serialNumber = params.get("sn");
        const returnUrl = params.get("return_url");
        const deviceName = params.get("device_name");
        const location = params.get("location");

        if (setupCode) {
          claimTokenInput.value = setupCode.trim();
          setupCodeField.classList.add("hidden");
          serialNumberField.classList.add("hidden");
          serialNumberInput.required = false;
          setStatus("Device authorization received. Enter your home Wi-Fi details.", "success");
        }
        if (serialNumber) {
          serialNumberInput.value = serialNumber.trim();
        }
        if (returnUrl) {
          returnUrlInput.value = returnUrl.trim();
        }
        if (deviceName) {
          deviceNameInput.value = deviceName.trim();
        }
        if (location) {
          locationInput.value = location.trim();
        }

        const cleanUrl = `${window.location.origin}${window.location.pathname}`;
        window.history.replaceState({}, document.title, cleanUrl);
      }

      function setSsidOptions(networks) {
        ssidSelect.innerHTML = "";
        const setupSsids = new Set(["PlantLab-Setup", "Hotspot"]);
        const homeNetworks = networks.filter((network) => !setupSsids.has(network.ssid));
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = homeNetworks.length ? "Select nearby Wi-Fi" : "Type your home Wi-Fi below";
        ssidSelect.appendChild(placeholder);

        homeNetworks.forEach((network) => {
          const option = document.createElement("option");
          option.value = network.ssid;
          const signal = Number.isInteger(network.signal) ? ` (${network.signal}%)` : "";
          option.textContent = `${network.ssid}${signal}`;
          ssidSelect.appendChild(option);
        });

        const manualOption = document.createElement("option");
        manualOption.value = "__manual__";
        manualOption.textContent = "My Wi-Fi is not listed";
        ssidSelect.appendChild(manualOption);

        ssidInput.classList.toggle("visible", homeNetworks.length === 0);
        if (homeNetworks.length === 0) {
          ssidSelect.value = "__manual__";
        }
      }

      async function loadNetworks() {
        try {
          const response = await fetch("/wifi/networks", {
            headers: {
              Accept: "application/json"
            }
          });
          const data = await response.json();
          if (!response.ok || !data.ok) {
            throw new Error(data.message || "Wi-Fi scan failed.");
          }
          setSsidOptions(data.networks || []);
        } catch (error) {
          setSsidOptions([]);
          setStatus("Could not scan Wi-Fi. Type your Wi-Fi name manually.", "error");
        }
      }

      ssidSelect.addEventListener("change", () => {
        const manualSelected = ssidSelect.value === "__manual__";
        ssidInput.classList.toggle("visible", manualSelected);
        if (!manualSelected) {
          ssidInput.value = "";
        }
      });

      togglePasswordButton.addEventListener("click", () => {
        const isHidden = passwordInput.type === "password";
        passwordInput.type = isHidden ? "text" : "password";
        togglePasswordButton.textContent = isHidden ? "Hide" : "Show";
      });

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearStatus();

        const validationError = validateForm();
        if (validationError) {
          setStatus(validationError, "error");
          return;
        }

        const payload = {
          ssid: selectedSsid(),
          password: passwordInput.value,
          serial_number: serialNumberInput.value.trim(),
          claim_token: claimTokenInput.value.trim(),
          backend_url: backendUrlInput.value.trim(),
          return_url: returnUrlInput.value.trim(),
          device_name: deviceNameInput.value.trim(),
          location: locationInput.value.trim()
        };

        submitButton.disabled = true;
        setStatus("Saving setup details...", "info");

        try {
          const response = await fetch("/provision", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Accept: "application/json"
            },
            body: JSON.stringify(payload)
          });
          const data = await response.json();

          if (!response.ok || !data.ok) {
            throw new Error(data.message || "Could not save setup details.");
          }

          const connectingMessage = "Setup saved. PlantLab is reconnecting to your Wi-Fi and will reopen the dashboard when it is ready.";
          setStatus(connectingMessage, "success");
          showConnectingView(connectingMessage);
          form.reset();
          if (data.redirect_url) {
            await redirectWhenReachable(data.redirect_url);
          }
        } catch (error) {
          submitButton.disabled = false;
          setupFormView.hidden = false;
          connectingView.classList.remove("visible");
          setStatus(error.message || "Something went wrong. Please try again.", "error");
        }
      });

      async function canReachReturnPage(url) {
        try {
          await fetch(url, {
            method: "GET",
            mode: "no-cors",
            cache: "no-store",
          });
          return true;
        } catch (_error) {
          return false;
        }
      }

      async function redirectWhenReachable(url) {
        const maxAttempts = 12;
        for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
          if (await canReachReturnPage(url)) {
            window.location.replace(url);
            return;
          }
          await new Promise((resolve) => window.setTimeout(resolve, 1500));
        }
        window.location.replace(url);
      }

      applySetupCodeFromUrl();
      loadNetworks();
    </script>
  </body>
</html>
"""


@dataclass
class ProvisioningPayload:
    ssid: str
    password: str
    claim_token: str
    backend_url: str
    serial_number: str = ""
    return_url: str = ""
    device_name: str = ""
    location: str = ""


class LocalSetupServer:
    def __init__(self, host: str, port: int, backend_url: str, network_manager: NetworkManager):
        self.host = host
        self.port = port
        self.backend_url = backend_url
        self.network_manager = network_manager
        self.app = Flask(__name__)
        self.payload: ProvisioningPayload | None = None
        self.payload_received = threading.Event()
        self._server = None
        self._thread: threading.Thread | None = None
        self._configure_routes()

    def _configure_routes(self) -> None:
        @self.app.get("/")
        def index():
            return render_template_string(SETUP_TEMPLATE, backend_url=self.backend_url)

        @self.app.get("/health")
        def health():
            return jsonify({"ok": True, "service": "plantlab-local-setup"})

        @self.app.get("/wifi/networks")
        def wifi_networks():
            status = self.network_manager.scan_wifi_networks()
            if not status.ok:
                return jsonify(
                    {
                        "ok": False,
                        "error": "wifi_scan_failed",
                        "message": status.message,
                        "networks": [],
                    }
                ), 503
            return jsonify(
                {
                    "ok": True,
                    "message": status.message,
                    "networks": status.details.get("networks", []),
                }
            )

        @self.app.post("/provision")
        def provision():
            data = request.get_json(silent=True) or {}
            ssid = str(data.get("ssid", "")).strip()
            password = str(data.get("password", ""))
            serial_number = str(data.get("serial_number", "")).strip()
            claim_token = str(data.get("claim_token", "")).strip()
            backend_url = str(data.get("backend_url", "")).strip()
            return_url = unquote(str(data.get("return_url", "")).strip())
            device_name = str(data.get("device_name", "")).strip()
            location = str(data.get("location", "")).strip()
            if not ssid or not backend_url or (not claim_token and not serial_number):
                return jsonify(
                    {
                        "ok": False,
                        "error": "validation_error",
                        "message": "Wi-Fi SSID, SN, and setup service are required.",
                    }
                ), 400

            self.payload = ProvisioningPayload(
                ssid=ssid,
                password=password,
                claim_token=claim_token,
                backend_url=backend_url,
                serial_number=serial_number,
                return_url=return_url,
                device_name=device_name,
                location=location,
            )
            self.payload_received.set()
            threading.Thread(target=self.shutdown, daemon=True).start()
            return jsonify(
                {
                    "ok": True,
                    "message": "Provisioning details received. Device is connecting to Wi-Fi.",
                    "redirect_url": return_url,
                }
            )

    def start(self) -> None:
        logger.info("starting local setup server on %s:%s", self.host, self.port)
        self._server = make_server(self.host, self.port, self.app)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def wait_for_payload(self) -> ProvisioningPayload:
        self.payload_received.wait()
        if self.payload is None:
            raise RuntimeError("provisioning payload was not captured")
        return self.payload

    def shutdown(self) -> None:
        if self._server is not None:
            logger.info("stopping local setup server")
            self._server.shutdown()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)
