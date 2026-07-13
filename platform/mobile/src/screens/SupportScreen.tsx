import { useEffect, useState } from "react";
import Constants from "expo-constants";
import { StyleSheet, Text } from "react-native";

import { getDeviceSettingsDetails, type DeviceSettingsDetails } from "@/api/devices";
import { DashboardTopNav, EvtCard, EvtInfoRow } from "@/components/evt/EvtComponents";
import { EmptyState } from "@/components/EmptyState";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { Screen } from "@/components/Screen";
import { SkeletonCard } from "@/components/Skeleton";
import { useDevices } from "@/hooks/useDevices";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";
import { formatDeviceStatus, formatTimestamp, formatUptime } from "@/utils/formatting";

export function SupportScreen() {
  const { token } = useSession();
  const { devices, refresh, isLoading: isDevicesLoading } = useDevices();
  const selectedDevice = devices[0];
  const [details, setDetails] = useState<DeviceSettingsDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDetailsLoading, setIsDetailsLoading] = useState(false);

  useEffect(() => {
    if (!selectedDevice?.id) {
      setDetails(null);
      return;
    }
    let cancelled = false;
    setIsDetailsLoading(true);
    setError(null);
    getDeviceSettingsDetails(selectedDevice.id, token ?? undefined)
      .then((result) => {
        if (!cancelled) {
          setDetails(result.details);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load support details.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsDetailsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedDevice?.id, token]);

  const device = details?.device ?? selectedDevice;
  const primary = details?.hardwareHealth?.primary;
  const diagnostics = primary?.diagnostics;

  return (
    <Screen onRefresh={refresh} refreshing={isDevicesLoading || isDetailsLoading}>
      <Text style={styles.screenTitle}>Dashboard</Text>
      <DashboardTopNav active="support" />
      <Text style={styles.kicker}>Equipment health</Text>

      {error ? <FeedbackBanner tone="error" message={error} /> : null}
      {isDevicesLoading && !device ? <SkeletonCard /> : null}
      {!device && !isDevicesLoading ? (
        <EvtCard>
          <EmptyState title="No support data" message="Add a PlantLab device before support diagnostics can be shown." />
        </EvtCard>
      ) : null}

      {device ? (
        <EvtCard compact>
          <EvtInfoRow label="Device ID" value={device.id} mono />
          <EvtInfoRow label="Plant type" value={device.plantType ?? "Not configured"} />
          <EvtInfoRow label="The last time I saw" value={formatTimestamp(device.lastSeenAt ?? details?.hardwareHealth?.lastHeartbeatAt)} />
          <EvtInfoRow label="uptime" value={formatUptime(diagnostics?.uptimeSeconds)} />
          <EvtInfoRow label="firmware" value={diagnostics?.firmwareVersion ?? primary?.softwareVersion ?? "Not reported"} />
          <EvtInfoRow label="Connection status" value={formatDeviceStatus(device.status)} />
          <EvtInfoRow label="Application version" value={Constants.expoConfig?.version ?? "Not configured"} />
        </EvtCard>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  screenTitle: {
    color: theme.colors.textPrimary,
    fontSize: 16,
    fontWeight: "900",
    textAlign: "center",
  },
  kicker: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
    paddingHorizontal: 22,
  },
});
