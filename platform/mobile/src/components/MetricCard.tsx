import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

type MetricCardProps = {
  label: string;
  value: string;
  meta?: string;
  tone?: "primary" | "secondary";
  children?: ReactNode;
};

export function MetricCard({ label, value, meta, tone = "primary", children }: MetricCardProps) {
  return (
    <View style={[styles.card, tone === "secondary" ? styles.secondaryCard : null]}>
      <Text style={styles.label}>{label}</Text>
      {children ? (
        <View style={styles.valueRow}>
          <Text style={[styles.value, tone === "secondary" ? styles.secondaryValue : null]}>{value}</Text>
          {children}
        </View>
      ) : (
        <Text style={[styles.value, tone === "secondary" ? styles.secondaryValue : null]}>{value}</Text>
      )}
      {meta ? <Text style={styles.meta}>{meta}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexBasis: "48%",
    flexGrow: 1,
    minHeight: 104,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    gap: theme.spacing.sm,
  },
  secondaryCard: {
    minHeight: 88,
    backgroundColor: theme.colors.surfaceMuted,
  },
  label: {
    fontSize: theme.typography.meta,
    fontWeight: "700",
    color: theme.colors.textSecondary,
  },
  value: {
    fontSize: 27,
    fontWeight: "800",
    color: theme.colors.textPrimary,
  },
  secondaryValue: {
    fontSize: 22,
  },
  meta: {
    fontSize: theme.typography.caption,
    color: theme.colors.textMuted,
  },
  valueRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
});
