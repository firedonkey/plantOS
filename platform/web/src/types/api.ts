import type { CameraRole } from "@/contracts/deviceProtocol";

export type DeviceConnectionState = "online" | "offline" | "unknown" | "degraded" | "stale" | "warning" | "waiting";
export type FriendlyHardwareStatus = "online" | "recently_seen" | "offline" | "needs_attention";

export type { CameraRole };

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
  cameraRole?: CameraRole;
  sourceHardwareDeviceId?: string;
};

export type TimelapseFrame = LatestImage;

export type DeviceTimelapse = {
  frames: TimelapseFrame[];
  frameCount: number;
  totalImageCount: number;
  intervalMinutes: number;
  targetDurationSeconds: number;
  playbackFrameMs: number;
  windowStart: string;
  windowEnd: string;
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
  cameraRole?: CameraRole;
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
  action:
    | "light_on"
    | "light_off"
    | "light_intensity"
    | "light_red_intensity"
    | "light_white_intensity"
    | "ambient_belt_color"
    | "ambient_belt_off"
    | "pump_run"
    | "capture_image";
  cameraRole?: CameraRole | "all";
  cameraNodeId?: string;
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
  cameraImages?: Partial<Record<CameraRole, LatestImage>>;
  recentImages: LatestImage[];
  timelapse?: DeviceTimelapse;
  recentCommands: DeviceCommand[];
  history: SensorReading[];
};

export type AuthSession = {
  token: string;
  email: string;
  mode: "mock" | "api" | "production";
  expiresAt?: string;
  isAdmin?: boolean;
  isDemo?: boolean;
};

export type CurrentUserProfile = {
  authenticated: boolean;
  id?: string;
  email: string;
  name?: string;
  avatarUrl?: string;
  isAdmin?: boolean;
  isDemo?: boolean;
};

export type AdminSummary = {
  users: number;
  activeUsers: number;
  devices: number;
  activeDevices: number;
  releasedDevices: number;
  archivedDevices: number;
  hardwareNodes: number;
  staleNodes: number;
  recentWarningEvents: number;
  firmwareReleases: number;
};

export type AdminUser = {
  id: string;
  email: string;
  name?: string;
  createdAt: string;
  deviceCount: number;
  activeDeviceCount: number;
  lastSeenAt?: string;
  recentWarningEventCount: number;
  recentCommandCount: number;
  lastCommandAt?: string;
};

export type AdminNode = {
  hardwareDeviceId: string;
  nodeRole?: string;
  displayName?: string;
  hardwareModel?: string;
  softwareVersion?: string;
  status: string;
  lastSeenAt?: string;
  otaStatus?: string;
  otaTargetVersion?: string;
  otaError?: string;
};

export type AdminDevice = {
  id: string;
  name: string;
  ownerEmail: string;
  location?: string;
  plantType?: string;
  status: string;
  createdAt: string;
  releasedAt?: string;
  archivedAt?: string;
  latestReadingAt?: string;
  latestImageAt?: string;
  nodeCount: number;
  nodes: AdminNode[];
  lastErrorCode?: string;
  lastErrorMessage?: string;
  recentEventCount: number;
};

export type AdminEvent = {
  id: string;
  deviceId: string;
  deviceName: string;
  ownerEmail: string;
  hardwareDeviceId?: string;
  eventType: string;
  severity: string;
  code?: string;
  message?: string;
  occurredAt: string;
};

export type AdminCommand = {
  id: string;
  deviceId: string;
  deviceName: string;
  ownerEmail: string;
  target: string;
  action: string;
  value?: string;
  status: string;
  message?: string;
  createdAt: string;
  sentAt?: string;
  completedAt?: string;
};

export type AdminFirmwareRelease = {
  releaseId: string;
  nodeRole: string;
  hardwareModel?: string;
  version: string;
  status: string;
  publishedAt?: string;
};

export type AdminDiagnostics = {
  generatedAt: string;
  requestedBy: {
    id: string;
    email: string;
  };
  summary: AdminSummary;
  users: AdminUser[];
  devices: AdminDevice[];
  recentEvents: AdminEvent[];
  recentCommands: AdminCommand[];
  firmwareReleases: AdminFirmwareRelease[];
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
