import { useCallback, useEffect, useRef, useState } from "react";

import {
  formatExpiry,
  requestDeviceClaimToken
} from "../lib/deviceClaimApi.js";
import "../styles/add-device.css";

const ONBOARDING_STEPS = [
  "Power on the PlantLab device.",
  "Connect your phone or laptop to the PlantLab-Setup Wi-Fi network.",
  "Tap Continue setup to open the local device page.",
  "Enter your home Wi-Fi name and password.",
  "PlantLab sends the device authorization automatically."
];

export default function AddDevicePage() {
  const [serialNumber, setSerialNumber] = useState("123");
  const [claimToken, setClaimToken] = useState("");
  const [setupUrl, setSetupUrl] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const abortControllerRef = useRef(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleRequestToken = useCallback(async () => {
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setStatus("loading");
    setMessage("");
    setClaimToken("");
    setSetupUrl("");

    const normalizedSerialNumber = serialNumber.trim();
    if (!normalizedSerialNumber) {
      setStatus("error");
      setMessage("Enter the serial number from the device label.");
      return;
    }

    try {
      const result = await requestDeviceClaimToken({
        serialNumber: normalizedSerialNumber,
        signal: abortController.signal
      });
      setClaimToken(result.setupCode);
      setSetupUrl(result.setupUrl || "");
      setExpiresAt(result.expiresAt);
      setStatus("success");
      setMessage("SN verified. Connect to PlantLab-Setup, then continue setup.");
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }
      setStatus("error");
      setMessage(error.message || "Could not verify this SN.");
    }
  }, [serialNumber]);

  const isLoading = status === "loading";
  const hasToken = Boolean(claimToken);
  const expiryLabel = formatExpiry(expiresAt);

  return (
    <main className="add-device-page">
      <section className="add-device-hero" aria-labelledby="add-device-title">
        <p className="add-device-eyebrow">PlantLab Setup</p>
        <h1 id="add-device-title">Add a new device</h1>
        <p>
          Enter the device SN, connect to the device Wi-Fi, then continue to
          the local setup page.
        </p>
      </section>

      <section className="add-device-layout">
        <div className="claim-card" aria-live="polite">
          <div className="claim-card-header">
            <div>
              <p className="add-device-eyebrow">Step 1</p>
              <h2>Verify device SN</h2>
            </div>
            {status === "success" && <span className="status-pill">Ready</span>}
            {status === "error" && <span className="status-pill error">Error</span>}
          </div>

          <p className="claim-copy">
            Enter the SN from the device label or QR code. For this test build,
            use SN 123.
          </p>

          <label className="serial-number-field">
            SN
            <input
              value={serialNumber}
              onChange={(event) => setSerialNumber(event.target.value)}
              placeholder="123"
              autoComplete="off"
            />
          </label>

          <p className="claim-copy">
            PlantLab will verify this SN and prepare the device authorization
            behind the scenes.
          </p>

          <button
            className="primary-action"
            type="button"
            onClick={handleRequestToken}
            disabled={isLoading}
          >
            {isLoading ? "Verifying SN..." : hasToken ? "Verify another SN" : "Verify SN"}
          </button>

          {hasToken && (
            <div className="token-panel">
              <span className="token-label">SN verified</span>
              {setupUrl && (
                <a className="continue-setup-link" href={setupUrl}>
                  Continue setup
                </a>
              )}
              {expiryLabel && <p>Expires around {expiryLabel}.</p>}
            </div>
          )}

          {message && (
            <p className={`state-message ${status === "error" ? "error" : ""}`}>
              {message}
            </p>
          )}
        </div>

        <div className="instructions-card">
          <p className="add-device-eyebrow">Step 2</p>
          <h2>Provision the device</h2>
          <ol className="onboarding-steps">
            {ONBOARDING_STEPS.map((step, index) => (
              <li key={step}>
                <span>{index + 1}</span>
                <p>{step}</p>
              </li>
            ))}
          </ol>
          <div className="setup-note">
            <strong>Local setup address</strong>
            <code>http://10.42.0.1:8080</code>
          </div>
        </div>
      </section>
    </main>
  );
}
