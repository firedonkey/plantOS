import { apiRequest } from "./client";
import { mockDashboards, mockDevices } from "@/mock/data";
import { Device, DeviceCommand, DeviceDashboard } from "@/types";

type ApiDevice = {
  id: number;
  name: string;
  location?: string | null;
};

export async function listDevices(token?: string): Promise<{ devices: Device[]; usedMock: boolean }> {
  try {
    const apiDevices = await apiRequest<ApiDevice[]>("/api/devices", {}, token);
    return {
      usedMock: false,
      devices: apiDevices.map((device) => ({
        id: String(device.id),
        name: device.name,
        location: device.location ?? undefined,
        status: "unknown",
      })),
    };
  } catch {
    return { devices: mockDevices, usedMock: true };
  }
}

export async function getDeviceDashboard(
  deviceId: string,
  token?: string,
): Promise<{ dashboard: DeviceDashboard; usedMock: boolean }> {
  try {
    const summary = await apiRequest<any>(`/api/devices/${deviceId}`, {}, token);
    const mock = mockDashboards[deviceId] ?? mockDashboards["1"];
    return {
      usedMock: true,
      dashboard: {
        ...mock,
        device: {
          ...mock.device,
          id: String(summary.id),
          name: summary.name,
          location: summary.location ?? mock.device.location,
        },
      },
    };
  } catch {
    return {
      usedMock: true,
      dashboard: mockDashboards[deviceId] ?? mockDashboards["1"],
    };
  }
}

export async function sendDeviceCommand(
  deviceId: string,
  action: DeviceCommand["action"],
  token?: string,
): Promise<{ command: DeviceCommand; usedMock: boolean }> {
  try {
    const created = await apiRequest<any>(
      `/api/devices/${deviceId}/commands`,
      {
        method: "POST",
        body: JSON.stringify({
          action,
        }),
      },
      token,
    );
    return {
      usedMock: false,
      command: {
        id: String(created.id),
        deviceId,
        action,
        createdAt: created.created_at ?? new Date().toISOString(),
        status: created.status ?? "pending",
      },
    };
  } catch {
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
