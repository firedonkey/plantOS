import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { StatusChip } from "@/components/StatusChip";
import { DeviceConnectionState, HardwareDiagnostics, HardwareHealth } from "@/types";
import { theme } from "@/styles/theme";

type HardwareHealthPanelProps = {
  health?: HardwareHealth;
};

export function HardwareHealthPanel({ health }: HardwareHealthPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [dismissedAttentionSignature, setDismissedAttentionSignature] = useState<string | null>(null);
  if (!health) {
    return (
      <Card>
        <PanelHeader
          expanded={expanded}
          statusLabel="Waiting"
          statusTone="unknown"
          subtitle="Waiting for backend hardware health details."
          title="Hardware health"
          onPress={() => setExpanded((value) => !value)}
        />
        {expanded ? <EmptyState title="Waiting for health" message="Node heartbeat, camera, and command details will appear after the device reports health." /> : null}
      </Card>
    );
  }

  const attentionItems = getAttentionItems(health);
  const attentionSignature = attentionItems.join("|");
  const attentionDismissed = attentionSignature.length > 0 && dismissedAttentionSignature === attentionSignature;
  const visibleAttentionItems = attentionDismissed ? [] : attentionItems;
  const headerStatusLabel =
    attentionDismissed && health.friendlyStatus === "needs_attention"
      ? "Reviewed"
      : formatFriendlyStatus(health.friendlyStatus, health.overallStatus);
  const headerStatusTone =
    attentionDismissed && health.friendlyStatus === "needs_attention"
      ? "unknown"
      : friendlyTone(health.friendlyStatus, health.overallStatus);

  return (
    <Card>
      <PanelHeader
        expanded={expanded}
        statusLabel={headerStatusLabel}
        statusTone={headerStatusTone}
        subtitle={formatAge(health.lastHeartbeatAt ?? health.primary?.lastSeenAt, "Heartbeat")}
        title="Hardware health"
        onPress={() => setExpanded((value) => !value)}
      />

      {!expanded ? null : (
        <>
          {visibleAttentionItems.length ? (
            <View style={styles.attentionBox}>
              <View style={styles.attentionHeader}>
                <Text style={styles.attentionTitle}>Needs attention</Text>
                <Pressable
                  accessibilityRole="button"
                  onPress={() => setDismissedAttentionSignature(attentionSignature)}
                  style={styles.dismissButton}
                >
                  <Text style={styles.dismissButtonText}>Dismiss</Text>
                </Pressable>
              </View>
              {visibleAttentionItems.map((item) => (
                <Text key={item} style={styles.attentionText}>- {item}</Text>
              ))}
            </View>
          ) : null}

          <View style={styles.grid}>
            <HealthItem title="Master" tone={health.masterStatus ?? health.primary?.status ?? "unknown"} value={formatNodeStatus(health.primary?.displayName ?? "Master", health.masterStatus ?? health.primary?.status ?? "unknown")} detail={formatAge(health.primary?.lastSeenAt, "Last heartbeat")} />
            <HealthItem
              title="Firmware"
              tone={otaTone(health.primary?.otaStatus)}
              value={formatFirmwareValue(health)}
              detail={formatFirmwareDetail(health)}
            />
            <HealthItem
              title="Camera"
              tone={health.cameraStatus ?? health.imageStatus ?? "waiting"}
              value={
                health.cameras.length
                  ? health.cameras
                      .map((camera) => formatNodeStatus(camera.displayName ?? `Camera ${camera.nodeIndex ?? ""}`.trim(), camera.status))
                      .join(", ")
                  : "No camera nodes yet"
              }
              detail={formatAge(health.lastImageAt, "Last image")}
            />
            <HealthItem title="Reading" tone={health.readingStatus ?? "waiting"} value={formatAge(health.lastReadingAt, "Last reading")} detail={formatAge(health.lastHeartbeatAt, "Last heartbeat")} />
            <HealthItem
              title="Last command"
              tone={health.lastCommand ? commandTone(health.lastCommand.status) : "waiting"}
              value={health.lastCommand ? `${formatAction(health.lastCommand.action)} · ${formatCommandStatus(health.lastCommand.status)}` : "No recent commands"}
              detail={health.lastCommand ? formatAge(health.lastCommand.timestamp, "Updated") : "Command history will appear here after the first control action."}
            />
          </View>

          <View style={styles.supportSection}>
            <Text style={styles.supportTitle}>Support diagnostics</Text>
            <DiagnosticRow label="Firmware" value={health.primary?.diagnostics?.firmwareVersion ?? health.primary?.softwareVersion ?? "Not reported"} />
            <DiagnosticRow label="Uptime" value={formatUptime(health.primary?.diagnostics?.uptimeSeconds)} />
            <DiagnosticRow label="Wi-Fi RSSI" value={formatRssi(health.primary?.diagnostics?.wifiRssiDbm)} />
            <DiagnosticRow label="Reboot reason" value={formatCode(health.primary?.diagnostics?.rebootReason)} />
            <DiagnosticRow label="Provisioning" value={formatCode(health.primary?.diagnostics?.provisioningState)} />
            <DiagnosticRow label="Last heartbeat" value={formatAge(health.lastHeartbeatAt ?? health.primary?.lastSeenAt, "Heartbeat")} />
            <DiagnosticRow label="Last reading" value={formatAge(health.lastReadingAt ?? health.primary?.diagnostics?.lastSensorReadingAt, "Reading")} />
            <DiagnosticRow label="Last camera upload" value={formatAge(health.lastImageAt ?? latestCameraDiagnostic(health)?.lastCameraImageUploadAt, "Image")} />
            <DiagnosticRow label="Last command" value={formatDiagnosticCommand(health.primary?.diagnostics, health)} />
            <DiagnosticRow label="OTA" value={formatFirmwareDetail(health)} />
            <DiagnosticRow label="Counters" value={formatCounters(health.primary?.diagnostics?.errorCounters)} />
            <DiagnosticRow label="Attention" value={attentionItems.length ? attentionItems.join(", ") : "No attention reasons"} />
          </View>

          {health.lastCommand?.message ? <Text style={styles.meta}>{health.lastCommand.message}</Text> : null}
        </>
      )}
    </Card>
  );
}

function getAttentionItems(health: HardwareHealth): string[] {
  const items = new Set<string>();

  health.attentionReasons?.forEach((reason) => items.add(formatCode(reason)));

  const heartbeatStatus = health.heartbeatStatus;
  const readingStatus = health.readingStatus;
  const cameraStatus = health.cameraStatus ?? health.imageStatus;
  const masterStatus = health.masterStatus ?? health.primary?.status;

  if (isProblemStatus(heartbeatStatus)) {
    items.add(`Heartbeat is ${formatStatusLabel(heartbeatStatus)}`);
  }
  if (isProblemStatus(readingStatus)) {
    items.add(`Sensor readings are ${formatStatusLabel(readingStatus)}`);
  }
  if (isProblemStatus(cameraStatus)) {
    items.add(`Camera images are ${formatStatusLabel(cameraStatus)}`);
  }
  if (isProblemStatus(masterStatus)) {
    items.add(`Master node is ${formatStatusLabel(masterStatus)}`);
  }

  health.cameras
    .filter((camera) => isProblemStatus(camera.status))
    .forEach((camera) => {
      items.add(`${camera.displayName ?? `Camera ${camera.nodeIndex ?? ""}`.trim()}: ${formatStatusLabel(camera.status)}`);
    });

  if (health.lastCommand?.status === "failed") {
    items.add(`${formatAction(health.lastCommand.action)} failed`);
  }
  if (health.primary?.diagnostics?.lastErrorCode) {
    items.add(`Last error: ${formatCode(health.primary.diagnostics.lastErrorCode)}`);
  }

  const counters = health.primary?.diagnostics?.errorCounters;
  Object.entries(counters ?? {})
    .filter(([, value]) => value > 0)
    .forEach(([key, value]) => items.add(`${formatCode(key)}: ${value}`));

  if (!items.size && health.friendlyStatus === "needs_attention") {
    items.add("Backend reported an issue but did not include a specific reason. Review the health rows below.");
  }

  return Array.from(items);
}

function isProblemStatus(status: string | undefined): status is string {
  return status === "offline" || status === "stale" || status === "warning" || status === "degraded" || status === "error";
}

function DiagnosticRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.diagnosticRow}>
      <Text style={styles.diagnosticLabel}>{label}</Text>
      <Text style={styles.diagnosticValue}>{value}</Text>
    </View>
  );
}

function PanelHeader({
  expanded,
  statusLabel,
  statusTone,
  subtitle,
  title,
  onPress,
}: {
  expanded: boolean;
  statusLabel: string;
  statusTone: DeviceConnectionState;
  subtitle: string;
  title: string;
  onPress: () => void;
}) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.header}>
      <View style={{ flex: 1, gap: 6 }}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>
      </View>
      <View style={styles.headerRight}>
        <StatusChip label={statusLabel} tone={statusTone} compact />
        <Text style={styles.expandText}>{expanded ? "Hide" : "Show"}</Text>
      </View>
    </Pressable>
  );
}

function HealthItem({
  title,
  tone,
  value,
  detail,
}: {
  title: string;
  tone: DeviceConnectionState | "provisioning" | "error";
  value: string;
  detail: string;
}) {
  const chipTone = tone === "provisioning" || tone === "error" ? "unknown" : tone;
  return (
    <View style={styles.item}>
      <View style={styles.itemHeader}>
        <Text style={styles.itemTitle}>{title}</Text>
        <StatusChip label={formatStatusLabel(tone)} tone={chipTone} compact />
      </View>
      <Text style={styles.itemValue}>{value}</Text>
      <Text style={styles.itemDetail}>{detail}</Text>
    </View>
  );
}

function commandTone(status: string): DeviceConnectionState {
  if (status === "completed") {
    return "online";
  }
  if (status === "failed") {
    return "offline";
  }
  return "waiting";
}

function otaTone(status: string | undefined): DeviceConnectionState {
  if (status === "success" || status === "idle") {
    return "online";
  }
  if (status === "failed") {
    return "offline";
  }
  if (status === "available") {
    return "warning";
  }
  if (status === "downloading" || status === "installing") {
    return "waiting";
  }
  return "unknown";
}

function friendlyTone(status: HardwareHealth["friendlyStatus"], fallback: HardwareHealth["overallStatus"]): DeviceConnectionState {
  if (status === "online") {
    return "online";
  }
  if (status === "offline") {
    return "offline";
  }
  if (status === "recently_seen") {
    return "stale";
  }
  if (status === "needs_attention") {
    return "warning";
  }
  return fallback === "provisioning" || fallback === "error" ? "unknown" : fallback;
}

function formatFriendlyStatus(status: HardwareHealth["friendlyStatus"], fallback: string) {
  switch (status) {
    case "online":
      return "Online";
    case "recently_seen":
      return "Recently seen";
    case "offline":
      return "Offline";
    case "needs_attention":
      return "Needs attention";
    default:
      return formatStatusLabel(fallback);
  }
}

function formatFirmwareValue(health: HardwareHealth) {
  const version = health.primary?.softwareVersion ?? "Unknown version";
  const status = formatOtaStatus(health.primary?.otaStatus);
  return `${version} · ${status}`;
}

function latestCameraDiagnostic(health: HardwareHealth): HardwareDiagnostics | undefined {
  return health.cameras.find((camera) => camera.diagnostics?.lastCameraImageUploadAt)?.diagnostics ?? health.cameras[0]?.diagnostics;
}

function formatUptime(seconds: number | undefined) {
  if (typeof seconds !== "number") {
    return "Not reported";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function formatRssi(value: number | undefined) {
  return typeof value === "number" ? `${value} dBm` : "Not reported";
}

function formatCode(value: string | undefined) {
  return value ? value.replace(/_/g, " ") : "Not reported";
}

function formatCounters(counters: Record<string, number> | undefined) {
  if (!counters || Object.keys(counters).length === 0) {
    return "Not reported";
  }
  return Object.entries(counters)
    .map(([key, value]) => `${formatCode(key)}: ${value}`)
    .join(", ");
}

function formatDiagnosticCommand(diagnostics: HardwareDiagnostics | undefined, health: HardwareHealth) {
  if (diagnostics?.lastCommandStatus) {
    const code = diagnostics.lastCommandCode ? ` · ${formatCode(diagnostics.lastCommandCode)}` : "";
    return `${formatCode(diagnostics.lastCommandStatus)}${code}`;
  }
  return health.lastCommand ? `${formatAction(health.lastCommand.action)} · ${formatCommandStatus(health.lastCommand.status)}` : "Not reported";
}

function formatFirmwareDetail(health: HardwareHealth) {
  const primary = health.primary;
  if (!primary) {
    return "Firmware: waiting";
  }
  if (primary.otaStatus === "failed" && primary.otaError) {
    return primary.otaError;
  }
  if (primary.otaTargetVersion) {
    const progress = typeof primary.otaProgress === "number" ? ` · ${primary.otaProgress}%` : "";
    return `Target: ${primary.otaTargetVersion}${progress}`;
  }
  if (primary.otaAvailableVersion) {
    return `Available: ${primary.otaAvailableVersion}`;
  }
  return primary.otaLastSuccessAt ? formatAge(primary.otaLastSuccessAt, "Last update") : "No update pending";
}

function formatOtaStatus(status: string | undefined) {
  switch (status) {
    case "idle":
      return "Idle";
    case "available":
      return "Update available";
    case "downloading":
      return "Downloading";
    case "installing":
      return "Installing";
    case "success":
      return "Updated";
    case "failed":
      return "Failed";
    default:
      return "Unknown";
  }
}

function formatNodeStatus(name: string, status: string) {
  return `${name}: ${formatStatusLabel(status)}`;
}

function formatStatusLabel(status: string) {
  switch (status) {
    case "online":
      return "Online";
    case "offline":
      return "Offline";
    case "degraded":
      return "Degraded";
    case "stale":
      return "Stale";
    case "warning":
      return "Warning";
    case "waiting":
      return "Waiting";
    case "provisioning":
      return "Provisioning";
    case "error":
      return "Error";
    case "unknown":
      return "Unknown";
    default:
      return "Unknown";
  }
}

function formatCommandStatus(status: string) {
  switch (status) {
    case "completed":
      return "Completed";
    case "in_progress":
      return "In progress";
    case "pending":
      return "Pending";
    case "sent":
      return "Sent";
    case "failed":
      return "Failed";
    default:
      return "Unknown";
  }
}

function formatAction(action: string) {
  switch (action) {
    case "light_on":
      return "Grow LED on";
    case "light_off":
      return "Grow LED off";
    case "light_intensity":
      return "Grow LED intensity";
    case "pump_run":
      return "Pump run";
    default:
      return "Capture image";
  }
}

function formatAge(timestamp: string | undefined, label: string) {
  if (!timestamp) {
    return `${label}: waiting`;
  }
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) {
    return `${label}: ${seconds}s ago`;
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${label}: ${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  return `${label}: ${hours}h ago`;
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.md },
  headerRight: { alignItems: "flex-end", gap: theme.spacing.sm },
  title: { fontSize: theme.typography.sectionTitle, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: theme.typography.body, color: theme.colors.textSecondary },
  expandText: { fontSize: theme.typography.meta, fontWeight: "700", color: theme.colors.accent },
  grid: { gap: theme.spacing.md },
  attentionBox: {
    borderWidth: 1,
    borderColor: theme.colors.warning,
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.warningSoft,
    padding: theme.spacing.md,
    gap: theme.spacing.xs,
    marginBottom: theme.spacing.md,
  },
  attentionHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", gap: theme.spacing.md },
  attentionTitle: { fontSize: 15, fontWeight: "800", color: theme.colors.warning },
  attentionText: { fontSize: 13, color: theme.colors.textPrimary },
  dismissButton: {
    borderColor: theme.colors.warning,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
  },
  dismissButtonText: { color: theme.colors.warning, fontSize: 13, fontWeight: "800" },
  supportSection: { gap: theme.spacing.sm, marginTop: theme.spacing.md },
  supportTitle: { fontSize: 15, fontWeight: "800", color: theme.colors.textPrimary },
  diagnosticRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderSoft,
    paddingBottom: theme.spacing.xs,
  },
  diagnosticLabel: { flex: 1, fontSize: 13, color: theme.colors.textSecondary },
  diagnosticValue: { flex: 1.5, fontSize: 13, color: theme.colors.textPrimary, textAlign: "right" },
  item: {
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surfaceMuted,
    gap: theme.spacing.sm,
  },
  itemHeader: { flexDirection: "row", justifyContent: "space-between", gap: theme.spacing.md, alignItems: "center" },
  itemTitle: { fontSize: 15, fontWeight: "800", color: theme.colors.textPrimary },
  itemValue: { fontSize: 14, color: theme.colors.textPrimary },
  itemDetail: { fontSize: 13, color: theme.colors.textSecondary },
  meta: { fontSize: 13, color: theme.colors.textSecondary },
});
