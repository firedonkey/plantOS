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
  soilMoisturePercent: 29.1,
  waterLevelPercent: 74,
  lightOn: false,
  pumpOn: false,
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
    id: "cmd-pump",
    deviceId: "1",
    action: "pump_run",
    createdAt: new Date(now.getTime() - 5 * 60 * 1000).toISOString(),
    status: "pending",
    detail: "Pump run is queued for the device.",
  },
];

const history: SensorReading[] = Array.from({ length: 8 }, (_, index) => ({
  timestamp: new Date(now.getTime() - index * 60 * 60 * 1000).toISOString(),
  temperatureC: 22.4 + index * 0.1,
  humidityPercent: 52 + index * 0.2,
  soilMoisturePercent: 31 - index * 0.3,
  waterLevelPercent: 78 - index,
  lightOn: index % 2 === 0,
  pumpOn: false,
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
    id: "cmd-pump",
    action: "pump_run",
    status: "pending",
    message: "Pump run is queued for the device.",
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
