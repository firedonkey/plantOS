export type DeviceConnectionState = "online" | "offline" | "unknown" | "degraded" | "stale" | "warning" | "waiting";

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
  healthStatus?: DeviceConnectionState;
  lastSeenAt?: string;
};

export type SensorReading = {
  timestamp: string;
  temperatureC?: number;
  humidityPercent?: number;
  soilMoisturePercent?: number;
  waterLevelPercent?: number;
  lightOn?: boolean;
  pumpOn?: boolean;
};

export type DeviceCommandAction = "light_on" | "light_off" | "pump_run" | "capture_image";

export type DeviceCommandStatus = "pending" | "sent" | "in_progress" | "completed" | "failed";

export type DeviceCommand = {
  id: string;
  deviceId: string;
  action: DeviceCommandAction;
  createdAt: string;
  status: DeviceCommandStatus;
  detail?: string;
  updatedAt?: string;
};

export type HardwareCommandHealth = {
  id: string;
  action: DeviceCommandAction;
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
  heartbeatStatus?: DeviceConnectionState;
  lastReadingAt?: string;
  readingStatus?: DeviceConnectionState;
  lastImageAt?: string;
  imageStatus?: DeviceConnectionState;
  cameraStatus?: DeviceConnectionState;
  lastCommand?: HardwareCommandHealth;
};

export type LatestImage = {
  id: string;
  url: string;
  capturedAt: string;
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
  mode: "mock" | "api" | "production";
  expiresAt?: string;
  refreshToken?: string;
};
