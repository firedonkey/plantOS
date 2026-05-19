import { useEffect, useState } from "react";
import { Link, useLocalSearchParams } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { CommandActivityPanel } from "@/components/CommandActivityPanel";
import { EmptyState } from "@/components/EmptyState";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { HardwareHealthPanel } from "@/components/HardwareHealthPanel";
import { MetricCard } from "@/components/MetricCard";
import { ReadingTrendSection } from "@/components/ReadingTrendSection";
import { RecentImageGallery } from "@/components/RecentImageGallery";
import { Screen } from "@/components/Screen";
import { SkeletonCard } from "@/components/Skeleton";
import { StatusChip } from "@/components/StatusChip";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

type DeviceDashboardScreenProps = {
  deviceId: string;
};

export function DeviceDashboardScreen({ deviceId }: DeviceDashboardScreenProps) {
  const params = useLocalSearchParams<{ setup?: string }>();
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
  const latestReading = dashboard?.device.latestReading;
  const setupComplete = params.setup === "complete";
  const growLedOn = (dashboard?.device.currentLightOn ?? dashboard?.device.latestReading?.lightOn) === true;
  const growLedIntensityPercent = dashboard?.device.currentLightIntensityPercent ?? dashboard?.device.latestReading?.lightIntensityPercent;
  const lightIntensitySupported = hasLightIntensitySupport(dashboard?.hardwareHealth?.primary?.capabilities);
  const currentLightIntensity = clampLightIntensity(growLedIntensityPercent ?? (growLedOn ? 100 : 0));
  const [lightIntensityDraft, setLightIntensityDraft] = useState(currentLightIntensity);
  const pendingLightOn = activeCommandAction === "light_on" || isActionBlocked("light_on");
  const pendingLightOff = activeCommandAction === "light_off" || isActionBlocked("light_off");
  const pendingLightIntensity = activeCommandAction === "light_intensity" || isActionBlocked("light_intensity");
  const nextLightAction = growLedOn ? "light_off" : "light_on";
  const lightToggleDisabled = isCommandRunning || pendingLightOn || pendingLightOff;
  const lightIntensityDisabled = isCommandRunning || pendingLightIntensity;
  const lightToggleLabel = pendingLightOn
    ? "Turning on..."
    : pendingLightOff
      ? "Turning off..."
      : isCommandRunning
        ? "Working..."
        : growLedOn
          ? "Turn off"
          : "Turn on";

  useEffect(() => {
    setLightIntensityDraft(currentLightIntensity);
  }, [currentLightIntensity, dashboard?.device.id]);

  if (!deviceId) {
    return (
      <Screen>
        <FeedbackBanner tone="error" message="Missing device id." />
      </Screen>
    );
  }

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      {dashboard ? (
        <>
          <Card variant="hero">
            <View style={styles.header}>
              <View style={{ flex: 1, gap: 8 }}>
                <Text style={styles.eyebrow}>PLANTLAB DEVICE</Text>
                <Text style={styles.title}>{dashboard.device.name}</Text>
                <Text style={styles.subtitle}>
                  {dashboard.device.plantType ?? "Plant type not set"} | {dashboard.device.location ?? "No location set"}
                </Text>
                <Text style={styles.meta}>
                  {lastUpdatedAt ? `Updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Pull to refresh for the latest device state."}
                </Text>
              </View>
              <StatusChip label={usedMock ? "Mock mode" : dashboard.device.status} tone={usedMock ? "mock" : dashboard.device.status} />
            </View>
          </Card>

          {setupComplete ? <FeedbackBanner tone="success" message="Setup complete. The dashboard is ready when the first live readings arrive." /> : null}
          {error ? <FeedbackBanner tone="error" message={error} /> : null}
          {commandMessage ? (
            <FeedbackBanner
              message={commandMessage}
              tone={commandTone === "error" ? "error" : commandTone === "info" ? "info" : "success"}
            />
          ) : null}

          <Card>
            <View style={{ flex: 1, gap: 8 }}>
              <Text style={styles.sectionTitle}>Primary readings</Text>
              <Text style={styles.meta}>Latest air and water sensor state.</Text>
            </View>
            <View style={styles.metricsGrid}>
              <MetricCard label="Air temp" value={`${latestReading?.temperatureC?.toFixed(1) ?? "--"} C`} meta={formatAge(latestReading?.timestamp)} />
              <MetricCard label="Humidity" value={`${latestReading?.humidityPercent?.toFixed(1) ?? "--"}%`} meta={formatAge(latestReading?.timestamp)} />
              <MetricCard label="Water temp" value={`${latestReading?.waterTemperatureC?.toFixed(1) ?? "--"} C`} meta={formatAge(latestReading?.timestamp)} />
              <MetricCard label="Water level" value={formatWaterLevel(latestReading?.waterLevelState, latestReading?.waterLevelRaw)} meta={latestReading?.waterLevelRaw !== undefined ? `Raw ${latestReading.waterLevelRaw}` : "Waiting"} />
            </View>
            {!latestReading ? (
              <EmptyState title="Waiting for first reading" message="Primary metrics will populate after the device posts its next sensor sample." />
            ) : null}
          </Card>

          <Card variant="inset">
            <View style={styles.growLedRow}>
              <View style={styles.growLedCopy}>
                <Text style={styles.sectionTitle}>Grow LED</Text>
                <Text style={styles.meta}>
                  {growLedOn ? (lightIntensitySupported ? `On | ${currentLightIntensity}%` : "On") : "Off"}
                </Text>
              </View>
              <ToggleButton
                disabled={lightToggleDisabled}
                label={lightToggleLabel}
                on={growLedOn}
                onPress={() => runCommand(nextLightAction)}
              />
            </View>
            {lightIntensitySupported ? (
              <LightIntensityStepper
                disabled={lightIntensityDisabled}
                onChange={setLightIntensityDraft}
                onSubmit={() => runCommand("light_intensity", { intensityPercent: lightIntensityDraft })}
                pending={pendingLightIntensity}
                unchanged={lightIntensityDraft === currentLightIntensity}
                value={lightIntensityDraft}
              />
            ) : null}
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
        <FeedbackBanner tone="error" message={error} />
      ) : (
        <>
          <SkeletonCard />
          <SkeletonCard />
        </>
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

function LightIntensityStepper({
  disabled,
  onChange,
  onSubmit,
  pending,
  unchanged,
  value,
}: {
  disabled: boolean;
  onChange: (value: number) => void;
  onSubmit: () => void;
  pending: boolean;
  unchanged: boolean;
  value: number;
}) {
  const decrease = () => onChange(clampLightIntensity(value - 5));
  const increase = () => onChange(clampLightIntensity(value + 5));
  return (
    <View style={styles.intensityControl}>
      <View style={styles.intensityHeader}>
        <Text style={styles.intensityLabel}>Intensity</Text>
        <Text style={styles.intensityValue}>{value}%</Text>
      </View>
      <View style={styles.intensityActions}>
        <Pressable
          accessibilityLabel="Decrease grow LED intensity"
          accessibilityRole="button"
          disabled={disabled || value <= 0}
          onPress={decrease}
          style={[styles.intensityStepButton, disabled || value <= 0 ? styles.intensityDisabled : null]}
        >
          <Text style={styles.intensityStepLabel}>-</Text>
        </Pressable>
        <Pressable
          accessibilityLabel="Increase grow LED intensity"
          accessibilityRole="button"
          disabled={disabled || value >= 100}
          onPress={increase}
          style={[styles.intensityStepButton, disabled || value >= 100 ? styles.intensityDisabled : null]}
        >
          <Text style={styles.intensityStepLabel}>+</Text>
        </Pressable>
        <Pressable
          accessibilityLabel="Set grow LED intensity"
          accessibilityRole="button"
          disabled={disabled || unchanged}
          onPress={onSubmit}
          style={[styles.intensityApplyButton, disabled || unchanged ? styles.intensityDisabled : null]}
        >
          <Text style={styles.intensityApplyLabel}>{pending ? "Setting" : "Set"}</Text>
        </Pressable>
      </View>
    </View>
  );
}

function formatWaterLevel(state?: string, raw?: number) {
  const label = state ? state.charAt(0).toUpperCase() + state.slice(1) : "--";
  return raw !== undefined ? `${label} (${raw})` : label;
}

function clampLightIntensity(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(value)));
}

function hasLightIntensitySupport(capabilities?: Record<string, unknown>): boolean {
  if (!capabilities) {
    return false;
  }
  if (
    capabilities.light_intensity_control === true ||
    capabilities.light_dimming === true ||
    capabilities.light_pwm === true
  ) {
    return true;
  }
  const modes = capabilities.light_control_modes;
  if (!Array.isArray(modes)) {
    return false;
  }
  return modes.some((mode) => ["intensity", "dimming", "pwm"].includes(String(mode).toLowerCase()));
}

function formatAge(timestamp?: string) {
  if (!timestamp) {
    return "Waiting";
  }
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", gap: theme.spacing.md, alignItems: "flex-start" },
  eyebrow: { fontSize: theme.typography.eyebrow, fontWeight: "800", color: theme.colors.accent },
  title: { fontSize: theme.typography.screenTitle, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: theme.typography.bodyLarge, color: theme.colors.textSecondary },
  meta: { fontSize: theme.typography.body, color: theme.colors.textSecondary, lineHeight: 20 },
  metricsGrid: { flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.md },
  sectionTitle: { fontSize: theme.typography.sectionTitle, fontWeight: "800", color: theme.colors.textPrimary },
  growLedRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: theme.spacing.md,
    justifyContent: "space-between",
  },
  growLedCopy: { flex: 1, gap: 4 },
  intensityControl: {
    borderTopColor: theme.colors.borderSoft,
    borderTopWidth: 1,
    gap: theme.spacing.sm,
    paddingTop: theme.spacing.md,
  },
  intensityHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  intensityLabel: { color: theme.colors.textSecondary, fontSize: theme.typography.body, fontWeight: "700" },
  intensityValue: { color: theme.colors.textPrimary, fontSize: 18, fontWeight: "800" },
  intensityActions: { alignItems: "center", flexDirection: "row", gap: theme.spacing.sm },
  intensityStepButton: {
    alignItems: "center",
    backgroundColor: theme.colors.surfaceInset,
    borderColor: theme.colors.border,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    height: 44,
    justifyContent: "center",
    width: 52,
  },
  intensityStepLabel: { color: theme.colors.textPrimary, fontSize: 22, fontWeight: "800" },
  intensityApplyButton: {
    alignItems: "center",
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radii.md,
    flex: 1,
    height: 44,
    justifyContent: "center",
  },
  intensityApplyLabel: { color: theme.colors.white, fontSize: 15, fontWeight: "800" },
  intensityDisabled: { opacity: 0.55 },
  toggleSwitch: {
    width: 108,
    height: 48,
    borderRadius: theme.radii.md,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    position: "relative",
  },
  toggleSwitchOn: { backgroundColor: theme.colors.accent },
  toggleSwitchOff: { backgroundColor: theme.colors.border },
  toggleSwitchDisabled: { opacity: 0.6 },
  toggleLabel: {
    fontSize: 14,
    fontWeight: "800",
    letterSpacing: 0,
    zIndex: 1,
  },
  toggleLabelOn: { color: theme.colors.white },
  toggleLabelOff: { color: theme.colors.textSecondary, marginLeft: 44 },
  toggleKnob: {
    position: "absolute",
    top: 6,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: theme.colors.white,
  },
  toggleKnobOn: { right: 7 },
  toggleKnobOff: { left: 7 },
  settingsButton: {
    width: "100%",
    borderRadius: theme.radii.md,
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: "center",
    backgroundColor: theme.colors.accent,
  },
  settingsButtonLabel: {
    color: theme.colors.white,
    fontSize: 15,
    fontWeight: "700",
  },
});
