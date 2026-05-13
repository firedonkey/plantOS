import { useEffect, useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import { Link } from "expo-router";

import { getDeviceSettingsDetails, updateDeviceSettings } from "@/api/devices";
import type { DeviceSettingsDetails } from "@/api/devices";
import { Card } from "@/components/Card";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { StatusChip } from "@/components/StatusChip";
import { useSession } from "@/hooks/useSession";
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

  if (!deviceId) {
    return (
      <Screen>
        <Text style={styles.error}>Missing device id.</Text>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.header}>
        <View style={{ flex: 1, gap: 8 }}>
          <Text style={styles.eyebrow}>DEVICE SETTINGS</Text>
          <Text style={styles.title}>{details?.device.name ?? "Device settings"}</Text>
          <Text style={styles.subtitle}>Edit the core labels and review the live hardware identity and provisioning state.</Text>
        </View>
        {usedMock ? <StatusChip label="Mock mode" tone="mock" /> : null}
      </View>

      {error ? <Text style={[styles.feedback, styles.feedbackError]}>{error}</Text> : null}
      {message ? <Text style={[styles.feedback, styles.feedbackSuccess]}>{message}</Text> : null}

      <Card>
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
        {isLoading && !details ? <Text style={styles.meta}>Loading device details…</Text> : null}
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

      <Card>
        <Text style={styles.sectionTitle}>Recovery guidance</Text>
        <Text style={styles.meta}>{details?.onboardingGuidance ?? "Use this page to keep the operational labels in sync with the real device."}</Text>
        <View style={styles.stack}>
          <Text style={styles.meta}>• For a clean re-provision, use the hardware button flow and watch the serial monitor rather than changing values here.</Text>
          <Text style={styles.meta}>• If the device stops reporting, confirm power, Wi-Fi, and the current device token before deleting or re-adding it.</Text>
          <Text style={styles.meta}>• No remote reboot or re-provision action is wired in yet, by design.</Text>
        </View>
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
  header: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  eyebrow: { fontSize: 13, fontWeight: "700", color: theme.colors.accent },
  title: { fontSize: 30, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: 16, color: theme.colors.textSecondary },
  sectionTitle: { fontSize: 18, fontWeight: "700", color: theme.colors.textPrimary },
  sectionSubtitle: { fontSize: 15, fontWeight: "700", color: theme.colors.textPrimary },
  label: { fontSize: 14, color: theme.colors.textSecondary },
  input: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: theme.colors.textPrimary,
  },
  feedback: { fontWeight: "600", borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10 },
  feedbackSuccess: { color: theme.colors.accent, backgroundColor: "#dff7e8" },
  feedbackError: { color: "#b42318", backgroundColor: "#fde4e4" },
  error: { color: "#b42318" },
  meta: { fontSize: 14, color: theme.colors.textSecondary, lineHeight: 20 },
  stack: { gap: 10 },
  detailRow: {
    borderTopWidth: 1,
    borderTopColor: "#e7ecef",
    paddingTop: 10,
    gap: 6,
  },
  detailLabel: { fontSize: 14, fontWeight: "700", color: theme.colors.textPrimary },
  detailValue: { fontSize: 14, color: theme.colors.textSecondary },
  mono: { fontFamily: "Courier" },
  backLink: { color: theme.colors.accent, fontSize: 16, fontWeight: "700" },
});
