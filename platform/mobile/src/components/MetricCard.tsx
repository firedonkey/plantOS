import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

type MetricCardProps = {
  label: string;
  value: string;
};

export function MetricCard({ label, value }: MetricCardProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
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
});
