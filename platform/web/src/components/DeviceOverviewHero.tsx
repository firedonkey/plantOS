import type { DeviceDashboard, DeviceConnectionState, LatestImage } from "@/types";

type DeviceOverviewHeroProps = {
  dashboard: DeviceDashboard;
  usedMock: boolean;
  latestImage?: LatestImage;
  latestImageUrl?: string;
  lastUpdatedAt?: string | null;
};

export function DeviceOverviewHero({
  dashboard,
  usedMock,
  latestImage,
  latestImageUrl,
  lastUpdatedAt,
}: DeviceOverviewHeroProps) {
  const device = dashboard.device;
  const health = resolveHealth(dashboard);
  const wifi = resolveWifi(dashboard);
  const camera = resolveCamera(dashboard);
  const light = resolveLight(dashboard);
  const lastSeen = dashboard.hardwareHealth?.lastHeartbeatAt ?? device.lastSeenAt;

  return (
    <section className={`device-overview-hero surface surface-hero device-overview-hero-${health.tone}`}>
      <div className="device-overview-main">
        <div className="device-overview-kicker">
          <span className={`status-token health-token-${health.tone}`}>{health.label}</span>
          {usedMock ? <span className="status-token status-token-mock">Simulator</span> : null}
        </div>

        <div>
          <div className="eyebrow">DEVICE OVERVIEW</div>
          <h2>{device.name}</h2>
          <p className="device-overview-subtitle">
            {device.plantType ?? "Plant type not set"} • {device.location ?? "No location set"}
          </p>
        </div>

        <div className="device-overview-meta">
          <span>Last seen {formatAge(lastSeen)}</span>
          <span>Updated {lastUpdatedAt ? new Date(lastUpdatedAt).toLocaleTimeString() : "waiting"}</span>
        </div>
      </div>

      <div className="device-overview-side">
        <div className="device-overview-image">
          {latestImage && latestImageUrl ? (
            <>
              <img src={latestImageUrl} alt={`${device.name} latest capture`} />
              <span>Latest capture {formatAge(latestImage.capturedAt)}</span>
            </>
          ) : (
            <div className="device-overview-image-empty">
              <strong>No image yet</strong>
              <span>Captures will appear after the camera uploads.</span>
            </div>
          )}
        </div>

        <div className="device-overview-stats" aria-label="Device runtime summary">
          <OverviewStat label="Connection" value={formatConnection(device.status)} tone={connectionTone(device.status)} meta={formatAge(lastSeen)} />
          <OverviewStat label="Wi-Fi" value={wifi.label} tone={wifi.tone} meta={wifi.meta} />
          <OverviewStat label="Camera" value={camera.label} tone={camera.tone} meta={camera.meta} />
          <OverviewStat label="Grow light" value={light.label} tone={light.tone} meta={light.meta} />
        </div>
      </div>
    </section>
  );
}

function OverviewStat({
  label,
  value,
  tone,
  meta,
}: {
  label: string;
  value: string;
  tone: "online" | "degraded" | "offline" | "updating" | "error";
  meta: string;
}) {
  return (
    <div className="device-overview-stat">
      <span className={`device-overview-dot status-dot-${tone}`} aria-hidden="true" />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{meta}</small>
      </div>
    </div>
  );
}

function resolveHealth(dashboard: DeviceDashboard): { label: string; tone: "healthy" | "attention" | "offline" | "updating" | "critical" } {
  const health = dashboard.hardwareHealth;
  const status = health?.friendlyStatus ?? health?.overallStatus ?? dashboard.device.status;
  const cameraStatus = health?.cameraStatus;

  if (status === "online" || status === "recently_seen") {
    return {
      label: "Healthy",
      tone: "healthy",
    };
  }

  if (status === "offline" || dashboard.device.status === "offline") {
    return {
      label: "Offline",
      tone: "offline",
    };
  }

  if (status === "provisioning") {
    return {
      label: "Provisioning",
      tone: "updating",
    };
  }

  if (status === "error") {
    return {
      label: "Needs attention",
      tone: "critical",
    };
  }

  if (cameraStatus === "offline") {
    return {
      label: "Camera offline",
      tone: "attention",
    };
  }

  return {
    label: "Needs attention",
    tone: "attention",
  };
}

function resolveWifi(dashboard: DeviceDashboard): { label: string; tone: "online" | "degraded" | "offline" | "updating" | "error"; meta: string } {
  const rssi = dashboard.hardwareHealth?.primary?.diagnostics?.wifiRssiDbm;
  if (typeof rssi !== "number") {
    return { label: "Waiting", tone: "offline", meta: "No RSSI yet" };
  }
  if (rssi <= -85) {
    return { label: "Weak", tone: "error", meta: `${rssi} dBm` };
  }
  if (rssi <= -75) {
    return { label: "Low", tone: "degraded", meta: `${rssi} dBm` };
  }
  return { label: "Good", tone: "online", meta: `${rssi} dBm` };
}

function resolveCamera(dashboard: DeviceDashboard): { label: string; tone: "online" | "degraded" | "offline" | "updating" | "error"; meta: string } {
  const status = dashboard.hardwareHealth?.cameraStatus ?? dashboard.hardwareHealth?.cameras[0]?.status;
  const cameraCount = dashboard.hardwareHealth?.cameras.length ?? 0;
  if (!cameraCount && !status) {
    return { label: "Waiting", tone: "offline", meta: "No node yet" };
  }
  if (status === "online") {
    return { label: "Online", tone: "online", meta: `${cameraCount || 1} node${cameraCount === 1 ? "" : "s"}` };
  }
  if (status === "degraded" || status === "warning" || status === "stale") {
    return { label: "Review", tone: "degraded", meta: formatConnection(status) };
  }
  if (status === "offline") {
    return { label: "Offline", tone: "offline", meta: "Reconnect pending" };
  }
  return { label: "Waiting", tone: "updating", meta: "Joining" };
}

function resolveLight(dashboard: DeviceDashboard): { label: string; tone: "online" | "degraded" | "offline" | "updating" | "error"; meta: string } {
  const reading = dashboard.device.latestReading;
  const lightOn = (dashboard.device.currentLightOn ?? reading?.lightOn) === true;
  const intensity = dashboard.device.currentLightIntensityPercent ?? reading?.lightIntensityPercent;
  if (lightOn) {
    return { label: "On", tone: "online", meta: typeof intensity === "number" ? `${Math.round(intensity)}%` : "Active" };
  }
  return { label: "Off", tone: "offline", meta: typeof intensity === "number" ? `${Math.round(intensity)}%` : "Ready" };
}

function connectionTone(status: DeviceConnectionState): "online" | "degraded" | "offline" | "updating" | "error" {
  if (status === "online") {
    return "online";
  }
  if (status === "degraded" || status === "stale" || status === "warning") {
    return "degraded";
  }
  if (status === "offline") {
    return "offline";
  }
  return "updating";
}

function formatConnection(status: string | undefined): string {
  if (!status) {
    return "Unknown";
  }
  return status
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatAge(timestamp?: string): string {
  if (!timestamp) {
    return "waiting";
  }
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 10) {
    return "just now";
  }
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
  return `${Math.round(hours / 24)}d ago`;
}
