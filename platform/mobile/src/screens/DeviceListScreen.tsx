import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { StatusChip } from "@/components/StatusChip";
import { useDevices } from "@/hooks/useDevices";
import { theme } from "@/styles/theme";

export function DeviceListScreen() {
  const { devices, usedMock, isLoading, error, refresh, lastUpdatedAt } = useDevices();

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.eyebrow}>PLANTLAB</Text>
          <Text style={styles.title}>Devices</Text>
          <Text style={styles.subtitle}>
            {usedMock ? "Showing bundled mock devices because the backend is unavailable." : "Showing devices from your local PlantLab backend."}
          </Text>
          <Text style={styles.meta}>
            {lastUpdatedAt ? `Last updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Pull to refresh when you are ready."}
          </Text>
        </View>
        <PrimaryButton label="Add device" onPress={() => router.push("/(app)/devices/add")} />
      </View>

      {usedMock ? <StatusChip label="Mock data mode" tone="mock" /> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {isLoading && devices.length === 0 ? <Text style={styles.info}>Loading your devices…</Text> : null}
      {devices.map((device) => (
        <Pressable key={device.id} onPress={() => router.push(`/(app)/devices/${device.id}`)}>
          <Card>
            <View style={styles.cardHeader}>
              <View style={styles.cardTitleGroup}>
                <Text style={styles.cardTitle}>{device.name}</Text>
                <Text style={styles.cardSubtitle}>{device.location ?? "No location set"}</Text>
              </View>
              <StatusChip label={device.status} tone={device.status} />
            </View>
            <Text style={styles.meta}>
              {device.latestReading
                ? `Reading from ${new Date(device.latestReading.timestamp).toLocaleString()}`
                : "No reading received yet."}
            </Text>
            <Text style={styles.summary}>
              {device.latestReading
                ? `${device.latestReading.temperatureC?.toFixed(1) ?? "--"} C • ${device.latestReading.humidityPercent?.toFixed(1) ?? "--"}% • ${device.latestReading.soilMoisturePercent?.toFixed(1) ?? "--"}%`
                : "Latest sensor summary unavailable."}
            </Text>
          </Card>
        </Pressable>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: 12 },
  headerText: { gap: 8 },
  eyebrow: { fontSize: 13, fontWeight: "700", color: theme.colors.accent },
  title: { fontSize: 34, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: 16, color: theme.colors.textSecondary },
  meta: { fontSize: 13, color: theme.colors.textMuted },
  error: { color: "#b42318" },
  info: { color: theme.colors.textSecondary },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  cardTitleGroup: { gap: 4, flex: 1 },
  cardTitle: { fontSize: 20, fontWeight: "700", color: theme.colors.textPrimary },
  cardSubtitle: { fontSize: 14, color: theme.colors.textSecondary },
  summary: { fontSize: 15, color: theme.colors.textSecondary },
});
