export type DeviceConnectionState = "online" | "offline" | "unknown" | "degraded";

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

export type HardwareNodeHealth = {
  hardwareDeviceId: string;
  nodeRole?: string;
  nodeIndex?: number;
  displayName?: string;
  status: DeviceConnectionState | "provisioning" | "error";
  lastSeenAt?: string;
};

export type DeviceCommandStatus = "pending" | "sent" | "in_progress" | "completed" | "failed";

export type DeviceCommand = {
  id: string;
  deviceId: string;
  action: "light_on" | "light_off" | "pump_run" | "capture_image";
  createdAt: string;
  status: DeviceCommandStatus;
  detail?: string;
  updatedAt?: string;
};

export type HardwareCommandHealth = {
  id: string;
  action: DeviceCommand["action"];
  status: DeviceCommandStatus;
  message?: string;
  timestamp: string;
};

export type HardwareHealth = {
  overallStatus: DeviceConnectionState | "provisioning" | "error";
  masterStatus?: DeviceConnectionState | "provisioning" | "error";
  masterOnline: boolean;
  primary?: HardwareNodeHealth;
  cameras: HardwareNodeHealth[];
  lastHeartbeatAt?: string;
  lastReadingAt?: string;
  lastImageAt?: string;
  lastCommand?: HardwareCommandHealth;
};

export type DeviceDashboard = {
  device: Device;
  hardwareHealth?: HardwareHealth;
  recentImages: LatestImage[];
  recentCommands: DeviceCommand[];
  history: SensorReading[];
};

export type AuthSession = {
  token: string;
  email: string;
  mode: "mock" | "api";
};
