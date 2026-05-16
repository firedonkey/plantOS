import { Device, DeviceDashboard, DeviceCommand, HardwareHealth, LatestImage, SensorReading } from "@/types";

const now = new Date();

const latestImage: LatestImage = {
  id: "mock-image-1",
  url: "https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=1200&q=80",
  capturedAt: now.toISOString(),
};

const recentImages: LatestImage[] = [
  latestImage,
  {
    id: "mock-image-2",
    url: "https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07?auto=format&fit=crop&w=1200&q=80",
    capturedAt: new Date(now.getTime() - 45 * 60 * 1000).toISOString(),
  },
  {
    id: "mock-image-3",
    url: "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1200&q=80",
    capturedAt: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
  },
];

const latestReading: SensorReading = {
  timestamp: now.toISOString(),
  temperatureC: 23.1,
  humidityPercent: 53.2,
  waterTemperatureC: 20.4,
  waterLevelRaw: 35200,
  waterLevelState: "ok",
  lightOn: false,
};

const recentCommands: DeviceCommand[] = [
  {
    id: "cmd-light-off",
    deviceId: "1",
    action: "light_off",
    createdAt: new Date(now.getTime() - 15 * 60 * 1000).toISOString(),
    status: "completed",
    detail: "Light turned off successfully.",
  },
  {
    id: "cmd-capture",
    deviceId: "1",
    action: "capture_image",
    createdAt: new Date(now.getTime() - 5 * 60 * 1000).toISOString(),
    status: "pending",
    detail: "Capture is queued for the camera node.",
  },
];

const history: SensorReading[] = Array.from({ length: 8 }, (_, index) => ({
  timestamp: new Date(now.getTime() - index * 60 * 60 * 1000).toISOString(),
  temperatureC: 22.4 + index * 0.1,
  humidityPercent: 52 + index * 0.2,
  waterTemperatureC: 20.1 + index * 0.03,
  waterLevelRaw: 35000 + index * 180,
  waterLevelState: index > 6 ? "low" : "ok",
  lightOn: index % 2 === 0,
})).reverse();

export const mockDevices: Device[] = [
  {
    id: "1",
    name: "Device 1",
    location: "Location 1",
    plantType: "Basil",
    status: "online",
    lastSeenAt: now.toISOString(),
    latestReading,
    latestImage,
  },
];

const hardwareHealth: HardwareHealth = {
  overallStatus: "online",
  masterStatus: "online",
  masterOnline: true,
  primary: {
    hardwareDeviceId: "pl-esp32-mock",
    nodeRole: "master",
    displayName: "Master",
    status: "online",
    softwareVersion: "0.1.0",
    otaStatus: "available",
    otaAvailableVersion: "0.1.1",
    otaTargetVersion: "0.1.1",
    otaProgress: 0,
    capabilities: {
      pump: false,
      moisture_sensor: false,
      water_temperature_sensor: true,
      water_level_sensor: true,
      light_control: true,
      led_driver: "AL8860QMP-13",
    },
    lastSeenAt: new Date(now.getTime() - 15 * 1000).toISOString(),
  },
  cameras: [
    {
      hardwareDeviceId: "pl-cam-mock",
      nodeRole: "camera",
      nodeIndex: 1,
      displayName: "Camera 1",
      status: "online",
      lastSeenAt: new Date(now.getTime() - 45 * 1000).toISOString(),
    },
  ],
  lastHeartbeatAt: new Date(now.getTime() - 15 * 1000).toISOString(),
  lastReadingAt: latestReading.timestamp,
  lastImageAt: latestImage.capturedAt,
  lastCommand: {
    id: "cmd-capture",
    action: "capture_image",
    status: "pending",
    message: "Capture is queued for the camera node.",
    timestamp: new Date(now.getTime() - 5 * 60 * 1000).toISOString(),
  },
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
