import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import Constants from "expo-constants";
import { router } from "expo-router";

import { deleteAccount } from "@/api/auth";
import { getApiBaseUrl } from "@/api/config";
import { DashboardTopNav, Dot, EvtCard, EvtInfoRow } from "@/components/evt/EvtComponents";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { useDevices } from "@/hooks/useDevices";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";
import { formatDeviceStatus } from "@/utils/formatting";

export function SettingsScreen() {
  const { authMode, session, signOut, token } = useSession();
  const { devices, refresh, isLoading } = useDevices();
  const currentDevice = devices[0];
  const userName = session?.name?.trim() || session?.email || "Signed out";
  const apiUrl = getApiBaseUrl() || "Not configured";
  const modeLabel = session?.mode ? `${session.mode} (${authMode})` : `Signed out (${authMode})`;

  const logout = async () => {
    await signOut();
    router.replace("/login");
  };

  const confirmDeleteAccount = () => {
    Alert.alert(
      "Delete account?",
      "This permanently deletes your PlantLab account, devices, sessions, and stored device history. This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete account",
          style: "destructive",
          onPress: async () => {
            try {
              await deleteAccount(token);
              await signOut();
              router.replace("/login");
            } catch (error) {
              Alert.alert("Could not delete account", error instanceof Error ? error.message : "Unknown error.");
            }
          },
        },
      ],
    );
  };

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      <Text style={styles.screenTitle}>Dashboard</Text>
      <DashboardTopNav active="settings" />

      <EvtCard compact>
        <View style={styles.hardwareStatus}>
          <Text style={styles.rowLabel}>Hardware status</Text>
          <View style={styles.statusValue}>
            <Dot color={currentDevice?.status === "offline" ? theme.colors.danger : theme.colors.success} size={6} />
            <Text style={styles.onlineText}>{currentDevice ? formatDeviceStatus(currentDevice.status) : "No device"}</Text>
          </View>
        </View>
      </EvtCard>

      <EvtCard compact>
        <EvtInfoRow label="Account" value={userName} />
        <EvtInfoRow label="API website address" value={apiUrl} />
        <EvtInfoRow label="Conversation mode" value={modeLabel} />
        <EvtInfoRow label="remarks" value={Constants.expoConfig?.version ? `App version ${Constants.expoConfig.version}` : "No app version configured"} />
        <Pressable
          accessibilityRole="button"
          onPress={() => currentDevice ? router.push(`/(app)/devices/${currentDevice.id}/settings`) : router.push("/(app)/devices/add")}
        >
          <View style={styles.equipmentRow}>
            <Text style={styles.rowLabel}>Equipment settings</Text>
            <Text style={styles.rowValue} numberOfLines={1}>
              {currentDevice ? "Open device settings" : "Add a device first"}
            </Text>
          </View>
        </Pressable>
      </EvtCard>

      <PrimaryButton label="log out" tone="secondary" onPress={logout} />

      <EvtCard compact>
        <Text style={styles.dangerTitle}>Account deletion</Text>
        <Text style={styles.note}>Delete your PlantLab account and remove associated devices and history from the backend.</Text>
        <PrimaryButton label="Delete account" tone="danger" disabled={!token} onPress={confirmDeleteAccount} />
      </EvtCard>
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
  hardwareStatus: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    minHeight: 45,
    paddingHorizontal: 10,
  },
  statusValue: {
    alignItems: "center",
    flexDirection: "row",
    gap: 7,
  },
  onlineText: {
    color: theme.colors.success,
    fontSize: theme.evtTypography.body,
  },
  equipmentRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    justifyContent: "space-between",
    minHeight: 45,
    paddingHorizontal: 10,
  },
  rowLabel: {
    color: theme.colors.textPrimary,
    flex: 1,
    fontSize: theme.evtTypography.body,
  },
  rowValue: {
    color: theme.colors.textMuted,
    flex: 1,
    fontSize: theme.evtTypography.body,
    textAlign: "right",
  },
  dangerTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.body,
    fontWeight: "900",
  },
  note: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.body,
    lineHeight: 19,
  },
});
