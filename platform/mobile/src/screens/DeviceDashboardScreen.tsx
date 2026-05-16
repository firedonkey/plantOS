import { Link } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { CommandActivityPanel } from "@/components/CommandActivityPanel";
import { HardwareHealthPanel } from "@/components/HardwareHealthPanel";
import { MetricCard } from "@/components/MetricCard";
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
  const { token } = useSession();
  const growLedOn = dashboard?.device.latestReading?.lightOn === true;
  const pendingLightOn = activeCommandAction === "light_on" || isActionBlocked("light_on");
  const pendingLightOff = activeCommandAction === "light_off" || isActionBlocked("light_off");
  const nextLightAction = growLedOn ? "light_off" : "light_on";
  const lightToggleDisabled = isCommandRunning || pendingLightOn || pendingLightOff;
  const lightToggleLabel = pendingLightOn
    ? "Turning on..."
    : pendingLightOff
      ? "Turning off..."
      : isCommandRunning
        ? "Working..."
        : growLedOn
          ? "Turn off"
          : "Turn on";

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
              <MetricCard label="Air temp" value={`${dashboard.device.latestReading?.temperatureC?.toFixed(1) ?? "--"} C`} />
              <MetricCard label="Humidity" value={`${dashboard.device.latestReading?.humidityPercent?.toFixed(1) ?? "--"}%`} />
              <MetricCard label="Water temp" value={`${dashboard.device.latestReading?.waterTemperatureC?.toFixed(1) ?? "--"} C`} />
              <MetricCard label="Water level" value={formatWaterLevel(dashboard.device.latestReading?.waterLevelState, dashboard.device.latestReading?.waterLevelRaw)} />
              <MetricCard label="Grow LED" value={growLedOn ? "On" : "Off"}>
                <ToggleButton
                  disabled={lightToggleDisabled}
                  label={lightToggleLabel}
                  on={growLedOn}
                  onPress={() => runCommand(nextLightAction)}
                />
              </MetricCard>
            </View>
          </Card>

          <RecentImageGallery
            images={dashboard.recentImages}
            imageHeaders={token ? { Authorization: `Bearer ${token}` } : undefined}
            captureDisabled={isCommandRunning || isActionBlocked("capture_image")}
            captureLabel={
              activeCommandAction === "capture_image" || isActionBlocked("capture_image")
                ? "Capture pending"
                : isCommandRunning
                  ? "Working..."
                  : "Capture image"
            }
            onCapture={() => runCommand("capture_image")}
          />

          <ReadingTrendSection
            history={dashboard.history}
            title="Sensor trends"
            subtitle="Use the range tabs to request matching backend history windows for air and water readings."
            selectedRange={selectedRange}
            onRangeChange={setSelectedRange}
            loading={isLoading}
          />

          <HardwareHealthPanel health={dashboard.hardwareHealth} />

          <CommandActivityPanel commands={dashboard.recentCommands} />

          <Link href={`/(app)/devices/${deviceId}/settings`} asChild>
            <Pressable accessibilityRole="button" style={styles.settingsButton}>
              <Text style={styles.settingsButtonLabel}>Device settings</Text>
            </Pressable>
          </Link>
        </>
      ) : error ? (
        <Text style={styles.error}>{error}</Text>
      ) : (
        <Text style={styles.meta}>Loading dashboard…</Text>
      )}
    </Screen>
  );
}

function ToggleButton({ disabled, label, on, onPress }: { disabled: boolean; label: string; on: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="switch"
      accessibilityState={{ checked: on, disabled }}
      disabled={disabled}
      onPress={onPress}
      style={[styles.toggleSwitch, on ? styles.toggleSwitchOn : styles.toggleSwitchOff, disabled ? styles.toggleSwitchDisabled : null]}
    >
      <Text style={[styles.toggleLabel, on ? styles.toggleLabelOn : styles.toggleLabelOff]}>{on ? "ON" : "OFF"}</Text>
      <View style={[styles.toggleKnob, on ? styles.toggleKnobOn : styles.toggleKnobOff]} />
    </Pressable>
  );
}

function formatWaterLevel(state?: string, raw?: number) {
  const label = state ? state.charAt(0).toUpperCase() + state.slice(1) : "--";
  return raw !== undefined ? `${label} (${raw})` : label;
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
  toggleSwitch: {
    width: 108,
    height: 48,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    position: "relative",
  },
  toggleSwitchOn: { backgroundColor: theme.colors.accent },
  toggleSwitchOff: { backgroundColor: "#d7dee3" },
  toggleSwitchDisabled: { opacity: 0.6 },
  toggleLabel: {
    fontSize: 14,
    fontWeight: "800",
    letterSpacing: 0,
    zIndex: 1,
  },
  toggleLabelOn: { color: "#ffffff" },
  toggleLabelOff: { color: theme.colors.textSecondary, marginLeft: 44 },
  toggleKnob: {
    position: "absolute",
    top: 6,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#ffffff",
  },
  toggleKnobOn: { right: 7 },
  toggleKnobOff: { left: 7 },
  settingsButton: {
    width: "100%",
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: "center",
    backgroundColor: theme.colors.accent,
  },
  settingsButtonLabel: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "700",
  },
});
