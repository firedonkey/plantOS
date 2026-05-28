import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useMemo } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { SkeletonCard } from "@/components/Skeleton";
import { StatusChip } from "@/components/StatusChip";
import { useDevices } from "@/hooks/useDevices";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";
import type { Device } from "@/types";

export function DeviceListScreen() {
  const { devices, usedMock, isLoading, error, refresh, lastUpdatedAt } = useDevices();
  const { token } = useSession();
  const params = useLocalSearchParams<{ hiddenDeviceId?: string; refreshAt?: string }>();
  const hiddenDeviceIds = useMemo(() => {
    const raw = Array.isArray(params.hiddenDeviceId) ? params.hiddenDeviceId : params.hiddenDeviceId ? [params.hiddenDeviceId] : [];
    return new Set(raw.map((value) => String(value).trim()).filter(Boolean));
  }, [params.hiddenDeviceId]);
  const visibleDevices = useMemo(
    () => devices.filter((device) => !hiddenDeviceIds.has(device.id)),
    [devices, hiddenDeviceIds],
  );

  useFocusEffect(
    useCallback(() => {
      void refresh({ background: true });
    }, [refresh, params.refreshAt]),
  );

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.eyebrow}>PLANTLAB</Text>
          <Text style={styles.title}>Devices</Text>
          <Text style={styles.subtitle}>
            {usedMock ? "Simulator data is active." : "Your connected PlantLab devices."}
          </Text>
          <Text style={styles.meta}>
            {lastUpdatedAt ? `Last updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Pull to refresh when you are ready."}
          </Text>
        </View>
        <View style={styles.addButton}>
          <PrimaryButton label="Add device" onPress={() => router.push("/(app)/devices/add")} />
        </View>
      </View>

      {usedMock ? <StatusChip label="Mock data mode" tone="mock" /> : null}
      {error ? <FeedbackBanner tone="error" message={error} /> : null}
      {isLoading && visibleDevices.length === 0 ? <SkeletonCard /> : null}
      {!isLoading && visibleDevices.length === 0 ? (
        <EmptyState title="No devices yet" message="Add a PlantLab device to start tracking readings, images, and hardware health." />
      ) : null}
      {visibleDevices.map((device) => (
        <MobileDeviceCard device={device} key={device.id} token={token} />
      ))}
    </Screen>
  );
}

function MobileDeviceCard({ device, token }: { device: Device; token: string | null }) {
  const latestReading = device.latestReading;
  return (
    <Pressable key={device.id} onPress={() => router.push(`/(app)/devices/${device.id}`)}>
      <Card variant="elevated" style={styles.deviceCard}>
        <View style={styles.deviceCardTop}>
          <View style={styles.deviceImageFrame}>
            {device.latestImage ? (
              <Image source={imageSource(device.latestImage.url, token)} style={styles.deviceImage} />
            ) : (
              <Text style={styles.deviceImageInitial}>{device.name.slice(0, 1).toUpperCase()}</Text>
            )}
          </View>
          <View style={styles.deviceCardCopy}>
            <View style={styles.deviceCardTitleRow}>
              <View style={styles.cardTitleGroup}>
                <Text style={styles.cardTitle}>{device.name}</Text>
                <Text style={styles.cardSubtitle}>
                  {device.plantType ?? "Plant type not set"} | {device.location ?? "No location set"}
                </Text>
              </View>
              <StatusChip label={statusLabel(device.status)} tone={device.status} compact />
            </View>
            <Text style={styles.summary}>{deviceSummary(device)}</Text>
          </View>
        </View>
        <View style={styles.deviceMetricRow}>
          <DeviceMetric label="Air" value={formatMetric(latestReading?.temperatureC, "C")} />
          <DeviceMetric label="Humidity" value={formatMetric(latestReading?.humidityPercent, "%")} />
          <DeviceMetric label="Water" value={formatMetric(latestReading?.waterTemperatureC, "C")} />
        </View>
        <View style={styles.deviceCardFooter}>
          <Text style={styles.meta}>{formatLightState(device)}</Text>
          <Text style={styles.meta}>Last seen {formatAge(device.lastSeenAt ?? latestReading?.timestamp)}</Text>
        </View>
      </Card>
    </Pressable>
  );
}

function DeviceMetric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.deviceMetric}>
      <Text style={styles.deviceMetricLabel}>{label}</Text>
      <Text style={styles.deviceMetricValue}>{value}</Text>
    </View>
  );
}

function imageSource(url: string, token: string | null) {
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  return headers ? { uri: url, headers } : { uri: url };
}

function statusLabel(status: Device["status"]) {
  if (status === "online") {
    return "Online";
  }
  if (status === "offline") {
    return "Offline";
  }
  if (status === "degraded" || status === "warning") {
    return "Needs review";
  }
  if (status === "stale") {
    return "Stale";
  }
  if (status === "waiting") {
    return "Waiting";
  }
  return "Unknown";
}

function deviceSummary(device: Device): string {
  if (device.status === "offline") {
    return "Recent data is preserved while the device reconnects.";
  }
  if (!device.latestReading) {
    return "Waiting for the first sensor sample.";
  }
  return "Readings and camera history are updating.";
}

function formatMetric(value: number | undefined, unit: string) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }
  return `${value.toFixed(1)} ${unit}`;
}

function formatLightState(device: Device) {
  const latestReading = device.latestReading;
  const lightOn = (device.currentLightOn ?? latestReading?.lightOn) === true;
  const intensity = device.currentLightIntensityPercent ?? latestReading?.lightIntensityPercent;
  if (!lightOn) {
    return "Light off";
  }
  return typeof intensity === "number" ? `Light on ${Math.round(intensity)}%` : "Light on";
}

function formatAge(timestamp?: string) {
  if (!timestamp) {
    return "waiting";
  }
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) {
    return "just now";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  return `${Math.round(hours / 24)}d ago`;
}

const styles = StyleSheet.create({
  header: { gap: theme.spacing.md },
  headerText: { gap: 8 },
  eyebrow: { fontSize: theme.typography.eyebrow, fontWeight: "800", color: theme.colors.accent },
  title: { fontSize: theme.typography.screenTitle, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: theme.typography.bodyLarge, color: theme.colors.textSecondary, lineHeight: 22 },
  meta: { fontSize: theme.typography.meta, color: theme.colors.textMuted },
  addButton: { alignSelf: "flex-start", minWidth: 132 },
  deviceCard: { gap: theme.spacing.md },
  deviceCardTop: { flexDirection: "row", gap: theme.spacing.md, alignItems: "stretch" },
  deviceImageFrame: {
    width: 86,
    height: 96,
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.surfaceInset,
    borderColor: theme.colors.borderSoft,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  deviceImage: { width: "100%", height: "100%" },
  deviceImageInitial: { color: theme.colors.accent, fontSize: 28, fontWeight: "800" },
  deviceCardCopy: { flex: 1, gap: theme.spacing.sm },
  deviceCardTitleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: theme.spacing.md,
  },
  cardTitleGroup: { gap: 4, flex: 1 },
  cardTitle: { fontSize: theme.typography.cardTitle, fontWeight: "800", color: theme.colors.textPrimary },
  cardSubtitle: { fontSize: theme.typography.body, color: theme.colors.textSecondary },
  summary: { fontSize: 15, color: theme.colors.textSecondary, lineHeight: 21 },
  deviceMetricRow: { flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm },
  deviceMetric: {
    ...theme.surfaces.muted,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    flex: 1,
    gap: 2,
    minWidth: 92,
    padding: theme.spacing.sm,
  },
  deviceMetricLabel: { color: theme.colors.textMuted, fontSize: theme.typography.caption, fontWeight: "800" },
  deviceMetricValue: { color: theme.colors.textPrimary, fontSize: theme.typography.body, fontWeight: "800" },
  deviceCardFooter: {
    borderTopColor: theme.colors.borderSoft,
    borderTopWidth: 1,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: theme.spacing.sm,
    justifyContent: "space-between",
    paddingTop: theme.spacing.md,
  },
});
