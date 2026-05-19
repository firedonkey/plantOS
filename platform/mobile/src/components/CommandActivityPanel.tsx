import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { StatusChip } from "@/components/StatusChip";
import { DeviceCommand } from "@/types";
import { theme } from "@/styles/theme";

type CommandActivityPanelProps = {
  commands: DeviceCommand[];
};

export function CommandActivityPanel({ commands }: CommandActivityPanelProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card variant="inset">
      <Pressable accessibilityRole="button" onPress={() => setExpanded((value) => !value)} style={styles.header}>
        <View style={{ flex: 1, gap: 6 }}>
          <Text style={styles.title}>Command activity</Text>
          <Text style={styles.subtitle}>{commands.length ? `${commands.length} recent control event${commands.length === 1 ? "" : "s"}` : "No control events yet"}</Text>
        </View>
        <View style={styles.headerRight}>
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{commands.length}</Text>
          </View>
          <Text style={styles.expandText}>{expanded ? "Hide" : "Show"}</Text>
        </View>
      </Pressable>

      {!expanded ? null : !commands.length ? (
        <EmptyState title="No commands yet" message="Control activity will appear after the grow LED or camera actions run." />
      ) : (
        <View style={styles.list}>
          {commands.map((command) => (
            <View key={command.id} style={styles.row}>
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={styles.label}>{formatAction(command.action)}</Text>
                <Text style={styles.meta}>{new Date(command.createdAt).toLocaleString()}</Text>
                {command.detail ? <Text style={styles.meta}>{command.detail}</Text> : null}
              </View>
              <StatusChip label={formatStatus(command.status)} tone={command.status === "completed" ? "online" : command.status === "failed" ? "offline" : "waiting"} compact />
            </View>
          ))}
        </View>
      )}
    </Card>
  );
}

function formatAction(action: DeviceCommand["action"]): string {
  switch (action) {
    case "light_on":
      return "Grow LED on";
    case "light_off":
      return "Grow LED off";
    case "light_intensity":
      return "Grow LED intensity";
    case "pump_run":
      return "Pump run";
    case "capture_image":
      return "Capture image";
  }
}

function formatStatus(status: DeviceCommand["status"]): string {
  switch (status) {
    case "completed":
      return "Completed";
    case "pending":
      return "Pending";
    case "sent":
      return "Sent";
    case "in_progress":
      return "In progress";
    case "failed":
      return "Failed";
  }
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.md },
  headerRight: { alignItems: "flex-end", gap: theme.spacing.sm },
  title: { fontSize: theme.typography.sectionTitle, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: theme.typography.body, color: theme.colors.textSecondary },
  expandText: { fontSize: theme.typography.meta, fontWeight: "700", color: theme.colors.accent },
  countBadge: { minWidth: 28, borderRadius: theme.radii.pill, paddingHorizontal: 9, paddingVertical: 5, backgroundColor: theme.colors.surfaceInset, alignItems: "center" },
  countText: { fontSize: theme.typography.caption, fontWeight: "700", color: theme.colors.textSecondary },
  list: { gap: theme.spacing.md },
  row: {
    flexDirection: "row",
    gap: theme.spacing.md,
    alignItems: "center",
    justifyContent: "space-between",
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderSoft,
    paddingTop: theme.spacing.md,
  },
  label: { fontSize: 15, fontWeight: "800", color: theme.colors.textPrimary },
  meta: { fontSize: theme.typography.meta, color: theme.colors.textSecondary },
});
