import { useState } from "react";
import { router } from "expo-router";
import * as Linking from "expo-linking";
import { Alert, StyleSheet, Text, TextInput, View } from "react-native";

import { getMobileGoogleAuthStartUrl, loginWithBackendFallback } from "@/api/auth";
import { isDevAuthEnabled } from "@/api/config";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

export function LoginScreen() {
  const { authMode, signIn } = useSession();
  const [email, setEmail] = useState("dev@plantlab.local");
  const [password, setPassword] = useState("password");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async () => {
    try {
      setIsSubmitting(true);
      const session = await loginWithBackendFallback({ email, password });
      await signIn(session);
      if (session.mode === "mock") {
        Alert.alert("Mock mode", "Backend is unavailable, so the app is using bundled mock data.");
      }
      router.replace("/(app)/devices");
    } catch (error) {
      Alert.alert("Sign in failed", error instanceof Error ? error.message : "Unknown error.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const onProductionAuth = async () => {
    try {
      const startUrl = getMobileGoogleAuthStartUrl("plantlab://auth/callback");
      await Linking.openURL(startUrl);
    } catch (error) {
      Alert.alert("Production auth unavailable", error instanceof Error ? error.message : "Unknown error.");
    }
  };

  const showDevLogin = authMode === "dev" && isDevAuthEnabled();

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>PLANTLAB MOBILE</Text>
        <Text style={styles.title}>Sign in</Text>
        <Text style={styles.subtitle}>
          {showDevLogin
            ? "Use Google sign-in for backend-owned auth, or use dev-only login for local testing."
            : "Use backend-owned Google sign-in. Dev login is hidden unless EXPO_PUBLIC_ENABLE_DEV_AUTH=true."}
        </Text>
      </View>

      <View style={styles.form}>
        <PrimaryButton label="Continue with Google" onPress={onProductionAuth} />
        {showDevLogin ? (
          <>
            <View style={styles.divider} />
            <TextInput value={email} onChangeText={setEmail} style={styles.input} placeholder="Email" autoCapitalize="none" />
            <TextInput
              value={password}
              onChangeText={setPassword}
              style={styles.input}
              placeholder="Password"
              secureTextEntry
            />
            <PrimaryButton label={isSubmitting ? "Signing in..." : "Continue"} onPress={onSubmit} />
          </>
        ) : null}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    gap: 10,
    marginTop: 24,
  },
  eyebrow: {
    fontSize: 13,
    fontWeight: "700",
    color: theme.colors.accent,
  },
  title: {
    fontSize: 38,
    fontWeight: "800",
    color: theme.colors.textPrimary,
  },
  subtitle: {
    fontSize: 16,
    lineHeight: 24,
    color: theme.colors.textSecondary,
  },
  form: {
    gap: 12,
  },
  divider: {
    height: 1,
    backgroundColor: theme.colors.border,
    marginVertical: 4,
  },
  input: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
});
