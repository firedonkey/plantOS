import { useEffect, useState } from "react";
import { router } from "expo-router";
import * as Linking from "expo-linking";
import * as AppleAuthentication from "expo-apple-authentication";
import { Alert, StyleSheet, Text, TextInput, View } from "react-native";

import { getMobileGoogleAuthStartUrl, loginWithAppleIdentityToken, loginWithBackendFallback } from "@/api/auth";
import { isDevAuthEnabled } from "@/api/config";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

export function LoginScreen() {
  const { authMode, signIn } = useSession();
  const [loginName, setLoginName] = useState("dev");
  const [password, setPassword] = useState("password");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAppleAvailable, setIsAppleAvailable] = useState(false);
  const showLocalLogin = authMode === "dev" && isDevAuthEnabled();

  useEffect(() => {
    if (showLocalLogin) {
      setIsAppleAvailable(false);
      return;
    }
    AppleAuthentication.isAvailableAsync()
      .then(setIsAppleAvailable)
      .catch(() => setIsAppleAvailable(false));
  }, [showLocalLogin]);

  const onSubmit = async () => {
    try {
      setIsSubmitting(true);
      const email = normalizeLocalLoginEmail(loginName);
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

  const onAppleAuth = async () => {
    if (isSubmitting) {
      return;
    }
    try {
      setIsSubmitting(true);
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });
      if (!credential.identityToken) {
        throw new Error("Apple did not return an identity token.");
      }
      const { session } = await loginWithAppleIdentityToken({
        identityToken: credential.identityToken,
        email: credential.email,
        fullName: formatAppleFullName(credential.fullName),
      });
      await signIn(session);
      router.replace("/(app)/devices");
    } catch (error) {
      if (isAppleCancelError(error)) {
        return;
      }
      Alert.alert("Apple sign-in failed", error instanceof Error ? error.message : "Unknown error.");
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
          {showLocalLogin
            ? "Use a local test account for this development build. Google sign-in stays off while AUTH_MODE is dev."
            : "Use backend-owned Google sign-in for the production backend."}
        </Text>
      </View>

      <View style={styles.form}>
        {showLocalLogin ? (
          <>
            <TextInput
              value={loginName}
              onChangeText={setLoginName}
              style={styles.input}
              placeholder="Username or email"
              autoCapitalize="none"
              autoCorrect={false}
            />
            <TextInput
              value={password}
              onChangeText={setPassword}
              style={styles.input}
              placeholder="Password"
              secureTextEntry
            />
            <PrimaryButton label={isSubmitting ? "Signing in..." : "Continue"} onPress={onSubmit} disabled={isSubmitting} />
          </>
        ) : (
          <>
            {isAppleAvailable ? (
              <AppleAuthentication.AppleAuthenticationButton
                buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
                buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
                cornerRadius={8}
                style={styles.appleButton}
                onPress={onAppleAuth}
              />
            ) : null}
            <PrimaryButton label="Continue with Google" tone="secondary" onPress={onProductionAuth} disabled={isSubmitting} />
          </>
        )}
      </View>
    </Screen>
  );
}

function normalizeLocalLoginEmail(loginName: string): string {
  const normalized = loginName.trim().toLowerCase();
  if (!normalized) {
    return "dev@plantlab.local";
  }
  if (normalized.includes("@")) {
    return normalized;
  }
  return `${normalized}@plantlab.local`;
}

function formatAppleFullName(fullName: AppleAuthentication.AppleAuthenticationFullName | null): string | null {
  if (!fullName) {
    return null;
  }
  const parts = [fullName.givenName, fullName.middleName, fullName.familyName]
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part));
  return parts.join(" ") || null;
}

function isAppleCancelError(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && (error as { code?: string }).code === "ERR_REQUEST_CANCELED";
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
  appleButton: {
    width: "100%",
    height: 48,
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
