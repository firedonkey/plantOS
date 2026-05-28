import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { HardwareHealthPanel } from "@/components/HardwareHealthPanel";
import { getDeviceSettingsDetails, updateDeviceSettings } from "@/api/devices";
import type { DeviceSettingsDetails } from "@/api/devices";
import { useSession } from "@/hooks/useSession";

export function DeviceSettingsScreen() {
  const { deviceId = "" } = useParams();
  const { token } = useSession();
  const [details, setDetails] = useState<DeviceSettingsDetails | null>(null);
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [name, setName] = useState("");

  useEffect(() => {
    if (!deviceId) {
      return;
    }
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const result = await getDeviceSettingsDetails(deviceId, token ?? undefined);
        if (cancelled) {
          return;
        }
        setDetails(result.details);
        setUsedMock(result.usedMock);
        setName(result.details.device.name);
      } catch (err) {
        if (!cancelled) {
          setUsedMock(false);
          setError(err instanceof Error ? err.message : "Unable to load device settings.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [deviceId, token]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!deviceId) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      const result = await updateDeviceSettings(
        deviceId,
        {
          name,
        },
        token ?? undefined,
      );
      setDetails(result.details);
      setUsedMock(result.usedMock);
      setMessage(result.usedMock ? "Mock mode preview updated locally." : "Device settings saved.");
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to save device settings.");
    } finally {
      setIsSaving(false);
    }
  };

  if (!deviceId) {
    return <p className="error-text">Missing device id.</p>;
  }

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">DEVICE SETTINGS</div>
          <h2>{details?.device.name ?? "Device settings"}</h2>
          <p className="subtitle">Edit the device name and review the identifiers and provisioning state used by the real hardware loop.</p>
        </div>
        <div className="header-actions">
          {usedMock ? <span className="chip chip-mock">Mock mode</span> : null}
          <Link className="secondary-button" to={`/devices/${deviceId}`}>
            Back to dashboard
          </Link>
        </div>
      </div>

      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {message ? <p className="status-banner status-banner-success">{message}</p> : null}

      <form className="card stack-form" onSubmit={onSubmit}>
        <h3>Edit labels</h3>
        <label className="field">
          <span>Device name</span>
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <div className="button-row">
          <button className="primary-button" type="submit" disabled={isSaving || isLoading}>
            {isSaving ? "Saving..." : "Save changes"}
          </button>
        </div>
      </form>

      <div className="card stack-form">
        <h3>Operational details</h3>
        {isLoading && !details ? <p className="subtitle">Loading device details…</p> : null}
        {details ? (
          <>
            <div className="detail-grid">
              <div className="detail-row">
                <strong>Provision status</strong>
                <span>{details.onboardingStatus}</span>
              </div>
              <div className="detail-row">
                <strong>Device token</strong>
                <span className="token-summary">{details.maskedToken}</span>
              </div>
              <div className="detail-row">
                <strong>Connection state</strong>
                <span>{details.device.status}</span>
              </div>
              <div className="detail-row">
                <strong>Last heartbeat</strong>
                <span>{details.device.lastSeenAt ? new Date(details.device.lastSeenAt).toLocaleString() : "Waiting for first heartbeat"}</span>
              </div>
            </div>

            <div className="stack-form">
              <strong>Hardware identifiers</strong>
              {details.hardwareIdentifiers.length ? (
                details.hardwareIdentifiers.map((item) => (
                  <div className="detail-row" key={`${item.label}-${item.value}`}>
                    <strong>{item.label}</strong>
                    <span className="token-summary">{item.value}</span>
                  </div>
                ))
              ) : (
                <p className="subtitle">Hardware identifiers will appear after the backend receives node registration details.</p>
              )}
            </div>
          </>
        ) : null}
      </div>

      <HardwareHealthPanel health={details?.hardwareHealth} />

      <div className="card stack-form">
        <h3>Recovery guidance</h3>
        <p className="subtitle">{details?.onboardingGuidance ?? "Use this page to keep the operational labels in sync with the real device."}</p>
        <ul className="setup-checklist">
          <li>For a clean re-provision, use the hardware button flow and watch the serial monitor rather than changing values here.</li>
          <li>If the device stops reporting, confirm power, Wi-Fi, and the current device token before deleting or re-adding it.</li>
          <li>No remote reboot or re-provision action is wired in yet, by design.</li>
        </ul>
      </div>
    </section>
  );
}
