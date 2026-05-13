import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { requestDeviceSetupCode } from "@/api/devices";
import { useSession } from "@/hooks/useSession";

export function AddDeviceScreen() {
  const { token } = useSession();
  const [deviceName, setDeviceName] = useState("");
  const [location, setLocation] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usedMock, setUsedMock] = useState(false);
  const [handoff, setHandoff] = useState<{
    serialNumber: string;
    setupToken?: string;
    continueSetupUrl: string;
    setupFinishingUrl: string;
  } | null>(null);

  const setupFinishingPath = useMemo(() => {
    if (!handoff) {
      return null;
    }
    try {
      const url = new URL(handoff.setupFinishingUrl, window.location.origin);
      return `${url.pathname}${url.search}`;
    } catch {
      return handoff.setupFinishingUrl;
    }
  }, [handoff]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await requestDeviceSetupCode(
        {
          serialNumber,
          deviceName,
          location: location || undefined,
        },
        token ?? undefined,
      );
      setUsedMock(result.usedMock);
      setHandoff(result.handoff);
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to start device setup.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">DEVICE ONBOARDING</div>
          <h2>Add device</h2>
          <p className="subtitle">This standalone flow uses backend APIs directly. Dev-only auth still applies in the standalone app.</p>
        </div>
      </div>

      {usedMock ? <p className="chip chip-mock">Mock data mode</p> : null}
      {error ? <p className="status-banner status-banner-error">{error}</p> : null}

      <form className="card stack-form" onSubmit={onSubmit}>
        <label className="field">
          <span>Device name</span>
          <input value={deviceName} onChange={(event) => setDeviceName(event.target.value)} placeholder="Device 1" required />
        </label>
        <label className="field">
          <span>Location</span>
          <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Kitchen" />
        </label>
        <label className="field">
          <span>Serial number</span>
          <input value={serialNumber} onChange={(event) => setSerialNumber(event.target.value)} placeholder="SN-ESP32-001" required />
        </label>
        <div className="button-row">
          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Verifying..." : "Verify serial and continue"}
          </button>
          <Link className="secondary-button" to="/devices">
            Back to devices
          </Link>
        </div>
      </form>

      {handoff ? (
        <div className="card stack-form">
          <h3>Next steps</h3>
          <p className="subtitle">
            We verified <strong>{handoff.serialNumber}</strong>. Open the device Wi-Fi setup page, finish Wi-Fi provisioning, then keep the setup-finishing page open until the first reading is ready.
          </p>
          <ol className="setup-checklist">
            <li>Connect your laptop or phone to <strong>PlantLab-Setup</strong>.</li>
            <li>Wait for the network switch to settle. On macOS, the setup page often takes 20-30 seconds to become reachable after joining the access point.</li>
            <li>Open the device Wi-Fi setup page and submit your home Wi-Fi name and password.</li>
            <li>Come back to the setup-finishing page and leave it open until the first reading arrives.</li>
          </ol>
          {handoff.setupToken ? <p className="meta-text">Setup token: {handoff.setupToken}</p> : null}
          <div className="button-row">
            <a className="primary-button" href={handoff.continueSetupUrl} rel="noreferrer" target="_blank">
              Open device Wi-Fi setup
            </a>
            {setupFinishingPath ? (
              <Link className="secondary-button" to={setupFinishingPath}>
                Open setup finishing
              </Link>
            ) : null}
          </div>
          <p className="meta-text">
            If the backend is unavailable, mock mode can still preview this flow, but it does not provision a real device.
          </p>
          <div className="onboarding-help">
            <strong>Troubleshooting</strong>
            <ul>
              <li>If the setup page does not open immediately, stay connected to <strong>PlantLab-Setup</strong> and try again after 20-30 seconds.</li>
              <li>If your browser complains about no internet, ignore that warning and open the setup page again.</li>
              <li>If the setup form loads but the device never appears, leave the setup-finishing page open and check the ESP32 serial monitor for registration logs.</li>
            </ul>
          </div>
        </div>
      ) : null}
    </section>
  );
}
