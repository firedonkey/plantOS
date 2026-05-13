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
  soilMoisturePercent: 31.2,
  waterLevelPercent: 72,
  lightOn: false,
  pumpOn: false,
};

const recentCommands: DeviceCommand[] = [
  {
    id: "web-cmd-1",
    deviceId: "1",
    action: "pump_run",
    createdAt: new Date(now.getTime() - 3 * 60 * 1000).toISOString(),
    status: "in_progress",
    detail: "Pump is currently running for 5 seconds.",
  },
];

const history: SensorReading[] = Array.from({ length: 12 }, (_, index) => ({
  timestamp: new Date(now.getTime() - index * 2 * 60 * 60 * 1000).toISOString(),
  temperatureC: 22.4 + index * 0.08,
  humidityPercent: 51.5 + index * 0.15,
  soilMoisturePercent: 34 - index * 0.35,
  waterLevelPercent: 80 - index,
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
  overallStatus: "degraded",
  masterStatus: "online",
  masterOnline: true,
  primary: {
    hardwareDeviceId: "pl-esp32-mock",
    nodeRole: "master",
    displayName: "Master",
    status: "online",
    lastSeenAt: new Date(now.getTime() - 20 * 1000).toISOString(),
  },
  cameras: [
    {
      hardwareDeviceId: "pl-cam-mock",
      nodeRole: "camera",
      nodeIndex: 1,
      displayName: "Camera 1",
      status: "offline",
      lastSeenAt: new Date(now.getTime() - 6 * 60 * 1000).toISOString(),
    },
  ],
  lastHeartbeatAt: new Date(now.getTime() - 20 * 1000).toISOString(),
  lastReadingAt: latestReading.timestamp,
  lastImageAt: latestImage.capturedAt,
  lastCommand: {
    id: "web-cmd-1",
    action: "pump_run",
    status: "in_progress",
    message: "Pump is currently running for 5 seconds.",
    timestamp: new Date(now.getTime() - 3 * 60 * 1000).toISOString(),
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
