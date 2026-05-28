import { useState } from "react";
import { Link } from "react-router-dom";

import type { Device, DeviceConnectionState } from "@/types";

type DeviceCardProps = {
  device: Device;
};

export function DeviceCard({ device }: DeviceCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const tone = statusTone(device.status);
  const latestReading = device.latestReading;
  const hasImage = Boolean(device.latestImage?.url && !imageFailed);

  return (
    <Link className={`device-card device-card-${tone}`} to={`/devices/${device.id}`}>
      <div className="device-card-media">
        {hasImage ? (
          <img src={device.latestImage!.url} alt={`${device.name} latest capture`} onError={() => setImageFailed(true)} />
        ) : (
          <div className="device-card-media-empty">
            <span>{device.name.slice(0, 1).toUpperCase()}</span>
          </div>
        )}
        <span className={`status-token ${statusTokenClass(tone)}`}>{statusLabel(device.status)}</span>
      </div>

      <div className="device-card-content">
        <div className="device-card-title-row">
          <div>
            <h3>{device.name}</h3>
            <p>{device.plantType ?? "Plant type not set"} • {device.location ?? "No location set"}</p>
          </div>
          <span className="device-card-arrow" aria-hidden="true">Open</span>
        </div>

        <div className="device-card-highlights">
          <DeviceCardMetric label="Air" value={formatMetric(latestReading?.temperatureC, "C")} />
          <DeviceCardMetric label="Humidity" value={formatMetric(latestReading?.humidityPercent, "%")} />
          <DeviceCardMetric label="Water" value={formatMetric(latestReading?.waterTemperatureC, "C")} />
        </div>

        <div className="device-card-footer">
          <span>{formatLightState(device)}</span>
          <span>Last seen {formatAge(device.lastSeenAt ?? latestReading?.timestamp)}</span>
        </div>
      </div>
    </Link>
  );
}

function DeviceCardMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function statusTone(status: DeviceConnectionState): "online" | "degraded" | "offline" | "updating" | "error" {
  if (status === "online") {
    return "online";
  }
  if (status === "degraded" || status === "warning" || status === "stale") {
    return "degraded";
  }
  if (status === "offline") {
    return "offline";
  }
  return "updating";
}

function statusTokenClass(tone: ReturnType<typeof statusTone>): string {
  if (tone === "error") {
    return "status-token-error";
  }
  return `status-token-${tone}`;
}

function statusLabel(status: DeviceConnectionState): string {
  if (status === "online") {
    return "Online";
  }
  if (status === "offline") {
    return "Offline";
  }
  if (status === "degraded" || status === "warning") {
    return "Needs attention";
  }
  if (status === "stale") {
    return "Stale";
  }
  if (status === "waiting") {
    return "Waiting";
  }
  return "Unknown";
}

function formatMetric(value: number | undefined, unit: string): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }
  return `${value.toFixed(1)} ${unit}`;
}

function formatLightState(device: Device): string {
  const latestReading = device.latestReading;
  const lightOn = (device.currentLightOn ?? latestReading?.lightOn) === true;
  const intensity = device.currentLightIntensityPercent ?? latestReading?.lightIntensityPercent;
  if (!lightOn) {
    return "Light off";
  }
  return typeof intensity === "number" ? `Light on ${Math.round(intensity)}%` : "Light on";
}

function formatAge(timestamp?: string): string {
  if (!timestamp) {
    return "waiting";
  }
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) {
    return "just now";
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
