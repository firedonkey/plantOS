import { useParams } from "react-router-dom";

import { ReadingTrendSection } from "@/components/ReadingTrendSection";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";

export function HistoryScreen() {
  const { deviceId = "" } = useParams();
  const { dashboard, usedMock, isLoading, error, refresh, lastUpdatedAt, selectedRange, setSelectedRange } = useDeviceDashboard(deviceId);
  const displayHistory = dashboard?.history ? [...dashboard.history].reverse() : [];

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">HISTORY</div>
          <h2>Recent sensor history</h2>
          <p className="subtitle">
            {usedMock ? "Mock history data shown because the backend is unavailable." : "Backend history data loaded from the standalone API."}
          </p>
          <p className="meta-text">
            {lastUpdatedAt ? `Last updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Waiting for first refresh."}
          </p>
        </div>
        <button className="secondary-button" disabled={isLoading} onClick={() => void refresh()}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {isLoading && !dashboard ? <p className="status-banner">Loading readings…</p> : null}
      {!isLoading && !dashboard?.history.length ? (
        <div className="empty-state">
          <h3>No readings yet</h3>
          <p className="subtitle">Once the device reports sensor data, the recent history will appear here.</p>
        </div>
      ) : null}

      {dashboard?.history.length ? (
        <ReadingTrendSection
          history={dashboard.history}
          title="Trend charts"
          subtitle="Range tabs now request matching backend history windows when the API is available."
          selectedRange={selectedRange}
          onRangeChange={setSelectedRange}
          loading={isLoading}
        />
      ) : null}

      <div className="history-list">
        {displayHistory.map((reading) => (
          <div className="card" key={reading.timestamp}>
            <strong>{new Date(reading.timestamp).toLocaleString()}</strong>
            <p className="subtitle">
              {reading.temperatureC?.toFixed(1) ?? "--"} C • {reading.humidityPercent?.toFixed(1) ?? "--"}% • {reading.soilMoisturePercent?.toFixed(1) ?? "--"}%
            </p>
            <p className="meta-text">
              Light {reading.lightOn ? "on" : "off"} • Pump {reading.pumpOn ? "on" : "off"}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
