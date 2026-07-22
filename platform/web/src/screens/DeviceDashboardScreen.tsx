import { Dispatch, SetStateAction, useEffect, useRef, useState } from "react";
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
  const protectedImageUrlCacheRef = useRef<Record<string, { sourceUrl: string; objectUrl: string }>>({});
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
  const [ambientBeltBrightness, setAmbientBeltBrightness] = useState(10);
  const pendingAmbientBeltColor = activeCommandAction === "ambient_belt_color" || isActionBlocked("ambient_belt_color");
  const pendingAmbientBeltOff = activeCommandAction === "ambient_belt_off" || isActionBlocked("ambient_belt_off");
  const ambientBeltColorDisabled = isCommandRunning || pendingAmbientBeltColor;
  const ambientBeltOffDisabled = isCommandRunning || pendingAmbientBeltOff;
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
      revokeProtectedImageUrls(protectedImageUrlCacheRef.current);
      protectedImageUrlCacheRef.current = {};
      updateProtectedImageUrls(setProtectedImageUrls, {});
      return;
    }

    if (!imageAuthHeaders) {
      revokeProtectedImageUrls(protectedImageUrlCacheRef.current);
      protectedImageUrlCacheRef.current = {};
      updateProtectedImageUrls(setProtectedImageUrls, Object.fromEntries(imageCandidates.map((image) => [image.id, image.url])));
      return;
    }

    let cancelled = false;
    const candidateIds = new Set(imageCandidates.map((image) => image.id));
    const directEntries = imageCandidates
      .filter((image) => !shouldUseImageAuthHeaders(image.url))
      .map((image) => [image.id, image.url] as const);
    const protectedImages = imageCandidates.filter((image) => shouldUseImageAuthHeaders(image.url));
    const cachedEntries = protectedImages
      .map((image) => {
        const cached = protectedImageUrlCacheRef.current[image.id];
        return cached && cached.sourceUrl === image.url ? ([image.id, cached.objectUrl] as const) : null;
      })
      .filter((entry): entry is readonly [string, string] => Boolean(entry));

    if (!protectedImages.length) {
      revokeProtectedImageUrls(protectedImageUrlCacheRef.current);
      protectedImageUrlCacheRef.current = {};
      updateProtectedImageUrls(setProtectedImageUrls, Object.fromEntries(directEntries));
      return;
    }

    updateProtectedImageUrls(setProtectedImageUrls, Object.fromEntries([...directEntries, ...cachedEntries]));

    Promise.all(
      protectedImages.map(async (image) => {
        const cached = protectedImageUrlCacheRef.current[image.id];
        if (cached && cached.sourceUrl === image.url) {
          return [image.id, cached.objectUrl] as const;
        }
        const response = await fetch(image.url, { headers: imageAuthHeaders });
        if (!response.ok) {
          throw new Error(`Unable to load image: ${response.status}`);
        }
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        if (cached && cached.objectUrl !== objectUrl) {
          URL.revokeObjectURL(cached.objectUrl);
        }
        protectedImageUrlCacheRef.current[image.id] = { sourceUrl: image.url, objectUrl };
        return [image.id, objectUrl] as const;
      }),
    )
      .then((entries) => {
        if (!cancelled) {
          for (const [id, cached] of Object.entries(protectedImageUrlCacheRef.current)) {
            if (!candidateIds.has(id)) {
              URL.revokeObjectURL(cached.objectUrl);
              delete protectedImageUrlCacheRef.current[id];
            }
          }
          updateProtectedImageUrls(setProtectedImageUrls, Object.fromEntries([...directEntries, ...entries]));
        }
      })
      .catch(() => {
        if (!cancelled) {
          updateProtectedImageUrls(setProtectedImageUrls, Object.fromEntries([...directEntries, ...cachedEntries]));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [dashboard?.recentImages, dashboard?.timelapse?.frames, imageAuthHeaders]);

  useEffect(() => {
    return () => {
      revokeProtectedImageUrls(protectedImageUrlCacheRef.current);
      protectedImageUrlCacheRef.current = {};
    };
  }, []);

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

          <div className="card stack-form ambient-led-belt-card">
            <div className="ambient-led-belt-heading">
              <div>
                <h3>Ambient LED belt</h3>
                <p className="subtitle">Bottom status belt | Brightness {ambientBeltBrightness}/51</p>
              </div>
              <button
                className="ambient-belt-off-button"
                disabled={ambientBeltOffDisabled}
                onClick={() => runCommand("ambient_belt_off")}
                type="button"
              >
                Off
              </button>
            </div>
            <div className="ambient-color-grid" aria-label="Ambient LED belt colors">
              {AMBIENT_LED_BELT_COLORS.map((option) => (
                <button
                  className="ambient-color-button"
                  disabled={ambientBeltColorDisabled}
                  key={option.key}
                  onClick={() => runCommand("ambient_belt_color", { ambientColor: option.color, ambientBrightness: ambientBeltBrightness })}
                  type="button"
                >
                  <span
                    aria-hidden="true"
                    className={`ambient-color-swatch ${option.key === "white" ? "ambient-color-swatch-light" : ""}`}
                    style={{ backgroundColor: option.swatch }}
                  />
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
            <div className="ambient-brightness-control">
              <label htmlFor="ambient-led-belt-brightness">
                <span>Brightness</span>
                <strong>{ambientBeltBrightness}/51</strong>
              </label>
              <input
                id="ambient-led-belt-brightness"
                aria-label="Ambient LED belt brightness"
                max={51}
                min={1}
                onChange={(event) => setAmbientBeltBrightness(clampAmbientLedBeltBrightness(Number(event.currentTarget.value)))}
                step={1}
                type="range"
                value={ambientBeltBrightness}
              />
            </div>
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

function updateProtectedImageUrls(
  setProtectedImageUrls: Dispatch<SetStateAction<Record<string, string>>>,
  nextUrls: Record<string, string>,
) {
  setProtectedImageUrls((current) => (sameStringRecord(current, nextUrls) ? current : nextUrls));
}

function sameStringRecord(left: Record<string, string>, right: Record<string, string>): boolean {
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) {
    return false;
  }
  return leftKeys.every((key) => left[key] === right[key]);
}

function revokeProtectedImageUrls(cache: Record<string, { objectUrl: string }>) {
  Object.values(cache).forEach((entry) => URL.revokeObjectURL(entry.objectUrl));
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

function clampAmbientLedBeltBrightness(value: number): number {
  if (!Number.isFinite(value)) {
    return 10;
  }
  return Math.max(1, Math.min(51, Math.round(value)));
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

const AMBIENT_LED_BELT_COLORS = [
  { key: "red", label: "Red", swatch: "#d93a32", color: { r: 255, g: 0, b: 0 } },
  { key: "green", label: "Green", swatch: "#238855", color: { r: 0, g: 255, b: 0 } },
  { key: "blue", label: "Blue", swatch: "#2d6cdf", color: { r: 0, g: 0, b: 255 } },
  { key: "white", label: "White", swatch: "#ffffff", color: { r: 255, g: 255, b: 255 } },
] as const;
