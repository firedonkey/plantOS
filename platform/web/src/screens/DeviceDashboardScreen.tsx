import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ReadingTrendSection } from "@/components/ReadingTrendSection";
import { RecentImageGallery } from "@/components/RecentImageGallery";
import { TimelapsePlayer } from "@/components/TimelapsePlayer";
import { DeviceOverviewHero } from "@/components/DeviceOverviewHero";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import type { LatestImage } from "@/types";

export function DeviceDashboardScreen() {
  const { deviceId = "" } = useParams();
  const {
    dashboard,
    usedMock,
    isLoading,
    error,
    commandMessage,
    commandTone,
    isCommandRunning,
    lastUpdatedAt,
    runCommand,
    imageAuthHeaders,
    selectedRange,
    setSelectedRange,
    isActionBlocked,
    activeCommandAction,
  } = useDeviceDashboard(deviceId);
  const [protectedImageUrls, setProtectedImageUrls] = useState<Record<string, string>>({});
  const latestReading = dashboard?.device.latestReading;
  const growLedOn = (dashboard?.device.currentLightOn ?? latestReading?.lightOn) === true;
  const growLedIntensityPercent = dashboard?.device.currentLightIntensityPercent ?? latestReading?.lightIntensityPercent;
  const lightIntensitySupported = hasLightIntensitySupport(dashboard?.hardwareHealth?.primary?.capabilities);
  const currentLightIntensity = clampLightIntensity(growLedIntensityPercent ?? (growLedOn ? 100 : 0));
  const [lightIntensityDraft, setLightIntensityDraft] = useState(currentLightIntensity);
  const [lightIntensityActive, setLightIntensityActive] = useState(false);
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
  const captureDisabled = isCommandRunning || isActionBlocked("capture_image");
  const captureLabel =
    activeCommandAction === "capture_image" || isActionBlocked("capture_image")
      ? "Capture pending"
      : isCommandRunning
        ? "Working..."
        : "Capture image";
  const latestHeroImage = dashboard?.recentImages[0] ?? dashboard?.device.latestImage;
  const resolveImageUrl = (image: LatestImage): string | undefined => {
    if (imageAuthHeaders && shouldUseImageAuthHeaders(image.url)) {
      return protectedImageUrls[image.id];
    }
    return protectedImageUrls[image.id] ?? image.url;
  };
  const latestHeroImageUrl = latestHeroImage ? resolveImageUrl(latestHeroImage) : undefined;

  useEffect(() => {
    if (!lightIntensityActive) {
      setLightIntensityDraft(currentLightIntensity);
    }
  }, [currentLightIntensity, dashboard?.device.id, lightIntensityActive]);

  const commitLightIntensity = () => {
    if (!lightIntensityActive) {
      return;
    }
    setLightIntensityActive(false);
    const nextValue = clampLightIntensity(lightIntensityDraft);
    if (!lightIntensityDisabled && nextValue !== currentLightIntensity) {
      runCommand("light_intensity", { intensityPercent: nextValue });
    }
  };

  useEffect(() => {
    const imageCandidates = [
      ...(dashboard?.recentImages ?? []),
      ...(dashboard?.timelapse?.frames ?? []),
    ];

    if (!imageCandidates.length) {
      setProtectedImageUrls({});
      return;
    }

    if (!imageAuthHeaders) {
      setProtectedImageUrls(
        Object.fromEntries(imageCandidates.map((image) => [image.id, image.url])),
      );
      return;
    }

    let cancelled = false;
    const objectUrls: string[] = [];
    const directEntries = imageCandidates
      .filter((image) => !shouldUseImageAuthHeaders(image.url))
      .map((image) => [image.id, image.url] as const);
    const protectedImages = imageCandidates.filter((image) => shouldUseImageAuthHeaders(image.url));

    if (!protectedImages.length) {
      setProtectedImageUrls(Object.fromEntries(directEntries));
      return;
    }

    setProtectedImageUrls(Object.fromEntries(directEntries));

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
  }, [dashboard?.recentImages, dashboard?.timelapse?.frames, imageAuthHeaders]);

  if (!deviceId) {
    return <p className="error-text">Missing device id.</p>;
  }

  return (
    <section className="page-section">
      {dashboard ? (
        <>
          <DeviceOverviewHero
            dashboard={dashboard}
            usedMock={usedMock}
            latestImage={latestHeroImage}
            latestImageUrl={latestHeroImageUrl}
            lastUpdatedAt={lastUpdatedAt}
          />

          {error ? <p className="status-banner status-banner-error">{error}</p> : null}
          {commandMessage ? (
            <p className={`status-banner ${commandTone === "error" ? "status-banner-error" : commandTone === "info" ? "status-banner-info" : "status-banner-success"}`}>
              {commandMessage}
            </p>
          ) : null}

          <div className="card stack-form">
            <div>
              <h3>Primary readings</h3>
              <p className="subtitle">Latest air and water sensor state.</p>
            </div>
            <div className="metrics-grid">
              <div className="metric-card"><span>Air temp</span><strong>{latestReading?.temperatureC?.toFixed(1) ?? "--"} C</strong><small>{formatAge(latestReading?.timestamp)}</small></div>
              <div className="metric-card"><span>Humidity</span><strong>{latestReading?.humidityPercent?.toFixed(1) ?? "--"}%</strong><small>{formatAge(latestReading?.timestamp)}</small></div>
              <div className="metric-card"><span>Water temp</span><strong>{latestReading?.waterTemperatureC?.toFixed(1) ?? "--"} C</strong><small>{formatAge(latestReading?.timestamp)}</small></div>
              <div className="metric-card"><span>Water level</span><strong>{formatWaterLevel(latestReading?.waterLevelState, latestReading?.waterLevelRaw)}</strong><small>{latestReading?.waterLevelRaw !== undefined ? `Raw ${latestReading.waterLevelRaw}` : "Waiting"}</small></div>
            </div>
            {!latestReading ? <p className="subtitle">Primary metrics will populate after the device posts its next sensor sample.</p> : null}
          </div>

          <div className="card stack-form grow-led-card">
            <div className="grow-led-row">
              <div>
                <h3>Grow LED</h3>
                <p className="subtitle">{growLedOn ? (lightIntensitySupported ? `On | ${currentLightIntensity}%` : "On") : "Off"}</p>
              </div>
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
                  <span>Brightness</span>
                  <strong>{pendingLightIntensity ? "Setting..." : `${lightIntensityDraft}%`}</strong>
                </label>
                <input
                  id="grow-led-intensity"
                  aria-label="Grow LED brightness"
                  disabled={lightIntensityDisabled}
                  max={100}
                  min={0}
                  onBlur={commitLightIntensity}
                  onChange={(event) => {
                    setLightIntensityActive(true);
                    setLightIntensityDraft(clampLightIntensity(Number(event.currentTarget.value)));
                  }}
                  onKeyUp={commitLightIntensity}
                  onPointerDown={() => setLightIntensityActive(true)}
                  onPointerUp={commitLightIntensity}
                  step={5}
                  type="range"
                  value={lightIntensityDraft}
                />
              </div>
            ) : null}
          </div>

          <RecentImageGallery
            images={dashboard.recentImages.map((image) => ({
              ...image,
              url: resolveImageUrl(image),
            }))}
            captureDisabled={captureDisabled}
            captureLabel={captureLabel}
            onCapture={() => runCommand("capture_image")}
          />

          <TimelapsePlayer
            timelapse={
              dashboard.timelapse
                ? {
                    ...dashboard.timelapse,
                    frames: dashboard.timelapse.frames
                      .map((frame) => ({
                        ...frame,
                        url: resolveImageUrl(frame),
                      }))
                      .filter((frame): frame is LatestImage => Boolean(frame.url)),
                  }
                : undefined
            }
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

function formatAge(timestamp?: string) {
  if (!timestamp) {
    return "Waiting";
  }
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.round(hours / 24);
  return `${days}d ago`;
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
