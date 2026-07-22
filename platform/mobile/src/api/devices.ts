import { ApiError, apiRequest, shouldUseMockFallback } from "./client";
import { mockDashboards, mockDevices } from "@/mock/data";
import {
  Device,
  DeviceCommand,
  DeviceDashboard,
  DeviceTimeline,
  DeviceTimelineEvent,
  DeviceTimelapse,
  FriendlyHardwareStatus,
  HardwareDiagnostics,
  HardwareHealth,
  HardwareNodeHealth,
  SensorReading,
  CameraRole,
} from "@/types";
import type { RangeKey } from "@/components/ReadingTrendSection";
import type { BleDeviceIdentity } from "@/ble/bleProvisioning";

type ApiDevice = {
  id: number;
  name: string;
  location?: string | null;
  plant_type?: string | null;
  api_token?: string | null;
  status?: string | null;
  current_light_on?: boolean | null;
  current_light_intensity_percent?: number | null;
  current_pump_on?: boolean | null;
  latest_reading?: ApiDeviceSummary["latest_reading"] | null;
  latest_image?: ApiDeviceSummary["latest_image"] | null;
  node_summary?: ApiDeviceSummary["node_summary"] | null;
  hardware_health?: ApiDeviceSummary["hardware_health"] | null;
};

type ApiDeviceSummary = {
  id: number;
  name: string;
  location?: string | null;
  plant_type?: string | null;
  current_light_on?: boolean | null;
  current_light_intensity_percent?: number | null;
  current_pump_on?: boolean | null;
  latest_reading?: {
    timestamp: string;
    moisture?: number | null;
    temperature?: number | null;
    humidity?: number | null;
    water_temperature_c?: number | null;
    water_level_raw?: number | null;
    water_level_state?: string | null;
    light_on?: boolean | null;
    light_intensity_percent?: number | null;
    pump_on?: boolean | null;
  } | null;
  latest_image?: {
    id: number;
    content_url: string;
    timestamp: string;
    source_hardware_device_id?: string | null;
    camera_role?: CameraRole | null;
  } | null;
  node_summary?: {
    overall_status?: string | null;
    primary?: {
      status?: string | null;
    } | null;
  } | null;
  hardware_health?: {
    overall_status: string;
    master_status?: string | null;
    master_online: boolean;
    primary?: ApiHealthNode | null;
    cameras?: ApiHealthNode[] | null;
    last_heartbeat_at?: string | null;
    heartbeat_status?: string | null;
    last_reading_at?: string | null;
    reading_status?: string | null;
    last_image_at?: string | null;
    image_status?: string | null;
    camera_status?: string | null;
    last_command?: ApiHealthCommand | null;
    friendly_status?: string | null;
    attention_reasons?: string[] | null;
  } | null;
};

type ApiHardwareDiagnostics = {
  schema_version?: number | null;
  reported_status?: string | null;
  firmware_version?: string | null;
  uptime_seconds?: number | null;
  wifi_rssi_dbm?: number | null;
  reboot_reason?: string | null;
  provisioning_state?: string | null;
  last_sensor_reading_at?: string | null;
  last_camera_image_upload_at?: string | null;
  last_command_id?: number | null;
  last_command_status?: string | null;
  last_command_code?: string | null;
  last_command_message?: string | null;
  last_command_at?: string | null;
  error_counters?: Record<string, number> | null;
  last_error_code?: string | null;
  last_error_message?: string | null;
  reported_at?: string | null;
  updated_at?: string | null;
};

type ApiHealthNode = {
  hardware_device_id: string;
  node_role?: string | null;
  camera_role?: CameraRole | null;
  node_index?: number | null;
  display_name?: string | null;
  status: string;
  health_status?: string | null;
  hardware_model?: string | null;
  hardware_version?: string | null;
  software_version?: string | null;
  ota_status?: string | null;
  ota_available_version?: string | null;
  ota_target_version?: string | null;
  ota_release_id?: string | null;
  ota_progress?: number | null;
  ota_error?: string | null;
  ota_updated_at?: string | null;
  ota_last_success_at?: string | null;
  capabilities?: Record<string, unknown> | null;
  last_seen_at?: string | null;
  diagnostics?: ApiHardwareDiagnostics | null;
};

type ApiHealthCommand = {
  id: number;
  target: "grow_light" | "light" | "pump" | "camera";
  action: "on" | "off" | "set_intensity" | "run" | "capture";
  status: "pending" | "sent" | "in_progress" | "completed" | "failed" | "timed_out";
  message?: string | null;
  timestamp: string;
};

type ApiSensorReading = {
  timestamp: string;
  moisture?: number | null;
  temperature?: number | null;
  humidity?: number | null;
  water_temperature_c?: number | null;
  water_level_raw?: number | null;
  water_level_state?: string | null;
  light_on?: boolean | null;
  light_intensity_percent?: number | null;
  pump_on?: boolean | null;
};

type ApiCommandRead = {
  id: number;
  device_id: number;
  target: "grow_light" | "light" | "pump" | "camera";
  action: "on" | "off" | "set_intensity" | "run" | "capture";
  value?: string | null;
  status: "pending" | "sent" | "in_progress" | "completed" | "failed" | "timed_out";
  message?: string | null;
  created_at: string;
  sent_at?: string | null;
  completed_at?: string | null;
};

type ApiCommandEnvelope = {
  status: "accepted" | "unsupported" | "error";
  device_id: number;
  command: "grow_light" | "light" | "pump" | "capture";
  action: string;
  queued: boolean;
  message: string;
  command_id?: number | null;
  command_status?: string | null;
  created_at?: string | null;
  value?: string | null;
};

type ApiDeviceImage = {
  id: number;
  content_url: string;
  timestamp: string;
  source_hardware_device_id?: string | null;
  camera_role?: CameraRole | null;
};

type ApiDeviceTimelapse = {
  device_id: number;
  camera_role?: CameraRole | null;
  window_start: string;
  window_end: string;
  interval_minutes: number;
  target_duration_seconds?: number;
  playback_frame_ms: number;
  total_image_count: number;
  frame_count: number;
  frames: ApiDeviceImage[];
};

type ApiDeviceTimelineEvent = {
  id: number;
  event_type: string;
  severity: string;
  occurred_at: string;
  hardware_device_id?: string | null;
  node_role?: string | null;
  correlation_id?: string | null;
  summary: string;
  code?: string | null;
  message?: string | null;
  data?: Record<string, unknown> | null;
  created_at: string;
};

type ApiDeviceTimeline = {
  events?: ApiDeviceTimelineEvent[] | null;
  next_before?: string | null;
};

type CommandRequestOptions = {
  intensityPercent?: number;
  cameraRole?: CameraRole | "all";
  cameraNodeId?: string;
};

type ApiSetupCodeResponse = {
  serial_number?: string | null;
  setup_code?: string | null;
  claim_token?: string | null;
  setup_token?: string | null;
  continue_setup_url: string;
  setup_finishing_url: string;
  expect_image: boolean;
  platform_url?: string | null;
  provisioning_api_url: string;
};

type ApiSetupStatusResponse = {
  ready: boolean;
  device_found?: boolean;
  device_id?: number | null;
  online?: boolean;
  last_heartbeat_at?: string | null;
  status?: string | null;
  redirect_path?: string | null;
};

type ApiClaimTokenStatusResponse = {
  used: boolean;
  used_by_device_id?: number | null;
  expected_device_id?: string | null;
  expires_at?: string | null;
  expired?: boolean;
  failure_code?: string | null;
  failure_message?: string | null;
  failed_at?: string | null;
};

type ApiDeleteResponse = {
  device_id: number;
  message: string;
};

type ApiReleaseResponse = {
  device_id: number;
  message: string;
  released_at?: string | null;
  status?: string | null;
};

const READING_LIMIT_BY_RANGE: Record<RangeKey, number> = {
  "24h": 5000,
  "7d": 25000,
  "30d": 50000,
  all: 50000,
};

export type DeviceSetupHandoff = {
  serialNumber?: string;
  expectedDeviceId?: string;
  setupToken?: string;
  continueSetupUrl: string;
  setupFinishingUrl: string;
  expectImage: boolean;
  platformUrl?: string;
  provisioningApiUrl?: string;
};

export type SetupStatusResult = {
  ready: boolean;
  deviceFound: boolean;
  deviceId?: string;
  online: boolean;
  lastHeartbeatAt?: string;
  status?: string;
  redirectPath?: string;
};

export type ClaimTokenStatusResult = {
  used: boolean;
  usedByDeviceId?: string;
  expectedDeviceId?: string;
  expiresAt?: string;
  expired: boolean;
  failureCode?: string;
  failureMessage?: string;
  failedAt?: string;
};

export type DeviceSettingsDetails = {
  device: Device;
  hardwareHealth?: HardwareHealth;
  maskedToken: string;
  hardwareIdentifiers: { label: string; value: string }[];
  onboardingStatus: string;
  onboardingGuidance: string;
};

export type DeviceTimelineFilters = {
  limit?: number;
  before?: string;
  after?: string;
  eventType?: string;
  severity?: string;
  nodeRole?: string;
  correlationId?: string;
};

function mapCommandStatus(status?: string | null): DeviceCommand["status"] {
  switch (status) {
    case "pending":
    case "sent":
    case "in_progress":
      return status;
    case "failed":
    case "timed_out":
      return "failed";
    case "completed":
      return "completed";
    default:
      return "pending";
  }
}

function mapStatus(
  summary?: Pick<ApiDeviceSummary, "node_summary" | "latest_reading" | "latest_image" | "hardware_health">,
  explicitStatus?: string | null,
): Device["status"] {
  const heartbeatStatus = normalizeFreshnessStatus(summary?.hardware_health?.heartbeat_status);
  if (heartbeatStatus === "offline" || heartbeatStatus === "stale") {
    return heartbeatStatus;
  }
  const healthOverall = normalizeHealthStatus(summary?.hardware_health?.overall_status);
  if (healthOverall === "provisioning" || healthOverall === "error") {
    return "warning";
  }
  if (healthOverall !== "unknown" && healthOverall !== "warning" && healthOverall !== "waiting") {
    return healthOverall;
  }
  const normalizedExplicit = explicitStatus?.toLowerCase();
  if (
    normalizedExplicit === "online" ||
    normalizedExplicit === "offline" ||
    normalizedExplicit === "unknown" ||
    normalizedExplicit === "degraded" ||
    normalizedExplicit === "stale" ||
    normalizedExplicit === "warning" ||
    normalizedExplicit === "waiting"
  ) {
    return normalizedExplicit;
  }
  const overallStatus = summary?.node_summary?.overall_status?.toLowerCase();
  if (overallStatus === "degraded") {
    return "degraded";
  }
  const primaryStatus = summary?.node_summary?.primary?.status?.toLowerCase();
  if (primaryStatus === "online") {
    return "online";
  }
  if (primaryStatus === "offline" || primaryStatus === "error") {
    return "offline";
  }
  if (summary?.latest_reading) {
    return "online";
  }
  return "unknown";
}

function mapReading(reading?: ApiDeviceSummary["latest_reading"] | ApiSensorReading | null) {
  if (!reading) {
    return undefined;
  }
  return {
    timestamp: reading.timestamp,
    temperatureC: reading.temperature ?? undefined,
    humidityPercent: reading.humidity ?? undefined,
    waterTemperatureC: reading.water_temperature_c ?? undefined,
    waterLevelRaw: reading.water_level_raw ?? undefined,
    waterLevelState: reading.water_level_state ?? undefined,
    lightOn: reading.light_on ?? undefined,
    lightIntensityPercent: reading.light_intensity_percent ?? undefined,
    pumpOn: reading.pump_on ?? undefined,
  };
}

function mergeLatestReadingIntoHistory(history: SensorReading[], latestReading?: SensorReading): SensorReading[] {
  if (!latestReading || typeof latestReading.waterTemperatureC !== "number") {
    return history;
  }
  if (history.some((reading) => typeof reading.waterTemperatureC === "number")) {
    return history;
  }

  const matchingIndex = history.findIndex((reading) => reading.timestamp === latestReading.timestamp);
  if (matchingIndex >= 0) {
    const merged = [...history];
    merged[matchingIndex] = { ...merged[matchingIndex], ...latestReading };
    return merged;
  }

  return [...history, latestReading].sort(
    (left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime(),
  );
}

function mapCommand(command: ApiCommandRead): DeviceCommand {
  return {
    id: String(command.id),
    deviceId: String(command.device_id),
    action: mapCommandAction(command.target, command.action),
    createdAt: command.completed_at ?? command.sent_at ?? command.created_at,
    status: mapCommandStatus(command.status),
    detail: command.message ?? undefined,
    updatedAt: command.completed_at ?? command.sent_at ?? undefined,
  };
}

function mapCommandAction(target: ApiCommandRead["target"], action: ApiCommandRead["action"]): DeviceCommand["action"] {
  if ((target === "grow_light" || target === "light") && action === "on") {
    return "light_on";
  }
  if ((target === "grow_light" || target === "light") && action === "off") {
    return "light_off";
  }
  if ((target === "grow_light" || target === "light") && action === "set_intensity") {
    return "light_intensity";
  }
  if (target === "pump" && action === "run") {
    return "pump_run";
  }
  return "capture_image";
}

function mapHardwareNode(node?: ApiHealthNode | null): HardwareNodeHealth | undefined {
  if (!node) {
    return undefined;
  }
  return {
    hardwareDeviceId: node.hardware_device_id,
    nodeRole: node.node_role ?? undefined,
    cameraRole: node.camera_role ?? undefined,
    nodeIndex: node.node_index ?? undefined,
    displayName: node.display_name ?? undefined,
    status: normalizeHealthStatus(node.status),
    healthStatus: normalizeFreshnessStatus(node.health_status),
    hardwareModel: node.hardware_model ?? undefined,
    hardwareVersion: node.hardware_version ?? undefined,
    softwareVersion: node.software_version ?? undefined,
    otaStatus: normalizeOtaStatus(node.ota_status),
    otaAvailableVersion: node.ota_available_version ?? undefined,
    otaTargetVersion: node.ota_target_version ?? undefined,
    otaReleaseId: node.ota_release_id ?? undefined,
    otaProgress: node.ota_progress ?? undefined,
    otaError: node.ota_error ?? undefined,
    otaUpdatedAt: node.ota_updated_at ?? undefined,
    otaLastSuccessAt: node.ota_last_success_at ?? undefined,
    capabilities: node.capabilities ?? undefined,
    lastSeenAt: node.last_seen_at ?? undefined,
    diagnostics: mapHardwareDiagnostics(node.diagnostics),
  };
}

function mapHardwareDiagnostics(diagnostics?: ApiHardwareDiagnostics | null): HardwareDiagnostics | undefined {
  if (!diagnostics) {
    return undefined;
  }
  return {
    schemaVersion: diagnostics.schema_version ?? undefined,
    reportedStatus: diagnostics.reported_status ?? undefined,
    firmwareVersion: diagnostics.firmware_version ?? undefined,
    uptimeSeconds: diagnostics.uptime_seconds ?? undefined,
    wifiRssiDbm: diagnostics.wifi_rssi_dbm ?? undefined,
    rebootReason: diagnostics.reboot_reason ?? undefined,
    provisioningState: diagnostics.provisioning_state ?? undefined,
    lastSensorReadingAt: diagnostics.last_sensor_reading_at ?? undefined,
    lastCameraImageUploadAt: diagnostics.last_camera_image_upload_at ?? undefined,
    lastCommandId: diagnostics.last_command_id ?? undefined,
    lastCommandStatus: diagnostics.last_command_status ?? undefined,
    lastCommandCode: diagnostics.last_command_code ?? undefined,
    lastCommandMessage: diagnostics.last_command_message ?? undefined,
    lastCommandAt: diagnostics.last_command_at ?? undefined,
    errorCounters: diagnostics.error_counters ?? undefined,
    lastErrorCode: diagnostics.last_error_code ?? undefined,
    lastErrorMessage: diagnostics.last_error_message ?? undefined,
    reportedAt: diagnostics.reported_at ?? undefined,
    updatedAt: diagnostics.updated_at ?? undefined,
  };
}

function mapHardwareHealth(health?: ApiDeviceSummary["hardware_health"] | null): HardwareHealth | undefined {
  if (!health) {
    return undefined;
  }
  return {
    overallStatus: normalizeHealthStatus(health.overall_status),
    masterStatus: health.master_status ? normalizeHealthStatus(health.master_status) : undefined,
    masterOnline: health.master_online,
    primary: mapHardwareNode(health.primary),
    cameras: (health.cameras ?? []).map((camera) => mapHardwareNode(camera)!).filter(Boolean),
    lastHeartbeatAt: health.last_heartbeat_at ?? undefined,
    heartbeatStatus: normalizeFreshnessStatus(health.heartbeat_status),
    lastReadingAt: health.last_reading_at ?? undefined,
    readingStatus: normalizeFreshnessStatus(health.reading_status),
    lastImageAt: health.last_image_at ?? undefined,
    imageStatus: normalizeFreshnessStatus(health.image_status),
    cameraStatus: normalizeFreshnessStatus(health.camera_status),
    lastCommand: health.last_command
      ? {
          id: String(health.last_command.id),
          action: mapCommandAction(health.last_command.target, health.last_command.action),
          status: mapCommandStatus(health.last_command.status),
          message: health.last_command.message ?? undefined,
          timestamp: health.last_command.timestamp,
        }
      : undefined,
    friendlyStatus: normalizeFriendlyStatus(health.friendly_status),
    attentionReasons: health.attention_reasons ?? [],
  };
}

function mapTimelineEvent(event: ApiDeviceTimelineEvent): DeviceTimelineEvent {
  return {
    id: String(event.id),
    eventType: event.event_type,
    severity: event.severity,
    occurredAt: event.occurred_at,
    hardwareDeviceId: event.hardware_device_id ?? undefined,
    nodeRole: event.node_role ?? undefined,
    correlationId: event.correlation_id ?? undefined,
    summary: event.summary,
    code: event.code ?? undefined,
    message: event.message ?? undefined,
    data: event.data ?? {},
    createdAt: event.created_at,
  };
}

function buildMockDeviceTimeline(deviceId: string): DeviceTimeline {
  const mockDashboard = mockDashboards[deviceId] ?? mockDashboards["1"];
  const now = new Date();
  const health = mockDashboard.hardwareHealth;
  const latestReading = mockDashboard.device.latestReading;
  const lightOn = mockDashboard.device.currentLightOn ?? latestReading?.lightOn ?? false;
  const lightBrightness = mockDashboard.device.currentLightIntensityPercent ?? latestReading?.lightIntensityPercent ?? 0;
  const primaryHardwareId = health?.primary?.hardwareDeviceId;
  const cameraHardwareId = health?.cameras[0]?.hardwareDeviceId;
  const events: DeviceTimelineEvent[] = [
    {
      id: "mock-timeline-image",
      eventType: "IMAGE_UPLOADED",
      severity: "info",
      occurredAt: new Date(now.getTime() - 60 * 1000).toISOString(),
      hardwareDeviceId: cameraHardwareId,
      nodeRole: "camera",
      correlationId: "mock-image-upload",
      summary: "Image uploaded #1 (manual)",
      data: {
        image_id: 1,
        upload_reason: "manual",
        source_hardware_device_id: cameraHardwareId,
      },
      createdAt: new Date(now.getTime() - 60 * 1000).toISOString(),
    },
    {
      id: "mock-timeline-command",
      eventType: "COMMAND_COMPLETED",
      severity: "info",
      occurredAt: new Date(now.getTime() - 2 * 60 * 1000).toISOString(),
      hardwareDeviceId: primaryHardwareId,
      nodeRole: "master",
      correlationId: "mock-command-light",
      summary: "SET_GROW_LIGHT_BRIGHTNESS completed",
      data: {
        command_id: "mock-command-light",
        command_type: "SET_GROW_LIGHT_BRIGHTNESS",
        status: "completed",
        actuator_state: {
          grow_light: {
            enabled: lightOn,
            brightness_percent: lightBrightness,
          },
        },
      },
      createdAt: new Date(now.getTime() - 2 * 60 * 1000).toISOString(),
    },
    {
      id: "mock-timeline-heartbeat",
      eventType: "HEARTBEAT_RECEIVED",
      severity: "info",
      occurredAt: new Date(now.getTime() - 5 * 60 * 1000).toISOString(),
      hardwareDeviceId: primaryHardwareId,
      nodeRole: "master",
      correlationId: "mock-heartbeat",
      summary: `Heartbeat received${health?.primary?.diagnostics?.wifiRssiDbm ? ` (RSSI ${health.primary.diagnostics.wifiRssiDbm} dBm)` : ""}`,
      data: {
        wifi_rssi_dbm: health?.primary?.diagnostics?.wifiRssiDbm,
        firmware_version: health?.primary?.diagnostics?.firmwareVersion,
        runtime: {
          camera_node_status: health?.cameraStatus,
          last_command_status: health?.lastCommand?.status,
        },
      },
      createdAt: new Date(now.getTime() - 5 * 60 * 1000).toISOString(),
    },
    {
      id: "mock-timeline-diagnostics",
      eventType: "DIAGNOSTICS_RECEIVED",
      severity: health?.friendlyStatus === "needs_attention" ? "warning" : "info",
      occurredAt: new Date(now.getTime() - 10 * 60 * 1000).toISOString(),
      hardwareDeviceId: primaryHardwareId,
      nodeRole: "master",
      summary: health?.friendlyStatus === "needs_attention" ? "Diagnostics received (warning)" : "Diagnostics received (info)",
      data: {
        status: health?.overallStatus,
        attention_reasons: health?.attentionReasons ?? [],
      },
      createdAt: new Date(now.getTime() - 10 * 60 * 1000).toISOString(),
    },
  ];
  return { events };
}

function filterMockTimeline(timeline: DeviceTimeline, filters: DeviceTimelineFilters): DeviceTimeline {
  const events = timeline.events.filter((event) => {
    if (filters.eventType && event.eventType !== filters.eventType) {
      return false;
    }
    if (filters.severity && event.severity !== filters.severity) {
      return false;
    }
    if (filters.nodeRole && event.nodeRole !== filters.nodeRole) {
      return false;
    }
    if (filters.correlationId && event.correlationId !== filters.correlationId) {
      return false;
    }
    if (filters.before && new Date(event.occurredAt).getTime() >= new Date(filters.before).getTime()) {
      return false;
    }
    if (filters.after && new Date(event.occurredAt).getTime() < new Date(filters.after).getTime()) {
      return false;
    }
    return true;
  });
  return { events: events.slice(0, filters.limit ?? 30) };
}

function normalizeFriendlyStatus(status?: string | null): FriendlyHardwareStatus | undefined {
  const normalized = status?.toLowerCase();
  if (normalized === "online" || normalized === "recently_seen" || normalized === "offline" || normalized === "needs_attention") {
    return normalized;
  }
  return undefined;
}

function normalizeHealthStatus(status?: string | null): HardwareNodeHealth["status"] {
  const normalized = status?.toLowerCase();
  if (
    normalized === "online" ||
    normalized === "offline" ||
    normalized === "unknown" ||
    normalized === "degraded" ||
    normalized === "stale" ||
    normalized === "warning" ||
    normalized === "waiting" ||
    normalized === "provisioning" ||
    normalized === "error"
  ) {
    return normalized;
  }
  return "unknown";
}

function normalizeFreshnessStatus(status?: string | null): Device["status"] | undefined {
  const normalized = status?.toLowerCase();
  if (
    normalized === "online" ||
    normalized === "offline" ||
    normalized === "unknown" ||
    normalized === "degraded" ||
    normalized === "stale" ||
    normalized === "warning" ||
    normalized === "waiting"
  ) {
    return normalized;
  }
  return undefined;
}

function normalizeOtaStatus(status?: string | null): HardwareNodeHealth["otaStatus"] | undefined {
  const normalized = status?.toLowerCase();
  if (
    normalized === "idle" ||
    normalized === "available" ||
    normalized === "downloading" ||
    normalized === "installing" ||
    normalized === "success" ||
    normalized === "failed"
  ) {
    return normalized;
  }
  return undefined;
}

export async function listDevices(token?: string): Promise<{ devices: Device[]; usedMock: boolean }> {
  try {
    const apiDevices = await apiRequest<ApiDevice[]>("/api/devices", {}, token);
    return {
      usedMock: false,
      devices: apiDevices.map((device) => {
        const summary = {
          latest_reading: device.latest_reading ?? undefined,
          latest_image: device.latest_image ?? undefined,
          node_summary: device.node_summary ?? undefined,
          hardware_health: device.hardware_health ?? undefined,
        };
        return {
          id: String(device.id),
          name: device.name,
          location: device.location ?? undefined,
          plantType: device.plant_type ?? undefined,
          status: mapStatus(summary, device.status),
          lastSeenAt: device.hardware_health?.last_heartbeat_at ?? device.latest_reading?.timestamp ?? undefined,
          currentLightOn: device.current_light_on ?? undefined,
          currentLightIntensityPercent: device.current_light_intensity_percent ?? undefined,
          currentPumpOn: device.current_pump_on ?? undefined,
          latestReading: mapReading(device.latest_reading),
          latestImage: device.latest_image
            ? {
                id: String(device.latest_image.id),
                url: device.latest_image.content_url,
                capturedAt: device.latest_image.timestamp,
                cameraRole: device.latest_image.camera_role ?? undefined,
                sourceHardwareDeviceId: device.latest_image.source_hardware_device_id ?? undefined,
              }
            : undefined,
        };
      }),
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return { devices: mockDevices, usedMock: true };
  }
}

export async function getDeviceDashboard(
  deviceId: string,
  range: RangeKey = "24h",
  token?: string,
  options?: { includeTimelapse?: boolean },
): Promise<{ dashboard: DeviceDashboard; usedMock: boolean }> {
  try {
    const readingsQuery = buildReadingsQuery(range);
    const includeTimelapse = options?.includeTimelapse ?? true;
    const [summary, history, commands, recentImages, timelapse] = await Promise.all([
      apiRequest<ApiDeviceSummary>(`/api/devices/${deviceId}/summary`, {}, token),
      apiRequest<ApiSensorReading[]>(`/api/devices/${deviceId}/readings?${readingsQuery}`, {}, token),
      apiRequest<ApiCommandRead[]>(`/api/devices/${deviceId}/commands`, {}, token),
      apiRequest<ApiDeviceImage[]>(`/api/devices/${deviceId}/images?limit=6`, {}, token).catch((error) => {
        if (error instanceof ApiError && error.status === 404) {
          return [];
        }
        throw error;
      }),
      includeTimelapse ? getDeviceTimelapse(deviceId, token) : Promise.resolve(undefined),
    ]);
    const latestImage = summary.latest_image
      ? {
          id: String(summary.latest_image.id),
          url: summary.latest_image.content_url,
          capturedAt: summary.latest_image.timestamp,
          cameraRole: summary.latest_image.camera_role ?? undefined,
          sourceHardwareDeviceId: summary.latest_image.source_hardware_device_id ?? undefined,
        }
      : undefined;
    const galleryImages =
      recentImages.length > 0
        ? recentImages.map((image) => ({
            id: String(image.id),
            url: image.content_url,
            capturedAt: image.timestamp,
            cameraRole: image.camera_role ?? undefined,
            sourceHardwareDeviceId: image.source_hardware_device_id ?? undefined,
          }))
        : latestImage
          ? [latestImage]
          : [];
    const latestReading = mapReading(summary.latest_reading);
    const mappedHistory = history
      .map((reading) => mapReading(reading)!)
      .sort((left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime());

    return {
      usedMock: false,
      dashboard: {
        device: {
          id: String(summary.id ?? deviceId),
          name: summary.name,
          location: summary.location ?? undefined,
          plantType: summary.plant_type ?? undefined,
          status: mapStatus(summary),
          lastSeenAt: summary.hardware_health?.last_heartbeat_at ?? summary.latest_reading?.timestamp ?? undefined,
          currentLightOn: summary.current_light_on ?? undefined,
          currentLightIntensityPercent: summary.current_light_intensity_percent ?? undefined,
          currentPumpOn: summary.current_pump_on ?? undefined,
          latestReading,
          latestImage,
        },
        hardwareHealth: mapHardwareHealth(summary.hardware_health),
        recentImages: galleryImages,
        timelapse,
        recentCommands: commands.slice(0, 6).map(mapCommand),
        history: mergeLatestReadingIntoHistory(mappedHistory, latestReading),
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    const mockDashboard = mockDashboards[deviceId] ?? mockDashboards["1"];
    return {
      usedMock: true,
      dashboard: {
        ...mockDashboard,
        history: filterMockHistory(mockDashboard.history, range),
      },
    };
  }
}

export async function getDeviceTimelapse(deviceId: string, token?: string): Promise<DeviceTimelapse | undefined> {
  try {
    const timelapse = await apiRequest<ApiDeviceTimelapse>(
      `/api/devices/${deviceId}/timelapse?days=7&interval_minutes=5&max_frames=168&target_duration_seconds=30`,
      {},
      token,
    );
    return mapTimelapse(timelapse);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return undefined;
    }
    throw error;
  }
}

export async function getDeviceTimeline(
  deviceId: string,
  filters: DeviceTimelineFilters = {},
  token?: string,
): Promise<{ timeline: DeviceTimeline; usedMock: boolean }> {
  try {
    const params = new URLSearchParams({ limit: String(filters.limit ?? 30) });
    if (filters.eventType) {
      params.set("event_type", filters.eventType);
    }
    if (filters.severity) {
      params.set("severity", filters.severity);
    }
    if (filters.nodeRole) {
      params.set("node_role", filters.nodeRole);
    }
    if (filters.correlationId) {
      params.set("correlation_id", filters.correlationId);
    }
    if (filters.before) {
      params.set("before", filters.before);
    }
    if (filters.after) {
      params.set("after", filters.after);
    }

    const payload = await apiRequest<ApiDeviceTimeline>(`/api/devices/${deviceId}/timeline?${params.toString()}`, {}, token);
    return {
      usedMock: false,
      timeline: {
        events: (payload.events ?? []).map(mapTimelineEvent),
        nextBefore: payload.next_before ?? undefined,
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return {
      usedMock: true,
      timeline: filterMockTimeline(buildMockDeviceTimeline(deviceId), filters),
    };
  }
}

function mapTimelapse(timelapse: ApiDeviceTimelapse): DeviceTimelapse {
  return {
    frames: timelapse.frames.map((frame) => ({
      id: String(frame.id),
      url: frame.content_url,
      capturedAt: frame.timestamp,
      cameraRole: frame.camera_role ?? timelapse.camera_role ?? undefined,
      sourceHardwareDeviceId: frame.source_hardware_device_id ?? undefined,
    })),
    frameCount: timelapse.frame_count,
    totalImageCount: timelapse.total_image_count,
    intervalMinutes: timelapse.interval_minutes,
    targetDurationSeconds: timelapse.target_duration_seconds ?? 30,
    playbackFrameMs: timelapse.playback_frame_ms,
    windowStart: timelapse.window_start,
    windowEnd: timelapse.window_end,
  };
}

function buildReadingsQuery(range: RangeKey): string {
  const params = new URLSearchParams({ limit: String(READING_LIMIT_BY_RANGE[range]), order: "newest" });
  const end = new Date();
  params.set("end", end.toISOString());
  const start = rangeStart(range, end);
  if (start) {
    params.set("start", start.toISOString());
  }
  return params.toString();
}

function rangeStart(range: RangeKey, end: Date): Date | null {
  const start = new Date(end);
  switch (range) {
    case "24h":
      start.setHours(start.getHours() - 24);
      return start;
    case "7d":
      start.setDate(start.getDate() - 7);
      return start;
    case "30d":
      start.setDate(start.getDate() - 30);
      return start;
    case "all":
      return null;
  }
}

function filterMockHistory(history: DeviceDashboard["history"], range: RangeKey) {
  const start = rangeStart(range, new Date());
  if (!start) {
    return history;
  }
  return history.filter((reading) => new Date(reading.timestamp).getTime() >= start.getTime());
}

export async function sendDeviceCommand(
  deviceId: string,
  action: DeviceCommand["action"],
  options?: CommandRequestOptions,
  token?: string,
): Promise<{ command: DeviceCommand; usedMock: boolean }> {
  try {
    const request = commandRequestForAction(action, options);
    const created = await apiRequest<ApiCommandEnvelope>(request.path(deviceId), request.init, token);
    return {
      usedMock: false,
      command: {
        id: String(created.command_id ?? `${created.command}-${Date.now()}`),
        deviceId,
        action,
        createdAt: created.created_at ?? new Date().toISOString(),
        status: created.command_status ? mapCommandStatus(created.command_status) : created.queued ? "pending" : "failed",
        detail: created.message,
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return {
      usedMock: true,
      command: {
        id: `mock-${action}-${Date.now()}`,
        deviceId,
        action,
        createdAt: new Date().toISOString(),
        status: "completed",
        detail: "Mock mode command completed immediately.",
      },
    };
  }
}

export async function requestDeviceSetupCode(
  input: {
    serialNumber: string;
    deviceName: string;
    location?: string;
  },
  token?: string,
): Promise<{ handoff: DeviceSetupHandoff; usedMock: boolean }> {
  try {
    const created = await apiRequest<ApiSetupCodeResponse>(
      "/api/devices/setup-code",
      {
        method: "POST",
        body: JSON.stringify({
          serial_number: input.serialNumber,
          device_name: input.deviceName,
          location: input.location ?? null,
        }),
      },
      token,
    );
    return {
      usedMock: false,
      handoff: {
        serialNumber: created.serial_number ?? input.serialNumber,
        setupToken: created.setup_token ?? created.setup_code ?? created.claim_token ?? undefined,
        continueSetupUrl: created.continue_setup_url,
        setupFinishingUrl: created.setup_finishing_url,
        expectImage: created.expect_image,
        platformUrl: created.platform_url ?? undefined,
        provisioningApiUrl: created.provisioning_api_url ?? undefined,
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    const params = new URLSearchParams({
      device_name: input.deviceName,
      location: input.location ?? "",
      expect_image: "1",
    });
    return {
      usedMock: true,
      handoff: {
        serialNumber: input.serialNumber,
        setupToken: "mock-claim-token",
        continueSetupUrl: `http://10.42.0.1:8080/?setup_code=mock-claim-token&sn=${encodeURIComponent(input.serialNumber)}`,
        setupFinishingUrl: `/devices/setup-finishing?${params.toString()}`,
        expectImage: true,
        platformUrl: undefined,
        provisioningApiUrl: undefined,
      },
    };
  }
}

export async function requestDeviceClaimToken(
  input: {
    deviceName: string;
    location?: string;
    deviceIdentity: BleDeviceIdentity;
  },
  token?: string,
): Promise<{ handoff: DeviceSetupHandoff; usedMock: boolean }> {
  try {
    const created = await apiRequest<ApiSetupCodeResponse & { expected_device_id?: string | null }>(
      "/api/devices/claim-token",
      {
        method: "POST",
        body: JSON.stringify({
          device_name: input.deviceName,
          location: input.location ?? null,
          device_identity: {
            source: input.deviceIdentity.source,
            schema_version: input.deviceIdentity.schemaVersion,
            device_id: input.deviceIdentity.deviceId,
            hardware_device_id: input.deviceIdentity.hardwareDeviceId,
            hardware_model: input.deviceIdentity.hardwareModel ?? null,
            hardware_version: input.deviceIdentity.hardwareVersion ?? null,
            software_version: input.deviceIdentity.softwareVersion ?? null,
            node_role: input.deviceIdentity.nodeRole ?? null,
            display_name: input.deviceIdentity.displayName ?? null,
            ble_name: input.deviceIdentity.bleName ?? null,
            serial_number: input.deviceIdentity.serialNumber ?? null,
          },
        }),
      },
      token,
    );
    return {
      usedMock: false,
      handoff: {
        serialNumber: created.serial_number ?? undefined,
        expectedDeviceId: created.expected_device_id ?? input.deviceIdentity.hardwareDeviceId,
        setupToken: created.setup_token ?? created.setup_code ?? created.claim_token ?? undefined,
        continueSetupUrl: created.continue_setup_url,
        setupFinishingUrl: created.setup_finishing_url,
        expectImage: created.expect_image,
        platformUrl: created.platform_url ?? undefined,
        provisioningApiUrl: created.provisioning_api_url ?? undefined,
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    const params = new URLSearchParams({
      device_name: input.deviceName,
      location: input.location ?? "",
      expect_image: "1",
    });
    return {
      usedMock: true,
      handoff: {
        expectedDeviceId: input.deviceIdentity.hardwareDeviceId,
        setupToken: "mock-claim-token",
        continueSetupUrl: `http://10.42.0.1:8080/?setup_code=mock-claim-token&device_id=${encodeURIComponent(input.deviceIdentity.hardwareDeviceId)}`,
        setupFinishingUrl: `/devices/setup-finishing?${params.toString()}`,
        expectImage: true,
        platformUrl: undefined,
        provisioningApiUrl: undefined,
      },
    };
  }
}

export async function getSetupStatus(
  input: {
    deviceName?: string;
    location?: string;
    expectedDeviceId?: string;
    expectImage?: boolean;
  },
  token?: string,
): Promise<{ status: SetupStatusResult; usedMock: boolean }> {
  const params = new URLSearchParams();
  const deviceName = input.deviceName?.trim();
  const location = input.location?.trim();
  const expectedDeviceId = input.expectedDeviceId?.trim();
  if (deviceName) {
    params.set("device_name", deviceName);
  }
  if (location) {
    params.set("location", location);
  }
  if (expectedDeviceId) {
    params.set("expected_device_id", expectedDeviceId);
  }
  params.set("expect_image", input.expectImage === false ? "0" : "1");

  try {
    const response = await apiRequest<ApiSetupStatusResponse>(
      `/api/setup/status?${params.toString()}`,
      {},
      token,
    );
    return {
      usedMock: false,
      status: {
        ready: response.ready,
        deviceFound: response.device_found ?? false,
        deviceId: response.device_id != null ? String(response.device_id) : undefined,
        online: response.online ?? false,
        lastHeartbeatAt: response.last_heartbeat_at ?? undefined,
        status: response.status ?? undefined,
        redirectPath: response.redirect_path ?? undefined,
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return {
      usedMock: true,
      status: {
        ready: true,
        deviceFound: true,
        deviceId: "1",
        online: true,
        status: "online",
        redirectPath: "/devices/1?setup=complete",
      },
    };
  }
}

export async function getClaimTokenStatus(
  input: { setupToken: string },
  token?: string,
): Promise<{ status: ClaimTokenStatusResult; usedMock: boolean }> {
  try {
    const response = await apiRequest<ApiClaimTokenStatusResponse>(
      "/api/setup/claim-token/status",
      {
        method: "POST",
        body: JSON.stringify({ setup_token: input.setupToken }),
      },
      token,
    );
    return {
      usedMock: false,
      status: {
        used: response.used,
        usedByDeviceId: response.used_by_device_id != null ? String(response.used_by_device_id) : undefined,
        expectedDeviceId: response.expected_device_id ?? undefined,
        expiresAt: response.expires_at ?? undefined,
        expired: response.expired ?? false,
        failureCode: response.failure_code ?? undefined,
        failureMessage: response.failure_message ?? undefined,
        failedAt: response.failed_at ?? undefined,
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return {
      usedMock: true,
      status: {
        used: true,
        usedByDeviceId: "1",
        expired: false,
      },
    };
  }
}

export async function deleteDevice(
  deviceId: string,
  token?: string,
): Promise<{ deviceId: string; usedMock: boolean; message: string }> {
  try {
    const response = await apiRequest<ApiDeleteResponse>(
      `/api/devices/${deviceId}`,
      {
        method: "DELETE",
      },
      token,
    );
    return {
      usedMock: false,
      deviceId: String(response.device_id),
      message: response.message,
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return {
      usedMock: true,
      deviceId,
      message: "Mock mode does not persist device removal, but the flow is available for layout testing.",
    };
  }
}

export async function releaseDeviceForTransfer(
  deviceId: string,
  token?: string,
): Promise<{ deviceId: string; usedMock: boolean; message: string; releasedAt?: string }> {
  try {
    const response = await apiRequest<ApiReleaseResponse>(
      `/api/devices/${deviceId}/release`,
      {
        method: "POST",
      },
      token,
    );
    return {
      usedMock: false,
      deviceId: String(response.device_id),
      message: response.message,
      releasedAt: response.released_at ?? undefined,
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return {
      usedMock: true,
      deviceId,
      message: "Mock mode previews release for transfer, but it does not change ownership.",
    };
  }
}

export async function getDeviceSettingsDetails(
  deviceId: string,
  token?: string,
): Promise<{ details: DeviceSettingsDetails; usedMock: boolean }> {
  try {
    const device = await apiRequest<ApiDevice>(`/api/devices/${deviceId}`, {}, token);
    const mappedDevice: Device = {
      id: String(device.id),
      name: device.name,
      location: device.location ?? undefined,
      plantType: device.plant_type ?? undefined,
      status: mapStatus(
        {
          latest_reading: device.latest_reading ?? undefined,
          latest_image: device.latest_image ?? undefined,
          node_summary: device.node_summary ?? undefined,
          hardware_health: device.hardware_health ?? undefined,
        },
        device.status,
      ),
      lastSeenAt: device.hardware_health?.last_heartbeat_at ?? device.latest_reading?.timestamp ?? undefined,
      latestReading: mapReading(device.latest_reading),
      latestImage: device.latest_image
        ? {
            id: String(device.latest_image.id),
            url: device.latest_image.content_url,
            capturedAt: device.latest_image.timestamp,
            cameraRole: device.latest_image.camera_role ?? undefined,
            sourceHardwareDeviceId: device.latest_image.source_hardware_device_id ?? undefined,
          }
        : undefined,
    };
    const hardwareHealth = mapHardwareHealth(device.hardware_health);
    return {
      usedMock: false,
      details: {
        device: mappedDevice,
        hardwareHealth,
        maskedToken: maskToken(device.api_token ?? ""),
        hardwareIdentifiers: collectHardwareIdentifiers(hardwareHealth),
        onboardingStatus: deriveOnboardingStatus(mappedDevice, hardwareHealth),
        onboardingGuidance: deriveOnboardingGuidance(mappedDevice, hardwareHealth),
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    const mockDashboard = mockDashboards[deviceId] ?? mockDashboards["1"];
    const health = mockDashboard.hardwareHealth;
    return {
      usedMock: true,
      details: {
        device: mockDashboard.device,
        hardwareHealth: health,
        maskedToken: "mock...token",
        hardwareIdentifiers: collectHardwareIdentifiers(health),
        onboardingStatus: deriveOnboardingStatus(mockDashboard.device, health),
        onboardingGuidance: deriveOnboardingGuidance(mockDashboard.device, health),
      },
    };
  }
}

export async function updateDeviceSettings(
  deviceId: string,
  input: { name: string; location?: string; plantType?: string },
  token?: string,
): Promise<{ details: DeviceSettingsDetails; usedMock: boolean }> {
  try {
    await apiRequest<ApiDevice>(
      `/api/devices/${deviceId}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          name: input.name,
          location: input.location ?? null,
          plant_type: input.plantType ?? null,
        }),
      },
      token,
    );
    return getDeviceSettingsDetails(deviceId, token);
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    const mockDashboard = mockDashboards[deviceId] ?? mockDashboards["1"];
    return {
      usedMock: true,
      details: {
        device: {
          ...mockDashboard.device,
          name: input.name,
          location: input.location,
          plantType: input.plantType,
        },
        hardwareHealth: mockDashboard.hardwareHealth,
        maskedToken: "mock...token",
        hardwareIdentifiers: collectHardwareIdentifiers(mockDashboard.hardwareHealth),
        onboardingStatus: deriveOnboardingStatus(mockDashboard.device, mockDashboard.hardwareHealth),
        onboardingGuidance: "Mock mode previews the settings form, but it does not persist device changes.",
      },
    };
  }
}

function maskToken(token: string): string {
  if (!token) {
    return "Not issued yet";
  }
  if (token.length <= 10) {
    return token;
  }
  return `${token.slice(0, 4)}…${token.slice(-4)}`;
}

function collectHardwareIdentifiers(health?: HardwareHealth) {
  const identifiers: { label: string; value: string }[] = [];
  if (health?.primary?.hardwareDeviceId) {
    identifiers.push({ label: health.primary.displayName ?? "Primary node", value: health.primary.hardwareDeviceId });
  }
  for (const camera of health?.cameras ?? []) {
    identifiers.push({ label: camera.displayName ?? `Camera ${camera.nodeIndex ?? ""}`.trim(), value: camera.hardwareDeviceId });
  }
  return identifiers;
}

function deriveOnboardingStatus(device: Device, health?: HardwareHealth) {
  if (!health?.primary) {
    return "Provisioning details have not reached the backend yet.";
  }
  if (!device.latestReading) {
    return "Device registered and waiting for its first reading.";
  }
  if (health.cameras.length > 0 && !device.latestImage) {
    return "Master is online. Waiting for the first camera image.";
  }
  return "Device is provisioned and actively reporting.";
}

function deriveOnboardingGuidance(device: Device, health?: HardwareHealth) {
  if (!health?.primary) {
    return "If the device never appears here, put it back into provisioning mode and walk through the setup flow again.";
  }
  if (!device.latestReading) {
    return "Keep power connected and confirm the device joined your home Wi-Fi. The dashboard opens fully after the first reading arrives.";
  }
  if (health.cameras.length > 0 && !device.latestImage) {
    return "The camera node may still be joining. Check the camera power and ESP-NOW logs if images stay missing.";
  }
  return "For a reboot or re-provision, use the physical device controls and watch the serial monitor. No remote recovery action is wired in yet.";
}

function commandRequestForAction(action: DeviceCommand["action"], options?: CommandRequestOptions) {
  switch (action) {
    case "light_on":
      return {
        path: (deviceId: string) => `/api/devices/${deviceId}/commands/light`,
        init: {
          method: "POST",
          body: JSON.stringify({ state: "on" }),
        },
      };
    case "light_off":
      return {
        path: (deviceId: string) => `/api/devices/${deviceId}/commands/light`,
        init: {
          method: "POST",
          body: JSON.stringify({ state: "off" }),
        },
      };
    case "light_intensity":
      return {
        path: (deviceId: string) => `/api/devices/${deviceId}/commands/light`,
        init: {
          method: "POST",
          body: JSON.stringify({ intensity_percent: options?.intensityPercent ?? 0 }),
        },
      };
    case "pump_run":
      return {
        path: (deviceId: string) => `/api/devices/${deviceId}/commands/pump`,
        init: {
          method: "POST",
          body: JSON.stringify({ action: "run", seconds: 5 }),
        },
      };
    case "capture_image":
      const capturePayload: { camera_role?: CameraRole | "all"; camera_node_id?: string } = {};
      if (options?.cameraRole) {
        capturePayload.camera_role = options.cameraRole;
      }
      if (options?.cameraNodeId) {
        capturePayload.camera_node_id = options.cameraNodeId;
      }
      return {
        path: (deviceId: string) => `/api/devices/${deviceId}/commands/capture`,
        init: {
          method: "POST",
          ...(Object.keys(capturePayload).length ? { body: JSON.stringify(capturePayload) } : {}),
        },
      };
  }
}
