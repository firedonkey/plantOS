import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

type EmptyStateProps = {
  title: string;
  message: string;
};

export function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <View style={styles.container}>
      <View style={styles.indicator} />
      <View style={styles.copy}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.message}>{message}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "flex-start",
    backgroundColor: theme.colors.surfaceMuted,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    gap: theme.spacing.md,
    padding: theme.spacing.lg,
  },
  indicator: {
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radii.pill,
    height: 3,
    width: 32,
  },
  copy: {
    gap: theme.spacing.xs,
  },
  title: {
    color: theme.colors.textPrimary,
    fontSize: theme.typography.bodyLarge,
    fontWeight: "800",
  },
  message: {
    color: theme.colors.textSecondary,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
});
