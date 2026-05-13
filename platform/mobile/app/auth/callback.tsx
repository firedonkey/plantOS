import { useEffect, useState } from "react";
import { router, useLocalSearchParams } from "expo-router";
import { Alert, StyleSheet, Text, View } from "react-native";

import { refreshProductionSession } from "@/api/auth";
import { Screen } from "@/components/Screen";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

export default function AuthCallbackRoute() {
  const params = useLocalSearchParams<{ handoff_code?: string; error?: string }>();
  const { signIn } = useSession();
  const [message, setMessage] = useState("Completing Google sign-in...");

  useEffect(() => {
    let isMounted = true;

    async function completeSignIn() {
      if (params.error) {
        const errorMessage = Array.isArray(params.error) ? params.error[0] : params.error;
        setMessage("Google sign-in did not complete.");
        Alert.alert("Sign in failed", errorMessage || "The backend returned an auth error.");
        router.replace("/login");
        return;
      }

      const handoffCode = Array.isArray(params.handoff_code) ? params.handoff_code[0] : params.handoff_code;
      if (!handoffCode) {
        setMessage("Missing Google sign-in handoff code.");
        Alert.alert("Sign in failed", "The backend did not return a mobile handoff code.");
        router.replace("/login");
        return;
      }

      try {
        const { session } = await refreshProductionSession({ handoffCode });
        await signIn(session);
        if (isMounted) {
          router.replace("/(app)/devices");
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error.";
        if (isMounted) {
          setMessage("Google sign-in failed.");
          Alert.alert("Sign in failed", errorMessage);
          router.replace("/login");
        }
      }
    }

    void completeSignIn();

    return () => {
      isMounted = false;
    };
  }, [params.error, params.handoff_code, signIn]);

  return (
    <Screen>
      <View style={styles.card}>
        <Text style={styles.title}>Google sign-in</Text>
        <Text style={styles.message}>{message}</Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: 8,
    backgroundColor: theme.colors.surface,
    padding: 18,
    gap: 8,
  },
  title: {
    color: theme.colors.textPrimary,
    fontSize: 22,
    fontWeight: "800",
  },
  message: {
    color: theme.colors.textSecondary,
    fontSize: 16,
    lineHeight: 23,
  },
});
