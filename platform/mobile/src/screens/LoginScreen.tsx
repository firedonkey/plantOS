import { useEffect, useMemo, useState } from "react";
import { router } from "expo-router";
import * as Linking from "expo-linking";
import * as AppleAuthentication from "expo-apple-authentication";
import { Alert, Image, ImageBackground, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import type { ImageSourcePropType } from "react-native";

import { getMobileGoogleAuthStartUrl, loginWithAppleIdentityToken, loginWithBackendFallback, loginWithDemoAccount } from "@/api/auth";
import { isDevAuthEnabled } from "@/api/config";
import { evtAssets } from "@/assets/evtAssets";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

export function LoginScreen() {
  const { authMode, signIn } = useSession();
  const [loginName, setLoginName] = useState("dev@plantlab.local");
  const [password, setPassword] = useState("password");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAppleAvailable, setIsAppleAvailable] = useState(false);
  const showProductionAuth = authMode === "production";
  const showLocalLogin = isDevAuthEnabled();
  const localSubmitDisabled = isSubmitting || !loginName.trim() || !password;

  useEffect(() => {
    if (!showProductionAuth) {
      setIsAppleAvailable(false);
      return;
    }
    AppleAuthentication.isAvailableAsync()
      .then(setIsAppleAvailable)
      .catch(() => setIsAppleAvailable(false));
  }, [showProductionAuth]);

  const helperCopy = useMemo(
    () => (showProductionAuth ? "Sign in to monitor your PlantLab devices." : "Use a local test account for this development build."),
    [showProductionAuth],
  );

  const onSubmit = async () => {
    if (localSubmitDisabled) {
      setErrorMessage("Enter an account and PIN before logging in.");
      return;
    }
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const email = normalizeLocalLoginEmail(loginName);
      const session = await loginWithBackendFallback({ email, password });
      await signIn(session);
      if (session.mode === "mock") {
        Alert.alert("Mock mode", "Backend is unavailable, so the app is using bundled mock data.");
      }
      router.replace("/(app)/devices");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error.";
      setErrorMessage(message);
      Alert.alert("Login failed", message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const onProductionAuth = async () => {
    try {
      setErrorMessage(null);
      const startUrl = getMobileGoogleAuthStartUrl("plantlab://auth/callback");
      await Linking.openURL(startUrl);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error.";
      setErrorMessage(message);
      Alert.alert("Google login unavailable", message);
    }
  };

  const onAppleAuth = async () => {
    if (isSubmitting) {
      return;
    }
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
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
      const message = error instanceof Error ? error.message : "Unknown error.";
      setErrorMessage(message);
      Alert.alert("Apple login failed", message);
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
      setErrorMessage(null);
      const { session } = await loginWithDemoAccount();
      await signIn(session);
      router.replace("/(app)/devices");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error.";
      setErrorMessage(message);
      Alert.alert("Demo unavailable", message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ImageBackground source={evtAssets.authLeafFrame} resizeMode="cover" style={styles.background}>
      <Screen transparentBackground>
        <View style={styles.authContent}>
          <View style={styles.brandBlock}>
            <Image source={evtAssets.plantLabLeafLogo} style={styles.leafLogo} resizeMode="contain" />
            <Text style={styles.logoText}>PLANT<Text style={styles.logoAccent}>LAB</Text></Text>
            <Text style={styles.heroTitle}>PLANT INTELLIGENCE MONITORING PLATFORM</Text>
            <Text style={styles.helperText}>{helperCopy}</Text>
          </View>

          {showLocalLogin ? (
            <View style={styles.form}>
              <AuthField
                accessibilityLabel="Account"
                autoCapitalize="none"
                autoComplete="email"
                icon={evtAssets.accountIcon}
                keyboardType="email-address"
                onChangeText={setLoginName}
                placeholder="Please enter account"
                value={loginName}
              />
              <AuthField
                accessibilityLabel="PIN"
                autoComplete="password"
                icon={evtAssets.lockIcon}
                onChangeText={setPassword}
                placeholder="Enter your PIN"
                secureTextEntry
                trailingIcon={evtAssets.eyeIcon}
                value={password}
              />
              {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
              <PrimaryButton label={isSubmitting ? "LOGGING IN..." : "LOGIN"} onPress={onSubmit} disabled={localSubmitDisabled} />
              <Pressable
                accessibilityRole="button"
                onPress={() => Alert.alert("Password reset", "Password reset is not available in this mobile build yet.")}
                style={styles.forgotButton}
              >
                <Text style={styles.forgotText}>Forgot Password?</Text>
              </Pressable>
            </View>
          ) : null}

          <View style={styles.socialStack}>
            {showProductionAuth ? (
              <>
                <SocialButton
                  disabled={isSubmitting}
                  icon={evtAssets.googleIcon}
                  label="Login with google"
                  onPress={onProductionAuth}
                />
                {isAppleAvailable ? (
                  <SocialButton
                    dark
                    disabled={isSubmitting}
                    icon={evtAssets.appleIcon}
                    label="login with Apple"
                    onPress={onAppleAuth}
                  />
                ) : null}
              </>
            ) : null}
            <Pressable accessibilityRole="button" disabled={isSubmitting} onPress={onDemoAuth} style={styles.demoButton}>
              <Text style={styles.demoButtonText}>{isSubmitting ? "Opening demo..." : "Try PlantLab Demo"}</Text>
            </Pressable>
          </View>

          <View style={styles.signupRow}>
            <Text style={styles.signupMuted}>Don't have an account?</Text>
            <Pressable accessibilityRole="button" onPress={() => router.push("/register" as never)}>
              <Text style={styles.signupLink}>Sign Up</Text>
            </Pressable>
          </View>
        </View>
      </Screen>
    </ImageBackground>
  );
}

function AuthField({
  accessibilityLabel,
  autoCapitalize,
  autoComplete,
  icon,
  keyboardType,
  onChangeText,
  placeholder,
  secureTextEntry,
  trailingIcon,
  value,
}: {
  accessibilityLabel: string;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  autoComplete?: "email" | "password";
  icon: ImageSourcePropType;
  keyboardType?: "default" | "email-address" | "phone-pad" | "number-pad";
  onChangeText: (value: string) => void;
  placeholder: string;
  secureTextEntry?: boolean;
  trailingIcon?: ImageSourcePropType;
  value: string;
}) {
  return (
    <View style={styles.field}>
      <Image source={icon} style={styles.fieldIcon} resizeMode="contain" />
      <TextInput
        accessibilityLabel={accessibilityLabel}
        autoCapitalize={autoCapitalize}
        autoComplete={autoComplete}
        autoCorrect={false}
        keyboardType={keyboardType}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.textMuted}
        secureTextEntry={secureTextEntry}
        style={styles.input}
        value={value}
      />
      {trailingIcon ? <Image source={trailingIcon} style={styles.trailingIcon} resizeMode="contain" /> : null}
    </View>
  );
}

function SocialButton({
  dark = false,
  disabled,
  icon,
  label,
  onPress,
}: {
  dark?: boolean;
  disabled?: boolean;
  icon: ImageSourcePropType;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [styles.socialButton, dark ? styles.socialButtonDark : null, disabled ? styles.disabled : null, pressed ? styles.pressed : null]}
    >
      <Image source={icon} style={styles.socialIcon} resizeMode="contain" />
      <Text style={[styles.socialLabel, dark ? styles.socialLabelDark : null]}>{label}</Text>
    </Pressable>
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
  background: {
    flex: 1,
  },
  authContent: {
    gap: 20,
    minHeight: 680,
    paddingTop: 28,
  },
  brandBlock: {
    alignItems: "center",
    gap: 8,
  },
  leafLogo: {
    height: 56,
    width: 56,
  },
  logoText: {
    color: "#6f6f6f",
    fontSize: 21,
    fontWeight: "600",
    letterSpacing: 0,
  },
  logoAccent: {
    color: theme.colors.secondaryGreen,
  },
  heroTitle: {
    color: theme.colors.darkGreen,
    fontSize: 17,
    fontWeight: "900",
    lineHeight: 24,
    marginTop: 18,
    maxWidth: 300,
    textAlign: "center",
  },
  helperText: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.meta,
    textAlign: "center",
  },
  form: {
    gap: 14,
    marginTop: 8,
  },
  field: {
    alignItems: "center",
    backgroundColor: "rgba(255, 255, 255, 0.78)",
    borderColor: theme.colors.darkGreen,
    borderRadius: 10,
    borderWidth: 1,
    flexDirection: "row",
    minHeight: 47,
    paddingHorizontal: 18,
  },
  fieldIcon: {
    height: 18,
    tintColor: theme.colors.darkGreen,
    width: 18,
  },
  input: {
    color: theme.colors.textPrimary,
    flex: 1,
    fontSize: theme.evtTypography.body,
    minHeight: 47,
    paddingHorizontal: 18,
  },
  trailingIcon: {
    height: 16,
    tintColor: theme.colors.darkGreen,
    width: 16,
  },
  errorText: {
    color: theme.colors.danger,
    fontSize: theme.evtTypography.meta,
    fontWeight: "700",
  },
  forgotButton: {
    alignSelf: "flex-end",
    minHeight: 32,
    justifyContent: "center",
  },
  forgotText: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.meta,
  },
  socialStack: {
    gap: 12,
  },
  socialButton: {
    alignItems: "center",
    backgroundColor: theme.colors.white,
    borderColor: theme.colors.border,
    borderRadius: 10,
    borderWidth: 1,
    flexDirection: "row",
    gap: 38,
    minHeight: 47,
    paddingHorizontal: 20,
  },
  socialButtonDark: {
    backgroundColor: "#000000",
    borderColor: "#000000",
  },
  socialIcon: {
    height: 20,
    width: 20,
  },
  socialLabel: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.bodyLarge,
    fontWeight: "700",
  },
  socialLabelDark: {
    color: theme.colors.white,
  },
  demoButton: {
    alignItems: "center",
    minHeight: 36,
    justifyContent: "center",
  },
  demoButtonText: {
    color: theme.colors.darkGreen,
    fontSize: theme.evtTypography.body,
    fontWeight: "800",
  },
  signupRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 14,
    justifyContent: "center",
    marginTop: "auto",
    paddingBottom: 12,
  },
  signupMuted: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.meta,
  },
  signupLink: {
    color: theme.colors.darkGreen,
    fontSize: theme.evtTypography.meta,
  },
  disabled: {
    opacity: 0.56,
  },
  pressed: {
    opacity: 0.82,
  },
});
