export const PLANTLAB_SCHEMA_VERSION = "1.0" as const;

export type NodeRole = "master" | "camera" | "sensor" | "actuator";

export type CameraRole = "top" | "side";

export type MessageType = "HEARTBEAT" | "DIAGNOSTICS" | "COMMAND" | "COMMAND_RESULT" | "OTA_STATUS" | "IMAGE_UPLOAD";

export type DeviceStatus = "online" | "degraded" | "offline" | "provisioning" | "updating" | "error";

export type DiagnosticSeverity = "info" | "warning" | "critical";

export type EventType =
  | "DEVICE_ONLINE"
  | "DEVICE_OFFLINE"
  | "HEARTBEAT_RECEIVED"
  | "DIAGNOSTICS_RECEIVED"
  | "SENSOR_ERROR"
  | "ACTUATOR_STATE_CHANGED"
  | "CAMERA_NODE_CONNECTED"
  | "CAMERA_NODE_DISCONNECTED"
  | "OTA_STATE_CHANGED"
  | "DEVICE_HEALTH_CHANGED"
  | "WIFI_SIGNAL_DEGRADED"
  | "WIFI_SIGNAL_RECOVERED"
  | "OTA_AVAILABLE"
  | "OTA_STARTED"
  | "OTA_PROGRESS"
  | "OTA_PREPARING"
  | "OTA_DOWNLOADING"
  | "OTA_VALIDATING"
  | "OTA_INSTALLING"
  | "OTA_REBOOTING"
  | "OTA_SUCCESS"
  | "OTA_FAILED"
  | "OTA_ROLLED_BACK"
  | "COMMAND_QUEUED"
  | "COMMAND_SENT"
  | "COMMAND_POLLED"
  | "COMMAND_POLL_STALE"
  | "COMMAND_ACKED"
  | "COMMAND_IN_PROGRESS"
  | "COMMAND_COMPLETED"
  | "COMMAND_FAILED"
  | "COMMAND_TIMED_OUT"
  | "COMMAND_REJECTED"
  | "PROVISIONING_STARTED"
  | "PROVISIONING_SUCCESS"
  | "PROVISIONING_FAILED"
  | "FACTORY_RESET"
  | "IMAGE_CAPTURE_STARTED"
  | "IMAGE_CAPTURED"
  | "IMAGE_UPLOAD_STARTED"
  | "IMAGE_UPLOADED"
  | "IMAGE_UPLOAD_FAILED";

export type CommandType =
  | "SET_GROW_LIGHT_BRIGHTNESS"
  | "SET_LIGHT_BRIGHTNESS"
  | "SET_AMBIENT_LED_BELT"
  | "CAPTURE_IMAGE"
  | "REBOOT"
  | "START_OTA"
  | "ENTER_PAIRING_MODE"
  | "FACTORY_RESET"
  | "REQUEST_DIAGNOSTICS"
  | "UPDATE_CAPTURE_INTERVAL";

export type CommandStatus = "queued" | "sent" | "acked" | "in_progress" | "completed" | "failed" | "timed_out" | "rejected";

export type CommandTargetRole = "master" | "camera" | "sensor" | "actuator";

export type CommandPriority = "low" | "normal" | "high";

export type CommandErrorCode =
  | "UNKNOWN_COMMAND"
  | "INVALID_PARAMS"
  | "UNSUPPORTED_TARGET"
  | "DEVICE_BUSY"
  | "TIMEOUT"
  | "TRANSPORT_ERROR"
  | "INTERNAL_ERROR";

export type OTAStatus =
  | "idle"
  | "available"
  | "preparing"
  | "downloading"
  | "validating"
  | "installing"
  | "rebooting"
  | "success"
  | "failed"
  | "rolled_back";

export type OTAFailureReason =
  | "checksum_mismatch"
  | "unsupported_hardware"
  | "unsupported_firmware_version"
  | "unsupported_schema_version"
  | "download_failed"
  | "validation_failed"
  | "install_failed"
  | "reboot_failed"
  | "rollback_failed"
  | "network_error"
  | "timeout"
  | "internal_error";

export type OTAChannel = "stable" | "alpha" | "beta" | "dev" | "local";

export type OTAInstallPhase =
  | "check"
  | "prepare"
  | "download"
  | "validate"
  | "install"
  | "reboot"
  | "completed"
  | "rollback";

export type ImageUploadStatus = "uploaded" | "failed";

export type DeviceMessage<TPayload extends Record<string, unknown>> = {
  schema_version: string;
  message_id: string;
  device_id?: number;
  hardware_device_id: string;
  node_role: NodeRole;
  message_type: MessageType;
  sent_at?: string;
  payload: TPayload;
} & Record<string, unknown>;

export type HeartbeatPayload = {
  uptime_seconds: number;
  wifi_rssi_dbm?: number;
  ip_address?: string;
  free_heap_bytes?: number;
  node_status: DeviceStatus;
  firmware_version: string;
  hardware_model?: string;
  hardware_version?: string;
  camera_role?: CameraRole;
  capabilities?: string[];
  actuators?: HeartbeatActuatorState;
  runtime?: HeartbeatRuntimeState;
} & Record<string, unknown>;

export type HeartbeatActuatorState = {
  grow_light?: {
    enabled?: boolean;
    brightness_percent?: number;
  } & Record<string, unknown>;
  ambient_light?: {
    enabled?: boolean;
    brightness_percent?: number;
  } & Record<string, unknown>;
} & Record<string, unknown>;

export type HeartbeatRuntimeState = {
  capture_interval_seconds?: number;
  ota_status?: OTAStatus;
  provisioning_status?: string;
  camera_node_status?: DeviceStatus;
  last_command_id?: string;
  last_command_status?: string;
  last_command_poll_at?: string;
  last_command_poll_status?: string;
  last_command_poll_error?: string;
  last_command_poll_latency_ms?: number;
  command_poll_stale_seconds?: number;
  ambient_led_belt?: HeartbeatAmbientLedBeltState;
  time_sync_status?: string;
  last_ntp_sync_at?: string;
} & Record<string, unknown>;

export type HeartbeatAmbientLedBeltState = {
  available?: boolean;
  enabled?: boolean;
  mode?: "off" | "solid" | "breathe" | "pulse" | "chase" | "rainbow" | "diagnostic";
  brightness?: number;
  max_brightness?: number;
  color?: {
    r?: number;
    g?: number;
    b?: number;
  } & Record<string, unknown>;
  logical_pixel_count?: number;
  physical_led_count?: number;
  color_order?: "RGB" | "RBG" | "GRB" | "GBR" | "BRG" | "BGR";
  data_gpio?: number;
  diagnostic_active?: boolean;
  last_error?: string | null;
} & Record<string, unknown>;

export type DiagnosticsPayload = {
  status: DeviceStatus;
  severity: DiagnosticSeverity;
  error_counters?: Record<string, number>;
  last_error_code?: string;
  last_error_message?: string;
  reboot_reason?: string;
  subsystem_statuses?: Record<string, DeviceStatus>;
} & Record<string, unknown>;

export type CommandTarget = {
  node_role: CommandTargetRole;
  hardware_device_id?: string;
  camera_role?: CameraRole;
} & Record<string, unknown>;

export type RetryPolicy = {
  max_attempts: number;
  backoff_ms: number;
} & Record<string, unknown>;

export type CommandPayload = {
  command_id: string;
  command_type: CommandType;
  target: CommandTarget;
  params: Record<string, unknown>;
  timeout_ms: number;
  retry_policy?: RetryPolicy;
  priority?: CommandPriority;
  scheduled_for?: string | null;
} & Record<string, unknown>;

export type CommandResultPayload = {
  command_id: string;
  command_type: CommandType;
  status: CommandStatus;
  message?: string;
  result?: Record<string, unknown>;
  error_code?: CommandErrorCode | null;
  occurred_at?: string;
} & Record<string, unknown>;

export type OTACommandParams = {
  target_version: string;
  firmware_channel?: OTAChannel;
  download_url?: string;
  checksum_sha256?: string;
  hardware_model?: string;
  minimum_current_version?: string;
  schema_major?: number;
  rollback_version?: string;
} & Record<string, unknown>;

export type OTAStatusPayload = {
  command_id: string;
  status: OTAStatus;
  progress_percent?: number;
  current_version?: string;
  target_version?: string;
  firmware_channel?: OTAChannel;
  phase?: OTAInstallPhase;
  message?: string;
  failure_reason?: OTAFailureReason | null;
  release_id?: string;
} & Record<string, unknown>;

export type ImageUploadPayload = {
  status: ImageUploadStatus;
  image_id?: number;
  camera_node_id?: string;
  camera_role?: CameraRole;
  source_hardware_device_id?: string;
  source_node_role?: NodeRole;
  captured_at?: string;
  upload_reason?: string;
  width?: number;
  height?: number;
  content_type?: string;
  upload_ms?: number;
  failure_reason?: string;
} & Record<string, unknown>;

export type CommandMessage = DeviceMessage<CommandPayload>;

export type CommandPollResponse = {
  schema_version: string;
  commands: CommandMessage[];
} & Record<string, unknown>;

export type CommandResultMessage = DeviceMessage<CommandResultPayload>;

export type OTAStatusMessage = DeviceMessage<OTAStatusPayload>;

export type ImageUploadMessage = DeviceMessage<ImageUploadPayload>;

export type CanonicalEvent = {
  schema_version: string;
  event_type: EventType;
  severity: DiagnosticSeverity;
  device_id: number;
  hardware_device_id: string;
  node_role: NodeRole;
  occurred_at: string;
  correlation_id?: string;
  data: Record<string, unknown>;
} & Record<string, unknown>;

// TODO: replace this mirrored file with generated output from contracts/schemas.
