import { Link } from "react-router-dom";

import { useDevices } from "@/hooks/useDevices";

export function DeviceListScreen() {
  const { devices, usedMock, isLoading, error, refresh } = useDevices();

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">PLANTLAB</div>
          <h2>Devices</h2>
          <p className="subtitle">Standalone web scaffold using backend APIs when available and mock fallback when not.</p>
        </div>
        <button className="secondary-button" onClick={refresh}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {usedMock ? <p className="chip chip-mock">Mock data mode</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

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
