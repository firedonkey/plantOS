import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { CommandActivityPanel } from "@/components/CommandActivityPanel";
import { HardwareHealthPanel } from "@/components/HardwareHealthPanel";
import { ReadingTrendSection } from "@/components/ReadingTrendSection";
import { RecentImageGallery } from "@/components/RecentImageGallery";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { useSession } from "@/hooks/useSession";

export function DeviceDashboardScreen() {
  const { deviceId = "" } = useParams();
  const { session } = useSession();
  const {
    dashboard,
    usedMock,
    isLoading,
    error,
    commandMessage,
    commandTone,
    isCommandRunning,
    lastUpdatedAt,
    refresh,
    runCommand,
    imageAuthHeaders,
    selectedRange,
    setSelectedRange,
    isActionBlocked,
    activeCommandAction,
  } = useDeviceDashboard(deviceId);
  const [protectedImageUrls, setProtectedImageUrls] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!dashboard?.recentImages.length) {
      setProtectedImageUrls({});
      return;
    }

    if (session?.mode !== "api" || !imageAuthHeaders) {
      setProtectedImageUrls(
        Object.fromEntries(dashboard.recentImages.map((image) => [image.id, image.url])),
      );
      return;
    }

    let cancelled = false;
    const objectUrls: string[] = [];

    Promise.all(
      dashboard.recentImages.map(async (image) => {
        const response = await fetch(image.url, { headers: imageAuthHeaders });
        if (!response.ok) {
          throw new Error(`Unable to load image: ${response.status}`);
        }
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        objectUrls.push(objectUrl);
        return [image.id, objectUrl] as const;
      }),
    )
      .then((entries) => {
        if (!cancelled) {
          setProtectedImageUrls(Object.fromEntries(entries));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setProtectedImageUrls({});
        }
      });

    return () => {
      cancelled = true;
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [dashboard?.recentImages, imageAuthHeaders, session?.mode]);

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
              <p className="meta-text">
                {lastUpdatedAt ? `Last updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Waiting for first refresh."}
              </p>
            </div>
            <div className="header-actions">
              {usedMock ? <span className="chip chip-mock">Mock mode</span> : null}
              <button className="secondary-button" disabled={isLoading || isCommandRunning} onClick={() => void refresh()}>
                {isLoading ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </div>

          {error ? <p className="status-banner status-banner-error">{error}</p> : null}
          {commandMessage ? (
            <p className={`status-banner ${commandTone === "error" ? "status-banner-error" : commandTone === "info" ? "status-banner-info" : "status-banner-success"}`}>
              {commandMessage}
            </p>
          ) : null}

          <div className="metrics-grid">
            <div className="metric-card"><span>Temperature</span><strong>{dashboard.device.latestReading?.temperatureC?.toFixed(1) ?? "--"} C</strong></div>
            <div className="metric-card"><span>Humidity</span><strong>{dashboard.device.latestReading?.humidityPercent?.toFixed(1) ?? "--"}%</strong></div>
            <div className="metric-card"><span>Soil Moisture</span><strong>{dashboard.device.latestReading?.soilMoisturePercent?.toFixed(1) ?? "--"}%</strong></div>
            <div className="metric-card"><span>Water Level</span><strong>{dashboard.device.latestReading?.waterLevelPercent?.toFixed(0) ?? "--"}%</strong></div>
            <div className="metric-card"><span>Light</span><strong>{dashboard.device.latestReading?.lightOn ? "On" : "Off"}</strong></div>
            <div className="metric-card"><span>Pump</span><strong>{dashboard.device.latestReading?.pumpOn ? "On" : "Off"}</strong></div>
          </div>

          <ReadingTrendSection
            history={dashboard.history}
            title="Sensor trends"
            subtitle="Use the range tabs to request matching backend history windows for temperature, humidity, and soil moisture."
            selectedRange={selectedRange}
            onRangeChange={setSelectedRange}
            loading={isLoading}
          />

          <RecentImageGallery
            images={dashboard.recentImages.map((image) => ({
              ...image,
              url: protectedImageUrls[image.id] ?? image.url,
            }))}
          />

          <HardwareHealthPanel health={dashboard.hardwareHealth} />

          <CommandActivityPanel commands={dashboard.recentCommands} />

          <div className="card">
            <h3>Manual controls</h3>
            <div className="button-row">
              <button className="primary-button" disabled={isCommandRunning || isActionBlocked("light_on")} onClick={() => runCommand("light_on")}>
                {activeCommandAction === "light_on" || isActionBlocked("light_on") ? "Light on pending" : isCommandRunning ? "Working..." : "Light on"}
              </button>
              <button className="primary-button" disabled={isCommandRunning || isActionBlocked("light_off")} onClick={() => runCommand("light_off")}>
                {activeCommandAction === "light_off" || isActionBlocked("light_off") ? "Light off pending" : "Light off"}
              </button>
              <button className="primary-button" disabled={isCommandRunning || isActionBlocked("pump_run")} onClick={() => runCommand("pump_run")}>
                {activeCommandAction === "pump_run" || isActionBlocked("pump_run") ? "Pump run pending" : "Pump run"}
              </button>
              <button className="secondary-button" disabled title="Image capture is coming later.">
                Capture coming later
              </button>
            </div>
            {dashboard.hardwareHealth?.lastCommand ? (
              <p className="meta-text">
                Last command: {formatActionLabel(dashboard.hardwareHealth.lastCommand.action)} {formatStatusLabel(dashboard.hardwareHealth.lastCommand.status).toLowerCase()}.
              </p>
            ) : null}
          </div>

          <Link className="text-link" to={`/devices/${deviceId}/history`}>
            View history
          </Link>
          <Link className="text-link" to={`/devices/${deviceId}/settings`}>
            Device settings
          </Link>
          <Link className="text-link" to={`/devices/${deviceId}/remove`}>
            Remove device
          </Link>
        </>
      ) : error ? (
        <p className="status-banner status-banner-error">{error}</p>
      ) : (
        <p className="status-banner">Loading dashboard…</p>
      )}
    </section>
  );
}

function formatActionLabel(action: string) {
  switch (action) {
    case "light_on":
      return "Light on";
    case "light_off":
      return "Light off";
    case "pump_run":
      return "Pump run";
    default:
      return "Capture image";
  }
}

function formatStatusLabel(status: string) {
  switch (status) {
    case "completed":
      return "Completed";
    case "in_progress":
      return "In progress";
    case "pending":
      return "Pending";
    case "sent":
      return "Sent";
    case "failed":
      return "Failed";
    default:
      return "Unknown";
  }
}
