import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

export type OwnershipTransferInfoVariant = "conflict" | "postReset" | "reconnect" | "reset" | "transfer";

type OwnershipTransferInfoProps = {
  variant: OwnershipTransferInfoVariant;
  compact?: boolean;
};

const contentByVariant: Record<
  OwnershipTransferInfoVariant,
  {
    eyebrow: string;
    title: string;
    description: string;
    steps: string[];
    note?: string;
  }
> = {
  conflict: {
    eyebrow: "OWNERSHIP",
    title: "Moving PlantLab to a new account?",
    description: "PlantLab can only be connected to one account at a time.",
    steps: [
      "If this is your device, hold the setup button for 20 seconds until the light blinks quickly.",
      "Wait for PlantLab to restart. It can take about a minute to appear again.",
      "Start setup again from this account.",
    ],
    note: "If someone else owns this device, ask them to remove it from their account before setup.",
  },
  postReset: {
    eyebrow: "RESET",
    title: "PlantLab is restarting",
    description: "This can take about a minute after a full reset.",
    steps: [
      "Keep PlantLab powered on.",
      "Wait for the status light to return to setup mode.",
      "Look for PlantLab again when the light is blinking slowly.",
    ],
  },
  reconnect: {
    eyebrow: "WI-FI",
    title: "Reconnect PlantLab",
    description: "Use this when changing routers, moving rooms, or updating Wi-Fi details.",
    steps: [
      "Hold the setup button for 5 seconds until the light blinks slowly.",
      "Keep this device in your account.",
      "Send the new Wi-Fi details from this app.",
    ],
  },
  reset: {
    eyebrow: "FULL RESET",
    title: "Reset PlantLab",
    description: "Use a full reset when setup is stuck or the device needs to be added to another account.",
    steps: [
      "Hold the setup button for 20 seconds.",
      "Release when the light blinks quickly.",
      "Wait for PlantLab to restart before starting setup again.",
    ],
    note: "A full reset clears saved Wi-Fi on the device. Existing history may remain in the previous account unless the device was released there first.",
  },
  transfer: {
    eyebrow: "TRANSFER",
    title: "Prepare PlantLab for someone else",
    description: "Release it from this account first, then reset the physical device.",
    steps: [
      "Tap Prepare device for transfer.",
      "Hold the setup button for 20 seconds until the light blinks quickly.",
      "The next owner can add PlantLab from their account after it restarts.",
    ],
  },
};

export function OwnershipTransferInfo({ compact = false, variant }: OwnershipTransferInfoProps) {
  const content = contentByVariant[variant];
  return (
    <View style={[styles.container, compact && styles.compactContainer]}>
      <Text style={styles.eyebrow}>{content.eyebrow}</Text>
      <Text style={styles.title}>{content.title}</Text>
      <Text style={styles.description}>{content.description}</Text>
      <View style={styles.steps}>
        {content.steps.map((step, index) => (
          <View key={step} style={styles.stepRow}>
            <View style={styles.stepNumber}>
              <Text style={styles.stepNumberText}>{index + 1}</Text>
            </View>
            <Text style={styles.stepText}>{step}</Text>
          </View>
        ))}
      </View>
      {content.note ? <Text style={styles.note}>{content.note}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.surfaceMuted,
    padding: theme.spacing.lg,
    gap: theme.spacing.sm,
  },
  compactContainer: {
    padding: theme.spacing.md,
  },
  eyebrow: {
    color: theme.colors.accent,
    fontSize: theme.typography.eyebrow,
    fontWeight: "800",
  },
  title: {
    color: theme.colors.textPrimary,
    fontSize: theme.typography.sectionTitle,
    fontWeight: "800",
  },
  description: {
    color: theme.colors.textSecondary,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
  steps: {
    gap: theme.spacing.sm,
    marginTop: theme.spacing.xs,
  },
  stepRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: theme.spacing.sm,
  },
  stepNumber: {
    width: 22,
    height: 22,
    borderRadius: theme.radii.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.accentSoft,
    borderWidth: 1,
    borderColor: theme.status.online.border,
  },
  stepNumberText: {
    color: theme.colors.accent,
    fontSize: theme.typography.caption,
    fontWeight: "800",
  },
  stepText: {
    flex: 1,
    color: theme.colors.textSecondary,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
  note: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.meta,
    lineHeight: 18,
  },
});
