import { useEffect, useState } from "react";
import { router } from "expo-router";
import * as Linking from "expo-linking";
import * as AppleAuthentication from "expo-apple-authentication";
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { getMobileGoogleAuthStartUrl, loginWithAppleIdentityToken, loginWithBackendFallback, loginWithDemoAccount } from "@/api/auth";
import { isDevAuthEnabled } from "@/api/config";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

export function LoginScreen() {
  const { authMode, signIn } = useSession();
  const [loginName, setLoginName] = useState("dev@plantlab.local");
  const [password, setPassword] = useState("password");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAppleAvailable, setIsAppleAvailable] = useState(false);
  const showProductionAuth = authMode === "production";
  const showLocalLogin = isDevAuthEnabled();

  useEffect(() => {
    if (!showProductionAuth) {
      setIsAppleAvailable(false);
      return;
    }
    AppleAuthentication.isAvailableAsync()
      .then(setIsAppleAvailable)
      .catch(() => setIsAppleAvailable(false));
  }, [showProductionAuth]);

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

  const onDemoAuth = async () => {
    if (isSubmitting) {
      return;
    }
    try {
      setIsSubmitting(true);
      const { session } = await loginWithDemoAccount();
      await signIn(session);
      router.replace("/(app)/devices");
    } catch (error) {
      Alert.alert("Demo unavailable", error instanceof Error ? error.message : "Unknown error.");
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
          {showProductionAuth
            ? "Sign in to sync and manage your PlantLab devices."
            : "Use a local test account for this development build."}
        </Text>
      </View>

      {showProductionAuth ? (
        <View style={styles.productVisual} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
          <View style={styles.growLight} />
          <View style={styles.lightBeam} />
          <View style={styles.plantScene}>
            <View style={styles.leftLeaf} />
            <View style={styles.stem} />
            <View style={styles.rightLeaf} />
          </View>
          <View style={styles.planter} />
        </View>
      ) : null}

      <View style={styles.form}>
        {showProductionAuth ? (
          <>
            <Pressable
              disabled={isSubmitting}
              onPress={onProductionAuth}
              style={({ pressed }) => [
                styles.googleButton,
                isSubmitting && styles.disabledButton,
                pressed && !isSubmitting && styles.pressedButton,
              ]}
            >
              <View style={styles.googleIcon}>
                <Text style={styles.googleIconText}>G</Text>
              </View>
              <Text style={styles.googleButtonLabel}>Continue with Google</Text>
            </Pressable>
            {isAppleAvailable ? (
              <AppleAuthentication.AppleAuthenticationButton
                buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
                buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
                cornerRadius={8}
                style={styles.appleButton}
                onPress={onAppleAuth}
              />
            ) : null}
            <PrimaryButton label={isSubmitting ? "Opening demo..." : "Try PlantLab Demo"} onPress={onDemoAuth} disabled={isSubmitting} />
          </>
        ) : null}
        {showLocalLogin ? (
          <View style={[styles.localLoginFields, showProductionAuth ? styles.localLoginPanel : null]}>
            <Text style={styles.localLoginTitle}>Local development sign-in</Text>
            <TextInput
              value={loginName}
              onChangeText={setLoginName}
              style={styles.input}
              placeholder="Username or email"
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
            />
            <TextInput
              value={password}
              onChangeText={setPassword}
              style={styles.input}
              placeholder="Password"
              secureTextEntry
            />
            <PrimaryButton label={isSubmitting ? "Signing in..." : "Continue locally"} onPress={onSubmit} disabled={isSubmitting} />
          </View>
        ) : null}
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
    marginTop: 42,
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
  localLoginPanel: {
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderSoft,
    marginTop: 6,
    paddingTop: 16,
  },
  localLoginFields: {
    gap: 12,
  },
  localLoginTitle: {
    color: theme.colors.textSecondary,
    fontSize: 16,
    fontWeight: "700",
  },
  productVisual: {
    height: 132,
    borderRadius: 8,
    backgroundColor: theme.colors.surfaceMuted,
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
    marginTop: 2,
  },
  growLight: {
    position: "absolute",
    top: 22,
    width: 86,
    height: 5,
    borderRadius: 3,
    backgroundColor: theme.colors.textPrimary,
    opacity: 0.86,
  },
  lightBeam: {
    position: "absolute",
    top: 31,
    width: 124,
    height: 66,
    borderRadius: 8,
    borderTopWidth: 1,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: "rgba(47, 133, 90, 0.14)",
    backgroundColor: "rgba(47, 133, 90, 0.04)",
  },
  plantScene: {
    width: 82,
    height: 58,
    alignItems: "center",
    justifyContent: "flex-end",
    marginTop: 24,
  },
  stem: {
    width: 4,
    height: 42,
    borderRadius: 2,
    backgroundColor: theme.colors.accent,
  },
  leftLeaf: {
    position: "absolute",
    bottom: 24,
    left: 22,
    width: 28,
    height: 14,
    borderTopLeftRadius: 14,
    borderBottomRightRadius: 14,
    backgroundColor: theme.colors.accent,
    transform: [{ rotate: "-18deg" }],
  },
  rightLeaf: {
    position: "absolute",
    bottom: 32,
    right: 22,
    width: 30,
    height: 15,
    borderTopRightRadius: 15,
    borderBottomLeftRadius: 15,
    backgroundColor: "#44a16d",
    transform: [{ rotate: "18deg" }],
  },
  planter: {
    width: 88,
    height: 18,
    borderRadius: 6,
    backgroundColor: theme.colors.textPrimary,
    opacity: 0.9,
    marginTop: -1,
  },
  appleButton: {
    width: "100%",
    height: 50,
  },
  googleButton: {
    minHeight: 50,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: "#c2ced6",
    backgroundColor: "#fbfdfc",
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 10,
    paddingHorizontal: 16,
    shadowColor: "#10251a",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  googleIcon: {
    width: 22,
    height: 22,
    borderRadius: 11,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.white,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  googleIconText: {
    fontSize: 15,
    fontWeight: "800",
    color: "#4285F4",
  },
  googleButtonLabel: {
    fontSize: 17,
    fontWeight: "800",
    color: theme.colors.textPrimary,
  },
  pressedButton: {
    opacity: 0.84,
  },
  disabledButton: {
    opacity: 0.55,
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
