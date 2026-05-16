import { StyleSheet, Text, View } from "react-native";
import Constants from "expo-constants";
import { router } from "expo-router";

import { Card } from "@/components/Card";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { useSession } from "@/hooks/useSession";
import { getApiBaseUrl } from "@/api/config";
import { theme } from "@/styles/theme";

export function SettingsScreen() {
  const { authMode, session, signOut } = useSession();

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>SETTINGS</Text>
        <Text style={styles.title}>App settings</Text>
      </View>

      <Card>
        <Text style={styles.label}>API URL</Text>
        <Text style={styles.value}>{getApiBaseUrl() || "Not configured"}</Text>
      </Card>

      <Card>
        <Text style={styles.label}>Session mode</Text>
        <Text style={styles.value}>{session?.mode ?? "Signed out"} ({authMode})</Text>
      </Card>

      <Card>
        <Text style={styles.label}>Auth note</Text>
        <Text style={styles.todo}>Production mobile auth uses backend Google handoff, but refresh-token persistence is disabled until secure storage is added.</Text>
      </Card>

      <Card>
        <Text style={styles.label}>App version</Text>
        <Text style={styles.value}>{Constants.expoConfig?.version ?? "0.1.0"}</Text>
      </Card>

      <Card>
        <Text style={styles.label}>Device settings</Text>
        <Text style={styles.todo}>Open a device, then tap Device settings to edit labels, reconnect Wi-Fi, repair setup, prepare transfer, or view factory reset guidance.</Text>
      </Card>

      <PrimaryButton
        label="Log out"
        onPress={async () => {
          await signOut();
          router.replace("/login");
        }}
      />

      <Text style={styles.todo}>
        TODO: push notifications require an Expo development build or native capability work, not just Expo Go.
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: 8 },
  eyebrow: { fontSize: 13, fontWeight: "700", color: theme.colors.accent },
  title: { fontSize: 30, fontWeight: "800", color: theme.colors.textPrimary },
  label: { fontSize: 14, color: theme.colors.textSecondary },
  value: { fontSize: 17, fontWeight: "700", color: theme.colors.textPrimary },
  todo: { fontSize: 14, color: theme.colors.textSecondary, lineHeight: 20 },
});
