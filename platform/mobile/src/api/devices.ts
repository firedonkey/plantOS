import { ApiError, apiRequest, shouldUseMockFallback } from "./client";
import { mockDashboards, mockDevices } from "@/mock/data";
import { Device, DeviceCommand, DeviceDashboard, HardwareHealth, HardwareNodeHealth } from "@/types";
import type { RangeKey } from "@/components/ReadingTrendSection";
import type { BleDeviceIdentity } from "@/ble/bleProvisioning";

type ApiDevice = {
  id: number;
  name: string;
  location?: string | null;
  plant_type?: string | null;
  api_token?: string | null;
  status?: string | null;
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
  latest_reading?: {
    timestamp: string;
    moisture?: number | null;
    temperature?: number | null;
    humidity?: number | null;
    water_temperature_c?: number | null;
    water_level_raw?: number | null;
    water_level_state?: string | null;
    light_on?: boolean | null;
    pump_on?: boolean | null;
  } | null;
  latest_image?: {
    id: number;
    content_url: string;
    timestamp: string;
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
  } | null;
};

type ApiHealthNode = {
  hardware_device_id: string;
  node_role?: string | null;
  node_index?: number | null;
  display_name?: string | null;
  status: string;
  health_status?: string | null;
  capabilities?: Record<string, unknown> | null;
  last_seen_at?: string | null;
};

type ApiHealthCommand = {
  id: number;
  target: "light" | "pump" | "camera";
  action: "on" | "off" | "run" | "capture";
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
  pump_on?: boolean | null;
};

type ApiCommandRead = {
  id: number;
  device_id: number;
  target: "light" | "pump" | "camera";
  action: "on" | "off" | "run" | "capture";
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
  command: "light" | "pump" | "capture";
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
};

export type DeviceSettingsDetails = {
  device: Device;
  hardwareHealth?: HardwareHealth;
  maskedToken: string;
  hardwareIdentifiers: { label: string; value: string }[];
  onboardingStatus: string;
  onboardingGuidance: string;
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
    pumpOn: reading.pump_on ?? undefined,
  };
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
  if (target === "light" && action === "on") {
    return "light_on";
  }
  if (target === "light" && action === "off") {
    return "light_off";
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
    nodeIndex: node.node_index ?? undefined,
    displayName: node.display_name ?? undefined,
    status: normalizeHealthStatus(node.status),
    healthStatus: normalizeFreshnessStatus(node.health_status),
    capabilities: node.capabilities ?? undefined,
    lastSeenAt: node.last_seen_at ?? undefined,
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
  };
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
          latestReading: mapReading(device.latest_reading),
          latestImage: device.latest_image
            ? {
                id: String(device.latest_image.id),
                url: device.latest_image.content_url,
                capturedAt: device.latest_image.timestamp,
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
): Promise<{ dashboard: DeviceDashboard; usedMock: boolean }> {
  try {
    const readingsQuery = buildReadingsQuery(range);
    const [summary, history, commands, recentImages] = await Promise.all([
      apiRequest<ApiDeviceSummary>(`/api/devices/${deviceId}/summary`, {}, token),
      apiRequest<ApiSensorReading[]>(`/api/devices/${deviceId}/readings?${readingsQuery}`, {}, token),
      apiRequest<ApiCommandRead[]>(`/api/devices/${deviceId}/commands`, {}, token),
      apiRequest<ApiDeviceImage[]>(`/api/devices/${deviceId}/images?limit=6`, {}, token).catch((error) => {
        if (error instanceof ApiError && error.status === 404) {
          return [];
        }
        throw error;
      }),
    ]);
    const latestImage = summary.latest_image
      ? {
          id: String(summary.latest_image.id),
          url: summary.latest_image.content_url,
          capturedAt: summary.latest_image.timestamp,
        }
      : undefined;
    const galleryImages =
      recentImages.length > 0
        ? recentImages.map((image) => ({
            id: String(image.id),
            url: image.content_url,
            capturedAt: image.timestamp,
          }))
        : latestImage
          ? [latestImage]
          : [];
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
          latestReading: mapReading(summary.latest_reading),
          latestImage,
        },
        hardwareHealth: mapHardwareHealth(summary.hardware_health),
        recentImages: galleryImages,
        recentCommands: commands.slice(0, 6).map(mapCommand),
        history: history.map((reading) => mapReading(reading)!),
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

function buildReadingsQuery(range: RangeKey): string {
  const params = new URLSearchParams({ limit: "500", order: "oldest" });
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
  token?: string,
): Promise<{ command: DeviceCommand; usedMock: boolean }> {
  try {
    const request = commandRequestForAction(action);
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

function commandRequestForAction(action: DeviceCommand["action"]) {
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
    case "pump_run":
      return {
        path: (deviceId: string) => `/api/devices/${deviceId}/commands/pump`,
        init: {
          method: "POST",
          body: JSON.stringify({ action: "run", seconds: 5 }),
        },
      };
    case "capture_image":
      return {
        path: (deviceId: string) => `/api/devices/${deviceId}/commands/capture`,
        init: {
          method: "POST",
        },
      };
  }
}
