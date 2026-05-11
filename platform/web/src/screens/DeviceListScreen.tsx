import { Link } from "react-router-dom";

import { useDevices } from "@/hooks/useDevices";

export function DeviceListScreen() {
  const { devices, usedMock, isLoading, error, refresh, lastUpdatedAt } = useDevices();

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
        <button className="secondary-button" disabled={isLoading} onClick={refresh}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {usedMock ? <p className="chip chip-mock">Mock data mode</p> : null}
      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {isLoading && devices.length === 0 ? <p className="status-banner">Loading your devices…</p> : null}
      {!isLoading && devices.length === 0 ? (
        <div className="empty-state">
          <h3>No devices yet</h3>
          <p className="subtitle">Add a PlantLab from the existing backend-rendered flow, then come back here to monitor it.</p>
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
                ? `${device.latestReading.temperatureC?.toFixed(1) ?? "--"} C • ${device.latestReading.humidityPercent?.toFixed(1) ?? "--"}% • ${device.latestReading.soilMoisturePercent?.toFixed(1) ?? "--"}%`
                : "Latest sensor summary unavailable."}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
