import { useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useDevices } from "@/hooks/useDevices";

export function DeviceListScreen() {
  const location = useLocation();
  const navigate = useNavigate();
  const { devices, usedMock, isLoading, error, refresh, lastUpdatedAt } = useDevices();
  const flashState = location.state && typeof location.state === "object" ? (location.state as { flashMessage?: string; flashTone?: "success" | "info" }) : null;

  useEffect(() => {
    if (!flashState?.flashMessage) {
      return;
    }
    navigate(location.pathname, { replace: true });
  }, [flashState?.flashMessage, location.pathname, navigate]);

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">PLANTLAB</div>
          <h2>Devices</h2>
          <p className="subtitle">
            {usedMock
              ? "Showing bundled mock devices because the backend is unavailable."
              : "Showing devices from your local PlantLab backend."}
          </p>
          <p className="meta-text">
            {lastUpdatedAt ? `Last updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Waiting for first refresh."}
          </p>
        </div>
        <div className="header-actions">
          <Link className="primary-button" to="/devices/add">
            Add device
          </Link>
          <button className="secondary-button" disabled={isLoading} onClick={() => void refresh()}>
            {isLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {usedMock ? <p className="chip chip-mock">Mock data mode</p> : null}
      {flashState?.flashMessage ? (
        <p className={`status-banner ${flashState.flashTone === "info" ? "status-banner-info" : "status-banner-success"}`}>
          {flashState.flashMessage}
        </p>
      ) : null}
      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {isLoading && devices.length === 0 ? <p className="status-banner">Loading your devices…</p> : null}
      {!isLoading && !error && devices.length === 0 ? (
        <div className="empty-state">
          <h3>No devices yet</h3>
          <p className="subtitle">Start onboarding here, then come back to monitor the device once setup finishes.</p>
          <Link className="text-link" to="/devices/add">
            Open add-device flow
          </Link>
        </div>
      ) : null}

      <div className="card-grid">
        {devices.map((device) => (
          <Link className="device-card" key={device.id} to={`/devices/${device.id}`}>
            <div className="device-card-header">
              <div>
                <h3>{device.name}</h3>
                <p>{device.location ?? "No location set"}</p>
              </div>
              <span className={`chip chip-${device.status}`}>{device.status}</span>
            </div>
            <p className="meta-text">
              {device.latestReading
                ? `Reading from ${new Date(device.latestReading.timestamp).toLocaleString()}`
                : "No reading received yet."}
            </p>
            <p className="metric-summary">
              {device.latestReading
                ? `Air ${device.latestReading.temperatureC?.toFixed(1) ?? "--"} C • Water ${device.latestReading.waterTemperatureC?.toFixed(1) ?? "--"} C • Level ${device.latestReading.waterLevelState ?? "--"}`
                : "Latest sensor summary unavailable."}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
