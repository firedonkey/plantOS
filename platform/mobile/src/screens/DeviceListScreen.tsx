import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { SkeletonCard } from "@/components/Skeleton";
import { StatusChip } from "@/components/StatusChip";
import { useDevices } from "@/hooks/useDevices";
import { theme } from "@/styles/theme";

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
            {usedMock ? "Showing bundled mock devices because the backend is unavailable." : "Showing devices from your local PlantLab backend."}
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
        <Pressable key={device.id} onPress={() => router.push(`/(app)/devices/${device.id}`)}>
          <Card variant="elevated">
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
                ? `Air ${device.latestReading.temperatureC?.toFixed(1) ?? "--"} C | Water ${device.latestReading.waterTemperatureC?.toFixed(1) ?? "--"} C | Level ${device.latestReading.waterLevelState ?? "--"}`
                : "Latest sensor summary unavailable."}
            </Text>
          </Card>
        </Pressable>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: theme.spacing.md },
  headerText: { gap: 8 },
  eyebrow: { fontSize: theme.typography.eyebrow, fontWeight: "800", color: theme.colors.accent },
  title: { fontSize: theme.typography.screenTitle, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: theme.typography.bodyLarge, color: theme.colors.textSecondary, lineHeight: 22 },
  meta: { fontSize: theme.typography.meta, color: theme.colors.textMuted },
  addButton: { alignSelf: "flex-start", minWidth: 132 },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: theme.spacing.md,
  },
  cardTitleGroup: { gap: 4, flex: 1 },
  cardTitle: { fontSize: theme.typography.cardTitle, fontWeight: "800", color: theme.colors.textPrimary },
  cardSubtitle: { fontSize: theme.typography.body, color: theme.colors.textSecondary },
  summary: { fontSize: 15, color: theme.colors.textSecondary, lineHeight: 21 },
});
