import { Link } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { CommandActivityPanel } from "@/components/CommandActivityPanel";
import { HardwareHealthPanel } from "@/components/HardwareHealthPanel";
import { MetricCard } from "@/components/MetricCard";
import { PrimaryButton } from "@/components/PrimaryButton";
import { ReadingTrendSection } from "@/components/ReadingTrendSection";
import { RecentImageGallery } from "@/components/RecentImageGallery";
import { Screen } from "@/components/Screen";
import { StatusChip } from "@/components/StatusChip";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

type DeviceDashboardScreenProps = {
  deviceId: string;
};

export function DeviceDashboardScreen({ deviceId }: DeviceDashboardScreenProps) {
  const {
    dashboard,
    usedMock,
    isLoading,
    error,
    commandMessage,
    commandTone,
    isCommandRunning,
    lastUpdatedAt,
    refresh,
    runCommand,
    selectedRange,
    setSelectedRange,
    isActionBlocked,
    activeCommandAction,
  } = useDeviceDashboard(deviceId);
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
              <Text style={styles.meta}>
                {lastUpdatedAt ? `Last updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Pull to refresh for the latest device state."}
              </Text>
            </View>
            <StatusChip label={usedMock ? "Mock mode" : dashboard.device.status} tone={usedMock ? "mock" : dashboard.device.status} />
          </View>

          {error ? <Text style={styles.error}>{error}</Text> : null}
          {commandMessage ? (
            <Text
              style={[
                styles.feedback,
                commandTone === "error" ? styles.feedbackError : commandTone === "info" ? styles.feedbackInfo : styles.feedbackSuccess,
              ]}
            >
              {commandMessage}
            </Text>
          ) : null}

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

          <ReadingTrendSection
            history={dashboard.history}
            title="Sensor trends"
            subtitle="Use the range tabs to request matching backend history windows for temperature, humidity, and soil moisture."
            selectedRange={selectedRange}
            onRangeChange={setSelectedRange}
            loading={isLoading}
          />

          <RecentImageGallery
            images={dashboard.recentImages}
            imageHeaders={session?.mode === "api" && token ? { Authorization: `Bearer ${token}` } : undefined}
          />

          <HardwareHealthPanel health={dashboard.hardwareHealth} />

          <CommandActivityPanel commands={dashboard.recentCommands} />

          <Card>
            <Text style={styles.sectionTitle}>Manual controls</Text>
            <View style={styles.buttonRow}>
              <PrimaryButton
                disabled={isCommandRunning || isActionBlocked("light_on")}
                label={activeCommandAction === "light_on" || isActionBlocked("light_on") ? "Light on pending" : isCommandRunning ? "Working..." : "Light on"}
                onPress={() => runCommand("light_on")}
              />
              <PrimaryButton
                disabled={isCommandRunning || isActionBlocked("light_off")}
                label={activeCommandAction === "light_off" || isActionBlocked("light_off") ? "Light off pending" : "Light off"}
                onPress={() => runCommand("light_off")}
              />
            </View>
            <View style={styles.buttonRow}>
              <PrimaryButton
                disabled={isCommandRunning || isActionBlocked("pump_run")}
                label={activeCommandAction === "pump_run" || isActionBlocked("pump_run") ? "Pump run pending" : "Pump run"}
                onPress={() => runCommand("pump_run")}
              />
              <PrimaryButton disabled label="Capture later" tone="secondary" onPress={() => {}} />
            </View>
            {dashboard.hardwareHealth?.lastCommand ? (
              <Text style={styles.meta}>
                Last command: {formatActionLabel(dashboard.hardwareHealth.lastCommand.action)} {formatStatusLabel(dashboard.hardwareHealth.lastCommand.status).toLowerCase()}.
              </Text>
            ) : null}
            <Text style={styles.meta}>Manual image capture is postponed while the shared backend capture contract stays in 501 mode.</Text>
          </Card>

          <Link href={`/(app)/devices/${deviceId}/history`} style={styles.historyLink}>
            View history
          </Link>
          <Link href={`/(app)/devices/${deviceId}/settings`} style={styles.historyLink}>
            Device settings
          </Link>
        </>
      ) : (
        <Text style={styles.meta}>Loading dashboard…</Text>
      )}
    </Screen>
  );
}

function formatActionLabel(action: string) {
  switch (action) {
    case "light_on":
      return "Light on";
    case "light_off":
      return "Light off";
    case "pump_run":
      return "Pump run";
    default:
      return "Capture image";
  }
}

function formatStatusLabel(status: string) {
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

const styles = StyleSheet.create({
  header: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  eyebrow: { fontSize: 13, fontWeight: "700", color: theme.colors.accent },
  title: { fontSize: 34, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: 16, color: theme.colors.textSecondary },
  meta: { fontSize: 14, color: theme.colors.textSecondary },
  metricsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  sectionTitle: { fontSize: 18, fontWeight: "700", color: theme.colors.textPrimary },
  error: { color: "#b42318" },
  feedback: { fontWeight: "600", borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10 },
  feedbackSuccess: { color: theme.colors.accent, backgroundColor: "#dff7e8" },
  feedbackError: { color: "#b42318", backgroundColor: "#fde4e4" },
  feedbackInfo: { color: "#6941c6", backgroundColor: "#efe7ff" },
  buttonRow: { gap: 10 },
  historyLink: { color: theme.colors.accent, fontSize: 16, fontWeight: "700" },
});
