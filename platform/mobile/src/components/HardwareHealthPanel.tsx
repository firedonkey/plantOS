import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
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
        {expanded ? <Text style={styles.subtitle}>Waiting for backend hardware health details.</Text> : null}
      </Card>
    );
  }

  return (
    <Card>
      <PanelHeader
        expanded={expanded}
        statusLabel={formatStatusLabel(health.overallStatus)}
        statusTone={health.overallStatus === "provisioning" || health.overallStatus === "error" ? "unknown" : health.overallStatus}
        subtitle="Live heartbeat, node, image, and command status from the shared backend contract."
        title="Hardware health"
        onPress={() => setExpanded((value) => !value)}
      />

      {!expanded ? null : (
        <>
          <View style={styles.grid}>
            <HealthItem title="Master" value={formatNodeStatus(health.primary?.displayName ?? "Master", health.masterStatus ?? health.primary?.status ?? "unknown")} detail={formatAge(health.primary?.lastSeenAt, "Last heartbeat")} />
            <HealthItem
              title="Camera"
              value={
                health.cameras.length
                  ? health.cameras
                      .map((camera) => formatNodeStatus(camera.displayName ?? `Camera ${camera.nodeIndex ?? ""}`.trim(), camera.status))
                      .join(", ")
                  : "No camera nodes yet"
              }
              detail={formatAge(health.lastImageAt, "Last image")}
            />
            <HealthItem title="Reading" value={formatAge(health.lastReadingAt, "Last reading")} detail={formatAge(health.lastHeartbeatAt, "Last heartbeat")} />
            <HealthItem
              title="Last command"
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
        <StatusChip label={statusLabel} tone={statusTone} />
        <Text style={styles.expandText}>{expanded ? "Hide" : "Show"}</Text>
      </View>
    </Pressable>
  );
}

function HealthItem({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <View style={styles.item}>
      <Text style={styles.itemTitle}>{title}</Text>
      <Text style={styles.itemValue}>{value}</Text>
      <Text style={styles.itemDetail}>{detail}</Text>
    </View>
  );
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
    case "provisioning":
      return "Provisioning";
    case "error":
      return "Error";
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
  header: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  headerRight: { alignItems: "flex-end", gap: 8 },
  title: { fontSize: 18, fontWeight: "700", color: theme.colors.textPrimary },
  subtitle: { fontSize: 14, color: theme.colors.textSecondary },
  expandText: { fontSize: 13, fontWeight: "700", color: theme.colors.accent },
  grid: { gap: 12 },
  item: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: 8,
    padding: 14,
    backgroundColor: "#f8fafb",
    gap: 6,
  },
  itemTitle: { fontSize: 15, fontWeight: "700", color: theme.colors.textPrimary },
  itemValue: { fontSize: 14, color: theme.colors.textPrimary },
  itemDetail: { fontSize: 13, color: theme.colors.textSecondary },
  meta: { fontSize: 13, color: theme.colors.textSecondary },
});
