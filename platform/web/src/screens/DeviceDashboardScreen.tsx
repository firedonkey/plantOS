import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

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
  const growLedOn = dashboard?.device.latestReading?.lightOn === true;
  const growLedIntensityPercent = dashboard?.device.latestReading?.lightIntensityPercent;
  const lightIntensitySupported = hasLightIntensitySupport(dashboard?.hardwareHealth?.primary?.capabilities);
  const currentLightIntensity = clampLightIntensity(growLedIntensityPercent ?? (growLedOn ? 100 : 0));
  const [lightIntensityDraft, setLightIntensityDraft] = useState(currentLightIntensity);
  const pendingLightOn = activeCommandAction === "light_on" || isActionBlocked("light_on");
  const pendingLightOff = activeCommandAction === "light_off" || isActionBlocked("light_off");
  const pendingLightIntensity = activeCommandAction === "light_intensity" || isActionBlocked("light_intensity");
  const nextLightAction = growLedOn ? "light_off" : "light_on";
  const lightToggleDisabled = isCommandRunning || pendingLightOn || pendingLightOff;
  const lightIntensityDisabled = isCommandRunning || pendingLightIntensity;
  const lightToggleLabel = pendingLightOn
    ? "Turning on..."
    : pendingLightOff
      ? "Turning off..."
      : isCommandRunning
        ? "Working..."
        : growLedOn
          ? "Turn off"
          : "Turn on";
  const lightIntensityApplyLabel = pendingLightIntensity ? "Setting..." : isCommandRunning ? "Working..." : "Set";

  useEffect(() => {
    setLightIntensityDraft(currentLightIntensity);
  }, [currentLightIntensity, dashboard?.device.id]);

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
    const directEntries = dashboard.recentImages
      .filter((image) => !shouldUseImageAuthHeaders(image.url))
      .map((image) => [image.id, image.url] as const);
    const protectedImages = dashboard.recentImages.filter((image) => shouldUseImageAuthHeaders(image.url));

    if (!protectedImages.length) {
      setProtectedImageUrls(Object.fromEntries(directEntries));
      return;
    }

    Promise.all(
      protectedImages.map(async (image) => {
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
          setProtectedImageUrls(Object.fromEntries([...directEntries, ...entries]));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setProtectedImageUrls(Object.fromEntries(directEntries));
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
            <div className="metric-card"><span>Air temp</span><strong>{dashboard.device.latestReading?.temperatureC?.toFixed(1) ?? "--"} C</strong></div>
            <div className="metric-card"><span>Humidity</span><strong>{dashboard.device.latestReading?.humidityPercent?.toFixed(1) ?? "--"}%</strong></div>
            <div className="metric-card"><span>Water temp</span><strong>{dashboard.device.latestReading?.waterTemperatureC?.toFixed(1) ?? "--"} C</strong></div>
            <div className="metric-card"><span>Water level</span><strong>{formatWaterLevel(dashboard.device.latestReading?.waterLevelState, dashboard.device.latestReading?.waterLevelRaw)}</strong></div>
            <div className="metric-card metric-card-control">
              <span>Grow LED</span>
              <div className="metric-control-row">
                <strong>{growLedOn ? (lightIntensitySupported ? `${currentLightIntensity}%` : "On") : "Off"}</strong>
                <button
                  aria-label={lightToggleLabel}
                  aria-pressed={growLedOn}
                  className={`toggle-switch ${growLedOn ? "toggle-switch-on" : "toggle-switch-off"}`}
                  disabled={lightToggleDisabled}
                  onClick={() => runCommand(nextLightAction)}
                  type="button"
                >
                  <span className="toggle-switch-label">{growLedOn ? "ON" : "OFF"}</span>
                  <span className="toggle-switch-knob" aria-hidden="true" />
                </button>
              </div>
              {lightIntensitySupported ? (
                <div className="light-intensity-control">
                  <label htmlFor="grow-led-intensity">
                    <span>Intensity</span>
                    <strong>{lightIntensityDraft}%</strong>
                  </label>
                  <input
                    id="grow-led-intensity"
                    aria-label="Grow LED intensity"
                    disabled={lightIntensityDisabled}
                    max={100}
                    min={0}
                    onChange={(event) => setLightIntensityDraft(clampLightIntensity(Number(event.currentTarget.value)))}
                    step={5}
                    type="range"
                    value={lightIntensityDraft}
                  />
                  <button
                    className="secondary-button light-intensity-button"
                    disabled={lightIntensityDisabled || lightIntensityDraft === currentLightIntensity}
                    onClick={() => runCommand("light_intensity", { intensityPercent: lightIntensityDraft })}
                    type="button"
                  >
                    {lightIntensityApplyLabel}
                  </button>
                </div>
              ) : null}
            </div>
          </div>

          <RecentImageGallery
            images={dashboard.recentImages.map((image) => ({
              ...image,
              url: protectedImageUrls[image.id] ?? image.url,
            }))}
            captureDisabled={isCommandRunning || isActionBlocked("capture_image")}
            captureLabel={
              activeCommandAction === "capture_image" || isActionBlocked("capture_image")
                ? "Capture pending"
                : isCommandRunning
                  ? "Working..."
                  : "Capture image"
            }
            onCapture={() => runCommand("capture_image")}
          />

          <ReadingTrendSection
            history={dashboard.history}
            title="Sensor trends"
            subtitle="Use the range tabs to request matching backend history windows for air and water readings."
            selectedRange={selectedRange}
            onRangeChange={setSelectedRange}
            loading={isLoading}
          />

          <Link className="primary-button dashboard-action-button" to={`/devices/${deviceId}/settings`}>
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

function shouldUseImageAuthHeaders(url: string): boolean {
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  return path.startsWith("/api/images/") && path.split("?")[0].endsWith("/content");
}

function formatWaterLevel(state?: string, raw?: number) {
  const label = state ? state.charAt(0).toUpperCase() + state.slice(1) : "--";
  return raw !== undefined ? `${label} (${raw})` : label;
}

function clampLightIntensity(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(value)));
}

function hasLightIntensitySupport(capabilities?: Record<string, unknown>): boolean {
  if (!capabilities) {
    return false;
  }
  if (
    capabilities.light_intensity_control === true ||
    capabilities.light_dimming === true ||
    capabilities.light_pwm === true
  ) {
    return true;
  }
  const modes = capabilities.light_control_modes;
  if (!Array.isArray(modes)) {
    return false;
  }
  return modes.some((mode) => ["intensity", "dimming", "pwm"].includes(String(mode).toLowerCase()));
}
