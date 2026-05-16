import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { StatusChip } from "@/components/StatusChip";
import { DeviceConnectionState, HardwareHealth } from "@/types";
import { theme } from "@/styles/theme";

type HardwareHealthPanelProps = {
  health?: HardwareHealth;
};

export function HardwareHealthPanel({ health }: HardwareHealthPanelProps) {
  const [expanded, setExpanded] = useState(false);
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

  return (
    <Card>
      <PanelHeader
        expanded={expanded}
        statusLabel={formatStatusLabel(health.overallStatus)}
        statusTone={health.overallStatus === "provisioning" || health.overallStatus === "error" ? "unknown" : health.overallStatus}
        subtitle={formatAge(health.lastHeartbeatAt ?? health.primary?.lastSeenAt, "Heartbeat")}
        title="Hardware health"
        onPress={() => setExpanded((value) => !value)}
      />

      {!expanded ? null : (
        <>
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

          {health.lastCommand?.message ? <Text style={styles.meta}>{health.lastCommand.message}</Text> : null}
        </>
      )}
    </Card>
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

function formatFirmwareValue(health: HardwareHealth) {
  const version = health.primary?.softwareVersion ?? "Unknown version";
  const status = formatOtaStatus(health.primary?.otaStatus);
  return `${version} · ${status}`;
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
