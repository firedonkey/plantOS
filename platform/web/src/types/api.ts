export type DeviceConnectionState = "online" | "offline" | "unknown";

export type SensorReading = {
  timestamp: string;
  temperatureC?: number;
  humidityPercent?: number;
  soilMoisturePercent?: number;
  waterLevelPercent?: number;
  lightOn?: boolean;
  pumpOn?: boolean;
};

export type LatestImage = {
  id: string;
  url: string;
  capturedAt: string;
};

export type Device = {
  id: string;
  name: string;
  location?: string;
  plantType?: string;
  status: DeviceConnectionState;
  lastSeenAt?: string;
  latestReading?: SensorReading;
  latestImage?: LatestImage;
};

export type DeviceCommand = {
  id: string;
  deviceId: string;
  action: "light_on" | "light_off" | "pump_run" | "capture_image";
  createdAt: string;
  status: "pending" | "sent" | "acknowledged" | "failed";
};

export type DeviceDashboard = {
  device: Device;
  recentImages: LatestImage[];
  recentCommands: DeviceCommand[];
  history: SensorReading[];
};

export type AuthSession = {
  token: string;
  email: string;
  mode: "mock" | "api";
};
