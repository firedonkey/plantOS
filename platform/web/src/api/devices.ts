import { apiRequest, shouldUseMockFallback } from "./client";
import { mockDashboards, mockDevices } from "@/mock/data";
import { Device, DeviceCommand, DeviceDashboard } from "@/types";

type ApiDevice = {
  id: number;
  name: string;
  location?: string | null;
  plant_type?: string | null;
  status?: string | null;
  latest_reading?: ApiDeviceSummary["latest_reading"] | null;
  latest_image?: ApiDeviceSummary["latest_image"] | null;
  node_summary?: ApiDeviceSummary["node_summary"] | null;
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
    light_on?: boolean | null;
    pump_on?: boolean | null;
  } | null;
  latest_image?: {
    id: number;
    content_url: string;
    timestamp: string;
  } | null;
  node_summary?: {
    primary?: {
      status?: string | null;
    } | null;
  } | null;
};

type ApiSensorReading = {
  timestamp: string;
  moisture?: number | null;
  temperature?: number | null;
  humidity?: number | null;
  light_on?: boolean | null;
  pump_on?: boolean | null;
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

function mapCommandStatus(status?: string | null): DeviceCommand["status"] {
  switch (status) {
    case "pending":
    case "sent":
    case "failed":
      return status;
    case "completed":
      return "acknowledged";
    default:
      return "pending";
  }
}

function mapStatus(summary?: Pick<ApiDeviceSummary, "node_summary" | "latest_reading">, explicitStatus?: string | null): Device["status"] {
  const normalizedExplicit = explicitStatus?.toLowerCase();
  if (normalizedExplicit === "online" || normalizedExplicit === "offline" || normalizedExplicit === "unknown") {
    return normalizedExplicit;
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
    soilMoisturePercent: reading.moisture ?? undefined,
    lightOn: reading.light_on ?? undefined,
    pumpOn: reading.pump_on ?? undefined,
  };
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
        };
        return {
          id: String(device.id),
          name: device.name,
          location: device.location ?? undefined,
          plantType: device.plant_type ?? undefined,
          status: mapStatus(summary, device.status),
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
  token?: string,
): Promise<{ dashboard: DeviceDashboard; usedMock: boolean }> {
  try {
    const [summary, history] = await Promise.all([
      apiRequest<ApiDeviceSummary>(`/api/devices/${deviceId}/summary`, {}, token),
      apiRequest<ApiSensorReading[]>(`/api/devices/${deviceId}/readings?limit=50`, {}, token),
    ]);
    return {
      usedMock: false,
      dashboard: {
        device: {
          id: String(summary.id ?? deviceId),
          name: summary.name,
          location: summary.location ?? undefined,
          plantType: summary.plant_type ?? undefined,
          status: mapStatus(summary),
          latestReading: mapReading(summary.latest_reading),
          latestImage: summary.latest_image
            ? {
                id: String(summary.latest_image.id),
                url: summary.latest_image.content_url,
                capturedAt: summary.latest_image.timestamp,
              }
            : undefined,
        },
        recentCommands: [],
        history: history.map((reading) => mapReading(reading)!),
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return {
      dashboard: mockDashboards[deviceId] ?? mockDashboards["1"],
      usedMock: true,
    };
  }
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
        status: "acknowledged",
      },
    };
  }
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
