import type { DeviceDashboard, LatestImage } from "@/types";

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

      </div>
    </section>
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
