import { router, useLocalSearchParams } from "expo-router";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import { evtAssets } from "@/assets/evtAssets";
import { DashboardTopNav, Dot, EvtCard, EvtImageCard, EvtSectionHeader, MetricTile } from "@/components/evt/EvtComponents";
import { EmptyState } from "@/components/EmptyState";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { PrimaryButton } from "@/components/PrimaryButton";
import { ReadingTrendSection } from "@/components/ReadingTrendSection";
import { Screen } from "@/components/Screen";
import { SkeletonCard } from "@/components/Skeleton";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";
import type { Device, DeviceDashboard, SensorReading } from "@/types";
import {
  formatDeviceStatus,
  formatHumidity,
  formatLightState,
  formatRelativeAge,
  formatShortTimestamp,
  formatTemperature,
  formatTimestamp,
  formatWaterLevel,
} from "@/utils/formatting";

type DeviceDashboardScreenProps = {
  deviceId: string;
  showTopNav?: boolean;
};

export function DeviceDashboardScreen({ deviceId, showTopNav = false }: DeviceDashboardScreenProps) {
  const params = useLocalSearchParams<{ setup?: string }>();
  const {
    activeCommandAction,
    dashboard,
    error,
    commandMessage,
    commandTone,
    isActionBlocked,
    isCommandRunning,
    isLoading,
    refresh,
    runCommand,
    selectedRange,
    setSelectedRange,
  } = useDeviceDashboard(deviceId);
  const { token } = useSession();
  const setupComplete = params.setup === "complete";

  if (!deviceId) {
    return (
      <Screen>
        <DashboardTitle />
        {showTopNav ? <DashboardTopNav active="device" /> : null}
        <FeedbackBanner tone="error" message="Missing device id." />
      </Screen>
    );
  }

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      <DashboardTitle />
      {showTopNav ? <DashboardTopNav active="device" /> : null}

      {setupComplete ? <FeedbackBanner tone="success" message="Setup complete. The dashboard is ready when the first live readings arrive." /> : null}
      {error ? <FeedbackBanner tone="error" message={error} /> : null}
      {commandMessage ? (
        <FeedbackBanner
          message={commandMessage}
          tone={commandTone === "error" ? "error" : commandTone === "info" ? "info" : "success"}
        />
      ) : null}

      {dashboard ? (
        <DashboardContent
          activeCommandAction={activeCommandAction}
          dashboard={dashboard}
          deviceId={deviceId}
          imageHeaders={token ? { Authorization: `Bearer ${token}` } : undefined}
          isActionBlocked={isActionBlocked}
          isCommandRunning={isCommandRunning}
          isLoading={isLoading}
          runCommand={runCommand}
          selectedRange={selectedRange}
          setSelectedRange={setSelectedRange}
        />
      ) : error ? null : (
        <>
          <SkeletonCard />
          <SkeletonCard />
        </>
      )}
    </Screen>
  );
}

function DashboardTitle() {
  return <Text style={styles.screenTitle}>Dashboard</Text>;
}

function DashboardContent({
  activeCommandAction,
  dashboard,
  deviceId,
  imageHeaders,
  isActionBlocked,
  isCommandRunning,
  isLoading,
  runCommand,
  selectedRange,
  setSelectedRange,
}: {
  activeCommandAction: string | null;
  dashboard: DeviceDashboard;
  deviceId: string;
  imageHeaders?: Record<string, string>;
  isActionBlocked: (action: "light_on" | "light_off" | "light_intensity" | "pump_run" | "capture_image") => boolean;
  isCommandRunning: boolean;
  isLoading: boolean;
  runCommand: (action: "light_on" | "light_off" | "light_intensity" | "pump_run" | "capture_image", options?: { intensityPercent?: number }) => void;
  selectedRange: "24h" | "7d" | "30d" | "all";
  setSelectedRange: (range: "24h" | "7d" | "30d" | "all") => void;
}) {
  const device = dashboard.device;
  const latestReading = device.latestReading;
  const latestImage = dashboard.recentImages[0] ?? device.latestImage;
  const lightOn = (device.currentLightOn ?? latestReading?.lightOn) === true;
  const lightIntensity = clampPercent(device.currentLightIntensityPercent ?? latestReading?.lightIntensityPercent ?? (lightOn ? 100 : 0));
  const lightIntensitySupported = hasLightIntensitySupport(dashboard.hardwareHealth?.primary?.capabilities);
  const lightDisabled = isCommandRunning || device.status === "offline";
  const capturePending = activeCommandAction === "capture_image" || isActionBlocked("capture_image");
  const captureDisabled = isCommandRunning || capturePending || device.status === "offline";
  const nextLightAction = lightOn ? "light_off" : "light_on";
  const lightTogglePending = activeCommandAction === "light_on" || activeCommandAction === "light_off" || isActionBlocked("light_on") || isActionBlocked("light_off");
  const lightToggleLabel = lightTogglePending ? "pending" : "on/off";
  const scopedImageHeaders = latestImage?.url ? imageHeadersFor(latestImage.url, imageHeaders) : undefined;

  return (
    <>
      <EvtCard>
        <View style={styles.deviceSummary}>
          <View style={styles.deviceImageWrap}>
            <EvtImageCard
              accessibilityLabel="PlantLab plant summary image"
              imageHeaders={scopedImageHeaders}
              imageUrl={latestImage?.url}
              style={styles.deviceImage}
            />
          </View>
          <View style={styles.deviceCopy}>
            <Text style={styles.deviceName}>{device.name}</Text>
            <Text style={styles.deviceMeta}>Last viewed: {formatTimestamp(latestReading?.timestamp ?? device.lastSeenAt)}</Text>
            <Text style={styles.deviceMeta}>Latest photo: {formatTimestamp(latestImage?.capturedAt)}</Text>
          </View>
          <View style={styles.onlineBadge}>
            <Dot color={statusColor(device.status)} size={6} />
            <Text style={styles.onlineText}>{formatDeviceStatus(device.status)}</Text>
          </View>
        </View>
      </EvtCard>

      <EvtCard>
        <EvtSectionHeader title="Sensor Status" actionLabel={`Updated: ${formatShortTimestamp(latestReading?.timestamp)}`} />
        <View style={styles.sensorGrid}>
          <DashboardMetric label="Air Temp" reading={latestReading} value={formatTemperature(latestReading?.temperatureC)} series="temperatureC" tone="green" />
          <DashboardMetric label="Humidity" reading={latestReading} value={formatHumidity(latestReading?.humidityPercent)} series="humidityPercent" tone="green" />
          <DashboardMetric label="Water Temp" reading={latestReading} value={formatTemperature(latestReading?.waterTemperatureC)} series="waterTemperatureC" tone="purple" />
          <MetricTile label="Water Level" value={formatWaterLevel(latestReading)} meta={latestReading?.waterLevelState ? "Reported" : "Waiting"} tone="blue" />
        </View>
        {!latestReading ? (
          <EmptyState title="Waiting for first reading" message="Sensor metrics will populate after the device posts its next sample." />
        ) : null}
      </EvtCard>

      <EvtCard>
        <View style={styles.lightHeader}>
          <EvtSectionHeader title="Grow Light Control" />
          <Text style={styles.lightIndex}>Grow Light: {formatLightState(device)}</Text>
        </View>
        <View style={styles.lightTrack}>
          <View style={[styles.lightTrackFill, { width: `${lightIntensity}%` }]} />
        </View>
        <View style={styles.lightScale}>
          <Text style={styles.scaleText}>0%</Text>
          <Text style={styles.scaleText}>50%</Text>
          <Text style={styles.scaleText}>100%</Text>
        </View>
        <View style={styles.lightButtons}>
          {lightIntensitySupported
            ? [25, 50, 75, 100].map((value) => (
                <Pressable
                  accessibilityLabel={`Set grow light to ${value}%`}
                  accessibilityRole="button"
                  disabled={lightDisabled || isActionBlocked("light_intensity")}
                  key={value}
                  onPress={() => runCommand("light_intensity", { intensityPercent: value })}
                  style={[styles.lightButton, lightIntensity === value ? styles.lightButtonActive : null, lightDisabled ? styles.disabled : null]}
                >
                  <Text style={[styles.lightButtonText, lightIntensity === value ? styles.lightButtonTextActive : null]}>{value}%</Text>
                </Pressable>
              ))
            : null}
          <Pressable
            accessibilityRole="switch"
            accessibilityState={{ checked: lightOn, disabled: lightDisabled }}
            disabled={lightDisabled || lightTogglePending}
            onPress={() => runCommand(nextLightAction)}
            style={[styles.lightButton, styles.lightToggleButton, lightTogglePending || lightDisabled ? styles.disabled : null]}
          >
            <Text style={styles.lightButtonText}>{lightToggleLabel}</Text>
          </Pressable>
        </View>
      </EvtCard>

      <EvtCard>
        <EvtSectionHeader title="Latest Capture" actionLabel={latestImage ? formatShortTimestamp(latestImage.capturedAt) : "Waiting"} />
        <EvtImageCard
          accessibilityLabel="Latest PlantLab capture"
          imageHeaders={scopedImageHeaders}
          imageUrl={latestImage?.url}
        >
          <Pressable
            accessibilityLabel={capturePending ? "Capture pending" : "Capture photo"}
            accessibilityRole="button"
            disabled={captureDisabled}
            onPress={() => runCommand("capture_image")}
            style={[styles.cameraButton, captureDisabled ? styles.disabled : null]}
          >
            <Image source={evtAssets.cameraIcon} style={styles.cameraIcon} resizeMode="contain" />
          </Pressable>
        </EvtImageCard>
        <View style={styles.identificationRow}>
          <Image source={evtAssets.plantIdentificationIcon} style={styles.identificationIcon} resizeMode="contain" />
          <View style={styles.identificationCopy}>
            <Text style={styles.identificationLabel}>Plant Identification</Text>
            <Text style={styles.identificationTitle}>{device.plantType ?? "Plant profile not set"}</Text>
            <Text style={styles.identificationMeta}>{device.plantType ? "Profile data from device settings" : "Add plant type in settings"}</Text>
          </View>
          <Text style={styles.chevron}>&gt;</Text>
        </View>
      </EvtCard>

      <EvtCard>
        <EvtSectionHeader title="Latest shoot" subtitle="From Day 1 to Day 7" actionLabel={`${dashboard.recentImages.length} Photos`} />
        <GrowthStrip dashboard={dashboard} imageHeaders={imageHeaders} />
        <View style={styles.historyMetaRow}>
          <Text style={styles.historyMeta}>30 Days</Text>
          <Text style={styles.historyMeta}>{dashboard.recentImages.length} Photos</Text>
          <Text style={styles.historyMeta}>{dashboard.timelapse?.targetDurationSeconds ?? 15}s Timelapse</Text>
        </View>
        <PrimaryButton label="Watch Growth Video" tone="secondary" onPress={() => router.push(`/(app)/devices/${deviceId}/history`)} />
      </EvtCard>

      <ReadingTrendSection
        history={dashboard.history}
        title="Sensor Trends"
        selectedRange={selectedRange}
        onRangeChange={setSelectedRange}
        loading={isLoading}
      />

      <Pressable accessibilityRole="button" onPress={() => router.push(`/(app)/devices/${deviceId}/settings`)}>
        <EvtCard compact>
          <View style={styles.settingsRow}>
            <Image source={evtAssets.settingsTabIcon} style={styles.settingsIcon} resizeMode="contain" />
            <View style={styles.settingsCopy}>
              <Text style={styles.settingsTitle}>Device Settings</Text>
              <Text style={styles.settingsMeta}>Manage your device preferences and configurations</Text>
            </View>
            <Text style={styles.chevron}>&gt;</Text>
          </View>
        </EvtCard>
      </Pressable>
    </>
  );
}

function DashboardMetric({
  label,
  reading,
  series,
  tone,
  value,
}: {
  label: string;
  reading?: SensorReading;
  series: keyof Pick<SensorReading, "temperatureC" | "humidityPercent" | "waterTemperatureC">;
  tone: "green" | "purple";
  value: string;
}) {
  return <MetricTile label={label} value={value} meta={reading?.[series] !== undefined ? "Optimal" : "Waiting"} tone={tone} />;
}

function GrowthStrip({ dashboard, imageHeaders }: { dashboard: DeviceDashboard; imageHeaders?: Record<string, string> }) {
  const images = dashboard.recentImages.slice(0, 7);
  if (!images.length) {
    return <Text style={styles.emptyText}>Growth images will appear after camera captures are available.</Text>;
  }
  return (
    <View style={styles.growthStrip}>
      {images.map((image, index) => (
        <View key={image.id} style={styles.growthItem}>
          <Image source={imageSource(image.url, imageHeadersFor(image.url, imageHeaders))} style={styles.growthImage} resizeMode="cover" />
          <Text style={styles.growthDay}>Day {index + 1}</Text>
          <Text style={styles.growthDate}>{formatShortTimestamp(image.capturedAt)}</Text>
        </View>
      ))}
    </View>
  );
}

function imageHeadersFor(url: string, headers?: Record<string, string>): Record<string, string> | undefined {
  if (!headers) {
    return undefined;
  }
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  return path.startsWith("/api/images/") && path.split("?")[0].endsWith("/content") ? headers : undefined;
}

function imageSource(url: string, headers?: Record<string, string>) {
  return headers ? { uri: url, headers } : { uri: url };
}

function statusColor(status: Device["status"]) {
  if (status === "online") {
    return theme.colors.success;
  }
  if (status === "offline") {
    return theme.colors.danger;
  }
  if (status === "warning" || status === "degraded" || status === "stale") {
    return theme.colors.warning;
  }
  return theme.colors.textMuted;
}

function clampPercent(value: number): number {
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

const styles = StyleSheet.create({
  screenTitle: {
    color: theme.colors.textPrimary,
    fontSize: 16,
    fontWeight: "900",
    textAlign: "center",
  },
  deviceSummary: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  deviceImageWrap: {
    width: 92,
  },
  deviceImage: {
    aspectRatio: 1.15,
  },
  deviceCopy: {
    flex: 1,
    gap: 7,
  },
  deviceName: {
    color: theme.colors.textPrimary,
    fontSize: 17,
    fontWeight: "900",
  },
  deviceMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
  onlineBadge: {
    alignItems: "center",
    flexDirection: "row",
    gap: 5,
    position: "absolute",
    right: 12,
    top: 10,
  },
  onlineText: {
    color: theme.colors.success,
    fontSize: theme.evtTypography.caption,
  },
  sensorGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  lightHeader: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  lightIndex: {
    color: theme.colors.darkGreen,
    fontSize: theme.evtTypography.body,
    fontWeight: "900",
  },
  lightTrack: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radii.pill,
    height: 6,
    overflow: "hidden",
  },
  lightTrackFill: {
    backgroundColor: theme.colors.primaryGreen,
    borderRadius: theme.radii.pill,
    height: 6,
  },
  lightScale: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  scaleText: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
  lightButtons: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  lightButton: {
    alignItems: "center",
    borderColor: theme.colors.border,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    flex: 1,
    minHeight: 34,
    minWidth: 56,
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  lightButtonActive: {
    backgroundColor: theme.colors.accentSoft,
    borderColor: theme.colors.primaryGreen,
  },
  lightToggleButton: {
    borderColor: theme.colors.primaryGreen,
  },
  lightButtonText: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.caption,
    fontWeight: "800",
  },
  lightButtonTextActive: {
    color: theme.colors.primaryGreen,
  },
  cameraButton: {
    alignItems: "center",
    backgroundColor: theme.colors.white,
    borderRadius: 18,
    bottom: 12,
    height: 36,
    justifyContent: "center",
    position: "absolute",
    right: 12,
    width: 36,
  },
  cameraIcon: {
    height: 19,
    tintColor: theme.colors.textPrimary,
    width: 19,
  },
  identificationRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  identificationIcon: {
    height: 48,
    width: 48,
  },
  identificationCopy: {
    flex: 1,
    gap: 2,
  },
  identificationLabel: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.caption,
    fontWeight: "800",
  },
  identificationTitle: {
    color: theme.colors.textPrimary,
    fontSize: 17,
    fontWeight: "900",
  },
  identificationMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
  chevron: {
    color: theme.colors.textPrimary,
    fontSize: 20,
    fontWeight: "700",
  },
  historyMetaRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 14,
    justifyContent: "center",
  },
  historyMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.body,
  },
  growthStrip: {
    flexDirection: "row",
    gap: 8,
  },
  growthItem: {
    alignItems: "center",
    flex: 1,
    gap: 2,
  },
  growthImage: {
    aspectRatio: 1,
    borderRadius: 4,
    width: "100%",
  },
  growthDay: {
    color: theme.colors.textPrimary,
    fontSize: 9,
    fontWeight: "800",
  },
  growthDate: {
    color: theme.colors.textMuted,
    fontSize: 8,
  },
  emptyText: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.body,
  },
  settingsRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  settingsIcon: {
    height: 28,
    tintColor: theme.colors.textMuted,
    width: 28,
  },
  settingsCopy: {
    flex: 1,
    gap: 2,
  },
  settingsTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.sectionTitle,
    fontWeight: "900",
  },
  settingsMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
  disabled: {
    opacity: 0.48,
  },
});
