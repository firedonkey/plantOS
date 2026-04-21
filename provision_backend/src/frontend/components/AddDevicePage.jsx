import { useCallback, useEffect, useRef, useState } from "react";

import {
  copyTextToClipboard,
  formatExpiry,
  requestDeviceClaimToken
} from "../lib/deviceClaimApi.js";
import "../styles/add-device.css";

const ONBOARDING_STEPS = [
  "Power on the PlantLab device.",
  "Connect your phone or laptop to the PlantLab-XXXX Wi-Fi network.",
  "Open http://192.168.4.1 in your browser.",
  "Enter your home Wi-Fi name and password.",
  "Paste this claim token on the device setup page."
];

export default function AddDevicePage() {
  const [claimToken, setClaimToken] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const [copied, setCopied] = useState(false);
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
    setCopied(false);

    try {
      const result = await requestDeviceClaimToken({
        signal: abortController.signal
      });
      setClaimToken(result.claimToken);
      setExpiresAt(result.expiresAt);
      setStatus("success");
      setMessage("Claim token ready. Use it before it expires.");
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }
      setStatus("error");
      setMessage(error.message || "Could not create a claim token.");
    }
  }, []);

  const handleCopyToken = useCallback(async () => {
    try {
      const didCopy = await copyTextToClipboard(claimToken);
      setCopied(didCopy);
      setMessage(didCopy ? "Claim token copied." : "Could not copy the token.");
    } catch (_error) {
      setCopied(false);
      setMessage("Could not copy the token.");
    }
  }, [claimToken]);

  const isLoading = status === "loading";
  const hasToken = Boolean(claimToken);
  const expiryLabel = formatExpiry(expiresAt);

  return (
    <main className="add-device-page">
      <section className="add-device-hero" aria-labelledby="add-device-title">
        <p className="add-device-eyebrow">PlantLab Setup</p>
        <h1 id="add-device-title">Add a new device</h1>
        <p>
          Generate a one-time claim token, then paste it into the local setup
          page on your PlantLab device.
        </p>
      </section>

      <section className="add-device-layout">
        <div className="claim-card" aria-live="polite">
          <div className="claim-card-header">
            <div>
              <p className="add-device-eyebrow">Step 1</p>
              <h2>Generate claim token</h2>
            </div>
            {status === "success" && <span className="status-pill">Ready</span>}
            {status === "error" && <span className="status-pill error">Error</span>}
          </div>

          <p className="claim-copy">
            Claim tokens are short-lived and can only be used once. The device
            will exchange this token for its own long-term device access token.
          </p>

          <button
            className="primary-action"
            type="button"
            onClick={handleRequestToken}
            disabled={isLoading}
          >
            {isLoading ? "Creating token..." : hasToken ? "Create new token" : "Request claim token"}
          </button>

          {hasToken && (
            <div className="token-panel">
              <span className="token-label">Claim token</span>
              <code>{claimToken}</code>
              <button type="button" onClick={handleCopyToken}>
                {copied ? "Copied" : "Copy token"}
              </button>
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
            <code>http://192.168.4.1</code>
          </div>
        </div>
      </section>
    </main>
  );
}
