import { router } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { theme } from "@/styles/theme";

export function LandingScreen() {
  return (
    <Screen>
      <View style={styles.hero}>
        <View style={styles.brandRow}>
          <View style={styles.brandMark}>
            <View style={styles.brandSproutStem} />
            <View style={styles.brandSproutLeft} />
            <View style={styles.brandSproutRight} />
          </View>
          <Text style={styles.brandText}>PlantLab</Text>
        </View>

        <Text style={styles.eyebrow}>SMART GROWING AT HOME</Text>
        <Text style={styles.title}>A calmer way to care for your plants.</Text>
        <Text style={styles.subtitle}>
          Monitor readings, review plant photos, and control your grow light from one simple app.
        </Text>
      </View>

      <View style={styles.productVisual} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
        <View style={styles.growLight} />
        <View style={styles.lightBeam} />
        <View style={styles.sensorPanel}>
          <Metric label="Air" value="26.4 C" />
          <Metric label="Humidity" value="38%" />
          <Metric label="Water" value="25.0 C" />
        </View>
        <View style={styles.planterScene}>
          <View style={styles.leftLeaf} />
          <View style={styles.stem} />
          <View style={styles.rightLeaf} />
          <View style={styles.planter} />
        </View>
      </View>

      <View style={styles.featureList}>
        <Feature title="Live device status" body="See sensor trends, connectivity, and alerts without opening a terminal." />
        <Feature title="Photos over time" body="Check recent camera captures to understand how your plant is changing." />
        <Feature title="Mobile setup" body="Add the device from your iPhone, then monitor it anywhere." />
      </View>

      <View style={styles.cta}>
        <PrimaryButton label="Get started" onPress={() => router.push("/login")} />
        <Text style={styles.ctaNote}>Already using PlantLab? Sign in to sync your devices.</Text>
      </View>
    </Screen>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.feature}>
      <View style={styles.featureMarker} />
      <View style={styles.featureCopy}>
        <Text style={styles.featureTitle}>{title}</Text>
        <Text style={styles.featureBody}>{body}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  hero: {
    gap: 14,
    marginTop: 34,
  },
  brandRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 10,
    marginBottom: 18,
  },
  brandMark: {
    width: 34,
    height: 34,
    borderRadius: 8,
    backgroundColor: theme.colors.textPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  brandSproutStem: {
    width: 3,
    height: 15,
    borderRadius: 2,
    backgroundColor: "#7ccf91",
    marginTop: 8,
  },
  brandSproutLeft: {
    position: "absolute",
    width: 13,
    height: 8,
    borderTopLeftRadius: 8,
    borderBottomRightRadius: 8,
    backgroundColor: "#7ccf91",
    top: 10,
    left: 8,
    transform: [{ rotate: "-22deg" }],
  },
  brandSproutRight: {
    position: "absolute",
    width: 13,
    height: 8,
    borderTopRightRadius: 8,
    borderBottomLeftRadius: 8,
    backgroundColor: "#94d86f",
    top: 9,
    right: 8,
    transform: [{ rotate: "22deg" }],
  },
  brandText: {
    color: theme.colors.textPrimary,
    fontSize: 18,
    fontWeight: "800",
  },
  eyebrow: {
    color: theme.colors.accent,
    fontSize: 13,
    fontWeight: "800",
  },
  title: {
    color: theme.colors.textPrimary,
    fontSize: 42,
    fontWeight: "800",
    lineHeight: 44,
  },
  subtitle: {
    color: theme.colors.textSecondary,
    fontSize: 17,
    lineHeight: 26,
  },
  productVisual: {
    height: 244,
    borderRadius: 8,
    backgroundColor: theme.colors.surfaceMuted,
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
  },
  growLight: {
    position: "absolute",
    top: 26,
    width: 128,
    height: 6,
    borderRadius: 4,
    backgroundColor: theme.colors.textPrimary,
    opacity: 0.9,
  },
  lightBeam: {
    position: "absolute",
    top: 38,
    width: 180,
    height: 106,
    borderRadius: 8,
    borderTopWidth: 1,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: "rgba(47, 133, 90, 0.14)",
    backgroundColor: "rgba(47, 133, 90, 0.04)",
  },
  sensorPanel: {
    position: "absolute",
    left: 14,
    right: 14,
    bottom: 14,
    flexDirection: "row",
    gap: 8,
  },
  metric: {
    flex: 1,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: "rgba(255, 255, 255, 0.88)",
    padding: 10,
  },
  metricLabel: {
    color: theme.colors.textSecondary,
    fontSize: 12,
    marginBottom: 2,
  },
  metricValue: {
    color: theme.colors.textPrimary,
    fontSize: 16,
    fontWeight: "800",
  },
  planterScene: {
    alignItems: "center",
    justifyContent: "flex-end",
    width: 120,
    height: 86,
    marginBottom: 42,
  },
  stem: {
    width: 5,
    height: 48,
    borderRadius: 3,
    backgroundColor: theme.colors.accent,
  },
  leftLeaf: {
    position: "absolute",
    bottom: 40,
    left: 35,
    width: 32,
    height: 16,
    borderTopLeftRadius: 16,
    borderBottomRightRadius: 16,
    backgroundColor: theme.colors.accent,
    transform: [{ rotate: "-20deg" }],
  },
  rightLeaf: {
    position: "absolute",
    bottom: 48,
    right: 33,
    width: 34,
    height: 17,
    borderTopRightRadius: 17,
    borderBottomLeftRadius: 17,
    backgroundColor: "#44a16d",
    transform: [{ rotate: "20deg" }],
  },
  planter: {
    width: 98,
    height: 20,
    borderRadius: 6,
    backgroundColor: theme.colors.textPrimary,
    opacity: 0.92,
  },
  featureList: {
    gap: 12,
  },
  feature: {
    flexDirection: "row",
    gap: 14,
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    backgroundColor: theme.colors.surface,
  },
  featureMarker: {
    width: 6,
    alignSelf: "stretch",
    borderRadius: 8,
    backgroundColor: theme.colors.accent,
  },
  featureCopy: {
    flex: 1,
    gap: 4,
  },
  featureTitle: {
    color: theme.colors.textPrimary,
    fontSize: 17,
    fontWeight: "800",
  },
  featureBody: {
    color: theme.colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
  },
  cta: {
    gap: 12,
    paddingBottom: 8,
  },
  ctaNote: {
    color: theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
    textAlign: "center",
  },
});
