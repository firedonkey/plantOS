import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

type MetricCardProps = {
  label: string;
  value: string;
  children?: ReactNode;
};

export function MetricCard({ label, value, children }: MetricCardProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      {children ? (
        <View style={styles.valueRow}>
          <Text style={styles.value}>{value}</Text>
          {children}
        </View>
      ) : (
        <Text style={styles.value}>{value}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexBasis: "48%",
    flexGrow: 1,
    minHeight: 96,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: 14,
    backgroundColor: theme.colors.surface,
    gap: 8,
  },
  label: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  value: {
    fontSize: 28,
    fontWeight: "700",
    color: theme.colors.textPrimary,
  },
  valueRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
});
