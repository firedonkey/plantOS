import { Link } from "expo-router";
import { Image, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { MetricCard } from "@/components/MetricCard";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { StatusChip } from "@/components/StatusChip";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

type DeviceDashboardScreenProps = {
  deviceId: string;
};

export function DeviceDashboardScreen({ deviceId }: DeviceDashboardScreenProps) {
  const { dashboard, usedMock, isLoading, error, commandMessage, refresh, runCommand } = useDeviceDashboard(deviceId);
  const { token, session } = useSession();

  if (!deviceId) {
    return (
      <Screen>
        <Text style={styles.error}>Missing device id.</Text>
      </Screen>
    );
  }

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      {dashboard ? (
        <>
          <View style={styles.header}>
            <View style={{ flex: 1, gap: 8 }}>
              <Text style={styles.eyebrow}>DEVICE DASHBOARD</Text>
              <Text style={styles.title}>{dashboard.device.name}</Text>
              <Text style={styles.subtitle}>
                {dashboard.device.plantType ?? "Plant type not set"} • {dashboard.device.location ?? "No location set"}
              </Text>
            </View>
            <StatusChip label={usedMock ? "Mock mode" : dashboard.device.status} tone={usedMock ? "mock" : dashboard.device.status} />
          </View>

          {error ? <Text style={styles.error}>{error}</Text> : null}
          {commandMessage ? <Text style={styles.commandMessage}>{commandMessage}</Text> : null}

          <Card>
            <View style={styles.metricsGrid}>
              <MetricCard label="Temperature" value={`${dashboard.device.latestReading?.temperatureC?.toFixed(1) ?? "--"} C`} />
              <MetricCard label="Humidity" value={`${dashboard.device.latestReading?.humidityPercent?.toFixed(1) ?? "--"}%`} />
              <MetricCard label="Soil Moisture" value={`${dashboard.device.latestReading?.soilMoisturePercent?.toFixed(1) ?? "--"}%`} />
              <MetricCard label="Water Level" value={`${dashboard.device.latestReading?.waterLevelPercent?.toFixed(0) ?? "--"}%`} />
              <MetricCard label="Light" value={dashboard.device.latestReading?.lightOn ? "On" : "Off"} />
              <MetricCard label="Pump" value={dashboard.device.latestReading?.pumpOn ? "On" : "Off"} />
            </View>
          </Card>

          <Card>
            <Text style={styles.sectionTitle}>Latest capture</Text>
            {dashboard.device.latestImage ? (
              <>
                <Image
                  source={{
                    uri: dashboard.device.latestImage.url,
                    headers:
                      session?.mode === "api" && token
                        ? { Authorization: `Bearer ${token}` }
                        : undefined,
                  }}
                  style={styles.image}
                />
                <Text style={styles.meta}>Captured {new Date(dashboard.device.latestImage.capturedAt).toLocaleString()}</Text>
              </>
            ) : (
              <Text style={styles.meta}>No image available yet.</Text>
            )}
          </Card>

          <Card>
            <Text style={styles.sectionTitle}>Manual controls</Text>
            <View style={styles.buttonRow}>
              <PrimaryButton label="Light on" onPress={() => runCommand("light_on")} />
              <PrimaryButton label="Light off" onPress={() => runCommand("light_off")} />
            </View>
            <View style={styles.buttonRow}>
              <PrimaryButton label="Pump run" onPress={() => runCommand("pump_run")} />
              <PrimaryButton label="Capture image" onPress={() => runCommand("capture_image")} />
            </View>
          </Card>

          <Link href={`/(app)/devices/${deviceId}/history`} style={styles.historyLink}>
            View history
          </Link>
        </>
      ) : (
        <Text style={styles.meta}>Loading dashboard...</Text>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  eyebrow: { fontSize: 13, fontWeight: "700", color: theme.colors.accent },
  title: { fontSize: 34, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: 16, color: theme.colors.textSecondary },
  metricsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  sectionTitle: { fontSize: 18, fontWeight: "700", color: theme.colors.textPrimary },
  image: { width: "100%", height: 220, borderRadius: 8, backgroundColor: "#dfe5e9" },
  meta: { fontSize: 14, color: theme.colors.textSecondary },
  error: { color: "#b42318" },
  commandMessage: { color: theme.colors.accent, fontWeight: "600" },
  buttonRow: { gap: 10 },
  historyLink: { color: theme.colors.accent, fontSize: 16, fontWeight: "700" },
});
