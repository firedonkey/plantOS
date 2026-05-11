import { useParams } from "react-router-dom";

import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";

export function HistoryScreen() {
  const { deviceId = "" } = useParams();
  const { dashboard, usedMock, isLoading, error, refresh } = useDeviceDashboard(deviceId);

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">HISTORY</div>
          <h2>Recent sensor history</h2>
          <p className="subtitle">
            {usedMock ? "Mock history data shown because the backend is unavailable." : "Backend history data loaded from the standalone API."}
          </p>
        </div>
        <button className="secondary-button" onClick={refresh}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      <div className="history-list">
        {dashboard?.history.map((reading) => (
          <div className="card" key={reading.timestamp}>
            <strong>{new Date(reading.timestamp).toLocaleString()}</strong>
            <p className="subtitle">
              {reading.temperatureC?.toFixed(1) ?? "--"} C • {reading.humidityPercent?.toFixed(1) ?? "--"}% • {reading.soilMoisturePercent?.toFixed(1) ?? "--"}%
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
