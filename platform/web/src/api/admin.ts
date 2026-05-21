import { apiRequest } from "@/api/client";
import {
  AdminCommand,
  AdminDevice,
  AdminDiagnostics,
  AdminEvent,
  AdminFirmwareRelease,
  AdminNode,
  AdminSummary,
  AdminUser,
} from "@/types";

type ApiAdminDiagnostics = {
  generated_at: string;
  requested_by: {
    id: number;
    email: string;
  };
  summary: ApiAdminSummary;
  users: ApiAdminUser[];
  devices: ApiAdminDevice[];
  recent_events: ApiAdminEvent[];
  recent_commands: ApiAdminCommand[];
  firmware_releases: ApiAdminFirmwareRelease[];
};

type ApiAdminSummary = {
  users: number;
  active_users: number;
  devices: number;
  active_devices: number;
  released_devices: number;
  archived_devices: number;
  hardware_nodes: number;
  stale_nodes: number;
  recent_warning_events: number;
  firmware_releases: number;
};

type ApiAdminUser = {
  id: number;
  email: string;
  name?: string | null;
  created_at: string;
  device_count: number;
  active_device_count: number;
  last_seen_at?: string | null;
  recent_warning_event_count: number;
  recent_command_count: number;
  last_command_at?: string | null;
};

type ApiAdminNode = {
  hardware_device_id: string;
  node_role?: string | null;
  display_name?: string | null;
  hardware_model?: string | null;
  software_version?: string | null;
  status: string;
  last_seen_at?: string | null;
  ota_status?: string | null;
  ota_target_version?: string | null;
  ota_error?: string | null;
};

type ApiAdminDevice = {
  id: number;
  name: string;
  owner_email: string;
  location?: string | null;
  plant_type?: string | null;
  status: string;
  created_at: string;
  released_at?: string | null;
  archived_at?: string | null;
  latest_reading_at?: string | null;
  latest_image_at?: string | null;
  node_count: number;
  nodes: ApiAdminNode[];
  last_error_code?: string | null;
  last_error_message?: string | null;
  recent_event_count: number;
};

type ApiAdminEvent = {
  id: number;
  device_id: number;
  device_name: string;
  owner_email: string;
  hardware_device_id?: string | null;
  event_type: string;
  severity: string;
  code?: string | null;
  message?: string | null;
  occurred_at: string;
};

type ApiAdminCommand = {
  id: number;
  device_id: number;
  device_name: string;
  owner_email: string;
  target: string;
  action: string;
  value?: string | null;
  status: string;
  message?: string | null;
  created_at: string;
  sent_at?: string | null;
  completed_at?: string | null;
};

type ApiAdminFirmwareRelease = {
  release_id: string;
  node_role: string;
  hardware_model?: string | null;
  version: string;
  status: string;
  published_at?: string | null;
};

export async function fetchAdminDiagnostics(token?: string): Promise<AdminDiagnostics> {
  const payload = await apiRequest<ApiAdminDiagnostics>("/api/admin/diagnostics", {}, token);
  return {
    generatedAt: payload.generated_at,
    requestedBy: {
      id: String(payload.requested_by.id),
      email: payload.requested_by.email,
    },
    summary: mapSummary(payload.summary),
    users: payload.users.map(mapUser),
    devices: payload.devices.map(mapDevice),
    recentEvents: payload.recent_events.map(mapEvent),
    recentCommands: payload.recent_commands.map(mapCommand),
    firmwareReleases: payload.firmware_releases.map(mapFirmwareRelease),
  };
}

function mapSummary(summary: ApiAdminSummary): AdminSummary {
  return {
    users: summary.users,
    activeUsers: summary.active_users,
    devices: summary.devices,
    activeDevices: summary.active_devices,
    releasedDevices: summary.released_devices,
    archivedDevices: summary.archived_devices,
    hardwareNodes: summary.hardware_nodes,
    staleNodes: summary.stale_nodes,
    recentWarningEvents: summary.recent_warning_events,
    firmwareReleases: summary.firmware_releases,
  };
}

function mapUser(user: ApiAdminUser): AdminUser {
  return {
    id: String(user.id),
    email: user.email,
    name: user.name ?? undefined,
    createdAt: user.created_at,
    deviceCount: user.device_count,
    activeDeviceCount: user.active_device_count,
    lastSeenAt: user.last_seen_at ?? undefined,
    recentWarningEventCount: user.recent_warning_event_count,
    recentCommandCount: user.recent_command_count,
    lastCommandAt: user.last_command_at ?? undefined,
  };
}

function mapNode(node: ApiAdminNode): AdminNode {
  return {
    hardwareDeviceId: node.hardware_device_id,
    nodeRole: node.node_role ?? undefined,
    displayName: node.display_name ?? undefined,
    hardwareModel: node.hardware_model ?? undefined,
    softwareVersion: node.software_version ?? undefined,
    status: node.status,
    lastSeenAt: node.last_seen_at ?? undefined,
    otaStatus: node.ota_status ?? undefined,
    otaTargetVersion: node.ota_target_version ?? undefined,
    otaError: node.ota_error ?? undefined,
  };
}

function mapDevice(device: ApiAdminDevice): AdminDevice {
  return {
    id: String(device.id),
    name: device.name,
    ownerEmail: device.owner_email,
    location: device.location ?? undefined,
    plantType: device.plant_type ?? undefined,
    status: device.status,
    createdAt: device.created_at,
    releasedAt: device.released_at ?? undefined,
    archivedAt: device.archived_at ?? undefined,
    latestReadingAt: device.latest_reading_at ?? undefined,
    latestImageAt: device.latest_image_at ?? undefined,
    nodeCount: device.node_count,
    nodes: device.nodes.map(mapNode),
    lastErrorCode: device.last_error_code ?? undefined,
    lastErrorMessage: device.last_error_message ?? undefined,
    recentEventCount: device.recent_event_count,
  };
}

function mapEvent(event: ApiAdminEvent): AdminEvent {
  return {
    id: String(event.id),
    deviceId: String(event.device_id),
    deviceName: event.device_name,
    ownerEmail: event.owner_email,
    hardwareDeviceId: event.hardware_device_id ?? undefined,
    eventType: event.event_type,
    severity: event.severity,
    code: event.code ?? undefined,
    message: event.message ?? undefined,
    occurredAt: event.occurred_at,
  };
}

function mapCommand(command: ApiAdminCommand): AdminCommand {
  return {
    id: String(command.id),
    deviceId: String(command.device_id),
    deviceName: command.device_name,
    ownerEmail: command.owner_email,
    target: command.target,
    action: command.action,
    value: command.value ?? undefined,
    status: command.status,
    message: command.message ?? undefined,
    createdAt: command.created_at,
    sentAt: command.sent_at ?? undefined,
    completedAt: command.completed_at ?? undefined,
  };
}

function mapFirmwareRelease(release: ApiAdminFirmwareRelease): AdminFirmwareRelease {
  return {
    releaseId: release.release_id,
    nodeRole: release.node_role,
    hardwareModel: release.hardware_model ?? undefined,
    version: release.version,
    status: release.status,
    publishedAt: release.published_at ?? undefined,
  };
}
