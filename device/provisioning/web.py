import logging
import threading
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
      }
    </style>
  </head>
  <body>
    <main>
      <div class="card">
        <p class="eyebrow">PlantLab Local Setup</p>
        <h1>PlantLab Setup</h1>
        <p>Connect this device to your home Wi-Fi and claim it to your PlantLab account.</p>
        <p>Get a claim token from the PlantLab website by opening Add Device, then paste it below.</p>

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

          <label>
            Claim token
            <input id="claim-token" name="claim_token" required autocomplete="off" placeholder="PL-ABC123XYZ">
          </label>

          <label>
            Backend URL
            <input id="backend-url" name="backend_url" required autocomplete="off" value="{{ backend_url }}">
          </label>

          <button class="submit-button" id="submit-button" type="submit">Save and connect</button>
        </form>

        <div class="status" id="status" role="status" aria-live="polite"></div>
        <p class="hint">After submitting, the device will leave setup mode and try to join your Wi-Fi.</p>
      </div>
    </main>

    <script>
      const form = document.querySelector("#provision-form");
      const ssidInput = document.querySelector("#ssid");
      const ssidSelect = document.querySelector("#ssid-select");
      const passwordInput = document.querySelector("#password");
      const claimTokenInput = document.querySelector("#claim-token");
      const backendUrlInput = document.querySelector("#backend-url");
      const togglePasswordButton = document.querySelector("#toggle-password");
      const submitButton = document.querySelector("#submit-button");
      const statusBox = document.querySelector("#status");

      function setStatus(message, type = "info") {
        statusBox.textContent = message;
        statusBox.className = `status visible ${type}`;
      }

      function clearStatus() {
        statusBox.textContent = "";
        statusBox.className = "status";
      }

      function validateForm() {
        const ssid = selectedSsid();
        const claimToken = claimTokenInput.value.trim();
        const backendUrl = backendUrlInput.value.trim();

        if (!ssid) {
          return "Enter your home Wi-Fi name.";
        }
        if (!claimToken) {
          return "Paste the claim token from the PlantLab website.";
        }
        if (!backendUrl) {
          return "Backend URL is required.";
        }
        try {
          new URL(backendUrl);
        } catch (_error) {
          return "Backend URL must look like https://marspotatolab.com.";
        }
        return "";
      }

      function selectedSsid() {
        return ssidSelect.value === "__manual__" ? ssidInput.value.trim() : ssidSelect.value.trim();
      }

      function setSsidOptions(networks) {
        ssidSelect.innerHTML = "";
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = networks.length ? "Select nearby Wi-Fi" : "No networks found";
        ssidSelect.appendChild(placeholder);

        networks.forEach((network) => {
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

        ssidInput.classList.toggle("visible", networks.length === 0);
        if (networks.length === 0) {
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
          claim_token: claimTokenInput.value.trim(),
          backend_url: backendUrlInput.value.trim()
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

          setStatus("Setup saved. PlantLab is connecting to your Wi-Fi now.", "success");
          form.reset();
        } catch (error) {
          submitButton.disabled = false;
          setStatus(error.message || "Something went wrong. Please try again.", "error");
        }
      });

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
            claim_token = str(data.get("claim_token", "")).strip()
            backend_url = str(data.get("backend_url", "")).strip()
            if not ssid or not claim_token or not backend_url:
                return jsonify(
                    {
                        "ok": False,
                        "error": "validation_error",
                        "message": "Wi-Fi SSID, claim token, and backend URL are required.",
                    }
                ), 400

            self.payload = ProvisioningPayload(
                ssid=ssid,
                password=password,
                claim_token=claim_token,
                backend_url=backend_url,
            )
            self.payload_received.set()
            threading.Thread(target=self.shutdown, daemon=True).start()
            return jsonify(
                {
                    "ok": True,
                    "message": "Provisioning details received. Device is connecting to Wi-Fi.",
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
