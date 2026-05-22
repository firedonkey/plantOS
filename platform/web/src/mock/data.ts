import { Device, DeviceDashboard, DeviceCommand, HardwareHealth, LatestImage, SensorReading } from "@/types";

const now = new Date();

const latestImage: LatestImage = {
  id: "web-mock-image-1",
  url: "https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=1200&q=80",
  capturedAt: now.toISOString(),
};

const recentImages: LatestImage[] = [
  latestImage,
  {
    id: "web-mock-image-2",
    url: "https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07?auto=format&fit=crop&w=1200&q=80",
    capturedAt: new Date(now.getTime() - 45 * 60 * 1000).toISOString(),
  },
  {
    id: "web-mock-image-3",
    url: "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1200&q=80",
    capturedAt: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
  },
];

const latestReading: SensorReading = {
  timestamp: now.toISOString(),
  temperatureC: 23.4,
  humidityPercent: 52.8,
  waterTemperatureC: 20.4,
  waterLevelRaw: 35200,
  waterLevelState: "ok",
  lightOn: false,
  lightIntensityPercent: 0,
};

const recentCommands: DeviceCommand[] = [
  {
    id: "web-cmd-1",
    deviceId: "1",
    action: "capture_image",
    createdAt: new Date(now.getTime() - 3 * 60 * 1000).toISOString(),
    status: "completed",
    detail: "Image captured and uploaded.",
  },
];

const history: SensorReading[] = Array.from({ length: 12 }, (_, index) => ({
  timestamp: new Date(now.getTime() - index * 2 * 60 * 60 * 1000).toISOString(),
  temperatureC: 22.4 + index * 0.08,
  humidityPercent: 51.5 + index * 0.15,
  waterTemperatureC: 20.1 + index * 0.03,
  waterLevelRaw: 35000 + index * 180,
  waterLevelState: index > 6 ? "low" : "ok",
  lightOn: index % 2 === 0,
  lightIntensityPercent: index % 2 === 0 ? 60 : 0,
})).reverse();

export const mockDevices: Device[] = [
  {
    id: "1",
    name: "Device 1",
    location: "Location 1",
    plantType: "Basil",
    status: "online",
    lastSeenAt: now.toISOString(),
    currentLightOn: latestReading.lightOn,
    currentLightIntensityPercent: latestReading.lightIntensityPercent,
    latestReading,
    latestImage,
  },
];

const hardwareHealth: HardwareHealth = {
  overallStatus: "degraded",
  masterStatus: "online",
  masterOnline: true,
  primary: {
    hardwareDeviceId: "pl-esp32-mock",
    nodeRole: "master",
    displayName: "Master",
    status: "online",
    capabilities: {
      light_control: true,
      light_intensity_control: true,
      light_control_modes: ["on_off", "intensity"],
      water_temperature_sensor: true,
      water_level_sensor: true,
    },
    diagnostics: {
      schemaVersion: 1,
      reportedStatus: "online",
      firmwareVersion: "0.2.4",
      uptimeSeconds: 3661,
      wifiRssiDbm: -67,
      rebootReason: "power_on",
      provisioningState: "normal",
      lastSensorReadingAt: latestReading.timestamp,
      lastCommandId: 12,
      lastCommandStatus: "completed",
      lastCommandCode: "ok",
      lastCommandMessage: "Image captured and uploaded.",
      lastCommandAt: new Date(now.getTime() - 3 * 60 * 1000).toISOString(),
      errorCounters: {
        wifi_reconnects: 1,
      },
      reportedAt: new Date(now.getTime() - 20 * 1000).toISOString(),
      updatedAt: new Date(now.getTime() - 20 * 1000).toISOString(),
    },
    lastSeenAt: new Date(now.getTime() - 20 * 1000).toISOString(),
  },
  cameras: [
    {
      hardwareDeviceId: "pl-cam-mock",
      nodeRole: "camera",
      nodeIndex: 1,
      displayName: "Camera 1",
      status: "offline",
      diagnostics: {
        schemaVersion: 1,
        reportedStatus: "offline",
        firmwareVersion: "0.2.3",
        uptimeSeconds: 822,
        wifiRssiDbm: -84,
        rebootReason: "watchdog_reset",
        provisioningState: "normal",
        lastCameraImageUploadAt: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
        errorCounters: {
          upload_failures: 2,
        },
        lastErrorCode: "upload_failed",
        lastErrorMessage: "Last camera upload did not reach the backend.",
        reportedAt: new Date(now.getTime() - 6 * 60 * 1000).toISOString(),
        updatedAt: new Date(now.getTime() - 6 * 60 * 1000).toISOString(),
      },
      lastSeenAt: new Date(now.getTime() - 6 * 60 * 1000).toISOString(),
    },
  ],
  lastHeartbeatAt: new Date(now.getTime() - 20 * 1000).toISOString(),
  lastReadingAt: latestReading.timestamp,
  lastImageAt: latestImage.capturedAt,
  lastCommand: {
    id: "web-cmd-1",
    action: "capture_image",
    status: "completed",
    message: "Image captured and uploaded.",
    timestamp: new Date(now.getTime() - 3 * 60 * 1000).toISOString(),
  },
  friendlyStatus: "needs_attention",
  attentionReasons: ["camera_offline", "upload_failures"],
};

export const mockDashboards: Record<string, DeviceDashboard> = {
  "1": {
    device: mockDevices[0],
    hardwareHealth,
    recentImages,
    recentCommands,
    history,
  },
};
