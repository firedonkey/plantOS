export type DeviceConnectionState = "online" | "offline" | "unknown" | "degraded" | "stale" | "warning" | "waiting";
export type FirmwareOtaStatus = "idle" | "available" | "downloading" | "installing" | "success" | "failed";
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

export type Device = {
  id: string;
  name: string;
  location?: string;
  plantType?: string;
  status: DeviceConnectionState;
  lastSeenAt?: string;
  currentLightOn?: boolean;
  currentLightIntensityPercent?: number;
  currentPumpOn?: boolean;
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
  hardwareModel?: string;
  hardwareVersion?: string;
  softwareVersion?: string;
  otaStatus?: FirmwareOtaStatus;
  otaAvailableVersion?: string;
  otaTargetVersion?: string;
  otaReleaseId?: string;
  otaProgress?: number;
  otaError?: string;
  otaUpdatedAt?: string;
  otaLastSuccessAt?: string;
  capabilities?: Record<string, unknown>;
  lastSeenAt?: string;
  diagnostics?: HardwareDiagnostics;
};

export type SensorReading = {
  timestamp: string;
  temperatureC?: number;
  humidityPercent?: number;
  waterTemperatureC?: number;
  waterLevelRaw?: number;
  waterLevelState?: string;
  lightOn?: boolean;
  lightIntensityPercent?: number;
  pumpOn?: boolean;
};

export type DeviceCommandAction = "light_on" | "light_off" | "light_intensity" | "pump_run" | "capture_image";

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
  friendlyStatus?: FriendlyHardwareStatus;
  attentionReasons?: string[];
};

export type LatestImage = {
  id: string;
  url: string;
  capturedAt: string;
};

export type TimelapseFrame = LatestImage;

export type DeviceTimelapse = {
  frames: TimelapseFrame[];
  frameCount: number;
  totalImageCount: number;
  intervalMinutes: number;
  playbackFrameMs: number;
  windowStart: string;
  windowEnd: string;
};

export type DeviceDashboard = {
  device: Device;
  hardwareHealth?: HardwareHealth;
  recentImages: LatestImage[];
  timelapse?: DeviceTimelapse;
  recentCommands: DeviceCommand[];
  history: SensorReading[];
};

export type DeviceTimelineEvent = {
  id: string;
  eventType: string;
  severity: string;
  occurredAt: string;
  hardwareDeviceId?: string;
  nodeRole?: string;
  correlationId?: string;
  summary: string;
  code?: string;
  message?: string;
  data: Record<string, unknown>;
  createdAt: string;
};

export type DeviceTimeline = {
  events: DeviceTimelineEvent[];
  nextBefore?: string;
};

export type AuthSession = {
  token: string;
  email: string;
  mode: "mock" | "api" | "production";
  expiresAt?: string;
  refreshToken?: string;
};
