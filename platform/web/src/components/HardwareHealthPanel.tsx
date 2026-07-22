import { useState } from "react";

import { HardwareHealth } from "@/types";

type HardwareHealthPanelProps = {
  health?: HardwareHealth;
};

export function HardwareHealthPanel({ health }: HardwareHealthPanelProps) {
  const [dismissedAttentionSignature, setDismissedAttentionSignature] = useState<string | null>(null);
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

  const attentionItems = getAttentionItems(health);
  const attentionSignature = attentionItems.join("|");
  const attentionDismissed = attentionSignature.length > 0 && dismissedAttentionSignature === attentionSignature;
  const visibleAttentionItems = attentionDismissed ? [] : attentionItems;
  const headerStatusLabel =
    attentionDismissed && health.friendlyStatus === "needs_attention"
      ? "Reviewed"
      : formatFriendlyStatus(health.friendlyStatus, health.overallStatus);
  const headerChipTone =
    attentionDismissed && health.friendlyStatus === "needs_attention"
      ? "unknown"
      : chipTone(health.friendlyStatus, health.overallStatus);

  return (
    <details className="card stack-form collapsible-panel">
      <summary className="collapsible-summary">
        <div>
          <h3>Hardware health</h3>
          <p className="subtitle">Live heartbeat, node, image, and command status from the shared backend contract.</p>
        </div>
        <span className={`chip chip-${headerChipTone}`}>
          {headerStatusLabel}
        </span>
        <span className="collapsible-indicator" aria-hidden="true" />
      </summary>

      {visibleAttentionItems.length ? (
        <div className="attention-panel">
          <div className="attention-panel-header">
            <strong>Needs attention</strong>
            <button className="attention-dismiss" type="button" onClick={() => setDismissedAttentionSignature(attentionSignature)}>
              Dismiss
            </button>
          </div>
          <ul>
            {visibleAttentionItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="health-grid">
        <div className="health-item">
          <strong>Master</strong>
          <span>{formatNodeStatus(health.primary?.displayName ?? "Master", health.masterStatus ?? health.primary?.status ?? "unknown")}</span>
          <small>{formatAge(health.primary?.lastSeenAt, "Last heartbeat")}</small>
        </div>
        <div className="health-item">
          <strong>Camera</strong>
          <span>{health.cameras.length ? health.cameras.map((camera) => formatNodeStatus(formatCameraNodeName(camera), camera.status)).join(", ") : "No camera nodes yet"}</span>
          <small>{formatAge(health.lastImageAt, "Last image")}</small>
        </div>
        <div className="health-item">
          <strong>Reading</strong>
          <span>{formatAge(health.lastReadingAt ?? health.primary?.diagnostics?.lastSensorReadingAt, "Last reading")}</span>
          <small>{formatAge(health.lastHeartbeatAt, "Last heartbeat")}</small>
        </div>
        <div className="health-item">
          <strong>Last command</strong>
          <span>{health.lastCommand ? `${formatAction(health.lastCommand.action)} · ${formatCommandStatus(health.lastCommand.status)}` : "No recent commands"}</span>
          <small>{health.lastCommand ? formatAge(health.lastCommand.timestamp, "Updated") : "Command history will appear here after the first control action."}</small>
        </div>
      </div>

      <div className="health-grid">
        <div className="health-item">
          <strong>Firmware</strong>
          <span>{health.primary?.diagnostics?.firmwareVersion ?? "Not reported"}</span>
          <small>Uptime: {formatUptime(health.primary?.diagnostics?.uptimeSeconds)}</small>
        </div>
        <div className="health-item">
          <strong>Wi-Fi</strong>
          <span>{formatRssi(health.primary?.diagnostics?.wifiRssiDbm)}</span>
          <small>Reboot: {formatCode(health.primary?.diagnostics?.rebootReason)}</small>
        </div>
        <div className="health-item">
          <strong>Provisioning</strong>
          <span>{formatCode(health.primary?.diagnostics?.provisioningState)}</span>
          <small>Last error: {formatCode(health.primary?.diagnostics?.lastErrorCode)}</small>
        </div>
        <div className="health-item">
          <strong>Counters</strong>
          <span>{formatCounters(health.primary?.diagnostics?.errorCounters)}</span>
          <small>{attentionItems.length ? attentionItems.join(", ") : "No attention reasons"}</small>
        </div>
      </div>

      {health.lastCommand?.message ? <p className="meta-text">{health.lastCommand.message}</p> : null}
    </details>
  );
}

function getAttentionItems(health: HardwareHealth): string[] {
  const items = new Set<string>();

  health.attentionReasons?.forEach((reason) => items.add(formatCode(reason)));

  const heartbeatStatus = health.heartbeatStatus;
  const readingStatus = health.readingStatus;
  const cameraStatus = health.cameraStatus ?? health.imageStatus;
  const masterStatus = health.masterStatus ?? health.primary?.status;

  if (isProblemStatus(heartbeatStatus)) {
    items.add(`Heartbeat is ${formatStatusLabel(heartbeatStatus)}`);
  }
  if (isProblemStatus(readingStatus)) {
    items.add(`Sensor readings are ${formatStatusLabel(readingStatus)}`);
  }
  if (isProblemStatus(cameraStatus)) {
    items.add(`Camera images are ${formatStatusLabel(cameraStatus)}`);
  }
  if (isProblemStatus(masterStatus)) {
    items.add(`Master node is ${formatStatusLabel(masterStatus)}`);
  }

  health.cameras
    .filter((camera) => isProblemStatus(camera.status))
    .forEach((camera) => {
      items.add(`${formatCameraNodeName(camera)}: ${formatStatusLabel(camera.status)}`);
    });

  if (health.lastCommand?.status === "failed") {
    items.add(`${formatAction(health.lastCommand.action)} failed`);
  }
  if (health.primary?.diagnostics?.lastErrorCode) {
    items.add(`Last error: ${formatCode(health.primary.diagnostics.lastErrorCode)}`);
  }

  const counters = health.primary?.diagnostics?.errorCounters;
  Object.entries(counters ?? {})
    .filter(([, value]) => value > 0)
    .forEach(([key, value]) => items.add(`${formatCode(key)}: ${value}`));

  if (!items.size && health.friendlyStatus === "needs_attention") {
    items.add("Backend reported an issue but did not include a specific reason. Review the health rows below.");
  }

  return Array.from(items);
}

function formatCameraNodeName(camera: HardwareHealth["cameras"][number]): string {
  if (camera.cameraRole === "top") {
    return camera.displayName ?? "Top camera";
  }
  if (camera.cameraRole === "side") {
    return camera.displayName ?? "Side camera";
  }
  return camera.displayName ?? `Camera ${camera.nodeIndex ?? ""}`.trim();
}

function isProblemStatus(status: string | undefined): status is string {
  return status === "offline" || status === "stale" || status === "warning" || status === "degraded" || status === "error";
}

function chipTone(status: HardwareHealth["friendlyStatus"], fallback: string): string {
  if (status === "needs_attention") {
    return "degraded";
  }
  if (status === "recently_seen") {
    return "degraded";
  }
  if (status === "online" || status === "offline") {
    return status;
  }
  return fallback === "online" || fallback === "offline" || fallback === "degraded" ? fallback : "unknown";
}

function formatFriendlyStatus(status: HardwareHealth["friendlyStatus"], fallback: string): string {
  switch (status) {
    case "online":
      return "Online";
    case "recently_seen":
      return "Recently seen";
    case "offline":
      return "Offline";
    case "needs_attention":
      return "Needs attention";
    default:
      return formatStatusLabel(fallback);
  }
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
    case "stale":
      return "Stale";
    case "warning":
      return "Warning";
    case "waiting":
      return "Waiting";
    case "provisioning":
      return "Provisioning";
    case "error":
      return "Error";
    default:
      return "Unknown";
  }
}

function formatUptime(seconds: number | undefined): string {
  if (typeof seconds !== "number") {
    return "Not reported";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function formatRssi(value: number | undefined): string {
  return typeof value === "number" ? `${value} dBm` : "Not reported";
}

function formatCode(value: string | undefined): string {
  return value ? value.replace(/_/g, " ") : "Not reported";
}

function formatCounters(counters: Record<string, number> | undefined): string {
  if (!counters || Object.keys(counters).length === 0) {
    return "Not reported";
  }
  return Object.entries(counters)
    .map(([key, value]) => `${formatCode(key)}: ${value}`)
    .join(", ");
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
    case "light_intensity":
      return "Grow LED intensity";
    case "ambient_belt_color":
      return "Ambient LED belt color";
    case "ambient_belt_off":
      return "Ambient LED belt off";
    case "pump_run":
      return "Legacy command";
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
