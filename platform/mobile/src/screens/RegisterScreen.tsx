import { useState } from "react";
import type { ReactNode } from "react";
import { router } from "expo-router";
import { Alert, Image, ImageBackground, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import type { ImageSourcePropType } from "react-native";

import { evtAssets } from "@/assets/evtAssets";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { theme } from "@/styles/theme";

export function RegisterScreen() {
  const [account, setAccount] = useState("");
  const [code, setCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const explainRegistration = () => {
    const nextMessage = "Account registration is not enabled in this EVT mobile build. Use Google, Apple, demo access, or local development sign-in.";
    setMessage(nextMessage);
    Alert.alert("Registration unavailable", nextMessage);
  };

  return (
    <ImageBackground source={evtAssets.authLeafFrame} resizeMode="cover" style={styles.background}>
      <Screen transparentBackground>
        <View style={styles.content}>
          <View style={styles.brandBlock}>
            <Image source={evtAssets.plantLabLeafLogo} style={styles.leafLogo} resizeMode="contain" />
            <Text style={styles.logoText}>PLANT<Text style={styles.logoAccent}>LAB</Text></Text>
            <Text style={styles.heroTitle}>PLANT INTELLIGENCE MONITORING PLATFORM</Text>
          </View>

          <View style={styles.form}>
            <RegisterField
              accessibilityLabel="Mobile phone number or email"
              icon={evtAssets.accountIcon}
              keyboardType="email-address"
              onChangeText={setAccount}
              placeholder="Enter your mobile phone number"
              value={account}
            />
            <RegisterField
              accessibilityLabel="Verification code"
              icon={evtAssets.lockIcon}
              keyboardType="number-pad"
              onChangeText={setCode}
              placeholder="Enter the verification code"
              trailing={
                <Pressable accessibilityRole="button" onPress={explainRegistration} style={styles.sendButton}>
                  <Text style={styles.sendText}>send</Text>
                </Pressable>
              }
              value={code}
            />
            {message ? <Text style={styles.message}>{message}</Text> : null}
            <PrimaryButton label="REGISTER" onPress={explainRegistration} disabled={!account.trim() || !code.trim()} />
          </View>

          <View style={styles.footer}>
            <Text style={styles.footerMuted}>Already have an account?</Text>
            <Pressable accessibilityRole="button" onPress={() => router.replace("/login")}>
              <Text style={styles.footerLink}>Log In</Text>
            </Pressable>
          </View>
        </View>
      </Screen>
    </ImageBackground>
  );
}

function RegisterField({
  accessibilityLabel,
  icon,
  keyboardType,
  onChangeText,
  placeholder,
  trailing,
  value,
}: {
  accessibilityLabel: string;
  icon: ImageSourcePropType;
  keyboardType?: "default" | "email-address" | "phone-pad" | "number-pad";
  onChangeText: (value: string) => void;
  placeholder: string;
  trailing?: ReactNode;
  value: string;
}) {
  return (
    <View style={styles.field}>
      <Image source={icon} style={styles.fieldIcon} resizeMode="contain" />
      <TextInput
        accessibilityLabel={accessibilityLabel}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType={keyboardType}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.textMuted}
        style={styles.input}
        value={value}
      />
      {trailing}
    </View>
  );
}

const styles = StyleSheet.create({
  background: {
    flex: 1,
  },
  content: {
    gap: 36,
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
  form: {
    gap: 20,
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
  sendButton: {
    minHeight: 36,
    minWidth: 46,
    justifyContent: "center",
  },
  sendText: {
    color: theme.colors.darkGreen,
    fontSize: theme.evtTypography.body,
    fontWeight: "800",
    textAlign: "center",
  },
  message: {
    color: theme.colors.warning,
    fontSize: theme.evtTypography.meta,
    lineHeight: 18,
  },
  footer: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    justifyContent: "center",
    marginTop: "auto",
    paddingBottom: 12,
  },
  footerMuted: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.meta,
  },
  footerLink: {
    color: theme.colors.darkGreen,
    fontSize: theme.evtTypography.meta,
  },
});
