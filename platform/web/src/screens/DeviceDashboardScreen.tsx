import { Link, useParams } from "react-router-dom";

import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";

export function DeviceDashboardScreen() {
  const { deviceId = "" } = useParams();
  const { dashboard, usedMock, isLoading, error, commandMessage, refresh, runCommand } = useDeviceDashboard(deviceId);

  if (!deviceId) {
    return <p className="error-text">Missing device id.</p>;
  }

  return (
    <section className="page-section">
      {dashboard ? (
        <>
          <div className="page-header">
            <div>
              <div className="eyebrow">DEVICE DASHBOARD</div>
              <h2>{dashboard.device.name}</h2>
              <p className="subtitle">
                {dashboard.device.plantType ?? "Plant type not set"} • {dashboard.device.location ?? "No location set"}
              </p>
            </div>
            <div className="header-actions">
              {usedMock ? <span className="chip chip-mock">Mock mode</span> : null}
              <button className="secondary-button" onClick={refresh}>
                {isLoading ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </div>

          {error ? <p className="error-text">{error}</p> : null}
          {commandMessage ? <p className="success-text">{commandMessage}</p> : null}

          <div className="metrics-grid">
            <div className="metric-card"><span>Temperature</span><strong>{dashboard.device.latestReading?.temperatureC?.toFixed(1) ?? "--"} C</strong></div>
            <div className="metric-card"><span>Humidity</span><strong>{dashboard.device.latestReading?.humidityPercent?.toFixed(1) ?? "--"}%</strong></div>
            <div className="metric-card"><span>Soil Moisture</span><strong>{dashboard.device.latestReading?.soilMoisturePercent?.toFixed(1) ?? "--"}%</strong></div>
            <div className="metric-card"><span>Water Level</span><strong>{dashboard.device.latestReading?.waterLevelPercent?.toFixed(0) ?? "--"}%</strong></div>
            <div className="metric-card"><span>Light</span><strong>{dashboard.device.latestReading?.lightOn ? "On" : "Off"}</strong></div>
            <div className="metric-card"><span>Pump</span><strong>{dashboard.device.latestReading?.pumpOn ? "On" : "Off"}</strong></div>
          </div>

          <div className="card">
            <h3>Latest capture</h3>
            {dashboard.device.latestImage ? (
              <>
                <img alt="Latest device capture" className="capture-image" src={dashboard.device.latestImage.url} />
                <p className="subtitle">Captured {new Date(dashboard.device.latestImage.capturedAt).toLocaleString()}</p>
              </>
            ) : (
              <p className="subtitle">No image available yet.</p>
            )}
          </div>

          <div className="card">
            <h3>Manual controls</h3>
            <div className="button-row">
              <button className="primary-button" onClick={() => runCommand("light_on")}>Light on</button>
              <button className="primary-button" onClick={() => runCommand("light_off")}>Light off</button>
              <button className="primary-button" onClick={() => runCommand("pump_run")}>Pump run</button>
              <button className="primary-button" onClick={() => runCommand("capture_image")}>Capture image</button>
            </div>
          </div>

          <Link className="text-link" to={`/devices/${deviceId}/history`}>
            View history
          </Link>
        </>
      ) : (
        <p className="subtitle">Loading dashboard...</p>
      )}
    </section>
  );
}
