import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { useSession } from "@/hooks/useSession";

export function DeviceDashboardScreen() {
  const { deviceId = "" } = useParams();
  const { session } = useSession();
  const { dashboard, usedMock, isLoading, error, commandMessage, refresh, runCommand, imageAuthHeaders } =
    useDeviceDashboard(deviceId);
  const [protectedImageUrl, setProtectedImageUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!dashboard?.device.latestImage) {
      setProtectedImageUrl(null);
      return;
    }

    if (session?.mode !== "api" || !imageAuthHeaders) {
      setProtectedImageUrl(dashboard.device.latestImage.url);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;

    fetch(dashboard.device.latestImage.url, { headers: imageAuthHeaders })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Unable to load image: ${response.status}`);
        }
        return response.blob();
      })
      .then((blob) => {
        if (cancelled) {
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setProtectedImageUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) {
          setProtectedImageUrl(null);
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [dashboard?.device.latestImage, imageAuthHeaders, session?.mode]);

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
            {dashboard.device.latestImage && protectedImageUrl ? (
              <>
                <img alt="Latest device capture" className="capture-image" src={protectedImageUrl} />
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
