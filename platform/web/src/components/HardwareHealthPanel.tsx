import { HardwareHealth } from "@/types";

type HardwareHealthPanelProps = {
  health?: HardwareHealth;
};

export function HardwareHealthPanel({ health }: HardwareHealthPanelProps) {
  if (!health) {
    return (
      <details className="card stack-form collapsible-panel">
        <summary className="collapsible-summary">
          <div>
            <h3>Hardware health</h3>
            <p className="subtitle">Waiting for backend hardware health details.</p>
          </div>
          <span className="chip chip-unknown">Waiting</span>
          <span className="collapsible-indicator" aria-hidden="true" />
        </summary>
        <p className="subtitle">Waiting for backend hardware health details.</p>
      </details>
    );
  }

  return (
    <details className="card stack-form collapsible-panel">
      <summary className="collapsible-summary">
        <div>
          <h3>Hardware health</h3>
          <p className="subtitle">Live heartbeat, node, image, and command status from the shared backend contract.</p>
        </div>
        <span className={`chip chip-${health.overallStatus === "degraded" ? "degraded" : health.overallStatus === "online" ? "online" : health.overallStatus === "offline" ? "offline" : "unknown"}`}>
          {formatStatusLabel(health.overallStatus)}
        </span>
        <span className="collapsible-indicator" aria-hidden="true" />
      </summary>

      <div className="health-grid">
        <div className="health-item">
          <strong>Master</strong>
          <span>{formatNodeStatus(health.primary?.displayName ?? "Master", health.masterStatus ?? health.primary?.status ?? "unknown")}</span>
          <small>{formatAge(health.primary?.lastSeenAt, "Last heartbeat")}</small>
        </div>
        <div className="health-item">
          <strong>Camera</strong>
          <span>{health.cameras.length ? health.cameras.map((camera) => formatNodeStatus(camera.displayName ?? `Camera ${camera.nodeIndex ?? ""}`.trim(), camera.status)).join(", ") : "No camera nodes yet"}</span>
          <small>{formatAge(health.lastImageAt, "Last image")}</small>
        </div>
        <div className="health-item">
          <strong>Reading</strong>
          <span>{formatAge(health.lastReadingAt, "Last reading")}</span>
          <small>{formatAge(health.lastHeartbeatAt, "Last heartbeat")}</small>
        </div>
        <div className="health-item">
          <strong>Last command</strong>
          <span>{health.lastCommand ? `${formatAction(health.lastCommand.action)} · ${formatCommandStatus(health.lastCommand.status)}` : "No recent commands"}</span>
          <small>{health.lastCommand ? formatAge(health.lastCommand.timestamp, "Updated") : "Command history will appear here after the first control action."}</small>
        </div>
      </div>

      {health.lastCommand?.message ? <p className="meta-text">{health.lastCommand.message}</p> : null}
    </details>
  );
}

function formatNodeStatus(name: string, status: string): string {
  return `${name}: ${formatStatusLabel(status)}`;
}

function formatStatusLabel(status: string): string {
  switch (status) {
    case "online":
      return "Online";
    case "offline":
      return "Offline";
    case "degraded":
      return "Degraded";
    case "provisioning":
      return "Provisioning";
    case "error":
      return "Error";
    default:
      return "Unknown";
  }
}

function formatCommandStatus(status: string): string {
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

function formatAction(action: string): string {
  switch (action) {
    case "light_on":
      return "Grow LED on";
    case "light_off":
      return "Grow LED off";
    case "pump_run":
      return "Pump run";
    case "capture_image":
      return "Capture image";
    default:
      return action;
  }
}

function formatAge(timestamp: string | undefined, label: string): string {
  if (!timestamp) {
    return `${label}: waiting`;
  }
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) {
    return `${label}: ${seconds}s ago`;
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${label}: ${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  return `${label}: ${hours}h ago`;
}
