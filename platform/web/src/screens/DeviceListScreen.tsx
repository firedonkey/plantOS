import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { DeviceCard } from "@/components/DeviceCard";
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
          <p className="subtitle">Add your PlantLab device from the mobile app. It will appear here after setup finishes.</p>
        </div>
      ) : null}

      <div className="card-grid">
        {devices.map((device) => (
          <DeviceCard device={device} key={device.id} />
        ))}
      </div>
    </section>
  );
}
