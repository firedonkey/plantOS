export type DeviceConnectionState = "online" | "offline" | "unknown" | "degraded" | "stale" | "warning" | "waiting";
export type FriendlyHardwareStatus = "online" | "recently_seen" | "offline" | "needs_attention";

export type HardwareDiagnostics = {
  schemaVersion?: number;
  reportedStatus?: string;
  firmwareVersion?: string;
  uptimeSeconds?: number;
  wifiRssiDbm?: number;
  rebootReason?: string;
  provisioningState?: string;
  lastSensorReadingAt?: string;
  lastCameraImageUploadAt?: string;
  lastCommandId?: number;
  lastCommandStatus?: string;
  lastCommandCode?: string;
  lastCommandMessage?: string;
  lastCommandAt?: string;
  errorCounters?: Record<string, number>;
  lastErrorCode?: string;
  lastErrorMessage?: string;
  reportedAt?: string;
  updatedAt?: string;
};

export type SensorReading = {
  timestamp: string;
  temperatureC?: number;
  humidityPercent?: number;
  soilMoisturePercent?: number;
  waterTemperatureC?: number;
  waterLevelRaw?: number;
  waterLevelState?: string;
  lightOn?: boolean;
  lightIntensityPercent?: number;
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
  capabilities?: Record<string, unknown>;
  diagnostics?: HardwareDiagnostics;
};

export type DeviceCommandStatus = "pending" | "sent" | "in_progress" | "completed" | "failed";

export type DeviceCommand = {
  id: string;
  deviceId: string;
  action: "light_on" | "light_off" | "light_intensity" | "pump_run" | "capture_image";
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
  heartbeatStatus?: DeviceConnectionState;
  lastReadingAt?: string;
  readingStatus?: DeviceConnectionState;
  lastImageAt?: string;
  imageStatus?: DeviceConnectionState;
  cameraStatus?: DeviceConnectionState;
  lastCommand?: HardwareCommandHealth;
  friendlyStatus?: FriendlyHardwareStatus;
  attentionReasons?: string[];
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
};

export type CurrentUserProfile = {
  authenticated: boolean;
  id?: string;
  email: string;
  name?: string;
  avatarUrl?: string;
};

export type DeviceDiagnosticSnapshot = {
  hardwareDeviceId: string;
  deviceId: string;
  nodeRole?: string;
  schemaVersion: number;
  reportedStatus?: string;
  firmwareVersion?: string;
  uptimeSeconds?: number;
  wifiRssiDbm?: number;
  rebootReason?: string;
  provisioningState?: string;
  lastSensorReadingAt?: string;
  lastCameraImageUploadAt?: string;
  lastCommandId?: number;
  lastCommandStatus?: string;
  lastCommandCode?: string;
  lastCommandMessage?: string;
  lastCommandAt?: string;
  errorCounters: Record<string, number>;
  lastErrorCode?: string;
  lastErrorMessage?: string;
  reportedAt: string;
  updatedAt: string;
};

export type DeviceDiagnosticEvent = {
  id: string;
  deviceId: string;
  hardwareDeviceId?: string;
  eventType: string;
  severity: string;
  code?: string;
  message?: string;
  count?: number;
  metadata: Record<string, unknown>;
  occurredAt: string;
  createdAt: string;
};

export type DeviceDiagnostics = {
  snapshots: DeviceDiagnosticSnapshot[];
  recentEvents: DeviceDiagnosticEvent[];
};
