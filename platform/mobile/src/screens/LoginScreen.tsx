import { useState } from "react";
import { router } from "expo-router";
import { Alert, StyleSheet, Text, TextInput, View } from "react-native";

import { loginWithPlaceholder } from "@/api/auth";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

export function LoginScreen() {
  const { signIn } = useSession();
  const [email, setEmail] = useState("dev@plantlab.local");
  const [password, setPassword] = useState("password");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async () => {
    try {
      setIsSubmitting(true);
      const session = await loginWithPlaceholder({ email, password });
      await signIn(session);
      router.replace("/(app)/devices");
    } catch (error) {
      Alert.alert("Sign in failed", error instanceof Error ? error.message : "Unknown error.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>PLANTLAB MOBILE</Text>
        <Text style={styles.title}>Sign in</Text>
        <Text style={styles.subtitle}>
          Dev-only placeholder login for the first local mobile build. TODO: replace with real mobile auth.
        </Text>
      </View>

      <View style={styles.form}>
        <TextInput value={email} onChangeText={setEmail} style={styles.input} placeholder="Email" autoCapitalize="none" />
        <TextInput
          value={password}
          onChangeText={setPassword}
          style={styles.input}
          placeholder="Password"
          secureTextEntry
        />
        <PrimaryButton label={isSubmitting ? "Signing in..." : "Continue"} onPress={onSubmit} />
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
