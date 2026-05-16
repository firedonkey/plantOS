import { useEffect, useState } from "react";
import { Alert, StyleSheet, Text, TextInput, View } from "react-native";
import { Link, router } from "expo-router";

import { deleteDevice, getDeviceSettingsDetails, releaseDeviceForTransfer, updateDeviceSettings } from "@/api/devices";
import type { DeviceSettingsDetails } from "@/api/devices";
import { Card } from "@/components/Card";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { SkeletonCard } from "@/components/Skeleton";
import { StatusChip } from "@/components/StatusChip";
import { useSession } from "@/hooks/useSession";
import { hideDeviceFromActiveList } from "@/storage/hiddenDevices";
import { theme } from "@/styles/theme";

type DeviceSettingsScreenProps = {
  deviceId: string;
};

export function DeviceSettingsScreen({ deviceId }: DeviceSettingsScreenProps) {
  const { token } = useSession();
  const [details, setDetails] = useState<DeviceSettingsDetails | null>(null);
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [plantType, setPlantType] = useState("");
  const [isRemoving, setIsRemoving] = useState(false);
  const [isReleasing, setIsReleasing] = useState(false);
  const primaryHardwareId = details?.hardwareHealth?.primary?.hardwareDeviceId;

  useEffect(() => {
    if (!deviceId) {
      return;
    }
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const result = await getDeviceSettingsDetails(deviceId, token ?? undefined);
        if (cancelled) {
          return;
        }
        setDetails(result.details);
        setUsedMock(result.usedMock);
        setName(result.details.device.name);
        setLocation(result.details.device.location ?? "");
        setPlantType(result.details.device.plantType ?? "");
      } catch (err) {
        if (!cancelled) {
          setUsedMock(false);
          setError(err instanceof Error ? err.message : "Unable to load device settings.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [deviceId, token]);

  const onSave = async () => {
    if (!deviceId) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      const result = await updateDeviceSettings(
        deviceId,
        {
          name,
          location: location || undefined,
          plantType: plantType || undefined,
        },
        token ?? undefined,
      );
      setDetails(result.details);
      setUsedMock(result.usedMock);
      setMessage(result.usedMock ? "Mock mode preview updated locally." : "Device settings saved.");
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to save device settings.");
    } finally {
      setIsSaving(false);
    }
  };

  const removeDevice = async () => {
    if (!deviceId) {
      return;
    }
    setIsRemoving(true);
    setError(null);
    setMessage(null);
    try {
      await deleteDevice(deviceId, token ?? undefined);
      await hideDeviceFromActiveList(deviceId);
      router.replace({
        pathname: "/(app)/devices",
        params: { hiddenDeviceId: deviceId, refreshAt: String(Date.now()) },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove device.");
    } finally {
      setIsRemoving(false);
    }
  };

  const onRemovePress = () => {
    const deviceName = details?.device.name ?? "this device";
    Alert.alert("Remove device?", `Remove ${deviceName} from your account. The physical device may need to be factory reset before adding it again.`, [
      { text: "Cancel", style: "cancel" },
      { text: "Remove", style: "destructive", onPress: removeDevice },
    ]);
  };

  const startRecoveryFlow = (mode: "wifi" | "repair") => {
    if (!details || !primaryHardwareId) {
      setError("Hardware identity is not available yet. Wait for the device to register once, then retry recovery.");
      return;
    }
    router.push({
      pathname: "/(app)/devices/add",
      params: {
        recoveryMode: mode,
        recoveryDeviceId: deviceId,
        recoveryHardwareId: primaryHardwareId,
        recoveryName: details.device.name,
      },
    });
  };

  const releaseForTransfer = async () => {
    setIsReleasing(true);
    setError(null);
    setMessage(null);
    try {
      const result = await releaseDeviceForTransfer(deviceId, token ?? undefined);
      setUsedMock(result.usedMock);
      await hideDeviceFromActiveList(deviceId);
      const goBackToDevices = () => router.replace({
        pathname: "/(app)/devices",
        params: { hiddenDeviceId: deviceId, refreshAt: String(Date.now()) },
      });
      Alert.alert(
        "Device released",
        `${result.message} Hold the device button for 15 seconds before the next owner adds it.`,
        [{ text: "Back to devices", onPress: goBackToDevices }],
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to release this device for transfer.");
    } finally {
      setIsReleasing(false);
    }
  };

  const onTransferPress = () => {
    const deviceName = details?.device.name ?? "this device";
    Alert.alert("Prepare for transfer?", `${deviceName} will stop syncing to this account. Historical data is kept here, and the next owner can add it after you hold the device button for 15 seconds.`, [
      { text: "Cancel", style: "cancel" },
      { text: "Release device", style: "destructive", onPress: releaseForTransfer },
    ]);
  };

  const onFactoryResetPress = () => {
    Alert.alert(
      "Factory reset this device",
      "Hold the device button for 15 seconds until the light blinks rapidly. This clears local Wi-Fi and device tokens. Backend ownership stays with this account unless you prepare it for transfer first.",
      [{ text: "OK" }],
    );
  };

  if (!deviceId) {
    return (
      <Screen>
        <FeedbackBanner tone="error" message="Missing device id." />
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.header}>
        <View style={{ flex: 1, gap: 8 }}>
          <Text style={styles.eyebrow}>DEVICE SETTINGS</Text>
          <Text style={styles.title}>{details?.device.name ?? "Device settings"}</Text>
          <Text style={styles.subtitle}>Edit labels, recover Wi-Fi setup, and review provisioning state.</Text>
        </View>
        {usedMock ? <StatusChip label="Mock mode" tone="mock" /> : null}
      </View>

      {error ? <FeedbackBanner tone="error" message={error} /> : null}
      {message ? <FeedbackBanner tone="success" message={message} /> : null}
      {isLoading && !details ? <SkeletonCard /> : null}

      <Card variant="elevated">
        <Text style={styles.sectionTitle}>Edit labels</Text>
        <Text style={styles.label}>Device name</Text>
        <TextInput value={name} onChangeText={setName} style={styles.input} />
        <Text style={styles.label}>Location</Text>
        <TextInput value={location} onChangeText={setLocation} style={styles.input} placeholder="Optional" />
        <Text style={styles.label}>Plant type</Text>
        <TextInput value={plantType} onChangeText={setPlantType} style={styles.input} placeholder="Optional" />
        <PrimaryButton label={isSaving ? "Saving..." : "Save changes"} disabled={isSaving || isLoading} onPress={onSave} />
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Operational details</Text>
        {isLoading && !details ? <Text style={styles.meta}>Loading device details...</Text> : null}
        {details ? (
          <View style={styles.stack}>
            <DetailRow label="Provision status" value={details.onboardingStatus} />
            <DetailRow label="Device token" value={details.maskedToken} mono />
            <DetailRow label="Connection state" value={details.device.status} />
            <DetailRow
              label="Last heartbeat"
              value={details.device.lastSeenAt ? new Date(details.device.lastSeenAt).toLocaleString() : "Waiting for first heartbeat"}
            />
            <Text style={styles.sectionSubtitle}>Hardware identifiers</Text>
            {details.hardwareIdentifiers.length ? (
              details.hardwareIdentifiers.map((item) => <DetailRow key={`${item.label}-${item.value}`} label={item.label} value={item.value} mono />)
            ) : (
              <Text style={styles.meta}>Hardware identifiers will appear after the backend receives node registration details.</Text>
            )}
          </View>
        ) : null}
      </Card>

      <Card variant="inset">
        <Text style={styles.sectionTitle}>Recovery</Text>
        <Text style={styles.meta}>{details?.onboardingGuidance ?? "Use this page to keep the operational labels in sync with the real device."}</Text>
        <View style={styles.stack}>
          <PrimaryButton label="Reconnect Wi-Fi" tone="secondary" disabled={isLoading || !primaryHardwareId} onPress={() => startRecoveryFlow("wifi")} />
          <PrimaryButton label="Re-provision / repair setup" tone="secondary" disabled={isLoading || !primaryHardwareId} onPress={() => startRecoveryFlow("repair")} />
          <PrimaryButton label={isReleasing ? "Releasing..." : "Prepare device for transfer"} tone="secondary" disabled={isLoading || isReleasing} onPress={onTransferPress} />
          <PrimaryButton label="Factory reset this device" tone="danger" disabled={isLoading} onPress={onFactoryResetPress} />
          <Text style={styles.meta}>For Wi-Fi recovery, hold the setup button for 5 seconds until the status light blinks. For transfer or full local reset, hold it for 15 seconds.</Text>
        </View>
      </Card>

      <Card variant="inset">
        <Text style={styles.sectionTitle}>Remove device</Text>
        <Text style={styles.meta}>Remove this device from your account. Use this only when replacing hardware or preparing to add the device again.</Text>
        <PrimaryButton label={isRemoving ? "Removing..." : "Remove device"} tone="danger" disabled={isRemoving || isLoading} onPress={onRemovePress} />
      </Card>

      <Link href={`/(app)/devices/${deviceId}`} style={styles.backLink}>
        Back to dashboard
      </Link>
    </Screen>
  );
}

function DetailRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={[styles.detailValue, mono && styles.mono]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", gap: theme.spacing.md, alignItems: "flex-start" },
  eyebrow: { fontSize: theme.typography.eyebrow, fontWeight: "800", color: theme.colors.accent },
  title: { fontSize: theme.typography.screenTitle, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: theme.typography.bodyLarge, color: theme.colors.textSecondary, lineHeight: 22 },
  sectionTitle: { fontSize: theme.typography.sectionTitle, fontWeight: "800", color: theme.colors.textPrimary },
  sectionSubtitle: { fontSize: 15, fontWeight: "800", color: theme.colors.textPrimary },
  label: { fontSize: theme.typography.body, color: theme.colors.textSecondary },
  input: {
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: theme.colors.textPrimary,
    backgroundColor: theme.colors.surface,
  },
  meta: { fontSize: theme.typography.body, color: theme.colors.textSecondary, lineHeight: 20 },
  stack: { gap: theme.spacing.md },
  detailRow: {
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderSoft,
    paddingTop: theme.spacing.md,
    gap: 6,
  },
  detailLabel: { fontSize: theme.typography.body, fontWeight: "800", color: theme.colors.textPrimary },
  detailValue: { fontSize: theme.typography.body, color: theme.colors.textSecondary },
  mono: { fontFamily: "Courier" },
  backLink: { color: theme.colors.accent, fontSize: 16, fontWeight: "700" },
});
