import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { DeviceCommand } from "@/types";
import { theme } from "@/styles/theme";

type CommandActivityPanelProps = {
  commands: DeviceCommand[];
};

export function CommandActivityPanel({ commands }: CommandActivityPanelProps) {
  return (
    <Card>
      <Text style={styles.title}>Command activity</Text>
      <Text style={styles.subtitle}>Recent light and pump commands from the shared backend command history.</Text>

      {!commands.length ? (
        <Text style={styles.subtitle}>No recent commands yet. Command activity will appear here after you use the controls.</Text>
      ) : (
        <View style={styles.list}>
          {commands.map((command) => (
            <View key={command.id} style={styles.row}>
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={styles.label}>{formatAction(command.action)}</Text>
                <Text style={styles.meta}>{new Date(command.createdAt).toLocaleString()}</Text>
              </View>
              <View style={[styles.badge, command.status === "acknowledged" ? styles.badgeSuccess : command.status === "failed" ? styles.badgeError : styles.badgeNeutral]}>
                <Text style={[styles.badgeText, command.status === "acknowledged" ? styles.badgeTextSuccess : command.status === "failed" ? styles.badgeTextError : styles.badgeTextNeutral]}>
                  {formatStatus(command.status)}
                </Text>
              </View>
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
      return "Light on";
    case "light_off":
      return "Light off";
    case "pump_run":
      return "Pump run";
    case "capture_image":
      return "Capture image";
  }
}

function formatStatus(status: DeviceCommand["status"]): string {
  switch (status) {
    case "acknowledged":
      return "Done";
    case "pending":
      return "Pending";
    case "sent":
      return "Sent";
    case "failed":
      return "Failed";
  }
}

const styles = StyleSheet.create({
  title: { fontSize: 18, fontWeight: "700", color: theme.colors.textPrimary },
  subtitle: { fontSize: 14, color: theme.colors.textSecondary },
  list: { gap: 12 },
  row: {
    flexDirection: "row",
    gap: 12,
    alignItems: "center",
    justifyContent: "space-between",
    borderTopWidth: 1,
    borderTopColor: "#e7ecef",
    paddingTop: 12,
  },
  label: { fontSize: 15, fontWeight: "700", color: theme.colors.textPrimary },
  meta: { fontSize: 13, color: theme.colors.textSecondary },
  badge: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 6 },
  badgeSuccess: { backgroundColor: "#dff7e8" },
  badgeError: { backgroundColor: "#fde4e4" },
  badgeNeutral: { backgroundColor: "#eceff3" },
  badgeText: { fontSize: 12, fontWeight: "700" },
  badgeTextSuccess: { color: "#157347" },
  badgeTextError: { color: "#b42318" },
  badgeTextNeutral: { color: theme.colors.textSecondary },
});
