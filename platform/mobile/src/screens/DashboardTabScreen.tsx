import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useMemo } from "react";
import { StyleSheet, Text } from "react-native";

import { DashboardTopNav, EvtCard } from "@/components/evt/EvtComponents";
import { EmptyState } from "@/components/EmptyState";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { SkeletonCard } from "@/components/Skeleton";
import { useDevices } from "@/hooks/useDevices";
import { DeviceDashboardScreen } from "@/screens/DeviceDashboardScreen";
import { theme } from "@/styles/theme";

export function DashboardTabScreen() {
  const { deviceId } = useLocalSearchParams<{ deviceId?: string }>();
  const { devices, error, isLoading, refresh } = useDevices();
  const selectedDevice = useMemo(
    () => devices.find((device) => device.id === deviceId) ?? devices[0],
    [deviceId, devices],
  );

  useFocusEffect(
    useCallback(() => {
      void refresh({ background: true });
    }, [refresh]),
  );

  if (isLoading && !selectedDevice) {
    return (
      <Screen>
        <DashboardTitle />
        <DashboardTopNav active="device" />
        <SkeletonCard />
      </Screen>
    );
  }

  if (!selectedDevice) {
    return (
      <Screen onRefresh={refresh} refreshing={isLoading}>
        <DashboardTitle />
        <DashboardTopNav active="device" />
        {error ? <FeedbackBanner tone="error" message={error} /> : null}
        <EvtCard>
          <EmptyState title="No device data" message="Add a PlantLab device before opening analytics." />
          <PrimaryButton label="Add device" onPress={() => router.push("/(app)/devices/add")} />
        </EvtCard>
      </Screen>
    );
  }

  return <DeviceDashboardBridge deviceId={selectedDevice.id} />;
}

function DeviceDashboardBridge({ deviceId }: { deviceId: string }) {
  return <DeviceDashboardScreen deviceId={deviceId} showTopNav />;
}

export function DashboardTitle() {
  return <Text style={styles.title}>Dashboard</Text>;
}

const styles = StyleSheet.create({
  title: {
    color: theme.colors.textPrimary,
    fontSize: 16,
    fontWeight: "900",
    textAlign: "center",
  },
});
