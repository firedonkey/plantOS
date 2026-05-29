import { StyleSheet, Text, View } from "react-native";

import { PrimaryButton } from "@/components/PrimaryButton";
import { theme } from "@/styles/theme";

type RecoveryAction = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  tone?: "primary" | "secondary" | "danger";
};

type RecoveryScreenProps = {
  title: string;
  explanation: string;
  likelyCauses?: string[];
  recommendedActions?: string[];
  primaryAction: RecoveryAction;
  secondaryAction?: RecoveryAction;
  tertiaryAction?: RecoveryAction;
};

export function RecoveryScreen({
  title,
  explanation,
  likelyCauses = [],
  recommendedActions = [],
  primaryAction,
  secondaryAction,
  tertiaryAction,
}: RecoveryScreenProps) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.statusDot} />
        <View style={styles.headerText}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.explanation}>{explanation}</Text>
        </View>
      </View>

      {likelyCauses.length > 0 ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Things to check</Text>
          {likelyCauses.map((cause) => (
            <View key={cause} style={styles.listRow}>
              <Text style={styles.bullet}>-</Text>
              <Text style={styles.listText}>{cause}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {recommendedActions.length > 0 ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>What to do next</Text>
          {recommendedActions.map((action) => (
            <View key={action} style={styles.listRow}>
              <Text style={styles.bullet}>-</Text>
              <Text style={styles.listText}>{action}</Text>
            </View>
          ))}
        </View>
      ) : null}

      <View style={styles.actions}>
        <PrimaryButton
          disabled={primaryAction.disabled}
          label={primaryAction.label}
          onPress={primaryAction.onPress}
          tone={primaryAction.tone ?? "primary"}
        />
        {secondaryAction ? (
          <PrimaryButton
            disabled={secondaryAction.disabled}
            label={secondaryAction.label}
            onPress={secondaryAction.onPress}
            tone={secondaryAction.tone ?? "secondary"}
          />
        ) : null}
        {tertiaryAction ? (
          <PrimaryButton
            disabled={tertiaryAction.disabled}
            label={tertiaryAction.label}
            onPress={tertiaryAction.onPress}
            tone={tertiaryAction.tone ?? "secondary"}
          />
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.lg,
    gap: theme.spacing.lg,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: theme.spacing.md,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: theme.radii.pill,
    backgroundColor: theme.colors.warning,
    marginTop: 6,
  },
  headerText: {
    flex: 1,
    gap: theme.spacing.xs,
  },
  title: {
    color: theme.colors.textPrimary,
    fontSize: theme.typography.sectionTitle,
    fontWeight: "800",
  },
  explanation: {
    color: theme.colors.textSecondary,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
  section: {
    gap: theme.spacing.sm,
  },
  sectionTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.typography.body,
    fontWeight: "800",
  },
  listRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: theme.spacing.sm,
  },
  bullet: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
  listText: {
    flex: 1,
    color: theme.colors.textSecondary,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
  actions: {
    gap: theme.spacing.sm,
  },
});
