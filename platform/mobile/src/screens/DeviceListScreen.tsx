import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useMemo } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import { evtAssets } from "@/assets/evtAssets";
import { Dot, EvtCard, EvtImageCard, EvtSectionHeader, MetricTile, PlantLabHeader, SmallActionCard } from "@/components/evt/EvtComponents";
import { EmptyState } from "@/components/EmptyState";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { SensorLineChart } from "@/components/SensorLineChart";
import { SkeletonCard } from "@/components/Skeleton";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { useDevices } from "@/hooks/useDevices";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";
import type { Device, DeviceCommand, DeviceDashboard, HardwareHealth } from "@/types";
import {
  formatCommandAction,
  formatDeviceStatus,
  formatHumidity,
  formatLightState,
  formatRelativeAge,
  formatShortTimestamp,
  formatTemperature,
  formatWaterLevel,
} from "@/utils/formatting";

export function DeviceListScreen() {
  const { devices, usedMock, isLoading, error, refresh, lastUpdatedAt } = useDevices();
  const params = useLocalSearchParams<{ hiddenDeviceId?: string; refreshAt?: string }>();
  const hiddenDeviceIds = useMemo(() => {
    const raw = Array.isArray(params.hiddenDeviceId) ? params.hiddenDeviceId : params.hiddenDeviceId ? [params.hiddenDeviceId] : [];
    return new Set(raw.map((value) => String(value).trim()).filter(Boolean));
  }, [params.hiddenDeviceId]);
  const visibleDevices = useMemo(
    () => devices.filter((device) => !hiddenDeviceIds.has(device.id)),
    [devices, hiddenDeviceIds],
  );
  const selectedDevice = visibleDevices[0];

  useFocusEffect(
    useCallback(() => {
      void refresh({ background: true });
    }, [refresh, params.refreshAt]),
  );

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      <PlantLabHeader />

      <View style={styles.quickActions}>
        <SmallActionCard
          body="Explore Plant Cases"
          icon={<Image source={evtAssets.deviceTabIcon} style={styles.actionImage} resizeMode="contain" />}
          onPress={() => router.push("/(app)/case" as never)}
          title="Cases"
        />
        <SmallActionCard
          body="View Full Analytics"
          icon={<Image source={evtAssets.dataIcon} style={styles.actionImage} resizeMode="contain" />}
          onPress={() => router.push("/(app)/dashboard" as never)}
          title="Dashboard"
        />
      </View>

      {usedMock ? <FeedbackBanner tone="info" message="Simulator data is active." /> : null}
      {error ? <FeedbackBanner tone="error" message={error} /> : null}

      {isLoading && !visibleDevices.length ? <SkeletonCard /> : null}
      {!isLoading && !visibleDevices.length ? (
        <EvtCard>
          <EmptyState title="No devices yet" message="Add a PlantLab device to start tracking readings, images, and hardware health." />
          <PrimaryButton label="Add device" onPress={() => router.push("/(app)/devices/add")} />
        </EvtCard>
      ) : null}

      {selectedDevice ? (
        <HomeDeviceExperience
          baseDevice={selectedDevice}
          deviceCount={visibleDevices.length}
          lastUpdatedAt={lastUpdatedAt}
        />
      ) : null}
    </Screen>
  );
}

function HomeDeviceExperience({
  baseDevice,
  deviceCount,
  lastUpdatedAt,
}: {
  baseDevice: Device;
  deviceCount: number;
  lastUpdatedAt: string | null;
}) {
  const {
    activeCommandAction,
    dashboard,
    error,
    isActionBlocked,
    isCommandRunning,
    isLoading,
    refresh,
    runCommand,
  } = useDeviceDashboard(baseDevice.id);
  const { token } = useSession();
  const device = dashboard?.device ?? baseDevice;
  const latestReading = device.latestReading;
  const latestImage = dashboard?.recentImages[0] ?? device.latestImage;
  const imageHeaders = latestImage?.url ? imageHeadersFor(latestImage.url, token) : undefined;
  const captureDisabled = isCommandRunning || isActionBlocked("capture_image");
  const captureLabel =
    activeCommandAction === "capture_image" || isActionBlocked("capture_image")
      ? "Capture pending"
      : "Capture Photo";
  const alerts = buildAttentionItems(dashboard);

  return (
    <>
      {deviceCount > 1 ? (
        <EvtCard compact>
          <Text style={styles.selectorTitle}>Current device</Text>
          <Text style={styles.selectorText}>{device.name} is selected. Open Devices to manage the full list.</Text>
        </EvtCard>
      ) : null}
      {error ? <FeedbackBanner tone="error" message={error} /> : null}

      <EvtCard>
        <EvtSectionHeader title="Latest Capture" actionLabel={latestImage ? formatShortTimestamp(latestImage.capturedAt) : "Waiting"} />
        <EvtImageCard
          accessibilityLabel="Latest PlantLab camera capture"
          imageHeaders={imageHeaders}
          imageUrl={latestImage?.url}
          style={styles.latestImage}
        >
          <Pressable
            accessibilityLabel={captureLabel}
            accessibilityRole="button"
            disabled={captureDisabled}
            onPress={() => runCommand("capture_image")}
            style={[styles.cameraButton, captureDisabled ? styles.disabled : null]}
          >
            <Image source={evtAssets.cameraIcon} style={styles.cameraIcon} resizeMode="contain" />
          </Pressable>
        </EvtImageCard>
        <Pressable accessibilityRole="button" onPress={() => router.push(`/(app)/devices/${device.id}`)} style={styles.identificationRow}>
          <View style={styles.identificationIcon}>
            <Image source={evtAssets.plantIdentificationIcon} style={styles.identificationImage} resizeMode="contain" />
          </View>
          <View style={styles.identificationCopy}>
            <Text style={styles.identificationLabel}>Plant Identification</Text>
            <Text style={styles.identificationTitle}>{device.plantType ?? "Plant profile not set"}</Text>
            <Text style={styles.identificationMeta}>
              {device.plantType ? "Profile data from device settings" : "Add plant type in device settings"}
            </Text>
          </View>
          <Text style={styles.chevron}>&gt;</Text>
        </Pressable>
      </EvtCard>

      <View style={styles.sectionSpacer}>
        <EvtSectionHeader title="Environment Overview" actionLabel="View All" onActionPress={() => router.push("/(app)/dashboard" as never)} />
        <View style={styles.metricRow}>
          <MetricTile label="Temperature" value={formatTemperature(latestReading?.temperatureC)} meta={metricFreshness(latestReading?.timestamp)} tone="green" />
          <MetricTile label="Humidity" value={formatHumidity(latestReading?.humidityPercent)} meta={metricFreshness(latestReading?.timestamp)} tone="green" />
          <MetricTile label="Water Level" value={formatWaterLevel(latestReading)} meta="Reported" tone="blue" />
          <MetricTile label="Light" value={formatLightState(device)} meta="Reported" tone="orange" />
        </View>
      </View>

      <EvtCard>
        <EvtSectionHeader
          title="Attention Needed"
          actionLabel={`${alerts.length} Issue${alerts.length === 1 ? "" : "s"} Detected`}
          icon={alerts.length ? <Text style={styles.warningIcon}>▲</Text> : <Dot color={theme.colors.success} />}
        />
        {alerts.length ? (
          <View style={styles.alertStack}>
            {alerts.map((item) => (
              <View key={item.title} style={styles.alertRow}>
                <View style={styles.alertIcon}>
                  <Text style={styles.alertGlyph}>{item.glyph}</Text>
                </View>
                <View style={styles.alertCopy}>
                  <Text style={styles.alertTitle}>{item.title}</Text>
                  <Text style={styles.alertBody}>{item.body}</Text>
                </View>
                <View style={styles.alertButton}>
                  <Text style={styles.alertButtonText}>{item.action}</Text>
                </View>
              </View>
            ))}
          </View>
        ) : (
          <Text style={styles.bodyText}>No active care or device issues are reported.</Text>
        )}
      </EvtCard>

      <EvtCard>
        <EvtSectionHeader title="Live Monitor" actionLabel={formatDeviceStatus(device.status)} icon={<Dot color={statusColor(device.status)} />} />
        <Text style={styles.liveValue}>{formatTemperature(latestReading?.temperatureC)}</Text>
        <Text style={styles.liveCaption}>Real-time Temperature</Text>
        <SensorLineChart
          color={theme.colors.primaryGreen}
          height={150}
          minDomainSpan={5}
          points={(dashboard?.history ?? []).map((reading) => ({ timestamp: reading.timestamp, value: reading.temperatureC }))}
        />
      </EvtCard>

      <View style={styles.metricRow}>
        <MetricTile label="Humidity" value={formatHumidity(latestReading?.humidityPercent)} meta="Optimal" tone="green" />
        <MetricTile label="Grow Light" value={formatLightState(device)} meta="Reported" tone="orange" />
        <MetricTile label="Water Temp" value={formatTemperature(latestReading?.waterTemperatureC)} meta="Optimal" tone="blue" />
      </View>

      <EvtCard compact>
        <View style={styles.healthRow}>
          <View style={styles.healthCopy}>
            <Text style={styles.healthTitle}>Device Health</Text>
            <Text style={styles.healthMeta}>{healthSummary(dashboard?.hardwareHealth, device)}</Text>
          </View>
          <View style={styles.statusPill}>
            <Dot color={statusColor(device.status)} />
            <Text style={styles.statusPillText}>{formatDeviceStatus(device.status)}</Text>
          </View>
        </View>
      </EvtCard>

      <View style={styles.twoColumn}>
        <EvtCard style={styles.twoColumnCard}>
          <EvtSectionHeader title="Recent Events" actionLabel="View All" onActionPress={() => router.push(`/(app)/devices/${device.id}/history`)} />
          <View style={styles.eventList}>
            {(dashboard?.recentCommands ?? []).slice(0, 4).map((command) => (
              <EventRow command={command} key={command.id} />
            ))}
            {dashboard && dashboard.recentCommands.length === 0 ? <Text style={styles.emptyText}>No recent commands.</Text> : null}
          </View>
        </EvtCard>
        <EvtCard style={styles.twoColumnCard}>
          <EvtSectionHeader title="Grow Light" />
          <Text style={styles.lightValue}>{formatLightState(device)}</Text>
          <Text style={styles.lightMeta}>Current reported state</Text>
          <View style={styles.lightArc}>
            <View style={styles.lightArcFill} />
            <Dot color={theme.colors.primaryGreen} size={5} />
          </View>
          <PrimaryButton label={captureLabel} onPress={() => runCommand("capture_image")} disabled={captureDisabled} />
        </EvtCard>
      </View>

      <EvtCard>
        <EvtSectionHeader title="Growth History" subtitle="From Day 1 to Day 7" actionLabel="View Full History" onActionPress={() => router.push(`/(app)/devices/${device.id}/history`)} />
        <GrowthStrip dashboard={dashboard} imageHeaders={token ? { Authorization: `Bearer ${token}` } : undefined} />
      </EvtCard>

      <EvtCard>
        <EvtSectionHeader title="Growth Story" />
        <Text style={styles.storyTitle}>Your {device.plantType ?? "plant"} is growing steadily.</Text>
        <Text style={styles.bodyText}>
          {lastUpdatedAt
            ? `The latest mobile refresh was ${formatRelativeAge(lastUpdatedAt)}.`
            : "Refresh the dashboard to see the latest story from live device data."}
        </Text>
      </EvtCard>

      {isLoading && !dashboard ? <SkeletonCard /> : null}
    </>
  );
}

function EventRow({ command }: { command: DeviceCommand }) {
  return (
    <View style={styles.eventRow}>
      <Dot color={command.status === "failed" ? theme.colors.danger : theme.colors.primaryGreen} size={8} />
      <Text style={styles.eventTitle} numberOfLines={1}>{formatCommandAction(command.action)}</Text>
      <Text style={styles.eventTime}>{formatRelativeAge(command.updatedAt ?? command.createdAt)}</Text>
    </View>
  );
}

function GrowthStrip({ dashboard, imageHeaders }: { dashboard: DeviceDashboard | null; imageHeaders?: Record<string, string> }) {
  const images = dashboard?.recentImages.slice(0, 7) ?? [];
  if (!images.length) {
    return <Text style={styles.emptyText}>Growth images will appear after camera captures are available.</Text>;
  }
  return (
    <View style={styles.growthStrip}>
      {images.map((image, index) => (
        <View key={image.id} style={styles.growthItem}>
          <Image source={imageSource(image.url, imageHeaders)} style={styles.growthImage} resizeMode="cover" />
          <Text style={styles.growthDay}>Day {index + 1}</Text>
          <Text style={styles.growthDate}>{formatShortTimestamp(image.capturedAt)}</Text>
        </View>
      ))}
    </View>
  );
}

function buildAttentionItems(dashboard: DeviceDashboard | null) {
  const device = dashboard?.device;
  const health = dashboard?.hardwareHealth;
  const items: Array<{ title: string; body: string; glyph: string; action: string }> = [];
  if (device?.status === "offline" || device?.status === "stale") {
    items.push({
      title: "Device Offline",
      body: "Recent values are preserved while the device reconnects.",
      glyph: "!",
      action: "Review",
    });
  }
  if (health?.friendlyStatus === "needs_attention" || health?.overallStatus === "warning" || health?.overallStatus === "degraded") {
    items.push({
      title: "Hardware Review",
      body: health.attentionReasons?.[0] ? health.attentionReasons[0].replace(/_/g, " ") : "A hardware signal needs review.",
      glyph: "i",
      action: "View",
    });
  }
  if (dashboard?.device.latestReading?.waterLevelState && dashboard.device.latestReading.waterLevelState !== "ok") {
    items.push({
      title: "Watering Reminder",
      body: "The water level is not reporting an optimal state.",
      glyph: "w",
      action: "Water Now",
    });
  }
  return items.slice(0, 2);
}

function healthSummary(health: HardwareHealth | undefined, device: Device): string {
  if (health?.friendlyStatus === "needs_attention") {
    return "A device subsystem needs review.";
  }
  if (device.status === "offline") {
    return "Device is offline. Data may be stale.";
  }
  if (health?.lastHeartbeatAt) {
    return `Last heartbeat ${formatRelativeAge(health.lastHeartbeatAt)}.`;
  }
  return "All systems operational.";
}

function metricFreshness(timestamp?: string): string {
  return timestamp ? formatRelativeAge(timestamp) : "Waiting";
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

function imageHeadersFor(url: string, token: string | null): Record<string, string> | undefined {
  if (!token) {
    return undefined;
  }
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  return path.startsWith("/api/images/") && path.split("?")[0].endsWith("/content") ? { Authorization: `Bearer ${token}` } : undefined;
}

function imageSource(url: string, headers?: Record<string, string>) {
  return headers ? { uri: url, headers } : { uri: url };
}

const styles = StyleSheet.create({
  quickActions: {
    flexDirection: "row",
    gap: 10,
  },
  actionImage: {
    height: 26,
    tintColor: theme.colors.textPrimary,
    width: 26,
  },
  selectorTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.body,
    fontWeight: "800",
  },
  selectorText: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.body,
  },
  latestImage: {
    aspectRatio: 315 / 160,
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
    alignItems: "center",
    backgroundColor: theme.colors.surfaceMuted,
    borderRadius: theme.radii.sm,
    height: 54,
    justifyContent: "center",
    width: 54,
  },
  identificationImage: {
    height: 36,
    width: 36,
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
    fontSize: 26,
  },
  sectionSpacer: {
    gap: theme.spacing.sm,
  },
  metricRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  warningIcon: {
    color: theme.colors.warning,
    fontSize: theme.evtTypography.body,
    fontWeight: "900",
  },
  alertStack: {
    gap: 12,
  },
  alertRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  alertIcon: {
    alignItems: "center",
    backgroundColor: theme.colors.warningSoft,
    borderRadius: theme.radii.sm,
    height: 40,
    justifyContent: "center",
    width: 40,
  },
  alertGlyph: {
    color: theme.colors.warning,
    fontSize: theme.evtTypography.bodyLarge,
    fontWeight: "900",
  },
  alertCopy: {
    flex: 1,
    gap: 2,
  },
  alertTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.body,
    fontWeight: "800",
  },
  alertBody: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.caption,
    lineHeight: 15,
  },
  alertButton: {
    borderColor: theme.colors.primaryGreen,
    borderRadius: theme.radii.sm,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  alertButtonText: {
    color: theme.colors.primaryGreen,
    fontSize: theme.evtTypography.caption,
    fontWeight: "900",
  },
  bodyText: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.body,
    lineHeight: 19,
  },
  liveValue: {
    color: theme.colors.primaryGreen,
    fontSize: 28,
    fontWeight: "900",
  },
  liveCaption: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.caption,
    fontWeight: "800",
  },
  healthRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    gap: theme.spacing.md,
  },
  healthCopy: {
    flex: 1,
    gap: 2,
  },
  healthTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.sectionTitle,
    fontWeight: "900",
  },
  healthMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
  statusPill: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
  },
  statusPillText: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.body,
  },
  twoColumn: {
    flexDirection: "row",
    gap: 10,
  },
  twoColumnCard: {
    flex: 1,
    minHeight: 160,
  },
  eventList: {
    gap: 12,
  },
  eventRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
  },
  eventTitle: {
    color: theme.colors.textPrimary,
    flex: 1,
    fontSize: theme.evtTypography.caption,
    fontWeight: "800",
  },
  eventTime: {
    color: theme.colors.textMuted,
    fontSize: 9,
  },
  emptyText: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.body,
    lineHeight: 18,
  },
  lightValue: {
    color: theme.colors.primaryGreen,
    fontSize: 22,
    fontWeight: "900",
  },
  lightMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
  lightArc: {
    alignItems: "center",
    borderColor: theme.colors.border,
    borderRadius: 48,
    borderTopColor: theme.colors.primaryGreen,
    borderWidth: 7,
    height: 74,
    justifyContent: "center",
    alignSelf: "center",
    width: 74,
  },
  lightArcFill: {
    display: "none",
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
  storyTitle: {
    color: theme.colors.primaryGreen,
    fontSize: theme.evtTypography.body,
    fontWeight: "900",
  },
  disabled: {
    opacity: 0.56,
  },
});
