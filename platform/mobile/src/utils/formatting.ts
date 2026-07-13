import type { Device, DeviceCommand, HardwareHealth, SensorReading } from "@/types";

export function formatTemperature(value?: number): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}°C` : "--";
}

export function formatPercent(value?: number): string {
  return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value)}%` : "--";
}

export function formatHumidity(value?: number): string {
  return formatPercent(value);
}

export function formatWaterLevel(reading?: SensorReading): string {
  const state = reading?.waterLevelState ? titleCase(reading.waterLevelState) : undefined;
  if (state && typeof reading?.waterLevelRaw === "number") {
    return `${state} (${reading.waterLevelRaw})`;
  }
  return state ?? "--";
}

export function formatLightState(device?: Device): string {
  if (!device) {
    return "--";
  }
  const latestReading = device.latestReading;
  const lightOn = (device.currentLightOn ?? latestReading?.lightOn) === true;
  const intensity = device.currentLightIntensityPercent ?? latestReading?.lightIntensityPercent;
  if (!lightOn) {
    return "Off";
  }
  return typeof intensity === "number" ? `On ${Math.round(intensity)}%` : "On";
}

export function formatTimestamp(timestamp?: string, fallback = "Not available"): string {
  if (!timestamp) {
    return fallback;
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return fallback;
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatShortTimestamp(timestamp?: string, fallback = "Waiting"): string {
  if (!timestamp) {
    return fallback;
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return fallback;
  }
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function formatRelativeAge(timestamp?: string, fallback = "Waiting"): string {
  if (!timestamp) {
    return fallback;
  }
  const time = new Date(timestamp).getTime();
  if (Number.isNaN(time)) {
    return fallback;
  }
  const seconds = Math.max(0, Math.round((Date.now() - time) / 1000));
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

export function formatUptime(seconds?: number): string {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) {
    return "Not reported";
  }
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  if (days > 0) {
    return `${days} day${days === 1 ? "" : "s"}${hours ? ` ${hours} hour${hours === 1 ? "" : "s"}` : ""}`;
  }
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours} hour${hours === 1 ? "" : "s"}${minutes ? ` ${minutes} minute${minutes === 1 ? "" : "s"}` : ""}`;
  }
  return `${minutes} minute${minutes === 1 ? "" : "s"}`;
}

export function formatDeviceStatus(status?: Device["status"] | HardwareHealth["overallStatus"]): string {
  switch (status) {
    case "online":
      return "Online";
    case "offline":
      return "Offline";
    case "degraded":
    case "warning":
      return "Needs attention";
    case "stale":
      return "Stale";
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

export function formatCommandAction(action: DeviceCommand["action"]): string {
  switch (action) {
    case "capture_image":
      return "Photo Captured";
    case "light_on":
      return "Light Turned On";
    case "light_off":
      return "Light Turned Off";
    case "light_intensity":
      return "Light Adjusted";
    case "pump_run":
      return "Pump Run";
  }
}

export function titleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}
