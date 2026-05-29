import { Alert, StyleSheet, Text, View } from "react-native";
import Constants from "expo-constants";
import { router } from "expo-router";

import { deleteAccount } from "@/api/auth";
import { getApiBaseUrl } from "@/api/config";
import { Card } from "@/components/Card";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

export function SettingsScreen() {
  const { authMode, session, signOut, token } = useSession();
  const userName = session?.name?.trim() || session?.email || "Signed out";
  const userEmail = session?.email?.trim();

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
    <Screen>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>SETTINGS</Text>
        <Text style={styles.title}>App settings</Text>
      </View>

      <Card variant="elevated">
        <Text style={styles.label}>User name</Text>
        <Text style={styles.value}>{userName}</Text>
        {userEmail && userEmail !== userName ? <Text style={styles.note}>{userEmail}</Text> : null}
      </Card>

      <Card variant="elevated">
        <Text style={styles.label}>API URL</Text>
        <Text style={styles.value}>{getApiBaseUrl() || "Not configured"}</Text>
      </Card>

      <Card>
        <Text style={styles.label}>Session mode</Text>
        <Text style={styles.value}>{session?.mode ?? "Signed out"} ({authMode})</Text>
      </Card>

      <Card variant="inset">
        <Text style={styles.label}>Auth note</Text>
        <Text style={styles.note}>Production mobile auth supports Sign in with Apple and backend Google handoff. Refresh-token persistence will remain disabled until secure storage is enabled.</Text>
      </Card>

      <Card>
        <Text style={styles.label}>App version</Text>
        <Text style={styles.value}>{Constants.expoConfig?.version ?? "0.1.0"}</Text>
      </Card>

      <Card variant="inset">
        <Text style={styles.label}>Device settings</Text>
        <Text style={styles.note}>Open a device to edit labels, recover Wi-Fi setup, prepare transfer, or view reset guidance.</Text>
      </Card>

      <PrimaryButton
        label="Log out"
        onPress={async () => {
          await signOut();
          router.replace("/login");
        }}
      />

      <Card variant="inset">
        <Text style={styles.label}>Account deletion</Text>
        <Text style={styles.note}>Delete your PlantLab account and remove associated devices and history from the backend.</Text>
        <PrimaryButton label="Delete account" tone="danger" disabled={!token} onPress={confirmDeleteAccount} />
      </Card>

      <Text style={styles.note}>Push notifications require an Expo development build or native capability work.</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: 8 },
  eyebrow: { fontSize: theme.typography.eyebrow, fontWeight: "800", color: theme.colors.accent },
  title: { fontSize: theme.typography.screenTitle, fontWeight: "800", color: theme.colors.textPrimary },
  label: { fontSize: theme.typography.body, color: theme.colors.textSecondary },
  value: { fontSize: 17, fontWeight: "800", color: theme.colors.textPrimary },
  note: { fontSize: theme.typography.body, color: theme.colors.textSecondary, lineHeight: 20 },
});
