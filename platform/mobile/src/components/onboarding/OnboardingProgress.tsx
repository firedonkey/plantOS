import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

export type OnboardingProgressStep = {
  id: string;
  label: string;
  description?: string;
};

type OnboardingProgressProps = {
  title: string;
  description: string;
  steps: OnboardingProgressStep[];
  currentStepId: string;
  completedStepIds?: string[];
  loading?: boolean;
  errorMessage?: string | null;
  successMessage?: string | null;
};

export function OnboardingProgress({
  title,
  description,
  steps,
  currentStepId,
  completedStepIds = [],
  loading = false,
  errorMessage,
  successMessage,
}: OnboardingProgressProps) {
  const completed = new Set(completedStepIds);
  const currentIndex = steps.findIndex((step) => step.id === currentStepId);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        {loading ? <ActivityIndicator color={theme.colors.accent} /> : null}
        <View style={styles.headerText}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.description}>{description}</Text>
        </View>
      </View>

      <View style={styles.steps}>
        {steps.map((step, index) => {
          const isComplete = completed.has(step.id);
          const isCurrent = step.id === currentStepId;
          const isPastCurrent = currentIndex >= 0 && index < currentIndex;
          const tone = isComplete || isPastCurrent ? "complete" : isCurrent ? "current" : "pending";

          return (
            <View key={step.id} style={styles.stepRow}>
              <View style={[styles.stepMarker, markerStyles[tone]]}>
                <Text style={[styles.stepMarkerText, markerTextStyles[tone]]}>{isComplete || isPastCurrent ? "OK" : index + 1}</Text>
              </View>
              <View style={styles.stepText}>
                <Text style={[styles.stepLabel, isCurrent && styles.stepLabelCurrent]}>{step.label}</Text>
                {step.description ? <Text style={styles.stepDescription}>{step.description}</Text> : null}
              </View>
            </View>
          );
        })}
      </View>

      {successMessage ? <Text style={styles.success}>{successMessage}</Text> : null}
      {errorMessage ? <Text style={styles.error}>{errorMessage}</Text> : null}
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
    gap: theme.spacing.lg,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: theme.spacing.md,
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
  description: {
    color: theme.colors.textSecondary,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
  steps: {
    gap: theme.spacing.md,
  },
  stepRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: theme.spacing.md,
  },
  stepMarker: {
    width: 28,
    height: 28,
    borderRadius: theme.radii.pill,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  stepMarkerText: {
    fontSize: theme.typography.caption,
    fontWeight: "800",
  },
  stepText: {
    flex: 1,
    gap: 2,
    paddingTop: 2,
  },
  stepLabel: {
    color: theme.colors.textSecondary,
    fontSize: theme.typography.body,
    fontWeight: "700",
  },
  stepLabelCurrent: {
    color: theme.colors.textPrimary,
  },
  stepDescription: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.meta,
    lineHeight: 18,
  },
  success: {
    color: theme.colors.success,
    fontSize: theme.typography.body,
    fontWeight: "700",
  },
  error: {
    color: theme.colors.danger,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
});

const markerStyles = StyleSheet.create({
  complete: {
    backgroundColor: theme.colors.successSoft,
    borderColor: theme.status.online.border,
  },
  current: {
    backgroundColor: theme.colors.accentSoft,
    borderColor: theme.colors.accent,
  },
  pending: {
    backgroundColor: theme.colors.surface,
    borderColor: theme.colors.border,
  },
});

const markerTextStyles = StyleSheet.create({
  complete: {
    color: theme.colors.success,
  },
  current: {
    color: theme.colors.accent,
  },
  pending: {
    color: theme.colors.textMuted,
  },
});
